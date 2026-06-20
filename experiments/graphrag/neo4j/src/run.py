"""Neo4j を使った GraphRAG パイプラインの PoC。"""

import json
import os
from pathlib import Path

import httpx
from neo4j import GraphDatabase

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "testpassword")

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def embed(text: str) -> list[float]:
    """Ollama でテキストを埋め込みベクトルに変換する。"""
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def generate(context: str, question: str) -> str:
    """Ollama でコンテキストを元に質問に回答する。"""
    prompt = (
        "以下の情報を参考に質問に答えてください。\n\n"
        f"コンテキスト:\n{context}\n\n"
        f"質問: {question}\n\n回答:"
    )
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def setup_schema(driver: GraphDatabase, dims: int) -> None:
    """制約とベクトルインデックスを作成する。"""
    with driver.session() as session:
        session.run(
            "CREATE CONSTRAINT concept_node_id IF NOT EXISTS "
            "FOR (n:Concept) REQUIRE n.node_id IS UNIQUE"
        )
        session.run(
            f"CREATE VECTOR INDEX concept_embedding IF NOT EXISTS "
            f"FOR (n:Concept) ON (n.embedding) "
            f"OPTIONS {{indexConfig: {{`vector.dimensions`: {dims}, "
            f"`vector.similarity_function`: 'cosine'}}}}"
        )


def insert_nodes(driver: GraphDatabase, nodes: list[dict]) -> None:
    """ノードを埋め込みと共に Neo4j に挿入する。"""
    with driver.session() as session:
        for node in nodes:
            vec = embed(node["content"])
            session.run(
                "MERGE (n:Concept {node_id: $node_id}) "
                "SET n.label = $label, n.content = $content, n.embedding = $embedding",
                node_id=node["id"],
                label=node["label"],
                content=node["content"],
                embedding=vec,
            )
            print(f"  ✓ ノード挿入: {node['label']}")


def insert_edges(driver: GraphDatabase, edges: list[dict]) -> None:
    """エッジ（グラフ関係）を Neo4j に挿入する。"""
    with driver.session() as session:
        for edge in edges:
            session.run(
                "MATCH (a:Concept {node_id: $from_id}), (b:Concept {node_id: $to_id}) "
                "MERGE (a)-[:HAS_RELATION {relation: $relation}]->(b)",
                from_id=edge["from"],
                to_id=edge["to"],
                relation=edge["relation"],
            )
            print(f"  ✓ エッジ挿入: {edge['from']} --[{edge['relation']}]--> {edge['to']}")


def vector_search(driver: GraphDatabase, query_vec: list[float], top_k: int = 3) -> list[dict]:
    """ベクトルインデックスで類似ノードを取得する。"""
    with driver.session() as session:
        result = session.run(
            "CALL db.index.vector.queryNodes('concept_embedding', $k, $vec) "
            "YIELD node, score "
            "RETURN node.node_id AS node_id, node.label AS label, "
            "node.content AS content, score",
            k=top_k,
            vec=query_vec,
        )
        return [dict(r) for r in result]


def graph_traverse(driver: GraphDatabase, node_ids: list[str]) -> list[dict]:
    """指定ノードからグラフを1ホップ走査して関連ノードを取得する。"""
    related = []
    with driver.session() as session:
        for nid in node_ids:
            result = session.run(
                "MATCH (n:Concept {node_id: $id})-[:HAS_RELATION]->(r:Concept) "
                "RETURN r.node_id AS node_id, r.label AS label, r.content AS content",
                id=nid,
            )
            related.extend([dict(r) for r in result])
    return related


def main() -> None:
    """GraphRAG パイプラインを実行する。"""
    print("=== Neo4j GraphRAG PoC ===\n")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    try:
        # 埋め込み次元を検出
        print("[1/5] 埋め込み次元を検出中...")
        probe_vec = embed("test")
        dims = len(probe_vec)
        print(f"  埋め込み次元: {dims}\n")

        # スキーマ設定
        print("[2/5] スキーマを設定中...")
        setup_schema(driver, dims)
        print("  ✓ スキーマ設定完了\n")

        # ノード挿入
        print("[3/5] ノードを挿入中...")
        insert_nodes(driver, data["nodes"])
        print()

        # エッジ挿入
        print("[4/5] エッジを挿入中...")
        insert_edges(driver, data["edges"])
        print()

        # クエリ実行
        question = data["query"]
        print(f"[5/5] クエリ実行: {question}\n")

        query_vec = embed(question)
        vector_hits = vector_search(driver, query_vec, top_k=3)
        print(f"  ベクトル検索ヒット: {[h['label'] for h in vector_hits]}")

        graph_hits = graph_traverse(driver, [h["node_id"] for h in vector_hits])
        print(f"  グラフ展開ヒット: {[h.get('label', '?') for h in graph_hits]}\n")

        all_nodes = vector_hits + graph_hits
        seen = set()
        unique_nodes = []
        for n in all_nodes:
            if n.get("node_id") and n["node_id"] not in seen:
                seen.add(n["node_id"])
                unique_nodes.append(n)

        context = "\n".join(f"- {n['label']}: {n['content']}" for n in unique_nodes)
        answer = generate(context, question)

        print("=== 回答 ===")
        print(answer)

    finally:
        driver.close()


if __name__ == "__main__":
    main()

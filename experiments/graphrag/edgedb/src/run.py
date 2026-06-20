"""EdgeDB を使った GraphRAG パイプラインの PoC。"""

import json
import os
from pathlib import Path

import httpx
import numpy as np
import edgedb

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

EDGEDB_DSN = os.getenv(
    "EDGEDB_DSN",
    "edgedb://edgedb@localhost:5656/edgedb?tls_security=insecure",
)

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


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """2つのベクトルのコサイン類似度を計算する。"""
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom != 0.0 else 0.0


def setup_schema(client: edgedb.Client) -> None:
    """EdgeDB にスキーマを作成する（devmode では DDL を直接実行可能）。"""
    client.execute("""
        CREATE TYPE IF NOT EXISTS default::Concept {
            CREATE REQUIRED PROPERTY node_id -> str {
                CREATE CONSTRAINT exclusive;
            };
            CREATE REQUIRED PROPERTY label -> str;
            CREATE REQUIRED PROPERTY content -> str;
            CREATE PROPERTY embedding -> array<float64>;
            CREATE MULTI LINK related_concepts -> default::Concept;
        };
    """)


def insert_nodes(client: edgedb.Client, nodes: list[dict]) -> None:
    """ノードを埋め込みと共に EdgeDB に挿入する。"""
    for node in nodes:
        vec = embed(node["content"])
        client.query(
            """
            INSERT default::Concept {
                node_id := <str>$node_id,
                label   := <str>$label,
                content := <str>$content,
                embedding := <array<float64>>$embedding,
            } UNLESS CONFLICT ON .node_id;
            """,
            node_id=node["id"],
            label=node["label"],
            content=node["content"],
            embedding=vec,
        )
        print(f"  ✓ ノード挿入: {node['label']}")


def insert_edges(client: edgedb.Client, edges: list[dict]) -> None:
    """エッジ（グラフ関係）を EdgeDB のリンクとして挿入する。"""
    for edge in edges:
        client.query(
            """
            UPDATE default::Concept
            FILTER .node_id = <str>$from_id
            SET {
                related_concepts += (
                    SELECT default::Concept FILTER .node_id = <str>$to_id
                )
            };
            """,
            from_id=edge["from"],
            to_id=edge["to"],
        )
        print(f"  ✓ エッジ挿入: {edge['from']} --[{edge['relation']}]--> {edge['to']}")


def vector_search(
    client: edgedb.Client, query_vec: list[float], top_k: int = 3
) -> list[dict]:
    """全ノードの埋め込みを取得し、Python でコサイン類似度を計算してソートする。"""
    all_nodes = client.query(
        "SELECT default::Concept { node_id, label, content, embedding }"
    )
    scored = [
        {
            "node_id": n.node_id,
            "label": n.label,
            "content": n.content,
            "score": cosine_similarity(query_vec, list(n.embedding)),
        }
        for n in all_nodes
        if n.embedding
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def graph_traverse(client: edgedb.Client, node_ids: list[str]) -> list[dict]:
    """指定ノードのリンク先（related_concepts）を取得する。"""
    related = []
    for nid in node_ids:
        result = client.query(
            """
            SELECT default::Concept {
                related_concepts: { node_id, label, content }
            }
            FILTER .node_id = <str>$id
            """,
            id=nid,
        )
        for row in result:
            for r in row.related_concepts:
                related.append({
                    "node_id": r.node_id,
                    "label": r.label,
                    "content": r.content,
                })
    return related


def main() -> None:
    """GraphRAG パイプラインを実行する。"""
    print("=== EdgeDB GraphRAG PoC ===\n")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    client = edgedb.create_client(dsn=EDGEDB_DSN)

    try:
        # 埋め込み次元を検出
        print("[1/5] 埋め込み次元を検出中...")
        probe_vec = embed("test")
        dims = len(probe_vec)
        print(f"  埋め込み次元: {dims}\n")

        # スキーマ設定
        print("[2/5] スキーマを設定中...")
        setup_schema(client)
        print("  ✓ スキーマ設定完了\n")

        # ノード挿入
        print("[3/5] ノードを挿入中...")
        insert_nodes(client, data["nodes"])
        print()

        # エッジ挿入
        print("[4/5] エッジを挿入中...")
        insert_edges(client, data["edges"])
        print()

        # クエリ実行
        question = data["query"]
        print(f"[5/5] クエリ実行: {question}\n")

        query_vec = embed(question)
        vector_hits = vector_search(client, query_vec, top_k=3)
        print(f"  ベクトル検索ヒット: {[h['label'] for h in vector_hits]}")

        graph_hits = graph_traverse(client, [h["node_id"] for h in vector_hits])
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
        client.close()


if __name__ == "__main__":
    main()

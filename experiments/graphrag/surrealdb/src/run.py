"""SurrealDB を使った GraphRAG パイプラインの PoC。"""

import json
import os
from pathlib import Path

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

SURREAL_URL = os.getenv("SURREAL_URL", "http://localhost:8000")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS = os.getenv("SURREAL_NS", "graphrag_ns")
SURREAL_DB = os.getenv("SURREAL_DB", "graphrag_db")

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


def surreal_query(sql: str) -> list:
    """SurrealDB HTTP API に SQL を送信して結果を返す。"""
    resp = httpx.post(
        f"{SURREAL_URL}/sql",
        content=sql,
        headers={
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "NS": SURREAL_NS,
            "DB": SURREAL_DB,
        },
        auth=(SURREAL_USER, SURREAL_PASS),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def setup_schema(dims: int) -> None:
    """テーブル定義とベクトルインデックスを作成する。"""
    surreal_query(f"""
        DEFINE TABLE concept SCHEMALESS;
        DEFINE FIELD node_id   ON concept TYPE string;
        DEFINE FIELD label     ON concept TYPE string;
        DEFINE FIELD content   ON concept TYPE string;
        DEFINE FIELD embedding ON concept TYPE array;
        DEFINE INDEX idx_embedding ON TABLE concept COLUMNS embedding
            HNSW DIMENSION {dims} DIST COSINE;
    """)


def insert_nodes(nodes: list[dict]) -> None:
    """ノードを埋め込みと共に SurrealDB に挿入する。"""
    for node in nodes:
        vec = embed(node["content"])
        vec_str = json.dumps(vec)
        surreal_query(f"""
            CREATE concept:{node['id']} SET
                node_id   = '{node['id']}',
                label     = '{node['label']}',
                content   = '{node['content']}',
                embedding = {vec_str};
        """)
        print(f"  ✓ ノード挿入: {node['label']}")


def insert_edges(edges: list[dict]) -> None:
    """エッジ（グラフ関係）を SurrealDB に挿入する。"""
    for edge in edges:
        surreal_query(f"""
            RELATE concept:{edge['from']}->has_relation->concept:{edge['to']}
                SET relation = '{edge['relation']}';
        """)
        print(f"  ✓ エッジ挿入: {edge['from']} --[{edge['relation']}]--> {edge['to']}")


def vector_search(query_vec: list[float], top_k: int = 3) -> list[dict]:
    """ベクトル類似度検索で上位ノードを取得する。"""
    vec_str = json.dumps(query_vec)
    result = surreal_query(f"""
        SELECT node_id, label, content
        FROM concept
        WHERE embedding <|{top_k},COSINE|> {vec_str};
    """)
    return result[0].get("result", [])


def graph_traverse(node_ids: list[str]) -> list[dict]:
    """指定ノードからグラフを1ホップ走査して関連ノードを取得する。"""
    related = []
    for nid in node_ids:
        result = surreal_query(f"""
            SELECT ->has_relation->concept.* AS related
            FROM concept:{nid};
        """)
        for row in result[0].get("result", []):
            for r in row.get("related", []):
                if r:
                    related.append(r)
    return related


def main() -> None:
    """GraphRAG パイプラインを実行する。"""
    print("=== SurrealDB GraphRAG PoC ===\n")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    # 埋め込み次元を検出
    print("[1/5] 埋め込み次元を検出中...")
    probe_vec = embed("test")
    dims = len(probe_vec)
    print(f"  埋め込み次元: {dims}\n")

    # スキーマ設定
    print("[2/5] スキーマを設定中...")
    setup_schema(dims)
    print("  ✓ スキーマ設定完了\n")

    # ノード挿入
    print("[3/5] ノードを挿入中...")
    insert_nodes(data["nodes"])
    print()

    # エッジ挿入
    print("[4/5] エッジを挿入中...")
    insert_edges(data["edges"])
    print()

    # クエリ実行
    question = data["query"]
    print(f"[5/5] クエリ実行: {question}\n")

    query_vec = embed(question)
    vector_hits = vector_search(query_vec, top_k=3)
    print(f"  ベクトル検索ヒット: {[h['label'] for h in vector_hits]}")

    graph_hits = graph_traverse([h["node_id"] for h in vector_hits])
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


if __name__ == "__main__":
    main()

"""グラフを検索して回答を生成する（ベクトル検索とグラフ検索の並列実行）。

使い方:
    python src/query.py "質問文"
"""

import sys

from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_surrealdb.vectorstores import SurrealDBVectorStore

from common import extract_entities, generate, get_connection, get_embeddings, surreal_query

TABLE = "concept"


def _surreal_result(rows: list) -> list:
    """SurrealDBクライアントの結果形式差を吸収してリストを返す。"""
    if rows and isinstance(rows[0], dict) and "result" in rows[0]:
        return rows[0].get("result", [])
    return rows or []


def vector_search(question: str, top_k: int = 3) -> list[dict]:
    """SurrealDBVectorStoreでベクトル類似検索する。"""
    conn = get_connection()
    store = SurrealDBVectorStore(embedding=get_embeddings(), connection=conn, table=TABLE)
    hits = store.similarity_search(question, k=top_k)
    return [{"node_id": d.metadata.get("node_id", ""), "label": d.metadata.get("label", ""),
             "content": d.page_content} for d in hits]


def graph_search(question: str) -> list[dict]:
    """LLMエンティティ抽出 → BM25全文検索 → グラフ探索（ベクトル検索と独立）。"""
    entities = extract_entities(question)
    results: list[dict] = []
    seen: set[str] = set()
    for entity in entities:
        escaped = entity.replace("'", "\\'")
        rows = surreal_query(
            f"SELECT node_id, label, content FROM {TABLE} "
            f"WHERE label @@ '{escaped}' OR content @@ '{escaped}' LIMIT 5;")
        nodes = _surreal_result(rows)
        for node in nodes:
            nid = node.get("node_id")
            if not nid or nid in seen:
                continue
            seen.add(nid)
            results.append(node)
            related_rows = surreal_query(f"SELECT ->has_relation->{TABLE}.* AS related FROM {TABLE}:⟨{nid}⟩;")
            for row in _surreal_result(related_rows):
                for r in row.get("related", []):
                    if r and r.get("node_id") not in seen:
                        seen.add(r["node_id"])
                        results.append(r)
    return results


def retrieve(question: str, top_k: int = 3) -> list[dict]:
    """ベクトル検索とグラフ検索を並列実行してコンテキストノードをマージする。"""
    chain = RunnableParallel({
        "vector": RunnableLambda(lambda q: vector_search(q, top_k)),
        "graph": RunnableLambda(graph_search),
    })
    results = chain.invoke(question)
    print(f"  ベクトル検索: {[n['label'] for n in results['vector']]}")
    print(f"  グラフ検索:   {[n['label'] for n in results['graph']]}")
    seen: set[str] = set()
    unique = []
    for n in results["vector"] + results["graph"]:
        if n.get("node_id") and n["node_id"] not in seen:
            seen.add(n["node_id"])
            unique.append(n)
    return unique


def main() -> None:
    """質問を受けてGraphRAGで回答する。"""
    if len(sys.argv) < 2:
        print("使い方: python src/query.py \"質問文\"", file=sys.stderr)
        sys.exit(1)
    question = sys.argv[1]
    print(f"=== SurrealDB Hybrid RAG Query ===\n質問: {question}\n")
    nodes = retrieve(question)
    print(f"\n  コンテキストノード数: {len(nodes)}")
    context = "\n".join(f"- {n['label']}: {n['content']}" for n in nodes)
    print(f"\n=== 回答 ===\n{generate(context, question)}")


if __name__ == "__main__":
    main()

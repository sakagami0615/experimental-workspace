"""グラフを検索して回答を生成する（ベクトル検索とグラフ検索の並列実行）。

使い方:
    python src/query.py "質問文"
"""

import sys

from langchain_core.runnables import RunnableLambda, RunnableParallel

from common import cosine_similarity, extract_entities, generate, get_client, get_embeddings


def vector_search(question: str, top_k: int = 3) -> list[dict]:
    """全ノードのコサイン類似度を計算してtop-kを返す。"""
    query_vec = get_embeddings().embed_query(question)
    client = get_client()
    try:
        all_nodes = client.query("SELECT default::Concept { node_id, label, content, embedding }")
        scored = sorted(
            [{"node_id": n.node_id, "label": n.label, "content": n.content,
              "score": cosine_similarity(query_vec, list(n.embedding))}
             for n in all_nodes if n.embedding],
            key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
    finally:
        client.close()


def graph_search(question: str) -> list[dict]:
    """LLMエンティティ抽出 → ILIKEキーワード検索 → グラフ探索（ベクトル検索と独立）。"""
    entities = extract_entities(question)
    client = get_client()
    try:
        results: list[dict] = []
        seen: set[str] = set()
        for entity in entities:
            nodes = client.query(
                "SELECT default::Concept { node_id, label, content } "
                "FILTER .label ILIKE <str>$term OR .content ILIKE <str>$term",
                term=f"%{entity}%",
            )
            for node in nodes:
                if node.node_id in seen:
                    continue
                seen.add(node.node_id)
                results.append({"node_id": node.node_id, "label": node.label, "content": node.content})
                for row in client.query(
                    "SELECT default::Concept { related_concepts: { node_id, label, content } } "
                    "FILTER .node_id = <str>$id",
                    id=node.node_id,
                ):
                    for r in row.related_concepts:
                        if r.node_id not in seen:
                            seen.add(r.node_id)
                            results.append({"node_id": r.node_id, "label": r.label, "content": r.content})
        return results
    finally:
        client.close()


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
    print(f"=== EdgeDB Hybrid RAG Query ===\n質問: {question}\n")
    nodes = retrieve(question)
    print(f"\n  コンテキストノード数: {len(nodes)}")
    context = "\n".join(f"- {n['label']}: {n['content']}" for n in nodes)
    print(f"\n=== 回答 ===\n{generate(context, question)}")


if __name__ == "__main__":
    main()

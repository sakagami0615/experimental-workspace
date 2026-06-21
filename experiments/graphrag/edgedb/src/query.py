"""グラフを検索して回答を生成する。

使い方:
    python src/query.py "質問文"
"""

import sys

import edgedb

from common import cosine_similarity, generate, get_client, get_embeddings


def retrieve(client: edgedb.Client, question: str, top_k: int = 3) -> list[dict]:
    """Python側コサイン類似度によるベクトル検索とグラフ展開で重複なしのコンテキストノードを返す。"""
    query_vec = get_embeddings().embed_query(question)
    all_nodes = client.query("SELECT default::Concept { node_id, label, content, embedding }")
    scored = sorted(
        [{"node_id": n.node_id, "label": n.label, "content": n.content,
          "score": cosine_similarity(query_vec, list(n.embedding))}
         for n in all_nodes if n.embedding],
        key=lambda x: x["score"], reverse=True)
    hits = scored[:top_k]
    print(f"  ベクトルヒット: {[h['label'] for h in hits]}")

    related: list[dict] = []
    for nid in [h["node_id"] for h in hits]:
        for row in client.query(
                "SELECT default::Concept { related_concepts: { node_id, label, content } } FILTER .node_id=<str>$id",
                id=nid):
            related += [{"node_id": r.node_id, "label": r.label, "content": r.content}
                        for r in row.related_concepts]

    seen: set[str] = set()
    unique = []
    for n in hits + related:
        if n.get("node_id") and n["node_id"] not in seen:
            seen.add(n["node_id"])
            unique.append(n)
    print(f"  コンテキストノード数: {len(unique)}")
    return unique


def main() -> None:
    """質問を受けてGraphRAGで回答する。"""
    if len(sys.argv) < 2:
        print("使い方: python src/query.py \"質問文\"", file=sys.stderr)
        sys.exit(1)
    question = sys.argv[1]
    print(f"=== EdgeDB Query ===\n質問: {question}\n")
    client = get_client()
    try:
        nodes = retrieve(client, question)
        context = "\n".join(f"- {n['label']}: {n['content']}" for n in nodes)
        print(f"\n=== 回答 ===\n{generate(context, question)}")
    finally:
        client.close()


if __name__ == "__main__":
    main()

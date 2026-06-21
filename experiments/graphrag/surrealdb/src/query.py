"""グラフを検索して回答を生成する。

使い方:
    python src/query.py "質問文"
"""

import sys

from langchain_surrealdb.vectorstores import SurrealDBVectorStore

from common import generate, get_connection, get_embeddings

TABLE = "concept"


def retrieve(question: str, top_k: int = 3) -> list[dict]:
    """ベクトル検索とグラフ展開で重複なしのコンテキストノードを返す。"""
    conn = get_connection()
    store = SurrealDBVectorStore(embedding=get_embeddings(), connection=conn, table=TABLE)

    hits = store.similarity_search(question, k=top_k)
    print(f"  ベクトルヒット: {[d.metadata.get('label') for d in hits]}")

    contexts = [{"label": d.metadata.get("label", ""), "content": d.page_content} for d in hits]
    seen = {d.metadata.get("node_id") for d in hits}

    for doc in hits:
        nid = doc.metadata.get("node_id")
        if not nid:
            continue
        rows = conn.query(f"SELECT ->has_relation->{TABLE}.* AS related FROM {TABLE}:⟨{nid}⟩;")
        for row in (rows or []):
            for r in row.get("related", []):
                if r and r.get("node_id") not in seen:
                    seen.add(r["node_id"])
                    contexts.append({"label": r.get("label", ""), "content": r.get("content", "")})

    print(f"  コンテキストノード数: {len(contexts)}")
    return contexts


def main() -> None:
    """質問を受けてGraphRAGで回答する。"""
    if len(sys.argv) < 2:
        print("使い方: python src/query.py \"質問文\"", file=sys.stderr)
        sys.exit(1)
    question = sys.argv[1]
    print(f"=== SurrealDB Query ===\n質問: {question}\n")
    contexts = retrieve(question)
    context_text = "\n".join(f"- {c['label']}: {c['content']}" for c in contexts)
    print(f"\n=== 回答 ===\n{generate(context_text, question)}")


if __name__ == "__main__":
    main()

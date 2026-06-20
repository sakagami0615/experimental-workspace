"""グラフを検索して回答を生成する。

使い方:
    python src/query.py "質問文"
"""

import json
import sys

from common import embed, generate, surreal_query


def retrieve(query_vec: list[float], top_k: int = 3) -> list[dict]:
    """ベクトルKNN検索とグラフ展開で重複なしのコンテキストノードを返す。"""
    res = surreal_query(
        f"SELECT node_id, label, content FROM concept WHERE embedding <|{top_k},COSINE|> {json.dumps(query_vec)};")
    hits = res[0].get("result", []) if res else []
    print(f"  ベクトルヒット: {[h['label'] for h in hits]}")
    related: list[dict] = []
    for nid in [h["node_id"] for h in hits]:
        rows = surreal_query(f"SELECT ->has_relation->concept.* AS related FROM concept:{nid};")
        if rows:
            for row in rows[0].get("result", []):
                related.extend(r for r in row.get("related", []) if r)
    print(f"  グラフ展開: {[r.get('label', '?') for r in related]}")
    seen: set[str] = set()
    unique = []
    for n in hits + related:
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
    print(f"=== SurrealDB Query ===\n質問: {question}\n")
    nodes = retrieve(embed(question))
    context = "\n".join(f"- {n['label']}: {n['content']}" for n in nodes)
    print(f"\n=== 回答 ===\n{generate(context, question)}")


if __name__ == "__main__":
    main()

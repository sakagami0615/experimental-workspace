"""グラフを検索して回答を生成する。

使い方:
    python src/query.py "質問文"
"""

import sys

from neo4j import Driver

from common import embed, generate, get_driver


def retrieve(driver: Driver, query_vec: list[float], top_k: int = 3) -> list[dict]:
    """ベクトル検索とグラフ展開で重複なしのコンテキストノードを返す。"""
    with driver.session() as s:
        hits = [dict(r) for r in s.run(
            "CALL db.index.vector.queryNodes('concept_embedding', $k, $vec) YIELD node, score "
            "RETURN node.node_id AS node_id, node.label AS label, node.content AS content",
            k=top_k, vec=query_vec)]
        print(f"  ベクトルヒット: {[h['label'] for h in hits]}")
        related: list[dict] = []
        for h in hits:
            related += [dict(r) for r in s.run(
                "MATCH (n:Concept {node_id: $id})-[:HAS_RELATION]->(r:Concept) "
                "RETURN r.node_id AS node_id, r.label AS label, r.content AS content",
                id=h["node_id"])]
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
    print(f"=== Neo4j Query ===\n質問: {question}\n")
    driver = get_driver()
    try:
        nodes = retrieve(driver, embed(question))
        context = "\n".join(f"- {n['label']}: {n['content']}" for n in nodes)
        print(f"\n=== 回答 ===\n{generate(context, question)}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()

"""グラフを検索して回答を生成する（ベクトル検索とグラフ検索の並列実行）。

使い方:
    python src/query.py "質問文"
"""

import sys

from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_neo4j import Neo4jVector

from common import NEO4J_PASS, NEO4J_URI, NEO4J_USER, extract_entities, generate, get_embeddings, get_graph

INDEX_NAME = "concept_embedding"
NODE_LABEL = "Concept"


def vector_search(question: str, top_k: int = 3) -> list[dict]:
    """Neo4jVectorでベクトル類似検索する。"""
    store = Neo4jVector(
        embedding=get_embeddings(),
        url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASS,
        index_name=INDEX_NAME, node_label=NODE_LABEL,
        text_node_property="content", embedding_node_property="embedding",
    )
    hits = store.similarity_search(question, k=top_k)
    return [{"node_id": d.metadata.get("node_id", ""), "label": d.metadata.get("label", ""),
             "content": d.page_content} for d in hits]


def graph_search(question: str) -> list[dict]:
    """LLMエンティティ抽出 → エンティティごとに全文検索+グラフ探索を1クエリで実行（ベクトル検索と独立）。"""
    entities = extract_entities(question)
    graph = get_graph()
    seen: set[str] = set()
    results: list[dict] = []
    for entity in entities:
        rows = graph.query(
            "CALL db.index.fulltext.queryNodes('conceptFulltext', $entity) YIELD node "
            "WITH node LIMIT 3 "
            "OPTIONAL MATCH (node)-[:HAS_RELATION]->(r:Concept) "
            "WITH node, collect(r) AS neighbors "
            "RETURN node.node_id AS node_id, node.label AS label, node.content AS content, "
            "       [r IN neighbors | {node_id: r.node_id, label: r.label, content: r.content}] AS related",
            params={"entity": entity},
        )
        for row in rows:
            if row["node_id"] and row["node_id"] not in seen:
                seen.add(row["node_id"])
                results.append({"node_id": row["node_id"], "label": row["label"], "content": row["content"]})
            for r in row["related"]:
                if r.get("node_id") and r["node_id"] not in seen:
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
    print(f"=== Neo4j Hybrid RAG Query ===\n質問: {question}\n")
    nodes = retrieve(question)
    print(f"\n  コンテキストノード数: {len(nodes)}")
    context = "\n".join(f"- {n['label']}: {n['content']}" for n in nodes)
    print(f"\n=== 回答 ===\n{generate(context, question)}")


if __name__ == "__main__":
    main()

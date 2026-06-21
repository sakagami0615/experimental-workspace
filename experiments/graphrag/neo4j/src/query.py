"""グラフを検索して回答を生成する。

使い方:
    python src/query.py "質問文"
"""

import sys

from langchain_neo4j import Neo4jVector

from common import NEO4J_PASS, NEO4J_URI, NEO4J_USER, generate, get_embeddings, get_graph

INDEX_NAME = "concept_embedding"
NODE_LABEL = "Concept"


def retrieve(question: str, top_k: int = 3) -> list[dict]:
    """ベクトル検索とグラフ展開で重複なしのコンテキストノードを返す。"""
    store = Neo4jVector(
        embedding=get_embeddings(),
        url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASS,
        index_name=INDEX_NAME, node_label=NODE_LABEL,
        text_node_property="content", embedding_node_property="embedding",
    )
    hits = store.similarity_search(question, k=top_k)
    print(f"  ベクトルヒット: {[d.metadata.get('label') for d in hits]}")

    contexts = [{"label": d.metadata.get("label", ""), "content": d.page_content} for d in hits]
    seen = {d.metadata.get("node_id") for d in hits}

    graph = get_graph()
    for doc in hits:
        nid = doc.metadata.get("node_id")
        if not nid:
            continue
        related = graph.query(
            "MATCH (n:Concept {node_id: $id})-[:HAS_RELATION]->(r:Concept) "
            "RETURN r.node_id AS node_id, r.label AS label, r.content AS content",
            params={"id": nid},
        )
        for r in related:
            if r["node_id"] not in seen:
                seen.add(r["node_id"])
                contexts.append({"label": r["label"], "content": r["content"]})

    print(f"  コンテキストノード数: {len(contexts)}")
    return contexts


def main() -> None:
    """質問を受けてGraphRAGで回答する。"""
    if len(sys.argv) < 2:
        print("使い方: python src/query.py \"質問文\"", file=sys.stderr)
        sys.exit(1)
    question = sys.argv[1]
    print(f"=== Neo4j Query ===\n質問: {question}\n")
    contexts = retrieve(question)
    context_text = "\n".join(f"- {c['label']}: {c['content']}" for c in contexts)
    print(f"\n=== 回答 ===\n{generate(context_text, question)}")


if __name__ == "__main__":
    main()

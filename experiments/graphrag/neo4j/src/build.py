"""グラフを新規構築する（ベクトルインデックス作成 + データ投入）。"""

import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_neo4j import Neo4jVector

from common import NEO4J_PASS, NEO4J_URI, NEO4J_USER, extract_relations, get_embeddings, get_graph

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"
INDEX_NAME = "concept_embedding"
NODE_LABEL = "Concept"


def build_graph(data: dict) -> None:
    """ノードをベクトルストアに登録し、エッジをCypherで作成する。"""
    docs = [
        Document(page_content=node["content"], metadata={"node_id": node["id"], "label": node["label"]})
        for node in data["nodes"]
    ]
    Neo4jVector.from_documents(
        docs, get_embeddings(),
        url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASS,
        index_name=INDEX_NAME, node_label=NODE_LABEL,
        text_node_property="content", embedding_node_property="embedding",
    )
    print(f"  {len(docs)} ノードを登録しました。")

    print("  LLMでノード間の関係を抽出中...")
    edges = extract_relations(data["nodes"])
    graph = get_graph()
    for edge in edges:
        graph.query(
            "MATCH (a:Concept {node_id: $f}), (b:Concept {node_id: $t}) "
            "MERGE (a)-[:HAS_RELATION {relation: $r}]->(b)",
            params={"f": edge.source, "t": edge.target, "r": edge.relation},
        )
    print(f"  {len(edges)} エッジを作成しました。")

    graph.query(
        "CREATE FULLTEXT INDEX conceptFulltext IF NOT EXISTS "
        "FOR (n:Concept) ON EACH [n.label, n.content]"
    )
    print("  全文検索インデックスを作成しました。")


def main() -> None:
    """グラフを構築する。"""
    print("=== Neo4j Build ===\n")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    build_graph(data)
    print("\n完了。グラフを構築しました。")


if __name__ == "__main__":
    main()

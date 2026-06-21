"""既存グラフのデータを更新する（ノード・エッジのアップサート）。

使い方:
    python src/update.py [data/your_data.json]

引数省略時は data/sample.json を使用する。
"""

import json
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_neo4j import Neo4jVector

from common import NEO4J_PASS, NEO4J_URI, NEO4J_USER, get_embeddings, get_graph

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"
INDEX_NAME = "concept_embedding"
NODE_LABEL = "Concept"


def upsert_graph(data: dict) -> None:
    """ノードをベクトルストアにアップサートし、エッジを追加する。"""
    store = Neo4jVector(
        embedding=get_embeddings(),
        url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASS,
        index_name=INDEX_NAME, node_label=NODE_LABEL,
        text_node_property="content", embedding_node_property="embedding",
    )
    docs = [
        Document(page_content=node["content"], metadata={"node_id": node["id"], "label": node["label"]})
        for node in data["nodes"]
    ]
    store.add_documents(docs)
    print(f"  {len(docs)} ノードをアップサートしました。")

    graph = get_graph()
    for edge in data["edges"]:
        graph.query(
            "MATCH (a:Concept {node_id: $f}), (b:Concept {node_id: $t}) "
            "MERGE (a)-[:HAS_RELATION {relation: $r}]->(b)",
            params={"f": edge["from"], "t": edge["to"], "r": edge["relation"]},
        )
    print(f"  {len(data['edges'])} エッジを追加しました。")


def main() -> None:
    """グラフデータをアップサートする。JSONファイルパスを引数で指定できる。"""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_PATH
    print(f"=== Neo4j Update: {path.name} ===\n")
    data = json.loads(path.read_text(encoding="utf-8"))
    upsert_graph(data)
    print("\n完了。データを更新しました。")


if __name__ == "__main__":
    main()

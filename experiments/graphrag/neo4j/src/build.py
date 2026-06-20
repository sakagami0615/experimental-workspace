"""グラフを新規構築する（スキーマ作成 + データ投入）。"""

import json
from pathlib import Path

from neo4j import Driver

from common import embed, get_driver

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def setup_schema(driver: Driver, dims: int) -> None:
    """制約とベクトルインデックスを作成する。"""
    with driver.session() as s:
        s.run("CREATE CONSTRAINT concept_node_id IF NOT EXISTS FOR (n:Concept) REQUIRE n.node_id IS UNIQUE")
        s.run(f"CREATE VECTOR INDEX concept_embedding IF NOT EXISTS FOR (n:Concept) ON (n.embedding) "
              f"OPTIONS {{indexConfig: {{`vector.dimensions`: {dims}, `vector.similarity_function`: 'cosine'}}}}")


def load_data(driver: Driver, data: dict) -> None:
    """ノードとエッジを挿入し、ベクトルインデックスが利用可能になるまで待機する。"""
    with driver.session() as s:
        for node in data["nodes"]:
            s.run("MERGE (n:Concept {node_id: $id}) SET n.label=$label, n.content=$content, n.embedding=$emb",
                  id=node["id"], label=node["label"], content=node["content"], emb=embed(node["content"]))
            print(f"  node: {node['label']}")
        for edge in data["edges"]:
            s.run("MATCH (a:Concept {node_id: $f}), (b:Concept {node_id: $t}) "
                  "MERGE (a)-[:HAS_RELATION {relation: $r}]->(b)",
                  f=edge["from"], t=edge["to"], r=edge["relation"])
        s.run("CALL db.index.vector.awaitIndexOnline('concept_embedding', 300)")


def main() -> None:
    """グラフを構築する。"""
    print("=== Neo4j Build ===\n")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    dims = len(embed("test"))
    driver = get_driver()
    try:
        print(f"[1/2] スキーマ設定（次元: {dims}）...")
        setup_schema(driver, dims)
        print("[2/2] データ投入...")
        load_data(driver, data)
        print("\n完了。グラフを構築しました。")
    finally:
        driver.close()


if __name__ == "__main__":
    main()

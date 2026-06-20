"""既存グラフのデータを更新する（ノード・エッジのアップサート）。

使い方:
    python src/update.py [data/your_data.json]

引数省略時は data/sample.json を使用する。
"""

import json
import sys
from pathlib import Path

from neo4j import Driver

from common import embed, get_driver

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def upsert_data(driver: Driver, data: dict) -> None:
    """ノードをアップサートし、エッジを追加する。"""
    with driver.session() as s:
        for node in data["nodes"]:
            s.run("MERGE (n:Concept {node_id: $id}) SET n.label=$label, n.content=$content, n.embedding=$emb",
                  id=node["id"], label=node["label"], content=node["content"], emb=embed(node["content"]))
            print(f"  upsert: {node['label']}")
        for edge in data["edges"]:
            s.run("MATCH (a:Concept {node_id: $f}), (b:Concept {node_id: $t}) "
                  "MERGE (a)-[:HAS_RELATION {relation: $r}]->(b)",
                  f=edge["from"], t=edge["to"], r=edge["relation"])
            print(f"  edge: {edge['from']} -> {edge['to']}")


def main() -> None:
    """グラフデータをアップサートする。JSONファイルパスを引数で指定できる。"""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_PATH
    print(f"=== Neo4j Update: {path.name} ===\n")
    data = json.loads(path.read_text(encoding="utf-8"))
    driver = get_driver()
    try:
        upsert_data(driver, data)
        print("\n完了。データを更新しました。")
    finally:
        driver.close()


if __name__ == "__main__":
    main()

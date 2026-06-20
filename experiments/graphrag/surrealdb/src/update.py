"""既存グラフのデータを更新する（ノード・エッジのアップサート）。

使い方:
    python src/update.py [data/your_data.json]

引数省略時は data/sample.json を使用する。
"""

import json
import sys
from pathlib import Path

from common import embed, surreal_query

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def upsert_data(data: dict) -> None:
    """ノードをアップサートし、エッジを追加する。"""
    for node in data["nodes"]:
        nid, label, content = (v.replace("'", "\\'") for v in (node["id"], node["label"], node["content"]))
        surreal_query(f"UPSERT concept:{nid} SET node_id='{nid}', label='{label}', content='{content}', "
                      f"embedding={json.dumps(embed(node['content']))};")
        print(f"  upsert: {node['label']}")
    for edge in data["edges"]:
        fid, tid, rel = (v.replace("'", "\\'") for v in (edge["from"], edge["to"], edge["relation"]))
        surreal_query(f"RELATE concept:{fid}->has_relation->concept:{tid} SET relation='{rel}';")
        print(f"  edge: {edge['from']} -> {edge['to']}")


def main() -> None:
    """グラフデータをアップサートする。JSONファイルパスを引数で指定できる。"""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_PATH
    print(f"=== SurrealDB Update: {path.name} ===\n")
    data = json.loads(path.read_text(encoding="utf-8"))
    upsert_data(data)
    print("\n完了。データを更新しました。")


if __name__ == "__main__":
    main()

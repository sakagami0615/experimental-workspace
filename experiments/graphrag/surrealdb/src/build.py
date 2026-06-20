"""グラフを新規構築する（スキーマ作成 + データ投入）。"""

import json
from pathlib import Path

from common import embed, surreal_query

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def setup_schema(dims: int) -> None:
    """テーブル定義とHNSWベクトルインデックスを作成する。"""
    surreal_query(f"""
        DEFINE TABLE concept SCHEMALESS;
        DEFINE FIELD node_id ON concept TYPE string;
        DEFINE FIELD label ON concept TYPE string;
        DEFINE FIELD content ON concept TYPE string;
        DEFINE FIELD embedding ON concept TYPE array;
        DEFINE INDEX idx_embedding ON TABLE concept COLUMNS embedding HNSW DIMENSION {dims} DIST COSINE;
    """)


def load_data(data: dict) -> None:
    """ノードを埋め込みと共にアップサートし、エッジを作成する。"""
    for node in data["nodes"]:
        nid, label, content = (v.replace("'", "\\'") for v in (node["id"], node["label"], node["content"]))
        surreal_query(f"UPSERT concept:{nid} SET node_id='{nid}', label='{label}', content='{content}', "
                      f"embedding={json.dumps(embed(node['content']))};")
        print(f"  node: {node['label']}")
    for edge in data["edges"]:
        fid, tid, rel = (v.replace("'", "\\'") for v in (edge["from"], edge["to"], edge["relation"]))
        surreal_query(f"RELATE concept:{fid}->has_relation->concept:{tid} SET relation='{rel}';")


def main() -> None:
    """グラフを構築する。"""
    print("=== SurrealDB Build ===\n")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    dims = len(embed("test"))
    print(f"[1/2] スキーマ設定（次元: {dims}）...")
    setup_schema(dims)
    print("[2/2] データ投入...")
    load_data(data)
    print("\n完了。グラフを構築しました。")


if __name__ == "__main__":
    main()

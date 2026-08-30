"""既存グラフのデータを更新する（ノード・エッジのアップサート）。

使い方:
    python src/update.py [data/your_data.json]

引数省略時は data/sample.json を使用する。
"""

import json
import sys
from pathlib import Path

import edgedb

from common import extract_relations, get_client, get_embeddings

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def upsert_data(client: edgedb.Client, data: dict) -> None:
    """ノードをアップサートし、LLMで抽出した関係を追加する。"""
    embeddings = get_embeddings()
    for node in data["nodes"]:
        emb = embeddings.embed_query(node["content"])
        client.query(
            "INSERT default::Concept { node_id:=<str>$nid, label:=<str>$label, "
            "content:=<str>$content, embedding:=<array<float64>>$emb } "
            "UNLESS CONFLICT ON .node_id ELSE ("
            "  UPDATE default::Concept "
            "  SET { label:=<str>$label, content:=<str>$content, embedding:=<array<float64>>$emb }"
            ");",
            nid=node["id"], label=node["label"], content=node["content"], emb=emb)
        print(f"  upsert: {node['label']}")

    print("  LLMでノード間の関係を抽出中...")
    edges = extract_relations(data["nodes"])
    for edge in edges:
        client.query(
            "UPDATE default::Concept FILTER .node_id=<str>$fid "
            "SET { related_concepts += (SELECT default::Concept FILTER .node_id=<str>$tid) };",
            fid=edge.source,
            tid=edge.target,
        )
        print(f"  edge: {edge.source} -> {edge.target}")
    print(f"  {len(edges)} エッジを追加しました。")


def main() -> None:
    """グラフデータをアップサートする。JSONファイルパスを引数で指定できる。"""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_PATH
    print(f"=== EdgeDB Update: {path.name} ===\n")
    data = json.loads(path.read_text(encoding="utf-8"))
    client = get_client()
    try:
        upsert_data(client, data)
        print("\n完了。データを更新しました。")
    finally:
        client.close()


if __name__ == "__main__":
    main()

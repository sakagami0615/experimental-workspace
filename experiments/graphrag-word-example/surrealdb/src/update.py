"""既存グラフのデータを更新する（ノード・エッジのアップサート）。

使い方:
    python src/update.py [data/your_data.json]

引数省略時は data/sample.json を使用する。
"""

import json
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_surrealdb.vectorstores import SurrealDBVectorStore

from common import get_connection, get_embeddings

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"
TABLE = "concept"


def upsert_graph(data: dict) -> None:
    """ノードをベクトルストアにアップサートし、エッジを追加する。"""
    conn = get_connection()
    embeddings = get_embeddings()
    store = SurrealDBVectorStore(embedding=embeddings, connection=conn, table=TABLE)

    docs = [
        Document(page_content=node["content"], metadata={"node_id": node["id"], "label": node["label"]})
        for node in data["nodes"]
    ]
    store.add_documents(docs)
    print(f"  {len(docs)} ノードをアップサートしました。")

    for edge in data["edges"]:
        fid, tid, rel = edge["from"], edge["to"], edge["relation"]
        conn.query(f"RELATE {TABLE}:⟨{fid}⟩->has_relation->{TABLE}:⟨{tid}⟩ SET relation='{rel}';")
    print(f"  {len(data['edges'])} エッジを追加しました。")


def main() -> None:
    """グラフデータをアップサートする。JSONファイルパスを引数で指定できる。"""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_PATH
    print(f"=== SurrealDB Update: {path.name} ===\n")
    data = json.loads(path.read_text(encoding="utf-8"))
    upsert_graph(data)
    print("\n完了。データを更新しました。")


if __name__ == "__main__":
    main()

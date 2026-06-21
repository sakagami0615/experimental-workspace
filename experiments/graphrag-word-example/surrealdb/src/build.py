"""グラフを新規構築する（スキーマ作成 + データ投入）。"""

import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_surrealdb.vectorstores import SurrealDBVectorStore

from common import get_connection, get_embeddings, surreal_query

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"
TABLE = "concept"


def build_graph(data: dict) -> None:
    """ノードをベクトルストアに登録し、エッジをSurrealDBのRELATEで作成する。"""
    conn = get_connection()
    embeddings = get_embeddings()

    docs = [
        Document(page_content=node["content"], metadata={"node_id": node["id"], "label": node["label"]})
        for node in data["nodes"]
    ]
    store = SurrealDBVectorStore.from_documents(docs, embeddings, connection=conn, table=TABLE)
    print(f"  {len(docs)} ノードを登録しました。")

    for edge in data["edges"]:
        fid, tid, rel = edge["from"], edge["to"], edge["relation"]
        conn.query(f"RELATE {TABLE}:⟨{fid}⟩->has_relation->{TABLE}:⟨{tid}⟩ SET relation='{rel}';")
    print(f"  {len(data['edges'])} エッジを作成しました。")

    surreal_query("""
        DEFINE ANALYZER text_analyzer TOKENIZERS blank FILTERS lowercase, ascii;
        DEFINE INDEX idx_label_fts ON TABLE concept COLUMNS label SEARCH ANALYZER text_analyzer BM25;
        DEFINE INDEX idx_content_fts ON TABLE concept COLUMNS content SEARCH ANALYZER text_analyzer BM25;
    """)
    print("  全文検索インデックスを作成しました。")


def main() -> None:
    """グラフを構築する。"""
    print("=== SurrealDB Build ===\n")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    build_graph(data)
    print("\n完了。グラフを構築しました。")


if __name__ == "__main__":
    main()

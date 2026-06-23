"""グラフを新規構築する（スキーマ作成 + データ投入）。"""

import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_surrealdb.vectorstores import SurrealDBVectorStore

from common import extract_relations, get_connection, get_embeddings, surreal_query

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"
TABLE = "concept"


def build_graph(data: dict) -> None:
    """ノードをベクトルストアに登録し、LLMで抽出した関係をRELATEで作成する。"""
    conn = get_connection()
    embeddings = get_embeddings()

    docs = [
        Document(id=node["id"], page_content=node["content"], metadata={"node_id": node["id"], "label": node["label"]})
        for node in data["nodes"]
    ]
    store = SurrealDBVectorStore.from_documents(docs, embeddings, connection=conn, table=TABLE)
    for node in data["nodes"]:
        conn.query(
            f"UPDATE {TABLE}:⟨{node['id']}⟩ SET "
            f"node_id = {json.dumps(node['id'], ensure_ascii=False)}, "
            f"label = {json.dumps(node['label'], ensure_ascii=False)}, "
            f"content = {json.dumps(node['content'], ensure_ascii=False)};"
        )
    print(f"  {len(docs)} ノードを登録しました。")

    print("  LLMでノード間の関係を抽出中...")
    edges = extract_relations(data["nodes"])
    for edge in edges:
        conn.query(
            f"RELATE {TABLE}:⟨{edge.source}⟩->has_relation->{TABLE}:⟨{edge.target}⟩ "
            f"SET relation='{edge.relation}';"
        )
    print(f"  {len(edges)} エッジを作成しました。")

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

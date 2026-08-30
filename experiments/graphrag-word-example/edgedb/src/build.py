"""グラフを新規構築する（スキーマ作成 + データ投入）。"""

import json
from pathlib import Path

import edgedb

from common import extract_relations, get_client, get_embeddings

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def setup_schema(client: edgedb.Client) -> None:
    """EdgeDBにスキーマを作成する。"""
    try:
        client.execute("""
            CREATE TYPE default::Concept {
                CREATE REQUIRED PROPERTY node_id -> str { CREATE CONSTRAINT exclusive; };
                CREATE REQUIRED PROPERTY label -> str;
                CREATE REQUIRED PROPERTY content -> str;
                CREATE PROPERTY embedding -> array<float64>;
                CREATE MULTI LINK related_concepts -> default::Concept;
            };
        """)
    except edgedb.errors.SchemaDefinitionError:
        pass


def load_data(client: edgedb.Client, data: dict) -> None:
    """ノードを埋め込みと共に挿入し、LLMで抽出した関係をリンクとして設定する。"""
    embeddings = get_embeddings()
    for node in data["nodes"]:
        emb = embeddings.embed_query(node["content"])
        client.query(
            "INSERT default::Concept { node_id:=<str>$nid, label:=<str>$label, "
            "content:=<str>$content, embedding:=<array<float64>>$emb } UNLESS CONFLICT ON .node_id;",
            nid=node["id"], label=node["label"], content=node["content"], emb=emb)
        print(f"  node: {node['label']}")

    print("  LLMでノード間の関係を抽出中...")
    edges = extract_relations(data["nodes"])
    for edge in edges:
        client.query(
            "UPDATE default::Concept FILTER .node_id=<str>$fid "
            "SET { related_concepts += (SELECT default::Concept FILTER .node_id=<str>$tid) };",
            fid=edge.source,
            tid=edge.target,
        )
    print(f"  {len(edges)} エッジを作成しました。")


def main() -> None:
    """グラフを構築する。"""
    print("=== EdgeDB Build ===\n")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    client = get_client()
    try:
        print("[1/2] スキーマ設定...")
        setup_schema(client)
        print("[2/2] データ投入...")
        load_data(client, data)
        print("\n完了。グラフを構築しました。")
    finally:
        client.close()


if __name__ == "__main__":
    main()

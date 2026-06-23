# このファイルはスキーマの参考ドキュメントです。
# 実際のスキーマは run.py の setup_schema() で DDL として適用されます（EdgeDB devmode）。
# EdgeDB の通常のマイグレーションワークフローでは このファイルが使用されますが、
# このPoCでは devmode の DDL 直接実行を使用しています。

module default {
    type Concept {
        required node_id: str {
            constraint exclusive;
        };
        required label: str;
        required content: str;
        embedding: array<float64>;
        multi related_concepts: Concept;
    }
}

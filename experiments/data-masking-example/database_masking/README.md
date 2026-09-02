# データマスキングツール

顧客社内・閉域環境において、CSV/Excel/SQLiteの表形式データを外部分析基盤へ持ち出し可能な状態に
加工するためのローカル実行ツールです。設計の背景は
[docs/specs/design.md](docs/specs/design.md)
を参照してください。

## セットアップ

このディレクトリ（`database_masking/`）でビルドします。
DockerイメージはPython 3.14.7の公式通常版イメージを使用します。

```bash
docker compose build
```

以降のコマンドはコンテナ内で実行できます。

```bash
# サンプルデータ生成（初回のみ）
docker compose run --rm app python sample_data/generate_sample.py

# マスキング実行
docker compose run --rm app python -m database_masking mask \
  --input sample_data/customer_raw_sample.csv \
  --policy config/policy.example.yaml \
  --output output/masked.csv

# 検出漏れチェック
docker compose run --rm app python -m database_masking verify \
  --input output/masked.csv \
  --policy config/policy.example.yaml \
  --output output/verify_report.json
```

`docker-compose.yml` はこのプロジェクト単体用です。`output/` と `.secrets/` はホスト側の
`database_masking/` 配下に作成されます。

## サンプルデータについて

`sample_data/` と `output_example/` に含まれるデータは、動作確認用に
`sample_data/generate_sample.py` の固定リストとテンプレートから生成した架空の合成データです。
実在の個人情報・顧客情報は含まれていません。

本番でより高精度なNERが必要な場合は、`policy.yaml` の `spacy_model` を
`ja_core_news_lg` に変更し、Dockerfile内のモデルダウンロード対象も
`ja_core_news_lg` に変更して再ビルドしてください（モデルサイズが大きいため、事前に
ディスク容量とネットワーク環境を確認してください）。

## 使い方

```bash
# サンプルデータ生成（初回のみ）
docker compose run --rm app python sample_data/generate_sample.py

# マスキング実行
docker compose run --rm app python -m database_masking mask \
  --input sample_data/customer_raw_sample.csv \
  --policy config/policy.example.yaml \
  --output output/masked.csv

# 検出漏れチェック
docker compose run --rm app python -m database_masking verify \
  --input output/masked.csv \
  --policy config/policy.example.yaml \
  --output output/verify_report.json
```

`verify` は残存PII候補が1件でもあれば非ゼロの終了コードを返します。
レポート（`output/verify_report.json`）は人間がレビューし、問題がないことを確認してから
初めて外部分析基盤へのデータ持ち出しを承認してください。

### SQLiteデータベースから直接マスキングする

CSV/Excelの代わりに、SQLiteデータベースのテーブルを直接読み書きできます。

```bash
# サンプルデータ生成時にSQLite版（customer_raw_sample.db）も生成されます
docker compose run --rm app python sample_data/generate_sample.py

docker compose run --rm app python -m database_masking mask \
  --input sample_data/customer_raw_sample.db --input-table customers \
  --policy config/policy.example.yaml \
  --output output/masked.csv

docker compose run --rm app python -m database_masking verify \
  --input output/masked.csv \
  --policy config/policy.example.yaml \
  --output output/verify_report.json
```

`--input-table`（`mask`/`verify`共通）・`--output-table`（`mask`のみ。`verify`の出力は常に
CSV/JSONレポートのため`--output-table`は存在しません）は、対応する`--input`/`--output`の
拡張子が`.db`/`.sqlite`の場合にのみ必要です（CSV/Excelでは無視されます）。テーブル名は
英数字とアンダースコアのみ使用できます。

## policy.yaml の書き方

カラムごとに `drop`（削除）/ `pseudonymize`（値全体を仮名化）/ `keep`（維持）/
`freetext`（Regex・NERで検出しながら該当箇所のみ仮名化）を指定します。
入力データに存在するすべてのカラムを列挙してください。未定義のカラムがあると
`mask` はエラーで停止します（意図しないカラムの持ち出しを防ぐための安全策です）。

`config/policy.example.yaml` をサンプルとして参照してください。

### 設定項目一覧

`config/policy.example.yaml` は以下のような構成です。

```yaml
columns:
  customer_id: {action: pseudonymize, entity_type: CUSTOMER_ID}
  name: {action: pseudonymize, entity_type: PERSON}
  email: {action: drop}
  address: {action: pseudonymize, entity_type: ADDRESS}
  age: {action: keep}
  inquiry: {action: freetext}

custom_patterns:
  - entity_type: CUSTOMER_CODE
    regex: 'CUST-\d{6}'

spacy_model: ja_core_news_sm
```

#### `columns`（必須）

入力データの全カラムについて、`{action: ..., entity_type: ...}` の形式でポリシーを
1つずつ定義します。入力に存在するカラムが1つでも列挙から漏れていると、`mask` は
エラーで停止します（意図しないカラムの持ち出しを防ぐための安全策です）。

`action` に指定できる値は次の4種類です。

| action | 意味 |
| --- | --- |
| `drop` | カラムを削除する（例: `email: {action: drop}`） |
| `pseudonymize` | 値全体を仮名化トークンに置き換える（例: `name: {action: pseudonymize, entity_type: PERSON}`） |
| `keep` | 値をそのまま維持する（例: `age: {action: keep}`） |
| `freetext` | Regex・NERで検出しながら、該当箇所のみを仮名化する（例: `inquiry: {action: freetext}`） |

`entity_type` は `action: pseudonymize` の場合に必須です（未指定だとエラーになります）。
仮名化後のトークンに埋め込まれるラベル文字列で、命名規約は「先頭が大文字英字、以降は
大文字英字・数字・アンダースコアのみ」です（例: `PERSON`, `CUSTOMER_ID`）。この規約に
反する `entity_type`（小文字を含む、数字やアンダースコアで始まる等）を指定すると
エラーになります。

#### `custom_patterns`（任意）

顧客固有の正規表現による検出パターンのリストです。`freetext` カラムの自由記述テキスト
内で、ここに列挙した正規表現にマッチした箇所が、対応する `entity_type` として仮名化
されます。各要素には `entity_type`（`columns` と同じ命名規約）と `regex`（検出対象の
正規表現パターン）の両方が必須です。

```yaml
custom_patterns:
  - entity_type: CUSTOMER_CODE
    regex: 'CUST-\d{6}'
```

上記の例では、`inquiry` のような `freetext` カラムに `CUST-123456` のような文字列が
含まれていると、`CUSTOMER_CODE` として仮名化されます。

#### `spacy_model`（任意、デフォルト: `ja_core_news_sm`）

`freetext` カラムのNER（固有表現抽出）に使用するspaCy日本語モデル名です。省略した
場合は `ja_core_news_sm` が使われます。

- `ja_core_news_sm`: デフォルト。軽量・高速だが検出精度は限定的（開発・検証向け）。
- `ja_core_news_lg`: 高精度。ダウンロードサイズが大きいが、本番運用ではこちらを推奨します
  （Dockerfile内のモデルダウンロード対象を変更し、イメージを再ビルドしてください）。

## 重要な運用上の注意

- `.secrets/salt.key` は仮名化のハッシュに使うソルトです。**顧客環境の外に一切持ち出さないでください**。
  作成時に所有者のみ読み書き可能なパーミッション（`0600`）に制限されます。
- 仮名化は不可逆です。元の値と仮名の対応表は保存されません。同じsalt・同じ正規化入力であれば
  常に同じトークンになるため、データセット内での同一エンティティの一貫性は保たれます。
- `verify` のレポートには検出テキストの原文がそのまま含まれます。人間レビュー用のファイルであり、
  外部へは一切送信しないでください。
- **`verify` は `mask` と同一の検出器（同じspaCyモデル）を再適用するため、検出漏れの盲点も
  共有します。** 特に日本語人名（姓+名）が仮名化トークンに直接隣接する場合、名（下の名前）だけが
  検出されずプレーンテキストのまま残ることが確認されています
  （詳細は[docs/specs/design.md](docs/specs/design.md)の9.2節を参照）。
  **`verify` レポートが空であっても「PIIが完全に除去された」ことにはなりません。** マスキング済み
  ファイル自体を人間がサンプル抽出して目視確認してください。本番運用では `ja_core_news_lg` の
  利用を推奨します。
- SQLiteの`INTEGER`/`REAL`型カラムに`NULL`値が含まれる場合、pandasの型変換仕様により、当該カラム
  全体が浮動小数点数として読み込まれ、`30`のような整数値が`"30.0"`のような文字列に変換されて
  出力されることがあります（例: `age`カラムにNULL行が1件でもあると、他の行の`30`が`30.0`に
  なる）。本ツールは主にTEXT型カラム（顧客名・住所・自由記述等）のマスキングを想定しており、
  数値カラムをそのまま維持（`keep`）する用途では、SQLite側のカラムをTEXT型で定義することを
  推奨します。

## テスト

```bash
docker compose run --rm app pytest
```

## スコープ外

- PostgreSQL/MySQL等へのライブDB接続（`src/io/base.py` にインターフェースが
  定義されており、CSV/Excel/SQLite〔ファイルベース〕実装のみ存在）
- 外部分析基盤への投入
- 人間レビューUI（CSV/JSONレポートを目視確認する運用を想定）

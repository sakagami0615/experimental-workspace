# データマスキングツール 設計書

- 対象パッケージ: `database_masking`
- 対象ソースコード: このリポジトリの `src/`, `config/`, `sample_data/`, `tests/` 一式
- 本書は実装の現状（ソースコード）を正とし、それに合わせて記述する最終成果物としての設計書です。

## 1. 概要・背景

本ツールは、顧客の閉域環境にある実データ（CSV/Excel）を、外部分析基盤へ持ち出し可能な状態に加工するための、顧客環境内で
完結するローカル実行のデータ持ち出し前処理ツールです。

想定する運用プロセス全体は以下の通りです。

```
実データ → PoC対象データ抽出 → 不要項目削除 → ローカルでPII/機密情報検出
→ マスキング・仮名化 → 検出漏れチェック → 人によるレビュー → 持ち出し承認
===================================
外部分析基盤での検索・生成AI活用
```

このうち本ツールが担うのは「不要項目削除」から「検出漏れチェック」までであり、
「人によるレビュー」と「持ち出し承認」はツール外での人間の判断（レポートを見ての承認）です。
外部分析基盤への投入プロセス自体は本ツールのスコープ外です。

生データを外部分析基盤へ上げてからマスキングするのではなく、**顧客環境内でマスキング・仮名化・
検出漏れチェックまでを完結させ、人間のレビュー・承認を経てから外部分析基盤へ持ち出す**、という
運用を支えることが本ツールの目的です。外部API・外部通信には一切依存せず、すべての処理は
ローカルで完結します。

## 2. 全体アーキテクチャ

CLIは `mask` サブコマンドと `verify` サブコマンドに分離されています。両者は
`database_masking.detectors.analyzer.build_analyzer()` を通じて**同一の検出器**
（Regexレコグナイザ + Presidio NER）を同じ `policy.yaml` から組み立てて
使用するため、検出ロジックの不一致による見落としを防ぐ設計になっています。

```
[customer_raw.csv/xlsx]
      | mask
      v
+-------------------------------------------------+
| 1. policy.yaml のカラムポリシー適用               |
|    - drop         : カラムごと削除                |
|    - pseudonymize : セル値全体を仮名化トークンに置換|
|    - keep         : そのまま維持                  |
|    - freetext     : 検出器で該当箇所のみ仮名化      |
| 2. freetextカラムの検出（検出器はpolicy.yamlから構築）|
|    - Regexレコグナイザ（JP電話番号/郵便番号/カスタム）|
|    - Presidio NER（spaCy日本語モデル）              |
+-------------------------------------------------+
      v
[masked.csv/xlsx]
      | verify（mask と同じ policy.yaml から同じ検出器を再構築して適用）
      v
[verify_report.csv/json]
      → 人間がレポートとマスキング済みデータそのものをレビューし、持ち出し可否を判断
```

`mask` はマスキング済みデータを出力し、`verify` はそのデータに対してもう一度検出器を
適用して「検出できてしまうPIIらしき文字列が残っていないか」をレポートするという役割分担です。
`verify` はマスキングを行いません（読み取り専用のチェックです）。

## 3. ディレクトリ構成

実際に存在するファイル構成は以下の通りです。

```
database_masking/
├── src/
│   ├── __init__.py
│   ├── __main__.py                # CLIエントリ（mask / verify サブコマンド、argparse）
│   ├── config.py                  # policy.yaml のロード・バリデーション、entity_type命名規約の定義元
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── analyzer.py            # Presidio AnalyzerEngine組み立て（spaCy + Regex recognizer群）
│   │   └── regex_recognizers.py   # JP電話番号/郵便番号/custom_patterns用 PatternRecognizer
│   ├── io/
│   │   ├── __init__.py
│   │   ├── base.py                # DataSource/DataSink 抽象インターフェース（DB拡張点）
│   │   ├── readers.py             # CSV/Excel/SQLite読み込み実装（pandas）
│   │   └── writers.py             # CSV/Excel/SQLite書き込み実装（pandas）
│   ├── masking/
│   │   ├── __init__.py
│   │   ├── anonymizer.py          # カラムポリシー適用（drop/pseudonymize/keep/freetext）
│   │   ├── pipeline.py            # mask全体のオーケストレーション（run_mask）
│   │   └── pseudonymizer.py       # 決定的HMACベースの仮名化ロジック、salt管理
│   └── verify/
│       ├── __init__.py
│       ├── report.py              # レポート生成（CSV/JSON）
│       ├── runner.py              # verify全体のオーケストレーション（run_verify）
│       └── scanner.py             # マスク済みデータへの再検出、仮名化トークン自己検出フィルタ
├── config/
│   └── policy.example.yaml        # policy.yaml のサンプル
├── sample_data/
│   ├── __init__.py
│   ├── generate_sample.py         # ダミー顧客データ生成スクリプト
│   ├── customer_raw_sample.csv    # 生成済みサンプルデータ（CSV）
│   └── customer_raw_sample.db     # 生成済みサンプルデータ（SQLite、customersテーブル）
├── tests/
│   ├── test_analyzer.py
│   ├── test_anonymizer.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_docker_config.py
│   ├── test_e2e.py
│   ├── test_generate_sample.py
│   ├── test_io.py
│   ├── test_known_limitations.py
│   ├── test_pipeline.py
│   ├── test_pseudonymizer.py
│   ├── test_regex_recognizers.py
│   ├── test_smoke.py
│   ├── test_verify.py
│   └── test_verify_runner.py
├── docs/
│   └── specs/
│       ├── design.md              # 本書
│       ├── dsign.html             # 本書を視覚化したHTML
│       └── design-system/
│           ├── document.css
│           └── math-copy.js
├── output/
│   └── .gitkeep                   # 出力ディレクトリ保持用
├── .secrets/                      # .gitignore対象。salt.key を保存（実行時に自動生成）
├── Dockerfile
├── README.md
├── docker-compose.yml
└── pyproject.toml
```

`src/io/base.py` に `DataSource` / `DataSink` の抽象インターフェースが定義されており、
`readers.py` / `writers.py` はそれぞれCSV/Excel/SQLite（ファイルベース）向けの実装を持ちます。
一方、PostgreSQL/MySQL等への直接のライブDB接続（ネットワーク越しの接続）は実装されておらず、
今回のスコープ外です。

## 4. 技術スタック

`pyproject.toml` に基づく実際の依存関係です。

- 言語: Python 3.14以上（`requires-python = ">=3.14"`）
- PII/NER検出: Microsoft Presidio（`presidio-analyzer>=2.2`）
  - すべてローカル（顧客環境内）で実行し、外部APIへは一切データを送信しません。
  - なお `presidio-anonymizer>=2.2` も依存関係に含まれていますが、実際の置換処理
    （`src/masking/anonymizer.py`）は Presidio の `AnonymizerEngine` を使わず、
    検出結果のオフセットに基づく文字列置換を自前実装しています（詳細は6章・7章）。
- 日本語NER: spaCy（`spacy>=3.7`）。モデル名は `policy.yaml` の `spacy_model` で指定し、
  未指定時のデフォルトは `src/config.py` の `DEFAULT_SPACY_MODEL = "ja_core_news_sm"`
  です（軽量モデル。より高精度な `ja_core_news_lg` に変更可能。詳細は8章）。
- 構造化データ入出力: pandas（`pandas>=2.0`）。Excel入出力のため `openpyxl>=3.1` を使用。
  CSV/Excelに加えて、標準ライブラリ`sqlite3`経由でSQLiteデータベースのテーブルを直接
  読み書きできる（新規の外部依存追加なし）。
- 設定ファイル: PyYAML（`PyYAML>=6.0`）
- CLI: 標準ライブラリ `argparse`（追加依存なし）
- テスト: pytest（`pytest>=8.0`、`dev` extra）

## 5. policy.yaml のポリシースキーマ

`src/config.py` の `load_policy()` がロード・バリデーションを行います。

カラムごとに `action` を指定します（`VALID_ACTIONS = {"drop", "pseudonymize", "keep", "freetext"}`）。

| action | 意味 |
|---|---|
| `drop` | カラムごと削除する（データ最小化） |
| `pseudonymize` | セル値全体を仮名化トークンに置換する。`entity_type` の指定が必須 |
| `keep` | そのまま維持する |
| `freetext` | Regex/NERの検出器でカラム内テキストをスキャンし、該当箇所のみ仮名化トークンに置換する |

```yaml
columns:
  customer_id: {action: pseudonymize, entity_type: CUSTOMER_ID}
  name:        {action: pseudonymize, entity_type: PERSON}
  email:       {action: drop}
  phone:       {action: drop}
  address:     {action: pseudonymize, entity_type: ADDRESS}
  age:         {action: keep}
  product:     {action: keep}
  category:    {action: keep}
  inquiry:     {action: freetext}
  purchase_date: {action: keep}

custom_patterns:                 # 顧客固有の正規表現（社員コード・案件番号等）
  - entity_type: CUSTOMER_CODE
    regex: 'CUST-\d{6}'

spacy_model: ja_core_news_sm      # 省略時のデフォルトも ja_core_news_sm
```

バリデーション規則（`load_policy` 内で実施）:

- `columns` セクションが存在しない場合はエラー。
- 各カラムに `action` が必須。`VALID_ACTIONS` にない値はエラー。
- `action: pseudonymize` の場合は `entity_type` が必須。
- `entity_type` を指定する場合は命名規約（8章参照）に従う必要がある。
- `custom_patterns` の各要素は `entity_type` と `regex` が必須。`regex` は `re.compile` で
  コンパイル可能である必要がある。

さらに `src/masking/pipeline.py` の `validate_columns_covered()` により、
入力データに存在するが `policy.yaml` に定義されていないカラムがあると `mask` はエラーで
停止します（`ColumnCoverageError`）。未定義カラムをうっかりそのまま持ち出さないための
安全策です。この検証はデータ読み込み直後、検出器の構築より前に行われます。

## 6. 検出レイヤー

`freetext` カラムには基本としてRegexとNERの2種類の検出を重ねて適用します。すべて
`src/detectors/analyzer.py` の `build_analyzer()` が1つの Presidio
`AnalyzerEngine` に統合します。

1. **Regexレコグナイザ**（`src/detectors/regex_recognizers.py`）
   - 日本の電話番号（`0\d{1,4}-\d{1,4}-\d{3,4}`、entity_type=`PHONE_NUMBER`）を検出する
     独自の `PatternRecognizer`。
   - 日本の郵便番号（`\d{3}-\d{4}`、entity_type=`JP_POSTAL_CODE`）を検出する独自の
     `PatternRecognizer`。電話番号と桁数が重なるケースがありますが、検出漏れを避ける
     多層防御の観点から意図的に許容しています。
   - `policy.yaml` の `custom_patterns` から動的に生成される `PatternRecognizer`
     （顧客固有の社員コード・案件番号などに対応）。
2. **Presidio NER**（`src/detectors/analyzer.py`）
   - `NlpEngineProvider` 経由でspaCy日本語モデルをロードし、`PERSON` / `LOCATION` /
     `ORGANIZATION` / `DATE_TIME` 等のエンティティを検出します。
   - `RecognizerRegistry.load_predefined_recognizers()` によりPresidio組み込みの
     言語非依存レコグナイザ（メールアドレス等）もあわせてロードされます。
`mask` の `freetext` 処理（`src/masking/anonymizer.py`）では、これら複数レイヤーの
検出結果が同じ文字範囲を重複検出しうるため、スコア降順（同点ならスパン長の降順）で貪欲に
非重複な検出結果を選び、末尾側から順に文字列を置換していきます（先頭側から置換すると
後続のオフセットがずれるため）。

## 7. 仮名化アルゴリズム（可逆性なし・一貫性あり）

`src/masking/pseudonymizer.py` に実装されています。

```python
def pseudonymize(value: str, entity_type: str, salt: bytes) -> str:
    normalized = normalize(value)  # unicodedata.normalize("NFKC", value).strip()
    digest = hmac.new(salt, normalized.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{entity_type}_{digest[:8]}"
```

- `normalize()` はUnicode正規化（NFKC、全角半角統一など）と前後空白除去のみを行います。
- `salt` は `mask` 初回実行時に `.secrets/salt.key`（デフォルトパス。CLIの `--salt-file` で
  変更可能）へ `secrets.token_bytes(32)` でランダム生成・保存されます
  （**顧客環境外へは一切持ち出しません**。詳細は9章）。
- **元の値と仮名の対応表は一切保存しません**（不可逆）。ハッシュのソルトのみが保存対象です。
- 同一 salt・同一正規化入力であれば常に同一トークンになるため、「同一人物・同一組織は
  同一トークン」というデータセット内の一貫性（例: `PERSON_a3f9c2e1` が複数行で同じ
  トークンとして現れる）が保たれます。
- カラム単位仮名化（`pseudonymize` アクション）と自由記述内の検出（`freetext` アクション）は
  `src/masking/anonymizer.py` の `apply_column_policy()` から同じ `pseudonymize()`
  関数を共有して呼び出されるため、同一エンティティであればカラムをまたいで同じトークンに
  なります。
- 実際の置換処理は Presidio の `AnonymizerEngine`／カスタム `Operator` は使わず、上記の
  `pseudonymize()` 関数とオフセットベースの文字列置換を `apply_column_policy()` /
  `_mask_freetext()` 内で直接組み合わせて実装しています。

## 8. entity_type 命名規約

`src/config.py` に以下が定義されています。

```python
ENTITY_TYPE_NAME_FRAGMENT = r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*"
ENTITY_TYPE_NAME_PATTERN = re.compile(rf"^{ENTITY_TYPE_NAME_FRAGMENT}$")
```

`policy.yaml` の `columns[].entity_type` / `custom_patterns[].entity_type` は、この正規表現（先頭大文字、大文字英数字とアンダースコアのみ、
例: `CUSTOMER_ID`, `EMPLOYEE_NAME`）に従う必要があり、`load_policy()` でバリデーションされます。
違反すると `PolicyError` が送出されます。

この制約が必要な理由は、`verify` 側の仮名化トークン自己検出フィルタ（下記9章）にあります。
`src/verify/scanner.py` は次のパターンで「これは `mask` 自身が生成した仮名化
トークンである」ことを構文的に判定します。

```python
# database_masking.config.ENTITY_TYPE_NAME_FRAGMENT を単一の情報源として共有し、
# トークン全体（entity_type + "_" + 8桁16進数）にマッチする形に組み立てる
PSEUDONYM_TOKEN_PATTERN = re.compile(rf"{ENTITY_TYPE_NAME_FRAGMENT}_[0-9a-f]{{8}}")
```

`entity_type` が任意の文字列を許容してしまうと、この構文的な自己検出判定が成立しなくなる
ため、命名規約として制限しています（`ENTITY_TYPE_NAME_FRAGMENT` を `config.py` 側の
単一情報源とし、`scanner.py` はそれを import して組み立てることで、規約がズレないように
しています）。

なお、Presidio組み込みのレコグナイザ（`PERSON`, `DATE_TIME`, `ORGANIZATION` 等）が生成する
`entity_type` は `policy.yaml` 経由のバリデーション対象外であり、これらが
命名規約に準拠しているかどうかはPresidioライブラリ自体の命名規則に依存します（本ツールが
確認している組み込み `entity_type` 名はいずれも規約に準拠しています）。

## 9. verify（検出漏れチェック）の仕組みと限界

`src/verify/runner.py` の `run_verify()` が、`mask` の出力ファイルに対して
同一の検出器群（`build_analyzer(config)`、Regex + NER）を再構築・再適用し、
残存PII候補をレポートとして出力します。

```csv
row_index,column,entity_type,detected_text,score
128,inquiry,PERSON,"田中様",0.85
```

- レポートは顧客環境内に留めるものであり、外部へは渡しません。人間レビュー用に検出テキストの
  原文をそのまま含みます。
- レポートに1件でも候補があれば `run_verify()` は `1` を返し、`main()` はそれをそのまま
  プロセスの終了コードとして返します（`0` = 候補なし、`1` = 候補あり）。CI等での自動
  チェックにも使える設計です。

### 9.1 仮名化トークンの自己検出フィルタ

`mask` → `verify` を実行すると、`verify` が `mask` 自身の生成した仮名化トークン
（例: `CUSTOMER_ID_03df7aa8`）をspaCyが `"CUSTOMER"` 等の部分文字列として誤検出し、
大量の偽陽性を報告する問題があります。これに対処するため、`src/verify/scanner.py`
の `scan_dataframe()` は、検出結果のスパンが `PSEUDONYM_TOKEN_PATTERN`（8章参照）に
マッチする範囲と重なる場合、その検出結果を候補から除外します。

### 9.2 既知の制限（`ja_core_news_sm` の検出漏れ）

デフォルトのspaCyモデル `ja_core_news_sm` を用いた場合、複数トークンからなる日本語人名
（姓+名）のうち、仮名化トークンに直接隣接する「名」（下の名前）部分が `PERSON` として
認識されず、平文のまま残存するケースが確認されています。

実例: サンプルデータの「高橋健一」という人名について、姓「高橋」は `PERSON` として
正しく仮名化されますが、名「健一」がタグ付けされず、`PERSON_xxxxxxxx健一様が…` のように
平文の一部が残ります。この既知の制限は `tests/test_known_limitations.py` に
`xfail(strict=True)` の回帰テストとして記録されています。将来モデル変更や検出器の
改善によりこの問題が解消された場合、当該テストは意図せず成功（XPASS）してテストスイート
全体を失敗させるため、修正の見落としを防止できます。

さらに重要なのは、`verify` は `mask` と**同一の検出器**（同じspaCyモデルを含む）を
再適用する設計（2章参照）であるため、**この種の検出漏れは `verify` のレポートにも
現れない**という点です。すなわち **`verify` レポートが空であることは、「PIIが完全に
除去されたことの保証」にはなりません。**

これは、1章で述べた「人によるレビュー」工程が本質的に必要である理由そのものであり、
`verify` はあくまで人間レビューを補助するチェックであって、レビューの代替ではありません。

本番運用にあたっては、以下の2点を運用要件として推奨します。

1. `policy.yaml` の `spacy_model` を `ja_core_news_lg` に変更し、`ja_core_news_sm` より
   高精度なNERモデルを利用すること。モデル追加はDockerfileに組み込み、イメージを再ビルドする。
2. `verify` レポートの確認に加えて、マスキング済みデータそのものを人間がサンプル抽出し、
   目視でスポットチェックを行うこと。

### 9.3 既知の制限（SQLiteのINTEGER/REAL型NULL値）

なお、SQLite経由でマスキングする場合、`INTEGER`/`REAL`型カラムに`NULL`値が含まれると、
pandasの型変換仕様により当該カラム全体が浮動小数点数化され、整数値が`"30.0"`のような
文字列になることがある（`SqliteDataSource`はTEXT型カラムでの利用を主眼に設計されている）。

## 10. CLI

```bash
# マスキング実行
python -m database_masking mask \
  --input sample_data/customer_raw_sample.csv \
  --policy config/policy.example.yaml \
  --output output/masked.csv \
  --salt-file .secrets/salt.key      # 省略可（デフォルトも同じパス）

# 検出漏れチェック
python -m database_masking verify \
  --input output/masked.csv \
  --policy config/policy.example.yaml \
  --output output/verify_report.csv     # 拡張子 .csv / .json に対応

# SQLiteを入力とする場合の例（--input-table が必須）
python -m database_masking mask \
  --input sample_data/customer_raw_sample.db --input-table customers \
  --policy config/policy.example.yaml \
  --output output/masked.csv
```

`mask` の必須引数: `--input`, `--policy`, `--output`（`--salt-file` は任意、デフォルト
`.secrets/salt.key`）。`verify` の必須引数: `--input`, `--policy`, `--output`。
サブコマンド未指定・不正な場合は `argparse` がエラーを出して終了します。

`mask` は `--input-table`/`--output-table`（任意、デフォルト `None`）を受け付けます。`verify`
は入力のみを扱うため `--input-table`（任意、デフォルト `None`）のみを受け付け、
`--output-table`は存在しません（`verify`の出力は常にCSV/JSONレポートであり、データシンクへの
書き込みを行わないため）。`--input`の拡張子が`.db`/`.sqlite`の場合は`--input-table`が、
（`mask`の場合）`--output`の拡張子が`.db`/`.sqlite`の場合は`--output-table`が必須になります
（`build_data_source()` / `build_data_sink()` が未指定を検知して `ValueError` を送出します）。
CSV/Excelの場合はこれらのオプションは無視されます。テーブル名は
`src/io/readers.py` の `TABLE_NAME_PATTERN`（`^[A-Za-z_][A-Za-z0-9_]*$`）により、
英数字とアンダースコアのみ（先頭は英字またはアンダースコア）に制限されます。

## 11. セキュリティ・運用上の注意

- `.secrets/salt.key` は仮名化のハッシュに使うソルトです。**顧客環境の外に一切持ち出しては
  いけません。** 初回 `mask` 実行時に自動生成され、作成時に所有者のみ読み書き可能な
  パーミッション（`0600`）に制限されます（`load_or_create_salt()`）。`.secrets/` は
  `.gitignore` 対象です。
- 仮名化は不可逆です。元の値と仮名の対応表は保存されません。同じsalt・同じ正規化入力で
  あれば常に同じトークンになるため、データセット内での同一エンティティの一貫性は保たれます
  （7章）。
- `verify` のレポート（CSV/JSON）には検出テキストの原文がそのまま含まれます。人間レビュー用の
  ファイルであり、外部へは一切送信しないでください。
- `verify` は `mask` と同一の検出器（同じspaCyモデルを含む）を再適用するため、検出漏れの
  盲点も共有します（9章）。`verify` レポートが空であっても「PIIが完全に除去された」ことには
  なりません。本番運用では `ja_core_news_lg` の利用と、マスキング済みデータの人手による
  サンプルチェックを推奨します。
- `policy.yaml` に定義されていないカラムが入力データにあると `mask` はエラーで停止します
  （5章）。意図しないカラムの持ち出しを防ぐための安全策であり、無効化する手段は
  実装されていません。

## 12. テスト方針

`tests/` 配下に以下のテストファイルが存在します（`pytest`、`pyproject.toml` の
`[tool.pytest.ini_options]` で `testpaths = ["tests"]` を指定）。

| ファイル | 主な検証内容 |
|---|---|
| `test_smoke.py` | パッケージがimport可能であることの疎通確認 |
| `test_config.py` | `load_policy()` のバリデーション（正常系・未対応設定・action不正・entity_type不正・命名規約違反・custom_patterns不正など） |
| `test_io.py` | CSV/Excel/SQLiteの読み書き往復、未対応拡張子の拒否、出力ディレクトリの自動作成、SQLiteのテーブル名バリデーション・NULL値の空文字変換 |
| `test_regex_recognizers.py` | JP電話番号・郵便番号・custom_patterns の検出精度 |
| `test_analyzer.py` | `AnalyzerEngine` 組み立て、人名検出、custom_pattern検出、空文字列の扱い |
| `test_pseudonymizer.py` | 仮名化の決定性・非決定性（異なる入力/salt）、出力フォーマット、全角半角正規化、元の値が出力に含まれないこと（非可逆性）、salt生成・永続化・パーミッション |
| `test_anonymizer.py` | drop/pseudonymize/keep/freetextの各アクションの適用、空値・NaN値の扱い、freetext検出でのオフセット破壊がないこと |
| `test_pipeline.py` | `run_mask()` のエンドツーエンド動作、未定義カラムによるエラー |
| `test_verify.py` | 残存PII検出、クリーンなテキストで候補が出ないこと、空値スキップ、仮名化トークン自己検出フィルタの有効性、フィルタが隣接する本物の漏えいまで隠さないこと、レポート出力（CSV/JSON）、未対応拡張子の拒否 |
| `test_verify_runner.py` | `run_verify()` の終了コード（候補あり/なし） |
| `test_cli.py` | `mask`→`verify` のCLI一気通貫実行、サブコマンド未指定時のエラー |
| `test_e2e.py` | サンプルデータ生成から `mask`→`verify` までの一気通貫シナリオ |
| `test_generate_sample.py` | `sample_data/generate_sample.py` が生成する行の妥当性（カラム構成、customer_idの一意性、氏名/電話番号の参照） |
| `test_known_limitations.py` | `ja_core_news_sm` の既知の検出漏れを `xfail(strict=True)` として回帰記録（9.2章） |

## 13. スコープ外

- PostgreSQL/MySQL等へのライブDB接続（`src/io/base.py` に `DataSource` /
  `DataSink` の抽象インターフェースが定義されており、CSV/Excel/SQLite（ファイルベース）
  実装のみが存在する）
- 外部分析基盤への投入部分
- 人間レビューUI（CSV/JSONレポートおよびマスキング済みデータそのものを人間が目視確認する
  運用を想定。承認ワークフロー自体は対象外）

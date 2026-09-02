# ドキュメントマスキングツール 設計書

- 対象パッケージ: `document_masking`
- 対象ソースコード: このリポジトリの `document_masking/` 一式
  （`src/`, `sample_data/`, `tests/`）
- 本書は実装の現状（ソースコード）を正とし、それに合わせて記述する最終成果物としての設計書です。
- 本書は `document_masking/` 単体で完結しており、他ツール（`database_masking/`）のドキュメントを
  参照しなくても読める内容になっています。

## 1. 概要・背景

本ツールは、顧客の閉域環境にある自由記述のテキストファイル（問い合わせメモ・議事録などの
`.txt`/`.md`ファイル）から、氏名・電話番号などのPIIらしき情報をローカルで検出・仮名化する
ためのツールです。データ持ち出し前の前処理として、顧客環境内で完結する形で実行します。

本リポジトリには、表形式データ（CSV/Excel/SQLite）をカラム単位のポリシー（`policy.yaml`）で
処理する `database_masking/` というツールも存在しますが、`document_masking` はそれとは
独立した別ツールです。分離している理由は、扱うデータの構造そのものが本質的に異なるためです。

- `database_masking` の入力はカラムを持つ表形式データであり、「このカラムは氏名だから
  仮名化する／このカラムは電話番号だから削除する」といったカラム単位の判断（ポリシー）が
  意味を持ちます。
- 一方、問い合わせメモや議事録のような自由記述の文書には「カラム」という概念自体が
  存在しません。氏名や電話番号がテキストのどこに何個現れるかは文書ごとにまちまちであり、
  あらかじめカラムを指定してポリシーを適用するという設計が成立しません。

そのため `document_masking` では、`policy.yaml` のようなカラム単位の設定ファイルを持たず、
**ファイル全体を1つのテキストとして読み込み、Regex・NERの検出器を文書全体に一様に適用する**
というシンプルな設計を採っています。外部API・外部通信には一切依存せず、すべての処理はローカルで
完結します。

## 2. 全体アーキテクチャ

CLIは `mask` サブコマンドと `verify` サブコマンドに分離されています。両者は
`document_masking.detectors.analyzer.build_analyzer()` を通じて**同一の検出器**
（Regexレコグナイザ + Presidio NER）を同じ引数（`spacy_model`）から組み立てて使用するため、検出ロジックの不一致による見落としを
防ぐ設計になっています。

```
[inquiry.txt / meeting_notes.md]
      | mask
      v
+-------------------------------------------------+
| 1. ファイル全体をテキストとして読み込み             |
| 2. 検出器を文書全体に一様に適用                     |
|    - Regexレコグナイザ（JP電話番号/郵便番号/カスタム）|
|    - Presidio NER（spaCy日本語モデル）              |
| 3. 検出結果の重複解消（スコア降順の貪欲選択）         |
| 4. 末尾側から仮名化トークンへ置換                    |
+-------------------------------------------------+
      v
[masked.txt / masked.md]
      | verify（mask と同じ検出器を再構築して適用）
      v
[verify_report.csv/json]
      → 人間がレポートとマスキング済みファイルそのものをレビューし、持ち出し可否を判断
```

`mask` はマスキング済みファイルを出力し、`verify` はそのファイルに対してもう一度検出器を
適用して「検出できてしまうPIIらしき文字列が残っていないか」をレポートするという役割分担
です。`verify` はマスキングを行いません（読み取り専用のチェックです）。カラム単位の
ポリシーがないぶん、`database_masking` よりも単純な一直線のパイプラインになっています。

## 3. ディレクトリ構成

実際に存在するファイル構成は以下の通りです。

```
document_masking/
├── src/
│   ├── __init__.py
│   ├── __main__.py                # CLIエントリ（mask / verify サブコマンド、argparse）
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── analyzer.py            # Presidio AnalyzerEngine組み立て（spaCy + Regex recognizer群）
│   │   └── regex_recognizers.py   # JP電話番号/郵便番号/CustomPattern用 PatternRecognizer
│   ├── masking/
│   │   ├── __init__.py
│   │   ├── masker.py              # ファイル全体の検出→重複解消→置換のオーケストレーション
│   │   └── pseudonymizer.py       # 決定的HMACベースの仮名化ロジック、salt管理
│   └── verify/
│       ├── __init__.py
│       ├── report.py              # レポート生成（CSV/JSON）
│       └── scanner.py             # マスク済みテキストへの再検出、仮名化トークン自己検出フィルタ
├── sample_data/
│   ├── __init__.py
│   ├── generate_sample.py         # ダミー問い合わせメモ・議事録の生成スクリプト
│   ├── sample_inquiry.txt         # 生成済みサンプルデータ（.txt）
│   └── sample_meeting_notes.md    # 生成済みサンプルデータ（.md）
├── tests/
│   ├── test_analyzer.py
│   ├── test_cli.py
│   ├── test_docker_config.py
│   ├── test_e2e.py
│   ├── test_generate_sample.py
│   ├── test_masker.py
│   ├── test_pseudonymizer.py
│   ├── test_regex_recognizers.py
│   ├── test_smoke.py
│   └── test_verify.py
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

`database_masking` に存在する `config.py`（policy.yamlのロード）・`io/`（CSV/Excel/SQLite
入出力）に相当するモジュールは `document_masking` には存在しません。入出力は
`masking/masker.py` の `mask_file()` が標準ライブラリの `Path.read_text()`/`write_text()`
（UTF-8固定）で直接行っており、専用の入出力抽象化レイヤーを設けるほどの複雑さがないため
です。

## 4. 技術スタック

`pyproject.toml` に基づく実際の依存関係です。

- 言語: Python 3.14以上（`requires-python = ">=3.14"`）
- PII/NER検出: Microsoft Presidio（`presidio-analyzer>=2.2`）
  - すべてローカル（顧客環境内）で実行し、外部APIへは一切データを送信しません。
  - `database_masking` とは異なり `presidio-anonymizer` には依存していません。置換処理は
    Presidioの `AnonymizerEngine` を使わず、検出結果のオフセットに基づく文字列置換を
    自前実装しています（詳細は6章・7章）。
- 日本語NER: spaCy（`spacy>=3.7`）。モデル名はCLIの `--spacy-model` で指定し、デフォルトは
  `ja_core_news_sm`（軽量モデル。より高精度な `ja_core_news_lg` に変更可能。詳細は9章）。
- 構造化データ入出力ライブラリ（pandas / openpyxl）・設定ファイル読み込み（PyYAML）には
  依存していません。入力はテキストファイル（.txt/.md）そのものであり、`Path.read_text()`
  で読み込むだけで足りるためです。
- CLI: 標準ライブラリ `argparse`（追加依存なし）
- テスト: pytest（`pytest>=8.0`、`dev` extra）

## 5. 検出レイヤー

文書全体に2種類の検出を重ねて適用します。すべて `src/detectors/analyzer.py`
の `build_analyzer()` が1つの Presidio `AnalyzerEngine` に統合します。`database_masking`
とは異なり、`freetext`/`pseudonymize`等のカラム単位のアクション分岐は存在せず、検出は
常にファイル全体に一様に適用されます。

1. **Regexレコグナイザ**（`src/detectors/regex_recognizers.py`）
   - 日本の電話番号（`0\d{1,4}-\d{1,4}-\d{3,4}`、entity_type=`PHONE_NUMBER`）を検出する
     独自の `PatternRecognizer`。
   - 日本の郵便番号（`\d{3}-\d{4}`、entity_type=`JP_POSTAL_CODE`）を検出する独自の
     `PatternRecognizer`。電話番号と桁数が重なるケースがありますが、検出漏れを避ける
     多層防御の観点から意図的に許容しています。
   - `build_analyzer()` の `custom_patterns` 引数（`CustomPattern`のリスト）から動的に
     生成される `PatternRecognizer`（顧客固有の社員コード・案件番号などに対応）。
2. **Presidio NER**（`src/detectors/analyzer.py`）
   - `NlpEngineProvider` 経由でspaCy日本語モデルをロードし、`PERSON` / `LOCATION` /
     `ORGANIZATION` / `DATE_TIME` 等のエンティティを検出します。
   - `RecognizerRegistry.load_predefined_recognizers()` によりPresidio組み込みの
     言語非依存レコグナイザ（メールアドレス等）もあわせてロードされます。

`src/masking/masker.py` の `_select_non_overlapping()` では、これら複数
レイヤーの検出結果が同じ文字範囲を重複検出しうるため、スコア降順（同点ならスパン長の
降順）で貪欲に非重複な検出結果を選び、末尾側から順に文字列を置換していきます（先頭側から
置換すると後続のオフセットがずれるため）。

## 6. 仮名化アルゴリズム（可逆性なし・一貫性あり）

`src/masking/pseudonymizer.py` に実装されています。`database_masking`の
同名モジュールと同じHMAC-SHA256ベースの決定的な仮名化アルゴリズムですが、共有ライブラリ
としては切り出されておらず、`document_masking`側に独立して複製実装されています
（理由は12章参照）。

```python
def pseudonymize(value: str, entity_type: str, salt: bytes) -> str:
    normalized = normalize(value)  # unicodedata.normalize("NFKC", value).strip()
    digest = hmac.new(salt, normalized.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{entity_type}_{digest[:8]}"
```

- `normalize()` はUnicode正規化（NFKC、全角半角統一など）と前後空白除去のみを行います。
- `salt` は `mask` 初回実行時に `.secrets/salt.key`（デフォルトパス。CLIの `--salt-file` で
  変更可能）へ `secrets.token_bytes(32)` でランダム生成・保存されます（作成時にパーミッション
  `0600`に制限）。**顧客環境外へは一切持ち出しません**（詳細は10章）。
- **元の値と仮名の対応表は一切保存しません**（不可逆）。ハッシュのソルトのみが保存対象です。
- 同一 salt・同一正規化入力であれば常に同一トークンになるため、「同一人物・同一組織は
  同一トークン」という文書内の一貫性（例: `PERSON_a3f9c2e1` が同じ文書内の複数箇所で
  同じトークンとして現れる）が保たれます。
- 実際の置換処理は Presidio の `AnonymizerEngine`／カスタム `Operator` は使わず、上記の
  `pseudonymize()` 関数とオフセットベースの文字列置換を `masker.py` の `mask_text()` 内で
  直接組み合わせて実装しています。

## 7. entity_type 命名規約と仮名化トークンの自己検出フィルタ

仮名化トークンは `{entity_type}_{8桁16進数}`（例: `PERSON_a3f9c2e1`）という形式で
生成されます。`verify` を `mask` の出力に対して実行すると、`mask` 自身が生成した
仮名化トークンをspaCyが `"PERSON"` 等の部分文字列として誤検出し、大量の偽陽性を
報告してしまう問題があります。これを防ぐため、`src/verify/scanner.py`
は次のパターンで「これは `mask` 自身が生成した仮名化トークンである」ことを構文的に
判定し、検出結果のスパンがこのパターンに重なる場合は候補から除外します。

```python
# scanner.py: 仮名化トークンの自己検出フィルタ
PSEUDONYM_TOKEN_PATTERN = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_[0-9a-f]{8}")
```

このパターンが機能するためには、`pseudonymize()` が生成する `entity_type` 部分が
「先頭大文字、大文字英数字とアンダースコアのみ」という命名規約に従っている必要が
あります。`document_masking` ではカラムポリシーを持たないため、命名規約は
仮名化トークンの自己検出フィルタで使う構文上の制約として扱います。

Presidio組み込みのレコグナイザ（`PERSON`, `DATE_TIME`, `ORGANIZATION` 等）が生成する
`entity_type`、および `regex_recognizers.py` が生成する `PHONE_NUMBER` /
`JP_POSTAL_CODE` は、いずれもこの命名規約に準拠しています。

## 8. CLI

```bash
# マスキング実行
python -m document_masking mask \
  --input sample_data/sample_inquiry.txt \
  --output output/masked.txt \
  --salt-file .secrets/salt.key \
  --spacy-model ja_core_news_sm

# 検出漏れチェック
python -m document_masking verify \
  --input output/masked.txt \
  --output output/verify_report.json      # 拡張子 .csv / .json に対応
```

`--salt-file`・`--spacy-model` はいずれも省略可能で、省略時は
デフォルト値（`--salt-file`は`.secrets/salt.key`、`--spacy-model`は`ja_core_news_sm`）が使われます。

`mask` の引数（`src/__main__.py` の `build_parser()`）:

| 引数 | 必須/任意 | デフォルト |
|---|---|---|
| `--input` | 必須 | - |
| `--output` | 必須 | - |
| `--salt-file` | 任意 | `.secrets/salt.key` |
| `--spacy-model` | 任意 | `ja_core_news_sm` |

`verify` の引数（`--salt-file` は存在しません。`verify` は仮名化を行わないためソルトを
使いません）:

| 引数 | 必須/任意 | デフォルト |
|---|---|---|
| `--input` | 必須 | - |
| `--output` | 必須 | - |
| `--spacy-model` | 任意 | `ja_core_news_sm` |

サブコマンド未指定・不正な場合は `argparse` がエラーを出して終了します
（`subparsers = parser.add_subparsers(dest="command", required=True)`）。

`verify` の終了コードは、残存PII候補が1件でもあれば `1`、なければ `0` です
（`main()` が `scan_text()` の結果をそのまま真偽判定し、プロセスの終了コードとして
返します）。CI等での自動チェックにも使える設計です。

## 9. 既知の制限（`ja_core_news_sm` の検出漏れとverifyの盲点）

デフォルトのspaCyモデル `ja_core_news_sm` を用いた場合、複数トークンからなる日本語人名
（姓+名）の一部がタグ付けされず平文のまま残存するなど、モデルの精度に起因する検出漏れが
起こり得ます。

さらに重要なのは、`verify` は `mask` と**同一の検出器**（同じspaCyモデルを含む）を
再適用する設計（2章参照）であるため、**この種の検出漏れは `verify` のレポートにも
現れない**という点です。すなわち **`verify` レポートが空であることは、「PIIが完全に
除去されたことの保証」にはなりません。**

これは、`verify` があくまで人間レビューを補助するチェックであって、レビューの代替では
ないということを意味します。本番運用にあたっては、以下の2点を運用要件として推奨します。

1. CLIの `--spacy-model` を `ja_core_news_lg` に変更し、`ja_core_news_sm` より高精度な
   NERモデルを利用すること。モデル追加はDockerfileに組み込み、イメージを再ビルドする。
2. `verify` レポートの確認に加えて、マスキング済みファイルそのものを人間が目視で
   確認すること。

## 10. セキュリティ・運用上の注意

- `.secrets/salt.key` は仮名化のハッシュに使うソルトです。**顧客環境の外に一切持ち出しては
  いけません。** 初回 `mask` 実行時に自動生成され、作成時に所有者のみ読み書き可能な
  パーミッション（`0600`）に制限されます（`load_or_create_salt()`）。`.secrets/` は
  `.gitignore` 対象です。
- 仮名化は不可逆です。元の値と仮名の対応表は保存されません。同じsalt・同じ正規化入力で
  あれば常に同じトークンになるため、文書内での同一エンティティの一貫性は保たれます
  （6章）。
- `verify` のレポート（CSV/JSON）には検出テキストの原文がそのまま含まれます。人間レビュー用の
  ファイルであり、外部へは一切送信しないでください。
- `verify` は `mask` と同一の検出器（同じspaCyモデルを含む）を再適用するため、検出漏れの
  盲点も共有します（9章）。`verify` レポートが空であっても「PIIが完全に除去された」ことには
  なりません。本番運用では `ja_core_news_lg` の利用と、マスキング済みファイルの人手による
  目視確認を推奨します。

## 11. テスト方針

TDD（テスト駆動開発）で実装されており、`tests/` 配下に以下のテストファイルが存在します
（`pytest`、`pyproject.toml` の `[tool.pytest.ini_options]` で `testpaths = ["tests"]`
を指定）。ファイルシステムに触れるテストはすべて `tmp_path` フィクスチャで隔離されており、
リポジトリ内の実ファイルや `.secrets/` を汚しません。

| ファイル | 主な検証内容 |
|---|---|
| `test_smoke.py` | パッケージがimport可能であることの疎通確認 |
| `test_regex_recognizers.py` | JP電話番号・郵便番号・CustomPattern（顧客固有パターン）の検出精度 |
| `test_analyzer.py` | `AnalyzerEngine` 組み立て、人名検出、電話番号検出、空文字列の扱い |
| `test_pseudonymizer.py` | 仮名化の決定性・非決定性（異なる入力/salt）、出力フォーマット、全角半角正規化、元の値が出力に含まれないこと（非可逆性）、salt生成・永続化・パーミッション |
| `test_masker.py` | `mask_text()`/`mask_file()` の検出→置換動作、空文字列の扱い、重複検出時にテキストが破壊されないこと、ファイル読み書き |
| `test_verify.py` | 残存PII検出、クリーンなテキストで候補が出ないこと、仮名化トークン自己検出フィルタの有効性、レポート出力（CSV/JSON）、未対応拡張子の拒否 |
| `test_cli.py` | `mask`→`verify` のCLI一気通貫実行、サブコマンド未指定時のエラー |
| `test_generate_sample.py` | `sample_data/generate_sample.py` が生成するテキストに氏名・電話番号が含まれること |
| `test_e2e.py` | サンプルデータ生成から `mask`→`verify` までの一気通貫シナリオ（Task 13で追加） |

## 12. スコープ外

- Word（`.docx`）・PowerPoint（`.pptx`）への対応。現状は`.txt`/`.md`をプレーンテキストとして
  読み込む実装のみであり、Officeファイル形式のパース処理は実装されていません（将来拡張）。
- カラム単位のポリシー設定（`policy.yaml`のような仕組み）。1章で述べた通り、自由記述の
  文書には「カラム」という概念が存在しないため、意図的に持たせていません。カラム単位の
  制御が必要な表形式データは `database_masking/` の対象範囲です。
- `database_masking` とのコード共有。`masking/pseudonymizer.py` の仮名化アルゴリズムや
  entity_type命名規約は、両ツール間で処理内容が一致していますが、共通ライブラリとして
  切り出さず、それぞれのツール内に独立して複製実装しています。これは実装の見落としでは
  なく、「各ツールが自身のフォルダ内で設計・実装・ドキュメントを完結して管理する」という
  本プロジェクトの方針に基づく意図的な選択です。両ツールが共有ライブラリに依存すると、
  一方の変更がもう一方の挙動に意図せず影響する結合が生まれるため、それぞれのツールが
  独立してリリース・保守できることを優先しています。

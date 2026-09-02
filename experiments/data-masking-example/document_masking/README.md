# ドキュメントマスキングツール

自由記述のテキストファイル（.txt/.md）を対象に、ファイル全体をスキャンして
氏名・電話番号などのPIIらしき情報を検出し、仮名化するローカル実行ツールです。
表形式データ（CSV/Excel/SQLite）向けの`database_masking/`とは独立したツールです。

## セットアップ

このディレクトリ（`document_masking/`）でビルドします。
DockerイメージはPython 3.14.7の公式通常版イメージを使用します。

```bash
docker compose build
```

以降のコマンドはコンテナ内で実行できます。

```bash
# サンプルデータ生成（初回のみ）
docker compose run --rm app python sample_data/generate_sample.py

# マスキング実行
docker compose run --rm app python -m document_masking mask \
  --input sample_data/sample_inquiry.txt \
  --output output/masked.txt

# 検出漏れチェック
docker compose run --rm app python -m document_masking verify \
  --input output/masked.txt \
  --output output/verify_report.json
```

`docker-compose.yml` はこのプロジェクト単体用です。`output/` と `.secrets/` はホスト側の
`document_masking/` 配下に作成されます。

## サンプルデータについて

`sample_data/` と `output_example/` に含まれるデータは、動作確認用に
`sample_data/generate_sample.py` の固定文面から生成した架空の合成データです。
実在の個人情報・顧客情報は含まれていません。

## 使い方

```bash
# サンプルデータ生成（初回のみ）
docker compose run --rm app python sample_data/generate_sample.py

# マスキング実行
docker compose run --rm app python -m document_masking mask \
  --input sample_data/sample_inquiry.txt \
  --output output/masked.txt

# 検出漏れチェック
docker compose run --rm app python -m document_masking verify \
  --input output/masked.txt \
  --output output/verify_report.json
```

`--spacy-model`（デフォルト`ja_core_news_sm`、本番では`ja_core_news_lg`を推奨）は任意で
指定できます。

`policy.yaml`のようなカラム単位の設定は存在しません。ファイル全体をテキストとして読み込み、
Regex・NER（spaCy日本語モデル）を基本の検出器として使い、見つかった箇所をすべて
仮名化トークンに置換します。

## 重要な運用上の注意

- `.secrets/salt.key` は仮名化のハッシュに使うソルトです。**顧客環境の外に一切持ち出さないでください**。
- 仮名化は不可逆です。元の値と仮名の対応表は保存されません。
- `verify` は `mask` と同一の検出器を再適用するため、検出漏れの盲点も共有します。
  `verify` レポートが空であっても「PIIが完全に除去された」ことにはなりません。
  マスキング済みファイルを人間が目視確認してください。

## テスト

```bash
docker compose run --rm app pytest
```

## スコープ外

- Word（.docx）・PowerPoint（.pptx）への対応（将来拡張）
- カラム単位のポリシー設定（`database_masking/`を参照）

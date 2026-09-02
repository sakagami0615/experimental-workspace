# masking example

顧客の閉域環境で実データを外部分析基盤へ持ち出し可能な状態に加工するための、
ローカル実行ツール群です。用途に応じて2つの独立したツールに分かれています。

## [database_masking/](database_masking/) — 表形式データ向け

CSV・Excel・SQLiteデータベースを対象に、`policy.yaml`でカラム単位のマスキング方針
（削除・仮名化・維持・自由記述スキャン）を定義して適用します。詳細は
[database_masking/README.md](database_masking/README.md)を参照してください。

## [document_masking/](document_masking/) — 自由記述文書向け

プレーンテキスト・Markdownファイルを対象に、ファイル全体をスキャンして氏名・電話番号
などのPIIらしき情報を検出・仮名化します。詳細は
[document_masking/README.md](document_masking/README.md)を参照してください。

---

各ツールは独立したPythonプロジェクトです（それぞれ独自の`pyproject.toml`とDocker環境を
持ちます）。セットアップ手順は各ツールのREADMEを参照してください。

## サンプルデータについて

この実験に含まれる `sample_data/` と `output_example/` のデータは、動作確認用に固定リストと
テンプレートから生成した架空の合成データです。実在の個人情報・顧客情報は含まれていません。

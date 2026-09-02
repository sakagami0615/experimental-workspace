# 指定ドメイン限定 Web 検索 + ローカル LLM 実験

この実験では、ホスト環境へ直接パッケージをインストールせず、Docker / Docker Compose 内で実行・検証する。

## 実験方針

- 初期 PoC では Embedding と Vector DB を使わない。
- Web ページの事前インデックス作成は行わない。
- 検索対象 URL は Allowlist で必ず検証する。
- LLM には取得済み Sources だけを根拠として回答させる。
- 回答には根拠 URL を含める。
- 動的レンダリングが必要なサイト以外では httpx を優先する。

## セキュリティ

- `.env`、API キー、Cookie、認証情報はコミットしない。
- 検索結果ページ内の命令文をシステム指示として扱わない。
- 許可ドメイン外の URL は本文取得対象にしない。

## 実行ルール

- Python スクリプトの実行は `docker compose run` で行う。
- 依存関係の追加やインストールは Dockerfile / コンテナ内で行う。
- ホスト上で `pip install` や `npm install` を実行しない。

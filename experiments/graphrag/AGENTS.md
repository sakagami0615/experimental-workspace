# GraphRAG 実験

SurrealDB / Neo4j / EdgeDB の3種類のDBを使ってGraphRAGパイプラインを検証する実験。
各DBは `surrealdb/`, `neo4j/`, `edgedb/` フォルダで独立して管理する。

## 前提条件

- Docker / Docker Compose がインストール済み
- ホストマシンで Ollama が起動中（デフォルト: `http://localhost:11434`）
- 使用するモデルが Ollama にプルされていること（例: `ollama pull nomic-embed-text && ollama pull llama3.2`）

## 各環境の起動方法

各 DB フォルダ内で以下を実行:

```bash
# .env ファイルを作成
cp .env.example .env

# DB コンテナを起動
docker compose up -d <db-service>

# [1] グラフ構築（スキーマ作成 + データ投入）
docker compose run --rm python python src/build.py

# [2] データ更新（JSONファイルを引数で指定、省略時は data/sample.json を使用）
docker compose run --rm python python src/update.py [data/your_data.json]

# [3] 回答生成（質問を引数で指定）
docker compose run --rm python python src/query.py "質問文"

# 後片付け
docker compose down -v
```

### スクリプト構成

各 DB フォルダの `src/` には以下の4ファイルがある:

| ファイル | 役割 |
|---|---|
| `common.py` | 共有ユーティリティ（`embed`, `generate`, DB接続ヘルパー） |
| `build.py` | スキーマ作成 + 初回データ投入 |
| `update.py` | 既存グラフへのノード・エッジのアップサート |
| `query.py` | クエリ検索 + LLM回答生成 |

## 環境変数（.env）

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `OLLAMA_BASE_URL` | OllamaのベースURL | `http://host.docker.internal:11434` |
| `OLLAMA_EMBED_MODEL` | 埋め込みモデル名 | `nomic-embed-text` |
| `OLLAMA_LLM_MODEL` | LLMモデル名 | `llama3.2` |

## 注意事項

- `.env` ファイルはコミットしないこと（`.gitignore` で除外済み）
- OllamaのモデルはRunするたびに変更可能（`.env` を編集）
- Linux では `host.docker.internal` が自動解決されないため、`docker-compose.yml` の `extra_hosts` で対応済み
- 各DBの詳細は `memo.txt` を参照
- パッケージインストールには `uv` を使用し、Dockerfile内では `pip install uv --no-cache-dir && uv pip install --system --no-cache -r requirements.txt` のパターンを使うこと。`pip install` を直接書かない。

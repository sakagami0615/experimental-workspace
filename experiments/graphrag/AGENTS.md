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

# GraphRAG スクリプトを実行
docker compose run --rm python python src/run.py

# 後片付け
docker compose down -v
```

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

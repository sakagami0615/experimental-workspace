# GraphRAG 実験環境 設計書

## 概要

SurrealDB / Neo4j / EdgeDB の3種類のデータベースを使ったGraphRAGのPoC実験環境を構築する。
動作環境はDocker、LLM・埋め込みモデルはホストで動作するOllamaを使用する。

## 要件

- **対象DB**: SurrealDB、Neo4j、EdgeDB（3つ全て）
- **ランタイム**: Docker（DBおよびPython実行環境をコンテナ化）
- **LLM / 埋め込みモデル**: ホストのOllama（コンテナからは `host.docker.internal:11434` でアクセス）
- **目的**: 各DBでGraphRAGパイプラインが動作することを確認するPoC
- **インターフェース**: 各DB用の独立したPythonスクリプト（`src/run.py`）
- **モデル設定**: `.env` ファイルの環境変数で切り替え可能

## ディレクトリ構成

```
experiments/graphrag/
├── AGENTS.md
├── README.md
├── .gitignore
├── surrealdb/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── src/
│   │   └── run.py
│   └── data/
│       └── sample.json
├── neo4j/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── src/
│   │   └── run.py
│   └── data/
│       └── sample.json
└── edgedb/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── .env.example
    ├── src/
    │   └── run.py
    ├── schemas/
    │   └── default.esdl
    └── data/
        └── sample.json
```

各DBフォルダは完全に独立しており、個別に `docker compose up` で起動・実行できる。

## データフロー（各DBで共通）

```
1. data/sample.json からドキュメント（ノード・エッジ）を読み込む
2. Ollama embed API でテキストを埋め込みベクトルに変換
3. DBにノード・エッジ・ベクトルを格納
4. ユーザークエリをベクトル化
5. ベクトル検索 + グラフトラバースで関連コンテキストを取得
6. 取得したコンテキストを Ollama LLM API に渡して回答生成
7. 回答を標準出力に表示
```

## サンプルデータ仕様（sample.json）

技術トピック間の関係を表す簡単な知識グラフ。

- **ノード**: 技術概念（例: "GraphRAG", "ベクトル検索", "グラフDB"など）
- **エッジ**: 関係の種類（例: "RELATED_TO", "REQUIRES", "PART_OF"）

3環境で同じ `sample.json` フォーマットを使用し、比較しやすくする。

## Ollama接続設定

| 項目 | 内容 |
|---|---|
| ホストアクセス | `http://host.docker.internal:11434` |
| Linux対応 | `docker-compose.yml` に `extra_hosts: ["host.docker.internal:host-gateway"]` を追加 |

## 環境変数（.env.example）

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2
```

モデルは `.env` を編集することで自由に変更可能。スクリプト内では `os.getenv()` で読み込む。

## 各DB固有の実装方針

### SurrealDB

- SurrealQL の1クエリでベクトル検索（`<|K,COSINE|>`）とグラフトラバース（`->`）を同時実行
- バージョン: `surrealdb/surrealdb:latest`
- Pythonライブラリ: `surrealdb`

### Neo4j

- ベクトル検索: `db.index.vector.queryNodes` で k-NN 検索
- グラフ検索: 別途 `MATCH` クエリでパス探索し、アプリ側でマージ
- バージョン: `neo4j:5`（Vector Index サポート版）
- Pythonライブラリ: `neo4j`

### EdgeDB

- 埋め込みは手動で生成してプロパティとして保存（`ext::ai` は外部API依存のため不使用）
- ベクトル検索: 全ノードの埋め込みをPython側に取得し、コサイン類似度を計算してソート（PoCのため小規模データを前提）
- グラフ探索: EdgeQL の `link` 参照でネストした SELECT
- バージョン: `edgedb/edgedb:5`
- Pythonライブラリ: `edgedb`
- スキーマ定義: `schemas/default.esdl`

## 除外事項（PoCスコープ外）

- 性能ベンチマーク・比較測定
- 認証・TLS設定
- 大規模データ投入
- テストコード

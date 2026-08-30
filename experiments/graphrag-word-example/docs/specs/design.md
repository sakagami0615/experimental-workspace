# GraphRAG 実験環境 設計書

## 目的

この実験環境は、SurrealDB / Neo4j / EdgeDB の3種類のデータベースで Hybrid GraphRAG パイプラインを実装し、同じ知識データに対して各DBの表現力、検索方法、実装差分を比較するための PoC である。

GraphRAG の主目的は、ベクトル検索だけでは拾いにくい概念間の関係をグラフ検索で補い、LLM に渡すコンテキストの網羅性を高めることにある。

## スコープ

対象に含めるもの:

- 小規模な概念ノードを対象にしたグラフ構築
- LLM によるノード間関係の自動抽出
- ベクトル検索とグラフ検索の並列実行
- 検索結果の重複排除とマージ
- 取得コンテキストを使った LLM 回答生成
- SurrealDB / Neo4j / EdgeDB の実装比較

対象外とするもの:

- 大規模データ投入
- 本番運用向けの認証・TLS・監査ログ
- 性能ベンチマークの自動化
- UI / API サーバ化
- 継続的なインデックス再構築戦略

## 全体アーキテクチャ

各DB環境は独立したフォルダとして構成し、DBサービスと Python 実行環境を `docker-compose.yml` で定義する。Python コンテナはホストで起動している Ollama に `host.docker.internal:11434` 経由で接続する。

```text
ユーザー
  |
  | docker compose run --rm python python src/query.py "質問文"
  v
Python コンテナ
  |
  +-- Ollama: 埋め込み生成 / エンティティ抽出 / 回答生成
  |
  +-- 対象DB: ノード、埋め込み、関係エッジを保存・検索
```

## ディレクトリ構成

```text
.
├── README.md
├── docs/
│   └── design.md
├── surrealdb/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── pyproject.toml
│   ├── data/sample.json
│   └── src/
│       ├── common.py
│       ├── build.py
│       ├── update.py
│       └── query.py
├── neo4j/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── pyproject.toml
│   ├── data/sample.json
│   └── src/
│       ├── common.py
│       ├── build.py
│       ├── update.py
│       └── query.py
└── edgedb/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── pyproject.toml
    ├── dbschema/default.esdl
    ├── data/sample.json
    └── src/
        ├── common.py
        ├── build.py
        ├── update.py
        └── query.py
```

## データモデル

入力データは各DBフォルダの `data/sample.json` に置く。現在の設計では、JSON 側にはノード情報を定義し、エッジは `build.py` / `update.py` 実行時に LLM がノード内容から自動抽出する。

```json
{
  "nodes": [
    {
      "id": "graphrag",
      "label": "GraphRAG",
      "content": "GraphRAGはグラフ構造を活用したRAG手法..."
    }
  ],
  "query": "GraphRAGとは何か？"
}
```

ノードの論理モデル:

| 項目 | 説明 |
|---|---|
| `node_id` | ノードの一意識別子。入力JSONの `id` に対応する。 |
| `label` | 概念名。全文検索と表示に使用する。 |
| `content` | 概念説明。埋め込み生成と回答コンテキストに使用する。 |
| `embedding` | `content` から生成したベクトル。 |
| relation | LLM が抽出した概念間の関係。`USES` / `EXTENDS` / `REQUIRES` / `PART_OF` / `RELATED_TO` を想定する。 |

## 処理フロー

### グラフ構築

`src/build.py` は初回構築用のスクリプトである。

```text
data/sample.json 読み込み
  |
  +-- content を Ollama 埋め込みモデルでベクトル化
  |
  +-- DB に Concept ノードを登録
  |
  +-- LLM でノード間の関係を抽出
  |
  +-- DB に関係エッジまたはリンクを作成
  |
  +-- 必要な全文検索インデックスを作成
```

### データ更新

`src/update.py` は既存グラフへの追加・更新用のスクリプトである。引数で JSON ファイルを指定でき、省略時は `data/sample.json` を使用する。

```text
追加JSON 読み込み
  |
  +-- ノードをアップサート
  |
  +-- LLM で対象ノード間の関係を抽出
  |
  +-- 関係を追加
```

### 質問応答

`src/query.py` は Hybrid RAG の検索・回答生成を行う。

```text
質問
  |
  +-- ベクトル検索: 質問に意味的に近い Concept を top-k 取得
  |
  +-- グラフ検索: LLMでエンティティ抽出 → 全文検索 → 隣接ノード取得
  |
  +-- RunnableParallel で両検索を並列実行
  |
  +-- node_id で重複排除してコンテキスト化
  |
  +-- Ollama LLM にコンテキストと質問を渡して回答生成
```

## 共通コンポーネント

各DBの `src/common.py` は、以下の責務を持つ。

| 関数 | 責務 |
|---|---|
| `get_embeddings()` | `langchain_ollama.OllamaEmbeddings` を生成する。 |
| `get_llm()` | `langchain_ollama.ChatOllama` を生成する。 |
| `generate()` | 検索コンテキストを使って回答を生成する。 |
| `extract_relations()` | LLM の構造化出力またはJSON出力からノード間関係を抽出する。 |
| `extract_entities()` | 質問からグラフ検索用キーワードを抽出する。 |
| DB接続ヘルパー | 各DBのクライアントまたは接続オブジェクトを生成する。 |

## DB別設計

### Neo4j

Neo4j は専用グラフDBとして、ノードとリレーションを直接表現する。

| 項目 | 内容 |
|---|---|
| DBサービス | `neo4j:5` |
| 接続 | Bolt: `bolt://neo4j:7687` |
| ベクトル検索 | `langchain_neo4j.Neo4jVector` |
| グラフ検索 | Fulltext Index + Cypher traversal |
| ノードラベル | `Concept` |
| 関係 | `(:Concept)-[:HAS_RELATION {relation}]->(:Concept)` |

特徴:

- `Neo4jVector.from_documents()` で埋め込み付きノードを作成する。
- `CREATE FULLTEXT INDEX conceptFulltext` で `label` / `content` を検索対象にする。
- グラフ検索では全文検索で起点ノードを探し、`HAS_RELATION` の隣接ノードを取得する。
- `Neo4jGraph` は APOC 依存を避けるため `refresh_schema=False` で利用する。

### SurrealDB

SurrealDB はマルチモデルDBとして、ドキュメント、ベクトル、グラフ関係を同一DB上で扱う。

| 項目 | 内容 |
|---|---|
| DBサービス | `surrealdb/surrealdb:v2` |
| 接続 | HTTP: `http://surrealdb:8000` |
| ベクトル検索 | `langchain_surrealdb.vectorstores.SurrealDBVectorStore` |
| グラフ検索 | BM25全文検索 + SurrealQL graph traversal |
| テーブル | `concept` |
| 関係 | `concept:id->has_relation->concept:id` |

特徴:

- `SurrealDBVectorStore` で埋め込みを保存・検索する。
- `DEFINE ANALYZER` と `DEFINE INDEX ... SEARCH ... BM25` で全文検索を構成する。
- 起点ノードから `->has_relation->concept.*` で隣接ノードを取得する。
- SurrealDB クライアントの結果形式差は `_surreal_result()` で吸収する。

### EdgeDB

EdgeDB は型付きスキーマとリンクにより、概念間の関係を表現する。

| 項目 | 内容 |
|---|---|
| DBサービス | `edgedb/edgedb:4` |
| 接続 | `edgedb://edgedb@edgedb:5656/edgedb?tls_security=insecure` |
| ベクトル検索 | Python側でコサイン類似度を計算 |
| グラフ検索 | `ILIKE` キーワード検索 + link traversal |
| 型 | `default::Concept` |
| 関係 | `multi related_concepts: Concept` |

特徴:

- `build.py` が dev mode の DDL で `Concept` 型を作成する。
- `embedding` は `array<float64>` として保存する。
- LangChain 公式の EdgeDB vector store は使わず、全ノードを取得して Python 側でコサイン類似度を計算する。
- `RunnableParallel` の並列実行に備え、検索ブランチごとに独立した EdgeDB クライアントを生成してクローズする。

## 環境変数

各DBフォルダで `.env.example` を `.env` にコピーし、必要に応じて値を変更する。実際の `.env` はコミット対象外である。

| 変数 | デフォルト | 説明 |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama のベースURL。 |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | 埋め込みモデル名。 |
| `OLLAMA_LLM_MODEL` | `llama3.2` | 関係抽出、エンティティ抽出、回答生成に使うモデル名。 |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j 接続URI。 |
| `NEO4J_USER` | `neo4j` | Neo4j ユーザー名。 |
| `NEO4J_PASS` | `testpassword` | Neo4j パスワード。 |
| `SURREAL_URL` | `http://surrealdb:8000` | SurrealDB 接続URL。 |
| `SURREAL_USER` | `root` | SurrealDB ユーザー名。 |
| `SURREAL_PASS` | `root` | SurrealDB パスワード。 |
| `SURREAL_NS` | `graphrag_ns` | SurrealDB namespace。 |
| `SURREAL_DB` | `graphrag_db` | SurrealDB database。 |
| `EDGEDB_DSN` | `edgedb://edgedb@edgedb:5656/edgedb?tls_security=insecure` | EdgeDB 接続DSN。 |

## 実行シーケンス

対象DBのフォルダに移動して実行する。

```bash
cp .env.example .env
docker compose up -d <db-service>
docker compose run --rm python python src/build.py
docker compose run --rm python python src/update.py [data/your_data.json]
docker compose run --rm python python src/query.py "質問文"
docker compose down -v
```

`<db-service>` は `neo4j` / `surrealdb` / `edgedb` のいずれかである。

## 比較観点

| 観点 | Neo4j | SurrealDB | EdgeDB |
|---|---|---|---|
| グラフ表現 | ネイティブなノード・リレーション | record link / relation table | link |
| クエリ言語 | Cypher | SurrealQL | EdgeQL |
| ベクトル検索 | LangChain統合を利用 | LangChain統合を利用 | Python側で独自計算 |
| 全文検索 | Fulltext Index | BM25 Search Index | `ILIKE` |
| スキーマ | 柔軟 | 柔軟 | 明示的な型定義 |
| PoCでの強み | グラフトラバースの自然さ | 1DBで多モデルを扱える | 型安全なモデル表現 |
| PoCでの制約 | Neo4j固有の運用知識が必要 | バージョン差や結果形式差に注意 | 大規模ベクトル検索には不向き |

## 設計上の制約と注意

- LLM による関係抽出は非決定的であり、モデルやプロンプトによりエッジ数・関係種別が変わる可能性がある。
- `update.py` は新規ノード投入と関係追加を目的とし、既存関係の削除や再正規化は扱わない。
- EdgeDB のベクトル検索は全件をアプリケーション側に読み出すため、小規模PoC専用の実装である。
- SurrealDB のクエリ文字列生成では、入力データの扱いに注意する。PoCではローカルサンプルを前提とする。
- 本番相当の検証を行う場合は、認証情報管理、スキーママイグレーション、LLM出力検証、テストデータ管理を追加設計する必要がある。

## 今後の拡張候補

- 検索結果のスコア統合とランキング改善
- LLM 抽出エッジの監査ログ化
- エッジ種別ごとの重み付け
- DBごとの性能比較スクリプト
- 評価用質問セットと期待回答による回帰テスト
- 共通コードの抽象化とDB別アダプタ化

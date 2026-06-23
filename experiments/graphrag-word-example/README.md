# GraphRAG 実験

## 概要

SurrealDB / Neo4j / EdgeDB の 3 種類のグラフデータベースを使った **Hybrid GraphRAG** パイプラインの PoC。  
ベクトル検索とグラフ検索を並列実行して回答の精度向上を検証する。

---

## Hybrid RAG とは

このPoCで実装しているアーキテクチャは、**ベクトル検索** と **グラフ検索** を独立して並列実行し、結果をマージしてコンテキストを構成する手法（LangChain ブログ参考）。

```
質問
 ├─ [ベクトル検索] 意味的に近いノードを k 件取得
 └─ [グラフ検索]   LLM でエンティティ抽出 → DB 全文検索 → 隣接ノードを辿る
         ↓
  両結果をマージ（重複除去）
         ↓
  LLM が回答生成
```

グラフ検索を加えることで、ベクトル検索では拾えない「関連概念の連鎖」を文脈に含められる。

---

## スクリプト構成

各 DB フォルダに以下の 3 スクリプトがある。

| スクリプト | 役割 |
|---|---|
| `src/build.py` | グラフを初期構築（ノード登録 + エッジ作成 + インデックス作成） |
| `src/update.py` | 既存グラフへのノード・エッジ追加（アップサート） |
| `src/query.py` | Hybrid RAG で質問に回答 |

---

## データ形式

`data/sample.json` にノード情報を定義する。サンプルデータには手動エッジを含めず、各 DB の build/update がノード内容から関係を自動抽出してエッジを作成する。

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

| フィールド | 必須 | 説明 |
|---|---|---|
| `nodes[].id` | ○ | ノードの一意識別子（英数字・アンダースコア推奨） |
| `nodes[].label` | ○ | 概念名（全文検索・表示に使用） |
| `nodes[].content` | ○ | 概念の説明文（ベクトル埋め込みに使用） |
| `query` | - | 動作確認用のサンプル質問 |

---

## DB ごとの比較

### 機能比較表

| 観点 | Neo4j | SurrealDB | EdgeDB |
|---|---|---|---|
| DBの種別 | 専用グラフDB | マルチモデルDB | グラフ・リレーショナルDB |
| クエリ言語 | Cypher | SurrealQL | EdgeQL |
| ベクトル検索 | Neo4jVector（langchain） | SurrealDBVectorStore（langchain） | 独自実装（コサイン類似度） |
| グラフ全文検索 | Fulltext Index + Cypher | BM25 `@@` 演算子 | `ILIKE` パターンマッチ |
| エッジ定義 | LLM が自動抽出 | LLM が自動抽出 | LLM が自動抽出 |
| LangChain 統合 | あり（langchain-neo4j） | あり（langchain-surrealdb） | なし（公式統合なし） |

### Neo4j

- **特徴**: グラフDB の中で最も成熟した製品。Cypher という専用クエリ言語を持ち、複雑な多段トラバースが得意。
- **ベクトル検索**: `Neo4jVector` を利用。ベクトルインデックスをネイティブ管理。
- **グラフ検索**: `CREATE FULLTEXT INDEX` で全文インデックスを作成し、`CALL db.index.fulltext.queryNodes()` で検索後にグラフトラバース。
- **エッジ**: `build.py` 実行時に LLM（Pydantic 構造化出力）が `nodes` の内容を読んで関係を自動抽出する。JSON に `edges` の記載は不要。
- **注意**: 標準イメージには APOC プラグインが含まれないため、`Neo4jGraph` に `refresh_schema=False` を設定している。

```cypher
-- グラフ検索クエリ例
CALL db.index.fulltext.queryNodes('conceptFulltext', $entity) YIELD node
WITH node LIMIT 3
OPTIONAL MATCH (node)-[:HAS_RELATION]->(r:Concept)
RETURN node.node_id, node.label, node.content, collect(r) AS neighbors
```

### SurrealDB

- **特徴**: グラフ・ドキュメント・ベクトルを 1 つの DB で扱えるマルチモデル DB。クエリも 1 本で完結しやすい。
- **ベクトル検索**: `SurrealDBVectorStore` を利用。
- **グラフ検索**: BM25 全文検索（`@@` 演算子）でノードを特定し、SurrealQL のグラフ構文 `->has_relation->concept.*` で隣接ノードを取得。
- **エッジ**: `build.py` / `update.py` 実行時に LLM が `nodes` の内容を読んで関係を自動抽出し、`RELATE` 文で登録する。JSON に `edges` の記載は不要。

```surql
-- グラフ検索クエリ例（全文検索）
SELECT node_id, label, content FROM concept WHERE label @@ 'GraphRAG' LIMIT 5;

-- 隣接ノード取得
SELECT ->has_relation->concept.* AS related FROM concept:⟨graphrag⟩;
```

### EdgeDB

- **特徴**: リレーショナル DB の厳密な型システムとグラフ DB のリンク機能を組み合わせた DB。スキーマ定義が必須。
- **ベクトル検索**: LangChain 公式統合がないため独自実装。全ノードのベクトルをメモリに読み込み、コサイン類似度で順位付けする（ノード数が増えると低速になる）。
- **グラフ検索**: ネイティブの全文インデックスがないため `ILIKE` で部分一致検索し、`related_concepts` リンクで隣接ノードを取得。
- **エッジ**: `build.py` / `update.py` 実行時に LLM が `nodes` の内容を読んで関係を自動抽出し、EdgeQL の `UPDATE ... SET { related_concepts += ... }` でリンクを設定する。JSON に `edges` の記載は不要。
- **スレッド安全性**: `RunnableParallel` の各ブランチが独立した EdgeDB クライアントを生成・クローズする実装になっている。

```edgeql
-- 全文検索（ILIKE による近似）
SELECT default::Concept { node_id, label, content }
FILTER .label ILIKE '%GraphRAG%' OR .content ILIKE '%GraphRAG%';

-- 隣接ノード取得
SELECT default::Concept { related_concepts: { node_id, label, content } }
FILTER .node_id = 'graphrag';
```

---

## 実行手順

### 前提

- Docker / Docker Compose が起動していること
- Ollama がローカルで動作していること（`localhost:11434`）
- 以下のモデルが Ollama にダウンロード済みであること
  - 埋め込みモデル: `nomic-embed-text`
  - LLM: 任意（デフォルト `llama3.2`。`.env` で変更可）

### 共通手順

```bash
# 対象DBのフォルダに移動
cd neo4j/   # または surrealdb/ / edgedb/

# モデルを変更したい場合は .env を作成
cp .env.example .env
# OLLAMA_LLM_MODEL=gemma3:latest など編集

# グラフ構築（初回）
docker compose run --rm python python src/build.py

# ノード追加・更新（2回目以降）
docker compose run --rm python python src/update.py [data/your_data.json]

# 質問して回答生成
docker compose run --rm python python src/query.py "質問文"

# コンテナ停止
docker compose down
```

### 環境変数

各フォルダの `.env.example` を参照。主な変数は以下の通り。

| 変数 | デフォルト | 説明 |
|---|---|---|
| `OLLAMA_LLM_MODEL` | `llama3.2` | 回答生成・エンティティ抽出に使う LLM |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | ベクトル埋め込みモデル |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama エンドポイント |

---

## 参考

- [LangChain Blog: Enhancing RAG-Based Applications Accuracy by Constructing and Leveraging Knowledge Graphs](https://www.langchain.com/blog/enhancing-rag-based-applications-accuracy-by-constructing-and-leveraging-knowledge-graphs)
- 詳細な調査結果: `APPENDIX/DeepReserch.md`

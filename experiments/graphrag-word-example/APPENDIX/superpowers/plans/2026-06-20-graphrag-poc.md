# GraphRAG PoC 実験環境 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SurrealDB / Neo4j / EdgeDB の3種類のDBを使ったGraphRAGパイプラインをDocker + Ollama(ホスト)環境で動作確認する

**Architecture:** 各DBフォルダが独立したDocker Compose構成を持ち、Pythonスクリプト（コンテナ内）が `host.docker.internal:11434` 経由でホストのOllamaにアクセスする。ベクトル生成・LLM呼び出しはOllama REST APIをhttpxで直接呼ぶ。SurrealDBはHTTP REST API経由、Neo4jはPython公式ドライバ、EdgeDBはPython公式クライアントを使用。

**Tech Stack:** Python 3.12, httpx, neo4j, edgedb, SurrealDB REST API, Ollama REST API, Docker Compose

---

## ファイルマップ

```
experiments/graphrag/
├── AGENTS.md
├── README.md
├── .gitignore
├── surrealdb/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── requirements.txt
│   ├── data/
│   │   └── sample.json
│   └── src/
│       └── run.py
├── neo4j/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── requirements.txt
│   ├── data/
│   │   └── sample.json
│   └── src/
│       └── run.py
└── edgedb/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── .env.example
    ├── requirements.txt
    ├── dbschema/
    │   └── default.esdl
    ├── data/
    │   └── sample.json
    └── src/
        └── run.py
```

---

## Task 1: feature ブランチ作成 + ベース構造

**Files:**
- Create: `experiments/graphrag/AGENTS.md`
- Create: `experiments/graphrag/README.md`
- Modify: `experiments/graphrag/.gitignore`

- [ ] **Step 1: feature ブランチを作成**

```bash
git checkout -b feature/graphrag-poc
```

Expected: `Switched to a new branch 'feature/graphrag-poc'`

- [ ] **Step 2: .gitignore を更新**

`experiments/graphrag/.gitignore` の内容:

```gitignore
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
data/raw/
```

- [ ] **Step 3: AGENTS.md を作成**

`experiments/graphrag/AGENTS.md` の内容:

```markdown
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
```

- [ ] **Step 4: README.md を作成**

`experiments/graphrag/README.md` の内容:

```markdown
# GraphRAG 実験

## 概要

SurrealDB / Neo4j / EdgeDB の3種類のグラフデータベースを使ったGraphRAGパイプラインのPoC。

## 構成

| フォルダ | DB | 特徴 |
|---|---|---|
| `surrealdb/` | SurrealDB | ベクトル+グラフを1クエリで処理 |
| `neo4j/` | Neo4j | 成熟したグラフDB、Cypher使用 |
| `edgedb/` | EdgeDB | グラフ-リレーショナルモデル |

## 各環境の実行手順

各フォルダの README を参照。共通の手順は `AGENTS.md` に記載。

## 参考

詳細な比較・調査結果は `memo.txt` を参照。
```

- [ ] **Step 5: コミット**

```bash
git add experiments/graphrag/AGENTS.md experiments/graphrag/README.md experiments/graphrag/.gitignore
git commit -m "feat: add graphrag experiment base structure"
```

---

## Task 2: 共通サンプルデータ

**Files:**
- Create: `experiments/graphrag/surrealdb/data/sample.json`
- Create: `experiments/graphrag/neo4j/data/sample.json`
- Create: `experiments/graphrag/edgedb/data/sample.json`

3つの環境で同一のデータを使う。

- [ ] **Step 1: sample.json を3箇所に作成**

`experiments/graphrag/surrealdb/data/sample.json`（および `neo4j/data/sample.json`, `edgedb/data/sample.json`）の内容:

```json
{
  "nodes": [
    {
      "id": "graphrag",
      "label": "GraphRAG",
      "content": "GraphRAGはグラフ構造を活用したRAG手法で、ドキュメント間の関係をグラフとして保持し、ベクトル検索とグラフトラバースを組み合わせて回答精度を向上させる技術。"
    },
    {
      "id": "rag",
      "label": "RAG",
      "content": "RAG（Retrieval-Augmented Generation）は、LLMの回答生成時に外部ドキュメントを検索して取得し、コンテキストとして付与することで事実に基づいた回答を可能にする手法。"
    },
    {
      "id": "vector_search",
      "label": "ベクトル検索",
      "content": "テキストを高次元ベクトルに変換し、コサイン類似度などの指標でクエリと意味的に近いドキュメントを高速に検索する技術。HNSWなどの近似最近傍アルゴリズムが使われる。"
    },
    {
      "id": "graph_db",
      "label": "グラフDB",
      "content": "データをノードとエッジで表現するデータベース。複雑な関係の探索や多段階トラバースが得意で、Neo4j、SurrealDB、EdgeDBなどが代表的な製品。"
    },
    {
      "id": "llm",
      "label": "LLM",
      "content": "大規模言語モデル（Large Language Model）は大量のテキストデータで学習した自然言語処理モデル。GPT、Llama、Gemmaなどが代表的で、テキスト生成・要約・翻訳などに活用される。"
    },
    {
      "id": "embedding",
      "label": "埋め込みモデル",
      "content": "テキストを固定長の高次元ベクトルに変換するモデル。意味的に近いテキストは近いベクトルになる。nomic-embed-text、text-embedding-3-smallなどが代表的。"
    }
  ],
  "edges": [
    {"from": "graphrag", "to": "rag",           "relation": "EXTENDS"},
    {"from": "graphrag", "to": "graph_db",       "relation": "USES"},
    {"from": "graphrag", "to": "vector_search",  "relation": "USES"},
    {"from": "rag",      "to": "llm",            "relation": "USES"},
    {"from": "rag",      "to": "vector_search",  "relation": "USES"},
    {"from": "vector_search", "to": "embedding", "relation": "REQUIRES"}
  ],
  "query": "GraphRAGとは何か？どのような技術を使うか説明してください。"
}
```

- [ ] **Step 2: コミット**

```bash
git add experiments/graphrag/surrealdb/data/ experiments/graphrag/neo4j/data/ experiments/graphrag/edgedb/data/
git commit -m "feat: add shared sample data for graphrag experiments"
```

---

## Task 3: SurrealDB 環境

**Files:**
- Create: `experiments/graphrag/surrealdb/Dockerfile`
- Create: `experiments/graphrag/surrealdb/docker-compose.yml`
- Create: `experiments/graphrag/surrealdb/.env.example`
- Create: `experiments/graphrag/surrealdb/requirements.txt`
- Create: `experiments/graphrag/surrealdb/src/run.py`

### SurrealDB 技術メモ

- HTTP REST API: `POST /sql` にSQLを送信（Content-Type: text/plain）
- ベクトルインデックス: `DEFINE INDEX idx ON TABLE t COLUMNS col HNSW DIMENSION {n} DIST COSINE;`
- KNN検索: `SELECT *, vector::similarity::cosine(embedding, $vec) AS score FROM t WHERE embedding <|K,COSINE|> $vec`
- グラフエッジ: `RELATE source:id->edge_name->target:id`
- グラフトラバース: `SELECT ->edge_name->target.* FROM source:id`

- [ ] **Step 1: Dockerfile を作成**

`experiments/graphrag/surrealdb/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY data/ ./data/
```

- [ ] **Step 2: requirements.txt を作成**

`experiments/graphrag/surrealdb/requirements.txt`:

```
httpx==0.27.2
```

- [ ] **Step 3: docker-compose.yml を作成**

`experiments/graphrag/surrealdb/docker-compose.yml`:

```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:latest
    command: start --log trace --user root --pass root memory
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8000/health || exit 1"]
      interval: 5s
      timeout: 5s
      retries: 10

  python:
    build: .
    depends_on:
      surrealdb:
        condition: service_healthy
    env_file:
      - .env
    environment:
      - SURREAL_URL=http://surrealdb:8000
      - SURREAL_USER=root
      - SURREAL_PASS=root
      - SURREAL_NS=graphrag_ns
      - SURREAL_DB=graphrag_db
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

- [ ] **Step 4: .env.example を作成**

`experiments/graphrag/surrealdb/.env.example`:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2
```

- [ ] **Step 5: src/run.py を作成**

`experiments/graphrag/surrealdb/src/run.py`:

```python
"""SurrealDB を使った GraphRAG パイプラインの PoC。"""

import json
import os
import sys
from pathlib import Path

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

SURREAL_URL = os.getenv("SURREAL_URL", "http://localhost:8000")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS = os.getenv("SURREAL_NS", "graphrag_ns")
SURREAL_DB = os.getenv("SURREAL_DB", "graphrag_db")

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def embed(text: str) -> list[float]:
    """Ollama でテキストを埋め込みベクトルに変換する。"""
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def generate(context: str, question: str) -> str:
    """Ollama でコンテキストを元に質問に回答する。"""
    prompt = (
        "以下の情報を参考に質問に答えてください。\n\n"
        f"コンテキスト:\n{context}\n\n"
        f"質問: {question}\n\n回答:"
    )
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def surreal_query(sql: str) -> list:
    """SurrealDB HTTP API に SQL を送信して結果を返す。"""
    resp = httpx.post(
        f"{SURREAL_URL}/sql",
        content=sql,
        headers={
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "NS": SURREAL_NS,
            "DB": SURREAL_DB,
        },
        auth=(SURREAL_USER, SURREAL_PASS),
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def setup_schema(dims: int) -> None:
    """テーブル定義とベクトルインデックスを作成する。"""
    surreal_query(f"""
        DEFINE TABLE concept SCHEMALESS;
        DEFINE FIELD node_id   ON concept TYPE string;
        DEFINE FIELD label     ON concept TYPE string;
        DEFINE FIELD content   ON concept TYPE string;
        DEFINE FIELD embedding ON concept TYPE array;
        DEFINE INDEX idx_embedding ON TABLE concept COLUMNS embedding
            HNSW DIMENSION {dims} DIST COSINE;
    """)


def insert_nodes(nodes: list[dict]) -> None:
    """ノードを埋め込みと共に SurrealDB に挿入する。"""
    for node in nodes:
        vec = embed(node["content"])
        vec_str = json.dumps(vec)
        surreal_query(f"""
            CREATE concept:{node['id']} SET
                node_id   = '{node['id']}',
                label     = '{node['label']}',
                content   = '{node['content']}',
                embedding = {vec_str};
        """)
        print(f"  ✓ ノード挿入: {node['label']}")


def insert_edges(edges: list[dict]) -> None:
    """エッジ（グラフ関係）を SurrealDB に挿入する。"""
    for edge in edges:
        surreal_query(f"""
            RELATE concept:{edge['from']}->has_relation->concept:{edge['to']}
                SET relation = '{edge['relation']}';
        """)
        print(f"  ✓ エッジ挿入: {edge['from']} --[{edge['relation']}]--> {edge['to']}")


def vector_search(query_vec: list[float], top_k: int = 3) -> list[dict]:
    """ベクトル類似度検索で上位ノードを取得する。"""
    vec_str = json.dumps(query_vec)
    result = surreal_query(f"""
        SELECT node_id, label, content
        FROM concept
        WHERE embedding <|{top_k},COSINE|> {vec_str};
    """)
    return result[0].get("result", [])


def graph_traverse(node_ids: list[str]) -> list[dict]:
    """指定ノードからグラフを1ホップ走査して関連ノードを取得する。"""
    related = []
    for nid in node_ids:
        result = surreal_query(f"""
            SELECT ->has_relation->concept.* AS related
            FROM concept:{nid};
        """)
        for row in result[0].get("result", []):
            for r in row.get("related", []):
                if r:
                    related.append(r)
    return related


def main() -> None:
    """GraphRAG パイプラインを実行する。"""
    print("=== SurrealDB GraphRAG PoC ===\n")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    # 埋め込み次元を検出
    print("[1/5] 埋め込み次元を検出中...")
    probe_vec = embed("test")
    dims = len(probe_vec)
    print(f"  埋め込み次元: {dims}\n")

    # スキーマ設定
    print("[2/5] スキーマを設定中...")
    setup_schema(dims)
    print("  ✓ スキーマ設定完了\n")

    # ノード挿入
    print("[3/5] ノードを挿入中...")
    insert_nodes(data["nodes"])
    print()

    # エッジ挿入
    print("[4/5] エッジを挿入中...")
    insert_edges(data["edges"])
    print()

    # クエリ実行
    question = data["query"]
    print(f"[5/5] クエリ実行: {question}\n")

    query_vec = embed(question)
    vector_hits = vector_search(query_vec, top_k=3)
    print(f"  ベクトル検索ヒット: {[h['label'] for h in vector_hits]}")

    graph_hits = graph_traverse([h["node_id"] for h in vector_hits])
    print(f"  グラフ展開ヒット: {[h.get('label', '?') for h in graph_hits]}\n")

    all_nodes = vector_hits + graph_hits
    seen = set()
    unique_nodes = []
    for n in all_nodes:
        if n.get("node_id") and n["node_id"] not in seen:
            seen.add(n["node_id"])
            unique_nodes.append(n)

    context = "\n".join(f"- {n['label']}: {n['content']}" for n in unique_nodes)
    answer = generate(context, question)

    print("=== 回答 ===")
    print(answer)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: DBコンテナが起動することを確認**

```bash
cd experiments/graphrag/surrealdb
cp .env.example .env
docker compose up -d surrealdb
docker compose ps
```

Expected: `surrealdb` が `healthy` になる

- [ ] **Step 7: スクリプトを実行して動作確認**

```bash
docker compose run --rm python python src/run.py
```

Expected: 最後に `=== 回答 ===` と回答テキストが出力される

- [ ] **Step 8: 後片付けしてコミット**

```bash
docker compose down -v
cd ../../..
git add experiments/graphrag/surrealdb/
git commit -m "feat: add SurrealDB GraphRAG PoC environment"
```

---

## Task 4: Neo4j 環境

**Files:**
- Create: `experiments/graphrag/neo4j/Dockerfile`
- Create: `experiments/graphrag/neo4j/docker-compose.yml`
- Create: `experiments/graphrag/neo4j/.env.example`
- Create: `experiments/graphrag/neo4j/requirements.txt`
- Create: `experiments/graphrag/neo4j/src/run.py`

### Neo4j 技術メモ

- Pythonドライバ: `neo4j` パッケージ（`GraphDatabase.driver(uri, auth=(user, pass))`）
- ベクトルインデックス（Neo4j 5.x）:
  ```cypher
  CREATE VECTOR INDEX concept_embedding IF NOT EXISTS
  FOR (n:Concept) ON (n.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}}
  ```
- KNN検索:
  ```cypher
  CALL db.index.vector.queryNodes('concept_embedding', 3, $vec)
  YIELD node, score RETURN node, score
  ```
- グラフ走査:
  ```cypher
  MATCH (n:Concept {node_id: $id})-[:HAS_RELATION]->(r:Concept)
  RETURN r
  ```

- [ ] **Step 1: Dockerfile を作成**

`experiments/graphrag/neo4j/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY data/ ./data/
```

- [ ] **Step 2: requirements.txt を作成**

`experiments/graphrag/neo4j/requirements.txt`:

```
httpx==0.27.2
neo4j==5.25.0
```

- [ ] **Step 3: docker-compose.yml を作成**

`experiments/graphrag/neo4j/docker-compose.yml`:

```yaml
services:
  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/testpassword
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"
      - "7687:7687"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 10

  python:
    build: .
    depends_on:
      neo4j:
        condition: service_healthy
    env_file:
      - .env
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASS=testpassword
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

- [ ] **Step 4: .env.example を作成**

`experiments/graphrag/neo4j/.env.example`:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2
```

- [ ] **Step 5: src/run.py を作成**

`experiments/graphrag/neo4j/src/run.py`:

```python
"""Neo4j を使った GraphRAG パイプラインの PoC。"""

import json
import os
from pathlib import Path

import httpx
from neo4j import GraphDatabase

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "testpassword")

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def embed(text: str) -> list[float]:
    """Ollama でテキストを埋め込みベクトルに変換する。"""
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def generate(context: str, question: str) -> str:
    """Ollama でコンテキストを元に質問に回答する。"""
    prompt = (
        "以下の情報を参考に質問に答えてください。\n\n"
        f"コンテキスト:\n{context}\n\n"
        f"質問: {question}\n\n回答:"
    )
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def setup_schema(driver: GraphDatabase, dims: int) -> None:
    """制約とベクトルインデックスを作成する。"""
    with driver.session() as session:
        session.run(
            "CREATE CONSTRAINT concept_node_id IF NOT EXISTS "
            "FOR (n:Concept) REQUIRE n.node_id IS UNIQUE"
        )
        session.run(
            f"CREATE VECTOR INDEX concept_embedding IF NOT EXISTS "
            f"FOR (n:Concept) ON (n.embedding) "
            f"OPTIONS {{indexConfig: {{`vector.dimensions`: {dims}, "
            f"`vector.similarity_function`: 'cosine'}}}}"
        )


def insert_nodes(driver: GraphDatabase, nodes: list[dict]) -> None:
    """ノードを埋め込みと共に Neo4j に挿入する。"""
    with driver.session() as session:
        for node in nodes:
            vec = embed(node["content"])
            session.run(
                "MERGE (n:Concept {node_id: $node_id}) "
                "SET n.label = $label, n.content = $content, n.embedding = $embedding",
                node_id=node["id"],
                label=node["label"],
                content=node["content"],
                embedding=vec,
            )
            print(f"  ✓ ノード挿入: {node['label']}")


def insert_edges(driver: GraphDatabase, edges: list[dict]) -> None:
    """エッジ（グラフ関係）を Neo4j に挿入する。"""
    with driver.session() as session:
        for edge in edges:
            session.run(
                "MATCH (a:Concept {node_id: $from_id}), (b:Concept {node_id: $to_id}) "
                "MERGE (a)-[:HAS_RELATION {relation: $relation}]->(b)",
                from_id=edge["from"],
                to_id=edge["to"],
                relation=edge["relation"],
            )
            print(f"  ✓ エッジ挿入: {edge['from']} --[{edge['relation']}]--> {edge['to']}")


def vector_search(driver: GraphDatabase, query_vec: list[float], top_k: int = 3) -> list[dict]:
    """ベクトルインデックスで類似ノードを取得する。"""
    with driver.session() as session:
        result = session.run(
            "CALL db.index.vector.queryNodes('concept_embedding', $k, $vec) "
            "YIELD node, score "
            "RETURN node.node_id AS node_id, node.label AS label, "
            "node.content AS content, score",
            k=top_k,
            vec=query_vec,
        )
        return [dict(r) for r in result]


def graph_traverse(driver: GraphDatabase, node_ids: list[str]) -> list[dict]:
    """指定ノードからグラフを1ホップ走査して関連ノードを取得する。"""
    related = []
    with driver.session() as session:
        for nid in node_ids:
            result = session.run(
                "MATCH (n:Concept {node_id: $id})-[:HAS_RELATION]->(r:Concept) "
                "RETURN r.node_id AS node_id, r.label AS label, r.content AS content",
                id=nid,
            )
            related.extend([dict(r) for r in result])
    return related


def main() -> None:
    """GraphRAG パイプラインを実行する。"""
    print("=== Neo4j GraphRAG PoC ===\n")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    try:
        # 埋め込み次元を検出
        print("[1/5] 埋め込み次元を検出中...")
        probe_vec = embed("test")
        dims = len(probe_vec)
        print(f"  埋め込み次元: {dims}\n")

        # スキーマ設定
        print("[2/5] スキーマを設定中...")
        setup_schema(driver, dims)
        print("  ✓ スキーマ設定完了\n")

        # ノード挿入
        print("[3/5] ノードを挿入中...")
        insert_nodes(driver, data["nodes"])
        print()

        # エッジ挿入
        print("[4/5] エッジを挿入中...")
        insert_edges(driver, data["edges"])
        print()

        # クエリ実行
        question = data["query"]
        print(f"[5/5] クエリ実行: {question}\n")

        query_vec = embed(question)
        vector_hits = vector_search(driver, query_vec, top_k=3)
        print(f"  ベクトル検索ヒット: {[h['label'] for h in vector_hits]}")

        graph_hits = graph_traverse(driver, [h["node_id"] for h in vector_hits])
        print(f"  グラフ展開ヒット: {[h.get('label', '?') for h in graph_hits]}\n")

        all_nodes = vector_hits + graph_hits
        seen = set()
        unique_nodes = []
        for n in all_nodes:
            if n.get("node_id") and n["node_id"] not in seen:
                seen.add(n["node_id"])
                unique_nodes.append(n)

        context = "\n".join(f"- {n['label']}: {n['content']}" for n in unique_nodes)
        answer = generate(context, question)

        print("=== 回答 ===")
        print(answer)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: DBコンテナが起動することを確認**

```bash
cd experiments/graphrag/neo4j
cp .env.example .env
docker compose up -d neo4j
docker compose ps
```

Expected: `neo4j` が `healthy` になる（初回は30秒程度かかる）

- [ ] **Step 7: スクリプトを実行して動作確認**

```bash
docker compose run --rm python python src/run.py
```

Expected: 最後に `=== 回答 ===` と回答テキストが出力される

- [ ] **Step 8: 後片付けしてコミット**

```bash
docker compose down -v
cd ../../..
git add experiments/graphrag/neo4j/
git commit -m "feat: add Neo4j GraphRAG PoC environment"
```

---

## Task 5: EdgeDB 環境

**Files:**
- Create: `experiments/graphrag/edgedb/Dockerfile`
- Create: `experiments/graphrag/edgedb/docker-compose.yml`
- Create: `experiments/graphrag/edgedb/.env.example`
- Create: `experiments/graphrag/edgedb/requirements.txt`
- Create: `experiments/graphrag/edgedb/dbschema/default.esdl`
- Create: `experiments/graphrag/edgedb/src/run.py`

### EdgeDB 技術メモ

- EdgeDB を `--devmode` で起動することで、Pythonクライアントから DDL（`CREATE TYPE` など）を直接実行できる
- ベクトル検索は組み込みサポートなし（`ext::ai` は OpenAI 依存）のため、全埋め込みを Python 側に取得しコサイン類似度を計算
- EdgeDB Python クライアント接続: `edgedb.create_client(dsn="edgedb://edgedb@edgedb:5656/edgedb?tls_security=insecure")`
- EdgeQL でリンクを経由した関連ノード取得: `SELECT Concept { related_concepts: { label, content } } FILTER .node_id = <str>$id`

- [ ] **Step 1: dbschema/default.esdl を作成**

`experiments/graphrag/edgedb/dbschema/default.esdl`:

```sdl
module default {
    type Concept {
        required node_id: str {
            constraint exclusive;
        };
        required label: str;
        required content: str;
        embedding: array<float64>;
        multi related_concepts: Concept;
    }
}
```

- [ ] **Step 2: Dockerfile を作成**

`experiments/graphrag/edgedb/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.edgedb.com | sh -s -- --no-modify-path
ENV PATH="/root/.edgedb/bin:${PATH}"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY data/ ./data/
COPY dbschema/ ./dbschema/
```

- [ ] **Step 3: requirements.txt を作成**

`experiments/graphrag/edgedb/requirements.txt`:

```
httpx==0.27.2
edgedb==2.1.0
numpy==2.1.3
```

- [ ] **Step 4: docker-compose.yml を作成**

`experiments/graphrag/edgedb/docker-compose.yml`:

```yaml
services:
  edgedb:
    image: edgedb/edgedb:5
    environment:
      EDGEDB_SERVER_SECURITY: insecure_dev_mode
      EDGEDB_SERVER_EXTRA_ARGS: --devmode
    ports:
      - "5656:5656"
    volumes:
      - edgedb_data:/var/lib/edgedb/data
    healthcheck:
      test: ["CMD", "edgedb", "--host", "localhost", "--port", "5656",
             "--tls-security", "insecure", "query", "SELECT 1"]
      interval: 10s
      timeout: 5s
      retries: 15

  python:
    build: .
    depends_on:
      edgedb:
        condition: service_healthy
    env_file:
      - .env
    environment:
      - EDGEDB_DSN=edgedb://edgedb@edgedb:5656/edgedb?tls_security=insecure
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  edgedb_data:
```

- [ ] **Step 5: .env.example を作成**

`experiments/graphrag/edgedb/.env.example`:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2
```

- [ ] **Step 6: src/run.py を作成**

`experiments/graphrag/edgedb/src/run.py`:

```python
"""EdgeDB を使った GraphRAG パイプラインの PoC。"""

import json
import os
from pathlib import Path

import httpx
import numpy as np
import edgedb

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

EDGEDB_DSN = os.getenv(
    "EDGEDB_DSN",
    "edgedb://edgedb@localhost:5656/edgedb?tls_security=insecure",
)

DATA_PATH = Path(__file__).parent.parent / "data" / "sample.json"


def embed(text: str) -> list[float]:
    """Ollama でテキストを埋め込みベクトルに変換する。"""
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def generate(context: str, question: str) -> str:
    """Ollama でコンテキストを元に質問に回答する。"""
    prompt = (
        "以下の情報を参考に質問に答えてください。\n\n"
        f"コンテキスト:\n{context}\n\n"
        f"質問: {question}\n\n回答:"
    )
    resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """2つのベクトルのコサイン類似度を計算する。"""
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


def setup_schema(client: edgedb.Client) -> None:
    """EdgeDB にスキーマを作成する（devmode では DDL を直接実行可能）。"""
    client.execute("""
        CREATE TYPE IF NOT EXISTS default::Concept {
            CREATE REQUIRED PROPERTY node_id -> str {
                CREATE CONSTRAINT exclusive;
            };
            CREATE REQUIRED PROPERTY label -> str;
            CREATE REQUIRED PROPERTY content -> str;
            CREATE PROPERTY embedding -> array<float64>;
            CREATE MULTI LINK related_concepts -> default::Concept;
        };
    """)


def insert_nodes(client: edgedb.Client, nodes: list[dict]) -> None:
    """ノードを埋め込みと共に EdgeDB に挿入する。"""
    for node in nodes:
        vec = embed(node["content"])
        client.query(
            """
            INSERT default::Concept {
                node_id := <str>$node_id,
                label   := <str>$label,
                content := <str>$content,
                embedding := <array<float64>>$embedding,
            } UNLESS CONFLICT ON .node_id;
            """,
            node_id=node["id"],
            label=node["label"],
            content=node["content"],
            embedding=vec,
        )
        print(f"  ✓ ノード挿入: {node['label']}")


def insert_edges(client: edgedb.Client, edges: list[dict]) -> None:
    """エッジ（グラフ関係）を EdgeDB のリンクとして挿入する。"""
    for edge in edges:
        client.query(
            """
            UPDATE default::Concept
            FILTER .node_id = <str>$from_id
            SET {
                related_concepts += (
                    SELECT default::Concept FILTER .node_id = <str>$to_id
                )
            };
            """,
            from_id=edge["from"],
            to_id=edge["to"],
        )
        print(f"  ✓ エッジ挿入: {edge['from']} --[{edge['relation']}]--> {edge['to']}")


def vector_search(
    client: edgedb.Client, query_vec: list[float], top_k: int = 3
) -> list[dict]:
    """全ノードの埋め込みを取得し、Python でコサイン類似度を計算してソートする。"""
    all_nodes = client.query(
        "SELECT default::Concept { node_id, label, content, embedding }"
    )
    scored = [
        {
            "node_id": n.node_id,
            "label": n.label,
            "content": n.content,
            "score": cosine_similarity(query_vec, list(n.embedding)),
        }
        for n in all_nodes
        if n.embedding
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def graph_traverse(client: edgedb.Client, node_ids: list[str]) -> list[dict]:
    """指定ノードのリンク先（related_concepts）を取得する。"""
    related = []
    for nid in node_ids:
        result = client.query(
            """
            SELECT default::Concept {
                related_concepts: { node_id, label, content }
            }
            FILTER .node_id = <str>$id
            """,
            id=nid,
        )
        for row in result:
            for r in row.related_concepts:
                related.append({
                    "node_id": r.node_id,
                    "label": r.label,
                    "content": r.content,
                })
    return related


def main() -> None:
    """GraphRAG パイプラインを実行する。"""
    print("=== EdgeDB GraphRAG PoC ===\n")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    client = edgedb.create_client(dsn=EDGEDB_DSN)

    # 埋め込み次元を検出
    print("[1/5] 埋め込み次元を検出中...")
    probe_vec = embed("test")
    dims = len(probe_vec)
    print(f"  埋め込み次元: {dims}\n")

    # スキーマ設定
    print("[2/5] スキーマを設定中...")
    setup_schema(client)
    print("  ✓ スキーマ設定完了\n")

    # ノード挿入
    print("[3/5] ノードを挿入中...")
    insert_nodes(client, data["nodes"])
    print()

    # エッジ挿入
    print("[4/5] エッジを挿入中...")
    insert_edges(client, data["edges"])
    print()

    # クエリ実行
    question = data["query"]
    print(f"[5/5] クエリ実行: {question}\n")

    query_vec = embed(question)
    vector_hits = vector_search(client, query_vec, top_k=3)
    print(f"  ベクトル検索ヒット: {[h['label'] for h in vector_hits]}")

    graph_hits = graph_traverse(client, [h["node_id"] for h in vector_hits])
    print(f"  グラフ展開ヒット: {[h.get('label', '?') for h in graph_hits]}\n")

    all_nodes = vector_hits + graph_hits
    seen = set()
    unique_nodes = []
    for n in all_nodes:
        if n.get("node_id") and n["node_id"] not in seen:
            seen.add(n["node_id"])
            unique_nodes.append(n)

    context = "\n".join(f"- {n['label']}: {n['content']}" for n in unique_nodes)
    answer = generate(context, question)

    print("=== 回答 ===")
    print(answer)

    client.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: DBコンテナが起動することを確認**

```bash
cd experiments/graphrag/edgedb
cp .env.example .env
docker compose up -d edgedb
docker compose ps
```

Expected: `edgedb` が `healthy` になる（初回は30秒程度かかる）

- [ ] **Step 8: スクリプトを実行して動作確認**

```bash
docker compose run --rm python python src/run.py
```

Expected: 最後に `=== 回答 ===` と回答テキストが出力される

- [ ] **Step 9: 後片付けしてコミット**

```bash
docker compose down -v
cd ../../..
git add experiments/graphrag/edgedb/
git commit -m "feat: add EdgeDB GraphRAG PoC environment"
```

---

## 実行順序のまとめ

各環境を試す際の手順:

```bash
# SurrealDB
cd experiments/graphrag/surrealdb
cp .env.example .env  # 必要に応じてモデル名を編集
docker compose up -d surrealdb
docker compose run --rm python python src/run.py
docker compose down -v

# Neo4j
cd experiments/graphrag/neo4j
cp .env.example .env
docker compose up -d neo4j
docker compose run --rm python python src/run.py
docker compose down -v

# EdgeDB
cd experiments/graphrag/edgedb
cp .env.example .env
docker compose up -d edgedb
docker compose run --rm python python src/run.py
docker compose down -v
```

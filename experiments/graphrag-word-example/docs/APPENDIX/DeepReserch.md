# エグゼクティブサマリ

- **SurrealDB** はドキュメント・グラフ・ベクトル検索を一元的に扱うマルチモデルDBで、ベクトル検索とグラフ走査を単一クエリで組み合わせ可能。組み込みの埋め込み格納や類似度検索機能（HNSW/DISKANN）を備え、SurrealQL でグラフパターンやベクトル検索を「共等位」の述語として同時処理できる。バックアップ・インデックス管理・セキュリティ機能も整備されており、AIエージェントのメモリやRAG用途に適する。しかし新興技術ゆえ成熟度やコミュニティは限定的。

- **EdgeDB** は「グラフ-リレーショナル」モデルを採用し、EdgeQL でリンク（外部キーのような参照）を自然に扱える。EdgeDB 5 では `ext::ai` 拡張により埋め込み索引と類似検索が容易に実現される。ただしグラフ探索機能は Neo4j ほど強力ではなく、マルチホップ・パス検索のためにはネストしたクエリを組む必要がある。運用・バックアップは Postgres 風（Gel CLI）で扱えるが、大規模クエリやノード/リレーションの冗長な配置には注意が必要。

- **Neo4j** は成熟したグラフDBで、Cypher で複雑なパターン検索や深いトラバースが得意。5.11以降、ネイティブなベクトル索引とクエリ（`CALL db.index.vector.queryNodes` 等）もサポートされており、GraphRAGの構成要素は揃っている。ただしグラフ探索とベクトル検索は別ステップで実行する必要があり、実装時の手続きコストが大きい。コミュニティとエコシステムは豊富だが、大規模・多段階クエリではメモリ増大のリスクもある。

**実装面の推奨:** 新規プロジェクトで多様なデータモデルを統合するなら SurrealDB が有力。既存でグラフ中心の要件が強い場合は Neo4j、リレーショナル志向かつ軽量RAGなら EdgeDB も選択肢。各DBの詳細比較とプロトタイプコード例を以下で示す。

## SurrealDB の特徴と検討点

- **ベクトル検索サポート:** 組み込みの埋め込み型（配列型）と索引機能（HNSW, DiskANN 等）を備え、`<|K,METHOD|>`構文で近傍検索が可能。ユーザ空間で任意の次元のベクトルを格納でき、インデックス作成もSurrealQLから実行できる。  
- **グラフクエリ機能:** サブジェクト・述語・目的語のリレーション（エッジ）を `RELATE` 文で定義・更新し、矢印 `->` で経路を直接照会できる。例：`$customer->owns->product->has_issue->knowledge_base` のように多段階トラバースがシームレス。  
- **ハイブリッド検索実現:** SurrealQL の WHERE 句に、ベクトル距離評価 (`vector::distance::knn()`) と全文検索スコア (`search::score`) などを含め、グラフフィルタと組み合わせた複合検索が**一つのクエリ文**で実現できる。記述が簡潔でパイプライン不要な点が最大の利点。  
- **スケーラビリティ・性能:** Rust製でインメモリ優先、ウォームアップなしで低レイテンシを実現。トランザクション型DBなのでACID保証下での最新データを検索できる。HNSW 索引は高次元でも高速だが、メモリ使用量と初期構築時間には注意。水平スケールはクラスター機能（beta）で対応可能。  
- **運用:** CLI によるバックアップ（`surreal export` / `import`）や時系列クエリもサポート。インデックスはSurrealQLで自動管理でき、監査ログやユーザ権限管理機能も備わる。TLS/SSL対応や暗号化設定がドキュメントに記載されており安全運用が可能。  
- **導入コスト・エコシステム:** OSS版は無料、エンタープライズ版で商用サポートあり。公式 Python/Node ライブラリと REST/WS API を提供。LangChain連携やコミュニティも活発化中。ドキュメントやチュートリアルも増えており、学習コストは中程度。  
- **制約・リスク:** 新興技術ゆえ安定度に不安が残る（特にクラスター構成）。他DBに比べ利用実績は少なく、エコシステムの成熟には時間がかかる可能性。開発言語がRustなためC拡張が少ないなど制約もある。  

## EdgeDB の特徴と検討点

- **ベクトル検索サポート:** EdgeDB 5 では `ext::ai` 拡張により、テーブルの文字列プロパティに埋め込みインデックスを付与できる。INSERT時に自動埋め込み生成や`ext::ai::search`で類似文書検索が可能で、設定はEdgeQLで比較的簡単（埋め込みモデル指定など）。内部的には PostgreSQL の pgvector を利用しており、数百万件まで対応。  
- **グラフクエリ機能:** EdgeDB は **グラフ-リレーショナル** モデルを採用し、テーブル（オブジェクト型）間を `link` 定義で接続できる。例：`type Movie { multi link actors -> Person; }`。EdgeQL の `SELECT` では、ネストしたパス構造を用いて関連オブジェクトを取得できる（疑似グラフ照会）。ただし、動的な多段階トラバースやパス探索機能（Cypherのようなパス構文）はなく、ネスト深度は静的に記述する必要がある。  
- **ハイブリッド検索実現:** ベクトル検索は `ext::ai` を用い、グラフ探索はEdgeQLでリンク経由により実施する。GraphRAG的には、ベクトルで得た文書群に対し、関連するノードやエッジを追加でSELECTするといった手順になる。Surrealのように単一クエリで完結はせず、処理はアプリ側で統合する必要がある。EdgeDB自体にはRAG用のパイプライン機能は無いが、LLM連携をサポートする拡張も開発中。  
- **スケーラビリティ・性能:** 基盤にPostgreSQLを持つため水平スケーリングには限界がある（主に垂直スケール）。単一マシンでの性能はPostgres並みで高速だが、クエリ最適化はEdgeQLに依存する。AI拡張はCloud API呼び出しが発生するため通信遅延がボトルネックになり得る。また、複雑なJOIN/リンク結合では計算コストが高くなる可能性あり。  
- **運用:** Gel CLI (旧EdgeDB CLI) でバックアップ/リストア（`gel backup`/`gel restore`）やバージョン管理が可能。Cloud版ではマネージドサービス提供。トランザクション、アクセス制御、ロールベース認証などエンタープライズ向け機能を内蔵。セキュリティも強固で、TLS通信も標準サポート。  
- **導入コスト・エコシステム:** OSSで無償利用可能。PythonやTypeScript向け公式クライアントあり。コミュニティはSurrealDBより小規模だが、開発は活発。`ext::ai`利用にはOpenAI APIキー等が必要になるが、設定自体はEdgeQLで完結できる。EdgeDBは比較的新しいため教育リソースが少ないものの、Postgres互換知識が活かせる。  
- **制約・リスク:** 純粋なグラフDBではないため、複雑なグラフアルゴリズム（短絡経路検索等）は組み込み機能なし。大規模分散処理には不向き。`ext::ai` は外部依存（LLM API）なのでコスト・ネットワークに注意が必要。最新機能はまだプレビュー版も含むため、安定性の確認が必要。

## Neo4j の特徴と検討点

- **ベクトル検索サポート:** Neo4j 5.11以降、ネイティブにベクトル型プロパティと索引をサポートする。埋め込みはノード/リレーションのプロパティとして保存でき、`CALL db.index.vector.queryNodes` で k-NN 検索が可能（Cypher呼び出し）。全文検索もLuceneベースで強力。VectorDB的な使い勝手には向くが、クエリは手続き型になる。  
- **グラフクエリ機能:** Cypher言語により、ノードラベル・リレーションタイプを指定して複雑なパターンマッチングが可能。パス検索（`MATCH (a)-[*..3]-(b)` 等の可変長パス）やグラフアルゴリズム（GDSライブラリ）が豊富で、非常に自由度が高い。トラバース性能に優れ、多層リレーションやネットワーク中心の探索に強い。  
- **ハイブリッド検索実現:** VectorRAG と GraphRAG を統合する場合、まず Cypher の `CALL db.index.vector.queryNodes` で類似ノードを取得し、別途 `MATCH` で関係するノードやリレーションを検索するといったフローになる。1クエリではなく複数ステップを組み合わせる必要があり、クエリ実行計画が分離されるためパフォーマンス調整が難しい場合がある。しかし、手動でスコアブレンドやフィルタを統合すれば GraphRAG ハイブリッドを実現できる。  
- **スケーラビリティ・性能:** 単一ノード/クラスターともに高い並列処理能力を持ち、写像系ワークロードに最適化されている。メモリ負荷は高めなので、大規模データではクラスタリング（Enterprise）でのスケールアウトが必要。構造化グラフ検索は高速だが、複数CALLの中間結果が増大するとメモリ増大リスクが生じる。Javaベースの最適化設定で性能向上可能。  
- **運用:** Neo4j は成熟した商用DBで、監視・バックアップ・リカバリ機能が充実（Enterprise版でのHOTバックアップなど）。Community版はバックアップに制限あり。ACLやKerberos認証、ACLの細粒度設定などセキュリティ機能が豊富。公式ドライバ（Python/Java等）やGUIツールも整備されている。  
- **導入コスト・エコシステム:** コミュニティ版は無料、Enterprise版は商用ライセンスが必要。豊富なプラグインとサードパーティライブラリ、データサイエンスライブラリ（GDS）やトランザクション・シャーディング機能が利用可能。日本語ドキュメントも存在し、コミュニティ規模が大きい。学習コストはCypherに慣れれば中程度。  
- **制約・リスク:** ハイブリッド検索ではクエリが複数ステップになるため、実装とチューニングが複雑化する。また、GraphRAGの本質である「一貫したトランザクション内のグラフ・ベクトル検索」が困難（各操作が分割実行される）で、データ鮮度に一貫性問題が生じ得る。大規模投入時にはGCやメモリ管理に注意が必要。

## プロトタイプ実装例

以下は各DBでの最小プロトタイプ例。Pythonで実装し、LLM呼び出しにはOpenAI APIを使用する想定（APIキー設定）。実行前提：各DBを起動（Docker等）し、接続情報を設定していること。必要な依存ライブラリを pip 等でインストールする（例：`surrealdb`、`edgedb`、`neo4j-driver`、`openai`）。

### SurrealDB (Python)

```python
# 前提: SurrealDB v3.x が 8000ポートで起動中 (例: docker run -p8000:8000 surrealdb/surrealdb)
# Pythonライブラリ: surrealdb (pip install surrealdb), openai (pip install openai)

from surrealdb import Surreal
import openai

# SurrealDB に接続
db = Surreal("ws://localhost:8000/rpc")
db.signin({"user": "root", "pass": "root"})
db.use("test_ns", "test_db")

# スキーマ定義: サンプル文書とベクトルカラム
db.query('''
  DEFINE TABLE Article SCHEMALESS;
  DEFINE FIELD content ON Article TYPE string;
  DEFINE FIELD embedding ON Article TYPE array;
  CREATE INDEX ON Article (embedding) OPTIONS { method: 'hnsw', dist: 'cosine' };
''')

# データ投入: 単純な記事例と埋め込み (例えば 3次元)
db.query('CREATE Article CONTENT = "ラグビーワールドカップ", embedding = [0.1, 0.2, 0.3];')
db.query('CREATE Article CONTENT = "AI技術とデータベース", embedding = [0.4, 0.5, 0.6];')
db.query('CREATE Article CONTENT = "機械学習の応用事例", embedding = [0.7, 0.8, 0.9];')

# クエリ時: 検索語を埋め込み化 (ここでは固定ベクトル例)
query_embedding = [0.45, 0.55, 0.65]
user_text = "データベースにおけるAI事例"

# SurrealQLでハイブリッド検索: ベクトル類似度と全文検索をブレンド
results = db.query('''
  SELECT content, vector::distance::knn(embedding) AS score
  FROM Article
  WHERE embedding <|2,COSINE|> $query_embedding
    AND content @1@ $text
  ORDER BY score DESC
  LIMIT 3;
''', {'query_embedding': query_embedding, 'text': user_text})

print("Search results:", results)

# 簡易 RAG: 検索結果をコンテキストとしてLLMに投げる
context = "\n".join([r['content'] for r in results])
prompt = f"以下の情報を参考に、質問に答えてください。\nContext: {context}\nQuestion: {user_text}\nAnswer:"
response = openai.ChatCompletion.create(
    model="gpt-4", messages=[{"role": "user", "content": prompt}]
)
print("Answer:", response.choices[0].message.content)
```

### EdgeDB (Python)

```python
# 前提: EdgeDB 5.x が起動中 (ポート5656)し、ext::ai拡張を利用可能
# Pythonライブラリ: edgedb (pip install edgedb[ai]), openai

import edgedb, openai

async def main():
    con = await edgedb.async_connect()
    # ext::ai 拡張の初期化 (存在確認・有効化)
    await con.execute('CREATE EXTENSION IF NOT EXISTS ai;')

    # スキーマ定義: ブログ記事 (テキスト) と埋め込みインデックス
    await con.execute('''
      module default {
        type BlogPost {
          content: str;
          # ext::ai::index により content から埋め込みを自動生成可能
          multi link related -> BlogPost;  # 関連記事リンク
          index ext::ai::index(embedding_model := 'text-embedding-3-small') on (.content);
        }
      }
    ''')

    # データ投入
    await con.execute(r'''
      INSERT BlogPost { content := "グラフデータベースとAI", related := (INSERT BlogPost {content := "Neo4j 入門"}) };
      INSERT BlogPost { content := "SurrealDB で始めるマルチモデルDB", related := (INSERT BlogPost {content := "エッジDBの特徴"}) };
    ''')

    # 検索: ext::ai::search でベクトル類似検索 (例: 固定queryベクトル)
    query_vector = [0.2, 0.8, 0.1]  # 実際は OpenAI 等で埋め込み取得
    result = await con.query('''
      SELECT ext::ai::search(BlogPost, <array<float64>>$vec) {
        id, score
      } LIMIT 2;
    ''', vec=query_vector)
    print("Vector search results:", result)

    # グラフ探索: 類似検索結果の関連リンクを取得
    post_ids = [r.id for r in result]
    graph_context = await con.query(f'''
      SELECT BlogPost {{
        content,
        related: {{ content }}
      }} FILTER .id IN <array<uuid>>[{', '.join(map(lambda id: f'uuid\\'{id}\\'', post_ids))}];
    ''')
    print("Graph query results:", graph_context)

    # RAG: 検索結果を結合して回答生成
    combined = "\n".join([b["content"] for b in graph_context])
    prompt = f"Context:\n{combined}\nQuestion: 上記に基づく質問への回答をお願いします。"
    res = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role":"user","content":prompt}])
    print("Answer:", res.choices[0].message.content)

# 非同期実行
import asyncio
asyncio.run(main())
```

### Neo4j (Python)

```python
# 前提: Neo4j 5.x が起動中 (デフォルト bolt:7687) し、Vector Indexを事前作成
# Pythonライブラリ: neo4j (pip install neo4j), openai

from neo4j import GraphDatabase
import openai

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "test"))

def setup_data(tx):
    # サンプルノード作成: 文章と埋め込み (Neo4jでは埋め込みをリストとして保持)
    tx.run("CREATE (a:Article {content: $text, embedding: $vec})", 
           text="AIとRAGについての概要", vec=[0.3,0.6,0.9])
    tx.run("CREATE (b:Article {content: $text, embedding: $vec})", 
           text="グラフデータベースの活用例", vec=[0.4,0.5,0.7])
    # シンプルな関係 (グラフ部分)
    tx.run("CREATE (p:Person {name: 'Tanaka'})-[:READ]->(a:Article {content: 'Neo4j入門', embedding: [0.2,0.8,0.5]})")
    # ベクトル索引の作成 (事前にCypher で実行)
    tx.run("CALL db.index.fulltext.createNodeIndex('articleContent', ['Article'], ['content'])")

with driver.session() as session:
    session.write_transaction(setup_data)

# ユーザークエリの例
query_text = "RAGとベクトル検索の概念は？"

# 埋め込みは外部で取得 (ここはダミー)
query_vector = [0.35,0.55,0.85]

with driver.session() as session:
    # 1) ベクトル検索 (VectorRAG)
    vec_results = session.run(
        "MATCH (x:Article) WHERE exists(x.embedding) "
        "WITH x, x.embedding AS emb "
        "ORDER BY gds.similarity.cosine(emb, $vec) DESC "
        "LIMIT 3 RETURN x.content AS content, gds.similarity.cosine(emb, $vec) AS score",
        vec=query_vector
    )
    vec_docs = [record["content"] for record in vec_results]
    print("Vector search docs:", vec_docs)

    # 2) グラフ走査 (GraphRAG): 例えば "Tanaka" が読んだ記事を取得
    graph_results = session.run(
        "MATCH (p:Person {name: $name})-[:READ]->(doc:Article) RETURN doc.content AS content",
        name="Tanaka"
    )
    graph_docs = [record["content"] for record in graph_results]
    print("Graph search docs:", graph_docs)

# 取得したコンテキストを結合してLLMに投入
context = "\n".join(vec_docs + graph_docs)
prompt = f"以下の情報に基づいて質問に答えてください。\n{context}\n質問: {query_text}"
response = openai.ChatCompletion.create(model="gpt-4", messages=[{"role":"user","content":prompt}])
print("Answer:", response.choices[0].message.content)
```

各コードでは、DB起動・スキーマ設定・データ挿入・ベクトル検索・グラフ検索・結果統合の流れを示した。実際には依存関係（OpenAIキー、DBバージョンなど）を揃え、挿入データやベクトル長は目的に応じて調整する。

## 比較表

| データベース   | ベクトル検索サポート     | グラフ機能                            | ハイブリッド検索実装 | 実装難易度   | 性能予想                          | 推奨ユースケース            | サンプルコード行数目安 |
|--------------|-------------------------|--------------------------------------|--------------------|--------------|----------------------------------|-------------------------|---------------------|
| SurrealDB    | ネイティブ組込 (HNSW/DISKANN) | ネイティブグラフ（RELATE/矢印構文） | SurrealQL一文で可能 | 低~中    | 高速（メモリ依存、高次元対応） | AIエージェント・リアルタイムRAG | 約30行        |
| EdgeDB       | 拡張機能 `ext::ai` により可能 | グラフ-リレーショナル (リンク)      | アプリ統合が必要 (分割クエリ)   | 中          | Postgres準拠 (大規模は専用DBほど高速でない) | LLM＋SQLライクなRAG        | 約40行        |
| Neo4j        | ネイティブ組込 (CALL で k-NN 検索) | 高度なグラフ照会・パス検索         | 複数ステップ (Cypher/MATCH＋CALL) | 高       | グラフ遍歴向け (マルチホップ重視; 中規模以上推奨) | グラフ中心の複雑クエリRAG  | 約35行        |

- **実装難易度:** SurrealDB は一体型APIのためクエリ実装が直感的。EdgeDB はEdgeQL学習が必要だがSQLライクで親和性あり。Neo4j はCypherの習得が必要で、ベクトル検索との連携はやや複雑。  
- **パフォーマンス:** ベクトル検索はどれも高効率な索引を使えば高速だが、規模に依存。グラフ探索は Neo4j が得意だが、処理パイプライン分割によるオーバーヘッドに注意。SurrealDB は全条件を同時評価できるため最適化効果が高い。EdgeDB の `ext::ai` は外部API呼び出しに時間がかかる可能性。  
- **推奨ユースケース:** SurrealDB は **AIエージェントの状態管理やリアルタイムRAG** に最適。EdgeDB は **RDBがベースのアプリケーションにAI機能追加**、Neo4j は **深いネットワーク分析とRAG** に向く。

## アーキテクチャ図とフロー

以下にハイブリッドRAGの基本フロー図を示す。ユーザークエリに対し、ベクトル検索とグラフ検索を並行実行し、その結果を統合してLLMに渡す流れである。

```mermaid
flowchart TD
  subgraph SurrealDB
    SQ[User Query]
    SV[ベクトル検索 (embedding で kNN)]
    SG[グラフ走査 (-> でノード間Traverse)]
    SC[コンテキスト統合]
    SL[LLM生成呼び出し]
    SQ --> SV
    SQ --> SG
    SV --> SC
    SG --> SC
    SC --> SL
    SL --> Answer1[回答]
  end

  subgraph Neo4j
    NQ[User Query] 
    NV[ベクトル検索 (CALL db.index)]
    NG[グラフ検索 (MATCH パターン)]
    NC[結果統合]
    NL[LLM]
    NQ --> NV
    NQ --> NG
    NV --> NC
    NG --> NC
    NC --> NL
    NL --> Answer2
  end

  subgraph EdgeDB
    EQ[User Query]
    EV[ベクトル検索 (ext::ai::search)]
    EG[グラフリンク検索 (EdgeQL SELECT)]
    EC[結果統合]
    EL[LLM]
    EQ --> EV
    EQ --> EG
    EV --> EC
    EG --> EC
    EC --> EL
    EL --> Answer3
  end
```

- **SurrealDB:** 単一のSurrealQLクエリでベクトル類似度 (`vector::distance`) とグラフフィルター (`->`) を同時処理できる。  
- **Neo4j:** ベクトル検索は `db.index.vector.queryNodes` 呼び出しで行い、グラフ探索は別途 MATCH パターンで実施。結果はアプリ側でマージ。  
- **EdgeDB:** `ext::ai::search` で文書検索し、EdgeQL のリンク参照で関連情報を取得。Surrealのような単一文ではなく2ステップ以上になる。  

（図は主要な流れを示した概略であり、実際のシステムではアクセス制御やログ記録、エラーハンドリング等の追加要素が入る）

## 推奨と次のステップ

- **推奨データベースの選定:** 開発リソースと要件に応じ、用途に最適なDBを選択する。マルチモデルを活用した高速開発を重視するなら SurrealDB、既存グラフ投資や高度なグラフ解析を優先するなら Neo4j、SQL調和型でLLM機能を組み込みたいなら EdgeDB が向く。  
- **パイロット実装:** 上記プロトタイプコードを基に、実際のデータ量・クエリ内容でベンチマークを行う。各DBでの遅延やスループット、リソース使用量を測定し、要件（レイテンシ、同時接続数、データサイズ）を検証する。  
- **データ整備とインデックス設計:** 適切なインデックス（ベクトル/全文/グラフ）を整備し、インポートパイプラインを確立する。特にNeo4jではMATCH拡張が中間状態を生まないよう絞り込みを工夫し、SurrealDBではWHERE節の条件順序でチューニングする。  
- **セキュリティ・運用:** 選定DBのドキュメントに従い、TLS設定や認証方式（JWT/LDAPなど）、定期バックアップ、監視体制を確立する。特に SurrealDB や EdgeDB は比較的新しいため、脆弱性情報など最新の開発状況を追い続ける。  
- **エコシステム活用:** LangChain や LlamaIndex などの高レベルフレームワークで提供される各DB対応モジュールも併用し、RAGパイプラインやエージェント機能を効率化する。実装例ではPythonで示したが、Node.js のSDKも存在するので開発チームの経験に合わせた言語選択も検討する。  

以上の検討をもとに、要件に最適なアーキテクチャを選択し、設計書作成およびPoC検証を進めるとよい。すべてのDBで実装可能であるため、プロジェクトの重心や既存システムとの親和性を考慮して選択すると成功確率が高まる。  

**参考資料:** SurrealDB公式ブログ・ドキュメント、EdgeDB公式ブログ、Neo4j公式ドキュメントなど。
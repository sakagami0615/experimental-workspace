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

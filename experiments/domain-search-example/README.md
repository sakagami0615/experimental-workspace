# 指定ドメイン限定 Web 検索 + ローカル LLM 実験

## 概要

Ollama などのローカル LLM を使い、指定した Web サイトまたはドメイン内の情報だけを質問時に検索して回答する方式を検証する実験。

一般的な RAG のような Embedding、Vector DB、事前インデックス作成は初期スコープに含めず、質問ごとに Web 検索、本文取得、本文抽出、LLM 回答生成を行う。

## 初期スコープ

- 指定ドメインだけを検索対象にする
- Open WebUI を操作 UI として使う
- SearXNG によるローカル検索基盤を使う
- httpx で検索結果ページを並列取得する
- Trafilatura で本文を抽出する
- Ollama のローカル LLM に Sources として本文を渡す
- 回答には根拠 URL を含める
- Sources にない内容は回答しないように制御する
- 回答後に次の質問候補を表示する

## 想定構成

```text
ユーザー
  ↓
Open WebUI
  ↓
Python App / Pipe Function
  ↓
SearXNG
  ↓
指定ドメイン検索
  ↓
httpx / Playwright
  ↓
Trafilatura
  ↓
Ollama
  ↓
回答 + 参照 URL + 次の質問候補
```

## 推奨初期パラメータ

| 項目 | 初期値 |
|---|---:|
| 検索結果取得 | 10 件 |
| 本文取得 | 3 ページ |
| 最大ページ数 | 5 ページ |
| 1 ページ本文 | 3,000〜5,000 文字程度 |
| 回答方式 | Streaming 推奨 |
| 操作 UI | Open WebUI |

## 作業メモ

詳細な調査内容は [docs/APPENDIX/research-report.md](docs/APPENDIX/research-report.md) を参照。

設計と実装計画は以下を参照。

- [設計 Markdown](docs/superpowers/specs/2026-08-30-domain-limited-local-llm-design.md)
- [設計 HTML](docs/superpowers/specs/2026-08-30-domain-limited-local-llm-design.html)
- [実装計画 Markdown](docs/superpowers/plans/2026-08-30-domain-limited-local-llm.md)
- [実装計画 HTML](docs/superpowers/plans/2026-08-30-domain-limited-local-llm.html)

## セットアップ

```bash
cp .env.example .env
docker compose build
docker compose up
```

Ollama はこの Compose では起動しない。`.env` の `OLLAMA_BASE_URL` に、別環境で動いている Ollama の URL を指定する。

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:8b
ALLOWED_DOMAINS=learn.microsoft.com
```

`OLLAMA_MODEL` は Ollama 側に実際に pull 済みのモデル名と一致させる。未インストールのモデル名を指定すると `/api/generate` が 404 を返す。事前に対象の Ollama で次を実行し、インストール済みモデル名を確認する。

```bash
curl http://<Ollamaのホスト>:11434/api/tags
```

## 検索対象ドメインの設定箇所

このシステムは「特定の1つのURL」を直接読み込むのではなく、`ALLOWED_DOMAINS` で指定した**ドメイン単位**を検索対象にする方式。設定は次の流れで反映される。

1. `.env`(`.env.example` をコピー)の `ALLOWED_DOMAINS` にカンマ区切りでドメインを列挙する
2. `docker-compose.yml` の `search-service` サービスが `.env` の値を環境変数として読み込む
3. `src/settings.py` の `AppSettings.allowed_domains` が値を保持し、`allowed_domain_list` でカンマ区切りをリスト化する
4. `src/search.py` の `build_site_query` が `site:ドメイン` 演算子付きのクエリを組み立てて SearXNG に問い合わせる
5. `src/allowlist.py` の `is_allowed_url` が検索結果URLのホスト名を照合し、許可ドメインおよびそのサブドメインのみ本文取得対象として通す

## 回答できる質問・できない質問

質問ごとに Web 検索を行う方式のため、狙った情報を回答させたい場合は次の条件を満たす質問にする。

- 質問に含めたキーワードが、対象ドメイン内のページ本文・タイトルに実際に存在し、検索エンジンでヒットしやすいこと
- 知りたい情報が載っているページのドメイン(サブドメイン含む)が `ALLOWED_DOMAINS` に含まれていること
- 製品名・機能名・設定項目名などの固有名詞を含む具体的な質問であること(曖昧な質問は的外れな検索結果になりやすい)

対象ドメイン内に情報がない、または検索でヒットしない質問には固定文言「指定されたWebサイトからは確認できません。」が返る(`src/pipeline.py` の `NO_SOURCES_MESSAGE`)。

### ALLOWED_DOMAINS とサンプル質問の組み合わせ

| ALLOWED_DOMAINS | サンプル質問 |
|---|---|
| `learn.microsoft.com` | Azure Functions の既定のタイムアウト時間を教えてください |
| `learn.microsoft.com` | Azure AI Search の料金体系を教えてください |
| `docs.python.org` | asyncio.gather の使い方を教えてください |
| `developer.mozilla.org` | JavaScript の Array.prototype.map の仕様を教えてください |

いずれもドメイン単位の設定例であり、実際にヒットするかは SearXNG の検索結果次第。手元で試す際は「CLI での動作確認」のコマンドで実行結果(回答・参照URL)を確認する。

## Open WebUI での操作

1. `http://localhost:3002` を開く。別ポートにしたい場合は `.env` の `OPEN_WEBUI_PORT` を変更する。
2. `open-webui/functions/domain_search_pipe.py` を Admin Panel > Functions から登録する。
3. New Chat 画面のモデル選択ドロップダウン(通常 `llama3` 等が並ぶ場所)を開き、`指定ドメイン検索` を選ぶ。専用のメニューやボタンではなく、Pipe Function がモデル一覧に追加される形で表示される。
4. 質問する。
5. 回答本文、参照 URL、次の質問候補を確認する。

モデル一覧に `指定ドメイン検索` が表示されない場合は、Admin Panel > Functions で該当 Function が有効化されているか、エラー表示が出ていないかを確認する。

Function の詳しい登録手順は [docs/open-webui-function.md](docs/open-webui-function.md) を参照。

## CLI での動作確認

```bash
docker compose run --rm search-service uv run domain-search "調べたい質問"
```

## テスト

```bash
docker compose run --rm search-service uv run pytest -q
```

## トラブルシューティング

### `search-service` への接続が 500 エラーになる(SearXNG が 403 を返す)

SearXNG は既定で JSON 形式のレスポンス(`format=json`)を無効化しており、`src/search.py` はこの形式で問い合わせるため 403 Forbidden になり、結果として `search-service` が 500 を返す。本リポジトリでは `config/searxng/settings.yml` で `search.formats` に `json` を追加し、`docker-compose.yml` の `searxng` サービスにマウントすることで解消している。`docker compose logs searxng` に `SearxEngineAccessDeniedException` や `403` が出る場合は、このファイルがマウントされているか、`docker compose up -d searxng` でコンテナが再作成されているかを確認する。

### Ollama への問い合わせが 404 になる

`OLLAMA_MODEL` に指定したモデルが Ollama 側に pull されていないと `/api/generate` が 404 を返す。`curl http://<Ollamaのホスト>:11434/api/tags` でインストール済みモデル名を確認し、`.env` の `OLLAMA_MODEL` と一致させる。

### 回答生成がタイムアウトする

ローカル LLM の応答生成、特に初回のモデルロードを含む呼び出しは `REQUEST_TIMEOUT_SECONDS`(既定 60 秒)を超えることがある。CPU 実行や大きめのモデルを使う場合は `.env` の `REQUEST_TIMEOUT_SECONDS` をさらに増やす。

### `docker compose run` で `domain-search: executable file not found` になる

`domain-search` コマンドは `uv sync` で作成される仮想環境内にのみ存在するため、`uv run domain-search ...` のように `uv run` を付けて実行する。

### 短時間に連続で質問すると「確認できません」や検索エンジンのブロック表示が出る

SearXNG は Google・Bing 等の公開検索エンジンを内部的にスクレイピングして結果を集約している。同じ質問・似た質問を短時間に連続で送ると、これらの検索エンジン側が自動アクセス(ボット)と判定し、CAPTCHA表示やレート制限(HTTP 429/403)で一時的にブロックすることがある。ブロックされている間は検索結果が0件になり、正しくドメイン内に情報があっても回答できない。

- 本リポジトリでは `config/searxng/settings.yml` で、観測上ブロックが頻発しやすい `duckduckgo` / `startpage` / `wikidata` / `wikipedia` を無効化し、`brave` / `google cse` のみを有効にしている。これらもアクセス過多になると一時的にブロックされる(目安: 数分〜1時間程度)。
- ブロックが原因で回答できなかった場合は、固定文言ではなく「検索エンジンが一時的にブロックされているため検索結果を取得できませんでした(エンジン名: 理由, ...)。しばらく時間をおいてから再度お試しください。」という具体的なメッセージが返る(`src/pipeline.py` の `build_engines_blocked_message`)。これは SearXNG の JSON レスポンスに含まれる `unresponsive_engines` を利用して判定している。
- 短時間に何度も同じ質問を送って検証しない、テスト間隔を空ける、といった運用上の配慮が必要。`docker compose logs searxng` で `too many requests` や `CAPTCHA` が出ていないか確認すると状況を切り分けられる。

## 今後の作業候補

1. `docker-compose.yml` で Open WebUI、Python App、SearXNG を定義する
2. Allowlist による URL 検証ロジックを実装する
3. SearXNG 検索クライアントを実装する
4. httpx と Trafilatura による本文取得・抽出を実装する
5. Ollama への問い合わせと参照 URL 付き回答生成を実装する
6. Open WebUI から使う Pipe Function を実装する
7. 回答後の次質問候補を Open WebUI に返す
8. サンプルドメインを使った E2E 検証を追加する

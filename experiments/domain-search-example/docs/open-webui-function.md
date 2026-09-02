# Open WebUI Function 登録手順

## 前提

`docker compose up` で Open WebUI、search-service、SearXNG を起動する。

Open WebUI の Function はサーバー側で Python コードを実行する。登録前に `open-webui/functions/domain_search_pipe.py` の内容を確認し、信頼できるローカルコードだけを登録する。

## 登録手順

1. ブラウザで `http://localhost:3002` を開く。別ポートにしたい場合は `.env` の `OPEN_WEBUI_PORT` を変更する。
2. 管理者ユーザーでログインする。
3. Admin Panel > Functions を開く。
4. Create を選ぶ。
5. `open-webui/functions/domain_search_pipe.py` の内容を貼り付ける。
6. Save して Function を有効化する。
7. Valves で `search_service_base_url` が `http://search-service:8000` になっていることを確認する。
8. Chat 画面で `指定ドメイン検索` を選ぶ。
9. 質問を送信する。
10. 回答本文、参照 URL、回答下の次質問候補を確認する。

## 次質問候補

Pipe Function は search-service の `follow_ups` を Open WebUI の `chat:message:follow_ups` イベントとして送る。Open WebUI 側で Follow-Up Prompts が有効な場合、回答下にクリック可能な候補として表示される。

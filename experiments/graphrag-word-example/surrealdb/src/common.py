"""SurrealDB GraphRAG 共有ユーティリティ。"""

import json
import os
import re

from langchain_ollama import ChatOllama, OllamaEmbeddings
from surrealdb import BlockingHttpSurrealConnection

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
SURREAL_URL = os.getenv("SURREAL_URL", "http://surrealdb:8000")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS = os.getenv("SURREAL_NS", "graphrag_ns")
SURREAL_DB = os.getenv("SURREAL_DB", "graphrag_db")


def get_embeddings() -> OllamaEmbeddings:
    """Ollama埋め込みモデルを返す。"""
    return OllamaEmbeddings(base_url=OLLAMA_BASE_URL, model=OLLAMA_EMBED_MODEL)


def get_llm() -> ChatOllama:
    """Ollama LLMを返す。"""
    return ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_LLM_MODEL)


def get_connection() -> BlockingHttpSurrealConnection:
    """認証済みのSurrealDB HTTP接続を返す。"""
    conn = BlockingHttpSurrealConnection(SURREAL_URL)
    conn.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
    conn.use(SURREAL_NS, SURREAL_DB)
    return conn


def surreal_query(query: str) -> list:
    """SurrealDBにクエリを実行して結果を返す。"""
    return get_connection().query(query)


def generate(context: str, question: str) -> str:
    """Ollamaでコンテキストを元に回答を生成する。"""
    prompt = f"以下の情報を参考に質問に答えてください。\n\nコンテキスト:\n{context}\n\n質問: {question}\n\n回答:"
    return get_llm().invoke(prompt).content


def extract_entities(question: str) -> list[str]:
    """LLMでクエリからグラフ検索用のキーワード・エンティティを抽出する。"""
    prompt = (
        "以下の質問から、グラフ検索に使うキーワードや概念名を抽出してください。\n"
        "JSON配列形式（例: [\"GraphRAG\", \"ベクトル検索\"]）のみ返してください。\n"
        f"質問: {question}\n"
        "キーワード:"
    )
    result = get_llm().invoke(prompt).content.strip()
    match = re.search(r"\[.*?\]", result, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return [question]

"""EdgeDB GraphRAG 共有ユーティリティ。"""

import os

import edgedb
import numpy as np
from langchain_ollama import ChatOllama, OllamaEmbeddings

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
EDGEDB_DSN = os.getenv("EDGEDB_DSN", "edgedb://edgedb@localhost:5656/edgedb?tls_security=insecure")


def get_embeddings() -> OllamaEmbeddings:
    """Ollama埋め込みモデルを返す。"""
    return OllamaEmbeddings(base_url=OLLAMA_BASE_URL, model=OLLAMA_EMBED_MODEL)


def get_llm() -> ChatOllama:
    """Ollama LLMを返す。"""
    return ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_LLM_MODEL)


def get_client() -> edgedb.Client:
    """EdgeDB クライアントを生成して返す。"""
    return edgedb.create_client(dsn=EDGEDB_DSN)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """2つのベクトルのコサイン類似度を計算する。"""
    va, vb = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 1e-10 else 0.0


def generate(context: str, question: str) -> str:
    """Ollamaでコンテキストを元に回答を生成する。"""
    prompt = f"以下の情報を参考に質問に答えてください。\n\nコンテキスト:\n{context}\n\n質問: {question}\n\n回答:"
    return get_llm().invoke(prompt).content

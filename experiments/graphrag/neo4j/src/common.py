"""Neo4j GraphRAG 共有ユーティリティ。"""

import os

import httpx
from neo4j import Driver, GraphDatabase

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "testpassword")


def embed(text: str) -> list[float]:
    """テキストをOllamaで埋め込みベクトルに変換する。"""
    r = httpx.post(f"{OLLAMA_BASE_URL}/api/embeddings",
                   json={"model": OLLAMA_EMBED_MODEL, "prompt": text}, timeout=60.0)
    r.raise_for_status()
    return r.json()["embedding"]


def generate(context: str, question: str) -> str:
    """Ollamaでコンテキストを元に回答を生成する。"""
    prompt = f"以下の情報を参考に質問に答えてください。\n\nコンテキスト:\n{context}\n\n質問: {question}\n\n回答:"
    r = httpx.post(f"{OLLAMA_BASE_URL}/api/generate",
                   json={"model": OLLAMA_LLM_MODEL, "prompt": prompt, "stream": False}, timeout=120.0)
    r.raise_for_status()
    return r.json()["response"]


def get_driver() -> Driver:
    """Neo4j ドライバーを生成して返す。"""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

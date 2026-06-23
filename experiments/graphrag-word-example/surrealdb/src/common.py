"""SurrealDB GraphRAG 共有ユーティリティ。"""

import json
import os
import re

from langchain_ollama import ChatOllama, OllamaEmbeddings
from pydantic import BaseModel, Field
from surrealdb import BlockingHttpSurrealConnection

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
SURREAL_URL = os.getenv("SURREAL_URL", "http://surrealdb:8000")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS = os.getenv("SURREAL_NS", "graphrag_ns")
SURREAL_DB = os.getenv("SURREAL_DB", "graphrag_db")
ALLOWED_RELATIONS = {"USES", "EXTENDS", "REQUIRES", "PART_OF", "RELATED_TO"}


class Relation(BaseModel):
    """概念間の関係を表す。"""

    source: str = Field(description="関係元ノードのID")
    target: str = Field(description="関係先ノードのID")
    relation: str = Field(description="USES / EXTENDS / REQUIRES / PART_OF / RELATED_TO のいずれか")


class RelationList(BaseModel):
    """LLMが抽出した関係の一覧。"""

    relations: list[Relation]


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


def extract_relations(nodes: list[dict]) -> list[Relation]:
    """LLMでノード一覧から関係を自動抽出する。"""
    ids = [n["id"] for n in nodes]
    node_list = "\n".join(f'- {n["id"]}: {n["label"]} - {n["content"]}' for n in nodes)
    prompt = (
        "以下の概念リストから、概念間の関係を抽出してください。\n"
        f"source と target のIDは必ず次のリストから選んでください: {ids}\n"
        "relationはUSES, EXTENDS, REQUIRES, PART_OF, RELATED_TOのいずれかを使ってください。\n"
        "明確な関係がない場合は省略してください。\n\n"
        f"概念リスト:\n{node_list}"
    )
    llm = get_llm().with_structured_output(RelationList)
    result: RelationList = llm.invoke(prompt)
    valid_ids = set(ids)
    return [
        r for r in result.relations
        if r.source in valid_ids and r.target in valid_ids and r.relation in ALLOWED_RELATIONS
    ]


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

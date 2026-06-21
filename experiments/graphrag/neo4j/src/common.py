"""Neo4j GraphRAG 共有ユーティリティ。"""

import os

from langchain_neo4j import Neo4jGraph
from langchain_ollama import ChatOllama, OllamaEmbeddings
from pydantic import BaseModel, Field

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "testpassword")


class Relation(BaseModel):
    source: str = Field(description="関係元ノードのID")
    target: str = Field(description="関係先ノードのID")
    relation: str = Field(description="USES / EXTENDS / REQUIRES / PART_OF / RELATED_TO のいずれか")


class RelationList(BaseModel):
    relations: list[Relation]


class EntityList(BaseModel):
    entities: list[str]


def get_embeddings() -> OllamaEmbeddings:
    """Ollama埋め込みモデルを返す。"""
    return OllamaEmbeddings(base_url=OLLAMA_BASE_URL, model=OLLAMA_EMBED_MODEL)


def get_llm() -> ChatOllama:
    """Ollama LLMを返す。"""
    return ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_LLM_MODEL)


def get_graph() -> Neo4jGraph:
    """Neo4jGraph接続を返す。"""
    return Neo4jGraph(url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASS, refresh_schema=False)


def generate(context: str, question: str) -> str:
    """Ollamaでコンテキストを元に回答を生成する。"""
    prompt = f"以下の情報を参考に質問に答えてください。\n\nコンテキスト:\n{context}\n\n質問: {question}\n\n回答:"
    return get_llm().invoke(prompt).content


def extract_relations(nodes: list[dict]) -> list[Relation]:
    """LLMでノード一覧から関係を自動抽出する。"""
    ids = [n["id"] for n in nodes]
    node_list = "\n".join(f'- {n["id"]}: {n["label"]} — {n["content"]}' for n in nodes)
    prompt = (
        "以下の概念リストから、概念間の関係を抽出してください。\n"
        f"source と target のIDは必ず次のリストから選んでください: {ids}\n"
        "relationはUSES, EXTENDS, REQUIRES, PART_OF, RELATED_TOのいずれかを使ってください。\n"
        "明確な関係がない場合は省略してください。\n\n"
        f"概念リスト:\n{node_list}"
    )
    llm = get_llm().with_structured_output(RelationList)
    result: RelationList = llm.invoke(prompt)
    return result.relations


def extract_entities(question: str) -> list[str]:
    """LLMでクエリからグラフ検索用のキーワード・エンティティを抽出する。"""
    prompt = (
        "以下の質問から、グラフ検索に使うキーワードや概念名を抽出してください。\n\n"
        f"質問: {question}"
    )
    llm = get_llm().with_structured_output(EntityList)
    result: EntityList = llm.invoke(prompt)
    return result.entities or [question]

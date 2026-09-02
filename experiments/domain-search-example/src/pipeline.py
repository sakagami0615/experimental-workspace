from collections.abc import Sequence

from pydantic import BaseModel

from allowlist import is_allowed_url
from extract import extract_text
from fetch import fetch_pages
from ollama import Source, generate_answer
from search import search_searxng
from settings import AppSettings

NO_SOURCES_MESSAGE = "指定されたWebサイトからは確認できません。"


class AnswerResponse(BaseModel):
    """Response returned to Open WebUI."""

    answer: str
    sources: list[str]
    follow_ups: list[str]


def build_engines_blocked_message(unresponsive_engines: Sequence[tuple[str, str]]) -> str:
    """Explain that search engines are temporarily blocking SearXNG's requests."""
    engine_details = ", ".join(f"{engine}: {reason}" for engine, reason in unresponsive_engines)
    return (
        f"検索エンジンが一時的にブロックされているため検索結果を取得できませんでした({engine_details})。"
        "しばらく時間をおいてから再度お試しください。"
    )


def build_follow_up_questions(question: str) -> list[str]:
    """Return fixed follow-up prompts for domain-limited investigation."""
    return [
        "この内容の前提条件を詳しく確認してください",
        "根拠URLごとの差分を比較してください",
        "関連する制限事項や注意点を確認してください",
    ]


async def answer_question(question: str, settings: AppSettings) -> AnswerResponse:
    """Answer a question from allowed web sources."""
    search_outcome = await search_searxng(question, settings)
    allowed_results = [
        result
        for result in search_outcome.results
        if is_allowed_url(result.url, settings.allowed_domain_list)
    ][: settings.fetch_page_limit]

    if not allowed_results:
        answer = (
            build_engines_blocked_message(search_outcome.unresponsive_engines)
            if search_outcome.unresponsive_engines
            else NO_SOURCES_MESSAGE
        )
        return AnswerResponse(
            answer=answer,
            sources=[],
            follow_ups=build_follow_up_questions(question),
        )

    pages = await fetch_pages(
        [result.url for result in allowed_results],
        settings.request_timeout_seconds,
    )
    titles_by_url = {result.url: result.title for result in allowed_results}
    sources: list[Source] = []
    for page in pages:
        text = extract_text(page.html, settings.max_chars_per_page)
        if text:
            sources.append(
                Source(
                    url=page.url,
                    title=titles_by_url.get(page.url, page.url),
                    text=text,
                )
            )

    if not sources:
        return AnswerResponse(
            answer=NO_SOURCES_MESSAGE,
            sources=[],
            follow_ups=build_follow_up_questions(question),
        )

    answer = await generate_answer(question, sources, settings)
    return AnswerResponse(
        answer=answer or NO_SOURCES_MESSAGE,
        sources=[source.url for source in sources],
        follow_ups=build_follow_up_questions(question),
    )

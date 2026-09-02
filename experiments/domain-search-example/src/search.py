from collections.abc import Iterable
from dataclasses import dataclass

import httpx

from settings import AppSettings


@dataclass(frozen=True)
class SearchResult:
    """A normalized SearXNG search result."""

    title: str
    url: str
    content: str | None = None


@dataclass(frozen=True)
class SearchOutcome:
    """Results of a SearXNG search plus per-engine failure diagnostics."""

    results: list[SearchResult]
    unresponsive_engines: tuple[tuple[str, str], ...]


def build_site_query(question: str, allowed_domains: Iterable[str]) -> str:
    """Build a search query constrained by site operators."""
    site_clause = " OR ".join(f"site:{domain}" for domain in allowed_domains)
    return f"{question} ({site_clause})"


def parse_search_results(payload: dict) -> list[SearchResult]:
    """Parse SearXNG JSON search results."""
    results: list[SearchResult] = []
    for item in payload.get("results", []):
        url = item.get("url")
        if not url:
            continue
        results.append(
            SearchResult(
                title=item.get("title") or url,
                url=url,
                content=item.get("content"),
            )
        )
    return results


def parse_unresponsive_engines(payload: dict) -> tuple[tuple[str, str], ...]:
    """Parse SearXNG's per-engine failure diagnostics (e.g. rate limits, CAPTCHA)."""
    return tuple(
        (str(engine), str(reason)) for engine, reason in payload.get("unresponsive_engines", [])
    )


async def search_searxng(question: str, settings: AppSettings) -> SearchOutcome:
    """Search SearXNG for the question within allowed domains."""
    query = build_site_query(question, settings.allowed_domain_list)
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(
            f"{settings.searxng_base_url.rstrip('/')}/search",
            params={"q": query, "format": "json", "language": "ja", "safesearch": 1},
        )
        response.raise_for_status()
    payload = response.json()
    return SearchOutcome(
        results=parse_search_results(payload)[: settings.search_result_limit],
        unresponsive_engines=parse_unresponsive_engines(payload),
    )

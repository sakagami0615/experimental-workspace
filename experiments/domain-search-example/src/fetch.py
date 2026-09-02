import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class FetchedPage:
    """Fetched HTML for a URL."""

    url: str
    html: str


async def fetch_pages(urls: Sequence[str], timeout_seconds: float) -> list[FetchedPage]:
    """Fetch pages concurrently and return successful HTML responses."""
    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "domain-search-example/0.1"},
    ) as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    pages: list[FetchedPage] = []
    for url, response in zip(urls, responses, strict=True):
        if isinstance(response, Exception):
            continue
        if response.status_code >= 400:
            continue
        pages.append(FetchedPage(url=url, html=response.text))
    return pages

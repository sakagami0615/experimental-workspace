"""
title: Domain Limited Search
author: local
version: 0.1.0
requirements: httpx, pydantic
"""

from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from pydantic import BaseModel, Field


class Pipe:
    """Open WebUI Pipe Function for domain-limited search."""

    class Valves(BaseModel):
        """Administrator-configurable Pipe settings."""

        search_service_base_url: str = Field(default="http://search-service:8000")

    def __init__(self) -> None:
        self.valves = self.Valves()

    def pipes(self) -> list[dict[str, str]]:
        """Return the model entry shown in Open WebUI."""
        return [{"id": "domain-limited-search", "name": "指定ドメイン検索"}]

    async def pipe(
        self,
        body: dict[str, Any],
        __event_emitter__: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> str:
        """Send the latest user question to the search service."""
        question = self._latest_user_message(body)
        if not question:
            return "質問を入力してください。"

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "指定ドメイン内を検索しています", "done": False},
                }
            )

        try:
            data = await self._request_answer(question)
        except httpx.HTTPError as exc:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "検索回答サービスへの接続に失敗しました", "done": True},
                    }
                )
            return f"検索回答サービスへの接続に失敗しました: {exc}"

        if __event_emitter__:
            await self._emit_sources(data.get("sources") or [], __event_emitter__)
            await self._emit_follow_ups(data.get("follow_ups") or [], __event_emitter__)
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "回答を生成しました", "done": True},
                }
            )

        return self._format_answer(data)

    def _latest_user_message(self, body: dict[str, Any]) -> str:
        """Extract the latest user message from an Open WebUI request body."""
        for message in reversed(body.get("messages", [])):
            if message.get("role") == "user":
                return str(message.get("content", "")).strip()
        return ""

    async def _request_answer(self, question: str) -> dict[str, Any]:
        """Call the Python search service."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.valves.search_service_base_url.rstrip('/')}/answer",
                json={"question": question},
            )
            response.raise_for_status()
        return dict(response.json())

    async def _emit_sources(
        self,
        sources: list[str],
        event_emitter: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Emit source citations to Open WebUI."""
        for source in sources:
            await event_emitter(
                {
                    "type": "citation",
                    "data": {
                        "document": [source],
                        "metadata": [{"source": source}],
                        "source": {"name": source, "url": source},
                    },
                }
            )

    async def _emit_follow_ups(
        self,
        follow_ups: list[str],
        event_emitter: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Emit clickable follow-up prompts to Open WebUI."""
        if follow_ups:
            await event_emitter(
                {
                    "type": "chat:message:follow_ups",
                    "data": {"follow_ups": follow_ups},
                }
            )

    def _format_answer(self, data: dict[str, Any]) -> str:
        """Format answer text for Open WebUI message persistence."""
        answer = data.get("answer") or "指定されたWebサイトからは確認できません。"
        sources = data.get("sources") or []

        sections = [answer]
        if sources:
            sections.append("参照URL:\n" + "\n".join(f"- {source}" for source in sources))
        return "\n\n".join(sections)

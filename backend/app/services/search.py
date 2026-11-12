"""Genuine web search through Tavily (configurable provider)."""
from __future__ import annotations

import time
from typing import Any

import httpx

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError

settings = get_settings()


async def search(query: str, max_results: int | None = None) -> dict[str, Any]:
    if settings.search_provider != "tavily":
        raise IntegrationNotConfigured(
            settings.search_provider, "TAVILY_API_KEY", f"Unsupported search provider: {settings.search_provider}"
        )
    if not settings.tavily_api_key:
        raise IntegrationNotConfigured("Tavily", "TAVILY_API_KEY")
    started = time.perf_counter()
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "max_results": max_results or settings.search_max_results,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post("https://api.tavily.com/search", json=payload)
    if response.status_code != 200:
        raise ProviderError("Tavily", f"Search failed: HTTP {response.status_code} {response.text[:300]}")
    data = response.json()
    results = [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
            "score": float(item.get("score", 0) or 0),
        }
        for item in data.get("results", [])
    ]
    return {
        "query": query,
        "answer": data.get("answer"),
        "results": results,
        "provider": "tavily",
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }

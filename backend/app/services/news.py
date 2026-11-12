"""Global News Intelligence: RSS aggregation + Tavily AI-powered search."""
from __future__ import annotations

import asyncio
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from ..config import get_settings
from ..errors import ProviderError
from .openrouter import chat as openrouter_chat
from .search import search as tavily_search

settings = get_settings()

RSS_FEEDS: dict[str, list[str]] = {
    "world": ["https://feeds.bbci.co.uk/news/world/rss.xml", "https://www.aljazeera.com/xml/rss/all.xml"],
    "technology": ["https://feeds.bbci.co.uk/news/technology/rss.xml"],
    "science": ["https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"],
    "business": ["https://feeds.bbci.co.uk/news/business/rss.xml"],
    "india": ["https://feeds.bbci.co.uk/news/world/asia/india/rss.xml"],
    "ai": ["https://feeds.bbci.co.uk/news/technology/rss.xml"],
    "health": ["https://feeds.bbci.co.uk/news/health/rss.xml"],
    "sports": ["https://feeds.bbci.co.uk/sport/rss.xml"],
}

CATEGORY_LABELS = {
    "world": "World News",
    "technology": "Technology",
    "science": "Science",
    "business": "Business & Finance",
    "india": "India",
    "ai": "AI & Technology",
    "health": "Health",
    "sports": "Sports",
}


def _fetch_rss(url: str, timeout: float = 12) -> list[dict[str, Any]]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NexaMindAI/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except Exception:
        return []
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(raw)
        channel = root.find("channel")
        if channel is None:
            # Atom feeds
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns)[:20]:
                title = entry.findtext("atom:title", "", ns)
                link = (entry.find("atom:link", ns) or ET.Element("x")).get("href", "")
                items.append({"title": title, "url": link, "source": url, "published": entry.findtext("atom:updated", "", ns)})
            return items
        for item in channel.findall("item")[:20]:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub = item.findtext("pubDate", "").strip()
            description = item.findtext("description", "").strip()
            source_el = item.find("source")
            source_name = (source_el.text or "").strip() if source_el is not None else ""
            published = ""
            if pub:
                try:
                    published = parsedate_to_datetime(pub).isoformat()
                except Exception:
                    published = pub
            if title and link:
                items.append({
                    "title": title,
                    "url": link,
                    "description": description,
                    "source": source_name or url.split("/")[2].replace("feeds.", "").replace("www.", ""),
                    "published": published,
                })
    except Exception:
        return []
    return items


async def get_headlines(category: str = "world", limit: int = 12) -> list[dict[str, Any]]:
    feeds = RSS_FEEDS.get(category, RSS_FEEDS["world"])
    loop = asyncio.get_running_loop()
    results: list[list[dict[str, Any]]] = await asyncio.gather(
        *(loop.run_in_executor(None, _fetch_rss, url) for url in feeds)
    )
    seen_urls: set[str] = set()
    merged: list[dict[str, Any]] = []
    for batch in results:
        for item in batch:
            if item["url"] and item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                merged.append(item)
    merged.sort(key=lambda item: item.get("published") or "", reverse=True)
    return merged[:limit]


async def search_news(query: str, limit: int = 8) -> dict[str, Any]:
    """Tavily news search with AI synthesis."""
    if not settings.tavily_api_key:
        return {"configured": False, "answer": "", "results": [], "notice": "TAVILY_API_KEY not configured"}
    result = await tavily_search(query, max_results=limit)
    return {
        "configured": True,
        "query": query,
        "answer": result.get("answer", ""),
        "results": result.get("results", []),
        "latency_ms": result.get("latency_ms"),
    }


async def summarize_article(title: str, url: str = "", content: str = "") -> str:
    """AI summary of a news item."""
    if not settings.openrouter_api_key:
        raise ProviderError("OpenRouter", "OPENROUTER_API_KEY not configured")
    source = content or f"Title: {title}\nURL: {url}"
    response = await openrouter_chat(
        messages=[
            {
                "role": "system",
                "content": "Summarize the news item in 3-4 sentences: what happened, where, who is involved, why it matters. Be factual; do not invent details. If uncertain, say so.",
            },
            {"role": "user", "content": source[:4000]},
        ],
        model=settings.default_model,
        max_tokens=300,
    )
    return (response.get("content") or "").strip() or "Summary could not be generated."


def list_categories() -> list[dict[str, str]]:
    return [{"id": key, "label": label} for key, label in CATEGORY_LABELS.items()]

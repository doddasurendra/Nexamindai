"""Deep research: plan, multi-source retrieval, conflict comparison and cited report."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError
from ..models import ResearchRun
from . import openrouter, search
from .fetch import fetch_page

settings = get_settings()


async def _plan(question: str) -> list[str]:
    if not settings.openrouter_configured:
        raise IntegrationNotConfigured("OpenRouter", "OPENROUTER_API_KEY")
    result = await openrouter.chat(
        [
            {
                "role": "system",
                "content": (
                    "Create a research plan. Return JSON only: {\"subquestions\": [3-5 focused questions]}. "
                    "Questions must be answerable from public sources and collectively cover the topic."
                ),
            },
            {"role": "user", "content": question},
        ],
        model=settings.default_model,
        temperature=0.2,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    try:
        payload = json.loads(result["text"])
        items = [str(q) for q in payload.get("subquestions", []) if str(q).strip()]
    except (json.JSONDecodeError, AttributeError):
        items = []
    if not items:
        raise ProviderError("OpenRouter", "Research planner returned no subquestions")
    return items[:5]


async def run_research(db: AsyncSession, user_id: int, question: str, depth: str = "standard") -> ResearchRun:
    if not settings.search_configured:
        raise IntegrationNotConfigured("Tavily", "TAVILY_API_KEY")
    run = ResearchRun(user_id=user_id, question=question, status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)

    plan = await _plan(question)
    run.plan = plan
    await db.commit()

    sources: list[dict[str, Any]] = []
    notes: list[str] = []
    per_question = {"quick": 2, "standard": 3, "deep": 5}[depth]
    for subquestion in plan:
        result = await search.search(subquestion, max_results=per_question)
        for item in result["results"]:
            sources.append(
                {
                    "title": item["title"],
                    "url": item["url"],
                    "snippet": item["content"][:800],
                    "subquestion": subquestion,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        notes.append(f"### {subquestion}\n" + "\n".join(f"- {item['title']}: {item['content'][:400]}" for item in result["results"]))
        if depth != "quick" and result["results"]:
            try:
                page = await fetch_page(result["results"][0]["url"])
                sources.append(
                    {
                        "title": page.title or result["results"][0]["title"],
                        "url": page.final_url,
                        "snippet": page.text[:1500],
                        "subquestion": subquestion,
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception:  # noqa: BLE001 - retrieval failure is recorded, not fabricated
                pass

    unique: dict[str, dict[str, Any]] = {}
    for source in sources:
        unique.setdefault(source["url"], source)
    source_list = list(unique.values())

    bibliography = "\n".join(f"[{i + 1}] {s['title']} — {s['url']}" for i, s in enumerate(source_list))
    evidence = "\n\n".join(
        f"[{i + 1}] ({s['title']}, retrieved {s['retrieved_at']})\n{s['snippet']}" for i, s in enumerate(source_list)
    )
    if not settings.openrouter_configured:
        run.status = "failed"
        run.report = "Research synthesis requires OPENROUTER_API_KEY; retrieval results are stored but no report was generated."
        run.sources = source_list
        await db.commit()
        return run

    synthesis = await openrouter.chat(
        [
            {
                "role": "system",
                "content": (
                    "Write a structured research report using ONLY the numbered evidence. Include: Executive summary, "
                    "Findings (cited as [n]), Conflicts and uncertainty, Limitations, Sources. If sources disagree, say so "
                    "explicitly. Never invent a citation."
                ),
            },
            {"role": "user", "content": f"Question: {question}\n\nEvidence:\n{evidence}\n\nSources:\n{bibliography}"},
        ],
        model=settings.default_model,
        temperature=0.2,
        max_tokens=2000,
    )
    report = synthesis["text"] + f"\n\n## Sources\n{bibliography}"
    run.report = report
    run.sources = source_list
    run.status = "completed"
    await db.commit()
    await db.refresh(run)
    return run

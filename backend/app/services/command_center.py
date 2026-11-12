"""AI Command Center: decompose large tasks, assign agents, execute and verify."""
from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Agent, User
from ..errors import ProviderError
from .agents import AGENT_SPECS, execute_agent, route_agent
from .openrouter import chat as openrouter_chat
from ..config import get_settings

settings = get_settings()


async def decompose_task(objective: str) -> list[dict[str, Any]]:
    """Break an objective into ordered subtasks with agent assignments."""
    agent_catalog = ", ".join(f"{spec['slug']}: {spec['description']}" for spec in AGENT_SPECS)
    response = await openrouter_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a task planner. Break the user's objective into 2-5 concrete subtasks. "
                    f"Assign each subtask to one of these agents: {agent_catalog}. "
                    'Return ONLY a JSON array like [{"id": 1, "task": "...", "agent": "quantum"}]. '
                    "No prose, no markdown fences."
                ),
            },
            {"role": "user", "content": objective},
        ],
        model=settings.default_model,
        max_tokens=1200,
    )
    raw = (response.get("content") or "").strip()
    try:
        plan = json.loads(raw)
        if isinstance(plan, list):
            return [
                {
                    "id": int(item.get("id", index + 1)),
                    "task": str(item.get("task", "")).strip(),
                    "agent": str(item.get("agent", "quantum")).strip(),
                }
                for index, item in enumerate(plan)
                if str(item.get("task", "")).strip()
            ]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    # Fallback: single subtask routed to the best agent
    routed = await route_agent(objective)
    slug = routed.get("agent", AGENT_SPECS[0]["slug"])
    return [{"id": 1, "task": objective, "agent": slug}]


async def execute_plan(db: AsyncSession, user: User, objective: str) -> dict[str, Any]:
    """Execute every subtask sequentially, collecting results."""
    started = time.perf_counter()
    plan = await decompose_task(objective)
    agents = {a.slug: a for a in (await db.execute(select(Agent))).scalars().all()}

    results: list[dict[str, Any]] = []
    context = ""

    for step in plan:
        agent_slug = step["agent"] if step["agent"] in agents else next(iter(agents))
        agent = agents[agent_slug]
        prompt = step["task"] + (f"\n\nContext from prior steps:\n{context[-2000:]}" if context else "")
        try:
            execution = await execute_agent(db, user, agent, prompt, model=None, use_tools=True)
            output = execution.output or ""
            status = execution.status
            execution_id = execution.id
        except Exception as exc:  # noqa: BLE001
            output = f"Subtask failed: {exc}"
            status = "failed"
            execution_id = None
        results.append({
            "id": step["id"],
            "task": step["task"],
            "agent": agent_slug,
            "status": status,
            "output": output,
            "execution_id": execution_id,
        })
        context += f"\nStep {step['id']} ({agent_slug}): {output[:800]}"

    synthesis = await openrouter_chat(
        messages=[
            {
                "role": "system",
                "content": "Combine the subtask outputs into one coherent final answer. Cite each contributing agent. Be honest about failures.",
            },
            {"role": "user", "content": f"Objective: {objective}\n\nSubtask outputs:\n{context}"},
        ],
        model=settings.default_model,
        max_tokens=2000,
    )

    return {
        "objective": objective,
        "plan": plan,
        "results": results,
        "final": (synthesis.get("content") or "").strip(),
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "status": "completed" if all(r["status"] != "failed" for r in results) else "partial",
    }

"""Specialized agents, deterministic guardrails, tool use and an orchestrator."""
from __future__ import annotations

import json
import re
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError
from ..models import Agent, AgentExecution, User
from . import openrouter, search
from .fetch import fetch_page

settings = get_settings()

AGENT_SPECS: list[dict[str, Any]] = [
    {
        "slug": "quantum",
        "name": "Quantum Computing Agent",
        "domain": "quantum",
        "description": "Explains qubits, gates, circuits and quantum algorithms with rigorous caveats.",
        "model": "",
        "tools": ["web_search", "fetch_url"],
        "restrictions": ["Never claim a quantum advantage without citing hardware and assumptions."],
        "system_prompt": (
            "You are the NexaMind Quantum Computing agent. Explain quantum concepts (qubits, superposition, "
            "entanglement, gates, circuits, error correction) precisely. When asked for code, provide Qiskit "
            "snippets that are syntactically valid and state the Qiskit version assumptions. Distinguish theory "
            "from current hardware capability and never fabricate experimental results."
        ),
    },
    {
        "slug": "healthcare",
        "name": "Healthcare AI Agent",
        "domain": "healthcare",
        "description": "Summarizes medical documents and research with strict safety framing.",
        "model": "",
        "tools": ["web_search", "fetch_url", "rag"],
        "restrictions": ["Never diagnose. Always recommend consulting a licensed clinician."],
        "system_prompt": (
            "You are the NexaMind Healthcare agent. Summarize medical documents and research accurately, explain "
            "terminology, and cite sources. You are not a clinician: never provide a diagnosis, dosage, or treatment "
            "decision. Always include a clear safety note encouraging consultation with a qualified professional. "
            "For emergencies, advise contacting local emergency services."
        ),
    },
    {
        "slug": "finance",
        "name": "Financial AI Agent",
        "domain": "finance",
        "description": "Analyzes financial documents, budgets and risk without executing transactions.",
        "model": "",
        "tools": ["web_search", "fetch_url"],
        "restrictions": ["No transactions.", "No guaranteed returns."],
        "system_prompt": (
            "You are the NexaMind Financial agent. Analyze budgets, filings, and market context with explicit "
            "assumptions. You cannot execute transactions and must never promise returns. Flag risk, uncertainty, "
            "and missing data. This is informational analysis, not personalized financial advice."
        ),
    },
    {
        "slug": "cybersecurity",
        "name": "Cybersecurity AI Agent",
        "domain": "cybersecurity",
        "description": "Defensive security analysis, log review, secure coding and threat explanation.",
        "model": "",
        "tools": ["web_search", "fetch_url"],
        "restrictions": [
            "Defensive and authorized testing only.",
            "Refuse requests to attack systems without authorization.",
        ],
        "system_prompt": (
            "You are the NexaMind Cybersecurity agent. Support defensive security: log triage, vulnerability "
            "explanation, secure coding, detection engineering and authorized assessment. Refuse requests to "
            "compromise systems, exfiltrate data, or evade authorization. Ask for scope/authorization when relevant."
        ),
    },
]

REFUSAL_PATTERNS = [
    r"how (do|can) i (hack|breach|exploit|ddos)",
    r"(write|create|build) (me )?(a )?(ransomware|keylogger|botnet|malware)",
    r"steal (credentials|passwords|tokens)",
    r"phishing (page|email|kit)",
    r"bypass (auth|authentication|mfa)",
    r"unauthorized (access|entry)",
]

MEDICAL_DISCLAIMER = (
    "\n\n> Safety note: This is general information, not medical advice or a diagnosis. "
    "Consult a licensed clinician for personal medical decisions."
)
FINANCE_DISCLAIMER = (
    "\n\n> Risk note: Informational analysis only, not personalized financial advice. "
    "Markets involve risk and past performance does not guarantee future results."
)


async def seed_agents(db: AsyncSession) -> None:
    existing = set((await db.execute(select(Agent.slug))).scalars().all())
    for spec in AGENT_SPECS:
        if spec["slug"] not in existing:
            db.add(
                Agent(
                    user_id=None,
                    slug=spec["slug"],
                    name=spec["name"],
                    domain=spec["domain"],
                    description=spec["description"],
                    system_prompt=spec["system_prompt"],
                    model=spec["model"],
                    tools=spec["tools"],
                    restrictions=spec["restrictions"],
                )
            )
    await db.commit()


def _keyword_route(question: str) -> str:
    text = question.lower()
    scores = {
        "quantum": len(re.findall(r"quantum|qubit|qiskit|entangl|circuit|shor|grover", text)),
        "healthcare": len(re.findall(r"medical|clinical|patient|diagnos|health|symptom|drug|trial", text)),
        "finance": len(re.findall(r"financ|budget|market|stock|revenue|risk|portfolio|invoice", text)),
        "cybersecurity": len(re.findall(r"security|vulnerab|malware|log|threat|phish|exploit|firewall|siem", text)),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "cybersecurity"


async def route_agent(question: str) -> dict[str, Any]:
    if settings.openrouter_configured:
        try:
            result = await openrouter.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "Route the user request to exactly one domain: quantum, healthcare, finance, cybersecurity. "
                            'Reply with JSON only: {"agent": "<domain>", "reason": "<short>"}'
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                model=settings.default_model,
                temperature=0,
                max_tokens=80,
                response_format={"type": "json_object"},
            )
            payload = json.loads(result["text"])
            slug = str(payload.get("agent", "")).lower()
            if slug in {spec["slug"] for spec in AGENT_SPECS}:
                return {"agent": slug, "reason": payload.get("reason", "model-routed")}
        except (ProviderError, ValueError, json.JSONDecodeError):
            pass
    return {"agent": _keyword_route(question), "reason": "keyword-fallback"}


def _is_refused(question: str) -> bool:
    text = question.lower()
    return any(re.search(pattern, text) for pattern in REFUSAL_PATTERNS)


async def execute_agent(
    db: AsyncSession,
    user: User,
    agent: Agent,
    question: str,
    *,
    model: str | None = None,
    use_tools: bool = True,
) -> AgentExecution:
    started = time.perf_counter()
    log: list[dict[str, Any]] = []

    execution = AgentExecution(
        agent_id=agent.id,
        user_id=user.id,
        input=question,
        model=model or agent.model or settings.default_model,
        status="running",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    if agent.slug == "cybersecurity" and _is_refused(question):
        execution.status = "refused"
        execution.output = (
            "I can't help with unauthorized offensive activity. I can support authorized defensive security: "
            "log triage, detection rules, vulnerability remediation, or secure code review."
        )
        execution.log = [{"step": "guardrail", "status": "blocked", "reason": "offensive-security request"}]
        execution.latency_ms = int((time.perf_counter() - started) * 1000)
        await db.commit()
        return execution

    context_blocks: list[str] = []
    sources: list[dict[str, str]] = []

    if use_tools and "web_search" in agent.tools and settings.search_configured:
        if re.search(r"latest|news|research|study|2024|2025|current|compare", question, re.I):
            try:
                result = await search.search(question, max_results=4)
                log.append({"step": "web_search", "status": "ok", "results": len(result["results"])})
                for item in result["results"][:4]:
                    context_blocks.append(f"[{item['title']}] {item['content'][:1200]}\n({item['url']})")
                    sources.append({"title": item["title"], "url": item["url"]})
                if result.get("answer"):
                    context_blocks.append(f"Search summary: {result['answer']}")
            except (IntegrationNotConfigured, ProviderError) as exc:
                log.append({"step": "web_search", "status": "error", "error": str(exc)})
    else:
        log.append({"step": "web_search", "status": "skipped", "reason": "provider not configured or disabled"})

    if context_blocks and "fetch_url" in agent.tools and sources:
        try:
            page = await fetch_page(sources[0]["url"])
            log.append({"step": "fetch_url", "status": "ok", "url": page.final_url, "bytes": page.bytes_read})
            context_blocks.append(f"Page excerpt ({page.final_url}):\n{page.text[:3000]}")
        except Exception as exc:  # noqa: BLE001
            log.append({"step": "fetch_url", "status": "error", "error": str(exc)})

    messages: list[dict[str, Any]] = [{"role": "system", "content": agent.system_prompt}]
    if context_blocks:
        messages.append(
            {
                "role": "system",
                "content": "Use only the retrieved context below when it is relevant. Cite URLs where used.\n\n"
                + "\n\n".join(context_blocks),
            }
        )
    messages.append({"role": "user", "content": question})

    try:
        result = await openrouter.chat(
            messages, model=execution.model, temperature=0.3, max_tokens=1200
        )
        output = result["text"]
        if agent.slug == "healthcare":
            output += MEDICAL_DISCLAIMER
        if agent.slug == "finance":
            output += FINANCE_DISCLAIMER
        execution.output = output
        execution.status = "completed"
        execution.tokens_in = result["tokens_in"]
        execution.tokens_out = result["tokens_out"]
        execution.cost = result["cost"]
        execution.log = log
        execution.latency_ms = int((time.perf_counter() - started) * 1000)
    except IntegrationNotConfigured as exc:
        execution.status = "failed"
        execution.error = str(exc)
        execution.log = log + [{"step": "model", "status": "not_configured", "error": str(exc)}]
        execution.latency_ms = int((time.perf_counter() - started) * 1000)
    except ProviderError as exc:
        execution.status = "failed"
        execution.error = str(exc)
        execution.log = log + [{"step": "model", "status": "error", "error": str(exc)}]
        execution.latency_ms = int((time.perf_counter() - started) * 1000)

    await db.commit()
    await db.refresh(execution)
    return execution

"""Automation workflow engine with nodes, logs, retries and approval gates."""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError
from ..models import Document, Workflow, WorkflowExecution
from . import agents as agent_service
from . import openrouter, rag, search
from .docs import extract_text
from .fetch import fetch_page, validate_url

settings = get_settings()

SUPPORTED_NODES = {
    "trigger",
    "ai",
    "search",
    "fetch_url",
    "doc_extract",
    "rag",
    "agent",
    "http",
    "transform",
    "notify",
    "approval",
}


def _order_nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not nodes:
        raise ValueError("Workflow graph has no nodes")
    ids = [node["id"] for node in nodes]
    incoming = {node_id: 0 for node_id in ids}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in ids}
    for edge in edges:
        src, dst = edge.get("from"), edge.get("to")
        if src in adjacency and dst in incoming:
            adjacency[src].append(dst)
            incoming[dst] += 1
    queue = [node for node in nodes if incoming[node["id"]] == 0]
    ordered: list[dict[str, Any]] = []
    while queue:
        node = queue.pop(0)
        ordered.append(node)
        for nxt in adjacency[node["id"]]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                queue.append(next(n for n in nodes if n["id"] == nxt))
    if len(ordered) != len(nodes):
        raise ValueError("Workflow graph contains a cycle")
    return ordered


async def _run_node(
    db: AsyncSession, user_id: int, node: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any]:
    kind = node.get("type")
    config = node.get("config") or {}
    if kind not in SUPPORTED_NODES:
        raise ValueError(f"Unsupported node type: {kind}")

    if kind == "trigger":
        return {"output": state.get("input", {})}

    if kind == "ai":
        prompt = config.get("prompt", "Summarize the input")
        text = str(state.get("text") or state.get("input") or "")
        result = await openrouter.chat(
            [
                {"role": "system", "content": "You are a workflow step. Return concise, useful output."},
                {"role": "user", "content": f"{prompt}\n\nInput:\n{text[:12000]}"},
            ],
            model=config.get("model") or settings.default_model,
            temperature=float(config.get("temperature", 0.4)),
            max_tokens=int(config.get("max_tokens", 800)),
        )
        return {"output": result["text"], "usage": result}

    if kind == "search":
        query = str(config.get("query") or state.get("text") or state.get("input") or "")[:500]
        result = await search.search(query, max_results=int(config.get("max_results", 5)))
        return {"output": result}

    if kind == "fetch_url":
        url = config.get("url") or state.get("text")
        if not url:
            raise ValueError("fetch_url node needs a url")
        page = await fetch_page(str(url))
        return {"output": {"url": page.final_url, "title": page.title, "text": page.text[:8000]}}

    if kind == "doc_extract":
        document = await db.get(Document, int(config.get("document_id", 0)))
        if document is None:
            raise ValueError("Document not found")
        text, meta = extract_text(Path(document.stored_path), document.filename, document.mime_type)
        return {"output": {"text": text[:20000], "meta": meta}}

    if kind == "rag":
        from .rag import answer_with_rag

        result = await answer_with_rag(
            db,
            int(config.get("knowledge_base_id", 0)),
            str(config.get("query") or state.get("text") or ""),
            model=config.get("model"),
        )
        return {"output": result}

    if kind == "agent":
        from sqlalchemy import select

        from ..models import Agent, User

        slug = config.get("agent_slug", "quantum")
        agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
        if agent is None:
            raise ValueError(f"Agent {slug} not found")
        user = await db.get(User, user_id)
        execution = await agent_service.execute_agent(
            db, user, agent, str(config.get("question") or state.get("text") or ""), use_tools=False
        )
        return {"output": {"agent": slug, "text": execution.output, "execution_id": execution.id}}

    if kind == "http":
        url = await validate_url(str(config.get("url", "")))
        method = str(config.get("method", "GET")).upper()
        if method not in {"GET", "POST"}:
            raise ValueError("Only GET and POST are allowed")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, url, json=config.get("body"), headers=config.get("headers"))
        return {"output": {"status": response.status_code, "body": response.text[:8000]}}

    if kind == "transform":
        data = state.get("text") or state.get("input")
        if "template" in config:
            return {"output": str(config["template"]).format(input=data, text=state.get("text", ""))}
        path = config.get("path")
        current: Any = data
        for part in str(path or "").split("."):
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                current = None
                break
        return {"output": current}

    if kind == "notify":
        # No outbound notification provider is configured by default. Record the notification
        # in the execution log instead of pretending an email/webhook was delivered.
        return {
            "output": {
                "channel": config.get("channel", "in-app"),
                "message": str(config.get("message") or state.get("text") or "")[:1000],
                "delivered": False,
                "note": "Recorded in workflow log; configure a webhook channel to deliver externally.",
            }
        }

    if kind == "approval":
        return {"output": {"approval_required": True, "message": config.get("message", "Approval required")}}

    raise ValueError(f"Unhandled node type: {kind}")


async def execute_workflow(
    db: AsyncSession,
    workflow: Workflow,
    execution: WorkflowExecution,
    *,
    approved: bool = False,
) -> WorkflowExecution:
    ordered = _order_nodes(workflow.graph)
    execution.status = "running"
    logs = execution.logs or []
    state: dict[str, Any] = {"input": execution.input, "text": ""}
    start_index = int((execution.output or {}).get("resume_index", 0))

    for index, node in enumerate(ordered):
        if index < start_index:
            continue
        started = time.perf_counter()
        entry: dict[str, Any] = {"node_id": node.get("id"), "type": node.get("type")}
        try:
            if node.get("type") == "approval" and not approved:
                execution.status = "awaiting_approval"
                execution.approval_token = uuid.uuid4().hex
                execution.output = {"resume_index": index, "awaiting_node": node.get("id"), "state": state}
                entry.update({"status": "awaiting_approval", "ms": 0})
                logs.append(entry)
                execution.logs = list(logs)
                await db.commit()
                return execution

            result = await _run_node(db, execution.user_id, node, state)
            output = result.get("output")
            state["text"] = output if isinstance(output, str) else state.get("text")
            state[node.get("id", "")] = output
            entry.update(
                {"status": "ok", "ms": int((time.perf_counter() - started) * 1000), "output": output}
            )
        except (IntegrationNotConfigured, ProviderError, ValueError, httpx.HTTPError) as exc:
            entry.update({"status": "error", "error": str(exc), "ms": int((time.perf_counter() - started) * 1000)})
            logs.append(entry)
            execution.logs = list(logs)
            execution.status = "failed"
            execution.error = str(exc)
            await db.commit()
            return execution

        logs.append(entry)
        execution.logs = list(logs)
        await db.commit()

    execution.status = "completed"
    execution.output = {"result": state.get("text") or state, "state": state}
    execution.logs = list(logs)
    await db.commit()
    await db.refresh(execution)
    return execution

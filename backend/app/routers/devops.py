"""Developer workspace: health, integrations, metrics, logs and redacted config."""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..logging_buffer import BUFFER
from ..models import (
    Agent,
    AgentExecution,
    APIUsage,
    Conversation,
    EvaluationRun,
    MediaItem,
    Message,
    User,
    Workflow,
    WorkflowExecution,
)
from ..services import openrouter

settings = get_settings()
router = APIRouter(prefix="/api/devops", tags=["devops"])


@router.get("/health")
async def health(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    checks: dict[str, str] = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"
    checks["storage"] = "ok" if os.access(settings.storage_dir, os.W_OK) else "read-only or missing"
    checks["openrouter"] = "configured" if settings.openrouter_configured else "not configured"
    checks["search"] = "configured" if settings.search_configured else "not configured"
    checks["ollama"] = "configured" if settings.ollama_configured else "not configured"
    checks["firebase"] = "configured" if settings.firebase_enabled else "not configured"
    return {"status": "ok" if checks["database"] == "ok" else "degraded", "time": time.time(), "checks": checks}


@router.get("/integrations")
async def integrations(user: User = Depends(get_current_user)) -> list[dict]:
    return [
        {"provider": "OpenRouter", "configured": settings.openrouter_configured, "env": "OPENROUTER_API_KEY"},
        {"provider": "Tavily search", "configured": settings.search_configured, "env": "TAVILY_API_KEY"},
        {"provider": "Ollama", "configured": settings.ollama_configured, "env": "OLLAMA_BASE_URL"},
        {"provider": "Firebase", "configured": settings.firebase_enabled, "env": "FIREBASE_PROJECT_ID"},
        {"provider": "Replicate video", "configured": bool(settings.replicate_api_token), "env": "REPLICATE_API_TOKEN"},
        {"provider": "OpenRouter embeddings", "configured": settings.embedding_provider == "openrouter" and settings.openrouter_configured, "env": "EMBEDDING_PROVIDER=openrouter"},
    ]


@router.get("/config")
async def config(_: User = Depends(require_admin)) -> dict:
    """Redacted configuration: secrets are never returned."""
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "default_model": settings.default_model,
        "fallback_models": settings.fallback_model_list,
        "embedding_provider": settings.embedding_provider,
        "search_provider": settings.search_provider,
        "database": settings.database_url.split("://")[0],
        "storage_dir": str(settings.storage_dir),
        "max_upload_mb": settings.max_upload_mb,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "cors_origins": settings.cors_origin_list,
    }


@router.get("/usage")
async def usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = (
        await db.execute(
            select(
                func.count(APIUsage.id),
                func.coalesce(func.sum(APIUsage.tokens_in), 0),
                func.coalesce(func.sum(APIUsage.tokens_out), 0),
                func.coalesce(func.sum(APIUsage.cost), 0.0),
            ).where(APIUsage.user_id == user.id)
        )
    ).one()
    return {"requests": rows[0], "tokens_in": rows[1], "tokens_out": rows[2], "cost": round(float(rows[3]), 6)}


@router.get("/metrics")
async def metrics(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    async def count(model, condition=None) -> int:
        query = select(func.count()).select_from(model)
        if condition is not None:
            query = query.where(condition)
        return int((await db.execute(query)).scalar_one())

    return {
        "conversations": await count(Conversation, Conversation.user_id == user.id),
        "messages": await count(
            Message, Message.conversation_id.in_(select(Conversation.id).where(Conversation.user_id == user.id))
        ),
        "media": await count(MediaItem, MediaItem.user_id == user.id),
        "agent_executions": await count(AgentExecution, AgentExecution.user_id == user.id),
        "workflows": await count(Workflow, Workflow.user_id == user.id),
        "workflow_executions": await count(WorkflowExecution, WorkflowExecution.user_id == user.id),
        "evaluation_runs": await count(EvaluationRun, EvaluationRun.user_id == user.id),
        "agents_available": await count(Agent),
    }


@router.get("/logs")
async def logs(user: User = Depends(require_admin)) -> list[dict]:
    return list(BUFFER)[-200:]


@router.get("/openrouter-models")
async def openrouter_models(user: User = Depends(get_current_user)) -> dict:
    if not settings.openrouter_configured:
        return {"configured": False, "models": []}
    models = await openrouter.catalog.get()
    return {"configured": True, "count": len(models), "models": models[:50]}

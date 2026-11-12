"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import SessionLocal, init_db
from .errors import IntegrationNotConfigured, ProviderError, RateLimited, SSRFBlocked
from .logging_buffer import install as install_log_buffer
from .middleware import RateLimitMiddleware
from .routers import (
    agents,
    auth,
    chatbots,
    chat,
    devops,
    evals,
    knowledge,
    mcp,
    media,
    models,
    ollama,
    search,
    url,
    workflows,
)
from .services.agents import seed_agents

settings = get_settings()
logging.basicConfig(level=logging.INFO)
install_log_buffer()
logger = logging.getLogger("nexamind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with SessionLocal() as db:
        await seed_agents(db)
    logger.info("NexaMind AI started (env=%s)", settings.environment)
    yield


app = FastAPI(title="NexaMind AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(IntegrationNotConfigured)
async def integration_not_configured(_: Request, exc: IntegrationNotConfigured):
    return JSONResponse(
        status_code=503,
        content={
            "detail": exc.message,
            "code": "integration_not_configured",
            "provider": exc.provider,
            "env_var": exc.env_var,
        },
    )


@app.exception_handler(ProviderError)
async def provider_error(_: Request, exc: ProviderError):
    return JSONResponse(
        status_code=exc.status_code or 502,
        content={"detail": str(exc), "code": "provider_error", "provider": exc.provider},
    )


@app.exception_handler(SSRFBlocked)
async def ssrf_blocked(_: Request, exc: SSRFBlocked):
    return JSONResponse(status_code=400, content={"detail": str(exc), "code": "ssrf_blocked"})


@app.exception_handler(RateLimited)
async def rate_limited(_: Request, exc: RateLimited):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "code": "rate_limited"},
        headers={"Retry-After": str(exc.retry_after)},
    )


for module in (auth, chat, models, search, url, knowledge, media, agents, evals, workflows, chatbots, mcp, ollama, devops):
    app.include_router(module.router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
        "openrouter_configured": settings.openrouter_configured,
        "search_configured": settings.search_configured,
        "ollama_configured": settings.ollama_configured,
    }


@app.get("/api/meta")
async def meta() -> dict:
    return {
        "name": "NexaMind AI",
        "tagline": "One workspace for chat, research, agents, and automation.",
        "version": "1.0.0",
        "features": [
            "chat", "search", "deep_research", "image_generation", "video_generation",
            "media", "agents", "automation", "chatbot_studio", "knowledge_base",
            "mcp", "evaluation", "devtools", "settings",
        ],
    }


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

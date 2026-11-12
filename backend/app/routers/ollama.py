"""Ollama API routes: health, models, generate, embeddings."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import HFInferenceRequest
from ..services import ollama

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/status")
async def status(user: User = Depends(get_current_user)) -> dict:
    return await ollama.health()


@router.get("/models")
async def models(user: User = Depends(get_current_user)) -> dict:
    return {"configured": ollama._configured(), "models": await ollama.list_models()}


@router.post("/generate")
async def generate(payload: HFInferenceRequest, user: User = Depends(get_current_user)) -> dict:
    return await ollama.generate(payload.prompt, payload.model or None, payload.max_tokens)


@router.post("/embeddings")
async def embeddings(payload: dict, user: User = Depends(get_current_user)) -> dict:
    texts = payload.get("texts") or []
    if not isinstance(texts, list) or not texts:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="texts must be a non-empty list")
    vectors = await ollama.embed([str(t) for t in texts])
    return {"count": len(vectors), "dimensions": len(vectors[0]) if vectors else 0, "embeddings": vectors}
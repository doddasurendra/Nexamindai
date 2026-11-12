"""Global News Intelligence routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..deps import get_current_user
from ..models import User
from ..services import news as news_service

router = APIRouter(prefix="/api/news", tags=["news"])


class SummarizeRequest(BaseModel):
    title: str
    url: str = ""
    content: str = ""


@router.get("/headlines")
async def headlines(
    category: str = Query(default="world"),
    limit: int = Query(default=12, ge=1, le=30),
    user: User = Depends(get_current_user),
) -> list[dict]:
    return await news_service.get_headlines(category, limit)


@router.get("/categories")
async def categories(user: User = Depends(get_current_user)) -> list[dict]:
    return news_service.list_categories()


@router.get("/search")
async def search_news(
    q: str = Query(min_length=2),
    limit: int = Query(default=8, ge=1, le=20),
    user: User = Depends(get_current_user),
) -> dict:
    return await news_service.search_news(q, limit)


@router.post("/summarize")
async def summarize(payload: SummarizeRequest, user: User = Depends(get_current_user)) -> dict:
    summary = await news_service.summarize_article(payload.title, payload.url, payload.content)
    return {"summary": summary}

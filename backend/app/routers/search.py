"""Web search and deep research endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import ResearchRun, User
from ..schemas import ResearchOut, ResearchRequest, SearchRequest, SearchResponse
from ..services import research, search

router = APIRouter(prefix="/api", tags=["research"])


@router.post("/search", response_model=SearchResponse)
async def web_search(payload: SearchRequest, user: User = Depends(get_current_user)) -> SearchResponse:
    result = await search.search(payload.query, max_results=payload.max_results)
    return SearchResponse(**result)


@router.post("/research", response_model=ResearchOut)
async def deep_research(
    payload: ResearchRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ResearchOut:
    run = await research.run_research(db, user.id, payload.question, payload.depth)
    return ResearchOut.model_validate(run)


@router.get("/research", response_model=list[ResearchOut])
async def list_research(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[ResearchOut]:
    runs = (
        await db.execute(select(ResearchRun).where(ResearchRun.user_id == user.id).order_by(ResearchRun.id.desc()))
    ).scalars().all()
    return [ResearchOut.model_validate(r) for r in runs]


@router.get("/research/{run_id}", response_model=ResearchOut)
async def get_research(run_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ResearchOut:
    run = await db.get(ResearchRun, run_id)
    if run is None or run.user_id != user.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Research run not found")
    return ResearchOut.model_validate(run)

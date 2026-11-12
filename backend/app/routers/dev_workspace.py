"""Software Development Workspace routes: GitHub repo inspection."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import get_current_user
from ..models import User
from ..services import dev_workspace

router = APIRouter(prefix="/api/dev-workspace", tags=["dev-workspace"])


class InspectRequest(BaseModel):
    repo: str = Field(min_length=3, max_length=200)


@router.post("/inspect")
async def inspect(payload: InspectRequest, user: User = Depends(get_current_user)) -> dict:
    try:
        return await dev_workspace.inspect_repo(payload.repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

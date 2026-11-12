"""AI Command Center routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..services import command_center

router = APIRouter(prefix="/api/command-center", tags=["command-center"])


class CommandRequest(BaseModel):
    objective: str = Field(min_length=3, max_length=4000)


@router.post("/execute")
async def execute(payload: CommandRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    return await command_center.execute_plan(db, user, payload.objective.strip())

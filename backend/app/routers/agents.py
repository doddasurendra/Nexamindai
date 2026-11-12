"""Agent catalog, routing, execution and logs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import Agent, AgentExecution, User
from ..schemas import AgentExecutionOut, AgentOut, AgentRunRequest
from ..services import agents as agent_service

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[AgentOut]:
    rows = (await db.execute(select(Agent).order_by(Agent.id))).scalars().all()
    if not rows:
        await agent_service.seed_agents(db)
        rows = (await db.execute(select(Agent).order_by(Agent.id))).scalars().all()
    return [AgentOut.model_validate(a) for a in rows]


@router.post("/route")
async def route(payload: dict, user: User = Depends(get_current_user)) -> dict:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=422, detail="question is required")
    return await agent_service.route_agent(question)


@router.post("/run", response_model=AgentExecutionOut)
async def run_agent(
    payload: AgentRunRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentExecutionOut:
    slug = payload.agent_slug
    if not slug:
        route_result = await agent_service.route_agent(payload.input)
        slug = route_result["agent"]
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found")
    execution = await agent_service.execute_agent(
        db, user, agent, payload.input, model=payload.model, use_tools=payload.use_tools
    )
    return AgentExecutionOut.model_validate(execution)


@router.get("/executions", response_model=list[AgentExecutionOut])
async def list_executions(
    agent_slug: str | None = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AgentExecutionOut]:
    query = select(AgentExecution).where(AgentExecution.user_id == user.id)
    if agent_slug:
        agent = (await db.execute(select(Agent).where(Agent.slug == agent_slug))).scalar_one_or_none()
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        query = query.where(AgentExecution.agent_id == agent.id)
    rows = (await db.execute(query.order_by(AgentExecution.id.desc()).limit(100))).scalars().all()
    return [AgentExecutionOut.model_validate(e) for e in rows]


@router.get("/executions/{execution_id}", response_model=AgentExecutionOut)
async def get_execution(
    execution_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentExecutionOut:
    execution = await db.get(AgentExecution, execution_id)
    if execution is None or execution.user_id != user.id:
        raise HTTPException(status_code=404, detail="Execution not found")
    return AgentExecutionOut.model_validate(execution)

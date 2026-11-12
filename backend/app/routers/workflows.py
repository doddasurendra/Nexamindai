"""Workflow CRUD, execution and approval gates."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import User, Workflow, WorkflowExecution
from ..schemas import (
    ApprovalRequest,
    WorkflowCreate,
    WorkflowExecutionOut,
    WorkflowOut,
    WorkflowRunRequest,
)
from ..services import workflows as engine

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowOut, status_code=201)
async def create_workflow(
    payload: WorkflowCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> WorkflowOut:
    workflow = Workflow(user_id=user.id, name=payload.name, description=payload.description, graph=payload.graph)
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return WorkflowOut.model_validate(workflow)


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[WorkflowOut]:
    rows = (
        await db.execute(select(Workflow).where(Workflow.user_id == user.id).order_by(Workflow.id.desc()))
    ).scalars().all()
    return [WorkflowOut.model_validate(w) for w in rows]


@router.patch("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(
    workflow_id: int,
    payload: WorkflowCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowOut:
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None or workflow.user_id != user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.name = payload.name
    workflow.description = payload.description
    workflow.graph = payload.graph
    workflow.version += 1
    await db.commit()
    await db.refresh(workflow)
    return WorkflowOut.model_validate(workflow)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None or workflow.user_id != user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.delete(workflow)
    await db.commit()
    from fastapi import Response

    return Response(status_code=204)


@router.post("/{workflow_id}/run", response_model=WorkflowExecutionOut)
async def run_workflow(
    workflow_id: int,
    payload: WorkflowRunRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowExecutionOut:
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None or workflow.user_id != user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    execution = WorkflowExecution(
        workflow_id=workflow.id, user_id=user.id, status="pending", input=payload.input, logs=[]
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    execution = await engine.execute_workflow(db, workflow, execution)
    return WorkflowExecutionOut.model_validate(execution)


@router.post("/executions/{execution_id}/approve", response_model=WorkflowExecutionOut)
async def approve(
    execution_id: int,
    payload: ApprovalRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowExecutionOut:
    execution = await db.get(WorkflowExecution, execution_id)
    if execution is None or execution.user_id != user.id:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status != "awaiting_approval" or execution.approval_token != payload.token:
        raise HTTPException(status_code=409, detail="Execution is not awaiting this approval token")
    if not payload.approved:
        execution.status = "rejected"
        await db.commit()
        return WorkflowExecutionOut.model_validate(execution)
    execution.approval_token = None
    execution.status = "running"
    workflow = await db.get(Workflow, execution.workflow_id)
    execution.output = {"resume_index": int((execution.output or {}).get("resume_index", 0)) + 1}
    await db.commit()
    execution = await engine.execute_workflow(db, workflow, execution, approved=True)
    return WorkflowExecutionOut.model_validate(execution)


@router.get("/executions", response_model=list[WorkflowExecutionOut])
async def list_executions(
    workflow_id: int | None = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[WorkflowExecutionOut]:
    query = select(WorkflowExecution).where(WorkflowExecution.user_id == user.id)
    if workflow_id:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)
    rows = (await db.execute(query.order_by(WorkflowExecution.id.desc()).limit(100))).scalars().all()
    return [WorkflowExecutionOut.model_validate(e) for e in rows]

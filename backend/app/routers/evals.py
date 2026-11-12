"""Evaluation datasets, benchmark runs and comparison."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import EvaluationDataset, EvaluationRun, User
from ..schemas import EvalDatasetCreate, EvalDatasetOut, EvalRunOut, EvalRunRequest
from ..services import eval as eval_service

router = APIRouter(prefix="/api/evals", tags=["evaluation"])


@router.post("/datasets", response_model=EvalDatasetOut, status_code=201)
async def create_dataset(
    payload: EvalDatasetCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> EvalDatasetOut:
    dataset = EvaluationDataset(user_id=user.id, name=payload.name, items=payload.items)
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return EvalDatasetOut.model_validate(dataset)


@router.get("/datasets", response_model=list[EvalDatasetOut])
async def list_datasets(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[EvalDatasetOut]:
    rows = (
        await db.execute(select(EvaluationDataset).where(EvaluationDataset.user_id == user.id).order_by(EvaluationDataset.id.desc()))
    ).scalars().all()
    return [EvalDatasetOut.model_validate(d) for d in rows]


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    dataset = await db.get(EvaluationDataset, dataset_id)
    if dataset is None or dataset.user_id != user.id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await db.delete(dataset)
    await db.commit()
    from fastapi import Response

    return Response(status_code=204)


@router.post("/runs", response_model=EvalRunOut)
async def run_eval(
    payload: EvalRunRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> EvalRunOut:
    dataset = await db.get(EvaluationDataset, payload.dataset_id)
    if dataset is None or dataset.user_id != user.id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    run = await eval_service.run_evaluation(
        db, dataset=dataset, user_id=user.id, model=payload.model, max_items=payload.max_items
    )
    return EvalRunOut.model_validate(run)


@router.get("/runs", response_model=list[EvalRunOut])
async def list_runs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[EvalRunOut]:
    rows = (
        await db.execute(select(EvaluationRun).where(EvaluationRun.user_id == user.id).order_by(EvaluationRun.id.desc()))
    ).scalars().all()
    return [EvalRunOut.model_validate(r) for r in rows]


@router.get("/runs/{run_id}", response_model=EvalRunOut)
async def get_run(run_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EvalRunOut:
    run = await db.get(EvaluationRun, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Run not found")
    return EvalRunOut.model_validate(run)


@router.get("/compare")
async def compare_runs(run_a: int, run_b: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = []
    for run_id in (run_a, run_b):
        run = await db.get(EvaluationRun, run_id)
        if run is None or run.user_id != user.id:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        rows.append({"id": run.id, "model": run.model, "metrics": run.metrics})
    return {"runs": rows}

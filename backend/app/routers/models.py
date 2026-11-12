"""Model catalog and provider status."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import AIModel, User
from ..schemas import ModelOut
from ..services import openrouter

settings = get_settings()
router = APIRouter(prefix="/api/models", tags=["models"])


async def refresh_catalog(db: AsyncSession) -> list[AIModel]:
    catalog = await openrouter.catalog.get(force=True)
    existing = {m.model_id: m for m in (await db.execute(select(AIModel))).scalars().all()}
    for item in catalog:
        model = existing.get(item["model_id"])
        if model is None:
            model = AIModel(model_id=item["model_id"])
            db.add(model)
        model.name = item["name"]
        model.context_window = item["context_window"]
        model.input_price = item["input_price"]
        model.output_price = item["output_price"]
        model.capabilities = item["capabilities"]
    await db.commit()
    return (await db.execute(select(AIModel).order_by(AIModel.name))).scalars().all()


@router.get("")
async def list_models(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    models = (await db.execute(select(AIModel).order_by(AIModel.name))).scalars().all()
    if not models and settings.openrouter_configured:
        try:
            models = await refresh_catalog(db)
        except Exception:  # noqa: BLE001 - surfaced through the configured flag and empty list
            models = []
    return {
        "configured": settings.openrouter_configured,
        "default_model": settings.default_model,
        "models": [ModelOut.model_validate(m).model_dump() for m in models],
    }


@router.post("/refresh")
async def refresh(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    models = await refresh_catalog(db)
    return {"count": len(models), "models": [ModelOut.model_validate(m).model_dump() for m in models]}

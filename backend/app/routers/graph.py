"""Global Knowledge Graph routes: entities and relationships."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import KnowledgeEntity, KnowledgeRelation, User

router = APIRouter(prefix="/api/graph", tags=["knowledge-graph"])


class EntityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    entity_type: str = Field(default="concept", max_length=60)
    summary: str = ""
    source_url: str = ""
    tags: list[str] = []
    confidence: str = "derived"


class RelationCreate(BaseModel):
    source_id: int
    target_id: int
    relation_type: str = Field(default="related_to", max_length=80)
    confidence: str = "inferred"
    evidence: str = ""


@router.get("/entities")
async def list_entities(q: str | None = Query(default=None), entity_type: str | None = Query(default=None), limit: int = Query(default=50, le=200), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    stmt = select(KnowledgeEntity)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(KnowledgeEntity.name.ilike(pattern), KnowledgeEntity.summary.ilike(pattern), KnowledgeEntity.tags.cast(str).ilike(pattern)))
    if entity_type:
        stmt = stmt.where(KnowledgeEntity.entity_type == entity_type)
    rows = (await db.execute(stmt.order_by(KnowledgeEntity.updated_at.desc()).limit(limit))).scalars().all()
    return [_entity_dict(e) for e in rows]


@router.post("/entities", status_code=201)
async def create_entity(payload: EntityCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    entity = KnowledgeEntity(
        name=payload.name.strip(),
        entity_type=payload.entity_type.strip() or "concept",
        summary=payload.summary.strip(),
        source_url=payload.source_url.strip(),
        tags=payload.tags,
        confidence=payload.confidence,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return _entity_dict(entity)


@router.get("/entities/{entity_id}")
async def entity_detail(entity_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    entity = await db.get(KnowledgeEntity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    relations = (
        await db.execute(
            select(KnowledgeRelation).where(or_(KnowledgeRelation.source_id == entity_id, KnowledgeRelation.target_id == entity_id))
        )
    ).scalars().all()
    related_ids = {r.source_id for r in relations} | {r.target_id for r in relations}
    related = (await db.execute(select(KnowledgeEntity).where(KnowledgeEntity.id.in_(related_ids)))).scalars().all() if related_ids else []
    return {
        **_entity_dict(entity),
        "relations": [
            {
                "id": r.id,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "relation_type": r.relation_type,
                "confidence": r.confidence,
                "evidence": r.evidence,
            }
            for r in relations
        ],
        "related": [_entity_dict(e) for e in related],
    }


@router.post("/relations", status_code=201)
async def create_relation(payload: RelationCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    for eid in (payload.source_id, payload.target_id):
        if await db.get(KnowledgeEntity, eid) is None:
            raise HTTPException(status_code=404, detail=f"Entity {eid} not found")
    relation = KnowledgeRelation(
        source_id=payload.source_id,
        target_id=payload.target_id,
        relation_type=payload.relation_type.strip() or "related_to",
        confidence=payload.confidence,
        evidence=payload.evidence.strip(),
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return {"id": relation.id, "source_id": relation.source_id, "target_id": relation.target_id, "relation_type": relation.relation_type}


@router.delete("/entities/{entity_id}", status_code=204)
async def delete_entity(entity_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    entity = await db.get(KnowledgeEntity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    await db.delete(entity)
    await db.commit()


def _entity_dict(entity: KnowledgeEntity) -> dict:
    return {
        "id": entity.id,
        "name": entity.name,
        "entity_type": entity.entity_type,
        "summary": entity.summary,
        "source_url": entity.source_url,
        "tags": entity.tags,
        "confidence": entity.confidence,
    }

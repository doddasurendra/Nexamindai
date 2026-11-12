"""API Universe routes: catalogue browsing, search, categories, ingestion, testing."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import APIAPI, APICategory, MCPServer, User
from ..services.api_catalog import CatalogImporter
from ..services.api_connector import ApiConnector
from ..services.fetch import validate_url

router = APIRouter(prefix="/api/apis", tags=["api-universe"])


async def _get_public(db: AsyncSession, api_id: int) -> APIAPI | None:
    return await db.get(APIAPI, api_id)


@router.get("/categories")
async def list_categories(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.execute(select(APICategory).order_by(APICategory.name))).scalars().all()
    return [{"name": c.name, "api_count": c.api_count, "synced_at": c.synced_at.isoformat() if c.synced_at else None} for c in rows]


@router.get("/apis")
async def list_apis(
    category: str | None = Query(default=None),
    query: str | None = Query(default=None),
    auth_type: str | None = Query(default=None),
    pricing: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(APIAPI)
    if category:
        stmt = stmt.where(APIAPI.category_name == category)
    if auth_type:
        stmt = stmt.where(APIAPI.auth_type == auth_type)
    if pricing:
        stmt = stmt.where(APIAPI.pricing_class == pricing)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(APIAPI.name.ilike(pattern), APIAPI.description.ilike(pattern)))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.order_by(APIAPI.name).limit(limit).offset(offset))).scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "category": a.category_name,
                "auth_type": a.auth_type,
                "https": a.https,
                "cors": a.cors,
                "pricing": a.pricing_class,
                "status": a.status,
                "docs_url": a.docs_url,
                "health": "unknown",
            }
            for a in rows
        ],
    }


@router.get("/apis/{api_id}")
async def api_detail(api_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    api = await db.get(APIAPI, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    return {
        "id": api.id,
        "name": api.name,
        "description": api.description,
        "category": api.category_name,
        "auth_type": api.auth_type,
        "https": api.https,
        "cors": api.cors,
        "pricing": api.pricing_class,
        "status": api.status,
        "docs_url": api.docs_url,
        "provider": api.provider.name if api.provider else None,
    }


@router.post("/test/{api_id}")
async def test_api(api_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    api = await db.get(APIAPI, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    if not api.base_url:
        raise HTTPException(status_code=422, detail="API has no base URL to test")
    connector = ApiConnector(db, user.id)
    result = await connector.get(api.base_url)
    return result


@router.post("/ingest")
async def ingest_catalog(user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> dict:
    path = Path("public_apis_catalog.json")
    if not path.exists():
        # Try from project root
        project_root = Path(__file__).resolve().parents[3]
        path = project_root / "backend" / "public_apis_catalog.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="public_apis_catalog.json not found")
    importer = CatalogImporter(db)
    counts = await importer.import_catalog(str(path))
    return counts


@router.get("/featured")
async def featured_apis(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Return some well-known, no-auth, HTTPS APIs for quick access."""
    featured = [
        {"name": "Open Library", "url": "https://openlibrary.org/developers/api", "category": "Books", "description": "Books and related data", "auth": "none", "pricing": "free"},
        {"name": "Bible API", "url": "https://bible-api.com/", "category": "Books", "description": "Free Bible API", "auth": "none", "pricing": "free"},
        {"name": "Nager.Date", "url": "https://date.nager.at", "category": "Calendar", "description": "Public holidays for 90+ countries", "auth": "none", "pricing": "free"},
        {"name": "Abstract Calendar", "url": "https://abstractapi.com/api/holidays", "category": "Calendar", "description": "Holidays API", "auth": "none", "pricing": "freemium"},
    ]
    return featured


@router.get("/mcp-servers")
async def list_mcp_servers(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.execute(select(MCPServer).order_by(MCPServer.name))).scalars().all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "auth": m.auth_type,
            "transport": m.transport,
            "install_links": m.install_links,
            "status": m.status,
        }
        for m in rows
    ]
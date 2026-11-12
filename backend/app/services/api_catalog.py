"""Catalog ingestion service: imports public-apis catalogue into NexaMind DB."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import (
    APIAPI,
    APICategory,
    APIProvider,
    APIConnection,
    APIEndpoint,
    MCPServer,
    User,
)

settings = get_settings()


def _provider_key(name: str | None) -> str | None:
    if not name:
        return None
    return name.strip()


class CatalogImporter:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def import_catalog(self, json_path: str | Path) -> dict[str, int]:
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Catalog JSON not found: {path}")
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)

        counts = {"categories": 0, "providers": 0, "apis": 0, "mcps": 0}

        # --- Categories first ---
        cats = data.get("categories", [])
        cat_map: dict[str, APICategory] = {}
        for cat_name in cats:
            existing = (
                await self.db.execute(select(APICategory).where(APICategory.name == cat_name))
            ).scalar_one_or_none()
            if not existing:
                existing = APICategory(name=cat_name, description="", api_count=0)
                self.db.add(existing)
                await self.db.flush()
            cat_map[cat_name] = existing
            counts["categories"] += 1
        await self.db.commit()

        # --- Providers ---
        prov_map: dict[str, APIProvider] = {}
        for api in data.get("apis", []):
            prov_name = _derive_provider_name(api.get("name", ""), api.get("url", ""))
            if prov_name not in prov_map:
                existing = (
                    await self.db.execute(
                        select(APIProvider).where(APIProvider.name == prov_name)
                    )
                ).scalar_one_or_none()
                if not existing:
                    existing = APIProvider(
                        name=prov_name,
                        website=api.get("url", ""),
                        documentation_url="",
                    )
                    self.db.add(existing)
                    await self.db.flush()
                prov_map[prov_name] = existing
                counts["providers"] += 1
        await self.db.commit()

        # --- APIs ---
        for api in data.get("apis", []):
            category = cat_map.get(api.get("category", ""))
            provider = prov_map.get(_derive_provider_name(api.get("name", ""), api.get("url", "")))
            pricing = classify_pricing(api.get("auth", ""), api.get("name", ""), api.get("url", ""))

            existing = (
                await self.db.execute(
                    select(APIAPI).where(
                        APIAPI.name == api["name"], APIAPI.category_name == api.get("category", "")
                    )
                )
            ).scalar_one_or_none()
            if existing:
                # Refresh fields
                existing.description = api.get("description", "")
                existing.base_url = api.get("url", "")
                existing.docs_url = api.get("url", "")
                existing.auth_type = normalize_auth(api.get("auth", ""))
                existing.https = api.get("https", "Unknown")
                existing.cors = api.get("cors", "Unknown")
                existing.pricing_class = pricing
                existing.category = category
                existing.provider = provider
                await self.db.flush()
            else:
                existing = APIAPI(
                    name=api["name"],
                    description=api.get("description", ""),
                    category_name=api.get("category", ""),
                    category=category,
                    provider=provider,
                    base_url=api.get("url", ""),
                    docs_url=api.get("url", ""),
                    auth_type=normalize_auth(api.get("auth", "")),
                    https=api.get("https", "Unknown"),
                    cors=api.get("cors", "Unknown"),
                    pricing_class=pricing,
                    status="discovered",
                    tags=[],
                )
                self.db.add(existing)
                await self.db.flush()
            counts["apis"] += 1

        await self.db.commit()

        # --- MCPs ---
        for mcp in data.get("mcps", []):
            existing = (
                await self.db.execute(select(MCPServer).where(MCPServer.name == mcp["name"]))
            ).scalar_one_or_none()
            if not existing:
                existing = MCPServer(
                    name=mcp["name"],
                    description=mcp.get("description", ""),
                    url=mcp.get("url", ""),
                    auth_type=mcp.get("auth", "none"),
                    transport=mcp.get("transport", "stdio"),
                    install_links=mcp.get("install", ""),
                    status="discovered",
                )
                self.db.add(existing)
                counts["mcps"] += 1
        await self.db.commit()

        return counts


def _derive_provider_name(name: str, url: str) -> str:
    """Derive a provider name from the API name/URL when no explicit provider exists."""
    n = (name or "").strip()
    u = (url or "").strip()
    # Use the domain as provider fallback
    if u:
        parts = u.split("//")[-1].split("/")[0]
        domain = parts.split(":")[0]
        if domain:
            return domain
    return n or "Unknown"


def normalize_auth(auth: str) -> str:
    a = (auth or "").strip().lower()
    if a in ("api key", "apikey", "api key "):
        return "apiKey"
    if a in ("oauth", "oauth2"):
        return "OAuth"
    if a in ("no", "none"):
        return "none"
    return a or "none"


def classify_pricing(auth: str, name: str, url: str) -> str:
    """Heuristic pricing classification - does NOT assume free."""
    combined = f"{name} {url} {auth}".lower()
    paid_hints = ["paid", "subscription", "premium", "enterprise", "credit", "billing", "pro plan"]
    if any(h in combined for h in paid_hints):
        return "freemium"
    return "free"  # Default assumption for public-apis entries; verified individually


async def seed_connections_for_free_noauth_apis(db: AsyncSession, user_id: int) -> int:
    """Configure connections for eligible free no-auth APIs (discovered only)."""
    free_no_auth = (
        await db.execute(
            select(APIAPI).where(
                APIAPI.auth_type == "none",
                APIAPI.https == "Yes",
                APIAPI.cors.in_(["Yes", "Unknown"]),
                APIAPI.status == "discovered",
            )
        )
    ).scalars().all()

    count = 0
    for api in free_no_auth:
        conn = APIConnection(
            user_id=user_id,
            api_id=api.id,
            connection_name=f"{api.name} connection",
            enabled=True,
            approved=True,
            status="connected",
        )
        db.add(conn)
        count += 1
    await db.commit()
    return count


async def sync_from_github(db: AsyncSession, user_id: int) -> dict[str, int]:
    """Re-sync from GitHub README (placeholder - calls import_catalog with latest JSON)."""
    from pathlib import Path
    json_path = Path("public_apis_catalog.json")
    importer = CatalogImporter(db)
    counts = await importer.import_catalog(json_path)
    synced = await seed_connections_for_free_noauth_apis(db, user_id)
    counts["auto_connected_free_noauth"] = synced
    return counts

"""Async database engine/session setup with SQLite (dev) and PostgreSQL (prod) support."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

settings = get_settings()
settings.ensure_directories()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables when enabled. In production prefer Alembic migrations."""
    from . import models  # noqa: F401  (register metadata)

    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

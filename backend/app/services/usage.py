"""Usage accounting helper."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import APIUsage


async def record_usage(
    db: AsyncSession,
    *,
    user_id: int | None,
    endpoint: str,
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost: float,
    latency_ms: int,
) -> None:
    db.add(
        APIUsage(
            user_id=user_id,
            endpoint=endpoint,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            latency_ms=latency_ms,
        )
    )
    await db.commit()

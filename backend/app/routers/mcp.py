"""MCP connection management, tool discovery and permissioned execution."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import AuditLog, MCPConnection, User
from ..schemas import MCPCallRequest, MCPCreate, MCPOut
from ..services import mcp as mcp_service

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


async def _own(db: AsyncSession, connection_id: int, user: User) -> MCPConnection:
    connection = await db.get(MCPConnection, connection_id)
    if connection is None or connection.user_id != user.id:
        raise HTTPException(status_code=404, detail="MCP connection not found")
    return connection


@router.post("/connections", response_model=MCPOut, status_code=201)
async def create_connection(
    payload: MCPCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MCPOut:
    connection = MCPConnection(
        user_id=user.id,
        name=payload.name,
        url=payload.url,
        headers_encrypted=mcp_service.encrypt_headers(payload.headers),
        allowed_tools=payload.allowed_tools,
        require_approval=payload.require_approval,
        allow_private=payload.allow_private,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return MCPOut.model_validate(connection)


@router.get("/connections", response_model=list[MCPOut])
async def list_connections(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[MCPOut]:
    rows = (
        await db.execute(select(MCPConnection).where(MCPConnection.user_id == user.id).order_by(MCPConnection.id.desc()))
    ).scalars().all()
    return [MCPOut.model_validate(c) for c in rows]


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(connection_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    connection = await _own(db, connection_id, user)
    await db.delete(connection)
    await db.commit()
    from fastapi import Response

    return Response(status_code=204)


@router.post("/connections/{connection_id}/connect", response_model=MCPOut)
async def connect(connection_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> MCPOut:
    connection = await _own(db, connection_id, user)
    try:
        _init, tools = await mcp_service.connect(
            connection.url, mcp_service.decrypt_headers(connection.headers_encrypted), allow_private=connection.allow_private
        )
        connection.tools = tools
        connection.status = "connected"
        connection.last_error = None
    except Exception as exc:  # noqa: BLE001
        connection.status = "error"
        connection.last_error = str(exc)
    connection.last_checked = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(connection)
    return MCPOut.model_validate(connection)


@router.post("/connections/{connection_id}/call")
async def call_tool(
    connection_id: int,
    payload: MCPCallRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    connection = await _own(db, connection_id, user)
    if not connection.enabled:
        raise HTTPException(status_code=409, detail="Connection is disabled")
    if connection.allowed_tools and payload.tool not in connection.allowed_tools:
        raise HTTPException(status_code=403, detail=f"Tool '{payload.tool}' is not in the allowlist")
    if connection.require_approval and not payload.approved:
        raise HTTPException(status_code=428, detail="This connection requires explicit approval for tool execution")
    try:
        result = await mcp_service.call_tool(
            connection.url,
            mcp_service.decrypt_headers(connection.headers_encrypted),
            payload.tool,
            payload.arguments,
            allow_private=connection.allow_private,
        )
        db.add(
            AuditLog(
                user_id=user.id,
                action="mcp.tool.call",
                detail={"connection_id": connection.id, "tool": payload.tool, "ok": True},
            )
        )
        await db.commit()
        return result
    except Exception as exc:  # noqa: BLE001
        db.add(
            AuditLog(
                user_id=user.id,
                action="mcp.tool.call",
                detail={"connection_id": connection.id, "tool": payload.tool, "ok": False, "error": str(exc)},
            )
        )
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/logs")
async def mcp_logs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user.id, AuditLog.action == "mcp.tool.call")
            .order_by(AuditLog.id.desc())
            .limit(100)
        )
    ).scalars().all()
    return [{"id": row.id, "detail": row.detail, "created_at": row.created_at.isoformat()} for row in rows]

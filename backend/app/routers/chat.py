"""Conversation CRUD and streaming chat with persistence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..models import Conversation, Message, User
from ..schemas import (
    ChatRequest,
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)
from ..services import openrouter
from ..services.usage import record_usage

settings = get_settings()
router = APIRouter(prefix="/api", tags=["chat"])


async def _get_conversation(db: AsyncSession, conversation_id: int, user: User) -> Conversation:
    conversation = (
        await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _history_messages(conversation: Conversation, extra_system: str | None = None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if conversation.system_prompt:
        messages.append({"role": "system", "content": conversation.system_prompt})
    for message in conversation.messages:
        if message.role in {"user", "assistant"} and message.content:
            messages.append({"role": message.role, "content": message.content})
    if extra_system:
        messages.insert(0, {"role": "system", "content": extra_system})
    return messages


async def _save_assistant(
    db: AsyncSession,
    conversation: Conversation,
    *,
    content: str,
    model: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost: float = 0.0,
    error: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=cost,
        error=error,
    )
    db.add(message)
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(message)
    return message


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    payload: ConversationCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ConversationOut:
    conversation = Conversation(
        user_id=user.id,
        title=payload.title or "New chat",
        model=payload.model or settings.default_model,
        system_prompt=payload.system_prompt,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return ConversationOut.model_validate(conversation)


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    q: str | None = Query(default=None, max_length=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    query = select(Conversation).where(Conversation.user_id == user.id)
    if q:
        pattern = f"%{q}%"
        message_ids = select(Message.conversation_id).where(Message.content.ilike(pattern))
        query = query.where(or_(Conversation.title.ilike(pattern), Conversation.id.in_(message_ids)))
    query = query.order_by(Conversation.updated_at.desc()).limit(200)
    rows = (await db.execute(query)).scalars().all()
    return [ConversationOut.model_validate(c) for c in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ConversationDetail:
    conversation = await _get_conversation(db, conversation_id, user)
    detail = ConversationDetail.model_validate(conversation)
    detail.messages = [MessageOut.model_validate(m) for m in conversation.messages]
    return detail


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationOut:
    conversation = await _get_conversation(db, conversation_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(conversation, field, value)
    await db.commit()
    await db.refresh(conversation)
    return ConversationOut.model_validate(conversation)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    conversation = await _get_conversation(db, conversation_id, user)
    await db.delete(conversation)
    await db.commit()
    return Response(status_code=204)


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: int,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await _get_conversation(db, conversation_id, user)
    if format == "json":
        payload = {
            "id": conversation.id,
            "title": conversation.title,
            "model": conversation.model,
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in conversation.messages
            ],
        }
        return Response(json.dumps(payload, indent=2), media_type="application/json")
    lines = [f"# {conversation.title}", f"_Model: {conversation.model}_", ""]
    for message in conversation.messages:
        lines.append(f"## {message.role.title()}")
        lines.append(message.content)
        lines.append("")
    return Response("\n".join(lines), media_type="text/markdown")


async def _stream_reply(conversation_id: int, user_id: int, request: ChatRequest) -> StreamingResponse:
    async def generator():
        async with SessionLocal() as db:
            conversation = (
                await db.execute(
                    select(Conversation)
                    .options(selectinload(Conversation.messages))
                    .where(Conversation.id == conversation_id)
                )
            ).scalar_one_or_none()
            if conversation is None or conversation.user_id != user_id:
                yield _sse({"type": "error", "error": "Conversation not found"})
                return
            model = request.model or conversation.model
            conversation.model = model
            await db.commit()
            history = _history_messages(conversation)
            yield _sse({"type": "meta", "conversation_id": conversation.id, "model": model})
            collected: list[str] = []
            final: dict[str, Any] = {}
            async for event in openrouter.chat_stream(history, model=model, temperature=request.temperature, max_tokens=request.max_tokens):
                if event["type"] == "delta":
                    collected.append(event["text"])
                    yield _sse(event)
                elif event["type"] == "done":
                    final = event
                elif event["type"] == "error":
                    yield _sse(event)
                    await _save_assistant(
                        db,
                        conversation,
                        content="".join(collected),
                        model=model,
                        error=event.get("error"),
                    )
                    return
            content = "".join(collected)
            message = await _save_assistant(
                db,
                conversation,
                content=content,
                model=final.get("model", model),
                tokens_in=final.get("tokens_in", 0),
                tokens_out=final.get("tokens_out", 0),
                cost=final.get("cost", 0.0),
            )
            await record_usage(
                db,
                user_id=user_id,
                endpoint="chat/stream",
                provider="openrouter",
                model=message.model,
                tokens_in=message.tokens_in,
                tokens_out=message.tokens_out,
                cost=message.cost,
                latency_ms=final.get("latency_ms", 0),
            )
            yield _sse({"type": "done", "message_id": message.id, **final})

    return StreamingResponse(generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    conversation = await _get_conversation(db, payload.conversation_id, user)
    message = Message(conversation_id=conversation.id, role="user", content=payload.content, model=payload.model or conversation.model)
    db.add(message)
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return await _stream_reply(conversation.id, user.id, payload)


@router.post("/chat/complete", response_model=MessageOut)
async def chat_complete(
    payload: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MessageOut:
    """Non-streaming variant used by tests and integrations."""
    conversation = await _get_conversation(db, payload.conversation_id, user)
    db.add(Message(conversation_id=conversation.id, role="user", content=payload.content))
    await db.commit()
    conversation = await _get_conversation(db, payload.conversation_id, user)
    model = payload.model or conversation.model
    result = await openrouter.chat(
        _history_messages(conversation), model=model, temperature=payload.temperature, max_tokens=payload.max_tokens
    )
    message = await _save_assistant(
        db,
        conversation,
        content=result["text"],
        model=result["model"],
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        cost=result["cost"],
    )
    await record_usage(
        db,
        user_id=user.id,
        endpoint="chat/complete",
        provider="openrouter",
        model=message.model,
        tokens_in=message.tokens_in,
        tokens_out=message.tokens_out,
        cost=message.cost,
        latency_ms=result["latency_ms"],
    )
    return MessageOut.model_validate(message)


@router.post("/chat/regenerate")
async def regenerate(
    payload: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    conversation = await _get_conversation(db, payload.conversation_id, user)
    assistants = [m for m in conversation.messages if m.role == "assistant"]
    if assistants:
        await db.delete(assistants[-1])
        await db.commit()
        await db.refresh(conversation)
    return await _stream_reply(conversation.id, user.id, payload)


@router.post("/chat/edit")
async def edit_and_resend(
    message_id: int,
    content: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await db.get(Message, message_id)
    if message is None or message.role != "user":
        raise HTTPException(status_code=404, detail="User message not found")
    conversation = await _get_conversation(db, message.conversation_id, user)
    message.content = content
    later = [m for m in conversation.messages if m.id > message.id]
    for item in later:
        await db.delete(item)
    await db.commit()
    await db.refresh(conversation)
    request = ChatRequest(conversation_id=conversation.id, content=content)
    return await _stream_reply(conversation.id, user.id, request)

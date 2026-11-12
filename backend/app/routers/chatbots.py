"""Chatbot Studio: CRUD, testing, publishing and public widget endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Chatbot, KnowledgeBase, User
from ..schemas import ChatbotCreate, ChatbotOut, ChatbotTestRequest
from ..services import openrouter, rag

settings = get_settings()
router = APIRouter(prefix="/api", tags=["chatbots"])


async def _own(db: AsyncSession, chatbot_id: int, user: User) -> Chatbot:
    bot = await db.get(Chatbot, chatbot_id)
    if bot is None or bot.user_id != user.id:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return bot


@router.post("/chatbots", response_model=ChatbotOut, status_code=201)
async def create_chatbot(
    payload: ChatbotCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ChatbotOut:
    if payload.knowledge_base_id:
        kb = await db.get(KnowledgeBase, payload.knowledge_base_id)
        if kb is None or kb.user_id != user.id:
            raise HTTPException(status_code=404, detail="Knowledge base not found")
    bot = Chatbot(
        user_id=user.id,
        name=payload.name,
        instructions=payload.instructions,
        model=payload.model,
        knowledge_base_id=payload.knowledge_base_id,
        grounded=payload.grounded,
        public_token=uuid.uuid4().hex,
        theme=payload.theme,
    )
    db.add(bot)
    await db.commit()
    await db.refresh(bot)
    return ChatbotOut.model_validate(bot)


@router.get("/chatbots", response_model=list[ChatbotOut])
async def list_chatbots(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[ChatbotOut]:
    rows = (await db.execute(select(Chatbot).where(Chatbot.user_id == user.id).order_by(Chatbot.id.desc()))).scalars().all()
    return [ChatbotOut.model_validate(b) for b in rows]


@router.patch("/chatbots/{chatbot_id}", response_model=ChatbotOut)
async def update_chatbot(
    chatbot_id: int,
    payload: ChatbotCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatbotOut:
    bot = await _own(db, chatbot_id, user)
    bot.name = payload.name
    bot.instructions = payload.instructions
    bot.model = payload.model
    bot.knowledge_base_id = payload.knowledge_base_id
    bot.grounded = payload.grounded
    bot.theme = payload.theme
    await db.commit()
    await db.refresh(bot)
    return ChatbotOut.model_validate(bot)


@router.delete("/chatbots/{chatbot_id}", status_code=204)
async def delete_chatbot(chatbot_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    bot = await _own(db, chatbot_id, user)
    await db.delete(bot)
    await db.commit()
    from fastapi import Response

    return Response(status_code=204)


@router.post("/chatbots/{chatbot_id}/test")
async def test_chatbot(
    chatbot_id: int, payload: ChatbotTestRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    bot = await _own(db, chatbot_id, user)
    return await _answer(bot, payload.message, db)


@router.post("/chatbots/{chatbot_id}/publish", response_model=ChatbotOut)
async def publish(
    chatbot_id: int, published: bool = True, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ChatbotOut:
    bot = await _own(db, chatbot_id, user)
    bot.published = published
    await db.commit()
    await db.refresh(bot)
    return ChatbotOut.model_validate(bot)


async def _answer(bot: Chatbot, message: str, db: AsyncSession) -> dict:
    if bot.grounded and bot.knowledge_base_id:
        result = await rag.answer_with_rag(
            db, bot.knowledge_base_id, message, model=bot.model or None, grounded=True
        )
        return {"answer": result["answer"], "citations": result["citations"], "grounded": True}
    if bot.grounded and not bot.knowledge_base_id:
        return {
            "answer": "This chatbot is in knowledge-only mode but has no knowledge base connected.",
            "citations": [],
            "grounded": True,
        }
    result = await openrouter.chat(
        [
            {"role": "system", "content": bot.instructions or "You are a helpful assistant."},
            {"role": "user", "content": message},
        ],
        model=bot.model or settings.default_model,
        temperature=0.5,
        max_tokens=800,
    )
    return {"answer": result["text"], "citations": [], "grounded": False}


@router.get("/public/chatbots/{token}")
async def public_info(token: str, db: AsyncSession = Depends(get_db)) -> dict:
    bot = (await db.execute(select(Chatbot).where(Chatbot.public_token == token, Chatbot.published.is_(True)))).scalar_one_or_none()
    if bot is None:
        raise HTTPException(status_code=404, detail="Chatbot not found or not published")
    return {"name": bot.name, "theme": bot.theme, "grounded": bot.grounded}


@router.post("/public/chatbots/{token}/chat")
async def public_chat(token: str, payload: ChatbotTestRequest, db: AsyncSession = Depends(get_db)) -> dict:
    bot = (await db.execute(select(Chatbot).where(Chatbot.public_token == token, Chatbot.published.is_(True)))).scalar_one_or_none()
    if bot is None:
        raise HTTPException(status_code=404, detail="Chatbot not found or not published")
    return await _answer(bot, payload.message, db)

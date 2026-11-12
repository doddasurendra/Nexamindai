"""Media gallery, uploads, vision analysis, image and video generation."""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import MediaItem, User
from ..schemas import ImageGenerateRequest, ImageQuestion, MediaOut, VideoGenerateRequest
from ..services import imagegen, openrouter, videogen
from ..services.media import delete_file, kind_for_extension, save_upload
from ..services.usage import record_usage

settings = get_settings()
router = APIRouter(prefix="/api", tags=["media"])


async def _own_media(db: AsyncSession, media_id: int, user: User) -> MediaItem:
    item = await db.get(MediaItem, media_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Media not found")
    return item


@router.post("/media/upload", response_model=MediaOut, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaOut:
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    kind = kind_for_extension(ext)
    path, digest, size = await save_upload(user.id, file, kind)
    item = MediaItem(
        user_id=user.id,
        kind=kind,
        title=file.filename or path.name,
        stored_path=str(path),
        mime_type=file.content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        size=size,
        source="upload",
        meta={"sha256": digest},
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return MediaOut.model_validate(item)


@router.get("/media", response_model=list[MediaOut])
async def list_media(
    kind: str | None = Query(default=None),
    q: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MediaOut]:
    query = select(MediaItem).where(MediaItem.user_id == user.id)
    if kind:
        query = query.where(MediaItem.kind == kind)
    if q:
        query = query.where(MediaItem.title.ilike(f"%{q}%"))
    items = (await db.execute(query.order_by(MediaItem.id.desc()).limit(200))).scalars().all()
    return [MediaOut.model_validate(item) for item in items]


@router.get("/media/{media_id}/file")
async def media_file(media_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await _own_media(db, media_id, user)
    path = Path(item.stored_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Stored file is missing")
    return FileResponse(path, media_type=item.mime_type or "application/octet-stream", filename=item.title)


@router.delete("/media/{media_id}", status_code=204)
async def delete_media(media_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await _own_media(db, media_id, user)
    delete_file(item.stored_path)
    await db.delete(item)
    await db.commit()
    return Response(status_code=204)


@router.post("/media/{media_id}/analyze")
async def analyze_media(
    media_id: int,
    payload: ImageQuestion,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await _own_media(db, media_id, user)
    if item.kind != "image":
        raise HTTPException(status_code=400, detail="Only image analysis is supported")
    if not settings.openrouter_configured:
        from ..errors import IntegrationNotConfigured

        raise IntegrationNotConfigured("OpenRouter vision", "OPENROUTER_API_KEY")
    raw = Path(item.stored_path).read_bytes()
    data_url = f"data:{item.mime_type or 'image/png'};base64,{base64.b64encode(raw).decode()}"
    result = await openrouter.chat(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": payload.question},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        model=payload.model or settings.default_model,
        temperature=0.2,
        max_tokens=800,
    )
    await record_usage(
        db,
        user_id=user.id,
        endpoint="media/analyze",
        provider="openrouter",
        model=result["model"],
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        cost=result["cost"],
        latency_ms=result["latency_ms"],
    )
    return {"answer": result["text"], "model": result["model"], "usage": result}


@router.post("/images/generate", response_model=list[MediaOut], status_code=201)
async def generate_images(
    payload: ImageGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MediaOut]:
    result = await imagegen.generate_images(user.id, payload.prompt, payload.model or None, payload.n)
    created: list[MediaItem] = []
    for image in result["images"]:
        item = MediaItem(
            user_id=user.id,
            kind="image",
            title=payload.prompt[:120],
            stored_path=image["path"],
            mime_type="image/png",
            size=image["bytes"],
            source="generated",
            meta={"model": result["model"], "prompt": payload.prompt},
        )
        db.add(item)
        created.append(item)
    await db.commit()
    for item in created:
        await db.refresh(item)
    return [MediaOut.model_validate(item) for item in created]


@router.post("/videos/generate", response_model=MediaOut, status_code=201)
async def generate_video(
    payload: VideoGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaOut:
    result = await videogen.generate_video(user.id, payload.prompt, payload.model or None)
    item = MediaItem(
        user_id=user.id,
        kind="video",
        title=payload.prompt[:120],
        stored_path=result["path"],
        mime_type="video/mp4",
        size=result["bytes"],
        source="generated",
        meta={"model": result["model"], "prompt": payload.prompt, "prediction_id": result.get("prediction_id")},
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return MediaOut.model_validate(item)

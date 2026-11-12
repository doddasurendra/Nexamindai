"""Secure file storage for uploads and generated media."""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile

from ..config import get_settings
from ..errors import ProviderError

settings = get_settings()


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def validate_upload(filename: str, size: int) -> str:
    ext = extension_of(filename)
    if ext not in settings.allowed_upload_extensions:
        raise ProviderError("storage", f"File type .{ext} is not allowed", 415)
    if size <= 0:
        raise ProviderError("storage", "Empty upload", 400)
    if size > settings.max_upload_mb * 1024 * 1024:
        raise ProviderError("storage", f"File exceeds {settings.max_upload_mb} MB", 413)
    return ext


def kind_for_extension(ext: str) -> str:
    if ext in {"png", "jpg", "jpeg", "webp", "gif", "bmp"}:
        return "image"
    if ext in {"mp4", "webm", "mov"}:
        return "video"
    if ext in {"mp3", "wav", "ogg"}:
        return "audio"
    return "document"


def save_bytes(user_id: int, data: bytes, filename: str, kind: str) -> tuple[Path, str]:
    folder = settings.storage_dir / str(user_id) / kind
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
    path = folder / safe_name
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


async def save_upload(user_id: int, upload: UploadFile, kind: str) -> tuple[Path, str, int]:
    data = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
    validate_upload(upload.filename or "upload.bin", len(data))
    path, digest = save_bytes(user_id, data, upload.filename or "upload.bin", kind)
    return path, digest, len(data)


def delete_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass

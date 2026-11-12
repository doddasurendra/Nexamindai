"""Image generation through OpenRouter image-capable models (real API calls only)."""
from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any

import httpx

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError
from . import openrouter
from .media import save_bytes

settings = get_settings()


def _decode_image(value: str) -> bytes:
    if value.startswith("data:"):
        header, _, payload = value.partition(",")
        if ";base64" not in header:
            raise ProviderError("OpenRouter", "Image response was not base64 encoded")
        return base64.b64decode(payload)
    return base64.b64decode(value)


async def generate_images(user_id: int, prompt: str, model: str | None = None, n: int = 1) -> dict[str, Any]:
    if not settings.openrouter_configured:
        raise IntegrationNotConfigured("OpenRouter image generation", "OPENROUTER_API_KEY")
    chosen = model or settings.image_generation_model
    images: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=180) as client:
        body = {
            "model": chosen,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
        }
        response = await client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": settings.openrouter_app_url,
                "X-Title": settings.openrouter_app_name,
            },
            json=body,
        )
        if response.status_code >= 400:
            raise ProviderError("OpenRouter", f"Image generation failed: HTTP {response.status_code} {response.text[:300]}")
        data = response.json()
        usage = data.get("usage") or {}
        message = ((data.get("choices") or [{}])[0]).get("message") or {}
        for item in message.get("images") or []:
            url = ((item.get("image_url") or {}).get("url")) if isinstance(item, dict) else None
            if not url:
                continue
            try:
                raw = _decode_image(url)
            except (binascii.Error, ValueError) as exc:
                raise ProviderError("OpenRouter", f"Invalid image payload: {exc}") from exc
            path, _digest = save_bytes(user_id, raw, f"generated_{len(images) + 1}.png", "image")
            images.append({"path": str(path), "bytes": len(raw), "model": chosen, "prompt": prompt})
            if len(images) >= n:
                break
    if not images:
        raise ProviderError(
            "OpenRouter",
            f"Model {chosen} returned no image content. Choose an image-capable model (modalities: image).",
        )
    return {"model": chosen, "images": images, "usage": usage, "prompt": prompt}

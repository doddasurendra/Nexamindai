"""Video generation through Replicate (real provider; explicit not-configured state)."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError
from .media import save_bytes

settings = get_settings()


async def generate_video(user_id: int, prompt: str, model: str | None = None) -> dict[str, Any]:
    if not settings.replicate_api_token:
        raise IntegrationNotConfigured("Replicate video generation", "REPLICATE_API_TOKEN")
    chosen = model or settings.video_model
    headers = {"Authorization": f"Bearer {settings.replicate_api_token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"https://api.replicate.com/v1/models/{chosen}/predictions",
            headers=headers,
            json={"input": {"prompt": prompt}},
        )
        if response.status_code >= 400:
            raise ProviderError("Replicate", f"Prediction create failed: HTTP {response.status_code} {response.text[:300]}")
        prediction = response.json()
        get_url = (prediction.get("urls") or {}).get("get")
        if not get_url:
            raise ProviderError("Replicate", "Prediction response lacked a polling URL")
        for _ in range(60):
            status = prediction.get("status")
            if status in {"succeeded", "failed", "canceled"}:
                break
            await asyncio.sleep(3)
            poll = await client.get(get_url, headers=headers)
            if poll.status_code >= 400:
                raise ProviderError("Replicate", f"Polling failed: HTTP {poll.status_code}")
            prediction = poll.json()
    if prediction.get("status") != "succeeded":
        raise ProviderError("Replicate", f"Generation {prediction.get('status')}: {prediction.get('error') or 'unknown error'}")
    output = prediction.get("output")
    url = output[0] if isinstance(output, list) and output else output if isinstance(output, str) else None
    if not url:
        raise ProviderError("Replicate", "Provider returned no video URL")
    async with httpx.AsyncClient(timeout=120) as client:
        media = await client.get(url)
    if media.status_code >= 400:
        raise ProviderError("Replicate", f"Video download failed: HTTP {media.status_code}")
    path, _digest = save_bytes(user_id, media.content, "generated_video.mp4", "video")
    return {"model": chosen, "path": str(path), "bytes": len(media.content), "prompt": prompt, "prediction_id": prediction.get("id")}

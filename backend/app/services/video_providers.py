"""Video API providers from the public-apis catalogue (#video).

Connectors:
- KPainter   (https://api.kpainter.ai)      — prompt-to-video generation, Bearer key, 120–1500s durations
- JSON2Video (https://api.json2video.com)   — programmatic scenes -> MP4, x-api-key header
- Shotstack  (https://shotstack.io)         — cloud video editing/render, x-api-key header

Each provider is disabled until its key is set in the environment. `auto` tries them in order.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError
from .media import save_bytes

settings = get_settings()

PROVIDER_ORDER = ["replicate", "kpainter", "json2video", "shotstack"]


def provider_status() -> list[dict[str, Any]]:
    return [
        {"provider": "replicate", "configured": bool(settings.replicate_api_token), "env": "REPLICATE_API_TOKEN", "role": "text-to-video (billing required)"},
        {"provider": "kpainter", "configured": bool(settings.kpainter_api_key), "env": "KPAINTER_API_KEY", "role": "prompt-to-video generation (public-apis)"},
        {"provider": "json2video", "configured": bool(settings.json2video_api_key), "env": "JSON2VIDEO_API_KEY", "role": "programmatic scenes -> MP4 (public-apis)"},
        {"provider": "shotstack", "configured": bool(settings.shotstack_api_key), "env": "SHOTSTACK_API_KEY", "role": "cloud editing/render, 10 free credits/30 days (public-apis)"},
    ]


def configured_providers() -> list[str]:
    return [item["provider"] for item in provider_status() if item["configured"]]


async def _download(url: str, timeout: float = 300) -> bytes:
    import urllib.request

    return await asyncio.get_running_loop().run_in_executor(
        None, lambda: urllib.request.urlopen(url, timeout=timeout).read()
    )


# ---------- KPainter ----------

async def _kpainter_poll(creation_id: str, headers: dict[str, str]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(120):  # ~10 minutes
            resp = await client.get(f"https://api.kpainter.ai/openapi/v1/creations/{creation_id}", headers=headers)
            if resp.status_code >= 400:
                raise ProviderError("KPainter", f"Poll failed: HTTP {resp.status_code} {resp.text[:200]}")
            data = resp.json()
            status = data.get("status")
            if status == "ready":
                return data
            if status == "failed":
                raise ProviderError("KPainter", f"Creation failed: {data.get('result_code') or 'unknown'}")
            await asyncio.sleep(5)
    raise ProviderError("KPainter", "Creation timed out while waiting for output")


async def generate_kpainter(user_id: int, prompt: str, duration_seconds: int = 120) -> dict[str, Any]:
    if not settings.kpainter_api_key:
        raise IntegrationNotConfigured("KPainter", "KPAINTER_API_KEY")
    # KPainter duration presets: 120, 240, 360, 510, 900, 1500
    presets = [120, 240, 360, 510, 900, 1500]
    chosen = min(presets, key=lambda value: abs(value - duration_seconds))
    headers = {"Authorization": f"Bearer {settings.kpainter_api_key}", "Content-Type": "application/json"}
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.kpainter.ai/openapi/v1/creations",
            headers=headers,
            json={"type": "video", "prompt": prompt, "video": {"duration_seconds": chosen, "language": "auto"}},
        )
    if resp.status_code not in (200, 201, 202):
        raise ProviderError("KPainter", f"Create failed: HTTP {resp.status_code} {resp.text[:300]}")
    creation = resp.json()
    creation_id = creation.get("id")
    if not creation_id:
        raise ProviderError("KPainter", "Create returned no creation id")

    finished = await _kpainter_poll(creation_id, headers)
    async with httpx.AsyncClient(timeout=30) as client:
        out = await client.get(f"https://api.kpainter.ai/openapi/v1/creations/{creation_id}/outputs", headers=headers)
    if out.status_code >= 400:
        raise ProviderError("KPainter", f"Outputs failed: HTTP {out.status_code}")
    outputs = out.json().get("outputs", [])
    video_url = next((o.get("url") for o in outputs if o.get("kind") == "video"), None)
    if not video_url:
        raise ProviderError("KPainter", "No video output returned")
    content = await _download(video_url)
    path, _digest = save_bytes(user_id, content, "generated_video.mp4", "video")
    return {
        "provider": "kpainter",
        "path": str(path),
        "bytes": len(content),
        "prompt": prompt,
        "duration_seconds": chosen,
        "creation_id": creation_id,
        "latency_ms": int((time.perf_counter() - start) * 1000),
    }


# ---------- JSON2Video ----------

async def generate_json2video(user_id: int, prompt: str, duration_seconds: int = 30, language: str = "English") -> dict[str, Any]:
    if not settings.json2video_api_key:
        raise IntegrationNotConfigured("JSON2Video", "JSON2VIDEO_API_KEY")
    headers = {"x-api-key": settings.json2video_api_key, "Content-Type": "application/json"}
    scene_duration = max(5, min(duration_seconds, 60))
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.json2video.com/v2/movies",
            headers=headers,
            json={
                "resolution": "full-hd",
                "scenes": [
                    {
                        "duration": scene_duration,
                        "elements": [
                            {"type": "text", "text": prompt[:400], "style": "001"},
                        ],
                    }
                ],
            },
        )
    if resp.status_code >= 400:
        raise ProviderError("JSON2Video", f"Create failed: HTTP {resp.status_code} {resp.text[:300]}")
    project = resp.json().get("project")
    if not project:
        raise ProviderError("JSON2Video", "Create returned no project id")

    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(120):  # ~10 minutes
            poll = await client.get("https://api.json2video.com/v2/movies", params={"project": project}, headers=headers)
            if poll.status_code >= 400:
                raise ProviderError("JSON2Video", f"Poll failed: HTTP {poll.status_code}")
            movie = poll.json().get("movie", {})
            if movie.get("status") == "done":
                url = movie.get("url")
                if not url:
                    raise ProviderError("JSON2Video", "Rendered movie has no URL")
                content = await _download(url)
                path, _digest = save_bytes(user_id, content, "generated_video.mp4", "video")
                return {
                    "provider": "json2video",
                    "path": str(path),
                    "bytes": len(content),
                    "prompt": prompt,
                    "duration_seconds": scene_duration,
                    "project": project,
                    "latency_ms": int((time.perf_counter() - start) * 1000),
                }
            if movie.get("status") == "error":
                raise ProviderError("JSON2Video", f"Render failed: {movie.get('message') or 'unknown'}")
            await asyncio.sleep(4)
    raise ProviderError("JSON2Video", "Render timed out while waiting for output")


# ---------- Shotstack ----------

SANDBOX_URL = "https://api.sandbox.shotstack.io"
PRODUCTION_URL = "https://api.shotstack.io"


async def generate_shotstack(user_id: int, prompt: str, duration_seconds: int = 30) -> dict[str, Any]:
    if not settings.shotstack_api_key:
        raise IntegrationNotConfigured("Shotstack", "SHOTSTACK_API_KEY")
    # Sandbox first (free, watermarked); production if SHOTSTACK_ENV=production
    import os

    base = PRODUCTION_URL if os.environ.get("SHOTSTACK_ENV", "").lower() == "production" else SANDBOX_URL
    headers = {"x-api-key": settings.shotstack_api_key, "Content-Type": "application/json"}
    clip_length = max(5, min(duration_seconds, 60))
    timeline = {
        "background": "#101828",
        "tracks": [
            {
                "clips": [
                    {
                        "asset": {"type": "text", "text": prompt[:200], "font": {"family": "Montserrat", "size": 40, "color": "#ffffff"}},
                        "start": 0,
                        "length": clip_length,
                        "fit": "contain",
                    }
                ]
            }
        ],
    }
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{base}/edit/v1/render", headers=headers, json={"timeline": timeline, "output": {"format": "mp4", "resolution": "hd"}})
    if resp.status_code not in (200, 201, 202):
        raise ProviderError("Shotstack", f"Render failed: HTTP {resp.status_code} {resp.text[:300]}")
    render_id = (resp.json().get("response") or {}).get("id")
    if not render_id:
        raise ProviderError("Shotstack", "Render returned no id")

    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(120):  # ~10 minutes
            poll = await client.get(f"{base}/edit/v1/render/{render_id}", headers=headers)
            if poll.status_code >= 400:
                raise ProviderError("Shotstack", f"Poll failed: HTTP {poll.status_code}")
            body = poll.json().get("response", {})
            if body.get("status") == "done":
                url = body.get("url")
                if not url:
                    raise ProviderError("Shotstack", "Rendered video has no URL")
                content = await _download(url)
                path, _digest = save_bytes(user_id, content, "generated_video.mp4", "video")
                return {
                    "provider": "shotstack",
                    "path": str(path),
                    "bytes": len(content),
                    "prompt": prompt,
                    "duration_seconds": clip_length,
                    "render_id": render_id,
                    "sandbox": base == SANDBOX_URL,
                    "latency_ms": int((time.perf_counter() - start) * 1000),
                }
            if body.get("status") in {"failed", "error"}:
                raise ProviderError("Shotstack", f"Render failed: {body.get('error') or 'unknown'}")
            await asyncio.sleep(4)
    raise ProviderError("Shotstack", "Render timed out while waiting for output")


# ---------- dispatcher ----------

async def generate_with_provider(user_id: int, prompt: str, provider: str, duration_seconds: int, language: str = "English") -> dict[str, Any]:
    provider = (provider or "auto").lower().strip()
    if provider == "replicate":
        from . import videogen

        return await videogen.generate_video(user_id, prompt, None)
    if provider == "kpainter":
        return await generate_kpainter(user_id, prompt, duration_seconds)
    if provider == "json2video":
        return await generate_json2video(user_id, prompt, duration_seconds, language)
    if provider == "shotstack":
        return await generate_shotstack(user_id, prompt, duration_seconds)
    if provider == "auto":
        last_error: Exception | None = None
        for candidate in PROVIDER_ORDER:
            try:
                return await generate_with_provider(user_id, prompt, candidate, duration_seconds, language)
            except IntegrationNotConfigured:
                continue
            except ProviderError as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise ProviderError("VideoProviders", f"All configured providers failed. Last: {last_error}")
        raise IntegrationNotConfigured(
            "Video providers",
            "REPLICATE_API_TOKEN / KPAINTER_API_KEY / JSON2VIDEO_API_KEY / SHOTSTACK_API_KEY",
            "No video provider is configured. Set at least one key (see .env).",
        )
    raise ProviderError("VideoProviders", f"Unknown provider: {provider}. Valid: auto, replicate, kpainter, json2video, shotstack")

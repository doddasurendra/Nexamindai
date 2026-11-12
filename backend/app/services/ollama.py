"""Ollama service: local model inference, listing and health."""
from __future__ import annotations

import time
from typing import Any

import httpx

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError

settings = get_settings()


def _base_url() -> str:
    return settings.ollama_base_url.rstrip("/")


def _configured() -> bool:
    return bool(settings.ollama_base_url)


async def health() -> dict[str, Any]:
    if not _configured():
        return {"configured": False, "status": "not_configured", "reason": "OLLAMA_BASE_URL is not set"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{_base_url()}/api/tags")
        if response.status_code == 200:
            data = response.json()
            return {"configured": True, "status": "ok", "models": [m["name"] for m in data.get("models", [])]}
        return {"configured": True, "status": f"error: HTTP {response.status_code}"}
    except Exception as exc:  # noqa: BLE001
        return {"configured": True, "status": "unreachable", "error": str(exc)}


async def list_models() -> list[dict[str, Any]]:
    if not _configured():
        return []
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{_base_url()}/api/tags")
    if response.status_code != 200:
        return []
    return response.json().get("models", [])


async def chat(messages: list[dict[str, Any]], model: str | None = None, temperature: float = 0.7, max_tokens: int = 1024) -> dict[str, Any]:
    """Chat completion via local Ollama (OpenAI-style messages)."""
    if not _configured():
        raise IntegrationNotConfigured("Ollama", "OLLAMA_BASE_URL")
    chosen = model or settings.ollama_model
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            f"{_base_url()}/api/chat",
            json={
                "model": chosen,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
        )
    if response.status_code >= 400:
        raise ProviderError("Ollama", f"Chat failed: HTTP {response.status_code} {response.text[:300]}")
    data = response.json()
    content = (data.get("message") or {}).get("content", "")
    return {"text": content, "model": chosen, "tokens_in": data.get("prompt_eval_count", 0), "tokens_out": data.get("eval_count", 0), "cost": 0.0, "latency_ms": 0}


async def generate(prompt: str, model: str | None = None, max_tokens: int = 256) -> dict[str, Any]:
    if not _configured():
        raise IntegrationNotConfigured("Ollama", "OLLAMA_BASE_URL")
    chosen = model or settings.ollama_model
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{_base_url()}/api/generate",
            json={"model": chosen, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}},
        )
    if response.status_code >= 400:
        raise ProviderError("Ollama", f"Generation failed: HTTP {response.status_code} {response.text[:300]}")
    data = response.json()
    return {"text": data.get("response", ""), "model": chosen, "eval_count": data.get("eval_count", 0)}


async def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    if not _configured():
        raise IntegrationNotConfigured("Ollama embeddings", "OLLAMA_BASE_URL")
    chosen = model or settings.ollama_model
    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=60) as client:
        for text in texts:
            response = await client.post(
                f"{_base_url()}/api/embeddings",
                json={"model": chosen, "prompt": text},
            )
            if response.status_code >= 400:
                raise ProviderError("Ollama", f"Embedding failed: HTTP {response.status_code} {response.text[:200]}")
            vectors.append(response.json().get("embedding", []))
    return vectors
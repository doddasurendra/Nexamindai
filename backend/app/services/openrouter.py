"""Server-side OpenRouter client: streaming, retries, fallback, usage and cost."""
from __future__ import annotations

import asyncio
import json
import random
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError

settings = get_settings()

try:  # optional exact token accounting
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_ENC.encode(text))

except Exception:  # pragma: no cover - fallback estimator

    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_app_url,
        "X-Title": settings.openrouter_app_name,
    }


def is_configured() -> bool:
    return settings.openrouter_configured


def ensure_configured() -> None:
    if not settings.openrouter_configured:
        raise IntegrationNotConfigured("OpenRouter", "OPENROUTER_API_KEY")


class ModelCatalog:
    def __init__(self) -> None:
        self._models: list[dict[str, Any]] = []
        self._fetched_at: float = 0.0

    async def get(self, force: bool = False) -> list[dict[str, Any]]:
        ensure_configured()
        if self._models and not force and time.time() - self._fetched_at < 3600:
            return self._models
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{settings.openrouter_base_url}/models", headers=_headers())
            if resp.status_code != 200:
                raise ProviderError("OpenRouter", f"Model catalog failed: HTTP {resp.status_code}", resp.status_code)
            data = resp.json().get("data", [])
        normalized = [normalize_model(m) for m in data]
        self._models = normalized
        self._fetched_at = time.time()
        return normalized


catalog = ModelCatalog()


def normalize_model(raw: dict[str, Any]) -> dict[str, Any]:
    pricing = raw.get("pricing") or {}
    try:
        prompt_price = float(pricing.get("prompt", 0)) * 1_000_000
    except (TypeError, ValueError):
        prompt_price = 0.0
    try:
        completion_price = float(pricing.get("completion", 0)) * 1_000_000
    except (TypeError, ValueError):
        completion_price = 0.0
    modality = (raw.get("architecture") or {}).get("modality", "")
    capabilities = {
        "vision": "image" in modality,
        "text": True,
        "image_output": "image" in (raw.get("architecture") or {}).get("output_modalities", []),
        "tools": "tools" in (raw.get("supported_parameters") or []),
    }
    return {
        "model_id": raw.get("id", ""),
        "name": raw.get("name") or raw.get("id", ""),
        "context_window": int(raw.get("context_length") or 0),
        "input_price": round(prompt_price, 4),
        "output_price": round(completion_price, 4),
        "capabilities": capabilities,
        "description": raw.get("description", ""),
    }


def trim_messages(messages: list[dict[str, Any]], max_tokens: int | None = None) -> list[dict[str, Any]]:
    """Keep the system message and newest turns within the context budget."""
    budget = max_tokens or settings.max_context_tokens
    if not messages:
        return messages
    system = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    kept: list[dict[str, Any]] = []
    used = sum(count_tokens(str(m.get("content", ""))) for m in system)
    for message in reversed(rest):
        cost = count_tokens(str(message.get("content", "")))
        if kept and used + cost > budget:
            break
        kept.append(message)
        used += cost
    kept.reverse()
    return system + kept


async def _request_with_retry(
    method: str,
    url: str,
    *,
    json_body: dict[str, Any] | None = None,
    stream: bool = False,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(settings.max_retries):
        try:
            client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)
            request = client.build_request(method, url, headers=_headers(), json=json_body)
            response = await client.send(request, stream=stream)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < settings.max_retries - 1:
                await response.aclose()
                await client.aclose()
                delay = min(8.0, 0.5 * (2**attempt)) + random.uniform(0, 0.25)
                await asyncio.sleep(delay)
                continue
            response._nexamind_client = client  # type: ignore[attr-defined]
            return response
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt < settings.max_retries - 1:
                await asyncio.sleep(min(8.0, 0.5 * (2**attempt)))
                continue
    raise ProviderError("OpenRouter", f"Request failed after retries: {last_error}")


async def close_response(response: httpx.Response) -> None:
    client = getattr(response, "_nexamind_client", None)
    await response.aclose()
    if client is not None:
        await client.aclose()


def _models_to_try(primary: str) -> list[str]:
    chain = [primary]
    for fallback in settings.fallback_model_list:
        if fallback not in chain:
            chain.append(fallback)
    return chain


async def chat(
    messages: list[dict[str, Any]],
    model: str | None = None,
    *,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Non-streaming completion with fallback. Returns text, usage, model and cost."""
    ensure_configured()
    primary = model or settings.default_model
    last_error: Exception | None = None

    for candidate in _models_to_try(primary):
        body: dict[str, Any] = {
            "model": candidate,
            "messages": trim_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = response_format
        try:
            started = time.perf_counter()
            response = await _request_with_retry(
                "POST", f"{settings.openrouter_base_url}/chat/completions", json_body=body
            )
            if response.status_code >= 400:
                text = (await response.aread()).decode("utf-8", "replace")[:500]
                await close_response(response)
                last_error = ProviderError("OpenRouter", f"{candidate}: HTTP {response.status_code} {text}")
                continue
            data = response.json()
            await close_response(response)
            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content") or ""
            usage = data.get("usage") or {}
            tokens_in = int(usage.get("prompt_tokens") or 0)
            tokens_out = int(usage.get("completion_tokens") or 0)
            return {
                "text": content,
                "model": data.get("model", candidate),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost": float(usage.get("cost") or 0.0),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "raw": data,
            }
        except ProviderError as exc:
            last_error = exc
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    raise ProviderError("OpenRouter", f"All model attempts failed: {last_error}")


async def chat_stream(
    messages: list[dict[str, Any]],
    model: str | None = None,
    *,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AsyncIterator[dict[str, Any]]:
    """Yield events: delta / done / error. Falls back only before the first token."""
    ensure_configured()
    primary = model or settings.default_model
    last_error: Exception | None = None

    for candidate in _models_to_try(primary):
        body = {
            "model": candidate,
            "messages": trim_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        started = time.perf_counter()
        emitted = False
        try:
            response = await _request_with_retry(
                "POST", f"{settings.openrouter_base_url}/chat/completions", json_body=body, stream=True
            )
            if response.status_code >= 400:
                text = (await response.aread()).decode("utf-8", "replace")[:300]
                await close_response(response)
                last_error = ProviderError("OpenRouter", f"{candidate}: HTTP {response.status_code} {text}")
                continue
            usage: dict[str, Any] = {}
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if chunk.get("usage"):
                    usage = chunk["usage"]
                for choice in chunk.get("choices") or []:
                    delta = (choice.get("delta") or {}).get("content")
                    if delta:
                        emitted = True
                        yield {"type": "delta", "text": delta}
            yield {
                "type": "done",
                "model": candidate,
                "tokens_in": int(usage.get("prompt_tokens") or 0),
                "tokens_out": int(usage.get("completion_tokens") or 0),
                "cost": float(usage.get("cost") or 0.0),
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
            await close_response(response)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if emitted:
                yield {"type": "error", "error": f"Stream interrupted: {exc}"}
                return
            continue
    yield {"type": "error", "error": f"All model attempts failed: {last_error}"}


async def embeddings(texts: list[str], model: str | None = None) -> list[list[float]]:
    ensure_configured()
    body = {"model": model or settings.embedding_model, "input": texts}
    response = await _request_with_retry(
        "POST", f"{settings.openrouter_base_url}/embeddings", json_body=body
    )
    if response.status_code >= 400:
        text = (await response.aread()).decode("utf-8", "replace")[:300]
        await close_response(response)
        raise ProviderError("OpenRouter", f"Embeddings failed: HTTP {response.status_code} {text}")
    data = response.json()
    await close_response(response)
    items = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
    return [item["embedding"] for item in items]


def estimate_cost(model_info: dict[str, Any] | None, tokens_in: int, tokens_out: int) -> float:
    if not model_info:
        return 0.0
    return round(
        (tokens_in / 1_000_000) * float(model_info.get("input_price", 0))
        + (tokens_out / 1_000_000) * float(model_info.get("output_price", 0)),
        6,
    )

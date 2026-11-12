"""Video generation through Replicate (real provider; explicit not-configured state)."""
from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError
from .media import save_bytes
from .openrouter import chat as openrouter_chat

settings = get_settings()

LATIN_RANGE = re.compile(r"^[\x00-\x7FÀ-ÖØ-öø-ÿĀ-ſ]*$")


def _needs_translation(text: str) -> bool:
    """Detect prompts with non-Latin scripts (Telugu, Hindi, etc.) that video models can't process."""
    return bool(re.search(r"[^\x00-\x7FÀ-ÖØ-öø-ÿĀ-ſ\s\d\W_]", text)) or bool(re.search(r"[\u0C00-\u0C7F\u0900-\u097F\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]", text))


async def _translate_to_english(prompt: str) -> str:
    """Translate a non-English prompt to English for the video model. Falls back to the original."""
    if not settings.openrouter_api_key:
        return prompt
    try:
        response = await openrouter_chat(
            messages=[
                {
                    "role": "system",
                    "content": "Translate the user's video prompt to concise English. Return ONLY the translated prompt, no explanation.",
                },
                {"role": "user", "content": prompt},
            ],
            model=settings.default_model,
            max_tokens=256,
        )
        translated = (response.get("content") or "").strip()
        if translated:
            return translated
    except Exception:
        pass
    return prompt


async def generate_video(user_id: int, prompt: str, model: str | None = None) -> dict[str, Any]:
    if not settings.replicate_api_token:
        raise IntegrationNotConfigured("Replicate video generation", "REPLICATE_API_TOKEN")
    chosen = model or settings.video_model
    headers = {"Authorization": f"Bearer {settings.replicate_api_token}", "Content-Type": "application/json"}

    # Video models are English-optimized: translate non-Latin prompts to English
    original_prompt = prompt.strip()
    generation_prompt = original_prompt
    translated = False
    if _needs_translation(original_prompt):
        generation_prompt = await _translate_to_english(original_prompt)
        translated = generation_prompt != original_prompt

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"https://api.replicate.com/v1/models/{chosen}/predictions",
            headers=headers,
            json={"input": {"prompt": generation_prompt, "prompt_optimizer": True}},
        )
        if response.status_code >= 400:
            raise ProviderError("Replicate", f"Prediction create failed: HTTP {response.status_code} {response.text[:300]}")
        prediction = response.json()
        get_url = (prediction.get("urls") or {}).get("get")
        if not get_url:
            raise ProviderError("Replicate", "Prediction response lacked a polling URL")

        # Poll up to ~6.5 minutes (video rendering can be slow)
        for _ in range(100):
            status = prediction.get("status")
            if status in {"succeeded", "failed", "canceled"}:
                break
            await asyncio.sleep(4)
            poll = await client.get(get_url, headers=headers)
            if poll.status_code >= 400:
                raise ProviderError("Replicate", f"Polling failed: HTTP {poll.status_code}")
            prediction = poll.json()

    status = prediction.get("status")
    if status != "succeeded":
        provider_error = prediction.get("error")
        if provider_error:
            detail = str(provider_error)
        else:
            detail = (
                f"The video provider ({chosen}) could not render this prompt. "
                "Video models are tuned for English and general scenes — try a short English description "
                "(e.g. 'a person explaining quantum computing with glowing qubits')."
            )
        raise ProviderError("Replicate", f"Generation {status}: {detail}")

    output = prediction.get("output")
    url = output[0] if isinstance(output, list) and output else output if isinstance(output, str) else None
    if not url:
        raise ProviderError("Replicate", "Provider returned no video URL")
    async with httpx.AsyncClient(timeout=180) as client:
        media = await client.get(url)
    if media.status_code >= 400:
        raise ProviderError("Replicate", f"Video download failed: HTTP {media.status_code}")

    path, _digest = save_bytes(user_id, media.content, "generated_video.mp4", "video")
    return {
        "model": chosen,
        "path": str(path),
        "bytes": len(media.content),
        "prompt": original_prompt,
        "generation_prompt": generation_prompt,
        "translated": translated,
        "prediction_id": prediction.get("id"),
    }

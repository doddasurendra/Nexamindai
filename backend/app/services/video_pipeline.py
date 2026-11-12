"""Video production pipeline: script -> voiceover -> scenes -> stitched MP4.

Supports longer videos with narration by:
1. Generating a timed script with OpenRouter (in the requested language)
2. Generating the full voiceover in one TTS call (Replicate minimax/speech-02-hd)
3. Generating N short video clips (minimax/video-01, ~6s each)
4. Stitching clips + voiceover with moviepy (requires imageio-ffmpeg)

Duration is capped at MAX_DURATION_SECONDS to bound cost and render time.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from ..config import get_settings
from ..errors import IntegrationNotConfigured, ProviderError
from .media import save_bytes
from .openrouter import chat as openrouter_chat

settings = get_settings()

MAX_DURATION_SECONDS = 3600  # 1 hour cap (user-requested); each 6s clip = ~600 predictions at the cap
CLIP_SECONDS = 6
TTS_MODEL = "minimax/speech-02-hd"
VIDEO_MODEL = "minimax/video-01"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.replicate_api_token}"}


async def _replicate(path: str, method: str = "POST", json_body: dict | None = None, timeout: float = 60) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, f"https://api.replicate.com/v1{path}", headers={**_headers(), "Content-Type": "application/json"}, json=json_body)
    if response.status_code >= 400:
        raise ProviderError("Replicate", f"{method} {path} failed: HTTP {response.status_code} {response.text[:300]}")
    return response.json()


async def _wait_prediction(get_url: str, timeout_seconds: float = 900) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        start = time.time()
        while time.time() - start < timeout_seconds:
            response = await client.get(get_url, headers=_headers())
            if response.status_code >= 400:
                raise ProviderError("Replicate", f"Polling failed: HTTP {response.status_code}")
            prediction = response.json()
            status = prediction.get("status")
            if status in {"succeeded", "failed", "canceled"}:
                return prediction
            await asyncio.sleep(4)
    raise ProviderError("Replicate", "Prediction timed out while waiting for output")


def _download(url: str) -> bytes:
    import urllib.request

    with urllib.request.urlopen(url, timeout=300) as r:
        return r.read()


async def generate_script(topic: str, language: str, duration_seconds: int) -> str:
    """Generate a narration script sized to the requested duration."""
    words_target = max(int(duration_seconds * 2.2), 60)  # ~130 wpm narration pace
    response = await openrouter_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    f"Write a narration script for a {duration_seconds}-second educational video about the topic below. "
                    f"Language: {language}. Aim for about {words_target} words (spoken pace). "
                    "Write ONLY the narration text, no stage directions, no headers, no markdown. "
                    "Make it engaging, accurate and suitable for a general audience."
                ),
            },
            {"role": "user", "content": topic},
        ],
        model=settings.default_model,
        max_tokens=4000,
    )
    script = (response.get("text") or "").strip()
    if not script:
        raise ProviderError("OpenRouter", "Script generation returned empty content")
    return script


async def generate_scenes(topic: str, language: str, count: int) -> list[str]:
    """Generate short English scene prompts for the video model."""
    response = await openrouter_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    f"Create {count} short visual scene descriptions (English, max 15 words each) for a video about the topic. "
                    "Each scene should be a concrete, filmable visual — no text overlays. "
                    'Return ONLY a JSON array of strings, e.g. ["scene 1", "scene 2"]. No prose.'
                ),
            },
            {"role": "user", "content": topic},
        ],
        model=settings.default_model,
        max_tokens=1500,
    )
    raw = (response.get("text") or "").strip()
    try:
        scenes = json.loads(raw)
        if isinstance(scenes, list):
            return [str(s).strip() for s in scenes if str(s).strip()][:count]
    except json.JSONDecodeError:
        pass
    # Fallback: split numbered lines
    lines = [re.sub(r"^\s*\d+[.)]\s*", "", line).strip(" -") for line in raw.splitlines() if line.strip()]
    return [line for line in lines if line][:count] or [f"visual about {topic}"] * count


def _stitch(clips: list[Path], voiceover: Path, output: Path) -> None:
    """Concatenate clips and mix the voiceover with moviepy."""
    try:
        from moviepy import AudioFileClip, VideoFileClip, concatenate_videoclips
    except Exception as exc:  # noqa: BLE001
        raise ProviderError("VideoPipeline", f"moviepy is not installed or failed to import: {exc}")

    video_clips = [VideoFileClip(str(c)) for c in clips]
    final = concatenate_videoclips(video_clips, method="compose")
    audio = AudioFileClip(str(voiceover))
    # Loop/trim video to match voiceover length
    if final.duration < audio.duration:
        repeats = int(audio.duration // final.duration) + 1
        final = concatenate_videoclips([final] * repeats, method="compose").subclipped(0, audio.duration)
    else:
        final = final.subclipped(0, audio.duration)
    final = final.with_audio(audio)
    final.write_videofile(str(output), codec="libx264", audio_codec="aac", fps=24, logger=None)
    for c in video_clips:
        c.close()
    audio.close()
    final.close()


async def generate_video_with_voiceover(
    user_id: int,
    topic: str,
    duration_seconds: int = 30,
    language: str = "English",
    voice_id: str | None = None,
) -> dict[str, Any]:
    """Full pipeline: script -> TTS -> scenes -> stitched MP4 with voiceover."""
    if not settings.replicate_api_token:
        raise IntegrationNotConfigured("Replicate video generation", "REPLICATE_API_TOKEN")
    if not settings.openrouter_api_key:
        raise IntegrationNotConfigured("OpenRouter (script generation)", "OPENROUTER_API_KEY")

    duration_seconds = max(6, min(duration_seconds, MAX_DURATION_SECONDS))
    scene_count = max(1, duration_seconds // CLIP_SECONDS)

    # 1. Script
    script = await generate_script(topic, language, duration_seconds)

    # 2. Voiceover (single TTS call — supports up to 10k chars ≈ 10 min)
    tts_input: dict[str, Any] = {"text": script[:10000]}
    if voice_id:
        tts_input["voice_id"] = voice_id
    tts_prediction = await _replicate(f"/models/{TTS_MODEL}/predictions", json_body={"input": tts_input})
    tts_get = (tts_prediction.get("urls") or {}).get("get")
    if not tts_get:
        raise ProviderError("Replicate", "TTS prediction lacked a polling URL")
    tts_result = await _wait_prediction(tts_get, timeout_seconds=600)
    if tts_result.get("status") != "succeeded":
        raise ProviderError("Replicate", f"Voiceover generation failed: {tts_result.get('error') or 'unknown error'}")
    tts_output = tts_result.get("output")
    tts_url = tts_output[0] if isinstance(tts_output, list) and tts_output else str(tts_output) if tts_output else None
    if not tts_url:
        raise ProviderError("Replicate", "TTS provider returned no audio URL")

    # 3. Scenes (English prompts for the video model)
    scenes = await generate_scenes(topic, "English", scene_count)

    # 4. Generate scene clips (sequential to bound load; each polls to completion)
    clip_paths: list[Path] = []
    for idx, scene in enumerate(scenes):
        pred = await _replicate(
            f"/models/{VIDEO_MODEL}/predictions",
            json_body={"input": {"prompt": scene, "prompt_optimizer": True}},
            timeout=120,
        )
        get_url = (pred.get("urls") or {}).get("get")
        if not get_url:
            continue
        result = await _wait_prediction(get_url, timeout_seconds=600)
        if result.get("status") != "succeeded":
            continue
        output = result.get("output")
        url = output[0] if isinstance(output, list) and output else str(output) if output else None
        if not url:
            continue
        clip_bytes = _download(url)
        clip_path, _ = save_bytes(user_id, clip_bytes, f"scene_{idx}.mp4", "video")
        clip_paths.append(Path(clip_path))

    if not clip_paths:
        raise ProviderError("Replicate", "No video scenes could be generated (all predictions failed)")

    # 5. Download voiceover and stitch
    voice_bytes = _download(tts_url)
    voice_path, _ = save_bytes(user_id, voice_bytes, "voiceover.mp3", "audio")

    output_path, _ = save_bytes(user_id, b"", "final_video.mp4", "video")
    _stitch(clip_paths, Path(voice_path), Path(output_path))

    return {
        "model": VIDEO_MODEL,
        "path": str(output_path),
        "bytes": Path(output_path).stat().st_size if Path(output_path).exists() else 0,
        "prompt": topic,
        "language": language,
        "duration_seconds": duration_seconds,
        "scenes": len(clip_paths),
        "script": script,
        "prediction_id": tts_result.get("id"),
    }

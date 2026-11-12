"""Video editing with moviepy: trim, crop, resize, speed, volume, text overlay, concatenate."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..errors import ProviderError
from .media import save_bytes


def _load_font() -> str:
    """Best-effort: find a usable font for text overlays."""
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return "arial"  # moviepy will raise if missing; caller handles it


def edit_video(
    user_id: int,
    source_path: str,
    *,
    trim_start: float | None = None,
    trim_end: float | None = None,
    resize_width: int | None = None,
    crop: dict[str, int] | None = None,
    speed: float | None = None,
    volume: float | None = None,
    overlay_text: str | None = None,
    overlay_position: str = "bottom",
    overlay_fontsize: int = 48,
) -> dict[str, Any]:
    """Apply edits to a stored video file and save the result."""
    try:
        from moviepy import (
            CompositeVideoClip,
            TextClip,
            VideoFileClip,
            vfx,
            afx,
        )
    except Exception as exc:  # noqa: BLE001
        raise ProviderError("VideoEditor", f"moviepy is not installed or failed to import: {exc}")

    clip = VideoFileClip(source_path)
    try:
        # Trim
        if trim_start is not None or trim_end is not None:
            start = max(0.0, float(trim_start or 0.0))
            end = float(trim_end) if trim_end is not None else clip.duration
            end = min(end, clip.duration)
            if end > start:
                clip = clip.subclipped(start, end)

        # Crop
        if crop:
            x = max(0, int(crop.get("x", 0)))
            y = max(0, int(crop.get("y", 0)))
            w = int(crop.get("width", clip.w))
            h = int(crop.get("height", clip.h))
            w = min(w, clip.w - x)
            h = min(h, clip.h - y)
            if w > 0 and h > 0:
                clip = clip.cropped(x1=x, y1=y, width=w, height=h)

        # Resize
        if resize_width and resize_width > 0:
            clip = clip.resized(width=int(resize_width))

        # Speed
        if speed and speed > 0 and not math.isclose(speed, 1.0):
            clip = clip.with_effects([vfx.MultiplySpeed(float(speed))])

        # Volume
        if volume is not None and not math.isclose(volume, 1.0):
            clip = clip.with_effects([afx.MultiplyVolume(float(volume))])

        # Text overlay
        if overlay_text:
            try:
                txt = TextClip(
                    text=overlay_text,
                    font_size=int(overlay_fontsize),
                    color="white",
                    font=_load_font(),
                    method="caption",
                    size=(int(clip.w * 0.9), None),
                ).with_duration(clip.duration)
                pos = {
                    "top": ("center", 30),
                    "center": ("center", "center"),
                    "bottom": ("center", "bottom"),
                }.get(overlay_position, ("center", "bottom"))
                if overlay_position == "bottom":
                    txt = txt.with_position(("center", clip.h - 60))
                else:
                    txt = txt.with_position(pos)
                clip = CompositeVideoClip([clip, txt])
            except Exception as exc:  # noqa: BLE001
                raise ProviderError("VideoEditor", f"Text overlay failed (font issue?): {exc}")

        output_path, _digest = save_bytes(user_id, b"", "edited.mp4", "video")
        clip.write_videofile(str(output_path), codec="libx264", audio_codec="aac", fps=24, logger=None)
        size = Path(output_path).stat().st_size
        clip.close()
        return {"path": str(output_path), "bytes": size, "width": clip.w, "height": clip.h, "duration": clip.duration}
    except ProviderError:
        clip.close()
        raise
    except Exception as exc:  # noqa: BLE001
        try:
            clip.close()
        except Exception:
            pass
        raise ProviderError("VideoEditor", f"Edit failed: {exc}")


def concatenate_videos(user_id: int, source_paths: list[str]) -> dict[str, Any]:
    """Concatenate multiple stored videos into one."""
    try:
        from moviepy import VideoFileClip, concatenate_videoclips
    except Exception as exc:  # noqa: BLE001
        raise ProviderError("VideoEditor", f"moviepy is not installed or failed to import: {exc}")

    clips = [VideoFileClip(p) for p in source_paths]
    try:
        final = concatenate_videoclips(clips, method="compose")
        output_path, _digest = save_bytes(user_id, b"", "concatenated.mp4", "video")
        final.write_videofile(str(output_path), codec="libx264", audio_codec="aac", fps=24, logger=None)
        size = Path(output_path).stat().st_size
        duration = final.duration
        width, height = final.w, final.h
        for c in clips:
            c.close()
        final.close()
        return {"path": str(output_path), "bytes": size, "duration": duration, "width": width, "height": height}
    except Exception as exc:  # noqa: BLE001
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        raise ProviderError("VideoEditor", f"Concatenation failed: {exc}")

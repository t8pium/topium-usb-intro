"""Decode/composite one cycle of a GIF, ignoring infinite-loop metadata."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageSequence, UnidentifiedImageError

MAX_FRAMES = 160
MAX_PIXELS = 1_048_576  # reject huge images before alloc
MAX_RGBA_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class GifFrame:
    rgba: bytes
    width: int
    height: int
    duration_ms: int


def load_one_cycle(file: str | Path) -> list[GifFrame]:
    """GIF playback frames in original order, regardless of GIF loop=0/forever.

    GIF delays lower than 20ms are normalized to 20ms to avoid spinning the UI.
    """
    result: list[GifFrame] = []
    cumulative = 0
    try:
        with Image.open(file) as gif:
            if gif.format != "GIF":
                raise ValueError("Expected GIF format")
            width, height = gif.size
            if width * height > MAX_PIXELS or width <= 0 or height <= 0:
                raise ValueError("GIF dimensions exceed safety limit")
            for frame in ImageSequence.Iterator(gif):
                if len(result) >= MAX_FRAMES:
                    raise ValueError("GIF has too many frames")
                duration = max(20, min(2000, int(frame.info.get("duration", 100) or 100)))
                rgba = frame.convert("RGBA").tobytes()
                cumulative += len(rgba)
                if cumulative > MAX_RGBA_BYTES:
                    raise ValueError("GIF frames exceed memory limit")
                result.append(GifFrame(rgba, width, height, duration))
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Unable to decode GIF: {exc}") from exc
    if not result:
        raise ValueError("GIF contains no frames")
    return result

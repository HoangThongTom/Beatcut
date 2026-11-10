"""One literal title, timed on the final montage rather than source footage."""

from __future__ import annotations

import math
import re


def validate_title(title: dict | None, duration: float | None = None) -> None:
    if title is None:
        return
    if not isinstance(title, dict) or set(title) != {
        "text", "start", "end", "position", "color", "size",
    }:
        raise ValueError("Invalid title settings.")
    text = title["text"]
    if (not isinstance(text, str) or not text.strip() or len(text) > 120
            or any(ord(char) < 32 and char != "\n" for char in text)):
        raise ValueError("Enter title text from 1 to 120 characters, without control characters.")
    for key in ("start", "end", "size"):
        if type(title[key]) not in (int, float) or not math.isfinite(title[key]):
            raise ValueError("Title times and size must be finite numbers.")
    if title["start"] < 0 or title["end"] - title["start"] < 0.1 - 1e-9:
        raise ValueError("Title end must be at least 0.1s after start, with start at or after 0.")
    if duration is not None and title["end"] > duration + 1e-9:
        raise ValueError(f"Title must end within the {duration:.2f}s montage. Adjust its times.")
    if title["position"] not in ("top", "center", "bottom"):
        raise ValueError("Choose top, center or bottom for the title.")
    if not isinstance(title["color"], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", title["color"]):
        raise ValueError("Title color must be a six-digit hex color.")
    if not 2 <= title["size"] <= 8:
        raise ValueError("Title size must be between 2 and 8 percent.")

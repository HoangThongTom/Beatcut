"""Portable edit decisions; media must be supplied again when reopening."""

from __future__ import annotations

import json
import math
import re

from .editing import rows_to_segments, validate_segments
from .titles import validate_title
from .types import Segment


def load_project(raw: bytes) -> dict:
    if len(raw) > 1_000_000:
        raise ValueError("Project files must be smaller than 1 MB.")
    try:
        data = json.loads(raw)
        if data["format"] != "beatcut-project" or data["version"] != 1:
            raise ValueError
        sources = data["sources"]
        for kind in ("video", "music"):
            source = sources[kind]
            if not isinstance(source["name"], str) or len(source["name"]) > 256:
                raise ValueError
            if not re.fullmatch(r"[a-f0-9]{64}", source["sha256"]):
                raise ValueError
        duration = data["duration"]
        if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
            raise ValueError
        rows = data["rows"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
            raise ValueError
        for row in rows:
            if type(row["Keep"]) is not bool or not math.isfinite(row["Order"]):
                raise ValueError
            if any(type(row[key]) not in (int, float)
                   for key in ("Order", "Start (s)", "End (s)")):
                raise ValueError
            validate_segments([Segment(row["Start (s)"], row["End (s)"])], duration)
        selection = rows_to_segments(rows, duration)
        settings = data["settings"]
        required = {
            "music_start_s", "keep_game_audio", "game_audio_volume", "music_volume",
        }
        if not required <= set(settings) or set(settings) - required - {"title"}:
            raise ValueError
        validate_title(settings.get("title"), sum(s.duration for s in selection))
        if type(settings["keep_game_audio"]) is not bool:
            raise ValueError
        for key in ("music_start_s", "game_audio_volume", "music_volume"):
            if type(settings[key]) not in (int, float) or not math.isfinite(settings[key]):
                raise ValueError
            if settings[key] < 0 or (key != "music_start_s" and settings[key] > 2):
                raise ValueError
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError, RecursionError) as exc:
        raise ValueError("Invalid or unsupported BeatCut project file.") from exc
    return {
        "format": "beatcut-project", "version": 1,
        "sources": {kind: {"name": sources[kind]["name"], "sha256": sources[kind]["sha256"]}
                    for kind in ("video", "music")},
        "duration": duration,
        "rows": [{key: row[key] for key in ("Keep", "Order", "Start (s)", "End (s)")}
                 for row in rows],
        "settings": settings,
    }


def save_project(project: dict) -> bytes:
    data = {
        "format": "beatcut-project", "version": 1,
        "sources": project["sources"], "duration": project["duration"],
        "rows": project["rows"],
        "settings": {key: project["config"][key] for key in (
            "music_start_s", "keep_game_audio", "game_audio_volume", "music_volume",
        )},
    }
    if project["config"].get("title") is not None:
        data["settings"]["title"] = project["config"]["title"]
    raw = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
    load_project(raw)
    return raw

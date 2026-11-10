"""Independent human annotations and conservative two-person agreement."""

from __future__ import annotations

import json
import math
import re
from collections import Counter

from .editing import validate_segments
from .types import Segment


def validate_annotations(data: dict) -> dict:
    try:
        if (set(data) != {"format", "version", "video", "sha256", "duration_s",
                          "annotator", "highlights"}
                or data["format"] != "beatcut-annotations"
                or type(data["version"]) is not int or data["version"] != 1):
            raise ValueError("Use an independent annotation file, not a montage/project file.")
        if (not isinstance(data["video"], str) or not 1 <= len(data["video"]) <= 256
                or any(char in data["video"] for char in ("/", "\\"))):
            raise ValueError("Store the video filename without its folder path.")
        if not isinstance(data["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", data["sha256"]):
            raise ValueError("Invalid video fingerprint.")
        if (not isinstance(data["annotator"], str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", data["annotator"])):
            raise ValueError("Annotator ID: use 1–32 letters, digits, underscores or hyphens.")
        duration = data["duration_s"]
        if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
            raise ValueError("Invalid source duration.")
        items = data["highlights"]
        if not isinstance(items, list) or len(items) > 1000:
            raise ValueError("Use at most 1000 highlight intervals.")
        segments = []
        for item in items:
            if set(item) != {"start", "end"} or any(
                type(item[key]) not in (int, float) for key in ("start", "end")
            ):
                raise ValueError("Highlights must contain numeric start/end times only.")
            segments.append(Segment(item["start"], item["end"]))
        if segments:
            validate_segments(segments, duration)
        segments.sort(key=lambda segment: segment.start)
        if any(right.start < left.end
               for left, right in zip(segments, segments[1:], strict=False)):
            raise ValueError("Merge overlapping or duplicate highlights before saving.")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid independent annotation file.") from exc
    return {**data, "highlights": [{"start": s.start, "end": s.end} for s in segments]}


def load_annotations(raw: bytes) -> dict:
    if len(raw) > 1_000_000:
        raise ValueError("Annotation files must be smaller than 1 MB.")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, RecursionError) as exc:
        raise ValueError("Invalid annotation JSON.") from exc
    return validate_annotations(data)


def save_annotations(data: dict) -> bytes:
    return json.dumps(validate_annotations(data), ensure_ascii=False, indent=2).encode("utf-8")


def agree_annotations(left: dict, right: dict) -> dict:
    """Keep only mutually unique matches within ±2s at both endpoints."""
    left, right = validate_annotations(left), validate_annotations(right)
    if left["annotator"] == right["annotator"]:
        raise ValueError("Use labels from two different independent annotators.")
    if left["sha256"] != right["sha256"] or left["duration_s"] != right["duration_s"]:
        raise ValueError("Both annotation files must refer to the same original video.")
    pairs = [(i, j) for i, a in enumerate(left["highlights"])
             for j, b in enumerate(right["highlights"])
             if abs(a["start"] - b["start"]) <= 2 and abs(a["end"] - b["end"]) <= 2]
    counts_a, counts_b = Counter(i for i, _ in pairs), Counter(j for _, j in pairs)
    agreed = [(i, j) for i, j in pairs if counts_a[i] == counts_b[j] == 1]
    highlights = [{key: (left["highlights"][i][key] + right["highlights"][j][key]) / 2
                   for key in ("start", "end")} for i, j in agreed]
    return {
        "video": left["video"], "sha256": left["sha256"], "duration_s": left["duration_s"],
        "annotators": [left["annotator"], right["annotator"]], "highlights": highlights,
        "agreement": {"tolerance_s": 2, "matched": len(agreed),
                      "excluded_a": len(left["highlights"]) - len(agreed),
                      "excluded_b": len(right["highlights"]) - len(agreed)},
    }

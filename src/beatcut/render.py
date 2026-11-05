"""ffmpeg rendering: cut, concatenate, lay the music over the result.

Segments are re-encoded (not stream-copied) because a copy can only start on a
keyframe, which would put cuts up to a few seconds off the beat. Re-encoding is
the price of frame accuracy; NVENC can be swapped in in M3.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from .media import FFMPEG
from .types import Segment


def cut(
    video: str | Path,
    segment: Segment,
    out: str | Path,
    crf: int = 20,
    preset: str = "veryfast",
) -> Path:
    """Re-encode a single time range to its own file."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.1, segment.duration)
    cmd = [
        FFMPEG, "-y", "-v", "error",
        "-ss", f"{segment.start:.3f}",
        "-i", str(video),
        "-t", f"{duration:.3f}",
        "-an",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


def concat(parts: Sequence[str | Path], out: str | Path) -> Path:
    """Join clips that were encoded with identical settings, without re-encoding."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    list_file = out.with_suffix(".concat.txt")

    lines = []
    for part in parts:
        # ffmpeg's concat demuxer wants forward slashes and escaped quotes.
        safe = str(Path(part).resolve()).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{safe}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cmd = [
        FFMPEG, "-y", "-v", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


def mux_music(
    video: str | Path,
    music: str | Path,
    out: str | Path,
    music_start_s: float = 0.0,
) -> Path:
    """Replace the (already stripped) audio with the music track.

    ``apad`` pads a short track with silence so ``-shortest`` stops on the video,
    not on the music.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-v", "error",
        "-i", str(video),
        "-ss", f"{max(0.0, music_start_s):.3f}",
        "-i", str(music),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "apad",
        "-shortest",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out

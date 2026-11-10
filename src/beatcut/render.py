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
    with_audio: bool = True,
) -> Path:
    """Re-encode a single time range to its own file.

    `with_audio` keeps the game sound, which is mixed under the music later.
    Every part must use the same settings or the concat demuxer refuses to
    stitch them, so this flag has to be identical for all parts of one montage.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.1, segment.duration)
    cmd = [
        FFMPEG, "-y", "-v", "error",
        "-ss", f"{segment.start:.3f}",
        "-i", str(video),
        "-t", f"{duration:.3f}",
    ]
    if not with_audio:
        cmd.append("-an")
    cmd += [
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p",
    ]
    if with_audio:
        cmd += ["-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "44100"]
    cmd.append(str(out))
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
    music_volume: float = 1.0,
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
        "-af", f"volume={music_volume:.3f},alimiter=limit=0.95:level=false,apad",
        "-shortest",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


def mix_filter(game_volume: float = 0.5, music_volume: float = 0.7) -> str:
    """ffmpeg filter that lays the music under the game audio.

    ``normalize=0`` keeps amix from halving both inputs, which would make the
    result quieter than either source. ``duration=first`` ends the mix with the
    game audio, so a long music track cannot stretch the video. The limiter
    matters: a mastered track already peaks at 0 dBFS, so summing anything on
    top of it clips without one.
    """
    return (
        f"[0:a]volume={game_volume:.3f}[game];"
        f"[1:a]volume={music_volume:.3f}[music];"
        "[game][music]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95:level=false[aout]"
    )


def mux_mixed(
    video: str | Path,
    music: str | Path,
    out: str | Path,
    music_start_s: float = 0.0,
    game_volume: float = 0.5,
    music_volume: float = 0.7,
) -> Path:
    """Keep the game audio and mix the music underneath it."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-v", "error",
        "-i", str(video),
        "-ss", f"{max(0.0, music_start_s):.3f}",
        "-i", str(music),
        "-filter_complex", mix_filter(game_volume, music_volume),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out

"""Thin wrappers around ffmpeg/ffprobe.

Every call goes through an argument list (never a shell string) so file names
with spaces or quotes are safe. Frame streaming is done through a pipe instead
of decoding with OpenCV, which keeps memory flat on hour-long VODs.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from .types import VideoInfo

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE_BIN", "ffprobe")


def _parse_rate(value: str) -> float:
    """'30000/1001' -> 29.97. Returns 0.0 when ffprobe reports something odd."""
    num, _, den = str(value).partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _display_size(video: dict) -> tuple[int, int]:
    """Coded size, swapped when a rotation matrix makes ffmpeg swap it too.

    Phone recordings are often stored as landscape frames plus a rotation
    flag. ffmpeg's autorotate applies that flag while decoding, so the frames
    we receive are portrait even though ffprobe reports 1920x1080. Reporting
    the displayed size keeps the frame-buffer maths in `iter_frames_gray`
    correct and makes the manifest match what a human sees.
    """
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)

    rotation = 0.0
    for side_data in video.get("side_data_list") or []:
        if "rotation" in side_data:
            try:
                rotation = float(side_data["rotation"])
            except (TypeError, ValueError):
                pass
    if rotation == 0.0:
        try:
            rotation = float((video.get("tags") or {}).get("rotate", 0))
        except (TypeError, ValueError):
            rotation = 0.0

    if abs(rotation) % 180 == 90:
        width, height = height, width
    return width, height


def probe(path: str | Path) -> VideoInfo:
    """Read duration, resolution, frame rate and audio presence."""
    cmd = [
        FFPROBE,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(completed.stdout or "{}")

    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError(f"no video stream found in {path}")

    duration = data.get("format", {}).get("duration") or video.get("duration") or 0.0
    width, height = _display_size(video)
    return VideoInfo(
        path=str(Path(path).resolve()),
        duration_s=float(duration),
        width=width,
        height=height,
        fps=_parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0"),
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
    )


def audio_duration(path: str | Path) -> float:
    """Read a music track's duration without decoding the full file."""
    completed = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "a:0", "-show_entries",
         "format=duration:stream=duration,codec_type", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(completed.stdout or "{}")
    streams = data.get("streams", [])
    if not streams:
        raise ValueError(f"no audio stream found in {path}")
    duration = float(data.get("format", {}).get("duration") or streams[0].get("duration") or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError(f"cannot determine music duration: {path}")
    return duration


def find_gaps(
    times: np.ndarray,
    factor: float = 1.6,
    min_gap_s: float = 0.08,
) -> list[tuple[float, float]]:
    """Ranges where consecutive frames are further apart than they should be.

    A phone screen recorder drops frames when the device stutters; cutting a
    clip through one of those holes is what a viewer sees as a freeze.
    """
    times = np.asarray(times, dtype=float)
    if times.size < 3:
        return []
    steps = np.diff(times)
    threshold = max(float(np.median(steps)) * factor, min_gap_s)
    return [
        (float(times[i]), float(times[i + 1]))
        for i in np.where(steps > threshold)[0]
    ]


def frame_gaps(path: str | Path, factor: float = 1.6) -> list[tuple[float, float]]:
    """Return the ranges where the recording dropped frames.

    Reads packet timestamps, not frame timestamps: ``-show_entries frame=``
    forces ffprobe to decode every frame, which on a 60fps 1170p HEVC phone
    recording takes minutes. Packets carry the same presentation timing and
    parse in about a second, because nothing is decoded.

    Packets arrive in decode order, so they are sorted by pts before diffing.
    """
    cmd = [
        FFPROBE, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "packet=pts_time",
        "-of", "csv=p=0",
        str(path),
    ]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)

    times: list[float] = []
    for line in completed.stdout.splitlines():
        value = line.strip().split(",")[0]
        try:
            times.append(float(value))
        except ValueError:
            continue
    return find_gaps(np.sort(np.asarray(times, dtype=float)), factor)


def extract_audio(video: str | Path, out_wav: str | Path, sr: int = 22050) -> Path:
    """Decode the first audio stream to mono 16-bit PCM at `sr` Hz."""
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-v", "error",
        "-i", str(video),
        "-vn", "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True)
    return out_wav


def iter_frames_gray(
    video: str | Path,
    info: VideoInfo,
    sample_fps: float = 4.0,
    width: int = 320,
) -> Iterator[tuple[float, np.ndarray]]:
    """Yield `(timestamp_s, gray_frame)` pairs at roughly `sample_fps`."""
    if info.width <= 0 or info.height <= 0:
        raise ValueError(f"bad frame size for {video}: {info.width}x{info.height}")

    height = max(2, round(info.height * width / info.width))
    height += height % 2  # yuv-friendly even height

    cmd = [
        FFMPEG, "-v", "error",
        "-i", str(video),
        "-vf", f"fps={sample_fps},scale={width}:{height}",
        "-f", "rawvideo", "-pix_fmt", "gray",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    frame_bytes = width * height
    index = 0
    try:
        assert proc.stdout is not None
        while True:
            buffer = proc.stdout.read(frame_bytes)
            if not buffer or len(buffer) < frame_bytes:
                break
            frame = np.frombuffer(buffer, dtype=np.uint8).reshape(height, width)
            yield index / sample_fps, frame
            index += 1
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()

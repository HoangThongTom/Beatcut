"""The end-to-end job: probe -> score -> select -> align -> render.

:func:`analyze` stops before rendering and returns the chosen segments, so the
evaluation script (and the future API) can measure clip selection on its own.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .beats import align_segment, detect_beats
from .config import Config
from .media import extract_audio, probe
from .render import concat, cut, mux_mixed, mux_music
from .scoring import audio_energy_curve, fuse, motion_energy_curve
from .select import select_segments, window_scores
from .types import BeatGrid, Segment, VideoInfo


@dataclass
class Analysis:
    video: VideoInfo
    grid: BeatGrid
    segments: list[Segment]

    def to_dict(self) -> dict:
        return {
            "video": self.video.to_dict(),
            "music": self.grid.to_dict(),
            "segments": [segment.to_dict() for segment in self.segments],
            "total_duration_s": round(sum(s.duration for s in self.segments), 3),
        }


def _work_dir(out_path: Path, work_dir: str | Path | None) -> Path:
    if work_dir is not None:
        return Path(work_dir)
    return out_path.parent / f"{out_path.stem}_work"


def analyze(
    video: str | Path,
    music: str | Path,
    config: Config | None = None,
    work_dir: str | Path | None = None,
) -> Analysis:
    """Pick the highlight segments without rendering anything."""
    cfg = config or Config()
    video = Path(video)
    music = Path(music)

    if not video.exists():
        raise FileNotFoundError(f"video not found: {video}")
    if not music.exists():
        raise FileNotFoundError(f"music not found: {music}")

    work = Path(work_dir) if work_dir is not None else Path("outputs/analysis")
    work.mkdir(parents=True, exist_ok=True)

    info = probe(video)

    curves: dict[str, tuple] = {}
    motion_times, motion_values = motion_energy_curve(
        str(video), info, cfg.sample_fps, cfg.frame_width
    )
    curves["motion"] = (motion_times, motion_values)

    if info.has_audio:
        gameplay_wav = extract_audio(video, work / "gameplay_audio.wav", cfg.audio_sr)
        curves["audio"] = audio_energy_curve(str(gameplay_wav), cfg.audio_sr)

    music_wav = extract_audio(music, work / "music.wav", cfg.audio_sr)
    grid = detect_beats(str(music_wav), cfg.audio_sr, cfg.beats_per_bar)

    weights = {"motion": cfg.motion_weight, "audio": cfg.audio_weight}
    fused = fuse(motion_times, curves, weights)

    candidates = window_scores(motion_times, fused, cfg.window_s, cfg.stride_s)
    if not candidates:
        raise RuntimeError(
            f"video is shorter than one window ({cfg.window_s:.1f}s); "
            "lower window_s in your config or use a longer VOD"
        )

    picked = select_segments(
        candidates, cfg.target_duration_s, cfg.min_gap_s, cfg.max_segments
    )

    aligned: list[Segment] = []
    for segment in picked:
        start, end = align_segment(
            segment.start,
            segment.end,
            grid,
            snap_tol_s=cfg.snap_tol_s,
            min_clip_s=cfg.min_clip_s,
            max_clip_s=cfg.max_clip_s,
        )
        end = min(end, info.duration_s)
        start = max(0.0, min(start, end - cfg.min_clip_s))
        aligned.append(Segment(round(start, 3), round(end, 3), round(segment.score, 4)))

    return Analysis(video=info, grid=grid, segments=aligned)


def run(
    video: str | Path,
    music: str | Path,
    out: str | Path,
    config: Config | None = None,
    work_dir: str | Path | None = None,
    keep_work: bool = False,
) -> dict:
    """Analyze, render the montage, and write a manifest next to it."""
    cfg = config or Config()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    work = _work_dir(out, work_dir)
    work.mkdir(parents=True, exist_ok=True)

    analysis = analyze(video, music, cfg, work_dir=work)

    keep_game = cfg.keep_game_audio and analysis.video.has_audio
    parts = [
        cut(
            video,
            segment,
            work / f"part_{index:02d}.mp4",
            cfg.crf,
            cfg.preset,
            with_audio=keep_game,
        )
        for index, segment in enumerate(analysis.segments)
    ]
    silent = concat(parts, work / "montage_silent.mp4")

    music_start = cfg.music_start_s
    if music_start is None:
        music_start = analysis.grid.downbeats[0] if analysis.grid.downbeats else 0.0

    if keep_game:
        mux_mixed(silent, music, out, music_start, cfg.game_audio_volume, cfg.music_volume)
    else:
        mux_music(silent, music, out, music_start)

    manifest = {
        "beatcut_version": __version__,
        "elapsed_s": round(time.perf_counter() - started, 2),
        "output": str(out.resolve()),
        "music_start_s": round(float(music_start), 3),
        "game_audio_mixed": keep_game,
        "config": cfg.to_dict(),
        "analysis": analysis.to_dict(),
    }
    out.with_suffix(".json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if not keep_work:
        for part in parts:
            part.unlink(missing_ok=True)
        for leftover in (silent, work / "gameplay_audio.wav", work / "music.wav"):
            Path(leftover).unlink(missing_ok=True)

    return manifest

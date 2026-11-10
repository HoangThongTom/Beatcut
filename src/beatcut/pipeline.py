"""The end-to-end job: probe -> score -> select -> align -> render.

:func:`analyze` stops before rendering and returns the chosen segments, so the
evaluation script (and the future API) can measure clip selection on its own.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import __version__, cache
from .beats import align_segment, bar_duration, detect_beats, quantize_duration
from .config import Config
from .editing import validate_segments
from .media import extract_audio, frame_gaps, probe
from .render import concat, cut, mux_mixed, mux_music
from .scoring import audio_energy_curve, boost_curve, fuse, motion_energy_curve
from .select import select_segments, window_scores
from .types import BeatGrid, Segment, VideoInfo


@dataclass
class Analysis:
    video: VideoInfo
    grid: BeatGrid
    segments: list[Segment]
    bar_s: float = 0.0
    dropped_windows: int = 0
    kill_times: list[float] | None = None

    def to_dict(self) -> dict:
        return {
            "video": self.video.to_dict(),
            "music": self.grid.to_dict(),
            "bar_s": round(self.bar_s, 4),
            "dropped_windows": self.dropped_windows,
            "kill_count": len(self.kill_times or []),
            "kill_times": [round(t, 2) for t in (self.kill_times or [])],
            "segments": [segment.to_dict() for segment in self.segments],
            "total_duration_s": round(sum(s.duration for s in self.segments), 3),
        }


def _work_dir(out_path: Path, work_dir: str | Path | None) -> Path:
    if work_dir is not None:
        return Path(work_dir)
    return out_path.parent / f"{out_path.stem}_work"


def music_beats(music: str | Path, cfg: Config, work: Path,
                progress: Callable[[str], None] | None = None) -> BeatGrid:
    """Load or detect music beats without analyzing the gameplay."""
    report = progress or (lambda message: None)
    key = cache.fingerprint(music, cfg, "music")
    cached = cache.load(cfg.cache_dir, key) if cfg.use_cache else None
    grid = cached[1] if cached is not None else None
    if grid is not None:
        report("Reusing saved music beats.")
        return grid
    report("Analyzing the music beat…")
    work.mkdir(parents=True, exist_ok=True)
    music_wav = extract_audio(music, work / "music.wav", cfg.audio_sr)
    grid = detect_beats(str(music_wav), cfg.audio_sr, cfg.beats_per_bar)
    if cfg.use_cache:
        cache.save(cfg.cache_dir, key, {}, grid)
    return grid


def analyze(
    video: str | Path,
    music: str | Path,
    config: Config | None = None,
    work_dir: str | Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> Analysis:
    """Pick the highlight segments without rendering anything."""
    cfg = config or Config()
    report = progress or (lambda message: None)
    video = Path(video)
    music = Path(music)

    if not video.exists():
        raise FileNotFoundError(f"video not found: {video}")
    if not music.exists():
        raise FileNotFoundError(f"music not found: {music}")

    work = Path(work_dir) if work_dir is not None else Path("outputs/analysis")
    work.mkdir(parents=True, exist_ok=True)

    report("Reading gameplay information…")
    info = probe(video)

    cache_dir = Path(cfg.cache_dir)
    video_key = cache.fingerprint(video, cfg)
    cached = cache.load(cache_dir, video_key) if cfg.use_cache else None

    if cached is not None:
        report("Reusing saved gameplay analysis.")
        curves, _ = cached
        motion_times = curves["motion"][0]
    else:
        report("Analyzing gameplay motion…")
        curves = {}
        motion_times, motion_values = motion_energy_curve(
            str(video), info, cfg.sample_fps, cfg.frame_width
        )
        curves["motion"] = (motion_times, motion_values)

        if info.has_audio:
            report("Analyzing gameplay audio…")
            gameplay_wav = extract_audio(video, work / "gameplay_audio.wav", cfg.audio_sr)
            curves["audio"] = audio_energy_curve(str(gameplay_wav), cfg.audio_sr)

        if cfg.use_cache:
            cache.save(cache_dir, video_key, curves)

    grid = music_beats(music, cfg, work, progress)

    weights = {"motion": cfg.motion_weight, "audio": cfg.audio_weight}
    fused = fuse(motion_times, curves, weights)

    kill_times: list[float] = []
    if cfg.kill_crop:
        kill_cache_key = cache.kill_key(video_key, cfg.kill_crop)
        kill_times = (
            cache.load_kills(cache_dir, kill_cache_key) if cfg.use_cache else None
        )
        if kill_times is None:
            report("Detecting gameplay kills…")
            from .scoreboard import extract_kills

            events = extract_kills(video, tuple(cfg.kill_crop), 2.0)
            kill_times = [event.time for event in events]
            if cfg.use_cache:
                cache.save_kills(cache_dir, kill_cache_key, kill_times)
        else:
            report("Reusing saved kill detections.")
        fused = boost_curve(
            motion_times, fused, kill_times, cfg.kill_window_s, cfg.kill_boost
        )

    report("Selecting highlights and aligning cuts to the music…")
    candidates = window_scores(motion_times, fused, cfg.window_s, cfg.stride_s)
    dropped = 0
    if cfg.skip_frame_drops and candidates:
        gaps = frame_gaps(video)
        if gaps:
            kept = [
                candidate
                for candidate in candidates
                if not any(gap_start < candidate[1] and gap_end > candidate[0]
                           for gap_start, gap_end in gaps)
            ]
            dropped = len(candidates) - len(kept)
            candidates = kept

    if not candidates:
        raise RuntimeError(
            f"no usable window ({cfg.window_s:.1f}s); the video is shorter than "
            "one window, or every window contains a recording stutter"
        )

    picked = select_segments(
        candidates, cfg.target_duration_s, cfg.min_gap_s, cfg.max_segments
    )

    # Snap each clip to a whole number of bars. Cuts land at cumulative offsets,
    # so if every clip is a multiple of one bar and the music starts on a
    # downbeat, every cut in the montage lands on a bar line. Snapping the
    # source timestamps instead would align nothing: the music is laid over the
    # concatenated result, not over the source timeline.
    bar_s = bar_duration(grid.tempo, cfg.beats_per_bar)
    fps = info.fps if info.fps > 0 else 30.0

    aligned: list[Segment] = []
    ideal_end = 0.0     # exact bar grid, in seconds
    emitted = 0         # frames actually encoded so far
    for segment in picked:
        if cfg.quantize_to_bars and bar_s > 0:
            length = quantize_duration(
                segment.duration, bar_s, cfg.min_clip_s, cfg.max_clip_s
            )
            # Rounding each clip on its own lets the error accumulate: after
            # eight clips the last cut can sit 50ms off the grid. Rounding the
            # cumulative position instead keeps every cut within half a frame.
            ideal_end += length
            end_frame = round(ideal_end * fps)
            clip_length = (end_frame - emitted) / fps
            emitted = end_frame
            start = segment.start
            end = min(start + clip_length, info.duration_s)
        else:
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
        aligned.append(Segment(start, end, segment.score))

    analysis = Analysis(
        video=info,
        grid=grid,
        segments=aligned,
        bar_s=bar_s,
        dropped_windows=dropped,
        kill_times=kill_times,
    )
    return analysis


def run(
    video: str | Path,
    music: str | Path,
    out: str | Path,
    config: Config | None = None,
    work_dir: str | Path | None = None,
    keep_work: bool = False,
    progress: Callable[[str], None] | None = None,
    segments: list[Segment] | None = None,
) -> dict:
    """Analyze, render the montage, and write a manifest next to it."""
    cfg = config or Config()
    report = progress or (lambda message: None)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    work = _work_dir(out, work_dir)
    work.mkdir(parents=True, exist_ok=True)

    if segments is None:
        analysis = analyze(video, music, cfg, work_dir=work, progress=progress)
    else:
        report("Loading your edited highlight selection…")
        info = probe(video)
        analysis = Analysis(info, BeatGrid(), validate_segments(segments, info.duration_s))

    keep_game = cfg.keep_game_audio and analysis.video.has_audio
    parts = []
    total = len(analysis.segments)
    report(f"Rendering highlights: 0/{total} completed.")
    for index, segment in enumerate(analysis.segments):
        parts.append(cut(
            video,
            segment,
            work / f"part_{index:02d}.mp4",
            cfg.crf,
            cfg.preset,
            with_audio=keep_game,
        ))
        report(f"Rendering highlights: {index + 1}/{total} completed.")
    report("Joining highlight clips…")
    silent = concat(parts, work / "montage_silent.mp4")

    music_start = cfg.music_start_s
    if music_start is None:
        music_start = analysis.grid.downbeats[0] if analysis.grid.downbeats else 0.0

    report("Mixing audio and exporting the MP4…")
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

    report("Montage ready.")
    return manifest

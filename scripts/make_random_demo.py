"""Render reproducible random demos; these are not human highlight annotations.

Example:
    python scripts/make_random_demo.py data/raw/match_03.mp4 --music data/raw/song.mp3
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from beatcut.config import Config
from beatcut.editing import validate_segments
from beatcut.media import audio_duration, probe
from beatcut.pipeline import run
from beatcut.types import Segment


def sample_segments(duration: float, seed: int) -> list[Segment]:
    """Pick one 9-second clip from each fifth of the source, in source order."""
    if not math.isfinite(duration) or duration < 45:
        raise ValueError("Random demos require at least 45 seconds of source video.")
    rng = random.Random(seed)
    width = duration / 5
    clips = []
    for index in range(5):
        start = round(rng.uniform(index * width, (index + 1) * width - 9), 3)
        clips.append(Segment(start, round(start + 9, 3)))
    validate_segments(clips, duration)
    assert all(a.end <= b.start for a, b in zip(clips, clips[1:], strict=False))
    return clips


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--music", required=True, type=Path)
    parser.add_argument("--out", default="outputs/random-demo", type=Path)
    parser.add_argument("--seed", default=42, type=int)
    args = parser.parse_args()
    if len({video.stem for video in args.videos}) != len(args.videos):
        parser.error("Use unique video filenames to avoid overwriting results.")
    if audio_duration(args.music) < 45:
        parser.error("Music must contain at least 45 seconds of audio.")
    plans = []
    for index, video in enumerate(args.videos):
        info = probe(video)
        seed = args.seed + index
        clips = sample_segments(info.duration_s, seed)
        assert clips == sample_segments(info.duration_s, seed)
        plans.append((video, info, seed, clips))
    args.out.mkdir(parents=True, exist_ok=False)
    summary = {"purpose": "random_demo_only_not_ground_truth", "results": []}
    for video, info, seed, clips in plans:
        output = args.out / f"{video.stem}_random_demo.mp4"
        print(f"Starting {video.name}, seed={seed}", flush=True)
        cfg = Config(
            target_duration_s=45, music_start_s=0, crf=23, preset="veryfast",
            game_audio_volume=0.35, music_volume=0.7,
            title={"text": "DEMO · NGẪU NHIÊN", "start": 0, "end": 45,
                   "position": "top", "color": "#67E8DF", "size": 3},
        )
        manifest = run(video, args.music, output, cfg, segments=clips,
                       progress=lambda message: print(message, flush=True))
        manifest["sampling"] = {"method": "stratified_random", "seed": seed,
                                "purpose": summary["purpose"]}
        output.with_suffix(".json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        rendered = probe(output)
        if not rendered.has_audio or abs(rendered.duration_s - 45) > 0.5:
            raise RuntimeError(f"Unexpected rendered duration/audio in {output}.")
        summary["results"].append({
            "source": video.name, "source_duration_s": info.duration_s,
            "output": output.name, "seed": seed, "n_clips": len(clips),
            "duration_s": rendered.duration_s, "bytes": output.stat().st_size,
        })
        (args.out / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        print(f"Verified {output}: {rendered.duration_s:.2f}s", flush=True)


if __name__ == "__main__":
    main()

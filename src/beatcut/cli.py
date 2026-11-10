"""Command line entry point: ``beatcut doctor | analyze | run``."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import Config

# ---------------------------------------------------------------- doctor ----

def _check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {label}{(' - ' + detail) if detail else ''}")
    return ok


def cmd_doctor(_args: argparse.Namespace) -> int:
    """Report whether this machine can actually run the pipeline."""
    healthy = True

    major, minor = sys.version_info[:2]
    healthy &= _check(
        "python version",
        (major, minor) >= (3, 10) and (major, minor) < (3, 13),
        f"{major}.{minor} (need >=3.10,<3.13 for numba/librosa wheels)",
    )

    for binary in ("ffmpeg", "ffprobe"):
        path = shutil.which(binary)
        version = ""
        if path:
            try:
                out = subprocess.run(
                    [binary, "-version"], capture_output=True, text=True, check=False
                ).stdout
                version = out.splitlines()[0][:60] if out else ""
            except OSError:
                path = None
        healthy &= _check(binary, path is not None, version or path or "not on PATH")

    for module in ("numpy", "librosa", "yaml"):
        try:
            __import__(module)
            healthy &= _check(f"import {module}", True)
        except ImportError:
            healthy &= _check(f"import {module}", False, "run scripts/bootstrap.ps1")

    print("\nready" if healthy else "\nnot ready - fix the FAIL lines above")
    return 0 if healthy else 1


# ---------------------------------------------------------------- shared ----

def _load_config(args: argparse.Namespace) -> Config:
    cfg = Config.load(args.config) if args.config else Config()
    if getattr(args, "target_duration", None) is not None:
        cfg.target_duration_s = args.target_duration
    if getattr(args, "max_segments", None) is not None:
        cfg.max_segments = args.max_segments
    return cfg


def cmd_analyze(args: argparse.Namespace) -> int:
    from .pipeline import analyze

    result = analyze(args.video, args.music, _load_config(args))
    payload = result.to_dict()

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(
        f"video   {payload['video']['duration_s']:.1f}s "
        f"{payload['video']['width']}x{payload['video']['height']}"
        f" @ {payload['video']['fps']:.1f}fps"
    )
    print(f"music   {payload['music']['tempo_bpm']:.1f} BPM, "
          f"{payload['music']['n_beats']} beats")
    print(f"picked  {len(payload['segments'])} segments, "
          f"{payload['total_duration_s']:.1f}s total\n")
    for segment in payload["segments"]:
        print(
            f"  {segment['start']:8.2f} -> {segment['end']:8.2f} "
            f"({segment['duration']:5.2f}s)  score={segment['score']:.3f}"
        )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .pipeline import run

    manifest = run(
        args.video,
        args.music,
        args.out,
        _load_config(args),
        keep_work=args.keep_work,
    )
    analysis = manifest["analysis"]
    print(
        f"rendered {args.out} in {manifest['elapsed_s']:.1f}s "
        f"({len(analysis['segments'])} clips, "
        f"{analysis['total_duration_s']:.1f}s)\n"
        f"manifest {Path(args.out).with_suffix('.json')}"
    )
    return 0


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"beatcut {__version__}")
    return 0


# ------------------------------------------------------------------ main ----

def cmd_score(args: argparse.Namespace) -> int:
    from .evaluate import evaluate, format_report, load_labels, load_selection

    picked = load_selection(args.selection)
    highlights = load_labels(args.labels)
    if not highlights:
        print(f"error: {args.labels} contains no highlights", file=sys.stderr)
        return 1

    metrics = evaluate(picked, highlights, k=args.k, threshold=args.threshold)
    print(format_report(metrics))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


def cmd_kills(args: argparse.Namespace) -> int:
    from .scoreboard import extract_kills

    parts = [part.strip() for part in args.box.split(",")]
    if len(parts) != 4:
        print("error: --box wants x,y,width,height", file=sys.stderr)
        return 2
    box = tuple(int(value) for value in parts)

    events = extract_kills(args.video, box, args.fps, dump_samples=args.samples)
    print(f"read the kill counter {box} at {args.fps}/s -> {len(events)} kills\n")
    for event in events:
        print(f"  {event.time:8.2f}s  kill #{event.count}")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(
            json.dumps({"box": list(box), "events": [e.to_dict() for e in events]}, indent=2),
            encoding="utf-8",
        )
        print(f"\nwrote {args.json}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beatcut",
        description="Turn a long gameplay VOD into a beat-synced highlight montage.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor", help="check ffmpeg, python and libraries")
    p_doctor.set_defaults(func=cmd_doctor)

    p_version = sub.add_parser("version", help="print the version")
    p_version.set_defaults(func=cmd_version)

    p_analyze = sub.add_parser("analyze", help="pick clips without rendering")
    p_analyze.add_argument("video")
    p_analyze.add_argument("music")
    p_analyze.add_argument("-c", "--config", help="path to a YAML config")
    p_analyze.add_argument("--target-duration", type=float)
    p_analyze.add_argument("--max-segments", type=int)
    p_analyze.add_argument("--json", help="write the selection to this path")
    p_analyze.set_defaults(func=cmd_analyze)

    p_run = sub.add_parser("run", help="pick clips and render the montage")
    p_run.add_argument("video")
    p_run.add_argument("music")
    p_run.add_argument("-o", "--out", default="outputs/montage.mp4")
    p_run.add_argument("-c", "--config", help="path to a YAML config")
    p_run.add_argument("--target-duration", type=float)
    p_run.add_argument("--max-segments", type=int)
    p_run.add_argument("--keep-work", action="store_true", help="keep intermediate clips")
    p_run.set_defaults(func=cmd_run)

    p_score = sub.add_parser("score", help="score a selection against labelled highlights")
    p_score.add_argument("labels", help="label JSON, see docs/eval-protocol.md")
    p_score.add_argument("selection", help="JSON written by `beatcut analyze --json`")
    p_score.add_argument("-k", type=int, default=5, help="how many top clips to judge")
    p_score.add_argument("--threshold", type=float, default=0.5,
                         help="fraction of a clip that must overlap a label")
    p_score.add_argument("--json", help="write the metrics to this path")
    p_score.set_defaults(func=cmd_score)

    p_kills = sub.add_parser("kills", help="read the in-game kill counter with OCR")
    p_kills.add_argument("video")
    p_kills.add_argument("--box", required=True,
                         help="x,y,width,height of the kill digit, in displayed pixels")
    p_kills.add_argument("--fps", type=float, default=2.0, help="counter samples per second")
    p_kills.add_argument("--json", help="write the events to this path")
    p_kills.add_argument("--samples", help="dump every raw reading, for tuning")
    p_kills.set_defaults(func=cmd_kills)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

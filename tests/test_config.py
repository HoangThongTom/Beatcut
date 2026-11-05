"""Config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from beatcut.config import Config


def test_defaults_are_valid():
    cfg = Config()
    assert cfg.window_s > 0
    assert cfg.motion_weight + cfg.audio_weight > 0


def test_load_from_yaml(tmp_path: Path):
    path = tmp_path / "cfg.yaml"
    path.write_text("window_s: 4.0\nmax_segments: 3\n", encoding="utf-8")

    cfg = Config.load(path)

    assert cfg.window_s == 4.0
    assert cfg.max_segments == 3
    assert cfg.stride_s == Config().stride_s


def test_unknown_key_is_rejected(tmp_path: Path):
    path = tmp_path / "cfg.yaml"
    path.write_text("window_seconds: 4.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown keys"):
        Config.load(path)


def test_impossible_clip_lengths_are_rejected():
    with pytest.raises(ValueError, match="min_clip_s"):
        Config(min_clip_s=9.0, max_clip_s=3.0)


def test_zero_weights_are_rejected():
    with pytest.raises(ValueError, match="weight"):
        Config(motion_weight=0.0, audio_weight=0.0)

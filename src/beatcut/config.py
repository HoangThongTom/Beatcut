"""Run configuration: one dataclass, optionally overridden from a YAML file."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path

import yaml


@dataclass
class Config:
    # --- analysis ---
    sample_fps: float = 4.0
    frame_width: int = 320
    audio_sr: int = 22050

    # --- scoring ---
    motion_weight: float = 0.6
    audio_weight: float = 0.4

    # --- segment selection ---
    window_s: float = 6.0
    stride_s: float = 1.5
    target_duration_s: float = 45.0
    max_segments: int = 10
    min_gap_s: float = 1.0

    # --- beat alignment ---
    beats_per_bar: int = 4
    snap_tol_s: float = 0.25
    min_clip_s: float = 2.5
    max_clip_s: float = 10.0
    quantize_to_bars: bool = True

    # --- source quality ---
    skip_frame_drops: bool = True

    # --- render ---
    crf: int = 20
    preset: str = "veryfast"
    music_start_s: float | None = None

    # --- audio mix ---
    # Keeping the game sound is what makes a montage feel like gameplay rather
    # than a slideshow with a song over it.
    keep_game_audio: bool = True
    game_audio_volume: float = 0.5
    music_volume: float = 0.7

    # --- caching ---
    # The motion curve costs one full decode of the video. Selection parameters
    # do not change it, so cache it and make config tuning take seconds.
    use_cache: bool = True
    cache_dir: str = "data/interim/cache"

    # --- kill detection ---
    # x, y, width, height of the kill digit in the HUD. None disables it.
    kill_crop: list[int] | None = None
    kill_window_s: float = 5.0
    kill_boost: float = 0.6

    def __post_init__(self) -> None:
        if self.window_s <= 0 or self.stride_s <= 0:
            raise ValueError("window_s and stride_s must be positive")
        if self.kill_crop is not None:
            if len(self.kill_crop) != 4 or min(self.kill_crop) <= 0:
                raise ValueError("kill_crop must be four positive integers x,y,w,h")
        if self.min_clip_s > self.max_clip_s:
            raise ValueError("min_clip_s cannot exceed max_clip_s")
        if self.motion_weight < 0 or self.audio_weight < 0:
            raise ValueError("weights must be non-negative")
        if self.motion_weight == 0 and self.audio_weight == 0:
            raise ValueError("at least one scoring weight must be positive")
        for name, value in (
            ("game_audio_volume", self.game_audio_volume),
            ("music_volume", self.music_volume),
        ):
            if not 0.0 <= value <= 2.0:
                raise ValueError(f"{name} must be between 0 and 2")

    @classmethod
    def load(cls, path: str | Path | None = None) -> Config:
        """Build a config from YAML, falling back to the defaults in this class."""
        if path is None:
            return cls()
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected a mapping at the top level")
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"{path}: unknown keys {unknown}")
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)

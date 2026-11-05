"""Plain data types shared by every stage of the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VideoInfo:
    """Everything the rest of the pipeline needs to know about an input file."""

    path: str
    duration_s: float
    width: int
    height: int
    fps: float
    has_audio: bool

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "duration_s": round(self.duration_s, 3),
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 3),
            "has_audio": self.has_audio,
        }


@dataclass
class Segment:
    """A half-open time range `[start, end)` in seconds."""

    start: float
    end: float
    score: float = 0.0

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def overlaps(self, other: Segment, gap: float = 0.0) -> bool:
        """True when the two ranges touch or are closer than `gap` seconds."""
        return not (self.end + gap <= other.start or self.start >= other.end + gap)

    def to_dict(self) -> dict:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
            "score": round(self.score, 4),
        }


@dataclass
class BeatGrid:
    """Beat and downbeat positions (seconds) of the music track."""

    tempo: float = 0.0
    beats: list[float] = field(default_factory=list)
    downbeats: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tempo_bpm": round(self.tempo, 2),
            "n_beats": len(self.beats),
            "n_downbeats": len(self.downbeats),
            "first_downbeat_s": round(self.downbeats[0], 3) if self.downbeats else None,
        }

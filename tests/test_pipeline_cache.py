from unittest.mock import Mock

import numpy as np

from beatcut.config import Config
from beatcut.pipeline import analyze
from beatcut.types import BeatGrid, VideoInfo


def test_changing_music_reuses_gameplay_and_empty_kill_results(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    songs = [tmp_path / "one.wav", tmp_path / "two.wav"]
    for path in [video, *songs]:
        path.write_bytes(b"fixture")
    times = np.arange(0, 40, 0.25)
    motion = Mock(return_value=(times, np.ones_like(times)))
    audio = Mock(return_value=(times, np.ones_like(times)))
    beats = Mock(return_value=BeatGrid(120, list(range(40)), list(range(0, 40, 2))))
    kills = Mock(return_value=[])
    monkeypatch.setattr("beatcut.pipeline.probe", lambda path: VideoInfo(
        str(path), 40, 1280, 720, 30, True,
    ))
    monkeypatch.setattr("beatcut.pipeline.motion_energy_curve", motion)
    monkeypatch.setattr("beatcut.pipeline.audio_energy_curve", audio)
    monkeypatch.setattr("beatcut.pipeline.detect_beats", beats)
    monkeypatch.setattr("beatcut.pipeline.extract_audio", lambda source, out, sr: out)
    monkeypatch.setattr("beatcut.scoreboard.extract_kills", kills)
    cfg = Config(cache_dir=str(tmp_path / "cache"), skip_frame_drops=False,
                 kill_crop=[1, 1, 10, 10], target_duration_s=12)
    messages = []
    first = analyze(video, songs[0], cfg, tmp_path / "work", progress=messages.append)
    assert "Analyzing gameplay motion…" in messages
    messages.clear()
    second = analyze(video, songs[1], cfg, tmp_path / "work", progress=messages.append)
    assert "Reusing saved gameplay analysis." in messages
    assert "Reusing saved kill detections." in messages
    assert "Analyzing the music beat…" in messages
    assert first.segments == second.segments
    assert motion.call_count == audio.call_count == kills.call_count == 1
    assert beats.call_count == 2
    analyze(video, songs[0], cfg, tmp_path / "work")
    assert beats.call_count == 2
    cfg.use_cache = False
    analyze(video, songs[0], cfg, tmp_path / "work")
    assert motion.call_count == audio.call_count == kills.call_count == 2
    assert beats.call_count == 3

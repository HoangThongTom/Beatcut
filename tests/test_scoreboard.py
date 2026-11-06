"""Tests for turning noisy OCR readings into kill events. No OCR, no video."""

from __future__ import annotations

from beatcut.scoreboard import detect_events, parse_counter, smooth


def test_parse_counter_ignores_icon_letters():
    assert parse_counter(["X", "4", "中"]) == 4


def test_parse_counter_prefers_the_longest_number():
    assert parse_counter(["1", "10"]) == 10


def test_parse_counter_returns_none_when_nothing_parses():
    assert parse_counter(["X", "D", "中"]) is None


def test_detect_events_records_each_increase():
    samples = [(0.0, 0), (0.5, 0), (1.0, 1), (1.5, 1), (2.0, 2)]

    events = detect_events(samples)

    assert [event.count for event in events] == [1, 2]
    assert [event.time for event in events] == [1.0, 2.0]


def test_detect_events_ignores_backwards_readings():
    events = detect_events([(0.0, 5), (1.0, 3), (2.0, 6)])

    assert [event.count for event in events] == [6]


def test_detect_events_ignores_impossible_bursts():
    # A jump from 0 to 40 in half a second is a misread, not forty kills.
    events = detect_events([(0.0, 0), (1.0, 40), (2.0, 41)])

    assert events == []


def test_detect_events_rebaselines_when_a_value_persists():
    # If the HUD really did jump (a long OCR gap), five identical readings
    # establish a new baseline instead of blocking detection forever.
    samples = [(0.0, 0)] + [(float(i), 40) for i in range(1, 8)]

    events = detect_events(samples)

    assert events == []


def test_detect_events_skips_frames_where_ocr_failed():
    events = detect_events([(0.0, None), (1.0, 2), (2.0, None), (3.0, 3)])

    assert [event.count for event in events] == [3]

def test_parse_counter_strips_trailing_punctuation():
    # The recogniser appends a period to single digits.
    assert parse_counter(["4."]) == 4

def test_smooth_removes_a_single_bad_reading():
    samples = [(0.0, 4), (0.5, 4), (1.0, 43), (1.5, 4), (2.0, 4)]

    smoothed = smooth(samples, window=5)

    assert all(value == 4 for _, value in smoothed)


def test_smooth_keeps_a_real_step():
    samples = [(i * 0.5, 4 if i < 6 else 5) for i in range(12)]

    smoothed = smooth(samples, window=5)

    assert smoothed[0][1] == 4
    assert smoothed[-1][1] == 5

def test_detect_events_does_not_adopt_a_misread_as_baseline():
    # A spike to 43 used to become the new baseline, losing every later kill.
    samples = [(0.0, 0), (0.5, 1), (1.0, 43), (1.5, 2), (2.0, 3)]

    events = detect_events(samples)

    assert [event.count for event in events] == [1, 2, 3]

"""Sample-index <-> time conversion — FR-053, SR-014, PRD §4.4, T-053."""
from datetime import datetime, timezone, timedelta

import pytest

from seismonet.time_utils import (
    absolute_time,
    sample_to_seconds,
    seconds_to_sample,
    window_length_seconds,
)


def test_sample_to_seconds_basic():
    assert sample_to_seconds(100, 100.0) == pytest.approx(1.0)
    assert sample_to_seconds(0, 100.0) == pytest.approx(0.0)
    assert sample_to_seconds(50, 100.0) == pytest.approx(0.5)
    assert sample_to_seconds(3000, 100.0) == pytest.approx(30.0)


def test_seconds_to_sample_roundtrip():
    for sr in (50.0, 100.0, 200.0):
        for idx in (0, 1, 10, 3071):
            secs = sample_to_seconds(idx, sr)
            assert seconds_to_sample(secs, sr) == idx


def test_absolute_time():
    start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    # 150 samples at 100 Hz = 1.5 s
    t = absolute_time(start, 150, 100.0)
    assert t == start + timedelta(seconds=1.5)
    # index 0 is the start itself
    assert absolute_time(start, 0, 100.0) == start


def test_window_length_seconds():
    assert window_length_seconds(3072, 100.0) == pytest.approx(30.72)
    assert window_length_seconds(128, 100.0) == pytest.approx(1.28)


def test_invalid_rate_raises():
    with pytest.raises(ValueError):
        sample_to_seconds(10, 0)
    with pytest.raises(ValueError):
        seconds_to_sample(1.0, -100.0)
    with pytest.raises(ValueError):
        window_length_seconds(128, 0)


def test_negative_index_raises():
    with pytest.raises(ValueError):
        sample_to_seconds(-1, 100.0)
    with pytest.raises(ValueError):
        absolute_time(datetime.now(timezone.utc), -1, 100.0)

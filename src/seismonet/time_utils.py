"""Sample-index <-> time conversion — PRD FR-053, SR-014, §4.4.

Every waveform carries an implicit time origin:
  seconds_in_window = sample_index / sampling_rate
  absolute_time     = trace_start_time + seconds_in_window

No phase-picking semantic is involved here; this is pure arithmetic
so it can be tested without a model or dataset.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def sample_to_seconds(sample_index: int, sampling_rate: float) -> float:
    if sampling_rate <= 0:
        raise ValueError(f"sampling_rate must be >0, got {sampling_rate}")
    if sample_index < 0:
        raise ValueError(f"sample_index must be >=0, got {sample_index}")
    return float(sample_index) / float(sampling_rate)


def seconds_to_sample(seconds: float, sampling_rate: float) -> int:
    if sampling_rate <= 0:
        raise ValueError(f"sampling_rate must be >0, got {sampling_rate}")
    if seconds < 0:
        raise ValueError(f"seconds must be >=0, got {seconds}")
    # Round to nearest sample; exact invertibility holds for integer seconds*rate.
    return int(round(float(seconds) * float(sampling_rate)))


def absolute_time(
    trace_start: datetime,
    sample_index: int,
    sampling_rate: float,
) -> datetime:
    secs = sample_to_seconds(sample_index, sampling_rate)
    return trace_start + timedelta(seconds=secs)


def window_length_seconds(window_length: int, sampling_rate: float) -> float:
    if window_length <= 0:
        raise ValueError(f"window_length must be >0, got {window_length}")
    if sampling_rate <= 0:
        raise ValueError(f"sampling_rate must be >0, got {sampling_rate}")
    return float(window_length) / float(sampling_rate)

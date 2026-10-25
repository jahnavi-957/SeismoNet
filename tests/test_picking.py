"""Focused validation-time peak picking and window-offset tests."""

import numpy as np
import pytest

from seismonet.picking import (
    PeakPickingConfig,
    absolute_timing_error_samples,
    pick_phase_diagnostics,
    pick_phase,
    pick_phases,
    samples_to_milliseconds,
    window_relative_to_trace_sample,
)


def test_pick_phase_selects_strongest_peak_above_threshold():
    curve = np.zeros(32, dtype=float)
    curve[8] = 0.72
    curve[22] = 0.91
    pick = pick_phase(curve, threshold=0.5, min_peak_distance_samples=5)
    assert pick is not None
    assert pick.index == 22
    assert pick.probability == pytest.approx(0.91)


def test_pick_phase_returns_none_for_absent_or_below_threshold_peak():
    assert pick_phase(np.zeros(32), threshold=0.5) is None
    curve = np.zeros(32, dtype=float)
    curve[16] = 0.49
    assert pick_phase(curve, threshold=0.5) is None


def test_pick_phase_rejects_edge_only_activation_and_invalid_inputs():
    edge = np.zeros(8, dtype=float)
    edge[0] = 0.99
    assert pick_phase(edge, threshold=0.5) is None
    diagnostics = pick_phase_diagnostics(edge, threshold=0.5)
    assert diagnostics.pick is None
    assert diagnostics.edge_activation is True
    assert diagnostics.no_candidate_reason == "edge_only"
    with pytest.raises(ValueError, match="1-D"):
        pick_phase(np.zeros((3, 8)), threshold=0.5)
    with pytest.raises(ValueError, match="non-finite"):
        pick_phase(np.array([0.0, np.nan, 0.0]), threshold=0.5)
    with pytest.raises(ValueError, match="threshold"):
        pick_phase(np.zeros(8), threshold=1.1)
    with pytest.raises(ValueError, match="min_peak_distance"):
        pick_phase(np.zeros(8), threshold=0.5, min_peak_distance_samples=0)


def test_pick_phases_has_p_and_s_channels_and_missing_s_is_none():
    probabilities = np.zeros((3, 32), dtype=float)
    probabilities[0, 7] = 0.8
    probabilities[1, 18] = 0.4  # Below the configured S threshold.
    picks = pick_phases(
        probabilities,
        PeakPickingConfig(p_threshold=0.5, s_threshold=0.5),
    )
    assert picks["P"] is not None and picks["P"].index == 7
    assert picks["S"] is None


def test_pick_phase_diagnostics_reports_multiple_candidates_and_suppression():
    curve = np.zeros(32, dtype=float)
    curve[8] = 0.72
    curve[12] = 0.91
    diagnostics = pick_phase_diagnostics(curve, threshold=0.5, min_peak_distance_samples=5)
    assert diagnostics.candidate_count == 2
    assert diagnostics.retained_candidate_count == 1
    assert diagnostics.pick is not None and diagnostics.pick.index == 12


def test_window_offset_and_timing_conversions():
    assert window_relative_to_trace_sample(1200, 3071, window_length=3072) == 4271
    assert window_relative_to_trace_sample(1200, None, window_length=3072) is None
    assert absolute_timing_error_samples(4271, 4261) == 10
    assert absolute_timing_error_samples(None, 4261) is None
    assert samples_to_milliseconds(10, 100.0) == pytest.approx(100.0)


def test_window_offset_rejects_invalid_or_out_of_window_indices():
    with pytest.raises(ValueError, match="window_start"):
        window_relative_to_trace_sample(-1, 0, window_length=32)
    with pytest.raises(ValueError, match="relative_index"):
        window_relative_to_trace_sample(0, 32, window_length=32)
    with pytest.raises(ValueError, match="window_length"):
        window_relative_to_trace_sample(0, 0, window_length=0)
    with pytest.raises(ValueError, match="sampling_rate"):
        samples_to_milliseconds(1, 0)

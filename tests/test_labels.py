"""P/S target generation — FR-021..FR-024, SR-006, T-010..T-016.

Tiny synthetic fixtures; no seismic data.
"""
import numpy as np
import pytest

from seismonet.labels import make_targets


def test_shape_is_3_by_L(window_length):
    t = make_targets(window_length, p_idx=10, s_idx=60, sigma=5.0)
    assert t.shape == (3, window_length)
    assert t.dtype == np.float64


def test_values_in_unit_interval(window_length):
    t = make_targets(window_length, p_idx=20, s_idx=80, sigma=8.0)
    assert np.all(t >= 0.0) and np.all(t <= 1.0)


def test_p_peak_at_pick(window_length):
    p_idx = 25
    t = make_targets(window_length, p_idx=p_idx, s_idx=None, sigma=4.0)
    assert int(np.argmax(t[0])) == p_idx
    assert t[0, p_idx] == pytest.approx(1.0)


def test_s_peak_at_pick(window_length):
    s_idx = 90
    t = make_targets(window_length, p_idx=None, s_idx=s_idx, sigma=4.0)
    assert int(np.argmax(t[1])) == s_idx
    assert t[1, s_idx] == pytest.approx(1.0)


def test_absent_phase_all_zeros(window_length):
    t_p_only = make_targets(window_length, p_idx=20, s_idx=None, sigma=5.0)
    assert np.all(t_p_only[1] == 0.0)
    t_s_only = make_targets(window_length, p_idx=None, s_idx=80, sigma=5.0)
    assert np.all(t_s_only[0] == 0.0)
    t_noise = make_targets(window_length, p_idx=None, s_idx=None, sigma=5.0)
    assert np.all(t_noise[0] == 0.0) and np.all(t_noise[1] == 0.0)
    assert np.all(t_noise[2] == 1.0)


def test_noise_is_remainder_and_sum_is_one(window_length):
    t = make_targets(window_length, p_idx=30, s_idx=80, sigma=6.0)
    # Per-sample P+S+noise == 1 (FR-023)
    assert np.allclose(t[0] + t[1] + t[2], 1.0)
    # Noise == clip(1 - P - S)
    expected_noise = np.clip(1.0 - t[0] - t[1], 0.0, 1.0)
    assert np.allclose(t[2], expected_noise)


def test_overlapping_p_and_s_still_valid(window_length):
    # Near-source: P and S close (E4) — noise must stay non-negative.
    # When P+S > 1 at the overlap, noise is clipped to 0, so P+S+noise < 2
    # and is not exactly 1. The invariant is: noise == clip(1-P-S, 0, 1).
    p_idx, s_idx = 40, 48
    t = make_targets(window_length, p_idx=p_idx, s_idx=s_idx, sigma=8.0)
    assert np.all(t[2] >= 0.0)
    expected_noise = np.clip(1.0 - t[0] - t[1], 0.0, 1.0)
    assert np.allclose(t[2], expected_noise)


def test_sigma_changes_width(window_length):
    t_narrow = make_targets(window_length, p_idx=40, s_idx=None, sigma=3.0)
    t_wide = make_targets(window_length, p_idx=40, s_idx=None, sigma=12.0)
    # At an offset of e.g. +10 samples, wide should be larger.
    assert t_wide[0, 50] > t_narrow[0, 50]
    # Peaks stay at the pick.
    assert int(np.argmax(t_narrow[0])) == 40
    assert int(np.argmax(t_wide[0])) == 40


def test_pure_noise_has_noise_one(window_length):
    t = make_targets(window_length, p_idx=None, s_idx=None, sigma=5.0)
    assert np.all(t[2] == 1.0)


def test_out_of_bounds_raises(window_length):
    with pytest.raises(ValueError):
        make_targets(window_length, p_idx=window_length, s_idx=None)
    with pytest.raises(ValueError):
        make_targets(window_length, p_idx=None, s_idx=-1)

"""Metrics — FR-055..FR-062, FR-060, NFR-002/NFR-014, SC-2."""
import numpy as np
import pytest

from seismonet.metrics import classify_picks, residuals, residual_stats


def test_residuals_sign_is_pred_minus_ref():
    r = residuals([1.5, 2.0], [1.0, 2.5])
    assert np.allclose(r, [0.5, -0.5])


def test_residuals_empty():
    r = residuals([], [])
    assert r.size == 0


def test_residual_shape_mismatch_raises():
    with pytest.raises(ValueError, match="same shape"):
        residuals([1.0], [1.0, 2.0])


def test_residual_stats_basic():
    s = residual_stats([0.5, -0.5, 1.0, -1.0])
    assert s.n == 4
    assert s.mean == pytest.approx(0.0)
    assert s.mae == pytest.approx(0.75)
    assert s.median == pytest.approx(0.0)


def test_residual_stats_empty():
    s = residual_stats([])
    assert s.n == 0 and s.mean is None and s.mae is None


def test_classify_perfect():
    preds = [1.0, 2.0, None]
    refs = [1.0, 2.0, None]
    m = classify_picks(preds, refs, tolerance=0.01)
    assert (m.tp, m.fp, m.fn) == (2, 0, 0)
    assert m.precision == pytest.approx(1.0) and m.recall == pytest.approx(1.0) and m.f1 == pytest.approx(1.0)


def test_classify_out_of_tolerance_is_both_fp_and_fn():
    # Within the stated convention, an out-of-tolerance pick counts as both FP and FN.
    m = classify_picks([5.0], [5.5], tolerance=0.1)
    assert m.tp == 0 and m.fp == 1 and m.fn == 1


def test_classify_no_pick_vs_missing_ref():
    assert classify_picks([None], [None], tolerance=0.1).tp == 0
    assert classify_picks([1.0], [None], tolerance=0.1).fp == 1
    assert classify_picks([None], [1.0], tolerance=0.1).fn == 1


def test_classify_zero_denom_returns_zero_scores():
    # FR-062: denominator 0 -> defined 0, denominator reported via tp/fp/fn counts.
    m = classify_picks([None, None], [None, None], tolerance=0.1)
    assert m.tp == 0 and m.fp == 0 and m.fn == 0
    assert m.precision == 0.0 and m.recall == 0.0 and m.f1 == 0.0


def test_classify_p_and_s_separately():
    # FR-060: P and S are scored separately; this test documents two independent calls.
    m_p = classify_picks([1.0, 1.1], [1.0, 1.11], tolerance=0.05)
    m_s = classify_picks([2.0, None], [2.5, 2.6], tolerance=0.05)
    assert m_p.tp == 2
    assert m_s.fn == 2  # no correct S within tolerance


def test_tolerance_negative_raises():
    with pytest.raises(ValueError):
        classify_picks([1.0], [1.0], tolerance=-1)

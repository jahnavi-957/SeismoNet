"""Windowing, time-origin preservation and window-length assessment — FR-017/FR-018/FR-019, §4.4.

All waveforms are synthetic; no dataset record is read (NFR-010).
"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from seismonet.metadata import verify_noise_metadata
from seismonet.time_utils import absolute_time
from seismonet.windowing import (
    INSTANCE_ARRIVAL_DISTRIBUTION,
    STRATEGY_CENTER_MIDPOINT,
    STRATEGY_CENTER_P,
    STRATEGY_START,
    check_window_boundary,
    draw_pure_noise_mask,
    evaluate_window_length,
    evaluate_window_lengths,
    extract_window,
    plan_pure_noise,
    prepare_window,
    select_window_start,
    span_coverage,
    tensor_bytes,
)


@pytest.fixture
def waveform(rng):
    # Non-flat synthetic 3-component record long enough for a 128-sample window.
    return rng.normal(size=(3, 256)).astype(np.float64)


# --------------------------------------------------------------------------------------
# Extraction, index relationship and time origin (§4.4)
# --------------------------------------------------------------------------------------


def test_extract_window_shape_and_slice(waveform):
    window = extract_window(waveform, p_sample=100, s_sample=140, start=50, window_length=128)
    assert window.waveform.shape == (3, 128)
    assert window.start == 50
    assert window.length == 128
    assert window.stop == 178
    # The window is the exact slice of the parent record.
    assert np.array_equal(window.waveform, waveform[:, 50:178])


def test_sample_index_relationship_is_preserved(waveform):
    window = extract_window(waveform, p_sample=100, s_sample=140, start=50, window_length=128)
    # absolute -> window -> absolute round-trips exactly.
    assert window.p_index == 50
    assert window.s_index == 90
    assert window.sample_in_window(50) == 0
    assert window.sample_in_window(100) == window.p_index
    assert window.window_to_absolute(window.p_index) == 100
    assert window.window_to_absolute(window.s_index) == 140
    # Boundary semantics: start inclusive, stop exclusive.
    assert window.sample_in_window(178) is None
    assert window.sample_in_window(49) is None


def test_window_to_absolute_rejects_out_of_range(waveform):
    window = extract_window(waveform, None, None, start=0, window_length=128)
    with pytest.raises(ValueError):
        window.window_to_absolute(128)


def test_window_carries_time_origin(waveform):
    trace_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    window = extract_window(
        waveform, p_sample=100, s_sample=140, start=50, window_length=128, sampling_rate=100.0
    )
    expected_start = trace_start + timedelta(seconds=50 / 100.0)
    assert window.start_time(trace_start) == expected_start
    assert window.pick_time(trace_start, "P") == absolute_time(trace_start, 100, 100.0)
    assert window.pick_time(trace_start, "S") == absolute_time(trace_start, 140, 100.0)
    # Consistency: pick absolute time == window start + in-window offset.
    assert window.pick_time(trace_start, "P") == window.start_time(trace_start) + timedelta(
        seconds=window.p_index / 100.0
    )


def test_extract_window_rejects_out_of_range_start(waveform):
    with pytest.raises(ValueError):
        extract_window(waveform, None, None, start=200, window_length=128)
    with pytest.raises(ValueError):
        extract_window(waveform, None, None, start=-1, window_length=128)


def test_extract_window_rejects_flat_waveform():
    flat = np.zeros((3, 256))
    with pytest.raises(ValueError):
        extract_window(flat, None, None, start=0, window_length=128)


# --------------------------------------------------------------------------------------
# Boundary validation
# --------------------------------------------------------------------------------------


def test_boundary_ok_when_both_picks_inside():
    result = check_window_boundary(2000, 2100, start=1900, length=512)
    assert result.ok is True
    assert result.p_in_window and result.s_in_window
    assert result.reason is None


def test_boundary_p_out_of_window_is_a_defect():
    result = check_window_boundary(100, None, start=1900, length=512)
    assert result.ok is False
    assert result.reason == "p_out_of_window"


def test_boundary_missing_p_is_a_defect_when_required():
    assert check_window_boundary(None, None, start=0, length=512, require_p=True).reason == "missing_p"
    assert check_window_boundary(None, None, start=0, length=512, require_p=False).ok is True


def test_boundary_s_outside_is_legitimate_and_warned():
    # S present but outside the window is not a defect: the S target becomes all-zero (FR-024).
    result = check_window_boundary(100, 900, start=0, length=512)
    assert result.ok is True
    assert result.s_in_window is False
    assert any("S=" in warning for warning in result.warnings)


# --------------------------------------------------------------------------------------
# Start selection (FR-018)
# --------------------------------------------------------------------------------------


def test_deterministic_strategies_are_repeatable():
    kwargs = dict(p_sample=2000, s_sample=2500, mode="deterministic")
    mid_first = select_window_start(12000, 3072, strategy=STRATEGY_CENTER_MIDPOINT, **kwargs)
    mid_second = select_window_start(12000, 3072, strategy=STRATEGY_CENTER_MIDPOINT, **kwargs)
    assert mid_first == mid_second
    # Center of the midpoint (2250) in a 3072 window -> start 714.
    assert mid_first == 2250 - 3072 // 2
    # Center on P instead.
    assert select_window_start(12000, 3072, strategy=STRATEGY_CENTER_P, **kwargs) == 2000 - 1536
    # Legacy 0:L window.
    assert select_window_start(12000, 3072, strategy=STRATEGY_START, **kwargs) == 0


def test_deterministic_strategy_does_not_need_rng():
    start = select_window_start(12000, 3072, p_sample=100, s_sample=200, mode="deterministic")
    assert start == 0  # clamped from a negative centre


def test_random_mode_is_reproducible_with_seed():
    first = select_window_start(12000, 3072, p_sample=2041, s_sample=2555, mode="random", seed=0)
    second = select_window_start(12000, 3072, p_sample=2041, s_sample=2555, mode="random", seed=0)
    assert first == second


def test_random_mode_places_p_at_varying_offsets():
    offsets = set()
    for seed in range(64):
        start = select_window_start(12000, 3072, p_sample=2041, s_sample=2555, mode="random", seed=seed)
        offsets.add(2041 - start)
    # FR-018: the pick position must vary rather than sit at one fixed offset.
    assert len(offsets) > 3
    assert max(offsets) - min(offsets) > 100


def test_random_mode_requires_explicit_rng_or_seed():
    with pytest.raises(ValueError):
        select_window_start(12000, 3072, p_sample=2041, mode="random")
    with pytest.raises(ValueError):
        select_window_start(12000, 3072, p_sample=2041, mode="random", rng=np.random.default_rng(0), seed=0)


def test_prepare_window_streams_deterministically(waveform):
    a = prepare_window(waveform, 100, 140, window_length=128)
    b = prepare_window(waveform, 100, 140, window_length=128)
    assert a.start == b.start
    assert np.array_equal(a.waveform, b.waveform)
    assert a.boundary().ok is True


# --------------------------------------------------------------------------------------
# OQ-4 window-length assessment
# --------------------------------------------------------------------------------------


def test_window_length_assessment_matches_evidence():
    assessments = {a.length: a for a in evaluate_window_lengths()}
    assert set(assessments) == {128, 3000, 3072, 4000}
    # 3000 is not divisible by 2**4, so it cannot be a depth-4 production window (FR-036).
    assert assessments[3000].depth_compatible is False
    assert assessments[3000].decision == "reject-for-depth"
    # 128 is only a fast-test window.
    assert assessments[128].decision == "test-only"
    assert assessments[128].span_coverage == pytest.approx(0.0231)
    # 3072 and 4000 are plausible production lengths, provisionally.
    assert assessments[3072].depth_compatible is True
    assert assessments[3072].decision == "provisional-production"
    assert assessments[3072].span_coverage == pytest.approx(0.9977)
    assert assessments[4000].decision == "provisional-production"
    # No length guarantees both picks, and offset-0 misses P (p_max 6701 > 4000).
    assert all(not a.guarantees_p_and_s_in_one_window for a in assessments.values())
    assert all(not a.contains_all_p_from_offset_zero for a in assessments.values())


def test_window_length_decisions_stay_provisional_until_vram_measured():
    default = evaluate_window_length(3072)
    assert default.provisional is True
    assert default.vram_status == "not_measured"
    measured = evaluate_window_length(3072, vram_measured=True)
    assert measured.provisional is False
    assert measured.vram_status == "measured"


def test_arrival_distribution_bounds():
    arrival = INSTANCE_ARRIVAL_DISTRIBUTION
    assert arrival.max_span_upper_bound == arrival.s_max - arrival.p_min + 1
    assert arrival.mean_span == pytest.approx(arrival.s_mean - arrival.p_mean)


def test_span_coverage_and_tensor_bytes():
    assert span_coverage([100, 200, 3000], 512) == pytest.approx(2 / 3)
    assert tensor_bytes(3072, 8) == 8 * 3 * 3072 * 4
    with pytest.raises(ValueError):
        tensor_bytes(0, 8)


# --------------------------------------------------------------------------------------
# FR-019 — pure-noise windows gated on verification
# --------------------------------------------------------------------------------------


def test_pure_noise_mask_fraction_and_determinism():
    mask_a = draw_pure_noise_mask(1000, 0.2, seed=0)
    mask_b = draw_pure_noise_mask(1000, 0.2, seed=0)
    assert mask_a.dtype == bool
    assert np.array_equal(mask_a, mask_b)
    # "Config fraction is respected within sampling error."
    assert 0.15 < mask_a.mean() < 0.25
    assert draw_pure_noise_mask(10, 0.0, seed=0).sum() == 0
    assert draw_pure_noise_mask(10, 1.0, seed=0).all()


def test_plan_pure_noise_is_inert_without_verification(tmp_path):
    import csv

    path = tmp_path / "noise.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["source_id", "trace_dt_s", "trace_npts", "trace_name"]
        )
        writer.writeheader()
        writer.writerow(
            {"source_id": "x", "trace_dt_s": "0.01", "trace_npts": "12000", "trace_name": "a"}
        )
    verification = verify_noise_metadata(path)

    assert plan_pure_noise(0.1, verification).active is True
    assert plan_pure_noise(0.1, None).active is False
    assert plan_pure_noise(0.0, verification).active is False
    assert plan_pure_noise(0.1, verification, requested=False).active is False


def test_plan_pure_noise_rejects_failed_verification(tmp_path):
    import csv

    path = tmp_path / "noise_with_phases.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_id", "trace_dt_s", "trace_npts", "trace_name", "trace_P_arrival_sample"],
        )
        writer.writeheader()
        writer.writerow(
            {"source_id": "x", "trace_dt_s": "0.01", "trace_npts": "12000", "trace_name": "a",
             "trace_P_arrival_sample": "100"}
        )
    verification = verify_noise_metadata(path)
    plan = plan_pure_noise(0.1, verification)
    assert verification.ok is False
    assert plan.active is False
    assert "verification failed" in plan.reason

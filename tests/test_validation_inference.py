"""Protocol and metric helpers for validation-only inference."""

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from seismonet.picking import PeakPickingConfig  # noqa: E402
from seismonet.validation_inference import (  # noqa: E402
    _cross_phase_proximity,
    _failure_counts,
    _failure_hypothesis,
    _gallery_case,
    _phase_metrics,
    _plot_example,
    _plot_gallery,
    _plot_residual_histograms,
    _select_gallery_cases,
    _signed_residual_samples,
    _sweep_validation_thresholds,
    _write_frozen_protocol,
)


def _record(
    *,
    phase: str = "P",
    reference: int | None = 100,
    reference_status: str = "in_window",
    predicted: int | None = 100,
    candidate_count: int = 1,
    edge_activation: bool = False,
    p_after_s: bool = False,
) -> dict:
    references = {"P": None, "S": None}
    statuses = {"P": "missing", "S": "missing"}
    predictions = {"P": None, "S": None}
    timing = {"P": None, "S": None}
    references[phase] = reference
    statuses[phase] = reference_status
    predictions[phase] = predicted
    if reference_status == "in_window" and reference is not None and predicted is not None:
        timing[phase] = abs(predicted - reference)
    return {
        "reference_absolute": references,
        "reference_status": statuses,
        "predicted_absolute": predictions,
        "timing_error_samples": timing,
        "pick_diagnostics": {
            "P": {
                "candidate_count": candidate_count if phase == "P" else 0,
                "retained_candidate_count": candidate_count if phase == "P" else 0,
                "edge_activation": edge_activation if phase == "P" else False,
            },
            "S": {
                "candidate_count": candidate_count if phase == "S" else 0,
                "retained_candidate_count": candidate_count if phase == "S" else 0,
                "edge_activation": edge_activation if phase == "S" else False,
            },
        },
        "p_after_s": p_after_s,
    }


def test_phase_metrics_uses_one_to_one_out_of_tolerance_convention():
    metric = _phase_metrics(
        [_record(reference=100, predicted=105)],
        "P",
        tolerance_samples=2,
        sampling_rate=100.0,
    )
    assert metric["detection"]["tp"] == 0
    assert metric["detection"]["fp"] == 1
    assert metric["detection"]["fn"] == 1
    assert metric["residual_seconds"]["mean"] == pytest.approx(0.05)
    assert metric["residual_seconds"]["mae"] == pytest.approx(0.05)


def test_phase_metrics_keeps_missing_reference_as_false_positive():
    metric = _phase_metrics(
        [_record(reference=None, reference_status="missing", predicted=105)],
        "P",
        tolerance_samples=2,
        sampling_rate=100.0,
    )
    assert metric["detection"]["fp"] == 1
    assert metric["detection"]["fn"] == 0
    assert metric["accepted_prediction_on_missing_reference"] == 1


def test_phase_metrics_excludes_out_of_window_reference_and_reports_it():
    metric = _phase_metrics(
        [_record(reference=100, reference_status="out_of_window", predicted=105)],
        "P",
        tolerance_samples=2,
        sampling_rate=50.0,
    )
    assert metric["n_detection_eligible_traces"] == 0
    assert metric["detection"]["n_pred"] == 0
    assert metric["n_reference_out_of_window"] == 1
    assert metric["accepted_prediction_on_out_of_window_reference"] == 1


def test_phase_metrics_uses_sampling_rate_for_tolerance_and_timing_units():
    metric = _phase_metrics(
        [_record(reference=100, predicted=102)],
        "P",
        tolerance_samples=1,
        sampling_rate=50.0,
    )
    assert metric["matching_tolerance_milliseconds"] == pytest.approx(20.0)
    assert metric["absolute_timing_error_milliseconds"]["mean"] == pytest.approx(40.0)
    assert metric["residual_milliseconds"]["mean"] == pytest.approx(40.0)


def test_threshold_sweep_records_candidates_and_selects_highest_f1():
    probabilities = np.zeros((3, 12), dtype=float)
    probabilities[0, 5] = 0.8
    probabilities[1, 7] = 0.7
    inputs = [
        {
            "metadata": {
                "trace_name": "trace-1",
                "source_id": "event-1",
                "trace_P_arrival_sample": "5",
                "trace_S_arrival_sample": "7",
            },
            "window_start": 0,
            "probabilities": probabilities,
        }
    ]
    sweep = _sweep_validation_thresholds(
        inputs,
        candidate_thresholds=(0.2, 0.9),
        min_peak_distance_samples=2,
        matching_tolerance_samples=1,
        sampling_rate=100.0,
        window_length=12,
    )
    assert sweep["phases"]["P"]["selected_threshold"] == pytest.approx(0.2)
    assert len(sweep["phases"]["P"]["candidates"]) == 2
    assert sweep["phases"]["P"]["candidates"][0]["f1"] == pytest.approx(1.0)
    assert sweep["phases"]["S"]["selected_threshold"] == pytest.approx(0.2)


def test_frozen_protocol_cannot_be_overwritten(tmp_path):
    path = tmp_path / "protocol.json"
    config = PeakPickingConfig(
        p_threshold=0.5,
        s_threshold=0.1,
        min_peak_distance_samples=20,
        matching_tolerance_samples=20,
    )
    tuning = {
        "scope": "validation_only",
        "objective": "highest validation F1",
        "tie_break": ["highest precision", "highest recall", "highest threshold"],
    }
    protocol = _write_frozen_protocol(
        path,
        picking_config=config,
        sampling_rate=100.0,
        threshold_tuning=tuning,
    )
    assert protocol["protocol_id"].startswith("protocol-")
    with pytest.raises(FileExistsError, match="already exists"):
        _write_frozen_protocol(
            path,
            picking_config=config,
            sampling_rate=100.0,
            threshold_tuning=tuning,
        )


def _plot_record(
    *,
    trace_name: str = "trace-1",
    phase: str = "P",
    reference: int | None = 100,
    reference_status: str = "in_window",
    predicted: int | None = 102,
    window_length: int = 16,
) -> dict:
    references = {"P": None, "S": None}
    statuses = {"P": "missing", "S": "missing"}
    predictions = {"P": None, "S": None}
    references[phase] = reference
    statuses[phase] = reference_status
    predictions[phase] = predicted
    probabilities = np.full((3, window_length), 0.05, dtype=float)
    probabilities[0, 4] = 0.8
    probabilities[1, 6] = 0.7
    probabilities[2, :] = 1.0 - probabilities[0] - probabilities[1]
    return {
        "trace_name": trace_name,
        "event_id": "event-1",
        "window_start": 24,
        "window_length": window_length,
        "reference_absolute": references,
        "reference_status": statuses,
        "predicted_absolute": predictions,
        "timing_error_samples": {"P": None, "S": None},
        "pick_diagnostics": {
            "P": {"candidate_count": 1, "retained_candidate_count": 1, "edge_activation": False},
            "S": {"candidate_count": 1, "retained_candidate_count": 1, "edge_activation": False},
        },
        "p_after_s": False,
        "probabilities": probabilities,
    }


def test_signed_residuals_use_only_in_window_references_with_predictions():
    records = [
        _plot_record(reference=100, predicted=110),
        _plot_record(trace_name="b", reference=50, reference_status="missing", predicted=60),
        _plot_record(trace_name="c", reference=70, reference_status="out_of_window", predicted=80),
        _plot_record(trace_name="d", reference=90, predicted=None),
    ]
    residuals = _signed_residual_samples(records, "P")
    assert residuals.tolist() == [10.0]


def test_gallery_case_classifies_each_failure_category():
    tolerance = 5
    success = _gallery_case(
        _plot_record(reference=100, predicted=105), "P", tolerance_samples=tolerance
    )
    assert success["kind"] == "success"
    assert success["signed_error_samples"] == 5

    out_of_tolerance = _gallery_case(
        _plot_record(reference=100, predicted=130), "P", tolerance_samples=tolerance
    )
    assert out_of_tolerance["kind"] == "out_of_tolerance"
    assert out_of_tolerance["signed_error_samples"] == 30

    missed = _gallery_case(
        _plot_record(reference=100, predicted=None), "P", tolerance_samples=tolerance
    )
    assert missed["kind"] == "missed_detection"
    assert missed["signed_error_samples"] is None

    on_missing = _gallery_case(
        _plot_record(reference=None, reference_status="missing", predicted=40),
        "P",
        tolerance_samples=tolerance,
    )
    assert on_missing["kind"] == "false_positive_missing_reference"

    excluded = _gallery_case(
        _plot_record(reference=70, reference_status="out_of_window", predicted=80),
        "P",
        tolerance_samples=tolerance,
    )
    assert excluded is None

    nothing = _gallery_case(
        _plot_record(reference=None, reference_status="missing", predicted=None),
        "P",
        tolerance_samples=tolerance,
    )
    assert nothing is None


def test_select_gallery_cases_is_deterministic_and_covers_each_failure_kind():
    records = [
        _plot_record(trace_name="t1", reference=100, predicted=101),
        _plot_record(trace_name="t2", reference=100, predicted=103),
        _plot_record(trace_name="t3", reference=100, predicted=140),
        _plot_record(trace_name="t4", reference=100, predicted=None),
        _plot_record(trace_name="t5", reference=None, reference_status="missing", predicted=40),
    ]
    successes = _select_gallery_cases(
        records, tolerance_samples=5, kind="success", max_per_phase=2
    )
    assert [case["trace_name"] for case in successes] == ["t1", "t2"]

    failures = _select_gallery_cases(
        records, tolerance_samples=5, kind="failure", max_per_phase=3
    )
    assert [case["kind"] for case in failures] == [
        "out_of_tolerance",
        "missed_detection",
        "false_positive_missing_reference",
    ]
    assert failures == _select_gallery_cases(
        records, tolerance_samples=5, kind="failure", max_per_phase=3
    )

    with pytest.raises(ValueError, match="kind"):
        _select_gallery_cases(records, tolerance_samples=5, kind="other", max_per_phase=1)


def test_failure_hypothesis_is_flagged_or_marked_unexplained():
    near_other = _plot_record(reference=100, predicted=None)
    near_other["predicted_absolute"]["P"] = 195
    near_other["reference_absolute"]["S"] = 200
    near_other["reference_status"]["S"] = "in_window"
    hypothesis = _failure_hypothesis(
        near_other, "P", tolerance_samples=20, sampling_rate=100.0
    )
    assert hypothesis.startswith("HYPOTHESIS:")
    assert "hypothesis" in hypothesis
    assert "not confirmed" in hypothesis

    missing = _plot_record(reference=None, reference_status="missing", predicted=40)
    assert _failure_hypothesis(missing, "P", tolerance_samples=20, sampling_rate=100.0).startswith(
        "unexplained"
    )

    no_pick = _plot_record(reference=100, predicted=None)
    assert _failure_hypothesis(no_pick, "P", tolerance_samples=20, sampling_rate=100.0).startswith(
        "unexplained"
    )


def test_failure_counts_match_gallery_classification():
    records = [
        _plot_record(trace_name="t1", reference=100, predicted=101),
        _plot_record(trace_name="t2", reference=100, predicted=140),
        _plot_record(trace_name="t3", reference=100, predicted=None),
    ]
    counts = _failure_counts(records, tolerance_samples=5)
    assert counts["P"] == {
        "success": 1,
        "out_of_tolerance": 1,
        "missed_detection": 1,
    }
    assert counts["S"] == {}


def test_cross_phase_proximity_counts_out_of_tolerance_near_other_reference():
    near = _plot_record(trace_name="n1", reference=100, predicted=None)
    near["predicted_absolute"]["P"] = 195
    near["reference_absolute"]["S"] = 200
    near["reference_status"]["S"] = "in_window"
    far = _plot_record(trace_name="f1", reference=100, predicted=140)
    proximity = _cross_phase_proximity([near, far], tolerance_samples=20)
    assert proximity["P"] == {
        "out_of_tolerance": 2,
        "within_tolerance_of_other_reference": 1,
    }
    assert proximity["S"] == {"out_of_tolerance": 0, "within_tolerance_of_other_reference": 0}


def test_example_figure_draws_applied_thresholds(tmp_path):
    record = _plot_record(reference=100, predicted=104)
    waveform = np.zeros((3, record["window_length"]), dtype=float)
    figure = _plot_example(
        record,
        waveform,
        example_label="both_p_and_s",
        p_threshold=0.05,
        s_threshold=0.10,
    )
    try:
        probability_axis = figure.axes[3]
        y_values = [np.asarray(line.get_ydata()) for line in probability_axis.lines]
        assert any(np.allclose(values, 0.05) for values in y_values)
        assert any(np.allclose(values, 0.10) for values in y_values)
        path = tmp_path / "example.png"
        figure.savefig(path)
        assert path.stat().st_size > 0
    finally:
        plt.close(figure)


def test_residual_histogram_and_galleries_write_figures(tmp_path):
    records = [
        _plot_record(trace_name="t1", reference=100, predicted=101),
        _plot_record(trace_name="t2", reference=100, predicted=140),
    ]
    residuals_path = tmp_path / "residuals.png"
    _plot_residual_histograms(
        records, residuals_path, tolerance_samples=20, sampling_rate=100.0
    )
    assert residuals_path.stat().st_size > 0

    cases = _select_gallery_cases(
        records, tolerance_samples=20, kind="failure", max_per_phase=2
    )
    waveforms = {name: np.zeros((3, 16), dtype=float) for name in ("t1", "t2")}
    gallery_path = tmp_path / "gallery_failure.png"
    _plot_gallery(
        cases,
        gallery_path,
        waveforms_by_trace=waveforms,
        p_threshold=0.05,
        s_threshold=0.10,
        tolerance_samples=20,
        sampling_rate=100.0,
        show_hypothesis=True,
    )
    assert gallery_path.stat().st_size > 0

    with pytest.raises(ValueError, match="empty gallery"):
        _plot_gallery(
            [],
            tmp_path / "empty.png",
            waveforms_by_trace={},
            p_threshold=0.05,
            s_threshold=0.10,
            tolerance_samples=20,
            sampling_rate=100.0,
            show_hypothesis=False,
        )

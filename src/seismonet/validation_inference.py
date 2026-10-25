"""Validation-only inference, peak picking, metrics, and figures for the pilot checkpoint.

This is intentionally a small reporting entry point rather than a dashboard or a training
framework.  It consumes the saved pilot manifest and configuration, reads only the selected
validation traces, and writes a new ignored run directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import torch
import yaml

from seismonet.dataset import InstanceDataset, build_dataloader
from seismonet.model import SeismoUnet1d
from seismonet.metrics import classify_picks, residual_stats, residuals
from seismonet.picking import (
    PeakPickingConfig,
    absolute_timing_error_samples,
    pick_phase_diagnostics,
    samples_to_milliseconds,
    window_relative_to_trace_sample,
)


VALIDATION_THRESHOLD_CANDIDATES = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)
DEFAULT_MIN_PEAK_DISTANCE_SAMPLES = 20
DEFAULT_MATCHING_TOLERANCE_SAMPLES = 20


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("runs/pilot_seed42/run.json"),
        help="completed pilot manifest",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("runs/pilot_seed42/config_snapshot.yaml"),
        help="saved pilot configuration snapshot",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("runs/pilot_seed42/best.pt"),
        help="weights-only pilot checkpoint",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("runs/validation_inference_seed42"),
        help="new ignored output directory; never the pilot output directory",
    )
    parser.add_argument(
        "--p-threshold",
        type=float,
        default=None,
        help="optional fixed P threshold override; omit to select from validation candidates",
    )
    parser.add_argument(
        "--s-threshold",
        type=float,
        default=None,
        help="optional fixed S threshold override; omit to select from validation candidates",
    )
    parser.add_argument(
        "--min-peak-distance-samples",
        type=int,
        default=DEFAULT_MIN_PEAK_DISTANCE_SAMPLES,
    )
    parser.add_argument(
        "--matching-tolerance-samples",
        type=int,
        default=DEFAULT_MATCHING_TOLERANCE_SAMPLES,
    )
    return parser.parse_args()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _as_optional_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    return int(float(value))


def _reference_status(
    reference_sample: int | None,
    *,
    window_start: int,
    window_length: int,
) -> tuple[int | None, str]:
    if reference_sample is None:
        return None, "missing"
    relative = reference_sample - window_start
    if 0 <= relative < window_length:
        return relative, "in_window"
    return None, "out_of_window"


def _load_saved_state(
    checkpoint: Path,
    *,
    base: int,
    depth: int,
    device: torch.device,
) -> torch.nn.Module:
    """Load weights-only checkpoint and put the existing model in inference mode."""

    state = torch.load(checkpoint, map_location=device, weights_only=True)
    if not isinstance(state, dict) or not state:
        raise RuntimeError(f"checkpoint did not contain a non-empty state dict: {checkpoint}")
    model = SeismoUnet1d(base=base, depth=depth).to(device)
    model.load_state_dict(state)
    model.eval()
    return model


def _records_for_picking_config(
    prediction_inputs: list[dict[str, Any]],
    picking_config: PeakPickingConfig,
    *,
    window_length: int,
    sampling_rate: float,
) -> list[dict[str, Any]]:
    """Re-pick already-computed probability curves without another model forward pass."""

    return [
        _record_from_prediction(
            metadata=item["metadata"],
            window_start=int(item["window_start"]),
            probabilities=item["probabilities"],
            picking_config=picking_config,
            window_length=window_length,
            sampling_rate=sampling_rate,
        )
        for item in prediction_inputs
    ]


def _sweep_validation_thresholds(
    prediction_inputs: list[dict[str, Any]],
    *,
    candidate_thresholds: tuple[float, ...],
    min_peak_distance_samples: int,
    matching_tolerance_samples: int,
    sampling_rate: float,
    window_length: int,
    baseline_p_threshold: float = 0.5,
    baseline_s_threshold: float = 0.5,
) -> dict[str, Any]:
    """Select one threshold per phase using validation-only detection F1.

    Threshold candidates are scored independently by phase.  The deterministic tie-break is highest
    precision, then highest recall, then the highest threshold (the most conservative operating
    point).  The returned table is part of the protocol evidence; no test data is consulted.
    """

    sweep: dict[str, Any] = {
        "scope": "validation_only",
        "candidate_thresholds": [float(value) for value in candidate_thresholds],
        "objective": "highest validation F1",
        "tie_break": ["highest precision", "highest recall", "highest threshold"],
        "phases": {},
    }
    for phase in ("P", "S"):
        results: list[dict[str, Any]] = []
        for threshold in candidate_thresholds:
            config = PeakPickingConfig(
                p_threshold=float(threshold) if phase == "P" else baseline_p_threshold,
                s_threshold=float(threshold) if phase == "S" else baseline_s_threshold,
                min_peak_distance_samples=min_peak_distance_samples,
                matching_tolerance_samples=matching_tolerance_samples,
            )
            records = _records_for_picking_config(
                prediction_inputs,
                config,
                window_length=window_length,
                sampling_rate=sampling_rate,
            )
            metric = _phase_metrics(
                records,
                phase,
                tolerance_samples=matching_tolerance_samples,
                sampling_rate=sampling_rate,
            )
            detection = metric["detection"]
            results.append(
                {
                    "threshold": float(threshold),
                    "precision": float(detection["precision"]),
                    "recall": float(detection["recall"]),
                    "f1": float(detection["f1"]),
                    "n_pred": int(detection["n_pred"]),
                    "n_ref": int(detection["n_ref"]),
                    "tp": int(detection["tp"]),
                    "fp": int(detection["fp"]),
                    "fn": int(detection["fn"]),
                }
            )
        selected = max(
            results,
            key=lambda item: (
                item["f1"],
                item["precision"],
                item["recall"],
                item["threshold"],
            ),
        )
        sweep["phases"][phase] = {
            "selected_threshold": selected["threshold"],
            "candidates": results,
        }
    return sweep


def _write_frozen_protocol(
    path: Path,
    *,
    picking_config: PeakPickingConfig,
    sampling_rate: float,
    threshold_tuning: dict[str, Any],
) -> dict[str, Any]:
    """Write a content-addressed protocol once; never silently replace it."""

    if path.exists():
        raise FileExistsError(
            f"frozen protocol already exists at {path}; choose a new output directory"
        )
    protocol: dict[str, Any] = {
        "schema_version": 1,
        "status": "candidate_validation_protocol",
        "test_evaluation_allowed": False,
        "selection_scope": "validation_only",
        "sampling_rate_hz": float(sampling_rate),
        "picking": {
            "p_threshold": float(picking_config.p_threshold),
            "s_threshold": float(picking_config.s_threshold),
            "min_peak_distance_samples": int(picking_config.min_peak_distance_samples),
            "matching_tolerance_samples": int(picking_config.matching_tolerance_samples),
        },
        "rules": {
            "peak_rule": "strongest retained interior local maximum at or above threshold",
            "edge_policy": "edge-only activations are rejected and counted",
            "multi_peak_rule": (
                "rank candidates by descending probability then ascending sample index; "
                "suppress candidates closer than min_peak_distance_samples; return one strongest pick"
            ),
            "missing_reference": "exclude from reference denominator; an accepted prediction is a false positive",
            "out_of_window_reference": "exclude the trace from detection and timing denominators; count separately",
            "out_of_tolerance_match": "count as both false positive and false negative",
            "p_after_s": "report without reordering or repairing the predicted picks",
        },
        "threshold_tuning": threshold_tuning,
        "checkpoint_selection": {
            "criterion": "lowest validation loss",
            "provenance": "recorded by the bounded pilot manifest",
            "scientific_baseline_eligible": False,
        },
    }
    canonical = json.dumps(protocol, sort_keys=True, separators=(",", ":")).encode("utf-8")
    protocol["protocol_id"] = f"protocol-{hashlib.sha256(canonical).hexdigest()[:16]}"
    path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    return protocol


def _record_from_prediction(
    *,
    metadata: dict[str, str],
    window_start: int,
    probabilities: np.ndarray,
    picking_config: PeakPickingConfig,
    window_length: int,
    sampling_rate: float,
) -> dict[str, Any]:
    refs = {
        "P": _as_optional_int(metadata.get("trace_P_arrival_sample")),
        "S": _as_optional_int(metadata.get("trace_S_arrival_sample")),
    }
    relative_refs: dict[str, int | None] = {}
    ref_status: dict[str, str] = {}
    for phase in ("P", "S"):
        relative_refs[phase], ref_status[phase] = _reference_status(
            refs[phase], window_start=window_start, window_length=window_length
        )

    picking_config.validate()
    diagnostics = {
        "P": pick_phase_diagnostics(
            probabilities[0],
            threshold=picking_config.p_threshold,
            min_peak_distance_samples=picking_config.min_peak_distance_samples,
        ),
        "S": pick_phase_diagnostics(
            probabilities[1],
            threshold=picking_config.s_threshold,
            min_peak_distance_samples=picking_config.min_peak_distance_samples,
        ),
    }
    picks = {phase: diagnostics[phase].pick for phase in ("P", "S")}
    predicted_relative = {
        phase: None if picks[phase] is None else picks[phase].index for phase in ("P", "S")
    }
    predicted_probability = {
        phase: None if picks[phase] is None else picks[phase].probability for phase in ("P", "S")
    }
    predicted_absolute = {
        phase: window_relative_to_trace_sample(
            window_start, predicted_relative[phase], window_length=window_length
        )
        for phase in ("P", "S")
    }
    timing_error_samples = {
        phase: absolute_timing_error_samples(predicted_absolute[phase], refs[phase])
        if ref_status[phase] == "in_window"
        else None
        for phase in ("P", "S")
    }
    timing_error_ms = {
        phase: samples_to_milliseconds(timing_error_samples[phase], sampling_rate)
        for phase in ("P", "S")
    }
    predicted_p = predicted_absolute["P"]
    predicted_s = predicted_absolute["S"]

    return {
        "trace_name": metadata["trace_name"],
        "event_id": metadata.get("source_id", ""),
        "window_start": window_start,
        "window_length": window_length,
        "reference_absolute": refs,
        "reference_relative": relative_refs,
        "reference_status": ref_status,
        "predicted_relative": predicted_relative,
        "predicted_absolute": predicted_absolute,
        "predicted_probability": predicted_probability,
        "timing_error_samples": timing_error_samples,
        "timing_error_ms": timing_error_ms,
        "pick_diagnostics": {
            phase: {
                "candidate_count": diagnostics[phase].candidate_count,
                "retained_candidate_count": diagnostics[phase].retained_candidate_count,
                "edge_activation": diagnostics[phase].edge_activation,
                "no_candidate_reason": diagnostics[phase].no_candidate_reason,
            }
            for phase in ("P", "S")
        },
        "p_after_s": bool(
            predicted_p is not None and predicted_s is not None and predicted_p > predicted_s
        ),
        "probabilities": probabilities,
    }


def _phase_metrics(
    records: list[dict[str, Any]],
    phase: str,
    *,
    tolerance_samples: int,
    sampling_rate: float,
) -> dict[str, Any]:
    """Report detection and timing separately, retaining every exclusion reason."""

    statuses = [record["reference_status"][phase] for record in records]
    eligible = [record for record in records if record["reference_status"][phase] != "out_of_window"]
    gt_records = [record for record in eligible if record["reference_status"][phase] == "in_window"]
    predicted_times = [
        None
        if record["predicted_absolute"][phase] is None
        else float(record["predicted_absolute"][phase]) / sampling_rate
        for record in eligible
    ]
    reference_times = [
        None
        if record["reference_status"][phase] != "in_window"
        else float(record["reference_absolute"][phase]) / sampling_rate
        for record in eligible
    ]
    detection = classify_picks(
        predicted_times,
        reference_times,
        tolerance=float(tolerance_samples) / sampling_rate,
    )
    errors = [
        int(record["timing_error_samples"][phase])
        for record in gt_records
        if record["timing_error_samples"][phase] is not None
    ]
    residual_values = residuals(
        [
            float(record["predicted_absolute"][phase]) / sampling_rate
            for record in gt_records
            if record["predicted_absolute"][phase] is not None
        ],
        [
            float(record["reference_absolute"][phase]) / sampling_rate
            for record in gt_records
            if record["predicted_absolute"][phase] is not None
        ],
    )
    residual_summary = residual_stats(residual_values)

    missing_gt = statuses.count("missing")
    out_of_window = statuses.count("out_of_window")
    no_prediction_on_gt = sum(
        1
        for record in gt_records
        if record["predicted_absolute"][phase] is None
    )
    predicted_on_missing_gt = sum(
        1
        for record in records
        if record["reference_status"][phase] == "missing"
        and record["predicted_absolute"][phase] is not None
    )
    predicted_on_out_of_window_gt = sum(
        1
        for record in records
        if record["reference_status"][phase] == "out_of_window"
        and record["predicted_absolute"][phase] is not None
    )

    return {
        "phase": phase,
        "n_validation_traces": len(records),
        "n_detection_eligible_traces": len(eligible),
        "n_reference_picks_in_window": len(gt_records),
        "n_reference_missing": missing_gt,
        "n_reference_out_of_window": out_of_window,
        "n_accepted_predictions": detection.n_pred,
        "n_valid_timing_pairs": residual_summary.n,
        "timing_excluded_no_prediction": no_prediction_on_gt,
        "timing_excluded_missing_reference": missing_gt,
        "timing_excluded_out_of_window_reference": out_of_window,
        "accepted_prediction_on_missing_reference": predicted_on_missing_gt,
        "accepted_prediction_on_out_of_window_reference": predicted_on_out_of_window_gt,
        "n_no_pick": sum(
            1
            for record in records
            if record["predicted_absolute"][phase] is None
        ),
        "n_multi_peak_candidates": sum(
            1
            for record in records
            if record["pick_diagnostics"][phase]["candidate_count"] > 1
        ),
        "n_retained_multiple_candidates": sum(
            1
            for record in records
            if record["pick_diagnostics"][phase]["retained_candidate_count"] > 1
        ),
        "n_edge_only_activations": sum(
            1
            for record in records
            if record["pick_diagnostics"][phase]["edge_activation"]
        ),
        "n_p_after_s": sum(1 for record in records if record["p_after_s"]),
        "absolute_timing_error_samples": {
            "mean": float(np.mean(errors)) if errors else None,
            "median": float(np.median(errors)) if errors else None,
        },
        "absolute_timing_error_milliseconds": {
            "mean": samples_to_milliseconds(
                float(np.mean(errors)) if errors else None, sampling_rate
            ),
            "median": samples_to_milliseconds(
                float(np.median(errors)) if errors else None, sampling_rate
            ),
        },
        "matching_tolerance_samples": tolerance_samples,
        "matching_tolerance_milliseconds": float(tolerance_samples) * 1000.0 / sampling_rate,
        "residual_seconds": {
            "n": residual_summary.n,
            "mean": residual_summary.mean,
            "std": residual_summary.std,
            "median": residual_summary.median,
            "mae": residual_summary.mae,
        },
        "residual_milliseconds": {
            "n": residual_summary.n,
            "mean": None if residual_summary.mean is None else residual_summary.mean * 1000.0,
            "std": None if residual_summary.std is None else residual_summary.std * 1000.0,
            "median": None if residual_summary.median is None else residual_summary.median * 1000.0,
            "mae": None if residual_summary.mae is None else residual_summary.mae * 1000.0,
        },
        "detection": {
            "tp": detection.tp,
            "fp": detection.fp,
            "fn": detection.fn,
            "precision": detection.precision,
            "recall": detection.recall,
            "f1": detection.f1,
            "n_pred": detection.n_pred,
            "n_ref": detection.n_ref,
        },
    }


def _select_examples(records: list[dict[str, Any]]) -> dict[str, str]:
    """Select examples from ground-truth categories only, never from predicted positions."""

    both = [
        record
        for record in records
        if record["reference_status"]["P"] == "in_window"
        and record["reference_status"]["S"] == "in_window"
    ]
    missing_s = [
        record for record in records if record["reference_status"]["S"] == "missing"
    ]
    difficult = sorted(
        both,
        key=lambda record: (
            record["reference_absolute"]["S"] - record["reference_absolute"]["P"],
            record["trace_name"],
        ),
    )
    selected: dict[str, str] = {}
    if both:
        selected["both_p_and_s"] = both[0]["trace_name"]
    if missing_s:
        selected["missing_s"] = missing_s[0]["trace_name"]
    if difficult:
        selected["smallest_ground_truth_p_s_separation"] = difficult[0]["trace_name"]
    return selected


def _plot_example(
    record: dict[str, Any],
    waveform: np.ndarray,
    *,
    example_label: str,
    p_threshold: float,
    s_threshold: float,
) -> plt.Figure:
    probabilities = record["probabilities"]
    window_start = int(record["window_start"])
    length = int(record["window_length"])
    x = np.arange(length) + window_start
    fig, axes = plt.subplots(4, 1, figsize=(12, 9), sharex=True, dpi=140)
    component_names = ("component 0 (ENZ file order)", "component 1 (ENZ file order)", "component 2 (ENZ file order)")
    for channel, (axis, name) in enumerate(zip(axes[:3], component_names)):
        axis.plot(x, waveform[channel], color="#30343b", linewidth=0.65)
        axis.set_ylabel(name, fontsize=8)
        axis.grid(True, alpha=0.2)
        if channel == 0:
            axis.set_title(
                f"{example_label}: {record['trace_name']} | window samples "
                f"[{window_start}, {window_start + length})",
                loc="left",
            )
        for phase, color in (("P", "#1769aa"), ("S", "#c2410c")):
            reference = record["reference_absolute"][phase]
            if record["reference_status"][phase] == "in_window":
                axis.axvline(reference, color=color, linestyle="--", linewidth=1.0, alpha=0.8)
            predicted = record["predicted_absolute"][phase]
            if predicted is not None:
                axis.axvline(predicted, color=color, linestyle="-", linewidth=0.9, alpha=0.8)

    probability_axis = axes[3]
    for threshold, color, label in (
        (float(p_threshold), "#1769aa", "P threshold"),
        (float(s_threshold), "#c2410c", "S threshold"),
    ):
        probability_axis.axhline(
            threshold,
            color=color,
            linestyle=":",
            linewidth=1.2,
            alpha=0.95,
            label=f"{label} {threshold:g}",
        )
    probability_axis.plot(x, probabilities[0], label="P probability", color="#1769aa")
    probability_axis.plot(x, probabilities[1], label="S probability", color="#c2410c")
    probability_axis.plot(x, probabilities[2], label="noise probability", color="#5b6470")
    probability_axis.set_ylabel("probability")
    probability_axis.set_xlabel("original trace sample index")
    probability_axis.set_ylim(-0.02, 1.02)
    probability_axis.grid(True, alpha=0.2)
    probability_axis.legend(loc="upper right", ncol=3, fontsize=8)
    annotations = []
    for phase in ("P", "S"):
        status = record["reference_status"][phase]
        if status == "missing":
            annotations.append(f"{phase} reference missing")
        elif status == "out_of_window":
            annotations.append(f"{phase} reference outside window")
        pick = record["predicted_absolute"][phase]
        if pick is None:
            annotations.append(f"no accepted {phase} prediction")
    if annotations:
        probability_axis.text(
            0.01,
            0.02,
            "; ".join(annotations),
            transform=probability_axis.transAxes,
            fontsize=8,
            color="#7f1d1d",
        )
    fig.tight_layout()
    return fig


def _signed_residual_samples(records: list[dict[str, Any]], phase: str) -> np.ndarray:
    """Signed ``predicted - reference`` residuals in samples for valid timing pairs."""

    values = [
        float(record["predicted_absolute"][phase]) - float(record["reference_absolute"][phase])
        for record in records
        if record["reference_status"][phase] == "in_window"
        and record["predicted_absolute"][phase] is not None
    ]
    return np.asarray(values, dtype=float)


def _plot_residual_histograms(
    records: list[dict[str, Any]],
    output_path: Path,
    *,
    tolerance_samples: int,
    sampling_rate: float,
) -> None:
    """Two-panel signed residual histograms for P and S (FR-066)."""

    tolerance_ms = float(tolerance_samples) * 1000.0 / float(sampling_rate)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), dpi=140)
    for axis, phase in zip(axes, ("P", "S")):
        values_ms = _signed_residual_samples(records, phase) * 1000.0 / float(sampling_rate)
        color = "#1769aa" if phase == "P" else "#c2410c"
        axis.axvline(tolerance_ms, color="#5b6470", linewidth=1.0, linestyle=":")
        axis.axvline(-tolerance_ms, color="#5b6470", linewidth=1.0, linestyle=":")
        axis.axvline(
            tolerance_ms,
            color="#5b6470",
            linewidth=1.0,
            linestyle=":",
            label=f"+/-{tolerance_ms:.0f} ms matching tolerance",
        )
        if values_ms.size:
            axis.hist(values_ms, bins=30, color=color, edgecolor="white", alpha=0.9)
            mean_ms = float(np.mean(values_ms))
            median_ms = float(np.median(values_ms))
            axis.axvline(mean_ms, color="#111827", linewidth=1.3, label=f"mean {mean_ms:.0f} ms")
            axis.axvline(
                median_ms,
                color="#6b7280",
                linewidth=1.3,
                linestyle="--",
                label=f"median {median_ms:.0f} ms",
            )
            axis.legend(fontsize=8, loc="upper right")
        else:
            axis.text(
                0.5,
                0.5,
                "no valid timing pairs",
                transform=axis.transAxes,
                ha="center",
                va="center",
                fontsize=10,
                color="#7f1d1d",
            )
        axis.axvline(0.0, color="#111827", linewidth=1.1, alpha=0.8)
        axis.set_title(f"{phase} signed residuals (n = {int(values_ms.size)})", fontsize=10)
        axis.set_xlabel("predicted - reference (ms)")
        axis.set_ylabel("count")
        axis.grid(True, alpha=0.25)
    fig.suptitle("Validation-only timing residuals for matched pairs", fontsize=11)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


FAILURE_KIND_PRIORITY = (
    "out_of_tolerance",
    "missed_detection",
    "false_positive_missing_reference",
)


def _gallery_case(
    record: dict[str, Any],
    phase: str,
    *,
    tolerance_samples: int,
) -> dict[str, Any] | None:
    """Classify one trace for the success/failure galleries under the frozen tolerance.

    ``out_of_window`` references are excluded from galleries exactly as they are excluded from the
    detection denominators.  Categories are derived from the saved reference and prediction only,
    never from a manual judgement of the waveform.
    """

    status = record["reference_status"][phase]
    predicted = record["predicted_absolute"][phase]
    if status == "out_of_window":
        return None
    signed: int | None = None
    if status == "in_window":
        if predicted is None:
            kind = "missed_detection"
        else:
            signed = int(predicted) - int(record["reference_absolute"][phase])
            kind = "success" if abs(signed) <= int(tolerance_samples) else "out_of_tolerance"
    elif predicted is not None:
        kind = "false_positive_missing_reference"
    else:
        return None
    return {
        "trace_name": record["trace_name"],
        "phase": phase,
        "kind": kind,
        "signed_error_samples": signed,
        "record": record,
    }


def _select_gallery_cases(
    records: list[dict[str, Any]],
    *,
    tolerance_samples: int,
    kind: str,
    max_per_phase: int,
) -> list[dict[str, Any]]:
    """Deterministic example selection: ground truth and predictions only (FR-067).

    Successes are the smallest in-tolerance errors.  Failures are drawn round-robin across the
    failure categories so one dominant category cannot crowd the others out of the gallery.
    """

    if kind not in ("success", "failure"):
        raise ValueError(f"kind must be 'success' or 'failure', got {kind!r}")
    if max_per_phase < 0:
        raise ValueError(f"max_per_phase must be >= 0, got {max_per_phase}")
    selected: list[dict[str, Any]] = []
    for phase in ("P", "S"):
        cases = [
            case
            for case in (
                _gallery_case(record, phase, tolerance_samples=tolerance_samples)
                for record in records
            )
            if case is not None and (case["kind"] == "success") == (kind == "success")
        ]
        if not cases:
            continue
        if kind == "success":
            cases.sort(key=lambda case: (abs(case["signed_error_samples"]), case["trace_name"]))
            selected.extend(cases[:max_per_phase])
            continue
        buckets: dict[str, list[dict[str, Any]]] = {}
        for case in cases:
            buckets.setdefault(case["kind"], []).append(case)
        for bucket in buckets.values():
            bucket.sort(
                key=lambda case: (
                    0 if case["signed_error_samples"] is not None else 1,
                    -abs(case["signed_error_samples"] or 0),
                    case["trace_name"],
                )
            )
        per_bucket = max(1, -(-max_per_phase // len(buckets)))
        picked: list[dict[str, Any]] = []
        for category in FAILURE_KIND_PRIORITY:
            picked.extend(buckets.get(category, [])[:per_bucket])
        picked.sort(
            key=lambda case: (FAILURE_KIND_PRIORITY.index(case["kind"]), case["trace_name"])
        )
        selected.extend(picked[:max_per_phase])
    return selected


def _failure_counts(records: list[dict[str, Any]], *, tolerance_samples: int) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {phase: {} for phase in ("P", "S")}
    for phase in ("P", "S"):
        for record in records:
            case = _gallery_case(record, phase, tolerance_samples=tolerance_samples)
            if case is None:
                continue
            counts[phase][case["kind"]] = counts[phase].get(case["kind"], 0) + 1
    return counts


def _cross_phase_proximity(
    records: list[dict[str, Any]],
    *,
    tolerance_samples: int,
) -> dict[str, dict[str, int]]:
    """Count out-of-tolerance picks that sit within tolerance of the *other* phase reference.

    This is a measured position count, not a cause claim; it is the evidence a reviewer needs to
    judge the flagged cross-phase hypothesis.
    """

    proximity: dict[str, dict[str, int]] = {}
    for phase in ("P", "S"):
        other = "S" if phase == "P" else "P"
        out_of_tolerance = 0
        near_other = 0
        for record in records:
            case = _gallery_case(record, phase, tolerance_samples=tolerance_samples)
            if case is None or case["kind"] != "out_of_tolerance":
                continue
            out_of_tolerance += 1
            predicted = record["predicted_absolute"][phase]
            other_reference = record["reference_absolute"][other]
            if (
                predicted is not None
                and other_reference is not None
                and record["reference_status"][other] == "in_window"
                and abs(int(predicted) - int(other_reference)) <= int(tolerance_samples)
            ):
                near_other += 1
        proximity[phase] = {
            "out_of_tolerance": out_of_tolerance,
            "within_tolerance_of_other_reference": near_other,
        }
    return proximity


def _failure_hypothesis(
    record: dict[str, Any],
    phase: str,
    *,
    tolerance_samples: int,
    sampling_rate: float,
) -> str:
    """Return a cause hypothesis explicitly flagged as such, or an explicit ``unexplained`` label.

    Only measured positions are used.  Nothing here is presented as a confirmed cause (FR-068).
    """

    other = "S" if phase == "P" else "P"
    predicted = record["predicted_absolute"][phase]
    other_reference = record["reference_absolute"][other]
    if (
        predicted is not None
        and other_reference is not None
        and record["reference_status"][other] == "in_window"
        and abs(int(predicted) - int(other_reference)) <= int(tolerance_samples)
    ):
        offset_ms = (int(predicted) - int(other_reference)) * 1000.0 / float(sampling_rate)
        return (
            f"HYPOTHESIS: predicted {phase} lies {offset_ms:+.0f} ms from the {other} reference, "
            f"inside the {int(tolerance_samples)}-sample tolerance — hypothesis that the {phase} "
            f"channel responded to the {other} arrival. Flagged as a hypothesis, not confirmed."
        )
    if record["reference_status"][phase] == "missing":
        return (
            "unexplained — the reference label for this phase is missing on this trace, so the "
            "accepted pick cannot be scored against ground truth."
        )
    if predicted is None:
        return (
            "unexplained — no interior peak at or above the configured threshold was accepted on "
            "this trace."
        )
    return (
        "unexplained — the measured offset is outside both this phase's reference and the "
        "other-phase reference; no cause has been established."
    )


def _plot_gallery(
    cases: list[dict[str, Any]],
    output_path: Path,
    *,
    waveforms_by_trace: dict[str, np.ndarray],
    p_threshold: float,
    s_threshold: float,
    tolerance_samples: int,
    sampling_rate: float,
    show_hypothesis: bool,
) -> None:
    """Row-per-example gallery: waveform with picks, plus probability curves with thresholds."""

    if not cases:
        raise ValueError("cannot plot an empty gallery")
    rows = len(cases)
    fig, axes = plt.subplots(
        rows, 2, figsize=(13.0, 3.0 * rows), dpi=130, squeeze=False, sharex="col"
    )
    component_colors = ("#9aa3ad", "#6b7280", "#30343b")
    component_names = (
        "component 0 (ENZ file order)",
        "component 1 (ENZ file order)",
        "component 2 (ENZ file order)",
    )
    for row, case in enumerate(cases):
        record = case["record"]
        waveform = waveforms_by_trace[case["trace_name"]]
        window_start = int(record["window_start"])
        length = int(record["window_length"])
        x = np.arange(length) + window_start
        wave_axis, probability_axis = axes[row]
        for channel, (color, name) in enumerate(zip(component_colors, component_names)):
            wave_axis.plot(
                x,
                waveform[channel],
                color=color,
                linewidth=0.5,
                label=name if row == 0 else None,
            )
        wave_axis.grid(True, alpha=0.2)
        signed = case["signed_error_samples"]
        error_text = "no signed error" if signed is None else f"{signed * 1000.0 / sampling_rate:+.0f} ms"
        kind_text = case["kind"].replace("_", " ")
        title_line = (
            f"{case['phase']} {kind_text}: {case['trace_name']} | signed error {error_text}"
        )
        if show_hypothesis:
            hypothesis = _failure_hypothesis(
                record,
                case["phase"],
                tolerance_samples=tolerance_samples,
                sampling_rate=sampling_rate,
            )
            wave_axis.set_title(f"{title_line}\n{hypothesis}", loc="left", fontsize=8)
        else:
            wave_axis.set_title(title_line, loc="left", fontsize=9)
        if row == 0:
            wave_axis.legend(loc="upper right", fontsize=7, ncol=3)

        for threshold, color, label in (
            (float(p_threshold), "#1769aa", "P threshold"),
            (float(s_threshold), "#c2410c", "S threshold"),
        ):
            probability_axis.axhline(
                threshold,
                color=color,
                linestyle=":",
                linewidth=1.1,
                alpha=0.95,
                label=f"{label} {threshold:g}",
            )
        probability_axis.plot(x, record["probabilities"][0], color="#1769aa", linewidth=0.9, label="P probability")
        probability_axis.plot(x, record["probabilities"][1], color="#c2410c", linewidth=0.9, label="S probability")
        probability_axis.plot(x, record["probabilities"][2], color="#5b6470", linewidth=0.9, label="noise probability")
        probability_axis.set_ylim(-0.02, 1.02)
        probability_axis.grid(True, alpha=0.2)
        for axis in (wave_axis, probability_axis):
            for phase, color in (("P", "#1769aa"), ("S", "#c2410c")):
                if record["reference_status"][phase] == "in_window":
                    axis.axvline(
                        record["reference_absolute"][phase],
                        color=color,
                        linestyle="--",
                        linewidth=1.0,
                        alpha=0.85,
                    )
                predicted = record["predicted_absolute"][phase]
                if predicted is not None:
                    axis.axvline(predicted, color=color, linestyle="-", linewidth=0.9, alpha=0.85)
        if row == 0:
            probability_axis.legend(loc="upper right", fontsize=7, ncol=3)
        probability_axis.set_xlabel("original trace sample index")
    fig.suptitle(
        "Validation-only gallery — dashed line: reference pick, solid line: predicted pick",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def _write_failure_analysis(
    path: Path,
    *,
    protocol: dict[str, Any],
    counts: dict[str, dict[str, int]],
    proximity: dict[str, dict[str, int]],
    cases: list[dict[str, Any]],
    tolerance_samples: int,
    sampling_rate: float,
) -> None:
    lines = [
        "# Validation-only failure analysis",
        "",
        f"- Protocol: `{protocol['protocol_id']}` ({protocol['status']})",
        f"- Matching tolerance: `{tolerance_samples}` samples "
        f"(`{float(tolerance_samples) * 1000.0 / sampling_rate:.1f}` ms at {sampling_rate} Hz)",
        "- Test split: **not loaded, evaluated, tuned, or used**",
        "- Every cause statement below is either explicitly flagged as a **hypothesis** or labelled "
        "**unexplained**. None of them is a confirmed cause (FR-068).",
        "",
        "## Category counts",
        "",
        "| Phase | Success (in tolerance) | Out of tolerance | Missed detection | "
        "Prediction on missing reference |",
        "|---|---|---|---|---|",
    ]
    for phase in ("P", "S"):
        phase_counts = counts.get(phase, {})
        lines.append(
            f"| {phase} | {phase_counts.get('success', 0)} | "
            f"{phase_counts.get('out_of_tolerance', 0)} | "
            f"{phase_counts.get('missed_detection', 0)} | "
            f"{phase_counts.get('false_positive_missing_reference', 0)} |"
        )
    lines.extend(
        [
            "",
            "## Cross-phase proximity of out-of-tolerance picks",
            "",
            "Measured positions only: how many out-of-tolerance picks for a phase lie within the "
            "matching tolerance of the *other* phase's reference. This is the evidence behind the "
            "flagged cross-phase hypothesis, not a confirmation of it.",
            "",
            "| Phase | Out-of-tolerance picks | Of those, within tolerance of the other-phase reference |",
            "|---|---|---|",
        ]
    )
    for phase in ("P", "S"):
        entry = proximity.get(phase, {})
        lines.append(
            f"| {phase} | {entry.get('out_of_tolerance', 0)} | "
            f"{entry.get('within_tolerance_of_other_reference', 0)} |"
        )
    lines.extend(["", "## Gallery cases", ""])
    if not cases:
        lines.append("No failure cases were available for the gallery.")
    for case in cases:
        signed = case["signed_error_samples"]
        if signed is None:
            signed_text = "no signed error"
        else:
            signed_text = (
                f"{signed:+d} samples ({signed * 1000.0 / sampling_rate:+.0f} ms)"
            )
        lines.extend(
            [
                f"### `{case['phase']}` · `{case['kind']}` · `{case['trace_name']}`",
                "",
                f"- Signed error: `{signed_text}`",
                f"- {_failure_hypothesis(case['record'], case['phase'], tolerance_samples=tolerance_samples, sampling_rate=sampling_rate)}",
                "",
            ]
        )
    lines.extend(
        [
            "## Limitations",
            "",
            "- Category counts and hypotheses are computed on the same validation subset used for "
            "threshold selection, so they are exploratory and optimistically biased.",
            "- The hypotheses are generated from measured pick and reference positions only; "
            "confirming a cause requires a separate, separately approved investigation.",
            "- No test-set inference was performed.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_predictions_csv(records: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "trace_name",
        "event_id",
        "window_start",
        "P_reference_absolute",
        "P_reference_status",
        "P_predicted_absolute",
        "P_predicted_probability",
        "P_timing_error_samples",
        "P_timing_error_ms",
        "S_reference_absolute",
        "S_reference_status",
        "S_predicted_absolute",
        "S_predicted_probability",
        "S_timing_error_samples",
        "S_timing_error_ms",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {
                "trace_name": record["trace_name"],
                "event_id": record["event_id"],
                "window_start": record["window_start"],
            }
            for phase in ("P", "S"):
                row[f"{phase}_reference_absolute"] = record["reference_absolute"][phase]
                row[f"{phase}_reference_status"] = record["reference_status"][phase]
                row[f"{phase}_predicted_absolute"] = record["predicted_absolute"][phase]
                row[f"{phase}_predicted_probability"] = record["predicted_probability"][phase]
                row[f"{phase}_timing_error_samples"] = record["timing_error_samples"][phase]
                row[f"{phase}_timing_error_ms"] = record["timing_error_ms"][phase]
            writer.writerow(row)


def _write_report(
    path: Path,
    *,
    manifest_path: Path,
    checkpoint_path: Path,
    selected_count: int,
    picking_config: PeakPickingConfig,
    phase_metrics: dict[str, dict[str, Any]],
    examples: dict[str, str],
    elapsed_seconds: float,
    threshold_tuning: dict[str, Any],
    protocol: dict[str, Any],
    figure_paths: dict[str, str],
    failure_counts: dict[str, dict[str, int]],
    cross_phase_proximity: dict[str, dict[str, int]],
    failure_analysis_path: Path,
) -> None:
    lines = [
        "# Validation-only phase-picking inference",
        "",
        f"- Checkpoint: `{checkpoint_path}` (loaded with `weights_only=True`)",
        f"- Pilot manifest: `{manifest_path}`",
        f"- Validation traces evaluated: **{selected_count}**",
        f"- Device inference duration: **{elapsed_seconds:.3f} s**",
        "- Test split: **not loaded, evaluated, tuned, or used**",
        f"- Protocol: `{protocol['protocol_id']}` ({protocol['status']})",
        "",
        "## Picking rule",
        "",
        "The picker selects the strongest interior local maximum on each P/S probability curve "
        "when it is at or above the configured threshold. Edge-only activations are rejected. "
        "Nearby candidate maxima are suppressed using the configured minimum distance.",
        "",
        f"- P threshold: `{picking_config.p_threshold}`",
        f"- S threshold: `{picking_config.s_threshold}`",
        f"- Minimum peak distance: `{picking_config.min_peak_distance_samples}` samples",
        f"- Matching tolerance: `{picking_config.matching_tolerance_samples}` samples "
        f"(`{picking_config.matching_tolerance_samples * 1000.0 / protocol['sampling_rate_hz']:.1f}` ms "
        f"at {protocol['sampling_rate_hz']} Hz)",
        f"- Threshold objective: `{threshold_tuning['objective']}`",
        f"- Threshold tie-break: `{', '.join(threshold_tuning['tie_break'])}`",
        "- Edge-only activations: rejected and counted",
        "- Out-of-tolerance matches: counted as both FP and FN",
        "- P-after-S predictions: reported without reordering",
        "",
        "## Metrics",
        "",
        "Detection metrics and timing accuracy are reported separately. Timing statistics use "
        "only traces with an in-window reference and an accepted prediction. Missing or "
        "out-of-window references and absent predictions are retained as exclusions below.",
        "",
    ]
    for phase in ("P", "S"):
        metric = phase_metrics[phase]
        detection = metric["detection"]
        timing = metric["absolute_timing_error_samples"]
        timing_ms = metric["absolute_timing_error_milliseconds"]
        residual = metric["residual_seconds"]
        lines.extend(
            [
                f"### {phase} phase",
                "",
                f"- Accepted predictions: **{metric['n_accepted_predictions']}**",
                f"- In-window reference picks: **{metric['n_reference_picks_in_window']}**",
                f"- Valid timing pairs: **{metric['n_valid_timing_pairs']}**",
                f"- Mean absolute timing error: **{timing['mean']} samples / {timing_ms['mean']} ms**",
                f"- Median absolute timing error: **{timing['median']} samples / {timing_ms['median']} ms**",
                f"- Signed residual mean / std / median / MAE: **{residual['mean']} / "
                f"{residual['std']} / {residual['median']} / {residual['mae']} s**",
                f"- Detection TP/FP/FN: **{detection['tp']}/{detection['fp']}/{detection['fn']}**",
                f"- Precision / recall / F1: **{detection['precision']:.4f} / "
                f"{detection['recall']:.4f} / {detection['f1']:.4f}**",
                f"- Missing reference: `{metric['n_reference_missing']}`; out of window: "
                f"`{metric['n_reference_out_of_window']}`; no accepted prediction on reference: "
                f"`{metric['timing_excluded_no_prediction']}`",
                f"- Accepted predictions on missing reference: `{metric['accepted_prediction_on_missing_reference']}`",
                f"- Multi-peak candidates: `{metric['n_multi_peak_candidates']}`; edge-only activations: "
                f"`{metric['n_edge_only_activations']}`; no pick: `{metric['n_no_pick']}`",
                f"- P-after-S predictions: `{metric['n_p_after_s']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Deterministic example traces",
            "",
            "The both-P/S and missing-S examples were selected by the saved validation subset and "
            "ground-truth label availability. The difficult example is the available both-pick "
            "trace with the smallest ground-truth P-to-S separation; ground truth was not used to "
            "choose thresholds or predicted positions.",
            "",
        ]
    )
    for label, trace_name in examples.items():
        lines.append(f"- `{label}`: `{trace_name}`")
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "- Example figures show the three waveform components, the reference and predicted picks "
            "and the P/S/noise probability curves with the applied P and S thresholds drawn as "
            "dotted horizontal lines.",
            "- Residual histograms show signed `predicted - reference` values for every valid timing "
            "pair, with the matching tolerance marked.",
            "- The galleries are selected from ground truth and predictions only: successes are the "
            "smallest in-tolerance errors, failures are drawn round-robin across the failure "
            "categories.",
            "",
        ]
    )
    for label, figure_path in figure_paths.items():
        lines.append(f"- `{label}`: `{figure_path}`")
    lines.extend(
        [
            "",
            "## Failure categories",
            "",
            "| Phase | Success (in tolerance) | Out of tolerance | Missed detection | "
            "Prediction on missing reference |",
            "|---|---|---|---|---|",
        ]
    )
    for phase in ("P", "S"):
        phase_counts = failure_counts.get(phase, {})
        lines.append(
            f"| {phase} | {phase_counts.get('success', 0)} | "
            f"{phase_counts.get('out_of_tolerance', 0)} | "
            f"{phase_counts.get('missed_detection', 0)} | "
            f"{phase_counts.get('false_positive_missing_reference', 0)} |"
        )
    lines.extend(
        [
            "",
            "Measured cross-phase proximity of the out-of-tolerance picks "
            + "; ".join(
                f"{phase}: {entry.get('within_tolerance_of_other_reference', 0)} of "
                f"{entry.get('out_of_tolerance', 0)} within tolerance of the other-phase reference"
                for phase, entry in cross_phase_proximity.items()
            )
            + " (evidence only, not a confirmed cause).",
            "",
            f"Per-case cause statements are in `{failure_analysis_path}`. Each one is explicitly "
            "flagged as a hypothesis or labelled `unexplained`; none is a confirmed cause.",
            "",
            "## Limitations",
            "",
            "- This evaluates only the 210-trace validation subset used by the bounded pilot.",
            "- The three-epoch model and tiny event subset are not evidence of scientific performance or generalization.",
            "- Thresholds were selected and reported on the same validation subset; the protocol artifact is therefore a candidate validation protocol, not an unbiased performance estimate.",
            "- The checkpoint-selection criterion was recorded after the bounded pilot and is not eligible for a scientific test baseline.",
            "- No test-set inference was performed.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_validation_inference(
    *,
    manifest_path: Path,
    config_path: Path,
    checkpoint_path: Path,
    output_dir: Path,
    p_threshold: float | None = None,
    s_threshold: float | None = None,
    min_peak_distance_samples: int = DEFAULT_MIN_PEAK_DISTANCE_SAMPLES,
    matching_tolerance_samples: int = DEFAULT_MATCHING_TOLERANCE_SAMPLES,
) -> dict[str, Any]:
    if output_dir.resolve() == checkpoint_path.parent.resolve():
        raise ValueError("validation output must not overwrite the pilot checkpoint directory")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(
            f"validation output directory is not empty: {output_dir}; choose a new run identifier"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    saved_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dataset_info = manifest["dataset"]
    selected_validation_events = set(dataset_info["selected_validation_events"])
    metadata_path = Path(dataset_info["metadata_csv"])
    hdf5_path = Path(dataset_info["hdf5"])
    if not metadata_path.exists() or not hdf5_path.exists():
        raise FileNotFoundError("pilot manifest data paths are not available")
    rows = _read_csv(metadata_path)
    validation_rows = [
        row for row in rows if row.get("source_id", "").strip() in selected_validation_events
    ]
    if len(validation_rows) != int(dataset_info["selected_validation_trace_count"]):
        raise RuntimeError(
            f"validation subset count mismatch: manifest={dataset_info['selected_validation_trace_count']} "
            f"metadata={len(validation_rows)}"
        )
    if {row.get("source_id", "").strip() for row in validation_rows} != selected_validation_events:
        raise RuntimeError("selected validation event membership could not be reconstructed")

    # Only the validation split file is read as a membership guard.  The test split is never opened.
    validation_split_path = Path(manifest["split_files"]["validation"]["path"])
    validation_split_events = {
        row["event_id"].strip() for row in _read_csv(validation_split_path)
    }
    if not selected_validation_events <= validation_split_events:
        raise RuntimeError("selected validation events are not members of splits/validation.csv")

    window_length = int(saved_config["input_shape"][2])
    sampling_rate = float(
        saved_config.get(
            "sampling_rate",
            saved_config["dataset"]["coverage"]["expected_rate_hz"],
        )
    )
    if not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError(f"saved sampling rate must be finite and > 0, got {sampling_rate!r}")
    seed = int(saved_config["seed"])
    base = int(saved_config["model"]["base"])
    depth = int(saved_config["model"]["depth"])
    trace_names = [row["trace_name"] for row in validation_rows]
    metadata_by_trace = {row["trace_name"]: row for row in validation_rows}
    dataset = InstanceDataset(
        hdf5_path,
        metadata_path,
        window_length=window_length,
        sigma=float(saved_config["target_sigma_samples"]),
        depth=depth,
        training=False,
        seed=seed,
        trace_names=trace_names,
        pure_noise_fraction=0.0,
    )
    if len(dataset) != len(validation_rows):
        raise RuntimeError("validation dataset length does not match selected metadata")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = _load_saved_state(
        checkpoint_path,
        base=base,
        depth=depth,
        device=device,
    )
    baseline_p_threshold = 0.5 if p_threshold is None else float(p_threshold)
    baseline_s_threshold = 0.5 if s_threshold is None else float(s_threshold)
    initial_picking_config = PeakPickingConfig(
        p_threshold=baseline_p_threshold,
        s_threshold=baseline_s_threshold,
        min_peak_distance_samples=min_peak_distance_samples,
        matching_tolerance_samples=matching_tolerance_samples,
    )
    initial_picking_config.validate()

    loader = build_dataloader(dataset, batch_size=int(manifest["batch_size"]), num_workers=0, seed=seed)
    waveforms_by_trace: dict[str, np.ndarray] = {}
    prediction_inputs: list[dict[str, Any]] = []
    started = time.perf_counter()
    with torch.no_grad():
        for batch in loader:
            waveform = batch["waveform"].to(device=device, dtype=torch.float32)
            logits = model(waveform)
            probabilities = torch.softmax(logits, dim=1).cpu().numpy()
            for item_index, trace_name in enumerate(batch["trace_name"]):
                name = str(trace_name)
                window_start = int(batch["window_start"][item_index].item())
                waveforms_by_trace[name] = batch["waveform"][item_index].numpy()
                prediction_inputs.append(
                    {
                        "metadata": metadata_by_trace[name],
                        "window_start": window_start,
                        "probabilities": probabilities[item_index],
                    }
                )
    elapsed = time.perf_counter() - started
    prediction_inputs.sort(key=lambda item: item["metadata"]["trace_name"])
    threshold_tuning = _sweep_validation_thresholds(
        prediction_inputs,
        candidate_thresholds=VALIDATION_THRESHOLD_CANDIDATES,
        min_peak_distance_samples=min_peak_distance_samples,
        matching_tolerance_samples=matching_tolerance_samples,
        sampling_rate=sampling_rate,
        window_length=window_length,
        baseline_p_threshold=baseline_p_threshold,
        baseline_s_threshold=baseline_s_threshold,
    )
    selected_p_threshold = float(
        p_threshold
        if p_threshold is not None
        else threshold_tuning["phases"]["P"]["selected_threshold"]
    )
    selected_s_threshold = float(
        s_threshold
        if s_threshold is not None
        else threshold_tuning["phases"]["S"]["selected_threshold"]
    )
    threshold_tuning["selected_thresholds"] = {
        "P": selected_p_threshold,
        "S": selected_s_threshold,
    }
    threshold_tuning["explicit_overrides"] = {
        "P": p_threshold is not None,
        "S": s_threshold is not None,
    }
    picking_config = PeakPickingConfig(
        p_threshold=selected_p_threshold,
        s_threshold=selected_s_threshold,
        min_peak_distance_samples=min_peak_distance_samples,
        matching_tolerance_samples=matching_tolerance_samples,
    )
    picking_config.validate()
    protocol = _write_frozen_protocol(
        output_dir / "protocol.json",
        picking_config=picking_config,
        sampling_rate=sampling_rate,
        threshold_tuning=threshold_tuning,
    )
    (output_dir / "picking_config.json").write_text(
        json.dumps(
            {
                "protocol_id": protocol["protocol_id"],
                "p_threshold": picking_config.p_threshold,
                "s_threshold": picking_config.s_threshold,
                "min_peak_distance_samples": picking_config.min_peak_distance_samples,
                "matching_tolerance_samples": picking_config.matching_tolerance_samples,
                "sampling_rate_hz": sampling_rate,
                "threshold_tuning": threshold_tuning,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    records = _records_for_picking_config(
        prediction_inputs,
        picking_config,
        window_length=window_length,
        sampling_rate=sampling_rate,
    )
    if len(records) != len(dataset):
        raise RuntimeError("inference did not produce one result per validation trace")

    phase_metrics = {
        phase: _phase_metrics(
            records,
            phase,
            tolerance_samples=picking_config.matching_tolerance_samples,
            sampling_rate=sampling_rate,
        )
        for phase in ("P", "S")
    }
    examples = _select_examples(records)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    figure_paths: dict[str, str] = {}
    figure_names = {
        "both_p_and_s": "validation_both_p_s.png",
        "missing_s": "validation_missing_s.png",
        "smallest_ground_truth_p_s_separation": "validation_difficult_separation.png",
    }
    record_by_trace = {record["trace_name"]: record for record in records}
    for label, trace_name in examples.items():
        path = figures_dir / figure_names[label]
        figure = _plot_example(
            record_by_trace[trace_name],
            waveforms_by_trace[trace_name],
            example_label=label,
            p_threshold=picking_config.p_threshold,
            s_threshold=picking_config.s_threshold,
        )
        figure.savefig(path)
        plt.close(figure)
        figure_paths[label] = str(path)

    residual_path = figures_dir / "validation_residual_histograms.png"
    _plot_residual_histograms(
        records,
        residual_path,
        tolerance_samples=picking_config.matching_tolerance_samples,
        sampling_rate=sampling_rate,
    )
    figure_paths["residual_histograms"] = str(residual_path)

    success_cases = _select_gallery_cases(
        records,
        tolerance_samples=picking_config.matching_tolerance_samples,
        kind="success",
        max_per_phase=3,
    )
    failure_cases = _select_gallery_cases(
        records,
        tolerance_samples=picking_config.matching_tolerance_samples,
        kind="failure",
        max_per_phase=4,
    )
    if success_cases:
        success_path = figures_dir / "gallery_success.png"
        _plot_gallery(
            success_cases,
            success_path,
            waveforms_by_trace=waveforms_by_trace,
            p_threshold=picking_config.p_threshold,
            s_threshold=picking_config.s_threshold,
            tolerance_samples=picking_config.matching_tolerance_samples,
            sampling_rate=sampling_rate,
            show_hypothesis=False,
        )
        figure_paths["success_gallery"] = str(success_path)
    if failure_cases:
        failure_path = figures_dir / "gallery_failure.png"
        _plot_gallery(
            failure_cases,
            failure_path,
            waveforms_by_trace=waveforms_by_trace,
            p_threshold=picking_config.p_threshold,
            s_threshold=picking_config.s_threshold,
            tolerance_samples=picking_config.matching_tolerance_samples,
            sampling_rate=sampling_rate,
            show_hypothesis=True,
        )
        figure_paths["failure_gallery"] = str(failure_path)

    counts = _failure_counts(
        records, tolerance_samples=picking_config.matching_tolerance_samples
    )
    proximity = _cross_phase_proximity(
        records, tolerance_samples=picking_config.matching_tolerance_samples
    )
    failure_analysis_path = output_dir / "failure_analysis.md"
    _write_failure_analysis(
        failure_analysis_path,
        protocol=protocol,
        counts=counts,
        proximity=proximity,
        cases=failure_cases,
        tolerance_samples=picking_config.matching_tolerance_samples,
        sampling_rate=sampling_rate,
    )

    serializable_records = []
    for record in records:
        serializable = {key: value for key, value in record.items() if key != "probabilities"}
        serializable_records.append(serializable)
    (output_dir / "predictions.json").write_text(
        json.dumps(serializable_records, indent=2),
        encoding="utf-8",
    )
    _write_predictions_csv(records, output_dir / "predictions.csv")
    metrics = {
        "n_validation_traces_evaluated": len(records),
        "phases": phase_metrics,
        "examples": examples,
        "figures": figure_paths,
        "failure_counts": counts,
        "cross_phase_proximity": proximity,
        "gallery": {
            "success": [
                {"phase": case["phase"], "trace_name": case["trace_name"]}
                for case in success_cases
            ],
            "failure": [
                {
                    "phase": case["phase"],
                    "trace_name": case["trace_name"],
                    "kind": case["kind"],
                    "signed_error_samples": case["signed_error_samples"],
                }
                for case in failure_cases
            ],
        },
        "failure_analysis": str(failure_analysis_path),
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _write_report(
        output_dir / "validation_report.md",
        manifest_path=manifest_path,
        checkpoint_path=checkpoint_path,
        selected_count=len(records),
        picking_config=picking_config,
        phase_metrics=phase_metrics,
        examples=examples,
        elapsed_seconds=elapsed,
        threshold_tuning=threshold_tuning,
        protocol=protocol,
        figure_paths=figure_paths,
        failure_counts=counts,
        cross_phase_proximity=proximity,
        failure_analysis_path=failure_analysis_path,
    )
    run_metadata = {
        "run_type": "validation_inference_and_visualization",
        "manifest": str(manifest_path),
        "config": str(config_path),
        "checkpoint": str(checkpoint_path),
        "checkpoint_load": "torch.load(weights_only=True)",
        "device": str(device),
        "torch_version": str(torch.__version__),
        "cuda_version": str(torch.version.cuda) if torch.version.cuda else None,
        "validation_events": sorted(selected_validation_events),
        "n_validation_traces": len(records),
        "test_split_loaded": False,
        "test_split_evaluated": False,
        "test_split_used_for_tuning": False,
        "protocol": protocol,
        "picking_config": {
            "p_threshold": picking_config.p_threshold,
            "s_threshold": picking_config.s_threshold,
            "min_peak_distance_samples": picking_config.min_peak_distance_samples,
            "matching_tolerance_samples": picking_config.matching_tolerance_samples,
        },
        "threshold_tuning": threshold_tuning,
        "metrics": metrics,
        "elapsed_seconds": elapsed,
        "limitations": [
            "Validation-only inference on the 210-trace bounded pilot subset.",
            "Threshold selection and reporting use the same validation subset, so the result is exploratory.",
            "The frozen protocol is a candidate validation protocol and explicitly does not authorize test evaluation.",
            "The three-epoch model and tiny event subset do not support scientific generalization claims.",
        ],
    }
    (output_dir / "run.json").write_text(json.dumps(run_metadata, indent=2), encoding="utf-8")
    return run_metadata


def main() -> None:
    args = _parse_args()
    result = run_validation_inference(
        manifest_path=args.manifest,
        config_path=args.config,
        checkpoint_path=args.checkpoint,
        output_dir=args.out,
        p_threshold=args.p_threshold,
        s_threshold=args.s_threshold,
        min_peak_distance_samples=args.min_peak_distance_samples,
        matching_tolerance_samples=args.matching_tolerance_samples,
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.out),
                "n_validation_traces": result["n_validation_traces"],
                "figures": result["metrics"]["figures"],
                "test_split_loaded": result["test_split_loaded"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

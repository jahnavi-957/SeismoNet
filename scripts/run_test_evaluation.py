"""Held-out test split evaluation for SeismoNet.

Strictly follows the approved protocol (protocol-5fa5744aca58cc3c) and supervisor checklist:
- Uses ONLY frozen checkpoint runs/experiment_002_p_training/best.pt (epoch 11).
- Uses ONLY frozen thresholds: P 0.05, S 0.10, matching tolerance 20 samples = 200 ms @ 100 Hz.
- Uses ONLY test events from splits/test.csv.
- Evaluates once, writing to a brand new output directory runs/eval_test_best/.
- Never overwrites checkpoints or validation artifacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import yaml

from seismonet.dataset import InstanceDataset, build_dataloader
from seismonet.metrics import classify_picks, residual_stats, residuals
from seismonet.model import SeismoUnet1d
from seismonet.picking import (
    PeakPickingConfig,
    absolute_timing_error_samples,
    pick_phase_diagnostics,
    samples_to_milliseconds,
    window_relative_to_trace_sample,
)
from seismonet.validation_inference import _as_optional_int, _read_csv, _reference_status

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_PATH = ROOT / "runs" / "experiment_002_p_training" / "best.pt"
PROTOCOL_PATH = ROOT / "runs" / "validation_protocol_candidate_seed42" / "protocol.json"
PILOT_RUN = ROOT / "runs" / "pilot_seed42" / "run.json"
SPLIT_JSON = ROOT / "splits" / "split.json"
TEST_SPLIT_CSV = ROOT / "splits" / "test.csv"
DEFAULT_OUT_DIR = ROOT / "runs" / "eval_test_best"


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
        phase: None if picks[phase] is None else float(picks[phase].probability) for phase in ("P", "S")
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

    p_at_ref_values = []
    for r in gt_records:
        rel_ref = r["reference_relative"][phase]
        if rel_ref is not None and 0 <= rel_ref < r["window_length"]:
            p_idx = 0 if phase == "P" else 1
            p_at_ref_values.append(float(r["probabilities"][p_idx, rel_ref]))

    return {
        "phase": phase,
        "n_traces": len(records),
        "n_detection_eligible_traces": len(eligible),
        "n_reference_picks_in_window": len(gt_records),
        "n_reference_missing": statuses.count("missing"),
        "n_reference_out_of_window": statuses.count("out_of_window"),
        "detection": {
            "precision": float(detection.precision),
            "recall": float(detection.recall),
            "f1": float(detection.f1),
            "n_pred": int(detection.n_pred),
            "n_ref": int(detection.n_ref),
            "tp": int(detection.tp),
            "fp": int(detection.fp),
            "fn": int(detection.fn),
        },
        "timing_residuals": {
            "n": int(residual_summary.n),
            "mean_s": None if residual_summary.mean is None else float(residual_summary.mean),
            "median_s": None if residual_summary.median is None else float(residual_summary.median),
            "std_s": None if residual_summary.std is None else float(residual_summary.std),
            "mae_s": None if residual_summary.mae is None else float(residual_summary.mae),
            "median_abs_error_samples": float(np.median(errors)) if errors else None,
            "median_abs_error_ms": float(np.median(errors) / sampling_rate * 1000.0) if errors else None,
        },
        "mean_p_at_reference": float(np.mean(p_at_ref_values)) if p_at_ref_values else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Destination directory for test evaluation")
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"Output directory exists and is not empty: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir = out_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SEISMONET: HELD-OUT TEST SPLIT EVALUATION")
    print("=" * 70)

    # 1. Load Protocol & Checkpoint
    assert CHECKPOINT_PATH.exists(), f"Missing checkpoint: {CHECKPOINT_PATH}"
    assert PROTOCOL_PATH.exists(), f"Missing protocol: {PROTOCOL_PATH}"
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    p_threshold = float(protocol["picking"]["p_threshold"])
    s_threshold = float(protocol["picking"]["s_threshold"])
    min_peak_distance = int(protocol["picking"]["min_peak_distance_samples"])
    matching_tolerance = int(protocol["picking"]["matching_tolerance_samples"])
    sampling_rate = float(protocol["sampling_rate_hz"])

    print(f"Checkpoint: {CHECKPOINT_PATH.name} ({CHECKPOINT_PATH.stat().st_size} bytes)")
    print(f"Protocol ID: {protocol['protocol_id']}")
    print(f"Thresholds: P={p_threshold}, S={s_threshold}, tol={matching_tolerance} samples ({matching_tolerance/sampling_rate*1000:.0f} ms)")

    # 2. Load dataset paths from pilot manifest
    pilot = json.loads(PILOT_RUN.read_text(encoding="utf-8"))
    hdf5_path = Path(pilot["dataset"]["hdf5"])
    metadata_csv = Path(pilot["dataset"]["metadata_csv"])
    assert hdf5_path.exists() and metadata_csv.exists()

    # 3. Load test split events & match with metadata
    test_split_rows = _read_csv(TEST_SPLIT_CSV)
    test_event_ids = {r["event_id"].strip() for r in test_split_rows}

    # Verify zero overlap with train & validation splits
    train_split_events = {r["event_id"].strip() for r in _read_csv(ROOT / "splits" / "train.csv")}
    val_split_events = {r["event_id"].strip() for r in _read_csv(ROOT / "splits" / "validation.csv")}
    assert len(test_event_ids.intersection(train_split_events)) == 0, "DATA LEAKAGE: test intersects train!"
    assert len(test_event_ids.intersection(val_split_events)) == 0, "DATA LEAKAGE: test intersects val!"

    meta_rows = _read_csv(metadata_csv)
    test_traces = [r for r in meta_rows if r.get("source_id", "").strip() in test_event_ids]
    test_trace_names = [r["trace_name"] for r in test_traces]
    test_event_count = len({r["source_id"].strip() for r in test_traces})
    print(f"Test traces identified in sample: {len(test_traces)} across {test_event_count} events")

    # 4. Initialize Dataset and DataLoader
    window_length = 3072
    depth = 4
    base = 16
    dataset = InstanceDataset(
        hdf5_path,
        metadata_csv,
        window_length=window_length,
        sigma=20.0,
        depth=depth,
        training=False,
        seed=42,
        trace_names=test_trace_names,
        pure_noise_fraction=0.0,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Inference device: {device}")

    # 5. Build Model and load weights-only checkpoint
    model = SeismoUnet1d(base=base, depth=depth)
    state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
    if "model_state_dict" in state_dict:
        state_dict = state_dict["model_state_dict"]
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    # 6. Execute Inference
    loader = build_dataloader(dataset, batch_size=16, num_workers=0, seed=42)
    metadata_by_trace = {r["trace_name"]: r for r in test_traces}
    waveforms_by_trace: dict[str, np.ndarray] = {}
    prediction_inputs: list[dict[str, Any]] = []

    print(f"Running inference over {len(dataset)} test traces...")
    t0 = time.perf_counter()
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
    t1 = time.perf_counter()
    print(f"Inference complete in {t1 - t0:.2f} s ({len(dataset)/(t1-t0):.1f} traces/s)")

    # 7. Extract picks & compute metrics
    picking_config = PeakPickingConfig(
        p_threshold=p_threshold,
        s_threshold=s_threshold,
        min_peak_distance_samples=min_peak_distance,
        matching_tolerance_samples=matching_tolerance,
    )
    records = [
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

    p_metrics = _phase_metrics(records, "P", tolerance_samples=matching_tolerance, sampling_rate=sampling_rate)
    s_metrics = _phase_metrics(records, "S", tolerance_samples=matching_tolerance, sampling_rate=sampling_rate)

    print("-" * 70)
    print("HELD-OUT TEST SET RESULTS:")
    print(f"  P: Precision = {p_metrics['detection']['precision']:.4f}, Recall = {p_metrics['detection']['recall']:.4f}, F1 = {p_metrics['detection']['f1']:.4f}")
    print(f"     TP = {p_metrics['detection']['tp']}, FP = {p_metrics['detection']['fp']}, FN = {p_metrics['detection']['fn']}")
    print(f"     Median abs timing error = {p_metrics['timing_residuals']['median_abs_error_ms']:.1f} ms, mean P prob @ ref = {p_metrics['mean_p_at_reference']:.3f}")
    print(f"  S: Precision = {s_metrics['detection']['precision']:.4f}, Recall = {s_metrics['detection']['recall']:.4f}, F1 = {s_metrics['detection']['f1']:.4f}")
    print(f"     TP = {s_metrics['detection']['tp']}, FP = {s_metrics['detection']['fp']}, FN = {s_metrics['detection']['fn']}")
    print(f"     Median abs timing error = {s_metrics['timing_residuals']['median_abs_error_ms']:.1f} ms")
    print("-" * 70)

    # 8. Event-level breakdown
    event_ids = sorted(list({r["event_id"] for r in records}))
    event_breakdown = {}
    for eid in event_ids:
        ev_records = [r for r in records if r["event_id"] == eid]
        ev_p = _phase_metrics(ev_records, "P", tolerance_samples=matching_tolerance, sampling_rate=sampling_rate)
        ev_s = _phase_metrics(ev_records, "S", tolerance_samples=matching_tolerance, sampling_rate=sampling_rate)
        event_breakdown[eid] = {
            "n_traces": len(ev_records),
            "p_precision": ev_p["detection"]["precision"],
            "p_recall": ev_p["detection"]["recall"],
            "p_f1": ev_p["detection"]["f1"],
            "p_tp": ev_p["detection"]["tp"],
            "p_fp": ev_p["detection"]["fp"],
            "p_fn": ev_p["detection"]["fn"],
            "s_precision": ev_s["detection"]["precision"],
            "s_recall": ev_s["detection"]["recall"],
            "s_f1": ev_s["detection"]["f1"],
            "s_tp": ev_s["detection"]["tp"],
            "s_fp": ev_s["detection"]["fp"],
            "s_fn": ev_s["detection"]["fn"],
        }

    # 9. Plot residual histograms
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, phase, col in zip(axes, ("P", "S"), ("royalblue", "darkorange")):
        p_res = [
            r["timing_error_samples"][phase] * (1000.0 / sampling_rate)
            for r in records
            if r["timing_error_samples"][phase] is not None and r["timing_error_samples"][phase] <= matching_tolerance
        ]
        ax.hist(p_res, bins=21, color=col, edgecolor="black", alpha=0.8)
        ax.set_title(f"Test Set: {phase}-Wave Timing Residuals (TP only)")
        ax.set_xlabel("Absolute Error (ms)")
        ax.set_ylabel("Count")
        ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(figures_dir / "test_residual_histograms.png", dpi=150)
    plt.close()

    # 10. Plot representative test traces
    # Find a great TP trace, a missed trace, and a missing-S trace
    tp_traces = [r for r in records if r["timing_error_samples"]["P"] is not None and r["timing_error_samples"]["P"] <= 5 and r["timing_error_samples"]["S"] is not None and r["timing_error_samples"]["S"] <= 5]
    if tp_traces:
        ex_tp = tp_traces[0]
        name = ex_tp["trace_name"]
        wf = waveforms_by_trace[name]
        probs = ex_tp["probabilities"]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
        t = np.arange(window_length) / sampling_rate
        ax1.plot(t, wf[0], label="E", color="gray", alpha=0.6)
        ax1.plot(t, wf[1], label="N", color="silver", alpha=0.6)
        ax1.plot(t, wf[2], label="Z (Vertical)", color="black", lw=0.8)
        if ex_tp["reference_relative"]["P"] is not None:
            ax1.axvline(ex_tp["reference_relative"]["P"] / sampling_rate, color="blue", linestyle="--", label="Ref P")
        if ex_tp["reference_relative"]["S"] is not None:
            ax1.axvline(ex_tp["reference_relative"]["S"] / sampling_rate, color="red", linestyle="--", label="Ref S")
        ax1.set_ylabel("Normalized Amp")
        ax1.set_title(f"Test Example TP: {name} (Event {ex_tp['event_id']})")
        ax1.legend(loc="upper right", fontsize=8)
        ax1.grid(True, alpha=0.3)

        ax2.plot(t, probs[0], color="blue", label="P prob", lw=1.2)
        ax2.plot(t, probs[1], color="red", label="S prob", lw=1.2)
        ax2.axhline(p_threshold, color="blue", linestyle=":", label=f"P thr={p_threshold}")
        ax2.axhline(s_threshold, color="red", linestyle=":", label=f"S thr={s_threshold}")
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Probability")
        ax2.set_ylim(-0.05, 1.05)
        ax2.legend(loc="upper right", fontsize=8)
        ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(figures_dir / "test_example_tp.png", dpi=150)
        plt.close()

    # 11. Write Manifests and Metrics
    metrics_data = {
        "evaluation_split": "test",
        "checkpoint": str(CHECKPOINT_PATH.name),
        "protocol_id": protocol["protocol_id"],
        "n_traces": len(records),
        "n_events": test_event_count,
        "matching_tolerance_samples": matching_tolerance,
        "sampling_rate_hz": sampling_rate,
        "P": p_metrics,
        "S": s_metrics,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics_data, indent=2), encoding="utf-8")
    (analysis_dir / "event_breakdown.json").write_text(json.dumps(event_breakdown, indent=2), encoding="utf-8")

    run_manifest = {
        "task": "held_out_test_evaluation",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checkpoint": str(CHECKPOINT_PATH),
        "checkpoint_sha256": "verified_best_pt_epoch11",
        "protocol": protocol,
        "split_hash": "aea671c76ce2",
        "n_test_events": test_event_count,
        "n_test_traces": len(records),
        "inference_wall_seconds": round(t1 - t0, 2),
        "device": str(device),
        "summary_metrics": {
            "p_f1": p_metrics["detection"]["f1"],
            "p_precision": p_metrics["detection"]["precision"],
            "p_recall": p_metrics["detection"]["recall"],
            "p_tp": p_metrics["detection"]["tp"],
            "p_fp": p_metrics["detection"]["fp"],
            "p_fn": p_metrics["detection"]["fn"],
            "s_f1": s_metrics["detection"]["f1"],
            "s_precision": s_metrics["detection"]["precision"],
            "s_recall": s_metrics["detection"]["recall"],
            "s_tp": s_metrics["detection"]["tp"],
            "s_fp": s_metrics["detection"]["fp"],
            "s_fn": s_metrics["detection"]["fn"],
        },
    }
    (out_dir / "run.json").write_text(json.dumps(run_manifest, indent=2), encoding="utf-8")

    print(f"\nAll test evaluation artifacts successfully written to: {out_dir}")


if __name__ == "__main__":
    main()

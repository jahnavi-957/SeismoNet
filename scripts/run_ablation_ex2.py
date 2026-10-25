"""Pre-registered Bounded sigma Ablation Runner (EX-2).

Implements docs/ABLATION_PROPOSAL_EX2.md:
- One varied factor: target_sigma_samples in {10, 20, 40} on the identical 16/8-event task.
- sigma=20, seed 42 is already run in runs/experiment_002_p_training/ and is reused.
- Runs:
    1. runs/ablation_sigma10_seed42/ (sigma=10, seed 42, 20 epochs)
    2. runs/ablation_sigma40_seed42/ (sigma=40, seed 42, 20 epochs)
    3. runs/ablation_sigma20_seed43/ (sigma=20, seed 43, 20 epochs, noise-floor arm)
- Evaluates against frozen protocol protocol-5fa5744aca58cc3c (P 0.05 / S 0.10 / tol 20).
- Compares effect size to seed-to-seed variability (|val_p_f1_seed42 - val_p_f1_seed43|).
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
import torch.nn as nn
import yaml

from seismonet.dataset import InstanceDataset, build_dataloader
from seismonet.losses import soft_cross_entropy_loss
from seismonet.metrics import classify_picks, residual_stats, residuals
from seismonet.model import SeismoUnet1d
from seismonet.picking import PeakPickingConfig
from seismonet.validation_inference import _records_for_picking_config, _phase_metrics

ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = ROOT / "runs" / "pilot_seed42" / "run.json"
PILOT_CONFIG_SN = ROOT / "runs" / "pilot_seed42" / "config_snapshot.yaml"
EXP002_DIR = ROOT / "runs" / "experiment_002_p_training"

MAX_EPOCHS = 20
BATCH_SIZE = 4
LR = 0.001
WEIGHT_DECAY = 0.0001
PURE_NOISE_FRACTION = 0.0


def _select_best(history: list[dict]) -> dict:
    def _key(entry):
        return (entry["val_p_f1"], -entry["val_loss"], entry["val_s_f1"], -entry["epoch"])
    return max(history, key=_key)


def run_single_arm(
    *,
    out_dir: Path,
    target_sigma: float,
    seed: int,
) -> dict[str, Any]:
    print("=" * 70)
    print(f"RUNNING ABLATION ARM: sigma={target_sigma}, seed={seed}")
    print(f"Output directory: {out_dir}")
    print("=" * 70)

    if out_dir.exists() and (out_dir / "run.json").exists():
        print(f"Arm already completed in {out_dir}; loading existing run.json")
        return json.loads((out_dir / "run.json").read_text(encoding="utf-8"))

    checkpoint_dir = out_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir = out_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    snap = yaml.safe_load(PILOT_CONFIG_SN.read_text(encoding="utf-8"))

    train_events = list(manifest["dataset"]["selected_train_events"])
    val_events = list(manifest["dataset"]["selected_validation_events"])
    hdf5_path = Path(manifest["dataset"]["hdf5"])
    metadata_csv = Path(manifest["dataset"]["metadata_csv"])
    window_length = int(snap["input_shape"][2])

    rows = list(csv.DictReader(metadata_csv.read_text(encoding="utf-8").splitlines()))
    train_rows = [r for r in rows if r["source_id"].strip() in set(train_events)]
    val_rows = [r for r in rows if r["source_id"].strip() in set(val_events)]
    train_trace_names = sorted(r["trace_name"] for r in train_rows)
    val_trace_names = sorted(r["trace_name"] for r in val_rows)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_ds = InstanceDataset(
        hdf5_path, metadata_csv,
        window_length=window_length, sigma=target_sigma, depth=4,
        training=True, seed=seed, trace_names=train_trace_names,
        pure_noise_fraction=PURE_NOISE_FRACTION,
    )
    val_ds = InstanceDataset(
        hdf5_path, metadata_csv,
        window_length=window_length, sigma=target_sigma, depth=4,
        training=False, seed=seed, trace_names=val_trace_names,
        pure_noise_fraction=0.0,
    )
    train_loader = build_dataloader(train_ds, batch_size=BATCH_SIZE, num_workers=0, seed=seed)
    val_loader = build_dataloader(val_ds, batch_size=BATCH_SIZE, num_workers=0, seed=seed)

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    model = SeismoUnet1d(base=16, depth=4).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    picking_config = PeakPickingConfig(
        p_threshold=0.05,
        s_threshold=0.10,
        min_peak_distance_samples=20,
        matching_tolerance_samples=20,
    )
    picking_config.validate()

    val_metadata_by_trace = {r["trace_name"]: r for r in val_rows}
    history: list[dict] = []
    start_wall = time.perf_counter()

    for epoch in range(1, MAX_EPOCHS + 1):
        t0 = time.perf_counter()
        model.train()
        train_losses = []
        for batch in train_loader:
            waveform = batch["waveform"].to(device=device, dtype=torch.float32)
            targets = batch["targets"].to(device=device, dtype=torch.float32)
            logits = model(waveform)
            loss = soft_cross_entropy_loss(logits, targets)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))
        train_loss = float(np.mean(train_losses))

        model.eval()
        val_losses = []
        val_pred_inputs = []
        with torch.no_grad():
            for batch in val_loader:
                waveform = batch["waveform"].to(device=device, dtype=torch.float32)
                targets = batch["targets"].to(device=device, dtype=torch.float32)
                logits = model(waveform)
                loss = soft_cross_entropy_loss(logits, targets)
                val_losses.append(float(loss.item()))
                probs = torch.softmax(logits, dim=1).cpu().numpy()
                for bi, trace_name in enumerate(batch["trace_name"]):
                    val_pred_inputs.append({
                        "metadata": val_metadata_by_trace[str(trace_name)],
                        "window_start": int(batch["window_start"][bi].item()),
                        "probabilities": probs[bi].copy(),
                    })
        val_loss = float(np.mean(val_losses))
        val_pred_inputs.sort(key=lambda x: x["metadata"]["trace_name"])

        records = _records_for_picking_config(
            val_pred_inputs, picking_config, window_length=window_length, sampling_rate=100.0
        )
        p_met = _phase_metrics(records, "P", tolerance_samples=20, sampling_rate=100.0)
        s_met = _phase_metrics(records, "S", tolerance_samples=20, sampling_rate=100.0)

        p_det = p_met["detection"]
        s_det = s_met["detection"]
        p_res = p_met["absolute_timing_error_samples"]
        s_res = s_met["absolute_timing_error_samples"]

        # p_at_ref
        p_probs_at_ref = []
        for r in records:
            p_rel = r["reference_relative"]["P"]
            if p_rel is not None and 0 <= p_rel < window_length:
                p_probs_at_ref.append(float(r["probabilities"][0, p_rel]))
        mean_p_at_ref = float(np.mean(p_probs_at_ref)) if p_probs_at_ref else None

        t1 = time.perf_counter()
        entry = {
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_p_precision": float(p_det["precision"]),
            "val_p_recall": float(p_det["recall"]),
            "val_p_f1": float(p_det["f1"]),
            "val_p_tp": int(p_det["tp"]),
            "val_p_fp": int(p_det["fp"]),
            "val_p_fn": int(p_det["fn"]),
            "val_s_precision": float(s_det["precision"]),
            "val_s_recall": float(s_det["recall"]),
            "val_s_f1": float(s_det["f1"]),
            "val_s_tp": int(s_det["tp"]),
            "val_s_fp": int(s_det["fp"]),
            "val_s_fn": int(s_det["fn"]),
            "val_p_residual_median_abs_samples": p_res.get("median"),
            "val_p_mean_prob_at_reference": mean_p_at_ref,
            "epoch_wall_seconds": round(t1 - t0, 2),
        }
        history.append(entry)

        # Save checkpoint per epoch
        ckpt_path = checkpoint_dir / f"epoch_{epoch:03d}.pt"
        torch.save(model.state_dict(), ckpt_path)

        if epoch % 5 == 0 or epoch == MAX_EPOCHS:
            print(f"  Epoch {epoch:2d}/{MAX_EPOCHS}: val_loss={val_loss:.4f}  val_P_F1={entry['val_p_f1']:.4f}  val_S_F1={entry['val_s_f1']:.4f} ({t1-t0:.1f}s)")

    best = _select_best(history)
    print(f"Best epoch: {best['epoch']} (val_P_F1={best['val_p_f1']:.4f}, val_S_F1={best['val_s_f1']:.4f}, val_loss={best['val_loss']:.4f})")

    # Save best.pt
    best_ckpt = checkpoint_dir / f"epoch_{best['epoch']:03d}.pt"
    (out_dir / "best.pt").write_bytes(best_ckpt.read_bytes())

    wall_total = round(time.perf_counter() - start_wall, 2)
    arm_summary = {
        "target_sigma": target_sigma,
        "seed": seed,
        "best_epoch": best["epoch"],
        "val_loss": best["val_loss"],
        "val_p_f1": best["val_p_f1"],
        "val_p_precision": best["val_p_precision"],
        "val_p_recall": best["val_p_recall"],
        "val_p_tp": best["val_p_tp"],
        "val_p_fp": best["val_p_fp"],
        "val_p_fn": best["val_p_fn"],
        "val_s_f1": best["val_s_f1"],
        "val_s_precision": best["val_s_precision"],
        "val_s_recall": best["val_s_recall"],
        "val_s_tp": best["val_s_tp"],
        "val_s_fp": best["val_s_fp"],
        "val_s_fn": best["val_s_fn"],
        "val_p_residual_median_abs_samples": best["val_p_residual_median_abs_samples"],
        "val_p_mean_prob_at_reference": best["val_p_mean_prob_at_reference"],
        "total_wall_seconds": wall_total,
        "history": history,
    }
    (out_dir / "run.json").write_text(json.dumps(arm_summary, indent=2), encoding="utf-8")
    return arm_summary


def main():
    print("=" * 70)
    print("SEISMONET: PRE-REGISTERED BIASED SIGMA ABLATION (EX-2)")
    print("=" * 70)

    # Arm 2 is Experiment 002 (sigma=20, seed 42)
    exp002_run = json.loads((EXP002_DIR / "run.json").read_text(encoding="utf-8"))
    exp002_best = exp002_run["best_metrics"]
    arm_sigma20_seed42 = {
        "target_sigma": 20.0,
        "seed": 42,
        "best_epoch": exp002_best["epoch"],
        "val_loss": exp002_best["val_loss"],
        "val_p_f1": exp002_best["val_p_f1"],
        "val_p_precision": exp002_best["val_p_precision"],
        "val_p_recall": exp002_best["val_p_recall"],
        "val_p_tp": exp002_best["val_p_tp"],
        "val_p_fp": exp002_best["val_p_fp"],
        "val_p_fn": exp002_best["val_p_fn"],
        "val_s_f1": exp002_best["val_s_f1"],
        "val_s_precision": exp002_best["val_s_precision"],
        "val_s_recall": exp002_best["val_s_recall"],
        "val_s_tp": exp002_best["val_s_tp"],
        "val_s_fp": exp002_best["val_s_fp"],
        "val_s_fn": exp002_best["val_s_fn"],
        "val_p_residual_median_abs_samples": exp002_best.get("p_median_abs_residual_samples"),
        "val_p_mean_prob_at_reference": exp002_best.get("p_at_ref_mean"),
    }

    # Arm 1: sigma=10, seed 42
    arm_sigma10 = run_single_arm(
        out_dir=ROOT / "runs" / "ablation_sigma10_seed42",
        target_sigma=10.0,
        seed=42,
    )

    # Arm 3: sigma=40, seed 42
    arm_sigma40 = run_single_arm(
        out_dir=ROOT / "runs" / "ablation_sigma40_seed42",
        target_sigma=40.0,
        seed=42,
    )

    # Arm 4: sigma=20, seed 43 (Noise floor)
    arm_sigma20_seed43 = run_single_arm(
        out_dir=ROOT / "runs" / "ablation_sigma20_seed43",
        target_sigma=20.0,
        seed=43,
    )

    # Calculate noise floor
    seed_spread_p = abs(arm_sigma20_seed42["val_p_f1"] - arm_sigma20_seed43["val_p_f1"])
    seed_spread_s = abs(arm_sigma20_seed42["val_s_f1"] - arm_sigma20_seed43["val_s_f1"])

    print("\n" + "=" * 70)
    print("ABLATION EX-2 RESULTS TABLE:")
    print("=" * 70)
    print(f"{'Arm':<22} | {'val_loss':<8} | {'P F1':<7} | {'P Prec':<7} | {'P Rec':<7} | {'P TP/FP/FN':<12} | {'S F1':<7} | {'Med |err|':<10}")
    print("-" * 95)
    for name, arm in [
        ("sigma=10 (seed 42)", arm_sigma10),
        ("sigma=20 (seed 42, ref)", arm_sigma20_seed42),
        ("sigma=40 (seed 42)", arm_sigma40),
        ("sigma=20 (seed 43, noise)", arm_sigma20_seed43),
    ]:
        p_counts = f"{arm['val_p_tp']}/{arm['val_p_fp']}/{arm['val_p_fn']}"
        med_err = f"{arm['val_p_residual_median_abs_samples']} s" if arm['val_p_residual_median_abs_samples'] is not None else "N/A"
        print(f"{name:<22} | {arm['val_loss']:<8.4f} | {arm['val_p_f1']:<7.4f} | {arm['val_p_precision']:<7.4f} | {arm['val_p_recall']:<7.4f} | {p_counts:<12} | {arm['val_s_f1']:<7.4f} | {med_err:<10}")

    print("\nNoise Floor Analysis:")
    print(f"  Seed-to-seed variability for sigma=20 (|seed 42 - seed 43|): P spread = {seed_spread_p:.4f}, S spread = {seed_spread_s:.4f}")
    
    diff_10 = arm_sigma10["val_p_f1"] - arm_sigma20_seed42["val_p_f1"]
    diff_40 = arm_sigma40["val_p_f1"] - arm_sigma20_seed42["val_p_f1"]
    print(f"  sigma=10 vs sigma=20: delta P F1 = {diff_10:+.4f} (spread = {seed_spread_p:.4f}) -> {'EXCEEDS NOISE' if abs(diff_10) > seed_spread_p else 'WITHIN NOISE FLOOR'}")
    print(f"  sigma=40 vs sigma=20: delta P F1 = {diff_40:+.4f} (spread = {seed_spread_p:.4f}) -> {'EXCEEDS NOISE' if abs(diff_40) > seed_spread_p else 'WITHIN NOISE FLOOR'}")

    summary_file = ROOT / "runs" / "ablation_ex2_summary.json"
    summary_data = {
        "protocol": "protocol-5fa5744aca58cc3c",
        "seed_spread_p_f1": seed_spread_p,
        "seed_spread_s_f1": seed_spread_s,
        "arms": {
            "sigma10_seed42": arm_sigma10,
            "sigma20_seed42": arm_sigma20_seed42,
            "sigma40_seed42": arm_sigma40,
            "sigma20_seed43": arm_sigma20_seed43,
        },
        "conclusion": {
            "h1_supported": bool(diff_10 > seed_spread_p),
            "h2_supported": bool(diff_40 > seed_spread_p),
            "h3_supported": bool(abs(diff_10) <= seed_spread_p and abs(diff_40) <= seed_spread_p),
        }
    }
    summary_file.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    print(f"\nAblation summary saved to: {summary_file}")


if __name__ == "__main__":
    main()

"""Experiment 002: 20-epoch P-wave training on the frozen pilot subsets (no test).

Safety: uses only the 16 train / 8 val events recorded in runs/pilot_seed42/run.json.
Selection rule declared before training: best epoch = argmax val P F1;
tie -> min val loss; tie -> max val S F1; tie -> smallest epoch index.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import yaml
from torch.utils.data import DataLoader

from seismonet.dataset import InstanceDataset, build_dataloader
from seismonet.losses import soft_cross_entropy_loss
from seismonet.metrics import classify_picks, residual_stats, residuals
from seismonet.model import SeismoUnet1d
from seismonet.picking import PeakPickingConfig
from seismonet.validation_inference import (
    _records_for_picking_config,
    _phase_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = ROOT / "runs" / "pilot_seed42" / "run.json"
PILOT_CONFIG_SN = ROOT / "runs" / "pilot_seed42" / "config_snapshot.yaml"
OUT_DIR = ROOT / "runs" / "experiment_002_p_training"
CHECKPOINT_DIR = OUT_DIR / "checkpoints"

MAX_EPOCHS = 20
BATCH_SIZE = 4
SEED = 42
LR = 0.001
WEIGHT_DECAY = 0.0001
TARGET_SIGMA = 20.0
PURE_NOISE_FRACTION = 0.0


def _device_info():
    info = {
        "torch_version": torch.__version__,
        "cuda_version": str(torch.version.cuda) if torch.version.cuda else None,
        "cuda_available": bool(torch.cuda.is_available()),
        "device": "cuda" if torch.cuda.is_available() else "cpu",
    }
    if torch.cuda.is_available():
        try:
            name = torch.cuda.get_device_name(0)
            info["gpu_name"] = name
            info["gpu_total_memory_mib"] = float(
                torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
            )
        except Exception:
            info["gpu_name"] = None
    return info


def _select_best(history):
    """Deterministic best-epoch rule declared before training."""
    def _key(entry):
        # higher P F1 is better -> negation not needed if we use max with tuple
        return (entry["val_p_f1"], -entry["val_loss"], entry["val_s_f1"], -entry["epoch"])
    return max(history, key=_key)


def main() -> None:
    if OUT_DIR.exists():
        raise FileExistsError(f"refusing to overwrite existing {OUT_DIR}; remove or rename first")
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    snap = yaml.safe_load(PILOT_CONFIG_SN.read_text(encoding="utf-8"))

    # Confirm subsets
    train_events = list(manifest["dataset"]["selected_train_events"])
    val_events = list(manifest["dataset"]["selected_validation_events"])
    assert len(train_events) == 16 and len(val_events) == 8
    assert int(manifest["dataset"]["selected_train_trace_count"]) == 492
    assert int(manifest["dataset"]["selected_validation_trace_count"]) == 210

    hdf5_path = Path(manifest["dataset"]["hdf5"])
    metadata_csv = Path(manifest["dataset"]["metadata_csv"])
    assert hdf5_path.exists() and metadata_csv.exists(), "sample dataset not found at manifest paths"

    window_length = int(snap["input_shape"][2])
    assert window_length == 3072
    assert float(snap["target_sigma_samples"]) == TARGET_SIGMA

    # Validation membership guard — never open test.
    val_split_path = Path(manifest["split_files"]["validation"]["path"])
    val_split_events = {r["event_id"].strip() for r in csv.DictReader(val_split_path.read_text(encoding="utf-8").splitlines())}
    assert set(val_events) <= val_split_events

    # Build trace sets deterministically
    rows = list(csv.DictReader(metadata_csv.read_text(encoding="utf-8").splitlines()))
    train_rows = [r for r in rows if r["source_id"].strip() in set(train_events)]
    val_rows = [r for r in rows if r["source_id"].strip() in set(val_events)]
    assert len(train_rows) == 492 and len(val_rows) == 210
    # exact trace_names from manifest ordering is not stored; use all traces of those events
    train_trace_names = sorted(r["trace_name"] for r in train_rows)
    val_trace_names = sorted(r["trace_name"] for r in val_rows)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}  batch={BATCH_SIZE}  epochs={MAX_EPOCHS}  sigma={TARGET_SIGMA}")

    # Datasets: training with random windows, val deterministic
    sampling_rate = 100.0  # SR-003, same as pilot
    train_ds = InstanceDataset(
        hdf5_path, metadata_csv,
        window_length=window_length, sigma=TARGET_SIGMA, depth=4,
        training=True, seed=SEED, trace_names=train_trace_names,
        pure_noise_fraction=PURE_NOISE_FRACTION,
    )
    val_ds = InstanceDataset(
        hdf5_path, metadata_csv,
        window_length=window_length, sigma=TARGET_SIGMA, depth=4,
        training=False, seed=SEED, trace_names=val_trace_names,
        pure_noise_fraction=0.0,
    )
    train_loader = build_dataloader(train_ds, batch_size=BATCH_SIZE, num_workers=0, seed=SEED)
    val_loader = build_dataloader(val_ds, batch_size=BATCH_SIZE, num_workers=0, seed=SEED)

    model = SeismoUnet1d(base=16, depth=4).to(device)
    # Reproducible init
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)

    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    # Frozen picking protocol for the MAIN comparison (never changes epoch-to-epoch)
    picking_config = PeakPickingConfig(
        p_threshold=0.05,
        s_threshold=0.10,
        min_peak_distance_samples=20,
        matching_tolerance_samples=20,
    )
    picking_config.validate()

    # Metadata lookup for validation inference (val_ds is deterministic, same windows every epoch)
    val_metadata_by_trace = {r["trace_name"]: r for r in val_rows}

    history: list[dict] = []
    best_val_p_f1: float | None = None
    start_wall = time.perf_counter()

    for epoch in range(1, MAX_EPOCHS + 1):
        epoch_t0 = time.perf_counter()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats(device)

        model.train()
        train_losses: list[float] = []
        for batch in train_loader:
            waveform = batch["waveform"].to(device=device, dtype=torch.float32)
            targets = batch["targets"].to(device=device, dtype=torch.float32)
            logits = model(waveform)
            loss = soft_cross_entropy_loss(logits, targets)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite train loss at epoch {epoch}")
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))

        train_loss = float(sum(train_losses) / max(1, len(train_losses)))

        # Validation pass: loss + picking metrics + prob diagnostics
        model.eval()
        val_losses: list[float] = []
        val_pred_inputs: list[dict] = []
        # For prob-at-reference stats (pick the single peak per trace, no grouping)
        with torch.no_grad():
            for batch in val_loader:
                waveform = batch["waveform"].to(device=device, dtype=torch.float32)
                targets = batch["targets"].to(device=device, dtype=torch.float32)
                logits = model(waveform)
                loss = soft_cross_entropy_loss(logits, targets)
                if not torch.isfinite(loss):
                    raise RuntimeError(f"non-finite val loss at epoch {epoch}")
                val_losses.append(float(loss.item()))
                probs = torch.softmax(logits, dim=1).cpu().numpy()
                for bi, trace_name in enumerate(batch["trace_name"]):
                    trace_name = str(trace_name)
                    val_pred_inputs.append({
                        "metadata": val_metadata_by_trace[trace_name],
                        "window_start": int(batch["window_start"][bi].item()),
                        "probabilities": probs[bi].copy(),
                    })

        val_loss = float(sum(val_losses) / max(1, len(val_losses)))
        # Record metrics under the frozen protocol
        val_pred_inputs.sort(key=lambda x: x["metadata"]["trace_name"])

        # Single frozen picking config for comparison
        records = _records_for_picking_config(
            val_pred_inputs, picking_config, window_length=window_length, sampling_rate=sampling_rate
        )
        p_metrics = _phase_metrics(records, "P", tolerance_samples=20, sampling_rate=sampling_rate)
        s_metrics = _phase_metrics(records, "S", tolerance_samples=20, sampling_rate=sampling_rate)

        # Prob diagnostics (no threshold-dependent): mean P prob at reference where in-window
        # Use the model's raw probabilities per window.
        # For p_at_ref: use probs[0] at p_win if both present in window
        p_at_refs: list[float] = []
        s_at_refs: list[float] = []
        residual_p: list[float] = []
        for idx, entry in enumerate(val_pred_inputs):
            # find records[idx] after sort? Use sorted order — rebuild lookup by trace
            pass  # computed below via records loop

        # Align records with val_pred_inputs by trace order (already sorted)
        # records are in same sorted order as val_pred_inputs
        assert len(records) == len(val_pred_inputs)
        for rec in records:
            # p_at_ref comes from val_pred_inputs probability at p_win if in-window
            # rec["reference_status"]["P"] and rec["predicted_probability"] not relevant
            # pull from the raw probs via the rec's window-relative reference
            for phase in ("P", "S"):
                pass

        # Simpler: compute from val_pred_inputs directly
        for pi in val_pred_inputs:
            probs = pi["probabilities"]
            meta = pi["metadata"]
            w_start = int(pi["window_start"])
            for phase in ("P", "S"):
                key = f"trace_{phase}_arrival_sample"
                raw = meta.get(key, "").strip()
                if not raw:
                    continue
                abs_pick = int(float(raw))
                rel = abs_pick - w_start
                if 0 <= rel < window_length:
                    ch = 0 if phase == "P" else 1
                    if phase == "P":
                        p_at_refs.append(float(probs[ch][rel]))
                    else:
                        s_at_refs.append(float(probs[ch][rel]))

        p_at_ref_mean = float(sum(p_at_refs) / len(p_at_refs)) if p_at_refs else None
        s_at_ref_mean = float(sum(s_at_refs) / len(s_at_refs)) if s_at_refs else None

        # P argmax residual in samples (signed vs abs)
        p_resids_abs = [
            int(rec["timing_error_samples"]["P"])
            for rec in records
            if rec["timing_error_samples"]["P"] is not None
        ]
        p_signed = [
            float(rec["predicted_absolute"]["P"]) - float(rec["reference_absolute"]["P"])
            for rec in records
            if rec["reference_status"]["P"] == "in_window" and rec["predicted_absolute"]["P"] is not None
        ]
        p_signed_median = float(sorted(p_signed)[len(p_signed)//2]) if p_signed else None
        p_signed_mean = float(sum(p_signed)/len(p_signed)) if p_signed else None

        peak_alloc = peak_reserved = None
        if torch.cuda.is_available():
            peak_alloc = float(torch.cuda.max_memory_allocated(device)) / (1024 * 1024)
            peak_reserved = float(torch.cuda.max_memory_reserved(device)) / (1024 * 1024)

        entry = {
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_p_precision": float(p_metrics["detection"]["precision"]),
            "val_p_recall": float(p_metrics["detection"]["recall"]),
            "val_p_f1": float(p_metrics["detection"]["f1"]),
            "val_p_tp": int(p_metrics["detection"]["tp"]),
            "val_p_fp": int(p_metrics["detection"]["fp"]),
            "val_p_fn": int(p_metrics["detection"]["fn"]),
            "val_s_precision": float(s_metrics["detection"]["precision"]),
            "val_s_recall": float(s_metrics["detection"]["recall"]),
            "val_s_f1": float(s_metrics["detection"]["f1"]),
            "val_s_tp": int(s_metrics["detection"]["tp"]),
            "val_s_fp": int(s_metrics["detection"]["fp"]),
            "val_s_fn": int(s_metrics["detection"]["fn"]),
            "p_at_ref_mean": p_at_ref_mean,
            "s_at_ref_mean": s_at_ref_mean,
            "p_argmax_median_residual_samples": p_signed_median,
            "p_argmax_mean_residual_samples": p_signed_mean,
            "val_valid_pairs_p": int(p_metrics["n_valid_timing_pairs"]),
            "val_valid_pairs_s": int(s_metrics["n_valid_timing_pairs"]),
            "peak_allocated_mib": peak_alloc,
            "peak_reserved_mib": peak_reserved,
            "duration_seconds": float(time.perf_counter() - epoch_t0),
        }
        if p_resids_abs:
            entry["p_median_abs_residual_samples"] = float(sorted(p_resids_abs)[len(p_resids_abs)//2])
            entry["p_mean_abs_residual_samples"] = float(sum(p_resids_abs)/len(p_resids_abs))

        history.append(entry)
        print(
            f"epoch {epoch:2d}  train {train_loss:.4f}  val {val_loss:.4f}  "
            f"P F1 {entry['val_p_f1']:.4f} (P {entry['val_p_tp']}/{entry['val_p_tp']+entry['val_p_fp']+1e-9:.0f})  "
            f"S F1 {entry['val_s_f1']:.4f}"
        )

        # Save checkpoint every epoch
        ckpt = CHECKPOINT_DIR / f"checkpoint_epoch_{epoch:02d}.pt"
        torch.save(model.state_dict(), ckpt)

        # Early-stop guards
        if val_loss != val_loss or entry["val_p_f1"] != entry["val_p_f1"]:
            raise RuntimeError("non-finite val metrics")

    total_seconds = float(time.perf_counter() - start_wall)
    best = _select_best(history)
    best_epoch = int(best["epoch"])
    best_ckpt = CHECKPOINT_DIR / f"checkpoint_epoch_{best_epoch:02d}.pt"

    # Copy best to best.pt (weights-only)
    best_state = torch.load(str(best_ckpt), map_location="cpu", weights_only=True)
    torch.save(best_state, OUT_DIR / "best.pt")

    run_record = {
        "experiment_id": "experiment_002_p_training",
        "pilot_manifest": str(PILOT_MANIFEST),
        "pilot_config_snapshot": str(PILOT_CONFIG_SN),
        "new_output_dir": str(OUT_DIR),
        "model": {"name": "SeismoUnet1d", "base": 16, "depth": 4, "parameters": 678707},
        "input_shape": ["batch", 3, 3072],
        "optimizer": {"name": "Adam", "learning_rate": LR, "weight_decay": WEIGHT_DECAY},
        "seed": SEED,
        "epochs_requested": MAX_EPOCHS,
        "batch_size": BATCH_SIZE,
        "target_sigma_samples": TARGET_SIGMA,
        "target_sigma_status": "provisional",
        "pure_noise_fraction": PURE_NOISE_FRACTION,
        "split_files": json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))["split_files"],
        "dataset": json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))["dataset"],
        "device": _device_info(),
        "history": history,
        "selection_rule": {
            "primary": "max val P F1",
            "tie_break": ["min val loss", "max val S F1", "smallest epoch index"],
            "description": "best epoch = argmax P F1; tie -> argmin val loss; tie -> argmax S F1; tie -> earliest epoch",
        },
        "best_epoch": best_epoch,
        "best_metrics": best,
        "best_checkpoint": str(OUT_DIR / "best.pt"),
        "per_epoch_checkpoints_dir": str(CHECKPOINT_DIR),
        "total_seconds": total_seconds,
        "test_split_loaded": False,
        "test_split_used": False,
        "picking_protocol": {
            "protocol_id": "protocol-5fa5744aca58cc3c",
            "note": "frozen protocol reused unchanged for the main comparison",
            "p_threshold": float(picking_config.p_threshold),
            "s_threshold": float(picking_config.s_threshold),
            "min_peak_distance_samples": int(picking_config.min_peak_distance_samples),
            "matching_tolerance_samples": int(picking_config.matching_tolerance_samples),
        },
        "exploratory_thresholds_note": "any non-frozen threshold grid, if run, must be written to a separately labelled output and not used for the reported comparison",
    }

    (OUT_DIR / "run.json").write_text(json.dumps(run_record, indent=2) + "\n", encoding="utf-8")
    # Also dump config snapshot
    import shutil
    shutil.copy(PILOT_CONFIG_SN, OUT_DIR / "config_snapshot.yaml")

    # Loss + F1 figure
    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    epochs_x = [h["epoch"] for h in history]
    axes[0].plot(epochs_x, [h["train_loss"] for h in history], label="train loss", color="#1769aa")
    axes[0].plot(epochs_x, [h["val_loss"] for h in history], label="val loss", color="#c2410c")
    axes[0].set_ylabel("loss")
    axes[0].legend()
    axes[0].grid(True, alpha=0.2)
    axes[0].set_title(f"experiment_002_p_training — best epoch {best_epoch} by max val P F1")
    axes[1].plot(epochs_x, [h["val_p_f1"] for h in history], label="P F1", color="#1769aa", marker="o")
    axes[1].plot(epochs_x, [h["val_s_f1"] for h in history], label="S F1", color="#c2410c", marker="x")
    axes[1].set_xlabel("epoch")
    axes[1].set_ylabel("F1")
    axes[1].legend()
    axes[1].grid(True, alpha=0.2)
    if max(h["val_p_f1"] for h in history) > 0.01:
        axes[1].set_ylim(-0.05, 1.05)
    else:
        axes[1].set_ylim(-0.02, 0.15)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "loss_and_f1.png", dpi=160)
    plt.close(fig)

    print(f"done. best epoch {best_epoch}  P F1 {best['val_p_f1']:.4f}  S F1 {best['val_s_f1']:.4f}  val_loss {best['val_loss']:.4f}")
    print(f"artifacts in {OUT_DIR}")


if __name__ == "__main__":
    main()

"""Minimal local demo — frozen model + permitted validation example + probability view.

Scope:
  - uses ONLY the existing 210-trace validation subset (never test)
  - loads the frozen experiment_002 checkpoint best.pt (epoch 11)
  - loads the frozen protocol thresholds/tolerance (protocol-5fa5744aca58cc3c)
  - runs a single deterministic example (or a chosen trace_name/index)
  - displays P/S probability curves and predicted vs reference arrivals
  - outputs a PNG under runs/demo/ and prints exact metrics for that trace

Usage:
  python scripts/demo_validation.py                         # default example (first val trace)
  python scripts/demo_validation.py --trace 11210661.IV.FDMO..HH
  python scripts/demo_validation.py --index 5
  python scripts/demo_validation.py --out runs/demo/demo_11210661_IV_FDMO__HH.png
  python scripts/demo_validation.py --list                  # list all available validation traces

No dashboard, no web framework, no DB. Validation subset only; test split never loaded.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import yaml

from seismonet.dataset import InstanceDataset
from seismonet.model import SeismoUnet1d
from seismonet.picking import PeakPickingConfig, pick_phase_diagnostics

ROOT = Path(__file__).resolve().parents[1]
PILOT_RUN = ROOT / "runs" / "pilot_seed42" / "run.json"
EXP_DIR = ROOT / "runs" / "experiment_002_p_training"
CHECKPOINT = EXP_DIR / "best.pt"            # frozen reference (epoch 11)
PROTOCOL_PATH = ROOT / "runs" / "validation_protocol_candidate_seed42" / "protocol.json"

OUT_DEFAULT_DIR = ROOT / "runs" / "demo"


def _load_split_trace_names() -> tuple[set[str], set[str]]:
    pilot = json.loads(PILOT_RUN.read_text(encoding="utf-8"))
    val_ids = set(pilot["dataset"]["selected_validation_events"])
    test_ids = {r["event_id"].strip() for r in csv.DictReader(open(pilot["split_files"]["test"]["path"], encoding="utf-8"))}
    return val_ids, test_ids


def _pick_demo_trace(trace_arg: str | None, index_arg: int | None, val_rows_sorted: list[dict]) -> dict:
    if trace_arg is not None:
        cand = [r for r in val_rows_sorted if r["trace_name"] == trace_arg]
        if not cand:
            raise SystemExit(f"trace {trace_arg!r} not in the permitted validation subset (test not allowed)")
        return cand[0]
    if index_arg is not None:
        if not 0 <= index_arg < len(val_rows_sorted):
            raise SystemExit(f"--index {index_arg} out of [0,{len(val_rows_sorted)})")
        return val_rows_sorted[index_arg]
    return val_rows_sorted[0]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Minimal validation-only demo (frozen checkpoint, frozen protocol)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/demo_validation.py                           # first validation trace
  python scripts/demo_validation.py --index 5                 # 6th trace in sorted val list
  python scripts/demo_validation.py --trace 11210661.IV.FDMO..HH
  python scripts/demo_validation.py --out runs/demo/demo_FDMO.png
  python scripts/demo_validation.py --list                    # show all 210 validation traces
"""
    )
    ap.add_argument("--trace", type=str, default=None, help="exact trace_name inside the validation subset")
    ap.add_argument("--index", type=int, default=None, help="index inside the sorted validation subset (0-based)")
    ap.add_argument("--out", type=Path, default=None, help="output PNG path (default runs/demo/demo_<trace>.png)")
    ap.add_argument("--list", action="store_true", help="list all available validation traces and exit")
    args = ap.parse_args()

    if not CHECKPOINT.exists():
        raise SystemExit(f"checkpoint not found: {CHECKPOINT}")
    if not PROTOCOL_PATH.exists():
        raise SystemExit(f"protocol not found: {PROTOCOL_PATH}")

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    p_thr = float(protocol["picking"]["p_threshold"])
    s_thr = float(protocol["picking"]["s_threshold"])
    min_dist = int(protocol["picking"]["min_peak_distance_samples"])
    tol = int(protocol["picking"]["matching_tolerance_samples"])

    pilot = json.loads(PILOT_RUN.read_text(encoding="utf-8"))
    snap = yaml.safe_load((ROOT / "runs" / "pilot_seed42" / "config_snapshot.yaml").read_text(encoding="utf-8"))
    window_length = int(snap["input_shape"][2])

    hdf5_path = Path(pilot["dataset"]["hdf5"])
    metadata_csv = Path(pilot["dataset"]["metadata_csv"])
    val_events = set(pilot["dataset"]["selected_validation_events"])
    val_ids, test_ids = _load_split_trace_names()
    if val_events & test_ids:
        raise SystemExit("val/test event overlap detected — aborting demo")

    rows = list(csv.DictReader(open(metadata_csv, encoding="utf-8")))
    val_rows_sorted = sorted([r for r in rows if r.get("source_id", "").strip() in val_events], key=lambda r: r["trace_name"])

    if args.list:
        print(f"Available validation traces ({len(val_rows_sorted)}):")
        for i, r in enumerate(val_rows_sorted):
            p_abs = r.get("trace_P_arrival_sample", "").strip()
            s_abs = r.get("trace_S_arrival_sample", "").strip()
            p_str = f"P={p_abs}" if p_abs else "P=missing"
            s_str = f"S={s_abs}" if s_abs else "S=missing"
            print(f"  [{i:3d}] {r['trace_name']}  event={r.get('source_id','')}  {p_str}  {s_str}")
        return

    demo_meta = _pick_demo_trace(args.trace, args.index, val_rows_sorted)
    demo_trace = demo_meta["trace_name"]

    # Guard: demo trace must be in val, never test
    if demo_trace in {r["trace_name"] for r in rows if r.get("source_id", "").strip() in test_ids}:
        raise SystemExit("refusing to load a test trace for the demo")

    ds = InstanceDataset(
        Path(pilot["dataset"]["hdf5"]),
        Path(pilot["dataset"]["metadata_csv"]),
        window_length=window_length,
        sigma=20.0,
        depth=4,
        training=False,
        seed=42,
        trace_names=[demo_trace],
        pure_noise_fraction=0.0,
    )
    sample = ds[0]
    waveform = sample["waveform"].numpy()  # (3, 3072)
    w_start = int(sample["window_start"])

    device = torch.device("cpu")
    model = SeismoUnet1d(base=16, depth=4).to(device)
    state = torch.load(CHECKPOINT, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.eval()

    with torch.no_grad():
        logits = model(torch.from_numpy(waveform).unsqueeze(0).float().to(device))
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]  # (3, L)

    # Reference window-relative
    def _abs_raw(key: str) -> int | None:
        v = demo_meta.get(key, "").strip()
        return int(float(v)) if v else None

    p_abs = _abs_raw("trace_P_arrival_sample")
    s_abs = _abs_raw("trace_S_arrival_sample")
    p_win = (p_abs - w_start) if p_abs is not None and 0 <= p_abs - w_start < window_length else None
    s_win = (s_abs - w_start) if s_abs is not None and 0 <= s_abs - w_start < window_length else None

    cfg = PeakPickingConfig(
        p_threshold=p_thr,
        s_threshold=s_thr,
        min_peak_distance_samples=min_dist,
        matching_tolerance_samples=tol,
    )
    p_diag = pick_phase_diagnostics(probs[0], threshold=cfg.p_threshold, min_peak_distance_samples=cfg.min_peak_distance_samples)
    s_diag = pick_phase_diagnostics(probs[1], threshold=cfg.s_threshold, min_peak_distance_samples=cfg.min_peak_distance_samples)

    pred_p_win = p_diag.pick.index if p_diag.pick else None
    pred_s_win = s_diag.pick.index if s_diag.pick else None
    pred_p_abs = w_start + pred_p_win if pred_p_win is not None else None
    pred_s_abs = w_start + pred_s_win if pred_s_win is not None else None

    # Small deterministic report for this trace
    print(f"Demo trace: {demo_trace}  event {demo_meta.get('source_id','')}")
    print(f"Window: [{w_start}, {w_start+window_length})  protocol {protocol.get('protocol_id','?')}")
    print(f"Reference P_abs={p_abs} (win {p_win})  S_abs={s_abs} (win {s_win})")
    print(f"Predicted P win {pred_p_win} abs {pred_p_abs} prob {p_diag.pick.probability if p_diag.pick else None}")
    print(f"Predicted S win {pred_s_win} abs {pred_s_abs} prob {s_diag.pick.probability if s_diag.pick else None}")
    if p_win is not None and pred_p_win is not None:
        print(f"P residual: {pred_p_abs - p_abs} samples ({(pred_p_abs - p_abs)*1000/100:.0f} ms)  {'TP' if abs(pred_p_abs-p_abs)<=tol else 'FP (out of tol)'}")
    if s_win is not None and pred_s_win is not None:
        print(f"S residual: {pred_s_abs - s_abs} samples ({(pred_s_abs - s_abs)*1000/100:.0f} ms)  {'TP' if abs(pred_s_abs-s_abs)<=tol else 'FP (out of tol)'}")
    print("Note: demo uses the small 10k-sample validation subset; not a generalisation claim. Test split not loaded.")

    # Plot
    out = args.out if args.out is not None else (OUT_DEFAULT_DIR / f"demo_{demo_trace.replace('.', '_')}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    x = np.arange(window_length) + w_start
    fig, axes = plt.subplots(4, 1, figsize=(12, 9), sharex=True, dpi=140)
    comp_names = ("component 0 (ENZ file order)", "component 1", "component 2")
    for ch, (ax, name) in enumerate(zip(axes[:3], comp_names)):
        ax.plot(x, waveform[ch], color="#30343b", lw=0.6)
        ax.set_ylabel(name, fontsize=8)
        ax.grid(True, alpha=0.2)
        if ch == 0:
            ax.set_title(f"Demo — {demo_trace} | window [{w_start},{w_start+window_length}) | frozen {protocol.get('protocol_id','')}", loc="left", fontsize=10)
        for phase, color, awin in (("P", "#1769aa", p_win), ("S", "#c2410c", s_win)):
            if awin is not None and 0 <= awin < window_length:
                axes[ch].axvline(awin + w_start, color=color, ls="--", lw=1, alpha=0.85)
        if pred_p_win is not None:
            ax.axvline(pred_p_abs, color="#1769aa", ls="-", lw=0.9, alpha=0.85)
        if pred_s_win is not None:
            ax.axvline(pred_s_abs, color="#c2410c", ls="-", lw=0.9, alpha=0.85)
    pax = axes[3]
    for thr, col, lbl in ((p_thr, "#1769aa", "P thr"), (s_thr, "#c2410c", "S thr")):
        pax.axhline(thr, color=col, ls=":", lw=1.1, alpha=0.9, label=f"{lbl} {thr:g}")
    pax.plot(x, probs[0], color="#1769aa", label="P prob")
    pax.plot(x, probs[1], color="#c2410c", label="S prob")
    pax.plot(x, probs[2], color="#5b6470", label="noise")
    pax.set_ylim(-0.02, 1.02)
    pax.grid(True, alpha=0.2)
    pax.legend(fontsize=8, ncol=3, loc="upper right")
    pax.set_xlabel("original trace sample index")
    pax.set_ylabel("probability")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"Figure written: {out}")


if __name__ == "__main__":
    main()

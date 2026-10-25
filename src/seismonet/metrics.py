"""Evaluation metrics — PRD FR-055..FR-059, NFR-002/NFR-014; no training or I/O.

Residuals and tolerance-bounded precision/recall/F1 for P and S separately (FR-060).
A pick is TP iff |pred - ref| <= tolerance; matching is one-to-one per window.
FR-062: zero denominators return defined values with denominators reported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class ResidualStats:
    n: int
    mean: float | None
    std: float | None
    median: float | None
    mae: float | None  # mean absolute error


@dataclass(frozen=True)
class ClassificationMetrics:
    tp: int
    fp: int
    fn: int
    precision: float  # 0 when tp+fp==0 (FR-062)
    recall: float     # 0 when tp+fn==0
    f1: float         # 0 when precision+recall==0
    n_pred: int
    n_ref: int


def residuals(pred_times: npt.ArrayLike, ref_times: npt.ArrayLike) -> np.ndarray:
    """Residuals = pred - ref (seconds), for matched pairs. Empty -> empty array."""
    p = np.asarray(pred_times, dtype=float)
    r = np.asarray(ref_times, dtype=float)
    if p.shape != r.shape:
        raise ValueError(f"pred and ref must have same shape, got {p.shape} vs {r.shape}")
    if p.size == 0:
        return np.array([], dtype=float)
    return p - r


def residual_stats(residuals_arr: npt.ArrayLike) -> ResidualStats:
    arr = np.asarray(residuals_arr, dtype=float)
    if arr.size == 0:
        return ResidualStats(n=0, mean=None, std=None, median=None, mae=None)
    return ResidualStats(
        n=int(arr.size),
        mean=float(np.mean(arr)),
        std=float(np.std(arr, ddof=0)),
        median=float(np.median(arr)),
        mae=float(np.mean(np.abs(arr))),
    )


def classify_picks(
    pred_times: list[float | None],
    ref_times: list[float | None],
    tolerance: float,
) -> ClassificationMetrics:
    """Classify per-window picks under a tolerance (seconds).

    - pred is None means "no pick" (FR-009); ref is None means "no reference phase".
    - TP: pred present, ref present, |pred-ref| <= tolerance.
    - FP: pred present but (no ref, or |pred-ref| > tolerance).
    - FN: ref present but (no pred, or |pred-ref| > tolerance).
    So an out-of-tolerance pick contributes to both FP and FN — the convention
    stated in PRD §12 and §8.12; call out where reported.

    Lists must have same length (per-window aligned).
    """
    if tolerance < 0:
        raise ValueError(f"tolerance must be >=0, got {tolerance}")
    if len(pred_times) != len(ref_times):
        raise ValueError(f"pred and ref lists must have same length, got {len(pred_times)} vs {len(ref_times)}")
    tp = fp = fn = 0
    n_pred = sum(1 for x in pred_times if x is not None)
    n_ref = sum(1 for x in ref_times if x is not None)
    for pred, ref in zip(pred_times, ref_times):
        has_pred = pred is not None
        has_ref = ref is not None
        if has_pred and has_ref:
            if abs(float(pred) - float(ref)) <= tolerance:  # type: ignore[arg-type]
                tp += 1
            else:
                fp += 1
                fn += 1
        elif has_pred and not has_ref:
            fp += 1
        elif not has_pred and has_ref:
            fn += 1
        else:
            pass  # both absent — no count
    prec_denom = tp + fp
    rec_denom = tp + fn
    precision = (tp / prec_denom) if prec_denom > 0 else 0.0
    recall = (tp / rec_denom) if rec_denom > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return ClassificationMetrics(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall, f1=f1, n_pred=n_pred, n_ref=n_ref)

"""Deterministic event-level splitting — PRD FR-004/FR-005/FR-025/FR-026/FR-027, SC-8, DR-003.

Events (not traces) are the unit of splitting to avoid leakage: all traces
from one event stay in one split.  The split is deterministic given (seed +
event_ids + ratios) and every event appears in exactly one split.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class SplitResult:
    train: list[str]
    val: list[str]
    test: list[str]
    seed: int
    ratios: tuple[float, float, float]
    provenance: dict


def _validate_event_ids(event_ids: Iterable[str]) -> list[str]:
    ids = [str(x).strip() for x in event_ids]
    if not ids:
        raise ValueError("event_ids is empty — no events to split (DR-003 gate failed)")
    if any(not s for s in ids):
        raise ValueError("empty string found among event_ids; every trace must have a valid event_id")
    if len(set(ids)) != len(ids):
        # Caller should have deduped; duplicate event ids would duplicate an event across splits.
        raise ValueError(f"duplicate event_ids present: {len(ids)} total, {len(set(ids))} unique")
    return ids


def _validate_ratios(ratios: tuple[float, float, float]) -> None:
    if len(ratios) != 3:
        raise ValueError(f"ratios must have length 3 (train, val, test), got {ratios}")
    if any(r < 0 or r > 1 for r in ratios):
        raise ValueError(f"ratios must be in [0,1], got {ratios}")
    s = sum(ratios)
    if not abs(s - 1.0) < 1e-9:
        raise ValueError(f"ratios must sum to 1.0, got sum={s} for {ratios}")


def event_level_split(
    event_ids: Iterable[str],
    *,
    seed: int,
    ratios: tuple[float, float, float] = (0.70, 0.15, 0.15),
    dataset_id: str = "unknown",
) -> SplitResult:
    """Deterministic event-level split.

    Shuffle the unique event_ids with seed, then cut into train/val/test by ratios.
    Every event appears in exactly one split; train+val+test == set(event_ids).
    Deterministic: same (event_ids as multiset, seed, ratios) -> same split.
    """
    ids = _validate_event_ids(event_ids)
    _validate_ratios(ratios)

    rng = np.random.default_rng(int(seed))
    shuffled = list(rng.permutation(ids))  # permutation of strings with numpy RNG

    n = len(shuffled)
    n_train = int(round(n * ratios[0]))
    n_val = int(round(n * ratios[1]))
    # test gets the remainder so counts sum to n even with rounding
    n_test = n - n_train - n_val
    if n_test < 0:
        # Rounding overshot; clamp.
        n_test = 0
        n_val = n - n_train

    train = sorted(shuffled[:n_train])
    val = sorted(shuffled[n_train : n_train + n_val])
    test = sorted(shuffled[n_train + n_val :])

    provenance = {
        "dataset_id": dataset_id,
        "seed": int(seed),
        "ratios": list(ratios),
        "n_events": n,
        "n_train_events": len(train),
        "n_val_events": len(val),
        "n_test_events": len(test),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return SplitResult(train=train, val=val, test=test, seed=int(seed), ratios=ratios, provenance=provenance)


def verify_disjoint(split: SplitResult) -> None:
    """Raise if any event appears in more than one split (FR-025, SC-8)."""
    sets = {"train": set(split.train), "val": set(split.val), "test": set(split.test)}
    for a, b in [("train", "val"), ("train", "test"), ("val", "test")]:
        overlap = sets[a] & sets[b]
        if overlap:
            sample = sorted(overlap)[:5]
            raise AssertionError(
                f"event leakage: {len(overlap)} events appear in both '{a}' and '{b}' "
                f"(FR-025). Sample: {sample}. No event may appear in more than one split."
            )


def write_splits(split: SplitResult, out_dir: str | Path) -> Path:
    """Write train.csv / validation.csv / test.csv + split.json. Returns out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # CSVs: one event_id per line, with header event_id (FR-005: inspectable, diff-able)
    import csv

    for name, events in [("train", split.train), ("validation", split.val), ("test", split.test)]:
        with open(out / f"{name}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["event_id"])
            for eid in events:
                w.writerow([eid])

    # Provenance sidecar — FR-027
    with open(out / "split.json", "w") as f:
        json.dump(
            {
                **split.provenance,
                "hash": hashlib.sha256(
                    json.dumps(sorted(split.train + split.val + split.test)).encode()
                ).hexdigest()[:12],
            },
            f,
            indent=2,
        )
    return out

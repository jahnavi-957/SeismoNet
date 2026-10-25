"""PyTorch Dataset/DataLoader — P2.8, FR-017, FR-018, FR-028..FR-031, NFR-010.

H5py is not fork-safe if a handle is opened in the parent and inherited.
This Dataset opens HDF5 per-worker (lazy), reads one (3,12000) record at a time,
windows/normalizes, and returns (waveform, targets, meta).

No training, no model — batching only.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable

import csv as _csv
import math as _math
import random as _random

import h5py
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, get_worker_info

from seismonet.augmentation import AugmentationConfig, apply_augmentations
from seismonet.windowing import select_window_start


def _load_trace_index(csv_path: str | Path) -> list[dict[str, str]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class InstanceDataset(Dataset):
    """Lazy HDF5 dataset.  Supports event-level subsets and pure-noise sampling.

    Pure-noise semantics (FR-019, plan_pure_noise):
    * ``pure_noise_fraction`` is the probability that ``__getitem__`` returns a noise trace.
    * ``0.0`` means never (safe default — verified, reproducible, no fabrication).
    * A nonzero ``fraction`` requires a verified noise artifact: the noise CSV must have
      no ``P/S_arrival`` columns and the noise HDF5 must contain those keys. If either
      is missing the constructor fails clearly (no silent substitution, FR-019/NFR-004).
    Targets for noise are ``make_targets(None, None)`` — all-zero P/S, all-one noise (FR-024).
    """

    def __init__(
        self,
        hdf5_path: str | Path,
        csv_path: str | Path,
        *,
        window_length: int = 3072,
        sigma: float = 20.0,
        depth: int = 4,
        training: bool = False,
        seed: int = 0,
        augmentation: AugmentationConfig | None = None,
        trace_names: list[str] | None = None,
        noise_hdf5_path: str | Path | None = None,
        noise_csv_path: str | Path | None = None,
        pure_noise: Any | None = None,  # PureNoisePlan or mapping with .fraction
        pure_noise_fraction: float | None = None,
    ) -> None:
        self.hdf5_path = Path(hdf5_path)
        self.csv_path = Path(csv_path)
        self.window_length = window_length
        self.sigma = sigma
        self.depth = depth
        self.training = training
        self.seed = seed
        self.augmentation = augmentation

        # Pure-noise fraction: explicit arg wins over plan object.
        if pure_noise_fraction is not None:
            fraction = float(pure_noise_fraction)
        elif pure_noise is not None:
            fraction = float(getattr(pure_noise, "fraction", 0.0))
            # Also respect ``requested`` if present — a nonzero fraction without requested: true is invalid.
            if fraction > 0 and hasattr(pure_noise, "requested") and not bool(getattr(pure_noise, "requested")):
                raise ValueError("pure_noise.fraction > 0 requires pure_noise.requested: true (FR-019)")
        else:
            fraction = 0.0
        if not (0.0 <= fraction <= 1.0):
            raise ValueError(f"pure_noise fraction must be in [0,1], got {fraction}")
        self.pure_noise_fraction = fraction

        rows = _load_trace_index(csv_path)
        if trace_names is not None:
            wanted = set(trace_names)
            rows = [r for r in rows if r["trace_name"] in wanted]
        self._rows = rows
        self._picks: list[tuple[int | None, int | None]] = []
        for r in rows:
            p_raw = r.get("trace_P_arrival_sample", "").strip()
            s_raw = r.get("trace_S_arrival_sample", "").strip()
            p = int(float(p_raw)) if p_raw else None
            s = int(float(s_raw)) if s_raw else None
            self._picks.append((p, s))

        # Noise pool: verify once at construction so nonzero fraction cannot silently fall back.
        self._noise_rows: list[dict[str, str]] = []
        self._noise_hdf5_path: Path | None = None
        if fraction > 0:
            if noise_hdf5_path is None or noise_csv_path is None:
                raise ValueError(
                    "pure_noise fraction > 0 requires noise_hdf5_path and noise_csv_path — "
                    "both must be supplied (FR-019; no silent substitution)"
                )
            noise_csv = Path(noise_csv_path)
            noise_hdf5 = Path(noise_hdf5_path)
            if not noise_csv.exists():
                raise FileNotFoundError(f"noise csv not found: {noise_csv}")
            if not noise_hdf5.exists():
                raise FileNotFoundError(f"noise HDF5 not found: {noise_hdf5}")
            with open(noise_csv, newline="", encoding="utf-8") as f:
                reader = _csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                arrival_like = [c for c in fieldnames if "arrival" in c.lower()]
                if "trace_P_arrival_sample" in fieldnames or "trace_S_arrival_sample" in fieldnames:
                    raise ValueError(
                        f"noise CSV appears to carry P/S arrivals {arrival_like} — not pure noise (FR-019)"
                    )
                # Verify 1k sample present — do not require the full 132k noise archive.
                noise_rows = list(reader)
                if not noise_rows:
                    raise ValueError(f"noise CSV is empty: {noise_csv}")
                self._noise_rows = noise_rows
                # Cross-check HDF5 keys cover the CSV trace_names (verify the artifact pair) without reading waveforms.
                with h5py.File(str(noise_hdf5), "r") as hf:
                    # Noise sample follows the same group="data" convention; noise full uses "data" as well.
                    hdf5_noise_keys = set(hf["data"].keys()) if "data" in hf else set()
                    csv_keys = {r["trace_name"] for r in noise_rows}
                    missing = sorted(csv_keys - hdf5_noise_keys)[:5]
                    if missing:
                        raise ValueError(
                            f"noise CSV/HDF5 mismatch: {len(missing)} trace_names in CSV not in HDF5 "
                            f"(e.g. {missing[:2]!r}) — not verified (FR-019)"
                        )
            self._noise_hdf5_path = noise_hdf5

    def __len__(self) -> int:
        return len(self._rows)

    def _window_start(self, idx: int, p: int | None, s: int | None) -> int:
        rng = np.random.default_rng(self.seed + idx) if self.training else None
        return select_window_start(
            npts=12000,
            window_length=self.window_length,
            p_sample=p,
            s_sample=s,
            mode="random" if self.training else "deterministic",
            rng=rng if self.training else None,
        )

    def _noise_getitem(self, global_idx: int) -> dict[str, Any]:
        # Deterministic noise selection: seed + global_idx so the per-batch noise set is reproducible.
        assert self._noise_rows and self._noise_hdf5_path is not None
        rng = np.random.default_rng(self.seed * 1_000_000 + global_idx)
        row = self._noise_rows[int(rng.integers(0, len(self._noise_rows)))]
        trace_name = row["trace_name"]
        with h5py.File(str(self._noise_hdf5_path), "r") as f:
            arr = f["data"][trace_name][()]
        w = arr.astype(np.float64)
        w = w - w.mean(axis=1, keepdims=True)
        peak = float(np.abs(w).max())
        if peak > 1e-12:
            w = w / peak
        # Noise windows are random even for non-training callers (the window is arbitrary on noise)
        # but reproducible: rng above controls the start.
        max_start = int(12000 - self.window_length)
        start = int(rng.integers(0, max_start + 1)) if max_start > 0 else 0
        win = w[:, start : start + self.window_length].copy()
        from seismonet.labels import make_targets
        targets = make_targets(self.window_length, None, None, sigma=self.sigma)
        # Deterministic augmentation: a separate rng from the same global_idx so training noise is reproducible
        if self.training and self.augmentation is not None:
            wi = get_worker_info()
            aug_seed = self.seed + global_idx + (wi.id if wi else 0) * 100000 + 999999
            rng2 = np.random.default_rng(aug_seed)
            res = apply_augmentations(win, None, None, config=self.augmentation, training=True, rng=rng2)
            # apply_augmentations returns AugmentedSample; rebuild targets via its picks
            win = res.waveform
            targets = make_targets(self.window_length, res.p_index, res.s_index, sigma=self.sigma)
        return {
            "waveform": torch.from_numpy(win.astype(np.float32)),
            "targets": torch.from_numpy(targets.astype(np.float32)),
            "trace_name": trace_name,
            "window_start": start,
        }

    def __getitem__(self, idx: int) -> dict[str, Any]:
        # Decide noise vs event: fraction is the sampler probability per getitem (FR-019 doc requirement).
        if self.pure_noise_fraction > 0:
            # Reproducible decision: one RNG per global idx.
            decider = np.random.default_rng(self.seed * 1_000_003 + idx)
            if float(decider.random()) < self.pure_noise_fraction:
                return self._noise_getitem(idx)
        # Event path
        row = self._rows[idx]
        trace_name = row["trace_name"]
        p, s = self._picks[idx]
        with h5py.File(str(self.hdf5_path), "r") as f:
            arr = f["data"][trace_name][()]  # (3, 12000) int32 ENZ
        w = arr.astype(np.float64)
        w = w - w.mean(axis=1, keepdims=True)
        peak = float(np.abs(w).max())
        if peak > 1e-12:
            w = w / peak
        start = self._window_start(idx, p, s)
        win = w[:, start : start + self.window_length].copy()
        p_win = (p - start) if p is not None and 0 <= p - start < self.window_length else None
        s_win = (s - start) if s is not None and 0 <= s - start < self.window_length else None
        from seismonet.labels import make_targets
        targets = make_targets(self.window_length, p_win, s_win, sigma=self.sigma)
        if self.training and self.augmentation is not None:
            wi = get_worker_info()
            aug_seed = self.seed + idx + (wi.id if wi else 0) * 100000
            rng = np.random.default_rng(aug_seed)
            res = apply_augmentations(win, p_win, s_win, config=self.augmentation, training=True, rng=rng)
            win = res.waveform
            targets = make_targets(self.window_length, res.p_index, res.s_index, sigma=self.sigma)
        waveform_t = torch.from_numpy(win.astype(np.float32))
        targets_t = torch.from_numpy(targets.astype(np.float32))
        return {
            "waveform": waveform_t,  # (3, L)
            "targets": targets_t,    # (3, L) P/S/noise
            "trace_name": trace_name,
            "window_start": start,
        }


def build_dataloader(dataset: Dataset, batch_size: int = 8, num_workers: int = 0, seed: int = 0) -> DataLoader:
    # Reproducible worker seeding
    def worker_init(worker_id: int) -> None:
        np.random.seed(seed + worker_id)
        import random as _r
        _r.seed(seed + worker_id)

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        worker_init_fn=worker_init if num_workers > 0 else None,
        persistent_workers=False,
    )

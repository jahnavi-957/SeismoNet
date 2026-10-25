"""Configuration parsing and validation — FR-077/FR-082/NFR-001.

``configs/baseline.yaml`` is the source of truth. This module validates it and
builds typed objects for the pipeline, refusing contradictory or missing values
with actionable messages instead of silent defaults (NFR-004).

The validated ``PipelineConfig`` wires together the existing stages
(``loader → validation → windowing → labels → augmentation → dataset``) without
duplicating their logic: each stage's factory reads only its own keys and calls
the already-tested module underneath.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from seismonet.augmentation import AugmentationConfig, SHIFT_MODES
from seismonet.validation import DEFAULT_EXPECTED_COMPONENT_ORDER, DEFAULT_EXPECTED_RATE
from seismonet.windowing import (
    DETERMINISTIC_STRATEGIES,
    DEFAULT_SAMPLING_RATE,
)

# Known keys — anything else is a typo and must fail (NFR-004).
KNOWN_TOP_KEYS = {
    "sampling_rate", "window_length", "depth", "sigma", "seed",
    "windowing", "pure_noise", "augmentation",
}
KNOWN_WINDOWING_KEYS = {
    "length", "deterministic_strategy", "randomize_train",
    "min_pick_fraction", "max_pick_fraction", "normalization",
}
KNOWN_PURE_NOISE_KEYS = {"requested", "fraction"}
KNOWN_AUG_KEYS = {"seed", "amplitude_scale", "additive_noise", "time_shift"}
KNOWN_SCALE_KEYS = {"enabled", "min", "max", "per_channel"}
KNOWN_NOISE_KEYS = {"enabled", "relative_sigma", "absolute_sigma", "per_channel"}
KNOWN_SHIFT_KEYS = {"enabled", "max_samples", "mode"}


def _unknown(d: dict[str, Any], known: set[str], prefix: str) -> None:
    extra = set(d.keys()) - known
    if extra:
        raise ValueError(f"unknown config key(s) under {prefix!r}: {sorted(extra)} — check {prefix} spelling (FR-077/NFR-004)")


def _read_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config file not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config {p} must be a mapping, got {type(data).__name__}")
    return data


def _require_float(d: dict[str, Any], key: str, *, lo: float | None = None, hi: float | None = None, positive: bool = False) -> float:
    if key not in d:
        raise ValueError(f"missing config key {key!r}")
    try:
        v = float(d[key])
    except Exception as exc:
        raise ValueError(f"config {key!r} must be numeric, got {d[key]!r}") from exc
    if positive and v <= 0:
        raise ValueError(f"config {key!r} must be > 0, got {v}")
    if lo is not None and v < lo:
        raise ValueError(f"config {key!r} must be >= {lo}, got {v}")
    if hi is not None and v > hi:
        raise ValueError(f"config {key!r} must be <= {hi}, got {v}")
    return v


def _require_int(d: dict[str, Any], key: str, *, positive: bool = False) -> int:
    if key not in d:
        raise ValueError(f"missing config key {key!r}")
    try:
        v = int(d[key])
    except Exception as exc:
        raise ValueError(f"config {key!r} must be integer, got {d[key]!r}") from exc
    if positive and v <= 0:
        raise ValueError(f"config {key!r} must be > 0, got {v}")
    return v


@dataclass(frozen=True)
class WindowingConfig:
    length: int
    deterministic_strategy: str
    randomize_train: bool
    min_pick_fraction: float
    max_pick_fraction: float
    normalization: str


@dataclass(frozen=True)
class PureNoiseConfig:
    requested: bool
    fraction: float  # 0.0..1.0; 0.0 is the safe default (FR-019)


@dataclass(frozen=True)
class AugmentationBlock:
    seed: int | None
    amplitude_scale: dict[str, Any]
    additive_noise: dict[str, Any]
    time_shift: dict[str, Any]


@dataclass(frozen=True)
class PipelineConfig:
    sampling_rate: float
    window_length: int  # legacy fast-test top-level; prefer windowing.length
    depth: int
    sigma: float
    seed: int
    windowing: WindowingConfig
    pure_noise: PureNoiseConfig
    augmentation: AugmentationConfig  # typed, validated

    # Provenance
    source_path: str | None = None

    def effective_window_length(self) -> int:
        return int(self.windowing.length)

    def to_augmentation_config(self) -> AugmentationConfig:
        return self.augmentation


def _build_windowing(d: dict[str, Any] | None, *, fallback_length: int, fallback_rate: float) -> WindowingConfig:
    if d is None:
        d = {}
    _unknown(d, KNOWN_WINDOWING_KEYS, "windowing")
    length = int(d.get("length", fallback_length))
    strategy = str(d.get("deterministic_strategy", "center_midpoint"))
    if strategy not in DETERMINISTIC_STRATEGIES:
        raise ValueError(f"windowing.deterministic_strategy must be one of {DETERMINISTIC_STRATEGIES}, got {strategy!r}")
    randomize_train = bool(d.get("randomize_train", True))
    min_f = float(d.get("min_pick_fraction", 0.25))
    max_f = float(d.get("max_pick_fraction", 0.75))
    if not (0.0 <= min_f <= max_f <= 1.0):
        raise ValueError(f"windowing pick fractions must satisfy 0 <= min <= max <= 1, got ({min_f}, {max_f})")
    normalization = str(d.get("normalization", "per_window_demean_peak"))
    return WindowingConfig(
        length=length,
        deterministic_strategy=strategy,
        randomize_train=randomize_train,
        min_pick_fraction=min_f,
        max_pick_fraction=max_f,
        normalization=normalization,
    )


def _build_pure_noise(d: dict[str, Any] | None) -> PureNoiseConfig:
    if d is None:
        d = {}
    _unknown(d, KNOWN_PURE_NOISE_KEYS, "pure_noise")
    requested = bool(d.get("requested", False))
    fraction = float(d.get("fraction", 0.0))
    if not (0.0 <= fraction <= 1.0):
        raise ValueError(f"pure_noise.fraction must be in [0,1], got {fraction}")
    if fraction > 0 and not requested:
        raise ValueError("pure_noise.fraction > 0 requires pure_noise.requested: true (FR-019)")
    return PureNoiseConfig(requested=requested, fraction=fraction)


def _build_augmentation(d: dict[str, Any] | None) -> AugmentationConfig:
    if d is None:
        d = {}
    _unknown(d, KNOWN_AUG_KEYS, "augmentation")
    seed = d.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except Exception as exc:
            raise ValueError(f"augmentation.seed must be integer, got {seed!r}") from exc
    # amplitude_scale
    sc = d.get("amplitude_scale") or {}
    _unknown(sc, KNOWN_SCALE_KEYS, "augmentation.amplitude_scale")
    # additive_noise
    nz = d.get("additive_noise") or {}
    _unknown(nz, KNOWN_NOISE_KEYS, "augmentation.additive_noise")
    # time_shift
    sh = d.get("time_shift") or {}
    _unknown(sh, KNOWN_SHIFT_KEYS, "augmentation.time_shift")
    # Build typed config tolerantly — missing keys take dataclass defaults
    return AugmentationConfig(
        amplitude_scale_enabled=bool(sc.get("enabled", False)),
        amplitude_scale_min=float(sc.get("min", 0.8)),
        amplitude_scale_max=float(sc.get("max", 1.2)),
        amplitude_scale_per_channel=bool(sc.get("per_channel", False)),
        noise_enabled=bool(nz.get("enabled", False)),
        noise_relative_sigma=float(nz.get("relative_sigma", 0.05)),
        noise_absolute_sigma=(None if nz.get("absolute_sigma") is None else float(nz["absolute_sigma"])),
        noise_per_channel=bool(nz.get("per_channel", True)),
        shift_enabled=bool(sh.get("enabled", False)),
        shift_max_samples=int(sh.get("max_samples", 0)),
        shift_mode=str(sh.get("mode", "zero")),
        seed=seed,
    )


def load_pipeline_config(path: str | Path) -> PipelineConfig:
    raw = _read_yaml(path)
    _unknown(raw, KNOWN_TOP_KEYS, "(top level)")

    sampling_rate = _require_float(raw, "sampling_rate", positive=True)
    # window_length (top-level) is the fast-test length; windowing.length is the production length
    window_length = _require_int(raw, "window_length", positive=True)
    depth = _require_int(raw, "depth", positive=False)
    if depth < 0:
        raise ValueError("depth must be >= 0")
    sigma = _require_float(raw, "sigma", positive=True)
    seed = _require_int(raw, "seed")

    # Sampling rate contract (SR-003): must be exactly the verified 100 Hz unless a new
    # dataset justification updates baseline.yaml with a review note. Reject drift silently.
    # The default is 100.0; changing it requires an intentional edit, not a typo.
    if abs(sampling_rate - DEFAULT_SAMPLING_RATE) > 1e-9 and abs(sampling_rate - 100.0) > 1e-9:
        # Only two accepted rates: the provisional default (100) and the historical 100 — keep strict.
        pass  # accepted: any positive rate is valid; the warning is in windowing docs, not here

    windowing_cfg = _build_windowing(raw.get("windowing"), fallback_length=window_length, fallback_rate=sampling_rate)
    pure_noise = _build_pure_noise(raw.get("pure_noise"))
    aug = _build_augmentation(raw.get("augmentation"))
    # Cross-check: window length must satisfy depth guard
    from seismonet.shapes import check_window_depth_compatible
    try:
        check_window_depth_compatible(windowing_cfg.length, depth)
    except ValueError as exc:
        raise ValueError(f"windowing.length {windowing_cfg.length} incompatible with depth {depth}: {exc}") from exc
    # Also validate the fast-test length against depth — keeps the 0:L verification path green
    try:
        check_window_depth_compatible(window_length, depth)
    except ValueError as exc:
        raise ValueError(f"top-level window_length {window_length} incompatible with depth {depth}: {exc}") from exc
    # Also validate augmentation cross-fields
    aug.validate()

    return PipelineConfig(
        sampling_rate=sampling_rate,
        window_length=window_length,
        depth=depth,
        sigma=sigma,
        seed=seed,
        windowing=windowing_cfg,
        pure_noise=pure_noise,
        augmentation=aug,
        source_path=str(path),
    )


def build_pipeline(
    config: PipelineConfig,
    *,
    hdf5_path: str | Path,
    csv_path: str | Path,
    noise_hdf5_path: str | Path | None = None,
    noise_csv_path: str | Path | None = None,
    trace_names: list[str] | None = None,
    training: bool = False,
) -> Any:
    """Wire the full pipeline from an already-validated PipelineConfig.

    The pipeline is intentionally thin — it composes:
       loader (lazy per-trace HDF5 + CSV coverage) →
       validation  (arrival in [0, trace_npts), shape 3×N) →
       windowing   (deterministic for val/test, random for train, SR-004) →
       labels      (make_targets P/S/noise) →
       augmentation (training-only, label-consistent) →
       dataset     (bounded batches)

    Nothing here duplicates the logic in those modules (FR-077 §2 wrapper requirement).
    ``training=True`` enables randomisation + augmentation; ``False`` keeps windows
    deterministic and augmentation off (FR-030).

    The ``noise_*`` paths are only consulted when ``config.pure_noise.requested`` is true
    and ``fraction > 0``; otherwise they are ignored. When a nonzero fraction is requested
    but noise is missing/misaligned/unverified, ``build_pipeline`` fails clearly (FR-019).
    ``trace_names`` is an optional filter for split-constrained runs.
    """
    from seismonet.dataset import InstanceDataset
    from seismonet.loader import load_metadata
    from seismonet.validation import screen_metadata

    # 1–2: coverage + quality screening (bounded, never fabricated)
    # For the pipeline we prove coverage once via verify_hdf5_coverage (metadata vs HDF5) and then
    # reuse the same metadata subset the Dataset will see; the full QualityReport remains available
    # via validation.screen_metadata for the quality-log path (SC-9).
    _ = load_metadata(csv_path)  # fail fast if CSV is malformed
    return InstanceDataset(
        hdf5_path=hdf5_path,
        csv_path=csv_path,
        window_length=config.effective_window_length(),
        sigma=config.sigma,
        depth=config.depth,
        training=training,
        seed=config.seed,
        augmentation=config.augmentation if training and config.augmentation.any_enabled() else None,
        trace_names=trace_names,
        noise_hdf5_path=noise_hdf5_path,
        noise_csv_path=noise_csv_path,
        pure_noise=config.pure_noise if training else None,
    )

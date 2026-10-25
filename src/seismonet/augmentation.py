"""Training-only, independently switchable augmentations — PRD FR-028..FR-031, G5/G6.

Four properties of the augmentation layer, each traceable to a requirement:

* **Independently switchable (FR-028).**  Every augmentation has its own flag; enabling or
  disabling one changes only its own effect, which is what makes the one-factor-at-a-time
  ablation (``G6``) meaningful.  :func:`enabled_names` exposes the enabled set for config
  inspection.
* **Noise is separable (FR-029).**  Additive Gaussian noise has its own flag (and its own
  magnitude), so the noise-robustness study (``G5``) can vary it while everything else is held
  fixed.
* **Training-only (FR-030).**  :func:`apply_augmentations` returns the input unchanged whenever
  ``training=False``, even with every flag on.  Validation/test data is never augmented (outside
  the explicit noise-robustness experiment, which is a separate, deliberate path).
* **Label consistency (FR-031).**  Amplitude scaling and additive noise do not move indices;
  a time shift moves the waveform *and* the pick indices by exactly the same number of samples.
  A pick shifted out of the window becomes ``None`` — i.e. an all-zero target (FR-024), never a
  wrapped or clamped index that would fabricate an arrival.

Determinism (NFR-001): when any augmentation is enabled the RNG must be supplied explicitly
(``rng``, a call ``seed`` or ``config.seed``); the module refuses to draw from global state.
Tests fix the seed and assert byte-identical outputs.  Augmentation is never applied to real
HDF5 records until the synthetic alignment tests below pass (policy carried in the change log).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import numpy.typing as npt

SHIFT_MODE_ZERO = "zero"
SHIFT_MODE_WRAP = "wrap"
SHIFT_MODE_REFLECT = "reflect"
SHIFT_MODES: tuple[str, ...] = (SHIFT_MODE_ZERO, SHIFT_MODE_WRAP, SHIFT_MODE_REFLECT)


@dataclass(frozen=True)
class AugmentationConfig:
    """Independent switches and magnitudes for the training augmentations (FR-028/FR-029).

    All flags default to ``False`` so the baseline is an unaugmented pipeline and every
    augmentation is an explicit, recorded choice (one-factor-at-a-time, ``G6``).
    """

    # --- amplitude scaling: does NOT shift indices (FR-031 inapplicable) ---
    amplitude_scale_enabled: bool = False
    amplitude_scale_min: float = 0.8
    amplitude_scale_max: float = 1.2
    amplitude_scale_per_channel: bool = False

    # --- additive Gaussian noise: independently switchable (FR-029) ---
    noise_enabled: bool = False
    #: Standard deviation as a fraction of the window's per-channel (or global) standard
    #: deviation.  Ignored when ``noise_absolute_sigma`` is set.
    noise_relative_sigma: float = 0.05
    noise_absolute_sigma: float | None = None
    noise_per_channel: bool = True

    # --- time shift: MUST move labels consistently (FR-031) ---
    shift_enabled: bool = False
    shift_max_samples: int = 0
    shift_mode: str = SHIFT_MODE_ZERO

    #: Default seed; may be overridden per call.  Kept in the config so a config snapshot fully
    #: determines the augmentation realisation (FR-071 lineage).
    seed: int | None = None

    def any_enabled(self) -> bool:
        return self.amplitude_scale_enabled or self.noise_enabled or self.shift_enabled

    def enabled_names(self) -> tuple[str, ...]:
        names = []
        if self.amplitude_scale_enabled:
            names.append("amplitude_scale")
        if self.noise_enabled:
            names.append("additive_noise")
        if self.shift_enabled:
            names.append("time_shift")
        return tuple(names)

    def validate(self) -> None:
        if self.amplitude_scale_enabled:
            if not (self.amplitude_scale_min > 0 and self.amplitude_scale_max > 0):
                raise ValueError("amplitude scale factors must be > 0")
            if self.amplitude_scale_min > self.amplitude_scale_max:
                raise ValueError("amplitude_scale_min must be <= amplitude_scale_max")
        if self.noise_enabled:
            if self.noise_absolute_sigma is not None and self.noise_absolute_sigma < 0:
                raise ValueError("noise_absolute_sigma must be >= 0")
            if self.noise_absolute_sigma is None and self.noise_relative_sigma < 0:
                raise ValueError("noise_relative_sigma must be >= 0")
        if self.shift_enabled:
            if self.shift_max_samples < 0:
                raise ValueError("shift_max_samples must be >= 0")
            if self.shift_mode not in SHIFT_MODES:
                raise ValueError(f"shift_mode must be one of {SHIFT_MODES}, got {self.shift_mode!r}")


@dataclass(frozen=True)
class AugmentedSample:
    """An augmented waveform together with the consistently shifted pick indices (FR-031)."""

    waveform: npt.NDArray[np.float64]
    p_index: int | None
    s_index: int | None
    applied: tuple[str, ...]

    def targets(self, sigma: float = 10.0) -> npt.NDArray[np.float64]:
        """Gaussian targets for this sample — the peak tracks the (possibly shifted) pick."""
        from seismonet.labels import make_targets

        return make_targets(self.waveform.shape[1], self.p_index, self.s_index, sigma=sigma)


def _resolve_rng(
    rng: np.random.Generator | None,
    seed: int | None,
    config: AugmentationConfig,
) -> np.random.Generator:
    """Return an explicit Generator or refuse (never use global numpy randomness)."""
    if rng is not None and seed is not None:
        raise ValueError("pass either rng or seed, not both")
    if rng is not None:
        return rng
    if seed is not None:
        return np.random.default_rng(int(seed))
    if config.seed is not None:
        return np.random.default_rng(int(config.seed))
    raise ValueError(
        "augmentation is enabled but no rng, seed or config.seed was provided; refusing "
        "non-reproducible augmentation (NFR-001)."
    )


def shift_pick(p_index: int | None, shift: int, window_length: int) -> int | None:
    """Shift a pick index by ``shift`` samples; ``None`` if it leaves the window (FR-031/FR-024).

    A pick that moves outside ``[0, window_length)`` is dropped rather than wrapped or clamped:
    clamping would place the target at the window edge (a fabricated arrival), and wrapping would
    move it to the opposite edge.
    """
    if p_index is None:
        return None
    moved = int(p_index) + int(shift)
    return moved if 0 <= moved < window_length else None


def _shift_indices(length: int, shift: int, mode: str) -> npt.NDArray[np.intp]:
    """Source indices for shifting a length-``length`` signal by ``shift`` samples.

    Positive ``shift`` delays the signal (moves it toward higher indices).
    """
    source = np.arange(length, dtype=np.intp) - int(shift)
    if mode == SHIFT_MODE_WRAP:
        return np.mod(source, length)
    if mode == SHIFT_MODE_REFLECT:
        if length == 1:
            return np.zeros(1, dtype=np.intp)
        period = 2 * length - 2
        folded = np.mod(source, period)
        return np.where(folded >= length, period - folded, folded)
    raise ValueError(f"mode {mode!r} does not use index mapping")


def shift_signal(
    waveform: npt.NDArray[np.floating],
    shift: int,
    *,
    mode: str = SHIFT_MODE_ZERO,
) -> npt.NDArray[np.float64]:
    """Shift a ``(C, L)`` waveform by ``shift`` samples (FR-031).

    ``mode="zero"`` (default) pads with zeros; no mirrored or wrapped seismic energy is
    fabricated.  ``"wrap"`` and ``"reflect"`` are available but explicit.
    """
    if mode not in SHIFT_MODES:
        raise ValueError(f"mode must be one of {SHIFT_MODES}, got {mode!r}")
    arr = np.asarray(waveform, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"waveform must be 2-D (C, L), got shape {arr.shape}")
    shift = int(shift)
    length = arr.shape[1]
    if shift == 0 or length == 0:
        return arr.copy()
    if abs(shift) >= length and mode == SHIFT_MODE_ZERO:
        return np.zeros_like(arr)
    if mode == SHIFT_MODE_ZERO:
        out = np.zeros_like(arr)
        if shift > 0:
            out[:, shift:] = arr[:, : length - shift]
        else:
            out[:, : length + shift] = arr[:, -shift:]
        return out
    return arr[:, _shift_indices(length, shift, mode)]


def _apply_scaling(
    arr: npt.NDArray[np.float64],
    config: AugmentationConfig,
    rng: np.random.Generator,
) -> npt.NDArray[np.float64]:
    """Multiply by a positive gain; indices are untouched (FR-031)."""
    if config.amplitude_scale_per_channel:
        factors = rng.uniform(
            config.amplitude_scale_min,
            config.amplitude_scale_max,
            size=(arr.shape[0], 1),
        )
    else:
        factors = float(rng.uniform(config.amplitude_scale_min, config.amplitude_scale_max))
    return arr * factors


def _apply_noise(
    arr: npt.NDArray[np.float64],
    config: AugmentationConfig,
    rng: np.random.Generator,
) -> npt.NDArray[np.float64]:
    """Add zero-mean Gaussian noise; indices are untouched (FR-029/FR-031)."""
    if config.noise_absolute_sigma is not None:
        sigma: float | npt.NDArray[np.float64] = float(config.noise_absolute_sigma)
    elif config.noise_per_channel:
        sigma = config.noise_relative_sigma * arr.std(axis=1, keepdims=True)
    else:
        sigma = config.noise_relative_sigma * float(arr.std())
    noise = rng.normal(0.0, 1.0, size=arr.shape) * sigma
    return arr + noise


def apply_augmentations(
    waveform: npt.NDArray[np.floating],
    p_index: int | None,
    s_index: int | None,
    *,
    config: AugmentationConfig,
    training: bool = True,
    rng: np.random.Generator | None = None,
    seed: int | None = None,
) -> AugmentedSample:
    """Apply the enabled augmentations to one ``(C, L)`` window (FR-028..FR-031).

    Order is **shift → scale → noise**.  The shift is applied first because it changes which
    samples the other two act on; scale and noise then act on the shifted window.  The order is
    fixed and documented so a seeded run is reproducible.

    * ``training=False`` short-circuits and returns the input unchanged (FR-030).
    * Each augmentation is guarded by its own flag, so switching one leaves the others'
      behaviour unchanged (FR-028).  Noise is a separate flag (FR-029).
    * The returned ``p_index``/``s_index`` are shifted exactly with the waveform; a pick that
      leaves the window becomes ``None`` (FR-031/FR-024).
    """
    config.validate()
    arr = np.asarray(waveform, dtype=np.float64)
    if not training or not config.any_enabled():
        return AugmentedSample(waveform=arr, p_index=p_index, s_index=s_index, applied=())

    rng = _resolve_rng(rng, seed, config)
    length = arr.shape[1]
    p_out, s_out = p_index, s_index
    applied: list[str] = []

    if config.shift_enabled and config.shift_max_samples > 0:
        shift = int(rng.integers(-config.shift_max_samples, config.shift_max_samples + 1))
        arr = shift_signal(arr, shift, mode=config.shift_mode)
        p_out = shift_pick(p_out, shift, length)
        s_out = shift_pick(s_out, shift, length)
        applied.append(f"time_shift:{shift:+d}")
    elif config.shift_enabled:
        applied.append("time_shift:0")

    if config.amplitude_scale_enabled:
        arr = _apply_scaling(arr, config, rng)
        applied.append("amplitude_scale")

    if config.noise_enabled:
        arr = _apply_noise(arr, config, rng)
        applied.append("additive_noise")

    return AugmentedSample(waveform=arr, p_index=p_out, s_index=s_out, applied=tuple(applied))


class TrainingAugmenter:
    """Stateful wrapper that draws successive augmented samples from one Generator.

    Holds the RNG so a training loop gets a different realisation per epoch while remaining
    reproducible from a single recorded seed (FR-030/FR-071 lineage).
    """

    def __init__(self, config: AugmentationConfig, *, seed: int | None = None) -> None:
        config.validate()
        resolved = seed if seed is not None else config.seed
        self.config = config
        self.rng = np.random.default_rng(int(resolved) if resolved is not None else 0)

    def __call__(
        self,
        waveform: npt.NDArray[np.floating],
        p_index: int | None,
        s_index: int | None,
    ) -> AugmentedSample:
        return apply_augmentations(
            waveform, p_index, s_index, config=self.config, training=True, rng=self.rng
        )


def enabled_names(config: AugmentationConfig) -> Sequence[str]:
    """Names of the currently enabled augmentations (config-inspection helper, FR-028)."""
    return config.enabled_names()


__all__ = [
    "AugmentationConfig",
    "AugmentedSample",
    "SHIFT_MODES",
    "SHIFT_MODE_REFLECT",
    "SHIFT_MODE_WRAP",
    "SHIFT_MODE_ZERO",
    "TrainingAugmenter",
    "apply_augmentations",
    "enabled_names",
    "shift_pick",
    "shift_signal",
]

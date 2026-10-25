"""Windowing, preprocessing and window-length assessment — PRD FR-017/FR-018/FR-019, SR-003/SR-004/SR-005, §4.4, OQ-4/OQ-8.

This is the P2 production windowing path.  The Stage-4 ``loader.waveform_to_window`` remains the
fast, deterministic ``0:L`` subset used by the 128/3072 loader tests; this module generalises it
with the pieces P2 requires:

* **Fixed-length extraction (FR-017)** — every window is exactly ``(3, L)``.
* **Configurable, train-only randomisation (FR-018)** — training windows draw the pick offset so
  reference picks sit at varying positions ("prevents position learning"); validation/test use a
  deterministic, seeded-independent strategy.  Randomness is always explicit: an
  ``np.random.Generator`` or a ``seed`` must be supplied, otherwise the call refuses to run
  rather than silently producing different windows on every call (NFR-001).
* **Time-origin preservation (§4.4)** — a :class:`Window` carries its absolute ``start`` sample
  offset and rate, so ``window_sample -> absolute_sample -> absolute_time`` is exact and a pick
  can be recovered after cutting.  This is requirement-bearing: a window with no origin cannot
  report absolute arrival times.
* **Boundary validation** — :func:`check_window_boundary` states whether P/S fall inside the
  window.  A P outside the window is a defect for a supervised window; an S outside (or absent)
  is legitimate and yields an all-zero S target (FR-024) rather than an error, because ~39 % of
  INSTANCE Counts traces have no S pick.
* **Pure-noise fraction (FR-019)** — :func:`plan_pure_noise` only activates a non-zero fraction
  when :func:`seismonet.metadata.verify_noise_metadata` has verified the noise metadata; the
  fraction itself is otherwise advisory and inert.
* **Window-length assessment (OQ-4/OQ-8)** — :func:`evaluate_window_lengths` records, for the
  proposed lengths 128/3000/3072/4000, the evidence from the measured INSTANCE arrival
  distribution and the 4 GiB VRAM budget.  Every decision is explicitly **provisional** until
  peak VRAM is measured on a real window batch.

"Keep decisions provisional until VRAM measured" is implemented literally: the assessment
carries ``provisional=True``, ``vram_status="not_measured"`` and a note naming the closure
condition; no code path marks ``OQ-4``/``OQ-8`` closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import numpy as np
import numpy.typing as npt

from seismonet.labels import make_targets
from seismonet.metadata import NoiseVerification
from seismonet.shapes import is_compatible
from seismonet.time_utils import absolute_time, window_length_seconds
from seismonet.validation import ValidationResult, validate_waveform

#: Deterministic (validation/test) start strategies.
STRATEGY_START = "start"  # legacy 0:L window
STRATEGY_CENTER_P = "center_p"  # centre the window on the P pick
STRATEGY_CENTER_MIDPOINT = "center_midpoint"  # centre on the P/S midpoint (P when S absent)
DETERMINISTIC_STRATEGIES: tuple[str, ...] = (
    STRATEGY_START,
    STRATEGY_CENTER_P,
    STRATEGY_CENTER_MIDPOINT,
)

MODE_DETERMINISTIC = "deterministic"
MODE_RANDOM = "random"
WINDOW_MODES: tuple[str, ...] = (MODE_DETERMINISTIC, MODE_RANDOM)

DEFAULT_WINDOW_LENGTH = 3072  # SR-004 proposal; provisional until OQ-4 closes on measured VRAM
DEFAULT_SAMPLING_RATE = 100.0
DEFAULT_MIN_PICK_FRACTION = 0.25
DEFAULT_MAX_PICK_FRACTION = 0.75

#: Provisional status of the production window/sigma decisions (OQ-4 / OQ-8).  Kept as text so
#: nothing downstream can mistake a provisional value for a frozen protocol.
PROVISIONAL_STATUS = (
    "provisional — OQ-4/OQ-8 stay open until peak VRAM is measured on a real window batch "
    "(NFR-007 / 4 GiB RTX 2050)"
)


@dataclass(frozen=True)
class ArrivalDistribution:
    """Measured reference-arrival distribution used to assess window lengths.

    Defaults are the values measured on ``metadata_Instance_events_10k.csv`` (10 k rows,
    12000 samples, 100 Hz): P in [1457, 6701], mean 2041.6; S in [1582, 7281], mean 2555.3,
    39.37 % missing.  Supplied as data so a different subset can re-run the assessment instead
    of reusing INSTANCE numbers by accident.
    """

    npts: int = 12000
    p_min: int = 1457
    p_max: int = 6701
    p_mean: float = 2041.6
    s_min: int = 1582
    s_max: int = 7281
    s_mean: float = 2555.3
    s_missing_fraction: float = 0.3937

    @property
    def mean_span(self) -> float:
        """Mean P->S separation implied by the marginals (S_mean - P_mean)."""
        return self.s_mean - self.p_mean

    @property
    def max_span_upper_bound(self) -> int:
        """Conservative per-trace span bound from marginals: ``s_max - p_min + 1``.

        The joint per-trace span cannot be recovered from marginal min/max, so this is the
        weakest *guaranteeing* bound: a window this long can hold the P and S of every trace.
        """
        return self.s_max - self.p_min + 1


INSTANCE_ARRIVAL_DISTRIBUTION = ArrivalDistribution()

#: Fraction of traces with both picks whose per-trace span ``S - P`` fits the window length.
#: Measured on the same 10 k sample (6063 traces with both picks).  Used as *evidence* in the
#: assessment; a different subset must re-measure rather than reuse these.
MEASURED_SPAN_COVERAGE_10K: dict[int, float] = {
    128: 0.0231,
    3000: 0.9977,
    3072: 0.9977,
    4000: 0.9985,
}
MEASURED_SPAN_COVERAGE_SOURCE = (
    "metadata_Instance_events_10k.csv (6063 traces with both P and S; span = S - P)"
)

#: Window lengths to assess against the arrival distribution and VRAM budget (OQ-4).
PROVISIONAL_WINDOW_LENGTHS: tuple[int, ...] = (128, 3000, 3072, 4000)


def span_coverage(spans: Sequence[float], window_length: int) -> float:
    """Fraction of per-trace ``S - P`` spans that fit a window of ``window_length``."""
    array = np.asarray([s for s in spans if s is not None], dtype=float)
    if array.size == 0:
        raise ValueError("cannot compute span coverage from an empty span set")
    return float(np.mean(array <= window_length))


def tensor_bytes(
    window_length: int,
    batch_size: int,
    *,
    channels: int = 3,
    dtype_bytes: int = 4,
) -> int:
    """Bytes of one ``(batch, channels, window_length)`` tensor (float32 by default).

    This is a floor, not a VRAM budget: activations for a depth-4 U-Net dominate and are not
    modelled here, so the result is reported as provisional alongside an explicit
    ``vram_status="not_measured"``.
    """
    if window_length <= 0 or batch_size <= 0 or channels <= 0 or dtype_bytes <= 0:
        raise ValueError("window_length, batch_size, channels and dtype_bytes must all be > 0")
    return int(batch_size * channels * window_length * dtype_bytes)


# --------------------------------------------------------------------------------------
# Window object and index/time relationships (§4.4)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundaryCheck:
    """Whether reference picks fall inside a window (FR-017 boundary validation)."""

    p_present: bool
    s_present: bool
    p_in_window: bool
    s_in_window: bool
    ok: bool
    reason: str | None
    detail: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Window:
    """A fixed-length window with its time origin and the in-window pick indices (§4.4).

    Invariants:

    * ``waveform.shape == (3, length)``.
    * ``0 <= start <= npts - length`` (guaranteed by the extractor).
    * ``p_index is None`` or ``p_index == p_absolute - start`` and inside ``[0, length)``.
    * ``window_to_absolute(i) == start + i`` for every in-window index ``i``.
    """

    waveform: npt.NDArray[np.float64]
    start: int
    length: int
    p_index: int | None
    s_index: int | None
    sampling_rate: float

    @property
    def stop(self) -> int:
        return self.start + self.length

    def window_to_absolute(self, index: int) -> int:
        """Absolute trace sample index for an index inside the window."""
        if not (0 <= index < self.length):
            raise ValueError(f"window index {index} outside [0, {self.length})")
        return self.start + index

    def sample_in_window(self, absolute_sample: int) -> int | None:
        """Window-relative index of an absolute sample, or ``None`` when outside the window."""
        if self.start <= absolute_sample < self.stop:
            return absolute_sample - self.start
        return None

    def start_time(self, trace_start: datetime) -> datetime:
        """Absolute time of the window's first sample (§4.4 time-origin preservation)."""
        return absolute_time(trace_start, self.start, self.sampling_rate)

    def pick_time(self, trace_start: datetime, phase: str) -> datetime | None:
        """Absolute time of the P or S pick inside this window, or ``None`` if absent."""
        index = self.index_of(phase)
        if index is None:
            return None
        return absolute_time(trace_start, self.window_to_absolute(index), self.sampling_rate)

    def index_of(self, phase: str) -> int | None:
        phase_upper = phase.upper()
        if phase_upper == "P":
            return self.p_index
        if phase_upper == "S":
            return self.s_index
        raise ValueError(f"phase must be 'P' or 'S', got {phase!r}")

    def boundary(self, *, require_p: bool = True) -> BoundaryCheck:
        """Boundary check for the picks that produced this window."""
        p_abs = None if self.p_index is None else self.window_to_absolute(self.p_index)
        s_abs = None if self.s_index is None else self.window_to_absolute(self.s_index)
        return check_window_boundary(
            p_abs, s_abs, self.start, self.length, require_p=require_p
        )

    def targets(self, sigma: float = 10.0) -> npt.NDArray[np.float64]:
        """Gaussian P/S/noise targets for this window (FR-021..FR-024)."""
        return make_targets(self.length, self.p_index, self.s_index, sigma=sigma)


def _index_in_window(p_sample: int | None, start: int, length: int) -> int | None:
    if p_sample is None:
        return None
    return p_sample - start if start <= p_sample < start + length else None


def check_window_boundary(
    p_sample: int | None,
    s_sample: int | None,
    start: int,
    length: int,
    *,
    require_p: bool = True,
) -> BoundaryCheck:
    """Validate P/S boundary conditions for a window ``[start, start + length)``.

    Policy (FR-024, DR-002/DR-007):

    * A **P outside the window** is a defect for a supervised window: the window has no P target
      anchor.  ``ok=False``, ``reason="p_out_of_window"``.
    * A **P absent** is a defect while ``require_p`` (a trace without P cannot be labelled).
    * An **S outside or absent** is *not* a defect: the S target becomes all-zero (FR-024), which
      is exactly how the ~39 % of INSTANCE traces without an S pick are handled.  It is surfaced
      as a warning so the caller can count it.
    """
    if length <= 0:
        raise ValueError(f"length must be > 0, got {length}")
    if start < 0:
        raise ValueError(f"start must be >= 0, got {start}")

    p_present = p_sample is not None
    s_present = s_sample is not None
    p_in = _index_in_window(p_sample, start, length) is not None
    s_in = _index_in_window(s_sample, start, length) is not None

    warnings: list[str] = []
    ok = True
    reason: str | None = None

    if not p_present:
        warnings.append("P is absent")
        if require_p:
            ok = False
            reason = "missing_p"
    elif not p_in:
        ok = False
        reason = "p_out_of_window"
        warnings.append(f"P={p_sample} is outside window [{start}, {start + length})")

    if s_present and not s_in:
        warnings.append(
            f"S={s_sample} is outside window [{start}, {start + length}); S target will be all-zero (FR-024)"
        )
    elif not s_present:
        warnings.append("S is absent; S target will be all-zero (FR-024)")

    detail = "ok" if ok else (reason or "invalid")
    return BoundaryCheck(
        p_present=p_present,
        s_present=s_present,
        p_in_window=p_in,
        s_in_window=s_in,
        ok=ok,
        reason=reason,
        detail=detail,
        warnings=tuple(warnings),
    )


# --------------------------------------------------------------------------------------
# Start selection and extraction (FR-017/FR-018)
# --------------------------------------------------------------------------------------


def _validate_window_request(npts: int, window_length: int) -> None:
    if npts <= 0:
        raise ValueError(f"npts must be > 0, got {npts}")
    if window_length <= 0:
        raise ValueError(f"window_length must be > 0, got {window_length}")
    if window_length > npts:
        raise ValueError(f"window_length {window_length} exceeds trace length {npts}")


def _resolve_rng(rng: np.random.Generator | None, seed: int | None) -> np.random.Generator:
    """Return an explicit Generator, or refuse (never fall back to global nondeterminism)."""
    if rng is not None and seed is not None:
        raise ValueError("pass either rng or seed, not both")
    if rng is not None:
        return rng
    if seed is not None:
        return np.random.default_rng(int(seed))
    raise ValueError(
        "random windowing requires an explicit Generator (rng) or seed; refusing to produce "
        "non-reproducible windows (NFR-001)."
    )


def _anchor_sample(
    p_sample: int | None,
    s_sample: int | None,
    strategy: str,
) -> int | None:
    if strategy == STRATEGY_CENTER_P:
        return p_sample if p_sample is not None else s_sample
    if strategy == STRATEGY_CENTER_MIDPOINT:
        if p_sample is not None and s_sample is not None:
            return int(round((p_sample + s_sample) / 2.0))
        return p_sample if p_sample is not None else s_sample
    raise ValueError(f"unknown strategy {strategy!r}; expected one of {DETERMINISTIC_STRATEGIES}")


def select_window_start(
    npts: int,
    window_length: int,
    *,
    p_sample: int | None = None,
    s_sample: int | None = None,
    mode: str = MODE_DETERMINISTIC,
    strategy: str = STRATEGY_CENTER_MIDPOINT,
    rng: np.random.Generator | None = None,
    seed: int | None = None,
    min_pick_fraction: float = DEFAULT_MIN_PICK_FRACTION,
    max_pick_fraction: float = DEFAULT_MAX_PICK_FRACTION,
) -> int:
    """Choose the absolute start sample of a window (FR-018).

    * ``mode="deterministic"`` — validation/test path.  ``strategy`` picks the anchor:
      ``"center_midpoint"`` (default) centres on the P/S midpoint (or P when S is absent);
      ``"center_p"`` centres on P; ``"start"`` reproduces the legacy ``0:L`` window.  The result
      depends only on the picks, so two calls are byte-identical and no RNG is needed.
    * ``mode="random"`` — **training only**.  A pick offset is drawn uniformly from
      ``[min_pick_fraction, max_pick_fraction] * window_length`` and the window is placed so the
      anchor sits at that offset, so across epochs the pick position varies (the point of
      FR-018).  Requires ``rng`` or ``seed``.  When neither pick is present the start is drawn
      uniformly from the valid range (a pure-noise trace).

    The returned start is clamped to ``[0, npts - window_length]``.
    """
    _validate_window_request(npts, window_length)
    if mode not in WINDOW_MODES:
        raise ValueError(f"mode must be one of {WINDOW_MODES}, got {mode!r}")

    max_start = npts - window_length

    if mode == MODE_DETERMINISTIC:
        if strategy not in DETERMINISTIC_STRATEGIES:
            raise ValueError(
                f"strategy must be one of {DETERMINISTIC_STRATEGIES}, got {strategy!r}"
            )
        if strategy == STRATEGY_START:
            start = 0
        else:
            anchor = _anchor_sample(p_sample, s_sample, strategy)
            start = 0 if anchor is None else anchor - window_length // 2
    else:
        if not (0.0 <= min_pick_fraction <= max_pick_fraction <= 1.0):
            raise ValueError(
                f"pick fractions must satisfy 0 <= min <= max <= 1, got "
                f"({min_pick_fraction}, {max_pick_fraction})"
            )
        generator = _resolve_rng(rng, seed)
        anchor = p_sample if p_sample is not None else s_sample
        if anchor is None:
            start = int(generator.integers(0, max_start + 1))
        else:
            low = int(round(min_pick_fraction * window_length))
            high = int(round(max_pick_fraction * window_length))
            high = max(high, low)
            offset = int(generator.integers(low, high + 1))
            start = anchor - offset

    return int(min(max(start, 0), max_start))


def extract_window(
    waveform: npt.NDArray[np.floating],
    p_sample: int | None,
    s_sample: int | None,
    *,
    start: int,
    window_length: int,
    sampling_rate: float = DEFAULT_SAMPLING_RATE,
    validate: bool = True,
    expected_length: int | None = None,
) -> Window:
    """Cut ``[start, start + window_length)`` and attach the picks as window indices (§4.4).

    ``validate`` runs :func:`seismonet.validation.validate_waveform` on the source record first;
    an invalid record raises ``ValueError`` with the validation detail (the same contract the
    loader's inference path uses).  ``expected_length`` lets a shorter synthetic fixture share
    the path; pass ``None`` to skip the length check.
    """
    arr = np.asarray(waveform)
    if validate:
        result: ValidationResult = validate_waveform(arr, expected_length=expected_length)
        if not result.ok:
            raise ValueError(result.detail)
    if arr.ndim != 2:
        raise ValueError(f"waveform must be 2-D (3, npts), got shape {arr.shape}")
    npts = arr.shape[1]
    _validate_window_request(npts, window_length)
    if not (0 <= start <= npts - window_length):
        raise ValueError(
            f"start {start} outside [0, {npts - window_length}] for npts={npts}, "
            f"window_length={window_length}"
        )
    if sampling_rate <= 0:
        raise ValueError(f"sampling_rate must be > 0, got {sampling_rate}")

    window = arr[:, start : start + window_length].astype(np.float64, copy=True)
    return Window(
        waveform=window,
        start=int(start),
        length=int(window_length),
        p_index=_index_in_window(p_sample, start, window_length),
        s_index=_index_in_window(s_sample, start, window_length),
        sampling_rate=float(sampling_rate),
    )


def prepare_window(
    waveform: npt.NDArray[np.floating],
    p_sample: int | None,
    s_sample: int | None,
    *,
    window_length: int = DEFAULT_WINDOW_LENGTH,
    mode: str = MODE_DETERMINISTIC,
    strategy: str = STRATEGY_CENTER_MIDPOINT,
    rng: np.random.Generator | None = None,
    seed: int | None = None,
    sampling_rate: float = DEFAULT_SAMPLING_RATE,
    validate: bool = True,
    expected_length: int | None = None,
) -> Window:
    """Select a start (deterministic for val/test, random for train) and cut the window.

    This is the single configurable window-extraction entry point (FR-017/FR-018): the same
    function is used by the training and evaluation paths with different ``mode`` values, so
    preprocessing cannot silently diverge between them (FR-020).
    """
    npts = int(np.asarray(waveform).shape[1])
    start = select_window_start(
        npts,
        window_length,
        p_sample=p_sample,
        s_sample=s_sample,
        mode=mode,
        strategy=strategy,
        rng=rng,
        seed=seed,
    )
    return extract_window(
        waveform,
        p_sample,
        s_sample,
        start=start,
        window_length=window_length,
        sampling_rate=sampling_rate,
        validate=validate,
        expected_length=expected_length,
    )


# --------------------------------------------------------------------------------------
# FR-019 — pure-noise windows (gated on verification)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PureNoisePlan:
    """Whether a pure-noise window fraction may be applied (FR-019 / DR-007)."""

    fraction: float
    requested: bool
    verified: bool
    active: bool
    reason: str

    def summary(self) -> dict[str, object]:
        return {
            "fraction": self.fraction,
            "requested": self.requested,
            "verified": self.verified,
            "active": self.active,
            "reason": self.reason,
        }


def plan_pure_noise(
    fraction: float,
    verification: NoiseVerification | None,
    *,
    requested: bool = True,
) -> PureNoisePlan:
    """Decide whether a configured pure-noise fraction is allowed to take effect.

    The fraction is **inert unless the noise metadata has been verified** (FR-019 + DR-007):
    ``active`` requires ``requested and fraction > 0 and verification.ok``.  A missing or failing
    verification yields ``active=False`` with a reason naming what is missing, so the config can
    carry a fraction that simply does nothing until the evidence exists.
    """
    if not (0.0 <= fraction <= 1.0):
        raise ValueError(f"noise fraction must be in [0, 1], got {fraction}")
    if not requested:
        return PureNoisePlan(
            fraction=float(fraction),
            requested=False,
            verified=bool(verification and verification.ok),
            active=False,
            reason="pure-noise windows not requested",
        )
    if fraction == 0.0:
        return PureNoisePlan(
            fraction=0.0,
            requested=True,
            verified=bool(verification and verification.ok),
            active=False,
            reason="fraction is 0.0: no pure-noise windows",
        )
    if verification is None:
        return PureNoisePlan(
            fraction=float(fraction),
            requested=True,
            verified=False,
            active=False,
            reason="no noise metadata verified: run seismonet.metadata.verify_noise_metadata first (DR-007)",
        )
    if not verification.ok:
        return PureNoisePlan(
            fraction=float(fraction),
            requested=True,
            verified=False,
            active=False,
            reason=f"noise metadata verification failed: {verification.reasons}",
        )
    return PureNoisePlan(
        fraction=float(fraction),
        requested=True,
        verified=True,
        active=True,
        reason=f"verified pure-noise source ({verification.n_rows} rows, no P/S columns)",
    )


def draw_pure_noise_mask(
    n: int,
    fraction: float,
    *,
    rng: np.random.Generator | None = None,
    seed: int | None = None,
) -> npt.NDArray[np.bool_]:
    """Boolean mask marking which of ``n`` windows are pure noise (FR-019).

    Each window is independently pure-noise with probability ``fraction`` — the acceptance
    criterion is "config fraction is respected within sampling error".  Deterministic for a
    given ``seed``/``rng``.  Callers build the window's targets with ``make_targets(L, None,
    None)`` (all-zero P/S, noise = 1), never by relabelling a real pick.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if not (0.0 <= fraction <= 1.0):
        raise ValueError(f"fraction must be in [0, 1], got {fraction}")
    if n == 0:
        return np.zeros(0, dtype=bool)
    if fraction <= 0.0:
        return np.zeros(n, dtype=bool)
    if fraction >= 1.0:
        return np.ones(n, dtype=bool)
    generator = _resolve_rng(rng, seed)
    return generator.random(n) < fraction


# --------------------------------------------------------------------------------------
# OQ-4 / OQ-8 — window-length assessment (provisional until VRAM measured)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class WindowLengthAssessment:
    """Evidence for one candidate window length (OQ-4).  Always provisional pre-VRAM."""

    length: int
    seconds: float
    depth: int
    depth_compatible: bool
    contains_all_p_from_offset_zero: bool
    guarantees_p_and_s_in_one_window: bool
    span_coverage: float | None
    decision: str
    provisional: bool
    vram_status: str
    input_batch_bytes: int
    notes: tuple[str, ...]

    def summary(self) -> dict[str, object]:
        return {
            "length": self.length,
            "seconds": self.seconds,
            "depth": self.depth,
            "depth_compatible": self.depth_compatible,
            "contains_all_p_from_offset_zero": self.contains_all_p_from_offset_zero,
            "guarantees_p_and_s_in_one_window": self.guarantees_p_and_s_in_one_window,
            "span_coverage": self.span_coverage,
            "decision": self.decision,
            "provisional": self.provisional,
            "vram_status": self.vram_status,
            "input_batch_bytes": self.input_batch_bytes,
            "notes": list(self.notes),
        }


def evaluate_window_length(
    length: int,
    *,
    depth: int = 4,
    sampling_rate: float = DEFAULT_SAMPLING_RATE,
    arrival: ArrivalDistribution = INSTANCE_ARRIVAL_DISTRIBUTION,
    span_coverages: dict[int, float] | None = MEASURED_SPAN_COVERAGE_10K,
    batch_size: int = 8,
    vram_measured: bool = False,
) -> WindowLengthAssessment:
    """Assess one candidate window length against arrivals, depth and the VRAM budget (OQ-4).

    The ``decision`` is one of:

    * ``"reject-for-depth"`` — not divisible by ``2**depth`` (``FR-036``); e.g. 3000.
    * ``"test-only"`` — usable only as the fast unit-test window (128).
    * ``"provisional-production"`` — plausible production length pending measured VRAM.

    ``vram_measured=False`` (the default, and the only truthfully available value until a real
    batch runs) forces ``provisional=True`` and ``vram_status="not_measured"`` for every length,
    so nothing downstream can read the assessment as a closed decision.
    """
    if length <= 0:
        raise ValueError(f"length must be > 0, got {length}")

    compatible = is_compatible(length, depth)
    coverage = span_coverages.get(length) if span_coverages else None
    notes: list[str] = []

    contains_all_p = arrival.p_max < length
    guarantees = length >= arrival.max_span_upper_bound
    if not contains_all_p:
        notes.append(
            f"P reaches sample {arrival.p_max} (max) > {length}; a fixed 0:L window cannot contain "
            f"all P, so a pick-centred start strategy is required (FR-018)."
        )
    if not guarantees:
        notes.append(
            f"conservative per-trace P->S span may reach {arrival.max_span_upper_bound} samples "
            f"(s_max - p_min + 1); {length} does not guarantee both picks in one window."
        )
    if coverage is not None:
        notes.append(f"measured span coverage (both picks) = {coverage:.4f} ({MEASURED_SPAN_COVERAGE_SOURCE}).")
    if arrival.s_missing_fraction > 0:
        notes.append(
            f"{arrival.s_missing_fraction:.1%} of traces have no S pick; those windows get an "
            f"all-zero S target (FR-024) regardless of length."
        )

    if not compatible:
        decision = "reject-for-depth"
        notes.append(f"{length} is not divisible by 2**{depth}={1 << depth}; decoder skips misalign (FR-036).")
    elif length <= 256:
        decision = "test-only"
        notes.append(
            "fast unit-test window only; coverage is far below the production requirement "
            "(measured INSTANCE coverage ≈ {:.2%}).".format(coverage if coverage is not None else float("nan"))
        )
    else:
        decision = "provisional-production"

    vram_status = "measured" if vram_measured else "not_measured"
    batch_bytes = tensor_bytes(length, batch_size)
    notes.append(
        f"input tensor at batch {batch_size} = {batch_bytes} bytes; activation memory is not "
        f"modelled and must be measured before OQ-4 closes."
    )

    return WindowLengthAssessment(
        length=int(length),
        seconds=window_length_seconds(length, sampling_rate),
        depth=int(depth),
        depth_compatible=compatible,
        contains_all_p_from_offset_zero=contains_all_p,
        guarantees_p_and_s_in_one_window=guarantees,
        span_coverage=coverage,
        decision=decision,
        provisional=not vram_measured,
        vram_status=vram_status,
        input_batch_bytes=batch_bytes,
        notes=tuple(notes),
    )


def evaluate_window_lengths(
    lengths: Sequence[int] = PROVISIONAL_WINDOW_LENGTHS,
    *,
    depth: int = 4,
    sampling_rate: float = DEFAULT_SAMPLING_RATE,
    arrival: ArrivalDistribution = INSTANCE_ARRIVAL_DISTRIBUTION,
    span_coverages: dict[int, float] | None = MEASURED_SPAN_COVERAGE_10K,
    batch_size: int = 8,
    vram_measured: bool = False,
) -> list[WindowLengthAssessment]:
    """Assess several candidate lengths (default 128/3000/3072/4000) — the OQ-4 decision input."""
    if depth < 0:
        raise ValueError(f"depth must be >= 0, got {depth}")
    return [
        evaluate_window_length(
            length,
            depth=depth,
            sampling_rate=sampling_rate,
            arrival=arrival,
            span_coverages=span_coverages,
            batch_size=batch_size,
            vram_measured=vram_measured,
        )
        for length in lengths
    ]


__all__ = [
    "ArrivalDistribution",
    "BoundaryCheck",
    "DEFAULT_MAX_PICK_FRACTION",
    "DEFAULT_MIN_PICK_FRACTION",
    "DEFAULT_SAMPLING_RATE",
    "DEFAULT_WINDOW_LENGTH",
    "DETERMINISTIC_STRATEGIES",
    "INSTANCE_ARRIVAL_DISTRIBUTION",
    "MEASURED_SPAN_COVERAGE_10K",
    "MEASURED_SPAN_COVERAGE_SOURCE",
    "MODE_DETERMINISTIC",
    "MODE_RANDOM",
    "PROVISIONAL_STATUS",
    "PROVISIONAL_WINDOW_LENGTHS",
    "PureNoisePlan",
    "STRATEGY_CENTER_MIDPOINT",
    "STRATEGY_CENTER_P",
    "STRATEGY_START",
    "WINDOW_MODES",
    "Window",
    "WindowLengthAssessment",
    "check_window_boundary",
    "draw_pure_noise_mask",
    "evaluate_window_length",
    "evaluate_window_lengths",
    "extract_window",
    "plan_pure_noise",
    "prepare_window",
    "select_window_start",
    "span_coverage",
    "tensor_bytes",
]

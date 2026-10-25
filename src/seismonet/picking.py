"""Small, deterministic P/S peak-picking helpers for validation inference.

The picker deliberately does not tune on ground-truth arrival positions.  It selects the strongest
local maximum above a configured phase-specific probability threshold.  The minimum separation is
used while suppressing nearby candidate maxima, and all arithmetic stays in sample indices until a
caller explicitly converts a window-relative index to the original trace index.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class PeakPickingConfig:
    """Frozen validation-time picking and matching settings.

    Thresholds are probabilities in ``[0, 1]``.  ``min_peak_distance_samples`` suppresses nearby
    local maxima before the strongest remaining maximum is selected.  ``matching_tolerance`` is
    only for reporting detection metrics; it never changes the predicted position.
    """

    p_threshold: float = 0.5
    s_threshold: float = 0.5
    min_peak_distance_samples: int = 20
    matching_tolerance_samples: int = 20

    def validate(self) -> None:
        for name, value in (("p_threshold", self.p_threshold), ("s_threshold", self.s_threshold)):
            if not np.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and in [0, 1], got {value!r}")
        if self.min_peak_distance_samples <= 0:
            raise ValueError(
                "min_peak_distance_samples must be > 0, "
                f"got {self.min_peak_distance_samples}"
            )
        if self.matching_tolerance_samples < 0:
            raise ValueError(
                "matching_tolerance_samples must be >= 0, "
                f"got {self.matching_tolerance_samples}"
            )


@dataclass(frozen=True)
class Pick:
    """A single accepted window-relative pick."""

    index: int
    probability: float


@dataclass(frozen=True)
class PeakPickDiagnostics:
    """Auditable details about candidate selection for one phase curve.

    The existing :func:`pick_phase` API intentionally returns only ``Pick | None``.  This companion
    result keeps that API stable while making protocol-level reporting possible: a run can state
    how many candidates were above threshold, whether an edge activation was rejected, and whether
    nearby candidates were suppressed.
    """

    pick: Pick | None
    candidate_count: int
    retained_candidate_count: int
    edge_activation: bool
    no_candidate_reason: str | None


def _local_maxima(curve: npt.ArrayLike, threshold: float) -> list[int]:
    values = np.asarray(curve, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError(f"probability curve must be 1-D, got shape {values.shape}")
    if values.size < 3:
        return []
    if not np.isfinite(values).all():
        raise ValueError("probability curve contains non-finite values")
    interior = np.arange(1, values.size - 1)
    is_peak = (
        (values[1:-1] >= values[:-2])
        & (values[1:-1] >= values[2:])
        & (values[1:-1] >= threshold)
    )
    return [int(index) for index in interior[is_peak]]


def pick_phase_diagnostics(
    probability_curve: npt.ArrayLike,
    *,
    threshold: float,
    min_peak_distance_samples: int = 20,
) -> PeakPickDiagnostics:
    """Return a pick plus deterministic candidate-selection diagnostics.

    Endpoints are not considered local maxima, so an edge-only activation produces no fabricated
    pick.  Nearby candidates are considered from highest to lowest probability and a candidate is
    retained only when it is at least ``min_peak_distance_samples`` from an already retained
    candidate.  Because the public result contains one pick, the first retained candidate is the
    strongest non-suppressed peak.
    """

    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be finite and in [0, 1], got {threshold!r}")
    if min_peak_distance_samples <= 0:
        raise ValueError(
            "min_peak_distance_samples must be > 0, "
            f"got {min_peak_distance_samples}"
        )
    values = np.asarray(probability_curve, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError(f"probability curve must be 1-D, got shape {values.shape}")
    if values.size == 0:
        return PeakPickDiagnostics(
            pick=None,
            candidate_count=0,
            retained_candidate_count=0,
            edge_activation=False,
            no_candidate_reason="empty_curve",
        )
    if not np.isfinite(values).all():
        raise ValueError("probability curve contains non-finite values")

    candidates = _local_maxima(values, float(threshold))
    if not candidates:
        edge_activation = bool(
            values.size > 0
            and (values[0] >= threshold or values[-1] >= threshold)
        )
        return PeakPickDiagnostics(
            pick=None,
            candidate_count=0,
            retained_candidate_count=0,
            edge_activation=edge_activation,
            no_candidate_reason=(
                "edge_only" if edge_activation else "no_interior_peak_above_threshold"
            ),
        )
    ranked = sorted(candidates, key=lambda index: (-float(values[index]), index))
    retained: list[int] = []
    for index in ranked:
        if all(abs(index - previous) >= min_peak_distance_samples for previous in retained):
            retained.append(index)
    if not retained:
        return PeakPickDiagnostics(
            pick=None,
            candidate_count=len(candidates),
            retained_candidate_count=0,
            edge_activation=False,
            no_candidate_reason="all_candidates_suppressed",
        )
    index = retained[0]
    return PeakPickDiagnostics(
        pick=Pick(index=index, probability=float(values[index])),
        candidate_count=len(candidates),
        retained_candidate_count=len(retained),
        edge_activation=False,
        no_candidate_reason=None,
    )


def pick_phase(
    probability_curve: npt.ArrayLike,
    *,
    threshold: float,
    min_peak_distance_samples: int = 20,
) -> Pick | None:
    """Return the strongest accepted local maximum, or ``None`` when no peak is accepted."""

    return pick_phase_diagnostics(
        probability_curve,
        threshold=threshold,
        min_peak_distance_samples=min_peak_distance_samples,
    ).pick


def pick_phases(
    probabilities: npt.ArrayLike,
    config: PeakPickingConfig,
) -> Mapping[str, Pick | None]:
    """Pick P and S independently from a ``(3, L)`` P/S/noise probability array."""

    config.validate()
    values = np.asarray(probabilities, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] != 3:
        raise ValueError(f"probabilities must have shape (3, L), got {values.shape}")
    if not np.isfinite(values).all():
        raise ValueError("probabilities contain non-finite values")
    return {
        "P": pick_phase(
            values[0],
            threshold=config.p_threshold,
            min_peak_distance_samples=config.min_peak_distance_samples,
        ),
        "S": pick_phase(
            values[1],
            threshold=config.s_threshold,
            min_peak_distance_samples=config.min_peak_distance_samples,
        ),
    }


def window_relative_to_trace_sample(
    window_start: int,
    relative_index: int | None,
    *,
    window_length: int,
) -> int | None:
    """Convert a window-relative index to its original trace sample index.

    ``None`` stays ``None`` so absent predictions and missing reference picks cannot become sample
    zero.  An index outside the window is rejected rather than silently clamped.
    """

    if window_start < 0:
        raise ValueError(f"window_start must be >= 0, got {window_start}")
    if window_length <= 0:
        raise ValueError(f"window_length must be > 0, got {window_length}")
    if relative_index is None:
        return None
    if not 0 <= relative_index < window_length:
        raise ValueError(
            f"relative_index {relative_index} outside [0, {window_length})"
        )
    return int(window_start + relative_index)


def absolute_timing_error_samples(predicted: int | None, reference: int | None) -> int | None:
    """Return absolute timing error in samples, or ``None`` when either pick is absent."""

    if predicted is None or reference is None:
        return None
    return abs(int(predicted) - int(reference))


def samples_to_milliseconds(error_samples: int | None, sampling_rate: float) -> float | None:
    """Convert a non-negative sample error to milliseconds."""

    if sampling_rate <= 0:
        raise ValueError(f"sampling_rate must be > 0, got {sampling_rate}")
    if error_samples is None:
        return None
    if error_samples < 0:
        raise ValueError(f"error_samples must be >= 0, got {error_samples}")
    return float(error_samples) * 1000.0 / float(sampling_rate)


__all__ = [
    "PeakPickingConfig",
    "PeakPickDiagnostics",
    "Pick",
    "absolute_timing_error_samples",
    "pick_phase",
    "pick_phase_diagnostics",
    "pick_phases",
    "samples_to_milliseconds",
    "window_relative_to_trace_sample",
]

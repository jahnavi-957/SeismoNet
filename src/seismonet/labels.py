"""P/S target generation — PRD FR-021..FR-024, SR-006, REPRODUCIBILITY §6, ARCH §5.

Conventions (matching PRD §4 and TECHNICAL_ARCHITECTURE):
- Window shape: (C=3, L)  — channels Z, N, E.
- Targets shape: (3, L) — channels [P, S, noise], noise = remainder = 1 - P - S (clipped).
- P and S targets are Gaussian-shaped, peak == 1.0 at the pick index.
- Noise target is 1 - P - S, clipped to [0, 1]; never negative.
- If a phase is absent (pick is None), its target is all zeros.
- Window length L, pick indices, and sigma are explicit arguments (FR-077: config-driven, no hard codes).
"""
from __future__ import annotations

import numpy as np
import numpy.typing as npt


def _gaussian(length: int, center: int, sigma: float) -> npt.NDArray[np.float64]:
    """Unnormalised Gaussian with peak 1.0 at center, truncated to [0, length)."""
    x = np.arange(length, dtype=np.float64)
    # exp(-0.5 * ((x - center)/sigma)^2)
    g = np.exp(-0.5 * ((x - center) / sigma) ** 2)
    return g


def make_targets(
    window_length: int,
    p_idx: int | None,
    s_idx: int | None,
    sigma: float = 10.0,
) -> npt.NDArray[np.float64]:
    """Generate P/S/noise target curves for one window.

    Returns array of shape (3, window_length), dtype float64, in channel order [P, S, noise].

    Invariants (tested):
      - shape == (3, L)
      - values in [0, 1]
      - noise == clip(1 - P - S, 0, 1)
      - P+S+noise == 1 (within float tolerance) — FR-023
      - peak of P at p_idx (if present), similarly S — FR-022
      - absent phase -> all zeros — FR-024
    """
    if window_length <= 0:
        raise ValueError(f"window_length must be >0, got {window_length}")
    if sigma <= 0:
        raise ValueError(f"sigma must be >0, got {sigma}")

    p = np.zeros(window_length, dtype=np.float64)
    s = np.zeros(window_length, dtype=np.float64)

    if p_idx is not None:
        if not (0 <= p_idx < window_length):
            raise ValueError(f"p_idx {p_idx} out of bounds for length {window_length}")
        p = _gaussian(window_length, p_idx, sigma)

    if s_idx is not None:
        if not (0 <= s_idx < window_length):
            raise ValueError(f"s_idx {s_idx} out of bounds for length {window_length}")
        s = _gaussian(window_length, s_idx, sigma)

    noise = 1.0 - p - s
    # When P and S overlap (near-source), 1-P-S can go negative at overlap peak; clip.
    noise = np.clip(noise, 0.0, 1.0)

    # Stack as (3, L) with noise as third channel.
    targets = np.stack([p, s, noise], axis=0)
    return targets

"""Window depth/length compatibility — PRD FR-017, FR-036, SR-004/SR-008, T-036.

A 1D U-Net with stride-2 downsampling needs the window length divisible by 2**depth,
otherwise the decoder's skip connections cannot align (TECHNICAL_ARCHITECTURE §7).
"""
from __future__ import annotations


def check_window_depth_compatible(window_length: int, depth: int) -> None:
    if window_length <= 0:
        raise ValueError(f"window_length must be >0, got {window_length}")
    if depth < 0:
        raise ValueError(f"depth must be >=0, got {depth}")
    divisor = 1 << depth  # 2**depth
    if window_length % divisor != 0:
        raise ValueError(
            f"window_length {window_length} is not divisible by 2**depth (2**{depth}={divisor}); "
            f"decoder skip connections would misalign. Choose a length divisible by {divisor} "
            f"(e.g. 3072 for depth 4) or change depth (FR-036)."
        )


def is_compatible(window_length: int, depth: int) -> bool:
    try:
        check_window_depth_compatible(window_length, depth)
        return True
    except ValueError:
        return False

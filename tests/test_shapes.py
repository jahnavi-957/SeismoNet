"""Window depth/length compatibility — FR-036/FR-017, SR-004/SR-008, T-036."""
import pytest

from seismonet.shapes import check_window_depth_compatible, is_compatible


def test_compatible_lengths_pass():
    assert is_compatible(3072, 4)  # 3072 % 16 == 0, the PRD example
    assert is_compatible(128, 4)   # 128 % 16 == 0
    assert is_compatible(128, 3)   # 128 % 8 == 0
    assert is_compatible(64, 0)    # any length for depth 0


def test_incompatible_raises_with_message():
    with pytest.raises(ValueError, match="not divisible by 2\\*\\*depth"):
        check_window_depth_compatible(3001, 4)  # 3001 % 16 != 0 — PhaseNet's original, incompatible with depth 4
    with pytest.raises(ValueError, match="not divisible"):
        check_window_depth_compatible(100, 3)


def test_is_compatible_false_for_incompatible():
    assert not is_compatible(100, 3)
    assert not is_compatible(3001, 4)


def test_bad_args_raise():
    with pytest.raises(ValueError):
        check_window_depth_compatible(0, 2)
    with pytest.raises(ValueError):
        check_window_depth_compatible(64, -1)

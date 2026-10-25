"""Augmentation independence, training-only gating and label consistency — FR-028..FR-031.

Synthetic waveforms and fixed seeds only; augmentation is never applied to a real HDF5 record in
these tests (the policy is: synthetic alignment first).
"""
import numpy as np
import pytest

from seismonet.augmentation import (
    SHIFT_MODE_REFLECT,
    SHIFT_MODE_WRAP,
    SHIFT_MODE_ZERO,
    AugmentationConfig,
    TrainingAugmenter,
    apply_augmentations,
    enabled_names,
    shift_pick,
    shift_signal,
)


@pytest.fixture
def waveform(rng):
    return rng.normal(size=(3, 128)).astype(np.float64)


# --------------------------------------------------------------------------------------
# FR-028 — independent switchability
# --------------------------------------------------------------------------------------


def test_all_disabled_returns_unchanged(waveform):
    sample = apply_augmentations(
        waveform, 30, 80, config=AugmentationConfig(), training=True, seed=0
    )
    assert np.array_equal(sample.waveform, waveform)
    assert (sample.p_index, sample.s_index) == (30, 80)
    assert sample.applied == ()


def test_enabled_names_reflects_flags():
    config = AugmentationConfig(amplitude_scale_enabled=True, noise_enabled=True)
    assert set(enabled_names(config)) == {"amplitude_scale", "additive_noise"}
    assert config.any_enabled() is True
    assert AugmentationConfig().any_enabled() is False


def test_augmentation_requires_explicit_seed_when_enabled(waveform):
    config = AugmentationConfig(noise_enabled=True)
    with pytest.raises(ValueError):
        apply_augmentations(waveform, 30, 80, config=config, training=True)


def test_amplitude_scale_does_not_shift_indices(waveform):
    config = AugmentationConfig(
        amplitude_scale_enabled=True, amplitude_scale_min=2.0, amplitude_scale_max=2.0, seed=0
    )
    sample = apply_augmentations(waveform, 30, 80, config=config, training=True)
    assert (sample.p_index, sample.s_index) == (30, 80)
    assert np.allclose(sample.waveform, waveform * 2.0)
    # A fixed peak is still at the same index (FR-031 is trivially satisfied here).
    assert int(np.argmax(sample.targets(sigma=5.0)[0])) == 30


def test_noise_is_independently_switchable_from_scaling(waveform):
    # FR-029: noise alone, scaling off — indices unchanged, signal changed.
    noise_only = AugmentationConfig(noise_enabled=True, noise_relative_sigma=0.1, seed=0)
    sample = apply_augmentations(waveform, 30, 80, config=noise_only, training=True)
    assert sample.applied == ("additive_noise",)
    assert (sample.p_index, sample.s_index) == (30, 80)
    assert not np.array_equal(sample.waveform, waveform)


def test_enabling_noise_does_not_change_the_shift(waveform):
    # FR-028: the shift is drawn first, so turning noise on must not alter it.
    shift_only = AugmentationConfig(shift_enabled=True, shift_max_samples=6, seed=3)
    shift_and_noise = AugmentationConfig(
        shift_enabled=True, shift_max_samples=6, noise_enabled=True, noise_relative_sigma=0.1, seed=3
    )
    a = apply_augmentations(waveform, 40, 80, config=shift_only, training=True)
    b = apply_augmentations(waveform, 40, 80, config=shift_and_noise, training=True)
    assert a.p_index == b.p_index
    assert a.s_index == b.s_index
    assert a.applied[0] == b.applied[0]


# --------------------------------------------------------------------------------------
# FR-030 — training-only
# --------------------------------------------------------------------------------------


def test_not_training_returns_unchanged_even_with_everything_enabled(waveform):
    config = AugmentationConfig(
        amplitude_scale_enabled=True,
        noise_enabled=True,
        shift_enabled=True,
        shift_max_samples=10,
        seed=0,
    )
    # No rng/seed passed on the call: short-circuit must avoid resolving one at all.
    sample = apply_augmentations(waveform, 30, 80, config=config, training=False)
    assert np.array_equal(sample.waveform, waveform)
    assert (sample.p_index, sample.s_index) == (30, 80)
    assert sample.applied == ()


# --------------------------------------------------------------------------------------
# FR-031 — time shift moves labels consistently
# --------------------------------------------------------------------------------------


def test_shift_pick_helpers():
    assert shift_pick(40, 5, 128) == 45
    assert shift_pick(40, -5, 128) == 35
    assert shift_pick(125, 5, 128) is None  # leaves the window -> all-zero target
    assert shift_pick(2, -5, 128) is None
    assert shift_pick(None, 5, 128) is None


def test_shift_signal_zero_padding_positive():
    signal = np.arange(6, dtype=float).reshape(1, 6)
    shifted = shift_signal(signal, 2, mode=SHIFT_MODE_ZERO)
    assert np.array_equal(shifted[0], [0, 0, 0, 1, 2, 3])


def test_shift_signal_zero_padding_negative():
    signal = np.arange(6, dtype=float).reshape(1, 6)
    shifted = shift_signal(signal, -2, mode=SHIFT_MODE_ZERO)
    assert np.array_equal(shifted[0], [2, 3, 4, 5, 0, 0])


def test_shift_signal_wrap_and_reflect_preserve_length():
    signal = np.arange(6, dtype=float).reshape(1, 6)
    wrapped = shift_signal(signal, 2, mode=SHIFT_MODE_WRAP)
    assert np.array_equal(wrapped, np.roll(signal, 2, axis=1))
    reflected = shift_signal(signal, 2, mode=SHIFT_MODE_REFLECT)
    assert reflected.shape == signal.shape
    assert np.array_equal(reflected[0], [2, 1, 0, 1, 2, 3])


def test_shift_larger_than_window_zeroes_signal():
    signal = np.ones((1, 4))
    assert np.all(shift_signal(signal, 10, mode=SHIFT_MODE_ZERO) == 0.0)


def test_time_shift_moves_waveform_labels_and_targets(waveform):
    config = AugmentationConfig(shift_enabled=True, shift_max_samples=5, seed=3)
    sample = apply_augmentations(waveform, 40, 80, config=config, training=True)
    # Recover the applied shift from the recorded descriptor (deterministic given the seed).
    shift = int(sample.applied[0].split(":")[1])

    p_expected = 40 + shift if 0 <= 40 + shift < waveform.shape[1] else None
    s_expected = 80 + shift if 0 <= 80 + shift < waveform.shape[1] else None
    assert sample.p_index == p_expected
    assert sample.s_index == s_expected

    if sample.p_index is not None:
        # The P target peak tracks the shifted pick exactly (FR-031).
        assert int(np.argmax(sample.targets(sigma=5.0)[0])) == sample.p_index
        # Interior samples are the shifted originals.
        if shift > 0:
            assert np.allclose(sample.waveform[:, shift:], waveform[:, : waveform.shape[1] - shift])
        elif shift < 0:
            assert np.allclose(sample.waveform[:, : shift], waveform[:, -shift:])


def test_time_shift_out_of_window_becomes_none():
    # A shift drawn from a range large enough to push P out of the window.
    config = AugmentationConfig(shift_enabled=True, shift_max_samples=200, seed=0)
    sample = apply_augmentations(np.ones((3, 64)), 5, 60, config=config, training=True)
    shift = int(sample.applied[0].split(":")[1])
    expected_p = 5 + shift if 0 <= 5 + shift < 64 else None
    assert sample.p_index == expected_p
    if sample.p_index is None:
        assert np.all(sample.targets(sigma=5.0)[0] == 0.0)


# --------------------------------------------------------------------------------------
# Noise behaviour
# --------------------------------------------------------------------------------------


def test_zero_sigma_noise_is_a_noop(waveform):
    config = AugmentationConfig(noise_enabled=True, noise_relative_sigma=0.0, seed=0)
    sample = apply_augmentations(waveform, 30, 80, config=config, training=True)
    assert np.allclose(sample.waveform, waveform)
    assert (sample.p_index, sample.s_index) == (30, 80)


def test_noise_magnitude_tracks_relative_sigma(waveform):
    config = AugmentationConfig(noise_enabled=True, noise_relative_sigma=0.2, noise_per_channel=True, seed=0)
    sample = apply_augmentations(waveform, 30, 80, config=config, training=True)
    difference = sample.waveform - waveform
    expected = 0.2 * waveform.std(axis=1)
    observed = difference.std(axis=1)
    assert np.allclose(observed, expected, rtol=0.3)


def test_absolute_noise_sigma_is_honoured(waveform):
    config = AugmentationConfig(noise_enabled=True, noise_absolute_sigma=0.5, seed=0)
    sample = apply_augmentations(waveform, 30, 80, config=config, training=True)
    difference = sample.waveform - waveform
    assert difference.std() == pytest.approx(0.5, rel=0.2)


# --------------------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------------------


def test_same_seed_is_byte_identical(waveform):
    config = AugmentationConfig(
        shift_enabled=True, shift_max_samples=8, amplitude_scale_enabled=True,
        noise_enabled=True, noise_relative_sigma=0.1, seed=11,
    )
    a = apply_augmentations(waveform, 40, 80, config=config, training=True)
    b = apply_augmentations(waveform, 40, 80, config=config, training=True)
    assert np.array_equal(a.waveform, b.waveform)
    assert (a.p_index, a.s_index) == (b.p_index, b.s_index)
    assert a.applied == b.applied


def test_training_augmenter_is_reproducible_from_seed(waveform):
    config = AugmentationConfig(noise_enabled=True, noise_relative_sigma=0.1, shift_enabled=True, shift_max_samples=4)
    first = TrainingAugmenter(config, seed=7)
    second = TrainingAugmenter(config, seed=7)
    a = first(waveform, 40, 80)
    b = second(waveform, 40, 80)
    assert np.array_equal(a.waveform, b.waveform)


def test_config_validation_rejects_bad_values():
    with pytest.raises(ValueError):
        apply_augmentations(
            np.ones((3, 16)), 4, 8,
            config=AugmentationConfig(amplitude_scale_enabled=True, amplitude_scale_min=-1.0, amplitude_scale_max=1.0),
            training=True, seed=0,
        )
    with pytest.raises(ValueError):
        apply_augmentations(
            np.ones((3, 16)), 4, 8,
            config=AugmentationConfig(shift_enabled=True, shift_mode="bogus"),
            training=True, seed=0,
        )

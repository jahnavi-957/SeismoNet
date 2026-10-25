"""SeismoNet — 1D U-Net phase-picking pipeline.

Source layout:
    src/seismonet/validation.py  — waveform validation (FR-003/FR-008)
    src/seismonet/labels.py      — Gaussian P/S target generation (FR-021..FR-024)
    src/seismonet/time_utils.py  — sample-index <-> time conversion (FR-053)
    src/seismonet/shapes.py      — window depth/length compatibility (FR-036/FR-017)
    src/seismonet/split.py       — deterministic event-level splitting (FR-004..FR-006)
    src/seismonet/metrics.py     — evaluation metrics (FR-055..)
    src/seismonet/metadata.py    — event-id construction + stratification (FR-010/FR-011)
    src/seismonet/windowing.py   — windowing/preprocessing + window-length assessment (FR-017..FR-019)
    src/seismonet/augmentation.py— training-only augmentations (FR-028..FR-031)
"""

# 2026-10-17-022 — Validation-only phase-picking inference and visualization

## A. Change identification

- **Change ID:** 2026-10-17-022
- **Date and time:** 2026-10-17 (validation inference completed after the bounded pilot)
- **Short title:** Phase-picking inference and validation figures
- **Category:** feature / experiment
- **Files created / modified / removed:**
  - Created `src/seismonet/picking.py` with configurable P/S peak picking and sample-offset
    conversion helpers.
  - Created `src/seismonet/validation_inference.py`, a validation-only inference and reporting
    entry point.
  - Created `tests/test_picking.py` with six focused tests.
  - Created ignored outputs under `runs/validation_inference_seed42/`: `run.json`,
    `picking_config.json`, `metrics.json`, `predictions.csv`, `predictions.json`,
    `validation_report.md`, and three figures.
  - Modified `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`, and
    `docs/PROJECT_STATUS.md`.
  - The existing model, data pipeline, split files, pilot checkpoint, and pilot output files were
    read but not modified.

## B. What was changed?

The saved `runs/pilot_seed42/best.pt` checkpoint was loaded with
`torch.load(..., weights_only=True)`, placed in evaluation mode, and used under
`torch.no_grad()` for the exact 210-trace validation subset selected by the pilot.
The test split was never opened or evaluated.

A simple configurable picker was added:

- strongest interior local maximum on each P/S probability curve;
- phase threshold required for acceptance;
- edge-only activations rejected;
- nearby candidates suppressed with a 20-sample minimum distance;
- no accepted peak produces `None`, never a fabricated sample index.

The validation pass produced three deterministic figures containing the three waveform components,
window-offset/original trace sample coordinates, ground-truth P/S markers, predicted markers when
accepted, and P/S/noise probability curves. Predictions and metric denominators were retained for
all 210 traces, including missing-S cases and traces with no accepted prediction.

## C. Why was this change necessary?

The pilot established that the model could execute a training pipeline, but it did not show whether
its probability curves produced useful phase picks. This change supplies the smallest inference
and visualization slice needed to inspect that question without retraining, changing weights,
adding a dashboard, downloading more data, or touching the test split.

The validation window offset is part of the result. The implementation explicitly converts a
window-relative prediction back to `window_start + relative_index` and keeps missing or
out-of-window references as explicit statuses.

## D. Why was this approach chosen?

The strongest-local-maximum rule is intentionally simple and auditable for a college mini project.
It does not use ground-truth arrival positions to choose predicted positions. The initial
conservative thresholds were 0.5 for both phases. That produced no accepted P predictions, while
the S curve contained usable but noisy activations.

A small validation-only S-threshold sweep over `{0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40,
0.50}` selected `0.10` by the highest validation F1 at the fixed 20-sample matching tolerance.
The P threshold remained `0.50`: lower values produced many false peaks without useful validation
timing accuracy. This threshold choice is explicitly exploratory and optimistic because selection
and reporting use the same validation subset; it is not a frozen scientific protocol.

## E. How was it implemented?

`picking.py` provides `PeakPickingConfig`, `pick_phase`, `pick_phases`,
`window_relative_to_trace_sample`, `absolute_timing_error_samples`, and
`samples_to_milliseconds`. The inference entry point reads the saved pilot manifest to reconstruct
the selected validation events and reads only `splits/validation.csv` as a membership guard. It
does not open `splits/test.csv`.

The run used:

| Item | Value |
|---|---|
| Checkpoint | `runs/pilot_seed42/best.pt` |
| Loader | `weights_only=True`, `eval()`, `torch.no_grad()` |
| Validation traces | 210 from 8 pilot-selected validation events |
| Device | RTX 2050, CUDA PyTorch `2.14.1+cu126` |
| P threshold | 0.50 |
| S threshold | 0.10, selected by validation-only sweep |
| Peak separation | 20 samples |
| Matching tolerance | 20 samples = 200 ms at 100 Hz |

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** validation inference now produces reproducible P/S/noise curves,
  original-trace sample coordinates, prediction records, metric denominators, and three figures
  from the saved checkpoint without retraining.
- **VERIFIED improvement:** missing-S handling is explicit: 64 of 210 validation traces lacked S
  ground truth; timing metrics excluded those references, while accepted S predictions on them were
  counted as false positives (`37`).
- **VERIFIED finding:** at the selected rules, no P prediction was accepted on 210 P-labelled
  traces. P detection was `TP/FP/FN = 0/0/210`, with no timing pairs.
- **VERIFIED finding:** S produced 166 accepted predictions on 146 in-window S references and 64
  missing-S traces. Detection was `TP/FP/FN = 79/87/67`, precision `0.4759`, recall `0.5411`,
  and F1 `0.5064` at 20 samples. Timing error over 129 valid pairs was mean **38.73 samples /
  387.29 ms** and median **17 samples / 170 ms**.
- **HYPOTHESIS:** the P result suggests the tiny three-epoch model did not learn a usable P
  probability signal under this rule. This is a pipeline finding, not evidence that the architecture
  cannot learn P picks with an approved data/training protocol.

## G. Testing and verification

- **Tests added:** `tests/test_picking.py` (6 tests) covering accepted peaks, absent/below-threshold
  peaks, edge-only activation, invalid curves/configuration, missing S, window-offset conversion,
  timing error, and invalid offsets/rates.
- **Focused command:** `.venv\Scripts\python.exe -m pytest tests/test_picking.py tests/test_model.py -q`
  → **11 passed**.
- **Complete command:** `.venv\Scripts\python.exe -m pytest tests -q`
  → **199 passed, 1 skipped** in 14.02 s.
- **Test-set inference:** not run; the test split was not loaded, evaluated, or tuned.
- **Artifact check:** figures, JSON, CSV, and Markdown report exist under ignored
  `runs/validation_inference_seed42/`; the original `runs/pilot_seed42/` directory and split files
  remain unchanged.

## H. Risks and side effects

- The S threshold was selected and evaluated on the same validation subset, so the reported S
  detection numbers are exploratory and must not be treated as an unbiased estimate.
- P performance is a clear failure under the configured rule: lowering the threshold created false
  peaks rather than useful timing accuracy. No threshold was chosen to hide that result.
- The matching tolerance of 20 samples / 200 ms is provisional and not the project-wide frozen
  evaluation protocol.
- The small pilot and 210-trace validation subset do not support scientific generalization claims.
- Removing ignored `runs/validation_inference_seed42/` removes only inference artifacts. The pilot
  checkpoint and source changes remain separate.

## I. Relationship to the PRD and roadmap

This change supports the planned inference, visualization, timing-conversion, and validation
requirements (`FR-009`, `FR-012`, `FR-051`–`FR-059`, `FR-061`, `FR-064`–`FR-068`, `FR-084`,
`SR-011`, `SR-014`, `SR-016`). It is validation-only exploratory work and does not close the P5
protocol questions or constitute EX-1 scientific evaluation.

## J. Next steps

Do not change model weights based on this small validation result. The smallest appropriate fix is
to investigate P-target learning and the training/data protocol—especially P label/window coverage
and a separately approved threshold-selection protocol—before any larger run. Keep the test split
unused until the evaluation protocol is finalized. If the project remains a mini project, report
the current result honestly as: **S curves show limited, noisy signal; P picks were not recovered
under the conservative rule; no generalization claim is supported.**

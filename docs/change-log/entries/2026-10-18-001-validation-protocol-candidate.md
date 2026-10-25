# 2026-10-18-001 — Validation-only P5 protocol candidate

## A. Change identification

- **Change ID:** 2026-10-18-001
- **Date and time:** 2026-10-18 (after resuming the 2026-10-17 validation-inference work)
- **Short title:** Validation-only protocol candidate and evaluation diagnostics
- **Category:** feature / testing / documentation
- **Files created / modified / removed:**
  - Modified `src/seismonet/picking.py` with a non-breaking diagnostics API.
  - Modified `src/seismonet/validation_inference.py` with threshold sweeping, protocol writing,
    tested metric reuse, residual reporting and validation-run safety guards.
  - Modified `tests/test_picking.py` and created `tests/test_validation_inference.py`.
  - Modified `docs/REASONING_AND_DECISIONS.md`, `docs/REPRODUCIBILITY.md`,
    `docs/EXPERIMENT_PLAN.md`, `docs/PROJECT_STATUS.md`,
    `docs/change-log/CURRENT_STATUS.md`, and `docs/change-log/CHANGELOG.md`.
  - Created this entry.
  - Created ignored run outputs under `runs/validation_protocol_candidate_seed42/`:
    `protocol.json`, `picking_config.json`, `run.json`, `metrics.json`, `predictions.json`,
    `predictions.csv`, `validation_report.md`, and three figures.
  - Did not modify `splits/test.csv`, `splits/split.json`, pilot weights, or the prior validation
    run directory.

## B. What was changed?

The peak picker now exposes `PeakPickDiagnostics` and `pick_phase_diagnostics` while preserving the
existing `pick_phase(...) -> Pick | None` API. Each inference record retains candidate count,
retained-candidate count, edge activation, no-candidate reason, and whether the predicted P occurs
after the predicted S.

The validation inference entry point now:

- derives the sampling rate from the saved run configuration instead of assuming 100 Hz;
- runs one model forward pass and performs an actual independent threshold sweep for P and S;
- selects the highest validation F1, breaking ties by precision, recall and then higher threshold;
- recomputes detection metrics through `metrics.classify_picks` and timing summaries through
  `metrics.residuals` and `metrics.residual_stats`;
- reports signed residual mean, standard deviation, median and MAE in seconds and milliseconds;
- records missing-reference, out-of-window, no-pick, multi-peak, edge-only and P-after-S outcomes;
- writes a content-addressed `protocol.json` once and rejects overwriting an existing protocol or
  non-empty output directory; and
- keeps the validation-only guard that reads `splits/validation.csv` but never opens `splits/test.csv`.

The resulting candidate protocol is `protocol-5fa5744aca58cc3c`. It selected P `0.05` and S `0.10`
from the configured candidates at a 20-sample tolerance. On the same 210-trace validation subset,
P scored `TP/FP/FN = 1/205/209`, F1 `0.0048`; S scored `79/87/67`, F1 `0.5064`. These are
validation-only exploratory measurements, not test or generalization results.

## C. Why was this change necessary?

The saved work identified P5 protocol freeze as the next unfinished task. The previous inference pass
recorded a selected S threshold in prose and run metadata, but did not persist a dedicated immutable
protocol, did not implement the claimed sweep, and duplicated metric formulas locally. It also reported
timing in hard-coded 100-Hz units and did not count the protocol outcomes required by the roadmap.

Those gaps made it possible for a later run to silently change the threshold or tolerance and made
future validation and test evaluators vulnerable to diverging metric conventions. The safe continuation
was to make the validation protocol auditable without touching the test split or changing model
weights.

## D. Why was this approach chosen?

The change is deliberately validation-only. The pilot checkpoint is not eligible for a scientific
baseline because its lowest-validation-loss selection was recorded after the bounded run rather than
pre-registered. The protocol artifact therefore sets `test_evaluation_allowed` to `false` and labels
itself `candidate_validation_protocol`.

Independent per-phase threshold selection matches the existing P/S reporting requirement. Highest F1
is the declared operating objective; precision, recall and higher threshold are deterministic tie
breaks. The candidate values are not treated as universally correct: the same validation subset was
used for selection and reporting, so the measured numbers are explicitly optimistic/exploratory.

Reusing the tested metric functions avoids a second, drifting implementation of TP/FP/FN and residual
semantics. An immutable, content-addressed protocol prevents silent replacement and gives the future
test evaluator a concrete precondition to check.

## E. How was it implemented?

- `picking.py` added `PeakPickDiagnostics`; `pick_phase` delegates to the diagnostic implementation,
  so selection behavior remains unchanged while candidate and edge outcomes become observable.
- `validation_inference.py` added `_sweep_validation_thresholds`, `_records_for_picking_config`,
  and `_write_frozen_protocol`; it now uses the saved sampling rate and the tested metric module.
- `tests/test_picking.py` covers diagnostics for edge-only and suppressed multi-peak inputs.
- `tests/test_validation_inference.py` covers out-of-tolerance matching, missing and out-of-window
  references, non-100-Hz units, actual threshold selection, and protocol immutability.
- The validation run was executed with:

  ```powershell
  .venv\Scripts\python.exe -m seismonet.validation_inference --out runs/validation_protocol_candidate_seed42
  ```

  It produced three figures and complete JSON/CSV/Markdown artifacts for 210 validation traces.
  The command output reported `test_split_loaded: false`.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** protocol candidates and every threshold candidate's P/S detection counts
  are saved in a reviewable JSON artifact rather than only in prose.
- **VERIFIED improvement:** validation detection and residual calculations now use the same tested
  metric functions as the unit tests.
- **VERIFIED improvement:** timing tolerance and milliseconds are derived from the saved sampling
  rate; the implementation no longer assumes `10 ms/sample`.
- **VERIFIED improvement:** edge-only activation, no-pick, multi-peak and P-after-S outcomes are
  retained for failure analysis instead of being silently discarded.
- **EXPECTED improvement:** rejecting non-empty output directories and protocol overwrites reduces
  the risk of silently replacing a prior evaluation operating point.
- **HYPOTHESIS:** the very poor selected P F1 indicates that threshold tuning alone cannot rescue the
  current tiny pilot; this must be tested in a separately approved data/training investigation.

## G. Testing and verification

- **Tests added or modified:** one picking diagnostics test and six validation/protocol tests.
- **Focused command:** `.venv\Scripts\python.exe -m pytest tests/test_picking.py tests/test_metrics.py tests/test_validation_inference.py -q`
  → **24 passed**.
- **Full command:** `.venv\Scripts\python.exe -m pytest tests -q`
  → **206 passed, 1 skipped** in **18.33 s**.
- **Validation run:** executed on the saved 210-trace pilot validation subset; protocol and figures
  were written successfully; `test_split_loaded`, `test_split_evaluated` and
  `test_split_used_for_tuning` are all `false`.
- **Tests failed:** none.
- **Tests not run:** no test-set inference, no full scientific baseline, no Linux reproduction, and
  no EX-1/EX-2/EX-5 experiment; these are intentionally outside this validation-only slice.
- **Remaining limitations:** the threshold and tolerance are not owner-approved, the pilot checkpoint
  policy was not pre-registered, and the candidate is not authorized for test evaluation.

## H. Risks and side effects

- The candidate P threshold of `0.05` produces many false predictions; it is a measured failure mode,
  not a recommended production setting.
- Selection and reporting use the same validation subset, so the candidate metrics are optimistically
  biased and must not be reported as generalization evidence.
- The new non-empty-output guard means reruns require a new output directory; this is intentional for
  auditability. The prior `runs/validation_inference_seed42/` artifact remains intact.
- Rollback is possible by reverting the source/test/documentation changes in this entry; ignored run
  artifacts can be removed independently without changing source or split files.

## I. Relationship to the PRD and roadmap

This change advances P5 requirements `FR-049`–`FR-063`, especially `FR-051`, `FR-054`, `FR-055`,
`FR-056`, `FR-057`, `FR-058`, `FR-059`, `FR-061`, and `FR-062`; it also supports `FR-064`–`FR-068`,
`FR-084`, `SR-011`, `SR-014`, `SR-016`, and `NFR-003`. It fulfills a validation-only engineering
slice of the protocol workflow, but does not close `OQ-10`, `OQ-11`, `OQ-14`, `OQ-17` or `OQ-21`,
and does not constitute EX-1 or a test evaluation.

## J. Next steps

1. Review the candidate `protocol.json` with the owner/supervisor and decide whether the tolerance,
   matching rule, edge/P-after-S policies and per-phase threshold objective are acceptable.
2. Pre-register the checkpoint-selection criterion and obtain a new approved scientific baseline
   checkpoint; do not use the current pilot checkpoint for a headline test result.
3. Keep `splits/test.csv` untouched until those decisions are closed.
4. Investigate P label/window/training behavior separately; do not change weights ad hoc to hide the
   validation failure.

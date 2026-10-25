# 2026-10-18-002 — Validation-only figure suite (P6): thresholds, residual histograms, galleries

## A. Change identification

- **Change ID:** 2026-10-18-002
- **Date and time:** 2026-10-18 (resumed session; same day as 2026-10-18-001)
- **Short title:** Validation-only figure suite and failure analysis
- **Category:** feature / testing / documentation
- **Files created / modified / removed:**
  - Modified `src/seismonet/validation_inference.py` (threshold lines on the example figures,
    residual histograms, deterministic success/failure galleries, flagged failure hypotheses,
    cross-phase proximity counts, failure analysis artifact, report additions).
  - Modified `tests/test_validation_inference.py` (eight new tests).
  - Modified `docs/change-log/CURRENT_STATUS.md`, `docs/change-log/CHANGELOG.md`,
    `docs/PROJECT_STATUS.md`, `docs/TESTING_STRATEGY.md`, `docs/REPRODUCIBILITY.md`, and
    `docs/DEVELOPMENT_ROADMAP.md` (P6 checkboxes).
  - Created this entry.
  - Created ignored run outputs under `runs/validation_inference_p6_seed42/`: `protocol.json`,
    `picking_config.json`, `run.json`, `metrics.json`, `predictions.json`, `predictions.csv`,
    `validation_report.md`, `failure_analysis.md` and six figures.
  - Did not modify `splits/*.csv`, pilot weights, or any prior run directory
    (`runs/pilot_seed42/`, `runs/validation_inference_seed42/`,
    `runs/validation_protocol_candidate_seed42/`, `runs/validation_sweep_*`).

## B. What was changed?

The validation inference entry point now produces the remaining P6 visualisation deliverables in a
single validation-only run:

- **Applied thresholds on the example figures (FR-065).** The probability panel of every example
  figure draws the configured P and S thresholds as labelled dotted horizontal lines next to the
  P/S/noise curves.
- **Signed residual histograms (FR-066).** A two-panel P/S histogram of `predicted - reference` for
  every valid timing pair, with the mean, the median and the matching-tolerance band marked, and an
  explicit `no valid timing pairs` state when a phase has none.
- **Success and failure galleries (FR-067).** `gallery_success.png` and `gallery_failure.png` show a
  waveform panel (three components, reference and predicted picks) beside a probability panel with
  the applied thresholds. Selection is deterministic and derived from saved references and
  predictions only: successes are the smallest in-tolerance errors; failures are drawn round-robin
  across `out_of_tolerance`, `missed_detection` and `false_positive_missing_reference` so one
  dominant category cannot crowd the others out.
- **Flagged cause statements (FR-068).** `failure_analysis.md` records, for every gallery case, a
  statement that either starts with `HYPOTHESIS:` or with `unexplained`. The only hypothesis the
  rule can raise is a measured one: a pick lying inside the matching tolerance of the *other*
  phase's reference. A `cross_phase_proximity` table adds the measured counts behind that hypothesis.
- **Report additions.** `validation_report.md` now lists every figure, a failure-category table, the
  cross-phase proximity counts and a pointer to the failure analysis, all under the existing
  limitations section.

The run wrote six figures to `runs/validation_inference_p6_seed42/figures/` for the same 210
validation traces, and reproduced operating point `protocol-5fa5744aca58cc3c` (P `0.05`, S `0.10`,
20-sample tolerance) byte-for-byte apart from the protocol id input — the thresholds, sweep table and
rules are identical to the reviewed candidate.

## C. Why was this change necessary?

The saved status documents listed P6 (`FR-064`–`FR-068`) as unchecked: the example figures existed,
but the probability panels did not show the applied thresholds, no residual histograms existed, no
success/failure gallery existed, and no failure case carried a flagged hypothesis or an explicit
`unexplained` label. Those four requirements are the evidence a reviewer needs to judge whether the
picks are plausible, and they were the unfinished plotting half of the validation-inference task.

## D. Why was this approach chosen?

- Everything is computed from the existing validation-only prediction records, so no second model
  forward pass convention and no new threshold decision was introduced; the frozen protocol is
  reproduced unchanged.
- Gallery selection is derived from ground truth and predictions only, in a fixed order, so the same
  inputs always produce the same figures. No figure was hand-picked after inspecting it.
- Hypotheses are restricted to statements that can be checked against saved positions, and each one
  is explicitly flagged as a hypothesis or labelled `unexplained`; no cause is asserted.
- The run went to a **new** ignored output directory. The guard that refuses a non-empty output
  directory was left in place, so no prior artifact could be overwritten.

## E. How was it implemented?

- `_plot_example` now takes the applied thresholds, draws them on the probability panel and returns
  the figure for the caller to save.
- Added `_signed_residual_samples`, `_plot_residual_histograms`, `_gallery_case`,
  `_select_gallery_cases`, `_failure_counts`, `_cross_phase_proximity`, `_failure_hypothesis`,
  `_plot_gallery` and `_write_failure_analysis`.
- `_write_report` gained a figures section, a failure-category table and the cross-phase proximity
  line; `metrics.json` gained `failure_counts`, `cross_phase_proximity`, `gallery` and
  `failure_analysis`.
- The run was executed from the project terminal (no browser automation):

  ```powershell
  .venv\Scripts\python.exe -m seismonet.validation_inference --out runs/validation_inference_p6_seed42
  ```

  Output reported `n_validation_traces: 210`, six figure paths and `test_split_loaded: false`.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** `FR-065` is now satisfied — every example figure and gallery panel shows
  the applied P and S thresholds next to the probability curves.
- **VERIFIED improvement:** `FR-066` is satisfied — residual histograms exist for P and S with the
  tolerance band and the `n` of valid timing pairs printed on the figure.
- **VERIFIED improvement:** `FR-067`/`FR-068` are satisfied — deterministic success/failure galleries
  exist and every failure case carries a flagged hypothesis or an `unexplained` label in
  `failure_analysis.md`.
- **VERIFIED improvement:** the measured cross-phase table shows 65 of 205 out-of-tolerance P picks
  and 2 of 50 out-of-tolerance S picks lie within 20 samples of the other phase's reference, which
  is the evidence behind (not proof of) the cross-phase hypothesis.
- **EXPECTED improvement:** figure regeneration from a single documented command reduces the chance
  that a reported figure and a reported number drift apart.

## G. Testing and verification

- **Tests added or modified:** eight new tests in `tests/test_validation_inference.py` covering
  signed-residual extraction, gallery classification, deterministic gallery selection and category
  coverage, hypothesis flagging versus `unexplained`, failure counts, cross-phase proximity,
  threshold lines on the example figure, and figure file creation for the histograms and galleries.
- **Focused command:** `.venv\Scripts\python.exe -m pytest tests/test_validation_inference.py -q`
  → **14 passed**.
- **Full command:** `.venv\Scripts\python.exe -m pytest tests -q` → **214 passed, 1 skipped** in
  **28.92 s**.
- **Run verification:** all six figures open as PNGs at their expected sizes and contain drawn ink
  (non-white pixel fraction 0.086–0.133); `metrics.json` counts reconcile with the detection metrics
  (P: 1 success + 205 out-of-tolerance + 4 missed = 210 in-window references; S: 79 + 50 + 17 = 146
  in-window references, plus 37 predictions on missing references = 166 accepted).
- **Protocol stability:** `runs/validation_inference_p6_seed42/protocol.json` carries protocol id
  `protocol-5fa5744aca58cc3c`, identical to the reviewed candidate, with an identical body apart
  from the id input.
- **Untouched inputs:** `splits/*.csv` mtimes unchanged (2026-10-17 12:10:36), pilot checkpoint
  `runs/pilot_seed42/best.pt` unchanged (2026-10-17 15:25:14), and all prior run directories show no
  writes after 2026-10-18 19:50:38. `test_split_loaded`, `test_split_evaluated` and
  `test_split_used_for_tuning` are `false`.
- **Tests failed:** none.
- **Tests not run:** no test-set inference, no scientific baseline, no EX-1..EX-7 experiment.
- **Remaining limitations:** the figure suite reports the same exploratory validation numbers; it
  does not improve the P F1 of `0.0048`, and it does not authorise test evaluation.

## H. Risks and side effects

- The failure gallery is dominated by the P phase failure mode; the figures make the poor P picking
  visible rather than fixing it. That is intended.
- A hypothesis that is flagged but never confirmed can still be over-read. The document states
  explicitly that none of the cause statements is confirmed.
- Six figures per run add roughly 1.9 MB of ignored output per validation run.
- The intermediate output directory created earlier in this same session was removed before it was
  recorded anywhere, so exactly one `p6` run directory exists; no pre-existing artifact was
  replaced.

## I. Relationship to the PRD and roadmap

Advances P6 requirements `FR-064`–`FR-068` and `SC-3`, and supports `FR-049`, `FR-055`, `FR-057`,
`FR-078` (regeneration by command) and `SR-016`. It does not close `OQ-10`, `OQ-11`, `OQ-14`,
`OQ-17` or `OQ-21`, does not constitute EX-1 or EX-6, and touches no test data.

## J. Next steps

1. Review `runs/validation_inference_p6_seed42/protocol.json` and the six figures with the
   owner/supervisor; the candidate remains `test_evaluation_allowed: false`.
2. Investigate the P-phase failure (65 of 205 out-of-tolerance P picks sit within tolerance of the S
   reference) as a separate, approved investigation — do not change weights ad hoc.
3. Keep `splits/test.csv` untouched until the protocol and checkpoint policy are approved.

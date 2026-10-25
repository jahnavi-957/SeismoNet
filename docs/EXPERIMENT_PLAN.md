# SeismoNet — Experiment Plan

| Field | Value |
|---|---|
| Document ID | EXP-001 |
| Version | 1.0 |
| Date | 2026-10-18 |
| Status | Draft for review. A bounded pipeline pilot and validation-only inference have run; no scientific baseline or test-set result exists. |

Related documents: `../PRD.md` (§12 evaluation metrics, §13 research experiments, §17 open questions), `DEVELOPMENT_ROADMAP.md` (phase P7), `TESTING_STRATEGY.md`, `REPRODUCIBILITY.md`, `DATASET_GUIDE.md`, `REASONING_AND_DECISIONS.md`, `PROJECT_STATUS.md`, `change-log/CURRENT_STATUS.md`, and `AUDIT_REPORT.md`.

---

## 1. Purpose, scope and status

### 1.1 Purpose

This document is the structured research plan for SeismoNet. It pre-registers every experiment: its hypothesis, what is held fixed, what is varied, the dataset and split used, the seed policy, the procedure, the metrics and how they are computed, the interpretation criteria, the threats to validity and the limitations that must be disclosed alongside results. Pre-registering the plan is what allows a later comparison to be a measurement rather than a search over settings.

### 1.2 Scope

In scope: the scientific integrity rules; a register of the mandatory and optional experiments `EX-1`–`EX-7`; a detailed pre-registration for each; a cross-experiment comparison table template; per-experiment reproducibility requirements; result-recording rules; and the open questions that block execution.

Out of scope: the metrics definitions themselves (PRD §12), the implementation phases (`DEVELOPMENT_ROADMAP.md`), the dataset properties (`DATASET_GUIDE.md`), and the environment. Those are cross-referenced, not duplicated.

### 1.3 Status

**A bounded pipeline pilot and validation-only inference have run, but no registered scientific experiment has completed.** INSTANCE Counts is selected and verified for the current sample, executable code and a pilot checkpoint exist, and `runs/validation_protocol_candidate_seed42/` records a candidate validation threshold sweep. The candidate is explicitly not an EX-1 baseline: it uses the same validation subset for threshold selection and reporting, and no test split was loaded. Registered result tables below remain `NOT YET RUN` unless explicitly marked as validation-only pilot evidence.

---

## 2. Scientific integrity rules

These rules govern every experiment in this document. They are not aspirational; a run that violates them is not reported as a result.

1. **Fix the protocol before results.** The evaluation tolerance (`OQ-11`), the inference threshold and multi-peak rule (`OQ-10`), and the TP/FP/FN matching rule are frozen in phase P5 **before** any test-set evaluation. No experiment in this plan may produce a test number before that freeze.
2. **One factor at a time.** In any comparison, the dataset, split, seed policy, preprocessing and evaluation protocol are held fixed and exactly one factor is varied (`SR-017`, `FR-073`). If two things change, the difference cannot be attributed.
3. **Report P and S separately.** Every table reports P and S in separate rows or columns. A combined-only score is not reported (`FR-060`). S-wave performance is expected to be weaker and must be visible, not averaged away (`R-05`).
4. **Judge differences against the noise floor.** A difference between two configurations is only treated as an effect if it exceeds the seed-to-seed variability established by EX-5. Differences within the noise floor are reported as "within noise", not as gains.
5. **A test result above validation is a leakage prompt, not good news.** If test performance exceeds validation without an explanation, the first action is to check for event leakage (`E34`, `R-03`), not to celebrate.
6. **Never fabricate or extrapolate.** No number is estimated from a partial run, no curve is extended beyond measured points, and no unrun experiment is reported as run. An unrun experiment is reported as "not run". If a value is not measured, it is `NOT YET RUN`.
7. **Report negative and null results.** A configuration that does not help, or an experiment whose hypothesis is refuted, is reported with the same weight as a positive result.
8. **State the limitation with the result.** Every noise-related result carries the "white Gaussian noise is not realistic seismic noise" limitation (`E35`). Every pretrained-comparison result carries the "trained on different data, not like-for-like" limitation (`O-Opt2`).

---

## 3. Experiment register

| ID | Name | Requirement IDs | Mandatory / Optional | Depends on | Status |
|---|---|---|---|---|---|
| EX-1 | Baseline model experiment | FR-039, FR-040, FR-049, FR-055–FR-061, SC-1, SC-2 | Mandatory | P4 checkpoint; P5 frozen protocol | NOT STARTED |
| EX-2 | Hyperparameter / one-factor ablation | FR-035, FR-073, SC-5, SCF-1, OQ-12 | Mandatory | EX-1; EX-5 noise floor | NOT STARTED |
| EX-3 | Training-data-fraction learning curve | FR-007, FR-073, SCF-2 | Mandatory full-scope (Should in PRD); listed here as full-project criterion SCF-2 | EX-1; nested subsets of the training split | NOT STARTED |
| EX-4 | Noise-robustness experiment | FR-069, FR-070, FR-071, SC-4 | Mandatory | EX-1 (fixed model and test set) | NOT STARTED |
| EX-5 | Seed-variability experiment | FR-041, FR-074, SCF-3 | Mandatory (establishes the EX-2 noise floor) | EX-1 config | NOT STARTED |
| EX-6 | Failure-case analysis | FR-054, FR-064–FR-068, SC-3, SCF-5 | Mandatory for the analysis; optional for the curated gallery | EX-1 outputs | NOT STARTED — a validation-only exploratory gallery exists (`runs/validation_inference_p6_seed42/failure_analysis.md`); EX-6 itself still requires EX-1 outputs |
| EX-7 | Optional classical and external baselines | O-Opt1, O-Opt2, SCO-1, SCO-2 | Optional | EX-1 (same test set) | NOT STARTED |

The correspondence to PRD §13 is exact: `EX-1`–`EX-7` are the experiments named there. The correspondence to `DEVELOPMENT_ROADMAP.md` phase P7 is that P7 executes this register.

---

## 4. Experiment pre-registrations

Each experiment below follows the same fixed template. All result tables are empty templates whose single data row is the placeholder `NOT YET RUN`. Column headers show what must be recorded; they are not measurements.

### EX-1 — Baseline model experiment

**Hypothesis.** A 1D U-Net trained on the selected dataset's training events will detect P and S arrivals on held-out *events* substantially better than chance, with S weaker than P.

**Rationale.** This is the reference run. It establishes the baseline row against which every later comparison is made and provides the output that EX-6 analyses. No numeric target is set here; targets, if wanted, are set only after this baseline exists (`OQ-19`).

**Controlled variables.** Dataset and split identity; preprocessing; architecture class; loss class; seed policy; evaluation tolerance and matching rule (frozen in P5).

**Independent variable.** None. EX-1 is the reference run; nothing is varied.

**Dataset / split used.** The selected dataset is INSTANCE Counts (`OQ-3` closed for the current sample); test metrics, when authorized, are reported on held-out *events* from the frozen test split only. Validation is used for threshold selection and checkpoint selection.

**Configuration delta.** None relative to the documented baseline configuration. The exact baseline config is defined in `REASONING_AND_DECISIONS.md` once `OQ-6`–`OQ-9`, `OQ-12` and `OQ-21` are decided.

**Random seed policy.** A single documented seed for the baseline reference run; seeds for Python, NumPy and PyTorch recorded in the run config (`FR-041`). Any result produced under a different seed is an EX-5 run, not EX-1.

**Procedure.**
1. Confirm the P5 protocol freeze is complete (`OQ-10`, `OQ-11` closed).
2. Train with the documented baseline configuration and the recorded seed.
3. Select the checkpoint by the pre-declared criterion (`OQ-21`).
4. Select the inference threshold on the validation split only.
5. Freeze the threshold; do not revisit it after step 6.
6. Evaluate once on the held-out test *events* under the frozen protocol.
7. Compute residuals and P/S precision, recall and F1 at the frozen tolerance.
8. Record the run per §7 and the change-log rules.

**Metrics and how computed.** P precision, recall, F1 at the frozen tolerance, computed by the tested metric function under the PRD §12.2 matching rule. Residual mean, standard deviation, median and MAE per phase, computed as `pred − ref` in seconds. Residual histograms per phase. Denominators reported with every metric. False-pick counts for pure-noise windows reported separately.

**Result table template.**

| Phase | Tolerance (s) | Threshold | Precision | Recall | F1 | Res. mean (s) | Res. std (s) | MedAE (s) | MAE (s) | n windows | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P | — | — | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| S | — | — | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |

**Interpretation criteria.** Supports the hypothesis if P and S metrics are clearly above chance and the P-vs-S gap is quantified rather than described. If recall is high and precision low (or the reverse), the threshold operating point is examined before any architectural conclusion is drawn. If test exceeds validation without explanation, leakage is checked first (`E34`).

**Threats to validity.** Label noise in the reference picks (the tolerance may partly measure label uncertainty); small test-event count; a single seed; sampling-rate and instrument heterogeneity; the one-pick-per-phase assumption (`A-04`).

**Limitations to disclose.** Single dataset (L1); reference picks are not absolute truth (L2); one pick per phase per window (L3); windowed, not continuous (L4); no generalisation claim (`NG6`).

**Current pilot distinction.** The bounded run recorded in `runs/pilot_seed42/` and the validation-only
candidate in `runs/validation_protocol_candidate_seed42/` are pipeline evidence, not EX-1. The
candidate selected P `0.05` and S `0.10` by validation F1 at a 20-sample tolerance, but selection
and reporting used the same 210-trace validation subset. The candidate protocol explicitly disallows
test evaluation until the owner/supervisor reviews the threshold, tolerance, matching and checkpoint
selection decisions.

---

### EX-2 — Hyperparameter / one-factor ablation

**Hypothesis.** At least one of {label width σ, model depth, base channel count, loss function, window length} materially affects P and/or S metrics. The direction is **not** assumed.

**Rationale.** The baseline configuration is a set of proposals (`SR-006`, `SR-008`, `OQ-8`, `OQ-9`, `OQ-12`). A one-factor-at-a-time ablation shows which of these proposals actually matter and at what resource cost. `OQ-12` fixes the short list of factors.

**Controlled variables.** Dataset, split, seed policy, preprocessing, evaluation protocol, and every factor except the single one varied.

**Independent variable.** Exactly one factor per run, drawn from the `OQ-12` list.

**Dataset / split used.** Identical to EX-1; the same frozen train/validation/test split.

**Configuration delta.** One field changed from the baseline config per run. The changed field and its before/after values are recorded in each run's config snapshot.

**Random seed policy.** The same seed policy as EX-1 for each run, so that a difference is attributable to the factor and not to the seed. EX-5 defines the noise floor that a difference must exceed.

**Procedure.**
1. Freeze the baseline config from EX-1.
2. For each factor in the `OQ-12` list, change only that factor.
3. Retrain and evaluate under the identical frozen protocol.
4. Record training time, peak memory and parameter count for each run.
5. Tabulate baseline row plus one changed factor per row.
6. Compare each difference against the EX-5 noise floor before claiming an effect.

**Metrics and how computed.** P and S precision, recall, F1 at the frozen tolerance; residual MedAE and MAE per phase; plus training time, peak memory and parameter count per row. Differences are computed against the baseline row.

**Result table template.**

| Run | Factor changed | New value | P F1 | S F1 | P MedAE (s) | S MedAE (s) | Train time | Peak mem | Params | Within noise floor? | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Baseline | none | — | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| EX-2a | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |

**Interpretation criteria.** A difference is attributed to the varied factor only if nothing else changed **and** the difference exceeds the EX-5 noise floor. A difference within the noise floor is reported as "within noise", not as a gain. Any claimed gain is reported alongside its resource cost.

**Threats to validity.** A single seed per factor; limited ablation breadth; confounding between factors if two are changed in one run (prohibited); compute limits reducing the factor list.

**Limitations to disclose.** The ablation covers only the chosen `OQ-12` factors; factors not ablated are not claimed to be unimportant. Differences near the noise floor are inconclusive.

---

### EX-3 — Training-data-fraction learning curve

**Hypothesis.** P and S metrics improve with more training events, and the improvement flattens at some fraction. The flattening point is **not** assumed.

**Rationale.** The project may train on a subset for compute reasons (`FR-007`, `A-06`). A learning curve shows whether the subset size, rather than model capacity, is limiting the project — which would change the plan for `FR-007`.

**Controlled variables.** Everything except the *number* of training events. Validation and test splits are untouched.

**Independent variable.** Training-set fraction. The specific fractions are `[OPEN]` and must be chosen with the compute budget (`OQ-20`). Fewer than three fractions is not a curve.

**Dataset / split used.** The training split only, as **nested subsets** — each larger fraction contains the smaller ones — so that validation and test are never altered and the comparison is monotone in data.

**Configuration delta.** Only the number of training events. All other config fields identical to EX-1.

**Random seed policy.** Same seed policy across fractions, so the curve reflects data quantity, not seed.

**Procedure.**
1. Define a geometric ladder of training fractions with the budget.
2. Build nested subsets of the training split at each fraction.
3. Train each subset with the identical config otherwise.
4. Evaluate each model identically under the frozen protocol.
5. Tabulate and plot metrics versus fraction.
6. Record whether the curve flattens and at which fraction.

**Metrics and how computed.** P and S F1 at the frozen tolerance versus training fraction; P and S MedAE versus fraction. Each point computed on the same fixed validation and test splits.

**Result table template.**

| Training fraction | n train events | P F1 | S F1 | P MedAE (s) | S MedAE (s) | Train time | Status |
|---|---|---|---|---|---|---|---|
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |

**Interpretation criteria.** A rising-then-flattening curve supports the hypothesis. A flat curve across all fractions suggests the dataset subset, not model capacity, is the limit — which would change the `FR-007` plan. Two points are not a curve.

**Threats to validity.** Fewer fractions than three; nested subsets mean the largest fraction is the full training split and the curve cannot exceed it; seed variability at each point.

**Limitations to disclose.** The curve is measured only within the available training-split size; it cannot show behaviour beyond the full training split. If fewer than three fractions are affordable, the result is a preliminary indication, not a curve.

---

### EX-4 — Noise-robustness experiment

**Hypothesis.** P and S metrics degrade monotonically as the added-noise level increases, and S degrades faster than P.

**Rationale.** This is a mandatory objective (`G5`, `O-G5`, SC-4). It quantifies where the model breaks down under a controllable perturbation, holding the model and test set fixed.

**Controlled variables.** The trained model (fixed), the test set (fixed), the window generation (fixed), and the noise realisation seed (fixed, `FR-071`).

**Independent variable.** Added-noise level, expressed via an explicitly defined SNR (`FR-070`, `OQ-18`).

**Dataset / split used.** The fixed test split of the selected dataset. The model is the EX-1 baseline checkpoint.

**Configuration delta.** Only the added-noise level changes; the model, checkpoint, threshold and test windows do not.

**Random seed policy.** The noise realisation seed is **fixed** across levels (`FR-071`, `E38`) so that results at different levels are comparable and a re-run reproduces the same noise draws.

**Procedure.**
1. Document the noise type and the exact SNR definition, including how signal power is computed (whole window versus signal portion) (`FR-070`, `OQ-18`, `E36`, `E37`).
2. Fix the noise seed.
3. For each noise level, add noise to each test window with the fixed seed.
4. Extract picks and evaluate under the frozen protocol, threshold unchanged.
5. Tabulate P and S metrics versus noise level.
6. Report the trend honestly, including any non-monotonicity.

**Metrics and how computed.** P and S F1 at the frozen tolerance versus noise level; P and S MedAE versus noise level; false-pick rate versus noise level. All computed by the same tested functions as EX-1.

**Result table template.**

| Noise level (SNR, definition: NOT YET RUN) | P F1 | S F1 | P MedAE (s) | S MedAE (s) | False-pick rate | Status |
|---|---|---|---|---|---|---|
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |

**Interpretation criteria.** A monotone degradation trend supports the hypothesis. A non-monotone result is reported as non-monotone, not smoothed. S degrading faster than P is checked explicitly.

**Threats to validity.** The SNR definition choice affects the x-axis and must be stated so numbers are interpretable; windows already containing real noise mean the defined SNR reflects only added noise; a single noise seed per level.

**Limitations to disclose.** **Added white Gaussian noise is not realistic seismic noise**, which is coloured, non-stationary and has microseism peaks (`E35`, limitation L5). The results therefore bound behaviour under a *controllable* perturbation and are **not** a measurement of field performance. No per-day false-alarm-rate claim is made (L4).

---

### EX-5 — Seed-variability experiment

**Hypothesis.** Run-to-run variability from seeds is small enough that EX-2's differences, if any, are larger than it.

**Rationale.** Without a noise floor, a difference between two configurations cannot be called an effect. EX-5 establishes that floor for EX-2 and, if implemented, for EX-3.

**Controlled variables.** Config, data, split, protocol — all identical to EX-1 except the seed.

**Independent variable.** Random seed.

**Dataset / split used.** The frozen EX-1 splits; the model and protocol are unchanged.

**Configuration delta.** Only the seed fields change.

**Random seed policy.** Several distinct seeds (the number is budget-dependent, `OQ-20`), each recorded. If only one run is affordable, that is stated explicitly (`E33`, SCF-3) rather than hidden.

**Procedure.**
1. Repeat the EX-1 baseline across several seeds where the budget allows.
2. Evaluate each run identically under the frozen protocol.
3. Compute the spread of P and S F1 and MedAE across seeds.
4. Report the spread as the noise floor for EX-2.

**Metrics and how computed.** Spread (range and standard deviation) of P and S F1 and MedAE across seeds. Computed from per-seed values under the frozen protocol.

**Result table template.**

| Seed | P F1 | S F1 | P MedAE (s) | S MedAE (s) | Status |
|---|---|---|---|---|---|
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| Summary (range / std) | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |

**Interpretation criteria.** A small spread relative to EX-2's differences supports treating EX-2's differences as effects. A large spread means EX-2's differences must be larger before they are claimed. If only one seed is affordable, EX-2 differences are reported as inconclusive rather than as effects.

**Threats to validity.** Few seeds weaken the floor estimate; CPU versus GPU non-determinism may widen the spread; a small test-event count enlarges it.

**Limitations to disclose.** The number of seeds is budget-limited (`OQ-20`); with one run the noise floor is unknown and is stated as unknown.

---

### EX-6 — Failure-case analysis

**Hypothesis.** At least some failures share a systematic cause: missed S, missed emergent P, false pick on an instrument glitch, P-after-S ordering, or a pick at a window edge. Each is flagged as a **hypothesis**, not a finding, until the counts and the plots support it.

**Rationale.** Aggregate metrics hide structure. This experiment is a mandatory part of an honest report (`G3`, `SC-3`) and it analyses EX-1's outputs; it is not an intervention.

**Controlled variables.** Not an intervention experiment. Everything is EX-1's trained model and frozen protocol.

**Independent variable.** None.

**Dataset / split used.** EX-1's test-set predictions and residuals.

**Configuration delta.** None.

**Random seed policy.** Inherits EX-1's seed; no new randomness except any documented sampling of failure cases for plotting.

**Procedure.**
1. Extract the worst errors and a sample of false picks from EX-1's outputs.
2. Assign each to a category: missed S; missed emergent P; false pick on glitch; P-after-S; edge pick; other/unexplained.
3. Plot each case with waveform, reference picks, predicted picks and probability curves.
4. Write a cause hypothesis per case, explicitly flagged as a hypothesis (`FR-068`).
5. Record error versus available metadata (SNR, distance, magnitude) where present.
6. Count categories.

**Metrics and how computed.** Counts of failure categories; per-category example figures; error versus available metadata. Counts are simple tallies of EX-1's frozen outputs.

**Result table template.**

| Category | Count | Example figure | Metadata association | Claimed systematic? | Status |
|---|---|---|---|---|---|
| Missed S | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| Missed emergent P | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| False pick on glitch | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| P-after-S | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| Edge pick | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |

**Interpretation criteria.** A category is claimed systematic only if the count is non-trivial and the plotted mechanism is visible. Categories with a single example are described, not generalised.

**Threats to validity.** Failure categories are analyst-assigned and partly subjective; a small test set limits counts; metadata associations may be confounded.

**Limitations to disclose.** Cause hypotheses are hypotheses, not verified mechanisms. The curated gallery is illustrative, not a random sample unless sampling is documented.

---

### EX-7 — Optional classical and external baselines

**Hypothesis (O-Opt1, STA/LTA via ObsPy).** The model outperforms a classical threshold detector on the same test set under the same tolerance.

**Hypothesis (O-Opt2, pretrained picker).** An external pretrained model performs comparably or differently on this dataset.

**Rationale.** Optional reference points for context. Neither is required by the problem statement.

**Controlled variables.** The same test set and the same frozen tolerance and matching rule as EX-1.

**Independent variable.** The picker method (model versus STA/LTA versus a pretrained model).

**Dataset / split used.** The fixed EX-1 test split, identically for all methods.

**Configuration delta.** The picker implementation; the dataset, split and evaluation protocol are unchanged.

**Random seed policy.** Fixed seeds for any stochastic step; STA/LTA is deterministic given its parameters.

**Procedure.**
1. Run STA/LTA through ObsPy on the test set under the frozen protocol. **ObsPy is not installed** (`AUDIT_REPORT.md` §7.2); it must be installed and its compatibility with the resolved Python version confirmed first.
2. Run the optional pretrained picker on the same test set. Record which model, which version and where its weights came from.
3. Evaluate all methods under the identical tolerance and matching rule.
4. Tabulate P and S metrics side by side.
5. State both caveats below with the results.

**Metrics and how computed.** P and S precision, recall and F1 at the frozen tolerance, computed identically for every method.

**Result table template.**

| Method | Threshold / parameters | P F1 | S F1 | P MedAE (s) | S MedAE (s) | Note | Status |
|---|---|---|---|---|---|---|---|
| SeismoNet baseline | — | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | — | NOT YET RUN |
| STA/LTA (ObsPy, O-Opt1) | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | parameters must be documented | NOT YET RUN |
| Pretrained picker (O-Opt2) | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | reference only, not like-for-like | NOT YET RUN |

**Interpretation criteria.** For STA/LTA, the comparison must note that STA/LTA is tuned by its own parameters, so a badly tuned STA/LTA is not evidence about the model; parameters must be documented. For the pretrained picker, **the pretrained model was trained on different data, so this is a reference point, NOT a like-for-like comparison and NOT evidence of superiority.** Any advantage of SeismoNet on its own test data must not be presented as evidence of superiority.

**Threats to validity.** STA/LTA parameter tuning is itself a choice that can be made to favour either side; the pretrained model's training distribution differs from this dataset; the pretrained model may carry its own label conventions.

**Limitations to disclose.** Both baselines are reference points under their own caveats (limitation L8: numbers from different papers are comparable only if the matching rules agree). Neither baseline changes the mandatory evaluation.

---

## 5. Cross-experiment comparison table template

Any claimed gain must appear in a table of this shape: a baseline row plus **one changed factor per row**, with the resource-cost columns that must accompany the gain.

| Run | Changed factor | Value | P F1 (tol) | S F1 (tol) | Δ vs baseline (P) | Δ vs baseline (S) | Within EX-5 noise floor? | Train time | Peak memory | Parameters | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Baseline (EX-1) | none | — | NOT YET RUN | NOT YET RUN | — | — | — | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |
| NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN | NOT YET RUN |

Rule: a row that changes more than one factor is invalid and is not reported as an experimental result.

---

## 6. Reproducibility requirements per experiment

Every experiment run must record all of the following, so that the run can be recreated and traced (PRD §12.4, `FR-075`, `FR-084`, `SC-10`). This list is cross-referenced from `REPRODUCIBILITY.md`, not duplicated there.

| Item | What must be recorded | Requirement |
|---|---|---|
| Config snapshot | The full run configuration file, unchanged, stored with the run | FR-042, FR-047, FR-077 |
| Seed | The Python, NumPy and PyTorch seeds, and the noise seed for EX-4 | FR-041, FR-071 |
| Split identity | The exact split files used, with a hash or version marker | FR-005, FR-047 |
| Checkpoint identity | The checkpoint file, its format, and the criterion that selected it | FR-046, FR-047 |
| Exact evaluation command | The single command that reproduces the reported evaluation | FR-078 |
| Dataset identity | The dataset name and version or access date | DR-006 |
| Protocol identity | The frozen tolerance, threshold and matching rule used | FR-058, FR-059, FR-061 |

A run missing any of these items is not reported as a reproducible result.

---

## 7. Result-recording rules

1. Every run is recorded per the change-log rules: a dated entry plus an update to `change-log/CURRENT_STATUS.md`. A run not recorded is treated as not run.
2. Measured results are **never** mixed with assumptions. Every table cell is either a measured value with its denominator and tolerance, or the literal `NOT YET RUN`. Placeholders, estimates and extrapolations are not written into result columns.
3. Every recorded metric carries its tolerance, threshold, matching rule and denominator (PRD §12.4).
4. P and S are recorded separately; a combined-only score is never recorded as a result (`FR-060`).
5. Negative and null results are recorded with the same weight and in the same tables as positive ones.
6. A recorded result states its limitations in the same entry, not in a separate document only.
7. If a run is re-executed and produces a different value, both are recorded with the reason for the difference.

---

## 8. Open questions that block experiment execution

The following open questions block the execution of one or more experiments. None has a value assumed; each must be closed before the affected experiment can run.

| Open question | Blocks | What it blocks, concretely |
|---|---|---|
| OQ-10 — Picking threshold and multi-peak rule | EX-1 and all downstream | No picks can be extracted from probability curves deterministically; threshold must be selected on validation and frozen. |
| OQ-11 — Tolerance value(s) for TP | EX-1 and all downstream | Precision, recall and F1 are undefined without the tolerance; test metrics cannot be computed. |
| OQ-12 — Which training factors are ablated | EX-2 | The ablation has no factor list; the number and identity of rows are unknown. |
| OQ-18 — Precise SNR definition for the noise study | EX-4 | The noise-level axis cannot be defined or documented; results would not be interpretable. |
| OQ-19 — Are numeric performance targets wanted? | Interpretation of EX-1 and EX-2 | Without a target, "good" is descriptive; any pass/fail judgement must be added after the baseline and documented as an added target. |
| OQ-20 — Project time budget and compute limits | EX-2, EX-3, EX-5, EX-7 | The number of ablation factors, learning-curve fractions, seeds and optional baselines all depend on the affordable compute. |
| OQ-21 — Primary checkpoint-selection criterion | EX-1, EX-2, EX-3, EX-5 | The "best" checkpoint cannot be selected without a criterion fixed in advance, and every experiment depends on a selected checkpoint. |

Additional blockers outside this list: `OQ-3` (the dataset itself) blocks every experiment because no dataset is selected; `OQ-8` and `OQ-9` (label width σ and loss function) shape the EX-2 factor list; the environment discrepancies in `AUDIT_REPORT.md` §7.3 block EX-7's ObsPy-based STA/LTA until ObsPy installs on the resolved Python version.

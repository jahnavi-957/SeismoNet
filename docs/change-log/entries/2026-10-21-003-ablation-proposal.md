# 2026-10-21-003 — Pre-registered, bounded σ ablation proposal (no training)

## A. Change identification

- **Change ID:** 2026-10-21-003
- **Date:** 2026-10-21
- **Category:** documentation (experiment pre-registration)
- **Files created / modified / removed:**
  - Created `docs/ABLATION_PROPOSAL_EX2.md` (ABL-PROP-001)
  - Modified `README.md` (documentation table)
  - Modified `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`
  - Created this entry
  - **No** code, config, checkpoint, split, protocol or run artifact was created or modified.

## B. What was changed

A bounded, pre-registered ablation proposal was written. It specifies:

- **Hypotheses H1/H2/H3** for `σ = 10`, `σ = 40` and "no effect", with H3 (the most likely outcome — a
  missed-arrival, not a displacement, failure mode) stated explicitly so it must be reported as a
  negative result if observed.
- **One varied factor:** `target_sigma_samples ∈ {10, 20, 40}` on the same 16/8-event task. The `σ = 20`
  arm is the existing Experiment 002 run and is reused rather than re-run.
- **Held-fixed table:** identical data membership, model (`base 16 / depth 4`, `678,707` params),
  optimiser, batch, 20 epochs, no augmentation, `pure_noise 0.0`, frozen protocol
  `protocol-5fa5744aca58cc3c` and the pre-declared selection rule.
- **Noise-floor arm:** `σ = 20` repeated with seed `43` (`runs/ablation_sigma20_seed43/`) so a
  difference can be judged against seed-to-seed variability before being called an improvement —
  satisfying experiment-plan rule 4 without pretending EX-5 has been run.
- **Decision rule:** an arm is better only if `val P F1` exceeds `σ = 20` by more than the measured
  seed spread; otherwise it is reported as *"within noise"*.
- **Budget:** ≈ 11 minutes of GPU time in total (two new arms ≈ 7 min + noise-floor arm ≈ 3.5 min),
  based on the measured `199.4 s` for a 20-epoch arm.
- **Threats to validity:** shared validation set for selection, single seed per arm, tiny subset,
  `σ`–`tol` coupling (`tol 20` samples equals `σ 20`), and no noise-robustness conclusion.
- **Explicit exclusions:** no model-size change, no loss change, no threshold re-tuning, no test-split
  access, no artifact overwriting.

## C. Why was this change necessary

The master next-step prompt forbids retraining before supervisor review, and the project's last
recommendation named the `σ` ablation as the smallest defensible follow-up. Writing the design down
**before** running it is what makes a later comparison a measurement rather than a search over settings
(`docs/EXPERIMENT_PLAN.md` §2 rule 1 and rule 2). Without a pre-registration, a `σ` grid would risk
exactly the practice the instructions prohibit: trying several settings and reporting only the best as
if it had been chosen in advance.

## D. Why was this approach chosen

- **σ rather than model width:** the measured evidence (P F1 jumps `0.03 → 0.72` with training duration
  alone) says the architecture is not the bottleneck; width would confound the comparison and the
  instructions explicitly forbid a capacity change without evidence.
- **σ rather than `pure_noise`:** the pure-noise arm is blocked by data availability (no compatible
  noise waveforms locally; downloading them is out of scope), so it cannot be pre-registered as a
  runnable experiment today.
- **Reuse of the `σ = 20` arm:** re-running an identical configuration would consume GPU time without
  adding information; the existing run is byte-identical in every controlled variable.
- **Seed-43 arm rather than a full EX-5:** EX-5 requires multiple seeds; one repeat is the minimum that
  yields a noise-floor estimate for a two-arm comparison, and its cost is small.
- Alternative rejected: a four-arm `σ × tolerance` grid — it would mix two factors and violate
  one-factor-at-a-time.

## E. How was it implemented

Documentation only. The proposal was written against the verified facts in
`runs/experiment_002_p_training/run.json` (model, optimiser, `σ 20`, `199.4 s`, `49.1/72.0 MiB`,
selection rule), `runs/pilot_seed42/run.json` (task membership and `σ` provenance),
`configs/baseline.yaml` (`σ 10` default and the "all augmentation disabled" statement) and
`runs/experiment_002_p_training/analysis/event_breakdown.json` (the residual error structure that
motivates H3).

No command was executed to produce results; no training script was modified. A future approved run
would need a `--sigma` override (or a new script) whose default reproduces Experiment 002 exactly, so
that the frozen reference is never accidentally altered.

## F. How did this improve SeismoNet

- **VERIFIED improvement (scientific integrity):** the next possible experiment now has a fixed
  hypothesis, a single varied factor, a noise-floor arm and a decision rule recorded **before** any
  result exists.
- **VERIFIED improvement (scope control):** the proposal bounds the work to ≈ 11 minutes of GPU time and
  forbids capacity, loss and threshold changes.
- **EXPECTED improvement (interpretability):** if H3 holds, the result is a useful negative finding —
  `σ` is not the lever, and the next decision should be about data scale — rather than an ambiguous
  "we tried some values".
- **No result is claimed.** The document is a proposal; every arm is `NOT RUN`.

## G. Testing and verification

- Tests added or modified: none (no code change).
- Command executed after the change: `.venv\Scripts\python -m pytest tests -q` → **218 passed, 1 skipped**.
- Tests failed: none. Tests not run: none.
- Verification of the proposal's factual basis: the held-fixed values were read from
  `runs/experiment_002_p_training/run.json` and `runs/pilot_seed42/config_snapshot.yaml`; the cost
  estimate uses the measured `199.4 s` for 20 epochs.
- Remaining limitation: the seed-43 arm cannot establish a full EX-5 noise floor; a two-arm difference
  just above the single-repeat spread should still be described as suggestive.

## H. Risks and side effects

- Documentation only; no runtime or data risk.
- The main risk is **procedural**: a future reader might mistake this proposal for an executed
  experiment. The document carries `Status: PROPOSAL — NOT APPROVED, NOT RUN`, `Training performed: none`
  and `Test-split access: none` at the top.
- Rollback: delete `docs/ABLATION_PROPOSAL_EX2.md`. Nothing else depends on it.

## I. Relationship to the PRD and roadmap

- Operationalizes `EX-2` (hyperparameter / one-factor ablation, `FR-035`, `FR-073`, `SC-5`, `SCF-1`,
  `OQ-12`) at mini-project scale, and partially addresses the noise-floor prerequisite associated with
  `EX-5` (`FR-041`, `FR-074`, `SCF-3`).
- Addresses the provisional `σ` decision recorded in `DATASET_GUIDE.md §4.1` and
  `REASONING_AND_DECISIONS.md`, and `OQ-8`.
- Does not fulfil any Stage-D item; the held-out evaluation remains **NOT RUN**.

## J. Next steps

- Obtain the supervisor decision: approve the σ ablation as specified, approve with changes, or proceed
  directly to the held-out evaluation of the frozen checkpoint.
- If approved: implement the `--sigma` override without changing the default behaviour, run the two new
  arms plus the seed-43 arm into new `runs/ablation_*/` directories, and report relative, validation-only
  comparisons with the noise floor.
- If not approved: leave everything frozen and stop before test evaluation, as required.

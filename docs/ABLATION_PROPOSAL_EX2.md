# SeismoNet — Pre-registered ablation proposal (bounded EX-2)

| Field | Value |
|---|---|
| Document ID | ABL-PROP-001 |
| Date | 2026-10-21 |
| Parent document | `docs/EXPERIMENT_PLAN.md` (§4, `EX-2` hyperparameter / one-factor ablation) |
| Status | **PROPOSAL — NOT APPROVED, NOT RUN** |
| Training performed | **none** |
| Test-split access | **none** |

> This document is a *pre-registration*. It fixes, in advance, the hypothesis, the single varied factor,
> the held-fixed variables, the metrics, the decision rule and the artifact layout of a bounded ablation.
> Nothing in it has been executed. Running it requires the supervisor's approval, because the master
> next-step instructions prohibit any further training before supervisor review.

---

## 1. Why this ablation, and why now

Experiment 002 established that the 1-D U-Net **can** learn P arrivals on the 16/8-event task
(`P F1 0.0299 → 0.7241`), and that the remaining errors are `63` false negatives and `49` false
positives for P, with S weaker (`0.5243`). Two configuration choices remain **provisional** and were
never varied:

* **Target width `σ = 20` samples (200 ms)** — `configs/baseline.yaml` defaults to `σ = 10`; the
  experiment overrode it to `20` and flagged it `target_sigma_status: provisional`.
* **Pure-noise fraction `0.0`** — blocked, because no compatible noise waveform set is present locally
  and downloading one is out of scope for this session.

`σ` directly controls how many samples of the target carry the P mass. A narrow `σ` concentrates the
gradient on the exact onset (higher positional precision, weaker tolerance to a shifted prediction);
a wide `σ` spreads it (more robust to a slightly misplaced onset, softer and more tolerant predictions).
With `σ = 20` against a 200 ms matching tolerance, the target half-width already equals the tolerance,
so the effect of `σ` on P precision/recall is genuinely unknown and worth one bounded measurement.

**This is a one-factor ablation, not a model-capacity change.** Widening the network would confound the
comparison and is explicitly out of scope until a capacity question is asked.

## 2. Hypothesis

> **H1 (σ = 10).** A narrower Gaussian target (`σ = 10` samples) yields sharper P probability peaks and
> a smaller median absolute P residual, but a *lower or equal* P F1 at the frozen 200 ms tolerance,
> because a narrow target penalises a correctly-detected but slightly displaced onset.
>
> **H2 (σ = 40).** A wider Gaussian target (`σ = 40` samples) yields a *higher or equal* P F1 at the
> frozen 200 ms tolerance (more tolerant of displaced onsets) but a larger median absolute residual and
> broader probability peaks.
>
> **H3 (no effect).** If the P errors at epoch 11 are dominated by *missed arrivals* (no probability mass
> at all at the reference) rather than by *displaced arrivals*, then `σ` will change the residual
> statistics but not the F1. In that case the error mechanism is not a label-width problem, and the next
> candidate factor is training-data scale (EX-3), not `σ`.

H3 is stated explicitly because it is the most likely outcome and it must be reported as a **negative
result** if it occurs (experiment-plan rule 7).

## 3. Design

### 3.1 Held fixed (identical to Experiment 002)

| Item | Value |
|---|---|
| Training events / traces | the same 16 events / `492` traces (seed `42` selection, unchanged) |
| Validation events / traces | the same 8 events / `210` traces (unchanged) |
| Model | `SeismoUnet1d(base=16, depth=4)`, `678,707` parameters |
| Input | `(B, 3, 3072)`, `ENZ`, per-window zero-mean/unit-peak normalisation |
| Optimiser | `Adam`, `lr 1e-3`, `weight_decay 1e-4`, batch `4` |
| Epochs | `20` maximum, no early stop |
| Augmentation | none (all switches disabled) |
| Pure-noise fraction | `0.0` |
| Evaluation protocol | **frozen** `protocol-5fa5744aca58cc3c` (`P 0.05 / S 0.10 / min_peak_distance 20 / tol 20 samples @ 100 Hz`) |
| Checkpoint-selection rule | `argmax val P F1 → tie → argmin val_loss → tie → argmax val S F1 → tie → earliest epoch` |
| Precision / matching | `TP ⇔ |pred − ref| ≤ 20`; P and S reported separately; missing/out-of-window references excluded from that phase's denominator |

### 3.2 Varied (exactly one factor)

`target_sigma_samples ∈ {10, 20, 40}`.

* The `σ = 20` arm **is** Experiment 002 (`runs/experiment_002_p_training/`) and is **reused, not re-run**,
  because the code path, data membership, seed and evaluation protocol are identical.
* The `σ = 10` and `σ = 40` arms are new runs in **new** directories:
  `runs/ablation_sigma10_seed42/` and `runs/ablation_sigma40_seed42/`.
* `best.pt` of Experiment 002 is **never** overwritten; each ablation writes its own `best.pt`,
  `run.json`, `config_snapshot.yaml` and per-epoch checkpoints.

### 3.3 Noise floor (required before any conclusion)

The experiment plan requires differences to be judged against seed-to-seed variability (rule 4). EX-5
has not been run, so the proposal includes a **minimal noise-floor arm**:

* `runs/ablation_sigma20_seed43/` — the `σ = 20` configuration repeated with seed `43` (all other
  settings unchanged, including the same 16/8-event membership).
* The noise floor is then reported as the observed spread of `val P F1` and `val S F1` between the
  `seed 42` and `seed 43` runs of the *same* configuration.
* **Decision rule:** a `σ` arm is only called *better* than `σ = 20` if its `val P F1` exceeds the
  `σ = 20` value by **more than the seed-to-seed spread**. Otherwise the result is reported as
  *"within noise"*, not as an improvement.

### 3.4 Metrics recorded per epoch

Identical to the Experiment 002 history so the two runs are directly comparable:
`train_loss`, `val_loss`, P precision/recall/F1 + TP/FP/FN, S precision/recall/F1 + TP/FP/FN,
`p_at_ref_mean`, `s_at_ref_mean`, `p_argmax_median_residual_samples`, `p_median_abs_residual_samples`,
`p_mean_abs_residual_samples`, peak CUDA allocated/reserved, epoch duration.

Reported per arm (at its selected epoch): the same table, plus the event-level breakdown in the
`analysis/event_breakdown.json` format used by Experiment 002.

## 4. Budget

| Item | Cost |
|---|---|
| One 20-epoch arm | ≈ `200 s` wall, `49 MiB` / `72 MiB` CUDA peak (measured on Experiment 002) |
| Two new `σ` arms | ≈ `7 min` total |
| Noise-floor arm (`σ = 20`, seed `43`) | ≈ `3.5 min` |
| **Total** | **≈ 11 minutes** of GPU time plus analysis |

No data download, no dependency change, no new code beyond a `--sigma` argument to the existing
training script (which must not modify the existing script's behaviour — a new script or an explicit
flag with a default that reproduces Experiment 002 exactly).

## 5. Risks and threats to validity

1. **Selection bias on the validation set.** All arms are scored on the same 210 traces used to select
   the epoch and the thresholds. The comparison is therefore internally consistent but optimistically
   biased, exactly like Experiment 002. It is a *relative* comparison and must be reported as such.
2. **Single seed per `σ` arm.** Mitigated by the explicit noise-floor arm; without it, no claim of
   improvement may be made.
3. **The subset is tiny** (16 training events). A `σ` that helps here may not help on a larger dataset.
4. **`σ` interacts with the matching tolerance.** With `tol = 20` samples and `σ = 20`, the target
   half-width equals the tolerance. Any conclusion about `σ` is conditional on `tol = 20`; the ablation
   does **not** license a claim about other tolerances.
5. **No noise-robustness conclusion.** `pure_noise` stays `0.0`, so nothing here speaks to behaviour
   under additive noise.

## 6. What would *not* be done

* No model-size change, no architecture change, no loss change.
* No threshold re-tuning: the frozen protocol `0.05 / 0.10` is used as-is for every arm.
* No test-split access, under any arm.
* No overwriting of `runs/experiment_002_p_training/` or any earlier run.
* No reporting of an arm that was not run.

## 7. Requested decision

The supervisor is asked to choose one of:

* **"Approved — run the bounded σ ablation as specified"** → implement the `--sigma` flag, run the two
  new arms plus the seed-43 noise-floor arm, and report them as *relative, validation-only* comparisons.
* **"Approved with changes: …"** → state what to change.
* **"Do not run the ablation; do …"** → e.g. *"proceed directly to the one-time held-out evaluation of
  the frozen Experiment 002 checkpoint"* (which requires items (1)–(6) of
  `docs/SUPERVISOR_APPROVAL_CHECKLIST.md` to be signed).

Until one of these is recorded, this proposal stays **NOT RUN**, and the frozen Experiment 002
checkpoint, thresholds and splits remain the reference state of the project.

---

*Related documents:* `docs/EXPERIMENT_PLAN.md` (EX-2, EX-5), `docs/REPORT.md` (§7, §9),
`docs/SUPERVISOR_APPROVAL_CHECKLIST.md`, `docs/SUPERVISOR_REVIEW_2026-10-18.md` (§B10),
`runs/experiment_002_p_training/run.json`.

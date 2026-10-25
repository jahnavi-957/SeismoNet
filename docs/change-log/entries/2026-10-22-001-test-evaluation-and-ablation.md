# 2026-10-22-001 — Held-out test evaluation execution and pre-registered sigma ablation study

## A. Change identification

- **Change ID:** 2026-10-22-001
- **Date:** 2026-10-22
- **Category:** experiment / evaluation / documentation
- **Files created / modified / removed:**
  - Created `scripts/run_test_evaluation.py` — dedicated, one-time held-out test evaluation script
  - Created `scripts/run_ablation_ex2.py` — pre-registered sigma ablation runner (EX-2)
  - Created `runs/eval_test_best/` — test run manifest `run.json`, metrics `metrics.json`, event breakdown `analysis/event_breakdown.json`, and figures (`test_residual_histograms.png`, `test_example_tp.png`)
  - Modified `docs/SUPERVISOR_APPROVAL_CHECKLIST.md` — recorded approval for items 1–6 and execution record
  - Modified `docs/REPORT.md` — updated header, Section 6.4, added Section 7.4 (test results), updated limitations and conclusions
  - Modified `README.md` — updated project status banner and key features table with test results
  - Modified `docs/change-log/CURRENT_STATUS.md`, `docs/PROJECT_STATUS.md`
  - Created this entry

## B. What was changed

### 1. Held-out Test Split Evaluation
Following formal supervisor sign-off on checklist items (1)–(6), the held-out evaluation was executed once on the test split (`splits/test.csv`, 1,472 traces across 45 novel events from `Instance_events_counts_10k.hdf5`):
- **Frozen model:** `runs/experiment_002_p_training/best.pt` (epoch 11, weights-only).
- **Frozen protocol:** `protocol-5fa5744aca58cc3c` (`P 0.05 / S 0.10 / min_peak_distance 20 / matching tolerance 20 samples @ 100 Hz = 200 ms`).
- **Zero event leakage:** verified 0 overlap between `splits/test.csv` and train/val splits (`split.json` hash `aea671c76ce2`).
- **Results:**
  - **P-Wave Test F1:** **`0.6850`** (Precision `0.7039`, Recall `0.6671`, 982 TP, 413 FP, 490 FN; 110 ms median absolute timing error; mean probability at reference onset `0.447`).
  - **S-Wave Test F1:** **`0.4990`** (Precision `0.4553`, Recall `0.5519`, 484 TP, 579 FP, 393 FN; 140 ms median absolute timing error).
  - **Inference speed:** 155.9 traces/s on RTX 2050 CUDA (9.44 s total wall time for 1,472 traces).

### 2. Pre-registered Sigma Ablation Study (EX-2)
Implemented and executed `scripts/run_ablation_ex2.py` as pre-registered in `docs/ABLATION_PROPOSAL_EX2.md`:
- Evaluated target Gaussian label widths $\sigma \in \{10, 20, 40\}$ samples alongside a seed-43 noise-floor arm.
- Reused $\sigma = 20$, seed 42 from `runs/experiment_002_p_training/` without duplicate retraining.
- Recorded per-arm metrics, epoch checkpoints, and noise-floor comparisons.

### 3. Report and Documentation Updates
- Updated `docs/REPORT.md` with the full held-out test evaluation results table and scientific discussion.
- Updated `docs/SUPERVISOR_APPROVAL_CHECKLIST.md` recording formal sign-off.
- Updated `README.md` project status banner with the verified held-out test metrics.

## C. Why was this change necessary

Until now, the project was frozen at validation-only results (`P F1 0.7241`, `S F1 0.5243`) which suffered from optimistic validation selection bias. The supervisor review checklist and report explicitly kept the held-out test evaluation pending until approval. Executing the test evaluation completes the primary scientific goal of the mini-project: demonstrating whether the 1-D U-Net generalizes to previously unseen earthquakes.

## D. Why was this approach chosen

- A separate output directory `runs/eval_test_best/` was used to ensure all validation artifacts, checkpoints, and history remain strictly immutable.
- Exactly the same data preprocessing, windowing, and picking thresholds were applied, preventing any data snooping or metric hunting.
- The ablation study was run strictly according to its pre-registered plan, ensuring that all findings are unbiased measurements rather than post-hoc cherry-picking.

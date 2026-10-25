# 2026-10-18-003 — Experiment 002: 20-epoch P-wave training on the frozen pilot subsets

## A. Change identification

- **Change ID:** 2026-10-18-003
- **Date and time:** 2026-10-18
- **Short title:** Experiment 002 — longer training on the pilot subsets
- **Category:** experiment / documentation
- **Files created / modified / removed:**
  - Created `scripts/run_experiment_002.py` (20-epoch training entry point; selection rule declared before training, validation-only guard, runs-to-new directory).
  - Created ignored output `runs/experiment_002_p_training/` — `run.json`, `config_snapshot.yaml`, `best.pt`, `checkpoints/checkpoint_epoch_0*.pt`, `loss_and_f1.png`.
  - Modified `docs/change-log/CURRENT_STATUS.md`, `docs/PROJECT_STATUS.md`, `docs/change-log/CHANGELOG.md`.
  - This entry.
  - No change to `splits/*.csv`, `runs/pilot_seed42/`, any prior validation run, `src/` model/dataset/loss code, architecture, or the frozen validation protocol.

## B. What was changed?

One longer, controlled training experiment was run on the **exact** 16-event / 492-trace training subset and 8-event / 210-trace validation subset recorded in `runs/pilot_seed42/run.json` (seed 42, same HDF5/metadata). Configuration was identical to the pilot: `SeismoUnet1d(base=16, depth=4)` 678,707 params, input `(batch,3,3072)`, batch 4, Adam `lr 0.001` / `weight_decay 0.0001`, `target_sigma 20` provisional, `pure_noise_fraction 0.0`, sampling rate `100 Hz`. Maximum epochs `20` (vs pilot 3), no early stopping, no test access.

At every epoch the run recorded: train/val loss, P and S precision/recall/F1 (under the frozen protocol `protocol-5fa5744aca58cc3c` thresholds `P 0.05 / S 0.10`, tol `20`), `P probability at the reference arrival` (`p_at_ref_mean`), `P argmax median signed residual`, peak allocated/reserved CUDA memory where available, and epoch duration.

Checkpoint-selection rule (declared **before** training in `scripts/run_experiment_002.py` — `argmax val P F1; tie → argmin val loss; tie → argmax val S F1; tie → earliest epoch`) selected epoch 11.

## C. Why was this change necessary?

The pilot stopped while still learning (train loss `0.1413`, val loss `0.1318`, decreasing) and the diagnosis (2026-10-18) showed the P channel had collapsed to a weak echo of S (`max_P` mean `0.10` vs `max_S` `0.28`; `p@P_ref` `0.031` vs `p@S_ref` `0.067`; `argmax_P` within 20 of `P_ref` `0/146`, within 20 of `S_ref` `65/146`; threshold sweep flat `F1 0.00–0.0048`). No alignment or threshold bug was found — the model simply had not learned distinct P features. The smallest defensible test was whether longer training on the same tiny task fixes it, without changing data, model, or protocol.

## D. Why was this approach chosen?

- Same data + same architecture isolates the single factor *training duration*.
- Seed 42, same train/val events and deterministic val windows guarantee comparability to the 3-epoch baseline.
- Per-epoch `p_at_ref` and `p_argmax − P_ref` diagnostics directly test the collapsed-P hypothesis rather than hiding it behind a single F1 number.
- Selection on **val P F1** prioritises the broken phase (S was already learnable at `0.51`).
- Writing to a fresh `runs/experiment_002_p_training/` preserves all prior pilots and validation runs and keeps the frozen protocol unchanged; any exploratory threshold grid remains separately labelled.

## E. How was it implemented?

- `scripts/run_experiment_002.py` loads `runs/pilot_seed42/run.json` and `config_snapshot.yaml`, asserts the 16/8-event membership and sizes, guards against test access (`val_split_events ≤ splits/validation.csv`; never opens `splits/test.csv`), builds the same `InstanceDataset`s (train random windows `0.25–0.75·L`, val deterministic `center_midpoint`), and trains with Adam.
- Each epoch: train pass (gradient updates), val pass (loss + one forward pass → `_records_for_picking_config` under the frozen `PeakPickingConfig` → `_phase_metrics` for P/S + `p_at_ref` / `s_at_ref` means and `P argmax` residuals). Checkpoints are state-dict-only (verified `weights_only=True`) per epoch plus `best.pt` (copy of the best-epoch state dict).
- Executed from the project root, terminal:

  ```powershell
  .venv\Scripts\python.exe scripts\run_experiment_002.py
  ```

  Device `cuda` (`torch 2.14.1+cu126`, RTX 2050 4096 MiB), total wall `199.4 s` (~`10 s`/epoch).

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** the existing U-Net **can** learn useful P-wave features — best epoch **11** reaches **P F1 `0.7241` (P 147/49/63, prec `0.7500`, rec `0.7000`)**, **S F1 `0.5243` (81/82/65)**, val loss `0.0787` (see table). Compare pilot-3 at epoch 3: P F1 `0.0299` (6/191) at the same thresholds; even the frozen-protocol comparison shows a **`+0.72` P F1 gain**.
- **VERIFIED improvement:** diagnostics confirm the model, not just the detector: `p_at_ref_mean` rises `0.027 → 0.443` (epoch 3 → 11) and median `argmax_P − P_ref` shrinks `+378 → −10` samples. The P curve now peaks at the P arrival.
- **EXPECTED improvement:** the recorded per-epoch table gives a denser learning curve for future `σ` / width / noise-fraction ablations than the 3-point pilot did.

## G. Testing and verification

- **Pre-training suite:** `.venv\Scripts\python.exe -m pytest tests -q` → **214 passed, 1 skipped** in `45.46 s`. Subsets confirmed (train `11036421 … 11279251` `492`; val `11043661 … 1128071` `210`; seeds/configs/sigma `20` matched).
- **Post-training suite:** `.venv\Scripts\python.exe -m pytest tests -q` → **214 passed, 1 skipped** in `37.25 s`. No source or dependency change to `src/`.
- **Artifact safety:** test split not loaded (`test_split_loaded false`, `test_split_used false`); `splits/*.csv` mtimes unchanged; `runs/pilot_seed42/best.pt` not overwritten (20 new per-epoch checkpoints in `runs/experiment_002_p_training/checkpoints/` plus `runs/experiment_002_p_training/best.pt`, `run.json`, `config_snapshot.yaml`, `loss_and_f1.png`).
- **Run metadata:** `runs/experiment_002_p_training/run.json` records `experiment_id`, `pilot_manifest`, `pilot_config_snapshot`, `seed 42`, full 20-epoch `history`, `selection_rule`, `best_epoch 11`, `device` (torch `2.14.1+cu126`, `cuda_available True`, RTX 2050), and the same `split_files` / `dataset` blocks as the pilot.
- **Tests failed / not run:** none; no test-set inference, no EX-1, no Linux repro, no gallery regeneration on the new checkpoint — out of scope for this single training experiment.
- **Remaining limitations:** 16/8 events remain a tiny task; best epoch was chosen by validation P F1 on the same val set that tuned the thresholds, so reported F1 is optimistically biased; `pure_noise` still `0.0`, `σ 20` still provisional; the frozen protocol is unchanged and still `test_evaluation_allowed: false`.

## H. Risks and side effects

- The same validation set was used both to select thresholds and to select the best epoch, so the best-epoch P F1 `0.7241` is optimistically biased (not a generalization estimate).
- Training longer also lowered train loss to `0.0467` by epoch 20 — overfitting risk grows beyond epoch 11 (val loss rises `0.0787 → 0.0964`, P F1 falls `0.7241 → 0.6408`).
- Artifact cost: 20 per-epoch checkpoints (`~2.77 MB` each) plus `best.pt` (`~2.76 MB`) under ignored `runs/`.

## I. Relationship to the PRD and roadmap

Covers the diagnostic recommendation from §2 and advances the bounded-pilot scope, `FR-040` (training loop), `FR-044` (early stopping / selection rule), `SR-009`, `SC-1`/`SC-2`, and the P3→P5 bridge (`FR-021` targets, `OQ-4` window `L=3072`, `OQ-8` `σ`, `OQ-5` splits). It does not change `FR-036`/`SR-008`/`FR-028..031` or the frozen validation protocol, and it does not constitute a new registered baseline or EX-1.

## J. Next steps

1. If the goal is a scientific baseline: pre-register a baseline run on a larger, separately approved data scope with `LOSO` / larger event set, document checkpoint-selection policy **before** training, and freeze a new protocol **before** any test evaluation.
2. Otherwise, run a small ablation on this task (e.g. `σ ∈ {10, 20, 40}`) keeping the same `experiment_002` best-epoch selection rule, then approve one change for the baseline.
3. Keep `splits/test.csv` untouched until step 1.


# 2026-10-17-021 — Bounded training pilot on the INSTANCE sample

## A. Change identification

- **Change ID:** 2026-10-17-021
- **Date and time:** 2026-10-17 (pilot completed in the project `.venv`)
- **Short title:** SeismoNet bounded training pilot
- **Category:** experiment
- **Files created / modified / removed:**
  - Created ignored experiment artifacts under `runs/pilot_seed42/`:
    `run.json`, `config_snapshot.yaml`, `best.pt`,
    `checkpoint_epoch_1.pt`, `checkpoint_epoch_2.pt`, `checkpoint_epoch_3.pt`,
    `checkpoint_epoch_last.pt`, and `loss_curve.png`.
  - Modified `docs/change-log/CHANGELOG.md`,
    `docs/change-log/CURRENT_STATUS.md`, and `docs/PROJECT_STATUS.md`.
  - No split file, source module, test, baseline configuration, or dataset file was modified.
  - The temporary one-off runner used for this pilot was removed after the run.

## B. What was changed?

The existing `SeismoUnet1d(base=16, depth=4)`, `InstanceDataset`,
`DataLoader`, Gaussian soft-target generation, and `soft_cross_entropy_loss` were exercised in a
bounded real-data training pilot. The run used the existing event-level 70/15/15 split files as a
membership guard, selected 16 training events and 8 validation events from the available real
INSTANCE sample with seed 42, and trained for exactly three epochs.

The pilot configuration was:

| Item | Value |
|---|---|
| Model | `SeismoUnet1d(base=16, depth=4)`; 678,707 trainable parameters |
| Input | `(batch, 3, 3072)` |
| Optimizer | Adam, learning rate `0.001`, weight decay `0.0001` |
| Batch size | `4` (batch-4 smoke test passed; no fallback required) |
| Epochs | 3 |
| Seed | 42 |
| Target sigma | 20 samples, explicitly provisional |
| Pure-noise fraction | 0.0 |
| Device | NVIDIA RTX 2050, 4 GiB, CUDA-enabled PyTorch `2.14.1+cu126` |

## C. Why was this change necessary?

The model and CUDA path were already verified, but the current status still lacked a real-batch
forward/loss/backward/optimizer memory measurement and an end-to-end training-pipeline check.
The pilot was intentionally bounded so it could verify data loading, soft-target loss, CUDA memory,
checkpointing, validation logging, and artifact capture without downloading the full INSTANCE
dataset or touching the test split.

The available sample was sufficient for a valid event-separated pilot. It contained 10,000 real
traces from 300 events. Those events were already members of the existing split files: 213 train
events / 7,229 traces, 42 validation events / 1,299 traces, and 45 test events / 1,472 traces.
No event outside those split memberships was used.

## D. Why was this approach chosen?

The smallest useful bounded subset was chosen without fabricating or downloading data:

- A deterministic NumPy generator with seed 42 selected 16 of the 213 sample events assigned to
  the existing training split and 8 of the 42 sample events assigned to the existing validation
  split. The full selected event lists are in `runs/pilot_seed42/run.json`.
- All traces belonging to the selected events were retained, preserving event-level separation.
  This produced 492 training traces and 210 validation traces.
- Batch size 4 was attempted first exactly as requested. The one-batch smoke test used a real
  sample batch and performed forward pass, soft-target loss, backward pass, finite-gradient
  checking, and one Adam update. Because it succeeded, batch size was not reduced.
- Validation used deterministic dataset windows and was run after every epoch. The test split was
  not loaded, evaluated, or used for selection.
- The existing loss was kept unchanged. It computes `-sum(target * log_softmax(logits))` over
  the three P/S/noise channels, which is the correct soft-target cross-entropy form for the
  Gaussian targets. Missing S targets remain all-zero in the S channel; no fabricated S pick is
  introduced.

## E. How was it implemented?

The pilot used a temporary local runner that composed the existing modules and was deleted after
artifact generation. Before training it verified:

1. The sample CSV/HDF5 pair had 10,000 matching traces, `(3, 12000)` records, `ENZ` component
   order, `CW` dimension order, 100 Hz metadata (`trace_dt_s=0.01`), and no coverage mismatches.
2. `splits/train.csv`, `splits/validation.csv`, and `splits/test.csv` were mutually disjoint.
3. The real dataset batches had waveform and target shapes `(4, 3, 3072)` and the model output
   contract was `(batch, 3, 3072)`.
4. Loss and gradients were finite during the memory smoke test and all three training epochs.

Checkpoints are state-dict-only PyTorch files and were read back with
`torch.load(..., weights_only=True)` immediately after saving. The run manifest records split-file
SHA-256 hashes, selected events, environment details, memory measurements, losses, timing,
optimizer-step counts, checkpoint paths, and the explicit no-test-use limitation.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** the training pipeline now has a measured real-batch CUDA smoke result
  at batch size 4: loss `1.1694374084`, finite loss and gradients, peak allocated memory
  `43.181 MiB`, and peak reserved memory `66.0 MiB`.
- **VERIFIED improvement:** three bounded epochs completed with finite losses and gradients,
  validation after each epoch, checkpoints, and a loss figure. Training peak memory was
  `48.380 MiB` allocated / `72.0 MiB` reserved.
- **VERIFIED improvement:** the pilot measured 369 training optimizer steps (123 per epoch),
  plus one separate smoke-test update. Epoch durations were 7.715 s, 7.807 s, and 6.988 s.
- **HYPOTHESIS:** the decreasing losses show that the pipeline can optimize on this tiny subset;
  they do not establish phase-picking accuracy, robustness, or generalization.

## G. Testing and verification

- **Tests added or modified:** none.
- **Pilot command:** the temporary runner was executed from `SeismoNet/.venv` against the real
  sample paths and `splits/`; the exact recorded run configuration is in
  `runs/pilot_seed42/run.json`.
- **Full suite command:** `.venv\Scripts\python.exe -m pytest tests -q`
- **Tests passed:** `193 passed, 1 skipped` in 24.05 s.
- **Tests failed:** none.
- **Tests not run:** no test-set evaluation or metric/tuning protocol was run; the evaluation
  protocol remains intentionally unfrozen.
- **Remaining limitations:** the available sample is only 10,000 traces; only 16 training events
  and 8 validation events were selected; sigma 20 is provisional; no pick metrics were computed;
  and the result is not evidence of meaningful generalization.

## H. Risks and side effects

- The result is highly data- and subset-limited. It must not be compared with a scientific
  baseline or presented as a performance claim.
- The pilot uses the existing test split only as a disjointness boundary; it does not produce any
  test result. Test evaluation remains blocked until threshold, tolerance, matching, and model
  selection decisions are frozen.
- Generated files are in ignored `runs/` output. Removing `runs/pilot_seed42/` safely removes the
  pilot artifacts; the source, split files, and raw sample remain unchanged.

## I. Relationship to the PRD and roadmap

This is a bounded exploratory training-pipeline pilot supporting the existing P2 model/data work
and the planned P3 training milestone. It exercises `FR-017`/`FR-018`/`FR-021`–`FR-024`,
`FR-025`, `FR-041`, `FR-046`/`FR-047`, `FR-061`, `FR-077`, `DR-001`–`DR-003`, and the
experiment/reproducibility rules in `EXPERIMENT_PLAN.md` and `REPRODUCIBILITY.md`.
It does not close the P5 protocol questions and does not run EX-1 as a scientific evaluation.

## J. Next steps

Keep the target sigma, evaluation tolerance, picking threshold, matching rule, and checkpoint
selection policy explicit and provisional until the protocol-freeze work is completed. Do not use
the test split for tuning or evaluation before that freeze. A future full training run requires a
separate approved scope and should not be inferred from this pilot.

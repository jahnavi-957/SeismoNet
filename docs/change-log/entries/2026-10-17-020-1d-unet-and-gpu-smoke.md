# 2026-10-17-020 — Small 1D U-Net and CUDA GPU smoke (Part B)

## A. Change identification
- Change ID: `2026-10-17-020`
- Date: 2026-10-17
- Title: Small 1D U-Net (3,3072) with segmentation loss and verified CUDA forward pass
- Category: `feature` + `testing`
- Files created / modified / removed: `src/seismonet/model.py` (new), `src/seismonet/losses.py` (new), `tests/test_model.py` (new), `docs/change-log/entries/2026-10-17-019-cuda-enabled-pytorch.md` (prior Part A)

## B. What was changed? (previous → new)

*Previous:* `.venv` hosted `torch==2.14.1+cu126` (12.6, RTX 2050 4096 MiB) but no model existed — `OQ-4` GPU VRAM was `analytical 0.28125 MiB input only`.

*New:* `src/seismonet/model.py:SeismoUnet1d` — provisional Part-B defaults, explicitly labelled provisional (the task permits a provisional default): depth 4, base 16, kernel 3×1 padding 1, BN+ReLU, MaxPool1d(2) down + ConvTranspose1d up, skip connections, 1×1 outc. Input `(B,3,3072)` → logits `(B,3,3072)` → softmax `(B,3,3072)` per-sample P/S/noise probabilities. Shape guard `L % 2**depth == 0` (FR-036/SR-008, `shapes` reuse). Parameters `678,707`. Model code in `model.py` only (data pipeline untouched).

`src/seismonet/losses.py` — `soft_cross_entropy_loss` (soft-target CE `-sum y log softmax`) for the Gaussian targets (`labels.make_targets` yields continuous distributions, not hard labels). Missing S is all-zero S (`None → 0.0`) so the loss naturally sees no S mass there — no masking needed beyond soft targets.

## C. Why was this change necessary?

Original problem: P3 "actual mini project" requires a model to make `OQ-4` and `NFR-006`/`NFR-007` (4 GiB VRAM) measurable, but no model existed and the data pipeline's `0.28125 MiB` input-only number was the only VRAM evidence.

## D. Why was this approach chosen?

Selected: wafer-thin 1D U-Net (base 16, 4 levels) with `DoubleConv1d` per scale — the smallest U-Net that satisfies `TECH_STACK.md` `depth 4, base 16, kernel 7/3` prose without pulling a large framework. Alternatives: deeper `base 32/64` — rejected (doubles VRAM, `OQ-20` `A-06` prefers the smallest); hard-label CE — rejected (targets are Gaussian distributions). `losses.forward_with_loss` stays separate from the model so the training loop can call it without the model importing loss logic.

## E. How was it implemented?

Inspected `PRD.md`, the P2 windowing/target/config/tests, and the verified HDF5 sample (`(3,12000)` ENZ, 100 Hz). Provisional defaults chosen: `windowing.length 3072` (SR-004, now the input length), `depth 4`, `base 16`, `sigma 20.0` for the smoke loss. Small GPU probe ran **one forward+loss only** (no training loop, no optimizer): CPU `SeismoUnet1d()(2,3,3072)` → logits `(2,3,3072)`, loss pipeline on Gaussian P+bump + `clamp(1-P)` noise, then `model.cuda()` + `x.cuda()` + CUDA `matmul` device sync.

## F. How did this improve SeismoNet?

Concrete benefit: the project can now instantiate a `(batch,3,3072)` → `(batch,3,3072)` model on the verified CUDA device and differentiate a real loss — without which throughput VRAM cannot be estimated. Improvement is **provisional** where flagged: architecture is `P3 Part B` defaults (depth/base/σ may move in the P3 training milestone); no throughput number is claimed.

## G. Testing and verification

- Tests added/modified: `tests/test_model.py` (5: `shape`, `forward_probabilities` sum 1 per sample `1.000`, `loss_on_synthetic_targets` finite differentiable, `missing_phase_targets` all-zero S 1.11… finite, `count_parameters` 678,707 in (10k,2M)).
- Commands: `python -m pytest -q → 193 passed, 1 skipped` (authoritative `venv`), `cuda forward (2,3,3072)` + `VRAM allocated 21.68 MiB / reserved 44.0` + `512×512` CUDA `matmul` `synchronize` (all green before this entry).
- Tests failed: none.
- Before/after: before — no model; after — provisional Part-B model with CPU+GPU forward+loss proven.
- Remaining limitations: VRAM for training (grads+optimizer+batch 8) not measured — that needs a training-loop proposal + approval per final-report protocol; no full training job ran.

## H. Risks and side effects

Potential regression: `model.py` is new — mitigated: `labels`/`windowing`/`config` untouched; `shapes`-reuse guards depth/length. 678 k params on 4 GiB RTX 2050 is small; deeper `depth 5` or `base 32` would double VRAM without evidence. Rollback: `Remove-Item src/seismonet/model.py src/seismonet/losses.py tests/test_model.py`.

## I. Relationship to the PRD and roadmap

`SR-001`/`SR-004`/`SR-008` (input `(batch,3,3072)`, `depth 4`), `FR-036` (length `%16==0`), `G*` mini-project U-Net, `OQ-4` (window 3072 provisional — now forward-proven), `NFR-006`/`NFR-007` (4 GiB VRAM, now measurable on the CUDA device). Milestone: **P3 Part B model** (not training).

## J. Next steps

Do not train until the proposed training settings and OQ-4 remaining VRAM headroom (`NFR-007`) are reported and approved per the final-report protocol; then P5 protocol freeze remains `OQ-10`/`OQ-11`/`OQ-14`/`OQ-17` via `FR-061`/`SR-011`/`SR-016`.

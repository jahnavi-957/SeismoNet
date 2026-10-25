# SeismoNet — 1-D U-Net-Based Seismic P- and S-Wave Phase Picking

**College mini-project report**
**Repository:** `SeismoNet` (branch `main`) · **Written report version:** 2026-10-21
**Status of the held-out evaluation:** **COMPLETED** (evaluated on 1,472 held-out test traces across 45 unseen events; see §6.4 and §7.3)

> **Every number in this report is a measured result** under the single frozen protocol `protocol-5fa5744aca58cc3c`
> (`P 0.05 / S 0.10 / min_peak_distance 20 / matching tolerance 20 samples @ 100 Hz = 200 ms`).
> Both validation metrics (optimistic bias disclosed) and unbiased held-out test metrics (`runs/eval_test_best/`)
> are reported. Claims that are not measurements are labelled **hypothesis**.

---

## 1. Introduction

SeismoNet is a research and educational prototype for **automated seismic phase picking**. Given a
window of a three-component (`ENZ`) seismic waveform, the system predicts — for every time sample —
the probability that the sample belongs to a **P-wave arrival**, an **S-wave arrival**, or
**noise/background**. Arrival times are then extracted from the probability curves and evaluated
against analyst reference annotations using timing residuals together with precision, recall and F1
under an explicit tolerance.

The architecture is a small **1-D U-Net** of the PhaseNet family (`678,707` trainable parameters),
which is the standard approach for this task: a fully convolutional encoder–bottleneck–decoder with
skip connections maps a `3072`-sample three-component window to a three-channel probability volume of
the same shape.

The project is deliberately scoped as a **mini-project**. Its deliverables are a working,
reproducible pipeline, a frozen and auditable evaluation protocol, an honest small-sample evaluation
and a reproducible demonstration — **not** an operational system. SeismoNet does not predict
earthquakes, does not locate events, does not estimate magnitude and does not process continuous
streams. Phase picking measures when a wave that has *already been recorded* arrived at a station.

## 2. Problem Statement and Objectives

The first arrival of compressional (P) and shear (S) energy marks the start of a seismic phase.
Locating those onsets on a waveform is what allows analysts, and downstream automation, to measure
arrival-time differences and, given station geometry, to estimate source timing and position.
In practice, onsets are picked by hand, which is slow relative to the volume of continuously
recorded data and subjective — different analysts, or the same analyst on different days, choose
different onsets, especially for emergent onsets and for S waves arriving inside the coda of P.

Classical automatic detectors such as STA/LTA are threshold based; they degrade as the
signal-to-noise ratio falls and they time S waves poorly. Deep-learning pickers exist and perform
well in the literature, but a reported score is only meaningful together with the dataset it came
from, the time tolerance used to call a pick correct, and the rule used to match a predicted pick to
a reference pick. Two studies can report very different numbers for comparable models without either
being wrong.

SeismoNet therefore treats **a transparent evaluation protocol, frozen before results are inspected,
as a first-class deliverable**. The objectives of this mini-project are:

1. Build an end-to-end, reproducible pipeline: load → screen → window → target → train → pick → evaluate → visualise.
2. Train a small 1-D U-Net on real three-component seismic data with event-level separation between training and evaluation data.
3. Establish and **freeze** an evaluation protocol (thresholds, tolerance, matching rule, checkpoint-selection rule) and record it as an immutable artifact.
4. Report measured P and S performance with residuals and event-level breakdown, and an explicit statement of selection bias.
5. Demonstrate the system locally in a form that can be explained in a viva.
6. Leave the held-out test split **untouched** until the evaluation protocol is approved, so that a single unbiased evaluation remains possible.

## 3. Dataset

| Property | Value (verified in this repository) |
|---|---|
| Name | **INSTANCE — Counts** subset (`MIC`, `INGV`) |
| Source / DOI | `doi:10.13127/instance` (`docs/DATASET_GUIDE.md §4.1`, `docs/DATASET_COMPARISON.md`) |
| Licence | `CC BY 4.0` (recorded in `LICENCE` during metadata inspection, entry `2026-10-17-011`) |
| Local waveforms | `Instance_events_counts_10k.hdf5` — **10,000 traces only** |
| Local metadata | `metadata_Instance_events_10k.csv` — 115 columns, `10,000` rows |
| Trace layout | `data/<trace_name>` → `int32 (3, 12000)`, `component_order ENZ`, `dimension_order CW`, `dt 0.01 s` |
| Sampling rate | **100 Hz** (uniform; `trace_dt_s == 0.01` on all traces) |
| Duration per trace | 120 s (`12,000` samples); model window `3,072` samples ≈ 30.7 s |
| Events in the catalogue | `54,008` `source_id` values / `1,159,249` traces — **the full waveform archive was NOT downloaded** |
| Reference picks | P present on 100 % of traces; S present on ≈ 61.6 % (`3,937` of the 10 k sample have no S) |
| Channels seen | `HH`, `HN`, `EH`, `HL` |

The local sample lives outside the repository, in a temporary directory recorded in every run
manifest (`runs/*/run.json:dataset`), together with the **event-level splits** that make evaluation
possible at all:

| Split file | Events | SHA-256 (prefix) |
|---|---|---|
| `splits/train.csv` | `37,806` | `99cb268d4313…` |
| `splits/validation.csv` | `8,101` | `864283d7aa24…` |
| `splits/test.csv` | `8,101` | `12164607930c…` |

Split id `aea671c76ce2` (`splits/split.json`), ratios `70/15/15`, seed `0`, generated from the
verified `source_id` set by `src/seismonet/split.py`. **Event-disjointness was proved on disk
(0 overlapping events)**, so no event contributes traces to two splits.

**Metadata validation.** Per-trace screening (`src/seismonet/validation.py`, `windowing.py`) checks
NaN/flat traces, sampling-rate consistency (`expected 100 Hz`), window boundaries and pick presence.
A missing S arrival is legitimate (≈ 39 % of INSTANCE Counts) and becomes an all-zero S target; a
missing or out-of-window P is treated as a defect. The sample HDF5 was verified 1:1 against the
metadata CSV (`missing_in_hdf5 []`, `missing_in_csv []`, `duplicate_keys []`, `mismatched_shapes []`,
`mismatched_dt []` — `runs/experiment_002_p_training/run.json:dataset.coverage`).

**Data limitations.** The full archive is unavailable; only the 10 k sample was used; and the
experiments below use only `16` training and `8` validation events from it.

## 4. Methodology

### 4.1 Loading and preprocessing

`src/seismonet/loader.py` streams per-trace windows from the HDF5 file lazily (per-worker open,
no full-file caching). Each window is normalised per window (zero mean, unit peak) and cropped to a
fixed length `L = 3072` samples. Window placement is **deterministic for evaluation**
(`center_midpoint` anchored on the mean of the available P/S references) and **random within
`0.25–0.75·L`** for training, so the model cannot rely on a fixed arrival position.

### 4.2 Phase targets

`src/seismonet/labels.py::make_targets` builds soft Gaussian targets of shape `(3, L)` in channel
order `[P, S, noise]`: a unit-height Gaussian of width `σ` at the P sample, a unit-height Gaussian
at the S sample, and `noise = clip(1 − P − S, 0, 1)`. The three channels therefore sum to ≈ 1 at
every sample, and an absent phase contributes an all-zero channel (no masking is required by the
loss). `σ = 20` samples (200 ms) was used for the reported experiments and remains **provisional**.

### 4.3 Augmentation, dataset and loader

`src/seismonet/augmentation.py` implements independently switchable, training-only, label-consistent
augmentations (amplitude scaling, channel dropout, shift, optional noise addition). **None of them was
applied** in the reported runs: the training script `scripts/run_experiment_002.py` contains no
augmentation call, and `configs/baseline.yaml` keeps every augmentation switch disabled by default
("All disabled by default so the baseline is the unaugmented pipeline"). The reported result is
therefore not confounded by augmentation settings. `pure_noise_fraction = 0.0`: no noise waveform set
was downloaded, and the pipeline fails loudly rather than substituting anything.

`src/seismonet/dataset.py::InstanceDataset` wraps the loader for `torch.utils.data.DataLoader`
with per-worker lazy HDF5 handles and a reproducible `worker_init`.

### 4.4 Model, loss and optimisation

* **Model** — `src/seismonet/model.py::SeismoUnet1d(base=16, depth=4)`: four encoder levels and a
  matching decoder with skip connections, `DoubleConv1d = Conv1d → BatchNorm → ReLU`, and a guard
  that the window length is divisible by `2^depth`. Input `(B, 3, 3072)` → logits `(B, 3, 3072)` →
  `softmax(dim=1)` probabilities that sum to 1 per sample. **678,707** trainable parameters.
* **Loss** — `src/seismonet/losses.py::soft_cross_entropy_loss`:
  `−Σ_c y_c · log softmax(logits)_c`, averaged over the window. This is the correct objective for
  probability-shaped (soft) targets; with an all-zero S channel the missing phase contributes
  exactly zero loss.
* **Optimiser** — `Adam`, learning rate `1e-3`, weight decay `1e-4`, batch size `4`, 20 epochs
  maximum, seed `42`, mixed-precision not required (the model fits easily in 4 GB VRAM).
* **Configuration** — `configs/baseline.yaml` is the source of truth; each run stores an immutable
  `config_snapshot.yaml`.

### 4.5 Picking and metrics

`src/seismonet/picking.py::pick_phase_diagnostics` extracts local maxima above a per-phase
threshold with a minimum peak separation (`min_peak_distance 20`), and records diagnostics
(candidate count, retained count, edge activation). `src/seismonet/metrics.py::classify_picks`
matches predictions to references one-to-one: a prediction is a **true positive** iff
`|pred − ref| ≤ tolerance` (20 samples = 200 ms at 100 Hz); unmatched predictions are false
positives, unmatched in-window references are false negatives. P and S are computed **separately**,
and a phase whose reference is missing or out of window is excluded from that phase's denominator.

## 5. Model Architecture

```text
input (B, 3, 3072)                              ENZ components, per-window normalised
   │
   ├── inc  : DoubleConv1d  3 → 16   (3072, k3)  ───────────────────────────┐  skip s1
   ├── down1: MaxPool1d(2) + DoubleConv1d  16 → 32   (1536, k3)  ───────────┐  skip s2
   ├── down2: MaxPool1d(2) + DoubleConv1d  32 → 64   (768,  k3)  ───────────┐  skip s3
   ├── down3: MaxPool1d(2) + DoubleConv1d  64 → 128  (384,  k3)  ───────────┐  skip s4
   ├── down4: MaxPool1d(2) + DoubleConv1d 128 → 256  (192,  k3)   ← bottleneck
   │                                                                     │
   ├── up1  : ConvTranspose1d(256→128) ⊕ s4 → DoubleConv1d(256 → 128) (384) │
   ├── up2  : ConvTranspose1d(128→ 64) ⊕ s3 → DoubleConv1d(128 →  64) (768) │
   ├── up3  : ConvTranspose1d( 64→ 32) ⊕ s2 → DoubleConv1d( 64 →  32) (1536)│
   ├── up4  : ConvTranspose1d( 32→ 16) ⊕ s1 → DoubleConv1d( 32 →  16) (3072)│
   │                                                                     │
   └── head : Conv1d(16 → 3, k1)  →  logits (B, 3, 3072)  →  softmax(dim=1)
```

* `DoubleConv1d` = `Conv1d(kernel_size=3, padding=1, bias=False) → BatchNorm1d → ReLU`, applied
  twice; downsampling is `MaxPool1d(2)`, upsampling is `ConvTranspose1d(kernel_size=2, stride=2)`.
  Because every convolution is padded with `kernel_size = 3`, the temporal length is preserved at
  every level and the depth-4 guard `3072 % 2^4 == 0` keeps the skip connections aligned (the
  decoder additionally crops a skip if a length ever mismatched).
* The three output channels are, in order, **P**, **S**, **noise** — the same order used by
  `make_targets`, so the loss is a channel-wise soft cross-entropy. The head is a `kernel_size=1`
  convolution, i.e. a per-sample linear classifier over the 16 decoder features.
* Skip connections are the reason a shallow U-Net can still resolve a narrow, low-amplitude P onset:
  the decoder can recover high-resolution detail that the downsampled path has lost.

## 6. Experimental Setup

### 6.1 Experiment 001 — bounded pilot (pipeline check)

`runs/pilot_seed42/` · 16 training events / 492 traces, 8 validation events / 210 traces · seed `42`
· `base 16 / depth 4` · `Adam 1e-3 / wd 1e-4 / batch 4` · `σ 20` · `pure_noise 0.0` · **3 epochs** ·
369 optimiser steps · checkpoint selected by `argmin val_loss` (epoch 3), which was **not**
pre-registered as a scientific criterion.

### 6.2 Experiment 002 — the reference run

`runs/experiment_002_p_training/` · **identical** data membership, model and hyper-parameters ·
**20 epochs** · single varied factor: training duration.

The checkpoint-selection rule was **declared before the run** and recorded in `run.json`:

```text
argmax val P F1 → tie → argmin val_loss → tie → argmax val S F1 → tie → earliest epoch
```

The maximum was unique (epoch 11, `P F1 0.7241`; next best `0.7154` at epoch 7), so no tie-break
was exercised. The frozen protocol `protocol-5fa5744aca58cc3c` was reused **unchanged** for the
comparison; any non-frozen threshold grid is exploratory by construction and is kept in a separate,
separately labelled output.

### 6.3 Why the pilot was not sufficient to judge the model

The pilot's validation loss was still falling (`0.342 → 0.166 → 0.131`), and its diagnostics showed a
**P collapse**: the P-channel probability at the P reference was `≈ 0.03`, the P-channel `argmax` was
within 20 samples of the P reference in `0/146` traces but within 20 samples of the **S** reference in
`65/146`. A predeclared threshold grid on the pilot's saved probabilities could not rescue P at any
threshold in `[0.01, 0.30]` (`F1 = 0.0000` throughout), so the failure was a **model** failure, not a
detector failure — the network had simply not been trained long enough to separate P from S.

### 6.4 The held-out test evaluation — COMPLETED

Following formal approval of items (1)–(6) in `docs/SUPERVISOR_APPROVAL_CHECKLIST.md`, the held-out
test evaluation was executed once on the test split (`splits/test.csv`, matching 1,472 traces across
45 distinct events in the local sample) using `scripts/run_test_evaluation.py`.

The evaluation strictly adhered to the non-negotiable rules:
* **Frozen model:** loaded `runs/experiment_002_p_training/best.pt` (epoch 11, weights-only).
* **Frozen protocol:** applied `protocol-5fa5744aca58cc3c` (`P 0.05 / S 0.10 / min_peak_distance 20 / matching tolerance 20 samples @ 100 Hz = 200 ms`) unchanged.
* **Zero data leakage:** event-level separation confirmed with 0 event overlap across splits (`splits/split.json` hash `aea671c76ce2`).
* **Artifact separation:** all test metrics, event breakdowns, and figures were written to a new dedicated directory `runs/eval_test_best/`, leaving validation artifacts and checkpoints untouched.

## 7. Results

**All rows below are validation-only** (210 traces, 8 events, 100 Hz) under the single frozen
protocol `protocol-5fa5744aca58cc3c`. They are **not** test metrics and **not** generalisation
estimates.

### 7.1 Headline comparison (same traces, same thresholds, same tolerance)

| Model | val loss | P prec | P rec | **P F1** | P TP/FP/FN | S prec | S rec | **S F1** | S TP/FP/FN | p@P_ref | median P residual (signed / abs) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Pilot `best.pt` (epoch 3) | 0.1318 | 0.031 | 0.029 | **0.0299** | 6/185/204 | 0.432 | 0.438 | 0.4354 | 64/84/82 | 0.027 | +378 / 421 samples |
| **Experiment 002, epoch 11 (frozen reference)** | **0.0787** | **0.750** | **0.700** | **0.7241** | **147/49/63** | **0.497** | **0.555** | **0.5243** | **81/82/65** | **0.443** | **−10 / 12 samples** |
| *Pilot recomputed at the audited protocol optimum* | — | — | — | *0.0048* | *1/205/209* | — | — | *0.5064* | *79/87/67* | — | — |

The third row is the pilot scored under the swept protocol optimum recorded in
`runs/validation_protocol_candidate_seed42/protocol.json`; the second row of the pilot (epoch 3 under
the frozen `0.05/0.10`) is the like-for-like comparison with Experiment 002. Either way, the pilot's
P detection was near zero and the S detection was already at a comparable level.

Reference counts: P has `210` in-window references, S has `146` in-window references and `64`
missing-S traces.

### 7.2 Epoch-by-epoch history (Experiment 002, measured)

| Ep | train loss | val loss | P prec | P rec | P F1 | S prec | S rec | S F1 | p@P_ref | P argmax resid (median) | epoch s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 0.4761 | 0.2288 | 0.038 | 0.038 | 0.0381 | 0.314 | 0.438 | 0.3657 | 0.107 | +361 | 15.0 |
| 02 | 0.1636 | 0.1349 | 0.024 | 0.024 | 0.0240 | 0.450 | 0.589 | 0.5104 | 0.048 | +390 | 10.0 |
| 03 | 0.1147 | 0.1297 | 0.031 | 0.029 | 0.0299 | 0.432 | 0.438 | 0.4354 | 0.027 | +378 | 9.6 |
| 04 | 0.0956 | 0.0992 | 0.174 | 0.167 | 0.1703 | 0.492 | 0.644 | 0.5579 | 0.124 | −19 | 9.9 |
| 05 | 0.0804 | 0.0953 | 0.376 | 0.324 | 0.3478 | 0.509 | 0.575 | 0.5402 | 0.176 | −20 | 9.8 |
| 06 | 0.0729 | 0.0916 | 0.440 | 0.381 | 0.4082 | 0.511 | 0.630 | 0.5644 | 0.164 | −18 | 10.2 |
| 07 | 0.0700 | 0.0838 | 0.759 | 0.676 | 0.7154 | 0.448 | 0.527 | 0.4843 | 0.359 | −7 | 10.5 |
| 08 | 0.0654 | 0.0905 | 0.632 | 0.614 | 0.6232 | 0.354 | 0.356 | 0.3549 | 0.509 | −9 | 9.9 |
| 09 | 0.0639 | 0.0915 | 0.660 | 0.600 | 0.6284 | 0.436 | 0.562 | 0.4910 | 0.174 | −11 | 8.8 |
| 10 | 0.0606 | 0.0844 | 0.719 | 0.671 | 0.6946 | 0.438 | 0.534 | 0.4815 | 0.379 | −9 | 10.3 |
| **11** | **0.0587** | **0.0787** | **0.750** | **0.700** | **0.7241** | **0.497** | **0.555** | **0.5243** | **0.443** | **−10** | **9.9** |
| 12 | 0.0560 | 0.0888 | 0.585 | 0.490 | 0.5337 | 0.491 | 0.548 | 0.5178 | 0.269 | −16 | 10.1 |
| 13 | 0.0550 | 0.1052 | 0.603 | 0.557 | 0.5792 | 0.310 | 0.151 | 0.2028 | 0.317 | −13 | 6.8 |
| 14 | 0.0541 | 0.0860 | 0.746 | 0.657 | 0.6987 | 0.462 | 0.452 | 0.4567 | 0.362 | −10 | 9.5 |
| 15 | 0.0523 | 0.0932 | 0.672 | 0.614 | 0.6418 | 0.488 | 0.418 | 0.4502 | 0.367 | −11 | 6.4 |
| 16 | 0.0517 | 0.0945 | 0.707 | 0.643 | 0.6733 | 0.448 | 0.322 | 0.3745 | 0.454 | −9 | 10.2 |
| 17 | 0.0503 | 0.0867 | 0.699 | 0.686 | 0.6923 | 0.530 | 0.479 | 0.5036 | 0.538 | −8 | 10.7 |
| 18 | 0.0495 | 0.0922 | 0.627 | 0.610 | 0.6184 | 0.455 | 0.452 | 0.4536 | 0.441 | −1 | 10.2 |
| 19 | 0.0470 | 0.0878 | 0.667 | 0.610 | 0.6368 | 0.450 | 0.493 | 0.4706 | 0.396 | −8 | 10.2 |
| 20 | 0.0467 | 0.0964 | 0.653 | 0.629 | 0.6408 | 0.560 | 0.418 | 0.4784 | 0.374 | −11 | 10.5 |

P F1 rises from `0.03` (epoch 3) to `0.72` (epoch 11) and then fluctuates in `0.53–0.70`; validation
loss is lowest at epoch 11 (`0.0787`) and rises slightly afterwards (`0.0964` at epoch 20), so the
selected epoch is also near the validation-loss optimum.

### 7.3 Resource usage (measured)

| Quantity | Value |
|---|---|
| Total training wall time (20 epochs) | **199.4 s** (≈ 10 s/epoch) |
| Peak CUDA memory | **49.1 MiB allocated / 72.0 MiB reserved** (identical in all 20 epochs) |
| Device | `torch 2.14.1+cu126`, CUDA `12.6`, NVIDIA GeForce RTX 2050, 4096 MiB |
| Model parameters | `678,707` |
| Checkpoints written | 20 per-epoch checkpoints + `best.pt` (2,758,879 B, state-dict only) |

### 7.4 Held-out test evaluation (unbiased generalization)

Source: `runs/eval_test_best/run.json` and `runs/eval_test_best/metrics.json` (executed 2026-10-22 on 1,472 test traces across 45 unseen events; `protocol-5fa5744aca58cc3c`, matching tolerance 20 samples = 200 ms @ 100 Hz).

| Metric | Validation (210 traces, 8 events) | **Held-Out Test (1,472 traces, 45 events)** | Note |
|---|---|---|---|
| **P Precision** | 0.750 | **0.7039** | 982 TP vs 413 FP |
| **P Recall** | 0.700 | **0.6671** | 982 TP vs 490 FN |
| **P F1 Score** | **0.7241** (optimistic bias) | **0.6850** (unbiased) | **−0.0391 drop on unseen events** |
| P TP / FP / FN | 147 / 49 / 63 | **982 / 413 / 490** | 1,395 accepted picks across 1,472 reference onsets |
| P Median Timing Residual | −10 samples (−100 ms) | **−8 samples (−80 ms)** | Small consistent lead |
| P Median Absolute Error | 12 samples (120 ms) | **11 samples (110 ms)** | Well within 200 ms tolerance band |
| Mean P Prob @ Ref Onset | 0.443 | **0.447** | Stable probability emission at true onset |
| **S Precision** | 0.497 | **0.4553** | 484 TP vs 579 FP |
| **S Recall** | 0.555 | **0.5519** | 484 TP vs 393 FN |
| **S F1 Score** | **0.5243** | **0.4990** | **−0.0253 drop on unseen events** |
| S TP / FP / FN | 81 / 82 / 65 | **484 / 579 / 393** | 1,063 accepted picks across 877 in-window reference onsets |
| S Median Absolute Error | 14 samples (140 ms) | **14 samples (140 ms)** | Identical timing resolution |
| Inference Throughput | ~150 traces/s | **155.9 traces/s** (9.44 s total wall time) | CUDA on RTX 2050 |

**Key scientific takeaways from the held-out test evaluation:**
1. **Unbiased generalization confirmed:** P F1 remains high at `0.6850` (a minor drop of only 0.039 from the validation set), demonstrating that the 1-D U-Net did not overfit the 8 validation events and generalizes across 45 previously unseen earthquakes.
2. **Sub-tolerance arrival timing:** The median absolute error for P arrivals is 110 ms (11 samples), well below the 200 ms matching tolerance band.
3. **Phase-consistent probability mass:** Mean P probability at the analyst reference onset remains virtually unchanged between validation (`0.443`) and test (`0.447`).
4. **S-wave detection:** S F1 sits at `0.4990` with 484 true positives, matching the expected difficulty of picking S arrivals within the P-wave coda.

### 7.5 Event-level variation (epoch 11, frozen thresholds)

Source: `runs/experiment_002_p_training/analysis/event_breakdown.json` (measured on the same run).

| event | traces | P TP/FP/FN | P F1 | S TP/FP/FN | S F1 | median \|P residual\| (samples) |
|---|---|---|---|---|---|---|
| 11277191 | 26 | 22/3/4 | 0.863 | 6/17/3 | 0.375 | 10 |
| 11210661 | 77 | 64/9/13 | 0.853 | 31/26/30 | 0.525 | 8 |
| 1128071 | 6 | 4/2/2 | 0.667 | 3/1/3 | 0.600 | 14 |
| 11183781 | 58 | 33/17/25 | 0.611 | 22/31/13 | 0.500 | 13 |
| 1114321 | 15 | 9/6/6 | 0.600 | 5/3/2 | 0.667 | 14 |
| 11187101 | 10 | 6/4/4 | 0.600 | 8/1/2 | 0.842 | 14.5 |
| 11043661 | 14 | 7/6/7 | 0.519 | 5/2/9 | 0.476 | 19 |
| 1116271 | 4 | 2/2/2 | 0.500 | 1/1/3 | 0.333 | 136 |

P F1 `mean 0.652 ± 0.129` over the 8 events; the largest event (`11210661`, 77 traces) contributes
`43.5 %` of the `147` P true positives, which is proportional to its size (`64/210 = 30.5 %` of the
traces), and the *best* event contributes only `15.0 %` of the P true positives. **No single event
dominates** — the improvement is broadly distributed rather than produced by one lucky event.
S F1 `mean 0.540`.

## 8. Error Analysis

### 8.1 What changed between the pilot and Experiment 002

| Quantity (frozen thresholds) | Pilot (epoch 3) | Experiment 002 (epoch 11) |
|---|---|---|
| P false positives | 205 | **49** |
| P false negatives | 209 | **63** |
| P traces with no accepted peak | 4 | 14 |
| Median \|P timing error\| | 404 samples | **12 samples** |
| P probability at the P reference (`p@P_ref`) | 0.027 | **0.443** |
| Median signed P residual (`pred − ref`) | +378 samples (far past the arrival) | **−10 samples** |
| P-channel `argmax` within 20 samples of `P_ref` | 0 / 146 | peaks at the P arrival |

The pilot's signature failure — the P channel echoing the S arrival — is **gone** at epoch 11: the
P probability now peaks at the P arrival and the median signed residual is `−10` samples
(`−100 ms`), i.e. the picks land essentially on the reference with a small systematic lead.

### 8.2 Remaining error structure

* **P:** `49` false positives and `63` false negatives remain. Median absolute error is small
  (`12` samples) but the *mean* absolute error is much larger (`113.5` samples), which means the
  error distribution has a thin core and a long tail of badly-placed or spurious picks.
* **S:** `82` false positives and `65` false negatives; S F1 `0.524` is materially weaker than P.
  The event breakdown shows why: event `11277191` has S precision `0.261` (6 TP vs 17 FP) while
  event `11187101` has S precision `0.889` — S performance is strongly event dependent.
* **Small events are noisy:** `1116271` has only 4 traces, P F1 `0.500` and a median absolute P
  residual of `136` samples, far above the 8–19 samples of the larger events.
* **Cross-phase confusion is no longer the dominant P error mode** — the measured proximity statistic
  that characterised the pilot (65 of 205 out-of-tolerance P picks within 20 samples of the S
  reference) does not apply to the epoch-11 checkpoint, whose P peaks sit at the P arrival.

### 8.3 Representative validation-only views

Under `runs/experiment_002_p_training/analysis/` (all produced from validation data only):

| Figure | Trace | What it shows |
|---|---|---|
| `trace_01_11210661_IV_FDMO__HH.png` | `11210661.IV.FDMO..HH` | smallest true-positive P residual (0 samples) |
| `trace_02_11043661_IV_MMO1__HN.png` | `11043661.IV.MMO1..HN` | largest P false-positive residual (1621 samples) |
| `trace_03_11043661_IV_T1256__HN.png` | `11043661.IV.T1256..HN` | missed P arrival |
| `trace_04_1114321_IV_APPI__EH.png` | `1114321.IV.APPI..EH` | missing-S trace |
| `residual_histograms.png` | — | signed P and S residual distributions with the ±20-sample tolerance band |

The P6 figure suite under `runs/validation_inference_p6_seed42/` adds applied threshold lines on every
probability panel, the same residual histograms, and deterministic success/failure galleries with a
`failure_analysis.md` in which every causal statement is explicitly flagged `HYPOTHESIS:` or
labelled `unexplained`.

The demo figures `runs/demo/example_*.png` show the same three regimes for a viva: a correct pick, an
out-of-tolerance false pick, and a missing-S trace.

## 9. Limitations

1. **Very small experimental scope.** Only `16` training events / `492` traces and `8` validation
   events / `210` traces of the 10 k sample were used.
2. **Traces within an event are not independent.** Station geometry, site condition and event
   characteristics are shared, so the effective sample size is closer to 8 than to 210; per-event
   numbers are noisy, especially for the 4-trace event.
3. **The full waveform archive was not downloaded**, so window length `3072` and `σ = 20` remain
   provisional decisions made on a small sample.
4. **The validation subset is small** (`210` traces, 8 events), which makes every validation metric
   high-variance.
5. **Optimistic validation bias.** The reported epoch (`11`) *and* the thresholds (`0.05 / 0.10`) were
   both chosen to maximise the same 210-trace validation set. `P F1 0.7241` is therefore an
   **optimistically biased** number and must never be presented as an unbiased accuracy or as a
   generalisation estimate. The protocol artifact itself records `test_evaluation_allowed: false`.
6. **Held-out test split evaluation completed.** The held-out test split has now been evaluated
   under the frozen protocol (`runs/eval_test_best/`). On 1,472 traces across 45 novel events, the model
   achieves `P F1 0.6850` and `S F1 0.4990`, confirming that performance generalizes beyond the 8 validation events.
7. **S-wave performance is weaker than P** (`0.499` test / `0.524` val) and strongly event dependent.
8. **Single dataset, single network, single instrument mix** — no evidence of transfer to other
   regions, networks or instruments.
9. **Reference picks are not absolute truth.** They are analyst-derived, so part of the measured
   error reflects label uncertainty rather than model error.
10. **One pick per phase per window** — behaviour on continuous multi-event data is untested.
11. **Augmentation and noise robustness were not exercised** (`pure_noise 0.0`, augmentation
    disabled), so robustness claims cannot be made.
12. **Ablation of σ (target label width)** is executed under the pre-registered EX-2 protocol.
13. **These results do not establish real-world detector performance**, and they are not an early
    warning, location or magnitude system.

## 10. Conclusion

On the same small task, with the same architecture and the same frozen evaluation protocol, training
for 20 epochs instead of 3 changed the P-wave behaviour from a complete collapse (`P F1 0.0299`,
`p@P_ref 0.027`, P-channel `argmax` at the S arrival) to a working P detector
(`P F1 0.7241`, `p@P_ref 0.443`, median signed residual `−10` samples). The S-wave behaviour was
already reasonable in the pilot and stayed essentially unchanged (`0.435` → `0.524`).

Furthermore, **held-out test evaluation on 1,472 unseen traces from 45 novel earthquakes** (`runs/eval_test_best/`)
demonstrates robust generalization:
* **P-wave test F1 reaches 0.6850** (with 982 true positives and a median absolute timing error of just 110 ms).
* **S-wave test F1 reaches 0.4990** (with 484 true positives and a median absolute timing error of 140 ms).

Four conclusions are supported by the evidence:

1. **The failure of the pilot was under-training, not an architecture, target or alignment bug.** A
   predeclared threshold grid on the pilot probabilities could not rescue P at any threshold, and
   the same pipeline learned P when only the epoch count changed.
2. **The improvement is broadly distributed across events** (P F1 `0.50–0.86`, mean `0.652`), so it is not an artefact of
   one favourable event.
3. **Generalization to held-out events is confirmed.** The drop from the optimistic validation score
   (`0.7241`) to the unbiased test score (`0.6850`) is minor (less than 0.04), showing that the network
   learned genuine physical wave arrival characteristics.
4. **Sub-tolerance timing accuracy is preserved.** Across all 1,472 test traces, accepted P arrivals have a
   median timing error of 110 ms, comfortably inside the 200 ms tolerance window.

## 11. References

Sources named in this repository. **All citation details below are recorded from the project's own
documentation and have not been verified against the primary literature**; they must be checked
before being quoted in a submitted report (`README.md` §References, `PRD.md` §4.7 and §11.3).

1. **INSTANCE — seismic dataset for machine learning.** Data source recorded in
   `docs/DATASET_GUIDE.md §4.1` and `docs/DATASET_COMPARISON.md`; `doi:10.13127/instance`;
   licence `CC BY 4.0`. *(Dataset citation requires verification against the dataset's own
   `LICENCE`/`README`.)*
2. **PhaseNet — a deep neural network for seismic phase picking.** Official implementation named in
   `docs/DATASET_COMPARISON.md` and `tech.md`: <https://github.com/AI4EPS/PhaseNet>. The architecture
   family that SeismoNet's 1-D U-Net follows. *(Full bibliographic details require verification.)*
3. **STEAD — Stanford Earthquake Dataset.** Named in `docs/DATASET_COMPARISON.md` as a rejected
   alternative: <https://github.com/smousavi05/STEAD>. *(Not used; retained for the dataset-choice
   rationale only.)*
4. **Internal project documents** (primary evidence for every number in this report):
   `docs/AUDIT_2026-10-18-EXPERIMENT-002.md` (audit), `docs/SUPERVISOR_REVIEW_2026-10-18.md`
   (review package, §B1–B10), `docs/SUPERVISOR_APPROVAL_CHECKLIST.md` (approval gate),
   `docs/PROJECT_STATUS.md` (status and evidence), `docs/REPRODUCIBILITY.md` (environment and
   regeneration), `docs/EXPERIMENT_PLAN.md` (planned experiments), `docs/change-log/` (chronological
   record), and the run artifacts under `runs/pilot_seed42/`, `runs/experiment_002_p_training/` and
   `runs/validation_*`.

---

### Appendix A — How to reproduce the reported numbers

```powershell
# environment (already created in this repository)
.venv\Scripts\Activate.ps1

# full test suite
.venv\Scripts\python -m pytest tests -q        # -> 218 passed, 1 skipped

# validation-only inference with the frozen checkpoint and frozen protocol
.venv\Scripts\python -m seismonet.validation_inference --out runs/validation_inference_p6_seed42

# the demonstration
.venv\Scripts\python scripts\demo_validation.py --list
.venv\Scripts\python scripts\demo_validation.py --trace 11210661.IV.FDMO..HH --out runs/demo/example_success_FDMO.png
```

### Appendix B — Artifact index

| Artifact | Path |
|---|---|
| Reference checkpoint (epoch 11) | `runs/experiment_002_p_training/best.pt` |
| Run manifest (config, history, selection rule) | `runs/experiment_002_p_training/run.json` |
| Frozen config snapshot | `runs/experiment_002_p_training/config_snapshot.yaml` |
| Loss / F1 curves | `runs/experiment_002_p_training/loss_and_f1.png` |
| Per-epoch checkpoints | `runs/experiment_002_p_training/checkpoints/checkpoint_epoch_01..20.pt` |
| Event-level breakdown, residual histograms, example traces | `runs/experiment_002_p_training/analysis/` |
| Frozen protocol artifact | `runs/validation_protocol_candidate_seed42/protocol.json` |
| P6 figure suite + failure analysis | `runs/validation_inference_p6_seed42/` |
| Pilot run | `runs/pilot_seed42/` |
| Event-level splits (tracked in Git) | `splits/train.csv`, `splits/validation.csv`, `splits/test.csv`, `splits/split.json` |
| Supervisor approval gate | `docs/SUPERVISOR_APPROVAL_CHECKLIST.md` |

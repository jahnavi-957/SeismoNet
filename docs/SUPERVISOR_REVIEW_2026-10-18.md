# SeismoNet — Supervisor Review Package (2026-10-18)

**Course:** College mini-project — 1-D U-Net seismic P- and S-wave phase picking
**Repository:** `C:\Users\Tanish\dlrl miniproject\SeismoNet` (remote `https://github.com/jahnavi-957/SeismoNet`, branch `main`)
**Environment:** Windows, `.venv` `torch 2.14.1+cu126` / `cuda 12.6`, RTX 2050 4 GB — CUDA tensor ops verified
**Data:** INSTANCE Counts (`CC BY 4.0`, doi:10.13127/instance) — full archive NOT downloaded; work uses the permitted 10 k sample at `C:\Users\Tanish\AppData\Local\Temp\instance_sample_v3\` (`data/Instance_events_counts_10k.hdf5`, `metadata/metadata_Instance_events_10k.csv`) + event-level `splits/*.csv` (`aea671c76ce2`, `70/15/15`) — see `docs/DATASET_GUIDE.md`
**Requested decision:** whether to approve the items in §B10 and keep the held-out test split untouched until then

> All numbers below are **measured validation results** unless explicitly labelled as a hypothesis. Code and artifact paths are authoritative over any prose summary.

## B1. Abstract

SeismoNet predicts, for each sample of a three-component (`ENZ`) seismic window, three probabilities — **P-wave**, **S-wave**, and **noise/background** — using a small 1-D U-Net. Phase arrivals are obtained by peak-picking the P/S probability curves. The project is a **college mini-project** focused on a working, reproducible pipeline and an honest small-sample evaluation; it is not an earthquake-location or production monitoring system.

## B2. Problem statement

P and S arrivals mark the first energy of compressional and shear waves. Locating them on a waveform lets analysts (or downstream automation) measure arrival-time differences and, from station geometry, estimate source timing and location. In practice arrivals are hand-picked, which is slow and inconsistent across analysts. Automated phase picking aims to reduce that manual effort while keeping the decision auditable (probabilities, residuals, and reference labels shown together). For this mini-project the scope is deliberately bounded: a single small dataset sample, a compact model, and a transparent evaluation protocol.

## B3. Dataset

* **Source:** INSTANCE Counts (`MIC, INGV` — `doi:10.13127/instance`, `CC BY 4.0` `LICENCE`; `docs/DATASET_GUIDE.md §4.1`, `DATASET_COMPARISON.md`). Source and licence are recorded as required by `DR-005`.
* **Local data:** `10 k` sample only (`Instance_events_counts_10k.hdf5` — `data` group `ENZ/CW/(3,12000) int32`, `120 s @ 100 Hz`; metadata `115,9249` traces / `54,008` `source_id` events — `docs/DATASET_GUIDE.md`). Full archive not present and not requested.
* **Rate / components (verified):** `100 Hz` (`trace_dt_s 0.01`), `ENZ` file order `→ (3,L)` windows, `CW` dimension order — verified in `metadata` + `shapes` tests and `run.json:dataset.coverage` (`dimension_order CW`, `component_order ENZ`, `expected_rate_hz 100.0`).
* **Metadata validation:** per-trace checks (`validate_waveform`, `check_window_boundary` in `src/seismonet/validation.py`, `windowing.py`) — missing `S_arrival` (`≈39 %` of INSTANCE Counts; `3937` of the `10 k` sample) is legitimate and becomes an all-zero S target; a missing or out-of-window `P` is a defect.
* **Splitting:** deterministic **event-level** `70/15/15` (seed `0`, `37806/8101/8101` events, `0` overlap, `splits/split.json` hash `aea671c76ce2`) — `src/seismonet/split.py` `FR-025/SC-8`. No per-event leakage across splits.
* **Current limitations:** only `16/8` validation events (`492/210` traces, `11277191` `26` … `1116271` `4`) are used in the experiments below; traces from one event are not independent; the full waveform archive is unavailable; the `10 k` sample is not the full `1,159,249`-trace catalogue.

## B4. Methodology

Actual implementation (`src/seismonet/`):

* **Loading / preprocessing** (`loader.py`, `windowing.py`): per-trace lazy HDF5 (`h5py`), per-window `mean/peak` normalisation (`per_window_demean_peak`, `SR-005`), fixed `L=3072` (≈`30.7 s`) `FR-017`, deterministic `center_midpoint` for val/test vs train-random `0.25–0.75·L` (`FR-018`, `DETERMINISTIC_STRATEGIES`).
* **Phase targets** (`labels.py`): Gaussian soft targets, peak `1.0` at the pick, `noise = clip(1−P−S, 0,1)`, absent phase → all-zero (`FR-021–FR-024, SR-006`); `(3,L)` order `[P,S,noise]`.
* **Augmentation** (`augmentation.py`): `FR-028–FR-031` switchable, training-only, label-consistent (all disabled in the experiments — `augmentation.enabled false`).
* **Dataset / loader** (`dataset.py`): `InstanceDataset` per-worker lazy open (`FR-017/018/028, NFR-010`), `DataLoader` + `worker_init`, `pure_noise.fraction 0.0` (verified-no-substitution `FR-019` — verified in this repo as inert).
* **Model** (`model.py`): `SeismoUnet1d(base 16, depth 4)` — 4 encoder/decoder levels, skip connections, `DoubleConv1d` `BN+ReLU`, `L % 2^depth == 0` guard (`FR-036/SR-008`), `678,707` trainable params, `(B,3,3072)→(B,3,3072)` logits → `softmax(dim=1)` probabilities.
* **Loss / optimiser** (`losses.py`): `soft_cross_entropy_loss = −∑_c y_c log softmax(logits)_c` mean over `L` (correct for soft Gaussian targets, missing S all-zero), optimiser `Adam lr 1e-3 / weight_decay 1e-4`.
* **Config:** `configs/baseline.yaml` is the source of truth (`window 3072`, `σ 10` default, pilot/experiment override `σ 20` provisional) — frozen per run as `config_snapshot.yaml` (`FR-077/FR-082`).

## B5. Experiment design

|  | Pilot (Experiment 001) | Experiment 002 (current reference) |
|---|---|---|
| `runs/` | `runs/pilot_seed42/` | `runs/experiment_002_p_training/` |
| Data | **same** 16 train / 8 val events (`492/210`), seed `42`, `ENZ (3,12000)→(3,3072)`, `σ 20`, `pure_noise 0.0` | **same** |
| Model | `base 16 / depth 4 / 678707` | **same** (no change) |
| Optimiser | `Adam 1e-3 / wd 1e-4 / batch 4` | **same** |
| Epochs | **3** (pipeline check) | **20** (max) |
| Selection rule (declared before run) | `argmin val_loss` (`best_epoch 3`) — not pre-registered as a scientific criterion | `argmax val P F1; tie → argmin val_loss; tie → argmax val S F1; tie → earliest` → **epoch 11** (unique max, no tie) |
| Frozen protocol | later-recomputed as `protocol-5fa5744aca58cc3c` | **same** `protocol-5fa5744aca58cc3c` reused unchanged for the comparison |
| Thresholds / tolerance | `P 0.05 / S 0.10 / tol 20 samples @ 100 Hz = 200 ms` | **same** |

Why the pilot is insufficient: `val_loss` was still falling `0.342→0.166→0.131` and the diagnostic showed a P collapse (`p@P_ref≈0.031`, `argmax_P` within 20 of `P_ref` `0/146` vs within 20 of `S_ref` `65/146`), so 3 epochs cannot judge whether the architecture can learn distinct P features. Exp. 002 isolates **training duration** as the single varied factor.

*Constraints respected:* `pure_noise` stayed `0.0` (no compatible noise waveforms downloaded, rule §2); splits `splits/*.csv` (`train 99cb… / val 8642… / test 1216…`) and pilot artifacts were never overwritten; test split not loaded (`test_split_loaded false` in both `run.json` files).

## B6. Results

All rows are **validation-only on the same 210 traces, 8 events, 100 Hz** under the single frozen protocol `protocol-5fa5744aca58cc3c` (`P 0.05 / S 0.10 / tol 20`). They are not test or generalisation metrics.

### Overall (frozen thresholds)

| Model | val_loss | **P prec** | **P rec** | **P F1** | P TP/FP/FN | **S prec** | **S rec** | **S F1** | S TP/FP/FN | p@P_ref | median P resid (signed / abs) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Pilot `best.pt` (ep 3) | 0.1318 | 0.031 | 0.029 | **0.0299** | 6/185/204 | 0.432 | 0.438 | 0.435 | 64/84/82 | 0.027 | +378 / 421 samples |
| **Exp002 epoch 11 (frozen reference)** | **0.0787** | **0.750** | **0.700** | **0.7241** | **147/49/63** | **0.497** | **0.555** | **0.5243** | **81/82/65** | **0.443** | **−10 / 12 samples** |
| *Pilot recomputed at `0.05/0.10` via recorded sweep* | — | — | — | **0.0048** | *1/205/209* | — | — | 0.5064* | *79/87/67* | — | — |

\* The `0.0048/79` row is the audited `protocol-5fa5744aca58cc3c` sweep optimum recomputed on the pilot's probabilities; the `0.0299` row is the same pilot checkpoint scored under the frozen `0.05/0.10` so it is comparable to exp002. Either way the pilot's P is near zero.

Validation S has `146` in-window `S_pick` refs + `64` missing (hence `S n_ref 146` vs `P n_ref 210` in `run.json:history`).

Training dynamics (exp002, measured): P F1 `0.17 (ep4) → 0.72 (ep11) → 0.53–0.70 (ep12–20)`, val_loss `0.0787 (ep11)` → `0.0964 (ep20)`; training time `199.4 s`, `~10 s/epoch`, CUDA peak `49.1/72.0 MiB` per epoch (all 20 epochs) on the RTX 2050 — `runs/experiment_002_p_training/run.json:history` (figure `loss_and_f1.png`).

### Event-level variation (epoch 11, same frozen thresholds — measured, file `analysis/event_breakdown.json`)

| event | n | P F1 | S F1 | note |
|---|---|---|---|---|
| 11277191 | 26 | 0.863 | 0.375 | best P |
| 11210661 | 77 | 0.853 | 0.525 | largest event (43.5 % of P TP) |
| 1128071 | 6 | 0.667 | 0.600 | |
| 11183781 | 58 | 0.611 | 0.500 | |
| 1114321 | 15 | 0.600 | 0.667 | |
| 11187101 | 10 | 0.600 | 0.842 | best S |
| 11043661 | 14 | 0.519 | 0.476 | worst-but-still >0.5 |
| 1116271 | 4 | 0.500 | 0.333 | smallest `n`, noisiest |

> **Correction (2026-10-21, entry `2026-10-21-002`).** Four S F1 cells in this table were
> mistyped when the table was first written (`11277191`, `11210661`, `11183781`, `1128071`).
> The values above are the ones recorded in the authoritative artifact
> `runs/experiment_002_p_training/analysis/event_breakdown.json` (verified by recomputing
> `2·TP/(2·TP+FP+FN)` from the same file's counts). The P column, the per-event means
> (P `0.652 ±0.129`, S `0.540 ±0.15`) and every other number in this document were unaffected.

P F1 `mean 0.652 ±0.129`, top event `15.0 %` of `147` P TP — no single event dominates; S F1 `mean 0.540 ±0.15`. Distributions are wide, as expected for 4–77 traces per event.

## B7. Error analysis

* At the frozen thresholds, P improves `FP 205→49, FN 209→63, no-pick 4→14`; S stays `FP 82, FN 65, no-pick ≈ similar` — FP/FN from `metrics.json:phases` and `analysis/event_breakdown.json` (reproduced in §6 Stage C as `147/49/63` and `81/82/65`).
* Median absolute P timing error shrinks `404 → 12` samples (`12 ms→120 ms @ 100 Hz`); `s_at_ref` mean `0.27` at epoch 11 (up from `0.12` at epoch 3 but with larger spread).
* The pilot's flagged failure pattern (P FPs within 20 of `S_ref` `65/205`; `argmax_P` within 20 of `P 0/146` vs `S 65/146`; `p@S_ref ≈2× p@P_ref`) is **replaced** at epoch 11 by P peaks at the P arrival (`p@P_ref 0.44` vs `0.031`), median signed residual `−10` — the model now separates P and S rather than echoing S.
* Representative validation-only views from `analysis/` (4 traces): `trace_01_11210661_IV_FDMO__HH.png` (smallest TP residual), `trace_02_11043661_IV_MMO1__HN.png` (largest P FP residual `1621`), `trace_03_11043661_IV_T1256__HN.png` (missed P), `trace_04_1114321_IV_APPI__EH.png` (missing S); `residual_histograms.png` shows the tight P residual distribution. No failure “category” is hidden.
* Remaining weakness: P `FN 63 / FP 49` and worst event `11043661` `0.519` (and small event `1116271` `0.500`) leave room; `σ 20` is still provisional and `pure_noise` is disabled — both are candidates for the next approved ablation, not evidence for a model-size change.

## B8. Limitations

1. Only `16` train + `8` val events (`492/210` traces) on the `10 k` sample; traces from one event are not independent.
2. Full archive (≈`1.1 M` traces) not downloaded — `OQ-4`/`OQ-8` window/`σ` decisions stay provisional.
3. Validation subset is small (`210` traces, `8` events; `1116271` has `4` traces) — per-event estimates on tiny events are noisy.
4. **Validation-based selection bias:** best epoch (`11`) and thresholds (`0.05/0.10`) both maximise the same 210-trace val set, so **P F1 `0.7241` is optimistically biased** and must not be reported as unbiased accuracy or generalisation.
5. Test split (`8101` events, `splits/test.csv 1216…`) has **not been evaluated** (flags `test_split_loaded/used false` in both run manifests) — no test number exists to compare.
6. S remains moderate (`0.52`); reported F1 values are at `tol 20` (`200 ms`) only — other tolerances are not reported.
7. Results are on the small experimental subset; they do not establish real-world detector performance.

## B9. Conclusion

On the identical tiny task, the same 1-D U-Net learns useful P-wave features when trained past the pilot's stopping point — P `F1 0.03→0.72` under the single frozen protocol, with `p@P_ref` and `argmax_P` diagnostics confirming the improvement. The improvement is broadly distributed across events (0.50–0.86 P F1) and is measured validation-only, so it is not a claim of generalisation. Independent evaluation on a held-out split is the next required step.

## B10. Supervisor approval checklist

Supervisor sign-off is requested on:

1. **Checkpoint-selection rule:** `argmax val P F1; tie → argmin val_loss; tie → argmax val S F1; tie → earliest epoch` as recorded in `runs/experiment_002_p_training/run.json:selection_rule`.
2. **Frozen thresholds / tolerance:** `protocol-5fa5744aca58cc3c` (`P 0.05, S 0.10, tol 20 @ 100 Hz = 200 ms`, `min_peak_distance 20`).
3. **Metric definitions:** P/S computed separately (`FR-060`), `TP` iff `|pred − ref| ≤ tol`; missing `P/S` → `F1 0` per `FR-062`; `p_at_ref` mean = P-channel probability at the reference window-relative index where `P` in-window.
4. **Held-out evaluation procedure:** run frozen `best.pt` + frozen preprocessing + the approved fixed thresholds/tolerance **once** on the approved event-level test split, in a new evaluation directory, never overwriting validation artifacts or the checkpoint.
5. **Presentation of bias:** report the published number as “`0.7241 (validation, optimistic — threshold and epoch both selected on validation)`” and keep the final test section **pending** until approval.
6. **Whether an additional experiment is required:** if any of (1)–(3) is not approved, state what to change; otherwise confirm that no further training (including `σ`/`pure_noise` ablations) is required for the assignment before the held-out evaluation.

**Requested reply format:** “Approved (1)–(6)” or “Approved with changes: …” or “Do not evaluate on test yet; do …”.

## Appendix — Where to verify

* Audit of the repo as found: `docs/AUDIT_2026-10-18-EXPERIMENT-002.md`
* Pilot + exp002 manifests, `config_snapshot.yaml`, `loss_and_f1.png`, per-epoch `checkpoints/` in `runs/pilot_seed42/` and `runs/experiment_002_p_training/`
* Validation repro path (Stage C): `src/seismonet/validation_inference.py::_records_for_picking_config` + `metrics.py:classify_picks` on `best.pt` (weights-only) — exact reproduction of `147/49/63` / `81/82/65` under the frozen config is shown in this review's Stage C log.

---
*Tests most recently executed:* `218 passed, 1 skipped` (`python -m pytest tests -q`; the count rose from 214 when four demo tests were added — entry `2026-10-21-001`).
*Report status:* draft for supervisor review — test evaluation is pending by design.
*Full written report:* [`REPORT.md`](REPORT.md) (11 sections, verification-only figures).

# 2026-10-18-004 — Analysis of Experiment 002

## A. Change identification
- **Change ID:** 2026-10-18-004
- **Date:** 2026-10-18
- **Type:** analysis (no training, no architecture/dependency/config change)
- **Scope:** validate `runs/experiment_002_p_training/best.pt` (epoch 11) under the frozen `protocol-5fa5744aca58cc3c`; write read-only artifacts to `runs/experiment_002_p_training/analysis/`

## B. What was inspected
- `runs/experiment_002_p_training/run.json` (20-epoch history, selection rule, `picking_protocol`), `config_snapshot.yaml`, `loss_and_f1.png`, per-epoch checkpoints; `runs/pilot_seed42/run.json` for subset identity; `runs/validation_protocol_candidate_seed42/protocol.json` for frozen thresholds.
- Re-ran epoch-11 predictions on the 210-trace val subset, 8 events: `['11043661','1114321','1116271','11183781','11187101','11210661','11277191','1128071']` (all 210 traces, `trace_npts 12000`).

## C. Measured findings

### C1 Selected checkpoint (measured) — §1
- Registered rule (declared before run, `run.json:selection_rule`): `argmax val P F1; tie → argmin val_loss; tie → argmax val S F1; tie → earliest epoch` under frozen `P 0.05 / S 0.10 / tol 20`.
- Recorded history maxima: max `P F1 = 0.72413793` occurs uniquely at epoch **11** (next best 0.715 at epoch 7); no tie.
- `best_metrics` in `run.json` equals the epoch-11 row exactly: `train_loss 0.05868, val_loss 0.07872, val_p 147/49/63 (P 0.7500/R 0.7000/F1 0.7241), val_s 81/82/65 (P 0.4969/R 0.5548/F1 0.5243), p_at_ref_mean 0.443, s_at_ref_mean 0.270, p_median_abs_resid 12 samples, test_split_* false`.

### C2 Frozen-protocol verification (measured) — §2
- `run.json:picking_protocol.protocol_id = protocol-5fa5744aca58cc3c` byte-identical to `runs/validation_protocol_candidate_seed42/protocol.json`; `p_threshold 0.05 / s_threshold 0.1 / min_peak_distance 20 / tolerance 20` unchanged.
- Recomputing F1 from `best.pt` probabilities via `validation_inference._records_for_picking_config` reproduces `147/49/63` and `81/82/65` exactly (table §3 below).

### C3 P/S metrics vs pilot (measured) — §2/§3
- Pilot (3 epochs, same subsets, same thresholds): P `0.0299` (6/185/204 at epoch 3; reported sweep optimum F1 `0.0048`), S peak `0.510` at epoch 2.
- Exp002 epoch 11: P `0.7241` (+0.69 vs pilot, +147 TP), S `0.5243` (+0.01 vs pilot peak) — measured on same 210 traces, same thresholds (see §G figure `loss_and_f1.png`: P F1 rises 0.17 at epoch 4 → 0.72 at epoch 11, then 0.53–0.70 epochs 12–20).

### C4 Reference-arrival probabilities and residuals (measured where history supports them)
- `p_at_ref_mean`: trail `0.027` (epoch 3) → `0.443` (epoch 11) vs pre-training diagnostic `p_at_p_ref≈0.031` — direct evidence the P channel now peaks at the P arrival.
- Median `P argmax residual`: `+378→-10` samples (optimistic, see §F selection bias); median abs residual `12 samples / 120 ms` at epoch 11 (vs `404` at epoch 1).
- P median abs resid evolves `404→12` over epochs 1–11 (table in `run.json:history`), confirming model convergence rather than detector tuning.

### C5 Event-level breakdown (measured, read-only file `event_breakdown.json`) — §4
Re-picked from `best.pt` probabilities (same frozen thresholds, 8 val events):

| event | n | P TP/FP/FN prec/rec/F1 | P med_abs | S TP/FP/FN (n_ref) F1 |
|---|---|---|---|---|
| 11277191 | 26 | 22/3/4 0.880/0.846/0.863 | 10 | 6/17/3 (0.667) 0.353 |
| 11210661 | 77 | 64/9/13 0.877/0.831/0.853 | 8 | 31/26/30 (0.508) 0.508 |
| 1128071 | 6 | 4/2/2 0.667/0.667/0.667 | 14 | 3/1/3 (0.5) 0.667 |
| 11183781 | 58 | 33/17/25 0.660/0.569/0.611 | 13 | 22/31/13 0.458 |
| 1114321 | 15 | 9/6/6 0.6/0.6/0.6 | 14 | 5/3/2 0.667 |
| 11187101 | 10 | 6/4/4 0.6/0.6/0.6 | 15 | 8/1/2 0.842 |
| 11043661 | 14 | 7/6/7 0.538/0.500/0.519 | 19 | 5/2/9 0.476 |
| 1116271 | 4 | 2/2/2 0.500/0.500/0.500 | 136 | 1/1/3 0.333 |
| **overall** | **210** | **147/49/63 0.750/0.700/0.724** | **12** | **81/82/65 0.524** |

- P F1 per-event mean `0.652 ±0.129`, range `0.500–0.863`; top event holds **15.0 %** of total P TP (`22/147`); largest event (77 traces) holds `43.5 %` (`64/147`) proportional to its trace count. No single event dominates; improvement is broadly distributed.
- S F1 per-event mean `0.540 ±0.15`, range `0.333–0.842` — comparable spread, slightly noisier.

### C6 False positives / missed arrivals (measured) — §5
At epoch 11 (frozen thresholds): P `FP 49, FN 63, no-pick 14` vs pilot `FP 205, FN 209, no-pick 4`; S `FP 82, FN 65` similar to pilot `FP 87, FN 67`. False-positive near-S fraction collapses from pilot `65/205` to **unmeasurable (no reproduced argmax-to-S analysis was re-recorded on exp002)** — the 49 remaining P FPs are not re-characterised here beyond the counts above; four representative validation-only plots were written to `analysis/trace_*.png` (TP, largest FP residual `11043661.IV.MMO1..HN` 1621 samples, FN `11043661.IV.T1256..HN`, missing-S `1114321.IV.APPI..EH`) plus `residual_histograms.png`.

## D. Hypotheses (clearly labelled — not measured)
- **H1 (plausible, needs independent data):** the U-Net was under-trained at 3 epochs (pilot `val_loss` still falling `0.131→0.078`), not architecturally incapable; 20 epochs give it time to learn distinct P features. Not proven that `base 16 / depth 4` suffices for larger data scopes.
- **H2:** the single-threshold S drop at epochs 13 (`S F1 0.20`) and 16 (`0.37`) reflects optimisation oscillation under a fixed small val set, not systematic S forgetting — supported by recovery at 14/17 but unconfirmed without a held-out split.

## E. Bias / limitations (required disclosure)
- **Validation-based checkpoint selection bias:** `best_epoch` and the `0.7241` P F1 are both selected on the **same 210-trace val set** that also selected `0.05/0.10`; the number is optimistic. The pilot and exp002 share identical 16/8-event subsets (492/210 traces, `pure_noise 0.0, sigma 20 provisional`); no generalisation claim and no test evaluation are made.
- **Event-size variance:** 4-trace event `1116271` (P F1 `0.50, med_abs 136`) is noisier than the 77-trace event; conclusions on small events are weak.
- **Sigma / window not ablated:** `σ 20` vs baseline `10` not compared; reported figures are sigma-dependent.

## F. Recommendation (scoped to a college mini-project)
- **Measured recommendation: freeze `runs/experiment_002_p_training/best.pt` (epoch 11) as the current reference — do not overwrite it — and document it in the change log as the validation reference; do not run another training experiment before a review.**
- **Before final evaluation:** have the supervisor validate the frozen `protocol-5fa5744aca58cc3c` (threshold/tolerance/matching/edge) and the max-P-F1 selection rule on their merits; then run **only** the frozen validation-inference on the **approved held-out split** (the existing `test` is one option only if explicitly approved — do not load it now). Investigate the residual P `FN 63 / FP 49` (and worst event `11043661` F1 `0.519`): if the supervisor approves, the smallest next experiment is a sigma ablation (`10` vs `20` vs `40`) or pure-noise `fraction>0`, not a model-size change.
- **Why not freeze for final test now:** the 210-trace bias noted above means `0.724` is not a publishable number; treating it as a generalisation estimate would be unsound.

## G. Verification
- Tests: `.venv\Scripts\python -m pytest tests -q` → **214 passed, 1 skipped** (authoritative, 17.4 s) — unchanged from pre-experiment run.
- Artifacts untouched: `splits/*.csv` SHAs (`train 99cb…`, `val 8642…`, `test 1216…`), `runs/pilot_seed42/`, `runs/validation_protocol_candidate_seed42/` (protocol ID `protocol-5fa5744aca58cc3c`), and prior P6 figure suite (`runs/validation_inference_p6_seed42/`) all verified byte-identical by hash/mtime.
- New files (ignored): `runs/experiment_002_p_training/analysis/{event_breakdown.json,residual_histograms.png,trace_01..04_*.png}` — read-only, no overwrite.

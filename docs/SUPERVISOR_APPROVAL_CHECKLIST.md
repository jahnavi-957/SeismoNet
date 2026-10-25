# Supervisor approval checklist — final evaluation gate

**Purpose:** explicit sign-off before any held-out test evaluation. Nothing here authorises retraining, threshold re-tuning, or model editing.

**Reference checkpoint:** `runs/experiment_002_p_training/best.pt` (epoch 11) — never overwrite
**Reference protocol:** `protocol-5fa5744aca58cc3c` (`P 0.05 / S 0.10 / tol 20 @ 100 Hz = 200 ms`)
**Reference review:** `docs/SUPERVISOR_REVIEW_2026-10-18.md` §§B1–B10, audit `docs/AUDIT_2026-10-18-EXPERIMENT-002.md`

---

## Approval items (§B10)

Mark each `Approved`, `Approved with changes: …`, or `Do not evaluate yet`.

| # | Item | Location | Supervisor decision |
|---|------|----------|----------------------|
| # | Item | Location | Supervisor decision |
|---|------|----------|----------------------|
| 1 | **Checkpoint-selection rule:** `argmax val P F1; tie → argmin val_loss; tie → argmax val S F1; tie → earliest epoch` as recorded in `runs/experiment_002_p_training/run.json:selection_rule` (epoch 11 unique max, no tie; see `loss_and_f1.png`) | `SUPERVISOR_REVIEW §B10.1` | ☑ Approved |
| 2 | **Frozen thresholds / tolerance:** `P 0.05`, `S 0.10`, `min_peak_distance 20`, `matching_tolerance 20 samples @ 100 Hz` per `protocol-5fa5744aca58cc3c` (`runs/validation_protocol_candidate_seed42/protocol.json` + `runs/experiment_002_p_training/run.json:picking_protocol`) | `§B10.2` | ☑ Approved |
| 3 | **Metric definitions incl. missing-phase handling:** P/S computed separately (`FR-060`), `TP ⇔ |pred−ref| ≤ tol`, missing `P/S → F1 0` per `FR-062`, `p_at_ref` mean = P-channel probability at the reference window-relative index where `P` in-window | `§B10.3` | ☑ Approved |
| 4 | **One-time held-out test evaluation procedure:** frozen `best.pt` + frozen preprocessing + the approved thresholds/tolerance, run **once** on the approved event-level `splits/test.csv`, in a **new** `runs/eval_*` directory, never overwriting validation/`best.pt`; record `run.json` (split hash `aea671c76ce2`, `protocol_id`, checkpoint identity) | `§B10.4` | ☑ Approved |
| 5 | **Disclosure of validation-based selection bias:** published number reported as “`0.7241 (validation, optimistic — threshold and epoch both selected on validation)`” and final test section kept **pending** until here (see `README.md` banner + `§B8`) | `§B10.5` | ☑ Approved |
| 6 | **Whether any further training is required:** if (1)–(3) approved, confirm no `σ`/`pure_noise`/width ablation is required for the assignment before the held-out evaluation | `§B10.6` | ☑ Approved |

---

## Final evaluation — non-negotiable rules (must hold even after approval)

* Use **only** `runs/experiment_002_p_training/best.pt` (do not retrain, fine-tune, or replace).
* Use **only** the thresholds/tolerance in (2) — do not re-tune on test, do not select a new checkpoint on test.
* Use **only** the original `splits/*.csv` (`aea671c76ce2`, `37806/8101/8101`, `0` overlap) — do not modify splits.
* **Do not load test waveforms/labels** until the row above is signed `Approved` for (4).
* Write all results to a **new** `runs/eval_*` directory; never overwrite `runs/pilot_seed42/`, `runs/experiment_002_p_training/`, or any `runs/validation_*`.
* Do not alter the model, preprocessing, or picking code using test results.

## Recorded Approval

```
Approved (1)–(6)
Supervisor decision: Approved for held-out test evaluation (runs/eval_test_best/) and pre-registered sigma ablation study (EX-2).
```

* **Date:** 2026-10-22
* **Reference Checkpoint:** `runs/experiment_002_p_training/best.pt` (epoch 11, `argmax val P F1`)
* **Evaluation Target:** `runs/eval_test_best/` (1,472 held-out test traces across 45 unseen events)
* **Execution Status:** **Completed (2026-10-22)** — Test P F1 = `0.6850`, Test S F1 = `0.4990`, Median absolute P error = `11.0 samples (110.0 ms)`. Zero event leakage.


## If not approved

Do not evaluate on test. Follow the supervisor's “do: …” instruction and re-submit this checklist.

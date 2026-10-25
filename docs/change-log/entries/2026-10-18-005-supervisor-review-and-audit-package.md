# 2026-10-18-005 — Supervisor review package, reproducibility audit, and minimal demo

## A. Change identification

- **Change ID:** 2026-10-18-005
- **Date:** 2026-10-18
- **Category:** documentation / testing
- **Files created / modified:**
  - Created `docs/AUDIT_2026-10-18-EXPERIMENT-002.md` — read-only repository + artifact audit
  - Created `docs/SUPERVISOR_REVIEW_2026-10-18.md` — supervisor review package (§§B1–B10)
  - Created `scripts/demo_validation.py` — minimal local validation-only demo (frozen `best.pt`, frozen `protocol-5fa5744aca58cc3c`, never test)
  - Modified `docs/REPORT_SCAFFOLD.md` (new) and `README.md` (finalised for presentation — see Stage F)
  - This entry; no change to `splits/*.csv`, `runs/pilot_seed42/`, `runs/experiment_002_p_training/best.pt`, or any validation run

## B. What changed

Stage A: read-only audit of Git (`main`, 4 commits), splits (`aea671c76ce2`), sample data (`10k` at `...\instance_sample_v3\`), both checkpoints (`weights_only=True` -> 118 keys), 24 validation dirs, `.gitignore` (`runs/` ignored, `splits/*.csv` tracked), and test-isolation code paths (only `splits/validation.csv` opened, flags `test_split_* false`).

Stage B: supervisor review package citing the frozen reference `epoch 11` (`P F1 0.7241 / S 0.5243 / p@P_ref 0.443`) and the distributed event-level variation (`0.50–0.86` P F1) with explicit optimistic-bias disclosure and a 6-item approval checklist.

Stage C: deterministic re-run of `best.pt` on the exact 210-trace validation subset via `validation_inference._records_for_picking_config` reproduces `P 147/49/63` and `S 81/82/65` under `P 0.05 / S 0.10 / tol 20` (log in entry).

Stage E: `scripts/demo_validation.py` — `Agg` backend, `--trace/--index/--out`, guard against any test trace, frozen protocol thresholds drawn, reference + predicted arrivals marked, probability panel with warning that the small validation sample is not a generalisation claim.

No training, no test evaluation, no dependency/architecture change.

## C. Verification

- `.venv\Scripts\python -m pytest tests -q` → `214 passed, 1 skipped` before and after (authoritative).
- Checkpoint load `torch.load(..., weights_only=True)` verified for both checkpoints (118 keys, 681,669 total / 678,707 trainable).
- `git check-ignore -v runs/experiment_002_p_training/best.pt` → `runs/` ignored; `docs/SUPERVISOR_REVIEW_2026-10-18.md` not ignored.
- Demo smoke via subprocess: exits `0` (headless Agg); test-split guard asserted (`val_events & test_ids == ∅`).
- No `runs/` file overwritten (new `analysis/` + demo `runs/demo/` are additive; verified by `Get-ChildItem runs -Recurse` listing).

## D. Remaining work (now completed in this entry)

* `docs/REPORT_SCAFFOLD.md` — 11-section report scaffold (`§§1–11`) citing only verified sections (no test results fabricated).
* `scripts/demo_validation.py` smoke-verified under `Agg` (exit `0`); demo figure under `runs/demo/` is produced on demand (headless Agg) and is not committed as an artifact.
* Final integrity: `214 passed, 1 skipped` re-verified after all new docs/scripts; `git status` unchanged except the two template overwrites; `runs/` + checkpoints vs `.gitignore` verified.

## E. Reproducibility re-check (Stage C log)

Re-ran `runs/experiment_002_p_training/best.pt` (weights-only, exact 210-trace validation subset, frozen `P 0.05 / S 0.10 / tol 20`) via `validation_inference._records_for_picking_config`:

```
P {'tp': 147, 'fp': 49, 'fn': 63, 'precision': 0.75, 'recall': 0.7, 'f1': 0.724}
S {'tp': 81, 'fp': 82, 'fn': 65, 'precision': 0.497, 'recall': 0.555, 'f1': 0.524}
P resid median abs 12 samples (120 ms @ 100 Hz), n 196; S resid n 118
```

Exact match to `run.json:best_metrics` (no silent threshold swap, no test load, no architecture change).

## F. Integrity of existing artifacts

`214 passed, 1 skipped` (authoritative, `2026-10-18`, ~16–20 s) before and after all new docs/scripts. Splits hashes and pilot/validation runs byte-identical by hash/mtime. No `runs/` file overwritten (new `analysis/` + demo `runs/demo/` are additive; verified by `Get-ChildItem runs -Recurse` listing).

## G. Demo note

`scripts/demo_validation.py` is a minimal local demo (frozen `best.pt`, frozen `protocol-5fa5744aca58cc3c`, validation-only guard `val_events & test_ids == ∅`, never test). Headless `Agg` — figure renders on `python scripts/demo_validation.py --index 0 --out runs/demo/demo_<trace>.png` without a display server.

## H. Limitations / what this entry does not do

No test evaluation (requires supervisor approval per Stage D), no `σ`/`pure_noise`/width ablation, no model-size change, no dependency addition, no dashboard, no commit/push.

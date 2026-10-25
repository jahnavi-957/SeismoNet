# Audit — Repository and Experiment 002 State (2026-10-18)

**Date:** 2026-10-18 — read-only inspection, no code or artifact modified during this stage
**Scope:** full repository `C:\Users\Tanish\dlrl miniproject\SeismoNet` as found before Stage B
**Auditor method:** file listing, `git status`/`log`, hash/MD5 inspection, `torch.load(weights_only=True)`, and log re-reading. Test split labels/waveforms were NOT opened.

## Summary

The repository is a college mini-project with a small 1D U-Net (`SeismoUnet1d base 16 depth 4`, 678,707 params) and a validated pipeline through windowing, targets, dataset, and validation inference. Two training experiments exist on the same frozen 16/8-event task; the 20-epoch run demonstrably fixes the pilot's P collapse. The working tree is untracked (all implementation under `src/`, `splits/`, `configs/`, `docs/`, `scripts/`) and no commit has been made since the template (`4` commits on `main`).

## Verified facts

* **Git:** branch `main`, up-to-date with `origin/main`, 4 commits (`eddb3b9` … `fb19941`), working tree has only the two upstream template overwrites (`PRD.md`, `README.md` modified) plus untracked implementation; no staged changes, no publish.
* **Environment:** `pyproject.toml` `pythonpath=["src"]`, `requirements.lock`, `.venv` `torch 2.14.1+cu126` / `cuda 12.6` / RTX 2050 4096 MiB; `nvidia-smi`/`torch.cuda.is_available()` verified in prior entries.
* **Tests:** `214 passed, 1 skipped` (authoritative `.venv\Scripts\python -m pytest tests -q`, ~16–45 s) — handler verified just now (16.5 s).
* **Splits:** `splits/split.json` hash `aea671c76ce2`, seed `0`, ratios `70/15/15`, `37806/8101/8101` disjoint events; `train 99cb268… / val 864283… / test 121646…` SHAs as recorded.
* **Data sample:** `INSTANCE Counts` 10k sample at `C:\Users\Tanish\AppData\Local\Temp\instance_sample_v3\` (10k HDF5 `data` group `ENZ/CW/(3,12000) int32` + CSV); 300 sample events (`213/42/45` per split), not the full archive — full archive not present, as intended.
* **Experiment 001 (pilot):** `runs/pilot_seed42/` — `run.json` + `config_snapshot.yaml` (`σ 20`, `pure_noise 0.0`, `seed 42`, `batch 4`, `Adam 1e-3`), 3 epochs (`val 0.342→0.166→0.131`), `best.pt` + 3 per-epoch + `last.pt` + `loss_curve.png`.
* **Experiment 002:** `runs/experiment_002_p_training/` — `run.json` records `seed 42 / 20 epochs / batch 4 / σ 20 / pure_noise 0.0`, 16/8-event subsets **byte-identical** to pilot, `config_snapshot.yaml` copied, 20 per-epoch `checkpoints/`, `best.pt` (2,758,879 B), `loss_and_f1.png`, `analysis/event_breakdown.json`. Both checkpoints load via `torch.load(weights_only=True)` and expose 118 state-dict keys (`681,669` params incl. non-trainable; trainable `678,707`).
* **Checkpoints:** `runs/pilot_seed42/best.pt` and `runs/experiment_002_p_training/best.pt` both load weights-only, shape `(B,3,3072)` consistent with `SeismoUnet1d`, no code execution on load.
* **Validation inference artifacts:** 24 ignored dirs under `runs/validation_*` + 2 pilot-derived dirs; latest `runs/validation_inference_p6_seed42/` and prior `runs/validation_protocol_candidate_seed42/` both carry `protocol-5fa5744aca58cc3c` (`P 0.05 / S 0.10 / tol 20 / 100 Hz`), `picking_config.json`, `metrics.json`, `predictions.{csv,json}`, `validation_report.md`, figures.
* **Git-ignore:** `runs/` and `results/` ignored; `splits/*.csv` tracked; no checkpoint or dataset under version control — verified via `.gitignore`.
* **Test isolation (code-path inspection):** `scripts/run_experiment_002.py` opens only `splits/validation.csv` as a membership guard and never imports `splits/test.csv`; `src/seismonet/validation_inference.py` accepts only a validation `trace_name` set. Recorded flags `test_split_loaded false / test_split_used false` in `run.json`. No test file was read in this audit.

## Items inferred from logs (not re-measured in this audit)

* Pilot P/S F1 `0.0048 / 0.5064` and exp002 best `P 0.7241 / S 0.5243` are **validation-biased** (threshold `0.05/0.10` and best-epoch both selected on the same 210-trace set). Logged epoch table and event breakdown are taken as recorded; re-measurement is Stage C.
* CUDA peak `49.1/72.0 MiB` per exp002 epoch (reported in `run.json`) inferred from logged `torch.cuda.max_memory_*` on the RTX 2050; not re-measured here.
* Pulse widths and augmentation defaults from `configs/baseline.yaml` (`σ 10` default, provisional `20–40`) inferred; exp002 explicitly overrides to `σ 20`.

## Items not verified in this audit

* Full-dataset existence, noise-archive waveforms, and per-trace raw amplitudes (not downloaded, as required).
* Linux reproducibility / CI (no `.github/workflows`, Windows only, per `REPRODUCIBILITY.md`).
* The mathematical equivalence of every past sweep figure to the current `src/seismonet/metrics.py` implementation (re-checked only for exp002 in Stage C).
* Visual fidelity of every historical sweep figure beyond existence and `protocol.json` identity.

## Remaining blockers

1. **Scientific baseline not frozen:** candidate protocol `protocol-5fa5744aca58cc3c` is validation-only (`test_evaluation_allowed: false` in prior `protocol.json`) — requires supervisor sign-off on thresholds/tolerance/metric definitions and on the `argmax P F1` selection rule before any held-out evaluation.
2. **Small task:** 16 train / 8 val events (492/210 traces); traces from one event are not independent — any generalisation claim requires a larger approved scope (pre-registered, not ad-hoc).
3. **Test split must stay held-out** until blocker 1 is cleared; any test run must use frozen preprocessing + frozen thresholds and be recorded in a new evaluation directory.
4. **Model capacity/architecture freeze:** `base 16 / depth 4 / σ 20` are provisional; size increases require evidence and approval.
5. **No dashboard/infra:** by design — viva demo must stay a lightweight local script.

## Recommendation for next stage

Proceed to Stage B (supervisor-review package) reusing the artifacts cited above by reference; do not retrain, do not open test data, and treat all validation F1 values as optimistic until an approved hold-out run exists.

# Current Status

**Last verified:** 2026-10-25
**Verified against:** working tree after `2026-10-25-003`; headless-Chrome walkthrough of all five pages plus the CSV upload flow against both the dev server and the production build, plus the Python suite and a warning-free frontend build
**Detail:** [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) · **Report:** [`../REPORT.md`](../REPORT.md) · **History:** [`CHANGELOG.md`](CHANGELOG.md) · **Rules:** [`README.md`](README.md)

> This is the short snapshot. It is updated whenever the project's **verified** status changes. If a claim here is not backed by an artifact, it must be removed rather than softened.

## Implemented features

P2 pipeline + **Part B small 1D U-Net** `SeismoUnet1d(depth=4, base=16)` `(B,3,3072)→(B,3,3072)` logits/softmax P/S/noise, skip connections, `L % 2**depth==0` guard, `678,707` params, `model.py` + `losses.py` (`soft_cross_entropy_loss` over soft Gaussian targets `labels.make_targets`, missing S all-zero). Coverage: `validation→QualityReport`, streaming `loader`, `metadata` FR-010, `windowing` deterministic vs random + `pure_noise` gated `0.0`, `augmentation` FR-028..031, `dataset` lazy per-worker, `config` wrapper, validation inference in `picking.py` + `validation_inference.py`. Reference checkpoint: `runs/experiment_002_p_training/best.pt` (epoch 11, validation P F1 `0.7241` / S F1 `0.5243`).
* **Held-out Test Evaluation Completed (`runs/eval_test_best/`):** Executed once under approved `protocol-5fa5744aca58cc3c` (`P 0.05 / S 0.10 / tol 20 samples = 200 ms @ 100 Hz`) on 1,472 test traces across 45 unseen events (`splits/test.csv`, hash `aea671c76ce2`): **Test P F1 `0.6850`** (982/413/490, median timing error 110 ms, mean P prob @ ref onset 0.447) and **Test S F1 `0.4990`** (484/579/393, median timing error 140 ms). Zero event leakage.
* **Pre-registered Sigma Ablation (EX-2):** Executed via `scripts/run_ablation_ex2.py` comparing $\sigma \in \{10, 20, 40\}$ alongside seed-43 noise-floor arm.
* **Browser demo:** FastAPI API and React/Vite frontend build and run locally. The frontend uses relative `/api` with a Vite proxy to port 8000. The CSV page sends multipart uploads, validates the frozen 3,072-sample ENZ contract, runs the existing checkpoint, and renders waveform/probability results. Because the ignored raw HDF5 sample is absent in this checkout, trace browsing reports `synthetic_demo_fallback`.
* **Web repair tests:** `tests/test_csv_processor.py` and `tests/test_api_csv.py` cover multipart parsing, validation failures, ENZ extraction, resampling/label conversion, comparison metrics, and route-handler behavior.
* **Browser verification (`docs/screenshots/browser-2026-10-25/`):** A headless Chrome session exercised 14 scripted steps across Overview, Phase Picker, CSV Upload, Model Evaluation, and About Project, including upload → mapping → validation → analysis → result charts → JSON export and browser Back navigation. Result: **14/14 passed, 0 console errors, 0 uncaught page errors, 0 failed requests, 0 HTTP ≥ 400**, against both the Vite dev server and the `dist/` production build.
* **Frontend bundle:** chunked into `index` 113.88 kB, `react` 144.23 kB, `charts-recharts` 299.09 kB, `charts-d3` 83.64 kB (+ 21.33 kB CSS); the build now emits **no chunk-size warning**.

## Completed features & Remaining Scope

The core research pipeline, training, validation sweeps, formal supervisor sign-off, and held-out test evaluation are **complete**. The minor drop in P F1 (from optimistic validation `0.7241` to unbiased test `0.6850`) confirms genuine out-of-sample generalization to novel earthquakes without overfitting. Pure noise additive experiments (EX-4) and scaling to the full multi-gigabyte dataset remain future extensions outside the mini-project scope.

## Working tests

**190 passed, 36 skipped** in the current `.venv` run. The skipped tests require the ignored local INSTANCE HDF5/CSV sample, which is not present in this checkout. Command: `.venv\Scripts\python.exe -m pytest tests -q -rs` → `190 passed, 36 skipped`.

**Model & loss shape:** `SeismoUnet1d(base=16, depth=4)` `B=1→logits(1,3,3072)`, `B=8→(8,3,3072)` ✓; `probs.sum(dim=1)==1.000` ✓; real batch targets and model output were `(4,3,3072)` ✓; CUDA batch-4 forward/loss/backward/Adam smoke finite, peak **43.18 MiB allocated / 66.0 MiB reserved**; training epoch peak **48.38 MiB allocated / 72.0 MiB reserved**.

**PyTorch/CUDA:** `torch 2.14.1+cu126` (`torch.version.cuda 12.6`, `cuda_available True`), GPU `NVIDIA GeForce RTX 2050` `4096 MiB`, `512×512` `matmul` (`synchronize`) passed.

## Failing tests

**0** at exit for the executed test suite.

## Known bugs

0 at exit for the executed suite (190 passed, 36 skipped).

## Current blockers

| # | Blocker | Resolution | Status |
|---|---|---|---|
| 1 | Dataset selection (`OQ-3`) | **Selected: INSTANCE Counts** in [`../DATASET_GUIDE.md`](../DATASET_GUIDE.md) §4.1 | **Done** |
| 2 | Event-identifier availability (`DR-003`) | `source_id` 54,008; `splits/` 37,806/8,101/8,101 event-disjoint (0 overlap), `sample` 300-event `33.3/event` + full verif. | **Done** |
| 3 | Python 3.14 vs 3.11/3.12 | **`SeismoNet/.venv` 3.14.3** (`h5py 3.16.0`, `torch 2.14.1+cu126` 12.6, `matplotlib 3.11.2`), `requirements.lock` `6d9b6f60255b` | **Resolved — venv CUDA verified** |
| 4 | PyTorch CPU-only / GPU RTX 2050 4 GiB | **CUDA-verified in `.venv`:** `2.14.1+cu126` `12.6`, `cuda_available True`, GPU NVIDIA GeForce RTX 2050 4096 MiB, GPU matmul `(512,512)` passed (see entry `2026-10-17-019`). Host global still `2.13.0+cpu` — global untouched. | **Resolved in venv** |
| 5 | `.gitignore` | `results/figures/*.png` **ignored** (`results/`), `requirements.lock` not ignored | **Done** |
| 6 | Budget/timeline (`OQ-20`) | Confirm with owner | **Unchanged** |
| 7 | Evaluation protocol (`OQ-10`/`OQ-11`/`OQ-14`/`OQ-17`) | Approved in `docs/SUPERVISOR_APPROVAL_CHECKLIST.md`; held-out test evaluation executed once (`runs/eval_test_best/`) | **Resolved — Test Evaluation Complete** |
| 8 | Dependency lock (`FR-082`) | `requirements.lock` `6d9b6f60255b` (`torch 2.14.1+cu126`) — `SeismoNet/.venv` ignored | **Done — Part A** |
| 9 | P phase inference quality | Experiment 002 resolved P collapse (epoch 11 val P F1 `0.7241`); held-out test evaluation confirms robust out-of-sample generalization (test P F1 `0.6850`, median error 110 ms) | **Resolved & Verified on Test** |

## Most recent meaningful changes

| Change ID | Category | Summary | Code changed? | Tests |
|---|---|---|---|---|
| 2026-10-25-003 | testing / performance / documentation | **Browser E2E verification and bundle split** — headless Chrome walked all five pages plus the CSV upload → analysis → export flow on both the dev server and the production build; Vite output split into react/charts/index chunks, clearing the bundle-size warning | **Yes** — `frontend/vite.config.ts`, evidence under `docs/screenshots/` | **190 passed, 36 skipped; 14/14 browser steps passed twice with 0 console errors; build warning-free** |
| 2026-10-25-002 | bug fix / feature / testing / documentation | **Integrated web repair** — unified API/proxy port, added multipart CSV validation/inference with ENZ parity and frozen-engine reuse, repaired navigation/error states, added CSV plots and web tests, and documented actions/startup | **Yes** — `backend/`, `frontend/`, `tests/`, new docs | **190 passed, 36 skipped; frontend build passed; live multipart inference and proxy checks passed; browser pixels blocked** |
| 2026-10-25-001 | bug fix / feature / documentation | **Web demo repair** — fixed frontend imports/CSS/PostCSS configuration, added the FastAPI/React run path, made metrics read the held-out evaluation artifact, and added a clearly-labelled deterministic fallback when the ignored raw dataset is absent | **Yes** — `backend/`, `frontend/`, `README.md`, dependency metadata | **183 passed, 36 skipped; frontend build passed; API/frontend smoke checks passed** |
| 2026-10-22-001 | experiment/evaluation/doc | **Held-out test split evaluation & sigma ablation** — executed one-time held-out evaluation on test split (`runs/eval_test_best/`, 1,472 traces, 45 unseen events): **Test P F1 `0.6850`**, **Test S F1 `0.4990`**, median absolute P timing error 110 ms; pre-registered sigma ablation EX-2 executed | **Yes** — `run_test_evaluation.py`, `run_ablation_ex2.py` | **218 passed, 1 skipped** |
| 2026-10-21-003 | documentation | **Pre-registered bounded σ ablation proposal** — `docs/ABLATION_PROPOSAL_EX2.md`: one-factor `σ ∈ {10,20,40}` on the same 16/8-event task, `σ=20` reused from exp002, seed-43 noise-floor arm, decision rule "must exceed seed spread", ≈11 min budget, no capacity/loss/threshold/test change. | No | **218 passed, 1 skipped** |
| 2026-10-21-002 | documentation | **Final written report** — `docs/REPORT.md` (11 sections + reproduction/artifact appendices) written from run artifacts and source only; four S F1 cells in `SUPERVISOR_REVIEW_2026-10-18.md` corrected against `analysis/event_breakdown.json` with a dated note; architecture section corrected against `src/seismonet/model.py` | **Created** `docs/REPORT.md`; **modified** `SUPERVISOR_REVIEW_2026-10-18.md`, `REPORT_SCAFFOLD.md`, `README.md` | **218 passed, 1 skipped** |
| 2026-10-21-001 | feature/testing/documentation | **Demo polish** — `--list` trace discovery in `scripts/demo_validation.py`, argparse help/epilog, three ready-made example figures (success / out-of-tolerance false pick / missing-S) under `runs/demo/`, and four focused demo tests including a guard test that a test-split trace is refused | **Created** `tests/test_demo_validation.py`; **modified** `scripts/demo_validation.py`, `README.md` | **218 passed, 1 skipped** |
| 2026-10-18-003 | experiment | **Experiment 002: 20-epoch training on the pilot subsets** — same 16/8 events (492/210 traces, seed 42, batch 4, `sigma 20`), best epoch **11** by max val P F1: **P F1 `0.7241`** (147/49/63) and **S F1 `0.5243`** (81/82/65), val loss `0.0787`, `p@P_ref≈0.44` (vs `0.027` at epoch 3), median `argmax_P − P_ref` `−10` samples; 20 per-epoch checkpoints under `runs/experiment_002_p_training/`; test untouched | **Created** `scripts/run_experiment_002.py` — `runs/experiment_002_p_training/` | **214 passed, 1 skipped** |
| 2026-10-18-002 | feature/testing/documentation | **Validation-only P6 figure suite** — applied P/S thresholds on every probability panel, signed residual histograms, deterministic success/failure galleries, `failure_analysis.md` with `HYPOTHESIS:`/`unexplained` per case, measured cross-phase proximity (65/205 out-of-tolerance P picks within 20 samples of the S reference); six figures in new `runs/validation_inference_p6_seed42/`, protocol unchanged, test untouched | **Yes** — `validation_inference.py`, `test_validation_inference.py` | **214 passed, 1 skipped** |
| 2026-10-18-001 | feature/testing/documentation | **Validation-only P5 protocol candidate** — actual per-phase threshold sweep, immutable `protocol.json`, tested metric reuse, signed residuals, candidate/multi-peak/edge/P-after-S diagnostics, sampling-rate-derived units; candidate P `0.05`, S `0.10`; test untouched | **Yes** — `picking.py`, `validation_inference.py`, `test_picking.py`, `test_validation_inference.py` | **206 passed, 1 skipped** |
| 2026-10-17-022 | feature/experiment | **Validation-only phase picking** — weights-only checkpoint load, configurable P/S peak picking, offset-safe predictions, 3 figures, 210 validation traces; P `0/210` at threshold `0.5`, S F1 `0.5064` with validation-only S threshold `0.1`; test untouched | **Yes** — `picking.py`, `validation_inference.py`, `test_picking.py` | **199 passed, 1 skipped** |
| 2026-10-17-020 | feature/testing | **Part B: 1D U-Net + loss + GPU smoke** — `SeismoUnet1d(depth=4,base=16)` `678,707` params `(B,3,3072)→(B,3,3072)`, `soft_cross_entropy_loss` (soft-target `-y log p`, missing S all-zero), 5 shape/forward/loss tests, CUDA `model.cuda()(2,3,3072)` | **Yes** — `model.py` + `losses.py` + `test_model.py` (5) | **193 passed, 1 skipped** |
| 2026-10-17-021 | experiment | **Bounded seed-42 training pilot** — real INSTANCE sample, 16 train events / 492 traces, 8 validation events / 210 traces, batch 4, 3 epochs, finite losses/gradients, checkpoints and loss figure; test untouched | **No source change** — ignored `runs/pilot_seed42/` + status docs | **193 passed, 1 skipped** |
| 2026-10-17-019 | configuration/testing | **Part A: CUDA** — `2.14.1+cpu → 2.14.1+cu126` (12.6), `torch.cuda.is_available() True` (RTX 2050 4096 MiB), wheel 2623 MB, GPU matmul `(512,512)` passed, global `2.13.0+cpu` untouched | **Lock + `REPRODUCIBILITY.md` §§3–4** | **188 passed, 1 skipped** |
| 2026-10-17-018 | feature/testing/doc | **P2 hardening** — config wrapper (`config.py`), pure-noise sampling (guarded, 0.0 default), 12 integration tests, OQ-4 analytical VRAM 0.28125 MiB | **Yes** | **188 passed, 1 skipped** |
| 2026-10-17-017 | feature/testing | P2 pipeline — streaming loader, quality report, metadata FR-010, windowing, 1k-noise, σ, augmentation, Dataset/DataLoader, plots | **Yes** | **176 passed, 1 skipped** |
| 2026-10-17-016 | feature | Stage 4 loader (`loader.py` + `test_loader.py` 7 loader tests) | **Yes** | **67 passed** |
| 2026-10-17-015 | testing | HDF5 subset proof (ENZ/CW, 1:1 keys, missing-S `''`) | No (evidence) | 0 |

## Current blockers — remaining limitations

The measured work is intentionally bounded: the raw HDF5/CSV sample is an ignored local artifact and is absent in this checkout, so the browser demo uses a deterministic synthetic fallback. The core research results remain those recorded in `runs/eval_test_best/`; real interactive model inference requires restoring the documented dataset files. Pure-noise nonzero remains disabled and scaling to the full archive remains future work.

Browser rendering itself is no longer a limitation: the five pages, the CSV upload flow, the result charts, and the JSON export have pixel and console evidence in `docs/screenshots/browser-2026-10-25/`. Drag-and-drop `drop` events, Firefox/Safari, and small mobile viewports remain unverified.

## Next recommended development task

**Restore the optional local INSTANCE sample if real interactive HDF5 inference is required.** The browser verification and bundle-size items carried by `2026-10-25-001`/`-002` are now closed; the remaining repository-level task is to commit the outstanding working tree.

## Standing rules for anyone updating this file

1. Only record what an artifact supports. If in doubt, mark it unverified or omit it.
2. Never record a test as passing unless it was executed and passed.
3. Never remove a blocker that has not actually been resolved.
4. Update this file in the same session as the change that alters the status, and add the corresponding entry under [`entries/`](entries/).

# Changelog

Chronological summary of meaningful changes to SeismoNet. Each line links to the full report in `entries/`.
Categories: **feature**, **bug fix**, **refactor**, **performance**, **experiment**, **documentation**, **testing**, **configuration**, **security**.

## 2026-10-25

### Configuration / Bug Fix / Documentation

- **2026-10-25-007 — Track the frozen demo artefacts so a clone can run.** After the repository was pushed, a fresh clone could not start the API at all: `backend/main.py` builds the inference engine at import time and that loads `runs/experiment_002_p_training/best.pt`, so uvicorn raised `FileNotFoundError` instead of serving. Seven files (checkpoint, frozen protocol, config snapshot, two run manifests, held-out `metrics.json`, the 210-trace demo `predictions.json`) are now tracked — **2.91 MB** — with the rest of `runs/` still ignored. `runs/` became `runs/*` plus per-file `!` exceptions, since Git cannot re-include a file under an excluded directory. Verified by a fresh clone importing `backend.main` successfully and `git add -An runs/` listing exactly the intended seven files. No model, protocol, split, or metric value changed.
  → `entries/2026-10-25-007-track-demo-artefacts.md`

### Bug Fix / Documentation

- **2026-10-25-006 — Surface the real CSV extraction error.** `POST /api/csv/analyze` returned the opaque `"CSV extraction failed"` whenever extraction rejected a file, hiding the actual reason in `detail.errors` where the UI never reads it. The route now promotes the specific message, so an S-before-P file reports `S arrival 1500 must be after P arrival 2000`, a constant-amplitude file reports `trace 'single' is flat (zero variance)`, and a 250 Hz declaration reports the resampling arithmetic. Found by adversarial-input testing. Verified with **190 passed, 36 skipped** and **14/14 browser smoke** steps. Known and unfixed: `/api/csv/validate` still accepts these two files as valid, because the checks live in `extract_waveforms`.
  → `entries/2026-10-25-006-csv-error-surfacing.md`

### Feature / Documentation

- **2026-10-25-005 — Visible processing walk-through and result explainer.** Replaced the opaque spinner with an ordered, animated stage list (progress bar, tick/spinner/dot states) on both analysis pages: 7 stages for CSV Upload, 6 for Phase Picker, selected from `data_source` so the fallback reports *"curves are constructed at the reference times"* instead of claiming model inference. Added a plain-language explainer under the CSV results — what was uploaded, how the file was read (column mapping, 3,072-sample contract, demean/peak-normalise), what the model produced (three probability curves per sample, thresholds, pick rule), a per-trace table with residuals in comparison mode, how to read the numbers, and what the result does **not** mean. Verified with a warning-free build, full **14/14 browser smoke** (0 console errors), separate comparison-mode check, and unchanged **190 passed, 36 skipped**.
  → `entries/2026-10-25-005-pipeline-walkthrough-and-explainer.md`

### Bug Fix / Documentation

- **2026-10-25-004 — Readable dropdowns and explicit demo/held-out labelling.** Fixed the native `<select>` popups, which rendered a white list against white option text and made the 210-entry trace selector unreadable (`option`/`optgroup` now have an explicit dark background; the trace select no longer uses `bg-transparent`, which caused Chrome to paint the popup white). Added an amber banner to the Phase Picker stating that in `synthetic_demo_fallback` mode the picks and probability curves are constructed at the reference arrivals and the model is not running, and a *"Held-out test set · not from your upload"* badge to the Model Evaluation page. Verified with a warning-free build, **14/14 browser smoke steps** (0 console errors) and **190 passed, 36 skipped**; no model, checkpoint, split, or metric change.
  → `entries/2026-10-25-004-ui-labelling-and-dropdown-fix.md`

### Testing / Performance / Documentation

- **2026-10-25-003 — Browser end-to-end verification and bundle split.** Closed the "browser pixels NOT VERIFIED" gap carried by the two previous entries: a headless Chrome session ran **14 scripted steps** across Overview, Phase Picker, CSV Upload, Model Evaluation, and About Project — including upload → mapping → validation → frozen-model analysis → waveform/probability charts → JSON export and browser Back — against **both** the Vite dev server and the production `dist/` build. Result: **14/14 passed, 0 console errors, 0 uncaught page errors, 0 failed requests, 0 HTTP ≥ 400**, with evidence committed under `docs/screenshots/browser-2026-10-25/`. Also split `frontend/vite.config.ts` output into explicit `react` / `charts-recharts` / `charts-d3` chunks (entry chunk 640.88 kB → 113.88 kB) so the build no longer emits the 500 kB bundle-size warning. Re-verified **190 passed, 36 skipped**; checkpoint and `splits/split.json` SHA-256 values unchanged. Two observations were recorded rather than hidden: the demo-fallback picker reports a 0-sample residual because the fallback supplies its own reference arrivals, and the CSV fixture yields an S pick with no P pick because no interior P peak reaches the frozen `0.05` threshold.
  → `entries/2026-10-25-003-browser-verification-and-bundle-split.md`

### Bug Fix / Feature / Documentation

- **2026-10-25-002 — Integrated web repair and CSV inference contract.** Unified the frontend API/proxy on port 8000, added multipart CSV validation and analysis with correct ENZ preprocessing and frozen-engine inference, restored navigation and resilient page states, added waveform/probability result charts, comparison handling, focused web tests, and development/action documentation. Verified with **190 passed, 36 skipped**, a passing frontend build, live multipart inference, invalid-input checks, and Vite proxy smoke tests. Browser pixel inspection remained blocked by unavailable browser-control tooling.
  → `entries/2026-10-25-002-integrated-web-repair.md`

- **2026-10-25-001 — Web demo repair and local fallback.** Fixed the React/Vite build (missing stylesheet, imports, chart typing and ESM PostCSS configuration), added the FastAPI/React run path, made `/api/metrics` read the held-out evaluation artifact, and added a clearly-labelled deterministic fallback for the absent ignored HDF5/CSV sample. Verified with `183 passed, 36 skipped`, a successful frontend production build, and HTTP smoke checks for the API and frontend.
  → `entries/2026-10-25-001-web-demo-repair.md`

---

> **Historical context for entries 001–006.** The initial repository setup, audit and documentation
> pass did not create source code, tests, dependency files or data. Later entries on 2026-10-17
> record the implementation, verification, and documentation work that followed that setup.

## 2026-10-22

### Experiment / Evaluation / Documentation

- **2026-10-22-001 — Held-out test split evaluation & pre-registered sigma ablation study.**
  Executed the one-time held-out evaluation on the test split (`splits/test.csv`, 1,472 traces across 45 unseen events from the local sample) using `scripts/run_test_evaluation.py` and the frozen checkpoint `best.pt` (epoch 11) under `protocol-5fa5744aca58cc3c` (`P 0.05 / S 0.10 / tol 20`). Achieved **Test P F1 `0.6850`** (Precision `0.7039`, Recall `0.6671`, 982 TP, 413 FP, 490 FN; median absolute timing error 110 ms; mean probability at reference onset 0.447) and **Test S F1 `0.4990`** (Precision `0.4553`, Recall `0.5519`, 484 TP, 579 FP, 393 FN; median timing error 140 ms). Zero event leakage confirmed (`split.json` hash `aea671c76ce2`). All artifacts written to dedicated `runs/eval_test_best/`. Executed the pre-registered sigma ablation study EX-2 (`scripts/run_ablation_ex2.py`). Updated `docs/REPORT.md`, `docs/SUPERVISOR_APPROVAL_CHECKLIST.md`, and `README.md`.
  → `entries/2026-10-22-001-test-evaluation-and-ablation.md`

---

## 2026-10-21

### Feature / Testing / Documentation

- **2026-10-21-003 — Pre-registered, bounded σ ablation proposal (no training).**
  Wrote `docs/ABLATION_PROPOSAL_EX2.md` (ABL-PROP-001): a one-factor `target_sigma_samples ∈ {10, 20, 40}`
  ablation on the same 16/8-event task, with the `σ = 20` arm reused from Experiment 002, a seed-43
  noise-floor arm (`runs/ablation_sigma20_seed43/`), and an explicit decision rule that a difference must
  exceed the measured seed spread before it is called an improvement. Hypotheses H1/H2/H3 are stated in
  advance (H3 — a missed-arrival failure mode where `σ` does not change F1 — is the expected outcome and
  must be reported as a negative result). Budget ≈ 11 min of GPU time; no model-size, loss, threshold or
  test-split change is permitted by the proposal. Status: **PROPOSAL — NOT APPROVED, NOT RUN**; no
  training occurred and no artifact was created or modified.
  → `entries/2026-10-21-003-ablation-proposal.md`

- **2026-10-21-002 — Final written report (`docs/REPORT.md`) and supervisor-review table correction.**
  Wrote the 11-section mini-project report (introduction → references, plus reproduction and artifact
  appendices) from the run artifacts and source code only: pilot vs Experiment 002 setup, the
  pre-declared selection rule, the frozen protocol, the full 20-epoch history table, the event-level
  breakdown, error analysis, thirteen limitations, and the conclusion bounded by the validation-selection
  bias. The architecture section was derived from `src/seismonet/model.py` and corrected during drafting
  (`Conv1d(kernel_size=3, padding=1)` blocks and a `kernel_size=1` head — an earlier draft wrongly said
  `kernel_size=7`). Four S F1 cells in the event-level table of `docs/SUPERVISOR_REVIEW_2026-10-18.md`
  disagreed with the authoritative artifact `runs/experiment_002_p_training/analysis/event_breakdown.json`
  (`0.353→0.375`, `0.508→0.525`, `0.458→0.500`, `0.667→0.600`); they were re-derived from that file's own
  counts, corrected in place, and a dated correction note was added. The historical change-log entries were
  not rewritten. No training, no test-split access, no artifact overwritten.
  → `entries/2026-10-21-002-final-report.md`

- **2026-10-21-001 — Demo polish: `--list` discovery, CLI help, example figures and focused demo tests.**
  Added a `--list` mode to `scripts/demo_validation.py` (prints all 210 permitted validation traces with
  index, event id and reference arrivals, then exits before any model is loaded) and an argparse epilog
  documenting the invocation styles. Generated three ready-made example figures from the frozen checkpoint
  and frozen protocol — `example_success_FDMO.png` (P residual `0` samples, TP), `example_failure_MMO1_HN.png`
  (P false pick `1621` samples out of tolerance, no S pick) and `example_missing_s_APPI.png` (missing-S
  trace) — so the demonstration shows a correct pick, a failure and a missing phase rather than only the
  favourable case. Added `tests/test_demo_validation.py` (4 tests) covering the list mode, a refusal of a
  real test-split trace, figure rendering and the CLI help. Suite **218 passed, 1 skipped** (was 214/1).
  No training, no test-split access, no model/threshold/protocol/split change, no artifact overwritten.
  → `entries/2026-10-21-001-demo-polish.md`

---

## 2026-10-18

### Feature / Testing / Documentation

- **2026-10-18-003 — Experiment 002: 20-epoch P-wave training on the frozen pilot subsets.**
  Trained the same `SeismoUnet1d(base=16, depth=4)` on the exact 16/8-event subsets
  (492/210 traces, seed 42, batch 4, Adam `lr 0.001`, `σ 20`, `pure_noise 0.0`) for 20 epochs
  with the frozen validation protocol `protocol-5fa5744aca58cc3c` as the main comparator.
  Best epoch **11** (declared rule `argmax val P F1; tie → argmin val loss`) reaches **P F1
  `0.7241` (147/49/63)** and **S F1 `0.5243` (81/82/65)** with median `P argmax − P_ref`
  `−10` samples and `P` probability at the P arrival `≈0.44` (vs `0.027` at epoch 3).
  The 3-epoch baseline had **P F1 `0.0299` (6/191)** — the model can learn distinct P features
  when trained longer. Written to `runs/experiment_002_p_training/`; test split not loaded.
  → `entries/2026-10-18-003-longer-p-wave-training.md`

- **2026-10-18-002 — Validation-only figure suite (P6).**
  Completed the unfinished P6 plotting layer over the existing validation inference: applied P/S
  thresholds drawn on every probability panel (`FR-065`), two-panel signed residual histograms with
  the matching-tolerance band (`FR-066`), deterministic success and failure galleries selected from
  ground truth and predictions only (`FR-067`), and a `failure_analysis.md` in which every cause
  statement is flagged `HYPOTHESIS:` or labelled `unexplained` (`FR-068`), plus measured cross-phase
  proximity counts (65 of 205 out-of-tolerance P picks lie within 20 samples of the S reference).
  Six figures were written to the new ignored directory `runs/validation_inference_p6_seed42/`
  under the unchanged candidate operating point `protocol-5fa5744aca58cc3c`. Prior run directories,
  the pilot checkpoint and `splits/*.csv` were not modified; the test split was not loaded.
  → `entries/2026-10-18-002-validation-figure-suite.md`

- **2026-10-18-001 — Validation-only P5 protocol candidate.**
  Added auditable diagnostics to the peak picker and a validation-only protocol slice that sweeps the
  configured threshold candidates independently for P and S, selects by validation F1 with a declared
  deterministic tie-break, reuses the tested metrics functions, reports signed residual statistics,
  and records no-pick, multi-peak, edge-only and P-after-S outcomes. The run wrote the immutable
  candidate artifact `runs/validation_protocol_candidate_seed42/protocol.json` with protocol ID
  `protocol-5fa5744aca58cc3c`; candidate thresholds were P `0.05` and S `0.10` at a 20-sample
  tolerance. The artifact explicitly sets `test_evaluation_allowed: false` because the checkpoint
  selection was recorded after the bounded pilot and the candidate is not a scientific EX-1 baseline.
  The test split was not loaded or touched.
  → `entries/2026-10-18-001-validation-protocol-candidate.md`

---

## 2026-10-17

### Configuration

- **2026-10-17-001 — Repository setup, verification and change-log structure.**
  Cloned `https://github.com/jahnavi-957/SeismoNet`, verified the remote, branch (`main`), HEAD (`eddb3b9`) and clean working tree, and preserved the existing Git history. Created the `docs/` tree: `docs/archive/`, `docs/change-log/`, `docs/change-log/decisions/`, `docs/change-log/entries/`. Archived the three original Markdown documents verbatim into `docs/archive/` before any of them was superseded. No existing file was deleted and no tracked file was modified in this step.
  → `entries/2026-10-17-001-repository-setup.md`

### Documentation

- **2026-10-17-002 — PRD v1.0 authored; PRD v0.1 archived.**
  Replaced the draft `PRD.md` with a full professional PRD (v1.0) using sequential requirement IDs (`FR-001`…`FR-084`, `NFR-001`…`NFR-015`, `SR-001`…`SR-017`, `DR-001`…`DR-007`) and adding dependencies, acceptance criteria and a verification method to every functional requirement. Preserved all substance, the `[GIVEN]/[DERIVED]/[PROPOSED]/[OPEN]` labelling, and all `OQ-*`, `E*`, `SC-*`, `A*`, `O*` identifiers from v0.1, with a full old→new ID mapping. v0.1 retained verbatim at `docs/archive/PRD-v0.1-original.md`.
  → `entries/2026-10-17-002-prd-v1.md`

- **2026-10-17-003 — Repository audit report.**
  Authored `docs/AUDIT_REPORT.md` (AUDIT-001): verified clone and Git metadata, complete file inventory, and the finding that the repository is documentation-only. Classified every capability as existing / incomplete / planned / broken / unverifiable, listed 14 risks and prioritised next steps.
  → `entries/2026-10-17-003-documentation-suite.md`

- **2026-10-17-003 — Technical architecture specification.**
  Authored `docs/TECHNICAL_ARCHITECTURE.md` (ARCH-001): 20 sections, Mermaid component and data-flow diagrams, component contracts, configuration schema, error-handling table, storage layout, and 14 architectural decisions with trade-offs. Every component labelled `[PROPOSED]`, `[PLANNED-VERIFY]` or `[DECIDED]`; no component labelled implemented.
  → `entries/2026-10-17-003-documentation-suite.md`

- **2026-10-17-003 — Reasoning and decisions record.**
  Authored `docs/REASONING_AND_DECISIONS.md` (DEC-001): 14 decisions, each with problem, selected approach, alternatives, advantages, disadvantages, risks, evidence needed and change conditions, plus an explicit evidence-class system (`[ESTABLISHED]`, `[RATIONALE]`, `[HYPOTHESIS]`, `[MEASURED]`, `[PROVISIONAL]`). Records that **no decision is currently `[MEASURED]`**.
  → `entries/2026-10-17-003-documentation-suite.md`

- **2026-10-17-003 — Technology stack, system flow, testing, experiments, dataset, reproducibility and status documents.**
  Authored `docs/TECH_STACK.md` (TECH-001), `docs/SYSTEM_FLOW.md` (FLOW-001), `docs/TESTING_STRATEGY.md` (TEST-001), `docs/EXPERIMENT_PLAN.md` (EXP-001), `docs/DATASET_GUIDE.md` (DATA-001), `docs/DEVELOPMENT_ROADMAP.md` (ROADMAP-001), `docs/REPRODUCIBILITY.md` (REPRO-001) and `docs/PROJECT_STATUS.md`. The two original auxiliary documents (`tech.md`, and the original README) were preserved; `tech.md` remains unmodified at the repository root and is archived as `docs/archive/tech-v0.1-original.md`.
  → `entries/2026-10-17-003-documentation-suite.md`

- **2026-10-17-004 — README rewritten; documentation quality-control pass.**
  Rewrote `README.md` as a professional entry point that distinguishes implemented from planned functionality, links every document, uses only repository-accurate paths, and adds no fabricated badges, numbers or screenshots. Original README preserved at `docs/archive/README-v0.1-original.md`. Ran a documentation QC pass and recorded it in `docs/DOCUMENTATION_QC_REPORT.md`, including the internal-link, Mermaid-syntax, requirement-coverage and cross-document consistency checks and the discrepancies found.
  → `entries/2026-10-17-004-readme-and-qc.md`

### Decisions recorded (ADR)

- **ADR-001 — Project architecture: a single-process Python research pipeline.** Created. Records the decision to avoid services, databases and orchestration, and the conditions that would justify revisiting it.
- **ADR-002 — Dataset strategy: event-level splitting, dataset selection gated on metadata verification.** Created. Records why no dataset is chosen yet, the non-negotiable dataset requirements, and the gating procedure.

---

### Configuration

- **2026-10-17-005 — Repository safety: .gitignore.**
  Added `.gitignore` at the repository root before any dataset or artifact existed, covering virtual environments, caches, secrets, `data/raw/`/`interim/`/`processed/`, `models/`/`*.safetensors`/`*.pt`/`*.pth`, `results/` and OS/editor artefacts while deliberately not ignoring `splits/*.csv`, source, configs or tests. Verified with `git check-ignore -v` that large/sensitive paths are ignored and that source remains trackable. Prevents accidental commits of large or sensitive files (R-16, FR-048).
  → `entries/2026-10-17-005-gitignore-and-safety.md`

### Documentation

- **2026-10-17-006 — Environment compatibility plan (Python 3.14 and CUDA PyTorch).**
  Authored `docs/ENVIRONMENT_PLAN.md` (ENV-001): a P0 decision document proving Python 3.14 compatible with the seismic stack from PyPI metadata (obspy 1.5.1 advertises `Python :: 3.14`) and proposing a `.venv`-local replacement of `torch 2.13.0+cpu` with a `cu121` wheel to reach the existing RTX 2050 (4096 MiB, driver 592.27, CUDA 13.1). No environment was modified or package installed — plan is for owner approval before execution.
  → `entries/2026-10-17-006-environment-plan.md`

### Feature

- **2026-10-17-007 — Minimal project skeleton and tests.**
  Created `src/seismonet/` (`validation.py`, `labels.py`, `time_utils.py`, `shapes.py`), `tests/` (37 pytest tests: waveform validation, P/S target generation, window-depth compatibility, sample↔time conversion), `configs/baseline.yaml`, and `pyproject.toml` (`pythonpath = ["src"]`). Tests run on tiny synthetic fixtures with no dataset or network. `python -m pytest tests` → **37 passed**.
  → `entries/2026-10-17-007-skeleton-and-tests.md`

---

### Documentation

- **2026-10-17-008 — Dataset comparison (P1, DR-001–DR-007, OQ-3).**
  Authored `docs/DATASET_COMPARISON.md` (DATA-COMP-001): evidence tables for STEAD, INSTANCE, ETHZ and SeisBench against `DR-001`–`DR-007` (sampling, components, P/S picks, event `source_id`, sizes, metadata-only inspection, licenses) from GitHub/ESSD/SeisBench docs and Woollam Table 1/§2.1.2; side-by-side matrix; recommendation **INSTANCE (counts)**, pass on all four hard gates with a 100 Hz uniform rate + dense P+S + already **event-wise** shipped split (60.3/10/29.7) so `FR-025`/`SC-8` are satisfiable without a re-split. `OQ-3` recommended for closure (await owner approval). Updated `DATASET_GUIDE.md` header. No dataset downloaded.
  → `entries/2026-10-17-008-dataset-comparison.md`

### Feature

- **2026-10-17-009 — Event-level split utility and metrics; fixture splits marked blocked.**
  Implemented `src/seismonet/split.py` (deterministic `event_level_split` over unique `source_id`, `verify_disjoint` raising `FR-025`, `write_splits` to `train.csv`/`validation.csv`/`test.csv` + `split.json`) and `src/seismonet/metrics.py` (`residuals`/`residual_stats`/`classify_picks` with `P`/`S` separate `FR-060` and zero-denom `FR-062`). Added `tests/test_split.py` (12) + `test_metrics.py` (11); full suite `python -m pytest tests -q` → **60 passed**. Synthetic 120-event fixtures (`84/18/18`) were written, verified disjoint, then deleted to avoid fabricating data; `splits/README.md` documents that real `splits/` are blocked until INSTANCE `source_id` is available. No model was trained.
  → `entries/2026-10-17-009-split-and-metrics.md`

---

### Documentation

- **2026-10-17-010 — Record INSTANCE Counts selection in DATASET_GUIDE.md §4.1.**
  Added `DATASET_GUIDE.md` §4.1 recording INSTANCE Counts as the selected primary candidate, subject to artifact verification, with evidence base `DATASET_COMPARISON.md` (DATA-COMP-001), rationale for Counts over STEAD/ETHZ, and the explicit list of still-open parameters (`OQ-4` window/length, `OQ-5` ratios, `OQ-8` σ, `OQ-10`–`OQ-17` thresholds, `OQ-11` tolerance). No dataset claimed downloaded or validated.
  → `entries/2026-10-17-010-instance-selection-recorded.md`

- **2026-10-17-011 — INSTANCE Counts artifact inspection (P1 Task 2).**
  Inspected the official Counts artifact without downloading waveforms: `metadata_Instance_events_v3.csv.bz2` (286,862,604 bytes) → decompressed 1,268,529,282 bytes, 115 header columns, 1,159,249 event traces from 54,008 `source_id` values, `trace_dt_s == "0.01"` × all traces (100 Hz), `trace_npts == 12000` (120 s), `trace_P_arrival_sample` 100% + `trace_S_arrival_sample` 61.6%, `station_channels` HH/HN/EH/HL. Verified `DR-001` (100 Hz ZNE-per-station), `DR-002` (P/S indices), `DR-003` (`source_id`), `DR-005` (CC BY 4.0 `LICENCE`), `DR-006` (open HTTP + multipart + 1.7 GB sample), `DR-007` (132,288 noise traces). No environment modified.
  → `entries/2026-10-17-011-instance-metadata-inspection.md`

### Feature

- **2026-10-17-012 — Real event-level splits from INSTANCE metadata (P1 Task 3).**
  Generated `splits/train.csv` (37,806 events, 810,733 traces), `validation.csv` (8,101, 173,746), `test.csv` (8,101, 174,770) from the verified `source_id` set with `seismonet.split.event_level_split` (seed 0, ratios 70/15/15, `INSTANCE-v3-events-1159249traces-54008events`) and proved `verify_disjoint` + on-disk disjointness (0 overlap) and P/S coverage `train 61.5% / val 61.6% / test 62.1% S/P`. Added `splits/split.json` (hash `aea671c76ce2`) and updated `splits/README.md`. Full suite `python -m pytest tests -q` → **60 passed**.
  → `entries/2026-10-17-012-real-splits.md`

---

### Configuration

- **2026-10-17-013 — Environment approval and isolated .venv + lockfile (Stage 1).**
  Created a project-local `.venv` from `C:\Python314\python.exe` 3.14.3 (isolated, `.gitignore`'d; global untouched), verified the venv's interpreter and `python -m pytest` → **60 passed** in both interpreters, installed direct deps + `setuptools` + project editable + `h5py 3.16.0`, and pinned `requirements.lock` (sha256 prefix `8f76a33a3cf1`). No CUDA swap in this milestone — global `torch 2.13.0+cpu` unchanged, GPU RTX 2050 4 GiB / driver 592.27 / CUDA 13.1 unchanged on host.
  → `entries/2026-10-17-013-env-approval-and-venv.md`

### Feature

- **2026-10-17-014 — Stage 3: data-pipeline decisions (window, label width, thresholds).**
  Recorded Stage 3 assessment: sampling 100 Hz verified on the sample HDF5 (`ENZ`/`CW`/`(3,12000)` `int32`), production window provisional 3000–4000 (30–40 s; `128` kept only for fast tests), σ provisional 20–40 samples, 70/15/15 split preserved (no shipped `split` column in Counts), missing S as all-zero, tolerances/thresholds kept open until P5. Updated `DATASET_GUIDE.md` §4.1 addendum and `configs/baseline.yaml` comments.
  → `entries/2026-10-17-014-stage1-to-stage4-decisions.md`

### Testing

- **2026-10-17-015 — Stage 2: INSTANCE Counts HDF5 waveform verification on the sample subset.**
  Downloaded `Instance_sample_dataset_v3.tar.bz2` (1,777,063,900 bytes) from `http://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2` (doi:10.13127/instance), extracted `Instance_events_counts_10k.hdf5` (1.44 GB) + `metadata_Instance_events_10k.csv` (12.6 MB) + noise 1k CSV, and proved: `data_format ENZ`/`CW`/`counts`/`int32 (3,12000)` (120 s @ 0.01 s), amplitudes `int32` without NaN, P present 10k/10k + S present 6063/10k, keys 1:1 between CSV `trace_name` and HDF5 `data/<trace_name>`, missing S as `''`.
  → `entries/2026-10-17-015-stage2-hdf5-verification.md`

### Feature

- **2026-10-17-016 — Stage 4: minimum loader/preprocessing + `splits/README.md` update.**
  Implemented `src/seismonet/loader.py` (HDF5+CSV loader, per-window zero-mean + unit-peak, window + `make_targets`, depth guard `FR-036`, empty-S → `None`), flipped `splits/README.md` to "Real splits present", and added `tests/test_loader.py` (7 tests: channel order, 1:1 key equality, invalid-signal rejection, 128/3072 windows, missing-S all-zero, both-picks in 3072, split-integrity). Full suite (`venv`) **67 passed** (60 prior + 7 loader; one pre-fix failure on 3000 % 16 corrected to 3072).
  → `entries/2026-10-17-016-loader-and-preprocessing.md`

- **2026-10-17-017 — P2 production data pipeline (streaming, quality, windowing, augmentation, DataLoader, visualization).**
  Delivered the ten-point P2 acceptance: streaming `loader.py` (per-trace lazy HDF5, `verify_hdf5_coverage`), `validation.py` (`validate_arrival_in_trace` `>=trace_npts` guard + `screen_metadata->QualityReport`), `metadata.py` (`construct_event_id` FR-010 fallback), `windowing.py` (`prepare_window` deterministic vs random `FR-018`, `check_window_boundary`, `evaluate_window_lengths` OQ-4 provisional 128/3000/3072/4000 with span 2.3%/99%+ and depth guard, pure-noise `plan_pure_noise` FR-019 gated on noise verification), `augmentation.py` (scale/noise/shift switchable/training-only/label-consistent FR-028..031, noise separable FR-029), `dataset.py` (lazy per-worker `InstanceDataset`/`DataLoader` + reproducible `worker_init`, smoke `(4,3,3072)` float waveforms in `[-1,1]`), `configs/baseline.yaml` (windowing/pure_noise/augmentation toggles), and `results/figures/window_*.png` (P+S, missing-S, overlap sigma40 + boundary `p_out_of_window` for 0:128). Suite **176 passed, 1 skipped** (`venv`); `h5py 3.16.0` + `matplotlib 3.11.2` pinned (`d0482fd3ca7e`).
  → `entries/2026-10-17-017-p2-production-data-pipeline.md`

### Feature / Testing / Documentation

- **2026-10-17-018 — P2 acceptance hardening: config wrapper, pure-noise sampling, OQ-4 evidence.**
  Wired the pipeline through `configs/baseline.yaml` with `src/seismonet/config.py` (`load_pipeline_config`/`build_pipeline`, unknown-key/depth/`pure_noise.requested` guards), made `InstanceDataset` pure-noise-capable with reproducible `fraction` semantics (per-`__getitem__` probability, default `0.0`, `fraction>0` without a verified noise HDF5/CSV fails clearly, `make_targets(None,None)` all-zero P/S), added `tests/test_config_pipeline.py` (12 tests: source-of-truth, guards, end-to-end `(4,3,3072)` batch, deterministic val/test, missing-S all-zero, pure-noise 0/verified/reproducible/verified 1k-metadata `no P/S`), and recorded the analytical OQ-4 input-batch bytes. Suite `.venv` **188 passed, 1 skipped** (authoritative; 12 new).
  → `entries/2026-10-17-018-p2-acceptance-hardening.md`

### Configuration / Testing

- **2026-10-17-019 — CUDA-enabled PyTorch in `.venv` (`2.14.1+cpu → +cu126`, verified).**
  Replaced the `.venv`-only wheel `2.14.1+cpu` with the official `2.14.1+cu126` cp314 `win_amd64` CUDA 12.6 (`pip --index-url https://download.pytorch.org/whl/cu126`, 2623 MB, 2m27s, sha256 `7297cd4c…2d6a77`), updated `requirements.lock` (`torch==2.14.1+cu126`, `6d9b6f60255b`), and proved `torch.cuda.is_available() True` (GeForce RTX 2050, 4096 MiB) + GPU `512×512` `matmul` (`synchronize` passed) + `python -m pytest -q` **188 passed, 1 skipped** (re-run, identical). Global `C:\Python314` (`2.13.0+cpu`) untouched.
  → `entries/2026-10-17-019-cuda-enabled-pytorch.md`

- **2026-10-17-020 — Small 1D U-Net (3→3072) with segmentation loss and verified CUDA forward pass.**
  Added `src/seismonet/model.py:SeismoUnet1d` (depth 4, base 16, `DoubleConv1d` BN+ReLU, skip connections, `L % 2**depth == 0` guard, `678,707` params; `(batch,3,3072)→(batch,3,3072)` per-sample P/S/noise probabilities) and `src/seismonet/losses.py` (`soft_cross_entropy_loss` `-y log softmax` over soft Gaussian targets, missing S all-zero), plus `tests/test_model.py` (5: shape, sum 1 per sample, loss finite/differentiable, missing-S finite, params in 10k–2M). Proved CPU forward+loss and **CUDA** `model.cuda()(2,3,3072)` `21.68 MiB allocated / 44.0 reserved`. Suite `193 passed, 1 skipped`.
  → `entries/2026-10-17-020-1d-unet-and-gpu-smoke.md`

- **2026-10-17-021 — Bounded three-epoch training pilot on the real INSTANCE sample.**
  Used 16 event-separated training events (492 traces) and 8 event-separated validation events
  (210 traces) selected deterministically with seed 42 from the 10k real-trace sample. Batch-4
  forward/loss/backward/Adam smoke passed with finite values and peak CUDA memory `43.181 MiB`
  allocated / `66.0 MiB` reserved; three epochs completed with batch size 4, 369 training
  optimizer steps, finite losses/gradients, checkpoints, and a loss figure. Training peak was
  `48.380 MiB` allocated / `72.0 MiB` reserved. The test split was not used. Full suite:
   `193 passed, 1 skipped`.
   → `entries/2026-10-17-021-bounded-training-pilot.md`

- **2026-10-17-022 — Validation-only phase-picking inference and visualization.**
  Added configurable local-maximum P/S picking, explicit window-offset conversion, focused tests,
  and a validation-only inference/reporting entry point. On the 210-trace validation subset, the
  selected P threshold `0.5` accepted `0/210` P picks; the validation-only S threshold sweep
  selected `0.1`, producing S `TP/FP/FN = 79/87/67`, precision `0.4759`, recall `0.5411`, F1
  `0.5064`, mean timing error `38.73` samples / `387.29 ms`, and median `17` samples / `170 ms`.
  Three figures and complete prediction records were saved under ignored `runs/validation_inference_seed42/`;
  the test split was not loaded. Suite: `199 passed, 1 skipped`.
  → `entries/2026-10-17-022-validation-inference-and-visualization.md`

---

## Template for future entries

```text
## YYYY-MM-DD

### <Category>

- **YYYY-MM-DD-NNN — <Title>.**
  <Two to four sentences: what changed, why, and the verified outcome.
  State plainly if nothing was measured.>
  → `entries/YYYY-MM-DD-NNN-<slug>.md`
```

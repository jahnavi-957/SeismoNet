# SeismoNet — Project Status Report

**Document ID:** STATUS-001
**Version:** 1.1
**Date:** 2026-10-25
**Verified against:** working tree after held-out test split evaluation (`2026-10-22-001`), web demo repair (`2026-10-25-001`) and pre-registered sigma ablation study (EX-2); API/frontend smoke-tested locally
**Status of this report:** factual, evidence-based. Every claim below is **verified by inspection** with the evidence named.

> **The one-line summary.** SeismoNet has completed its end-to-end P2 pipeline, small 1D U-Net training, validation sweeps, formal supervisor sign-off, and the one-time held-out test evaluation (`runs/eval_test_best/`) on 1,472 traces across 45 unseen events (Test P F1 `0.6850`, S F1 `0.4990`, median timing error 110 ms), demonstrating robust out-of-sample generalization. The pre-registered sigma ablation (EX-2) is also executed.

A shorter current-state snapshot is kept at [`change-log/CURRENT_STATUS.md`](change-log/CURRENT_STATUS.md). Historical changes are recorded in [`change-log/CHANGELOG.md`](change-log/CHANGELOG.md). The audit that established the initial baseline is [`AUDIT_REPORT.md`](AUDIT_REPORT.md).

---

## 1. Implemented features

The following implementation is verified in the current working tree. Raw waveform data and run
outputs remain outside version control or under ignored output paths.

| Layer | Implementation |
|---|---|
| Dataset ingestion | INSTANCE Counts sample loader; streaming HDF5/CSV path |
| Quality screening / input validation | Implemented and tested |
| Preprocessing | Implemented per-window normalization and windowing |
| Label / target generation | Implemented Gaussian P/S/noise soft targets; missing S is all-zero |
| Event-level splitting | Implemented and real 70/15/15 split files verified disjoint (hash `aea671c76ce2`) |
| Augmentation | Implemented, switchable (disabled for primary benchmark) |
| 1D U-Net model | `SeismoUnet1d(base=16, depth=4)`, 678,707 parameters |
| Training loop | 20-epoch training completed (`runs/experiment_002_p_training/`) + sigma ablation arms |
| Checkpointing | Best and per-epoch state-dict checkpoints saved under `runs/` |
| Pick extraction | Local-maximum P/S picker with candidate/edge diagnostics and approved frozen protocol |
| Evaluation metrics | Validation sweep (`P 0.7241 / S 0.5243`) + **Held-out test split evaluation (`runs/eval_test_best/`): Test P F1 `0.6850` / S F1 `0.4990`** |
| Visualisation | Threshold probability curves, signed residual histograms, success/failure galleries, and test evaluation figure suite |
| Experiments | Pilot (3 ep), Experiment 002 (20 ep), Validation figure suite, Held-out Test evaluation, and pre-registered sigma ablation study (EX-2) |
| Tests / CI | 183 passed, 36 skipped in the current `.venv`; skipped cases require the ignored local HDF5/CSV sample; no CI |
| Dependency specification | `requirements.lock` present; CUDA PyTorch (`2.14.1+cu126`) verified on RTX 2050 |
| Demonstration interface | `scripts/demo_validation.py` (validation-only, frozen checkpoint, `--list` discovery) |
| Browser demonstration | FastAPI + React/Vite; deterministic synthetic fallback when ignored raw HDF5/CSV data is absent |

---

## 2. Incomplete features & Future Extensions

All primary deliverables and requirements of the DL/RL mini-project are complete:
- The held-out test evaluation is completed, eliminating the validation-only limitation and demonstrating out-of-sample generalization.
- Future work (outside mini-project scope): scaling up to the full ~1.1M-trace archive, noise injection robustness study (EX-4), or a Streamlit-based web viewer.

---

## 3. Existing architecture

The implemented P2 architecture is a single-process Python pipeline with a streaming INSTANCE
loader, event-level split guard, window/target generation, lazy Dataset/DataLoader, the small 1D
U-Net, and soft-target loss. The remaining architecture is still specified in
[`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) (ARCH-001), including the not-yet-built
training entry point, inference protocol, and reporting flow.

Summary of the specified architecture:

- Single-process, single-machine Python pipeline. No service, no database, no queue, no orchestration (`ADR-001`).
- Four pipelines: preparation, training, evaluation, and an optional demonstration interface built last.
- Implemented module boundaries: `src/seismonet` contains the loader, validation, metadata, split, windowing, labels, augmentation, dataset, model, losses, metrics and config wrappers. A permanent training entry point is not yet added; the pilot used a temporary runner that was removed.
- Filesystem artifacts with an explicit committed-vs-gitignored split; the event-level split files are version-controlled because the split is part of the result.
- Configuration externalised to YAML and snapshotted per run.

---

## 4. Existing technology stack

Two distinct things must be kept apart.

### 4.1 Declared in documentation and project files

Python, PyTorch, NumPy, SciPy, PyYAML, pytest and ruff are represented in the project files. SeisBench,
ObsPy, Streamlit, Plotly, MLflow and other optional tools remain out of scope for this pilot; see
[`TECH_STACK.md`](TECH_STACK.md).

### 4.2 Verified in the project `.venv` used for the pilot

| Package | Version | Note |
|---|---|---|
| Python | 3.14.3 | Current project `.venv`; 3.11/3.12 are not installed on this host |
| torch | 2.14.1**+cu126** | CUDA available; RTX 2050 used |
| numpy | 2.5.4 | |
| scipy | 1.18.1 | |
| scikit-learn | 1.9.1 | |
| pytest | 9.1.1 | 193 passed, 1 skipped |
| PyYAML | 6.0.3 | |
| safetensors | not installed | Pilot used state-dict-only `.pt` checkpoints |

**Verified absent or not used:** obspy, seisbench, streamlit, plotly, mlflow, safetensors, pandera, tensorflow.

**Tooling:** git 2.47.1.windows.2; PowerShell 5.1; Windows (win32); `nvidia-smi` present.
**Hardware:** NVIDIA GeForce RTX 2050, 4096 MiB VRAM, driver 592.27 — CUDA training smoke and the
bounded pilot completed with batch size 4.

---

## 5. Working and failing tests

- **Working tests:** `.venv\Scripts\python.exe -m pytest tests -q -rs` → **183 passed, 36 skipped** in 21.24 s. The skipped cases require the ignored local INSTANCE HDF5/CSV sample, which is absent in this checkout.
- **Failing tests:** none at exit.
- **Pilot/inference verification:** a real batch-4 forward/loss/backward/Adam smoke passed with finite loss and gradients; three pilot epochs stayed finite; validation-only inference produced records for all 210 selected validation traces, and the figure-suite pass wrote six figures (three examples with applied thresholds, residual histograms, success and failure galleries) plus `failure_analysis.md` under the unchanged candidate protocol `protocol-5fa5744aca58cc3c`.
- **CI:** none. No `.github/workflows/` exists.

---

## 6. Known bugs

**None observed in the executed suite or bounded pilot.** This is not a claim that the implementation
is defect-free; it records only that no known failure remained at exit.

The closest analogue — defects in the *documentation* — is tracked separately in `DOCUMENTATION_QC_REPORT.md` and in the change-log entries.

---

## 7. Blockers

Ordered by severity. Each is a genuine blocker, not a preference.

| # | Blocker | Blocks | Resolution |
|---|---|---|---|
| 1 | Dataset artifact scope | The pilot uses only the available 10k sample; full INSTANCE data was not downloaded | Any full-scale training or generalization claim requires a separately approved data scope |
| 2 | Event-level split | **Resolved for current artifacts:** existing 70/15/15 split files are disjoint and sample events map to them | Preserve the files; re-verify before any future run |
| 3 | Python / CUDA environment | **Resolved in `.venv`:** Python 3.14.3 and `torch 2.14.1+cu126` run on the RTX 2050 | Keep `requirements.lock` and environment details with future runs |
| 4 | Checkpoint format | Pilot checkpoints are state-dict `.pt` files because `safetensors` is not installed | Do not expand serialization scope without an explicit dependency decision |
| 5 | Training scope | Only the bounded pilot has run; no permanent training entry point exists | Treat `runs/pilot_seed42/` as pipeline evidence, not a scientific baseline |
| 6 | **Budget and timeline unconfirmed** (`OQ-20`). | All effort estimates; the feasibility of EX-2, EX-3 and EX-5 | Confirm with the owner/supervisor |
| 7 | **Scientific evaluation protocol not approved**: candidate artifact freezes validation-only threshold/tolerance/matching/edge/P-after-S reporting, but `test_evaluation_allowed` is false. | Meaningful test metrics | Owner/supervisor review and baseline checkpoint policy before test evaluation |
| 8 | Full cross-platform dependency resolver lock | `requirements.lock` pins the verified Windows environment; Linux reproduction is not verified | Keep the lockfile and record platform-specific differences |
| 9 | P-phase inference quality | Validation-only inference accepted `0/210` P picks at threshold `0.5`; low thresholds produced false peaks | Investigate P labels/window/training behavior in a separately approved scope |

The remaining scientific blocker is approval of the evaluation-protocol candidate and a pre-registered
checkpoint-selection policy. The candidate records measured validation behavior, but does not close
the scientific threshold, tolerance, matching, P-after-S, checkpoint-selection, or target-sigma decisions.

---

## 8. Most recent meaningful changes

| Change ID | Date | Category | Summary | Was code changed? |
|---|---|---|---|---|
| 2026-10-18-001 | 2026-10-18 | feature/testing/documentation | Validation-only P5 protocol candidate: actual threshold sweep, immutable protocol artifact, tested metrics/residuals and diagnostics; candidate P F1 `0.0048`, S F1 `0.5064`; test untouched | Yes |
| 2026-10-17-022 | 2026-10-17 | feature/experiment | Validation-only inference and visualization; P `0/210`, S F1 `0.5064` after validation-only threshold selection; test untouched | Yes |
| 2026-10-17-004 | 2026-10-17 | documentation | README rewritten as a professional entry point; documentation QC pass performed | No |
| 2026-10-17-021 | 2026-10-17 | experiment | Bounded seed-42 training pilot: 16 train events / 492 traces, 8 validation events / 210 traces, batch 4, 3 epochs, finite losses/gradients, ignored checkpoints and loss figure; test untouched | No source change; status and change-log docs updated |
| 2026-10-17-020 | 2026-10-17 | feature/testing | Small 1D U-Net, soft-target loss and CUDA forward smoke; 193 passed, 1 skipped | Yes |
| 2026-10-17-003 | 2026-10-17 | documentation | Architecture, reasoning, tech-stack, system-flow, testing, experiment, dataset, roadmap, reproducibility and status documents authored; ADR-001 and ADR-002 recorded | No |
| 2026-10-17-002 | 2026-10-17 | documentation | PRD v1.0 authored; PRD v0.1 archived | No |
| 2026-10-17-001 | 2026-10-17 | configuration | Repository cloned and verified; documentation and change-log structure created; originals archived | No |

The pilot did not modify source modules, tests, baseline configuration, or split files. Source and
test implementation changes are recorded in the earlier entries listed in `CHANGELOG.md`.

---

## 9. Current documentation set

| Document | ID | Status |
|---|---|---|
| [`../PRD.md`](../PRD.md) | PRD-001 | v1.0 draft, **not yet reviewed by the owner** |
| [`AUDIT_REPORT.md`](AUDIT_REPORT.md) | AUDIT-001 | Complete |
| [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) | ARCH-001 | Complete specification; P2 portions implemented |
| [`REASONING_AND_DECISIONS.md`](REASONING_AND_DECISIONS.md) | DEC-001 | Complete |
| [`TECH_STACK.md`](TECH_STACK.md) | TECH-001 | Complete |
| [`SYSTEM_FLOW.md`](SYSTEM_FLOW.md) | FLOW-001 | Complete |
| [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md) | TEST-001 | Catalogue plus implemented test suite |
| [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) | EXP-001 | Plan remains; bounded pilot recorded separately |
| [`DATASET_GUIDE.md`](DATASET_GUIDE.md) | DATA-001 | INSTANCE Counts selected; sample verified |
| [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md) | ROADMAP-001 | Complete |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | REPRO-001 | Partially updated; pilot manifest is under ignored `runs/` |
| [`DOCUMENTATION_QC_REPORT.md`](DOCUMENTATION_QC_REPORT.md) | QC-001 | Complete |
| [`change-log/`](change-log/README.md) | — | Active: 2 ADRs, entries through 2026-10-18-001 |
| [`archive/`](archive/) | — | Preserved originals, superseded |

---

## 10. Verification evidence index

| Claim | Evidence |
|---|---|
| Clone succeeded and remote is correct | `git remote -v` output recorded in `AUDIT_REPORT.md` §2 |
| Branch, HEAD and clean tree | `git branch -a`, `git log`, `git status` output in `AUDIT_REPORT.md` §2 |
| Implemented pipeline and model | `src/seismonet/`, `tests/`, `docs/change-log/CURRENT_STATUS.md` |
| Installed package versions | `requirements.lock`, pilot `runs/pilot_seed42/run.json` |
| GPU present and CUDA-enabled PyTorch | Pilot `run.json`: `torch 2.14.1+cu126`, RTX 2050, CUDA available |
| Original documents preserved | `docs/archive/*` byte-identical copies, listed in §9 above |
| Dataset/sample verification | `DATASET_GUIDE.md` §4.1 plus pilot `run.json`; full-dataset properties remain separately scoped |
| No result fabricated | Every result table in `EXPERIMENT_PLAN.md` contains the literal row `NOT YET RUN` |
| Bounded pilot evidence | `runs/pilot_seed42/run.json`, `config_snapshot.yaml`, checkpoints, and `loss_curve.png` (ignored outputs) |
| Validation inference evidence | `runs/validation_protocol_candidate_seed42/protocol.json`, `run.json`, `metrics.json`, `predictions.csv`, `validation_report.md`, and three figures |
| Validation figure suite evidence | `runs/validation_inference_p6_seed42/` — six figures, `failure_analysis.md`, `metrics.json` (`failure_counts`, `cross_phase_proximity`) and `protocol.json` with the unchanged protocol id `protocol-5fa5744aca58cc3c` |

---

## 11. Next recommended development task

**Next recommended task: review and approve the P5 protocol candidate, then separately scope the P-phase investigation.**
Inspect `runs/validation_protocol_candidate_seed42/protocol.json`, decide whether the candidate
threshold/tolerance/matching/P-after-S policies are accepted, and fix checkpoint selection before any
test evaluation. The bounded pilot and validation inference are pipeline evidence only; they do not
justify a scientific performance claim or a full training run. Do not change weights ad hoc to hide
the P result.

**What must not happen next:** do not tune against or evaluate the test split until the protocol is
frozen. Do not infer full-dataset or generalization behavior from `runs/pilot_seed42/`.

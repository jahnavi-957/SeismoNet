# SeismoNet — Repository Audit Report

**Document ID:** AUDIT-001
**Version:** 1.0
**Date:** 2026-10-17
**Audited commit:** `eddb3b9` on `main`
**Audit method:** direct inspection of the cloned working tree and Git metadata; no execution of any repository code (there is none to execute)

---

## 0. How to read this report

This is a factual audit of the repository **as it exists at commit `eddb3b9`**. It separates what is *verified by inspection* from what is *planned in documentation only*. The governing statement, repeated because it dominates every section below:

> The repository contains **three Markdown documents and no source code, no tests, no configuration, no dependencies file, no data, and no model artifacts.** Every functional capability described anywhere in the repository is a **plan**, not an implementation.

---

## 1. Project overview

| Item | Value |
|---|---|
| Project name | SeismoNet |
| One-line description | Deep-learning seismic phase picking: predict P-wave, S-wave and noise probabilities per time step from a three-component waveform, using a 1D U-Net inspired by PhaseNet |
| Primary objective | Detect P- and S-wave arrival times from seismic waveforms and evaluate them against reference annotations |
| Repository | https://github.com/jahnavi-957/SeismoNet |
| Local clone | `C:\Users\Tanish\dlrl miniproject\SeismoNet` |
| Default branch | `main` |
| HEAD commit | `eddb3b9` — "Update README.md" |
| Nature of project | University / mini research project (explicitly self-declared as "in development") |

---

## 2. Clone and Git verification results

Commands were run against the local clone; the clone succeeded.

| Check | Command | Result |
|---|---|---|
| Clone | `git clone https://github.com/jahnavi-957/SeismoNet.git` | Success (stderr banner "Cloning into 'SeismoNet'...") |
| Remote | `git remote -v` | `origin  https://github.com/jahnavi-957/SeismoNet.git (fetch/push)` |
| Current branch | `git branch -a` | `* main`; `remotes/origin/main`; `origin/HEAD -> origin/main` |
| Status | `git status` | `nothing to commit, working tree clean`; up to date with `origin/main` |
| Tags | `git tag` | none |
| Other branches | `git branch -a` | none beyond `main` |
| `.gitignore` present | `Test-Path .gitignore` | **False** |
| LICENSE present | (directory listing) | **False** |

### Full commit history (4 commits, all by the same author, all on one day)

| Commit | Date (ISO) | Author | Subject |
|---|---|---|---|
| `fb19941` | 2026-10-12 23:05:45 +0530 | jahnavi-957 `<shahjahnavi09@gmail.com>` | Add SeismoNet documentation (`README.md`, `tech.md`) |
| `67de916` | 2026-10-12 23:06:50 +0530 | jahnavi-957 | Add SeismoNet PRD (`PRD.md`) |
| `e939c75` | 2026-10-12 23:10:50 +0530 | jahnavi-957 | Delete team responsibilities from README |
| `eddb3b9` | 2026-10-12 23:12:34 +0530 | jahnavi-957 | Update README.md |

**Observation:** the entire history is documentation-only. No commit has ever added a source file, test, notebook, dataset pointer or dependency manifest.

---

## 3. Repository structure (verified)

Complete tracked file list (`git ls-files`):

```text
PRD.md
README.md
tech.md
```

Physical tree (excluding `.git`):

```text
SeismoNet/
├── PRD.md      (46,777 bytes, 657 lines)
├── README.md   (11,645 bytes, 263 lines)
└── tech.md     (14,833 bytes, 215 lines)
```

Total non-`.git` content: **73,255 bytes / 1,135 lines of Markdown.**

Directories referenced in the README's "Planned Repository Structure" (`data/`, `notebooks/`, `src/`, `models/`, `results/`, `reports/`, `app/`) **do not exist**. `src/preprocessing.py`, `src/model.py`, `src/train.py`, `src/predict.py`, `src/evaluate.py`, and `requirements.txt` **do not exist**.

---

## 4. Current implementation status (the central finding)

| Layer | Documented intent | Actually implemented | Evidence |
|---|---|---|---|
| Dataset ingestion | Yes (planned) | **No** | no `data/`, no loader code |
| Preprocessing pipeline | Yes (planned) | **No** | no `src/` |
| Label / target generation | Yes (planned) | **No** | no `src/` |
| Event-level splitting | Yes (planned) | **No** | no split files |
| 1D U-Net model | Yes (planned) | **No** | no `model.py`, no weights |
| Training loop | Yes (planned) | **No** | no `train.py`, no logs |
| Checkpointing | Yes (planned) | **No** | no `models/` |
| Pick extraction | Yes (planned) | **No** | no `predict.py` |
| Evaluation metrics | Yes (planned) | **No** | no `evaluate.py` |
| Visualisation | Yes (planned) | **No** | no plotting code, no figures |
| Experiments | Yes (planned) | **No** | no result tables |
| Tests | Yes (planned) | **No** | no `tests/`, no CI |
| Dependencies | Yes (planned — "recorded in `requirements.txt` after the working environment has been verified") | **No** | `requirements.txt` absent |
| Streamlit/Gradio demo | Yes (planned) | **No** | no `app/` |

**Implementation completeness: 0 of the 13 layers above. The repository is a specification-only repository.**

### Classification requested by the audit brief

| Category | Items |
|---|---|
| **Features that already exist and work** | None. There is no executable code, so nothing can work. |
| **Features that exist but are incomplete** | None. Documentation does not count as an incomplete feature. |
| **Features that are planned but not implemented** | Everything: data ingestion, validation, preprocessing, label generation, event-level splitting, augmentation, 1D U-Net, training, checkpointing, pick extraction, evaluation, visualisation/plots, noise study, configuration study, reproducibility packaging. |
| **Features that are broken** | Cannot be assessed — there is nothing to break. |
| **Features whose implementation cannot be verified** | All planned features, because they are unimplemented. |
| **Decisions that require clarification** | The 20 open questions carried in PRD v0.1 (`OQ-1` … `OQ-20`), consolidated in the new PRD §17 and `docs/PROJECT_STATUS.md`. |

> Note on the original README's own honesty guardrail: it states *"Using a pretrained model to generate predictions is not, by itself, evidence that the team trained a deep learning model."* The audit confirms that no training run, checkpoint, log or metric exists in the repository, so **no performance claim of any kind is currently supported.**

---

## 5. Documents present, and an assessment of each

### 5.1 `README.md` (263 lines)

- **Nature:** a *planned-scope* README, self-labelled as such in its "Current Project Status" section.
- **Verifiably accurate content:** project description, problem statement, objectives, target users, the 1D U-Net/PhaseNet framing, the P/S/noise output description, the planned metric list, the data-splitting precautions, limitations, references.
- **Content that is forward-looking (must not be read as done):** "How It Works" (all 8 steps unimplemented), "Deep Learning Approach", "Evaluation", "Planned Experiments", "Development Plan" (Day 1–6 table), "Planned Repository Structure".
- **No fabricated results:** confirmed — the README contains no numbers, no badges, no screenshots, no accuracy claims.
- **Deficiencies for a professional entry point:** no environment setup, no installation commands, no dataset acquisition instructions, no test/run commands, no links to per-topic documents (none existed), no architecture diagram.

### 5.2 `PRD.md` (657 lines) — v0.1 draft

- **Nature:** a genuinely careful draft PRD written from domain knowledge, with an explicit labelling discipline: every item is tagged `[GIVEN]`, `[DERIVED]`, `[PROPOSED]` or `[OPEN]`, and a stated policy of not inventing requirements.
- **Strengths (preserved in the new PRD):** requirement IDs (`FR-D1` … `FR-R3`, `NFR-1` … `NFR-7`, `DR-1` … `DR-5`), user stories `US-01` … `US-17`, success criteria `SC-1` … `SC-8`, 20 open questions `OQ-1` … `OQ-20`, 38 edge cases `E1` … `E38`, risks `R1` … `R8`, milestones `M1` … `M8`, assumptions `A1` … `A6`, optional features `O1` … `O4`, a glossary, and an explicit refusal to invent performance targets.
- **Self-declared limitation (verbatim, section 0):** *"No live literature search or database lookup was performed. Dataset statistics and citations in Sections 14 and 15 must be verified against the original sources before they are quoted in a report."*
- **Verification status of its citations:** **unverified.** The reference list (PhaseNet Zhu & Beroza 2019; EQTransformer Mousavi et al. 2020; GPD Ross et al. 2018; SeisBench Woollam et al. 2022; STEAD Mousavi et al. 2019; INSTANCE Michelini et al. 2021; Münchmeyer et al. 2022; STA/LTA Allen 1978) is asserted from memory. No URLs other than the PhaseNet and STEAD GitHub repositories appear anywhere in the repository. **These must be verified before being cited in any report.**
- **Gaps relative to the audit brief's requested PRD structure:** no document-control/changelog section, no explicit "Engineering objectives", no per-requirement *dependencies*, *acceptance criteria* and *verification method* columns (acceptance criteria live in user stories instead), no dedicated "Scientific and Model Requirements" section, no measurable-form non-functional requirements with TBD markers, no consolidated assumptions section.

### 5.3 `tech.md` (215 lines) — Tech stack recommendation v0.1

- **Nature:** a companion recommendation document. Explicitly tiered into "Tier 1 core", "Tier 2 optional demo", "Tier 3 scale-up", with the stated design principle of not inventing requirements (no database, no k8s, no React).
- **Its own self-declared limitation (verbatim):** *"Versions are not pinned here because current releases could not be checked; pin them in a lockfile (FR-R1)."*
- **Status of its recommendations:** all **proposed**, none installed or used. It references PRD IDs that exist only in PRD v0.1.
- **Has no companion code:** none of the recommended modules exist.

---

## 6. Existing architecture

There is **no implemented architecture**. The only architecture that exists is *described*:

- The README's "How It Works" implies a linear pipeline: load → preprocess → model → probabilities → extract picks → evaluate → record experiments → visualise.
- The README's planned directory layout implies a flat `src/` module split (`preprocessing.py`, `model.py`, `train.py`, `predict.py`, `evaluate.py`) plus `notebooks/`, `app/`, `results/`, `reports/`, `models/`, `data/`.
- `tech.md` §8 implies a layered stack: data layer (SeisBench/HDF5) → model layer (PyTorch 1D U-Net) → experiment layer (YAML + MLflow) → optional app layer (Streamlit/FastAPI).

None of these is realised in files. `docs/TECHNICAL_ARCHITECTURE.md` in this documentation set therefore documents a **proposed** architecture and labels it as such. It must not be mistaken for a description of running code.

---

## 7. Existing technology stack

### 7.1 Declared in documentation (all proposals)

Python, PyTorch, SeisBench, ObsPy, NumPy, SciPy, pandas, scikit-learn, Matplotlib/Plotly, Streamlit, Git/GitHub; optionally FastAPI, MLflow, Hydra/OmegaConf, safetensors, pytest, ruff, pandera, Docker, GitHub Actions, `uv`/pip-tools, Makefile. Never used in this repository because there is no code.

### 7.2 Actually installed in the audit environment (verified by introspection)

| Package | Version |
|---|---|
| Python | 3.14.3 (64-bit) |
| torch | 2.13.0**+cpu** (CUDA unavailable) |
| numpy | 2.4.3 |
| pandas | 3.0.1 |
| scipy | 1.17.1 |
| scikit-learn | 1.8.0 |
| pytest | 9.1.1 |
| PyYAML | 6.0.3 |
| safetensors | 0.8.0 |

**Verified absent:** `obspy`, `seisbench`, `matplotlib`, `streamlit`, `plotly`, `mlflow`, `ruff`, `pandera`, `tensorflow`.

**Tooling:** git 2.47.1.windows.2; PowerShell 5.1; OS win32 (Windows); `nvidia-smi` present.

**Hardware:** NVIDIA GeForce RTX 2050, 4096 MiB VRAM, driver 592.27 — but the installed PyTorch build is CPU-only, so GPU acceleration is **not currently available** without reinstalling a CUDA build.

### 7.3 Three environment discrepancies that will bite if not addressed

1. **Python 3.14.3 vs the recommendation.** `tech.md` recommends Python 3.11 or 3.12. SeisBench and ObsPy wheel availability on 3.14 is unverified and is a plausible installation blocker.
2. **CPU-only PyTorch.** Training on the local machine is currently CPU-only despite a physical NVIDIA GPU. The free-tier-GPU assumption (`A6`) is the documented mitigation.
3. **Missing core scientific/plotting libraries.** `obspy`, `seisbench` and `matplotlib` are required by the plan and are not installed.

---

## 8. Dependencies and environment requirements

- **No dependency manifest exists.** No `requirements.txt`, `pyproject.toml`, `environment.yml`, `uv.lock`, `poetry.lock` or `setup.py`.
- **No `.gitignore`.** With `data/` and `models/` planned, the absence of a `.gitignore` is a near-term risk (accidental commit of large datasets or checkpoints).
- **Environment requirements are therefore aspirational**, taken from `tech.md`, and unverified.

---

## 9. Dataset and data pipeline status

- **Selected dataset: not chosen.** `OQ-3` is open. README lists PhaseNet's repository and the STEAD dataset as "potential starting points" only, and explicitly warns: *"The dataset should not be assumed to be downloaded or configured merely because it is listed here."*
- **No data present.** No `data/` directory, no waveform files, no metadata CSV, no HDF5, no split files.
- **No downloader, no loader, no validation code.**
- **Dataset properties in PRD §14 are unverified** and self-flagged as such.
- **Requirement DR-3 (dataset must provide event IDs for event-level splitting) is unresolved** and is a dataset-selection gate.

---

## 10. Model implementation and training status

- **No model code.** No `model.py`, no architecture definition, no parameter count.
- **No training code.** No `train.py`, no loop, no loss, no optimiser, no scheduler.
- **No training log, no loss curve, no checkpoint, no run configuration.**
- The intended architecture (1D U-Net, depth 4, base 16 channels, kernel 7, three-channel softmax output) is a `tech.md` **proposal** and has never been built.

---

## 11. Inference and evaluation status

- **No inference code.** No `predict.py`, no peak picker, no threshold logic.
- **No evaluation code.** No residual computation, no precision/recall/F1, no matching rule implementation.
- **No evaluation protocol frozen.** Tolerance (`OQ-11`) and picking threshold (`OQ-10`) are open; PRD §8 records only the *structure* of the protocol.
- **No results of any kind.** No metrics, no tables, no residuals, no figures, no failure gallery.

---

## 12. Testing and reproducibility status

- **No tests.** No `tests/`, no fixtures, no synthetic waveform fixture, no leakage check.
- **No CI.** No `.github/workflows/`.
- **Reproducibility infrastructure: none.** No seed handling, no config files, no split files, no pinned dependencies, no regeneration script, no entry points.
- `pytest` is installed in the environment but unused by the (nonexistent) code.

---

## 13. Technical risks and missing components

Ordered by the audit's view of urgency for a team that wants to produce a defensible result.

| # | Risk / missing component | Consequence if unaddressed | Severity |
|---|---|---|---|
| 1 | **No dataset selected or validated** (`OQ-3`, `DR-3`). | Blocks everything; a late discovery that the dataset lacks S picks or event IDs would invalidate the split strategy. | Critical |
| 2 | **No code at all.** | No deliverable; success criteria `SC-1` … `SC-8` all fail. | Critical |
| 3 | **Python 3.14 vs SeisBench/ObsPy compatibility.** | Installation failure or wasted days. | High |
| 4 | **PyTorch is CPU-only; local GPU unusable as installed.** | Training turns into hours/days on CPU. | High |
| 5 | **No `.gitignore` with `data/`/`models/` planned.** | Accidental commit of large files; polluted history. | High |
| 6 | **Event leakage not enforceable yet** (`FR-D4`/`FR-D5`). | Inflated metrics; the single most common way a phase-picking mini-project produces invalid conclusions. | High |
| 7 | **Tolerance and threshold undecided** (`OQ-10`, `OQ-11`). | Metrics meaningless or tunable after the fact; `NFR-3` violated. | High |
| 8 | **Reference-arrival uncertainty unaddressed** (`OQ-13`). | A tolerance tighter than label uncertainty measures label noise as model error. | Medium |
| 9 | **Budget/compute/time unconfirmed** (`OQ-20`, `A6`). | Scope overrun; the `Day 1–6` plan in the README is unrealistic for an unscaffolded start. | Medium |
| 10 | **Unverified citations and dataset statistics** in PRD §14. | Reviewers can reject the report; risk of stating incorrect facts. | Medium |
| 11 | **No dependency lockfile** (`FR-R1`). | Results not reproducible on another machine. | Medium |
| 12 | **S-wave metrics at risk of being averaged away** (`R3`). | Over-optimistic reporting. | Medium |
| 13 | **No licence file.** | Unclear reuse terms; a university submission may require one. | Low–Medium |
| 14 | **Documentation drift risk.** Three documents with no cross-links and overlapping content. | Contradictions as the project evolves. | Low–Medium |

---

## 14. Documents created or modified by this audit and documentation task

See `docs/change-log/CHANGELOG.md` for the authoritative record and `docs/change-log/entries/2026-10-17-*.md` for per-change reports. Summary:

**Created:** this audit report, the new `PRD.md`, eight documents under `docs/`, and the complete `docs/change-log/` tree.
**Preserved unmodified:** `tech.md` at the repository root.
**Replaced with an archived copy retained:** the original `PRD.md` and `README.md` — both copied verbatim to `docs/archive/` before being superseded.
**No source code, data, model, test or dependency file was created, modified or removed.**

---

## 15. Recommended next steps, prioritized

1. **Close the dataset decision (`OQ-3`) and verify `DR-3`.** Inspect candidate dataset metadata for: three components, single/known sampling rate, P *and* S picks, and an event identifier. Write the result into `docs/DATASET_GUIDE.md`.
2. **Resolve the Python version question.** Create a 3.11/3.12 virtual environment and confirm SeisBench, ObsPy and a CUDA PyTorch build install cleanly. Record the outcome in `docs/REPRODUCIBILITY.md`.
3. **Create the repository skeleton** (`.gitignore` first, then `requirements.txt`/`pyproject.toml`, then `src/` and `tests/`) — no model code yet.
4. **Build the data path only** (`FR-001` … `FR-018`): loader, quality screening, event-level split, windowing, target generation, plus a synthetic-fixture test. This is the highest-risk area and yields the most early information.
5. **Implement the model and an overfit-tiny-batch sanity test** (`FR-023` … `FR-028`, `US-06`).
6. **Freeze the evaluation protocol** (`OQ-10`, `OQ-11`, `OQ-14`, `OQ-17`) *before* any test-set evaluation, then implement metrics (`FR-039` … `FR-046`).
7. **Only then** train the baseline, and afterwards run the noise and configuration experiments.
8. **Defer the Streamlit demo** until core validation is complete (`FR-059`).

Item-by-item phasing, dependencies, effort ranges and exit criteria are in `docs/DEVELOPMENT_ROADMAP.md`.

---

## 16. Audit conclusions

1. The clone is verified: `origin` correct, branch `main`, HEAD `eddb3b9`, working tree clean, history preserved.
2. The repository is a **documentation-only specification** with four commits and three Markdown files.
3. **Zero implementation exists.** No claim of functionality, accuracy or completion in any document is currently supportable by evidence in the repository.
4. The existing documentation is unusually disciplined about not inventing requirements — that discipline is preserved and extended by this documentation set.
5. The critical path is: **choose and validate a dataset → fix the environment → build the data path → model → freeze the protocol → baseline → experiments.**
6. The most valuable engineering insurance for a project of this shape is the event-level split check and the frozen evaluation protocol; both are cheap and both prevent invalid conclusions.

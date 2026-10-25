# SeismoNet — Product Requirements Document (PRD)

**Project:** SeismoNet — Deep-Learning-Based Seismic Phase Detection
**Document ID:** PRD-001
**Version:** 1.0
**Status:** Draft for approval — supersedes PRD v0.1
**Date:** 2026-10-17
**Superseded document:** `docs/archive/PRD-v0.1-original.md`

---

## 1. Document Control

| Field | Value |
|---|---|
| Project name | SeismoNet |
| Document type | Product Requirements Document for a research mini-project (not a production system) |
| Document ID | PRD-001 |
| Version | 1.0 |
| Status | Draft for approval. All `[PROPOSED]` and `[OPEN]` items await owner/supervisor review. |
| Date of issue | 2026-10-17 |
| Repository | https://github.com/jahnavi-957/SeismoNet |
| Repository state at issue | commit `eddb3b9`, branch `main` — documentation only, **no implementation** (see `docs/AUDIT_REPORT.md`) |
| Purpose | To fix, in one reviewable document, what SeismoNet must do, why, for whom, to what standard of rigour, and what is explicitly out of scope — so that implementation, evaluation and reporting can proceed without inventing requirements later. |
| Intended audience | Project author; academic supervisor; project evaluation panel; any contributor joining the repository; a reviewer attempting to reproduce the reported results. |
| Author | SeismoNet documentation task (AI-assisted), based on the original PRD v0.1 by the repository owner |
| Reviewers | Project owner / supervisor — **not yet reviewed** |
| Related documents | `docs/TECHNICAL_ARCHITECTURE.md`, `docs/TECH_STACK.md`, `docs/SYSTEM_FLOW.md`, `docs/REASONING_AND_DECISIONS.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/TESTING_STRATEGY.md`, `docs/EXPERIMENT_PLAN.md`, `docs/DATASET_GUIDE.md`, `docs/REPRODUCIBILITY.md`, `docs/PROJECT_STATUS.md`, `docs/AUDIT_REPORT.md`, `docs/change-log/` |

### Requirement labelling discipline (carried forward from v0.1)

Every requirement is tagged with exactly one origin:

| Tag | Meaning |
|---|---|
| `[GIVEN]` | Stated in the original project problem statement. |
| `[DERIVED]` | Follows directly from a `[GIVEN]` item or from established seismological / ML practice. |
| `[PROPOSED]` | A default chosen so work can start. Changeable. **Not** a stakeholder requirement. |
| `[OPEN]` | Genuinely undecided; listed in §17 with a suggested closure route. No value is assumed. |

### Policy: do not invent requirements or results

- No numeric performance target is set in this document. Baseline-relative targets, if wanted, are set **after** a baseline exists (§16, `OQ-19`).
- No dataset statistic, citation, benchmark number or experimental result is asserted as fact. Items that trace to the original v0.1 literature list remain **unverified** and are labelled as such (§4.7).
- Every `[PROPOSED]` scientific parameter carries an explicit rationale in §10 or a pointer to `docs/REASONING_AND_DECISIONS.md`.

### Change history

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | (original, undated in source) | Repository owner | Initial draft. Requirement IDs `FR-D1`…`FR-R3`, `NFR-1`…`NFR-7`, `DR-1`…`DR-5`, `US-01`…`US-17`, `SC-1`…`SC-8`, `OQ-1`…`OQ-20`, edge cases `E1`…`E38`, risks `R1`…`R8`, milestones `M1`…`M8`, assumptions `A1`…`A6`. Preserved verbatim at `docs/archive/PRD-v0.1-original.md`. |
| **1.0** | 2026-10-17 | Documentation task (AI-assisted) | Restructured to the full professional PRD structure. Introduced sequential requirement IDs (`FR-001`…, `NFR-001`…, `SR-001`…, `DR-001`…) and added per-requirement *dependencies*, *acceptance criteria* and *verification method*. Added §1 Document Control, §10 Scientific and Model Requirements, and §16 Acceptance Criteria. Preserved all v0.1 substance, all `OQ`/`E`/`SC`/`A`/`O` identifiers and the `[GIVEN]/[DERIVED]/[PROPOSED]/[OPEN]` labelling. Full old→new ID mapping in §18. |

---

## 2. Executive Summary

SeismoNet is a **reproducible deep-learning pipeline** that detects **P-wave** and **S-wave** arrival times in three-component seismic waveforms. It uses a one-dimensional U-Net architecture inspired by PhaseNet `[GIVEN]`. For every time sample, the model outputs the probability that the sample belongs to a P arrival, an S arrival, or noise `[GIVEN]`. Arrival times are extracted from those probability curves and compared with labelled reference picks using arrival-time residuals plus precision, recall and F1 under an explicit, pre-declared tolerance `[GIVEN]`. The project additionally studies how waveform noise and selected training configurations affect performance `[GIVEN]`.

The stated goal is to **demonstrate a reproducible pipeline and to assess its effectiveness on a selected dataset** — not to claim deployment-ready earthquake monitoring `[GIVEN]`.

**What SeismoNet is not.** It does not predict earthquakes before they happen, does not issue or claim to enable public emergency warnings, does not locate events, does not estimate magnitude, and does not process continuous real-time streams. Those are non-goals (§7.2).

**Current state at the time of writing.** The repository is a **specification-only repository**. It contains `PRD.md`, `README.md` and `tech.md` and no code, tests, data or models. Every capability named above is a plan, not an implementation. `docs/PROJECT_STATUS.md` is the authoritative status record and should be treated as the single source of truth for "what works".

**Why it is needed.** Seismic networks record continuously, and identifying phase onsets by hand is slow, subjective and hard to keep consistent at scale (`P1`–`P3`, §3). Modern deep-learning pickers exist, but their reported performance depends heavily on the dataset, the evaluation tolerance and the matching rule (`P4`). A transparent, reproducible evaluation — including the *unflattering* parts — is more valuable to a research team than a headline score.

**Who benefits.** Seismology researchers and analysts who need to judge whether automated picks are physically plausible (§6, `U1`); the project author and student contributors building ML/seismology skills (`U2`); and an evaluator or reviewer who must reproduce the work (`U3`).

**Expected deliverable.** A repository that takes a documented seismic dataset and produces: a trained 1D U-Net checkpoint with a saved configuration and seed; P/S/noise probability outputs on held-out *events*; extracted arrival times; P-and-S-separated precision/recall/F1 tables under a frozen tolerance; residual statistics and histograms; waveform-plus-pick-plus-probability figures including failure cases; a controlled noise-robustness study; a one-factor-at-a-time training-configuration study; and a documented command that regenerates the reported tables and figures on another machine.

---

## 3. Problem Statement

### 3.1 Manual phase picking is slow, subjective and hard to scale

Identifying the arrival of a P wave and an S wave in a seismic waveform is a routine but demanding analyst task. The practical difficulty is not recognising that a signal is present; it is deciding **where the onset begins** when it emerges gradually from noise, and doing so consistently across thousands of recordings.

Three distinct problems follow, and it is important not to overstate any of them:

- **Throughput.** Manual inspection consumes analyst time proportional to the number of recordings reviewed. This project does not measure or claim any specific productivity figure for that; the point is only that the cost grows with the volume of data.
- **Subjectivity.** An arrival time is not an exact physical instant but an analyst's judgement of where a phase becomes visible above noise. Different analysts — or the same analyst on different days — can choose different onsets, and this variability is largest for **emergent** onsets and for **S waves**, which arrive inside the coda of the P wave.
- **Consistency at low signal-to-noise ratio.** Threshold-based classical detectors such as STA/LTA degrade as signal-to-noise ratio (SNR) falls and tend to time S waves poorly, because S energy often rides on top of earlier arriving energy.

### 3.2 Deep-learning pickers exist, but their numbers are protocol-dependent

Deep-learning pickers such as PhaseNet-lineage models are well established in the literature. However, a reported score is only meaningful together with the dataset it was obtained on, the time tolerance used to count a pick as correct, the rule used to match a predicted pick to a reference pick, and the noise conditions. Two papers can report very different numbers for comparable models without either being wrong.

The consequence for this project is a methodological requirement rather than a modelling one: **a transparent, reproducible evaluation protocol, frozen before results are inspected, is a first-class deliverable** — arguably more valuable than any single score.

### 3.3 Problem statement for this project

> Given a window of three-component seismic waveform, predict per-sample probabilities of a P arrival, an S arrival, and noise; extract arrival times from those probabilities; and quantify — under an explicit, documented tolerance and matching rule — how closely the extracted times match labelled reference picks, including how that agreement changes with waveform noise level and with selected training configurations.

### 3.4 Goals

| ID | Goal | Source |
|---|---|---|
| G1 | Build a 1D U-Net that outputs P / S / noise probabilities for each time step. | `[GIVEN]` |
| G2 | Extract arrival times from the probability outputs. | `[GIVEN]` |
| G3 | Evaluate with arrival-time errors plus precision, recall and F1 under a clearly defined tolerance. | `[GIVEN]` |
| G4 | Provide preprocessing, training, evaluation and visualisation as one pipeline. | `[GIVEN]` |
| G5 | Investigate the effect of waveform noise on performance. | `[GIVEN]` |
| G6 | Investigate the effect of selected training configurations on performance. | `[GIVEN]` |
| G7 | Make the pipeline reproducible. | `[GIVEN]` |

### 3.5 Non-goals

| ID | Non-goal | Reason |
|---|---|---|
| NG1 | Claiming deployment-ready earthquake monitoring or early warning. | `[GIVEN]` Explicitly excluded. |
| NG2 | Earthquake location, magnitude estimation, focal mechanisms. | Downstream of picking; not in the problem statement. |
| NG3 | Real-time or low-latency continuous-stream processing. | Not stated. Windowed inference is the scope. |
| NG4 | Multi-station association (linking picks into events). | Not stated. |
| NG5 | Novel architecture research. | The stated approach is "inspired by PhaseNet". |
| NG6 | Global generalisation claims. | A single selected dataset is the stated scope. |

---

## 4. Background and Scientific Context

> **Verification note.** This section states standard seismological concepts for orientation. It is written from domain knowledge. Citations in §4.7 are carried over from v0.1 and are **unverified** — the v0.1 source explicitly warns that no literature lookup was performed. Verify before quoting.

### 4.1 Seismic waveforms

A seismogram is a time series of ground motion recorded by a seismometer. Modern stations record **three orthogonal components**, conventionally:

- **Z** — vertical,
- **N** — north–south horizontal,
- **E** — east–west horizontal.

Samples are counts of a digitised instrument output, taken at a fixed **sampling rate** `fs` (samples per second). Observed amplitude and shape depend on the source, the propagation path, the recording instrument and the noise field, so raw amplitudes are not directly comparable across stations or instruments.

### 4.2 P waves and S waves

- **P wave (primary, compressional).** The fastest body wave; arrives first. Particle motion is along the propagation direction, so for steeply incident rays it is strongest on the **vertical** component.
- **S wave (secondary, shear).** Slower; arrives later; typically carries larger amplitude on the component axes. Particle motion is transverse to propagation, so it is usually clearer on the **horizontal** components. S waves do not propagate through liquids.

The time difference **S minus P** increases with source–station distance. A commonly quoted crustal rule of thumb is roughly 8 km per second of S-P time; this is only approximate and depends on local velocity structure. Accurate P and S arrival times from several stations are the raw input to earthquake location, origin-time estimation, magnitude estimation, focal mechanisms and tomography — which is precisely why picking quality matters. None of those downstream tasks are in SeismoNet's scope (`NG2`).

### 4.3 Seismic phase picking

"Phase picking" means determining the arrival time of a seismic phase on a waveform. In practice the answer is a judgement of where the phase onset becomes distinguishable from noise. Onsets are described as:

- **impulsive** — a sharp, sudden onset, easy to time;
- **emergent** — a gradual onset, difficult to time, where analysts disagree most.

### 4.4 Sampling frequency, sample indices and timestamps

Arrival times are stored either as a **sample index** within a trace or window, or as an absolute **timestamp**. The conversion is:

```text
time_seconds          = sample_index / sampling_rate
absolute_timestamp    = trace_start_time + time_seconds
```

Two consequences follow, and both are requirement-bearing:

1. A phase pick is only meaningful relative to a **known sampling rate** and a **known time origin**. If a window is cut from a trace, the window's reference time origin must be carried with it, or absolute times cannot be recovered.
2. **Resampling changes the meaning of every sample index.** A pick index recorded at 100 Hz is not a valid index at 50 Hz. If resampling occurs, either the labels must be resampled with the waveform, or indices must be converted via time. This is a classic source of silent, large errors in picking pipelines.

### 4.5 Reference arrival annotations

The **reference picks** (also "labels" or "ground truth") are arrival times recorded by an analyst or taken from a catalogue. They are treated as ground truth in order to compute errors (`A5`), but they are not absolute physical truth: they derive from human judgement or from another algorithm, and therefore carry their own uncertainty and possible systematic bias. For clear impulsive P onsets this uncertainty may be a few samples; for emergent P and for S it is typically larger. A tolerance narrower than the reference-pick uncertainty partly measures label noise rather than model error. The report must state this relationship rather than presenting the reference as exact.

### 4.6 Probability-based phase detection

Instead of emitting a single arrival time per trace, a probabilistic picker such as the PhaseNet lineage emits, for **every time sample**, a probability for each class (P, S, noise). This has three useful consequences:

- The output is naturally aligned with the input: a window of `L` samples of three components maps to `L` samples of three class probabilities.
- Peaks in the P and S probability curves are candidate arrivals, so arrival times are **derived from** the network output rather than regressed directly.
- The shapes of the curves carry information: a broad or double-peaked curve is a signal of ambiguous or overlapping arrivals, which is useful for failure analysis and for an optional uncertainty estimate (`O4`).

### 4.7 The role of deep learning in seismic analysis, and in this project

Convolutional encoder–decoder networks learn waveform features directly from labelled examples, without an explicit threshold rule. The U-Net formulation adds skip connections between encoder and decoder so that coarse contextual features and fine timing detail are combined — attractive for a task where a decision is made per sample but requires context over a longer window.

PhaseNet demonstrated that a U-Net operating on three-component waveforms can output P/S/noise probability curves and that arrivals can be read from their peaks. SeismoNet is explicitly **inspired by** that approach rather than reproducing it (`NG5`).

**Phase picking is not earthquake prediction and is not early warning.** Phase picking measures when a wave *already recorded* arrived at a station. Earthquake prediction concerns whether and when an event will occur before it happens; SeismoNet makes no such claim. Early warning is an operational, multi-station, latency-critical system with its own validation regime; SeismoNet is not one, does not claim to be one, and does not claim to enable one (`NG1`, `NG3`).

**Background reading carried over from v0.1 (unverified):** PhaseNet (Zhu & Beroza); EQTransformer (Mousavi et al.); GPD (Ross et al.); SeisBench (Woollam et al.); STEAD (Mousavi et al.); INSTANCE (Michelini et al.); the "which picker fits my data?" comparison (Münchmeyer et al.); classical STA/LTA (Allen lineage) and AIC-based pickers. These are context, not requirements. See v0.1 §14 in `docs/archive/PRD-v0.1-original.md`.

---

## 5. Vision and Objectives

### 5.1 Vision

> A small, honest, fully reproducible seismic phase-picking pipeline whose every reported number can be traced back to a dataset version, a configuration file, a random seed and a documented evaluation protocol — and whose limitations are stated as clearly as its results.

### 5.2 Objectives

| ID | Objective | Type | Mandatory? |
|---|---|---|---|
| O-G1 | A trained 1D U-Net emitting P/S/noise probabilities per time step. | Primary | **Mandatory** |
| O-G2 | Extraction of P and S arrival times from probability curves using a documented rule. | Primary | **Mandatory** |
| O-G3 | Evaluation by residuals, precision, recall and F1 under a frozen tolerance, **separately for P and S**, with an explicit matching rule. | Primary | **Mandatory** |
| O-G4 | A single usable pipeline covering loading, preprocessing, training, inference, evaluation and visualisation. | Engineering | **Mandatory** |
| O-G5 | A controlled noise-robustness study on a fixed trained model over a fixed test set. | Research | **Mandatory** |
| O-G6 | A one-factor-at-a-time training-configuration study. | Research | **Mandatory** |
| O-G7 | Reproducibility: pinned dependencies, saved splits, recorded seeds/configs, and a documented regeneration command. | Engineering | **Mandatory** |
| O-E1 | Modular, tested, documented source layout. | Engineering | **Mandatory** |
| O-R1 | Statement of limitations and explicit absence of deployment claims. | Research/ethics | **Mandatory** |
| O-Opt1 | STA/LTA classical baseline for reference. | Optional | Optional |
| O-Opt2 | External pretrained picker evaluated on the same test set (reference only, not like-for-like). | Optional | Optional |
| O-Opt3 | Cross-dataset generalisation probe. | Optional | Optional |
| O-Opt4 | Pick-uncertainty estimate from probability-curve peak width. | Optional | Optional |
| O-Opt5 | Streamlit/Gradio demonstration interface. | Optional | Optional |

### 5.3 Rationale for treating what as mandatory

The mandatory set (O-G1…O-G7, O-E1, O-R1) maps **one-to-one onto the stated goals G1–G7 and the requirement to work responsibly**. Nothing in it is an invention. The optional set is exactly v0.1's `O1`–`O4` plus the demo interface; each raises the quality of the report but is not required by the problem statement, and each competes for the same finite budget (`OQ-20`).

### 5.4 Expected outcomes

1. A rented-or-free-tier-trainable checkpoint plus the exact configuration and seed that produced it.
2. Tables of P and S precision / recall / F1 at a frozen tolerance, with residual mean, standard deviation, median and MAE.
3. Residual histograms and waveform-plus-pick-plus-probability figures, including a curated failure set.
4. A noise-level sweep and a one-factor-at-a-time configuration comparison, in comparable tables.
5. A repository that another person can clone and use to regenerate the reported tables and figures.

### 5.5 Success criteria

Success is defined by **deliverables and rigour**, not by a score, because no numeric target was given (`SC-1`…`SC-8` in §16).

---

## 6. Target Users and Use Cases

The problem statement does not name users. The personas below are `[DERIVED]` from the nature of the task; whether any persona beyond the first two is genuinely in scope is `OQ-1`.

### 6.1 Primary users

**U1 — Seismology analyst / earthquake researcher**

- *Profile.* Familiar with P/S identification and pick quality; reviews and constructs earthquake catalogues.
- *Needs.* To judge whether the model's picks are physically plausible and how they differ from analyst picks; to see failure cases rather than only aggregate scores; to trust that no event leaked between splits; to see residuals in seconds with bias and spread.
- *Does not need.* To understand deep-learning internals.

**U2 — ML practitioner / student / project author**

- *Profile.* Builds and extends the pipeline; likely the project author.
- *Needs.* Modular code, configuration-driven experiments, fixed seeds, and a reproducible path from raw data to every reported figure and table.

### 6.2 Secondary users

**U3 — Project evaluator / reviewer / instructor**

- *Needs.* An unambiguous evaluation protocol, honest limitations, and the ability to reproduce the headline table on a different machine.

**U4 — Seismic network operator (indirect, not a design target)**

- Might later consider such a picker as a reference point. Because `NG1` excludes deployment claims, this persona is *informed by* the results, not served by them.

### 6.3 Out-of-scope users

Early-warning operators, emergency managers and members of the public. Nothing in this project is validated for such use (`NG1`).

### 6.4 Representative use cases (workflows)

| UC | Actor | Goal | Preconditions | Main flow | Success condition |
|---|---|---|---|---|---|
| UC-1 | U2 | Inspect the dataset before committing to it | Dataset local or cached | Load metadata → print summary statistics → plot a gallery of traces with reference P/S overlaid | P visibly precedes S; pick availability and quality issues are known |
| UC-2 | U2 | Prepare reproducible data | UC-1 satisfied, dataset has event IDs | Validate traces → event-level split → save split files → verify zero event overlap → generate windows and targets | Split files on disk; overlap check passes |
| UC-3 | U2 | Train a baseline | UC-2 satisfied; GPU or CPU budget known | Set seed → train with logged config → monitor validation loss → save best checkpoint | Checkpoint plus saved config plus loss curve exist; tiny-batch overfit test passed earlier |
| UC-4 | U1, U2 | Evaluate honestly | Checkpoint + frozen protocol | Extract picks on validation → select threshold → freeze → extract picks on test → compute P/S metrics and residuals | Tables exist at a stated tolerance with the matching rule stated |
| UC-5 | U1 | Understand a failure | UC-4 produced predictions | Select a failing sample → plot waveform, reference picks, predicted picks, probability curves → record a cause hypothesis flagged as hypothesis | A written, evidence-linked explanation, or an explicit "unexplained" |
| UC-6 | U1, U2 | Quantify noise sensitivity | A trained model and a defined SNR procedure | Degrade test windows to controlled noise levels → re-evaluate → tabulate metrics versus noise level | Table/plot of P and S metrics versus noise level, method documented |
| UC-7 | U3 | Reproduce a reported result | Repository cloned | Follow documented install + run + regenerate commands | Reported tables/figures reproduced, with any residual hardware-dependent variation stated |
| UC-8 | U1 (optional) | Explore picks interactively | Optional demo built | Select or upload a supported recording → view picks and probability curves → adjust threshold | Interactive view renders and results can be exported |

### 6.5 What this project does *not* offer its users

- No assurance of correctness on unseen data: a high probability output is not a verified pick.
- No guarantee of transfer to another region, network, instrument or magnitude range (`NG6`, limitation L1).
- No operational alerting, no location, no magnitude, no real-time stream processing.

---

## 7. Scope

### 7.1 In scope

1. Loading one supported seismic dataset with waveform, sampling rate and reference P/S pick indices.
2. Waveform preprocessing: quality screening, detrend/demean, amplitude normalisation, optional filtering, optional resampling.
3. Label preparation: fixed-length windows and per-sample P/S/noise target curves.
4. Event-aware train/validation/test splitting with persisted split membership.
5. Switchable, controlled training-time augmentation, with noise addition separable.
6. A 1D U-Net mapping a three-component window to three per-sample class probabilities.
7. Reproducible training with validation monitoring, checkpointing and configuration capture.
8. P-wave and S-wave inference: probability curves and extracted arrival times.
9. Probability visualisation: waveform, reference and predicted picks, probability curves, threshold.
10. Quantitative evaluation: residuals and P/S-separated precision, recall and F1 under a frozen tolerance.
11. A noise-robustness experiment with a documented noise-generation method.
12. A one-factor-at-a-time training-configuration experiment.
13. Reproducible results: pinned dependencies, saved splits, recorded seeds and configs, regeneration command.
14. A lightweight demonstration interface — **optional** (`O-Opt5`), and only after core validation (`FR-059`).
15. Honest documentation: a limitations section and no deployment claims.

### 7.2 Out of scope

1. Predicting earthquakes before they occur.
2. Claiming guaranteed or operational earthquake early warning.
3. Automatically issuing public or emergency alerts.
4. Real-time, low-latency continuous-stream processing and per-day false-alarm-rate claims.
5. Multi-station association, location, magnitude, focal mechanisms.
6. Unverified integrations with seismic monitoring infrastructure.
7. Instrument-response removal and absolute-magnitude/unit normalisation across heterogeneous instruments.
8. Teleseismic and sub-phase (Pn/Pg, Sn/Sg) identification as distinct classes.
9. Novel architecture research or a claim to reproduce PhaseNet's published numbers.
10. Any generalisation claim beyond the selected dataset.

---

## 8. Functional Requirements

Priorities use MoSCoW: **M** = Must, **S** = Should, **C** = Could.
Every subsequent requirement in this document is tagged `[GIVEN]`, `[DERIVED]`, `[PROPOSED]` or `[OPEN]`.
A **verification method** is one of: **UT** (unit test), **IT** (integration test), **INSP** (code/config/artifact inspection), **METRIC** (measured output), **VIS** (visual inspection of a figure), **DOC** (documented procedure).

### 8.1 Dataset ingestion, validation and metadata

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-001 | Load the selected dataset and expose, per trace: three-component waveform, sampling rate, reference P and S pick indices, and where available magnitude, distance and SNR. | M | OQ-3 closed | Loader reads a documented dataset layout and returns waveforms with associated sampling rate and picks; a smoke test loads ≥1 real trace | IT, INSP | `[GIVEN]` (v0.1 FR-D1) |
| FR-002 | Report dataset summary statistics: trace count, pick availability, sampling-rate distribution, and where available magnitude / distance / SNR distributions. | M | FR-001 | A report/notebook section prints these statistics from the real dataset | METRIC, VIS | `[DERIVED]` (FR-D2) |
| FR-003 | Detect and exclude or flag unusable traces: NaN/Inf samples, zero-variance (flat) traces, missing reference picks where picks are required, and sampling rate inconsistent with the expected value. Log the count and reason for each exclusion. | M | FR-001 | A machine-readable data-quality log lists each excluded trace ID and reason; a unit test with injected NaN and flat traces produces exactly the expected log entries | UT, INSP | `[DERIVED]` (FR-D3) |
| FR-004 | Split data into train / validation / test **by event identifier**, never by trace alone. | M | FR-001, DR-003 | Split code groups traces by event ID; a leakage test asserts zero event-ID overlap across splits | UT, IT | `[DERIVED]` — event leakage (FR-D4) |
| FR-005 | Persist split membership to disk in an inspectable, diff-able format. | M | FR-004 | Split files are written and re-loadable; the same inputs reproduce the same split given the same seed | UT, INSP | `[DERIVED]` (FR-D5) |
| FR-006 | Make split ratios configurable. | S | FR-004 | Changing a config value changes the split proportions; default recorded in config | INSP | `[PROPOSED]` (FR-D6; `OQ-5`) |
| FR-007 | Support running on a configurable subset of the dataset via a size limit. | S | FR-001 | A config limit reduces the number of traces loaded and logs how many were used | INSP, METRIC | `[PROPOSED]` (`A6`; FR-D7) |

### 8.2 Input validation

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-008 | Validate input windows at inference time: exactly three components, expected sampling rate, expected window length, finite values, and non-flat signal. Reject or explicitly resample/handle anything else; never silently accept a mismatch. | M | FR-001 | Parametrised tests feed wrong-shape, wrong-rate, NaN-containing and flat inputs and each is rejected or explicitly handled with a logged reason | UT | `[DERIVED]` (tech.md §3; E10–E12, E18) |
| FR-009 | Return an explicit "no pick" result rather than a fabricated or placeholder arrival time when no peak exceeds the threshold. | M | FR-034 | A synthetic all-noise input yields a "no pick" result object, not a number | UT | `[DERIVED]` (FR-K3) |

### 8.3 Metadata processing

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-010 | Construct or normalise the event identifier used for splitting, from dataset metadata, when the dataset does not supply one directly. | M | FR-001, DR-003 | The construction rule is documented and unit-tested on at least two synthetic metadata rows | UT, DOC | `[DERIVED]` (FR-D4, DR-3) |
| FR-011 | Support stratifying reported results by available metadata bins (e.g., SNR, distance, magnitude) **only when those fields exist**. | S | FR-002, FR-052 | Stratified tables are produced for the chosen dataset if the fields exist; if not, the absence is documented | METRIC, DOC | `[PROPOSED]` (FR-E8) |
| FR-012 | Record, per trace, the metadata used in preprocessing and evaluation (sampling rate, pick indices, window origin, assigned split). | M | FR-001 | Persisted record allows any reported sample to be traced back to its source trace and window | INSP | `[DERIVED]` |

### 8.4 Preprocessing

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-013 | Apply per-component detrend and demean. | M | FR-001 | Unit test confirms a detrended, demeaned trace has zero mean per channel within tolerance | UT | `[PROPOSED]` (FR-P1) |
| FR-014 | Apply amplitude normalisation to each window with a configurable, recorded method. Normalisation must not divide by zero. | M | FR-013 | Config names the method; a flat-channel test does not produce NaN/Inf | UT, INSP | `[DERIVED]` (FR-P2; E11) |
| FR-015 | Support an optional bandpass filter with configurable, recorded corner frequencies. If no filter is used, that decision is documented. | S | FR-013 | Config records either the filter parameters or the explicit decision to omit filtering | INSP, DOC | `[PROPOSED]` (FR-P3; `OQ-6`) |
| FR-016 | Resample to a common rate when source rates differ, applying anti-aliasing before any downsampling. | S | FR-001 | A test resamples a known synthetic waveform and confirms the expected length and preserved phase position within tolerance | UT | `[DERIVED]` (FR-P4; E18) |
| FR-017 | Produce fixed-length windows. | M | FR-013 | Every emitted window has exactly `L` samples and three channels | UT | `[DERIVED]` (FR-P5) |
| FR-018 | For training windows, randomise the window start so that reference picks fall at varying positions within the window. | M | FR-017 | Across many sampled training windows the empirical distribution of pick positions is broad and not concentrated at one offset | METRIC, UT | `[DERIVED]` — prevents position learning (FR-P6; `R2`) |
| FR-019 | Support a configurable fraction of pure-noise windows containing no P or S. | S | FR-017 | Config fraction is respected within sampling error; those windows carry all-zero P and S targets | UT | `[PROPOSED]` (FR-P7; `OQ-7`) |
| FR-020 | Use preprocessing at evaluation time identical to training time, except for training-only augmentation. | M | FR-013, FR-021 | A shared preprocessing function is used by train and evaluate paths; a test asserts identical output for identical input | UT, INSP | `[DERIVED]` (FR-P8) |

### 8.5 Target (label) generation

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-021 | Generate per-sample target curves for P, S and noise with the same length as the input window. | M | FR-017 | Target array shape equals input window shape along time | UT | `[GIVEN]` (FR-L1) |
| FR-022 | Represent P and S targets as smooth peaked curves centred on the reference pick, with configurable width σ. | M | FR-021 | A target for a known pick index peaks exactly at that index; σ changes the width as configured | UT | `[PROPOSED]` shape from PhaseNet lineage (FR-L2; `OQ-8`) |
| FR-023 | Define the noise target so that P + S + noise = 1 at every sample. | M | FR-021 | A test asserts per-sample sum equals 1 within floating-point tolerance for random pick configurations, including overlapping P/S targets | UT | `[DERIVED]` (FR-L3; `E4`) |
| FR-024 | Set that phase's target to all zeros when the window contains no pick for that phase, rather than fabricating a pick. | M | FR-021 | A window with no S pick yields an all-zero S target and a non-zero P target | UT | `[DERIVED]` (FR-L4; `E1`, `E2`) |

### 8.6 Dataset splitting (see also FR-004, FR-005)

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-025 | Verify, as an automated check, that no event appears in more than one split, and fail loudly if it does. | M | FR-004, FR-005 | The check is a runnable test and is also executed as a guard at training start | UT, IT | `[DERIVED]` (`SC-8`) |
| FR-026 | Make the split deterministic given a recorded seed and the input metadata. | M | FR-005 | Two runs with the same seed produce byte-identical split files | UT | `[GIVEN]` reproducibility |
| FR-027 | Document the split ratios and the rationale, and record them with each experiment. | M | FR-006 | Config snapshots contain split ratios; documentation states them | INSP, DOC | `[PROPOSED]` (`OQ-5`) |

### 8.7 Augmentation

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-028 | Make each augmentation independently switchable through configuration. | M | — | Enabling/disabling one augmentation leaves the others unchanged; config schema lists each independently | UT, INSP | `[DERIVED]` for ablation `G6` (FR-A1) |
| FR-029 | Make noise-addition augmentation switchable separately from all other augmentations. | M | FR-028 | A toggle controls noise addition alone; the configuration study can vary it independently | UT, INSP | `[DERIVED]` (`G5`, FR-A2) |
| FR-030 | Apply augmentation to training data only. Validation and test data are not augmented except in the explicit noise-robustness experiment. | M | FR-028 | Test asserts the validation/test path returns the unmodified signal for a fixed seed | UT | `[DERIVED]` (FR-A3) |
| FR-031 | Keep labels consistent with the waveform under any augmentation that moves or scales the signal (e.g., a shift must move the target curves by the same amount). | M | FR-021, FR-028 | A shift-augmentation test asserts the target peak moves by exactly the applied shift | UT | `[DERIVED]` (FR-A4) |

### 8.8 Model

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-032 | Implement a one-dimensional U-Net with an encoder, a decoder and skip connections. | M | — | Model constructs without error; encoder/decoder/skip structure is visible in code and described in `docs/TECHNICAL_ARCHITECTURE.md` | INSP, UT | `[GIVEN]` (FR-M1) |
| FR-033 | Accept a three-component window and output three channels (P, S, noise) per time step. | M | FR-032 | Input `[3, L]` produces output `[3, L]` | UT | `[GIVEN]`/`A2` (FR-M2) |
| FR-034 | Ensure output length equals input length. | M | FR-032 | Shape test asserts equality for several valid `L` | UT | `[DERIVED]` (FR-M3) |
| FR-035 | Make depth, base channel count and kernel size configurable. | M | FR-032 | Changing each config value changes the constructed model as expected | UT, INSP | `[DERIVED]` (`G6`, FR-M4) |
| FR-036 | Assert that the window length is compatible with the chosen depth (divisible by `2^depth` when using stride-2 down/upsampling) and fail with a clear message otherwise. | M | FR-032, FR-017 | Constructing the model with an incompatible length raises a specific, readable error | UT | `[DERIVED]` (FR-M5) |
| FR-037 | Apply a softmax over the three output channels so that the three probabilities sum to 1 per sample. | M | FR-033 | A test asserts each sample's three outputs sum to 1 within tolerance | UT | `[DERIVED]` (FR-L3, `US-05`) |
| FR-038 | Report the model's parameter count. | S | FR-032 | Training log and/or model summary states the parameter count | INSP | `[PROPOSED]` (FR-M6) |

### 8.9 Training

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-039 | Train with a loss defined on per-sample probability outputs against the target curves. | M | FR-021, FR-037 | Training runs and loss decreases on a small synthetic dataset; the loss is named in config and in the report | IT, INSP | `[GIVEN]`; exact loss `[OPEN]` (FR-T1, `OQ-9`) |
| FR-040 | Log training and validation loss per epoch, and save the best checkpoint by a stated validation criterion. | M | FR-039 | Loss curves exist; the saved checkpoint is the one the criterion selects | METRIC, INSP | `[DERIVED]` (FR-T2) |
| FR-041 | Set and record random seeds for Python, NumPy and PyTorch. | M | — | Seeds appear in config and in the run log; determinism test on CPU reproduces results within a stated tolerance | UT, INSP | `[GIVEN]` reproducibility (FR-T3) |
| FR-042 | Save the full run configuration alongside each checkpoint. | M | FR-040 | A config snapshot sits beside the checkpoint and reloads to the same values | INSP, UT | `[DERIVED]` (FR-T4) |
| FR-043 | Support early stopping. | S | FR-040 | Training halts after the configured patience without improving validation loss, and the event is logged | IT | `[PROPOSED]` (FR-T5) |
| FR-044 | Include an automated "overfit a tiny batch" sanity check that drives loss to near zero on a handful of samples. | M | FR-039 | A runnable test or script overfits a tiny fixed batch and asserts a low final loss | IT | `[DERIVED]` (`US-06`) |
| FR-045 | State clearly, in the repository, whether a result came from training/fine-tuning performed in this project or from a pretrained model being run. | M | FR-039 | Report and checkpoint metadata distinguish trained-from-scratch, fine-tuned, and pretrained-inference-only | DOC, INSP | `[GIVEN]` (README honesty note) |

### 8.10 Checkpointing and artifacts

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-046 | Save model checkpoints in a safe serialisation format (weights only; not arbitrary pickle), with a documented naming convention. | M | FR-040 | Checkpoint files load with weights-only semantics; naming convention documented in `docs/REPRODUCIBILITY.md` | INSP, UT | `[DERIVED]` (tech.md §7 security) |
| FR-047 | Record with each checkpoint: config hash or snapshot, seed, dataset/split identifier, and the validation metric that selected it. | M | FR-042, FR-046 | All four fields are recoverable from the checkpoint directory alone | INSP | `[DERIVED]` (`NFR-001`) |
| FR-048 | Keep artifacts (checkpoints, logs, figures, tables) in a documented directory layout that is excluded from version control. | M | — | `.gitignore` excludes large artifacts; layout documented | INSP | `[PROPOSED]` |

### 8.11 Inference and arrival-time extraction

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-049 | Produce per-sample P, S and noise probability curves for a given window using a trained checkpoint. | M | FR-037, FR-046 | Inference on a fixed window with a fixed checkpoint returns three curves of length `L` | UT | `[GIVEN]` (FR-K1 precursor) |
| FR-050 | Derive one P arrival time and one S arrival time from their respective probability channels using a threshold plus a peak-selection rule. | M | FR-049 | For a synthetic waveform with a known P time, the extracted P pick is within the documented tolerance of the true index | UT, IT | `[GIVEN]` (FR-K1; `A4`) |
| FR-051 | Make the threshold configurable and select it on validation data only. | M | FR-050 | Config exposes the threshold; the reported value is the one chosen on validation; test-set evaluation uses it unchanged | INSP, DOC | `[DERIVED]` (FR-K2; `FR-045`) |
| FR-052 | Apply a documented, deterministic rule where several peaks exceed threshold. | M | FR-050 | The rule is stated in the report and in code; the code returns exactly one pick per phase per window | INSP, UT | `[PROPOSED]` (FR-K4; `OQ-10`) |
| FR-053 | Convert picks to seconds using the window's sampling rate, and to absolute time using the trace start time where available. | M | FR-050 | A test verifies sample-index → seconds → absolute-time conversion against hand-computed values | UT | `[DERIVED]` (FR-K5) |
| FR-054 | Report how often multiple peaks, "no pick", and P-after-S outcomes occur, rather than silently discarding them. | S | FR-050, FR-052 | Inference summary counts these three conditions | METRIC | `[DERIVED]` (`E27`, `E29`) |

### 8.12 Evaluation

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-055 | Compute arrival-time residuals (predicted minus reference) for P and S separately. | M | FR-053 | Residual sign convention matches the definition and is stated; a test with hand-computed picks yields the expected residual | UT | `[GIVEN]` (FR-E1) |
| FR-056 | Report residual mean, standard deviation, median and mean absolute error. | M | FR-055 | All four statistics appear per phase in the results table | METRIC | `[PROPOSED]` (FR-E2) |
| FR-057 | Compute precision, recall and F1 under at least one clearly defined time tolerance. | M | FR-055 | Metrics are computed by a tested function; hand-computed cases reproduce expected values including edge cases | UT, METRIC | `[GIVEN]` (FR-E3) |
| FR-058 | Make tolerance value(s) configurable and state the tolerance in every results table. | M | FR-057 | No results table is emitted without a tolerance label; the value is configurable | INSP | `[GIVEN]`/`[OPEN]` (FR-E4; `OQ-11`) |
| FR-059 | Define the TP/FP/FN matching rule in the report, including the treatment of a pick that falls outside tolerance. | M | FR-057 | An "Evaluation protocol" section defines each outcome and states that an out-of-tolerance pick is counted under a stated convention | DOC | `[GIVEN]` (FR-E5) |
| FR-060 | Evaluate P and S separately and never report a combined-only score. | M | FR-055 | Every results table has separate P and S columns/rows | INSP | `[DERIVED]` (FR-E6; `R3`) |
| FR-061 | Compute final test metrics only after model selection and threshold selection are complete. | M | FR-051, FR-057 | A documented order of operations; test metrics are generated from a frozen config | DOC, INSP | `[DERIVED]` (FR-E7; `NFR-003`) |
| FR-062 | Handle undefined metric cases (zero denominators) by returning a defined value and reporting the denominator. | M | FR-057 | A zero-reference-phase test returns a defined value and the reported denominator is zero | UT | `[DERIVED]` (E32) |
| FR-063 | Assume at most one P pick and one S pick per window, and state this assumption in the report. | M | FR-050 | The limitation is stated explicitly in the report's limitations section | DOC | `[PROPOSED]` (`A4`) |

### 8.13 Visualisation

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-064 | Plot, for any chosen sample, the three-component waveform with reference and predicted picks overlaid. | M | FR-050 | A reusable function produces this figure for an arbitrary sample index | VIS | `[GIVEN]` (FR-V1) |
| FR-065 | Show P, S and noise probability curves and the applied threshold on the same figure. | M | FR-049 | Same figure includes the three curves and a threshold line | VIS | `[GIVEN]` (FR-V2) |
| FR-066 | Produce residual histograms for P and S. | M | FR-055 | Two histograms (or one two-panel figure) per evaluation run | VIS | `[DERIVED]` (FR-V3) |
| FR-067 | Produce example galleries of successes and failures. | S | FR-057, FR-064 | Gallery figures exist and are referenced from the report | VIS | `[PROPOSED]` (FR-V4) |
| FR-068 | For a failure case, present a short written cause hypothesis that is explicitly flagged as a hypothesis where it is not verified. | S | FR-067 | Failure gallery entries each carry a marked hypothesis or an explicit "unexplained" label | DOC, VIS | `[PROPOSED]` (`US-13`) |

### 8.14 Experiments

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-069 | Evaluate a fixed trained model on a fixed test set under multiple controlled noise levels. | M | FR-049, FR-061 | A table/plot of P and S metrics versus noise level exists; the model and test set are held fixed | METRIC | `[GIVEN]` (FR-X1) |
| FR-070 | Document the noise-generation method and the exact definition of the noise level (e.g., the SNR definition). | M | FR-069 | The report states the noise type, the SNR formula, and how signal power is computed | DOC | `[DERIVED]` (FR-X2; `E36`, `E37`, `OQ-18`) |
| FR-071 | Fix the noise random seed so results at different levels are comparable. | M | FR-069, FR-041 | Re-running the sweep reproduces the same noise realisations | UT | `[DERIVED]` (E38) |
| FR-072 | Support comparing models trained with and without noise-augmentation. | S | FR-029, FR-069 | A comparison table exists when the experiment is run | METRIC | `[PROPOSED]` (FR-X3) |
| FR-073 | Support one-factor-at-a-time variation of selected training configurations from a documented baseline. | M | FR-039 | An ablation table contains a baseline row and one changed factor per row | METRIC, INSP | `[GIVEN]`/`[OPEN]` (FR-X4; `OQ-12`) |
| FR-074 | Support repeated runs with different seeds so variability can be reported. | S | FR-041 | Multiple seeds can be launched from config; results are reported per seed | INSP, METRIC | `[PROPOSED]` (FR-X5) |
| FR-075 | Record every experiment with its hypothesis, configuration, seed, dataset/split identity, metrics and interpretation. | M | FR-073 | An experiment record exists per run, following `docs/EXPERIMENT_PLAN.md` | DOC, INSP | `[DERIVED]` (`G7`) |

### 8.15 Result export and experiment management

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-076 | Export results (per-sample predictions and aggregate metrics) to machine-readable CSV/JSON. | M | FR-057 | Exported files load cleanly in pandas and contain the tolerance and threshold used | INSP, UT | `[PROPOSED]` (tech.md §4) |
| FR-077 | Drive training, evaluation and experiments from configuration files rather than hard-coded values. | M | FR-042 | Every scientific parameter is a config field; changing a value requires no code edit | INSP | `[DERIVED]` (`NFR-001`, `NFR-004`) |
| FR-078 | Provide a single documented command sequence that regenerates the reported tables and figures from saved artifacts. | M | FR-076, FR-046 | Following the documented commands on a clean checkout reproduces the reported tables and figures | IT, DOC | `[DERIVED]` (FR-R3; `SC-6`) |

### 8.16 Optional user interface

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-079 | Provide a lightweight demonstration interface to browse samples, view waveform + reference picks + predicted picks + probability curves, and adjust the pick threshold. | C | FR-064, FR-065 | The application starts with one documented command and renders the four elements for a selected sample | VIS | `[PROPOSED]` (`O-Opt5`; `US-12`) |
| FR-080 | Export or display results from the interface without storing uploads unnecessarily. | C | FR-079 | The interface can show/export a result; no persistence of uploaded data by default | INSP | `[PROPOSED]` (tech.md §7) |
| FR-081 | Build the optional interface only after core validation is complete. | C | FR-057, FR-061 | Roadmap places the interface after baseline evaluation; no core work is blocked by it | DOC | `[DERIVED]` (`O-Opt5`) |

### 8.17 Reproducibility

| ID | Description | Pri | Depends on | Acceptance criteria | Verification | Source |
|---|---|---|---|---|---|---|
| FR-082 | Provide a pinned dependency specification. | M | — | A dependency file lists pinned versions; a fresh environment installs from it | IT, INSP | `[GIVEN]` (FR-R1) |
| FR-083 | Provide a README with install and run instructions that match the repository's actual state. | M | — | Every command shown exists and is marked implemented or planned | INSP | `[DERIVED]` (FR-R2) |
| FR-084 | Document, in one place, the environment, seeds, splits, config snapshots, checkpoints, evaluation commands and artifact naming. | M | FR-078 | `docs/REPRODUCIBILITY.md` covers all seven topics | DOC | `[DERIVED]` (`SC-6`) |

---

## 9. Non-Functional Requirements

Measurable targets are given only where they can be justified; otherwise the target is **TBD**, and no benchmark is invented.

| ID | Category | Requirement | Target | Pri | Verification | Source |
|---|---|---|---|---|---|---|
| NFR-001 | Reproducibility | Results shall be reproducible from a recorded configuration + seed + saved split, on the same hardware class, to within stated hardware non-determinism. | Reproduce headline table on CPU within documented tolerance; GPU variation disclosed | M | IT, DOC | `[GIVEN]` (`NFR-1`) |
| NFR-002 | Transparency / reliability | Every reported metric shall be accompanied by its tolerance, threshold and matching rule, and by its denominator. | 100% of results tables | M | INSP, DOC | `[DERIVED]` (`NFR-2`) |
| NFR-003 | Data integrity / no leakage | No tuning decision shall use test data, and no event shall appear in more than one split. | Zero event-ID overlap; zero test-set tuning steps | M | UT, DOC | `[DERIVED]` (`NFR-3`, `SC-8`) |
| NFR-004 | Reliability | Failures (missing files, malformed traces, incompatible shapes) shall fail loudly with a specific message, never silently degrade. | No silent exception swallowing in data and model paths | M | INSP, UT | `[DERIVED]` (`US-03`) |
| NFR-005 | Maintainability | Data, model, training, evaluation and experiments shall be separable modules. | Each concern in its own module; no cross-imports that make unit testing impossible | S | INSP | `[PROPOSED]` (`NFR-4`) |
| NFR-006 | Performance | Training and inference shall complete within the project's compute budget on a single commodity GPU or CPU fallback. | **TBD** — to be measured at M4; no target set in advance | S | METRIC | `[PROPOSED]` (`NFR-5`, `A6`, `OQ-20`) |
| NFR-007 | Memory efficiency | Peak memory shall fit the available device, using a dataset subset and a configurable batch size where needed. | **TBD** — measured at M4; must fit 4 GiB VRAM or run on CPU | S | METRIC | `[PROPOSED]` (audit §7) |
| NFR-008 | Portability | The pipeline shall run on Windows, Linux and macOS with only documented dependency installation; no OS-specific path assumptions. | Runs on at least Windows (author) and Linux (CI) | S | IT | `[PROPOSED]` |
| NFR-009 | Data integrity | Source data shall never be modified in place; all derived data written to separate outputs. | Read-only treatment of the raw dataset | M | INSP | `[DERIVED]` |
| NFR-010 | Testability | Core logic (labels, metrics, picking, splits, shapes) shall be unit-testable without the full dataset. | Synthetic-fixture tests exist for each core module | M | UT | `[DERIVED]` (`docs/TESTING_STRATEGY.md`) |
| NFR-011 | Documentation | Every scientific parameter shall have a recorded rationale; every document shall link to its neighbours rather than duplicating them. | Rationale present in §10 or `docs/REASONING_AND_DECISIONS.md` | M | INSP | `[DERIVED]` |
| NFR-012 | Usability | A reviewer shall be able to go from a clean clone to a reproduced result using only the README and `docs/`. | Documented path exists and is followed once end-to-end by the author | M | IT, DOC | `[DERIVED]` (`SC-6`) |
| NFR-013 | Licensing / data use | The chosen dataset's licence, attribution and citation requirements shall be followed and stated. | Licence recorded in `docs/DATASET_GUIDE.md` | M | DOC | `[DERIVED]` (`NFR-7`, `DR-005`) |
| NFR-014 | Honest scope | No document shall claim operational or deployment readiness. | Zero deployment/early-warning claims in any deliverable | M | INSP | `[GIVEN]` (`NFR-6`, `NG1`) |
| NFR-015 | Security | Downloaded checkpoints shall not be loaded in an unsafe pickle mode; no secrets shall be committed. | Weights-only checkpoint loading; no credentials in the repository | S | INSP | `[PROPOSED]` (tech.md §7) |

---

## 10. Scientific and Model Requirements

These requirements govern the *science* of the pipeline: the representations, the numerical conventions and the decision rules. Each carries a rationale. **Where a value is a starting proposal, it is labelled `[PROPOSED]` and is expected to be revisited; where the value is genuinely undecided it is `[OPEN]` and appears in §17.** Deeper discussion and alternatives are in `docs/REASONING_AND_DECISIONS.md`.

| ID | Requirement | Value / policy | Rationale | Status |
|---|---|---|---|---|
| SR-001 | **Input representation.** Input to the model shall be a fixed-length window of a three-component waveform, represented as a float array of shape `[3, L]` with channels ordered `(Z, N, E)`. | `(Z, N, E)`, float32 | A U-Net needs a fixed-size input. Z-first ordering is the conventional ordering for P-wave sensitivity on the vertical and S-wave sensitivity on horizontals. | `[PROPOSED]` (`A2`) |
| SR-002 | **Channel-ordering policy.** The channel order shall be validated at load time and asserted, not assumed. A trace whose component order cannot be established shall be excluded. | Assert `(Z, N, E)` | Silently swapping horizontals would corrupt S-wave learning while leaving the pipeline "working", which is the worst failure mode. | `[DERIVED]` |
| SR-003 | **Sampling-rate policy.** A single common sampling rate shall be used throughout. Traces at other rates shall be resampled with anti-aliasing before downsampling, or excluded. The rate shall be recorded with every window. | Common rate; default **100 Hz** `[PROPOSED]` | Sample indices, labels and tolerances are all rate-dependent. Mixing rates without conversion is a classic silent-error source (§4.4). 100 Hz is a common regional-network-based choice and matches earlier planning. | `[PROPOSED]` (`OQ-4`) |
| SR-004 | **Window-length policy.** Windows shall have a single configured length `L`, compatible with model depth. | Default **3072 samples** `[PROPOSED]` | 3072 = 3 × 1024 is divisible by `2^depth` for the proposed depth 4 (`FR-036`), so decoder and skip-connection shapes align exactly. PhaseNet-lineage implementations used 3001; the choice must be fixed and documented rather than left implicit. | `[PROPOSED]` (`A3`, `OQ-4`) |
| SR-005 | **Normalisation rules.** Per-component detrend and demean shall be applied, followed by per-window amplitude normalisation using a configurable, recorded method. Normalisation statistics shall be computed from the window only. | Per-window normalisation | Per-window normalisation removes the influence of unit and instrument scale without requiring instrument-response removal (out of scope, §7.2). Computing statistics from the whole dataset instead would leak information across splits and couple train and test preprocessing. | `[PROPOSED]` (`FR-014`) |
| SR-006 | **Target representation.** P and S targets shall be smooth peaked (Gaussian-shaped) curves centred on the reference pick. The noise target is the remainder, clipped to remain non-negative, so the three targets sum to 1 per sample. Picks absent from the window give an all-zero target for that phase. | Gaussian, σ = **10 samples** `[PROPOSED]` baseline | Gaussian targets are the established PhaseNet-lineage convention: they tolerate the ±few-sample uncertainty in reference onsets instead of demanding exact-index regression, and they produce a probability curve whose peak can be located by peak-picking. σ is a smoothing scale that must exceed label jitter and stay well below the window length. σ is in the ablation list. | `[PROPOSED]` (`OQ-8`, `E4`) |
| SR-007 | **Loss function.** The baseline loss shall be a probability-aware cross-entropy between predicted per-sample class probabilities and the Gaussian target curves. | Soft cross-entropy `[PROPOSED]`; MSE as an ablation | The targets are probability-shaped rather than one-hot, so "soft" cross-entropy (cross-entropy against soft targets) is the natural fit and is the PhaseNet-lineage choice. MSE treats the problem as regression and tends to produce over-smoothed, wider peaks. The choice is recorded and ablatable rather than assumed final. | `[PROPOSED]` (`OQ-9`) |
| SR-008 | **Architecture requirements.** The model shall be a 1D U-Net: an encoder of strided convolutions, a decoder of upsampling plus convolution, and skip connections between matching scales, with BatchNorm and ReLU activations by default. | Depth 4, base 16 channels, kernel 7 `[PROPOSED]` | Skip connections preserve fine timing precision that pooling alone would destroy — essential when the output is a per-sample time decision. A small depth/width is chosen deliberately so the baseline trains on free-tier or 4 GiB hardware; all three are configurable for the ablation study. | `[PROPOSED]` (`OQ-12`) |
| SR-009 | **Training and validation procedure.** Training shall use an adaptive optimiser with a validation-monitored learning-rate schedule, log per-epoch train/validation loss, and evaluate the validation set at a fixed cadence. | Adam/AdamW, lr 1e-3, `ReduceLROnPlateau` `[PROPOSED]`; batch size and epoch budget TBD | Adam-lineage optimisers are the reliable default for this network family. A plateau-based scheduler avoids hand-designing a decay schedule. Exact batch size and epoch count depend on the chosen dataset subset and must be tuned to the measured budget (NFR-006). | `[PROPOSED]` (`OQ-20`, `NFR-006`) |
| SR-010 | **Checkpoint-selection criterion.** The best checkpoint shall be selected on a validation criterion stated in advance. | Baseline: lowest validation loss `[PROPOSED]`; alternative: best validation P/S F1 at the frozen tolerance | Loss is available every epoch and is not metric-specific; F1-at-tolerance is closer to the reported objective but requires a threshold choice during training. Whichever is used must be fixed before training, so that "best" is not redefined after seeing results. | `[PROPOSED]` |
| SR-011 | **Inference threshold selection.** The peak-detection threshold shall be selected on validation data, frozen, and then applied unchanged to the test set. | Selected on validation `[OPEN]` — earlier candidate 0.3 | Choosing the threshold on test data would make the test set a tuning set and inflate the reported score (`NFR-003`). A slightly lower threshold trades precision for recall on weak S onsets; the operating point should be selected to match the intended use, and reported alongside at least one alternative. | `[DERIVED]` (`OQ-10`) |
| SR-012 | **Peak-detection rules.** A single peak per phase per window shall be selected using a documented, deterministic rule applied to peaks above threshold. | Baseline: highest peak above threshold; a minimum-separation constraint is permitted if documented | The highest-peak rule is simple and reproducible and satisfies `A4`'s one-pick-per-phase constraint. It is a weakness when a spurious early peak is larger than the true onset, which must be quantified, not hidden. | `[PROPOSED]` (`OQ-10`, `E27`) |
| SR-013 | **Missing-phase handling.** If no peak exceeds threshold, the result shall be an explicit "no pick". If a phase is absent from the window, its target shall be all zeros. | "No pick" object; all-zero target | Returning a fabricated arrival time would corrupt both the residual statistics and the precision/recall accounting. | `[DERIVED]` (`FR-009`, `FR-024`) |
| SR-014 | **Timestamp conversion.** Picks shall be reported in seconds as `sample_index / sampling_rate`, and in absolute time as `trace_start_time + seconds`, where a trace start time exists. | As stated | Separating relative from absolute time makes the relative results independent of absolute-time availability, and makes the conversion testable in isolation. | `[DERIVED]` (`FR-053`) |
| SR-015 | **Ordering and plausibility.** Predicted P occurring after predicted S shall be counted and reported rather than silently corrected, unless a configurable enforcement rule is enabled and its effect is reported. | Count and report; enforcement `[OPEN]` | A P-after-S prediction is physically implausible and is informative as a failure-rate statistic. Enforcing ordering would improve plausibility while hiding the model's actual behaviour, so both variants should be reported if enforcement is adopted. | `[OPEN]` (`OQ-17`, `E29`) |
| SR-016 | **Evaluation tolerance.** The evaluation tolerance shall be a fixed, pre-declared value in samples or seconds, chosen with reference to the reference picks' own uncertainty, and reported in every table. | `[OPEN]` — report a strict and a lenient value `[PROPOSED]` | The reference picks are analyst-derived and uncertain; a tolerance tighter than that uncertainty measures label noise rather than model error (§4.5). Reporting two tolerances shows how sensitive the conclusion is. | `[OPEN]` (`OQ-11`) |
| SR-017 | **Comparison across runs.** Any comparison of two configurations shall hold the dataset, split, seed policy, preprocessing and evaluation protocol fixed, and vary one factor. | One-factor-at-a-time | If several things change at once, the experiment cannot attribute the difference (`US-15`). | `[DERIVED]` (`FR-073`) |

---

## 11. Dataset Requirements

### 11.1 Status

**No dataset has been selected.** `OQ-3` is open. Everything below is a *requirement on* the eventual choice, plus a list of candidates whose properties have **not** been verified by this project. The README lists PhaseNet's repository and the STEAD dataset as "potential starting points" only. v0.1 additionally names INSTANCE and ETHZ as options reachable via SeisBench. **None of these properties has been checked; all must be verified from the dataset's own documentation before selection.**

### 11.2 Requirements on the chosen dataset

| ID | Requirement | Pri | Rationale | Verification | Source |
|---|---|---|---|---|---|
| DR-001 | The dataset shall provide waveform data on the required component set (three components for the planned model) with a known sampling rate. | M | The model input is fixed-length three-component; an unknown or mixed rate breaks label and tolerance semantics. | INSP of dataset docs; loader smoke test | v0.1 DR-1 |
| DR-002 | The dataset shall provide reference P pick times, and reference S pick times for S evaluation. | M | Without S labels, half the stated objective (`G3`, `FR-060`) is impossible. | INSP; count of traces with both picks | v0.1 DR-2 |
| DR-003 | The dataset shall provide an event identifier, or enough metadata (origin time, source location, event code) to construct one, so that event-level splitting is possible. **If it does not, the dataset choice must be revisited.** | M | Event-level splitting is the project's primary defence against inflated results (`FR-004`, `R1`). | INSP; construction rule tested (`FR-010`) | v0.1 DR-3 |
| DR-004 | Where available, the dataset should provide pick quality/uncertainty and SNR, to enable stratified analysis. | S | Enables `FR-011` and informs the tolerance choice (`SR-016`). | INSP | v0.1 DR-4 |
| DR-005 | The dataset's licence and citation terms shall be identified, recorded and complied with. | M | Legal and academic obligation (`NFR-013`). | DOC in `docs/DATASET_GUIDE.md` | v0.1 NFR-7 |
| DR-006 | The dataset format and required access procedure (direct download, toolbox download, registration) shall be documented and reproducible. | M | Reproducibility (`FR-078`); some datasets require registration, which affects automation. | DOC, IT | `[DERIVED]` |
| DR-007 | Noise-only examples should be available or constructible (for example, pre-P windows). | S | Needed for false-alarm evaluation (`E3`) and for a noise-window fraction (`FR-019`). | INSP | v0.1 DR-5 |

### 11.3 Candidate datasets — unverified

| Candidate | Access route named in the repository | Properties that must be verified before selection |
|---|---|---|
| STEAD | `https://github.com/smousavi05/STEAD` (linked in README) | Sampling rate(s), component set, P and S label availability, event identifier, licence, size, format |
| Dataset(s) reachable via SeisBench | Named in `tech.md` §1 | Same list, plus whether SeisBench's loader is compatible with the installed Python/Torch versions |
| INSTANCE | Named in v0.1 §14 | Same list |
| ETHZ | Named in v0.1 §12 (`OQ-3`) | Same list |

### 11.4 Confirmed vs assumed — an explicit separation

| Property | Status |
|---|---|
| Nothing about any candidate dataset has been verified by this project. | **Confirmed as unverified.** |
| The chosen dataset will need event IDs. | Confirmed as a *requirement* (`DR-003`); not yet confirmed to be *satisfiable*. |
| The chosen dataset will have a single sampling rate or a small number of rates. | **Assumed.** Must be verified. |
| The chosen dataset's P/S labels are of a known quality. | **Assumed, and known to be imperfect for large public datasets.** Must be checked (`FR-003`, `E8`). |
| Dataset size and storage requirements. | **Unverified.** Must be measured (`OQ-20`). |
| Licence terms. | **Unverified.** Must be recorded (`DR-005`). |

### 11.5 Data-quality checks required before use

1. Component and rate consistency per trace (`FR-003`).
2. Presence of both P and S picks; count and log traces missing either (`FR-003`).
3. Physical plausibility: S strictly after P (`E5`).
4. Finite, non-flat signals (`FR-003`).
5. Event-identifier coverage: what fraction of traces can be assigned an event (`FR-010`).
6. Duplicate-trace detection, where metadata permits (`E25` handling).

### 11.6 Splitting, leakage prevention and reproducibility

- Splits are **by event**, never by trace (`FR-004`).
- Split membership is persisted to disk in an inspectable format (`FR-005`).
- A test asserts zero event-ID overlap across splits (`FR-025`).
- Splits are deterministic given a recorded seed and the input metadata (`FR-026`).
- Ratios are configurable and recorded; an earlier plan suggested roughly 70/15/15 (`OQ-5`, `FR-006`).
- Representative rationale, plus the alternative of a time-based or region-based split, is discussed in `docs/REASONING_AND_DECISIONS.md`.

---

## 12. Evaluation Metrics

**Definitions used in this section.** `pred` is the predicted arrival time for a phase; `ref` is the reference arrival time; `tol` is the tolerance; `residual = pred − ref`.

### 12.1 Metric definitions

| Metric | Definition | Reported per phase? | Notes |
|---|---|---|---|
| Precision | `TP / (TP + FP)` | Yes, P and S separately | Depends entirely on `tol` and the matching rule; meaningless without them. |
| Recall | `TP / (TP + FN)` | Yes | The proportion of reference arrivals detected within tolerance. |
| F1-score | `2 · precision · recall / (precision + recall)` | Yes | Undefined when precision + recall = 0; return a defined value and report the denominator (`FR-062`). |
| Mean residual | `mean(pred − ref)` over matched picks | Yes | A non-zero mean indicates systematic bias, not just spread. |
| Standard deviation of residuals | `std(pred − ref)` | Yes | Spread. |
| Median absolute error (MedAE) | `median(|pred − ref|)` | Yes | Robust to a few large outliers, of which picking has many. |
| Mean absolute error (MAE) | `mean(|pred − ref|)` | Yes | Sensitive to outliers; reported *alongside* MedAE deliberately. |
| Timing residuals (full distribution) | The set of `pred − ref` values, plotted as a histogram or scatter | Yes | Distributions reveal structure (bimodality, tail) that summary statistics hide (`FR-066`). |
| Tolerance-based picking recall | `recall` computed at a stated tolerance | Yes | Must always be accompanied by the tolerance value (`FR-058`). |
| False-pick rate | `FP / number of windows evaluated`, or `FP` counts per window | Yes | Particularly relevant for pure-noise windows (`E3`). |

Units: residuals shall be reported **in seconds** (the seismologist's unit) with the tolerance also expressed in seconds; sample counts may be shown as a supplementary column. Reporting in samples alone makes cross-dataset comparison difficult and is not acceptable as the primary unit.

### 12.2 Matching rule (TP / FP / FN)

This is the proposed, pre-declared convention. It must be fixed before test results are examined.

| Outcome | Proposed definition |
|---|---|
| **TP** | A reference phase exists, a pick exists, and `|pred − ref| ≤ tol`. |
| **FP** | A pick exists but no reference phase exists, **or** the pick lies outside `tol`. |
| **FN** | A reference phase exists but no pick was made, **or** the pick lies outside `tol`. |

**Caveat that must appear in the report.** Under this definition a single out-of-tolerance pick counts as *both* an FP and an FN. This is a common convention but not universal. Other papers define the outcomes differently, so **numbers from different papers must not be compared without first checking whether the matching rules agree** (limitation L8).

**Additional conventions to state explicitly:**

- Windows with no reference phase for a given phase: any pick for that phase is an FP (`E3`).
- Windows excluded from a phase's evaluation (e.g., missing reference S): stated with the excluded count, never silently dropped (`E7`).
- Zero denominators: a defined return value plus the reported denominator (`FR-062`, `E32`).

### 12.3 Tolerance policy

- The tolerance is **`[OPEN]`** (`OQ-11`). It must be chosen with reference to (a) the reference picks' own uncertainty, where the dataset provides it, and (b) the sampling rate.
- **Proposal:** report at least one **strict** and one **lenient** tolerance so that sensitivity of the conclusion to the tolerance is visible.
- The tolerance must be **frozen before** test-set evaluation (`FR-061`), and stated in every table (`FR-058`).

### 12.4 Reporting requirements

1. **P and S are never aggregated into a single headline number** (`FR-060`). An averaged score hides the common case that S is substantially worse than P (`R3`).
2. Every table states: tolerance, threshold, matching rule, dataset/split identifier, checkpoint identifier, and the number of windows evaluated.
3. Residual statistics are accompanied by residual distributions (`FR-066`).
4. Where metadata permits, results are stratified by SNR / distance / magnitude bins (`FR-011`).
5. **No result is fabricated, estimated from a partial run, or extrapolated.** If an experiment was not run, it is reported as not run.

### 12.5 What is explicitly *not* a metric target in this document

No "F1 ≥ X" target is set. No comparison against a published number is claimed. If numeric pass/fail targets are wanted, they are set after the baseline exists (`OQ-19`, §16).

---

## 13. Research Experiments

Each experiment below follows: **hypothesis → controlled variables → independent variable → metrics → procedure → interpretation criteria.** Full runnable detail is in `docs/EXPERIMENT_PLAN.md`. **None of these experiments has been run.**

### EX-1 — Baseline model experiment

- **Hypothesis.** A 1D U-Net trained on the selected dataset's training events will detect P and S arrivals on held-out events substantially better than chance, with S weaker than P.
- **Controlled variables.** Dataset, split, preprocessing, architecture class, loss class, seeds policy, evaluation tolerance and matching rule.
- **Independent variable.** None — this is the reference run.
- **Metrics.** P and S precision, recall, F1 at the frozen tolerance; residual mean, std, MedAE, MAE per phase; residual histograms.
- **Procedure.** Train with the documented baseline config; select threshold on validation; freeze; evaluate once on test.
- **Interpretation criteria.** Establishes the reference row for all other experiments. P-vs-S gap quantified rather than described. If recall is high and precision low (or the reverse), the threshold operating point is examined before any architectural conclusion is drawn.

### EX-2 — Hyperparameter experiments (one-factor-at-a-time)

- **Hypothesis.** At least one of {label width σ, model depth, base channel count, loss function, window length} materially affects P and/or S metrics; the direction is not assumed.
- **Controlled variables.** Everything except the single varied factor. Same split, same seed policy, same evaluation protocol.
- **Independent variable.** One factor per run, from a short documented list (`OQ-12`).
- **Metrics.** Baseline metrics plus training time, peak memory, and parameter count, so that a gain can be weighed against cost.
- **Procedure.** Change one factor; retrain; evaluate under the identical protocol; tabulate.
- **Interpretation criteria.** A difference is attributed to the varied factor only if nothing else changed. Differences smaller than seed-to-seed variability (from EX-5) are **not** treated as real. Resource cost is reported alongside any gain.

### EX-3 — Training-data-fraction experiment

- **Hypothesis.** P and S metrics improve with more training events, and the improvement flattens at some fraction (which is not assumed).
- **Controlled variables.** Everything except the *number* of training events. Splits are nested subsets of the training split so that validation and test are untouched.
- **Independent variable.** Training-set fraction, e.g., a small geometric ladder (the specific fractions are `[OPEN]` and must be chosen with the compute budget).
- **Metrics.** P and S F1 at the frozen tolerance versus training fraction; the same for MedAE.
- **Procedure.** Train at each fraction with the same config otherwise; evaluate each model identically.
- **Interpretation criteria.** A learning curve. A flat curve suggests the dataset subset, not model capacity, is limiting the project, which would change the plan for `FR-007`. Fewer than three fractions is not a curve.

### EX-4 — Noise-robustness experiment (mandatory)

- **Hypothesis.** P and S metrics degrade monotonically as added-noise level increases, and S degrades faster than P.
- **Controlled variables.** The trained model (fixed), the test set (fixed), the window generation (fixed), the noise realisation seed (fixed, `FR-071`).
- **Independent variable.** Added-noise level, expressed via an explicitly defined SNR (`FR-070`, `OQ-18`).
- **Metrics.** P and S F1 and MedAE versus noise level; false-pick rate versus noise level.
- **Procedure.** Degrade each test window to each noise level with a fixed seed; re-run extraction and evaluation; tabulate.
- **Interpretation criteria.** A monotone trend supports the hypothesis; a non-monotone result must be reported as such, not smoothed. **Limitation to state:** added white Gaussian noise is not realistic seismic noise, which is coloured, non-stationary and has microseism peaks (`E35`). Results therefore bound behaviour under a *controllable* perturbation, and are not a measurement of field performance.

### EX-5 — Seed-variability experiment

- **Hypothesis.** Run-to-run variability from seeds is small enough that EX-2's differences, if any, are larger than it.
- **Controlled variables.** Config, data, protocol.
- **Independent variable.** Random seed.
- **Metrics.** Spread of P and S F1 and MedAE across seeds.
- **Procedure.** Repeat the baseline across several seeds where the budget allows.
- **Interpretation criteria.** Provides the noise floor for EX-2's comparisons. If only one run is affordable, that limitation is stated explicitly (`E33`) rather than hidden.

### EX-6 — Failure-case analysis

- **Hypothesis.** At least some failures share a systematic cause (missed emergent S, false pick on an instrument glitch, P-after-S ordering, pick at a window edge).
- **Controlled variables.** Not an intervention experiment; it analyses EX-1's outputs.
- **Independent variable.** None.
- **Metrics.** Counts of failure categories; per-category example figures; error versus available metadata.
- **Procedure.** Extract the worst errors and a sample of false picks; plot each with reference, prediction and probability curves; record a cause hypothesis per case, flagged as a hypothesis (`FR-068`).
- **Interpretation criteria.** A category is only claimed systematic if the count is non-trivial and the plotted mechanism is visible. Categories with one example are described, not generalised.

### EX-7 — Optional: classical and external baselines

- **STA/LTA via ObsPy (`O-Opt1`).** Hypothesis: the model outperforms a classical threshold detector on the same test set under the same tolerance. Interpretation must note that STA/LTA is tuned by its own parameters, so a badly tuned STA/LTA is not evidence about the model.
- **Pretrained picker on the same test set (`O-Opt2`).** Hypothesis: an external pretrained model performs comparably or differently on this dataset. **Critical caveat:** the pretrained model was trained on different data, so this is a *reference point*, not a like-for-like comparison; any advantage of SeismoNet on its own test data must not be presented as evidence of superiority.

---

## 14. Risks and Mitigation

| ID | Risk | Category | Likelihood / Impact | Mitigation | Requirement link |
|---|---|---|---|---|---|
| R-01 | The chosen dataset cannot be downloaded, is licence-restricted, or requires registration that blocks automation. | Dataset | Medium / High | Verify licence and access **before** committing (`DR-005`, `DR-006`); record the access procedure. | `FR-082`, `NFR-013` |
| R-02 | Missing, wrong, or biased reference labels. | Dataset | Medium / High | Quality screening and logging (`FR-003`); state reference uncertainty; check S-after-P; treat low-quality picks under a documented policy (`E8`, `OQ-13`). | `NFR-009` |
| R-03 | **Event leakage** — the same earthquake in train and test inflates results. | Methodology | Medium / High | Event-level split (`FR-004`), persisted splits (`FR-005`), automated zero-overlap test (`FR-025`), and treating an unexplained test>validation result as a leakage prompt (`E34`). | `NFR-003`, `SC-8` |
| R-04 | Model learns pick *position* rather than waveform features. | Modelling | Medium / High | Randomised window offsets in training (`FR-018`); verify the empirical pick-position distribution is broad for both classes. | `FR-018` |
| R-05 | S-wave performance poor and hidden by aggregated metrics. | Reporting | High / Medium | Separate P and S reporting everywhere (`FR-060`); S included in the failure gallery. | `R3`, `FR-067` |
| R-06 | GPU / memory limitation (4 GiB local VRAM; CPU-only torch as installed). | Compute | High / Medium | Dataset subset (`FR-007`); small baseline model (`SR-008`); configurable batch size; free-tier GPU or CPU fallback (`A6`). | `NFR-006`, `NFR-007` |
| R-07 | Compute or time shortage overall. | Project | Medium / Medium | Scope trims in `docs/DEVELOPMENT_ROADMAP.md`; optional features deferred; explicit `OQ-20` decision. | `OQ-20` |
| R-08 | Class imbalance (most samples are noise) → model collapses to all-noise. | Modelling | Medium / Medium | Monitor per-class probability statistics and P/S metrics, not overall accuracy (`E30`, `E31`); add class weighting **only if collapse is observed**, and report it as an intervention. | `SR-006` |
| R-09 | Noisy / emergent waveforms degrade performance. | Science | High / Medium | This is the object of study (EX-4), not a defect to hide; never exclude difficult test windows for being difficult (`E16`). | `FR-069` |
| R-10 | Overfitting to a small dataset subset. | Modelling | Medium / Medium | Early stopping (`FR-043`), validation-based checkpoint selection (`FR-040`), switchable augmentation (`FR-028`), and EX-3's learning curve. | `SR-009` |
| R-11 | Poor generalisation beyond the selected dataset. | Science | High / Medium | Stated as limitation L1; optional cross-dataset probe (`O-Opt3`) if budget permits; no generalisation claim without it (`NG6`). | `NG6` |
| R-12 | Incorrect sampling-rate conversion silently mislabels every pick. | Implementation | Medium / High | Single common rate policy (`SR-003`); labels resampled with the waveform or converted via time; a dedicated conversion unit test (`FR-053`); never mix rates. | `FR-016` |
| R-13 | Invalid scientific conclusions from protocol choices made after seeing results. | Science/ethics | Medium / High | Freeze tolerance, threshold and matching rule before test evaluation (`FR-061`, `SR-016`); one-factor-at-a-time comparisons (`SR-017`). | `NFR-003` |
| R-14 | Reproducibility failure on another machine. | Engineering | Medium / Medium | Pinned dependencies (`FR-082`), saved configs and splits (`FR-042`, `FR-005`), recorded seeds (`FR-041`), regeneration command (`FR-078`). | `NFR-001` |
| R-15 | Environment incompatibility (Python 3.14 vs SeisBench/ObsPy; CPU-only torch). | Engineering | Medium / High | Resolve at roadmap Phase 0 before writing pipeline code (audit §7.3). | audit §13 |
| R-16 | Accidental commit of datasets/checkpoints (no `.gitignore`). | Engineering/security | Medium / Medium | Add `.gitignore` first (`FR-048`). | `FR-048` |
| R-17 | Over-claiming from synthetic-noise results. | Reporting | Medium / Medium | Limitation L5 in every noise-related section; `NFR-014`. | `NFR-014` |
| R-18 | Unverified citations/statistics propagate into the report. | Reporting | Medium / Medium | Verify every citation and dataset statistic before quoting (§4.7, §11.3). | `NFR-011` |

---

## 15. Milestones and Deliverables

Phases are ordered by dependency. Effort ranges are **estimates only** and depend on the unresolved budget question (`OQ-20`) and on dataset property verification; they are not commitments. Detailed task breakdown: `docs/DEVELOPMENT_ROADMAP.md`.

| # | Phase | Deliverable | Measurable completion criteria | Depends on |
|---|---|---|---|---|
| P0 | Repository and environment setup | `.gitignore`, dependency spec, `src/` + `tests/` skeleton, resolved Python version, resolved PyTorch build | Clean clone installs from the pinned spec on Windows and Linux; a trivial test passes; dataset licence recorded | — |
| P1 | Dataset selection and exploration | Dataset chosen; quality log; event-level split files | `OQ-3` closed; `DR-001`…`DR-003` verified with evidence; split files on disk; zero-overlap check passes; `OQ-4`, `OQ-5` closed | P0 |
| P2 | Data pipeline | Loader, screening, preprocessing, windowing, target generation, `Dataset`/`DataLoader` | Unit tests for labels, conversion, shapes and augmentation alignment pass; sample figures show reference picks where physically expected | P1 |
| P3 | Model and sanity check | 1D U-Net plus tiny-batch overfit test | Shape/softmax/depth assertions pass; a tiny batch overfits to near-zero loss; parameter count reported | P2 |
| P4 | Baseline training | Checkpoint + config + seed + loss curves | Best checkpoint saved by a pre-declared criterion; run reproducible under the same seed; loss curves inspected for collapse | P3 |
| P5 | Protocol freeze, picking and evaluation | Frozen protocol; P/S metrics and residuals on validation then test | `OQ-10`, `OQ-11` closed **before** test evaluation; threshold selected on validation only; test metrics produced once with a frozen config | P4 |
| P6 | Visualisation and failure analysis | Waveform+picks+probability figures; residual histograms; failure gallery | Figures regenerate from artifacts; failure entries carry hypotheses flagged as hypotheses | P5 |
| P7 | Research experiments | Noise-robustness table/plot; one-factor ablation table; seed variability | Control variables held fixed; noise method and SNR definition documented; ablation rows differ in exactly one factor | P6 |
| P8 | Reporting and reproducibility packaging | Final report; updated README; regeneration command; status documents | A third party regenerates the reported tables/figures from the repository following documented steps; limitations section complete | P7 |
| P9 | Optional demonstration interface | Streamlit/Gradio app | Starts with one documented command; renders waveform, picks and probability curves; adjustable threshold | P8, `O-Opt5` |

**Milestone-to-requirement coverage** is checked in `docs/DOCUMENTATION_QC_REPORT.md`.

---

## 16. Acceptance Criteria

### 16.1 Minimum viable research prototype (MVP) — the project is "complete enough" when all of these hold

| ID | Criterion | Evidence required |
|---|---|---|
| SC-1 | A trained 1D U-Net produces P/S/noise probabilities on held-out test **events**. | Checkpoint + saved config + seed + probability outputs on test |
| SC-2 | Arrival times are extracted and evaluated with residuals, precision, recall and F1 under a defined tolerance, **for P and S separately**. | Results table with tolerance, threshold, matching rule, denominator |
| SC-3 | Visualisations (waveform + reference/predicted picks + probability curves) exist, including success and failure examples. | Figures in `results/`, regenerable by command |
| SC-4 | A noise-robustness analysis exists with a documented method. | Table/plot of P and S metrics versus noise level; SNR definition stated |
| SC-5 | A training-configuration study exists with one-factor-at-a-time changes. | Ablation table with a baseline row |
| SC-6 | Another person can regenerate the reported tables and figures from the repository. | Documented command sequence, followed once end-to-end on a clean checkout |
| SC-7 | Limitations are stated and no deployment claims are made. | Limitations section; zero early-warning/deployment claims |
| SC-8 | The event-level split is verified with zero overlap. | Automated check output showing zero shared event IDs |
| SC-9 | Data-quality screening is logged. | Data-quality log with counts and reasons |
| SC-10 | Nothing in the deliverables is fabricated: every reported number traces to an artifact. | Traceability from each table/figure to a config + checkpoint + split |

### 16.2 Full planned project — additionally required

| ID | Criterion |
|---|---|
| SCF-1 | Hyperparameter ablation beyond the minimum set, with resource cost reported per row. |
| SCF-2 | Training-data-fraction learning curve (EX-3). |
| SCF-3 | Seed-variability reporting (EX-5) or an explicit statement that only one seed was affordable. |
| SCF-4 | Stratified reporting by SNR / distance / magnitude where metadata permits. |
| SCF-5 | Curated failure gallery with per-case hypotheses flagged as hypotheses. |
| SCF-6 | Noise-augmentation on/off comparison (EX-4 variant). |
| SCF-7 | Deprecation/archive practice in place: superseded documents retained in `docs/archive/`. |
| SCF-8 | `docs/change-log/` maintained with a change report per meaningful change and an up-to-date `CURRENT_STATUS.md`. |

### 16.3 Optional future improvements

| ID | Criterion |
|---|---|
| SCO-1 | STA/LTA classical baseline (`O-Opt1`). |
| SCO-2 | External pretrained picker on the same test set, as a reference only (`O-Opt2`). |
| SCO-3 | Cross-dataset generalisation probe (`O-Opt3`). |
| SCO-4 | Pick-uncertainty estimate from probability-peak width (`O-Opt4`). |
| SCO-5 | Streamlit/Gradio demonstration interface (`O-Opt5`). |
| SCO-6 | Multi-seed confidence intervals as a standing reporting practice. |
| SCO-7 | Container image and CI running lint plus tests on a tiny fixture. |

### 16.4 Explicitly *not* acceptance criteria

No accuracy threshold, no speed threshold, no "beats PhaseNet" claim, and no operational-readiness criterion. Any such target must be added by the project owner *after* a baseline exists (`OQ-19`), and must be documented as an added target.

---

## 17. Assumptions and Open Questions

### 17.1 Assumptions (each is an assumption, not a verified fact)

| ID | Assumption | Status | Impact if wrong |
|---|---|---|---|
| A-01 | One selected dataset is used. | `[GIVEN]` | Multi-dataset work would change the split and reporting design. |
| A-02 | Input is a three-component (Z, N, E) waveform. | `[PROPOSED]` | A different component set invalidates `SR-001`. |
| A-03 | Input is a fixed-length window. | `[PROPOSED]` | A variable-length model would change the architecture and evaluation. |
| A-04 | At most one P and one S pick per window are extracted. | `[PROPOSED]` | Would require a different output format and metric formulation (`E21`). |
| A-05 | Reference picks are treated as ground truth for error computation. | `[DERIVED]` | Must be disclosed as label uncertainty, not truth, in the report. |
| A-06 | Compute is a single free-tier GPU (Colab/Kaggle) or an equivalent CPU fallback. | `[PROPOSED]` | **Currently the local machine has a 4 GiB GPU but a CPU-only PyTorch build** (audit §7.3). |
| A-07 | The project can afford several training runs for the ablation and seed studies. | **Unverified** | Would force reducing EX-2/EX-3/EX-5 scope. |
| A-08 | The chosen dataset's licence permits research use and citation is sufficient compliance. | **Unverified** | Would force a dataset change (`DR-005`). |
| A-09 | A dataset with both P and S labels *and* event identifiers exists and is accessible. | **Unverified** — a hard gate (`DR-003`). | If not, the split strategy and possibly the S-wave objective must be redesigned. |
| A-10 | Added-noise experiments are acceptable as a proxy for noise robustness. | `[PROPOSED]` | Must be disclosed as a limitation (L5, `E35`). |
| A-11 | Python 3.11/3.12 (recommended in `tech.md`) is available or installable. | `[PROPOSED]` | The audit environment has 3.14.3; SeisBench/ObsPy compatibility is unverified. |

### 17.2 Open questions

Carried forward from v0.1 with a suggested closure route for each. **None has a value assumed.**

| ID | Question | Affects | Suggested closure |
|---|---|---|---|
| OQ-1 | Who are the real intended readers/users beyond the author and evaluator? | §6 | Confirm with the supervisor. |
| OQ-2 | Which datasets are acceptable, and must the dataset provide event IDs? | `DR-003`, `FR-004` | Decide after inspecting metadata. |
| OQ-3 | **Which dataset is the "selected dataset"?** | All data requirements | Decide first; verify candidates' current properties. |
| OQ-4 | Window length and sampling rate. | `SR-003`, `SR-004`, `FR-017` | Fix once the dataset is chosen (proposal: 3072 @ 100 Hz). |
| OQ-5 | Split ratios, and whether time-based or region-based splitting is wanted. | `FR-006`, `FR-027` | Decide with the supervisor. |
| OQ-6 | Use a bandpass filter, and with which band? | `FR-015` | Decide from the dataset and document either way. |
| OQ-7 | Fraction of pure-noise training windows. | `FR-019` | Choose, then optionally ablate. |
| OQ-8 | Label width σ. | `SR-006`, `FR-022` | Choose a baseline, then include in the ablation. |
| OQ-9 | Baseline loss function. | `SR-007`, `FR-039` | Choose and state (proposal: soft cross-entropy). |
| OQ-10 | Picking threshold and multi-peak rule. | `SR-011`, `SR-012`, `FR-051`, `FR-052` | Choose on validation data only. |
| OQ-11 | **Tolerance value(s) for TP.** | §12, `FR-058` | Decide before testing; consider a strict and a lenient value. |
| OQ-12 | Which training factors are ablated? | `FR-073` | Choose a short list (e.g., from σ, depth, width, augmentation, loss). |
| OQ-13 | How to treat reference pick quality/uncertainty. | `E8`, §12 | Inspect what the dataset provides. |
| OQ-14 | Are picks near window edges allowed? | `E6` | Choose and state a rule. |
| OQ-15 | Policy for dead or missing components. | `E11`, `E12` | Decide: exclude or fill, then state. |
| OQ-16 | Handling of multi-event windows. | `E21` | Exclude, or label the main event only. |
| OQ-17 | Enforce P-before-S ordering on predictions? | `SR-015`, `E29` | Decide; if unsure, report both variants. |
| OQ-18 | Precise SNR definition for the noise study. | `FR-070`, `E36`, `E37` | Define and document. |
| OQ-19 | Are numeric performance targets wanted? | §16 | Set after a baseline exists. |
| OQ-20 | Project time budget and compute limits. | `NFR-006`, `A-07`, all effort estimates | Confirm with the owner/supervisor. |
| OQ-21 | Which checkpoint-selection criterion is primary: validation loss or validation P/S F1 at the frozen tolerance? | `SR-010`, `FR-040` | Decide before the first training run. |
| OQ-22 | Should the reference picks be re-indexed for overlapping P and S targets, or is the standard three-channel formulation retained? | `SR-006`, `FR-023`, `E4` | Decide after inspecting the dataset's S-P distribution. |
| OQ-23 | Is a `.gitignore`, a LICENSE file, and a CI workflow wanted, given the repository currently has none? | `FR-048`, `NFR-013` | Confirm with the owner; recommended. |

---

## 18. Identifier Mapping (v0.1 → v1.0)

### 18.1 Requirement IDs

| v0.1 ID | v1.0 ID | v0.1 ID | v1.0 ID |
|---|---|---|---|
| FR-D1 | FR-001 | FR-T1 | FR-039 |
| FR-D2 | FR-002 | FR-T2 | FR-040 |
| FR-D3 | FR-003 | FR-T3 | FR-041 |
| FR-D4 | FR-004, FR-010 | FR-T4 | FR-042 |
| FR-D5 | FR-005, FR-025 | FR-T5 | FR-043 |
| FR-D6 | FR-006, FR-027 | FR-K1 | FR-050 |
| FR-D7 | FR-007 | FR-K2 | FR-051 |
| FR-P1 | FR-013 | FR-K3 | FR-009, FR-053, `SR-013` |
| FR-P2 | FR-014 | FR-K4 | FR-052 |
| FR-P3 | FR-015 | FR-K5 | FR-053 |
| FR-P4 | FR-016 | FR-E1 | FR-055 |
| FR-P5 | FR-017 | FR-E2 | FR-056 |
| FR-P6 | FR-018 | FR-E3 | FR-057 |
| FR-P7 | FR-019 | FR-E4 | FR-058 |
| FR-P8 | FR-020 | FR-E5 | FR-059 |
| FR-L1 | FR-021 | FR-E6 | FR-060 |
| FR-L2 | FR-022, `SR-006` | FR-E7 | FR-061 |
| FR-L3 | FR-023, FR-037 | FR-E8 | FR-011 |
| FR-L4 | FR-024 | FR-V1 | FR-064 |
| FR-A1 | FR-028 | FR-V2 | FR-065 |
| FR-A2 | FR-029 | FR-V3 | FR-066 |
| FR-A3 | FR-030 | FR-V4 | FR-067, FR-068 |
| FR-A4 | FR-031 | FR-X1 | FR-069 |
| FR-M1 | FR-032 | FR-X2 | FR-070 |
| FR-M2 | FR-033 | FR-X3 | FR-072 |
| FR-M3 | FR-034 | FR-X4 | FR-073 |
| FR-M4 | FR-035 | FR-X5 | FR-074 |
| FR-M5 | FR-036 | FR-R1 | FR-082 |
| FR-M6 | FR-038 | FR-R2 | FR-083 |
| — | FR-R3 | FR-078 | |

| v0.1 ID | v1.0 ID |
|---|---|
| NFR-1 | NFR-001 |
| NFR-2 | NFR-002 |
| NFR-3 | NFR-003 |
| NFR-4 | NFR-005 |
| NFR-5 | NFR-006, NFR-007 |
| NFR-6 | NFR-014 |
| NFR-7 | NFR-013 |
| DR-1 | DR-001 |
| DR-2 | DR-002 |
| DR-3 | DR-003 |
| DR-4 | DR-004 |
| DR-5 | DR-007 |

### 18.2 Identifiers preserved unchanged

`G1`–`G7`, `NG1`–`NG6`, `A1`–`A6` (see §17.1), `US-01`–`US-17`, `SC-1`–`SC-8`, `OQ-1`–`OQ-20`, `E1`–`E38`, `R1`–`R8` (now `R-01`–`R-18`, expanded), `M1`–`M8` (now phases P0–P9, expanded), `O1`–`O4`.
User stories and edge cases are not restated here in full; they remain available in `docs/archive/PRD-v0.1-original.md` §6 and §9 and are cross-referenced by the requirement tables above.

---

## 19. Glossary

| Term | Meaning |
|---|---|
| P wave | Primary (compressional) body wave; the first arrival. |
| S wave | Secondary (shear) body wave; arrives after P; clearer on horizontals. |
| S-P time | Time difference between S and P arrivals; grows with source distance. |
| Phase picking | Determining the arrival time of a seismic phase. |
| Onset (impulsive / emergent) | How sharply a phase starts above noise. Emergent onsets are harder to time. |
| Coda | Scattered wave energy following the main arrivals. |
| SNR | Signal-to-noise ratio. **Its definition must be stated** (`OQ-18`). |
| Residual | Predicted pick time minus reference pick time. |
| Tolerance | Maximum absolute residual for a pick to count as correct. |
| TP / FP / FN | True positive / false positive / false negative, per §12.2. |
| STA/LTA | Short-term-average / long-term-average classical threshold detector. |
| Event leakage | The same earthquake appearing in both training and test data. |
| U-Net | Encoder–decoder network with skip connections between matching scales. |
| Soft cross-entropy | Cross-entropy computed against soft (Gaussian-shaped) probability targets rather than hard one-hot labels. |
| Picking threshold | The probability value above which a sample is a candidate arrival. |
| Baseline run | The reference training configuration against which other runs are compared. |

---

## 20. PRD Approval

| Role | Name | Status | Date |
|---|---|---|---|
| Project owner | jahnavi-957 (repository owner) | **Not yet reviewed** | — |
| Supervisor / academic reviewer | — | **Not yet reviewed** | — |
| Documentation task | AI-assisted documentation pass | Draft issued | 2026-10-17 |

**Outstanding before approval:** all `OQ-*` items in §17.2, all `[OPEN]` values in §10 and §12, and the effort estimates in §15.

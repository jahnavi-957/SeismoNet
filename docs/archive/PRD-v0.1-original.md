# SeismoNet: Product Requirements Document (PRD)

**Project:** SeismoNet, Deep Learning-Based Seismic Phase Detection
**Document type:** PRD for a research mini project (not a production system)
**Version:** 0.1 (draft)
**Perspective:** Written from the viewpoint of a seismologist / earthquake researcher

---

## 0. How to read this document

**Method note.** This PRD was prepared from background domain knowledge (seismology, phase picking literature, SeisBench and public benchmark datasets). No live literature search or database lookup was performed. Dataset statistics and citations in Sections 14 and 15 must be verified against the original sources before they are quoted in a report.

**"Do not invent unclear requirements" policy.** Every item in this document falls into exactly one of three categories, and is labelled accordingly:

| Label | Meaning |
|---|---|
| **[GIVEN]** | Stated in the original problem statement. |
| **[DERIVED]** | Follows directly from a [GIVEN] item or from established seismological practice. |
| **[PROPOSED]** | A default I chose so work can start. It is changeable and is not a stakeholder requirement. |
| **[OPEN]** | Genuinely undecided. Listed in Section 12 with an owner. No value is assumed. |

Where a numeric target (e.g., "F1 ≥ X") would normally appear, this PRD deliberately does **not** invent one. Performance targets are set *after* a baseline exists (see Section 11).

---

## 1. Executive summary

SeismoNet is a reproducible deep learning pipeline that detects **P-wave** and **S-wave** arrival times in three-component seismic waveforms. It uses a one-dimensional U-Net inspired by PhaseNet **[GIVEN]**. For every time sample, the model outputs the probability of P arrival, S arrival, or noise **[GIVEN]**. Arrival times are extracted from these probability curves and compared against labelled reference picks using arrival-time residuals, precision, recall and F1 under an explicit tolerance **[GIVEN]**. The project also studies how waveform noise and selected training configurations affect performance **[GIVEN]**.

The stated goal is to **demonstrate a reproducible pipeline and assess its effectiveness on a selected dataset**, not to claim deployment-ready earthquake monitoring **[GIVEN]**.

---

## 2. Problem

### 2.1 Domain background (seismologist's view)

When an earthquake occurs, energy radiates as seismic waves. Two body-wave types matter most for location:

- **P wave (primary, compressional):** the fastest wave, arrives first. Particle motion is along the propagation direction, so it is strongest on the **vertical** component for steeply incident rays.
- **S wave (secondary, shear):** slower, arrives later, typically with larger amplitude. Particle motion is transverse to propagation, so it is usually clearer on the **horizontal** components. S waves do not travel through liquids.

The time difference **S minus P** grows with source-station distance. A common crustal rule of thumb is roughly 8 km of distance per second of S-P time. It is only approximate and depends on local velocity structure. This is why accurate P and S arrival times from several stations are the raw input to **earthquake location**, origin time estimation, and subsequent magnitude, focal mechanism and tomography work.

In practice, "arrival time" is not an exact physical instant. It is an **analyst's judgement** of where a phase onset is visible above noise.

### 2.2 The problem being addressed

| # | Problem | Why it matters |
|---|---|---|
| P1 | Manual picking by trained analysts is slow. | Modern networks record continuously. Seismicity catalogues grow far faster than analysts can review. |
| P2 | Manual picks are subjective. | Different analysts, or the same analyst on different days, choose different onsets. This is especially true for **emergent** onsets and for **S waves**, which arrive inside the P coda. |
| P3 | Classical automatic pickers are sensitive to noise. | STA/LTA-type detectors are threshold-based and degrade at low signal-to-noise ratio (SNR). They also tend to fit S waves poorly. |
| P4 | Deep learning pickers exist but their behaviour on a *given* dataset is not obvious. | Reported performance depends on dataset, tolerance, matching rule and noise level. A transparent, reproducible evaluation is needed before trusting any number. |

### 2.3 Problem statement for this project

> Given a window of three-component seismic waveform, predict per-sample probabilities of P arrival, S arrival and noise, extract arrival times from them, and quantify, under an explicit and documented tolerance, how closely they match labelled reference picks, including how this changes with waveform noise and training configuration.

### 2.4 Goals

| ID | Goal | Source |
|---|---|---|
| G1 | Build a 1D U-Net that outputs P / S / noise probabilities per time step. | [GIVEN] |
| G2 | Extract arrival times from probability outputs. | [GIVEN] |
| G3 | Evaluate with arrival-time errors, precision, recall and F1 under a clearly defined tolerance. | [GIVEN] |
| G4 | Provide waveform preprocessing, training, evaluation and visualisation as one pipeline. | [GIVEN] |
| G5 | Investigate the effect of waveform noise on performance. | [GIVEN] |
| G6 | Investigate the effect of selected training configurations on performance. | [GIVEN] |
| G7 | Make the pipeline reproducible. | [GIVEN] |

### 2.5 Non-goals

| ID | Non-goal | Reason |
|---|---|---|
| NG1 | Claiming deployment-ready earthquake monitoring or early warning. | [GIVEN] Explicitly excluded. |
| NG2 | Earthquake location, magnitude estimation, focal mechanisms. | Downstream of picking. Not in the problem statement. |
| NG3 | Real-time or low-latency continuous-stream processing. | Not stated. Windowed inference is the scope. |
| NG4 | Multi-station association (linking picks into events). | Not stated. |
| NG5 | Novel architecture research. | The stated approach is "inspired by PhaseNet". |
| NG6 | Global generalisation claims. | A single selected dataset is the stated scope. |

---

## 3. Target users

The problem statement does not name users. The personas below are **[DERIVED]** from the nature of the task. Whether any persona beyond the first two is actually in scope is listed as an open question (OQ-1).

### 3.1 Primary users

**U1: Seismology analyst / earthquake researcher**
- Reviews and builds earthquake catalogues, familiar with P/S identification and pick quality.
- *Needs:* to judge whether the model's picks are physically plausible and how they differ from analyst picks. To see failure cases, not just aggregate scores. To trust that a split did not leak events.
- *Does not need:* to understand deep learning internals.

**U2: ML practitioner / student / project author**
- Building or extending the pipeline, probably the project author.
- *Needs:* clean modular code, config-driven experiments, fixed seeds, a reproducible path from raw data to every figure and table.

### 3.2 Secondary users

**U3: Project evaluator / reviewer / instructor**
- Reads the report and re-runs the pipeline.
- *Needs:* an unambiguous evaluation protocol, honest limitations, and the ability to reproduce the headline table.

**U4: Seismic network operator (indirect)**
- Might later consider such a picker as a reference or baseline.
- *Note:* Because NG1 excludes deployment claims, this persona is **informed by** the results but not a design target.

### 3.3 Out-of-scope users
Early-warning system operators, emergency managers, and members of the public. Nothing here is validated for such use.

---

## 4. Scope and operating assumptions

| ID | Item | Status |
|---|---|---|
| A1 | One selected dataset is used. | [GIVEN] "selected dataset" |
| A2 | Input is three-component waveform (Z, N, E). | [PROPOSED] Standard for PhaseNet-style models. Not specified in the statement. |
| A3 | Input is a fixed-length window. | [PROPOSED] Required by a fixed-size U-Net. Length is [OPEN] (OQ-4). Earlier planning used 3072 samples at 100 Hz. |
| A4 | At most one P and one S pick per window is extracted. | [PROPOSED] Mini-project simplification. Must be stated in the report. Realistic continuous data can contain many events. |
| A5 | The reference picks are treated as ground truth. | [DERIVED] Required to compute errors. The report must note they are analyst-derived and carry their own uncertainty. |
| A6 | Compute is a single free-tier GPU (Colab/Kaggle) or equivalent. | [PROPOSED] Implies using a dataset subset. Not stated by the problem. |

---

## 5. Core features

Each feature maps to goals and to the functional requirements in Section 7.

### F1. Data ingestion and quality screening
Load the selected dataset, expose metadata (sampling rate, pick indices, and where available magnitude, distance, SNR), and flag unusable traces (NaN, flat, missing picks, inconsistent sampling rate).
*Maps to:* G4, G7.

### F2. Event-aware dataset splitting
Split into train / validation / test **by seismic event**, never by trace or by station-recording alone, and persist split membership to disk.
*Why a seismologist insists on this:* one earthquake recorded at 50 stations produces 50 highly correlated traces. Random trace-level splits leak the event across splits and inflate scores.
*Maps to:* G3, G7.

### F3. Waveform preprocessing
Per-trace detrend/demean, optional filtering, amplitude normalisation, resampling to a common rate if needed. Every choice must be documented and configurable.
*Maps to:* G4.

### F4. Windowing and label generation
Cut fixed-length windows around reference picks at **randomised** positions, and generate per-sample target curves for P, S, noise (PhaseNet-style Gaussian-shaped P/S targets; noise = remainder). Include a configurable share of pure-noise windows.
*Maps to:* G1, G4.

### F5. Controlled augmentation (switchable)
Training-time augmentations that can each be turned on or off independently. Noise addition must be separable from other augmentations because noise is a study variable.
*Maps to:* G5, G6.

### F6. 1D U-Net model
Encoder-decoder with skip connections, three-channel output (P, S, noise) per input sample, configurable depth, base channels and kernel size.
*Maps to:* G1, G6.

### F7. Training pipeline
Reproducible training with a probability-aware loss, validation monitoring, checkpointing of the best model, and logged configuration.
*Maps to:* G4, G6, G7.

### F8. Pick extraction
Convert probability curves to discrete arrival times using a documented threshold and peak rule, separately for P and S.
*Maps to:* G2.

### F9. Evaluation
Compute residuals (predicted minus reference, in seconds) and precision / recall / F1 under an explicitly defined tolerance and matching rule, separately for P and S.
*Maps to:* G3.

### F10. Visualisation and failure analysis
Plot waveform + reference picks + predicted picks + probability curves; produce galleries of good and failed cases; relate errors to available metadata (SNR, distance, magnitude).
*Maps to:* G4, G3.

### F11. Noise-robustness study
Evaluate the same trained model on test data degraded to controlled noise levels, and compare against a model trained with different noise augmentation exposure.
*Maps to:* G5.

### F12. Training-configuration study
One-factor-at-a-time variation of selected training settings, reported in one comparable table.
*Maps to:* G6.

### F13. Reproducibility packaging
Fixed seeds, saved configs and splits, pinned dependencies, and a command that regenerates the reported tables and figures.
*Maps to:* G7.

### Optional features (not required by the statement)
Marked [PROPOSED] and clearly separable from the core:

| ID | Optional feature | Value |
|---|---|---|
| O1 | STA/LTA baseline | Gives readers a classical reference point. |
| O2 | Pretrained PhaseNet-type model evaluated on the same test set | Gives an external reference. Note: pretrained models were trained on other data, so this is a reference, not a like-for-like comparison. |
| O3 | Cross-dataset test | Probes generalisation, which NG6 otherwise leaves untested. |
| O4 | Uncertainty from peak width of the probability curve | Seismologists value pick uncertainty. |

---

## 6. User stories

Format: *As a [user], I want [capability], so that [outcome].* Acceptance criteria avoid inventing numeric performance targets.

### Data and preprocessing

**US-01 (U1, U2)**: As a researcher, I want to see summary statistics and example traces with reference picks overlaid, so that I can confirm the labels sit where I physically expect.
*Acceptance:* A notebook/report section shows metadata summaries and ≥1 plotted gallery of traces with P/S lines. Reviewer can visually confirm P precedes S.

**US-02 (U1)**: As a seismologist, I want the split performed by event, so that results are not inflated by the same earthquake appearing in train and test.
*Acceptance:* Saved split files exist. An automated check confirms **zero** event IDs shared across splits.

**US-03 (U2)**: As a developer, I want invalid traces (NaN, flat, missing or inconsistent picks, inconsistent sampling rate) detected and handled by documented rules, so that training does not silently ingest bad data.
*Acceptance:* A data-quality log lists how many traces were excluded and why.

**US-04 (U2)**: As a developer, I want preprocessing steps configurable and recorded, so that every result can be traced to the exact preprocessing used.
*Acceptance:* Config file contains all preprocessing parameters and is saved with each run.

### Modelling and training

**US-05 (U2)**: As a developer, I want a model that maps a three-component window to P/S/noise probabilities of the same length, so that arrival times can be read per sample.
*Acceptance:* Output length equals input length; the three channels sum to 1 per sample after softmax.

**US-06 (U2)**: As a developer, I want to confirm the model can overfit a tiny batch before full training, so that I can rule out pipeline bugs early.
*Acceptance:* Documented overfit test in the repo.

**US-07 (U2)**: As a developer, I want training to be repeatable from a seed and config, so that a reviewer can reproduce a result.
*Acceptance:* Same config + seed reproduces results to within documented hardware non-determinism. The report states what variation remains (GPU non-determinism can exist).

### Evaluation

**US-08 (U1, U3)**: As a reviewer, I want the tolerance, matching rule and picking threshold stated before results are shown, so that I can judge the metrics fairly.
*Acceptance:* An "Evaluation protocol" section defines TP/FP/FN and states how a pick outside tolerance is counted.

**US-09 (U1)**: As a seismologist, I want P and S evaluated separately, so that I can see S-wave weakness, which is common, instead of it being averaged away.
*Acceptance:* All main tables have separate P and S rows/columns.

**US-10 (U1)**: As a seismologist, I want residuals (not just F1) in seconds, with mean, standard deviation, median and MAE, so that I can see bias and spread.
*Acceptance:* Residual statistics and histograms for P and S.

**US-11 (U3)**: As a reviewer, I want the picking threshold selected on the validation set only and then applied once to the test set, so that test performance is not tuned.
*Acceptance:* Report states the threshold-selection procedure; test set is evaluated for final numbers only after selection.

### Visualisation

**US-12 (U1)**: As a seismologist, I want to see waveform, reference picks, predicted picks and probability curves together, so that I can judge whether a pick is physically sensible.
*Acceptance:* A reusable plotting function produces this for any sample index.

**US-13 (U1)**: As a seismologist, I want a curated set of failures (missed S, false pick, large error) with explanations, so that I understand when the model should not be trusted.
*Acceptance:* Failure gallery with a short written cause hypothesis per case, flagged as hypothesis where not verified.

### Experiments

**US-14 (U1, U2)**: As a researcher, I want performance reported against controlled noise level, so that I can see where the model breaks down.
*Acceptance:* Plot/table of P and S metrics vs. noise level, with the noise-generation method described.

**US-15 (U2)**: As a researcher, I want one-factor-at-a-time training ablations in one table, so that effects can be attributed to a single change.
*Acceptance:* Table with baseline row and one changed factor per row.

**US-16 (U3)**: As a reviewer, I want limitations stated plainly, so that results are not over-interpreted.
*Acceptance:* Limitations section includes at minimum the items in Section 13.

### Reproducibility

**US-17 (U3)**: As a reviewer, I want one documented command sequence that regenerates reported tables and figures, so that I can verify the work.
*Acceptance:* README with install and run steps; pinned dependencies.

---

## 7. Requirements

Priority uses MoSCoW: **M** = Must, **S** = Should, **C** = Could. Priorities are [PROPOSED] except where traced to [GIVEN].

### 7.1 Functional requirements

#### Data (FR-D)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-D1 | The system shall load one selected dataset and expose waveform, sampling rate and reference P/S pick indices per trace. | M | [GIVEN] |
| FR-D2 | The system shall report dataset summary statistics (trace count, pick availability, and where available magnitude / distance / SNR distributions). | M | [DERIVED] |
| FR-D3 | The system shall detect and exclude or flag traces with NaN/Inf values, flat (zero-variance) signal, missing reference picks where picks are required, and inconsistent sampling rate. The exclusion count and reason shall be logged. | M | [DERIVED] |
| FR-D4 | The system shall split data into train / validation / test **by event identifier**. | M | [DERIVED] from standard practice, event leakage |
| FR-D5 | The system shall persist split membership to disk and verify no event appears in more than one split. | M | [DERIVED] |
| FR-D6 | Split ratios shall be configurable. | S | [PROPOSED] (earlier plan: ~70/15/15; OQ-5) |
| FR-D7 | The system shall support using a subset of the dataset via a configurable size limit. | S | [PROPOSED] (compute constraint, A6) |

#### Preprocessing (FR-P)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-P1 | The system shall apply per-component detrend and demean. | M | [PROPOSED] standard practice |
| FR-P2 | The system shall apply amplitude normalisation to each window, with the method configurable and recorded. | M | [DERIVED] |
| FR-P3 | The system shall support an optional bandpass filter. If used, corner frequencies shall be configurable and recorded. If not used, that decision shall be documented. | S | [PROPOSED] (OQ-6) |
| FR-P4 | The system shall resample to a common rate when source sampling rates differ. | S | [DERIVED] (only needed if rates differ) |
| FR-P5 | The system shall produce fixed-length windows. | M | [DERIVED] from U-Net input |
| FR-P6 | For training, window start shall be randomised such that reference picks fall at varying positions within the window. | M | [DERIVED] prevents the model learning position rather than waveform |
| FR-P7 | The system shall support a configurable fraction of pure-noise windows (no P or S inside). | S | [PROPOSED] (OQ-7) |
| FR-P8 | Preprocessing applied at evaluation time shall be identical to that at training time, except for training-only augmentation. | M | [DERIVED] |

#### Labels (FR-L)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-L1 | The system shall generate per-sample target curves for P, S and noise with the same length as the input window. | M | [GIVEN] |
| FR-L2 | P and S targets shall be smooth peaked curves centred on the reference pick (PhaseNet-style Gaussian). Width (σ) shall be configurable. | M | [PROPOSED] shape from PhaseNet lineage; σ value is [OPEN] (OQ-8) |
| FR-L3 | The noise target shall be defined so the three targets sum to 1 at every sample. | M | [DERIVED] (softmax output) |
| FR-L4 | If a window contains no S pick (or no P pick), that phase's target shall be all zeros rather than a fabricated pick. | M | [DERIVED] |

#### Augmentation (FR-A)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-A1 | Each augmentation shall be independently switchable through configuration. | M | [DERIVED] required for ablation (G6) |
| FR-A2 | Noise-addition augmentation shall be switchable separately from all other augmentations. | M | [DERIVED] (G5) |
| FR-A3 | Augmentation shall apply to training data only. Validation and test data shall not be augmented, except in the explicit noise-robustness experiment. | M | [DERIVED] |
| FR-A4 | Augmentations shall not change reference pick positions incorrectly (e.g., after shifting, labels must move consistently with the waveform). | M | [DERIVED] |

#### Model (FR-M)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-M1 | The model shall be a one-dimensional U-Net with encoder, decoder and skip connections. | M | [GIVEN] |
| FR-M2 | The model shall accept a three-component window and output three channels (P, S, noise) per time step. | M | [GIVEN] / A2 |
| FR-M3 | Output length shall equal input length. | M | [DERIVED] |
| FR-M4 | Depth, base channel count and kernel size shall be configurable. | M | [DERIVED] (G6) |
| FR-M5 | Window length shall be compatible with the chosen depth (divisible by 2^depth if using stride-2 down/upsampling), and the code shall assert this. | M | [DERIVED] |
| FR-M6 | The model's parameter count shall be reported. | S | [PROPOSED] |

#### Training (FR-T)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-T1 | The system shall train with a loss defined on per-sample probability outputs against the target curves. The exact loss is [OPEN] for the baseline; soft cross-entropy was the earlier plan. | M | [GIVEN]/(OQ-9) |
| FR-T2 | The system shall log training and validation loss per epoch and save the best checkpoint by validation criterion. | M | [DERIVED] |
| FR-T3 | The system shall set and record random seeds for Python, NumPy and PyTorch. | M | [GIVEN] reproducibility |
| FR-T4 | The system shall save the full run configuration alongside each checkpoint. | M | [DERIVED] |
| FR-T5 | The system shall support early stopping. | S | [PROPOSED] |

#### Picking (FR-K)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-K1 | The system shall derive a P arrival time and an S arrival time from the respective probability channel using a threshold and a peak-selection rule. | M | [GIVEN] |
| FR-K2 | Threshold shall be configurable and selected on validation data only. | M | [DERIVED] |
| FR-K3 | The system shall return "no pick" when no peak exceeds threshold. | M | [DERIVED] |
| FR-K4 | Where several peaks exceed threshold, the system shall apply a documented rule to select one (A4). The earlier plan used the highest peak. | M | [PROPOSED] (OQ-10) |
| FR-K5 | Picks shall be converted to seconds using the window's sampling rate. | M | [DERIVED] |

#### Evaluation (FR-E)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-E1 | The system shall compute arrival-time residuals (predicted minus reference) for P and S separately. | M | [GIVEN] |
| FR-E2 | The system shall report residual mean, standard deviation, median and mean absolute error. | M | [PROPOSED] |
| FR-E3 | The system shall compute precision, recall and F1 under at least one clearly defined tolerance. | M | [GIVEN] |
| FR-E4 | The tolerance value(s) shall be configurable and stated in every results table. The tolerance value itself is [OPEN] (OQ-11). Earlier planning suggested reporting a strict and a lenient tolerance. | M | [GIVEN]/(OQ-11) |
| FR-E5 | The matching rule for TP / FP / FN shall be defined in the report, including how a pick outside tolerance is counted. | M | [GIVEN] "clearly defined" |
| FR-E6 | The system shall evaluate P and S separately and shall not report only a combined score. | M | [DERIVED] |
| FR-E7 | Final test results shall be computed only after model selection and threshold selection are complete. | M | [DERIVED] |
| FR-E8 | The system shall support stratified reporting by available metadata (e.g., SNR, distance, magnitude bins), if those fields exist in the dataset. | S | [PROPOSED] |

#### Visualisation (FR-V)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-V1 | The system shall plot, for any sample, the three-component waveform with reference and predicted picks. | M | [GIVEN] |
| FR-V2 | The same plot shall show P/S/noise probability curves and the threshold. | M | [GIVEN] |
| FR-V3 | The system shall produce residual histograms for P and S. | M | [DERIVED] |
| FR-V4 | The system shall produce example galleries of successes and failures. | S | [PROPOSED] |

#### Experiments (FR-X)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-X1 | The system shall evaluate a fixed trained model on a fixed test set under multiple controlled noise levels. | M | [GIVEN] |
| FR-X2 | The noise-generation method and the definition of the noise level (e.g., SNR definition) shall be documented. | M | [DERIVED] |
| FR-X3 | The system shall support comparing models trained with and without noise augmentation. | S | [PROPOSED] |
| FR-X4 | The system shall support one-factor-at-a-time variation of selected training configurations from a baseline. The list of factors is [OPEN] (OQ-12). | M | [GIVEN]/(OQ-12) |
| FR-X5 | Repeated runs with different seeds should be supported so variability can be reported. | S | [PROPOSED] |

#### Reproducibility (FR-R)

| ID | Requirement | Priority | Source |
|---|---|---|---|
| FR-R1 | The repository shall include a dependency specification with pinned versions. | M | [GIVEN] reproducibility |
| FR-R2 | The repository shall include a README with install and run instructions. | M | [DERIVED] |
| FR-R3 | A documented procedure shall regenerate all reported tables and figures from saved checkpoints/configs. | M | [DERIVED] |

### 7.2 Non-functional requirements

| ID | Requirement | Priority | Source |
|---|---|---|---|
| NFR-1 | **Reproducibility:** results shall be reproducible from config + seed + split files. | M | [GIVEN] |
| NFR-2 | **Transparency:** every metric shall be accompanied by its tolerance, threshold and matching rule. | M | [DERIVED] |
| NFR-3 | **No test leakage:** no tuning decision shall use test data. | M | [DERIVED] |
| NFR-4 | **Modularity:** data, model, training, evaluation and experiments shall be separable modules. | S | [PROPOSED] |
| NFR-5 | **Resource feasibility:** the baseline shall be trainable on a single commodity GPU using a dataset subset, within the project's time budget. | S | [PROPOSED] (A6; time budget [OPEN]) |
| NFR-6 | **Honest scope:** documentation shall not claim operational or deployment readiness. | M | [GIVEN] |
| NFR-7 | **Licensing / data use:** the chosen dataset's licence and citation requirements shall be followed. | M | [DERIVED] |

### 7.3 Data requirements

| ID | Requirement |
|---|---|
| DR-1 | The dataset must provide three-component (or the chosen component set) waveforms with a known sampling rate. |
| DR-2 | The dataset must provide reference P pick times; reference S pick times are required for S evaluation. |
| DR-3 | The dataset must provide an event identifier (or enough metadata to construct one) to enable event-wise splitting. If it does not, **dataset choice must be revisited** (see OQ-2). |
| DR-4 | The dataset should provide pick quality / uncertainty and SNR if available, because they enable stratified analysis. These are desirable, not required. |
| DR-5 | Noise-only examples should be available or constructible (e.g., pre-P windows). |

---

## 8. Evaluation protocol (to be fixed before results)

This section records the *structure* of the evaluation. Numeric values marked [OPEN] must be decided and frozen before looking at test results.

**Inputs to the protocol**

| Parameter | Value | Status |
|---|---|---|
| Tolerance(s) | not fixed here | [OPEN] OQ-11 (earlier suggestion: report a strict and a lenient value) |
| Pick threshold | selected on validation | [OPEN] OQ-10 (earlier default candidate: 0.3) |
| Picks per phase per window | at most 1 | [PROPOSED] A4 |
| Handling of windows with no true phase | any pick = FP | [PROPOSED] |

**Matching definitions (proposed)**

| Outcome | Definition |
|---|---|
| TP | A reference phase exists, a pick exists, and |pred − ref| ≤ tolerance. |
| FP | A pick exists but no reference phase exists, **or** the pick lies outside tolerance. |
| FN | A reference phase exists but no pick was made, **or** the pick lies outside tolerance. |

**Caveat to state in the report:** under this definition a pick outside tolerance counts as both FP and FN. This is a common convention but not universal. Other papers define it differently, so numbers must not be compared across papers without checking matching rules.

**Seismological caveat:** the reference picks themselves carry uncertainty (often on the order of a few samples for clear P, larger for emergent P and for S). A tolerance tighter than the reference-pick uncertainty measures label noise as much as model error. The report should discuss this relationship. If the dataset provides pick-uncertainty or quality information, it should be consulted (OQ-13).

---

## 9. Edge cases

Grouped by origin. For each, the **expected handling** is stated. Where a decision is not made, it is flagged [OPEN]. No handling is silently invented.

### 9.1 Label and phase-presence edge cases

| # | Edge case | Expected handling |
|---|---|---|
| E1 | Window contains P but not S (S falls after the window). | S target is all zeros; an S pick is a FP; no S FN. |
| E2 | Window contains S but not P (P before window start). | Symmetric with E1. |
| E3 | Window contains neither (pure noise). | Both targets zero. Any pick is FP. Required for evaluating false-alarm behaviour. |
| E4 | Reference S-P time is very short (near-source events). | P and S Gaussian targets overlap; noise target is clipped to stay valid (FR-L3). Peak extraction may merge them. Report performance by S-P time if metadata allows. Threshold on S-P time for exclusion is [OPEN]. |
| E5 | Reference S pick earlier than or equal to P pick (invalid ordering). | Treat as a data-quality error: flag/exclude and log (FR-D3). |
| E6 | Reference pick lies exactly at or very near a window edge. | Gaussian target is truncated. Define whether such windows are allowed. [OPEN] (OQ-14). |
| E7 | Missing reference pick (P or S absent in metadata). | Excluded from tasks requiring that pick (e.g., S evaluation). Counted and logged. |
| E8 | Reference picks of low quality or high uncertainty. | Use if provided. Policy (keep, down-weight, exclude) is [OPEN] (OQ-13). |
| E9 | Phase identity ambiguity (e.g., regional Pn/Pg or Sn/Sg). | The dataset's labelling convention is inherited. The project does **not** distinguish sub-phases unless the dataset does. Flag as a limitation. |

### 9.2 Signal-quality edge cases

| # | Edge case | Expected handling |
|---|---|---|
| E10 | NaN/Inf samples. | Exclude trace and log (FR-D3). |
| E11 | Flat (zero-variance) trace or channel (dead channel). | Exclude entire trace if all channels are dead. If only one component is dead, policy is [OPEN] (OQ-15). Normalisation must not divide by zero. |
| E12 | Missing component (e.g., only vertical, or 2 horizontals). | Not supported by a fixed 3-channel model. Excluded unless a zero-fill policy is chosen. [OPEN] (OQ-15). |
| E13 | Data gaps or zero-padded segments. | Detected and flagged where possible. Handling [OPEN]. |
| E14 | Spikes, glitches, instrument transients. | Not removed unless a documented rule exists. These are a likely source of false picks. Include in failure analysis. |
| E15 | Clipped / saturated signal from a large nearby event. | Flag if detectable. Phase onset may still be visible but amplitude is distorted. Report as a limitation. |
| E16 | Very low SNR / emergent onset. | Expected to degrade. This is the object of the noise study (G5). Never excluded from test purely for being difficult. |
| E17 | Anthropogenic or non-tectonic transients (quarry blasts, traffic, ocean microseism bursts). | May produce false P/S picks. Treated as ordinary noise unless the dataset labels them. Discuss in failure analysis. |
| E18 | Different sampling rates across traces. | Resample to a common rate (FR-P4) or exclude. Anti-aliasing must precede downsampling. |
| E19 | Different instrument types / units (counts vs velocity vs acceleration). | Per-window normalisation reduces but does not remove sensitivity. Instrument response removal is **not** assumed. Flag as limitation unless the dataset is already uniform. |
| E20 | Timing errors / clock drift in source data. | Cannot be detected by this project. Inherited as label noise. Limitation. |

### 9.3 Multi-event and signal-context edge cases

| # | Edge case | Expected handling |
|---|---|---|
| E21 | Two or more events in one window (aftershock sequences, swarms). | One pick per phase per window (A4) means extra events are missed or mis-assigned. Documented limitation. Windows with multiple reference events are either excluded or labelled only for the main event. [OPEN] (OQ-16). |
| E22 | Long coda of a large event masks a following small event. | Same as E21. Not addressed. |
| E23 | Very distant (teleseismic) events. | Phase identification differs (many later phases, low frequencies, emergent P). PhaseNet-style local/regional pickers are not designed for them. Out of scope unless the dataset says otherwise. |
| E24 | Windows that include the S wave but where the S onset is hidden in the P coda. | Expected harder than P. Report S separately (FR-E6). |
| E25 | Same event recorded at multiple stations with different SNR. | Handled by event-level splitting (FR-D4). Never split across sets. |

### 9.4 Model, picking and evaluation edge cases

| # | Edge case | Expected handling |
|---|---|---|
| E26 | Model outputs no peak above threshold. | "No pick" returned (FR-K3). Counts as FN if a reference exists. |
| E27 | Several peaks above threshold. | Selection rule documented (FR-K4). Report how often this occurs. |
| E28 | Probability peak is broad or double-peaked. | The pick is the peak location. Peak width may be used as uncertainty only under optional O4. |
| E29 | Predicted P pick occurs after predicted S pick. | Physically implausible. Count and report how often. Whether to enforce ordering is [OPEN] (OQ-17). |
| E30 | Model collapses to predicting all-noise. | Detect via training logs and per-class probability statistics. Treated as a training failure, not a result. |
| E31 | Strong class imbalance (most samples are noise). | Expected from the label design. Monitor P/S metrics, not just loss or overall accuracy. Mitigation approach is not pre-decided. |
| E32 | Metric undefined (no true positives, zero denominators). | Metrics return a defined value (e.g., 0) with the denominators also reported. Document the convention. |
| E33 | Performance differs strongly between seeds. | Report multiple seeds where affordable. State if only one run exists. |
| E34 | Test-set performance higher than validation without explanation. | Treat as a prompt to check for leakage, not as a positive finding. |

### 9.5 Noise-experiment edge cases

| # | Edge case | Expected handling |
|---|---|---|
| E35 | Added noise is white Gaussian, which is not realistic seismic noise (real noise is coloured, non-stationary, has microseism peaks). | Allowed because it is controllable. The limitation shall be stated explicitly. |
| E36 | Window already contains substantial real noise. | Defined SNR reflects only *added* noise relative to the signal power. The report must say how signal power is computed (whole window vs. signal portion). [OPEN] (OQ-18). |
| E37 | Noise level defined relative to a window that is mostly noise (long pre-P). | SNR numbers depend on window composition. State the definition so numbers can be interpreted. |
| E38 | Re-adding noise changes the random draw between evaluations. | Fix the noise seed so noise-sweep results are comparable. |

---

## 10. Dependencies

| Dependency | Notes | Status |
|---|---|---|
| Python, PyTorch | Model and training | [PROPOSED] framework |
| SeisBench | Dataset access and standard format. A plausible convenience, not required by the statement. | [PROPOSED] |
| NumPy / SciPy / pandas / matplotlib / scikit-learn | Processing, peak detection, tables, plots | [PROPOSED] |
| ObsPy (optional) | STA/LTA baseline (O1) and waveform utilities | [PROPOSED] optional |
| GPU (e.g., Colab/Kaggle) | Training | [PROPOSED], A6 |
| Chosen dataset | One dataset | [OPEN] OQ-3 |

---

## 11. Success criteria

Because no numeric performance target was given, success is defined by **deliverables and rigour**, not by a score.

| ID | Criterion | Source |
|---|---|---|
| SC-1 | A trained 1D U-Net produces P/S/noise probabilities on held-out test events. | [GIVEN] |
| SC-2 | Arrival times are extracted and evaluated with residuals, precision, recall and F1 under a defined tolerance, for P and S separately. | [GIVEN] |
| SC-3 | Visualisations (waveform + picks + probabilities) exist, including both success and failure cases. | [GIVEN]/[DERIVED] |
| SC-4 | A noise-robustness analysis exists with a documented method. | [GIVEN] |
| SC-5 | A training-configuration study exists with one-factor-at-a-time changes. | [GIVEN] |
| SC-6 | Another person can regenerate the reported tables/figures from the repository. | [GIVEN] |
| SC-7 | Limitations are stated and no deployment claims are made. | [GIVEN] |
| SC-8 | Event-level split verified with zero overlap. | [DERIVED] |

**Performance targets:** intentionally **not set**. If the team wants pass/fail targets (e.g., "S F1 above X at tolerance Y"), they should be set *after* the baseline run, and treated as [OPEN] until then (OQ-19).

---

## 12. Open questions and decisions needed

These are the items I could **not** responsibly decide for you. Each blocks or shapes a requirement above.

| ID | Question | Affects | Suggested way to close |
|---|---|---|---|
| OQ-1 | Who are the real intended readers/users beyond the project author and evaluator? | Section 3 | Confirm with project owner/supervisor. |
| OQ-2 | Which datasets are acceptable, and must the dataset provide event IDs? | DR-3, FR-D4 | Choose after inspecting metadata. |
| OQ-3 | **Which dataset is the "selected dataset"?** | Everything data-related | Decide first. Common options with different regions/scales exist (e.g., STEAD, INSTANCE, ETHZ via SeisBench). Verify their current properties before choosing. |
| OQ-4 | Window length and sampling rate. | A3, FR-P5, FR-M5 | Fix once dataset is chosen. (Earlier plan: 3072 samples at 100 Hz, which is a proposal.) |
| OQ-5 | Split ratios and whether a time-based or region-based split is wanted. | FR-D6 | Decide with supervisor. |
| OQ-6 | Use a bandpass filter? Which band? | FR-P3 | Decide based on dataset and document either way. |
| OQ-7 | Fraction of pure-noise training windows. | FR-P7 | Choose, then optionally ablate. |
| OQ-8 | Label width σ. | FR-L2 | Choose a baseline, then include in the ablation. |
| OQ-9 | Loss function for the baseline. | FR-T1 | Choose and state. |
| OQ-10 | Picking threshold and multi-peak rule. | FR-K2, FR-K4 | Choose on validation data. |
| OQ-11 | **Tolerance value(s) for TP.** | FR-E4, entire evaluation | Decide before testing. Consider reporting a strict and a lenient value. |
| OQ-12 | Which training factors are ablated? | FR-X4 | Choose a short list (e.g., from σ, depth, width, augmentation, loss). |
| OQ-13 | How to treat reference pick quality/uncertainty. | E8, Section 8 | Inspect what the dataset provides. |
| OQ-14 | Are picks near window edges allowed? | E6 | Choose a rule. |
| OQ-15 | Policy for dead/missing components. | E11, E12 | Exclude or fill, then state. |
| OQ-16 | Handling of multi-event windows. | E21 | Exclude, or label main event only. |
| OQ-17 | Enforce P-before-S ordering on predictions? | E29 | Decide, and report both variants if unsure. |
| OQ-18 | Precise SNR definition for the noise study. | E36 | Define and document. |
| OQ-19 | Are numeric performance targets wanted? | Section 11 | Set after the baseline exists. |
| OQ-20 | Project time budget and compute limits. | NFR-5 | Confirm. Earlier plan assumed a few weeks part-time. This is not a given. |

---

## 13. Known limitations (to carry into the final report)

These are expected from the problem framing and standard practice. They are not invented requirements. They are things a careful seismologist would insist on stating.

1. **Single dataset.** No evidence of generalisation to other regions, networks, instruments or magnitude ranges (NG6).
2. **Reference picks are not absolute truth.** They are analyst or catalogue derived and contain uncertainty, and possibly systematic bias. Reported "error" partly reflects label noise.
3. **One pick per phase per window.** Not representative of continuous multi-event data (A4, E21).
4. **Windowed, not continuous.** Behaviour on continuous streams, including false-alarm rates per day, is untested.
5. **Gaussian-noise experiments** do not represent real, coloured, non-stationary seismic noise (E35).
6. **Sub-phases and teleseismic phases** are not distinguished (E9, E23).
7. **Instrument response and units** are not explicitly handled (E19).
8. **Tolerance-dependent metrics.** Precision/recall/F1 change with tolerance and matching rules, so cross-paper comparison requires care.
9. **No deployment or early-warning claim** (NG1).

---

## 14. Background and related work (for context, not requirements)

*Verify all of the following before citing. I could not look them up.*

- **PhaseNet** (Zhu & Beroza, 2019, *Geophysical Journal International*): U-Net on 3-component waveforms, outputs P / S / noise probability curves, Gaussian-shaped training targets for P and S. Trained on Northern California data. This project is "inspired by" it **[GIVEN]**.
- **EQTransformer** (Mousavi et al., 2020, *Nature Communications*): multi-task detection plus picking using attention.
- **GPD** (Ross et al., 2018): CNN-based phase detection.
- **SeisBench** (Woollam et al., 2022, *Seismological Research Letters*): toolbox of datasets, models, and benchmark tooling.
- **STEAD** (Mousavi et al., 2019, *IEEE Access*): large global-ish, mostly local-distance labelled dataset.
- **INSTANCE** (Michelini et al., 2021): Italian dataset with noise and event waveforms.
- **Münchmeyer et al., 2022** ("Which picker fits my data?"): a comparative evaluation of deep learning pickers across datasets, relevant to evaluation design and to the point that metrics depend on protocol.
- **Classical methods:** STA/LTA (Allen, 1978 lineage), AIC-based pickers.

**Dataset properties (sampling rate, window length, number of traces, label sources, known label quality issues) must be checked from the dataset's own documentation.** Some large public datasets are known to contain label or metadata imperfections, so basic quality checks (FR-D3) are warranted rather than optional.

---

## 15. Risks

| ID | Risk | Likelihood / Impact | Mitigation |
|---|---|---|---|
| R1 | Event leakage inflates results. | Medium / High | FR-D4, FR-D5, SC-8, E34 check. |
| R2 | Model learns pick position instead of waveform features. | Medium / High | FR-P6 randomised window offset. |
| R3 | S-wave performance is poor and hidden by aggregated metrics. | High / Medium | FR-E6 separate P and S. |
| R4 | Tolerance chosen after seeing results. | Medium / High | Freeze in Section 8 before test (NFR-3). |
| R5 | Compute or time shortage. | Medium / Medium | FR-D7 subset, small baseline model. |
| R6 | Dataset lacks event IDs or S picks. | Low–Medium / High | DR-2, DR-3 check before committing to dataset (OQ-2/3). |
| R7 | Over-claiming from synthetic noise tests. | Medium / Medium | Limitation 5, NFR-6. |
| R8 | Irreproducible results due to GPU non-determinism. | Medium / Low | Fix seeds, report multiple seeds, state residual variation. |

---

## 16. Milestones (indicative, [PROPOSED])

No schedule was given in the problem statement. This is a suggested sequence only (OQ-20).

| Milestone | Deliverable |
|---|---|
| M1 | Dataset chosen and explored (OQ-3 closed). Data-quality log. Event-level splits saved. |
| M2 | Preprocessing, windowing, label generation, `Dataset`/`DataLoader`. Sample figures. |
| M3 | Model implemented and overfit-sanity-tested. |
| M4 | Baseline trained. Loss curves. Checkpoint. |
| M5 | Picking and evaluation protocol frozen (OQ-10, 11 closed). Baseline metrics on validation, then test. |
| M6 | Visualisation and failure analysis. |
| M7 | Noise-robustness and ablation experiments. |
| M8 | Report, README, regeneration script. |

---

## 17. Glossary

| Term | Meaning |
|---|---|
| P wave | Primary (compressional) body wave, first arrival. |
| S wave | Secondary (shear) body wave, arrives after P. |
| S-P time | Time difference between S and P arrivals, related to source distance. |
| Phase picking | Determining the arrival time of a seismic phase. |
| Onset (impulsive / emergent) | How sharply a phase starts above the noise. Emergent onsets are harder to time. |
| Coda | Scattered wave energy following the main arrivals. |
| SNR | Signal-to-noise ratio. Definition must be stated (OQ-18). |
| Residual | Predicted pick time minus reference pick time. |
| Tolerance | Maximum absolute residual for a pick to count as correct. |
| TP / FP / FN | True positive / false positive / false negative, per Section 8. |
| STA/LTA | Short-term-average / long-term-average classical detector. |
| Event leakage | The same earthquake appearing in both training and test data. |
| U-Net | Encoder-decoder network with skip connections. |

---

## 18. Revision history

| Version | Notes |
|---|---|
| 0.1 | Initial draft. All [PROPOSED] and [OPEN] items await owner review. |
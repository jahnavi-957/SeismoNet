# SeismoNet — Reasoning and Architectural Decisions

**Document ID:** DEC-001
**Version:** 1.0
**Date:** 2026-10-18
**Status:** Reasoning record updated after the bounded training pilot and validation-only inference. The pilot provides measured pipeline evidence, but it is not a scientific baseline and does not close the protocol decisions required before test evaluation.

---

## 0. Purpose and how to read this document

This document records **why** SeismoNet is designed the way it is. `TECHNICAL_ARCHITECTURE.md` states *what* the architecture is; this document states the reasoning behind it, the alternatives that were rejected, the risks accepted, the evidence that would validate or overturn each decision, and the conditions under which it should be revisited.

### 0.1 Evidence classes used throughout

Every decision is annotated with the class of support it currently has. This distinction is the whole point of the document: a design rationale is not evidence.

| Class | Meaning |
|---|---|
| **[ESTABLISHED]** | A settled scientific or methodological principle in seismology / machine learning. Not contingent on this project's experiments. |
| **[RATIONALE]** | A design argument that follows from the problem statement or from engineering constraints. Plausible and defensible, but not itself measured. |
| **[HYPOTHESIS]** | A testable claim about this project that is currently unverified. A named experiment (EX-*) would test it. |
| **[MEASURED]** | Supported by an actual experiment run in this project. A measured result is still bounded by its dataset, split, checkpoint and protocol scope. |
| **[PROVISIONAL]** | A value or choice that is expected to change once evidence exists. |

### 0.2 The honest summary

> The bounded pilot and validation-only inference now provide **[MEASURED]** pipeline evidence, including a candidate threshold sweep on 210 validation traces. They do not establish scientific performance, generalization, or a test-set result. Protocol choices that affect the future test evaluation remain **[PROVISIONAL]** until owner/supervisor review.

### 0.3 Cross-reference index

| Decision | Topic | Primary alternative considered |
|---|---|---|
| D-01 | 1D U-Net for time-series phase picking | RNN / Transformer / window classifier |
| D-02 | Per-sample probability output | Single scalar arrival time per trace |
| D-03 | P, S and noise as three classes | Independent binary P and S heads |
| D-04 | Consistency of waveform preprocessing | Faithful, less-processed input |
| D-05 | Careful sampling-rate and timestamp handling | Ignoring the scale / naive index conversion |
| D-06 | Event-level splitting | Random trace-level split |
| D-07 | Separate P and S metrics | One combined score |
| D-08 | Validation-selected inference threshold | Test-selected threshold; fixed guess |
| D-09 | Controlled noise experiments | Testing on naturally varying noise only |
| D-10 | Simple Python pipeline, minimal infrastructure | Web stack / database / service architecture |
| D-11 | Optional interface after core validation | Building the interface first |
| D-12 | Reproducible configuration and checkpoints | Ad-hoc runs; unrecorded hyperparameters |
| D-13 | Gaussian target curves (supporting decision) | Hard one-hot labels / direct regression |
| D-14 | One-factor-at-a-time experiment design (supporting decision) | Full grid search |

---

## D-01 — Why a 1D U-Net is suitable for time-series phase picking

**1. Problem being addressed.** Arrival time is a *per-sample* decision made with *multi-scale context*. A P onset is often a small, sharp change in amplitude and frequency at a specific sample; distinguishing it from a noise transient requires seeing a much longer window for context. A model must therefore produce a fine-grained time output while consuming a broad temporal context.

**[ESTABLISHED]** Convolutional encoders extract local waveform features; stacking strided convolutions enlarges the receptive field; a decoder with **skip connections** restores the output to per-sample resolution without losing the fine detail that downsampling destroyed. This is precisely the encoder–decoder-with-skips pattern, and it is a well-established principle in both image and time-series segmentation.

**2. Selected approach.** A one-dimensional U-Net: an encoder of strided convolutions, a decoder of upsampling plus convolution, skip connections between matching scales, and a three-channel per-sample output. `[DECIDED]` by the problem statement ("1D U-Net inspired by PhaseNet"); the parameters (depth, width, kernel) are `[PROPOSED]` (`SR-008`).

**3. Why selected.**

- **[RATIONALE]** Output length equals input length, so arrival times are read directly per sample rather than decoded from a compressed representation (`FR-034`).
- **[RATIONALE]** Skip connections are the specific mechanism that keeps onset sharpness; without them, the decoder would produce spatially smooth onsets, which is exactly the property that ruins timing precision.
- **[RATIONALE]** Fully convolutional, so the same weights work on any window length divisible by `2^depth` (`FR-036`) — no retraining per length.
- **[CONSTRAINT]** The project must train on a single free-tier or 4 GiB device. A convolutional U-Net scales more favourably in memory and data requirement than a Transformer for this data size (`R-06`, `NFR-007`).

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **RNN / LSTM over samples** | Sequential modelling of long dependencies | Slow to train, harder to parallelise, and the long-range dependency structure of a waveform is better captured hierarchically. No requirement favours recurrence. |
| **Transformer / attention over time samples** | Strong at long-range dependency | Higher data and compute appetite than a mini-project can justify; a 3072-sample sequence is long for full attention; speculative for this scope (`NG5` excludes architecture research). |
| **Fixed-window CNN classifier** (predict whether a phase is present in a short window) | Much simpler | Gives a window-level answer, not a per-sample time. Arrival time would then need a separate refinement step. Loses the elegant "output is a probability curve" property that makes peak-picking natural. |
| **Direct regression of arrival time** (one number per phase) | Trivially simple output | Forces the model to regress an ill-defined quantity (onset is a judgement, `PRD.md` §4.3); no way to express ambiguity; notoriously unstable for emergent onsets. |
| **Classical STA/LTA or AIC picker** | No training data needed; interpretable; fast | Threshold-based and degrades at low SNR; times S waves poorly; and the project's stated approach is deep learning. Retained only as an optional reference baseline (`O-Opt1`, EX-7). |

**5. Advantages.**

- Per-sample output aligned to the input, with no decoding step.
- Skip connections preserve onset sharpness.
- Small enough to train on modest hardware.
- Architecture is explainable in a report without hand-waving.
- The same family has known precedent in this exact task (PhaseNet lineage), so the project is "inspired by" a working approach rather than experimenting blindly.

**6. Disadvantages.**

- Requires labelled training data — the very thing that is uncertain here (`OQ-3`).
- More parameters and more compute than a classical detector.
- Skip-connection alignment imposes a divisibility constraint on window length (`FR-036`) that must be asserted, or shape errors appear late and confusingly.
- Convolutional receptive fields are finite: two phases separated by more than the receptive field cannot inform each other's classification without extra machinery.
- Softmax over three classes creates a coupling between them (see D-03).

**7. Risks.**

| Risk | Mitigation | Requirement |
|---|---|---|
| Onsets over-smoothed → large timing bias | Validate residuals, not just classification metrics; inspect residual distributions | `FR-055`, `FR-066` |
| Model too large for the device | Small baseline; configurable width; dataset subset | `FR-007`, `SR-008`, `NFR-007` |
| Shape/depth misconfiguration | Explicit assertion with a specific message | `FR-036` |
| No data → the whole decision is moot | Dataset selection is the first gated phase | `P1`, `DR-003` |
| Architecture treated as "obviously good" without evidence | Any depth/width claim goes through the EX-2 ablation | `FR-073` |

**8. Evidence needed.**

- **EX-1** demonstrates end-to-end that the architecture produces usable probability curves at all.
- **EX-2** varies depth, base channels and kernel size. Only then can a statement about the architecture's parameters be made.
- **The tiny-batch overfit test (`FR-044`)** verifies the wiring can learn before any claim about generalisation.
- Inspecting residuals (`FR-056`) checks specifically for the over-smoothing failure mode the skip connections are meant to prevent.

**9. Conditions that would justify changing this decision.** If, *after* the data path is verified correct, all trained configurations produce broad, flat probability curves with large residual bias and no configuration improves it, the choice of a plain convolutional encoder–decoder would need revisiting in favour of an architecture with stronger long-range or multi-scale modelling. This would be recorded as an ADR superseding D-01, and would not be attempted before the data path and protocol are verified, because a modelling change cannot fix a data bug.

**Evidence class: [ESTABLISHED] for the architecture family; [PROPOSED] for its parameters; [HYPOTHESIS] that its parameters are adequate for the chosen dataset.**

---

## D-02 — Why per-sample probabilities are useful

**1. Problem being addressed.** What should the model output? The deliverable is an arrival time, but an arrival time is a judgement with uncertainty, and a window may contain no phase at all.

**2. Selected approach.** For every sample, output a probability distribution over {P, S, noise}; arrival times are extracted from the probability curves by peak-picking (`FR-049`, `FR-050`).

**3. Why selected.**

- **[ESTABLISHED]** A probabilistic per-sample output is a *segmentation* formulation. It separates the learning problem ("which samples are P-like?") from the decision problem ("which peak, at what threshold?"). Separating them means the threshold can be chosen later, on validation data, without retraining (`D-08`).
- **[RATIONALE]** Peak-picking on a curve is trivially inspectable: a seismologist can look at the curve and the waveform together and judge plausibility, which is exactly what `U1` needs (`FR-065`, `US-12`).
- **[RATIONALE]** The curve's shape carries diagnostic information — a broad or double-peaked curve is visible as ambiguity rather than hidden behind a scalar (`E28`, optional `O-Opt4`).
- **[RATIONALE]** "No pick" becomes a natural, honest outcome when nothing exceeds threshold (`FR-009`, `SR-013`), instead of a fabricated number.
- **[RATIONALE]** The class probabilities give an explicit noise channel, which makes false-alarm behaviour measurable on pure-noise windows (`E3`).

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **One arrival time per phase, regressed directly** | Simplest interface | No uncertainty; unstable for emergent onsets; cannot express "no phase present" except by a sentinel value that corrupts error statistics |
| **Detect-then-refine two-stage** (a detector flags a window, a refiner predicts the offset) | Common in production systems | Two models, two failure modes, and a detection threshold that reintroduces exactly the tuning the probabilistic formulation avoids. Over-engineered for the scope (`P-8`) |
| **Per-sample binary P and per-sample binary S** | Slightly simpler heads | Loses the explicit noise class (`D-03`); the two heads are separately thresholded, complicating "no phase" handling |

**5. Advantages.** Inspectable; thresholdable post-hoc; expresses ambiguity; makes "no pick" first-class; gives a natural false-alarm channel; aligned with the input so no decoding is needed.

**6. Disadvantages.** Threshold becomes a parameter that must be chosen (`OQ-10`); probability is *not* correctness, so a confident-looking peak can still be wrong (limitation stated in `README.md`); peak-selection rules introduce their own arbitrariness when multiple peaks appear (`FR-052`).

**7. Risks.** A reviewer misreading a high probability as verified correctness — mitigated by stating the distinction in the report (limitation L2 and the README's own note); threshold chosen after seeing results — mitigated by `FR-061`.

**8. Evidence needed.** EX-1 must show that peaks in the curves are located near reference onsets. The threshold sweep on validation (`FR-051`) quantifies the precision/recall trade-off, which is what turns "a probability curve" into "a usable picker".

**9. Conditions to change.** If peak-picking from the curves proved to be the dominant error source (i.e., the curves were accurate but peaks were systematically misplaced), a post-processing refinement stage would be justified. That would be an *addition*, not a replacement of this decision, and would require evidence from EX-6.

**Evidence class: [ESTABLISHED] as a formulation; [RATIONALE] for its benefits here.**

---

## D-03 — Why P, S and noise are considered

**1. Problem being addressed.** The model must be able not to pick. Most samples in a typical window are noise, and some windows contain no phase at all. A model with only P and S outputs has no way to express "nothing here".

**2. Selected approach.** Three classes with a softmax across them, so the three probabilities sum to 1 per sample; the noise target is the remainder after the P and S Gaussians (`FR-023`, `SR-006`).

**3. Why selected.**

- **[RATIONALE]** An explicit noise class makes the "no phase" case learnable rather than implicit. Without it, the model must learn to keep *both* P and S near zero in noise, which is a harder and less natural objective than a three-way choice.
- **[ESTABLISHED]** A softmax over mutually exclusive classes — this sample is a P onset, an S onset, or neither — encodes the intended semantics and produces normalised probabilities.
- **[RATIONALE]** It matches the stated problem statement ("probability of P-wave arrivals, S-wave arrivals, and noise") and the PhaseNet lineage, so the project remains "inspired by" an established design rather than a novel one (`NG5`).
- **[DERIVED]** Summing to 1 also gives a well-defined noise probability to monitor, which is how training collapse to all-noise is detected (`E30`).

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **Two independent binary heads (P, S)** | Each head is a simple sigmoid; no coupling | No explicit noise class; the "neither" case is implicit; two thresholds instead of one; noise probability is not directly available for monitoring |
| **Four classes adding a separate "coda" class** | More expressive | Beyond the stated problem statement; adds labels the dataset is unlikely to provide (`NG5`, `OQ-3`) |
| **Regress an onset mask** | Smooth output | Treats the problem as regression; over-smooths; no probabilistic interpretation |

**5. Advantages.** Explicit noise modelling; normalised per-sample probabilities; a directly monitorable noise channel; aligned with the stated objectives and the reference architecture.

**6. Disadvantages and an honest caveat.** A softmax creates **coupling**: increasing confidence in P necessarily reduces noise probability, so an over-confident P prediction cannot be simultaneously uncertain. When P and S targets overlap — near-source events with very short S-P times — the noise remainder can be squeezed and must be clipped to stay valid (`E4`). This is a known structural limitation of the three-channel formulation, is inherited from the PhaseNet lineage, and is disclosed rather than solved.

**7. Risks.** Overlapping P/S targets weakening the noise class (`E4`, `OQ-22`); class imbalance making "noise" dominant so that the model trivially minimises loss by predicting noise — monitored via per-class statistics and P/S metrics rather than bare loss (`E31`, `R-08`).

**8. Evidence needed.** EX-1 verifies all three channels are non-degenerate (no channel collapses). The distribution of S-P times in the chosen dataset should be inspected to quantify how often the overlapping-target case occurs (`OQ-22`). Per-class probability statistics during training are the early-warning instrument (`E30`).

**9. Conditions to change.** If a large fraction of the chosen dataset has very short S-P times and the overlapping-target case demonstrably degrades performance (visible as a bimodal residual distribution for S), an alternative target or loss construction for close-in events would be justified. This would be documented as an ADR and would need EX-1 or EX-2 evidence, not intuition.

**Evidence class: [ESTABLISHED] for the softmax formulation; [RATIONALE] for three classes here; [HYPOTHESIS] that the noise remainder is an adequate target for this dataset.**

---

## D-04 — Why waveform preprocessing must be consistent

**1. Problem being addressed.** Waveforms arrive with offsets, trends, differing instrument gains and differing units. If training sees one preprocessing and evaluation sees another, every reported number measures the mismatch rather than the model.

**2. Selected approach.** A single, shared preprocessing path used by both training and evaluation: per-component detrend and demean, then per-window amplitude normalisation with a recorded method; no augmentation at evaluation (`FR-013`, `FR-014`, `FR-020`, `SR-005`).

**3. Why selected.**

- **[ESTABLISHED]** Detrending and demeaning remove baseline drift and DC offset, which are non-information for onset detection and can dominate a raw amplitude scale.
- **[RATIONALE]** Per-window normalisation removes the influence of instrument gain and units *without* requiring instrument-response removal, which is explicitly out of scope. This is the pragmatic middle ground.
- **[RATIONALE]** A shared code path (`FR-020`) makes train/eval consistency a property of the code structure rather than of developer discipline — the cheapest possible insurance. Train/eval preprocessing skew is one of the most common causes of a model that looks good in training and fails in evaluation.
- **[DERIVED]** Per-window statistics (rather than dataset-global statistics) also avoid a subtle leakage path: global statistics computed on the full dataset would couple the test split to the training split.

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **No preprocessing at all** | Maximally faithful to the raw signal | Trends and offsets dominate; normalisation would be impossible; differing gains across traces make the problem ill-posed |
| **Dataset-global normalisation (z-score over the whole dataset)** | Simple, one pass | Computes statistics across splits, coupling train and test, and is sensitive to dataset composition. A leakage risk for no clear benefit |
| **Instrument-response removal to physical units** | Scientifically the most correct | Requires response metadata that may not exist, adds significant scope, and is explicitly out of scope (limitation L7). Also unnecessary once per-window normalisation is applied |
| **Bandpass filtering always on** | Removes out-of-band noise | A filtering choice depends on the instrument band and the dataset's spectrum; making it mandatory would bake in an unjustified decision. Made optional and recorded instead (`FR-015`, `OQ-6`) |
| **Preprocessing inside the model (a normalisation layer)** | Guarantees consistency by construction | Hides a scientific decision inside the architecture, makes it invisible in the config, and complicates the "identical at eval" requirement. Explicit is better here |

**5. Advantages.** Consistency guaranteed by structure; instrument scale differences removed; leakage path avoided; every preprocessing choice visible in the config and recorded with the run (`FR-020`, `FR-042`).

**6. Disadvantages.** Per-window statistics can be unreliable for windows that are mostly noise, and normalisation rescales a genuinely large nearby event down to look like a small one — removing amplitude information that a human analyst would use. That information loss is accepted deliberately, because amplitude is instrument-dependent across a heterogeneous dataset.

**7. Risks.** A hidden asymmetry if preprocessing is applied conditionally (mitigated by the shared path and a test asserting identical output for identical input, `FR-020`); division by zero on flat channels (mitigated explicitly, `E11`); filtering parameters recorded but not justified (mitigated by documenting the decision in the report either way, `FR-015`).

**8. Evidence needed.** The test in `TESTING_STRATEGY.md` asserting train and eval preprocessing produce identical output. EX-1 for end-to-end adequacy. A filtered-vs-unfiltered comparison, if filtering is enabled, belongs to EX-2.

**9. Conditions to change.** If per-window normalisation demonstrably destroys amplitude information the model needs — visible as systematically poor performance on low-SNR events with a strong pre-phase noise burst — then a different normalisation scheme (for example, normalising on a fixed pre-pick noise window) would be justified. This requires a specific experiment to be designed; it should not be adopted on intuition.

**Evidence class: [ESTABLISHED] for detrend/demean; [RATIONALE] for per-window normalisation; [PROVISIONAL] for the specific normalisation method.**

---

## D-05 — Why sampling rates and timestamps require careful handling

**1. Problem being addressed.** Every quantity in the pipeline — pick index, Gaussian σ, evaluation tolerance, residual — is expressed in **samples**, but every geophysical meaning is expressed in **seconds**. A dataset may contain more than one sampling rate.

**2. Selected approach.** Fix one common sampling rate for the project; resample other traces with anti-aliasing before downsampling, or exclude them; record the rate with every window; convert picks to seconds explicitly; convert to absolute time only when a trace start time exists (`SR-003`, `FR-016`, `FR-053`, `SR-014`).

**3. Why selected.**

- **[ESTABLISHED]** `seconds = index / fs` and `absolute = trace_start + seconds`. These conversions are elementary but they are also where silent, large errors live: a pick index transferred between rates without conversion is wrong by a factor of the rate ratio.
- **[ESTABLISHED]** Downsampling without an anti-aliasing filter aliases high-frequency energy back into the passband, corrupting precisely the high-frequency content that impulsive onsets depend on. Anti-aliasing before decimation is not optional.
- **[DERIVED]** Parameters that are naturally defined in samples (the Gaussian σ, `SR-006`) must be **re-expressed** when the rate changes, or their physical meaning changes silently. σ = 10 samples at 100 Hz is 0.1 s; the same number at 50 Hz is 0.2 s.
- **[RATIONALE]** Keeping results in seconds as the primary unit makes them comparable with the seismological literature and with other datasets; samples are retained as a supplementary column for implementation-level debugging.
- **[RATIONALE]** Separating relative from absolute time means the project does not become dependent on the dataset carrying absolute trace start times, while still supporting them where present.

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **Keep multiple rates, track per-trace** | Avoids resampling loss | Every parameter (σ, window length, tolerance) becomes rate-dependent; the tolerance would not mean the same thing across traces; comparison across traces becomes invalid |
| **Resample by naive index scaling** (multiply indices by the rate ratio) | One-line implementation | **Wrong.** It ignores timing alignment and, for non-integer ratios, introduces systematic sub-sample error. The labels must be converted via time, not by index arithmetic |
| **Work entirely in seconds** | Conceptually clean | Model outputs are per *sample*; framework code (convolutions, peak-finding) is index-based. Fighting the implementation convention adds complexity for no scientific gain |
| **Exclude all traces whose rate differs from the majority** | Simple and defensible | Discards usable data. Offered as the fallback alongside resampling rather than as the default, and the choice must be logged |

**5. Advantages.** One rate means σ, window length and tolerance have a single fixed meaning; conversions are explicit and testable in isolation (`FR-053`); anti-aliasing prevents a subtle corruption of onset sharpness; results are reported in the seismologist's unit.

**6. Disadvantages.** Resampling loses information and costs a conversion step; the chosen rate is a compromise for traces originally recorded at other rates; the rate decision interacts with the window-length decision (`SR-004`) and with σ (`SR-006`), so all three must be fixed together and documented.

**7. Risks.** **[HIGH IMPACT]** Silent rate mismatch (mitigated by validating rate at load, `FR-003`, and by a dedicated conversion test, `FR-053`); aliasing from unfiltered downsampling (mitigated by requiring anti-aliasing, `FR-016`); σ not re-expressed after a rate change (mitigated by defining σ in samples *relative to the working rate* and recording the rate); window origin lost so absolute time cannot be recovered (mitigated by recording window origin per trace, `FR-012`).

**8. Evidence needed.** A unit test that converts a known index at a known rate and checks the seconds value and the absolute time against hand-computed values (`FR-053`). A resampling test that confirms a synthetic phase onset appears at the expected position after resampling within tolerance (`FR-016`). Inspection of the chosen dataset's rate distribution (`FR-002`) before fixing `OQ-4`.

**9. Conditions to change.** If the chosen dataset turns out to be rate-homogeneous, the resampling path becomes dead code and should be retained but documented as unused rather than removed (datasets change). If the dataset turns out to be heterogeneous in a way that resampling cannot handle well, exclusion becomes the primary policy and the dataset choice itself should be reconsidered.

**Evidence class: [ESTABLISHED] (index/time conversion and anti-aliasing); [PROPOSED] for the specific rate and σ.**

---

## D-06 — Why event-level splitting helps prevent leakage

**1. Problem being addressed.** A classifier evaluated on data statistically entangled with its training data reports a number that is not a measure of generalisation. In seismology the entanglement is severe and specific.

**2. Selected approach.** Split train / validation / test **by seismic event**, persist the split, and verify zero event overlap as both a test and a hard guard at training start (`FR-004`, `FR-005`, `FR-025`, `FR-026`).

**3. Why selected.**

- **[ESTABLISHED]** One earthquake recorded at many stations produces highly correlated traces: the same source mechanism, the same path effects, similar waveforms and similar relative phase timing. A random trace-level split puts near-duplicates of the same event on both sides of the boundary, so the test set is not independent and scores are inflated. This is a textbook data-leakage mechanism, not a hypothetical one.
- **[ESTABLISHED]** The scientific question is whether the model generalises to *events it has not seen*, because that is what any future use would require. Trace-level splitting answers a different, easier question.
- **[RATIONALE]** Seismologists specifically distrust any result where the same event appears in train and test, so event-level splitting is also a credibility requirement for `U1` (`US-02`).
- **[RATIONALE]** Persisting the split to disk makes the guarantee auditable and reproducible: a reviewer can re-run the overlap check rather than trusting a description (`FR-005`, `SC-8`).
- **[RATIONALE]** The zero-overlap check runs as a *guard at training start* so that a leaked split aborts the run rather than producing a flattering but invalid number.

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **Random trace-level split** | Simple, maximises data per split | Leaks events; inflates scores; answers the wrong question. Rejected on principle |
| **Station-level split** (hold out stations) | Tests cross-station generalisation | Does not prevent the same event appearing in both sides; a strong alternative *question* but not the leakage fix |
| **Time-based split** (train on earlier, test on later) | Realistic for operative monitoring; tests temporal generalisation | Legitimate and arguably attractive, but it assumes a long, continuous catalogue and interacts with how events are distributed in time. Note: check what the chosen dataset supports (`OQ-5`, PRD §11.6). It is compatible with event-level splitting, not a replacement for it |
| **Region-based split** (hold out a geographic area) | Tests spatial generalisation; strongly informative | Requires reliable event locations and enough events per region; likely beyond the dataset's guaranteed metadata. Recorded as an alternative rather than chosen |
| **Stratified random split** (balance by magnitude/SNR) | Balances classes | Does not address leakage; can be layered on top of the event-level split for stratification of *reported* metrics (`FR-011`) but not for the split itself |

**5. Advantages.** Prevents the dominant leakage mechanism; matches the scientific question; auditable and reproducible; strongly defensible to a seismological reviewer; cheap to implement relative to the damage it prevents.

**6. Disadvantages and the price paid.** It requires a usable **event identifier**, which is not guaranteed (`DR-003`, `R-01`, `OQ-3`) — if a dataset lacks event IDs, event-level splitting is impossible and the dataset choice must be reconsidered. Event-level splitting can also make splits less balanced, because events differ in how many stations recorded them and in quality; a large event with 200 traces will dominate the training split. Class and metadata imbalance must therefore be *inspected* (`FR-002`) and *reported* rather than assumed away.

**7. Risks.** Mis-constructed event IDs silently grouping distinct events together or splitting one event across groups (`FR-010` must be tested); a dataset whose "event" field is actually a per-trace identifier, which would make the guarantee vacuous (verify by counting traces per event); split ratios becoming very uneven for event counts versus trace counts — the ratios should be declared for **events**, and the resulting trace counts reported so the discrepancy is visible.

**8. Evidence needed.** The automated zero-overlap test (`FR-025`) is the direct evidence. Additionally: report the number of events and the number of traces per split, so a reviewer can see the split is not degenerate. **[Not yet measured: no split exists yet.]**

**9. Conditions to change.** If the selected dataset has no event identifier and no way to construct one, the project cannot satisfy `DR-003` with that dataset and must change datasets — this is a gating decision, not a design preference. If the dataset is a continuous catalogue with reliable timing, additionally adopting a time-based split (train on earlier events, test on later events) would strengthen the generalisation claim; that would be an added experiment, documented as an ADR, and the event-level guarantee would remain.

**Evidence class: [ESTABLISHED] as a leakage-control principle; [RATIONALE] for this project; [PLANNED-VERIFY] that the chosen dataset supports it.**

---

## D-07 — Why P-wave and S-wave metrics must be reported separately

**1. Problem being addressed.** A single aggregate score would hide the single most predictable and most informative feature of phase picking: **S waves are harder than P waves**.

**2. Selected approach.** Every results table reports P and S separately; no combined-only headline number is ever emitted (`FR-060`).

**3. Why selected.**

- **[ESTABLISHED]** S onsets are frequently emergent and arrive inside the P coda, where earlier energy masks them. Deterioration at low SNR is also typically worse for S. PhaseNet-lineage analysis of this task has consistently shown asymmetric P/S difficulty — the asymmetry is a property of the physics and of the proxy task, not of one implementation.
- **[RATIONALE]** An average over easy P and hard S produces a number that is misleadingly good and useless for deciding where to focus effort. Reporting separately is what makes the failure useful.
- **[RATIONALE]** `U1` is a seismologist who knows the physics; a single figure would read as either naive or evasive (`US-09`).
- **[DERIVED]** Because S is the weaker channel, it is also where the failure gallery and the noise study are most informative (`EX-4`, `EX-6`).

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **One combined P+S score** | Compact headline for a poster | Hides the asymmetry; cannot be used to prioritise work; invites over-claiming |
| **Report only P (since P is easier)** | Best-looking number | Omits half the stated objective (`G3`) |
| **Report a weighted combination** (e.g. by class frequency) | Single number | Any weighting is arbitrary and would need its own justification; still hides the mechanism |
| **Report P and S plus a combined figure clearly labelled as a summary** | Information-rich | Acceptable only if the combined figure is supplementary and never the headline. Not excluded by `FR-060` as long as separate reporting is present |

**5. Advantages.** Reveals the real difficulty structure; supports targeted failure analysis; matches `US-09`; makes the report more useful to a seismologist; prevents a flattering aggregate.

**6. Disadvantages.** More tables and figures, and no single line that can be quoted as "our accuracy". That absence of a quotable headline is a deliberate trade: the project's success criteria are defined by rigour and deliverables, not by a score (`SC-1`…`SC-10`).

**7. Risks.** S effort is under-budgeted because P looks adequate — mitigated by making the P/S gap an explicit interpretive criterion in EX-1 and EX-4. S sample counts are small after event-level splitting and quality screening, so S metrics rest on fewer instances — mitigated by always reporting the denominator (`NFR-002`, `FR-062`).

**8. Evidence needed.** EX-1 produces the first P-versus-S comparison. EX-4 establishes whether the gap widens with noise. **[Not yet measured.]** If S and P turn out to be comparable on this dataset, that is itself a finding worth reporting — it does not invalidate the decision to report them separately.

**9. Conditions to change.** There is no condition under which aggregation becomes preferable. The only refinement imaginable is adding further breakdowns (by S-P time, by distance, by magnitude bin) on top of P/S separation, which strengthens rather than replaces this decision.

**Evidence class: [ESTABLISHED] for the P/S difficulty asymmetry; [RATIONALE] for separate reporting; the magnitude of the gap here is [HYPOTHESIS].**

---

## D-08 — Why validation data should determine inference thresholds

**1. Problem being addressed.** A probability curve is not a pick until a threshold is applied. The threshold directly sets the precision/recall trade-off, so choosing it is a modelling decision. On which data may that decision be made?

**2. Selected approach.** The picking threshold is selected on the **validation set only**, frozen, and then applied unchanged to the test set. Test evaluation happens once, after the freeze (`FR-051`, `FR-061`, `SR-011`).

**3. Why selected.**

- **[ESTABLISHED]** Any choice made by inspecting test-set performance turns the test set into a second validation set, and the resulting number is optimistically biased by an unknown amount. This is the most basic rule of honest evaluation, and the reason three splits exist at all.
- **[RATIONALE]** The threshold is exactly the kind of hyperparameter that is easy and tempting to tune post hoc — the sweep is cheap and the curve looks attractive. Making the freeze an explicit, documented step with a runnable guard (`FR-061`) is the only reliable protection.
- **[DERIVED]** The tolerance is really the same kind of decision as the threshold, so both are pre-declared (`SR-016`, `FR-058`).
- **[RATIONALE]** Freezing also makes the reported operating point *interpretable*: "threshold selected on validation; test evaluated once" is a claim a reviewer can check.

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **Choose the threshold on the test set** | Gives the best-looking test numbers | Invalid. Inflates the result and makes it non-reproducible for anyone who also uses their own test data |
| **Fix an arbitrary threshold (e.g. 0.5) and never tune it** | Completely honest; zero tuning | Defensible and simple, but wastes the validation set's information and typically picks a suboptimal operating point. Retained as a fallback if the validation set is too small to select reliably |
| **Cross-validated threshold selection over all data** | Uses more data | Requires cross-validation folds and a defined aggregation; adds cost and complexity for a mini-project. Reasonable for a larger study |
| **Report the full precision-recall curve rather than one threshold** | Most informative; sidesteps the choice | Excellent as a *supplementary* figure and strongly recommended, but the project still needs one concrete operating point for the headline table and for the demo |
| **Threshold per phase (separate P and S thresholds)** | More flexible; S is harder | Legitimate, and arguably better. If adopted, each threshold is still selected on validation only, and the choice is documented |

**5. Advantages.** Test numbers remain a valid estimate of unseen-event performance; the operating point is reproducible; the freeze is auditable; it forces the validation set to be large enough to be useful, which is a healthy constraint.

**6. Disadvantages.** Requires an adequate validation set; can waste information if validation is small; and once frozen, no further improvement to the headline number is possible without a legitimate change of protocol, which must then be recorded and repeated.

**7. Risks.** A protocol changed after seeing test results without disclosure — mitigated by the change-log rules requiring every meaningful change to be documented, including a failure; a validation set too small for a stable threshold — mitigated by reporting the validation sweep and its variability; the temptation to report a "best-of-sweep" test number — mitigated by stating the single frozen threshold in every table (`FR-058`).

**8. Evidence needed.** The validation threshold sweep is now stored in the candidate protocol artifact at `runs/validation_protocol_candidate_seed42/protocol.json` and is explicitly validation-only. EX-5 seed variability, owner/supervisor review of the tolerance and matching policy, and a newly approved baseline checkpoint are still needed before a scientific test result.

**9. Conditions to change.** If the validation set is too small for a stable threshold, the honest response is to change the split ratio (increasing validation) and re-run, not to tune on test. If a per-phase threshold is adopted, the freeze principle is unchanged.

**Evidence class: [ESTABLISHED] principle; [RATIONALE] for the procedure; candidate values are [MEASURED] on the bounded validation subset but remain [PROVISIONAL] and [OPEN] (`OQ-10`, `OQ-11`) for the scientific baseline.**

---

## D-09 — Why controlled noise experiments are needed

**1. Problem being addressed.** The project must "investigate the effect of waveform noise on performance" (`G5`). Waveforms in the wild vary enormously in noise level, and a single average score says nothing about where the model stops working.

**2. Selected approach.** Take one trained model and one fixed test set, degrade the test windows to a series of **controlled** noise levels defined by an explicit SNR definition, keep the noise random seed fixed so the levels are comparable, and measure P and S metrics at each level (`FR-069`, `FR-070`, `FR-071`, EX-4).

**3. Why selected.**

- **[ESTABLISHED]** To attribute a change in performance to noise, noise must be the only thing that changes. Controlling the level isolates the variable; natural noise varies uncontrollably along with everything else.
- **[RATIONALE]** A degradation curve locates the breaking point, which is the actionable output: it tells a user when not to trust the picks, which is exactly the "understanding when the model should not be trusted" outcome `US-13`/`US-14` aim for.
- **[RATIONALE]** Because the test set and model are held fixed, the curve is comparable **across the whole sweep** — whereas comparing metrics computed on different natural-noise subsets confounds noise with event difficulty and distance.
- **[RATIONALE]** Fixing the noise seed (`FR-071`) makes the sweep reproducible and the levels monotone by construction; without it, re-drawing the noise would move the curve for reasons unrelated to the model.

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **Stratify existing test data by measured SNR** | Uses only real noise; no synthetic perturbation | Genuinely attractive and recommended **in addition**: it grounds the synthetic sweep in reality. But it requires a reliable SNR field (`DR-004`, `FR-011`), does not let the level be chosen, and cannot fill gaps where no data exist at intermediate levels |
| **Add real noise recorded from a quiet station** | Realistic noise colour and non-stationarity | Real noise requires a noise dataset that may not be available, and mixing unrelated stations introduces instrument-difference confounds. A strong future refinement |
| **Train with noise augmentation and test without** | Measures robustness benefit | Answers a different question (the value of augmentation). Kept as `FR-072`/EX-4 variant rather than as the noise-robustness study itself |
| **No noise experiment; rely on aggregate metrics** | Saves the whole experiment | Fails the stated objective `G5` outright |

**5. Advantages.** Isolates the variable; produces an actionable degradation curve; ensures all points on the curve are mutually comparable; the same machinery supports the augmentation-comparison variant; and it is honest about being a controlled perturbation rather than a field measurement.

**6. Disadvantages and the necessary honesty.** Added white Gaussian noise is **not** realistic seismic noise. Real seismic noise is coloured (with microseism peaks), non-stationary, spatially correlated and often impulsive. A controlled sweep therefore bounds behaviour under a *controllable perturbation* and does not measure field performance. This limitation (L5, `E35`) must be stated wherever the results appear. Additionally, the SNR definition itself is a choice: whether signal power is measured over the whole window or only the signal portion changes the numbers, so the definition must be published (`OQ-18`, `E36`, `E37`).

**7. Risks.** Over-interpretation of synthetic-noise results (`R-17`) — mitigated by stating L5 in every relevant section; an SNR definition that flatters the baseline (measuring signal power over a mostly-noise window) — mitigated by publishing the definition and, ideally, reporting both conventions; evaluating on difficult real windows only — mitigated by applying the same noise levels to the whole fixed test set so the sweep is complete rather than selective.

**8. Evidence needed.** The degradation curve itself, with the SNR definition published and the noise seed recorded. EX-4 is a mandatory experiment (`SC-4`). **[Not yet produced.]**

**9. Conditions to change.** If the dataset provides a reliable SNR estimate, add the SNR-stratified analysis as a companion and reconcile the two views; if real-noise recordings become available, add a real-noise condition as a third comparison. Neither replaces the controlled sweep, because only the controlled sweep isolates the variable.

**Evidence class: [ESTABLISHED] for the experimental logic; [RATIONALE] for the design; the actual degradation behaviour is [HYPOTHESIS].**

---

## D-10 — Why a simple Python pipeline is preferable to unnecessary infrastructure

**1. Problem being addressed.** What architecture should the project have, given that the deliverable is scientific evidence rather than a product?

**2. Selected approach.** A single-process, single-machine Python pipeline: functions and CLI entry points, YAML configuration, filesystem artifacts, no service, no database, no message queue, no container orchestration (`P-1`, `P-8`; `TECHNICAL_ARCHITECTURE.md` §1, §3, §11, §19).

**3. Why selected.**

- **[RATIONALE]** The stated objectives are: load data, train a model, extract picks, evaluate, visualise, study noise and configuration (`G1`–`G7`). **None requires a service or a database.** Adding one would mean inventing a requirement and then paying its cost.
- **[RATIONALE]** Three competing resources are all scarce and all better spent on the science: development time, debugging surface, and the limited compute budget. A FastAPI + PostgreSQL + orchestration stack adds three failure-prone layers that contribute nothing to the scientific claim.
- **[RATIONALE]** A ~50-line training loop is *explainable in a report*. A framework that hides the training step behind an abstraction makes the report harder to write and the science harder to defend — a real cost in an academic submission.
- **[RATIONALE]** The data format already stores waveforms and metadata efficiently (HDF5 and tabular files). Duplicating that into a database adds a synchronisation problem: two sources of truth that can disagree.
- **[ESTABLISHED]** In research code, the dominant failure mode is not insufficient architecture; it is incorrect logic hidden by complexity. Simplicity is a correctness strategy, not merely a preference.

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **Web application (React + backend + database)** | Polished, multi-user, demo-friendly | A second language, a build pipeline, a larger security surface, and a deployment burden — for a project whose stated scope explicitly excludes deployment claims (`NG1`). The science would be delivered later and less well |
| **Microservices / job queue / orchestrator** | Scales batch experiments | There is one machine and a handful of runs. A job queue is warranted when runs are numerous and long enough to need scheduling; not here |
| **Database for metadata and results** | Queryable, concurrent writes | Single-user, file-sized data. SQLite/files suffice; PostgreSQL is explicitly deferred to a hypothetical scale-up tier that has no current requirement |
| **Experiment-tracking server (hosted)** | Convenient dashboards | Sends data to a third party and adds an account dependency. A local, file-based record plus optional local tracking is enough; hosted tracking is a preference, not a requirement |
| **PyTorch Lightning** | Less boilerplate, callbacks | Legitimate, but its abstractions obscure exactly the parts a report must explain. Listed as a later upgrade if multi-GPU work appears |
| **Notebook-only project** | Fast exploration | Excellent for inspection (`US-01`) but not reproducible end-to-end, and the objective requires a regenerable pipeline (`FR-078`, `SC-6`). Notebooks are used for exploration, not as the delivery vehicle |
| **Container + orchestration from day one** | Environment parity | Useful *later* for the reproducibility tier (`SC-6`). As a starting point it costs setup time before any science happens. A lockfile plus, optionally, one container is the pragmatic minimum |

**5. Advantages.** Minimal debugging surface; low cost; every component explainable; fast iteration; no credential or deployment management; the science stays visible in the code; and the architecture stays *decomposable*, so a layer can be added later without a rewrite (the model code is deliberately independent of any app layer, D-11).

**6. Disadvantages.** Manual file hygiene is required, and the absence of a `.gitignore` right now is precisely this risk materialised (`R-16`). Batch experiments are run manually. There is no dashboard. Reproducibility depends on discipline (lockfile, seeds, saved configs) rather than on a platform enforcing it — which is exactly why those are written down as requirements (`FR-041`, `FR-042`, `FR-082`) rather than left to habit.

**7. Risks.** Discipline decay — mitigated by making the reproducibility items explicit acceptance criteria (`SC-6`) and by the change-log rules; a later scope surge tempting someone to bolt on infrastructure — mitigated by requiring an ADR and a stated requirement before any such addition (`P-8`); accidental artifact commits — mitigated by adding `.gitignore` first (`FR-048`).

**8. Evidence needed.** Not an experiment. The evidence is procedural: the pipeline runs end-to-end from a documented command sequence on a clean checkout (`SC-6`, `FR-078`). This is verifiable, and will be verified at phase P8.

**9. Conditions to change.** A new, *stated* requirement would justify revisiting: many runs needing scheduling, a genuine multi-user demo needing upload storage, or batch inference over data far exceeding one machine. Any such change requires an ADR recording the requirement, the options, and the trade-off accepted. Absent such a requirement, this decision stands.

**Evidence class: [RATIONALE] (engineering and scope reasoning), reinforced by the computation of what the stated objectives actually require.**

---

## D-11 — Why the optional Streamlit interface should come after core validation

**1. Problem being addressed.** There is a plausible, attractive demo (`US-12`): pick a sample, see the waveform, the reference picks, the predicted picks and the probability curves, and slide the threshold. When should it be built?

**2. Selected approach.** The interface is optional, is built only at phase P9, and only after core validation is complete. It wraps the existing inference and plotting code and reimplements no logic (`FR-079`, `FR-081`, `O-Opt5`).

**3. Why selected.**

- **[RATIONALE]** An interface has **nothing to show until a model exists and its picks have been evaluated**. Building it first means building a viewer for outputs that are absent or untrustworthy.
- **[RATIONALE]** Effort is zero-sum. Time spent on a viewer before the baseline, the protocol freeze and the noise study exist is time taken from the deliverables that constitute the actual result (`SC-1`…`SC-10`).
- **[RATIONALE]** The interface is explicitly **optional** — it traces to `O-Opt5`, not to the stated problem statement. Sequencing optional work after mandatory work is straightforward prioritisation (`ROADMAP-001`'s cut list).
- **[RATIONALE]** Wrapping validated code makes the interface cheap and safe. If it were built first, the validation and picking logic would likely be duplicated inside the app, creating two implementations that can disagree — a classic and avoidable bug.
- **[RATIONALE]** It is the natural vehicle for demonstrating threshold behaviour interactively, which is genuinely valuable *once* the threshold is frozen and understood. Before that, a slider invites tuning by eye, which is the opposite of the discipline the protocol freeze establishes (`D-08`).

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **Build the interface first** | Makes a strong early demo; motivates the team | Builds a shell for absent results; consumes the scarcest resource before the science exists; risks duplicating logic. This is the specific failure mode the sequencing rule exists to prevent |
| **Build it in parallel with the model** | Overlaps work | Couples an unstable interface to an unstable API; the two evolve together and neither is checkable in isolation. The interface cannot be validated before the outputs it displays are |
| **Skip the interface entirely; static figures in the report** | Fully sufficient for the stated objectives; zero interface cost | Legitimate and explicitly acceptable — `tech.md` §9 lists this as an open decision. Static figures (`FR-064`–`FR-067`) satisfy `SC-3`. The interface is an enhancement to the *demonstration*, not to the *result* |
| **Gradio instead of Streamlit** | Slightly better for upload-a-file demos | Close alternative; either is fine. Streamlit is preferred because it is Python-only and renders existing figures directly |
| **A FastAPI service instead of an app** | Programmatic access | Adds a second runtime surface and a validation layer for an interactive-viewing requirement that a local app already satisfies. Only warranted if a real programmatic consumer appears |

**5. Advantages.** Optional work is deferred until it can be useful; the app reuses validated code; the demo reflects a *frozen, understood* operating point rather than an exploratory one; and if the optional tier is dropped under time pressure, nothing mandatory is lost.

**6. Disadvantages.** No interactive demo is available early, so none of the informal "look, it works" momentum that a UI provides is available during development. Notebook figures and the plotting functions (`FR-064`) must carry that load in the meantime. This is accepted as the cost of protecting the critical path.

**7. Risks.** Interface creep — the app growing from a viewer into a parallel implementation of validation and picking logic. Mitigated by the architectural rule that the app must call the CLI inference path (`FR-008`, `FR-050`, `FR-079`). Presentational over-claiming in the app (implying operational readiness) — mitigated by `NFR-014` and by not persisting uploads (`FR-080`).

**8. Evidence needed.** Not an experiment. At phase P9, the acceptance evidence is that the app starts with one documented command and renders the required four elements for a selected sample, while calling the same validation and picking functions as the CLI. This is verifiable by inspection and by running it.

**9. Conditions to change.** If an evaluator's marking scheme explicitly rewards an interactive demonstration, the priority of P9 rises — but it still follows the protocol freeze, because a demo built on an unfrozen threshold would display an operating point that is not the reported one. If a *programmatic* consumer appears (for example, a batch-inference requirement), that is a new requirement and would be handled as a new ADR rather than by expanding the viewer.

**Evidence class: [RATIONALE] (dependency ordering and effort allocation); the decision to build it at all remains [OPEN] (`OQ-1`-adjacent, `tech.md` §9).**

---

## D-12 — Why reproducible configurations and checkpoints matter

**1. Problem being addressed.** A research result is only a result if it can be traced to the exact conditions that produced it and reproduced by someone else. `G7` and `SC-6` make this a stated objective, not a nicety.

**2. Selected approach.** Configuration is externalised to YAML, validated, snapshotted beside the checkpoint and hashed; seeds are set and recorded; the split is persisted; checkpoints are saved weights-only with a defined metadata set; dependencies are pinned; and a documented command regenerates the reported tables and figures from saved artifacts (`FR-041`, `FR-042`, `FR-046`, `FR-047`, `FR-078`, `FR-082`).

**3. Why selected.**

- **[ESTABLISHED]** The set of quantities that determine a training result — code version, dependency versions, data split, seed, hyperparameters, test protocol — is large and mostly invisible. If any of them is siloed in someone's memory or in a notebook cell, the result is not a result.
- **[RATIONALE]** A bare weights file is not a trained model in any meaningful sense: without its config, its split and its selection criterion, the weights cannot be interpreted and cannot be honestly compared with anything. Treating the checkpoint as an **artifact set** rather than a file is what makes comparison possible (`FR-047`).
- **[RATIONALE]** A *hashed, snapshotted* config makes "did this run use σ = 10 or σ = 20?" a lookup rather than a hypothesis. This directly prevents the most common form of accidental dishonesty in a student project: an inability to say what was actually run.
- **[RATIONALE]** Regeneration **from saved artifacts**, independent of retraining, is what makes verification affordable for a reviewer (`SC-6`). If verification required retraining, no reviewer would do it, and the reproducibility claim would be decorative.
- **[RATIONALE]** Pinned dependencies prevent "works on my machine" and re-run drift, and the audit already found a live instance of this hazard: `tech.md` recommends Python 3.11/3.12, the machine has 3.14.3, and the installed PyTorch is CPU-only (`R-15`).
- **[RATIONALE]** The seeding decision interacts with honesty about what remains non-deterministic: GPU operations are not bit-reproducible, so the requirement is a stated tolerance, not bitwise identity (`NFR-001`, `US-07`). Claiming perfect reproducibility on GPU would be false.

**4. Alternative approaches considered.**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| **"The Git commit is the record"** | Zero extra effort | Records code, not data split, not seed, not the runtime dependency set, and not which config was used. Insufficient |
| **Config values hard-coded in modules** | Simple to write | A change requires a code edit, so the "config" of a run is a code diff; two runs cannot be compared cleanly; fails `FR-077` |
| **Notebook-recorded runs** | Fast | Not reproducible end-to-end, no artifact contract, and the run history lives outside version control |
| **Save the checkpoint only** | Minimal storage | The checkpoint becomes uninterpretable; comparisons are impossible; `FR-047` fails |
| **Bitwise-exact reproducibility as the target** | Strongest claim | Not achievable on GPU and not achieved on CPU across library versions. The honest target is a documented tolerance |
| **Full data versioning tool (DVC) from the start** | Tracks large data formally | The actual need — a persistent, auditable, event-level split — is satisfied by committing small split files (`FR-005`). DVC is an option if data versioning becomes a real requirement, not a starting necessity |
| **Hosted experiment tracking** | Convenient diffing of runs | Introduces a third-party dependency and an account; a local file-based record meets the requirement. Optional and local if adopted |

**5. Advantages.** Every reported number is traceable to a config, seed, split and checkpoint; comparisons between runs are valid because only the intended factor differs; a reviewer can verify cheaply; and the practice prevents the silent, self-flattering errors that no amount of modelling rigour can compensate for. It also makes the change-log meaningful, because each change can be tied to a concrete artifact set.

**6. Disadvantages.** Real ongoing overhead: every run must write its config and manifest, splits must be managed, artifacts must be organised, and `.gitignore` discipline is mandatory (a discipline the repository currently lacks entirely — `R-16`). There is also a mild storage cost and a mild friction cost at the start of every experiment. The overhead is deliberately accepted, because the alternative is unreproducible work, which is the one outcome the project explicitly defines as failure (`SC-6`).

**7. Risks.** Artifact sprawl and large files leaking into Git (mitigated by `.gitignore` first at P0, `FR-048`); metadata omitted from a checkpoint set making it partially uninterpretable (mitigated by `FR-047`'s required four fields: config, seed, split id, selecting metric); seeds set inconsistently across libraries (mitigated by centralised seeding at the training entry point, `FR-041`); a lockfile that drifts from the environment actually used (mitigated by adding a dependency-audit step and by resolving the Python version question at P0, `R-15`).

**8. Evidence needed.** Procedural and verifiable: at phase P8, a clean clone followed by the documented install, data, evaluate and regenerate commands must reproduce the reported tables and figures, with any residual hardware-dependent variation stated. Failure to reproduce is itself a reported outcome, not something to conceal (the change-log rules require disclosing unverified behaviour).

**9. Conditions to change.** If data versioning becomes a genuine requirement — for example, experiments must cite specific dataset snapshots — a data-versioning tool becomes justified and would be added via an ADR. If training moves to a multi-node setup, tracking and orchestration needs increase. Absent such changes, the reasoning above holds, and the priorities within this decision are ordered: **saved splits and config snapshots first**, seeds second, pinned dependencies third, and optional tracking last.

**Evidence class: [ESTABLISHED] for the principle; [RATIONALE] for the specific mechanism; the reproducibility claim is currently [UNVERIFIED] because no pipeline exists yet.**

---

## D-13 (supporting) — Why Gaussian target curves rather than exact indices

**1. Problem being addressed.** How should a reference onset be represented as a training target, given that a reference onset is itself an uncertain judgement (`PRD.md` §4.5)?

**2. Selected approach.** Smooth, peaked (Gaussian-shaped) P and S target curves centred on the reference pick, with the noise target as the remainder so that P + S + noise = 1 per sample (`FR-022`, `FR-023`, `SR-006`).

**3. Why selected.**

- **[ESTABLISHED]** A hard one-hot target asserts that the true onset is exactly one sample. Given analyst-to-analyst disagreement of typically a few samples for clear P and more for S, that assertion is false, and a loss function built on it penalises a correct prediction. A smooth target encodes the tolerance in the label itself.
- **[RATIONALE]** A smooth target produces a smooth probability curve whose peak is locatable by `find_peaks`, which is what makes `FR-050` straightforward.
- **[RATIONALE]** The Gaussian is parameterised by a single width σ, which is directly interpretable (it is the label smoothing scale) and easy to ablate.
- **[RATIONALE]** It is the convention of the PhaseNet lineage, which keeps the project "inspired by" an established approach rather than inventing a target representation (`NG5`).

**4. Alternatives.** One-hot labels with a classification loss — rejects correct-but-offset predictions and gives a spiky, threshold-sensitive output. Direct time regression — unstable, no ambiguity representation, no noise channel. A logistic/step-shaped target — sharper but still injects an arbitrary width, with less convenient peak behaviour. Rectangular finite-width targets — equivalent in spirit but produce flat plateaus whose peak location is ambiguous.

**5. Advantages.** Tolerates label uncertainty; yields peak-pickable curves; one interpretable parameter; consistent with the reference approach; and the noise remainder keeps the three classes coherent.

**6. Disadvantages.** σ is an additional parameter that must be justified rather than derived (`OQ-8`); targets at window edges are truncated (`E6`); when P and S targets overlap for close-in events, the noise remainder is squeezed and must be clipped (`E4`); and a wide σ can blur two close arrivals into one peak.

**7. Risks.** σ mismatched to the dataset's label jitter (too narrow reintroduces the exact-index problem, too wide merges arrivals) — mitigated by making σ an ablation factor (EX-2); unbounded overlap damage in near-source cases — mitigated by inspecting the S-P distribution and treating overlap as a reported limitation (`OQ-22`).

**8. Evidence needed.** EX-2 varies σ and measures the effect on P and S metrics and on residual spread. Characterising the chosen dataset's reference-pick uncertainty, where the dataset provides quality information, would give an evidence-based σ rather than a convention. **[Neither exists yet.]**

**9. Conditions to change.** If the dataset supplies per-pick uncertainty, σ could be made *pick-dependent* rather than global — a refinement worth documenting. If σ has no measurable effect across the ablation range, that is a finding that simplifies the model. If overlapping targets demonstrably dominate errors on near-source events, an alternative treatment for those events would be justified.

**Evidence class: [ESTABLISHED] for label smoothing as a principle; [PROPOSED] for Gaussian shape and σ = 10 samples; [HYPOTHESIS] that this σ is adequate here.**

---

## D-14 (supporting) — Why one-factor-at-a-time rather than a grid search

**1. Problem being addressed.** The project must investigate how "selected training configurations" affect performance (`G6`). Which experimental design?

**2. Selected approach.** One-factor-at-a-time (OFAT): a documented baseline, then a set of runs each changing exactly one factor, reported in a single comparable table, with results interpreted against the seed-variability noise floor (`FR-073`, `SR-017`, EX-2, EX-5).

**3. Why selected.**

- **[RATIONALE]** Attribution is unambiguous: if one factor changed, any difference is attributable to it (subject to seed noise). A grid search leaves the effect of a factor entangled with the other factors' settings unless a full factorial analysis is performed.
- **[RATIONALE]** Cost. A grid over only five factors at three levels is 243 runs. At a plausible single-run cost on a free-tier GPU with a limited budget, that is not achievable — and an ambitious design that cannot be finished produces *no* comparable results, whereas a modest design that is completed produces defensible ones.
- **[RATIONALE]** OFAT is explainable and easy to audit in a report (`US-15` explicitly asks for "one changed factor per row").
- **[DERIVED]** It pairs naturally with the seed-variability experiment: EX-5 supplies the noise floor without which an OFAT difference cannot be interpreted at all.

**4. Alternatives.** Full factorial grid — detects interactions, at a cost this project cannot bear. Random/grid search for hyperparameter optimisation — optimises a score rather than attributing effects, and risks overfitting the validation set. Bayesian optimisation — efficient for tuning, but its output is a suggested configuration, not an explanation, which is the opposite of the stated objective. Fractional factorial — attractive in principle (screens many factors with fewer runs) but requires assumptions about negligible interactions that this project has no evidence for.

**5. Advantages.** Attributable, affordable, explainable, and completable. Directly satisfies `US-15` and `FR-073`.

**6. Disadvantages.** Cannot detect interactions. A factor that helps only in combination with another would be missed — for example, noise augmentation might only help at one particular σ. The honest position is to state this limitation rather than to imply the ablation is exhaustive, and to allow a follow-up run if the OFAT table suggests an interaction worth probing.

**7. Risks.** Treating a small difference as real when it is within seed noise — mitigated by EX-5 being run before or alongside EX-2; unbounded factor list making the ablation incomplete — mitigated by fixing a short list (`OQ-12`) and declaring what was and was not tested; resource cost of a gain being hidden — mitigated by reporting training time, peak memory and parameter count alongside each row (`EXPERIMENT_PLAN.md` §5).

**8. Evidence needed.** EX-2's table plus EX-5's spread. The interpretation rule is explicit: a difference smaller than the observed seed-to-seed spread is **not** claimed as an effect. **[Neither exists yet.]**

**9. Conditions to change.** If the completed OFAT table shows a strong, unexplained factor effect, a small targeted interaction experiment is justified. If the compute budget turns out to be larger than assumed (`OQ-20`), a fractional-factorial screen becomes reasonable. Absent those, OFAT stands.

**Evidence class: [RATIONALE] (experimental design and budget reasoning); [HYPOTHESIS] that the chosen factors matter at all.**

---

## Appendix A — Decisions that remain provisional

| Item | Provisional value or choice | Resolving item |
|---|---|---|
| Window length | 3072 samples, `[PROPOSED]` | `OQ-4`, dataset choice |
| Sampling rate | 100 Hz, `[PROPOSED]` | `OQ-4` |
| Gaussian σ | 10 samples, `[PROPOSED]` | `OQ-8`, EX-2 |
| Loss function | soft cross-entropy, `[PROPOSED]` | `OQ-9`, EX-2 |
| Model depth / width / kernel | 4 / 16 / 7, `[PROPOSED]` | `OQ-12`, EX-2 |
| Batch size, epoch budget | not fixed | `OQ-20` |
| Checkpoint-selection criterion | lowest validation loss recorded by the bounded pilot; not pre-registered for a scientific baseline | `OQ-021` |
| Picking threshold | candidate validation sweep selected P `0.05`, S `0.10`; same-subset selection/reporting means values remain provisional | `OQ-10`, `FR-051` |
| Multi-peak rule | strongest retained interior maximum; candidate/edge counts are reported | `OQ-10`, `FR-052` |
| Evaluation tolerance | candidate `20` samples (`200 ms` at `100 Hz`); not owner-approved as final | `OQ-11`, `SR-016` |
| SNR definition for the noise study | not fixed | `OQ-18` |
| P-after-S enforcement | report the count without reordering or repair; enforcement remains open | `OQ-17` |
| Split ratios | ~70/15/15 suggested | `OQ-5` |
| Filter usage and band | undecided | `OQ-6` |
| Noise-window fraction | undecided | `OQ-7` |
| Optional interface | optional; whether it is built at all is open | `OQ-1`-adjacent, `tech.md` §9 |
| Ablation factor list | open | `OQ-12` |
| Whether numeric performance targets are wanted | no targets set | `OQ-19` |

---

## Appendix B — What would constitute a "[MEASURED]" decision

The bounded pilot has measured a validation-only operating point, but that evidence is not enough to mark a scientific decision as validated. To move a decision from `[RATIONALE]` or `[PROVISIONAL]` to a scientific `[MEASURED]` decision, the following must exist:

1. A verified data path (so that a change in metrics cannot be caused by a data bug).
2. A frozen evaluation protocol with a declared tolerance and matching rule.
3. A completed baseline run recorded as an artifact set (config, seed, split, checkpoint).
4. Seed-variability information, so that a difference can be distinguished from noise (EX-5).
5. The specific controlled comparison the decision depends on (EX-2 for architecture, σ, and loss; EX-4 for noise; EX-3 for data fraction).

Until items 1–5 exist, every statement in this document about SeismoNet's *scientific performance* or about the *superiority* of the chosen design is reasoning, not evidence. The candidate validation artifact is evidence that the pipeline ran and that the selected operating point is reproducible on that bounded validation subset; it is not a generalization claim.

# SeismoNet — Testing Strategy

**Document ID:** TEST-001
**Version:** 1.0
**Date:** 2026-10-18
**Status:** Draft for approval — catalogue plus implemented offline/unit/integration tests; no CI workflow

---

## 0. Status statement — read this first

> **The SeismoNet repository now has executable source and tests.** The current working tree contains `src/`, `tests/`, a `pyproject.toml`, real split files and ignored pilot/validation artifacts. The historical audit in `AUDIT_REPORT.md` records the repository state before implementation and is not the current implementation status.
>
> **This document is both a test strategy and a traceability catalogue.** The implemented suite currently passes `206` tests with `1` intentional skip in the Windows `.venv`; rows still marked **PLANNED** remain future coverage, not claimed results.
>
> **Component labelling rule used throughout.** Each component is either **EXISTING**, **IMPLEMENTED**, or **PLANNED**. Historical specification rows retain their planned labels; the current source and test files are verified separately in `PROJECT_STATUS.md` and the change-log.

This strategy is the testing counterpart of [`SYSTEM_FLOW.md`](SYSTEM_FLOW.md) (workflow stages) and must be read with [`../PRD.md`](../PRD.md) (requirements), [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md) (phases P0–P9), [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) (artifact and data policy), and [`TECH_STACK.md`](TECH_STACK.md) (tooling choices). It does not redefine requirements; it specifies how each is verified.

---

## 1. Purpose, scope and status

### 1.1 Purpose

To define **what must be tested**, at which level, with which fixture, against which requirement, and what breaks if the test is absent. The strategy also records the boundary between implemented checks and planned coverage so later work does not mistake a test specification for executed evidence.

### 1.2 Scope

This strategy covers automated and semi-automated verification of the core pipeline: data ingestion and validation, preprocessing, label generation, event-level splitting and leakage, augmentation, model shape, the training smoke test, determinism, inference and pick extraction, timestamp conversion, and evaluation metrics. It defines the synthetic fixture, the test-data policy, a planned CI pipeline, coverage expectations, explicit exclusions, the definition of done for a code change, and full traceability.

### 1.3 Status

- **Implemented tests:** `tests/` contains the current offline/unit/integration suite; `.venv\Scripts\python.exe -m pytest tests -q` → **214 passed, 1 skipped** on 2026-10-18.
- **CI: none.** No `.github/workflows/` exists (`AUDIT_REPORT.md` §12). The CI plan in §7 is **PLANNED**.
- **Fixtures:** in-memory synthetic fixtures are implemented across the tests; the real INSTANCE sample is used only by explicitly executed validation/pilot runs.
- **Dependencies:** pytest 9.1.1 and the project `.venv` are verified; no CI workflow exists.
- **Verification method of this document:** INSP plus the executed test command above; individual planned rows remain INSP/PLANNED until implemented.

### 1.4 Relationship to the original testing recommendation

`archive/tech-v0.1-original.md` §5 already recommended: pytest unit tests for labels, pick extraction and metrics; a data-leakage test for zero shared event IDs; model shape/softmax/depth tests; an overfit-tiny-batch sanity test; a determinism test; parametrised edge-case tests; a tiny synthetic waveform fixture for the full chain; CI with ruff then pytest on CPU that never downloads the full dataset. **This strategy builds on that recommendation and does not contradict it.** It adds explicit test IDs, fixtures, failure modes, per-requirement and per-phase traceability, a test-data policy, and a definition of done.

---

## 2. Testing principles

1. **Test core logic without the full dataset.** Labels, picking, metrics, splitting, shapes and timestamp conversion are pure or near-pure logic and must be testable with small in-memory arrays. No unit test may require the real dataset.
2. **Use a tiny synthetic fixture with a known clean P and S onset as ground truth.** The fixture (§5) has P and S indices known by construction, so every assertion about a pick or a target has an unambiguous expected value. Ground truth the test author controls is worth more than a large unlabelled sample.
3. **Never let a test download the full dataset.** Tests must run offline. If a network call is unavoidable for an optional integration check, it must be skipped by default, not required.
4. **Fail loudly.** A test that cannot establish its precondition must error, not skip silently and not pass vacuously (`NFR-004`). An ambiguous precondition is treated as a fault in the test.
5. **Deterministic by construction.** Any test involving randomness sets a fixed seed, or asserts that a fixed seed reproduces the result (`FR-041`, `FR-026`, `FR-071`).
6. **One requirement, one observable assertion.** Each test asserts an observable fact traceable to a requirement ID, so a failure names the requirement it violates.
7. **Test the guards, not just the happy path.** The event-overlap check (`FR-025`), the depth-compatibility assertion (`FR-036`) and the zero-denominator convention (`FR-062`) are tested explicitly, because their absence is what silently invalidates results.

---

## 3. Test levels

| Level | Definition | Typical scope | Runs offline | Typical fixture |
|---|---|---|---|---|
| **Unit** | A single function or pure logic unit in isolation. | label curves, peak selection, metric maths, timestamp conversion, augmentation toggles | Yes | tiny arrays / synthetic fixture |
| **Integration** | Two or more modules composed. | load → validate → preprocess → labels; split → loaders | Yes | synthetic fixture set |
| **Data validation** | Schema and signal-quality checks on load. | metadata schema, NaN/flat/missing-component screening | Yes | synthetic fixture variants |
| **Model shape** | Shape, dtype and normalisation assertions on the network. | output length, 3 channels, softmax sum, depth compatibility | Yes | none (random tensors) |
| **Training smoke** | Minimal training run on a tiny batch. | loss decrease, overfit-to-near-zero | Yes | synthetic fixture batch |
| **Inference** | Input validation, probability output, pick and count behaviour. | reject invalid input, "no pick", multi-peak rule, ordering counts | Yes | synthetic fixture + crafted curves |
| **Timestamp** | Index ↔ seconds ↔ absolute-time conversion. | hand-computed expected values | Yes | fixture with a known rate and start time |
| **Leakage** | Event-level split integrity. | zero event-ID overlap, training-start guard | Yes | multi-event synthetic fixture |
| **Evaluation** | Metrics and matching behaviour. | TP/FP/FN, residuals, zero denominators, P/S separation | Yes | hand-computed pick pairs |
| **End-to-end** | Full pipeline on the tiny fixture. | load → ... → metrics table | Yes | synthetic fixture + saved artifact |

---

## 4. Test catalogue

The table below is the specification of every test to be written. Columns: **Test ID**, **Level**, **Module under test (proposed path)**, **What is verified**, **Fixture needed**, **Requirement ID**, **Expected failure mode if the test is missing**.

Indicative test IDs are allocated in blocks: `T-001`–`T-009` data validation and dataset ingestion; `T-010`–`T-016` label generation; `T-017`–`T-023` preprocessing; `T-024`–`T-027` augmentation; `T-028`–`T-032` channel ordering and input validation; `T-033`–`T-038` model shape; `T-039`–`T-040` training smoke; `T-041`–`T-042` determinism; `T-043`–`T-045` splitting and leakage; `T-046`–`T-052` pick extraction; `T-053` timestamp; `T-054`–`T-060` evaluation; `T-061`–`T-062` end-to-end and reproducibility; `T-063` optional interface; `T-064` visualisation; `T-065`–`T-066` experiments.

### 4.1 Data validation and dataset ingestion

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-001 | Data validation | `src/data/load_dataset.py` | Loader returns, per trace: three-component waveform, sampling rate, reference P and S indices, and available metadata. | Synthetic fixture (single trace) | `FR-001` | Loader returns wrong field order or omits picks; every downstream stage works on mis-shaped data |
| T-002 | Data validation | `src/data/validate.py` | Dataset summary statistics: trace count, pick availability, sampling-rate distribution, metadata distributions. | Multi-trace fixture | `FR-002` | Dataset assumptions (rate, pick coverage) go unchecked |
| T-003 | Data validation | `src/data/validate.py` | A trace containing NaN/Inf is excluded and logged with its ID and reason. | NaN fixture | `FR-003`, `E10` | NaNs propagate into normalisation and the model |
| T-004 | Data validation | `src/data/validate.py` | A flat (zero-variance) trace is excluded and logged. | Flat fixture | `FR-003`, `E11` | Division by zero in normalisation; silent NaNs |
| T-005 | Data validation | `src/data/validate.py` | A trace with a missing component is excluded (or handled by a stated policy) and logged. | Two-component fixture | `FR-003`, `E12` | Shape error surfaces deep in the model with an unclear cause |
| T-006 | Data validation | `src/data/validate.py` | A trace at a sampling rate inconsistent with the expected rate is excluded or explicitly resampled, and logged. | Wrong-rate fixture | `FR-003`, `SR-003`, `E18` | Silent rate mixing corrupts every sample index and label |
| T-007 | Data validation | `src/data/validate.py` | A reference pick pair with S ≤ P is flagged as a data-quality error and logged. | Fixture with S ≤ P | `FR-003`, `E5` | Invalid labels used as ground truth; residuals meaningless |
| T-008 | Unit | `src/data/load_dataset.py` | Event-ID construction from metadata is deterministic and correct on synthetic metadata rows. | Two metadata rows | `FR-010` | Splitting by trace, not event → leakage |
| T-009 | Data validation | `src/data/validate.py` | Metadata schema check rejects a malformed row with a specific error. | Malformed metadata row | `FR-001`, `NFR-004` | Malformed data loaded silently; failures appear far from their cause |

### 4.2 Label (target) generation

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-010 | Unit | `src/data/labels.py` | The P target peaks exactly at the reference P index. | Fixture with known P index | `FR-022` | Mis-centred P targets; model learns a biased P picker |
| T-011 | Unit | `src/data/labels.py` | The S target peaks exactly at the reference S index. | Fixture with known S index | `FR-022` | Mis-centred S targets; the weaker phase is corrupted first |
| T-012 | Unit | `src/data/labels.py` | P + S + noise = 1 at every sample, within floating-point tolerance, including when P and S targets overlap. | Fixture + overlap case | `FR-023`, `E4` | Targets are not a valid probability distribution; training objective ill-defined |
| T-013 | Unit | `src/data/labels.py` | A window lacking a phase yields an all-zero target for that phase and a non-zero target for the present phase. | Windows lacking S and lacking P | `FR-024`, `E1`, `E2` | Fabricated labels for absent phases; false ground truth |
| T-014 | Unit | `src/data/labels.py` | Target array length equals the input window length. | Fixture | `FR-021` | Shape mismatch between input and target; loss computes incorrectly |
| T-015 | Unit | `src/data/labels.py` | Changing σ changes the Gaussian width as configured, and the peak stays at the reference index. | Fixture, two σ values | `FR-022`, `OQ-8` | Label width silently fixed; the σ ablation is invalid |
| T-016 | Unit | `src/data/labels.py` | The noise target stays non-negative after clipping when P and S targets overlap. | Overlap fixture | `FR-023`, `E4` | Negative noise targets; degenerate probabilities |

### 4.3 Preprocessing

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-017 | Unit | `src/data/preprocess.py` | After detrend and demean, each channel has zero mean within tolerance. | Fixture (offset + trend) | `FR-013` | DC offset and drift corrupt normalisation and the input |
| T-018 | Unit | `src/data/preprocess.py` | Normalising a flat channel does not produce NaN or Inf. | Flat window | `FR-014`, `E11` | Divide-by-zero NaNs poisoning the batch |
| T-019 | Unit | `src/data/preprocess.py` | Resampling a known synthetic waveform yields the expected length and preserves the phase position within tolerance. | Synthetic waveform with known onset | `FR-016`, `SR-003`, `E18` | Phase indices shift silently under resampling |
| T-020 | Unit | `src/data/preprocess.py` | Anti-aliasing is applied before downsampling. | Synthetic tone + downsample | `FR-016`, `E18` | Aliased energy creates spurious features and false picks |
| T-021 | Unit | `src/data/preprocess.py` | Every emitted window has exactly `L` samples and three channels. | Fixture | `FR-017` | Variable window lengths break batching and skip-connection alignment |
| T-022 | Unit | `src/data/preprocess.py` | Train and evaluation paths produce identical output for identical input (augmentation excluded). | Fixture | `FR-020`, `FR-021` | Train/eval preprocessing drift invalidates evaluation |
| T-023 | Unit | `src/data/preprocess.py` | Randomised window start yields a broad pick-position distribution, not concentrated at one offset. | Many sampled windows | `FR-018`, `R-04` | Model learns pick position rather than waveform features |

### 4.4 Augmentation

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-024 | Unit | `src/data/dataset.py` | Each augmentation is independently switchable; enabling one leaves the others unchanged. | Fixture + config matrix | `FR-028` | Ablations are confounded; `EX-2` cannot attribute differences |
| T-025 | Unit | `src/data/dataset.py` | Noise addition is switchable separately from all other augmentations. | Fixture + toggle | `FR-029` | The noise-augmentation study (`FR-072`) is impossible to isolate |
| T-026 | Unit | `src/data/dataset.py` | Augmentation is applied to training only; validation/test paths return the unmodified signal for a fixed seed. | Fixture + fixed seed | `FR-030` | Test-time augmentation inflates or deflates reported metrics silently |
| T-027 | Unit | `src/data/dataset.py` | A shift augmentation moves the target peaks by exactly the applied shift. | Fixture | `FR-031` | Labels and waveform fall out of alignment under augmentation |

### 4.5 Channel ordering and input validation

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-028 | Inference | `src/data/validate.py` | An input with the wrong number of components is rejected with a logged reason. | Two-channel input | `FR-008`, `SR-001`, `E12` | Wrong-shape inputs cause obscure model errors or silent corruption |
| T-029 | Inference | `src/data/validate.py` | An input at the wrong sampling rate is rejected or explicitly resampled, never silently accepted. | Wrong-rate input | `FR-008`, `SR-003`, `E18` | Rate mismatch silently mislabels every pick |
| T-030 | Inference | `src/data/validate.py` | An input containing NaN/Inf is rejected. | NaN input | `FR-008`, `E10` | Inference returns meaningless probabilities on invalid data |
| T-031 | Inference | `src/data/validate.py` | A flat input is rejected. | Flat input | `FR-008`, `E11` | Normalisation divides by zero; result is fabricated |
| T-032 | Unit | `src/data/validate.py` | Channel order is asserted to be `(Z, N, E)`; a trace whose order cannot be established is excluded. | Reordered-component fixture | `SR-002` | Horizontals swapped → S-wave learning corrupted while the pipeline appears to work |

### 4.6 Model shape

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-033 | Model shape | `src/model/unet1d.py` | Output length equals input length for several valid `L`. | None (random tensors) | `FR-034` | Misaligned output; per-sample targets and outputs do not correspond |
| T-034 | Model shape | `src/model/unet1d.py` | The output has exactly three channels (P, S, noise). | None | `FR-033` | Channel/class count mismatch; softmax over the wrong axis |
| T-035 | Model shape | `src/model/unet1d.py` | The three output probabilities sum to 1 per sample within tolerance. | None | `FR-037` | Outputs are not a probability distribution; threshold semantics undefined |
| T-036 | Model shape | `src/model/unet1d.py` | Constructing the model with `L` not divisible by `2^depth` raises a specific, readable error. | None | `FR-036` | Shape error appears as an opaque runtime failure deep in the decoder |
| T-037 | Model shape | `src/model/unet1d.py` | Depth, base channel count and kernel size are configurable and change the model as expected. | None | `FR-035` | The architecture ablation (`FR-073`) cannot vary these factors |
| T-038 | Unit | `src/model/unet1d.py` | The parameter count is reported. | None | `FR-038` | Cost of an ablation cannot be weighed against its benefit |

### 4.7 Training smoke test

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-039 | Training smoke | `src/train/train.py` | Overfitting a tiny fixed batch drives loss to near zero. | Synthetic batch | `FR-044`, `US-06` | A broken loss, optimiser or label wiring is discovered only after a long run |
| T-040 | Training smoke | `src/train/train.py` | Loss decreases over a short run on a small synthetic dataset. | Synthetic dataset | `FR-039` | Training that does not learn is mistaken for a modelling limitation |

### 4.8 Determinism

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-041 | Unit | `src/train/train.py` | The same seed and config reproduce the same result on CPU within a stated tolerance. | Fixture + fixed seed | `FR-041`, `NFR-001` | Reported results are not reproducible; `SC-6` fails |
| T-042 | Unit | `src/data/split.py` | The same seed and input metadata produce byte-identical split files. | Fixture | `FR-026`, `FR-005` | Split membership changes between runs; results cannot be compared |

### 4.9 Splitting and leakage

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-043 | Leakage | `src/data/split.py` | Zero event-ID overlap across train, validation and test (run as an automated check). | Multi-event fixture | `FR-004`, `FR-005`, `FR-025`, `NFR-003`, `SC-8` | Event leakage inflates metrics; the project's core claim is invalid |
| T-044 | Leakage | `src/train/train.py` | Training start aborts loudly when a split overlap is detected (the guard, not just the test). | Crafted overlapping split | `FR-025`, `NFR-003` | A leaky split reaches training and produces a false result before anyone notices |
| T-045 | Unit | `src/data/split.py` | Changing the split-ratio configuration changes the split proportions as expected. | Fixture | `FR-006` | Ratios are hard-coded; `OQ-5` cannot be explored and recorded |

### 4.10 Pick extraction

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-046 | Inference | `src/infer/pick.py` | No peak above threshold yields an explicit "no pick" object, not a number or placeholder. | All-noise / flat-curve fixture | `FR-009`, `SR-013`, `E26` | A fabricated pick corrupts residuals and precision/recall accounting |
| T-047 | Inference | `src/infer/pick.py` | A single peak above threshold is selected at the correct sample index. | Fixture with one peak | `FR-050` | Peak selection is wrong; the core pick is incorrect |
| T-048 | Inference | `src/infer/pick.py` | Multiple peaks above threshold invoke the documented rule and return exactly one pick per phase. | Curve with two peaks | `FR-052`, `SR-012`, `E27` | Non-deterministic multi-pick behaviour; metrics depend on run |
| T-049 | Inference | `src/infer/pick.py` | A peak at or near the window edge is handled by the stated rule, not by a crash or silent drop. | Edge-peak fixture | `FR-050`, `E6` | Edge cases silently skipped or crash; recall overstated |
| T-050 | Inference | `src/infer/pick.py` | The threshold is configurable and the selection changes accordingly. | Fixture + two thresholds | `FR-051` | Threshold is hard-coded; validation-only selection cannot be demonstrated |
| T-051 | Inference | `src/infer/pick.py` | A predicted P after predicted S is counted and reported, not silently corrected. | Crafted P/S ordering | `SR-015`, `FR-054`, `E29` | Physically implausible outputs hidden; failure rate unknown |
| T-052 | Inference | `src/infer/pick.py` | Counts of multi-peak, "no pick" and P-after-S outcomes are produced and reported. | Fixture | `FR-054` | These outcomes silently discarded; evaluation denominators wrong |

### 4.11 Timestamp conversion

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-053 | Timestamp | `src/infer/timestamp.py` | Sample index → seconds → absolute time against hand-computed values, using `seconds = sample_index / sampling_rate` and `absolute = trace_start_time + seconds`. | Fixture with known rate and start time | `FR-053`, `SR-014` | Systematic time offset in every pick; residuals biased and results wrong |

### 4.12 Evaluation

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-054 | Evaluation | `src/eval/metrics.py` | Hand-computed TP/FP/FN cases reproduce the expected precision, recall and F1. | Hand-computed pick pairs | `FR-057`, `FR-059` | Metric implementation error goes unnoticed; scores are wrong |
| T-055 | Evaluation | `src/eval/metrics.py` | An out-of-tolerance pick is counted under the stated convention (as both FP and FN). | Hand-computed out-of-tolerance pick | `FR-059`, `../PRD.md` §12.2 | Reported scores use a different convention than declared; comparisons invalid |
| T-056 | Evaluation | `src/eval/metrics.py` | A zero denominator returns a defined value and reports the zero denominator. | No-reference-phase case | `FR-062`, `E32` | Metrics return NaN/undefined; tables unreadable and unreproducible |
| T-057 | Evaluation | `src/eval/metrics.py` | The residual sign convention `pred − ref` matches its definition on hand-computed picks. | Hand-computed picks | `FR-055` | Residual sign is inverted; bias conclusions are reversed |
| T-058 | Evaluation | `src/eval/metrics.py` | P and S are computed and reported separately; no combined-only score is produced. | Fixture | `FR-060` | Weak S performance averaged away by strong P (`R-05`) |
| T-059 | Evaluation | `src/eval/metrics.py` | The tolerance is configurable and present in the emitted result. | Fixture + two tolerances | `FR-058`, `SR-016` | A result table without a tolerance is uninterpretable |
| T-060 | Evaluation | `src/infer/pick.py` + `src/eval/metrics.py` | A synthetic waveform with a known P time yields a P pick within the documented tolerance. | Fixture with known P onset | `FR-050` | The end-to-end pick path is wrong but each unit looks correct |

### 4.13 End-to-end and reproducibility

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-061 | End-to-end | whole pipeline | The tiny fixture flows load → validate → preprocess → labels → split → model → one training step → inference → evaluation and produces a metrics table. | Synthetic fixture | `FR-078`, `SC-6` path | Module interfaces are incompatible; integration bugs found only during real runs |
| T-062 | End-to-end | documented regeneration command | The documented regeneration command reproduces a saved metric table from saved artifacts. | Fixture + saved artifact | `FR-078`, `SC-6` | `SC-6` fails: a reviewer cannot reproduce the reported table |

### 4.14 Optional interface, visualisation and experiments

| Test ID | Level | Module under test (proposed path) | What is verified | Fixture needed | Requirement ID | Expected failure mode if missing |
|---|---|---|---|---|---|---|
| T-063 | End-to-end (OPTIONAL) | `app/streamlit_app.py` | If built: the interface starts, renders waveform, picks and probability curves, and returns a result for a supported recording. | Fixture | `FR-079`, `FR-080` | Optional interface breaks silently; `O-Opt5` acceptance unverified |
| T-064 | Unit | `src/viz/plots.py` | Plotting functions return a figure without error on the fixture and include the threshold line. | Fixture | `FR-064`, `FR-065` | Figures fail only at report time; visual verification impossible |
| T-065 | Unit | noise generator | A fixed noise seed reproduces the same noise realisation at every noise level. | Fixture + fixed seed | `FR-071`, `E38` | Noise-sweep results are not comparable between runs |
| T-066 | Unit | `src/experiments/run.py` | A one-factor-at-a-time configuration changes exactly one factor from the baseline. | Two configs | `FR-073`, `SR-017` | Ablations confounded; differences cannot be attributed |

---

## 5. The synthetic seismic fixture

### 5.1 What the fixture must contain

The fixture is a small, deterministic, in-repo or in-memory dataset that gives fully trusted ground truth. It must contain at least:

1. **A clean three-component waveform** at a **known sampling rate** (the fixture's own rate, chosen so resampling tests are meaningful), with:
   - a **known impulsive P index** with energy concentrated on the vertical (Z) component;
   - a **later known S index** with energy concentrated on the horizontals (N, E);
   - low-amplitude background so the onsets are unambiguous.
2. **A pure-noise variant** of the same shape: no P, no S.
3. **A NaN/Inf variant**: finite shape, at least one non-finite sample in one channel.
4. **A flat variant**: constant (zero-variance) values on at least one channel.
5. **A wrong-shape variant** (e.g., two components) and a **wrong-rate variant** (metadata rate inconsistent with the expected rate) for input-validation tests.
6. Optionally, a **reordered-component variant** to exercise channel-order assertions.
7. Optionally, a **crafted probability curve** (two peaks; a peak at the window edge) for pick-extraction tests that do not need the model.

### 5.2 Why it gives trustworthy ground truth

- The P and S indices are **known by construction**, not estimated from data, so a target peak or a predicted pick has an exact expected value.
- The fixture is **deterministic**: a fixed generator and seed produce identical arrays on every machine, so tests are reproducible (`FR-041`).
- It is **small and offline**: tests run in seconds and never download anything.
- It **does not depend on the real dataset**, so it remains valid before any dataset is chosen (`OQ-3` is open) and after the dataset changes.
- It **exercises the real code paths** (load → validate → preprocess → labels → split → model → infer → evaluate) rather than mocks, so it catches interface and shape errors that pure unit tests miss.

### 5.3 Constraints

- The fixture must **not** import the real dataset, its loader's network path, or any optional dependency that fetches data.
- Generation is **preferred at test time** from a small generator module (proposed `tests/fixtures/synthetic.py`) with a fixed seed, so no binary is committed; if a committed fixture is used instead, it must be tiny and licence-free.
- The fixture rate and window length are parameters, not constants, so resampling and length tests can vary them.

### 5.4 Fixture generation is proposed using only installed libraries

The fixture generator is proposed to depend only on NumPy (present in the audit environment: 3.14.3 / NumPy 2.4.3, `AUDIT_REPORT.md` §7.2) and the standard library. It must not require ObsPy or SeisBench, which are not installed (`AUDIT_REPORT.md` §7.2).

---

## 6. Test data policy

1. **Never commit the real dataset.** The dataset is large and licence-restricted; it is gitignored and re-obtained per [`DATASET_GUIDE.md`](DATASET_GUIDE.md) and [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) (`DR-005`, `DR-006`, `NFR-009`).
2. **Only small synthetic fixtures are committed or generated.** Fixtures are deterministic and licence-free.
3. **Checkpoints, logs, figures and metric tables are gitignored** (`FR-048`) and regenerated by the documented command (`FR-078`). Tests that need a saved artifact (T-062) create it within a temporary directory, not in the repository.
4. **No test writes into the raw data directory.** Tests use temporary paths; source data is read-only (`NFR-009`).
5. **No secrets and no credentials in tests** (`NFR-015`).

---

## 7. CI plan (PLANNED)

> **Status: PLANNED.** No `.github/workflows/` directory exists in the repository (`AUDIT_REPORT.md` §12). The plan below describes the workflow that *should* be created.

### 7.1 Proposed workflow (proposed path `.github/workflows/ci.yml`)

1. **Trigger:** on push and pull request to `main`.
2. **Environment:** a pinned Python version (target 3.11/3.12 per `TECH_STACK.md`; the audit environment is 3.14.3, which is unverified for SeisBench/ObsPy), CPU-only, installing from the pinned dependency spec (`FR-082`).
3. **Step 1 — lint:** run `ruff` (lint and format check). Fail on error.
4. **Step 2 — tests:** run `pytest` on CPU with the tiny synthetic fixture only.
5. **Constraint:** CI **must not download the full dataset** and must not require a GPU. Any test that would need either is marked and skipped by default, never required.
6. **Non-goal in CI:** training a real model, running real evaluation, or producing reported results. Those are done locally or on the project's chosen compute, not in CI.

### 7.2 Why lint before tests

A lint failure is faster and cheaper to diagnose than a test failure; running `ruff` first keeps the feedback loop tight, consistent with `archive/tech-v0.1-original.md` §5.

### 7.3 Relationship to acceptance criteria

A green CI on the tiny fixture demonstrates `SC-7` (lint plus tests on a tiny fixture) from `../PRD.md` §16.3. It does **not** demonstrate any scientific result.

---

## 8. Coverage expectations and out-of-scope

### 8.1 Coverage expectations

- **Core logic coverage is mandatory** (`NFR-010`): labels, pick extraction, metrics, preprocessing, input validation, splitting/leakage, model shapes and timestamp conversion each have at least one test in §4.
- **Every `FR-*` marked UT or IT in `../PRD.md` §8 maps to a test** in §4 (see §10).
- Model-shape and label invariants (shapes, softmax sum, target sum) are asserted as unit tests, not only as training smoke checks.
- The leakage check exists in **two** places by design: as a test (T-043) and as a training-start guard (T-044).

### 8.2 Explicitly out of scope for automated testing

| Out-of-scope item | Why it cannot be unit-tested | How it is covered instead |
|---|---|---|
| **Absolute scientific validity of the dataset's reference labels** | Reference picks are analyst- or catalogue-derived and are not machine-checkable truth; the code cannot know the "physically correct" onset. | Manual inspection of traces with reference picks overlaid (`FR-002`, `FR-064`); labelled as label uncertainty, not truth (`A-05`, §4.5 of `../PRD.md`). |
| Generalisation to other regions, networks or magnitudes | Requires other datasets, which are out of scope (`NG6`). | Stated as a limitation (L1), optional cross-dataset probe (`O-Opt3`). |
| Performance under realistic seismic noise | Real noise is coloured, non-stationary, with microseism peaks (`E35`); the project perturbs with controlled added noise. | Noise-robustness experiment with a stated SNR definition and limitation (`EX-4`, `FR-070`). |
| Statistical significance of a metric difference | A single run cannot establish significance; multiple seeds may be unaffordable (`E33`). | Seed-variability study (`EX-5`) where affordable; explicit statement when not. |
| Hardware-level bit-for-bit reproducibility on GPU | GPU non-determinism is expected and documented. | Determinism is asserted on CPU within a stated tolerance (`FR-041`, `NFR-001`). |
| End-to-end timing and resource claims | No target is set and no run exists (`NFR-006`, `NFR-007` are TBD). | Measured at the relevant milestone and reported as measured, not asserted by a test. |

---

## 9. Definition of done for a code change

Every code change in SeismoNet shall satisfy the project's change-log rules. A change is done only when all of the following hold:

1. **Implementation finished.** The change does what the linked requirement states; no partial or stubbed behaviour is left unstated.
2. **Tests run where possible.** Relevant tests from §4 were written or updated and were executed; where a test cannot be run (for example, it needs the real dataset or a GPU), that is stated rather than omitted.
3. **Failures disclosed.** Any failing test, skipped test, or error is reported explicitly with its command and output; a change is not "done" by hiding a failure.
4. **Change report written.** A change report records what changed, which requirement and which test IDs it relates to, and what was and was not verified.
5. **Status updated.** The authoritative status record is updated: [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and [`change-log/CURRENT_STATUS.md`](change-log/CURRENT_STATUS.md), with the change-log tree maintained per the project's convention.

> **Note.** The `docs/change-log/` tree and its rules are themselves **PROPOSED**; they do not yet exist in the repository (referenced by `AUDIT_REPORT.md` §14 but not verified present). Until they exist, this definition of done is the intended convention to adopt.

A change that adds a requirement-facing behaviour without a test, or that changes a test's expectation to make it pass, is not done. Where no automated test is possible (§8.2), the change report must name the manual inspection that covers it.

---

## 10. Traceability table

### 10.1 Test → requirement

| Test ID | Requirement ID(s) |
|---|---|
| T-001 | `FR-001` |
| T-002 | `FR-002` |
| T-003 | `FR-003`, `E10` |
| T-004 | `FR-003`, `E11` |
| T-005 | `FR-003`, `E12` |
| T-006 | `FR-003`, `SR-003`, `E18` |
| T-007 | `FR-003`, `E5` |
| T-008 | `FR-010` |
| T-009 | `FR-001`, `NFR-004` |
| T-010 | `FR-022` |
| T-011 | `FR-022` |
| T-012 | `FR-023`, `E4` |
| T-013 | `FR-024`, `E1`, `E2` |
| T-014 | `FR-021` |
| T-015 | `FR-022`, `OQ-8` |
| T-016 | `FR-023`, `E4` |
| T-017 | `FR-013` |
| T-018 | `FR-014`, `E11` |
| T-019 | `FR-016`, `SR-003`, `E18` |
| T-020 | `FR-016`, `E18` |
| T-021 | `FR-017` |
| T-022 | `FR-020`, `FR-021` |
| T-023 | `FR-018`, `R-04` |
| T-024 | `FR-028` |
| T-025 | `FR-029` |
| T-026 | `FR-030` |
| T-027 | `FR-031` |
| T-028 | `FR-008`, `SR-001`, `E12` |
| T-029 | `FR-008`, `SR-003`, `E18` |
| T-030 | `FR-008`, `E10` |
| T-031 | `FR-008`, `E11` |
| T-032 | `SR-002` |
| T-033 | `FR-034` |
| T-034 | `FR-033` |
| T-035 | `FR-037` |
| T-036 | `FR-036` |
| T-037 | `FR-035` |
| T-038 | `FR-038` |
| T-039 | `FR-044`, `US-06` |
| T-040 | `FR-039` |
| T-041 | `FR-041`, `NFR-001` |
| T-042 | `FR-026`, `FR-005` |
| T-043 | `FR-004`, `FR-005`, `FR-025`, `NFR-003`, `SC-8` |
| T-044 | `FR-025`, `NFR-003` |
| T-045 | `FR-006` |
| T-046 | `FR-009`, `SR-013`, `E26` |
| T-047 | `FR-050` |
| T-048 | `FR-052`, `SR-012`, `E27` |
| T-049 | `FR-050`, `E6` |
| T-050 | `FR-051` |
| T-051 | `SR-015`, `FR-054`, `E29` |
| T-052 | `FR-054` |
| T-053 | `FR-053`, `SR-014` |
| T-054 | `FR-057`, `FR-059` |
| T-055 | `FR-059` |
| T-056 | `FR-062`, `E32` |
| T-057 | `FR-055` |
| T-058 | `FR-060` |
| T-059 | `FR-058`, `SR-016` |
| T-060 | `FR-050` |
| T-061 | `FR-078`, `SC-6` |
| T-062 | `FR-078`, `SC-6` |
| T-063 | `FR-079`, `FR-080` |
| T-064 | `FR-064`, `FR-065` |
| T-065 | `FR-071`, `E38` |
| T-066 | `FR-073`, `SR-017` |

### 10.2 Test → milestone phase (P0–P9)

| Phase | Purpose (`../PRD.md` §15) | Test IDs introduced | Notes |
|---|---|---|---|
| P0 | Repository and environment setup | none behavioural | The test harness, `.gitignore` and CI scaffold are created here; the first trivial test passes. |
| P1 | Dataset selection and exploration | T-001, T-002, T-003, T-004, T-005, T-006, T-007, T-008, T-009 | Data-validation and event-ID tests land with the loader and quality screening. |
| P2 | Data pipeline | T-010–T-027, T-032, T-042, T-043, T-045 | Labels, preprocessing, augmentation, channel-order assertion, split determinism and the leakage test. |
| P3 | Model and sanity check | T-033–T-040 | Model shape/softmax/depth assertions plus the tiny-batch overfit and loss-decrease smoke tests. |
| P4 | Baseline training | T-041, T-044 | Determinism test and the training-start leakage guard. |
| P5 | Protocol freeze, picking and evaluation | T-046–T-060 | Inference validation, pick extraction, timestamp conversion, and all metric tests. |
| P6 | Visualisation and failure analysis | T-064 | Plotting smoke test; failure analysis is largely manual (`VIS`, `FR-068`). |
| P7 | Research experiments | T-065, T-066 | Noise-seed determinism and one-factor-ablation isolation. |
| P8 | Reporting and reproducibility packaging | T-061, T-062 | End-to-end fixture run and the regeneration-command test. |
| P9 | Optional demonstration interface | T-063 | Optional; only if the interface is built (`FR-081`). |

### 10.3 Requirement → test completeness note

Every `FR-*` whose verification method in `../PRD.md` §8 is UT or IT is represented above. Requirements verified by INSP, METRIC, VIS or DOC (for example `FR-002`, `FR-064`, `FR-075`) are covered by inspection, measurement, visual review or documentation respectively, not by an automated test; where such a requirement also has a checkable kernel (for example `FR-002` statistics, T-002; `FR-064` figure construction, T-064) a test is included as a supplement. The manual-inspection requirements that cannot be automated are listed in §8.2.

---

## 11. Related documents

- [`../PRD.md`](../PRD.md) — requirements, acceptance criteria (§16), open questions (§17.2), evaluation matching rule (§12.2).
- [`SYSTEM_FLOW.md`](SYSTEM_FLOW.md) — the workflow each test exercises.
- [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) — module boundaries the test paths refer to.
- [`TECH_STACK.md`](TECH_STACK.md) — pytest, ruff and CI tooling.
- [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md) — phases P0–P9 and exit criteria.
- [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) — experiments whose controls T-065/T-066 protect.
- [`DATASET_GUIDE.md`](DATASET_GUIDE.md) — dataset access and licence.
- [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) — artifact, data and version-control policy.
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and [`change-log/CURRENT_STATUS.md`](change-log/CURRENT_STATUS.md) — authoritative status updated per the definition of done.
- `archive/tech-v0.1-original.md` §5 — the original testing recommendation this strategy builds on.
- `archive/PRD-v0.1-original.md` §9 — definitions of `E1`–`E38`.

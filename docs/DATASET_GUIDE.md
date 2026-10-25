# SeismoNet — Dataset Guide

| Field | Value |
|---|---|
| Document ID | DATA-001 |
| Version | 1.0 |
| Date | 2026-10-17 |
| Status | **P1 Task 1 — INSTANCE Counts selected as primary candidate.** `OQ-3` approved for this selection per project direction (2026-10-17). Evidence: `DATASET_COMPARISON.md` (DATA-COMP-001). Real-artifact verification still required before claiming the dataset is downloaded or validated (Task 2–3 below); per-dataset property rows remain UNVERIFIED except where DATA-COMP-001 provides a source link, and window length / split ratios / label width σ / tolerance / threshold remain explicitly open (see §4.1). |

Related documents: `../PRD.md` (§11 dataset requirements, §17 open questions), `DEVELOPMENT_ROADMAP.md` (phases P0–P2), `EXPERIMENT_PLAN.md`, `TECHNICAL_ARCHITECTURE.md`, `TECH_STACK.md`, `REPRODUCIBILITY.md`, `REASONING_AND_DECISIONS.md`, `PROJECT_STATUS.md`, and `AUDIT_REPORT.md`.

---

## 1. Purpose, scope and status

### 1.1 Purpose

This document is the acquisition, licensing, format, convention, validation and reproducible-preparation guide for the dataset SeismoNet will use. It defines what the project needs from a dataset, records the candidates named anywhere in the repository, provides a gating selection procedure, and specifies the validation and preparation steps required before any waveform is used.

### 1.2 Scope

In scope: the dataset requirements `DR-001`–`DR-007`; the candidate list with a per-candidate verification checklist; the selection decision procedure; expected waveform and annotation formats; metadata requirements and schema validation; directory conventions; validation procedures; reproducible preparation; the data-quality log; known risks; and an explicit non-assumptions list.

Out of scope: the model, the training procedure and the experiment protocols, which are cross-referenced to their own documents.

### 1.3 Status — the governing statement

**No dataset has been selected.** `OQ-3` is open. Nothing in this document is confirmed about any candidate dataset. The repository itself contains no data: there is no `data/` directory, no waveform file, no metadata file and no split file (`AUDIT_REPORT.md` §9).

**Governing rule for this document.** Every row in every dataset **property** table is marked **UNVERIFIED — must be checked against the dataset's own documentation**, unless the row states a **requirement** rather than a property. A requirement (for example, "the dataset must provide S picks") is a statement about what SeismoNet needs; it is not a claim about any dataset. No dataset has been downloaded, and no dataset is asserted to satisfy any requirement.

No dataset statistic, licence, size, sampling rate, component count, label count or download command is stated here as fact. Where a candidate is named, the only fact recorded is *where it was named in this repository*.

---

## 2. What the project needs from a dataset

These are requirements on the eventual choice, restated from PRD §11.2 with their rationale and the consequence of failing each. They are requirements, not properties, and are therefore not marked UNVERIFIED.

| ID | Requirement | Pri | Rationale | Consequence of failing |
|---|---|---|---|---|
| DR-001 | Three-component waveform data with a known sampling rate. | M | The model input is a fixed-length three-component window (`SR-001`); an unknown or mixed rate breaks label and tolerance semantics (§4.4). | The planned model cannot be trained or evaluated as specified; the architecture and the sample-index/tolerance logic would both change. |
| DR-002 | Reference P pick times, and reference S pick times for S evaluation. | M | Without S labels, half the stated objective (`G3`, `FR-060`) is impossible. | S cannot be evaluated; a core mandatory criterion (SC-2) fails, and the project's central question about S-wave difficulty cannot be answered. |
| DR-003 | An event identifier, or enough metadata (origin time, source location, event code) to construct one, so event-level splitting is possible. **If it does not, the dataset choice must be revisited.** | M | Event-level splitting is the project's primary defence against inflated results (`FR-004`, `R-03`). | The split strategy cannot be executed; results would risk event leakage and would be scientifically invalid. This is a **hard gate**. |
| DR-004 | Where available, pick quality/uncertainty and SNR, to enable stratified analysis. | S | Enables `FR-011` and informs the tolerance choice (`SR-016`). | Stratified reporting and a tolerance informed by label quality are lost; the absence must be documented. |
| DR-005 | The dataset's licence and citation terms identified, recorded and complied with. | M | Legal and academic obligation (`NFR-013`). | The work may not be legitimately redistributable or citable; a university submission may be non-compliant. |
| DR-006 | The dataset format and required access procedure (direct download, toolbox download, registration) documented and reproducible. | M | Reproducibility (`FR-078`); some datasets require registration, which affects automation. | Another person cannot obtain the data; reproducibility (SC-6) fails. |
| DR-007 | Noise-only examples available or constructible (for example, pre-P windows). | S | Needed for false-alarm evaluation (`E3`) and a noise-window fraction (`FR-019`). | False-alarm behaviour cannot be evaluated as intended; a false-pick rate cannot be computed meaningfully. |

---

## 3. Candidate datasets

### 3.1 Candidate table

Every property cell is **UNVERIFIED — must be checked against the dataset's own documentation**. The "Where it was named" column is the only verified column: it records where the candidate appears in this repository.

| Candidate | Where it was named in this repository | Access route | Licences | Formats | Sampling rate(s) | Components | P labels | S labels | Event identifier | Size | STATUS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| STEAD | Linked in `README.md` as a potential starting point; source `https://github.com/smousavi05/STEAD` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| PhaseNet data/repo | `README.md` lists `https://github.com/AI4EPS/PhaseNet` as an implementation reference; what data the repository actually ships is UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| INSTANCE | Named in v0.1 §12 and §14 (`docs/archive/PRD-v0.1-original.md`) | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| ETHZ | Named in v0.1 §12 (`OQ-3`, `docs/archive/PRD-v0.1-original.md`) | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| SeisBench-accessible datasets | Named in `tech.md` §1 as a convenience route | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |

Notes on the table:

- The only URLs recorded anywhere in the repository are `https://github.com/smousavi05/STEAD` and `https://github.com/AI4EPS/PhaseNet`. For every other candidate, **locate the official source and record the URL when verifying**; no other URL is invented here.
- "PhaseNet data/repo" is listed because the README names PhaseNet as an implementation reference. PhaseNet is an *implementation reference*; whether it ships a usable dataset, and under what terms, is UNVERIFIED and must be checked.
- "SeisBench-accessible datasets" is a *route*, not a single dataset. Its compatibility with the resolved Python and PyTorch versions is UNVERIFIED (see `AUDIT_REPORT.md` §7.3, discrepancy 1).

### 3.2 Verification checklist per candidate

For each candidate, the following must be checked **against the dataset's own documentation**, and the finding recorded. The dataset's own documentation is the authority; a third-party summary is not sufficient.

**STEAD**

- [ ] Locate and read the official documentation and the dataset's own licence statement.
- [ ] Record the licence and citation terms (`DR-005`).
- [ ] Record the access route and whether it requires registration (`DR-006`).
- [ ] Record the file formats shipped.
- [ ] Record the sampling rate(s).
- [ ] Record the component set.
- [ ] Record whether P labels are present, and their source.
- [ ] Record whether S labels are present, and their source.
- [ ] Record whether an event identifier is present or can be constructed (`DR-003`).
- [ ] Record the measured or documented size and storage requirement (`OQ-20`).

**PhaseNet data/repo**

- [ ] Locate and read the repository's own documentation.
- [ ] Determine whether the repository ships a dataset, and if so under what terms.
- [ ] If it ships data, repeat every check in the STEAD list above.
- [ ] If it does not ship data, record that fact and close the candidate (it is an implementation reference, not a dataset).

**INSTANCE**

- [ ] Locate the official source and record the URL.
- [ ] Repeat every check in the STEAD list above.

**ETHZ**

- [ ] Locate the official source and record the URL.
- [ ] Repeat every check in the STEAD list above.

**SeisBench-accessible datasets**

- [ ] Confirm SeisBench installs on the resolved Python version; this is UNVERIFIED and is a known installation risk (`AUDIT_REPORT.md` §7.3).
- [ ] Enumerate the datasets reachable through SeisBench and record which provide P **and** S labels **and** event identifiers.
- [ ] For each short-listed SeisBench dataset, repeat every check in the STEAD list above.

---

## 4. Dataset selection decision procedure

This gating procedure was executed in P1 Tasks 1–2. Its current state is recorded in §4.1; the generic steps remain below for audit.

1. **Start with the candidate list in §3.1.** For each candidate, complete the §3.2 checklist against the dataset's own documentation.
2. **Apply the component/rate gate (`DR-001`).** If a candidate cannot provide three-component waveform with a known sampling rate, mark it **revisit candidate** and continue.
3. **Apply the P-and-S label gate (`DR-002`).** If a candidate cannot provide both P and S reference picks, mark it **revisit candidate**.
4. **Apply the event-identifier gate (`DR-003`) — hard gate.** If a candidate cannot provide an event identifier or enough metadata to construct one, mark it **revisit candidate**. A candidate failing this gate changes the plan: event-level splitting cannot be executed and, per `DR-003`, the dataset choice must be revisited. Do not proceed to trimming this candidate's split design.
5. **Apply the licence gate (`DR-005`).** If the licence cannot be identified or does not permit the intended research use and citation, mark it **revisit candidate**, because a university submission may require a compliant licence.
6. **Apply the access gate (`DR-006`).** If the format and access procedure cannot be documented reproducibly (including where registration blocks automation), mark it **revisit candidate**; automation blockage is a known risk (`R-01`).
7. **Record the desirable extras (`DR-004`, `DR-007`).** Note; pick quality/uncertainty/SNR and noise-only constructibility do not gate selection but shape the tolerance and the false-alarm evaluation.
8. **Close `OQ-3` and answer `OQ-2`.** If at least one candidate passes steps 2–6, select the best-fitting candidate, record the evidence for every gate, and close `OQ-3`. Then fix `OQ-4` (window length and sampling rate) and `OQ-5` (split ratios) from the selected dataset's properties.
9. **If no candidate passes**, the outcome is **revisit candidate**: return to §3, widen the candidate list, and repeat from step 1. Do not select a dataset that fails any hard gate merely to make progress.

**Hard-gate warning, restated.** A dataset lacking **event identifiers** or lacking **S picks** does not merely reduce the achievable result — it changes the plan. Missing event identifiers invalidate the event-level split (`DR-003`, `R-03`) and therefore every honest evaluation; missing S picks removes half the stated objective (`DR-002`, `FR-060`). Either condition forces a return to candidate review, not a workaround.

### 4.1 Recorded decision — INSTANCE Counts (selected primary candidate, subject to artifact verification)

**Decision (Task 1, approved direction, 2026-10-17).** INSTANCE **Counts** is recorded as the **selected primary candidate**, subject to verification against the actual downloadable artifact and its metadata (§4.1, `REPRODUCIBILITY.md` §11; Task 2–3 below). The dataset is **not claimed to be downloaded or validated** until that work is complete.

**Evidence base.** `docs/DATASET_COMPARISON.md` (DATA-COMP-001) §§2–3: requirement-by-requirement evidence tables and side-by-side matrix for STEAD, INSTANCE, ETHZ, and the SeisBench framework as the distribution layer. Every factual cell there carries a source URL; SeisBench availability is not treated as proof that an annotation is present.

**Why Counts.**

* Counts exposes `source_id` (INGV bulletin event ID) for every trace — `DR-003` hard gate.
* It exposes P and S manual picks for a large, documented subset of traces — `DR-002`.
* It is three-component waveform data with a known sampling rate documented in its metadata — `DR-001` (exact rate confirmed only against the artifact's schema; see Task 2).
* Access and license are documented independently of this guide: the comparison records the official GitHub source, license, and size estimates with URLs; the artifact page and its embedded metadata are authoritative for the final sizes.

**Why not the others (summary; detail in DATA-COMP-001 §4.2–§4.3).** STEAD shares the waveform/label/event-id properties but does not carry a canonical event identifier in the same metadata column that INSTANCE's Counts export uses for P1 splitting; ETHZ satisfies `DR-003` but its sampling-rate and phase-label heterogeneity would require resampling or phase remapping before the single-rate model assumptions in `SR-003`/`FR-016` are satisfied — an extra preprocessing layer before the baseline `EX-1`. Counts is therefore the least-assumption primary candidate for a P1 baseline.

**What this decision does NOT close — Stage 3 assessment (2026-10-17, STAGE-ASSESSED).** Sampling rate **verified 100 Hz** on the INSTANCE Counts HDF5 sample (`data_format ENZ / CW / (3,12000) int32`, `trace_dt_s 0.01`). Production window **provisional 3000–4000 samples (30–40 s at 100 Hz)** for the 120 s traces — kept as provisional until Stage 4's loader measures peak VRAM on the 4 GiB RTX 2050; `configs/baseline.yaml` keeps `128` only for fast tests. Split ratios **preserved 70/15/15** (no shipped `split` column exists in Counts metadata). Label width **provisional 20–40 samples** (`OQ-8`). Missing S retained as all-zero S channel (loader must not drop). Tolerances/thresholds remain **explicitly open** until the P5 freeze (`OQ-10`/`OQ-11`/`OQ-14`/`OQ-17`, `FR-061`/`SR-011`/`SR-016`). See `docs/change-log/entries/2026-10-17-014-stage1-to-stage4-decisions.md`.

---

## 5. Expected waveform formats

This section states the formats the pipeline must be able to read and which reader is proposed for each. Readers are **PROPOSED and, where noted, NOT INSTALLED**.

| Format | Typical content | Proposed reader | Reader status (verified) |
|---|---|---|---|
| miniSEED / MSEED | Continuous or windowed three-component records | ObsPy | **PROPOSED. NOT INSTALLED** (`AUDIT_REPORT.md` §7.2). |
| SAC | Single-station waveform files | ObsPy | **PROPOSED. NOT INSTALLED.** |
| HDF5 / SeisBench native | Dataset packaged in SeisBench's native format with separate metadata | SeisBench | **PROPOSED. NOT INSTALLED.** |
| NumPy arrays | Pre-processed arrays or fixtures | NumPy | INSTALLED (2.4.3). |

ObsPy is proposed as the reader for miniSEED and SAC because it is the standard tool for those formats (`tech.md` §1). SeisBench is proposed for its own native HDF5 format. **Neither ObsPy nor SeisBench is installed**, and their availability on the machine's Python 3.14.3 is UNVERIFIED; `tech.md` recommends Python 3.11/3.12 (`AUDIT_REPORT.md` §7.3, discrepancy 1). This must be resolved in roadmap P0 before the format choice is fixed.

The project does not invent a reader: if the selected dataset's format has no proposed reader above, the reader is chosen and recorded as part of `DR-006`.

---

## 6. Annotation and metadata formats

Annotations must be recorded in a form that survives resampling and windowing. The following conventions are **PROPOSED** and must be confirmed against the selected dataset's actual annotation format.

- **Pick times versus sample indices.** Reference picks may be stored as absolute timestamps, relative times, or sample indices. The pipeline must record which representation the dataset uses and convert explicitly using `time_seconds = sample_index / sampling_rate` and `absolute_timestamp = trace_start_time + time_seconds` (`SR-014`, `FR-053`). A pick index is only meaningful with a known sampling rate and time origin (§4.4), and resampling changes the meaning of every sample index.
- **Event identifiers.** Where the dataset does not supply an event identifier directly, one is constructed from available metadata (origin time, source location, event code) by a documented, unit-tested rule (`FR-010`, `DR-003`).
- **Magnitude, distance and SNR fields.** Where present, these are recorded and used for stratified reporting (`FR-011`, `DR-004`). Where absent, the absence is recorded.
- **Quality and uncertainty fields.** Where the dataset provides pick quality or uncertainty, it is recorded and informs the tolerance choice (`SR-016`, `OQ-13`). Where absent, the absence is recorded and the reference is treated as carrying unknown uncertainty (`A-05`).
- **The requirement to record presence.** For every metadata field of interest, the project must record whether it is **present**, **absent** or **constructible** for the chosen dataset (`DR-004`, `FR-002`, `FR-011`). "Absent" is a valid recorded finding; a missing field is never silently treated as present.

---

## 7. Metadata requirements table

Field → required/desirable → why → used by which requirement. Status is a requirement-level classification, not a claim about any dataset.

| Field | Required / desirable | Why | Used by |
|---|---|---|---|
| Trace/record identifier | Required | Trace each reported sample back to its source | FR-012, SC-10 |
| Sampling rate | Required | Sample-index and tolerance semantics depend on it | DR-001, SR-003, FR-053 |
| Component identity (Z, N, E) | Required | Channel order must be validated, not assumed | SR-002 |
| Reference P pick | Required | P evaluation | DR-002, FR-055 |
| Reference S pick | Required | S evaluation | DR-002, FR-060 |
| Event identifier (or constructible equivalent) | Required | Event-level splitting | DR-003, FR-004 |
| Trace start time | Desirable | Absolute-time conversion | SR-014 |
| Pick quality / uncertainty | Desirable | Informs tolerance; stratified analysis | DR-004, SR-016 |
| SNR | Desirable | Stratified reporting; false-alarm context | DR-004, FR-011 |
| Source–station distance | Desirable | Stratified reporting; S-P context | DR-004, FR-011 |
| Magnitude | Desirable | Stratified reporting | DR-004, FR-011 |
| Instrument type / units | Desirable | Interpret normalisation limits | limitation L7 |

---

## 8. Metadata schema validation

**Status: PROPOSED.** A declared schema check applied on load is proposed so that a malformed metadata row fails loudly rather than silently entering the pipeline (`NFR-004`). This satisfies `FR-003` (detect and flag unusable traces with a logged reason).

The schema declares, at minimum: required columns present; sampling rate numeric and positive; component identity one of the accepted set; P and S pick fields present where picks are required; S strictly after P where both are present; finite, non-flat waveform values; and an assignable event identifier.

`tech.md` §5 mentions **pandera** or **Pydantic** as optional validation tools. **Neither is installed** (`AUDIT_REPORT.md` §7.2); pandera is listed as NOT installed. If a validation library is adopted, it is pinned in the dependency specification (`FR-082`). A hand-written schema check is an acceptable alternative and requires no new dependency.

---

## 9. Directory conventions

**Status: PROPOSED. The `data/` directory does not exist.** These are the intended conventions, to be created in roadmap P0–P2.

```text
data/
├── raw/          # as acquired; NEVER modified in place (NFR-009)
├── interim/      # partially processed intermediates (gitignored)
└── processed/    # windows, targets, derived artifacts (gitignored)
```

Rules:

- `data/` **does not exist yet** and must be created as part of the data path.
- `data/` **must be gitignored** before it is created; the `.gitignore` is added first in P0 to prevent committing datasets (`FR-048`, `R-16`).
- **Raw data is never modified in place** (`NFR-009`). All derived data is written to `interim/` or `processed/`.
- The split files and the metadata index are **committed**; waveform data is **not** (§11).

---

## 10. Data validation procedures

The following checks are required before a trace is used. Each check states what to do on failure and the requirement it satisfies. These are the PRD §11.5 checks, made operational.

1. **Component and rate consistency per trace (`FR-003`).** Confirm the trace has the expected three components and the expected sampling rate. On failure: exclude the trace and log the trace ID and reason.
2. **Presence of both P and S picks (`FR-003`, DR-002).** Count and log traces missing either. On failure for a phase: exclude the trace from that phase's evaluation, keep it in the other if still valid, and record the excluded count (`E7`).
3. **S strictly after P (`E5`).** Where both picks exist, require S > P. On failure: treat as a data-quality error; flag or exclude and log.
4. **Finite, non-flat signals (`FR-003`).** Reject NaN/Inf samples and zero-variance (flat) traces. On failure: exclude the trace (or the dead channel under the `OQ-15` policy) and log; normalisation must never divide by zero (`FR-014`, `E11`).
5. **Event-identifier coverage (`FR-010`, DR-003).** Measure the fraction of traces that can be assigned an event. On failure (coverage too low to support event-level splitting): stop and revisit the dataset per §4, step 4.
6. **Duplicate detection where metadata permits (`E25`).** Detect duplicate traces. On failure: deduplicate or flag before splitting, and record the count.

Every check writes to the data-quality log (§12). No check silently drops a trace.

---

## 11. Reproducible data preparation

The data-preparation pipeline is deterministic given the recorded seed and the input metadata. The sequence below is **PROPOSED** and is executed in phases P1–P2.

1. **Acquire.** Obtain the dataset through the documented access procedure (`DR-006`). Record the access date and the dataset version or identifier. Raw data stays read-only.
2. **Verify checksums and licence.** Record checksums where the source provides them, and confirm the licence and citation terms before use (`DR-005`, `NFR-013`). Do not assume a checksum exists; if none is provided, record that fact.
3. **Build the metadata index.** Construct the metadata table, including the event identifier and every recorded field (§7), plus the schema check (§8) (`FR-002`, `FR-012`).
4. **Event-level split.** Assign each **event** to train, validation or test by a documented, seeded, deterministic rule (`FR-004`, `FR-005`, `FR-026`). Ratios are configurable and recorded (`FR-006`, `FR-027`).
5. **Verify zero overlap.** Run the automated check asserting no event ID appears in more than one split (`FR-025`, `SC-8`). A non-zero overlap fails the pipeline loudly.
6. **Window and target generation.** Cut fixed-length windows and generate P/S/noise targets (`FR-017`, `FR-021`), preserving the window's time origin so absolute times remain recoverable (`FR-053`). Resampling, if used, moves labels with the waveform via time.
7. **Persist derived artifacts.** Write windows and targets to `processed/`, and write the split files and the metadata index as committed artifacts.

**What is gitignored versus committed.**

| Artifact | Committed? | Reason |
|---|---|---|
| Raw waveforms | **No** (gitignored) | Size; licence; never modify in place (`NFR-009`, `FR-048`) |
| Interim / processed waveforms and targets | **No** (gitignored) | Size; regenerable |
| Metadata index | **Yes** | Small, inspectable, needed for reproducibility (`FR-012`) |
| Split files | **Yes** | Small, diff-able, needed to prove zero overlap (`FR-005`, `SC-8`) |
| Data-quality log | **Yes** | Small, needed as evidence (`SC-9`) |

---

## 12. Data-quality log specification

The log records every excluded or flagged trace. It supports `FR-003` and the success criterion `SC-9` (data-quality screening is logged).

| Column | Meaning | Why useful |
|---|---|---|
| Trace / record ID | Identifier of the affected trace | Allows the exact trace to be located and re-judged |
| Reason | The check that failed (component, rate, missing pick, ordering, non-finite, flat, duplicate, no event ID) | Distinguishes cause from coincidence |
| Details | The observed value (e.g., rate seen versus expected) | Supports diagnosis and reporting |
| Action taken | Excluded / flagged / phase-specific exclusion | Matches the declared handling policy |
| Phase affected | P, S, or both | Prevents silently dropping a phase (`E7`) |
| Timestamp / run ID | When and by which run the log was produced | Ties the log to a specific dataset version and run |

A summary of counts per reason accompanies the log so that the reader sees the exclusion rate at a glance.

---

## 13. Known dataset risks

| Risk | Description | Mitigation / recording |
|---|---|---|
| R-02 — label quality | Large public datasets are known to contain label and metadata imperfections; picks may be missing, wrong or biased. | Quality screening and logging (§10, §12); state reference uncertainty; treat low-quality picks under a documented policy (`OQ-13`). |
| R-01 — licensing | The dataset's licence may restrict use or redistribution. | Identify and record the licence before committing; record the exact terms (`DR-005`, `NFR-013`). |
| R-01 — access/registration | Registration may block automated download. | Document the access procedure; if it cannot be automatable, record that and treat automated regeneration of the raw acquisition step as manual (`DR-006`). |
| OQ-20 — size/storage unknown | Dataset size and storage requirement are UNVERIFIED. | Measure or document size before selection; it drives the compute and storage budget. |
| R-12 / SR-003 — sampling-rate heterogeneity | Mixed sampling rates silently mislabel every pick if not converted. | Single common rate policy; anti-aliased resampling with labels moved via time; a dedicated conversion test (`FR-016`, `FR-053`). |
| L7 — instrument unit heterogeneity | Counts, velocity and acceleration units differ across instruments, and instrument-response removal is out of scope. | Per-window normalisation reduces but does not remove the effect; recorded as a limitation. |
| Event-identifier gap | A dataset lacking event identifiers invalidates event-level splitting. | The hard gate in §4, step 4 (`DR-003`). |

---

## 14. Explicit non-assumptions list

The following must **not** be assumed. Each row states the check that resolves it. This list is a direct application of the "do not invent" policy.

| Must not be assumed | Why it must not be assumed | Check that resolves it |
|---|---|---|
| That the dataset uses a single sampling rate | Rates may differ per trace or per subset, and mixing rates silently mislabels picks (§4.4, `R-12`). | Measure the sampling-rate distribution (`FR-002`, §10, check 1). |
| That the labels are clean | Large public datasets are known to contain label imperfections (`R-02`, v0.1 §14). | Run the quality checks (`FR-003`, §10) and inspect label availability. |
| That event identifiers are present | Splitting depends on them (`DR-003`). | Inspect metadata for an event ID or a constructible equivalent; apply the hard gate (§4, step 4). |
| That the licence is permissive | Terms may restrict use or redistribution (`R-01`). | Read and record the licence statement (`DR-005`). |
| That download is automatable | Some datasets require registration (`R-01`, `DR-006`). | Attempt or document the access procedure; record whether it can be automated. |
| That the dataset size is manageable | Size is UNVERIFIED and drives the compute budget (`OQ-20`). | Measure or document the size before selection. |
| That S picks exist at all | Without them half the objective fails (`DR-002`, `FR-060`). | Count traces with both P and S picks (§10, check 2). |
| That the components are three and correctly ordered | A different or mis-ordered component set corrupts S learning (`SR-002`). | Validate the component set and order (`FR-008`, §10, check 1). |
| That pick times are absolute timestamps | They may be sample indices or relative times (`SR-014`). | Record the representation and convert explicitly (`FR-053`). |
| That any listed candidate is currently accessible | Candidate properties are UNVERIFIED and may have changed. | Re-verify every candidate against its own documentation at selection time (§3.2). |

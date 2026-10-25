# ADR-002 — Dataset Strategy: event-level splitting, selection gated on metadata verification

- **ADR ID:** ADR-002
- **Status:** Accepted (design). **No dataset has been selected** — the selection itself remains open (`OQ-3`).
- **Date:** 2026-10-17
- **Deciders:** Project owner / supervisor (selection requires approval); documentation task (proposed)
- **Related:** `DEC-001` D-06 in `../REASONING_AND_DECISIONS.md`; PRD `DR-001`–`DR-007`, `FR-004`, `FR-005`, `FR-010`, `FR-025`, `R-01`, `R-02`, `R-03`, `SC-8`; `../DATASET_GUIDE.md`
- **Supersedes:** none
- **Superseded by:** none

---

## 1. Context

SeismoNet needs waveform data with reference P and S picks in order to train and evaluate a phase picker. The repository names candidate datasets (STEAD, PhaseNet's data, INSTANCE, ETHZ, SeisBench-accessible datasets) but has verified **none** of their properties. `OQ-3` ("which dataset is the selected dataset?") is open, and the original PRD v0.1 explicitly warns that listed datasets must not be assumed to be downloaded or configured.

Two facts make the dataset decision the highest-risk decision in the project:

1. **Everything downstream depends on it.** Sampling rate and window length (`SR-003`, `SR-004`), the Gaussian label width σ (`SR-006`), the evaluation tolerance (`SR-016`), the decoder's output resolution, and the storage and compute budget all follow from the dataset's properties.
2. **A wrong choice is discovered late and expensively.** If, after the pipeline is built, the dataset turns out to lack S picks, lack event identifiers, or have an unusable licence, the pipeline's split strategy and possibly its S-wave objective must be redesigned.

The specific methodological hazard is **event leakage**: one earthquake recorded at many stations produces many correlated traces. A random trace-level split places near-duplicates of the same event in both training and test, so the test set is not independent and the reported performance is inflated. This is a textbook leakage mechanism, and in seismology it is both common and easy to miss.

---

## 2. Options considered

### A. Random trace-level split *(rejected)*

Simple and maximises data per split, but leaks events across the boundary and answers the wrong scientific question ("can the model recognise traces similar to ones it has seen?").

### B. Event-level split, persisted and verified *(selected)*

Group traces by seismic event; assign whole events to train, validation or test; persist the assignment; verify zero event overlap as both a test and a hard guard at training start.

### C. Station-level split

Hold out entire stations. A legitimate alternative *question* (cross-station generalisation) but does **not** prevent one event appearing on both sides, so it does not fix leakage.

### D. Time-based split

Train on earlier events, test on later ones. Realistic for a continuous catalogue and arguably a stronger generalisation claim, but it assumes a long, well-time-ordered catalogue and interacts with how events are distributed in time. **Compatible with** Option B, not a replacement for it.

### E. Region-based split

Hold out a geographic area. Informative, but requires reliable event locations and sufficient events per region — metadata the dataset is not guaranteed to provide.

### F. Choose any dataset first, resolve splitting later

Fastest to start, but risks discovering an unusable dataset after the pipeline is built. Rejected: the cost of late discovery is far higher than the cost of a short verification step.

---

## 3. Decision

Adopt the following, in this order:

1. **Event-level splitting is mandatory** (Option B), with persisted split files, determinism given a recorded seed, and an automated zero-event-overlap check that runs both as a test and as a guard at training start (`FR-004`, `FR-005`, `FR-025`, `FR-026`).
2. **Dataset selection is gated on metadata verification.** No dataset is adopted until every non-negotiable dataset requirement has been verified *against the dataset's own documentation*, not against this repository's descriptions of it (`DR-001`–`DR-003`, `DR-005`).
3. **The gate is hard.** A candidate dataset that cannot supply an event identifier (or enough metadata to construct one) is **disqualified** for this project's scope, because event-level splitting cannot be built on it (`DR-003`).
4. **Split ratios are declared for events, not traces**, and the resulting trace counts per split are reported so that an uneven, event-dominated split is visible rather than hidden (`FR-006`, `FR-027`).
5. **A time-based split may be added later** as an additional, stronger generalisation experiment if the catalogue supports it (Option D). It supplements, never replaces, the event-level guarantee.
6. **No dataset property is asserted until verified.** Every candidate property remains `UNVERIFIED` in `../DATASET_GUIDE.md` until checked, with the source of the check recorded.

---

## 4. Rationale

| Consideration | Why this decision |
|---|---|
| Scientific validity | Event leakage is the single most plausible route to a flattering but invalid result in this problem class. Event-level splitting is the direct control (`R-03`). |
| Matching the real question | The question of interest is generalisation to *unseen events*, because that is what any future use would require. Option A answers an easier, different question. |
| Credibility with the domain user | A seismologist specifically distrusts any result where the same event appears in train and test (`US-02`). This is a correctness requirement *and* a credibility requirement. |
| Auditability | Persisting the split makes the guarantee checkable by a reviewer rather than merely asserted (`SC-8`). |
| Cost of verification vs cost of late discovery | Inspecting dataset metadata is cheap. Rebuilding the split strategy, or abandoning a dataset after the pipeline is written, is not. |
| Honesty about what cannot be claimed | Without event IDs, the project cannot support its central methodological claim, so the honest response is to change datasets rather than to substitute a weaker split and describe it loosely. |
| Compatibility with alternatives | Event-level splitting does not preclude adding a time-based or region-based view later; it is the foundation, not a constraint on further generalisation work. |

**Evidence class.** **[ESTABLISHED]** that random trace-level splitting leaks events and inflates results in this problem class; **[RATIONALE]** for the specific implementation (persisted splits, training-start guard, event-level ratios); **[PLANNED-VERIFY]** that the eventual dataset choice supports the guarantee.

---

## 5. Consequences

### Positive

- Prevents the dominant leakage mechanism, which protects every downstream metric.
- Makes the leakage guarantee auditable and reproducible rather than a claim.
- Provides the artifact (persisted splits) that makes reported numbers comparable across runs (`FR-005`).
- Forces the dataset decision to be made on evidence rather than on convenience, which de-risks the whole project at the cheapest possible moment.

### Negative / accepted costs

- **Requires event identifiers.** If the chosen dataset lacks them, the dataset must change — a real constraint on the candidate list.
- Splits can be **uneven**, because events differ in how many stations recorded them. A single large event can dominate a training split. This must be inspected and reported, not assumed away.
- It may reduce per-class instance counts, which matters most for S (the harder phase), so S denominators must always be reported (`NFR-002`).
- Constructing event identifiers from partial metadata introduces an implementation risk: an incorrect construction can silently group distinct events or split one event (`FR-010` must be tested).

### Neutral

- The split ratio choice itself (`OQ-5`) is independent of this decision; this decision fixes the *unit* of splitting (events), not the proportions.

---

## 6. Risks of this decision

| Risk | Mitigation | Requirement |
|---|---|---|
| Event identifier absent or unusable | Hard gate; disqualify the candidate and revisit (`OQ-2`, `OQ-3`) | `DR-003` |
| Event identifier mis-constructed, silently grouping or splitting events | Construction rule documented and unit-tested on synthetic metadata rows; verify traces-per-event distribution | `FR-010`, `FR-012` |
| Dataset's "event" field is actually per-trace, making the guarantee vacuous | Verify by counting traces per event before adopting the dataset | `DR-003`, `DATASET_GUIDE.md` §10 |
| Label quality imperfections in a large public dataset | Quality screening with a logged exclusion reason; disclose reference uncertainty rather than treating labels as exact | `FR-003`, limitation L2 |
| Licence or access blocks use, or registration blocks automation | Verify licence and access procedure before adoption; record both | `DR-005`, `DR-006`, `R-01` |
| Split becomes event-dominated, biasing the training set | Report event counts and trace counts per split; consider capping traces per event if extreme | `FR-002`, `FR-027` |

---

## 7. Evidence and validation

| Evidence | Status |
|---|---|
| Candidate dataset metadata inspected against `DR-001`–`DR-007`, with the source of each check recorded | **Not done** |
| `OQ-3` closed with a documented decision and rationale | **Open** |
| Split files produced and committed | **Does not exist** |
| Zero-event-overlap check passing | **Does not exist** |
| Traces-per-event and events-per-split distributions reported | **Not produced** |
| S-instance counts per split reported (to show S is evaluable) | **Not produced** |

All six items are phase-P1 exit criteria (`../DEVELOPMENT_ROADMAP.md`). Until they exist, this ADR records an **intended** strategy and no leakage claim is supported.

---

## 8. Conditions that would justify revisiting this decision

1. **No candidate dataset supplies event identifiers.** Response: change the dataset. Event-level splitting is not negotiable, because the alternative invalidates the results. If *every* candidate lacks them, that is a project-scope escalation requiring the owner's and supervisor's decision, and it should be raised immediately rather than worked around.
2. **The dataset provides reliable source times and a long continuous catalogue**, making a time-based split both possible and scientifically preferable. Response: adopt Option D *in addition*, and report both the event-level and time-based results.
3. **Reliable event locations are available**, enabling a region-based generalisation experiment. Response: adopt Option E as an additional experiment.
4. **The dataset's event field proves semantically unreliable.** Response: construct event identity from source time and location where possible; if not possible, disqualify the dataset.

None of these conditions justifies reverting to a random trace-level split.

---

## 9. Relationship to other documents

- Reasoning narrative: `../REASONING_AND_DECISIONS.md` D-06.
- Dataset detail, candidate table and verification procedure: `../DATASET_GUIDE.md`.
- Technical expression of the split module and its guards: `../TECHNICAL_ARCHITECTURE.md` §4, §6.1, §13.
- Workflow placement: `../SYSTEM_FLOW.md` Workflow A.
- Verification: `../TESTING_STRATEGY.md` (leakage tests).
- Requirements: PRD §11 (dataset requirements), `FR-004`, `FR-005`, `FR-025`, `FR-026`, `FR-027`, `DR-001`–`DR-007`, `SC-8`, risks `R-01`, `R-02`, `R-03`.

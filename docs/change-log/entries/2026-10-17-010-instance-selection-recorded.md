# 2026-10-17-010 — Record INSTANCE Counts selection (Task 1)

## A. Change identification
- Change ID: 2026-10-17-010
- Date: 2026-10-17 ~06:34 UTC
- Short title: Record INSTANCE Counts as selected primary candidate in DATASET_GUIDE.md §4.1
- Category: documentation
- Files created: —
- Files modified: `docs/DATASET_GUIDE.md` (header Status + new §4.1)
- Files removed: —

## B. What was changed?
Wrote the approved direction into `DATASET_GUIDE.md`:

- Header Status now records **P1 Task 1 — INSTANCE Counts selected as primary candidate, OQ-3 approved for this selection** with an explicit note that window length / split ratios / σ / tolerance / threshold remain open — the Gating Procedure (§4) is retained verbatim for audit.
- New §4.1 "Recorded decision — INSTANCE Counts" states: Counts as selected **subject to artifact verification**, evidence base (`DATA-COMP-001`), why Counts passed the four hard gates, why not the others (summary, detail deferred to DATA-COMP-001 §4.2–§4.3), and explicitly that window length, split ratios, label width, tolerance, and threshold remain open (OQ-4/5/8/11/10-17) for the P5 freeze — with the `configs/baseline.yaml` 128-sample window identified as a fast-test placeholder, not the production window.

No dataset was claimed downloaded or validated by this edit; §4's generic steps are kept for traceability.

## C. Why was this change necessary?
Task 1 required the selection to be recorded in `DATASET_GUIDE.md` §4 with reference to `DATASET_COMPARISON.md` and with rationale for the preference, without closing parameters that the comparison explicitly leaves open. The prior header still marked `OQ-3` as "recommended, pending owner approval" (entry 008); the approved direction makes approval explicit but keeps the "subject to verification" qualifier required by Task 1's preamble.

## D. Why was this approach chosen?
Selected: a **small, additive §4.1** rather than a rewrite of §3/§4. Alternatives: (a) copy DATA-COMP-001's 6-page evidence into DATASET_GUIDE.md — rejected (duplication, drift); (b) delete the gating procedure once the choice is recorded — rejected (the procedure is the audit trail for why a future substitution would be valid). Keeping §4.1 as a pointer plus the five-way open-parameter list satisfies Task 1's "do not claim … until that work is complete" and "keep … explicitly open" constraints in one place.

## E. How was it implemented?
Two edits to `docs/DATASET_GUIDE.md`: header Status and insertion of §4.1 (see §B). No Python execution, no download, no environment change.

## F. How did this improve SeismoNet?
- **EXPECTED — traceability:** the selection now has a single written record (`DATASET_GUIDE.md` §4.1) that ties the choice to its evidence (`DATA-COMP-001`) and names what it did **not** decide — closing the loop on `OQ-3` without implying the artifact has been inspected.
- **EXPECTED — risk disclosure:** by listing the still-open parameters, the decision cannot be misread as fixing `OQ-4`/`OQ-5`/`OQ-8`/`OQ-11`.

## G. Testing and verification
- Verification: `DATASET_GUIDE.md` was read back; header points to DATA-COMP-001; §4.1 contains the five open parameters and the "subject to verification" clause. No test suite is relevant to this documentation edit.
- Tests not run: `pytest` suite — not applicable to this entry (no `src/` change).

## H. Risks and side effects
The prior header's "every row remains UNVERIFIED" warning is preserved; the new wording could be misread as claiming waveform validation — mitigated by the explicit "Real-artifact verification still required" clause and by deferring P/T/S-rate/component claims to the Task 2 artifact inspection (entry 011).

## I. Relationship to the PRD and roadmap
`DR-001`–`DR-003` (hard gates), `DR-005`/`DR-006`, `OQ-3` (approved direction), `OQ-4`/`OQ-5`/`OQ-8`/`OQ-11`/`OQ-10` (still open), `FR-025`/`SC-8` (leakage guard, still to be proved on artifact). Roadmap **P1 Task 1** — selection recording.

## J. Next steps
Task 2: inspect the official Counts artifact and its embedded metadata schema before any waveform download (entry 011). Task 3: generate real `splits/` from the verified `source_id` set with the zero-overlap guard (entry 012, blocked until Task 2 succeeds).

# 2026-10-17-008 — Dataset comparison (P1, DR-001–DR-007, OQ-3)

## A. Change identification
- Change ID: 2026-10-17-008
- Date: 2026-10-17 05:56 UTC
- Short title: Compare STEAD/INSTANCE/ETHZ/SeisBench; recommend INSTANCE (counts); link OQ-3 closure
- Category: documentation
- Files created: `docs/DATASET_COMPARISON.md` (DATA-COMP-001, 1.0)
- Files modified: `docs/DATASET_GUIDE.md` (header Status updated to point to DATA-COMP-001)
- Files removed: —

## B. What was changed?
Created `docs/DATASET_COMPARISON.md`, an evidence-based comparison of the four
candidate families named in the project: STEAD, INSTANCE, ETHZ, and the SeisBench
framework (as the access/format layer). Each candidate was evaluated against
`DR-001`–`DR-007` with source links for sampling rate, component representation,
P/S annotation form, event identifier (`source_id`), dataset size, separable
metadata inspection, license/citation, and SeismoNet label/split compatibility.
Four parallel research probes (STEAD, INSTANCE, ETHZ, SeisBench) gathered the
evidence from GitHub READMEs/LICENSEs, the STEAD IEEE paper, the INSTANCE ESSD
paper, SED/SEIS network pages, and SeisBench docs + `sebench/data/base.py` +
Woollam et al. 2022 Table 1/§2.1.2 — so every factual cell in §2 carries a URL
or a measured header.

`DATASET_GUIDE.md` was updated only at its header Status field to mark the
comparison complete and to point to `DATASET_COMPARISON.md`; its per-dataset
property rows remain UNVERIFIED except where the comparison provides a link, per
its own governing rule. No dataset was downloaded and no split was persisted
in this entry.

## C. Why was this change necessary?
P1 Tasks 1–2 require a P1 gate: selection must be justified against `DR-001`–
`DR-006` before any pipeline code assumes a format, and `OQ-3` ("which dataset?")
blocks every downstream file (`splits/`, P2 loader). The prior `DATASET_GUIDE.md`
listed candidates with `UNVERIFIED` in every cell — deliberate, but insufficient
to decide. The gap was the justification artifact that satisfies `NFR-011`
("every scientific parameter has a rationale") for the dataset decision; this
document is it.

## D. Why was this approach chosen?
Four parallel probes rather than one sequential pass: the candidates are
independent sources, so parallel lookup is the fastest way to fill the matrix
without blocking on any one source. Evidence is cited at the cell level (not
summarized per dataset) so a reviewer can falsify a single row without
re-auditing the whole table. The "availability through SeisBench ≠ proof that
an annotation exists" rule is enforced structurally: SeisBench is compared as a
separate column, and each dataset's annotation rows cite the dataset's own
docs or `trace_P/S_arrival_sample` columns, not the framework's capability.
`OQ-3` is **recommended for closure on INSTANCE (counts)** but not closed in
`DATASET_GUIDE.md` until owner approval — per the task's "update OQ-3 only if
the evidence supports a defensible decision" rule.

## E. How was it implemented?
Launched probes: STEAD (GitHub README + LICENSE + IEEE 8871127 + SeisBench
STEAD page), INSTANCE (INGV GitHub + 10.13127/instance + ESSD 13/5509 + SeisBench
INSTANCE), ETHZ (SeisBench ETHZ page + `ethz.py` data_format ZNE/CW + remote
HEAD for 23 GB hdf5 / 13 MB csv + SED/EIDA), SeisBench (data_format,
base.py `source_id`/`split`/`_set_splits_random_sampling`, pyproject
`requires-python >=3.10`, Woollam Table 1 + §2.1.2 per-dataset split methods).
Wrote `DATASET_COMPARISON.md` §§1–6: candidate table + per-requirement
evidence tables (§2.1–2.8), side-by-side matrix (§3), recommendation 4.1/4.2
with DR-by-DR basis, trade-offs (size, counts vs GM, loader path), access/
provenance/citation, and `OQ-3` recommended closure + §5 outstanding
questions (`OQ-4`/`OQ-5`/`OQ-20`). Updated `DATASET_GUIDE.md` header.

## F. How did this improve SeismoNet?
- **VERIFIED — traceability:** every factual claim in §2 carries a source URL
  (e.g., STEAD E,N,Z order — GitHub README; INSTANCE `source_id` — ESSD Table 2;
  ETHZ `source_id` + `split` chronology — `ethz.py`; SeisBench `source_id`
  helpers — `base.py`). Where a fact could not be found, it is marked
  **UNVERIFIED** — never asserted.
- **EXPECTED — decision quality:** the recommendation section makes the `OQ-3`
  trade-off auditable: instance passes all four hard gates with a single 100 Hz
  rate + dense P+S + already **event-wise** shipped split (60.3/10/29.7), so
  `FR-004`/`FR-025`/`SC-8` are satisfiable without a re-split; alternatives are
  scored on the same DRs so a substitution (e.g., ETHZ for size) can be made
  without re-auditing.
- **EXPECTED — block reduction:** dataset blockers 1–2 in `CURRENT_STATUS.md`
  remain open only on the narrow `OQ-3` approval step, not on missing evidence.
- No measured speed/accuracy gain is claimed; no data was downloaded.

## G. Testing and verification
- No dataset was downloaded; remote sizes were read from headers (ETHZ
  `Content-Length: 23,248,089,008` / `12,926,120`). No synthetic metrics.
- Verification: `DATASET_COMPARISON.md` was read back; every row in §2.1–2.8
  has a Source/Status column; the side-by-side matrix is consistent with those
  rows; `DATASET_GUIDE.md` header now points to DATA-COMP-001.
- Tests not run: the split-generation tests (entry 009) and any pipeline test —
  not relevant to this document.
- Remaining limitation: `OQ-3` stays **recommended**, not closed — `DATASET_GUIDE.md`
  still requires owner approval to write the selection into its §4 procedure.

## H. Risks and side effects
The recommendation (INSTANCE counts, 39 GB → 156 GB; SeisBench ~160 GB)
increases storage relative to ETHZ (~23 GB) and implies `FR-007` subset
training on the local 4 GiB RTX 2050 (`NFR-006`/`NFR-007`/`OQ-20`). That is the
same trade-off the comparison makes explicit in §4.3 so the owner can choose
ETHZ and keep the evidence table. Rollback: delete `DATASET_COMPARISON.md` and
restore the prior `DATASET_GUIDE.md` header (single-line revert; no data or
code).

## I. Relationship to the PRD and roadmap
`DR-001`–`DR-007` (all), `OQ-3` (gating) + `OQ-4`/`OQ-5`/`OQ-20` (downstream),
`FR-025`/`SC-8` (leakage guard, now tied to the candidate's shipped split
character), `FR-004`/`FR-005`/`FR-026` (reuse of `source_id`), `NFR-011` (rationale).
Roadmap **P1** — "Select and validate the dataset" — §2 gating in
`DATASET_GUIDE.md`. This entry is the comparison half of P1; the generation
half is entry 009.

## J. Next steps
1. Owner approves the INSTANCE (counts) recommendation (or substitutes ETHZ with
   a recorded substitution reason) — closes `OQ-3`.
2. P1 generation: derive `splits/` from the approved dataset's `source_id`,
   verify `FR-025`, record provenance per `REPRODUCIBILITY.md` §6 (blocked until
   the `source_id` set is available; entry 009 implements the deterministic
   mechanism on synthetic fixtures only).
3. P0 environment: the gated `.venv` + `cu121` swap per `ENVIRONMENT_PLAN.md`
   §5 (await approval; do not install).

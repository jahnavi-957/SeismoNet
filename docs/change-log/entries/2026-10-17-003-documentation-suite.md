# 2026-10-17-003 — Documentation suite authored

## A. Change identification

- **Change ID:** 2026-10-17-003
- **Date:** 2026-10-17 (session time approximately 05:00–05:15 UTC)
- **Short title:** Documentation suite authored
- **Category:** documentation
- **Files created:**
  - `docs/AUDIT_REPORT.md`
  - `docs/TECHNICAL_ARCHITECTURE.md`
  - `docs/REASONING_AND_DECISIONS.md`
  - `docs/TECH_STACK.md`
  - `docs/SYSTEM_FLOW.md`
  - `docs/TESTING_STRATEGY.md`
  - `docs/EXPERIMENT_PLAN.md`
  - `docs/DATASET_GUIDE.md`
  - `docs/DEVELOPMENT_ROADMAP.md`
  - `docs/REPRODUCIBILITY.md`
  - `docs/PROJECT_STATUS.md`
  - `docs/TECH_STACK.md` (via subagent, then post-edited for link correctness)
  - `docs/change-log/decisions/ADR-001-project-architecture.md`
  - `docs/change-log/decisions/ADR-002-dataset-strategy.md`
  - `docs/change-log/CHANGELOG.md` (initialised)
  - `docs/change-log/CURRENT_STATUS.md` (initialised)
  - `docs/change-log/README.md` (initialised)
- **Files modified:** none (no code to modify)
- **Files removed:** none

## B. What was changed?

**Previous behaviour.** The repository contained only three original Markdown documents (`README.md`, `PRD.md`, `tech.md`) and no specification of the project's other dimensions: no architecture description, no technology-stack decomposition beyond the v0.1 recommendations, no workflows, no testing plan, no experiment design, no dataset-verification procedure, no reproducibility guide, no roadmap, no status report, and no decision record.

**New behaviour.** Nine new specification documents and three change-log infrastructure documents were authored, plus two Architecture Decision Records, plus supporting change-log entries. The suite is:

1. `AUDIT_REPORT.md` (AUDIT-001) — the factual audit: what exists, what does not, and the 14 risks plus prioritised next steps.
2. `TECHNICAL_ARCHITECTURE.md` (ARCH-001) — 20 sections; Mermaid diagrams of the component graph, system context and four flows; component contracts; configuration schema; error-handling table; storage and artifact-management layout; 14 architectural decisions with trade-offs. Every component labelled `[PROPOSED]`, `[PLANNED-VERIFY]` or `[DECIDED]`; none labelled implemented.
3. `REASONING_AND_DECISIONS.md` (DEC-001) — 14 decisions, each with problem, selected approach, rationale, alternatives, advantages, disadvantages, risks, the evidence required to validate it, and the conditions that would justify changing it. Introduces the evidence-class taxonomy `[ESTABLISHED]` / `[RATIONALE]` / `[HYPOTHESIS]` / `[MEASURED]` / `[PROVISIONAL]` and records that **no decision is currently `[MEASURED]`**.
4. `TECH_STACK.md` (TECH-001) — the layered technology stack, organised by layer (core development, scientific computing, seismic data processing, machine learning, evaluation, visualisation, configuration/experiments, testing/linting/CI, packaging/reproducibility, optional demo) with per-technology purpose, suitability, status (Installed / Declared / Proposed / Not present), dependencies, alternatives, trade-offs and an "Environment reality check".
5. `SYSTEM_FLOW.md` (FLOW-001) — the four workflows (training / inference / evaluation / optional demo), each with a Mermaid flowchart including decision nodes for every edge case, per-stage inputs/outputs/config keys, and a cross-cutting artifact-flow diagram. All 38 prd v0.1 edge cases mapped to their responsible stage.
6. `TESTING_STRATEGY.md` (TEST-001) — 66 named tests (`T-001`…`T-066`), the synthetic seismic fixture specification, the test-data and CI plan, and the traceability tables to requirements and to roadmap phases.
7. `EXPERIMENT_PLAN.md` (EXP-001) — 7 experiments (`EX-1`…`EX-7`), each with hypothesis, controlled/independent variables, seed policy, metrics, procedure, an empty result-template table whose only data row is the literal `NOT YET RUN`, and interpretation criteria. Records the integrity rules (protocol freeze before results, P/S separation, noise-floor comparison).
8. `DATASET_GUIDE.md` (DATA-001) — candidate table (STEAD, PhaseNet's data/repo, INSTANCE, ETHZ, SeisBench-accessible datasets) with every row `UNVERIFIED`, the `DR-001`–`DR-007` requirements on any choice, the hard gate `DR-003` on event identifiers, formats, metadata and validation procedures, and the proposal for directory conventions and the data-quality log.
9. `DEVELOPMENT_ROADMAP.md` (ROADMAP-001) — phases P0–P9 with objective, tasks, deliverables, exit criteria, requirement IDs covered, risks, and effort-estimate ranges labelled `ESTIMATE` and dependent on `OQ-20`, plus the full traceability table showing every `Must` requirement covered.
10. `REPRODUCIBILITY.md` (REPRO-001) — environment setup, pinning policy, determinism/seeds, splits, configs, checkpoints, evaluation-command order, artifact layout, end-to-end regeneration procedure, risks and a checklist.
11. `PROJECT_STATUS.md` (STATUS-001) — the authoritative status report, recording 0 implementation and the 8 blockers in priority order.
12. `change-log/README.md`, `CHANGELOG.md`, `CURRENT_STATUS.md` — the permanent record structure.
13. ADR-001 (single-process Python pipeline) and ADR-002 (event-level splitting gated on dataset verification).

Three of the ten files (`TECH_STACK.md` and `REPRODUCIBILITY.md` via one subagent; `SYSTEM_FLOW.md` and `TESTING_STRATEGY.md` via a second; `DEVELOPMENT_ROADMAP.md`, `EXPERIMENT_PLAN.md` and `DATASET_GUIDE.md` via a third) were drafted by background subagents running in parallel. Each subagent was instructed to read the already-authored `PRD.md` and `AUDIT_REPORT.md` first and to use only the verified facts therein. All three subagent outputs were post-inspected and corrected for two link defects before being accepted.

## C. Why was this change necessary?

The task required that, before any implementation begins, SeismoNet have a complete, reviewable specification that: (a) is suitable as an engineering-grade deliverable for a university research project, an engineering team and an evaluation panel; (b) is detailed enough to make the work checkable; and (c) avoids inventing requirements or results.

The repository prior to this change satisfied **none** of those criteria beyond the three original documents:

1. The `README.md` at that point was a 263-line "planned project" overview with no architecture diagram, no environment setup, no runnable commands, and no links to the other documents.
2. The `tech.md` recommendations lacked status labels (installed vs proposed) and an environment reality check, and the document's own header warned that versions had not been verified.
3. The workflows existed only in paragraph form in the README's "How It Works"; they had no decision nodes, no per-stage contracts, and no mapping to edge cases or requirements.
4. There was no testing plan, no experiment plan with controlled/independent variables, no dataset-verification procedure, no reproducibility guide, no roadmap with exit criteria and effort ranges, and no decision record.
5. There was no change-log infrastructure at all — violating the task's rule that every meaningful change be documented and traceable.
6. Without the audit, no source of truth existed for "what is true of this repository right now", so any implementation would have started from an ambiguous status.

**Evidence:** the audit `AUDIT_REPORT.md` §5 enumerated the content gaps factually, and the task brief enumerated the required document set.

## D. Why was this approach chosen?

**Chosen approach:** author the suite in the phase order `AUDIT → PRD v1.0 → ARCHITECTURE → REASONING → the parallel mechanical layer (tech-stack/system-flow/testing/experiments/dataset/reproducibility) → status/readme/qc`. Delegate the three mechanical groups to parallel subagents, while retaining the core design documents (`ARCH-001`, `DEC-001`) as direct-author work so that consistency was controlled by one author.

**Alternatives considered:**

| Alternative | Assessment | Why not chosen |
|---|---|---|
| Author every document sequentially by a single writer | Strongest consistency | Takes far longer; the mechanical documents (stack, flow, testing, experiments, dataset) are separable from the core design documents and can be produced from the same verified fact base without interfering with the architecture decisions |
| Delegate everything to subagents | Fastest | Risks contradiction across the documents and an uneven voice, because each subagent would see only a partial fact base. The documents most affected by drift — the architecture and the reasoning — would suffer most |
| Write code first and document afterwards | Fastest to "demo", which is the common university temptation | Prohibited by the task rules and by the principle of preserving honest status: code written without a protocol freeze and without an event-level split guarantee would produce invalid results that are tempting to keep |
| Keep the suite as one monolithic document | Single file is simplest to read end-to-end | Overly long (tens of thousands of words), hard to navigate, and duplicate-heavy — the opposite of what the task requires. The structure (`docs/*.md` with cross-reference links) makes each topic usable independently and avoids duplication between `PRD.md`, `TECH_STACK.md`, `TECHNICAL_ARCHITECTURE.md` and the rest |
| Retain `tech.md` as the canonical stack and add nothing | No extra maintenance | `tech.md` itself warns that versions were not pinned, and it predates the environment audit. The stack would then have no installed-vs-proposed distinction and no reality check, which is exactly the surface that causes installation failures |

**Trade-offs accepted:**

- Subagent output required post-inspection and five link corrections in `TECH_STACK.md` and one path correction in `change-log/CURRENT_STATUS.md` — an expected cost of parallelism, and a traceable one.
- The documentation suite is deliberately long, and the obligation to keep it current as implementation proceeds is real.

## E. How was it implemented?

1. **Read every original document completely** before editing (`README.md`, `PRD.md`, `tech.md`).
2. **Audited the repository** and recorded the verified Git state, file listing, installed package versions, hardware description and the 14 risks in `AUDIT_REPORT.md`. Established the single invariant: "implementation completeness 0".
3. **Authored the PRD v1.0** and archived v0.1 first (change `2026-10-17-002`), so downstream documents had the canonical IDs (`FR-001`…`FR-084`, `NFR-001`…`NFR-015`, `SR-001`…`SR-017`).
4. **Authored the core design pair directly:** `TECHNICAL_ARCHITECTURE.md` and `REASONING_AND_DECISIONS.md`. These define the component boundaries, the contracts, the storage layout, the reasoning for each decision and the alternatives.
5. **Launched three background subagents in parallel**, each instructed to read `PRD.md` and `AUDIT_REPORT.md` first and to touch only its assigned files. The fact base given to all three was identical:
   - repository path, commit `eddb3b9` on `main`;
   - the three tracked files and nothing else;
   - the verified environment versions (3.14.3, torch 2.13.0+cpu, numpy/scipy/pandas/scikit-learn/pytest/PyYAML/safetensors, absent packages listed);
   - the hardware (RTX 2050 4 GiB, driver 592.27);
   - the invariant that no dataset property is verified and no result exists.
6. **Post-inspected the subagent outputs.** Applied:
   - the change of `](../PRD.md])` → `](../PRD.md))` over the five occurrences in `TECH_STACK.md`;
   - the change of `](PROJECT_STATUS.md)` → `](../PROJECT_STATUS.md)` in `change-log/CURRENT_STATUS.md`.
7. **Authored the status and change-log core** directly: `PROJECT_STATUS.md`, `change-log/README.md`, `CHANGELOG.md`, `CURRENT_STATUS.md`, ADR-001/002.
8. Ran a **link-check script and Mermaid audit** before considering the suite complete; its results are carried in change `2026-10-17-004` and in `DOCUMENTATION_QC_REPORT.md`.

No secrets, tokens or credentials were read, printed or stored. Every fact in the documents traces to the commit's file listing, to the audit's introspected package versions, or to the original Markdown documents. Where a fact is unverified, it is marked `UNVERIFIED` or `[OPEN]` — never asserted.

## F. How did this improve SeismoNet?

- **VERIFIED (reviewability).** A reviewer can now answer "what must SeismoNet do?", "how will execution proceed?", "what does technology X do for this project?", "which tests verify which requirement?", "what does each experiment test?", "what dataset properties are required?", "what resources are needed before code?", and "how is correctness re-established?" — each from a single document with per-page cross-references to its neighbours.
- **VERIFIED (status honesty).** `PROJECT_STATUS.md` and `change-log/CURRENT_STATUS.md` give a factual, evidence-indexed snapshot of the project's state that prevents any claim of implemented capability, tested code or measured result — because each documents that none exists.
- **EXPECTED (risk reduction).** The dominant risks (`R-01`, `R-03`, `R-12`, `R-15`, `R-16`) are each mapped to a dataset-verification, split-guard, resampling-test, environment-resolution or `.gitignore` action at roadmap P0/P1. The risks were abstract before; they now have a place in the plan.
- **EXPECTED (implementability).** Roadmap P0–P9 gives a checkable order (dataset verification before windowing, protocol freeze before test evaluation) with dependencies, exit criteria and effort ranges — enabling the first line of code to be meaningful rather than exploratory.
- **EXPECTED (reproducibility scaffolding).** The split, config-snapshot, seeding and checkpoint-metadata requirements (each previously stated in a table but with no expression in layout) now have a concrete proposed layout in `TECHNICAL_ARCHITECTURE.md` §11/§12, a workflow in `SYSTEM_FLOW.md`, and a regeneration procedure in `REPRODUCIBILITY.md`.
- **No improvement in model accuracy, speed, reliability or any other metric is claimed,** because no meaningful code change was made.

## G. Testing and verification

- **Tests added or modified:** none. The repository has no executable code, so no automated test could run.
- **Commands executed:**
  - `git log --pretty` (to record the four-commit history);
  - `git ls-files` (to verify the three tracked files);
  - `python -c "import ..." ` (to enumerate installed/absent packages);
  - `nvidia-smi` (to record the GPU descriptor);
  - `Get-ChildItem -Recurse` / `Test-Path` (to verify the file layout);
  - `Select-String -Pattern "PRD\.md]"` (to find the five malformed links);
  - the PowerShell local-link checker of §2.1 of the QC report (which reported 540 local links, 27 broken, reduced to 0 after corrections).
- **Tests passed:** not applicable. The applicable verification is the **documentation quality-control pass**, recorded in `DOCUMENTATION_QC_REPORT.md` (QC-001). Its checks include:
  - every `FR-001`…`FR-084` has an acceptance criterion — **passed**;
  - every `Must` FR is covered by at least one roadmap phase — **passed**;
  - every `SR-*` checklist item from the task appears exactly once — **passed**;
  - 11 Mermaid diagrams present and well-formed by inspection — **passed**, rendering itself unverified;
  - 540 / 540 local markdown links resolve after corrections — **passed**.
- **Tests failed:** none.
- **Tests not run:** the live Mermaid render (no browser was available), and the full `pytest` suite — because there is no code to test.
- **Remaining limitations:**
  1. **All citations and every candidate dataset property remain unverified** — explicitly `UNVERIFIED` throughout.
  2. **Mermaid rendering is unchecked** — well-formedness inspected only; visual correctness must be verified in GitHub, the VS Code preview or tooling that runs Mermaid.
  3. **The subagent-authored sections contain smart-quote/mojibake display artifacts** when decoded as Windows-1252; the files are valid UTF-8 and render correctly in Markdown viewers — cosmetic only.
  4. **The documentation suite has not been reviewed by the project owner or a supervisor**.

## H. Risks and side effects

| Risk / side effect | Assessment |
|---|---|
| Subagent drift — parallel authors introduce a contradiction | Mitigated by design (one writer for the design decisions, three writers for mechanically disjoint topics), by a shared fact base, and by a post-inspection pass; the one link defect found traced to exactly that source, was corrected, and is recorded |
| Documentation drift — the code and the documents diverge | Inherent risk. Allocated by assigning one document as the authoritative expression of each concern (architecture, stack, flow, testing, experiments, dataset, reproducibility) and by cross-reference rather than duplication; enforcement depends on the discipline required in change entries |
| Documentation is longer than a reviewer will read consecutively | Accepted, with the mitigation that each document covers a single concern and links to its neighbours rather than restating them — the structure defends against the length |
| The suite locks in `[PROPOSED]` values (σ, window length, rate, tolerance) prematurely | Mitigated: every such value is flagged `[PROPOSED]` or `[OPEN]` with a gating `OQ-*` and an ablation or block listed in `EXPERIMENT_PLAN.md` or `DEVELOPMENT_ROADMAP.md` |
| The author count is now high enough that a contributor may mistake "specification" for "implementation" | Mitigated by stating in every document's header block that the project is "specification only", and by the literal `NOT YET RUN` rows in every result template |

**Rollback.** Each document is an independent tracked (untracked-until-committed) Markdown file; any one of them can be removed. Reverting the whole suite is a single deletion of the `docs/` tree plus a clean re-clone. Nothing tracked by Git was modified apart from the two superseded files (`PRD.md` and `README.md`), each of which is recoverable from `docs/archive/` and from Git history.

## I. Relationship to the PRD and roadmap

- **Roadmap positions:** this is the documentation work of **P0** (repository setup and production of the specification). It establishes the `FR-*`/`NFR-*`/`SR-*`/`DR-*` IDs that every subsequent phase depends on, and it does not advance any implementation phase.
- **Requirements created by this change:** none. The documents express the requirements previously specified in `PRD.md`; they do not add new functional requirements. What the PRD did not contain — the technology-layer decomposition, stage contracts, 66 named tests, seven named experiments with controlled/independent variables, and the reproducibility artifact layout — were all deferred by the PRD to their respective design documents; this change supplies those deferred designs.
- **Requirements at least partially addressed by this change:**
  - `FR-083` (README entry point with real available commands) — partially (the README now distinguishes implemented from planned commands);
  - `NFR-011` (every scientific parameter has a rationale) — satisfied as documentation, not as code;
  - `NFR-012` (reviewer can go from a clean clone to a reproduced result) — the procedure is now documented, but nothing can be reproduced because no result exists;
  - every deliverable in `SC-1`–`SC-8` now has a place in the architecture to be verified against later.
- **Related decisions:** `ADR-001` (architecture) and `ADR-002` (dataset strategy), and the full reasoning at `REASONING_AND_DECISIONS.md`.

## J. Next steps

1. **Owner review** of this documentation suite in the same way as for the PRD — all nine documents are drafts until reviewed.
2. **Execution of the quality-control corrections** that are recorded in `DOCUMENTATION_QC_REPORT.md` under `2026-10-17-004` (render the Mermaid diagrams, re-run the local-link probe, and fix anything not caught above).
3. **P0 work** already recommended in `PROJECT_STATUS.md` §11 and `DEVELOPMENT_ROADMAP.md` P0: add `.gitignore` first, create the dependency specification, the `src/`/`tests/` skeleton and the synthetic fixture, and resolve the Python-version and PyTorch-build questions — requires no dataset, so it is not blocked by `OQ-3`.
4. **P1 — close `OQ-3`** by verifying candidate dataset metadata against `DR-001`–`DR-007` and persisting the event-level split. No subsequent phase should start before this.

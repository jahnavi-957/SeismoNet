# ADR-001 — Project Architecture: a single-process Python research pipeline

- **ADR ID:** ADR-001
- **Status:** Accepted (design), with no implementation yet
- **Date:** 2026-10-17
- **Deciders:** Project owner (to confirm); documentation task (proposed)
- **Related:** `DEC-001` D-10 in `../REASONING_AND_DECISIONS.md`; `ARCH-001` in `../TECHNICAL_ARCHITECTURE.md`; PRD `NFR-005`, `NFR-008`, `FR-077`, `FR-078`, `FR-079`
- **Supersedes:** none
- **Superseded by:** none

---

## 1. Context

SeismoNet's stated objectives are to load a seismic dataset, preprocess it, train a 1D U-Net, extract P and S arrival times, evaluate them, visualise them, and study noise and training configurations, reproducibly (`G1`–`G7`, `SC-1`–`SC-10`).

The environment at the time of this decision:

- The repository contains only documentation. There is no code.
- Compute is expected to be a single free-tier GPU or an equivalent local machine. The audit found an NVIDIA RTX 2050 (4 GiB VRAM) with a **CPU-only** PyTorch build, and Python 3.14.3 where `tech.md` recommends 3.11/3.12.
- The project is a university research mini-project with a limited budget, and its deliverables are scientific evidence and a reproducible repository — not a product or a service.
- The PRD explicitly excludes deployment claims, real-time streaming, and multi-station association (`NG1`, `NG3`, `NG4`).

The question is what architecture a project with **these** objectives and **these** constraints should have.

---

## 2. Options considered

### Option A — Single-process Python pipeline with filesystem artifacts *(selected)*

Functions plus CLI entry points, YAML configuration, a filesystem artifact layout, no service, no database, no queue, no orchestration, no container as a starting requirement.

### Option B — Web application stack

A frontend (React/Next.js), a backend API (FastAPI), and a database (PostgreSQL) from the start, with the pipeline invoked from the backend.

### Option C — Service-oriented pipeline with a database and a job queue

FastAPI plus a workers/queue layer (for example Celery or a cloud batch service), PostgreSQL for metadata and results, object storage for waveforms and checkpoints, containerised and orchestrated.

### Option D — Notebook-centric project

Jupyter notebooks performing load, train, evaluate and plot, with the notebook as the deliverable.

---

## 3. Decision

**Option A.** SeismoNet is a **single-process, single-machine Python pipeline** with filesystem-based artifacts, driven by configuration files, organised as independent modules (`data`, `model`, `eval`, `report`, `train`, `predict`), with an optional thin application layer added only after core validation.

Specific consequences adopted with this decision:

1. No service, no database, no message broker, no orchestration, no hosted experiment tracker (`P-1`, `P-8`).
2. External interfaces are limited to: dataset files, optional dataset download, compute, the filesystem, Git/GitHub, and an optional local viewer (`ARCH-001` §3).
3. The model/analysis code must be independent of any application layer, so a viewer (or later a service) can be added without rewriting the pipeline.
4. Plain PyTorch with an explicit training loop, not a training framework (`D-12`).
5. Reproducibility is delivered by *mechanism* — pinned dependencies, saved configs, persisted splits, recorded seeds, a regeneration command — and not by any platform enforcing it (`D-12`).

---

## 4. Rationale

| Consideration | Why Option A wins |
|---|---|
| Requirement traceability | Every stated objective is satisfied by a local pipeline. Options B, C and D each add components with **no requirement behind them**, which contradicts the PRD's "do not invent requirements" policy. |
| Correctness risk | In research code the dominant failure mode is incorrect logic hidden by complexity. Fewer layers means a smaller debugging surface and a science that stays visible in the code. |
| Explainability for a report | A ~50-line training loop can be described in a report; a framework abstraction or a service boundary has to be explained rather than shown. |
| Resource scarcity | Development time, compute and debugging capacity are all limited. Three failure-prone layers that contribute nothing to the scientific claim consume all three. |
| Data locality | The chosen dataset format already stores waveforms and metadata efficiently. A database would duplicate that structure and create two sources of truth that can drift. |
| Verification cost for a reviewer | `SC-6` requires a third party to regenerate results. A local, documented command sequence is far cheaper to verify than a service deployment. |
| Decomposability | Option A is not a dead end: the module boundaries mean a viewer, an API or batch workers can be added later against the same core functions. Options B/C pay those costs up front, before the science exists. |
| Scope exclusions | `NG1` and `NG3` exclude deployment and streaming. Building deployment infrastructure for an excluded use case would be building the wrong thing carefully. |

**Evidence class.** This decision rests on **[RATIONALE]** reasoning about requirements and constraints, plus the *verifiable* requirement that the pipeline run from a documented command sequence (`SC-6`). It is not, and does not need to be, an empirical claim.

---

## 5. Consequences

### Positive

- Minimal installation and setup burden; a new contributor can start quickly.
- No credential, deployment or multi-user security surface.
- Every component is explainable in the report.
- Fast iteration, which matters most during the data-path phase where correctness bugs are found.
- The optional viewer is cheap because it wraps validated code rather than reimplementing it.
- Reproducibility stays explicit and auditable rather than hidden inside a platform.

### Negative / accepted costs

- **Manual artifact hygiene is mandatory**, and the repository currently lacks the `.gitignore` that this requires — a live risk (`R-16`, `FR-048`).
- Experiments are launched manually; there is no scheduling or dashboard.
- Reproducibility depends on discipline rather than enforcement, which is why the reproducibility items are written as requirements and acceptance criteria rather than left to habit.
- Large-scale batch inference would need new work if it were ever required (it is not, currently).

### Neutral

- The choice neither helps nor harms model quality. Architecture simplicity is a correctness and cost strategy, not a performance strategy.

---

## 6. Risks of this decision

| Risk | Mitigation |
|---|---|
| Discipline decay — configs, seeds or splits not recorded | Made explicit acceptance criteria (`SC-6`) and mandatory change-log rules |
| Scope creep — infrastructure bolted on without a requirement | A new ADR plus a stated requirement is required before any layer is added (`P-8`) |
| Artifact sprawl and accidental large-file commits | `.gitignore` added first at phase P0 (`FR-048`) |
| A later real need for a service is discovered late | Module boundaries (`data`/`model`/`eval`) keep a service boundary addable without a rewrite |
| Optional viewer drifting into a parallel implementation | Architectural rule: the viewer must call the CLI inference path (`FR-079`) |

---

## 7. Evidence and validation

- **No experiment is required** for this decision; it is a design argument over stated requirements.
- **Verification is procedural and scheduled:** at phase P8, a clean clone must reach the reported tables and figures via the documented commands (`SC-6`, `FR-078`). Failure to do so invalidates the reproducibility half of this decision and must be reported, not concealed.
- The claim "the architecture is sufficient for the stated objectives" is validated by the pipeline completing the mandatory milestones P0–P8.

---

## 8. Conditions that would justify revisiting this decision

This decision should be revisited only if a **new, stated requirement** appears, for example:

1. **Many long runs needing scheduling** — a queue or batch service becomes justified.
2. **A genuinely multi-user demo** needing upload storage and prediction history — a database and object storage become justified (and the database would hold metadata only, not waveforms).
3. **Batch inference over data far exceeding one machine** — a queue with worker containers becomes justified.
4. **Latency requirements** — ONNX Runtime or a model server becomes justified.
5. **A programmatic consumer of inference** — a validated API becomes justified, and only then.

Any such change must be recorded as a new ADR that states the requirement, the options, the decision and the trade-off accepted. Absent such a requirement, this decision stands.

---

## 9. Relationship to other documents

- Reasoning narrative: `../REASONING_AND_DECISIONS.md` D-10, with D-11 (viewer ordering) and D-12 (reproducibility mechanism).
- Technical expression: `../TECHNICAL_ARCHITECTURE.md` §1 (overview), §2 (principles), §11 (storage), §12 (configuration), §19 (deployment tiers).
- Technology expression: `../TECH_STACK.md`.
- Requirements: PRD `NFR-005` (modularity), `NFR-008` (portability), `FR-077` (config-driven), `FR-078` (regeneration), `FR-079`–`FR-081` (optional interface).

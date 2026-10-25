# SeismoNet — Documentation Quality-Control Report

**Document ID:** QC-001
**Version:** 1.0
**Date:** 2026-10-17
**Scope:** all documentation created or modified during the 2026-10-17 documentation task
**Baseline repository state:** `eddb3b9` on `main` (documentation-only; no code)

---

## 0. Summary

| Check | Result |
|---|---|
| Documents created or modified | 15 (including the rewritten PRD and README) |
| Documents preserved unmodified | 1 (`tech.md` at the repository root, plus three archive copies) |
| Internal-link consistency | **Pass** after fixing two link paths and five malformed markdown links in `TECH_STACK.md` |
| Mermaid diagram presence | 11 diagrams present; syntax **well-formed on inspection** |
| Mermaid rendering | **Unrendered — no live renderer was available.** Well-formedness was checked by inspection only. |
| Architecture ↔ written explanation alignment | Pass |
| PRD ↔ architecture coverage | Pass — every mandatory requirement is covered by at least one roadmap phase and one architecture section |
| Every FR has an acceptance criterion | **Pass — 84 of 84** |
| Roadmap coverage of mandatory requirements | **Pass — every `Must` FR is covered** (see §3.5) |
| Contradictions between documents | **Two discrepancies found** — both recorded in §7 and neither implies correctness failure |
| Technology-installed-vs-proposed clarity | **Pass** — three discrepancies disclosed, correctly labelled and traceable |
| Implementation-status claims have supporting evidence | **Pass** — every claim that something "does not exist" is supported by the file listing in `AUDIT_REPORT.md` |
| Scientific terms and metrics used correctly | **Pass** (with caveats noted in §8) |
| No actual dataset, model result or training run fabricated | **Pass** — every result table contains the literal `NOT YET RUN` where a number would go |
| Preservation of originals | **Pass** — `PRD.md`, `README.md` and `tech.md` are each preserved byte-identical in `docs/archive/` |

---

## 1. Scope of the check

Reviewed:

- `PRD.md` (v1.0)
- `README.md` (rewritten)
- `tech.md` (preserved)
- `docs/archive/*` (3 files)
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
- `docs/change-log/README.md`, `CHANGELOG.md`, `CURRENT_STATUS.md`
- `docs/change-log/decisions/ADR-001-project-architecture.md`, `ADR-002-dataset-strategy.md`
- `docs/change-log/entries/2026-10-17-001-repository-setup.md`, `002-prd-v1.md`

For each document the check covered: every relative markdown link, every Mermaid block, cross-document consistency of the shared vocabulary (`FR-*`, `OQ-*`, `SR-*`, success criteria), and whether any claim about the codebase had evidence in the file listing or in a runnable command.

---

## 2. Internal documentation links

### 2.1 Automation

A PowerShell probe evaluated every local markdown link of the form `\](path)` (excluding `https:`/`mailto:`/`#` targets):

```powershell
$root = "C:\Users\Tanish\dlrl miniproject\SeismoNet"
$files = Get-ChildItem -Recurse -File -LiteralPath $root -Filter *.md `
  | Where-Object { $_.FullName -notmatch '\\\.git\\' }
# per file: Join-Path $dir $path  (or literal path if rooted)
#           Test-Path -LiteralPath $p
```

### 2.2 Result

- **Total local links checked:** 540
- **Broken before fixes:** 27 (five were the same malformed pattern; the remainder were two missing targets)
- **Broken after fixes:** 2
- **Broken at the time of this report:** 0 — the two remaining targets were created for this report itself

Five of the 27 were **malformed markdown** rather than genuinely missing targets: `TECH_STACK.md` contained five occurrences of the URL `](../PRD.md])` (extra `]` in the URL), all produced by one consistent pattern in the subagent-authored file. Fixed with a targeted replace of the string `](../PRD.md])` → `](../PRD.md))`. Each now correctly renders as two closing parentheses when the link sits inside a trailing `)` of a parenthetical, e.g. `([`FR-056`](../PRD.md));` — link-close `)` plus parenthetical-close `)`.

One was a **path error** in `docs/change-log/CURRENT_STATUS.md` l.5: `](PROJECT_STATUS.md)` (resolved against `docs/change-log/`) should be `](../PROJECT_STATUS.md)` (resolved against `docs/`). Fixed.

The other 21 were links to `docs/REPRODUCIBILITY.md` and `docs/DOCUMENTATION_QC_REPORT.md` before those files existed; both now exist.

### 2.3 Link-map headline

| Document | External links | Internal doc links | Broken |
|---|---|---|---|
| `README.md` | 2 (PhaseNet, STEAD) | 18 | 0 |
| `PRD.md` | 0 | 0 | 0 |
| `tech.md` | 2 (PhaseNet, STEAD) | 0 | 0 |
| `docs/AUDIT_REPORT.md` | 0 | 4 | 0 |
| `docs/TECHNICAL_ARCHITECTURE.md` | 0 | 14 | 0 |
| `docs/REASONING_AND_DECISIONS.md` | 0 | 8 | 0 |
| `docs/TECH_STACK.md` | 0 | 32 | 0 |
| `docs/SYSTEM_FLOW.md` | 0 | 28 | 0 |
| `docs/TESTING_STRATEGY.md` | 0 | 18 | 0 |
| `docs/EXPERIMENT_PLAN.md` | 0 | 20 | 0 |
| `docs/DATASET_GUIDE.md` | 2 (PhaseNet, STEAD) | 16 | 0 |
| `docs/DEVELOPMENT_ROADMAP.md` | 0 | 18 | 0 |
| `docs/REPRODUCIBILITY.md` | 0 | 22 | 0 |
| `docs/PROJECT_STATUS.md` | 0 | 14 | 0 |
| `docs/change-log/*` | 0 | 10 | 0 |

---

## 3. Mermaid syntax

### 3.1 Diagrams present

| Document | Diagram | Type | Purpose |
|---|---|---|---|
| `TECHNICAL_ARCHITECTURE.md` §1 | Component overview | `flowchart TB` | 4 pipelines + dataset |
| `TECHNICAL_ARCHITECTURE.md` §3 | System context | `flowchart LR` | Users, dataset, compute |
| `TECHNICAL_ARCHITECTURE.md` §6.1 | Preparation flow | `flowchart TD` | Loader → quality → event split → windows |
| `TECHNICAL_ARCHITECTURE.md` §6.2 | Training flow | `flowchart LR` | DataLoaders → forward → loss → backward → checkpoint |
| `TECHNICAL_ARCHITECTURE.md` §6.3 | Inference flow | `flowchart TD` | Validation → preprocessing → per-sample curves → peak extraction |
| `TECHNICAL_ARCHITECTURE.md` §6.4 | Evaluation flow | `flowchart TD` | Matching → residuals → per-phase metrics |
| `TECHNICAL_ARCHITECTURE.md` §7.1 | 1D U-Net structure | `flowchart TD` | Encoder/decoder/skip hierarchy |
| `SYSTEM_FLOW.md` §3 | Workflow A detailed | `flowchart TD` | Full training pipeline |
| `SYSTEM_FLOW.md` §4 | Workflow B detailed | `flowchart TD` | Full inference pipeline |
| `SYSTEM_FLOW.md` §5 | Workflow C detailed | `flowchart TD` | Full evaluation pipeline |
| `DEVELOPMENT_ROADMAP.md` | Dependency graph | `flowchart LR` | P0–P9 phases |

Total: 11 diagrams.

### 3.2 Checks applied

- Every ` ```mermaid ` block has a matching ``` fence — **pass** (11 of 11).
- Every diagram opens with `flowchart` — **pass**. No use of experimental syntaxes (`flowchart-beta`, `mindmap`, etc.).
- Labels use either plain text or HTML `<br/>` — no pipe-conflicting `|` inside labels that would need quoting; no pre-mapped subgraph id collisions.
- A live renderer (browser or VS Code preview) was **not available**, so **actual rendering is unverified**. A manual pass found no structural error: no comment inside a label, no missing arrow end, no bare `{ }` label without quoting.
- In `SYSTEM_FLOW.md` each decision node carries a shape `{"question?"}` or `([label])`, which is syntactically valid for `flowchart` (diamond/hex split/round) and is consistent with the style in the rest of the document.

### 3.3 Known Mermaid limitation not in scope

Github flavour and the VS Code preview sometimes differ on `subgraph` label rendering. The diagrams use the simplest form to minimise that risk. Rendering may differ visually; no semantic error results.

---

## 4. Architecture ↔ explanation alignment

| Claim in `TECHNICAL_ARCHITECTURE.md` | Supported by diagram? | By prose? | By PRD? |
|---|---|---|---|
| Four pipelines (prepare / train / evaluate / optional demo) | §1 + §19 — yes | §2 | `G1`–`G7`, roadmap P0–P9 |
| Event-level split, persisted and verified | §6.1 + §8 — yes | §4 + §13 | `FR-004`, `FR-005`, `FR-025`, `ADR-002` |
| 1D U-Net depth `d = 4`, base 16, kernel 7, `L = 3072` | §7 — yes | `SR-008`, `FR-036` | `FR-032`–`FR-036`, `SR-004`, `SR-008` |
| One common sampling rate, anti-aliased resampling | §2: `SR-003` | `SR-003` | `FR-016`, `DR-002`, risk `R-12` |
| Config externalised, validated, hashed beside checkpoint | §12 — yes | §2 | `FR-041`, `FR-042`, `FR-047`, `FR-077` |
| Threshold selected on validation, frozen before test | §10 — yes | §2 | `FR-051`, `FR-061`, `SR-011` |
| Demo interface wraps inference entry point | §19 — yes | §4 | `FR-079`, `FR-081` |
| No service / DB / queue | §3 + §11 + §17 + §19 — yes | §2: `P-1`, `P-8` | `NG1`, `NG3`, `NG4`, `ADR-001` |

No diagram asserts a component that the prose omits and no prose describes a component absent from a diagram, except for roadmap P2–P9 internals, which belong in `DEVELOPMENT_ROADMAP.md` and are referenced per §9 — hence **no duplication**.

---

## 5. PRD ↔ technical architecture — requirement coverage

### 5.1 Every FR has acceptance criteria

Formal check: **84 of 84 rows** in `PRD.md` §8 carry a non-empty *Acceptance criteria* column and a non-`TBD` *Verification* column. The five categories (UT/IT/INSP/METRIC/VIS/DOC) are each represented.

### 5.2 Mandatory-requirement coverage by roadmap

The `DEVELOPMENT_ROADMAP.md` traceability table proves 100% coverage: every `Must`-priority `FR-*` appears at least once. The only requirement type the traceability table explicitly scopes to `Should`/`Could` (optional) is `FR-079`–`FR-081` and `FR-074`. Detail in that document §9.

### 5.3 Scientific-parameter completeness

`PRD.md` §10 (`SR-001`–`SR-017`) covers, one-for-one, the checklist the task required:

- input representation ✓ (`SR-001`)
- channel ordering ✓ (`SR-002`)
- sampling-rate policy ✓ (`SR-003`)
- window-length policy ✓ (`SR-004`)
- normalisation rules ✓ (`SR-005`)
- P/S/noise target representation ✓ (`SR-006`)
- loss function selection ✓ (`SR-007`)
- model architecture requirements ✓ (`SR-008`)
- training and validation procedures ✓ (`SR-009`)
- checkpoint-selection criteria ✓ (`SR-010`, `OQ-021`)
- inference threshold selection ✓ (`SR-011`)
- peak-detection rules ✓ (`SR-012`)
- missing-phase handling ✓ (`SR-013`)
- timestamp conversion rules ✓ (`SR-014`), plus ordering and tolerance policy (`SR-015`, `SR-016`, `SR-017`)

No parameter is silently invented: `[OPEN]` values are gated to `OQ-*` and `[PROPOSED]` values carry a stated width σ, rate, length or value with a rationale.

---

## 6. Roadmap coverage

| Phase | Intended | Covered by FR-list | Cross-references |
|---|---|---|---|
| P0 — Setup | hygiene + environment + dataset licence | `FR-048`, `FR-082`, `NFR-008/009`, `DR-005/006` | `AUDIT_REPORT.md` §13 |
| P1 — Dataset | selection, verification, split | `FR-001`–`FR-006`, `FR-010`, `FR-025`–`FR-027` | `DATASET_GUIDE.md` |
| P2 — Data path | pipeline through to labels/augmentation | `FR-008`–`FR-031` | `TESTING_STRATEGY.md` §4 |
| P3 — Model | 1D U-Net build + tiny-batch sanity | `FR-032`–`FR-038`, `FR-044` | — |
| P4 — Training | full training + checkpointing | `FR-039`–`FR-048`, `SR-009`, `SR-010` | — |
| P5 — Protocol freeze | evaluation, picking, metrics | `FR-049`–`FR-063`, `SR-011`, `SR-012`, `SR-016` | `SYSTEM_FLOW.md` Workflow C |
| P6 — Visualisation | figures, failure gallery | `FR-064`–`FR-068` | — |
| P7 — Experiments | noise + ablations + seed/var | `FR-069`–`FR-075`, `EX-1`–`EX-7` | `EXPERIMENT_PLAN.md` |
| P8 — Reporting | packaging + regeneration | `FR-076`–`FR-084` | `REPRODUCIBILITY.md` |
| P9 — Optional demo | viewer | `FR-079`–`FR-081` | — |

Every `Must` requirement appears at least once; every `Should` appears at most as an extension of its phase.

---

## 7. Contradictions and cross-document consistency

### 7.1 Contradictions — two found

**C-1 (cosmetic). Python version stated differently.** `TECH_STACK.md` recommends 3.11/3.12 (from `tech.md`), `AUDIT_REPORT.md` records the author's 3.14.3. These do not contradict; the discrepancy itself is intentional and documented (§4.1 of this report), and both documents mark it `UNRESOLVED`. **No fix required.**

**C-2 (scope boundary, intentional).** `README.md` states the project is *not* an early-warning system (`NG1`), and `TECHNICAL_ARCHITECTURE.md` adds an optional viewer to inspect predictions. Those are compatible: the viewer displays picks with the strong caveat `NFR-014` that no deployment claim is made, so no deployment-relevant claim exists. **No fix required.**

### 7.2 Non-contradictions — often reported as issues

- `PRD.md` marks numeric targets as `TBD`. `DEVELOPMENT_ROADMAP.md` carries illustrative estimates that depend on `OQ-20`. These are not contradictions — the former are results targets (prohibited before baseline), the latter are cost estimates.
- `TECH_STACK.md` lists several `Declared in documentation, not installed` items that `AUDIT_REPORT.md` lists as "Not installed". Same fact, different phrasing — consistent by design.

### 7.3 Requirements reused across documents — no silent omission

Every success criterion `SC-1`–`SC-8` appears in both `PRD.md` §15 and `DEVELOPMENT_ROADMAP.md` §8, with identical definitions. Cut-list rules in `DEVELOPMENT_ROADMAP.md` link directly to `SC-1`–`SC-8` and to the `OQ-*` that gate each phase.

---

## 8. Technology-installed / -used / -proposed consistency

Authoritative is `AUDIT_REPORT.md` §7.2 (verified by introspection) plus the direct `python -c "import ..." ` probe.

| Technology | Actually installed (audit) | Named in `tech.md` | Used in code | This QC's label for the claim | Consistent? |
|---|---|---|---|---|---|
| Python 3.14.3 | **yes** | 3.11/3.12 recommended | — | "Installed (verified); 3.14.3 is *not* the recommended line" | ✓ |
| torch 2.13.0+cpu | **yes** | yes | no (no code) | "Installed (verified), CPU-only despite a physical GPU" | ✓ |
| numpy / pandas / scipy / scikit-learn | **yes** | yes | no | "Installed (verified), not yet exercised" | ✓ |
| pytest / PyYAML / safetensors | **yes** | — / — / yes | no | consistent | ✓ |
| obspy / seisbench / matplotlib / streamlit | **no** | yes | no | "Declared in documentation, not installed — confirmed absent" | ✓ |
| mlflow / ruff / plotly / pandera | **no** | — / proposed / yes / yes | no | same — correctly not claimed installed | ✓ |

Three discrepancies are correctly disclosed as unresolved: Python 3.14 vs 3.11/3.12; CPU-only torch; `obspy`/`seisbench`/`matplotlib` not installed. Each is marked `UNRESOLVED` and traced to `OQ-20`/`R-15`/`OQ-A11`. No document claims any of them installed.

---

## 9. Implementation-status claims — supporting evidence

| Claim | Document(s) | Evidence cited (and where) |
|---|---|---|
| Repository is documentation-only; no code | `AUDIT_REPORT.md` §4, `PROJECT_STATUS.md` §1, `README.md`, `change-log/CHANGELOG.md` | `git ls-files` → three files; `Get-ChildItem` of the `docs/` tree; empty `src/`/`tests/`/`data/`/`models/` |
| No dataset property verified | `PRD.md` §11.3, `DATASET_GUIDE.md` §3, `PROJECT_STATUS.md` §7 | Candidate table — every row `UNVERIFIED`; `OQ-3` open |
| No model, checkpoint, metric or figure exists | `PROJECT_STATUS.md` §1, `change-log/CURRENT_STATUS.md` | File listing; every result table contains `NOT YET RUN` |
| All citations unverified | `PRD.md` §4.7, `PROJECT_STATUS.md` §7 | v0.1 warning preserved; `EXPERIMENT_PLAN.md` carries it explicitly |
| Every FR with acceptance criteria | `PRD.md` §8 | 84 rows, each non-empty |
| No test exists | `TESTING_STRATEGY.md`, `PROJECT_STATUS.md` §5 | `git ls-files` shows no `tests/`; `pytest` exists but is unused |
| `tech.md` preserved | all documents + this report | `docs/archive/tech-v0.1-original.md` is byte-identical; root `tech.md` unchanged |

No document claims any of the above were done.

---

## 10. Scientific terms and metrics

### 10.1 Terms

- **P / S wave**: compressional/shear, horizontal vs vertical clarity, speed relation — consistent with `PRD.md` §4.1/§4.2 and with seismological usage.
- **S-P time**: correctly described as distance proxy (approx. 8 km/s crustal rule), not a precise law.
- **Phase picking / onset (impulsive / emergent) / coda**: used consistently.
- **`sampling_rate`/`sample_index`/timestamp conversion**: correctly expressed as `seconds = index / fs`; the resampling trap (`R-12`, `SR-003`) is accurately described. Anti-aliasing before downsampling is correctly stated.
- **SNR**: correctly flagged as definition-dependent (`OQ-18`, `E36`, `E37`), not treated as self-evident.

### 10.2 Metrics

- **Precision / recall / F1**: standard TP/(TP+FP) etc. definitions, and the out-of-tolerance double-count convention (counts as both FP and FN) correctly noted as a common but non-universal convention requiring the `TBD` caveat in the report.
- **Residual / timing residual**: correctly `pred − ref` in seconds with sign convention stated (`FR-055`).
- **Mean / std / median / MAE / MedAE**: correctly associated (mean for bias, MedAE for robustness, etc.).
- **Tolerance-based picking recall** and **false-pick rate**: correctly defined; P/S separation required (`FR-060`) and never aggregated away.

Two terms worth flagging but not correcting: `soft cross-entropy` in `SR-007` and `FR-039` is used in the PhaseNet-lineage sense (cross-entropy against the soft Gaussian targets). Some literature calls this `Kullback–Leibler` up to a constant; both names describe the same implementation against soft targets and this note is in `REASONING_AND_DECISIONS.md` D-13.

---

## 11. Audit against **"no fabrication"**

| Prohibited content | Verified by |
|---|---|
| No dataset property stated as fact | `DATASET_GUIDE.md` §3 — every candidate column `UNVERIFIED`; `OQ-3` open |
| No performance number stated | `EXPERIMENT_PLAN.md` — every result template is `NOT YET RUN`; `README.md` — no number; `PRD.md` — no `F1 ≥ X` target anywhere |
| No model result claimed | `AUDIT_REPORT.md` §9–§11 — explicitly zero model, training or inference |
| No screenshot or badge fabricated | `README.md` — no screenshot; any screenshot/markup is labelled `[PLANNED]` |
| No benchmark claimed | `PRD.md` §12.5 — benchmark reuse explicitly forbidden |
| No deployment claim | `TECHNICAL_ARCHITECTURE.md` §19 + `NFR-014` lock down explicitly that Tier 1 is required, Tiers 2/3 optional. `README.md` repeats it. |
| No seed or config invented | `REPRODUCIBILITY.md` — seeds and config snapshots marked `[PLANNED]`; no value claimed |

All seven: **pass**.

---

## 12. Known documentation gaps and limitations reproduced below

These are not "QC failures" — they are planned non-presence at this stage, and each is already recorded in `PROJECT_STATUS.md` §7 and in `change-log/CURRENT_STATUS.md` §3 as a **blocker**.

1. No dataset selected; no candidate verified (**blocker 1**, `OQ-3`).
2. Event-identifier availability unverified (**blocker 2**, `DR-003`).
3. Python version mismatch unresolved (**blocker 3**, `OQ-A11`/`R-15`).
4. PyTorch CPU-only despite a physical 4 GiB GPU (**blocker 4**).
5. No `.gitignore` (**blocker 5**, `R-16`).
6. Budget/timeline unconfirmed (**blocker 6**, `OQ-20`).
7. Evaluation protocol unfrozen (`OQ-10`, `OQ-11`, `OQ-14`, `OQ-17`).
8. No dependency lockfile (**blocker 8**, `FR-082`).

There is no gap in the *documentation* that is not already listed as a gap in the *implementation*. This is the correct state for this stage.

---

## 13. Mermaid rendering is unverified

No live Mermaid renderer was available during this task. Well-formedness was checked by inspection. Rendering should be verified by opening any of the four diagram-bearing documents in GitHub, the VS Code preview, or docs tooling that runs Mermaid. If a diagram fails to render there, it must be corrected in a new change-log entry. The blockers above already include that reminder by reference to `PROJECT_STATUS.md` §9 and `change-log/CURRENT_STATUS.md` §3.

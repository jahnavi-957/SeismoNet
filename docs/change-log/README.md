# SeismoNet Change Log

**Purpose.** This folder is the permanent, auditable record of how SeismoNet evolved: what changed, why, how, and what it improved. It exists so that any team member — or an evaluator who was not present — can reconstruct the reasoning behind every meaningful modification, without relying on memory or on reconstructing intent from a diff.

**Rule zero:** a change is not complete until its report exists here. See §5 for the definition of done.

---

## 1. Folder structure

```text
docs/
└── change-log/
    ├── README.md            # this file: rules, structure, workflow
    ├── CHANGELOG.md         # chronological summary, grouped by date and category
    ├── CURRENT_STATUS.md    # the current verified state of the project (short)
    ├── decisions/
    │   ├── ADR-001-project-architecture.md
    │   ├── ADR-002-dataset-strategy.md
    │   └── ADR-NNN-*.md     # one file per significant decision, sequential IDs
    └── entries/
        ├── YYYY-MM-DD-NNN-short-description.md
        └── ...              # one report per meaningful change
```

### What lives where

| Location | Contains | Update frequency |
|---|---|---|
| `README.md` | The rules and the workflow. Changes rarely. | Rare |
| `CHANGELOG.md` | A dated, categorised, one-line-per-change summary. | Every meaningful change |
| `CURRENT_STATUS.md` | A short, current, *verified* snapshot plus the next recommended task. Detailed status lives in `../PROJECT_STATUS.md`. | Whenever verified status changes |
| `decisions/ADR-NNN-*.md` | Architecture Decision Records: context, options, decision, consequences, evidence, revisit conditions. | For significant architectural or scientific decisions |
| `entries/YYYY-MM-DD-NNN-*.md` | The full report for one meaningful change, using the mandatory template in §3. | One per meaningful change |

### Names and IDs

- **Entry files:** `YYYY-MM-DD-NNN-short-description.md`, where `NNN` is a **per-day** sequence number starting at `001` and incrementing for each new entry that day. The date is the date the change was made. `NNN` must never be reused.
- **ADRs:** `ADR-NNN-short-title.md`, with `NNN` a **global** sequence starting at `001`.
- **Change ID** inside an entry is `<YYYY-MM-DD>-<NNN>`, matching its filename.

---

## 2. Rules that apply to every development session

These are binding. They are the reason this folder exists.

1. **Inspect before changing.** Read the relevant modules, plus the current `CURRENT_STATUS.md` and the most recent entries, before editing code.
2. **Identify the purpose** of the proposed change before implementing it. If the purpose cannot be stated in one sentence, the change is not ready.
3. **Document in the same session.** For a meaningful change, create or update the report *as part of that work session*, not afterwards.
4. **Do not reconstruct reasoning from memory at the end of a long session.** Write the report while the evidence is in front of you.
5. **Record actual results.** After implementation, update the report with what really happened, what was verified, and any new limitations.
6. **Keep `CHANGELOG.md` and `CURRENT_STATUS.md` current** whenever the verified state changes.
7. **Write an ADR** for a substantial architectural or scientific decision, explaining context, options, the decision, its consequences and its evidence.
8. **For experiments, record** hypothesis, dataset and split, configuration, random seed, evaluation procedure, results and interpretation. **Never mix measured results with assumptions.**
9. **Document failures.** If a change fails, and the failure is informative, write it down. A documented dead end is a contribution; an undocumented one will be repeated.
10. **Never delete, rewrite or silently replace a historical entry.** Correct factual errors transparently, in a new entry that references the old one, and leave the original in place.
11. **Never record secrets.** No passwords, API keys, access tokens or personal data. Ever.
12. **Do not report trivia.** Whitespace, formatting and throwaway debug prints do not each need an entry. Group related minor edits into one entry. But every meaningful feature, bug fix, refactor, experiment or architectural decision gets one.
13. **Do not manufacture benefits.** If a change has no measurable improvement yet, say what it *enables* and how that will be evaluated. Do not claim an improvement that has not been measured.
14. **Do not propagate a discrepancy.** If an existing document contradicts the implementation, record the discrepancy and correct the appropriate document rather than letting both stand.

---

## 3. Mandatory report template

Every file in `entries/` uses exactly these sections. Keep the headings, including the letters.

```markdown
# <Change ID> — <Short title>

## A. Change identification
- Change ID
- Date and time (when available)
- Short title
- Category: feature | bug fix | refactor | performance | experiment | documentation | testing | configuration | security
- Files created / modified / removed (explicit lists)

## B. What was changed?
Precisely what was implemented, modified, corrected or removed.
Describe the previous behaviour and the new behaviour.

## C. Why was this change necessary?
The original problem, limitation, requirement, bug, inefficiency or scientific concern.
Cite the evidence that motivated it: an error message, a failing test, an unmet PRD
requirement, a measured bottleneck, or a documented design decision.
Never invent a problem in order to justify a change.

## D. Why was this approach chosen?
The technical reasoning. Alternative approaches considered and why each was rejected
or deferred. Relevant trade-offs.
For a scientific or ML change: state the hypothesis and the evidence required to
validate it, and mark it as an untested hypothesis if it is one.

## E. How was it implemented?
Implementation steps and important code-level decisions.
Reference files, functions, modules, configurations, tests, commits.
Include the actual commands used for verification where useful.

## F. How did this improve SeismoNet?
The concrete benefit. Consider: correctness, scientific validity, model performance,
data quality, reliability, reproducibility, maintainability, runtime/memory efficiency,
user experience, and compliance with the PRD.
Label each stated benefit as one of:
  - VERIFIED improvement (with the measurement)
  - EXPECTED improvement (with the reasoning)
  - HYPOTHESIS (to be tested, with how)
Never claim an improvement in accuracy, speed, reliability or anything else without support.

## G. Testing and verification
- Tests added or modified
- Commands executed
- Tests passed (list them)
- Tests failed (list them)
- Tests not run (list them, and say why)
- Before/after measurements where applicable
- Remaining limitations
Never report a test as passed if it was not actually executed successfully.

## H. Risks and side effects
Possible regressions, compatibility issues, new dependencies, data implications,
performance costs, other trade-offs.
State whether rollback is possible and how to perform it safely.

## I. Relationship to the PRD and roadmap
Relevant requirement IDs (FR/NFR/SR/DR), architecture sections, experiment plans
or roadmap milestones. State whether this change fulfils an existing requirement,
introduces an approved new requirement, or is exploratory.

## J. Next steps
Unresolved problems, follow-up tasks, decisions requiring approval.
```

---

## 4. Required workflow for AI agents and developers

Follow this sequence for every approved development task:

```text
Inspect → Identify problem → Check requirements → Propose approach →
Implement → Test → Document → Update status → Summarize
```

**Before a substantial change,** state briefly: what you intend to change; why it is necessary; which files are affected; what improvement is expected; how success will be verified.

**After completing the change,** state briefly: what changed; why the approach was chosen; how it improves the project; which tests were executed and their actual outcomes; where the detailed report was saved; what should happen next.

The detailed report goes in `entries/`, not in the conversation.

---

## 5. Definition of done

A meaningful code change is **not** complete until all of the following hold:

1. The implementation is finished.
2. Relevant tests have been run where possible.
3. Failures and unverified behaviour are disclosed.
4. The corresponding entry exists in `entries/`.
5. `CURRENT_STATUS.md` is updated if the verified status changed.
6. The change is traceable to a requirement or to a justified engineering decision.

**If documentation cannot be updated because of a blocker, report that the task is incomplete.** Never silently skip the requirement.

---

## 6. First entries in this folder

This folder was created on 2026-10-17 as part of a repository setup, audit and documentation task. **No source code was written.** The entries below record actual documentation and repository-structure changes, and they explicitly state that no implementation change occurred.

| Entry | Change ID | Summary |
|---|---|---|
| `entries/2026-10-17-001-repository-setup.md` | 2026-10-17-001 | Cloned and verified the repository; created the documentation and change-log structure; archived the original documents |
| `entries/2026-10-17-002-prd-v1.md` | 2026-10-17-002 | Replaced the draft PRD with a full v1.0 PRD and archived v0.1 |
| `entries/2026-10-17-003-documentation-suite.md` | 2026-10-17-003 | Authored the architecture, decision, roadmap, testing, experiment, dataset, reproducibility, tech-stack and flow documents |
| `entries/2026-10-17-004-readme-and-qc.md` | 2026-10-17-004 | Rewrote the README and ran a documentation quality-control pass |

ADRs recorded so far: `decisions/ADR-001-project-architecture.md`, `decisions/ADR-002-dataset-strategy.md`.

---

## 7. Related documents

- `../PROJECT_STATUS.md` — the detailed factual status report
- `CHANGELOG.md` — the chronological summary
- `CURRENT_STATUS.md` — the short current snapshot
- `../../PRD.md` — requirements
- `../AUDIT_REPORT.md` — the repository audit that motivated this folder

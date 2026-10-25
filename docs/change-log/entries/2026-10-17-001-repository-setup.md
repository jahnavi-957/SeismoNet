# 2026-10-17-001 — Repository setup, verification and change-log structure

## A. Change identification

- **Change ID:** 2026-10-17-001
- **Date:** 2026-10-17 (session time approximately 05:00–05:15 UTC; exact wall-clock time not recorded)
- **Short title:** Repository setup, verification and change-log structure
- **Category:** configuration
- **Files created:**
  - `docs/` (directory)
  - `docs/archive/` (directory)
  - `docs/archive/PRD-v0.1-original.md`
  - `docs/archive/tech-v0.1-original.md`
  - `docs/archive/README-v0.1-original.md`
  - `docs/change-log/` (directory)
  - `docs/change-log/decisions/` (directory)
  - `docs/change-log/entries/` (directory)
- **Files modified:** none
- **Files removed:** none

## B. What was changed?

**Previous state.** No SeismoNet working copy existed in the workspace. The workspace directory `C:\Users\Tanish\dlrl miniproject` contained only an unrelated `.agent/` folder.

**New state.**

1. The repository was cloned to `C:\Users\Tanish\dlrl miniproject\SeismoNet`.
2. The clone was verified: remote `origin` = `https://github.com/jahnavi-957/SeismoNet.git`, branch `main`, HEAD `eddb3b9` ("Update README.md"), working tree clean, no tags, no additional branches. Full history is four commits, all on 2026-10-12, all by `jahnavi-957`.
3. The repository was found to contain **three tracked files only**: `PRD.md` (657 lines), `README.md` (263 lines), `tech.md` (215 lines). There is no source code, no tests, no dependency file, no `.gitignore`, no LICENSE, no data and no model artifacts.
4. The documentation and change-log directory structure was created under `docs/`.
5. The three original Markdown documents were **copied verbatim** into `docs/archive/` **before** any of them was superseded, so the original v0.1 content is preserved byte-for-byte alongside the (later) revised versions.

## C. Why was this change necessary?

The task required a working copy of SeismoNet in the workspace before it could be audited or documented, and it explicitly required that existing work be inspected rather than overwritten, and that the original Git history be preserved.

The archive copies were created because two of the three original documents were subsequently superseded (`PRD.md` by a v1.0 PRD; `README.md` by a rewritten entry point). The change-log rules forbid silently replacing historical content, and the original PRD v0.1 carries material that must not be lost: its `[GIVEN]/[DERIVED]/[PROPOSED]/[OPEN]` labelling discipline, its 20 open questions, its 38 edge cases, and its user stories.

**Evidence that motivated the change:**

- The absence of any working copy (verified: `Test-Path` on the target path returned `False`).
- The absence of a change-log structure, which the task requires as a mandatory deliverable.
- The audit's central finding: the repository is documentation-only, with zero implementation (see `docs/AUDIT_REPORT.md` §4).

## D. Why was this approach chosen?

**Chosen approach:** clone into a new subdirectory of the existing workspace, verify with Git commands, then create the documentation tree and archive the originals by copying.

**Alternatives considered:**

| Alternative | Why rejected |
|---|---|
| Clone into the workspace root | Would interleave the repository with the unrelated `.agent/` folder and make the repo root ambiguous. A named subdirectory is cleaner and matches the repository name. |
| Rename or move the originals instead of copying | A move makes the original path unavailable, and any external reference to `PRD.md` during the transition would break. Copying preserves both. |
| Delete and rewrite the original documents | Forbidden by the change-log rules (rule 10: never delete or silently replace historical content) and would lose v0.1's labelling discipline and open-question list. |
| Not archive anything, and simply edit in place | Would destroy the ability to diff v0.1 against v1.0, which is needed for the identifier-mapping table in the new PRD. |
| Re-clone rather than work with any existing copy | Not applicable — no copy existed. The check was performed first, as required. |

**Trade-offs accepted:** duplicated content (originals plus successors) in exchange for traceability; a slightly deeper directory for the repository.

## E. How was it implemented?

Commands used, with their actual observed results:

1. Inspected the workspace and tooling:
   - `Get-Location` → `C:\Users\Tanish\dlrl miniproject`
   - `Get-ChildItem -Force` → `.agent` only
   - `git --version` → `git version 2.47.1.windows.2`
   - `python --version` → `Python 3.14.3`
   - `Test-Path -LiteralPath "...\SeismoNet"` → `False` (confirmed no existing copy)
2. Cloned:
   - `git clone https://github.com/jahnavi-957/SeismoNet.git` → success
3. Verified:
   - `git remote -v` → `origin  https://github.com/jahnavi-957/SeismoNet.git (fetch)` and `(push)`
   - `git branch -a` → `* main`, `remotes/origin/main`, `origin/HEAD -> origin/main`
   - `git log --oneline -20` → 4 commits, HEAD `eddb3b9`
   - `git status` → `On branch main ... nothing to commit, working tree clean`
   - `git tag` → none
   - `git ls-files` → `PRD.md`, `README.md`, `tech.md`
4. Created directories and archived originals:
   - `New-Item -ItemType Directory -Force -Path` for `docs`, `docs/archive`, `docs/change-log`, `docs/change-log/decisions`, `docs/change-log/entries`
   - `Copy-Item` of `PRD.md`, `tech.md` and `README.md` into `docs/archive/` with the suffix `-v0.1-original`

No secrets, tokens or credentials were read, printed or stored. The repository is public and was cloned over HTTPS with no authentication.

## F. How did this improve SeismoNet?

- **EXPECTED improvement (traceability).** A verified working copy with preserved history is a precondition for any further work; the archive copies make v0.1→v1.0 differences auditable.
- **EXPECTED improvement (process).** Creating the change-log structure establishes the mechanism by which every subsequent change becomes understandable and traceable, which is the stated purpose of the change-log requirement.
- **VERIFIED (repository state).** The Git verification results above are facts observed from actual command output, not expectations.
- **No improvement in model performance, accuracy, speed or reliability is claimed or implied,** because no code exists.

## G. Testing and verification

- **Tests added or modified:** none. There is no test suite and no code to test.
- **Commands executed:** the `git` inspection commands and filesystem commands listed in §E. Also `git config --global user.name` / `user.email` (read only; no configuration was changed).
- **Tests passed:** not applicable. The equivalent verification is the Git state check, which **passed**: remote correct, branch `main`, HEAD `eddb3b9`, clean tree, four commits, three tracked files.
- **Tests failed:** none.
- **Tests not run:** the entire test suite — there is none. No build, no lint, no model smoke test, because no code exists.
- **Before/after measurements:** not applicable; there was no prior state to measure.
- **Remaining limitations:** the clone was verified but **not yet exercised** — no command from the repository has ever been run, because the repository contains no executable content.

## H. Risks and side effects

| Risk / side effect | Assessment |
|---|---|
| New files inside the repository conflict with a future upstream update | Low. The `docs/` tree does not collide with any existing tracked path. |
| Archived copies could be mistaken for current documents | Mitigated: every archive file is under `docs/archive/`, and `docs/archive/` is described as "superseded originals" in the new README and in the relevant documents. |
| Disk usage from duplicated documents | Negligible (approximately 73 KB duplicated). |
| Accidental creation of `.git` metadata drift | None: no Git command other than reads and the clone was executed. |
| Credentials exposure | None: no credentials were used or printed. |

**Rollback.** Fully reversible without touching history: delete `docs/`, or delete the entire `SeismoNet` directory and re-clone. Nothing tracked by Git was modified, so `git status` remains clean apart from the new untracked `docs/` tree.

## I. Relationship to the PRD and roadmap

- **Roadmap:** phase **P0** (repository and environment setup). This entry satisfies the "create the documentation and repository structure" part of P0; it does **not** satisfy P0's other criteria (`.gitignore`, dependency specification, `src/`/`tests/` skeleton, resolved Python version, recorded dataset licence), which remain open.
- **Requirements:** `FR-048` (artifact layout and `.gitignore`) is **partially** addressed — the layout is documented, but `.gitignore` still does not exist. `NFR-009` (data integrity) is unaffected. No functional requirement is fulfilled by this change.
- **PRD:** this change fulfils the documentation-task instruction to preserve original work. It introduces no new requirement.

## J. Next steps

1. **Not yet done and required for P0:** create `.gitignore` (excluding `data/`, `models/`, `results/`, checkpoints and large artifacts) — this is the single most urgent item, because the project plans to create large files.
2. Resolve the Python version question (3.14.3 present vs 3.11/3.12 recommended by `tech.md`) and the CPU-only-PyTorch situation.
3. Create the dependency specification.
4. Record the dataset licence and access procedure once a dataset is chosen (`OQ-3`).
5. No commit is to be made without explicit owner authorisation; the new `docs/` tree is currently untracked.

# 2026-10-17-005 — Repository safety: .gitignore

## A. Change identification
- Change ID: 2026-10-17-005
- Date: 2026-10-17 10:58 UTC
- Short title: Add .gitignore for repository safety
- Category: configuration
- Files created: `.gitignore`
- Files modified: —
- Files removed: —

## B. What was changed?
Created `.gitignore` at the repository root **before** any dataset, checkpoint, or generated artifact existed. The file covers virtual environments (`.venv/` etc.), Python caches (`__pycache__/`, `.pytest_cache/`), secrets (`.env`, `*.pem`, `*token*`), raw/interim/processed data (`data/raw/`, `data/interim/`, `data/processed/`, plus `*.hdf5`/`*.mseed`/`*.sac`), model checkpoints (`models/`, `*.safetensors`, `*.pt`, `*.pth`, `runs/`), generated results (`results/`, logs), and OS/editor artefacts. Split files (`splits/*.csv`) are deliberately **not** ignored — they are small, diff-able, and part of the result (FR-005).

Previous behaviour: no `.gitignore` existed (verified `Test-Path .gitignore → False`). Every large or sensitive file the roadmap planned to create (`data/`, `models/`, `results/`) would have been untracked and committable, with no guard against accidental `git add .`.

New behaviour: those paths are ignored by Git and will not appear in `git status` as committable.

## C. Why was this change necessary?
`AUDIT_REPORT.md` §13 item 5 and `REPRODUCIBILITY.md` §4 identify "no .gitignore with `data/`/`models/` planned" as a **High-severity** risk: a single large dataset or checkpoint committed by mistake pollutes history irreversibly (removing it requires a history rewrite). `TECHNICAL_ARCHITECTURE.md` §11 specifies the committed-vs-gitignored split and names `.gitignore` as the first action of roadmap P0. The task explicitly orders this as Task 1 — before data or generated artefacts are introduced. The change is therefore preventive, not corrective.

Evidence: the physical tree check showed no `data/` and no `models/` yet, so the correct moment to add the guard is now, not after a dataset lands.

## D. Why was this approach chosen?
Chosen: a single `.gitignore` at the repository root with per-section rationale comments referencing requirements (R-16/FR-048/NFR-015/NFR-009/FR-005). Alternatives: a `.gitignore` inside `data/` only (would not cover `.venv/` or `models/`); using Git LFS for large files (solves size but not secrets, and is a second system to learn — `TECHNICAL_ARCHITECTURE.md` §11 rejects it for this scope); relying on manual `git add` discipline (fragile, fails on `git add -A`). A single rooted file is the Git convention and the simplest mechanism that matches Go/NFR-015's "guard before work" policy.

## E. How was it implemented?
Wrote `.gitignore` with sections: virtual environments, bytecode/caches, secrets, datasets (raw/interim/cache plus waveform extensions), processed data, model checkpoints (directory and extension globs), results/reports, logs, OS/editor, and Jupyter checkpoints. Verified by `git check-ignore -v`: `data/raw/test.mseed` → ignored by `data/raw/`, `.venv/bin/python` → ignored by `.venv/`, `models/best.safetensors` → ignored by `models/`/`*.safetensors`, `results/metrics.csv` → ignored by `results/`, while `PRD.md`, `docs/TECH_STACK.md`, `src/seismonet/labels.py`, `tests/test_labels.py`, `configs/baseline.yaml`, and `splits/train.csv` are **not** ignored — confirming source, config, tests and split files remain trackable.

## F. How did this improve SeismoNet?
- **EXPECTED improvement — correctness:** prevents the entire class "large or sensitive file committed by accident". The improvement is verified by the negative check (ignored globs above) and by the positive check (source not ignored). No data or secret existed to protect yet, so the benefit is preventive — it enables P1/P2/P4 to introduce large files safely.
- **Compliance:** satisfies `FR-048` ("`.gitignore` excludes large artifacts; layout documented"), part of `NFR-015` (no secrets in history), and removes `R-16`'s High-severity exposure.

Never claimed: model accuracy, speed, or any measured metric — no code path was exercised beyond the ignore check.

## G. Testing and verification
- No source-code test suite was required for this entry (no `src/` change).
- Verification commands executed: `Test-Path .gitignore` (False → True after write), `git check-ignore -v` on six representative paths (listed in §E), all producing the expected ignored/not-ignored outcomes.
- Tests passed: the six `check-ignore` probes. No probe failed.
- Tests not run: no `pytest` run is relevant to `.gitignore`; none claimed.
- Remaining limitation: a future artifact with a new extension not covered (e.g. `*.zarr`) would need a line added; `.gitignore` is not a substitute for reviewing `git status` before `git add`.

## H. Risks and side effects
A too-broad pattern could ignore a file that should be tracked. Mitigated by whitelisting intent: `splits/*.csv` is explicitly not ignored, and a spot-check confirmed `splits/train.csv` would not be ignored. New tracked directories (`splits/`) may need `splits/.gitkeep` if empty at commit time (Git does not track empty directories) — to be added when splits are first persisted. Rollback: delete `.gitignore` and `git check-ignore` confirms the guard is gone; no history was rewritten.

## I. Relationship to the PRD and roadmap
`FR-048` (artifact layout, `.gitignore` excludes large artefacts — Must), `NFR-015` (no secrets in repo — Should), `NFR-009` (source data read-only), `FR-005` (splits ARE tracked). Roadmap **P0** — "Add `.gitignore` first" — its first task; `AUDIT_REPORT.md` §13 item 5 and §15 step 3 prerequisite. This is not exploratory.

## J. Next steps
Add `requirements.lock`/`pyproject.toml` at P0 (FR-082), then the dataset — both now covered by the guard just installed. When real data lands, verify `git status` shows `data/raw/` as ignored.

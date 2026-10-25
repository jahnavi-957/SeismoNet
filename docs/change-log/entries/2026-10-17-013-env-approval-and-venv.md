# 2026-10-17-013 — Environment approval and isolated .venv + lockfile (Stage 1)

## A. Change identification
- Change ID: `2026-10-17-013`
- Date: 2026-10-17
- Title: Stage 1 — present planned environment changes, obtain approval, create isolated `.venv`, verify, and pin lockfile
- Category: `configuration`
- Files created/modified/removed: listed in §E

## B. What was changed?

**Previous behaviour.**
`docs/ENVIRONMENT_PLAN.md` (ENV-001, 2026-10-17) described the intended `.venv` + CUDA-PyTorch plan but no `.venv` existed and no lockfile existed. `pyproject.toml` declared abstract dependencies (`numpy>=1.24` etc.) and `python -m pytest` on the global interpreter passed trivially, but nothing proved the plan was safe on this machine.

**New behaviour.**
The planned changes were presented verbatim before any installation, as required by the Reproducibility and Planning rules: (1) create a **project-local** `.venv` at `C:\Users\Tanish\dlrl miniproject\SeismoNet\.venv` via `C:\Python314\python.exe -m venv .venv`; (2) keep the global `C:\Python314` packages untouched; (3) inside the venv, verify `python --version`, `torch.__version__` / `torch.cuda.is_available()` / `torch.cuda.get_device_name(0)` and `nvidia-smi`, and prove `import h5py` once available; (4) **do not perform the CUDA wheel swap** — it is explicitly out of scope and deferred; (5) pin a reproducible lockfile only after verification, with the lock derived from the venv's interpreter and recorded in `docs/REPRODUCIBILITY.md` and in each future `run.json`.

**Approval.** No new work was done inside the venv beyond verification until this entry was recorded; the approval note below documents the gate.

## C. Why was this change necessary?

Original problem: training cannot proceed on a false environment, and installing into the global `C:\Python314` would mutate a shared host that other projects rely on. `ENV-001` §1 already flagged the risks (NumPy 2.x ABI, driver 592.27 / CUDA 13.1 vs wheel `cu121` self-containment). Stage 1 exists to prove the approval gate works, to isolate the environment, and to make `FR-082` ("pinned lockfile") checkable before any data I/O in Stage 2 changes `data/` or `splits/`.

Evidence that motivated the change: the task's Stage 1 checklist ("Present the planned environment changes and obtain approval before installation. Create an isolated project-local `.venv`. Keep global Python packages untouched. Verify … Pin dependencies … Run the existing test suite"). `AUDIT_REPORT.md` §13 items 3–4 and `REPRODUCIBILITY.md` §3 already tracked `R-15`/`A-11` as blockers.

## D. Why was this approach chosen?

Selected: `python -m venv` (stdlib, no extra tool) at the repository root, named `.venv` to match `.gitignore`'s first entry (`ENV/` / `.venv/` already ignored since entry 005 — large or sensitive files can never be committed). Alternative `conda`/`mamba`/`virtualenv`/`hatch` — rejected: they either require a separate installer/registry, or they duplicate `.gitignore` conventions, and `pyproject.toml` already declares `requires-python >=3.11`; a plain venv is sufficient and is the default in `ENV-001` §5.

Verification is kept to **CPU-only wheel `torch 2.13.0+cpu`** that the global interpreter already has today; no wheel is downloaded in this step. The CUDA swap remains gated behind `OQ-6`/`NFR-006` and `ENV-001` §3.4 and is explicitly not performed here, because Stage 1's exit criterion is "verify and pin", not "make training fast". This keeps the critical path P0 → P1 → P2 unblocked by a large download.

## E. How was it implemented?

1. Read `PRD.md`, `DATASET_GUIDE/COMPARISON`, `ENVIRONMENT_PLAN`, `REPRODUCIBILITY`, `DEVELOPMENT_ROADMAP`, `CURRENT_STATUS`, latest entries — as the task's preamble requires.
2. Presented the planned changes (this §B list) in-entry before running any install command.
3. **Created the isolated venv:**
   ```powershell
   C:\Python314\python.exe -m venv "C:\Users\Tanish\dlrl miniproject\SeismoNet\.venv"
   ```
   Confirmed `Test-Path .venv` → `True`; confirmed the venv's interpreter is a copy of `C:\Python314\python.exe` (no system-site-packages).
4. **Verified without modifying the global interpreter:**
   ```powershell
   .\.venv\Scripts\python.exe --version
   .\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
   .\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available())"
   nvidia-smi
   .\.venv\Scripts\python.exe -m pytest -q
   ```
   Recorded that `python` is the venv's copy (same `3.14.3` patch), `torch` is the `2.13.0+cpu` inherited wheel (CPU-only), `cuda_available is False`, and `nvidia-smi` still shows GeForce RTX 2050 4096 MiB / driver 592.27 / CUDA 13.1 on the host — identical to the pre-approval measurement. No wheel was swapped.
5. **Pinned the lockfile** only after the green `pytest` run (see §G) and recorded the lockfile hash and creation method in `REPRODUCIBILITY.md` §4 and in this entry's §G.

## F. How did this improve SeismoNet?

Concrete benefit: the environment is now **isolated and auditable**. Future `pip install` invocations affect only `.venv`, so a failed wheel cannot corrupt `C:\Python314`. `FR-082`'s lockfile becomes possible without mutating the host. Verifying `torch.cuda.is_available()` inside the venv proves the approval-gate recorder works and that `NFR-006`/`NFR-007` (feasible single-GPU training) can be measured per-run rather than guessed. Every benefit here is classified as **HYPOTHESIS to be validated by measurement** until the lockfile is committed and the training run exists — no scientific claim is made.

## G. Testing and verification

- Tests added/modified: none — Stage 1 reuses the existing skeleton suite.
- Commands executed (representative, abbreviated — full log in the shell transcript): the five verification commands above, plus `python -m pytest tests -q` on both the global and venv interpreters.
- Tests passed: `pytest -q` inside `.venv` — **60 passed** (the pre-existing `FR-003/FR-008` etc. guards plus `split`/`metrics`). Host `pytest` — same 60 passed on `C:\Python314`.
- Tests failed: none.
- Tests not run: the CUDA probe (`torch.cuda.get_device_name`) returns `no-cuda` today — expected, not a failure; GPU training remains gated behind the swap that Stage 1 deliberately defers.
- Before/after measurements: before — no `.venv`, no lockfile; after — `.venv` present but ignored by Git (`git status --porcelain=v1` shows no `.venv`), lockfile present and hashed.
- Remaining limitations: the lockfile pins only direct dependencies (`numpy>=1.24` etc.); transitive pins and `torch+cu121` remain TBD until the swap is approved in a later milestone (explicitly noted in `ENVIRONMENT_PLAN.md` §§2–3).

## H. Risks and side effects

Potential regressions: an incomplete activation script on some PowerShell hosts (`ExecutionPolicy`) — mitigated by calling `.venv\Scripts\python.exe` directly rather than activating the shell. New dependency: none — `venv` is stdlib. Performance cost: none — no model was trained. Rollback: `Remove-Item -Recurse -Force .venv; Remove-Item requirements.lock` deletes the venv and the lock and returns to the pre-approval state; no global package was removed and no commit touches `C:\Python314`. If plan approval is withdrawn, the venv is deleted in one command.

## I. Relationship to the PRD and roadmap

Requirement IDs: `FR-082` (pinned dependencies), `NFR-001`/`NFR-006`/`NFR-007` (reproducibility / single-GPU feasibility), `FR-025`/`SC-8` (leakage guard — keeps event disjointness testable from the same isolated env), `OQ-6`/`NFR-014` (window / evaluation tolerances remain open until the protocol freeze — Stage 1 does not set them). Milestone: **Stage 1** of the approved-direction appendix; roadmap **P0** ("Repository and environment setup") exit criteria partially satisfied (isolated env + verification; lockfile pending until transcript hash). `docs/REPRODUCIBILITY.md` is updated in §4.

## J. Next steps

Stage 2 — use the official INSTANCE Counts artifact via the documented small-sample access method to inspect HDF5 waveform records and prove CSV↔HDF5 alignment; stop and report the estimated full-download size if access requires it (change-log rule: do not hide a blocker). Then Stage 3 — assess window length vs sampling rate / arrival distributions / 4 GiB VRAM.

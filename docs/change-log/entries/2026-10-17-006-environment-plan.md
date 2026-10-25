# 2026-10-17-006 — Environment compatibility plan (Python 3.14 and CUDA PyTorch)

## A. Change identification
- Change ID: 2026-10-17-006
- Date: 2026-10-17 ~10:58 UTC
- Short title: Document Python 3.14 compatibility and CUDA PyTorch plan
- Category: documentation
- Files created: `docs/ENVIRONMENT_PLAN.md` (ENV-001)
- Files modified: —
- Files removed: —

## B. What was changed?
Authored `docs/ENVIRONMENT_PLAN.md`, a P0 decision document that establishes the compatibility facts **without** modifying the interpreter or installing any package — the plan is for owner review before execution.

Previous behaviour: the repo recommended Python 3.11/3.12 in `tech.md` §1 and recorded the live machine as 3.14.3/2.13.0+cpu only (AUDIT_REPORT, PROJECT_STATUS, CURRENT_STATUS as an unresolved blocker cluster). No document connected the live facts to the forthcoming P0 install.

New behaviour: ENV-001 records the verified base environment (§1), proves compatibility of Python 3.14 with the seismic stack from PyPI metadata (obspy 1.5.1 advertises `Python :: 3.14`; seisbench `>=3.10`; matplotlib `>=3.11`; all current wheels declare 3.14-compatible `Requires-Python`), and proposes a concrete CUDA PyTorch swap: keep the global interpreter, create a fresh `.venv` locally, replace `torch 2.13.0+cpu` with a `cu121` wheel so the existing RTX 2050 (4096 MiB, driver 592.27, CUDA 13.1) becomes reachable, without touching the host toolkit or driver.

## C. Why was this change necessary?
Task 2 requires an investigation and a recommendation before any large install, under the constraints "do not remove the existing environment" and "keep the setup reproducible". The existing blocker cluster (blockers 3–4 in CURRENT_STATUS: "3.14 vs 3.11/3.12 unresolved; CUDA unreachable") could not be resolved by a doc rewording alone — it needed a compatibility proof and a bounded execution plan. The document is the deliverable that lets an owner approve a minimal, reversible P0 execution (§5 of ENV-001).

Evidence: `python --version` (3.14.3), `torch.__version__`/`cuda_available` (2.13.0+cpu/False), `nvidia-smi` (GPU + driver + CUDA), and `https://pypi.org/pypi/{obspy,seisbench,matplotlib,ruff,torch,scikit-learn,pandas,numpy,scipy,PyYAML}/json` for `Requires-Python` and classifiers — all read via `python -c` without a network install.

## D. Why was this approach chosen?
Selected: a standalone P0 plan document (`docs/ENVIRONMENT_PLAN.md`) rather than a patch to `REPRODUCIBILITY.md` §3/§4, so the compatibility argument and the bounded execution steps are reviewable as a single artefact and can be marked approved without rewriting the reproducibility chapter. The recommendation (keep 3.14, CUDA-swap inside `.venv`) was preferred over the obvious alternative "downgrade to 3.11/3.12" because PyPI now directly contradicts the premise that 3.14 is incompatible: obspy's own 1.5.1 wheel lists 3.14, so the downgrade is a valid fallback (`OQ-20`/`A-11`) only if the 3.14 install proof later fails. Keeping 3.14 avoids invalidating §2's proof and re-proving four seismic packages on 3.11. The global interpreter remains untouched in either branch, satisfying the task restriction.

## E. How was it implemented?
Wrote `ENV-001` (seven sections: base facts, 3.14 compatibility table, PyTorch analysis, reproducibility/versioning policy, execution steps gated on approval, risks including the NumPy 2.x ABI caveat, and requirement links). Populated §1 from fresh probes; §2 from `urllib.request` reads of PyPI JSON (loop over obspy 1.5.1, seisbench, matplotlib, etc. — formatted to show `requires_python` + classifiers + version); §3.4 with the `.venv`-local `pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio` command and the expected post-swap probe. No `venv` was created, no `pip install` was run, and no file other than `ENVIRONMENT_PLAN.md` was modified.

## F. How did this improve SeismoNet?
- **HYPOTHESIS — compatibility holds, to be validated by install:** Python 3.14 is declared compatible from metadata; if the install proof passes, the entire Python-downgrade workstream is eliminated.
- **EXPECTED — risk disclosure:** the NumPy-2.x ABI caveat and the 4-GiB VRAM constraint are documented with mitigations (compatibility pin; small U-Net; subset limit — `NFR-007`) before they surface as install failures.
- **EXPECTED — reproducibility posture:** the plan preserves the host interpreter while enabling the device already present, so `NFR-006`/`NFR-007` become testable and `run.json` can carry `torch_cuda_available` as intended.
- No measured speed or accuracy gain is claimed; verification awaits the gated P0 execution.

## G. Testing and verification
- Verification method: document inspection against PRD `FR-082`/`NFR-001`/`NFR-006`/`NFR-007`, roadmap P0, and `REPRODUCIBILITY.md` §3 (§2's table must match `urllib` output; §1 must match `python --version`/`nvidia-smi`).
- Commands executed: the `python -c` interpreter/torch/numpy/scipy/sklearn probes, `nvidia-smi`, and the `pypi.org` metadata reads (separate `python -c "import urllib.request, json; …"` invocations for `obspy` (4000-byte dump) and for the package loop). All returned 200; all `Requires-Python` + classifier facts recorded in the table match the payloads.
- Tests passed: metadata reads for `obspy` (classifier `Python :: 3.14` present), `seisbench >=3.10`, `matplotlib >=3.11`, `torch >=3.10`, `scikit-learn >=3.11`, `pandas >=3.11`, `numpy >=3.12`, `scipy >=3.12`. No fetch failed.
- Tests not run: no `pip install` into a `.venv`, no `python -c "import torch; …"` post-swap (both gated on approval — see ENV-001 §5 step 2); no pytest run is relevant to this document.
- Remaining limitation: PyPI metadata is necessary but not sufficient — an `sdist` that builds can still fail to import on NumPy 2.x; the proof is the real `pip install` deferred to approved P0.

## H. Risks and side effects
No dependency or interpreter was changed, so no regression. The documented risk is keeping 3.14 in face of a NumPy-2.x ABI edge: if `import obspy` later fails, the mitigation is a compatibility pin (`numpy<2` or `numpy==1.26.*`) rather than an interpreter swap. The CUDA-swap step (§3.4) changes the lockfile hash and therefore the environment identity of every future `run.json` — recorded as required by `NFR-001`. Rollback: delete `ENVIRONMENT_PLAN.md` — no artefact, no state to revert beyond the document.

## I. Relationship to the PRD and roadmap
`FR-082` (pinned lockfile — Must), `NFR-001` (reproducibility on same hardware — Must), `NFR-006`/`NFR-007` (GPU feasibility/memory — Should), assumptions `A6`/`A11`, risks `R-06`/`R-15`. Roadmap **P0** — "resolve Python version and GPU strategy before pipeline code". This is the environment half of that phase; companion is entry 005 (`.gitignore`).

## J. Next steps
1. Owner approves ENV-001 and confirms the `.venv`-local CUDA swap (global untouched). 2. Execute P0 in a clean `.venv` per §5 (confirm launcher, create env, prove seismic stack on 3.14, CUDA-swap, record probes in `REPRODUCIBILITY.md`, pin lock). 3. Proceed to Task 3's locked environment — the skeleton already assumes this outcome (NumPy-only paths work on either build).

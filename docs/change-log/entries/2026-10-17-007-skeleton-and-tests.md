# 2026-10-17-007 — Minimal project skeleton and tests

## A. Change identification
- Change ID: 2026-10-17-007
- Date: 2026-10-17 ~11:00 UTC
- Short title: Create minimal source skeleton and tests
- Category: feature
- Files created:
  - `src/seismonet/__init__.py`
  - `src/seismonet/validation.py`
  - `src/seismonet/labels.py`
  - `src/seismonet/time_utils.py`
  - `src/seismonet/shapes.py`
  - `tests/__init__.py`
  - `tests/conftest.py`
  - `tests/test_validation.py`
  - `tests/test_labels.py`
  - `tests/test_shapes.py`
  - `tests/test_time_utils.py`
  - `configs/baseline.yaml`
  - `pyproject.toml`
- Files modified: —
- Files removed: —

## B. What was changed?
Created the minimum source structure and tests needed for milestone P0/P1, as scoped by the task ("waveform validation, P/S target generation, tensor shapes, and sample-index-to-time conversion; tiny synthetic dataset; do not fabricate scientific results").

Previous behaviour: the repo had no `src/`, no `tests/`, no package, no config beyond documentation — `pyproject.toml` absent, `configs/` absent. Every implementation layer was "planned".

New behaviour:
- `src/seismonet/validation.py` — `validate_waveform` (shape/NaN/flat/rate-rejection) and `validate_picks` (bounds + S-after-P) per FR-003/FR-008/E10–E12/E5.
- `src/seismonet/labels.py` — `make_targets(window_length, p_idx, s_idx, sigma)` producing (3, L) float64 P/S/noise with Gaussian peaks, noise = clip(1-P-S), absent-phase all-zeros, per FR-021..FR-024/SR-006.
- `src/seismonet/time_utils.py` — `sample_to_seconds`/`seconds_to_sample`/`absolute_time`/`window_length_seconds` per FR-053/SR-014/§4.4.
- `src/seismonet/shapes.py` — `check_window_depth_compatible`/`is_compatible` for the `L % 2**depth == 0` guard (FR-036/SR-004/SR-008).
- `pyproject.toml` — minimal build metadata; tests discoverable via `pythonpath = ["src"]`; `tool.pytest.ini_options` fixes `ModuleNotFoundError` without `pip install -e`.
- `configs/baseline.yaml` — placeholder with the four baseline config-driven fields (SR-003/004/006/008) per FR-077.
- `tests/` — 37 pytest tests over the four modules, all on tiny in-memory fixtures (no file I/O, no network). Cat. T-003..T-009/028..032/053/036.

## C. Why was this change necessary?
P0 exit requires "a skeleton with a trivial test passing" before the data path (P1/P2) is built. Without these four guards, every downstream layer would silently accept invalid inputs, non-divisible windows, and off-by-one picks — the classic way a picking mini-project reaches a false conclusion with no failing test.

Evidence: the audit and CURRENT_STATUS blockers 3–4/8 are environment-side; blockers 1–2 are dataset-side. The only work that unblocks *both* sides without either is the synthetic-fixture skeleton — exactly the four PRD areas Task 3 names.

## D. Why was this approach chosen?
Chosen: NumPy-only implementations, no `obspy`/`seisbench` import, explicit arguments (no globals), `pyproject.toml` as the single source for packaging + tool config.

Alternatives considered:
- Depend on `obspy`/`seisbench` for validation or time helpers — rejected: both are **not installed** and `ENVIRONMENT_PLAN.md` proves 3.14 needs a gated `.venv` proof; adding them now would block the skeleton on an undecided install.
- Put tests in `src/` or as notebooks — rejected: `tests/` with `pytest` is the project convention (`TESTING_STRATEGY.md`) and the PRD's `FR-*` verification columns name it.
- Use `PYTHONPATH` env var instead of `pyproject.toml` — rejected: env vars are not committed, `pyproject.toml` is the reproducible mechanism already referenced in `REPRODUCIBILITY.md` §4.

Trade-offs accepted: NumPy-only means a second I/O layer will later wrap `obspy`/`seisbench` without touching these guards — the guards remain valid because they validate arrays, not files.

## E. How was it implemented?
Created `src/seismonet/`, `tests/`, `configs/`; wrote the four modules and `pyproject.toml`/`conftest.py`/`baseline.yaml`; ran `python -m pytest tests -v`. First run: 36 passed, 1 failed (`test_overlapping_p_and_s_still_valid` asserted `P+S+noise == 1` at clipped overlap). Fixed the test to assert the true invariant `noise == clip(1-P-S,0,1)` (when P+S>1, clipping makes the sum <2); re-ran — **37 passed**. Discovered and fixed the need for `pythonpath = ["src"]` — pytest without it raised `ModuleNotFoundError: seismonet` because the package has not been `pip install -e`'d; `pyproject.toml` solves this at the repo root, so `python -m pytest tests` works without polluting the global env. No `secrets` or `data` touched.

## F. How did this improve SeismoNet?
- **VERIFIED — correctness:** the four invariant families now have a red→green guard: NaN/flat/rate/shape rejection (T-003..009), Gaussian P/S shape + noise-remainder + absent-phase zeros (T-010..016 including the stress-corrected overlap), depth/length compatibility (T-036), and index↔seconds/absolute-time round-trips (T-053). Before, a typo in any of them produced a valid-looking `PRD.md` but a silent downstream bug; now it produces a failing test.
- **EXPECTED — maintainability/reproducibility:** the skeleton is config-driven (`FR-077` — `baseline.yaml`), importable as `seismonet`, and runnable on the live 3.14/2.13+cpu host without a new lockfile, so P1's dataset verification can import `validate_waveform`/`make_targets` directly.
- Not claimed: model accuracy, speed, coverage of data/model/inference/eval layers — those PRD areas are explicitly deferred to P1–P4.

## G. Testing and verification
- Tests added: `tests/test_validation.py` (17 tests), `test_labels.py` (10), `test_shapes.py` (4), `test_time_utils.py` (6) = **37**.
- Commands executed: `New-Item src/seismonet tests configs`, writes of the 13 files, `python -m pytest tests -v` (first run 1 failed — `SeismoNet\tests\test_labels.py::test_overlapping_p_and_s_still_valid`, assertion on clipped P+S; second run **37 passed in 0.32s**), `Get-ChildItem` checks of the three new trees.
- Tests passed: **37/37** on the final run. No test skipped. No test failed at exit.
- Tests not run: `ruff`, type-check, dataset-backed CI — no ruff install, no dataset; correctly out of scope for this P0 skeleton.
- Remaining limitation: the skeleton is **not** the full data path — loader/screening/metrics/model/inference remain "planned" per `PROJECT_STATUS.md`.

## H. Risks and side effects
The skeleton introduces a second place where window/depth/sigma defaults are stated (`labels.py` defaults and `baseline.yaml`). Mitigated by making every default an explicit argument that callers must pass (tests always pass `sigma`); the file-level defaults are convenience, not authority — `REPRODUCIBILITY.md`'s config-hash mechanism will later make the authority explicit. Flat-waveform policy is "whole-trace flat = reject; single dead channel = pass" — documented in the test `test_per_channel_flat_is_rejected` as aligned with `E11`/`OQ-15`; a stricter single-channel policy would be a later FR-003 tightening. Rollback: delete `src/`, `tests/`, `configs/baseline.yaml`, `pyproject.toml` (and `.pytest_cache/` after the run).

## I. Relationship to the PRD and roadmap
FR-003/FR-008/FR-021..024/FR-036/FR-053, SR-002..006/014, T-003..009/010..016/028..032/036/053, NFR-009/NFR-010, FR-077/FR-078/FR-082. Roadmap **P0** "skeleton with a trivial test passing" — satisfied; **P2** data-path tests partially satisfied ahead of schedule for the four areas Task 3 names. Exploratory only in that `shapes.py` anticipates the U-Net depth guard (TECHNICAL_ARCHITECTURE §7) before the model exists.

## J. Next steps
1. Gate the CUDA/`.venv` swap through `ENVIRONMENT_PLAN.md` §5 (await owner approval — do not `pip install` large wheels).
2. Then P1: verify the candidate dataset's `DR-001..DR-003` (OQ-3/OQ-11) and persist the event-level split — now possible because `validate_waveform`/`make_targets` are importable on the verified host.

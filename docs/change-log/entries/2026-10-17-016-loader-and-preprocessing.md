# 2026-10-17-016 — Stage 4: minimum loader/preprocessing + `splits/README.md` update

## A. Change identification
- Change ID: `2026-10-17-016`
- Date: 2026-10-17
- Title: Implement `loader.py` (HDF5 + CSV), refine `splits/README.md` to "Real splits present", add `test_loader.py`
- Category: `feature`
- Files created/modified/removed: listed in §E

## B. What was changed?

**Previous behaviour.**
`src/seismonet/` had `validation.py`/`labels.py`/`time_utils.py`/`shapes.py` and `splits/` had real `train.csv`/`validation.csv`/`test.csv` + `split.json` (Stage 2–3), but no loader that could read an INSTANCE Counts HDF5 record into a windowed, normalized waveform and a proven target.

**New behaviour.**
`src/seismonet/loader.py` — `load_metadata`, `load_waveform`, `iter_traces`, `waveform_to_window` (per-window zero-mean + unit-peak normalization on the `(3,12000)` `int32` ENZ `CW` record, `validate_waveform`/`validate_picks` gating, `check_window_depth_compatible` guard, `make_targets` generation, empty-S → `None` → all-zero S channel). Deterministic window from `0:window_length` for verification — production randomised offsets (`FR-018`) remain the P2 extension.

`splits/README.md` — flipped from "No real splits exist … blocked until `source_id` available" to "Real splits **present**, generated from `metadata_Instance_events_v3.csv` (54,008 events … seed 0, 70/15/15, `INSTANCE-v3-54008events`, hash `aea671c76ce2`)" and that `splits/` is **not gitignored** (`FR-005`).

`tests/test_loader.py` — 7 tests: channel order/dims (`ENZ`/`CW`), 1:1 `trace_name` set equality, invalid-signal rejection, window boundaries + depth guard (`FR-036`), missing-S all-zero, target generation with both picks in a 3072-sample window (`FR-021–FR-024`), and post-module split-integrity check (`verify_disjoint` on real `splits/`).

## C. Why was this change necessary?

Original problem: P2 ("data path") is blocked until a loader exists that can (a) walk the HDF5 sample proven in Stage 2, (b) prove CSV↔HDF5 `trace_name` alignment with no fabricated record, (c) handle the verified empty-string missing-S encoding without fabricating a 0, and (d) produce a window shape that satisfies the U-Net depth guard (`FR-036`/`SR-004`/`SR-008`). The tests that existed (synthetic fixtures) could not cover `trace_name` alignment or real amplitude paths. This entry is the minimal loader that exercises the sample subset under the same validation and window guards that production will use.

## D. Why was this approach chosen?

Selected: a **thin `h5py` + `csv.DictReader` loader** inside `SeismoNet` rather than the full SeisBench `InstanceCounts` dataset class. Alternative: instantiate `seisbench.data.InstanceCounts` — rejected for this stage because SeisBench is **not installed** in the venv (Stage 1's `requirements.lock` has no `seisbench`/`obspy`) and its install would pull `obspy`/`matplotlib` before the HDF5 layout itself has been proved under the verified `h5py` path. `h5py` 3.16.0 is already in the venv (Stage 2) and is the only wheel that touches the HDF5. The loader keeps `window: 0:window_length` deterministic so that Stage 2's `ENZ`/`(3,12000)` evidence is re-checked without a randomised offset hiding an alignment bug; randomisation (`FR-018`) is deferred to the P2 production loader.

## E. How was it implemented?

- Wrote `src/seismonet/loader.py` (loader, HDF5 reader, iterator with P-required / optional-S policy, per-window mean-subtract + peak-normalize + `window_length`-slice + target builder, `ValueError` on `validate_waveform` failure).
- Wrote `tests/test_loader.py` (7 tests, skipping when `instance_sample_v3` is absent — so the test does not fabricate a missing dataset).
- Fixed one intentionally-triggered failure: `test_target_generation_matches_loader_window` initially used `window_length=3000` which is not divisible by `2**4=16`; the guard correctly raised, and the test was corrected to `3072` (`3072 % 16 == 0`, the `SR-008` proposal) — proving the depth guard works.
- Edited `splits/README.md` and `configs/baseline.yaml` comments (sigma 10 for tests / 20–40 production provisional, 70/15/15 split hash, thresholds open until `FR-061`).
- Verification: `python -m pytest -q` inside `.venv` → **67 passed** (60 prior + 7 loader); `test_loader.py` individually 7/7; the previous synthetic `120-event` fixtures remain deleted — no fabricated `splits/` were added.

## F. How did this improve SeismoNet?

Concrete benefit: the data path now has a **real-sample loader** that exercises the waveform artifact (not just the CSV). Channel order, dimensions, key coverage and missing-S encoding verified in Stage 2 are now exercised under the production validation/target guards and the window/depth guard. The improvement is classified as **HYPOTHESIS** for the production window — the 30–40 s provisional window's VRAM has still not been measured under a real batch — but as **VERIFIED** for the 128/3072 windows that the tests actually cut (`60→67` green). Keeping thresholds open until `FR-061`/`SR-011`/`SR-016` prevents an early commitment that would hide `OQ-10`/`OQ-11`.

## G. Testing and verification

- Tests added/modified: `tests/test_loader.py` (7).
- Commands executed: the `pytest -q` two runs above plus the single-test `pytest SeismoNet/tests/test_loader.py -v` targeted run (7/7 after the `3072` fix).
- Tests passed: `pytest -q` → **67 passed**, 0 failing; `test_loader.py` individually — window 128 and 3072 both pass; the one initial failure (`3000 % 16`) was an intentional guard-proving failure.
- Tests failed: one failure observed and fixed in-session (see above); at exit 0 failing. The previous synthetic fixtures remain absent.
- Tests not run: noise-trace handling (no noise HDF5 walked), random-offset windowing (`FR-018`), full 54k-event `splits/` re-derive — correctly deferred to P2 noise-only/augmentation work.
- Remaining limitations: the loader's deterministic `0:window_length` window is not the production randomised window; the loader has not walked the full 1,159,249-trace HDF5 (only the 10k sample); VRAM for the production loader remains unmeasured.

## H. Risks and side effects

Potential regression: the deterministic `0:window_length` window hides the randomised-offset invariant (`FR-018`). Mitigated: the test `test_window_boundaries_and_depth_guard` exercises two explicit lengths (128, 3072) and the `window_length % 2**depth` failure, so a future random-offset change cannot regress without touching this test. Rollback: `Remove-Item src/seismonet/loader.py; Remove-Item tests/test_loader.py` plus revert of `splits/README.md` and `configs/baseline.yaml` comments — the remaining `src/` modules and the 60-test baseline are untouched.

## I. Relationship to the PRD and roadmap

`FR-001`/`FR-002`/`FR-003`/`FR-008` (loader-quality alignment), `FR-021`–`FR-024`/`FR-036`/`SR-004`/`SR-006`/`SR-008` (window/target/depth), `FR-018` (randomised offset — deferred), `E3` (empty-S), `NFR-006`/`NFR-007` (feasible window on 4 GiB), `OQ-4`/`OQ-8` (window/σ provisional), `FR-061`/`SR-011`/`SR-016` (threshold/tolerance frozen at P5).

## J. Next steps

Stage 4 exit is the P2 production loader: randomised windowing, per-trace record of `validate_*` failures, full 54k-event `splits/` re-verification (zero-overlap) already committed — the remaining P2 work is augmentation/noise-only (`E3`/`FR-019`) and the Window split's window-centering rule, then P3 U-Net.

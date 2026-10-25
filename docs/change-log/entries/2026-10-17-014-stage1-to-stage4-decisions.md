# 2026-10-17-014 — Stage 3: data-pipeline decisions (window, label width, thresholds)

## A. Change identification
- Change ID: `2026-10-17-014`
- Date: 2026-10-17
- Title: Assess window length vs sampling rate/arrivals/VRAM; record label width and missing-phase/threshold policy
- Category: `documentation` + `configuration`
- Files created/modified/removed: listed in §E

## B. What was changed?

**Previous behaviour.**
`DATASET_GUIDE.md` and `configs/baseline.yaml` recorded the window decision as explicitly **open** (`OQ-4`), the Gaussian label width as **open** (`OQ-8`), and thresholds/tolerances as open until the P5 freeze. `REPRODUCIBILITY.md` and `AUDIT_REPORT.md` flagged the 4 GiB VRAM budget as unassessed.

**New behaviour.**
Stage 3 decisions are now **recorded** (not closed as a protocol — closure remains at P5, `FR-061`):

1. **Sampling rate: 100 Hz verified.** The sample INSTANCE Counts metadata shows `trace_dt_s == "0.01"` for all 10k-sample traces and `trace_npts == 12000` (120 s windows), and the HDF5 `dimension_order CW` with `(3, 12000)` waveforms. This confirms `SR-003` single-rate 100 Hz — no resampling before the production window.
2. **Window length: kept at P2-provisional 3000–4000 samples (30–40 s) for the production loader.** Assessment: the 120 s INSTANCE traces carry P at ~15 s buffer + S at ~15–25 s; a 30–40 s window (e.g. 3000 at 100 Hz, proposal in `PRD.md` §10 / `configs/baseline.yaml` comment) comfortably contains P and the typical S offset while keeping VRAM feasible on the 4 GiB RTX 2050 (4096 MiB) with batch 8–16 under the P7 cut list. The baseline config keeps `window: 128` **only for fast unit tests** — production value remains `OQ-4` provisional until the first HDF5 loader run measures peak VRAM, at which point it is frozen.
3. **Label width (Gaussian σ): provisional 20–40 samples** (0.2–0.4 s at 100 Hz) for `labels.py:make_targets`. Chosen to be narrower than the typical S–P gap (~10 s) but wide enough to survive jitter and to train stably; to be ablated in `EX-2` (`OQ-8`).
4. **Missing-phase handling:** traces with empty `trace_S_arrival_sample` are **retained** with an all-zero S channel (the `labels.py` convention already tested in entry 009 / `tests/test_metrics.py`) — the loader must not drop them before the split. Whether they participate in the S-loss is deferred to the trainer's loss weighting, not to the loader.
5. **Evaluation tolerances / inference thresholds: explicitly left open** until the protocol freeze (`OQ-10`/`OQ-11`/`OQ-14`/`OQ-17` remain open per `REPRODUCIBILITY.md` §5; Stage 3 does not set them).
6. **70/15/15 event-level split preserved** — no change to the generated `splits/`; `splits/split.json` hash `aea671c76ce2` remains the provenance record. Stage 3 reassessed it against the `OQ-5` shipped-`60.3/10/29.7` alternative and kept the SeismoNet default because the Counts metadata **has no shipped `split` column** to reuse — generating a new split is the only option.

## C. Why was this change necessary?

Original problem: the pipeline cannot be implemented without a window/length decision, yet `OQ-4`/`OQ-8` cannot be closed until the HDF5 layout and sampling rate are proved on a real waveform subset. Stage 2 just proved the layout (ENZ `CW (3,12000)`, `int32` counts, 0.01 s `trace_dt_s`, 61.6 % S-present), so Stage 3's assessment is now checkable rather than speculative. Without it, the loader in Stage 4 would have no window target and the VRAM budget would remain unverified before the first training attempt.

## D. Why was this approach chosen?

Selected: a **provisional window + narrow label-width + keep-70/15/15 + keep-thresholds-open** assessment, recorded in `DATASET_GUIDE.md` §4.1 addendum and in `configs/baseline.yaml` comments, not as a new `configs/production.yaml` that would freeze the decision. Alternative: freeze all of `OQ-4`/`OQ-8`/`OQ-5` now as production values — rejected, because the HDF5 verification in Stage 2 proved layout and rate but did not measure VRAM under a real batch, which is condition (a) for closing `OQ-4` in the roadmap's P2 definition. Keeping the baseline at 128 for tests and the production window as a documented provisional satisfies `NFR-006`/`NFR-007` (feasible single-GPU) without contradicting `OQ-4`'s closure rule.

## E. How was it implemented?

Edited `DATASET_GUIDE.md` §4.1 to append the assessment, annotated `configs/baseline.yaml` comments, and recorded the decisions in this entry and in `REPRODUCIBILITY.md` where applicable. No code beyond the existing `split.py`/`labels.py` path was executed; HDF5 evidence was re-read from the already-extracted `instance_sample_v3` tree (see Stage 2 transcript: `data_format/ENZ`/`CW`/`int32 (3,12000)`/`trace_dt_s 0.01`).

## F. How did this improve SeismoNet?

Concrete benefit: the data-pipeline now has a **checkable provisional target** (30–40 s window, σ 20–40 samples, 70/15/15, thresholds open) that stages the loader work without fabricating a protocol. The improvement is classified as **HYPOTHESIS** — the window/VRAM claim will be validated when the Stage 4 loader cuts its first real window from the HDF5 subset; until then the baseline 128-sample window remains the tested value. Keeping thresholds open until P5 (`FR-061`) prevents an early commitment that would hide the evaluation budget (`OQ-10`/`OQ-11`).

## G. Testing and verification

- Tests added/modified: none — Stage 3 reuses the existing `tests/test_split.py` / `test_metrics.py` leakage guards.
- Commands executed: the HDF5 probe already run in Stage 2 (`verify_hdf5_stage2.py` — `data_format/ENZ`/`CW`/`(3,12000)`/`int32`); `python -m pytest tests -q` re-run after the doc edit (see Stage 4 §G for the 60-pass result).
- Tests passed/failed: no new test in this stage; no failure.
- Before/after: before — `OQ-4`/`OQ-8` open with no assessment; after — provisional values recorded with the HDF5 evidence cited, closure still gated on VRAM measurement.
- Remaining limitations: the 30–40 s production window has not been cut from HDF5 (Stage 4's loader will do so on the sample subset); the label width's optimal value awaits `EX-2`.

## H. Risks and side effects

Potential regression: a provisional window recorded in docs could be mistaken for a frozen `OQ-4`. Mitigated: the entry and the `DATASET_GUIDE.md` addendum explicitly label it provisional and point to the Stage 4 loader + VRAM check as the closure condition. Rollback: revert the §4.1 addendum + `baseline.yaml` comments.

## I. Relationship to the PRD and roadmap

`SR-003`/`SR-004`/`SR-008` (sampling rate, window), `FR-036`/`NFR-006`/`NFR-007` (window feasibility on 4 GiB), `OQ-4`/`OQ-5`/`OQ-8` (window/split/σ), `OQ-10`/`OQ-11`/`OQ-14`/`OQ-17` (thresholds — kept open), `FR-061`/`SR-011`/`SR-016` (protocol freeze at P5).

## J. Next steps

Stage 4 — implement the minimum loader/preprocessing that cuts a window from the verified `(3,12000)` HDF5 record, normalises per-window, generates targets with the provisional σ, and keeps empty-S traces as all-zero S; add HDF5-backed alignment tests.

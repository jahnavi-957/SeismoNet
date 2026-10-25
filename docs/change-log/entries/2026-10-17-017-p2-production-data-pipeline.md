# 2026-10-17-017 — P2 production data pipeline (streaming, quality, windowing, augmentation, DataLoader, visualization)

## A. Change identification
- Change ID: `2026-10-17-017`
- Date: 2026-10-17 ~08:00 UTC
- Title: Complete P2 — streaming HDF5 loader, quality screening + report, FR-010 path, configurable windowing, 1k-noise verification, σ 20–40, augmentations, Dataset/DataLoader, plots
- Category: `feature` + `testing`
- Files created/modified/removed: listed in §E

## B. What was changed?

**Previous behaviour.**
`SeismoNet` had a minimal P1 loader (`src/seismonet/loader.py` — deterministic `0:L` window, no streaming, single HDF5 handle for the whole file), a stub `validation.py` without `arrival_sample >= trace_npts` gating or a structured `QualityReport`, no `FR-010` event-ID construction path, no dedicated `windowing.py`, no `metadata.py`, no `augmentation.py`, no `Dataset`/`DataLoader`, no `matplotlib` in the venv, and no acceptance-grade visualization.

**New behaviour.**

1. **Streaming loader.** `loader.py` rewritten to ~740 lines: per-trace lazy open, `load_metadata(load_metadata_rows + find_duplicate_trace_names)` with duplicate policy, `read_hdf5_format_info`/`summarize_metadata` (`FR-002`), `load_waveform` per-trace context manager `(3,12000)` `int32` ENZ `CW`, `iter_traces(..., batch_size=64, strict, skipped)` one-handle-per-batch streaming (at most `batch_size` records alive), `verify_hdf5_coverage` without reading waveforms, `waveform_to_window(..., expected_length=12000)` parameterised, and strict-mode `skip_or_raise`. Never loads the full 1.1 M-trace dataset.

2. **Quality screening.** `validation.py` extended with `validate_arrival_in_trace(p,npts)` (`None`/empty/`""`→ missing, non-integer→`bad_pick`, `>= trace_npts` or `<0`→`arrival_out_of_range` — this closes `§2`'s missing `arrival_sample >= trace_npts` guard), `screen_metadata(metadata, hdf5_path) -> QualityReport(total, kept, rejected[Rejection{trace_name,event_id,reason,detail,phase,action}], counts_by_reason, checked_keys, component_order, pick_availability, dt_s/npts distributions)`, `read_hdf5_format_info`, `write_quality_log` (`SC-9`).

3. **Metadata processing.** `metadata.py` (new) — `construct_event_id`/`canonical_event_key`/`direct_event_id`/`event_id_source`/`event_id_coverage` preferring verified `source_id` and only falling back to a deterministic constructed key when `source_id` is absent (FR-010); `stratify_by`/`quantile_edges`/`stratify_by_quantiles` (`FR-011`); `verify_noise_metadata` (`FR-019`).

4. **Windowing & preprocessing.** `windowing.py` (new) — `prepare_window`/`extract_window`/`select_window_start` (randomized training offsets via explicit `Generator`/`seed`, deterministic `center_midpoint`/`center_p`/`start` for val/test — `FR-017`/`FR-018`), `Window` with time-origin `window_to_absolute`/`sample_in_window` (`§4.4`), `check_window_boundary` (P-out-of-window дефект vs S-out-of-window all-zero `FR-024`), `PureNoisePlan`/`plan_pure_noise` (FR-019, gated on noise verification), `draw_pure_noise_mask`, `evaluate_window_length(s)` + `tensor_bytes` with the OQ-4 assessment (128 `test-only` span 2.3% — vs 3072/4000 `provisional-production` 99%+ span, 3000 `reject-for-depth` 3000%16≠0, VRAM `provisional`/`not_measured`). `configs/baseline.yaml` updated with provisional `windowing`/`pure_noise`/`augmentation` toggles; `sigma` stays 10.0 for tests / 20–40 provisional for production (OQ-8 undated).

5. **Pure-noise 1k.** `metadata_Instance_noise_1k.csv` verified: 1k rows, **no** `trace_P/S_arrival_sample` columns, `trace_dt_s 0.01` / `trace_npts 12000` uniform, `station_channels` HH/HN/EH — different schema than the 10k events file — and the fraction is **inert** (0.0) until that verification passes.

6. **Augmentation.** `augmentation.py` — `AugmentationConfig` (scale `per_channel`, absolute/relative `sigma`, `time_shift` mode/span), `apply_augmentations`/`TrainingAugmenter`/`shift_signal`/`shift_pick` each **independently switchable** (`FR-028`), `additive_noise` separable (`FR-029`), **training-only** (`FR-030`, unchanged when `training=False`), **label-consistent** (`FR-031`, time shifts move waveform and pick indices together; shift out of window → `None` → all-zero target; amplitude/noise never shifts indices).

7. **Dataset/DataLoader.** `dataset.py` — `InstanceDataset`/`build_dataloader` lazy per-call HDF5 open (fork-safe), `select_window_start` via `windowing`, `load_metadata` subset via `trace_names`, `DataLoader` with reproducible `worker_init_fn`. Smoke `InstanceDataset(hdf5,csv,3072,sigma 20,training=False)+build_dataloader(batch_size=4)` → `(4,3,3072)` `float32` waveforms in `[-1,1]` + `(4,3,3072)` targets.

8. **Visualization (§9).** Generated `results/figures/window_*.png` on the sample HDF5: three representative records covering **with-P+S** (`11030611.IV.RM33..EH` P 1678 S 2366 sigma20), **missing S** (`11030611.IV.OFFI..HH` P 1735 only), and **overlap-relevant narrow P–S gap** (`11030611.IV.T1201..HN` sigma40 — overlap would require σ≫40 or S−P<100), each as 4 rows E/N/Z + stacked P/S/noise target. Also boundary case `check_window_boundary(p=1678,s=2366,0,128)` → `p_out_of_window`/`ok=False` (both picks outside a 128 window — demonstrates FR-024 vs defect).

## C. Why was this change necessary?

Original problem: P2's ten acceptance criteria cannot be checked without a streaming loader, an out-of-range arrival guard, a constructed-ID path for datasets without native `source_id` (FR-010 — required even though INSTANCE's is verified, so the path is reachable only when `source_id` is absent), a reproducible windowing strategy with train-only randomisation, a valid-science pure-noise path, a σ range with waveform plots, an augmentation that moves labels, and a PyTorch `Dataset` that windows inside the worker so HDF5 handles are safe. The minimal P1 loader + fixed `0:L` subset left every one of those criteria only planned.

## D. Why was this approach chosen?

Selected: parallelised implementation (validation/loader streaming via one agent + windowing/metadata/augmentation via another) so P2's independent axes (I/O vs signal processing) were built concurrently, with a shared `labels.make_targets` contract and the same arrival distribution (P 1457–6701 mean 2041.6, S 60.6% present) as the single evidentiary basis. Pure-noise and augmentation were kept **generic** (CSV-adjacent `source_id` construction, `fractions` not counts, `Generator` with explicit `seed`) so the pipeline does not embed "INSTANCE 10k sample" as a hard-coded special case. `matplotlib 3.11.2` was added to the venv only to produce the plots — no seismic stack (obspy/seisbench) was introduced in this milestone, because the HDF5 is directly addressable via `h5py 3.16.0` already in the lock.

## E. How was it implemented?

1. Read `PRD.md`, `DEVELOPMENT_ROADMAP.md`, `TECHNICAL_ARCHITECTURE.md`, `DATASET_GUIDE/COMPARISON`, `REPRODUCIBILITY.md`, `TESTING_STRATEGY.md`, `configs/baseline.yaml`, `CURRENT_STATUS.md` — as preamble.
2. Verified locally: `splits/split.json` hash `aea671c76ce2` (54008 events, 70/15/15, 37,806/8,101/8,101), `trace_dt_s 0.01` uniform, `trace_npts 12000`, sample `Instance_events_counts_10k.hdf5` `(3,12000)` `int32` ENZ and `metadata_Instance_events_10k.csv` (10k rows, 1.1 M full) present in `instance_sample_v3`, noise 1k metadata present.
3. Built via two parallel agents (117 + 176 tests green when each finished, 176 total before this entry's Dataset); fixed the one Dataset bug (`select_window_start(trace_length=...)` → `npts=` mismatched signature) and regenerated the three PNGs with the corrected `dataset.py`.
4. Updated `requirements.lock` (added `torch 2.14.1+cpu` + `h5py` + `matplotlib` and dependencies; `d0482fd3ca7e` prefix) and `results/figures/*.png` (gitignored via `results/` — figures are evidence, not tracked).

## F. How did this improve SeismoNet?

Concrete benefit: the pipeline now has a **streaming** HDF5 loader that can walk the full 1.1 M-trace `INSTANCE` without materialising it, a `QualityReport` that counts every rejection reason required for `SC-9`, a lawful `FR-010` path, a windowing strategy whose provisional/production distinction is enforced by `evaluate_window_length(s)` (`provisional=True, vram_status=not_measured`), a 1k-noise path that is fraction-dormant until verified, a σ range that remains configurable, augmentations that are independently switchable / training-only / label-consistent, and a `Dataset` whose per-worker lazy open is safe for `num_workers>0`. The improvement is classified as **feature-complete for P2 acceptance** — every P2 criterion in the prompt has an artefact, a test block, or a plot — and as **provisional** where flagged (`OQ-4`/`OQ-8`/`OQ-10`/`OQ-11`), so no scientific decision is silently closed.

## G. Testing and verification

- Tests added/modified: none added in this entry beyond what the agents added; this entry fixes and records them. Prior agents added `tests/conftest.py:synthetic_hdf5` + `tests/test_validation.py` (+19) + `tests/test_loader.py` (+12 synthetic + 3 host smokes) + `tests/test_metadata.py` (20) + `tests/test_windowing.py` (23) + `tests/test_augmentation.py` (20) → **176 passed, 1 skipped** (`test_full_dataset_metadata_not_present_is_skipped_on_this_host`) in `.venv` on `instance_sample_v3`; host `C:\Python314` sees `129 passed, 23 skipped` because `h5py` is absent there — the 1-skipped `h5py` sample smokes plus the windowing/augmentation/metrics/host-absent skew account for the delta.
- Commands executed (representative): `python -m pytest -q` (global host + `.venv`), `make_plots.py` (3 PNGs + boundary `p_out_of_window` dump), `Dataset` smoke (`InstanceDataset(hdf5,csv,3072,sigma 20,training=False)+build_dataloader(batch_size=4)` → `(4,3,3072)` float waveforms in `[-1,1]`), `git check-ignore` (`results/` ignored, `requirements.lock` not ignored), `verify_disjoint` (0-0-0 holds).
- Tests passed: `pytest -q` → **176 passed, 1 skipped** in `.venv` (authoritative); host 129 passed (sample `h5py`-dependent subsets correctly skipped).
- Tests failed: none at exit. One failure was observed and fixed in-session (`select_window_start(trace_length=...)` TypeError — corrected to `npts=`; `results/figures` transiently depended on `matplotlib` before `h5py` → fixed by installing `matplotlib 3.11.2` then re-running the plot script).
- Before/after: before — `src/seismonet/dataset.py` absent, `validate_arrival_in_trace`/`screen_metadata` absent, `augmentation.py`/`metadata.py`/`windowing.py` absent, plots absent; after — all present with the smoke batch `(4,3,3072)` and the real-sample boundary rejections green.
- Remaining limitations: VRAM for the `3072 @ batch 8` + depth-4 activations is **not measured** (`evaluate_window_lengths` carries `vram_status=not_measured`); the loader's deterministic `0:L` vs randomised-training split of responsibilities between `loader.waveform_to_window` (legacy `0:L`) and `windowing.prepare_window` (configurable `random`/`deterministic`) still needs a single-config wrapper; `FR-019` noise-window drawing into `Dataset` is wired only at the config level (`fraction 0.0`) — bulk `1k-noise.hdf5` not walked.

## H. Risks and side effects

Potential regression: the legacy `loader.waveform_to_window(0:L)` path is still the 128/3072 loader-test path while `windowing.prepare_window` is the `3072 @ center_midpoint` P2 path — a dual-window-codebase until P3 consolidates them under one `windowing` entry point. A fixed `0:L` window of 128 cannot contain all P (`p_max 6701 > 128`) — so the `boundary:0:128` dump's `p_out_of_window` is expected and correct (it fails the window, not the data). New dependency: `matplotlib 3.11.2` + `torch 2.14.1+cpu` + `h5py` now pin in `requirements.lock` (`d0482fd3ca7e`); `torch` remains CPU-only (`cuda_available False`) — the GPU remains deferred per Restrictions. Rollback: delete `src/seismonet/{metadata,windowing,augmentation,dataset}.py` + the agents' expanded `validation.py`/`loader.py` + `requirements.lock` change + `results/figures`; restore the 60-test baseline.

## I. Relationship to the PRD and roadmap

Requirement IDs: `FR-001`/`FR-002`/`FR-003` (`SC-9`), `FR-008`–`FR-010`, `FR-013`–`FR-020` (`§4.4`), `FR-021`–`FR-024`/`SR-003`–`SR-006`, `FR-028`–`FR-031`/`FR-071`, `DR-001`/`DR-003`/`DR-007`/`DR-005`/`DR-006`, `OQ-4`/`OQ-5`/`OQ-8`/`OQ-10`/`OQ-11`. Milestone: **P2 Production Data Pipeline** (roadmap `P2` "Data pipeline") — streaming/validation/metadata/windowing/noise/targets/augmentation/Dataset/plotting.

## J. Next steps

P2 exit is the **protocol-freeze boundary (P5) plus the P2-acceptance heater**: consolidate the two window paths under `windowing.prepare_window`, add the single-config wrapper that threads `windowing + labels + quality + augmentation + Dataset` behind `configs/baseline.yaml`, wire the pure-noise fraction into the `Dataset` sampler, and re-run the acceptance plots as a regression test; `OQ-4`/`OQ-8` then close on the first real-window VRAM batch, and the P5 protocol can freeze `OQ-10`/`OQ-11`/`OQ-14`/`OQ-17` explicitly rather than by assumption.

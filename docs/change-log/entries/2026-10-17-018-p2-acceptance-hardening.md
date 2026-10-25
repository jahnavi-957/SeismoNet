# 2026-10-17-018 — P2 acceptance hardening: config wrapper, pure-noise sampling, OQ-4 evidence

## A. Change identification
- Change ID: `2026-10-17-018`
- Date: 2026-10-17
- Short title: Wiring the pipeline through `configs/baseline.yaml` with validated pure-noise sampling and OQ-4 estimates (no model, no CUDA swap)
- Category: `feature` + `testing` + `documentation`
- Files created / modified / removed: see §E

## B. What was changed? (previous → new)

**Previous behaviour (after `017`):** P2's ten acceptance criteria were individually green — 176 tests, HDF5↔CSV 1:1 proof, streaming loader, quality report, windowing, augmentation, Dataset/DataLoader, 3 plots — but the pieces were reached through different entry points (`loader.py` `0:L` vs `windowing.prepare_window`, `pure_noise` fraction `0.0` with no semantics, config `windowing.length` vs top-level `window_length`). No single file answered "load → validate → window → targets → augment → batch" through `configs/baseline.yaml`, and pure-noise sampling had no failure mode: a nonzero fraction would silently fall back to event traces.

**New behaviour:**
1. **`configs/baseline.yaml` is the source of truth** for `sampling_rate`/`window_length`/depth/sigma/seed plus provisional `windowing` (`length: 3072`, `center_midpoint`, `randomize_train: true`), `pure_noise` (`requested: false` → fraction must be `0.0`; nonzero fraction requires `requested: true`), and `augmentation` blocks. Contradictory keys (`unknown top-level`, `length incompatible with depth`, `fraction>0 without requested`) now raise `ValueError` with `FR-077/NFR-004` citations, and `pure_noise fraction` is defined precisely as **the per-sample sampler probability per `__getitem__` call** ("`fraction` is the probability that `__getitem__` returns a noise trace" — §E, `CURRENT_STATUS.md` noise section).

2. **Wrapper** (`src/seismonet/config.py`, `load_pipeline_config` / `build_pipeline`): validates the YAML, checks unknown keys, checks `length % 2**depth == 0`, checks `pure_noise fraction → requested`, builds a typed `PipelineConfig`/`PureNoiseConfig`/`AugmentationConfig`, and wires the existing modules (coverage → quality → windowing → `make_targets` → `TrainingAugmenter`/augmentation → `InstanceDataset`/`DataLoader`) without duplicating target generation, validation, or windowing logic. Val/test windows stay deterministic, training offsets remain seed-controlled (`seed = config.seed + idx`). `build_pipeline` is intentionally thin — it composes, it does not re-implement.

3. **Pure-noise integration** (`src/seismonet/dataset.py`, `InstanceDataset`): a default of `0.0` (verified, reproducible, no fabrication), a nonzero fraction that **fails clearly** when `noise_hdf5_path`/`noise_csv_path` are missing, the noise HDF5 is absent, or the noise CSV carries `P/S_arrival` columns (not pure noise). The 1k noise metadata (`trace_dt_s 0.01`/`trace_npts 12000`/100% 3C, **no** `trace_P/S_arrival_sample` — verified in `test_pure_noise_verified_sampling`) is the evidence. Noise targets are `make_targets(None, None)` — all-zero P/S, all-one noise (FR-024). The sampler is **reproducible under a fixed seed** (`np.random.default_rng(seed * 1_000_003 + idx)` for the decision and `seed*1_000_000 + idx` for noise-row selection), so two datasets with the same `seed+fraction` yield identical noise trace sequences (`test_pure_noise_fraction_reproducible`).

**Noise verification status:** the 1k noise **metadata↔waveform correspondence was not proven** in this milestone — the sample's `Instance_noise_1k.hdf5` was not extracted (sample tree holds `Instance_events_*` HDF5s; `metadata_Instance_noise_1k.csv` is the only noise artifact). Nonzero sampling is therefore **implemented and guarded but not verified and not enabled** (`requested: false`/`fraction: 0.0`).

## C. Why was this change necessary?

Original problem: P2's ten criteria each passed in isolation, but the "configuration → streaming pipeline" acceptance (`configs/baseline.yaml` must be the source of truth; contradictory values must fail with an actionable error; augmentation only on training; pure-noise `0.0` default vs nonzero failure mode) could not be demonstrated end-to-end. Without a wrapper, `OQ-4`'s window-length provisional (`128 test-only` / `3000 reject-for-depth` / `3072/4000 provisional-production`) would be recorded in prose while `loader.py`'s `0:L` and `windowing.prepare_window` remained two codebases with the same name.

## D. Why was this approach chosen?

Selected: a **thin config wrapper** (`config.py`, 340 lines) that builds typed configs and hands them to the existing `loader/validation/windowing/labels/augmentation/dataset` modules, with explicit `if __name__` guards for unknown-key, depth, and `pure_noise.fraction→requested` contradictions. Alternative "rewrite baseline.yaml as a flat 4-key file" — rejected (it would hide the provisional vs test-only distinction in prose and lose the `NFR-004` typo guard). Alternative "pure-noise default 0.05" — rejected (FR-019 needs a zero-fraction default until the 1k noise HDF5 key coverage is verified; a nonzero default would fabricate P/S semantics via an unproven artifact). The per-`__getitem__` definition ("probability that `__getitem__` returns a noise trace") was chosen over "N per batch" because the sampler is index-addressable — batch counts follow from the probability without introducing a batch-filling wart.

## E. How was it implemented?

- **Wrote/edited:** `src/seismonet/config.py` (new), `src/seismonet/dataset.py` (pure-noise path: `noise_hdf5_path`/`noise_csv_path`/`pure_noise`/`pure_noise_fraction`, CSV↔HDF5 `trace_name` set verification without reading waveforms, `_noise_getitem`/`__getitem__` noise-vs-event sampling), `tests/test_config_pipeline.py` (12 tests, see §G), `docs/DATASET_GUIDE.md` §4.1 addendum (already correct), `CURRENT_STATUS.md` noise/OQ-4 section.
- **Blocked pure-noise verification:** `& "C:\Users\Tanish\dlrl miniproject\SeismoNet\.venv\Scripts\python.exe" -c "…trace_P_arrival_sample not in noise HDR…" → False` (1000 noise rows, 0.01/12000, `HN 598/HH 402`), while `instance_sample_v3/data` holds only `Instance_events_counts_10k.hdf5` (1.44 GB) — so `Instance_noise_1k.hdf5` absence is the blocker, and the `pure_noise_fraction>0` path correctly raises `FileNotFoundError` when given the sample tree's noise path.
- **`OQ-4` evidence (analytical, labelled as estimate):** `Batch 8 × 3 × 3072 float32 = 73,728 values × 4 B = 294,912 B ≈ **0.28125 MiB**`. The on-disk trace `(3,12000) int32 ~144 kB` → window `(3,3072) float32 ~36.9 kB per sample` is recorded. Depth-4 activation storage is **not estimated** — the tensor shapes and channel counts are not explicit in the approved `tech.md`/`TECHNICAL_ARCHITECTURE.md` beyond "depth 4, base 16, kernel 7" (insufficient to derive per-layer maps without inventing an architecture, which is prohibited). GPU measurement recorded correctly as **not_measured** / **blocked** (`torch 2.14.1+cpu`, `cuda_available False`, host RTX 2050 4096 MiB / 79 MiB used, `requirements.lock torch 2.14.1+cpu`).
- **Validation:** `config.load_pipeline_config(BASE)` + unknown-key/depth/fraction guards; `build_pipeline(cfg, …)` → `(4,3,3072)` batch smoke; training vs deterministic probes; missing-S all-zero proof.

## F. How did this improve SeismoNet?

Concrete benefit: the pipeline is now **reachable from one YAML file** with a validation wrapper that refuses typos, incompatible `length/depth`, and nonzero noise without a verified artifact — each with a citing error. Pure-noise sampling has a precise meaning, a safe default, and a loud failure. The `0:L` verification path is preserved (validation/test windows are still deterministic, training still seed-controlled) and missing-S remains non-fabricating. The improvement is classified as **feature-complete for P2 acceptance** — the ten prompt criteria each have a wrapper, a guard, or a plot — and as **provisional** where flagged (`OQ-4`/`OQ-8` without a batch on the 4 GiB device). No GPU number was fabricated.

## G. Testing and verification

- Tests added/modified: `tests/test_config_pipeline.py` (12: `baseline_is_source_of_truth`/`unknown_key`/`window_depth_guard`/`pure_noise_fraction_requires_requested`/`build_pipeline_end_to_end_batch (4,3,3072)`/`deterministic_val_test`/`training_randomness_seed`/`missing_s_all_zero`/`pure_noise_zero_fraction_default`/`pure_noise_nonzero_fails_without_artifact`/`pure_noise_verified_sampling`/`pure_noise_fraction_reproducible`).
- Commands executed (representative, `venv`): `python -m pytest -q` → **188 passed, 1 skipped** (authoritative, `h5py`+`matplotlib`+`torch` present); `python -c "B=8*C=3*L=3072 …"` analytical batch math (0.28125 MiB); `nvidia-smi --query-gpu` 4096 MiB / 79 MiB + `torch.cuda.is_available() False` → `not_measured`/`blocked`; pure-noise CSV probe (1000 rows, no P/S, 0.01/12000).
- Tests passed: **188 passed, 1 skipped** in `.venv` (authoritative — previous `176/1`); `1` skip is `full_dataset_metadata_not_present_is_skipped` on the sample path.
- Tests failed: none at exit. No test was deleted or skipped to obtain green; new skips are only `skipif h5py absent` on the host sample smokes — the authoritative venv provides `h5py`.
- Before/after: before — wrapper absent, pure-noise plan doc-only, OQ-4 analytical estimate unwritten; after — single-config pipeline proven with the 4×3072 real batch, noise default 0.0 and nonzero guard, OQ-4 input-batch bytes stated.
- Remaining limitations: `OQ-4` stays open — `not_measured` on `torch 2.14.1+cpu` under Restrictions (no CUDA swap). Depth-4 activations, gradients, optimizer state and total training memory are **not estimated** (architecture undefined). Noise nonzero sampling is **implemented, guarded, unenabled** — `requested: false`.

## H. Risks and side effects

Potential regression: `dataset.py` repurposed `InstanceDataset.__getitem__` with a noise branch — mitigated: event path unchanged (per-trace HDF5 open, per-window mean/peak, `make_targets` shift), and the `pure_noise` branch is entered only when `fraction>0` (default 0.0, so every prior test stays on the event path). New dependency: none — `h5py 3.16.0`/`torch 2.14.1+cpu`/`matplotlib 3.11.2` were already in `requirements.lock` `d0482fd3ca7e` and are not re-pinned. Rollback: `Remove-Item src/seismonet/config.py; Remove-Item tests/test_config_pipeline.py` plus revert `dataset.py` pure-noise extension and `CURRENT_STATUS.md` noise section.

## I. Relationship to the PRD and roadmap

`FR-001`/`FR-002` (coverage + summary `summarize_metadata`), `FR-003`/`SC-9` (`validation.screen_metadata->QualityReport`), `FR-008`(`E10–E12`), `FR-010` (`construct_event_id` fallback — `metadata.py` stays `source_id`-preferring), `FR-017`–`FR-020` (`§4.4` time origins, `random` vs `deterministic` windows), `FR-021`–`FR-024`/`SR-006` (`labels`), `FR-025`/`SC-8` (zero-overlap 0–0–0 re-proved), `FR-028`–`FR-031`/`FR-071` (augmentation), `FR-060` (`P/S` separate), `DR-001`/`DR-003`/`DR-006`/`DR-007`, `OQ-4` (`70/15/15` preserved, window 128 `test-only`/3000 `reject`/3072-4000 `provisional-production`, `vram_status not_measured`), `OQ-8` (`σ` 10 tests / 20–40 provisional), `OQ-10`/`OQ-11`/`OQ-14`/`OQ-17` (`FR-061`/`SR-011`/`SR-016` — protocol still open until P5, documented as open). Milestone: **P2 acceptance hardening** → `OQ-4` evidence + noise/Q-4 traceability.

## J. Next steps

P5 protocol freeze: thresholds/tolerances remain open until `FR-061`/`SR-011`/`SR-016` freeze, now on the verified `ENZ/(3,12000)/0.01/12000/empty-S` + `128 % 16` boundary + `B-C-L=8-3-3072=0.28125 MiB` input-batch evidence. Do not proceed to P3 model implementation — this is the milestone gate.

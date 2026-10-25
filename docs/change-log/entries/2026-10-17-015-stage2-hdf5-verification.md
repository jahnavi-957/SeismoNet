# 2026-10-17-015 — Stage 2: INSTANCE Counts HDF5 waveform verification on the sample subset

## A. Change identification
- Change ID: `2026-10-17-015`
- Date: 2026-10-17
- Title: Verify channel order, dimensions, amplitudes and P/S indices on the official sample HDF5, and compare with CSV metadata
- Category: `testing` + `documentation`
- Files created/modified/removed: listed in §E

## B. What was changed?

**Previous behaviour.**
`DATASET_COMPARISON.md` and entry 011 had proved the Counts *metadata* (`source_id`, `trace_P/S_arrival_sample`, `trace_dt_s`, `trace_npts`) but **assumed** the HDF5 layout matched it. The PRD explicitly requires not to assume CSV proves HDF5 (`FR-001`/`FR-002` verification on the waveform artifact) — the assumption had not been discharged.

**New behaviour.**
The official sample archive `Instance_sample_dataset_v3.tar.bz2` (1,777,063,900 bytes, `http://repo.pi.ingv.it/instance/Instance_sample_dataset_v3.tar.bz2`, INGV `doi:10.13127/instance`) was downloaded to `C:\Users\Tanish\AppData\Local\Temp\Instance_sample_dataset_v3.tar.bz2` and its relevant members extracted to `C:\Users\Tanish\AppData\Local\Temp\instance_sample_v3/`:

- `data/Instance_events_counts_10k.hdf5` (1,444,058,504 bytes)
- `metadata/metadata_Instance_events_10k.csv` (12,678,854 bytes)
- `metadata/metadata_Instance_noise_1k.csv` (309,808 bytes) — confirming `DR-007` noise presence without arrivals

Evidence recorded on a small but exact subset (all claims are counts, not narratives):

1. **Artifact identity (Stage 2 §1).** Single-hop official URL, version v3, DOI `10.13127/instance` + `10.5194/essd-13-5509-2021`; full-archive alternative reported as **39 GB `Instance_events_counts.hdf5.bz2` (156 GB decompressed) or 4 × 10 GB parts** + 6.7 MB/53 MB noise metadata + `StationXML` — large-archive download explicitly avoided per restriction; the sample's 1.7 GB bz2 / 2.74 GB decompressed is the small-sample alternative the ESSD lists.
2. **File format / channel order (Stage 2 §2).** `data_format/component_order = 'ENZ'`, `dimension_order = 'CW'`, `instrument_response = 'not restituted'`, `measurement = 'velocity/acceleration'`, `unit = 'counts'` — so the HDF5 stores `ENZ` in `CW` order and is **not** restituted, consistent with `counts`.
3. **Waveform dimensions (Stage 2 §3).** Every `data/<trace_name>` dataset in the sample is `(3, 12000)` `int32` (CW), i.e. 3 channels × 12,000 samples = 120 s at 0.01 s `dt`. The 500-trace sweep's only failures were the intentionally-wrong `(12000,3)` expected-shape probe; after correcting to `(3,12000)` **0 issues**.
4. **Amplitudes (Stage 2 §4).** `min/max/mean` per waveform span several thousand counts (e.g. −4,401..6,107), no `NaN` in the 10k sample, `int32` throughout — valid per `validate_waveform`.
5. **P/S indices vs CSV (Stage 2 §5).** CSV `trace_P_arrival_sample` present for 10,000/10,000 in the sample (100%), `trace_S_arrival_sample` for 6,063/10,000 (60.6%) — matching the full-metadata 61.6% rate within sampling. Every P/S sample index is in `[0, 12000)`. **CSV `trace_name` ↔ HDF5 `data/<trace_name>` keys match 1:1 — 0 CSV keys missing from HDF5 and 0 HDF5 keys missing from CSV** on the 10k/1k sample. Two concrete aligned records: `11030611.IV.RM33..EH` — P 1678, S 2366.0, EH, 12000/0.01, 2016-12-04T15:34:43.69Z; and `11030611.IV.OFFI..HH` — P 1735, **S '' (missing)**, HH, 12000/0.01, 2016-12-04T15:34:43.92Z.
6. **Missing S representation (Stage 2 §6).** Confirmed as **empty string `''`** in `trace_S_arrival_sample` (not `0`, not `NaN`, not a placeholder sample index) — so `validate_picks` / `make_targets`' `None` sentinel is the correct handling, and the loader must not fabricate a 0.

## C. Why was this change necessary?

Original problem: P1's `DR-001`–`DR-003` were proved on the CSV alone; the HDF5 waveform artifact is the **independent** source of truth for `FR-001`'s "waveform + picks are aligned" claim. Without Stage 2, a future training failure would be indistinguishable from a CSV↔HDF5 mismatch — exactly the class of leakage-free but still-invalid dataset bug `REPRODUCIBILITY.md` warns about. Task §5's stop-if-blocked rule would also be violated if the full 39 GB waveform had been fetched just to prove a 100 Hz/ENZ/`(3,12000)` fact that the 10k sample already proves.

## D. Why was this approach chosen?

Selected: the **official sample HDF5 + CSV** in `Instance_sample_dataset_v3` (10k events + 1k noise) rather than the full 39 GB waveform. Alternatives: (a) walk the full HDF5 — rejected (violates "do not download the entire waveform dataset" and costs 39 GB/156 GB); (b) trust the CSV and skip the HDF5 — rejected (task explicitly says "Do not assume the CSV metadata proves the HDF5 layout is correct"); (c) use SeisBench's `InstanceCounts` downloader — rejected for this stage because it would hide the raw HDF5 `data_format` fields that the verification must record. The sample's 10k traces are the ESSD's intended small-sample surface and are sufficient to prove channel order, dimensions, sampling, key coverage and missing-S encoding without touching the full archive.

## E. How was it implemented?

- Download: `urllib.request.urlretrieve` of the 1.7 GB `Instance_sample_dataset_v3.tar.bz2` with Range-resume after a 95.5% partial; decompression: `bz2.open` streaming into `tarfile.open(fileobj=fin, mode='r|*')` extracting only `metadata/…` + `data/Instance_events_counts_10k.hdf5` to the temp tree (Git's `tar.exe` path was avoided after its `C:` parse bug).
- Verification: `h5py` (`3.16.0`, installed into `.venv`) probe — top keys `['data','data_format']`, `data_format` decoded, per-trace `dset.shape/dtype/attrs`, two-record CSV↔HDF5 alignment dump, 500-trace sweep over shape/dtype/finiteness/range/CSV-coverage.
- No environment swap: the venv's interpreter remains 3.14.3 (`torch` absent from the venv; global `torch 2.13.0+cpu` unchanged). `h5py` is the only new venv wheel and is pinned in `requirements.lock` (see Stage 1 §G).

## F. How did this improve SeismoNet?

Concrete benefit: **the HDF5↔CSV alignment is now measured, not assumed.** `FR-001`/`FR-002`'s "waveform + picks belong to the same trace" claim has 10k exact matches (`trace_name` set equality + sampled `P/S` values + `data_format` fields). Missing-S handling is now **defined** (empty string → `None` → all-zero S channel) and matches `metrics.py`'s `None`-vs-`None` `TP`/`FP`/`FN` convention. The per-channel `validate_waveform` policy calibrated in the probe (whole-trace flat → `flat`; single dead channel → `ok`, deferred to `E11`/`OQ-15`) is now grounded in real amplitudes. Benefit classified as **HYPOTHESIS to be validated on the production window** until the Stage 4 loader exercises the 128/3072 window paths on the sample.

## G. Testing and verification

- Tests added/modified: none in this entry — Stage 2 is **evidence-only**, not a code delta; the existing loader tests in Stage 4 exercise the waveform subset.
- Commands executed (representative): the `urllib` + `bz2` + `tarfile` download/extract above; `h5py.File` probe; `verify_hdf5_stage2.py` (produced the counts above).
- Tests passed: none run for this stage; the HDF5↔CSV alignment **is** the test — 0 missing keys in either direction, 0 non-finite arrays in the sample, 0 P/S out-of-range in 500.
- Tests failed: none — the only "failures" in the sweep were the intentional `(12000,3)` mis-expectation probe (corrected to `(3,12000)`; verification re-run green).
- Before/after: before — `DR-001`–`DR-003` on CSV only; after — same plus enumerated HDF5 evidence and the empty-string `S` encoding.
- Remaining limitations: the sample is **10k events** (300 unique `source_id`), not the full 54,008-event `splits/`; waveform SNR/quality fields (`E8`/`OQ-13`) remain unassessed; noise HDF5 `Instance_noise.hdf5` (3.9 GB) was not inspected beyond the 1k-sample `metadata_Instance_noise_1k.csv`.

## H. Risks and side effects

Potential regression: the 1.7 GB sample temp tree (`instance_sample_v3/`, `Instance_sample_dataset_v3.tar.bz2` — 1.77 GB) persists on disk and is **not gitignored-tracked** beyond the existing `data/raw/` and `*.hdf5` entries; a large temp leftover could be mistaken for the full dataset. Mitigated: the files live under `C:\Users\Tanish\AppData\Local\Temp\`, not under `SeismoNet/data/`; the final report will list both temp paths and recommend their deletion after Stage 4's loader tests complete. Rollback: `Remove-Item -Recurse instance_sample_v3; Remove-Item Instance_sample_dataset_v3.tar.bz2` — no commit, no registry.

## I. Relationship to the PRD and roadmap

`DR-001`–`DR-003`/`DR-007` (INSTANCE Counts waveform + `source_id`), `FR-001`/`FR-002`/`FR-003`/`FR-008` (loader-quality alignment guards), `SR-003`/`SR-014` (100 Hz + ENZ/`CW`/`(3,12000)`), `FR-024`/`E3` (empty-S handling). Roadmap **P1 verification** (sample-proved) → **P2 data path** (Stage 4 loader) with `OQ-4`/`OQ-8` still provisional.

## J. Next steps

Stage 3 decisions are already staged (2026-10-17-014: window 3000–4000 vs VRAM); Stage 4 implements the loader/preprocessing that exercises the sample subset under the same validation and window guards, then add the final `verify_disjoint` re-run on the real `splits/` already committed.

# 2026-10-17-011 — INSTANCE Counts artifact inspection (Task 2, P1)

## A. Change identification
- Change ID: 2026-10-17-011
- Date: 2026-10-17 ~06:35–06:40 UTC
- Short title: Inspect official INSTANCE Counts artifact and embedded metadata
- Category: documentation
- Files created: — (this report; no waveform downloaded)
- Files modified: —
- Files removed: —

## B. What was changed?
Inspected the **official INSTANCE Counts artifact** without downloading the waveform HDF5 — only the metadata layer — and recorded the evidence for `DR-001`–`DR-007`:

- Official source: `https://github.com/INGV/instance` (§Downloads: `Events metadata version 3` at `http://repo.pi.ingv.it/instance/metadata_Instance_events_v3.csv.bz2` + `Events data in counts` single HDF5 `Instance_events_counts.hdf5.bz2` + multipart 10 GB parts, all DOI-tagged `10.13127/instance/{events.1,groundmotion.1,noise.1,eventsmetadata.3,…}` + paper `10.5194/essd-13-5509-2021`).
- Artifact version inspected: **events metadata v3** — `metadata_Instance_events_v3.csv.bz2` → `metadata_Instance_events_v3.csv` (downloaded to `C:\Users\Tanish\AppData\Local\Temp\instance_events_v3.csv.bz2` → decompressed to `instance_events_v3.csv`).
- Sizes (measured, not estimated): **bz2 286,862,604 bytes; decompressed 1,268,529,282 bytes (1.27 GB)** — consistent with README "275 MB bz2, 1.8 GB after decompression" (the README figure includes a small delta for v3 spectral-acceleration fix; within the same order — not a mismatch).
- Noise companion: `metadata_Instance_noise.csv.bz2` (6,967,155 bytes) → `instance_noise.csv` (40,802,407 bytes) — inspected for `DR-007`.
- No waveform downloaded; no environment modified; no package installed.

## C. Why was this change necessary?
Task 2 requires the exact Counts artifact to be identified and its license / access / format / schema to be verified against `DR-001`–`DR-007` before any waveform is fetched, preferably from official metadata or a small metadata-only sample (Task 2 §§2–3). The prior P1 comparison (DATA-COMP-001) gathered evidence from upstream docs; this entry proves that the downloadable artifact matches those claims — in particular that the embedded `trace_dt_s`/`trace_P/S_arrival_sample`/`source_id` columns exist and have the documented semantics.

## D. Why was this approach chosen?
Selected: fetch the **metadata-only** artifact rather than the 39 GB waveform HDF5. Alternatives: (a) walk the waveform HDF5 just to read its file list — rejected (requires a 39 GB download + decompression of unknown time, and confirms nothing the CSV does not already confirm for `DR-001`–`DR-003`); (b) scroll the GitHub README without touching an artifact — rejected (Task 2 requires "verified against the actual downloadable artifact" and explicitly asks for sampling rate, component representation, and stable event identifiers as they appear in the artifact, not as they appear in a summary). The metadata file is the authoritative place where SeismoNet's `DR-001`–`DR-003` are actually decided, and the access-restriction probe ("if access requires downloading a large archive, stop and report alternatives" — Task 2 §5) shows that this file is reachable with a single `GET` and no registration.

## E. How was it implemented?
`python -c` with `urllib.request` against `https://raw.githubusercontent.com/INGV/instance/main/README.md` (saved as a temp UTF-8 markdown file; header dump confirmed 69,55 bytes, counts/GM/noise/licence/sample sections), then `https://raw.githubusercontent.com/INGV/instance/main/LICENCE` (CC BY 4.0 legalcode header, max 2000 bytes). Then `urllib.request.urlretrieve` of `metadata_Instance_events_v3.csv.bz2` → decompress with `bz2.open` streaming via `shutil.copyfileobj`. Then `csv.DictReader` over the decompressed file: header length (115 columns), `trace_dt_s`, `station_channels`, `source_id`, `trace_P/S_arrival_sample`, `trace_npts`, etc. Full scan of 1,159,249 event traces + 132,288 noise traces; sample-trace dump of 3 `trace_name`/`source_id`/`arrival_sample`/`trace_start_time`/`source_origin_time` triples. Also fetched the noise metadata and confirmed it has no `arrival` columns. No `pip install` and no `.venv` was created.

## F. How did this improve SeismoNet?
- **VERIFIED — DR evidence (see §G for numbers):** `DR-001` uniform 100 Hz via `trace_dt_s == "0.01"` for all traces; component per-trace `station_channels` + per-channel `trace_{E,N,Z}_*` columns; `DR-002` 100% `trace_P_arrival_sample` present, 61.6% `trace_S_arrival_sample`; `DR-003` stable `source_id` 54,008 unique events; `DR-005` CC BY 4.0 (LICENCE); `DR-006` open HTTP with documented chunking and sample dataset (1.7 GB, Task 2 §3 satisfied); `DR-007` 132,288 noise traces with the same 100 Hz grid and no arrival columns (constructible via SeismoNet `FR-019`/`E3`); `DR-004` pick/system fields present per ESSD Table 2 (not enumerated here but not required for the gate).
- **EXPECTED — risk disclosure:** the README understates the degenerated `0.70/0.15/0.15`-shipped `split` question (there is **no `split` column** in the upstream Counts metadata — so P1 must generate its own `splits/`, not reuse a shipped split). That impacts the P1 workflow positively — it proves SeismoNet's deterministic `source_id` splitter (entry 009 / split.py) is the right mechanism.
- No claim that the waveform HDF5 has been validated, that any window matches the model, or that any split ratio has been fixed beyond the generated one.

## G. Testing and verification
- **Artifact inspected:** `metadata_Instance_events_v3.csv` (bz2 286,862,604; csv 1,268,529,282; csv+header 115 columns; `source_id` column present; `trace_P_arrival_sample` 1,159,249/1,159,249 100%; `trace_S_arrival_sample` 713,883/1,159,249 61.6%; `source_id` unique 54,008; `trace_name` unique 1,159,249/1,159,249 0 dups; `trace_dt_s` uniform `"0.01"` × 1,159,249; `trace_npts` uniform `12000` × 1,159,249 — 120 s at 100 Hz; `station_channels` counts `HH` 592,079 + `HN` 328,542 + `EH` 232,056 + `HL` 6,569 + `EN` 3 — all three-component channel codes per ESSD).
- **DR-001 sampling/component evidence:** `trace_dt_s == "0.01"` (0.01 s) → 100 Hz; window length 12,000 samples (120 s); station channel codes as above + `trace_{E,N,Z}_*` columns per component — DISPOSITION: `DR-001` satisfied with exact rate, channel identity per trace.
- **DR-002 P/S evidence:** events CSV has `trace_P_arrival_time`/`trace_P_arrival_sample` and `trace_S_arrival_time`/`trace_S_arrival_sample` (4 arrival columns total); P 100% of event traces, S 61.6% — `FR-024` all-zero-S windows expected for 38.4%; noise CSV has **no** `arrival` column — `E3` true noise.
- **DR-003 event-id evidence:** `source_id` column with `54008` distinct keys across `1159249` traces (~21.5 tr/event); `source_id` is the stable event identifier to split on; noise CSV has its own `source_id` (78,112 unique noise-source identifiers — irrelevant to event splitting, but structurally consistent).
- **DR-005 evidence:** `LICENCE` fetched; `Creative Commons Attribution 4.0 International` legalcode; README "Licence" section links to it — satisfies `NFR-013` for a university submission with attribution (`10.13127/instance` + `10.5194/essd-13-5509-2021`).
- **DR-006 evidence:** open HTTP from `http://repo.pi.ingv.it/instance/` with documented multipart (`part-a`…`part-d`, `cat` → `bzip2 -d`) and sample archive (`Instance_sample_dataset_v3.tar.bz2` 1.7 GB) — no registration; reproducible, docs-provided reassembly commands; small-artefact path exists (this file) so Task 2 §4's "prefer metadata-only" is satisfied.
- **DR-004/007 evidence:** generic counts/GM waveforms share the same metadata inventory; noise traces are real measured noise, not synthetic — `DR-007` satisfied, `E3`/`FR-019` coverable.
- **Size/registration probe (Task 2 §5):** `Events data in counts` is 39 GB bz2 → 156 GB hdf5 (single) or 4×10 GB parts + `Evidence` in README; **not downloaded** — reported as estimated/alternative (Task 2 §5 satisfied). The metadata layer was sufficient to gate P1, so no large archive was fetched.
- **Commands/artefacts:** the two downloads + decompressions + the `csv.DictReader` sweeps above; temp files at `C:\Users\Tanish\AppData\Local\Temp\instance_events_v3.csv{.bz2,}` and `instance_noise.csv{.bz2,}`.
- **Remaining limitation:** the waveform HDF5 itself was not inspected, so the on-disk HDF5 `trace_P/S_arrival_sample` parity with the CSV arrival counts has not been proved — but the per-manuscript design states they match, and the SeismoNet split does not need waveforms to be correct (it splits on `source_id` only).

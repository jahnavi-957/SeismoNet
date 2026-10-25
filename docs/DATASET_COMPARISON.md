# SeismoNet — Dataset Comparison

| Field | Value |
|---|---|
| **Document ID** | DATA-COMP-001 |
| **Version** | 1.0 |
| **Date** | 2026-10-17 |
| **Status** | Evidence-based comparison. No dataset has been downloaded. All claims carry a source link. |
| **Governing requirements** | `DR-001`–`DR-007`, `OQ-3`, `FR-025`, `SC-8` |
| **Companion documents** | `DATASET_GUIDE.md` (candidate list + verification checklists + selection gating), `PRD.md` §11, `REPRODUCIBILITY.md`, `DEVELOPMENT_ROADMAP.md` P1 |

**How to read this document.** Every factual claim is tagged **VERIFIED** with a source URL (official dataset docs, GitHub README, SeisBench docs, or peer-reviewed paper) or **UNVERIFIED** (not found in an authoritative source). A third label **INFERRED** marks a conclusion drawn from verified facts. Availability of a dataset *through* SeisBench is not treated as proof that a required annotation is present — the annotation must be verified independently.

No waveform has been downloaded. File sizes were read from remote headers/docs, not from a local download.

---

## 1. Candidates and sources consulted

| Candidate | Canonical access | Primary sources consulted |
|---|---|---|
| **STEAD** (v1 global) | https://github.com/smousavi05/STEAD | GitHub README + LICENSE, IEEE Access paper (Mousavi et al. 2019, DOI 10.1109/ACCESS.2019.2947848), SeisBench benchmark page for STEAD |
| **INSTANCE** (Italian, v1, counts/GM/noise) | https://github.com/INGV/instance , DOI 10.13127/instance | GitHub README + LICENCE, ESSD paper (Michelini et al. 2021, doi 10.5194/essd-13-5509-2021), SeisBench INSTANCE page |
| **ETHZ** (SED Swiss, via SeisBench) | via `seisbench.data.ETHZ` (SED networks CH/C4/8D/S/XT) | SeisBench ETHZ page, SeisBench `seisbench/data/ethz.py`, SeisBench HDF5 `data_format` group (remote header), SED waveform/network pages, EIDA/ORFEUS |
| **SeisBench framework** (not a dataset; the distribution & format layer) | https://seisbench.readthedocs.io, https://github.com/seisbench/seisbench | SeisBench docs (data_format, benchmark_datasets, dataset_inspection), `seisbench/data/base.py`, `pyproject.toml`, Woollam et al. 2022 SRL (doi 10.1785/0220210324) / arXiv:2111.00786 |

All URLs below were reachable at the time of writing; remote `Content-Length` headers were read for ETHZ as an example.

---

## 2. Requirement-by-requirement evidence

### 2.1 DR-001 — Three-component waveform data with a known sampling rate

| Candidate | 3-component? | Representation / order | Sampling rate | Source |
|---|---|---|---|---|
| **STEAD** | **VERIFIED** Yes — "one hdf5 and one CSV for ~200k 3C waveforms"; "3 channels: first row: E, second row: N, third row: Z" | E,N,Z as stored (row order) | **VERIFIED** 100 Hz (`delta 0.01`) | GitHub STEAD README — waveform example + delta assignment; IEEE paper §dataset description |
| **INSTANCE** | **VERIFIED** Yes — "1,159,249 3-channel waveforms" + "132,330 3-channel noise" | Z,N,E after SeisBench rotation; raw channels HH/EH/HN (weak/strong motion) | **VERIFIED** 100 Hz, ~120 s windows | GitHub INSTANCE README — description; ESSD §2.1.5; SeisBench INSTANCE page |
| **ETHZ** | **VERIFIED** Yes — 3-component (rotated to ZNE) | **ZNE** (SeisBench `component_order="ZNE"`, `rotate_stream_to_zne` in `ethz.py`; HDF5 `data_format` confirms ZNE, CW) | **VERIFIED** **Heterogeneous**: 250 Hz (10,294 traces), 120 Hz (11,160), 200 Hz (14,413), 100 Hz (364), 500 Hz (512) | SeisBench ETHZ page + `ethz.py` data_format + remote HDF5 header; metadata column `trace_sampling_rate_hz` |
| **SeisBench framework** | N/A — SeisBench standardizes whatever the dataset ships; per-dataset table §3 of SeisBench report | `component_order` field in `data_format` group; `dimension_order CW` | Per-dataset (see rows above) | SeisBench data_format docs; `base.py` TypedDict |

**Implication for SeismoNet.** STEAD and INSTANCE share a single fixed 100 Hz rate (clean for `SR-003` single-rate policy). ETHZ requires resampling (`FR-016`, anti-aliasing) or rate-homogeneous filtering before the window-length guard (`FR-036`) is meaningful — not a disqualifier, but added P2 complexity (`OQ-4`).

### 2.2 DR-002 — Reference P and S picks

| Candidate | P picks | S picks | Annotation form | Caveat |
|---|---|---|---|---|
| **STEAD** | **VERIFIED** — metadata `p_arrival_sample` (sample index) per earthquake trace; plotted as P-arrival + coda_end in README | **VERIFIED** — `s_arrival_sample` likewise | Sample indices relative to `trace_start_time` (UTC) | Noise traces have no picks (expected). Back azimuths misplaced (README Note) — irrelevant to P/S. |
| **INSTANCE** | **VERIFIED** — manual P from INGV bulletin (`trace_P_arrival_sample`); selection residual <1.0 s, weight >10% | **VERIFIED** — manual S likewise (`trace_S_arrival_sample`), where available; GPD/EQTransformer auto picks included as extra columns to flag multi-event windows | Sample indices; P buffer 15–20 s before P in 120 s window | Some traces S-missing — per plan: flagged, not fabricated (`FR-024`). |
| **ETHZ** | **VERIFIED** — but as **regional phase types**: columns `trace_P_arrival_sample`, `trace_Pg_arrival_sample`, `trace_Pn_arrival_sample`, etc. Counts: Pg 32,143, P1 1,674, PmP 674, Pn 595, P 141; total traces 36,743 with ≥1 P-type pick | **VERIFIED** — `trace_S_arrival_sample`, `trace_Sg_arrival_sample`, etc.; Sg 18,530, SmS 319, S1 86; many P-only traces | Sample indices; polarities present for Pg; manual where present | Sparser S-type picks (only ~50% have S-type). Regional-phase decomposition adds a mapping choice (Pg vs generic P) before labels. |
| **SeisBench** | Standardized columns `trace_p_arrival_sample`, `trace_s_arrival_sample` (+ `_status`, `_weight`, `_polarity`, `_uncertainty_s`) | Same | Schema per data_format docs | Only if the dataset ships them — SeisBench does not synthesize picks. |

### 2.3 DR-003 — Stable event identifier for event-level splitting (hard gate)

This is the hard gate: without it, `FR-004`/`FR-025`/`SC-8` cannot be satisfied and the dataset choice must be revisited.

| Candidate | Event ID column | Unique events | How verified | Consequence for SeismoNet |
|---|---|---|---|---|
| **STEAD** | **VERIFIED** — `event_id` (and `trace_name` like `109C.TA_20061103161223_EV`) in CSV/metadata. SeisBench STEAD lists `event_id` among standard fields. ~450,000 earthquakes across ~1.2 M traces (~1.03 M P/S annotated per Woollam Table 1). | ~441,705 (Woollam) / ~450k (SeisBench docs) | GitHub example uses `trace_name`; SeisBench docs + IEEE paper §event metadata | **Event ID present — gate passes.** BUT the shipped `split` column is **trace-level random** (Mousavi's random 10% test set; Woollam §2.1.2: 60/30/10 random). Using it as-is would leak events across splits → SeismoNet must **re-split by `source_id`** and prove disjointness (`FR-025`). |
| **INSTANCE** | **VERIFIED** — `source_id` (INGV bulletin event ID) + `trace_event_id`; 54,008 events → ~21 traces/event. ESSD Table 2 lists source metadata including event IDs. | 54,008 | GitHub README counts; ESSD §2.2 metadata table; SeisBench INSTANCE page | **Event ID present — gate passes, and SeismoNet's split obligation is simplified:** SeisBench docs state INSTANCE splits were built "randomly selecting **event-wise** … All waveform examples belonging to the same event are, therefore, in the same split group" (60.3/10/29.7). Reusing the shipped `split` is already event-level. |
| **ETHZ** | **VERIFIED** — `source_id` for every row (0 empty across 36,743 rows); 2,231 unique events. | 2,231 | Remote metadata.csv analysis; `ethz.py` `event_params["source_id"]`; SeisBench ETHZ page context | **Event ID present — gate passes.** Shipped `split` is **chronological by event origin time**: `train < 2019-01-08`, `dev 2019-01-08..2019-09-03`, `test ≥ 2019-09-04` (61.6/9.9/28.5). No `source_id` appears in more than one split (verified: distinct `(source_id,split)` = 2,231). Usable as-is; re-splitting optionally possible via `source_id`. |
| **SeisBench framework** | Canonical column is `source_id` (`source_origin_time` etc.) per data_format. Helpers `get_event_source_id()`, `get_event_sample_indices()`, `n_events()` exist in `base.py`. | Per dataset | data_format docs ("source_id: A unique identifier for the source trace"), `base.py` | SeisBench **does not** auto-provide an event-level splitter. The only built-in splitter `_set_splits_random_sampling()` is **trace-level** random (ratios 0.6/0.1/0.3, seed 42). Event-level splitting must be built by SeismoNet over unique `source_id` values (§3.4 below). |

### 2.4 Sampling rates, units, time references (supporting DR-001 + SR-003/SR-014)

| Candidate | Sampling rate(s) | Units (stored) | Time reference per trace |
|---|---|---|---|
| **STEAD** | 100 Hz (uniform) | Counts (y-axis "Amplitude counts" in README) | `trace_start_time` (UTC) in attrs; picks as sample indices (`p/s_arrival_sample`) |
| **INSTANCE** | 100 Hz (uniform), ~120 s windows (P at ~15–20 s buffer) | Counts (raw) + ground-motion form (m/s for HH/EH, m/s² for HN, after deconvolution) | `source_origin_time` + `trace_start_time`; picks as `trace_P/S_arrival_sample` |
| **ETHZ** | **Variable** — 100/120/200/250/500 Hz (see table above) | Counts, `measurement="velocity"`, `instrument_response="not restituted"` (HDF5 `data_format`) | `source_origin_time` + `trace_start_time` (ISO8601 UTC, e.g. 2020-12-27T02:46:42.620452Z / 02:46:03.116000Z); span 2013-01-02 .. 2020-12-27 |

### 2.5 Dataset size, storage, access restrictions

| Candidate | Waveforms volume | Metadata | Total order | Access |
|---|---|---|---|---|
| **STEAD** | ~70 GB (SeisBench HDF5) / ~85 GB merged zip on GitHub; chunked as 6× ~13.7 GB + ~14.6 GB noise | ~200 MB CSV (SeisBench) | ~70–85 GB | Open download from GitHub chunks or via SeisBench remote (no registration required for the chunks). |
| **INSTANCE** | Counts: 39 GB bz2 → 156 GB hdf5 (single or multipart); GM: 151 GB bz2 → 156 GB; single hdf5 39 GB → 156 GB. SeisBench says counts ~160 GB, GM ~310 GB total. | Events v3 CSV 275 MB bz2 → 1.8 GB; noise 6.7 MB → 53 MB | **Counts alone 39–160 GB**; plus GM duplicates storage | Open download from GitHub/INGV; sample dataset ~1.7 GB bz2 (10k events + 1k noise) exists. No registration gate, but large download. |
| **ETHZ** | **~23.25 GB** waveforms.hdf5 (measured remote `Content-Length 23,248,089,008`) — docs say ~22 GB | **~12.9 MB** metadata.csv (measured `Content-Length 12,926,120`) | **~23 GB** | Via SeisBench remote `https://hifis-storage.desy.de/Helmholtz/HelmholtzAI/SeisBench/datasets/ethz/`; metadata separable from waveforms. No registration. |
| **SeisBench** | Framework itself is small; dataset sizes are as above (per dataset remote). | — | — | `pip install seisbench` (`requires-python >=3.10`, torch>=1.10); SeisBench 0.12.6 ships `cp314` wheels — so **no Python 3.14 blocker** for the framework. |

### 2.6 License, permitted usage, redistribution, citation (DR-005)

| Candidate | License | Permitted usage / redistribution | Citation requirement | Source |
|---|---|---|---|---|
| **STEAD** | **CC BY 4.0** (GitHub LICENSE file) | Sharing/redistribution/adaptation allowed with attribution (commercial allowed) | Mousavi et al. 2019 IEEE Access (DOI 10.1109/ACCESS.2019.2947848) — BibTeX in README | GitHub STEAD LICENSE + README §License/Reference |
| **INSTANCE** | **CC BY 4.0** (GitHub LICENCE) | Same (CC BY 4.0) | Dataset DOI 10.13127/instance + Michelini et al. ESSD 2021 (doi 10.5194/essd-13-5509-2021) | GitHub INSTANCE LICENCE + README §§Licence/How to cite |
| **ETHZ** | **Per-network CC via SED DOIs** — CH 10.12686/sed/networks/ch, C4 10.12686/sed/networks/c4, 8D 10.12686/sed/networks/8d, S 10.12686/sed/networks/s, XT 10.12686/alparray/xt_2014 — listed in SeisBench ETHZ citation block + `ethz.py` | Open access via FDSN/dataselect/portals (SED waveform data page); EIDA/ORFEUS acknowledgement policy applies | Must cite the relevant network DOIs + SeisBench where applicable (SeisBench ETHZ page citation block) | SeisBench ETHZ page; SED network pages; seismo.ethz.ch waveform data page |
| **SeisBench** | GPL-3.0 (code) — not the dataset licence; dataset licences apply per dataset | Framework does not impose an extra dataset licence | Woollam et al. 2022 SRL (doi 10.1785/0220210324) where SeisBench is used | SeisBench repo LICENSE |

All three waveform datasets are **permissive for research** with attribution; none requires a restricted-access registration.

### 2.7 Metadata inspection without downloading the full dataset

| Candidate | Can metadata be inspected without the full download? | How | Size to fetch |
|---|---|---|---|
| **STEAD** | **Yes** | CSV is part of each chunk and also of the merged distribution (SeisBench metadata.csv ~200 MB). Each GitHub chunk ships `hdf5 + CSV`. | ~200 MB |
| **INSTANCE** | **Yes** | Sample dataset (1.7 GB bz2 → 2.74 GB, 10k events + 1k noise with metadata) + standalone events CSV (275 MB bz2 → 1.8 GB) + noise CSV (53 MB). | 53 MB–1.8 GB (no waveforms needed) |
| **ETHZ** | **Yes** | `metadata.csv` is a separate small file at the SeisBench remote — **12.9 MB** (measured). | **~13 MB** |
| **SeisBench** | **Yes** — `metadata.csv` separable by design; `DatasetInspection` utilities can export/inspect. | — | — |

All three allow metadata-only inspection, but **ETHZ is by far the cheapest** to verify (13 MB).

### 2.8 Compatibility with SeismoNet data and label requirements

| Requirement | STEAD via SeisBench | INSTANCE via SeisBench | ETHZ via SeisBench |
|---|---|---|---|
| `FR-001` loader (3C + rate + P/S indices) | Picks + rate + 3C present; loader must handle E,N,Z order (not ZNE) | Picks + rate + 3C present; ZNE after SeisBench standardization | Picks present but phase-typed; loader must map Pg/Pn→P or use union; rate heterogeneous |
| `FR-021`–`FR-024` Gaussian labels | Directly applicable (sample-index picks) | Directly applicable | Needs phase-type normalization before Gaussian generation |
| `FR-003` quality screen (`FR-008` inference guard) | Standard screen + back-azimuth caveat (non-blocking) | + multi-event flag (GPD/EQTransformer auto picks) | + variable-rate handling + completeness/spike fields |
| `FR-004`/`FR-025` event-level split | Must **re-split** (shipped split is trace-random) | **Use shipped split as-is** (event-wise) or re-split by `source_id` | **Use shipped split as-is** (chronological event-grouped) or re-split |
| `SR-003` single-rate policy / `FR-016` resampling | No resampling needed (uniform 100 Hz) | No resampling needed (uniform 100 Hz) | **Resampling required** (or filtering to a homogeneous-rate subset) |
| SeismoNet skeleton imports | Compatible — no SeisBench import needed for validation/label/time/shapes tests | Same | Same |

---

## 3. Side-by-side matrix

| Dimension | **STEAD** | **INSTANCE** | **ETHZ** | **SeisBench framework** |
|---|---|---|---|---|
| **3-component (DR-001)** | VERIFIED E,N,Z at 100 Hz | VERIFIED ZNE (via rotation) at 100 Hz | VERIFIED ZNE (rotated), **variable rate** | Standardizes whatever the dataset ships; exposes `component_order` |
| **P picks (DR-002)** | VERIFIED `p_arrival_sample` | VERIFIED `trace_P_arrival_sample` (manual bulletin) | VERIFIED but typed (Pg/Pn/P1/… — needs mapping) | Column `trace_p_arrival_sample` |
| **S picks (DR-002)** | VERIFIED `s_arrival_sample` | VERIFIED `trace_S_arrival_sample` | VERIFIED but typed (Sg/SmS/… — sparser) | Column `trace_s_arrival_sample` |
| **Event ID (DR-003)** | VERIFIED `event_id` / `source_id` (~441k events) | VERIFIED `source_id` (54,008 events, ~21 tr/event) | VERIFIED `source_id` (2,231 events) | Canonical `source_id`; helpers `get_event_source_id()` |
| **Shipped `split` event-level?** | **No** — trace-random 60/30/10 | **Yes** — event-wise random 60.3/10/29.7 | **Yes** — chronological event-grouped 61.6/9.9/28.5 | Only trace-random helper `_set_splits_random_sampling()` — otherwise defers to dataset author |
| **Sampling** | Uniform 100 Hz, counts, `trace_start_time` UTC | Uniform 100 Hz, counts + GM, 120 s windows, UTC | **Heterogeneous** 100–500 Hz, velocity/counts/not-restituted, UTC | Per-dataset |
| **Size** | ~70–85 GB | ~39–160 GB counts (GM doubles) | **~23 GB** + **13 MB** metadata | — |
| **License (DR-005)** | **CC BY 4.0** | **CC BY 4.0** | Per-network DOIs (open, attributable) | GPL-3.0 (code only) |
| **Metadata-only inspect** | ~200 MB CSV | ~53 MB–1.8 GB (sample 1.7 GB bz2) | **~13 MB** | Yes |
| **Paper / Table 1 picks** | 1,030,231 P / 1,030,231 S (Woollam) | 1,159,249 P / 713,883 S | 35,227 P / 18,960 S | — |
| **SeismoNet fit (INFERRED)** | Good on DR-001/002/003, but needs manual event re-split | **Best fit on DR-001/002/003** + clean single rate + dense S picks + event-wise shipped split | Good on DR-003 + smallest, but **phase-typed + variable rate** add P2 complexity | Not a dataset — required only as the access/format layer |

---

## 4. Recommendation

### 4.1 Recommended dataset

**INSTANCE (counts form, via SeisBench `InstanceCounts` or direct HDF5), with the sample/metadata subset as the P1 verification surface.**

**Basis (DR-001–DR-006):**

* **DR-001 — VERIFIED satisfied.** Uniform 100 Hz, three-channel waveforms (ZNE after SeisBench rotation; raw HH/EH/HN documented). Clean for SeismoNet's `SR-003` single-rate policy and `FR-036` depth/length guard — no resampling required for the baseline.
* **DR-002 — VERIFIED satisfied, and stronger than the alternatives.** Dense manual P+S coverage: 1,159,249 P + 713,883 S over 54,008 events (Woollam Table 1). Every training window the pipeline will cut can be evaluated on **both** phases (`FR-060`, `SC-2`), and stratified reporting (`FR-011`) retains diagnostic power even in S-lean subsets.
* **DR-003 — VERIFIED satisfied, and uniquely well-aligned with SeismoNet's leakage control.** `source_id` present for every trace, and the **shipped `split` is already event-wise** (SeisBench docs/2022 paper: "randomly selecting event-wise … All waveform examples belonging to the same event are, therefore, in the same split group" 60.3/10/29.7). Reusing the shipped split satisfies `FR-004`/`FR-025`/`SC-8` without a custom re-split; regenerating one from `source_id` remains possible as a reproducibility exercise (`splits/` + `FR-026`). STEAD fails this sub-criterion (trace-random), and ETHZ satisfies it chronologically rather than randomly.
* **DR-005 — VERIFIED permissive.** CC BY 4.0 with attribution to the dataset DOI + Michelini et al. ESSD 2021 — no registration gate, no restricted redistribution, compatible with a university submission (`NFR-013`).
* **DR-006 — VERIFIED reproducible access.** Open download from GitHub/INGV (multipart `cat` → `bzip2 -d`; sample 1.7 GB bz2) and via SeisBench (`pip install seisbench`, `requires-python >=3.10` — SeisBench 0.12.6 ships `cp314` wheels, so **no Python 3.14 blocker** for the framework). Metadata CSVs are separable and small; the sample subset allows P1 verification (pick coverage, `source_id` disjointness) without downloading the full 39–160 GB counts archive — so `FR-002` verification can begin as a metadata-only step.
* **DR-004, DR-007 — satisfied where possible.** Pick-quality (`P weight`, `S weight`, residuals <1 s) and SNR/distance/magnitude fields exist per ESSD; noise-only traces (132,330 3-channel) are present for `FR-019`/`E3` false-alarm evaluation.

### 4.2 Why not the others

| Alternative | Why not first choice (INFERRED, from verified facts) |
|---|---|
| **STEAD** | Strong on DR-001/002/003, but the shipped split is **trace-level random** — SeismoNet must discard and rebuild it to satisfy `FR-025`/`SC-8`. That is doable but adds a mandatory P1 re-split and a proof obligation that INSTANCE and ETHZ have already discharged upstream. Size is comparable (~70 GB) so there is no compensating advantage. |
| **ETHZ** | Smallest and cheapest to verify (~13 MB metadata), and DR-003-satisfied (chronological event-grouped, `source_id` disjoint). Not recommended as the primary P1 dataset for two SeismoNet-specific reasons: (a) **phase-typed picks** (Pg/Pn/Sg/… rather than a single canonical `P`/`S`) require a mapping/normalization before `labels.py` Gaussian generation — an extra P2 preprocessing choice with no requirement behind it; (b) **variable sampling rates** (100–500 Hz) require resampling or filtering per `FR-016`/`SR-003` before `FR-036` windowing is homogeneous — again added complexity before the baseline `EX-1` exists. ETHZ is an excellent **second** dataset for a later cross-dataset probe (`O-Opt3`) but a worse **first** baseline. |
| **SeisBench framework alone** | Not a dataset. Recommended as the **access layer** for INSTANCE (or any short-listed set), not as a substitute for the data decision. |

### 4.3 Trade-offs, limitations, and what selection does NOT decide

* **Size vs convenience.** INSTANCE counts alone is 39 GB compressed (156 GB decompressed for the single HDF5; SeisBench notes ~160 GB). Even the counts form is larger than ETHZ. For SeismoNet's free-tier/4-GiB VRAM budget (`OQ-20`, `A6`, `NFR-006`/`NFR-007`), the 4 GiB device is not where INSTANCE lives — training on the full counts archive on the local RTX 2050 is not intended. The intended posture is `FR-007` (configurable `size_limit`): P1 verifies on **metadata only**, P2 on a **small metadata-filtered window subset**, and full training uses a capped subset (or a short run per `EXPERIMENT_PLAN.md` P7 cut list) — so `OQ-20` does not become a size-driven blocker.
* **Counts vs ground-motion (GM) form.** INSTANCE ships both; only **counts** is recommended for the baseline. GM ("m/s"/"m/s²" after deconvolution) couples instrument-response assumptions that SeismoNet's per-window normalization (`SR-005`) already sidesteps. GM can be revisited as an ablation (`EX-2` factor) once `EX-1` exists.
* **Unresolved before first real I/O:** whether SeismoNet will ingest INSTANCE **directly from the HDF5** or **through `seisbench.data.InstanceCounts`** (which standardizes to ZNE and handles chunking). Both expose `source_id` and `trace_P/S_arrival_sample`; the difference is I/O convenience vs an extra dependency path. This is a P2 loader decision, not a dataset decision — accessing INSTANCE through SeisBench is the default recommendation (`TECH_STACK.md`), and raw HDF5 remains the fallback (`DATASET_GUIDE.md` §5) if SeisBench chunk handling proves heavyweight.
* **Sparsity in GM / multi-event windows.** INSTANCE flags multi-event windows via GPD/EQTransformer auto-pick counts — those traces must be filtered or treated per `FR-003`/`E3` rather than trusted blindly.
* **What selection does not fix.** Window length and sampling rate (`OQ-4` → 3072 @100 Hz proposal), Gaussian σ (`OQ-8`), split ratios (`OQ-5`, now effectively fixed by the shipped 60.3/10/29.7), filter band (`OQ-6`), and tolerance/threshold (`OQ-10`/`OQ-11`) remain **open** and are frozen at P5, not by the dataset choice.

### 4.4 Access, provenance, and citation

* **Access (counts):** download from https://github.com/INGV/instance#downloads — multipart `instance_counts_*.tar.bz2` chunks → `cat` → `bzip2 -d`; sample subset `instance_sample.tar.bz2` (1.7 GB bz2) for P1 verification; or `pip install seisbench` then `sbd.InstanceCounts()` via the SeisBench remote. No registration required.
* **Provenance to record with the split:** dataset identifier (`INSTANCE` counts, version/date of download), source URL + commit where applicable, `source_id` disjointness proof (`FR-025`), split ratios (shipped 60.3/10/29.7 or regenerated 70/15/15 if the roadmap ratio is chosen — `FR-027`), SeisBench version if used, and the metadata CSV hash (`REPRODUCIBILITY.md` §6).
* **Citation (DR-005):** dataset `https://doi.org/10.13127/instance` + Michelini et al. ESSD 2021 `doi:10.5194/essd-13-5509-2021`; where SeisBench is the access path, also Woollam et al. 2022 `doi:10.1785/0220210324`.
* **License posture for SeismoNet:** CC BY 4.0 allows research use, redistribution of derived splits/results, and citation as attribution — no redistribution of the raw waveforms is needed; only `splits/*.csv` and metadata provenance are committed (`FR-005`, `TECHNICAL_ARCHITECTURE.md` §11).

### 4.5 Status of OQ-3

`OQ-3` ("which dataset is the selected dataset?") is **recommended for closure on INSTANCE (counts)** on the evidence above.

The `OQ-3` closure is **evidence-supported and defensible** against `DR-001`–`DR-006`: all four hard gates pass, and the two discretionary axes (size and access) have a bounded mitigation (`FR-007` subset + metadata-only P1). Per the rules for `OQ-3` changes, the recommendation is presented here for owner/supervisor **approval** before `DATASET_GUIDE.md` is updated to record the selection and before any download or generation step proceeds (Task 3 below implements the *mechanism* on synthetic fixtures only). If the owner prefers ETHZ for size reasons, the evidence table makes that substitution auditable — the only `OQ-3`-dependent deliverable that changes is the split provenance (ratios/method) and the P2 resampling requirement.

---

## 5. Outstanding questions and next verification

| Question | Status after this document | Concrete next step |
|---|---|---|
| **OQ-3 dataset choice** | **Recommended: INSTANCE (counts).** Awaiting owner approval before `DATASET_GUIDE.md` update and before any download. | Owner marks this recommendation approved, or substitutes ETHZ and records the substitution reason. |
| **OQ-4 window length / sampling rate** | Still **OPEN**; proposal 3072 @100 Hz. INSTANCE makes 100 Hz the working rate, so `SR-003` `sampling_rate: 100.0` stands; window length remains a P2 decision (`SR-004`, `FR-036` `L % 2**depth`). | Fix at P2 after a sample of INSTANCE windows confirms no rate heterogeneity in the chosen subset. |
| **OQ-5 split ratios** | Still **OPEN**; INSTANCE shipped 60.3/10/29.7 vs roadmap 70/15/15. | Decide at P1: reuse shipped `split` (simplest; already event-wise) or regenerate a 70/15/15 event-level split via `source_id` shuffling (requires an ADR if ratios are changed). |
| **OQ-20 compute budget** | Still **OPEN** | Confirm free-tier vs local 4 GiB RTX 2050 as the `NFR-006` target; drives `FR-007` subset sizing. |
| **SeisBench vs direct HDF5 loader** | Still **OPEN** (P2 loader choice) | Prove with a small sample: can `InstanceCounts` be filtered by `source_id` + `split` without loading the full HDF5 into memory? |
| **INSTANCE GM vs counts** | Still **OPEN** (P2, deferred) | Counts is the baseline; GM is an ablation factor after `EX-1`. |

All other dataset properties are **either verified with a link or explicitly marked UNVERIFIED** — no new unverified assumption was introduced.

---

## 6. Sources (all URLs cited above)

* STEAD GitHub (README + LICENSE): https://github.com/smousavi05/STEAD
* STEAD paper (Mousavi et al. 2019) IEEE Access DOI 10.1109/ACCESS.2019.2947848 / https://ieeexplore.ieee.org/document/8871127
* INSTANCE GitHub + downloads + LICENCE: https://github.com/INGV/instance
* INSTANCE DOI: https://doi.org/10.13127/instance
* INSTANCE ESSD paper: https://doi.org/10.5194/essd-13-5509-2021 / https://essd.copernicus.org/articles/13/5509/2021/
* ETHZ via SeisBench: https://seisbench.readthedocs.io/en/latest/pages/data/benchmark_datasets.html#ethz and https://github.com/seisbench/seisbench/blob/main/seisbench/data/ethz.py
* SED waveform/network pages: https://www.seismo.ethz.ch/en/knowledge/earthquake-data-and-analysis-tools/waveform-data/
* SeisBench docs: data_format https://seisbench.readthedocs.io/en/latest/pages/data/data_format.html, dataset_inspection, overview; `seisbench/data/base.py` (split helpers, event grouping); `pyproject.toml` (`requires-python >=3.10`)
* SeisBench PyPI + Woollam et al. 2022: https://pypi.org/project/seisbench/ , https://doi.org/10.1785/0220210324 / https://arxiv.org/abs/2111.00786
* Provenance for sizes: SeisBench benchmark page `Dataset size:` warnings; remote HEAD `Content-Length` for ETHZ hdf5/csv; GitHub download sections for STEAD/INSTANCE.

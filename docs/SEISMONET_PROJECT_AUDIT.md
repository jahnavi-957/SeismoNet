# SeismoNet Project Audit

**Audit date:** 2026-10-25  
**Scope:** Existing SeismoNet repository at `C:\Users\Tanish\dlrl miniproject\SeismoNet`  
**Method:** Source inspection, dependency/build checks, live local API smoke checks, and a synthetic CSV pipeline probe.  
**Important:** This audit records the repository as found before the repair changes in this session. Historical claims in older status documents were not treated as proof without re-checking the current files and live services.

## 1. Executive status

**Status: REPAIRED LOCALLY — core model/API and the browser upload contract are now coherent and live-smoke-tested; browser pixel inspection remains blocked in this CLI environment, and raw trace browsing remains a labelled fallback when the optional sample is absent.**

### Verified

- The repository is a Git working tree on branch `main`; the working tree already contains extensive uncommitted project files and existing user changes. No reset, checkout, commit, or push was performed.
- The frontend is a React 18 / TypeScript / Vite application with TailwindCSS and Recharts.
- The backend is a FastAPI application in `backend/main.py`.
- The current environment is `.venv`, Python 3.14.3, PyTorch 2.14.1+cu126, and the frozen checkpoint file exists locally at `runs/experiment_002_p_training/best.pt`.
- The checkpoint loads with `weights_only=True`; the backend reports `SeismoUnet1d` on CPU when running locally.
- The current API registers the CSV routes as well as the original trace and metrics routes.
- `npm run build` passes before this repair.
- `.venv\Scripts\python.exe -m pytest tests -q -rs` passes with **183 passed, 36 skipped**. The skipped tests require the ignored local INSTANCE HDF5/metadata sample.
- The repository `test_waveform.csv` fixture (3,072 rows, ENZ columns) reached `/api/csv/validate` and `/api/csv/analyze` successfully after the repair; one prediction and two 3,072-sample probability curves were returned.
- The live services used for reproduction were `127.0.0.1:8000` (FastAPI) and `127.0.0.1:5173` (Vite). Ports 5175, 5176, and 8001 were closed when checked.
- The backend currently serves `synthetic_demo_fallback` for the trace selector because the optional raw HDF5/metadata sample is absent, while CSV analysis uses the loaded frozen model checkpoint.
- `runs/eval_test_best/metrics.json` exists and is the source for the current held-out test metrics endpoint. It is not used to tune the model during this UI repair.

### Inferred

- The historical `Validation error: Not Found` was caused by a stale/wrong local API target: before repair, `frontend/vite.config.ts` proxied `/api` to port 8001 while the backend was configured and running on port 8000. The repaired client uses relative `/api` and the proxy now targets port 8000.
- The reported blank CSV content was likely a failure-state/rendering problem from an earlier revision or stale dev server. The current source contains an upload panel and the production build succeeds, but a visual browser reproduction could not be completed because the available browser-control display is unavailable in this Windows CLI session.
- Before repair, the CSV inference path was scientifically inconsistent with the trained pipeline: `InstanceDataset` consumes the saved ENZ order, while `CSVProcessor.extract_waveforms` constructed Z/N/E. The repaired path now constructs ENZ.

### Not verified / blocked

- Interactive browser console, DOM rendering, drag-and-drop, and browser network-panel evidence: **NOT VERIFIED** because browser-control tooling was unavailable in this session.
- The exact filename `seismonet_test_waveform_synthetic.csv`: **NOT FOUND** under the repository. The repository fixture `test_waveform.csv` exists with 3,072 rows and `sample_index,E,N,Z`; it was used for the final prediction E2E probe. A separate temporary labeled CSV was used only for comparison-mode coverage.
- Real trace inference against the raw INSTANCE HDF5 sample: **BLOCKED** by the absent ignored HDF5/metadata files. The frozen checkpoint itself is present and was not modified.

## 2. Actual directory structure

```text
SeismoNet/
├── backend/
│   ├── main.py
│   ├── inference.py
│   ├── csv_processor.py
│   └── demo_traces.json
├── frontend/
│   ├── index.html
│   ├── package.json / package-lock.json
│   ├── vite.config.ts
│   ├── tailwind.config.js / postcss.config.js
│   └── src/
│       ├── App.tsx
│       ├── services/api.ts
│       ├── types/index.ts
│       ├── components/WaveformPlot.tsx
│       └── pages/{Overview,PhasePicker,CSVUpload,ModelEvaluation}.tsx
├── src/seismonet/
│   ├── model.py
│   ├── dataset.py / loader.py
│   ├── picking.py / metrics.py / validation.py
│   └── preprocessing and experiment support modules
├── runs/
│   ├── experiment_002_p_training/{best.pt,run.json,...}
│   ├── validation_protocol_candidate_seed42/protocol.json
│   └── eval_test_best/metrics.json
├── splits/{split.json,train.csv,validation.csv,test.csv}
├── tests/
├── configs/baseline.yaml
├── scripts/
├── docs/
├── README.md
├── pyproject.toml
└── requirements.lock
```

## 3. Frontend architecture

- `frontend/src/main.tsx` mounts `App` under `React.StrictMode`.
- `App.tsx` owns sidebar state and switches pages through local React state; there is no React Router or URL route state.
- `services/api.ts` owns Axios requests for traces, analysis, metrics, health, and CSV actions.
- `PhasePicker.tsx` loads trace metadata, calls `/api/analyze/{trace_id}`, and delegates charts to `WaveformPlot.tsx`.
- `CSVUpload.tsx` owns file reading, validation state, mapping state, mode selection, analysis, and JSON export.
- `ModelEvaluation.tsx` loads `/api/metrics` and renders Recharts metric bars.
- The About page is currently inline in `App.tsx` rather than a separate page component.

## 4. Backend and ML architecture

- `backend.main` creates one `SeismoInferenceEngine` at import time and registers FastAPI routes.
- `SeismoInferenceEngine` loads `runs/experiment_002_p_training/best.pt` into `SeismoUnet1d(base=16, depth=4)` and reads the frozen protocol from `runs/validation_protocol_candidate_seed42/protocol.json`.
- The verified run manifest records 678,707 trainable parameters, input `(batch, 3, 3072)`, best epoch 11, protocol `protocol-5fa5744aca58cc3c`, P threshold 0.05, S threshold 0.10, and tolerance 20 samples.
- The saved dataset pipeline documents ENZ input order. `CSVProcessor` currently performs its own demeaning, peak normalization, model call, softmax, and pick extraction instead of delegating to one engine method.
- When the optional raw sample is absent, trace browsing uses the tracked deterministic demo fixture. This fallback is explicitly labelled and is not a new scientific evaluation.

## 5. Live API inventory before repair

| Method | Path | Observed status | Notes |
|---|---|---|---|
| GET | `/api/health` | VERIFIED | Returned online, CPU, `synthetic_demo_fallback`, real dataset unavailable |
| GET | `/api/traces` | VERIFIED | Returned 210 demo trace records |
| GET | `/api/analyze/{trace_id}` | REGISTERED | Uses demo fallback without raw sample; not browser-verified here |
| GET | `/api/metrics` | VERIFIED | Returned held-out test artifact values |
| POST | `/api/csv/validate` | VERIFIED | Existing JSON body accepted a temporary 3,072-row CSV |
| POST | `/api/csv/analyze` | VERIFIED | Existing JSON body ran actual checkpoint inference on the temporary CSV |

### API contract gaps found

1. The documented/user-required upload contract is multipart file upload, but the existing endpoint implementation accepts a JSON string body and the frontend sends JSON rather than a file part.
2. Vite's proxy target is port 8001 while the active backend is port 8000.
3. Sampling-rate and arrival-coordinate fields are not fully validated or applied.
4. The parser accepts an empty CSV and non-finite values too late, and does not enforce the frozen 3,072-sample input contract before inference.
5. Multiple independent traces are not represented; all rows are treated as one waveform.
6. The current response does not include waveform samples, so the CSV page cannot render a backend-result waveform chart.

## 6. Page and interaction baseline

| Area | Current status | Evidence / gap |
|---|---|---|
| Overview | PARTIAL | Renders, but its two hero buttons have no handlers and it does not load verified health/metrics state. |
| Phase Picker | PARTIAL | API flow exists; empty/error states and zero-valued picks are fragile; source/inference mode should be more explicit. |
| CSV Upload | PARTIAL/BROKEN CONTRACT | Initial upload JSX exists, but API target/proxy mismatch and JSON-only contract are inconsistent; results lack plots. |
| Model Evaluation | PARTIAL | Loads metrics, but no visible loading/error retry distinction and values are not consistently formatted to three decimals. |
| About Project | PARTIAL | Static inline content exists but does not cover the actual limitations and upload workflow fully. |
| Sidebar | VERIFIED IN SOURCE | Local page switching works; no URL routing or deep-link behavior. |
| Logo/home | NOT FUNCTIONAL | Logo is decorative and has no click handler. |
| Profile/status icon | STATIC | No action is attached; should remain clearly non-interactive or be removed as a control. |

The full action inventory and verification matrix is maintained in `docs/SEISMONET_UI_ACTION_INVENTORY.md`.

## 7. Frozen artifact and isolation checks

- Checkpoint exists at `runs/experiment_002_p_training/best.pt`.
- Checkpoint SHA-256 recorded before repair: `180FEE49F68FEAAA19C7FF7E1F561D5F63FDA7E41E16EE684B2B61BC367358B4`.
- `runs/experiment_002_p_training/run.json` records `test_split_loaded: false` and `test_split_used: false` for training.
- `splits/split.json` contains the project split id `aea671c76ce2`; its SHA-256 before repair was `D435841A64436D6E4F0FAD9E085F6EF438E33D7115472BD35A6DD6730D8FF1B8`.
- No split file, checkpoint, or experiment artifact is to be modified by the web repair.
- The test metrics artifact is read-only presentation data; no test waveform access is needed for this repair.

## 8. Minimal repair order

1. Make the API base/proxy consistent and remove port ambiguity.
2. Make CSV upload endpoints accept multipart files, enforce size/row/shape/finite/rate/label rules, and preserve a small JSON compatibility path only if it does not weaken validation.
3. Reuse the frozen inference engine and correct the ENZ channel order; keep protocol thresholds server-owned.
4. Return normalized waveform data and effective sampling-rate/protocol metadata for charting.
5. Rewrite the CSV page around explicit upload → mapping → validation → analysis → results states, including inline failures, retry/reset, preview, plots, and safe export.
6. Repair global navigation/hero actions and harden Phase Picker and Evaluation loading/error states.
7. Add focused backend/API regression tests without touching held-out split files.
8. Run the Python suite, frontend build, live multipart E2E smoke test, checkpoint/split hashes, and documentation updates.

## 9. Repair verification result

### COMPLETED / VERIFIED

- Frontend API base is relative `/api`; Vite proxy target is `127.0.0.1:8000`; live proxy health request returned 200.
- CSV routes accept multipart uploads and remain compatible with the prior JSON body path.
- The repository `test_waveform.csv` fixture (3,072 rows, `sample_index,E,N,Z`) returned `is_valid: true` with detected E/N/Z mapping and preview rows.
- Multipart prediction invoked the loaded frozen checkpoint and returned one prediction, normalized ENZ waveform arrays, and 3,072-sample P/S probability curves.
- Multipart comparison returned predicted/reference residuals and metrics scoped to the uploaded labeled file.
- Invalid component, non-finite, short, invalid-rate, wrong-extension, and compare-without-label cases returned readable failures.
- Overview hero actions, global navigation, About page, Phase Picker retry/error states, Evaluation retry/error states, CSV reset/retry/export paths, and chart marker rendering are implemented and included in the production build.
- `.venv\Scripts\python.exe -m pytest tests -q -rs` returned **190 passed, 36 skipped**.
- `npm run build` returned success; only the existing Recharts bundle-size warning remains.
- Backend compilation returned success.
- Checkpoint SHA-256 remained `180FEE49F68FEAAA19C7FF7E1F561D5F63FDA7E41E16EE684B2B61BC367358B4` after repair.
- `splits/split.json` SHA-256 remained `D435841A64436D6E4F0FAD9E085F6EF438E33D7115472BD35A6DD6730D8FF1B8` after repair; no split file was changed.

### NOT VERIFIED / BLOCKED

- Interactive browser click, drag/drop, browser console, and pixel-level blank-page inspection were not run because the available browser-control display could not be opened.
- The exact filename `seismonet_test_waveform_synthetic.csv` was not present; prediction E2E used the repository `test_waveform.csv`, while comparison used a temporary labeled derivative outside the repository.
- Real HDF5-backed trace browsing remains blocked by the absent ignored raw sample. The API labels the deterministic fallback and does not present it as a scientific evaluation.

## 10. Addendum — browser verification completed (2026-10-25, entry `2026-10-25-003`)

Section 9 was written before a control channel to a real browser was available. That gap is now
closed. A headless Chrome session (`playwright-core`, run from a scratch directory outside the
repository) executed 14 scripted steps against the running application — twice: once against the
Vite dev server and once against `vite preview` serving `dist/`.

Result: **14/14 steps passed in both runs, with 0 console errors, 0 uncaught page errors, 0 failed
requests, and 0 HTTP ≥ 400 responses.** Screenshots and the machine-readable report are committed at
`docs/screenshots/browser-2026-10-25/`.

Superseded statements from section 9:

| Section 9 statement | Now |
|---|---|
| Interactive browser click / console / pixel inspection not run | **VERIFIED** for all five pages and the CSV flow; evidence filed |
| Error boundary behaviour unknown | **VERIFIED absent** in every traversed state |
| Browser Back navigation unverified | **VERIFIED** — Back restored the previously visited page |
| JSON export unverified | **VERIFIED** — a real download event was captured from the results view |
| Bundle-size warning open | **CLOSED** — output split into `index` 113.88 kB, `react` 144.23 kB, `charts-recharts` 299.09 kB, `charts-d3` 83.64 kB; build emits no warning |

Still open, unchanged: real HDF5-backed trace browsing (absent raw sample), the missing exact fixture
name `seismonet_test_waveform_synthetic.csv` (the repository fixture was used instead),
drag-and-drop `drop` events, and Firefox/Safari or small-viewport behaviour.

The checkpoint SHA-256 (`180FEE49F68FEAAA19C7FF7E1F561D5F63FDA7E41E16EE684B2B61BC367358B4`) and
`splits/split.json` SHA-256 (`D435841A64436D6E4F0FAD9E085F6EF438E33D7115472BD35A6DD6730D8FF1B8`)
were re-checked after this work and are unchanged.

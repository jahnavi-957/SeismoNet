# 2026-10-25-001 — Web demo repair and local fallback

## A. Change identification
- Change ID: `2026-10-25-001`
- Date and time: 2026-10-25
- Short title: Web demo repair and local fallback
- Category: bug fix | feature | documentation | configuration
- Files created / modified:
  - Created `frontend/src/index.css`, `backend/demo_traces.json`
  - Created `frontend/package-lock.json` via `npm install`
  - Modified `backend/inference.py`, `backend/main.py`
  - Modified `frontend/src/App.tsx`, `frontend/src/components/WaveformPlot.tsx`, `frontend/src/pages/PhasePicker.tsx`, `frontend/src/pages/ModelEvaluation.tsx`, `frontend/src/types/index.ts`, `frontend/index.html`, `frontend/postcss.config.js`
  - Modified `.gitignore`, `pyproject.toml`, `requirements.lock`, `README.md`, `docs/PROJECT_STATUS.md`, `docs/change-log/CURRENT_STATUS.md`, `docs/change-log/CHANGELOG.md`

## B. What was changed?
The browser application did not build or provide a usable trace-analysis flow in the current
checkout. The frontend had a missing stylesheet, incorrect page imports, an untyped chart data
array, and a CommonJS PostCSS configuration under an ES-module package. The backend also failed at
`GET /api/traces` because the ignored local HDF5/CSV sample was not present at the historical temp
path.

The frontend now builds with local Tailwind/PostCSS styles. The backend now reads the tracked
held-out metrics artifact and exposes the current test results. When the raw dataset is absent, it
serves deterministic, clearly-labelled synthetic demo traces derived from a bundled fixture or local
validation prediction metadata. If the real HDF5 and metadata files are restored, the existing model
inference path is used automatically.

## C. Why was this change necessary?
The requested user-facing result was a running backend and frontend that could be opened and tested.
The first reproductions showed:

- `npm run build` failed because `tsc` was not installed and, after dependency installation, TypeScript and PostCSS errors remained.
- Direct backend trace loading failed with `FileNotFoundError` for `metadata_Instance_events_10k.csv`.
- The raw dataset is intentionally ignored by the repository, so a clean or transferred checkout
  cannot assume that artifact exists; a small bundled fixture was added for that case.

## D. Why was this approach chosen?
The frontend issues were repaired with the smallest source changes rather than replacing the React
stack. The dataset fallback is intentionally not a fabricated scientific result: it is a local demo
mode marked in API responses as `synthetic_demo_fallback`. This preserves testability of the UI while
keeping real model inference available when the documented dataset files exist.

The metrics endpoint reads `runs/eval_test_best/metrics.json` instead of duplicating stale validation
numbers in code, so the dashboard reflects the repository's current held-out evaluation artifact.

## E. How was it implemented?
- Installed frontend dependencies with `npm install`, producing the frontend lockfile.
- Added the missing global stylesheet and Tailwind directives; removed the remote Tailwind runtime dependency.
- Corrected default page imports, the `WaveformPlot` import path, and the chart series type.
- Converted `postcss.config.js` to ESM syntax.
- Added dataset availability detection and a deterministic synthetic waveform/probability fallback in `SeismoInferenceEngine`, backed by `backend/demo_traces.json` when ignored run artifacts are unavailable.
- Added API health metadata for the active data source and loaded held-out test metrics.
- Added web dependency declarations and ignored `frontend/node_modules/`.
- Updated README and status/change-log documents to describe the actual running state and dataset limitation.

## F. How did this improve SeismoNet?
- **VERIFIED improvement:** `npm run build` completes successfully and produces `frontend/dist/`.
- **VERIFIED improvement:** the API serves 210 traces when local run metadata exists, and a minimal bundled fixture remains available when it does not; both paths return an analysis response, health metadata, and current test metrics without the raw dataset.
- **VERIFIED improvement:** the frontend dev server responds successfully on port 5173 and its source modules are served by Vite.
- **EXPECTED improvement:** restoring the documented raw files will switch the backend from fallback mode to real dataset inference without a frontend change.
- **No accuracy claim:** synthetic fallback responses are only for interface testing and are not a new evaluation result.

## G. Testing and verification
- Tests added or modified: none; existing unit/integration tests were preserved.
- Commands executed:
  - `.venv\Scripts\python.exe -m pytest tests -q -rs` → `183 passed, 36 skipped`.
  - `npm install` in `frontend/` → completed.
  - `npm run build` in `frontend/` → passed; Vite emitted only a bundle-size warning.
  - Direct engine smoke → 210 traces returned; first demo analysis returned a 3072-sample response with P/S picks.
  - Running API smoke checks → `/api/health`, `/api/traces`, `/api/analyze/{trace_id}` and `/api/metrics` returned successfully.
  - Frontend smoke checks → `http://127.0.0.1:5173` and Vite source modules returned HTTP 200.
- Tests failed: none after the repairs.
- Tests not run: no interactive browser screenshot was available in this environment; HTTP and Vite module smoke checks were used instead.
- Remaining limitation: 36 Python tests skip because the ignored local INSTANCE HDF5/CSV sample is absent.

## H. Risks and side effects
- The fallback can be mistaken for real seismic inference if the `data_source` label is ignored; the API and documentation explicitly label it.
- The frontend bundle is larger than Vite's 500 kB warning threshold because Recharts is included; this is a performance follow-up, not a functional blocker.
- The change is reversible by restoring the modified files and removing the frontend dependency installation; no raw data or credentials were added.

## I. Relationship to the PRD and roadmap
This change supports `FR-049`–`FR-065` for interactive inference visualisation, `FR-076`–`FR-084`
for result display and reproducibility, and the optional interface requirements `FR-079`–`FR-081`.
It is an implementation hardening change for the local demonstration layer; it does not change model
weights, the evaluation protocol, split files, or reported scientific results.

## J. Next steps
- Restore the documented local HDF5/CSV sample if real interactive dataset inference is required.
- Consider code-splitting the Recharts bundle if the browser demo becomes a performance concern.
- Keep the synthetic fallback labelled and separate from scientific evaluation artifacts.

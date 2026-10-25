# 2026-10-25-002 — Integrated web repair and CSV inference contract

## A. Change identification

- Change ID: `2026-10-25-002`
- Date: 2026-10-25
- Short title: Integrated web repair and CSV inference contract
- Category: bug fix | feature | testing | documentation
- Files created: `frontend/src/components/ErrorBoundary.tsx`, `frontend/src/components/CSVResultPlot.tsx`, `frontend/src/pages/AboutProject.tsx`, `frontend/src/vite-env.d.ts`, `docs/SEISMONET_DEVELOPMENT_GUIDE.md`, `docs/SEISMONET_UI_ACTION_INVENTORY.md`, `tests/test_csv_processor.py`, `tests/test_api_csv.py`
- Files modified: `backend/main.py`, `backend/csv_processor.py`, `backend/inference.py`, `frontend/vite.config.ts`, `frontend/src/App.tsx`, `frontend/src/services/api.ts`, `frontend/src/types/index.ts`, `frontend/src/pages/Overview.tsx`, `frontend/src/pages/PhasePicker.tsx`, `frontend/src/pages/CSVUpload.tsx`, `frontend/src/pages/ModelEvaluation.tsx`, `frontend/src/components/WaveformPlot.tsx`, `README.md`, `docs/SEISMONET_PROJECT_AUDIT.md`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`

## B. What was changed?

Unified the browser API path on port 8000, added multipart CSV upload support with a JSON compatibility
path, enforced the supported waveform/label contract, corrected CSV preprocessing to the research
pipeline's ENZ order, and reused the frozen inference engine for predictions. The frontend now has
working navigation actions, an error boundary, explicit upload/mapping/validation/results states,
waveform/probability result plots, comparison residuals, and upload-only metrics.

## C. Why was this change necessary?

The audit found that Vite proxied `/api` to port 8001 while the active FastAPI service was on port
8000, matching the historical `Validation error: Not Found`. The CSV endpoint contract was JSON-string
based rather than a browser file upload, CSV results had no plots, and `CSVProcessor` constructed Z/N/E
while the saved `InstanceDataset` contract is ENZ. The browser-control display was unavailable, so a
pixel-level blank-page reproduction was not possible; source/build evidence and live HTTP checks were
used instead.

## D. Why was this approach chosen?

The existing React/FastAPI architecture was preserved. No database, cloud service, router dependency,
retraining, or second inference implementation was added. The frozen checkpoint and protocol remain the
source of truth, and uploaded data cannot alter experiment artifacts or dataset splits.

## E. How was it implemented?

- Added `SeismoInferenceEngine.infer_waveform()` for one normalized ENZ window and protocol-owned picks.
- Reworked `CSVProcessor` around mapping resolution, finite/rate/length/label checks, optional trace
  grouping, correct rate conversion, and upload-only comparison metrics.
- Reworked the FastAPI CSV handlers to read multipart `file`, `mapping`, and `mode` fields and return
  structured errors.
- Changed the frontend API client to relative `/api` and `FormData`; changed Vite's proxy target to 8000.
- Added focused parser and route-handler tests and verified live multipart prediction/comparison with a
  temporary synthetic CSV outside the repository.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** frontend production build passes.
- **VERIFIED improvement:** multipart validation and analysis return actual frozen-checkpoint output,
  waveform arrays, and 3,072-sample P/S curves for a valid synthetic CSV.
- **VERIFIED improvement:** labeled comparison returns residuals and upload-only metrics.
- **VERIFIED improvement:** invalid/missing-component/non-finite/short/rate-invalid inputs return
  readable failures.
- **EXPECTED improvement:** page-level failures remain visible inside the application shell; browser
  pixel evidence still requires a desktop browser session.

## G. Testing and verification

- `.venv\Scripts\python.exe -m pytest tests -q -rs` → **190 passed, 36 skipped**.
- `npm run build` in `frontend` → **passed**; only the existing Vite bundle-size warning remains.
- `python -m compileall -q backend` → **passed**.
- Live OpenAPI → both CSV routes registered.
- Live health/traces/metrics → 200 responses; checkpoint available; 210 permitted fallback traces.
- Live multipart validate/analyze/compare → 200 responses with actual predictions and metrics.
- Invalid CSV/rate/mode cases → readable 200 validation failures or 400 request errors.
- Vite `/api/health` proxy → 200 through port 5173 to backend port 8000.
- Exact filename `seismonet_test_waveform_synthetic.csv` → **NOT FOUND**; the repository's
  `test_waveform.csv` fixture was used for prediction and a temporary labeled derivative was used for
  comparison.
- Browser console/network/pixel smoke → **NOT RUN / BLOCKED** because browser-control display was unavailable.

## H. Risks and side effects

The frontend bundle remains larger than Vite's advisory threshold because Recharts is bundled. Trace
browsing remains a labelled deterministic fallback when the optional raw sample is absent. The legacy
JSON path increases compatibility surface but uses the same CSV processor validation. No commit or push
was made; rollback is possible by restoring the listed files.

## I. Relationship to the PRD and roadmap

This implements the existing browser upload, visualization, error-handling, reproducibility, and local
demonstration requirements. It does not change model weights, checkpoint, split files, protocol, training
configuration, or scientific results.

## J. Next steps

- If required, run the documented smoke sequence in a desktop browser and record console/network evidence.
- Restore the optional raw HDF5/metadata sample only when real trace browsing is required.
- Consider code-splitting Recharts in a separate performance task.

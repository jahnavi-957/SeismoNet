# SeismoNet Development Guide

This guide describes the verified local development flow for the existing SeismoNet application.
It does not download the dataset, retrain the model, alter split files, or publish the service.

## 1. Prerequisites

Run commands from:

```text
C:\Users\Tanish\dlrl miniproject\SeismoNet
```

The verified environment is the existing `.venv` with Python 3.14.3, PyTorch 2.14.1+cu126, FastAPI,
Uvicorn, and the installed `seismonet` package. The frontend uses the existing `frontend\node_modules`
installation and React/Vite dependencies.

Activate the environment in PowerShell when desired:

```powershell
.venv\Scripts\Activate.ps1
```

The project can also be run with explicit `.venv\Scripts\python.exe` paths without activation.

## 2. Start the backend

Terminal 1, from the project root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Verified endpoints:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`
- Health: `http://127.0.0.1:8000/api/health`

The health response reports whether the frozen checkpoint is available, the active data source, the
3,072-sample window length, and protocol id. In the current checkout the optional raw HDF5/metadata
sample is absent, so trace browsing reports `synthetic_demo_fallback`. The checkpoint itself is
present and is used for uploaded CSV inference.

## 3. Start the frontend

Terminal 2:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

The Axios client uses the relative `/api` base by default. Vite proxies `/api` to
`http://127.0.0.1:8000`; do not use port 8001. If port 5173 is busy, Vite may choose another port;
the displayed frontend URL remains the source of truth. For an externally hosted API, set
`VITE_API_BASE_URL` before starting Vite.

## 4. CSV workflow

The CSV page performs this sequence:

1. Select or drop a `.csv` file.
2. Backend auto-detects columns and returns a preview.
3. Confirm E/N/Z, optional trace id, coordinate, and reference columns.
4. Enter the input sampling rate.
5. Validate the mapping and frozen window contract.
6. Choose prediction or comparison mode.
7. Run the actual Python model, display waveform/probability charts, and optionally calculate upload-only metrics.
8. Export the returned JSON result.

The browser sends multipart form data:

- `POST /api/csv/validate`: file field `file`, optional JSON field `mapping`.
- `POST /api/csv/analyze`: file field `file`, JSON field `mapping`, and `mode=predict|compare`.

The old JSON body contract remains accepted for local scripts, but new frontend code should use
multipart upload.

### Supported input

Prediction example:

```csv
sample_index,E,N,Z
0,0.124,-0.032,0.078
1,0.130,-0.029,0.075
```

Comparison example:

```csv
sample_index,E,N,Z,p_arrival_sample,s_arrival_sample
0,0.124,-0.032,0.078,1200,2450
1,0.130,-0.029,0.075,1200,2450
```

The frozen model consumes an ENZ `(3, 3072)` window at an effective 100 Hz. A different positive
input rate is accepted only when resampling produces exactly 3,072 samples; reference coordinates
are converted during that operation and the response reports the effective rate. A file with
multiple independent traces must provide a mapped `trace_id` column. Missing reference arrivals are
allowed for the corresponding phase; invalid, non-finite, inconsistent, or out-of-range labels
are rejected.

Uploaded data is held in the request path and is not added to `splits/`, training data, evaluation
artifacts, or third-party services. The repository fixture `test_waveform.csv` contains 3,072 rows
with `sample_index,E,N,Z` and is suitable for the software pipeline demo. The exact filename
`seismonet_test_waveform_synthetic.csv` is not present in this checkout. Any synthetic waveform
result is a software pipeline test and not a scientific seismic evaluation.

## 5. Checks

Run the focused web tests:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_csv_processor.py tests\test_api_csv.py -q -rs
```

Run the complete Python suite:

```powershell
.venv\Scripts\python.exe -m pytest tests -q -rs
```

The verified repair result is **190 passed, 36 skipped**. The skips require the ignored local
INSTANCE HDF5/metadata sample and do not represent web failures.

Build the frontend:

```powershell
cd frontend
npm run build
```

The build passes. Vite still reports a bundle-size warning because Recharts is included in the
single browser bundle; this is a performance follow-up, not a functional failure.

## 6. Smoke checks

With both services running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/traces
Invoke-RestMethod http://127.0.0.1:8000/api/metrics
Invoke-WebRequest http://127.0.0.1:5173/csv-upload -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:5173/api/health -UseBasicParsing
```

For multipart CSV checks, use Python `requests` or the browser page. The verified repair smoke test
used the repository `test_waveform.csv` fixture for prediction and a temporary labeled derivative for
comparison, confirming validation, actual checkpoint inference, waveform/probability response arrays,
comparison mode, invalid-input errors, and Vite proxying.

## 7. Stop local services

Only stop the PIDs that own the local demo ports:

```powershell
Get-NetTCPConnection -LocalPort 8000,5173 | Select-Object LocalPort,OwningProcess,State
Stop-Process -Id <backend-pid> -Force
Stop-Process -Id <frontend-pid> -Force
```

Do not kill unrelated Python or Node processes.

## 8. Troubleshooting

| Symptom | Check |
|---|---|
| `Validation error: Not Found` | Confirm the browser is using `/api` through Vite and that the backend is on port 8000. Port 8001 is not the configured API. |
| Frontend loads but API status is offline | Open `/api/health` on port 8000, then restart Vite so its proxy configuration is re-read. |
| CSV page shows an inline validation error | Read the reported mapping, rate, row-count, finite-value, or window-length reason; do not bypass validation. |
| Trace list is empty | Check `/api/health`; the raw optional sample may be absent. The tracked demo fixture should still provide permitted fallback traces. |
| Model cannot load | Confirm `runs/experiment_002_p_training/best.pt` exists and has not been replaced. Do not retrain automatically. |
| Browser route reload fails in a custom static host | Configure that host to serve `frontend/index.html` for `/`, `/picker`, `/csv-upload`, `/evaluation`, and `/about`. |

## 9. Integrity rules

- Do not modify `splits/*.csv` or `splits/split.json` for UI work.
- Do not tune thresholds on user uploads or test data.
- Do not overwrite `runs/` artifacts or the frozen checkpoint.
- Do not claim a synthetic CSV result is scientific evaluation.
- Keep the backend local; this project has no authentication or public deployment boundary.

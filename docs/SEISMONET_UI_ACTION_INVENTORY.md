# SeismoNet UI Action Inventory

This inventory maps visible controls to their handlers and evidence. **VERIFIED** means the source,
build, and relevant local request path were checked. **NOT VERIFIED** means interactive browser
click evidence was unavailable in this Windows CLI session; it is not a claim that the source path
is broken.

## Global shell

| Control | Intended action | Implementation | Status |
|---|---|---|---|
| SeismoNet logo | Return to Overview and update browser history | `App.navigate('overview')` | VERIFIED in source/build and by browser click |
| Overview | Show project entry point | `App.navigate('overview')` | VERIFIED in source/build |
| Phase Picker | Open permitted trace analysis | `App.navigate('picker')` | VERIFIED in source/build |
| CSV Upload | Open upload workflow | `App.navigate('csv-upload')` | VERIFIED in source/build |
| Model Evaluation | Open saved metrics page | `App.navigate('evaluation')` | VERIFIED in source/build |
| About Project | Open scope/limitations page | `App.navigate('about')` | VERIFIED in source/build |
| Sidebar toggle | Collapse/expand navigation | `setIsSidebarOpen` | VERIFIED in source/build |
| Backend status pill | Report health state; not a fake control | `seismoService.checkHealth()` | VERIFIED by live `/api/health` request |
| Profile/status icon | Informational only | No click handler | VERIFIED as non-interactive |

## Overview

| Control | Intended action | Implementation | Status |
|---|---|---|---|
| Open Phase Picker | Navigate to picker | `onNavigate('picker')` | VERIFIED in source/build |
| Analyze a CSV | Navigate to upload | `onNavigate('csv-upload')` | VERIFIED in source/build |
| View evaluation | Navigate to evaluation | `onNavigate('evaluation')` | VERIFIED in source/build |
| Metric cards | Display saved `/api/metrics` values | `seismoService.getMetrics()` | VERIFIED by live metrics response |
| Evaluation error state | Keep page visible and show failure | Inline error state | VERIFIED in source/build |

## Phase Picker

| Control | Intended action | Implementation | Status |
|---|---|---|---|
| Trace selector | Select one permitted trace | `setSelectedTrace` | VERIFIED in source/build; live trace list returned 210 records |
| Run analysis | Call `/api/analyze/{trace_id}` | `seismoService.analyzeTrace` | VERIFIED route registration and source; live demo fallback route is available |
| Reset view | Clear result/error without losing trace list | `setResult(null)` / `setError(null)` | VERIFIED in source/build |
| Retry | Reload trace metadata after failure | `loadTraces()` | VERIFIED in source/build |
| Waveform charts | Show E/N/Z waveform and probability curves | `WaveformPlot` + Recharts | VERIFIED in source/build and by browser rendering |
| Pick markers | Show predicted/reference P/S markers | Recharts `ReferenceLine` | VERIFIED in source/build |

## CSV Upload

| Control | Intended action | Implementation | Status |
|---|---|---|---|
| Choose file | Open `.csv` file picker | hidden input via `inputRef` | VERIFIED in source/build; browser file input exercised in E2E |
| Drag/drop zone | Accept one dropped CSV | `handleFile` | VERIFIED in source/build; browser drag/drop NOT VERIFIED |
| File extension/size guard | Reject unsupported or oversized files | client guard plus backend guard | VERIFIED in source/build |
| Auto-detect | Parse headers/preview/mapping | `POST /api/csv/validate` multipart | VERIFIED by live multipart request |
| E/N/Z selectors | Choose waveform columns | `updateMapping` | VERIFIED in source/build |
| Trace ID selector | Identify grouped traces | `updateMapping('trace_id_col')` | VERIFIED in source/build and backend parser |
| Coordinate selector | Choose sample index or seconds | `arrival_coordinate_type` | VERIFIED by backend unit test |
| Sampling-rate input | Provide input rate | `sampling_rate_hz` | VERIFIED by backend validation tests |
| P/S reference selectors | Enable comparison labels | `p_arrival_col` / `s_arrival_col` | VERIFIED by labeled multipart test |
| Validate CSV | Re-run backend validation after mapping | `seismoService.validateCSV` | VERIFIED by live multipart request |
| Prediction mode | Run inference without reference metrics | `mode='predict'` | VERIFIED by live analysis; actual model returned one prediction |
| Comparison mode | Compare valid uploaded references | `mode='compare'` | VERIFIED by live labeled analysis and backend test |
| Run real model analysis | Call `/api/csv/analyze` | `seismoService.analyzeCSV` | VERIFIED by live multipart request; frozen checkpoint was invoked |
| Retry analysis | Repeat failed request without blanking page | `runAnalysis()` | VERIFIED in source/build |
| Result trace selector | Switch chart/table among grouped predictions | `selectedIndex` | VERIFIED in source/build |
| Export JSON | Download returned response | Blob URL and anchor download | VERIFIED in source/build and by captured browser download |
| New file / Start over | Clear all upload state | `reset()` | VERIFIED in source/build |
| Result plots | Display normalized E/N/Z and P/S curves | `CSVResultPlot` | VERIFIED in source/build and by browser rendering |

## Model Evaluation

| Control | Intended action | Implementation | Status |
|---|---|---|---|
| Retry | Reload saved metrics artifact | `loadMetrics()` | VERIFIED in source/build |
| P/S metric charts | Display precision/recall/F1 without calling it accuracy | Recharts | VERIFIED by live metrics response and source |
| Protocol panel | Display checkpoint protocol, thresholds, tolerance, rate | `/api/metrics` response | VERIFIED by live response |

## About Project

| Control | Intended action | Implementation | Status |
|---|---|---|---|
| About content | Explain objective, method, data, upload flow, and limitations | `AboutProject.tsx` | VERIFIED in source/build |

## Live request evidence

The repair session verified:

- `GET /api/health` → 200, checkpoint available, backend online.
- `GET /api/traces` → 200, 210 permitted demo records.
- `GET /api/metrics` → 200, saved held-out test artifact values.
- `POST /api/csv/validate` multipart → 200, valid 3,072-row synthetic CSV.
- `POST /api/csv/analyze` multipart prediction → 200, actual model output, waveform arrays, and P/S probability curves.
- `POST /api/csv/analyze` multipart comparison → 200, residuals and upload-only metrics.
- Invalid/missing-component/non-finite/short/rate-invalid CSV cases → readable validation failures.
- Vite `/api/health` proxy → 200 through port 5173 to backend port 8000.

## Browser evidence (2026-10-25, entry `2026-10-25-003`)

A headless Chrome session (`playwright-core` run from a scratch directory outside the repository) executed
14 scripted steps against the running application, twice: against the Vite dev server and against
`vite preview` serving `dist/`.

- **14/14 steps passed in both runs**, with 0 console errors, 0 uncaught page errors, 0 failed requests,
  and 0 HTTP ≥ 400 responses.
- Screenshots: `docs/screenshots/browser-2026-10-25/01-overview.png`, `02-picker-analysis.png`,
  `03-csv-mapping.png`, `04-csv-results.png`, `05-evaluation.png`; machine-readable trace in
  `smoke-report.json`.
- Clicks exercised: hero buttons, all five sidebar destinations, sidebar logo, **Reset view**,
  **Run analysis** (Phase Picker), **Choose file** → **Validate CSV** → **Run real model analysis**,
  **Export JSON** (real download captured), and browser **Back**.
- Still unverified: drag-and-drop `drop` events (the file-input path was exercised instead),
  Firefox/Safari rendering, and small mobile viewports.

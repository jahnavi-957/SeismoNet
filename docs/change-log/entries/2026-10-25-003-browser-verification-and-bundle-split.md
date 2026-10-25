# 2026-10-25-003 — Browser end-to-end verification and bundle split

## A. Change identification

- Change ID: `2026-10-25-003`
- Date: 2026-10-25
- Short title: Browser end-to-end verification and bundle split
- Category: testing | performance | documentation
- Files created: `docs/screenshots/browser-2026-10-25/{01-overview,02-picker-analysis,03-csv-mapping,04-csv-results,05-evaluation}.png`, `docs/screenshots/browser-2026-10-25/smoke-report.json`, this entry
- Files modified: `frontend/vite.config.ts`, `docs/change-log/CURRENT_STATUS.md`, `docs/change-log/CHANGELOG.md`, `docs/SEISMONET_PROJECT_AUDIT.md`, `docs/SEISMONET_UI_ACTION_INVENTORY.md`

## B. What was changed?

The two items that entries `2026-10-25-001` and `2026-10-25-002` left open were closed:

1. **Browser evidence now exists.** A headless Chrome session drove the real application through
   all five pages, the Phase Picker analysis flow, the full CSV upload → mapping → validation →
   analysis → results → export flow, and browser Back navigation. Both the Vite dev server and the
   production build (`vite preview`) were exercised; both returned the same result.
2. **The single 640.88 kB JavaScript chunk was split.** `frontend/vite.config.ts` now assigns three
   dependency families to explicit chunks (`react`, `charts-recharts`, `charts-d3`). No application
   source file, no component, and no chart behaviour changed.

## C. Why was this change necessary?

`2026-10-25-002` recorded "browser console/network/pixel smoke → **NOT RUN / BLOCKED**", and the
audit carried the same limitation. A source-and-HTTP-only check cannot prove that a page renders,
that charts mount, or that a file input actually reaches the backend. The advisory bundle-size
warning was likewise carried as a known follow-up in both previous entries.

## D. Why was this approach chosen?

`playwright-core` was installed in a scratch directory outside the repository and driven against the
already-running local services, so the project gained evidence without gaining a heavyweight browser
test dependency, a new npm script, or any change to the shipped application. Vite's
`manualChunks` function was used without a catch-all bucket: an earlier attempt with a generic
`vendor` bucket produced `Circular chunk: charts -> vendor -> charts`, so the final configuration
maps only the three known families and lets Rollup place everything else.

## E. How was it implemented?

- Launched Chrome (`channel: 'chrome'`, headless, 1500×950 viewport) via `playwright-core` from a
  temporary directory; collected `console`, `pageerror`, `requestfailed`, and HTTP ≥ 400 events for
  the whole session.
- Recorded 14 named steps with pass/fail and duration; captured a full-page screenshot and DOM
  metrics (text length, `<svg>` count, scroll height) at each page state.
- Uploaded the tracked fixture `test_waveform.csv` through the real `<input type="file">`, clicked
  **Validate CSV**, clicked **Run real model analysis**, and captured the returned download from
  **Export JSON**.
- Asserted the absence of the error-boundary screen and that browser **Back** restored the previously
  visited page.
- Replaced the single-chunk build with explicit `manualChunks` groups in `frontend/vite.config.ts`.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** 14/14 scripted browser steps passed against the dev server and again
  against the production build, with **0 console errors, 0 uncaught page errors, 0 failed requests,
  and 0 HTTP ≥ 400 responses**.
- **VERIFIED improvement:** the Overview page renders the real held-out artifact values
  (P F1 `0.685`, S F1 `0.499`, 1,472 traces) with no console noise.
- **VERIFIED improvement:** the CSV upload reaches the backend through the browser, the frozen
  checkpoint runs, and three normalised waveform charts plus the P/S probability panel render.
- **VERIFIED improvement:** the JSON export produces a real download from the results view.
- **VERIFIED improvement:** no JavaScript chunk exceeds Vite's 500 kB advisory threshold, and the
  build emits no chunk warning. The initial payload drops from one 640.88 kB file to a 113.88 kB
  entry chunk plus cacheable dependency chunks.

## G. Testing and verification

- `.venv\Scripts\python.exe -m pytest tests -q -rs` → **190 passed, 36 skipped** (re-run this session).
- `npm run build` → **passed, no warnings**; chunks: `index` 113.88 kB, `react` 144.23 kB,
  `charts-recharts` 299.09 kB, `charts-d3` 83.64 kB, CSS 21.33 kB.
- Browser run against `http://127.0.0.1:5177` (dev) → **14/14 steps passed**.
- Browser run against `http://127.0.0.1:4178` (`vite preview` of `dist/`) → **14/14 steps passed**.
- Deep link `GET /picker` on the preview server → 200 (SPA fallback works).
- `GET /api/health` through the preview proxy → 200, `synthetic_demo_fallback`.
- Checkpoint SHA-256 after this work → `180FEE49F68FEAAA19C7FF7E1F561D5F63FDA7E41E16EE684B2B61BC367358B4` (unchanged).
- `splits/split.json` SHA-256 after this work → `D435841A64436D6E4F0FAD9E085F6EF438E33D7115472BD35A6DD6730D8FF1B8` (unchanged).
- Not run: Firefox/WebKit engines, mobile viewports, drag-and-drop `drop` events (the file input path
  was exercised instead), and real dataset-backed trace browsing (still blocked by the absent raw sample).

Two observations recorded rather than hidden:

- The Phase Picker reported **Residual: 0 samples** for both phases. This is correct for the labelled
  deterministic demo fallback — the same fixture supplies trace and reference arrivals — and the
  panel prints `Source: synthetic_demo_fallback` / `Mode: synthetic_demo` beside it. It is not model
  accuracy.
- The CSV fixture `test_waveform.csv` returned **S pick 2613 (p = 0.432)** and **no P pick**, because
  no interior P peak in that fixture reaches the frozen `0.05` threshold. The UI states this
  explicitly instead of inventing a pick.

## H. Risks and side effects

The evidence screenshots add ~600 kB of binary files under `docs/`; they are documentation artifacts,
not scientific results, and are not read by any code or test. The chunk split changes asset filenames
only, so any previously bookmarked `dist/assets/*` URL is invalidated — normal for a rebuild. Chrome
was used for verification; Safari/Firefox behaviour remains unverified.

## I. Relationship to the PRD and roadmap

This closes the browser-visualisation verification gap attached to `FR-049`–`FR-065` and
`FR-076`–`FR-084`, and the performance follow-up noted in `2026-10-25-001`. Model weights,
checkpoint, split files, protocol, training configuration, and reported scientific results are
unchanged.

## J. Next steps

- Restore the optional local INSTANCE HDF5/metadata sample if real dataset-backed trace browsing is
  required; this remains the only functional limitation.
- Consider Firefox/Safari coverage and a small-viewport pass if the demo is presented on other browsers.
- Commit the outstanding working tree (the repository still has only its four documentation commits).

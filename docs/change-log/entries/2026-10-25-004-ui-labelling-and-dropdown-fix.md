# 2026-10-25-004 — Readable dropdowns and explicit demo/held-out labelling

## A. Change identification

- Change ID: `2026-10-25-004`
- Date: 2026-10-25
- Short title: Readable dropdowns and explicit demo/held-out labelling
- Category: bug fix | documentation
- Files modified: `frontend/src/index.css`, `frontend/src/pages/PhasePicker.tsx`, `frontend/src/pages/ModelEvaluation.tsx`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`, this entry

## B. What was changed?

Three presentation fixes, no inference or artefact change:

1. **Native dropdowns are readable again.** The trace selector and the CSV column-mapping selects rendered their popup list with a white background while the option text stayed white, so the list appeared blank. Popups now have an explicit dark background and light text.
2. **The Phase Picker states that it is a demonstration.** When the backend reports `synthetic_demo_fallback` (i.e. no raw dataset in the checkout), the page shows an amber banner saying the picks and probability curves are constructed at the reference arrivals and that the model is not running there, pointing the reader at CSV Upload for real inference.
3. **The Model Evaluation page is labelled for what it is.** A badge under the title reads *"Held-out test set · not from your upload"*.

## C. Why was this change necessary?

- The dropdown defect was reported by the project owner: text was invisible against the popup background, which made the 210-entry trace list unusable and the CSV mapping selects hard to read.
- The Phase Picker's residual reads `0 samples` in fallback mode because the demo path plants wavelets at the reference arrivals and builds probability curves centred on them; it never invokes the model. Beside a held-out `P F1 0.685` on the evaluation page, that invites the reading that the model is perfect on traces and mediocre on test. The label existed only as a small `Source` / `Mode` line in the results panel.
- The evaluation page's numbers are read from `runs/eval_test_best/metrics.json` and are unrelated to any upload; the existing disclaimer was a small grey paragraph at the bottom of the page.

## D. Why this approach was chosen?

CSS rules on `option`/`optgroup` plus `color-scheme: dark` fix the popup for every select in the application without a component rewrite or a combobox dependency. The banner is driven by the `data_source` field already returned by `/api/traces` and `/api/analyze/{id}`, so no API or schema change was needed, and the banner disappears automatically on a checkout where the raw dataset is present. The badge is presentational only.

## E. How was it implemented?

- `index.css`: `select { color-scheme: dark }`; `option, optgroup { background-color: #0f172a; color: #e2e8f0 }`; `option:checked, option:hover` highlighted; `option:disabled` muted.
- `PhasePicker.tsx`: the trace select no longer uses `bg-transparent` (Chrome derives the popup from the select's own background, so transparent produced a white list); it now uses `bg-slate-900` with padding. Added `isDemoFallback`, computed from `result?.data_source ?? traces[0]?.data_source`, and an amber banner rendered above the trace cards.
- `ModelEvaluation.tsx`: added a badge inside the header block, beneath the existing subtitle.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** the popup list is legible — computed styles in Chrome are `option` background `rgb(15, 23, 42)`, text `rgb(226, 232, 240)`, `color-scheme: dark`, on both the trace selector and the CSV mapping selects.
- **VERIFIED improvement:** the Phase Picker banner is visible before and after running analysis, and names the reason (absent raw dataset) and the remedy (CSV Upload).
- **VERIFIED improvement:** the evaluation badge is visible directly under the page title.
- **No change** to the model, checkpoint, thresholds, splits, or any reported metric.

## G. Testing and verification

- `npm run build` → **passed, no bundle-size warning** (chunks unchanged: index 115.00 kB, react 144.23 kB, charts-recharts 299.09 kB, charts-d3 83.64 kB).
- Browser smoke (headless Chrome, dev server) → **14/14 steps passed, 0 console errors, 0 uncaught page errors, 0 failed requests, 0 HTTP ≥ 400**.
- Banner and badge presence asserted in the live DOM; both screenshotted.
- `.venv\Scripts\python.exe -m pytest tests -q` → **190 passed, 36 skipped** (unchanged; no Python code touched).
- Not verified: Safari, which honours `color-scheme` but ignores some `option` background rules; the fallback there is the browser's own dark popup.

## H. Risks and side effects

The `option` styling is global, so every future select inherits it — intended, but worth knowing. The banner appears only when the API reports the synthetic fallback, so a checkout with the raw dataset shows no banner. No behavioural, numerical, or artefact change.

## I. Relationship to the PRD and roadmap

Presentation and honesty-of-display work attached to `FR-076`–`FR-084` (result display and reproducibility). It does not touch model weights, checkpoint, split files, protocol, or scientific results.

## J. Next steps

- Replace the 210-entry native trace selector with a searchable selector (type-to-filter, group by event, mark traces that have an S reference).
- Offer the bundled example CSVs from the upload step so a new user has a working file without hunting for one.

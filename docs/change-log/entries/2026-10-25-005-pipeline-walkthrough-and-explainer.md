# 2026-10-25-005 — Visible processing walk-through and result explainer

## A. Change identification

- Change ID: `2026-10-25-005`
- Date: 2026-10-25
- Short title: Visible processing walk-through and result explainer
- Category: feature | documentation
- Files created: `frontend/src/components/PipelineSimulation.tsx`, `frontend/src/components/ResultExplainer.tsx`, this entry
- Files modified: `frontend/src/pages/CSVUpload.tsx`, `frontend/src/pages/PhasePicker.tsx`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`

## B. What was changed?

Two presentation features, no change to computation:

1. **A visible pipeline walk-through.** Instead of an opaque spinner, running an analysis now shows an ordered, animated list of the operations being performed with a progress bar, then reveals the result. Used by CSV Upload (7 stages) and Phase Picker (6 stages).
2. **A plain-language result explainer** on the CSV results page: what was uploaded, how the file was read, what the model did, a per-trace table of picks with residuals in comparison mode, how to read the numbers, and what the result does **not** mean.

The Phase Picker's walk-through is dataset-aware: when the API reports `synthetic_demo_fallback` it says the curves are *constructed at the reference times*, not inferred; with a real dataset the same stage reads *running the frozen 1D U-Net*.

## C. Why was this change necessary?

The owner asked for the analysis to be legible rather than instantaneous: a viewer could not tell what the system does between "Run analysis" and the charts, and the results page gave numbers without saying what they meant. For a mini-project demonstration, the path from a CSV row to a pick is the substance of the work, and it was invisible.

## D. Why this approach was chosen?

The walk-through is client-side narration of the existing backend order of operations — it adds no endpoint, no polling, and no fabricated data. Stage text is fixed and honest, and the one stage that could mislead (model inference) is switched on the `data_source` the API already returns. A minimum display delay was added so the stages are perceptible when inference finishes quickly on CPU; the real request still runs concurrently and its result is what is shown.

The explainer is built only from values already in the API response (`analysis`, `validation`, `mapping`) so every number on it is traceable to the backend.

## E. How was it implemented?

- `PipelineSimulation.tsx`: typed `PipelineStage[]` prop, 340 ms per stage, tick/spinner/dot states, percentage and progress bar, note that inference runs on CPU.
- `ResultExplainer.tsx`: six numbered sections plus a per-trace table; comparison columns and the upload-metrics block appear only when `mode === 'compare'`.
- `CSVUpload.tsx`: the stage list is asserted only while `busy === 'analyzing'`, replacing the validation panel; the request is raced against a 2.4 s minimum so the sequence is visible; `<ResultExplainer>` renders below the charts on the results step.
- `PhasePicker.tsx`: the waveform card shows the walk-through while `loadingAnalysis` is true, with a 1.9 s minimum; fallback vs model stages are selected from `data_source`.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** the CSV flow shows 7 named stages with a live progress bar, the real file name, row count and trace count.
- **VERIFIED improvement:** the Phase Picker shows 6 stages and switches its wording to the demo path when the raw dataset is absent, consistent with the `2026-10-25-004` banner.
- **VERIFIED improvement:** the results page now explains itself in plain language, including why "no pick" is a result and why upload metrics are not the model's accuracy.
- No change to model, checkpoint, thresholds, splits, or any reported metric.

## G. Testing and verification

- `npm run build` → **passed, no bundle-size warning**; entry chunk 130.66 kB (from 115.00 kB), gzip 39.54 kB.
- Headless-Chrome verification: the picker walk-through is visible mid-run and the result renders afterwards; the CSV walk-through is visible mid-run and the explainer renders with all five narrative sections.
- Comparison mode verified separately with a labelled 6-trace upload: residual columns and the upload-metrics section both render.
- Full browser smoke: **14/14 steps, 0 console errors, 0 uncaught page errors, 0 failed requests, 0 HTTP ≥ 400**.
- `pytest` unchanged at **190 passed, 36 skipped** (no Python touched).

## H. Risks and side effects

The minimum display delay adds ~2 s to each analysis; it does not delay the underlying request and cannot change its result. The stage list is narration, so it must be kept in step with the backend if the pipeline ever changes — the file header says so. The Phase Picker wording is the only place where a stage text depends on backend state.

## I. Relationship to the PRD and roadmap

Presentation of results for `FR-049`–`FR-065` and `FR-076`–`FR-084`, aimed at the local demonstration and review use case. No scientific artefact is affected.

## J. Next steps

- Reuse `ResultExplainer` on the Phase Picker so both analysis pages explain themselves.
- Add a "download example CSV" control on the upload step.

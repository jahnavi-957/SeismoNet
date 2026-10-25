# 2026-10-25-011 — Page through all demo traces with `--offset`

## A. Change identification

- Change ID: `2026-10-25-011`
- Date: 2026-10-25
- Short title: Page through all demo traces with `--offset`
- Category: feature | documentation
- Files modified: `scripts/make_demo_csv.py`, `samples/README.md`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`, this entry

## B. What was changed?

`scripts/make_demo_csv.py` gained `--offset N`, and the selection logic was split into `ordered_traces()`
so that every available demo trace can be reached by slicing a single stable order. The upload limit means
one file holds at most **32 traces** (32 × 3,072 = 98,304 rows, against the 100,000-row cap), so the 210
demo traces are covered by seven files.

## C. Why was this change necessary?

The demo shipped one 12-trace file. A reviewer demonstrating the trace selector asked for larger files, and
there was no way to produce them without duplicating traces: the previous `select_traces()` always started
from the same head of the list, so two invocations with a larger `--traces` value would overlap.

## D. Why this approach was chosen?

The trace list already has a natural order (one trace per event, then the largest events). Exposing it as a
slice keeps the script deterministic, reproduces the existing 12-trace sample exactly at offset 0, and needs no
state on disk. Raising the row limit was rejected: 100,000 rows is a deliberate denial-of-service guard.

## E. How was it implemented?

- `ordered_traces()` returns one trace per event followed by the remaining traces ordered by descending event
  size — the same ordering the old `select_traces()` produced for the first *n*, verified by regenerating
  `samples/demo_12traces_predict.csv` and comparing SHA-256 (identical).
- `main()` slices `ordered_traces()[offset : offset + traces]` and fails with a clear message when the offset
  is past the end.
- `--traces` remains capped at `MAX_TRACES_PER_FILE = 32`.

## F. How did this improve SeismoNet?

- **VERIFIED:** seven generated files cover all **210** demo traces (6 × 32 + 1 × 18).
- **VERIFIED:** every file uploads and analyses: `trace_count` matches the requested count, 209 of 210 traces
  receive both a P and an S pick, one receives P only.
- **VERIFIED:** the UI handles the maximum file — validation reports `98,304 rows · 32 trace`, the results
  selector offers 32 options, and the browser session logs no console errors.
- Measured analysis time: **14–17 s** per 32-trace file on CPU (row parsing dominates, not inference).

## G. Testing and verification

- Regenerated the committed 12-trace sample: **byte-identical** (SHA-256 match).
- Analysed all seven files through `/api/csv/analyze` in predict mode; counts recorded above.
- Headless Chrome on the 32-trace file: selector populated, no console or page errors.
- `pytest` unchanged at **190 passed, 36 skipped** (no library or backend code touched).

## H. Risks and side effects

A 32-trace file is 5.5 MB and sits 1,696 rows below the hard row limit — adding a row to such a file would
push it over. Inference is not the bottleneck; parsing 98k rows is, which is worth knowing before a live demo.

## I. Relationship to the PRD and roadmap

Demonstration ergonomics for `FR-049`–`FR-065`. No model, artefact, or metric changes.

## J. Next steps

- If larger demonstrations are needed, raise `MAX_ROWS` deliberately and document the memory consequence,
  rather than shipping a file that silently fails.

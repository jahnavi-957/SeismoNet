# 2026-10-25-010 — Demo CSV wrote absolute references instead of window-relative ones

## A. Change identification

- Change ID: `2026-10-25-010`
- Date: 2026-10-25
- Short title: Demo CSV wrote absolute references instead of window-relative ones
- Category: bug fix | documentation
- Files modified: `scripts/make_demo_csv.py`, `samples/README.md`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`, this entry

## B. What was changed?

`scripts/make_demo_csv.py --labeled` now writes `p_arrival_sample` / `s_arrival_sample` from the trace's
`reference_relative` values instead of `p_ref` / `s_ref`.

## C. Why was this change necessary?

The comparison page reported residuals of roughly **−6000 ms** on every trace, which looked like a broken
application. It was not: the CSV contract is one 3,072-sample window per trace, and each window is a crop of
the 12,000-sample record, so a reference must be expressed relative to the window.

For `1128071.IV.ASSB..HH` the numbers were unambiguous:

| | value |
|---|---|
| `window_start` | 551 |
| `reference_absolute` | P 1934, S 2240 |
| `reference_relative` | P 1383, S 1689 |
| written by the script | **1934 / 2240** (absolute) |
| predicted | 1326 / 1640 |
| reported residual | **−6080 ms / −6000 ms** |

`1326 − 1934 = −608 samples = −6080 ms`, so almost the entire residual was the window offset (−551 samples)
rather than model error. The trace list exposes `p_ref` / `s_ref` as absolute values, which is a reasonable
thing to put in an API and an easy thing to get wrong in a file written for a window-based contract.

## D. Why this approach was chosen?

The fix belongs in the generator, not the backend: the API comparison is correct, and changing it to guess
which coordinate frame a file uses would make the contract ambiguous. The trace metadata already carries both
frames (`reference_absolute` and `reference_relative`), so the script simply reads the right one.

## E. How was it implemented?

The loop already looks up the trace row through `engine._get_demo_trace`; the labelled branch now reads
`row["reference_relative"]["P"|"S"]` and writes blank cells when a phase has no reference. A comment records
why the absolute value must not be used.

## F. How did this improve SeismoNet?

- **VERIFIED:** residuals drop from ~−6000 ms to the model's actual bias on these synthetic windows,
  **−490 to −720 ms**, consistent across all twelve traces.
- **VERIFIED:** the generator still produces a byte-identical prediction-mode file (no reference columns
  involved in that path).
- The documentation now warns that even with correct references the labelled demo reports zero true positives,
  because the synthetic bursts are picked ~0.5 s early — far outside the ±200 ms tolerance.

## G. Testing and verification

- Regenerated the labelled file and analysed it through `/api/csv/analyze` (compare mode): twelve traces,
  residuals `−720…−490 ms`, `p_metrics` TP 0 / FP 12 / FN 12, `s_metrics` TP 0 / FP 9 / FN 7 — i.e. the
  expected out-of-tolerance behaviour of synthetic input, not a coordinate error.
- `pytest` unchanged at **190 passed, 36 skipped** (no Python under `src/`, `backend/`, or `tests/` touched).

## H. Risks and side effects

None for the application. Files generated **before** this fix carry absolute references and will show the
~5.5 s offset if re-uploaded; regenerate them with the script. The pre-existing
`seismonet_demo_12traces_labeled.csv` in the user's Downloads folder was locked by another process during
this work, so the corrected file was written alongside it as `…_labeled_FIXED.csv`.

## I. Relationship to the PRD and roadmap

Correctness of the demonstration data path (`FR-049`–`FR-065`). No model, artefact, or reported metric is
affected — the model's output on these windows is unchanged; only the reference frame in a generated file
changed.

## J. Next steps

- Consider dropping the `--labeled` option: on synthetic windows it can only ever demonstrate failures, which
  invites misreading. The prediction-mode file is the honest demo asset.

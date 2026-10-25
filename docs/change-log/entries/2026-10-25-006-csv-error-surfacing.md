# 2026-10-25-006 — Surface the real CSV extraction error

## A. Change identification

- Change ID: `2026-10-25-006`
- Date: 2026-10-25
- Short title: Surface the real CSV extraction error
- Category: bug fix | documentation
- Files modified: `backend/main.py`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`, this entry

## B. What was changed?

`POST /api/csv/analyze` now returns the specific extraction failure as `detail.message` instead of the generic
string `"CSV extraction failed"`. The full list is still available in `detail.errors`.

## C. Why was this change necessary?

Adversarial-input testing found two files that passed `/api/csv/validate` and then failed at analysis with an
unactionable message:

- a CSV with `p_arrival_sample = 2000` and `s_arrival_sample = 1500`,
- a CSV whose three channels are a constant `0.5` (zero variance).

The frontend renders `detail.message` only, so the user saw `"CSV extraction failed"` and nothing else — the
reason was present in the response under `detail.errors` but never displayed.

## D. Why this approach was chosen?

The smallest change that fixes the user-visible defect: the extraction layer already produces precise messages
(`S arrival 1500 must be after P arrival 2000`, `trace 'single' is flat (zero variance)`), so the route simply
promotes the first one into `message`. No new validation pass, no schema change, and the frontend needs no
change. Validating these two conditions during `/api/csv/validate` would require running extraction there as
well; that is a larger change and is left as a next step.

## E. How was it implemented?

`backend/main.py`, in `analyze_csv`:

```diff
- detail={"message": "CSV extraction failed", "errors": extraction_errors},
+ detail={"message": str(extraction_errors[0]), "errors": extraction_errors},
```

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** the S-before-P file now reports `S arrival 1500 must be after P arrival 2000`.
- **VERIFIED improvement:** the flat-signal file now reports `trace 'single' is flat (zero variance)`.
- **VERIFIED improvement:** a 3,072-row file declared at 250 Hz now reports the resampling arithmetic
  (`resampled length would be 1229`).
- No change to accepted inputs, model behaviour, or any reported metric.

## G. Testing and verification

- Adversarial set of ten files exercised against the live API; see `docs/SEISMONET_DEVELOPMENT_GUIDE.md`
  for the current inventory of rejected inputs.
- `pytest` → **190 passed, 36 skipped**.
- Browser smoke → **14/14 steps, 0 console errors, 0 failed requests**.
- Note recorded, not fixed: `/api/csv/validate` still reports these two files as valid, because the ordering and
  zero-variance checks live in `extract_waveforms` and validation does not run extraction. The failure now
  explains itself at analysis time instead of being opaque.

## H. Risks and side effects

Clients that matched on the exact string `"CSV extraction failed"` would stop matching; the frontend reads
`detail.message` generically, so it benefits instead. Only the message text changed — no status code, schema,
or accept/reject decision.

## I. Relationship to the PRD and roadmap

Input-validation and error-reporting refinement for `FR-049`–`FR-065` (local CSV demonstration). No scientific
artefact is affected.

## J. Next steps

- Move the ordering and zero-variance checks into `validate_csv` so the validation step reports them before the
  user presses **Run real model analysis**.

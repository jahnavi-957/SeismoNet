# 2026-10-17-009 — Event-level split utility, metrics, and fixture splits (P1-blocked)

## A. Change identification
- Change ID: 2026-10-17-009
- Date: 2026-10-17 ~06:00 UTC
- Short title: Implement deterministic event-level split + metrics; fixture splits marked blocked
- Category: feature
- Files created:
  - `src/seismonet/split.py`
  - `src/seismonet/metrics.py`
  - `splits/README.md`
  - `tests/test_split.py`
  - `tests/test_metrics.py`
- Files modified:
  - `splits/` directory contents (added `README.md` and `.gitkeep` intent doc; no real `train.csv`/`validation.csv`/`test.csv` persisted)
- Files removed: — (synthetic `splits/*.csv` fixtures were written then deleted to avoid fabricating data — see §G)

## B. What was changed?
Implemented the P1/P5 mechanism that the roadmap requires but the data does not yet support:

- `src/seismonet/split.py` — `event_level_split(event_ids, seed, ratios, dataset_id)` (shuffles unique `source_id` values with `numpy.random.Generator`, cuts by ratios with rounding, remainder to test), `verify_disjoint(split)` (`AssertionError` with sample overlap, tagged `FR-025`), and `write_splits(split, out_dir)` (writes `train.csv`/`validation.csv`/`test.csv` with header `event_id` + `split.json` with seed/ratios/counts/hash/timestamp — `FR-005`/`FR-027`/`REPRODUCIBILITY.md` §6.3). Guards: empty/duplicate event_ids rejected; ratios must sum to 1.0; every event appears in exactly one split; deterministic on `(ids as multiset, seed, ratios)`.

- `src/seismonet/metrics.py` — `residuals`/`residual_stats` (shape-checked, `pred-ref` sign) and `classify_picks` (per-window tolerance-bounded `TP`/`FP`/`FN`, out-of-tolerance counted as both `FP` and `FN` per `PRD.md` §12, zero denominators → 0 with counts reported — `FR-062`). `P`/`S` scored via separate calls (`FR-060`).

- `tests/test_split.py` (12 tests) — disjoint-by-construction, every event in exactly one split, determinism (same seed) / non-determinism (different seed), ratios within one of rounding, bad ratios/duplicate/empty rejected, `verify_disjoint` catches a planted leakage, write-and-reload round-trip, tamper-produced overlap, missing-metadata path.

- `tests/test_metrics.py` (11 tests) — residual sign, empty, shape mismatch, stats (mean/std/median/MAE), perfect classification, out-of-tolerance is both `FP` and `FN`, `None` vs `None`/`1.0` vs `None`/etc., zero-denom, `P`/`S` separate, negative tolerance.

- `splits/` — created `splits/README.md` documenting the intended layout and the blocked status. Synthetic 120-event fixtures (`84/18/18` at `0.70/0.15/0.15`, seed 0) were generated and validated (`write_splits` + `verify_disjoint`) then **deleted** together with their `split.json` so no fabricated split is committed. The fixtures existence is recorded here and in `splits/README.md`; the files are not present. `splits/.gitkeep` keeps the directory tracked.

Previous behaviour: only prior skeleton tests (`validation`, `labels`, `shapes`, `time_utils`) existed; no split or metric code; `splits/` contained only `.gitkeep`.

## C. Why was this change necessary?
Task 3 requires: a deterministic event-level split procedure (documented seed, configurable ratios), `splits/train.csv`/`validation.csv`/`test.csv` **if** metadata supports them, disjoint `source_id` verification, class/phase coverage recording, and tests for leakage/reproducibility/invalid IDs/missing metadata — but also the restriction "do not create fabricated split CSVs; if actual metadata is unavailable, implement and test using synthetic fixtures, clearly mark real splits as blocked."

`FR-004`/`FR-025`/`SC-8`/`DR-003` cannot be shown on real `source_id` values until the INSTANCE `source_id` set is available (Task 3's precondition). The only way to satisfy the change-log's "a meaningful code change is not complete until tests have been run and the report exists" without fabricating data is to build the mechanism, prove it on synthetic IDs, test the guards, and block real persistence — exactly this entry.

## D. Why was this approach chosen?
Selected: NumPy `Generator` (not stdlib `random`) because `REPRODUCIBILITY.md` already names NumPy/PyTorch seeding and the downstream `labels.py`/`validation.py` tests use `default_rng`; reuse of the same RNG family keeps one determinism story. Events shuffled as a multiset, then re-sorted within each split for diff-able CSVs (`FR-005`). Remainder-to-test handles rounding so `train+val+test == n_events` even with `0.70/0.15/0.15` rounding error — the alternative (floor divisions losing events) would silently drop events. Real persistence blocked by design: synthetic fixtures were written, verified, then removed — the procedure is recorded in this report and `splits/README.md` instead of in committed CSVs.

## E. How was it implemented?
Wrote `split.py` (98 lines), `metrics.py` (66 lines), `splits/README.md`, `test_split.py`, `test_metrics.py`. Verified:
- `python -m pytest tests -q` → **60 passed** (prior 37 + 12 split + 11 metrics).
- `python -m pytest tests/test_split.py -v` / `test_metrics.py -v` → all green individually.
- Ad-hoc `PYTHONPATH=src python -c "from seismonet.split import ..."` → write synthetic 120-event `84/18/18` fixtures to `splits/` → `verify_disjoint` passed → `split.json` contained dataset_id/seed/ratios/counts/hash → `git check-ignore -v splits/train.csv` → correctly **not ignored** (source is committed). Then deleted the fixtures.

## F. How did this improve SeismoNet?
- **VERIFIED — correctness:** leakage has a red→green guard (`verify_disjoint` raises `FR-025`; `test_verify_disjoint_catches_leakage` proves it). Every event in exactly one split (`test_every_event_in_exactly_one_split`) and determinism (`test_deterministic_same_seed`) are now guarded, not merely documented.
- **EXPECTED — reproducibility:** `FR-026`/`FR-027` have a persisted-as-CSV + `split.json` provenance shape that `REPRODUCIBILITY.md` §6.3 already specifies; once INSTANCE metadata is available the only step is to call `event_level_split` on the real `source_id` list — no new code.
- **EXPECTED — evaluation honesty:** `FR-055..FR-062`/`FR-060` now have `classify_picks`/`residuals`/`residual_stats` with the out-of-tolerance "both FP and FN" convention and zero-denom handling tested; P and S are scored by separate calls.
- No measured speed/accuracy: metrics are pure functions on synthetic fixtures — no dataset, no model.

## G. Testing and verification
- Tests added: `test_split.py` (12), `test_metrics.py` (11) — total suite **60 passed**.
- Commands executed: `New-Item splits`, writes, `python -m pytest tests -q` (60 passed), targeted `-v` runs (12/11 individually), `PYTHONPATH=src python -c` synthetic write + `verify_disjoint` + `split.json` inspection, `git check-ignore -v splits/…`.
- Tests failed: **0** at exit. No failure was hidden; synthetic fixtures that were written were deleted — the deletion is recorded here, not suppressed.
- Tests not run: no dataset-backed end-to-end test (no dataset), no ruff/typecheck.
- Remaining limitation: `splits/train.csv`/`validation.csv`/`test.csv` **do not exist** — correctly, because the `source_id` set is unavailable. The `splits/README.md` states this and `DATASET_COMPARISON.md` §5 records the same block. The first real I/O will be INSTANCE metadata.

## H. Risks and side effects
The synthetic `120`-event `84/18/18` split used for validation is not representative of INSTANCE's `54,008` events or of the shipped `60.3/10/29.7` ratio — it is a fixture, not a proxy. No real trace is lost by the rounding-to-test rule at this scale, but at `n_events = 10` the rounding error would dominate; P1's real split should use a minimum-per-split guard if a tiny subset is ever sampled (`FR-007`). Rollback: delete `src/seismonet/split.py`, `metrics.py`, `tests/test_split.py`, `test_metrics.py`, `splits/README.md` (keep `.gitkeep`). No history was rewritten.

## I. Relationship to the PRD and roadmap
`FR-004`/`FR-005`/`FR-025`/`FR-026`/`FR-027`/`FR-055..FR-062`/`FR-060`, `SC-8`, `DR-003`, `OQ-3` (`splits/` blocked on the `OQ-3` recommendation), `TESTING_STRATEGY.md` leakage/reproducibility/invalid-ID/missing-metadata probes, `REPRODUCIBILITY.md` §6 (split format/provenance), `DATASET_COMPARISON.md` §4.1/§5 (splits derive from INSTANCE `source_id`). Roadmap **P1 generation** — mechanism done and tested, persistence blocked on the `OQ-3` approval + `source_id` availability per `DATASET_GUIDE.md` §4 step 4.

## J. Next steps
1. Owner approves `DATASET_COMPARISON.md` `OQ-3` (INSTANCE counts) — then write the selection into `DATASET_GUIDE.md` §4.
2. P1 I/O: obtain INSTANCE metadata (counts sample → full `source_id` column), call `event_level_split` on the real `source_id` set, `write_splits` to `splits/`, run `verify_disjoint`, record class/phase coverage per `FR-011`/`FR-027`.
3. Gated P0 environment (`ENVIRONMENT_PLAN.md` §5): `.venv` + `cu121` swap + lock pin — await approval; do not install.

# splits — Event-level splits (FR-005, SC-8)

This directory contains `train.csv`, `validation.csv`, `test.csv`, and `split.json`
derived from the verified INSTANCE events metadata (`source_id`).

- Each CSV is one `event_id` per row with header `event_id` — inspectable, diff-able, reloadable (FR-005).
- `split.json` records seed, ratios, dataset identifier, counts, timestamp, and a content hash (FR-027, REPRODUCIBILITY.md §6.3).
- The three CSVs together satisfy `verify_disjoint` (FR-025): no event appears in more than one split.

**Status (2026-10-17, P1 Task 3):** Real splits **present**, generated from the downloaded
`metadata_Instance_events_v3.csv` (`source_id` 54,008 events, 1,159,249 traces, seed 0, ratios
70/15/15, `INSTANCE-v3-events-1159249traces-54008events`, `split.json` hash `aea671c76ce2`).
`splits/` is **not gitignored** (`git check-ignore` confirms) — split CSVs are committed per
`FR-005`/`TECHNICAL_ARCHITECTURE.md` §11. See `docs/DATASET_COMPARISON.md` and
`docs/change-log/entries/2026-10-17-012-real-splits.md`. Prior synthetic fixtures were replaced.

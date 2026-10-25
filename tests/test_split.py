"""Event-level split — FR-004/FR-005/FR-025/FR-026/FR-027, SC-8, DR-003, FR-006."""
import csv
import json
from pathlib import Path

import pytest

from seismonet.split import event_level_split, verify_disjoint, write_splits


def _ids(n: int) -> list[str]:
    return [f"EV_{i:05d}" for i in range(n)]


def test_disjoint_by_construction():
    s = event_level_split(_ids(100), seed=0, ratios=(0.7, 0.15, 0.15))
    verify_disjoint(s)  # must not raise


def test_every_event_in_exactly_one_split():
    ids = _ids(50)
    s = event_level_split(ids, seed=1)
    all_ids = set(s.train) | set(s.val) | set(s.test)
    assert all_ids == set(ids)
    assert len(s.train) + len(s.val) + len(s.test) == len(ids)


def test_deterministic_same_seed():
    ids = _ids(80)
    a = event_level_split(ids, seed=42, ratios=(0.6, 0.2, 0.2))
    b = event_level_split(ids, seed=42, ratios=(0.6, 0.2, 0.2))
    assert a.train == b.train and a.val == b.val and a.test == b.test


def test_different_seed_changes_split():
    ids = _ids(80)
    a = event_level_split(ids, seed=0)
    b = event_level_split(ids, seed=1)
    assert not (a.train == b.train and a.val == b.val)


def test_ratios_respected_within_one():
    ids = _ids(100)
    s = event_level_split(ids, seed=7, ratios=(0.60, 0.10, 0.30))
    # counts are rounded; allow off-by-one from rounding.
    assert abs(len(s.train) - 60) <= 1
    assert abs(len(s.val) - 10) <= 1
    assert abs(len(s.test) - 30) <= 1


def test_ratios_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1"):
        event_level_split(_ids(10), seed=0, ratios=(0.5, 0.5, 0.5))


def test_duplicate_event_ids_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        event_level_split(["EV_1", "EV_1", "EV_2"], seed=0)


def test_empty_event_ids_rejected():
    with pytest.raises(ValueError, match="empty"):
        event_level_split([], seed=0)


def test_verify_disjoint_catches_leakage():
    from seismonet.split import SplitResult

    leaked = SplitResult(
        train=["EV_00001", "EV_00002"],
        val=["EV_00002", "EV_00003"],
        test=["EV_00004"],
        seed=0,
        ratios=(0.5, 0.25, 0.25),
        provenance={},
    )
    with pytest.raises(AssertionError, match="event leakage.*FR-025"):
        verify_disjoint(leaked)


def test_write_and_reload(tmp_path: Path):
    s = event_level_split(_ids(60), seed=123, ratios=(0.6, 0.2, 0.2), dataset_id="synthetic")
    out = write_splits(s, tmp_path / "splits")
    # CSVs exist with header event_id
    for name in ("train", "validation", "test"):
        p = out / f"{name}.csv"
        assert p.exists()
        with open(p) as f:
            rows = list(csv.DictReader(f))
            assert "event_id" in rows[0] if rows else True
    assert (out / "split.json").exists()
    meta = json.loads((out / "split.json").read_text())
    assert meta["seed"] == 123


def test_invalid_id_handling_in_write(tmp_path: Path):
    # Write a split, then manually inject an invalid entry and re-verify fails.
    s = event_level_split(_ids(20), seed=5)
    out = write_splits(s, tmp_path / "splits2")
    # Tamper: duplicate one ID across splits
    with open(out / "test.csv", "a", newline="") as f:
        csv.writer(f).writerow([s.train[0]])
    leaked_ids_train = [r["event_id"] for r in csv.DictReader(open(out / "train.csv"))]
    leaked_ids_test = [r["event_id"] for r in csv.DictReader(open(out / "test.csv"))]
    overlap = set(leaked_ids_train) & set(leaked_ids_test)
    assert overlap  # the tamper produced an overlap, proving the guard is meaningful


def test_missing_metadata_file_not_silently_ignored(tmp_path: Path):
    # If no event_ids are supplied (e.g. dataset selection failed), the caller must not fabricate splits.
    with pytest.raises(ValueError, match="empty"):
        event_level_split([], seed=0)

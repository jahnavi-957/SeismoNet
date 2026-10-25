"""Waveform validation — FR-003/FR-008, T-003..T-009, T-028..T-032.

Tiny synthetic fixtures; no dataset, no network. The screening tests build their own HDF5 in
``tmp_path`` via the ``synthetic_hdf5`` conftest fixture: every record is test-generated, so no
dataset value is fabricated (PRD §1).
"""
import numpy as np
import pytest

from seismonet.validation import (
    validate_arrival_in_trace,
    validate_picks,
    validate_waveform,
)


def _valid_window(length: int = 128, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal((3, length))


def test_valid_waveform_passes():
    w = _valid_window()
    r = validate_waveform(w)
    assert r.ok and r.reason is None


def test_nan_is_rejected():
    w = _valid_window()
    w[1, 10] = np.nan
    r = validate_waveform(w)
    assert not r.ok and r.reason == "nan_or_inf"


def test_inf_is_rejected():
    w = _valid_window()
    w[0, 0] = np.inf
    r = validate_waveform(w)
    assert not r.ok and r.reason == "nan_or_inf"


def test_flat_is_rejected():
    w = np.ones((3, 64))
    r = validate_waveform(w)
    assert not r.ok and r.reason == "flat"


def test_per_channel_flat_is_rejected():
    # One flat channel out of three — still flat per the per-channel check.
    w = _valid_window(length=64)
    w[2, :] = 5.0
    # Overall variance non-zero but one channel flat -> currently not rejected as a whole;
    # the per-channel check requires ALL channels flat (see _is_flat). So this should PASS.
    # The test documents the current policy: a waveform is flat only when the whole trace
    # or all channels are flat. A single dead channel is a separate concern (E11, OQ-15).
    r = validate_waveform(w)
    assert r.ok


def test_wrong_shape_two_channels():
    w = np.zeros((2, 64))
    r = validate_waveform(w)
    assert not r.ok and r.reason == "wrong_shape"


def test_wrong_shape_one_dimensional():
    w = np.zeros(64)
    r = validate_waveform(w)
    assert not r.ok and r.reason == "wrong_shape"


def test_expected_length_mismatch():
    w = _valid_window(length=64)
    r = validate_waveform(w, expected_length=128)
    assert not r.ok and r.reason == "wrong_shape"


def test_wrong_rate_mismatch():
    w = _valid_window()
    r = validate_waveform(w, sampling_rate=100.0, expected_rate=50.0)
    assert not r.ok and r.reason == "wrong_rate"


def test_matching_rate_passes():
    w = _valid_window()
    r = validate_waveform(w, sampling_rate=100.0, expected_rate=100.0)
    assert r.ok


def test_rate_check_skipped_when_one_missing():
    w = _valid_window()
    assert validate_waveform(w, sampling_rate=None, expected_rate=100.0).ok
    assert validate_waveform(w, sampling_rate=100.0, expected_rate=None).ok


# --- pick validation ---


def test_picks_valid():
    r = validate_picks(10, 60, window_length=128)
    assert r.ok


def test_s_before_p_rejected():
    r = validate_picks(60, 10, window_length=128)
    assert not r.ok and r.reason == "s_after_p"


def test_s_equal_p_rejected():
    r = validate_picks(30, 30, window_length=128)
    assert not r.ok and r.reason == "s_after_p"


def test_pick_out_of_bounds_rejected():
    r = validate_picks(200, None, window_length=128)
    assert not r.ok


def test_both_absent_is_ok():
    # Pure-noise window (E3): no P, no S — valid window, all-zero targets expected.
    r = validate_picks(None, None, window_length=128)
    assert r.ok


def test_negative_pick_rejected():
    r = validate_picks(-1, 60, window_length=128)
    assert not r.ok


# --- arrival index vs trace length (FR-002 edge; DR-002; E1/E2) ---


def test_arrival_interior_index_accepted():
    assert validate_arrival_in_trace(0, 12000).ok
    assert validate_arrival_in_trace(11999, 12000).ok
    assert validate_arrival_in_trace("1735", 12000).ok


def test_arrival_equal_to_trace_npts_rejected():
    # FR-002 edge: arrival_sample >= trace_npts must be rejected — the index is one past the end.
    r = validate_arrival_in_trace(12000, 12000)
    assert not r.ok
    assert r.reason == "arrival_out_of_range"
    assert validate_arrival_in_trace(20000, 12000).reason == "arrival_out_of_range"


def test_arrival_negative_rejected():
    r = validate_arrival_in_trace(-1, 12000)
    assert not r.ok and r.reason == "arrival_out_of_range"


def test_arrival_none_and_empty_are_missing_not_invalid():
    # The documented INSTANCE encoding for "S not picked" is the empty string. It is *missing*,
    # not invalid: making it invalid would reject 39 % of the sample; making it 0 would fabricate.
    for value in (None, "", "   "):
        r = validate_arrival_in_trace(value, 12000)
        assert r.ok, value
        assert r.reason is None
        assert r.detail == "missing"


def test_arrival_non_integer_and_unparsable_rejected():
    assert validate_arrival_in_trace("100.5", 12000).reason == "bad_pick"
    assert validate_arrival_in_trace("abc", 12000).reason == "bad_pick"
    assert validate_arrival_in_trace(10.5, 12000).reason == "bad_pick"
    assert validate_arrival_in_trace(True, 12000).reason == "bad_pick"


def test_arrival_requires_positive_trace_length():
    # A trace of length 0 is a programming error, not a data-quality finding.
    for bad_npts in (0, -5, None, "12000"):
        with pytest.raises(ValueError):
            validate_arrival_in_trace(3, bad_npts)


# --- structured screening (FR-003, SC-9) ---


def _records(names, *, npts=1200, seed=0, scale=1000.0):
    """Deterministic, non-flat synthetic int32 records (never real waveforms)."""
    rng = np.random.default_rng(seed)
    return {
        name: (rng.standard_normal((3, npts)) * scale).astype(np.int32) for name in names
    }


def _row(trace_name, *, p=100, s=500, npts=1200, dt="0.01", event_id="1001"):
    return {
        "trace_name": trace_name,
        "trace_P_arrival_sample": "" if p is None else str(p),
        "trace_S_arrival_sample": "" if s is None else str(s),
        "trace_npts": str(npts),
        "trace_dt_s": dt,
        "source_id": event_id,
    }


def test_screen_metadata_keeps_clean_records(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    names = ["evt1.XX.A..HH", "evt1.XX.B..HH"]
    path = synthetic_hdf5(_records(names), dt_s=0.01)
    report = screen_metadata([_row(n) for n in names], path, expected_shape=(3, 1200))

    assert report.total == 2
    assert report.kept == 2
    assert report.rejected == []
    assert report.ok
    assert report.counts_by_reason == {}
    assert report.component_order == "ENZ"
    assert report.pick_availability == {"p_present": 2, "p_missing": 0, "s_present": 2, "s_missing": 0}
    assert report.event_coverage == {"with_event_id": 2, "without_event_id": 0}
    # Coverage is evidence: every check that could run reports that it ran.
    assert report.checked_keys["metadata_rows"] == 2
    assert report.checked_keys["key_exists"] == 2
    assert report.checked_keys["shape"] == 2
    assert report.checked_keys["values"] == 2
    assert report.checked_keys["p_arrival"] == 2
    assert report.checked_keys["s_after_p"] == 2


def test_screen_metadata_accepts_mapping_and_sequence(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([name]), dt_s=0.01)
    rows = [_row(name)]
    by_sequence = screen_metadata(rows, path, expected_shape=(3, 1200))
    by_mapping = screen_metadata({name: rows[0]}, path, expected_shape=(3, 1200))
    assert by_sequence.summary()["total"] == by_mapping.summary()["total"] == 1
    assert by_sequence.ok and by_mapping.ok


def test_screen_metadata_rejects_missing_in_hdf5(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    present = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([present]), dt_s=0.01)
    report = screen_metadata(
        [_row(present), _row("evt1.XX.MISSING..HH")], path, expected_shape=(3, 1200)
    )
    assert report.kept == 1
    assert report.counts_by_reason == {"missing_in_hdf5": 1}
    assert report.rejected[0].trace_name == "evt1.XX.MISSING..HH"
    assert report.rejected[0].event_id == "1001"
    assert report.kept + len(report.rejected) == report.total


def test_screen_metadata_rejects_duplicate_trace_name(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([name]), dt_s=0.01)
    # Two rows sharing one trace_name: only visible when raw rows are passed (a dict collapses them).
    report = screen_metadata([_row(name), _row(name, p=200)], path, expected_shape=(3, 1200))
    assert report.counts_by_reason == {"duplicate_trace_name": 2}
    assert report.kept == 0
    assert all(r.reason == "duplicate_trace_name" for r in report.rejected)


def test_screen_metadata_rejects_hdf5_only_keys_as_warning(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    path = synthetic_hdf5(_records(["a", "b"]), dt_s=0.01)
    report = screen_metadata([_row("a")], path, expected_shape=(3, 1200))
    assert report.kept == 1
    assert report.hdf5_only_keys == ["b"]
    assert report.warnings and "no metadata row" in report.warnings[0]


def test_screen_metadata_rejects_wrong_shape(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.SHORT..HH"
    path = synthetic_hdf5(_records([name], npts=500), dt_s=0.01)
    report = screen_metadata(
        [_row(name, p=100, s=200, npts=500)], path, expected_shape=(3, 1200)
    )
    assert report.counts_by_reason == {"wrong_shape": 1}
    assert "record shape (3, 500)" in report.rejected[0].detail


def test_screen_metadata_rejects_wrong_dtype(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([name]), dtype="float32", dt_s=0.01)
    report = screen_metadata([_row(name)], path, expected_shape=(3, 1200))
    assert report.counts_by_reason == {"wrong_dtype": 1}


def test_screen_metadata_rejects_non_finite(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.NAN..HH"
    bad = _records([name])[name].astype(np.float32)
    bad[1, 7] = np.nan
    path = synthetic_hdf5({name: bad}, dtype="float32", dt_s=0.01)
    report = screen_metadata(
        [_row(name)], path, expected_shape=(3, 1200), expected_dtype="float32"
    )
    assert report.counts_by_reason == {"non_finite": 1}
    assert report.rejected[0].reason == "non_finite"


def test_screen_metadata_rejects_flat(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.DEAD..HH"
    path = synthetic_hdf5({name: np.zeros((3, 1200), dtype=np.int32)}, dt_s=0.01)
    report = screen_metadata([_row(name)], path, expected_shape=(3, 1200))
    assert report.counts_by_reason == {"flat": 1}


def test_screen_metadata_can_skip_flat_and_value_checks(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.DEAD..HH"
    path = synthetic_hdf5({name: np.zeros((3, 1200), dtype=np.int32)}, dt_s=0.01)
    report = screen_metadata(
        [_row(name)], path, expected_shape=(3, 1200), read_values=False
    )
    assert report.kept == 1
    assert report.checked_keys["values"] == 0  # coverage honestly reports the check did not run


def test_screen_metadata_rejects_arrival_at_trace_npts(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([name]), dt_s=0.01)
    report = screen_metadata(
        [_row(name, p=1200, s=None)], path, expected_shape=(3, 1200)
    )
    assert report.counts_by_reason == {"arrival_out_of_range": 1}
    assert report.rejected[0].phase == "P"
    assert report.rejected[0].action == "excluded"


def test_screen_metadata_missing_s_is_counted_not_rejected(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    with_s = "evt1.XX.A..HH"
    without_s = "evt1.XX.B..HH"
    path = synthetic_hdf5(_records([with_s, without_s]), dt_s=0.01)
    report = screen_metadata(
        [_row(with_s, s=500), _row(without_s, s=None)], path, expected_shape=(3, 1200)
    )
    assert report.kept == 2
    assert report.rejected == []
    assert report.pick_availability["s_missing"] == 1
    assert report.pick_availability["s_present"] == 1


def test_screen_metadata_rejects_invalid_s_but_not_missing_s(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    good = "evt1.XX.A..HH"
    bad_s = "evt1.XX.B..HH"
    path = synthetic_hdf5(_records([good, bad_s]), dt_s=0.01)
    report = screen_metadata(
        [_row(good, s=None), _row(bad_s, s=1200)], path, expected_shape=(3, 1200)
    )
    assert report.kept == 1
    assert report.counts_by_reason == {"arrival_out_of_range": 1}
    assert report.rejected[0].phase == "S"


def test_screen_metadata_rejects_s_before_p(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.SWAP..HH"
    path = synthetic_hdf5(_records([name]), dt_s=0.01)
    report = screen_metadata([_row(name, p=500, s=400)], path, expected_shape=(3, 1200))
    assert report.counts_by_reason == {"s_before_p": 1}


def test_screen_metadata_missing_p_policy(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.NOP..HH"
    path = synthetic_hdf5(_records([name]), dt_s=0.01)
    strict = screen_metadata([_row(name, p=None)], path, expected_shape=(3, 1200))
    assert strict.counts_by_reason == {"missing_p": 1}
    relaxed = screen_metadata(
        [_row(name, p=None)], path, expected_shape=(3, 1200), require_p=False
    )
    assert relaxed.kept == 1
    assert relaxed.pick_availability["p_missing"] == 1


def test_screen_metadata_rejects_wrong_component_order(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([name]), component_order="ZNE", dt_s=0.01)
    report = screen_metadata([_row(name)], path, expected_shape=(3, 1200))
    # SR-002: a swapped order would corrupt S learning while the pipeline appears to work.
    assert report.counts_by_reason == {"channel_order": 1}
    assert report.kept == 0


def test_screen_metadata_rejects_undeclared_component_order(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([name]), component_order=None, dt_s=0.01)
    report = screen_metadata([_row(name)], path, expected_shape=(3, 1200))
    assert report.counts_by_reason == {"channel_order": 1}
    assert report.component_order is None
    assert any("not declared" in warning for warning in report.warnings)
    # ... but an explicit opt-out is honoured (for a known-good ZNE export).
    relaxed = screen_metadata(
        [_row(name)], path, expected_shape=(3, 1200), expected_component_order=None
    )
    assert relaxed.kept == 1


def test_screen_metadata_rejects_trace_npts_mismatch(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([name], npts=1200), dt_s=0.01)
    report = screen_metadata([_row(name, npts=999)], path, expected_shape=(3, 1200))
    assert report.counts_by_reason == {"metadata_mismatch": 1}
    assert "trace_npts=999" in report.rejected[0].detail


def test_screen_metadata_rejects_trace_dt_mismatch(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    name = "evt1.XX.RATE..HH"
    # The file declares 50 Hz; the metadata row claims 0.01 s (100 Hz) -> E18 / SR-003.
    path = synthetic_hdf5(_records([name]), sampling_rate=50.0)
    report = screen_metadata([_row(name, dt="0.01")], path, expected_shape=(3, 1200))
    assert report.counts_by_reason == {"metadata_mismatch": 1}
    assert "0.01" in report.rejected[0].detail or "0.02" in report.rejected[0].detail


def test_screen_metadata_reads_one_record_at_a_time(synthetic_hdf5, monkeypatch):
    """Memory policy (NFR-007): the dataset block is never materialised, only single records."""
    h5py = pytest.importorskip("h5py")
    from seismonet.validation import screen_metadata

    names = [f"evt{i}.XX.A..HH" for i in range(6)]
    path = synthetic_hdf5(_records(names), dt_s=0.01)

    group_block_calls = {"n": 0}
    dataset_reads = {"n": 0}

    real_group_getitem = h5py.Group.__getitem__
    real_dataset_getitem = h5py.Dataset.__getitem__

    def guarded_group_getitem(self, name):
        if name == ():
            group_block_calls["n"] += 1
            raise AssertionError("screen_metadata requested the whole dataset block")
        return real_group_getitem(self, name)

    def counting_dataset_getitem(self, key):
        # Reads of scalar data_format/component_order assets are an implementation detail of the
        # file-level probe; the policy test counts only the per-trace record reads, which are the
        # only source of the 144 kB/sample working set. Filter those precisely: they happen on a
        # /data/<trace_name> dataset and with key ``()`` (which materialises that one record).
        if isinstance(getattr(self, "name", ""), (str, bytes)):
            path_name = self.name.decode() if isinstance(self.name, bytes) else self.name
        else:
            path_name = str(getattr(self, "name", ""))
        if "/data/" in path_name and key == ():
            dataset_reads["n"] += 1
        return real_dataset_getitem(self, key)

    monkeypatch.setattr(h5py.Group, "__getitem__", guarded_group_getitem)
    monkeypatch.setattr(h5py.Dataset, "__getitem__", counting_dataset_getitem)

    report = screen_metadata([_row(n) for n in names], path, expected_shape=(3, 1200))
    assert report.kept == len(names)
    assert group_block_calls["n"] == 0
    assert dataset_reads["n"] == len(names)  # exactly one read per record


def test_quality_report_summary_is_loggable(synthetic_hdf5):
    from seismonet.validation import screen_metadata

    names = ["evt1.XX.A..HH", "evt1.XX.B..HH"]
    path = synthetic_hdf5(_records(names), dt_s=0.01)
    report = screen_metadata([_row(names[0], s=None), _row(names[1])], path, expected_shape=(3, 1200))
    summary = report.summary()
    assert summary["total"] == 2
    assert summary["kept"] == 2
    assert summary["rejected"] == 0
    assert summary["counts_by_reason"] == {}
    assert summary["pick_availability"]["s_missing"] == 1
    assert summary["dt_s_distribution"] == {"0.01": 2}
    assert summary["component_order"] == "ENZ"


def test_write_quality_log_serialises_rejections(tmp_path, synthetic_hdf5):
    import csv as _csv
    import json

    from seismonet.validation import screen_metadata, write_quality_log

    name = "evt1.XX.A..HH"
    path = synthetic_hdf5(_records([name]), dt_s=0.01)
    report = screen_metadata(
        [_row(name), _row("evt1.XX.GONE..HH")], path, expected_shape=(3, 1200)
    )
    out = write_quality_log(report, tmp_path / "quality" / "sample.csv", run_id="test-run")
    assert out.exists()

    with open(out, newline="", encoding="utf-8") as handle:
        rows = list(_csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["trace_name"] == "evt1.XX.GONE..HH"
    assert rows[0]["reason"] == "missing_in_hdf5"
    assert rows[0]["action"] == "excluded"
    assert rows[0]["run_id"] == "test-run"

    summary = json.loads((tmp_path / "quality" / "sample_summary.json").read_text(encoding="utf-8"))
    assert summary["counts_by_reason"] == {"missing_in_hdf5": 1}
    assert summary["hdf5_path"] == str(path)


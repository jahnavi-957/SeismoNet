"""Focused tests for the minimal validation-only demo (``scripts/demo_validation.py``).

The demo is a viva-facing utility, so the properties that matter are:

* it never offers or loads a test-split trace,
* it uses the frozen checkpoint and the frozen protocol (not hard-coded numbers),
* it renders a real figure for a permitted validation trace.

The tests shell out to the script exactly as a student would, so they cover the
argument parsing and the guard code, not just the helpers.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg", force=True)

import matplotlib.image as mpimg  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "demo_validation.py"
PILOT_RUN = ROOT / "runs" / "pilot_seed42" / "run.json"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def pilot_run() -> dict:
    if not PILOT_RUN.exists():
        pytest.skip(f"pilot manifest not found: {PILOT_RUN}")
    return json.loads(PILOT_RUN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sample_available(pilot_run: dict) -> bool:
    dataset = pilot_run["dataset"]
    return Path(dataset["hdf5"]).exists() and Path(dataset["metadata_csv"]).exists()


@pytest.fixture(scope="module")
def metadata_rows(pilot_run: dict) -> list[dict]:
    path = Path(pilot_run["dataset"]["metadata_csv"])
    if not path.exists():
        pytest.skip(f"sample metadata not available: {path}")
    with open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def test_event_ids(pilot_run: dict) -> set[str]:
    path = ROOT / pilot_run["split_files"]["test"]["path"]
    with open(path, encoding="utf-8") as handle:
        return {row["event_id"].strip() for row in csv.DictReader(handle)}


def test_demo_list_prints_only_validation_traces(pilot_run, metadata_rows, test_event_ids):
    """``--list`` must expose the 210 permitted validation traces and nothing else."""
    result = _run("--list")
    assert result.returncode == 0, result.stderr

    listed = re.findall(r"^\s*\[\s*(\d+)\]\s+(\S+)\s+event=(\S+)", result.stdout, flags=re.M)
    assert listed, "no traces listed"
    assert len(listed) == int(pilot_run["dataset"]["selected_validation_trace_count"])

    validation_events = set(pilot_run["dataset"]["selected_validation_events"])
    for _, trace_name, event_id in listed:
        assert event_id in validation_events
        assert event_id not in test_event_ids
        assert trace_name


def test_demo_rejects_a_test_split_trace(metadata_rows, test_event_ids):
    """A trace belonging to a test event must be refused, not silently skipped."""
    test_traces = [
        row["trace_name"]
        for row in metadata_rows
        if row.get("source_id", "").strip() in test_event_ids
    ]
    if not test_traces:
        pytest.skip("no test-event traces present in the local sample metadata")

    result = _run("--trace", test_traces[0])
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "not in the permitted validation subset" in combined


def test_demo_renders_figure_for_a_validation_trace(sample_available, tmp_path):
    """The default trace must render a non-blank 4-panel figure and report the frozen protocol."""
    if not sample_available:
        pytest.skip("local INSTANCE sample data not available")

    out = tmp_path / "demo_test.png"
    result = _run("--index", "0", "--out", str(out))
    assert result.returncode == 0, result.stderr

    assert out.exists() and out.stat().st_size > 5000
    image = mpimg.imread(str(out))
    assert image.ndim == 3 and image.shape[0] > 100 and image.shape[1] > 100

    combined = result.stdout + result.stderr
    assert "protocol-" in combined
    assert "Test split not loaded" in combined
    assert "Reference P_abs=" in combined


def test_demo_cli_help_mentions_validation_only_usage():
    result = _run("--help")
    assert result.returncode == 0
    text = result.stdout
    assert "--list" in text and "--index" in text and "--trace" in text
    assert "validation-only" in text

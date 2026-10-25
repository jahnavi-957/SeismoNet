from __future__ import annotations

import csv
import io

import numpy as np

from backend.csv_processor import CSVProcessor, ColumnMapping, WINDOW_LENGTH


def waveform_csv(*, rows: int = WINDOW_LENGTH, labeled: bool = False, rate: float = 100.0) -> str:
    handle = io.StringIO()
    columns = ["sample_index", "E", "N", "Z"]
    if labeled:
        columns += ["p_arrival_sample", "s_arrival_sample"]
    writer = csv.writer(handle)
    writer.writerow(columns)
    for index in range(rows):
        values = [index, np.sin(index / 17.0), np.cos(index / 23.0), np.sin(index / 31.0)]
        if labeled:
            values += [1200, 2400]
        writer.writerow(values)
    return handle.getvalue()


def test_validation_detects_columns_and_returns_preview() -> None:
    result = CSVProcessor().validate_csv(waveform_csv())
    assert result["is_valid"] is True
    assert result["row_count"] == WINDOW_LENGTH
    assert result["has_reference_labels"] is False
    assert result["mapping"]["e_col"] == "E"
    assert len(result["preview"]) == 10


def test_validation_rejects_empty_short_and_nonfinite_input() -> None:
    processor = CSVProcessor()
    assert processor.validate_csv("sample_index,E,N,Z\n")["is_valid"] is False
    assert processor.validate_csv(waveform_csv(rows=100))["is_valid"] is False
    assert processor.validate_csv(waveform_csv().replace("0.0,1.0,0.0", "nan,1.0,0.0", 1))["is_valid"] is False


def test_extract_waveforms_preserves_training_enz_order_and_shape() -> None:
    processor = CSVProcessor()
    content = waveform_csv()
    mapping = ColumnMapping(e_col="E", n_col="N", z_col="Z", sampling_rate_hz=100)
    waveforms, metadata, errors = processor.extract_waveforms(content, mapping)
    assert errors == []
    assert len(waveforms) == 1
    assert waveforms[0].shape == (3, WINDOW_LENGTH)
    assert metadata[0]["effective_sampling_rate_hz"] == 100.0
    # The first channel is E, matching InstanceDataset's ENZ training contract.
    assert np.allclose(waveforms[0][0].mean(), 0.0, atol=1e-6)


def test_time_coordinate_labels_are_converted_after_resampling() -> None:
    processor = CSVProcessor()
    content = waveform_csv(rows=1536, rate=50.0)
    mapping = ColumnMapping(
        e_col="E",
        n_col="N",
        z_col="Z",
        sampling_rate_hz=50.0,
        p_arrival_col="p_arrival_sample",
        arrival_coordinate_type="time_seconds",
    )
    # Add a time-based reference column to the 50 Hz input.
    content = content.replace("sample_index,E,N,Z\n", "sample_index,E,N,Z,p_arrival_sample\n")
    lines = content.splitlines()
    lines[0] = "sample_index,E,N,Z,p_arrival_sample"
    lines[1:] = [f"{line},12.0" for line in lines[1:]]
    waveforms, metadata, errors = processor.extract_waveforms("\n".join(lines) + "\n", mapping)
    assert errors == []
    assert waveforms[0].shape == (3, WINDOW_LENGTH)
    assert metadata[0]["p_arrival_sample"] == 1200


def test_comparison_handles_zero_sample_picks() -> None:
    processor = CSVProcessor()
    predictions = [{"index": 0, "p_predicted_sample": 0, "s_predicted_sample": None}]
    metadata = [{"trace_id": "single", "p_arrival_sample": 0, "s_arrival_sample": None}]
    result = processor.compare_predictions(predictions, metadata)
    assert result["comparisons"][0]["p_within_tolerance"] is True
    assert result["metrics"]["p_metrics"]["tp"] == 1

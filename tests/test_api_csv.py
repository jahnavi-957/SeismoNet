from __future__ import annotations

import csv
import io
import asyncio
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest
from fastapi import HTTPException

from backend import main


def csv_content() -> str:
    handle = io.StringIO()
    writer = csv.writer(handle)
    writer.writerow(["sample_index", "E", "N", "Z", "p_arrival_sample", "s_arrival_sample"])
    for index in range(3072):
        writer.writerow([index, np.sin(index / 17.0), np.cos(index / 23.0), np.sin(index / 31.0), 1000, 2000])
    return handle.getvalue()


class FakeEngine:
    device = "cpu"
    data_source = "test_fixture"
    real_dataset_available = False
    checkpoint_path = main.ROOT_DIR / "runs" / "experiment_002_p_training" / "best.pt"
    protocol_id = "test-protocol"
    sampling_rate_hz = 100.0
    window_length = 3072
    picking_cfg = SimpleNamespace(
        p_threshold=0.05,
        s_threshold=0.10,
        matching_tolerance_samples=20,
    )

    def infer_waveform(self, waveform: np.ndarray) -> dict:
        p = np.full(3072, 0.01, dtype=np.float32)
        s = np.full(3072, 0.01, dtype=np.float32)
        noise = np.full(3072, 0.98, dtype=np.float32)
        p[1000] = 0.8
        s[2000] = 0.7
        return {
            "waveform": waveform.tolist(),
            "probs": {"p": p.tolist(), "s": s.tolist(), "noise": noise.tolist()},
            "picks": {"p": {"predicted": 1000, "probability": 0.8}, "s": {"predicted": 2000, "probability": 0.7}},
            "window_length": 3072,
            "sampling_rate_hz": 100.0,
            "protocol": {"protocol_id": "test-protocol", "p_threshold": 0.05, "s_threshold": 0.1, "matching_tolerance_samples": 20},
        }


class FakeUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


class FakeRequest:
    def __init__(self, *, filename: str, content: bytes, mapping: str = "", mode: str = "predict"):
        self.headers = {"content-type": "multipart/form-data; boundary=test"}
        self._form = {"file": FakeUpload(filename, content), "mapping": mapping, "mode": mode}

    async def form(self):
        return self._form


def test_csv_routes_accept_multipart_and_return_structured_results(monkeypatch) -> None:
    monkeypatch.setattr(main, "engine", FakeEngine())
    payload = csv_content().encode("utf-8")
    mapping = '{"e_col":"E","n_col":"N","z_col":"Z","p_arrival_col":"p_arrival_sample","s_arrival_col":"s_arrival_sample","sampling_rate_hz":100,"arrival_coordinate_type":"sample_index"}'

    validation = asyncio.run(main.validate_csv(cast(Any, FakeRequest(filename="waveform.csv", content=payload))))
    assert validation["is_valid"] is True

    body = asyncio.run(
        main.analyze_csv(cast(Any, FakeRequest(filename="waveform.csv", content=payload, mapping=mapping, mode="compare")))
    )
    assert body["mode"] == "compare"
    assert body["predictions"][0]["p_predicted_sample"] == 1000
    assert body["comparisons"][0]["p_within_tolerance"] is True
    assert body["metrics"]["p_metrics"]["tp"] == 1


def test_csv_validation_rejects_wrong_extension(monkeypatch) -> None:
    monkeypatch.setattr(main, "engine", FakeEngine())
    with pytest.raises(HTTPException, match=r"Only \.csv"):
        asyncio.run(main.validate_csv(cast(Any, FakeRequest(filename="waveform.txt", content=b"sample_index,E,N,Z\n0,1,2,3\n"))))

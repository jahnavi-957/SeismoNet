"""FastAPI application for the local SeismoNet demonstration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.csv_processor import (
    MAX_FILE_SIZE_MB,
    MAX_ROWS,
    SAMPLING_RATE_HZ,
    CSVProcessor,
    ColumnMapping,
)
from backend.inference import SeismoInferenceEngine


class ColumnMappingRequest(BaseModel):
    e_col: Optional[str] = None
    n_col: Optional[str] = None
    z_col: Optional[str] = None
    trace_id_col: Optional[str] = None
    timestamp_col: Optional[str] = None
    p_arrival_col: Optional[str] = None
    s_arrival_col: Optional[str] = None
    sampling_rate_hz: float = SAMPLING_RATE_HZ
    arrival_coordinate_type: str = "sample_index"


class CSVValidationRequest(BaseModel):
    """Backward-compatible JSON contract for scripts and older local clients."""

    csv_content: str
    mapping: Optional[ColumnMappingRequest] = None


class CSVAnalysisRequest(BaseModel):
    """Backward-compatible JSON contract for scripts and older local clients."""

    csv_content: str
    mapping: Optional[ColumnMappingRequest] = None
    mode: str = "predict"


app = FastAPI(
    title="SeismoNet API",
    description="AI-powered seismic P- and S-wave phase picking backend",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
        "http://127.0.0.1:5176",
        "http://localhost:5176",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

ROOT_DIR = Path(__file__).resolve().parents[0].parent
engine = SeismoInferenceEngine(ROOT_DIR)
csv_processor = CSVProcessor(sampling_rate_hz=SAMPLING_RATE_HZ)


def _mapping_from_request(request: Optional[ColumnMappingRequest]) -> Optional[ColumnMapping]:
    if request is None:
        return None
    return ColumnMapping(
        e_col=request.e_col,
        n_col=request.n_col,
        z_col=request.z_col,
        trace_id_col=request.trace_id_col,
        timestamp_col=request.timestamp_col,
        p_arrival_col=request.p_arrival_col,
        s_arrival_col=request.s_arrival_col,
        sampling_rate_hz=request.sampling_rate_hz,
        arrival_coordinate_type=request.arrival_coordinate_type,
    )


def _mapping_request_from_payload(payload: Any) -> Optional[ColumnMappingRequest]:
    if payload in (None, "", {}):
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="mapping must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="mapping must be an object")
    try:
        return ColumnMappingRequest(**payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid mapping: {exc}") from exc


async def _read_csv_request(request: Request, *, require_mode: bool = False) -> tuple[str, Optional[ColumnMappingRequest], str, str | None]:
    """Read multipart uploads and the legacy JSON body without duplicating route logic."""
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        uploaded = form.get("file") or form.get("csv_file")
        filename: str | None = None
        if uploaded is not None and not isinstance(uploaded, str) and hasattr(uploaded, "read"):
            filename = getattr(uploaded, "filename", None)
            if filename and Path(filename).suffix.lower() != ".csv":
                raise HTTPException(status_code=400, detail="Only .csv uploads are supported")
            content_bytes = await uploaded.read()
        else:
            raw_content = form.get("csv_content")
            if raw_content is None:
                raise HTTPException(status_code=400, detail="Multipart request must include a CSV file")
            content_bytes = str(raw_content).encode("utf-8")
        if len(content_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"CSV exceeds the {MAX_FILE_SIZE_MB} MB limit")
        try:
            csv_content = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="CSV must be UTF-8 text") from exc
        mapping_payload = form.get("mapping") or form.get("mapping_json")
        mapping = _mapping_request_from_payload(mapping_payload)
        mode = str(form.get("mode") or "predict")
        return csv_content, mapping, mode, filename

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Expected multipart/form-data or a JSON body") from exc
    request_model: CSVValidationRequest | CSVAnalysisRequest
    if require_mode:
        request_model = CSVAnalysisRequest(**body)
    else:
        request_model = CSVValidationRequest(**body)
    content_bytes = request_model.csv_content.encode("utf-8")
    if len(content_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"CSV exceeds the {MAX_FILE_SIZE_MB} MB limit")
    mode = request_model.mode if isinstance(request_model, CSVAnalysisRequest) else "predict"
    return request_model.csv_content, request_model.mapping, mode, None


@app.post("/api/csv/validate", openapi_extra={"description": "Upload a UTF-8 CSV as multipart field 'file'."})
async def validate_csv(request: Request) -> dict[str, Any]:
    """Validate a CSV upload and return detected columns plus a small preview."""
    try:
        csv_content, mapping_request, _, _ = await _read_csv_request(request)
        result = csv_processor.validate_csv(csv_content, _mapping_from_request(mapping_request))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Validation error: {exc}") from exc


@app.post("/api/csv/analyze", openapi_extra={"description": "Analyze a CSV upload as multipart field 'file'."})
async def analyze_csv(request: Request) -> dict[str, Any]:
    """Run frozen inference and optional reference comparison on uploaded waveforms."""
    try:
        csv_content, mapping_request, mode, _ = await _read_csv_request(request, require_mode=True)
        if mode not in {"predict", "compare"}:
            raise HTTPException(status_code=400, detail="mode must be 'predict' or 'compare'")
        mapping = _mapping_from_request(mapping_request)
        validation_result = csv_processor.validate_csv(csv_content, mapping)
        if not validation_result.get("is_valid"):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": validation_result.get("error", "CSV validation failed"),
                    "validation": validation_result,
                },
            )
        resolved_mapping = mapping or ColumnMapping()
        waveforms, metadata, extraction_errors = csv_processor.extract_waveforms(csv_content, resolved_mapping)
        if extraction_errors:
            raise HTTPException(
                status_code=400,
                detail={"message": "CSV extraction failed", "errors": extraction_errors},
            )
        if not waveforms:
            raise HTTPException(status_code=400, detail="No valid waveform traces were extracted")
        prediction_result = csv_processor.predict_waveforms(waveforms, engine, metadata)
        if not prediction_result["predictions"]:
            raise HTTPException(
                status_code=422,
                detail={"message": "Inference returned no predictions", "warnings": prediction_result["warnings"]},
            )

        response: dict[str, Any] = {
            "mode": mode,
            "predictions": prediction_result["predictions"],
            "warnings": prediction_result["warnings"],
            "trace_count": len(prediction_result["predictions"]),
            "input_sampling_rate_hz": resolved_mapping.sampling_rate_hz,
            "effective_sampling_rate_hz": engine.sampling_rate_hz,
            "protocol": {
                "protocol_id": engine.protocol_id,
                "p_threshold": engine.picking_cfg.p_threshold,
                "s_threshold": engine.picking_cfg.s_threshold,
                "matching_tolerance_samples": engine.picking_cfg.matching_tolerance_samples,
                "sampling_rate_hz": engine.sampling_rate_hz,
            },
        }
        if mode == "compare":
            if not validation_result.get("has_reference_labels"):
                raise HTTPException(
                    status_code=400,
                    detail="Comparison mode requires at least one reference P/S arrival column",
                )
            comparison = csv_processor.compare_predictions(
                prediction_result["predictions"], metadata, tolerance_samples=engine.picking_cfg.matching_tolerance_samples
            )
            response.update(comparison)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis error: {exc}") from exc


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "online",
        "model": "SeismoUnet1d",
        "device": str(engine.device),
        "data_source": engine.data_source,
        "real_dataset_available": engine.real_dataset_available,
        "checkpoint_available": engine.checkpoint_path.is_file(),
        "checkpoint": str(engine.checkpoint_path.relative_to(ROOT_DIR)),
        "protocol_id": engine.protocol_id,
        "sampling_rate_hz": engine.sampling_rate_hz,
        "window_length": engine.window_length,
    }


@app.get("/api/traces")
async def get_traces() -> list[dict[str, Any]]:
    try:
        return engine.get_available_traces()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/analyze/{trace_id}")
async def analyze_trace(trace_id: str) -> dict[str, Any]:
    try:
        return engine.analyze_trace(trace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _metric_payload(metrics: dict[str, Any], split: str, note: str) -> dict[str, Any]:
    p_wave = metrics["P"]["detection"]
    s_wave = metrics["S"]["detection"]
    return {
        "evaluation_split": split,
        "n_traces": metrics.get("n_traces"),
        "n_events": metrics.get("n_events"),
        "matching_tolerance_samples": metrics.get("matching_tolerance_samples", engine.picking_cfg.matching_tolerance_samples),
        "sampling_rate_hz": metrics.get("sampling_rate_hz", engine.sampling_rate_hz),
        "p_wave": {key: p_wave[key] for key in ("f1", "precision", "recall", "tp", "fp", "fn")},
        "s_wave": {key: s_wave[key] for key in ("f1", "precision", "recall", "tp", "fp", "fn")},
        "protocol_id": engine.protocol_id,
        "p_threshold": engine.picking_cfg.p_threshold,
        "s_threshold": engine.picking_cfg.s_threshold,
        "note": note,
    }


@app.get("/api/metrics")
async def get_metrics() -> dict[str, Any]:
    test_path = ROOT_DIR / "runs" / "eval_test_best" / "metrics.json"
    if test_path.is_file():
        metrics = json.loads(test_path.read_text(encoding="utf-8"))
        return _metric_payload(
            metrics,
            "test",
            "Held-out test results from the frozen checkpoint under a protocol selected on validation; "
            "do not interpret F1 as accuracy.",
        )

    run_path = ROOT_DIR / "runs" / "experiment_002_p_training" / "run.json"
    if run_path.is_file():
        run = json.loads(run_path.read_text(encoding="utf-8"))
        best = run["best_metrics"]
        return {
            "evaluation_split": "validation",
            "n_traces": run["dataset"].get("selected_validation_trace_count"),
            "n_events": len(run["dataset"].get("selected_validation_events", [])),
            "matching_tolerance_samples": engine.picking_cfg.matching_tolerance_samples,
            "sampling_rate_hz": engine.sampling_rate_hz,
            "p_wave": {
                "f1": best["val_p_f1"], "precision": best["val_p_precision"], "recall": best["val_p_recall"],
                "tp": best["val_p_tp"], "fp": best["val_p_fp"], "fn": best["val_p_fn"],
            },
            "s_wave": {
                "f1": best["val_s_f1"], "precision": best["val_s_precision"], "recall": best["val_s_recall"],
                "tp": best["val_s_tp"], "fp": best["val_s_fp"], "fn": best["val_s_fn"],
            },
            "protocol_id": engine.protocol_id,
            "p_threshold": engine.picking_cfg.p_threshold,
            "s_threshold": engine.picking_cfg.s_threshold,
            "note": "Validation metrics from Experiment 002; epoch and thresholds were selected on validation and may be optimistic. F1 is not accuracy.",
        }
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No verified evaluation artifact is available")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

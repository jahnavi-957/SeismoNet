"""CSV waveform validation, preprocessing, inference, and comparison.

The browser upload path deliberately shares the frozen model contract with the research pipeline:
CSV rows are interpreted as ENZ samples, normalized with per-window demean/global-peak scaling,
converted to a 3,072-sample 100 Hz window, and sent to the existing Python inference engine.
Uploaded files are never added to a dataset split or written into experiment artifacts.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from seismonet.metrics import classify_picks
from seismonet.validation import validate_waveform


MAX_FILE_SIZE_MB = 50
MAX_ROWS = 100000
SAMPLING_RATE_HZ = 100.0
WINDOW_LENGTH = 3072
MIN_WAVEFORM_LENGTH = WINDOW_LENGTH


@dataclass
class ColumnMapping:
    """User-provided CSV column mapping."""

    e_col: Optional[str] = None
    n_col: Optional[str] = None
    z_col: Optional[str] = None
    trace_id_col: Optional[str] = None
    timestamp_col: Optional[str] = None
    p_arrival_col: Optional[str] = None
    s_arrival_col: Optional[str] = None
    sampling_rate_hz: float = SAMPLING_RATE_HZ
    arrival_coordinate_type: str = "sample_index"


def _clean_column(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _finite_float(value: Any, label: str) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not np.isfinite(parsed):
        raise ValueError(f"{label} must be finite")
    return parsed


class CSVProcessor:
    """Process one supported CSV file or a clearly grouped set of CSV traces."""

    def __init__(self, sampling_rate_hz: float = SAMPLING_RATE_HZ):
        self.sampling_rate_hz = float(sampling_rate_hz)
        self.tolerance_samples = 20

    def _read_rows(self, csv_content: str) -> tuple[list[str], list[dict[str, str]]]:
        if not isinstance(csv_content, str) or not csv_content.strip():
            raise ValueError("CSV is empty")
        reader = csv.DictReader(io.StringIO(csv_content))
        if not reader.fieldnames:
            raise ValueError("CSV is empty or has no headers")
        fieldnames = [str(name).strip().lstrip("\ufeff") for name in reader.fieldnames]
        if any(not name for name in fieldnames):
            raise ValueError("CSV contains an empty column name")
        reader.fieldnames = fieldnames
        rows = list(reader)
        return fieldnames, rows

    def _resolve_mapping(
        self, fieldnames: list[str], mapping: Optional[ColumnMapping]
    ) -> tuple[ColumnMapping, dict[str, Optional[str]]]:
        detected = self._detect_columns(set(fieldnames))
        requested = mapping or ColumnMapping()
        resolved = ColumnMapping(
            e_col=_clean_column(requested.e_col) or detected.get("e_col"),
            n_col=_clean_column(requested.n_col) or detected.get("n_col"),
            z_col=_clean_column(requested.z_col) or detected.get("z_col"),
            trace_id_col=_clean_column(requested.trace_id_col) or detected.get("trace_id_col"),
            timestamp_col=_clean_column(requested.timestamp_col) or detected.get("timestamp_col"),
            p_arrival_col=_clean_column(requested.p_arrival_col) or detected.get("p_arrival_col"),
            s_arrival_col=_clean_column(requested.s_arrival_col) or detected.get("s_arrival_col"),
            sampling_rate_hz=requested.sampling_rate_hz,
            arrival_coordinate_type=requested.arrival_coordinate_type,
        )
        return resolved, detected

    def _validate_mapping(self, fieldnames: list[str], mapping: ColumnMapping) -> list[str]:
        errors: list[str] = []
        required = {"e_col": mapping.e_col, "n_col": mapping.n_col, "z_col": mapping.z_col}
        missing = [name for name, column in required.items() if not column]
        if missing:
            errors.append("Cannot map E, N, Z waveform components")
        for label, column in required.items():
            if column and column not in fieldnames:
                errors.append(f"Mapped {label} column {column!r} was not found in the CSV")
        for label, column in (
            ("trace_id", mapping.trace_id_col),
            ("timestamp", mapping.timestamp_col),
            ("P arrival", mapping.p_arrival_col),
            ("S arrival", mapping.s_arrival_col),
        ):
            if column and column not in fieldnames:
                errors.append(f"Mapped {label} column {column!r} was not found in the CSV")
        if mapping.arrival_coordinate_type not in {"sample_index", "time_seconds"}:
            errors.append("arrival_coordinate_type must be 'sample_index' or 'time_seconds'")
        try:
            rate = _finite_float(mapping.sampling_rate_hz, "sampling_rate_hz")
            if rate <= 0 or rate > 10000:
                errors.append("sampling_rate_hz must be greater than 0 and no more than 10,000")
        except ValueError as exc:
            errors.append(str(exc))
        return errors

    def validate_csv(self, csv_content: str, mapping: Optional[ColumnMapping] = None) -> dict[str, Any]:
        """Validate structure, values, labels, and the frozen 3,072-sample contract."""
        try:
            fieldnames, rows = self._read_rows(csv_content)
        except ValueError as exc:
            return {"is_valid": False, "error": str(exc), "detected_columns": {}, "errors": []}

        resolved, detected = self._resolve_mapping(fieldnames, mapping)
        mapping_errors = self._validate_mapping(fieldnames, resolved)
        if mapping_errors:
            return {
                "is_valid": False,
                "error": mapping_errors[0],
                "errors": mapping_errors,
                "detected_columns": detected,
                "columns": fieldnames,
                "row_count": len(rows),
            }
        if not rows:
            return {
                "is_valid": False,
                "error": "CSV contains headers but no data rows",
                "errors": ["CSV contains no waveform samples"],
                "detected_columns": detected,
                "columns": fieldnames,
                "row_count": 0,
            }
        if len(rows) > MAX_ROWS:
            return {
                "is_valid": False,
                "error": f"CSV exceeds the {MAX_ROWS:,}-row limit",
                "errors": [f"row_count={len(rows)} exceeds MAX_ROWS={MAX_ROWS}"],
                "detected_columns": detected,
                "columns": fieldnames,
                "row_count": len(rows),
            }

        errors: list[str] = []
        groups: dict[str, int] = {}
        previous_coordinate: dict[str, float] = {}
        p_values: dict[str, set[float]] = {}
        s_values: dict[str, set[float]] = {}
        preview: list[dict[str, Any]] = []
        for row_idx, row in enumerate(rows, start=1):
            group = (row.get(resolved.trace_id_col, "") if resolved.trace_id_col else "single").strip()
            if not group:
                errors.append(f"row {row_idx}: trace identifier is empty")
                continue
            groups[group] = groups.get(group, 0) + 1
            try:
                for label, column in (("E", resolved.e_col), ("N", resolved.n_col), ("Z", resolved.z_col)):
                    _finite_float(row.get(column or ""), f"{label} at row {row_idx}")
            except ValueError as exc:
                errors.append(str(exc))
            if resolved.timestamp_col:
                try:
                    coordinate = _finite_float(row.get(resolved.timestamp_col), "sample/time coordinate")
                    if group in previous_coordinate and coordinate <= previous_coordinate[group]:
                        errors.append(f"row {row_idx}: sample/time coordinate is not strictly increasing")
                    previous_coordinate[group] = coordinate
                except ValueError as exc:
                    errors.append(f"row {row_idx}: {exc}")
            for label, column, target in (
                ("P", resolved.p_arrival_col, p_values),
                ("S", resolved.s_arrival_col, s_values),
            ):
                raw = row.get(column or "", "").strip() if column else ""
                if raw:
                    try:
                        target.setdefault(group, set()).add(_finite_float(raw, f"{label} arrival"))
                    except ValueError as exc:
                        errors.append(f"row {row_idx}: {exc}")
            if len(preview) < 10:
                preview.append({name: row.get(name, "") for name in fieldnames})

        if any(len(values) > 1 for values in p_values.values()):
            errors.append("P arrival labels must be consistent within each trace")
        if any(len(values) > 1 for values in s_values.values()):
            errors.append("S arrival labels must be consistent within each trace")

        input_rate = float(resolved.sampling_rate_hz)
        single_length = next(iter(groups.values())) if groups else 0
        expected_rows = round(single_length * SAMPLING_RATE_HZ / input_rate)
        if len(groups) == 1 and expected_rows != WINDOW_LENGTH:
            errors.append(
                f"waveform must contain {WINDOW_LENGTH} samples at the effective 100 Hz rate "
                f"(received {len(rows)} rows at {input_rate:g} Hz; resampled length would be {expected_rows})"
            )
        if len(groups) > 1 and resolved.trace_id_col is None:
            errors.append("multiple independent traces require a trace-id column mapping")
        if len(groups) > 1:
            for group, count in groups.items():
                if round(count * SAMPLING_RATE_HZ / input_rate) != WINDOW_LENGTH:
                    errors.append(
                        f"trace {group!r} must resample to {WINDOW_LENGTH} samples; "
                        f"received {count} rows at {input_rate:g} Hz"
                    )

        has_reference_labels = bool(resolved.p_arrival_col or resolved.s_arrival_col)
        return {
            "is_valid": not errors,
            "errors": errors,
            "error": errors[0] if errors else None,
            "row_count": len(rows),
            "trace_count": len(groups),
            "has_reference_labels": has_reference_labels,
            "detected_columns": detected,
            "columns": fieldnames,
            "mapping": {
                "e_col": resolved.e_col,
                "n_col": resolved.n_col,
                "z_col": resolved.z_col,
                "trace_id_col": resolved.trace_id_col,
                "timestamp_col": resolved.timestamp_col,
                "p_arrival_col": resolved.p_arrival_col,
                "s_arrival_col": resolved.s_arrival_col,
                "sampling_rate_hz": input_rate,
                "arrival_coordinate_type": resolved.arrival_coordinate_type,
            },
            "preview": preview,
            "effective_sampling_rate_hz": SAMPLING_RATE_HZ,
            "resampling_required": not np.isclose(input_rate, SAMPLING_RATE_HZ),
        }

    def extract_waveforms(
        self, csv_content: str, mapping: ColumnMapping
    ) -> tuple[list[np.ndarray], list[dict[str, Any]], list[str]]:
        """Extract independent traces as normalized ENZ windows."""
        errors: list[str] = []
        try:
            fieldnames, rows = self._read_rows(csv_content)
            resolved, _ = self._resolve_mapping(fieldnames, mapping)
            errors.extend(self._validate_mapping(fieldnames, resolved))
            if errors:
                return [], [], errors
        except ValueError as exc:
            return [], [], [str(exc)]

        grouped: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            group = (row.get(resolved.trace_id_col, "") if resolved.trace_id_col else "single").strip()
            grouped.setdefault(group, []).append(row)

        waveforms: list[np.ndarray] = []
        metadata_list: list[dict[str, Any]] = []
        input_rate = float(resolved.sampling_rate_hz)
        for trace_id, trace_rows in grouped.items():
            try:
                e = np.asarray([_finite_float(row.get(resolved.e_col or ""), "E") for row in trace_rows], dtype=np.float32)
                n = np.asarray([_finite_float(row.get(resolved.n_col or ""), "N") for row in trace_rows], dtype=np.float32)
                z = np.asarray([_finite_float(row.get(resolved.z_col or ""), "Z") for row in trace_rows], dtype=np.float32)
                waveform = np.stack([e, n, z], axis=0)
                if not np.isclose(input_rate, SAMPLING_RATE_HZ):
                    target_length = round(waveform.shape[1] * SAMPLING_RATE_HZ / input_rate)
                    if target_length != WINDOW_LENGTH:
                        raise ValueError(
                            f"trace {trace_id!r} resamples to {target_length} samples, "
                            f"expected {WINDOW_LENGTH}"
                        )
                    old_axis = np.linspace(0.0, 1.0, waveform.shape[1])
                    new_axis = np.linspace(0.0, 1.0, target_length)
                    waveform = np.vstack(
                        [np.interp(new_axis, old_axis, channel) for channel in waveform]
                    ).astype(np.float32)
                if waveform.shape != (3, WINDOW_LENGTH):
                    raise ValueError(
                        f"trace {trace_id!r} has shape {waveform.shape}; the frozen model requires (3, {WINDOW_LENGTH})"
                    )

                waveform = waveform - np.mean(waveform, axis=1, keepdims=True)
                peak = float(np.abs(waveform).max())
                if peak <= 1e-12:
                    raise ValueError(f"trace {trace_id!r} is flat (zero variance)")
                waveform = waveform / peak
                validation = validate_waveform(
                    waveform,
                    expected_length=WINDOW_LENGTH,
                    sampling_rate=SAMPLING_RATE_HZ,
                    expected_rate=SAMPLING_RATE_HZ,
                )
                if not validation.ok:
                    raise ValueError(validation.detail)

                p_arrival = self._extract_reference(resolved.p_arrival_col, trace_rows, resolved, input_rate)
                s_arrival = self._extract_reference(resolved.s_arrival_col, trace_rows, resolved, input_rate)
                for label, arrival in (("P", p_arrival), ("S", s_arrival)):
                    if arrival is not None and not 0 <= arrival < WINDOW_LENGTH:
                        raise ValueError(f"{label} arrival {arrival} outside [0, {WINDOW_LENGTH})")
                if p_arrival is not None and s_arrival is not None and s_arrival <= p_arrival:
                    raise ValueError(f"S arrival {s_arrival} must be after P arrival {p_arrival}")

                waveforms.append(waveform.astype(np.float32))
                metadata_list.append(
                    {
                        "trace_id": trace_id,
                        "p_arrival_sample": p_arrival,
                        "s_arrival_sample": s_arrival,
                        "input_sampling_rate_hz": input_rate,
                        "effective_sampling_rate_hz": SAMPLING_RATE_HZ,
                        "row_count": len(trace_rows),
                    }
                )
            except (TypeError, ValueError) as exc:
                errors.append(str(exc))

        return waveforms, metadata_list, errors

    def _extract_reference(
        self,
        column: Optional[str],
        rows: list[dict[str, str]],
        mapping: ColumnMapping,
        input_rate: float,
    ) -> Optional[int]:
        if not column:
            return None
        values = [row.get(column, "").strip() for row in rows if row.get(column, "").strip()]
        if not values:
            return None
        raw = _finite_float(values[0], f"reference column {column}")
        sample = raw if mapping.arrival_coordinate_type == "sample_index" else raw * input_rate
        return int(round(sample * SAMPLING_RATE_HZ / input_rate))

    def predict_waveforms(
        self,
        waveforms: list[np.ndarray],
        inference_engine: Any,
        metadata: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run the existing frozen inference engine on each extracted waveform."""
        predictions: list[dict[str, Any]] = []
        warnings: list[str] = []
        for idx, waveform in enumerate(waveforms):
            try:
                result = inference_engine.infer_waveform(waveform)
                p_pick = result["picks"]["p"]
                s_pick = result["picks"]["s"]
                rate = float(result["sampling_rate_hz"])
                predictions.append(
                    {
                        "index": idx,
                        "trace_id": metadata[idx].get("trace_id", str(idx)),
                        "waveform": result["waveform"],
                        "probs": result["probs"],
                        "p_predicted_sample": p_pick["predicted"],
                        "s_predicted_sample": s_pick["predicted"],
                        "p_predicted_ms": self._sample_to_ms(p_pick["predicted"], rate),
                        "s_predicted_ms": self._sample_to_ms(s_pick["predicted"], rate),
                        "p_probability": p_pick["probability"],
                        "s_probability": s_pick["probability"],
                        "p_probability_curve": result["probs"]["p"],
                        "s_probability_curve": result["probs"]["s"],
                        "noise_probability_curve": result["probs"]["noise"],
                        "sampling_rate_hz": rate,
                        "protocol": result["protocol"],
                    }
                )
            except Exception as exc:  # one bad trace should not blank the whole page
                warnings.append(f"Inference error for waveform {idx}: {exc}")
        return {"predictions": predictions, "warnings": warnings}

    def compare_predictions(
        self,
        predictions: list[dict[str, Any]],
        metadata: list[dict[str, Any]],
        *,
        tolerance_samples: int | None = None,
    ) -> dict[str, Any]:
        """Compare predicted and reference picks using the frozen sample tolerance."""
        tolerance = self.tolerance_samples if tolerance_samples is None else int(tolerance_samples)
        comparisons: list[dict[str, Any]] = []
        for pred, meta in zip(predictions, metadata):
            comp: dict[str, Any] = {
                "index": pred["index"],
                "trace_id": meta.get("trace_id", str(pred["index"])),
                "p_predicted_sample": pred.get("p_predicted_sample"),
                "p_reference_sample": meta.get("p_arrival_sample"),
                "s_predicted_sample": pred.get("s_predicted_sample"),
                "s_reference_sample": meta.get("s_arrival_sample"),
            }
            for phase in ("p", "s"):
                predicted = comp[f"{phase}_predicted_sample"]
                reference = comp[f"{phase}_reference_sample"]
                residual = predicted - reference if predicted is not None and reference is not None else None
                comp[f"{phase}_residual_samples"] = residual
                comp[f"{phase}_residual_ms"] = self._sample_to_ms(residual, SAMPLING_RATE_HZ)
                comp[f"{phase}_within_tolerance"] = (
                    abs(residual) <= tolerance if residual is not None else None
                )
            comparisons.append(comp)

        p_pred = [self._sample_to_seconds(p.get("p_predicted_sample")) for p in predictions]
        p_ref = [self._sample_to_seconds(m.get("p_arrival_sample")) for m in metadata]
        s_pred = [self._sample_to_seconds(p.get("s_predicted_sample")) for p in predictions]
        s_ref = [self._sample_to_seconds(m.get("s_arrival_sample")) for m in metadata]
        tolerance_seconds = tolerance / SAMPLING_RATE_HZ
        metrics: dict[str, Any] = {}
        if any(value is not None for value in p_pred + p_ref):
            metrics["p_metrics"] = self._classification_dict(classify_picks(p_pred, p_ref, tolerance_seconds))
        if any(value is not None for value in s_pred + s_ref):
            metrics["s_metrics"] = self._classification_dict(classify_picks(s_pred, s_ref, tolerance_seconds))
        return {"comparisons": comparisons, "metrics": metrics}

    @staticmethod
    def _classification_dict(classification: Any) -> dict[str, Any]:
        return {
            "tp": classification.tp,
            "fp": classification.fp,
            "fn": classification.fn,
            "precision": classification.precision,
            "recall": classification.recall,
            "f1": classification.f1,
        }

    @staticmethod
    def _sample_to_ms(sample: Optional[int], rate: float) -> Optional[float]:
        return float(sample) * 1000.0 / rate if sample is not None else None

    @staticmethod
    def _sample_to_seconds(sample: Optional[int]) -> Optional[float]:
        return float(sample) / SAMPLING_RATE_HZ if sample is not None else None

    def _detect_columns(self, fieldnames: set[str]) -> dict[str, Optional[str]]:
        """Auto-detect supported waveform, grouping, coordinate, and label columns."""
        detected: dict[str, Optional[str]] = {}
        fieldnames_lower = {name.lower().strip(): name for name in fieldnames}
        aliases = [
            ("e_col", ["e", "east", "e_component"]),
            ("n_col", ["n", "north", "n_component"]),
            ("z_col", ["z", "vertical", "z_component"]),
            ("trace_id_col", ["trace_id", "trace", "station", "trace_name"]),
            ("timestamp_col", ["sample_index", "sample", "timestamp", "time", "time_seconds"]),
            ("p_arrival_col", ["p_arrival", "p_arrival_sample", "p_pick", "p_reference"]),
            ("s_arrival_col", ["s_arrival", "s_arrival_sample", "s_pick", "s_reference"]),
        ]
        for key, names in aliases:
            for alias in names:
                if alias in fieldnames_lower:
                    detected[key] = fieldnames_lower[alias]
                    break
        return detected

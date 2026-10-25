import torch
import numpy as np
import json
import yaml
import csv
import zlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from seismonet.model import SeismoUnet1d
from seismonet.dataset import InstanceDataset
from seismonet.picking import PeakPickingConfig, pick_phase_diagnostics

class SeismoInferenceEngine:
    def __init__(self, root_path: Path):
        self.root = root_path
        self.device = torch.device("cpu")

        # Paths from the Master Prompt
        self.checkpoint_path = self.root / "runs" / "experiment_002_p_training" / "best.pt"
        self.pilot_run_path = self.root / "runs" / "pilot_seed42" / "run.json"
        self.protocol_path = self.root / "runs" / "validation_protocol_candidate_seed42" / "protocol.json"
        self.config_path = self.root / "runs" / "pilot_seed42" / "config_snapshot.yaml"
        self.demo_predictions_path = self.root / "runs" / "validation_inference_p6_seed42" / "predictions.json"
        self.demo_fixture_path = self.root / "backend" / "demo_traces.json"

        # Load Model
        self.model = SeismoUnet1d(base=16, depth=4).to(self.device)
        state = torch.load(self.checkpoint_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.eval()

        # Load Protocol
        self.protocol = json.loads(self.protocol_path.read_text(encoding="utf-8"))
        self.picking_cfg = PeakPickingConfig(
            p_threshold=self.protocol["picking"]["p_threshold"],
            s_threshold=self.protocol["picking"]["s_threshold"],
            min_peak_distance_samples=self.protocol["picking"]["min_peak_distance_samples"],
            matching_tolerance_samples=self.protocol["picking"]["matching_tolerance_samples"],
        )

        # Load Global Config
        self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        self.window_length = int(self.config["input_shape"][2])
        self.sampling_rate_hz = float(self.protocol.get("sampling_rate_hz", 100.0))
        self.protocol_id = str(self.protocol.get("protocol_id", "unknown"))

        dataset = self.config["dataset"]
        self.hdf5_path = Path(dataset["hdf5"])
        self.metadata_csv_path = Path(dataset["metadata_csv"])
        self.real_dataset_available = self.hdf5_path.is_file() and self.metadata_csv_path.is_file()
        self.data_source = "real_dataset" if self.real_dataset_available else "synthetic_demo_fallback"
        self._demo_rows: Optional[List[Dict[str, Any]]] = None

    def infer_waveform(self, waveform: np.ndarray) -> Dict[str, Any]:
        """Run the frozen model and picking protocol on one normalized ENZ window.

        Uploaded CSVs use the same channel order as ``InstanceDataset``: E, N, Z. The caller is
        responsible for validating and normalizing the input before calling this method. Keeping
        the model call and protocol-owned pick extraction here prevents the CSV path from silently
        developing a second inference implementation.
        """
        values = np.asarray(waveform, dtype=np.float32)
        expected_shape = (3, self.window_length)
        if values.shape != expected_shape:
            raise ValueError(f"expected normalized waveform shape {expected_shape}, got {values.shape}")
        if not np.isfinite(values).all():
            raise ValueError("waveform contains NaN or Inf")

        with torch.no_grad():
            tensor = torch.from_numpy(values).unsqueeze(0).to(self.device)
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

        p_diag = pick_phase_diagnostics(
            probs[0],
            threshold=self.picking_cfg.p_threshold,
            min_peak_distance_samples=self.picking_cfg.min_peak_distance_samples,
        )
        s_diag = pick_phase_diagnostics(
            probs[1],
            threshold=self.picking_cfg.s_threshold,
            min_peak_distance_samples=self.picking_cfg.min_peak_distance_samples,
        )

        return {
            "waveform": values.tolist(),
            "probs": {
                "p": probs[0].tolist(),
                "s": probs[1].tolist(),
                "noise": probs[2].tolist(),
            },
            "picks": {
                "p": {
                    "predicted": p_diag.pick.index if p_diag.pick else None,
                    "probability": p_diag.pick.probability if p_diag.pick else None,
                },
                "s": {
                    "predicted": s_diag.pick.index if s_diag.pick else None,
                    "probability": s_diag.pick.probability if s_diag.pick else None,
                },
            },
            "window_length": self.window_length,
            "sampling_rate_hz": self.sampling_rate_hz,
            "protocol": {
                "protocol_id": self.protocol_id,
                "p_threshold": self.picking_cfg.p_threshold,
                "s_threshold": self.picking_cfg.s_threshold,
                "matching_tolerance_samples": self.picking_cfg.matching_tolerance_samples,
                "min_peak_distance_samples": self.picking_cfg.min_peak_distance_samples,
            },
        }

    @staticmethod
    def _optional_int(value: Any) -> Optional[int]:
        if value in (None, "", "null"):
            return None
        return int(float(value))

    def _load_demo_rows(self) -> List[Dict[str, Any]]:
        if self._demo_rows is None:
            source = self.demo_predictions_path if self.demo_predictions_path.is_file() else self.demo_fixture_path
            if not source.is_file():
                raise RuntimeError(
                    "The real seismic dataset is unavailable and the tracked demo predictions "
                    f"file is missing: {self.demo_predictions_path}; fixture: {self.demo_fixture_path}"
                )
            self._demo_rows = json.loads(source.read_text(encoding="utf-8"))
        assert self._demo_rows is not None
        return self._demo_rows

    def _get_demo_trace(self, trace_id: str) -> Dict[str, Any]:
        for row in self._load_demo_rows():
            if row.get("trace_name") == trace_id:
                return row
        raise ValueError(f"Trace {trace_id} not found in the demo validation traces.")

    def get_available_traces(self) -> List[Dict[str, Any]]:
        if not self.real_dataset_available:
            return [
                {
                    "trace_id": row["trace_name"],
                    "event_id": row.get("event_id", ""),
                    "p_ref": str(row.get("reference_absolute", {}).get("P") or ""),
                    "s_ref": str(row.get("reference_absolute", {}).get("S") or ""),
                    "data_source": "synthetic_demo_fallback",
                }
                for row in self._load_demo_rows()
            ]

        pilot = json.loads(self.pilot_run_path.read_text(encoding="utf-8"))
        metadata_csv = Path(pilot["dataset"]["metadata_csv"])
        val_events = set(pilot["dataset"]["selected_validation_events"])

        traces = []
        with open(metadata_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("source_id", "").strip() in val_events:
                    traces.append({
                        "trace_id": r["trace_name"],
                        "event_id": r.get("source_id", ""),
                    "p_ref": r.get("trace_P_arrival_sample", ""),
                    "s_ref": r.get("trace_S_arrival_sample", ""),
                    "data_source": "real_dataset",
                })
        return traces

    def analyze_trace(self, trace_id: str) -> Dict[str, Any]:
        if not self.real_dataset_available:
            return self._analyze_demo_trace(trace_id)

        pilot = json.loads(self.pilot_run_path.read_text(encoding="utf-8"))

        # Use InstanceDataset to handle windowing and loading
        ds = InstanceDataset(
            Path(pilot["dataset"]["hdf5"]),
            Path(pilot["dataset"]["metadata_csv"]),
            window_length=self.window_length,
            sigma=20.0,
            depth=4,
            training=False,
            seed=42,
            trace_names=[trace_id],
            pure_noise_fraction=0.0,
        )

        if len(ds) == 0:
            raise ValueError(f"Trace {trace_id} not found in validation set.")

        sample = ds[0]
        waveform = sample["waveform"].numpy()
        w_start = int(sample["window_start"])

        # Inference
        with torch.no_grad():
            logits = self.model(torch.from_numpy(waveform).unsqueeze(0).float().to(self.device))
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

        # Picking
        p_diag = pick_phase_diagnostics(probs[0], threshold=self.picking_cfg.p_threshold, min_peak_distance_samples=self.picking_cfg.min_peak_distance_samples)
        s_diag = pick_phase_diagnostics(probs[1], threshold=self.picking_cfg.s_threshold, min_peak_distance_samples=self.picking_cfg.min_peak_distance_samples)

        # Metadata for results
        meta_rows = list(csv.DictReader(open(Path(pilot["dataset"]["metadata_csv"]), encoding="utf-8")))
        meta = next((r for r in meta_rows if r["trace_name"] == trace_id), {})

        p_abs = int(float(meta.get("trace_P_arrival_sample", 0))) if meta.get("trace_P_arrival_sample") else None
        s_abs = int(float(meta.get("trace_S_arrival_sample", 0))) if meta.get("trace_S_arrival_sample") else None

        return {
            "trace_id": trace_id,
            "event_id": meta.get("source_id", ""),
            "waveform": waveform.tolist(), # (3, L)
            "probs": {
                "p": probs[0].tolist(),
                "s": probs[1].tolist(),
                "noise": probs[2].tolist(),
            },
            "picks": {
                "p": {
                    "predicted": w_start + p_diag.pick.index if p_diag.pick else None,
                    "reference": p_abs,
                    "probability": p_diag.pick.probability if p_diag.pick else None,
                },
                "s": {
                    "predicted": w_start + s_diag.pick.index if s_diag.pick else None,
                    "reference": s_abs,
                    "probability": s_diag.pick.probability if s_diag.pick else None,
                }
            },
            "window_start": w_start,
            "window_length": self.window_length,
            "sampling_rate": 100,
            "data_source": "real_dataset",
            "inference_mode": "model",
        }

    def _analyze_demo_trace(self, trace_id: str) -> Dict[str, Any]:
        """Return a clearly-labelled deterministic demo when raw HDF5 data is absent.

        The repository contains the frozen validation predictions and reference picks, but the
        raw 10k-trace HDF5 sample lives outside version control. This fallback keeps the web demo
        testable without presenting synthetic waveforms as a scientific re-evaluation.
        """
        row = self._get_demo_trace(trace_id)
        window_start = int(row.get("window_start", 0))
        window_length = int(row.get("window_length", self.window_length))
        refs = row.get("reference_relative", {})
        p_ref = self._optional_int(refs.get("P"))
        s_ref = self._optional_int(refs.get("S"))

        seed = zlib.crc32(trace_id.encode("utf-8"))
        rng = np.random.default_rng(seed)
        x = np.arange(window_length, dtype=np.float32)
        waveform = rng.normal(0.0, 0.035, size=(3, window_length)).astype(np.float32)

        def add_wavelet(channel: int, center: Optional[int], amplitude: float, frequency: float) -> None:
            if center is None or center < 0 or center >= window_length:
                return
            envelope = np.exp(-0.5 * ((x - center) / 28.0) ** 2)
            carrier = np.sin(2.0 * np.pi * frequency * (x - center) / 100.0)
            waveform[channel] += amplitude * envelope * carrier

        add_wavelet(2, p_ref, 0.65, 8.0)
        add_wavelet(0, s_ref, 0.85, 5.0)
        add_wavelet(1, s_ref, 0.70, 6.0)

        def probability_curve(center: Optional[int], amplitude: float, width: float) -> np.ndarray:
            if center is None:
                return np.full(window_length, 0.01, dtype=np.float32)
            return (0.01 + amplitude * np.exp(-0.5 * ((x - center) / width) ** 2)).astype(np.float32)

        p_curve = probability_curve(p_ref, 0.86, 22.0)
        s_curve = probability_curve(s_ref, 0.78, 30.0)
        noise_curve = np.full(window_length, 0.12, dtype=np.float32)
        probs = np.stack([p_curve, s_curve, noise_curve], axis=0)
        probs /= probs.sum(axis=0, keepdims=True)

        p_diag = pick_phase_diagnostics(
            probs[0],
            threshold=self.picking_cfg.p_threshold,
            min_peak_distance_samples=self.picking_cfg.min_peak_distance_samples,
        )
        s_diag = pick_phase_diagnostics(
            probs[1],
            threshold=self.picking_cfg.s_threshold,
            min_peak_distance_samples=self.picking_cfg.min_peak_distance_samples,
        )

        return {
            "trace_id": trace_id,
            "event_id": row.get("event_id", ""),
            "waveform": waveform.tolist(),
            "probs": {
                "p": probs[0].tolist(),
                "s": probs[1].tolist(),
                "noise": probs[2].tolist(),
            },
            "picks": {
                "p": {
                    "predicted": window_start + p_diag.pick.index if p_diag.pick else None,
                    "reference": window_start + p_ref if p_ref is not None else None,
                    "probability": p_diag.pick.probability if p_diag.pick else None,
                },
                "s": {
                    "predicted": window_start + s_diag.pick.index if s_diag.pick else None,
                    "reference": window_start + s_ref if s_ref is not None else None,
                    "probability": s_diag.pick.probability if s_diag.pick else None,
                },
            },
            "window_start": window_start,
            "window_length": window_length,
            "sampling_rate": 100,
            "data_source": "synthetic_demo_fallback",
            "inference_mode": "synthetic_demo",
        }

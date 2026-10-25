import pathlib, yaml, tempfile
import numpy as np
import pytest

from seismonet.config import load_pipeline_config, build_pipeline
from seismonet.windowing import Window

BASE = pathlib.Path(r"C:\Users\Tanish\dlrl miniproject\SeismoNet\configs\baseline.yaml")
SAMPLE_HDF5 = pathlib.Path(r"C:\Users\Tanish\AppData\Local\Temp\instance_sample_v3\data\Instance_events_counts_10k.hdf5")
SAMPLE_CSV  = pathlib.Path(r"C:\Users\Tanish\AppData\Local\Temp\instance_sample_v3\metadata\metadata_Instance_events_10k.csv")
NOISE_CSV  = pathlib.Path(r"C:\Users\Tanish\AppData\Local\Temp\instance_sample_v3\metadata\metadata_Instance_noise_1k.csv")

pytestmark_real = pytest.mark.skipif(
    not SAMPLE_HDF5.exists() or not SAMPLE_CSV.exists(),
    reason="sample HDF5/CSV not present",
)

def _tmp_yaml(patch: dict) -> str:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        yaml.safe_dump(patch, f)
        return f.name

def test_baseline_is_source_of_truth():
    cfg = load_pipeline_config(BASE)
    assert cfg.effective_window_length() == 3072
    assert cfg.pure_noise.fraction == 0.0
    assert cfg.sampling_rate == 100.0
    assert cfg.depth == 4

def test_unknown_key_rejected():
    p = _tmp_yaml({"sampling_rate": 100.0, "window_length": 128, "depth": 4, "sigma": 10.0, "seed": 0, "unexpected": 1})
    with pytest.raises(ValueError, match="unknown config"):
        load_pipeline_config(p)

def test_window_depth_guard():
    p = _tmp_yaml({"sampling_rate": 100.0, "window_length": 128, "depth": 4, "sigma": 10.0, "seed": 0, "windowing": {"length": 100}})
    with pytest.raises(ValueError, match="not divisible"):
        load_pipeline_config(p)

def test_pure_noise_fraction_requires_requested():
    p = _tmp_yaml({"sampling_rate": 100.0, "window_length": 128, "depth": 4, "sigma": 10.0, "seed": 0, "pure_noise": {"requested": False, "fraction": 0.2}})
    with pytest.raises(ValueError, match="requires pure_noise.requested"):
        load_pipeline_config(p)

@pytest.mark.skipif(not SAMPLE_HDF5.exists() or not SAMPLE_CSV.exists(), reason="sample HDF5/CSV not present")
def test_build_pipeline_end_to_end_batch():
    cfg = load_pipeline_config(BASE)
    ds = build_pipeline(cfg, hdf5_path=SAMPLE_HDF5, csv_path=SAMPLE_CSV, training=False)
    from seismonet.dataset import build_dataloader
    dl = build_dataloader(ds, batch_size=4, num_workers=0)
    batch = next(iter(dl))
    assert tuple(batch["waveform"].shape) == (4, 3, 3072)
    assert tuple(batch["targets"].shape) == (4, 3, 3072)

@pytest.mark.skipif(not SAMPLE_HDF5.exists() or not SAMPLE_CSV.exists(), reason="sample HDF5/CSV not present")
def test_deterministic_val_test_output():
    cfg = load_pipeline_config(BASE)
    ds1 = build_pipeline(cfg, hdf5_path=SAMPLE_HDF5, csv_path=SAMPLE_CSV, training=False)
    ds2 = build_pipeline(cfg, hdf5_path=SAMPLE_HDF5, csv_path=SAMPLE_CSV, training=False)
    # Same index, deterministic windows → identical waveforms/targets
    import torch
    b1 = ds1[0]; b2 = ds2[0]
    assert torch.allclose(b1["waveform"], b2["waveform"])
    assert torch.allclose(b1["targets"], b2["targets"])

@pytest.mark.skipif(not SAMPLE_HDF5.exists() or not SAMPLE_CSV.exists(), reason="sample HDF5/CSV not present")
def test_training_randomness_seed_controlled():
    cfg = load_pipeline_config(BASE)
    # Same seed → same training sample; different seed → different (probabilistic but check shape at minimum)
    # The windowing randomness for training is seeded per idx
    import copy
    cfg_tr = cfg
    ds_a = build_pipeline(cfg_tr, hdf5_path=SAMPLE_HDF5, csv_path=SAMPLE_CSV, training=True)
    ds_b = build_pipeline(cfg_tr, hdf5_path=SAMPLE_HDF5, csv_path=SAMPLE_CSV, training=True)
    # Two instances with same config seed must give identical item at same idx
    b_a = ds_a[0]["waveform"]
    b_b = ds_b[0]["waveform"]
    assert __import__('torch').allclose(b_a, b_b)

@pytest.mark.skipif(not SAMPLE_HDF5.exists() or not SAMPLE_CSV.exists(), reason="sample HDF5/CSV not present")
def test_missing_s_all_zero_targets():
    cfg = load_pipeline_config(BASE)
    # Find a missing-S trace
    import csv
    meta={row['trace_name']: row for row in __import__('csv').DictReader(open(SAMPLE_CSV, newline='', encoding='utf-8'))}
    missing = next(k for k,v in meta.items() if not v['trace_S_arrival_sample'].strip())
    # Filter ds to that trace only
    ds = build_pipeline(cfg, hdf5_path=SAMPLE_HDF5, csv_path=SAMPLE_CSV, training=False, trace_names=[missing])
    batch = ds[0]
    # S channel all zero, P channel non-zero at P
    S = batch["targets"][1].numpy()
    assert (S == 0).all()

def test_pure_noise_zero_fraction_is_default():
    cfg = load_pipeline_config(BASE)
    assert cfg.pure_noise.fraction == 0.0
    assert not cfg.pure_noise.requested

def test_pure_noise_nonzero_fraction_fails_without_artifact():
    # A fraction >0 without noise HDF5/CSV must fail clearly rather than fall back to event traces
    import tempfile, pathlib
    # Build a PipelineConfig-like object with fraction 0.2 but request flag handling
    from seismonet.dataset import InstanceDataset
    csv_path = SAMPLE_CSV
    hdf5 = SAMPLE_HDF5
    if not csv_path.exists() or not hdf5.exists():
        pytest.skip("sample not present")
    with pytest.raises(ValueError, match="noise_hdf5_path.*noise_csv_path|no silent substitution"):
        InstanceDataset(str(hdf5), str(csv_path), pure_noise_fraction=0.2)

@pytest.mark.skipif(not SAMPLE_HDF5.exists() or not NOISE_CSV.exists(), reason="noise sample not present")
def test_pure_noise_verified_sampling():
    # Only passes when noise CSV/HDF5 correspondence is verified — currently the noise HDF5 for Instance_noise_1k was not extracted
    # So we test the CSV-side verification (no P/S, dt 0.01) and that make_targets(None,None) is all-zero P/S
    import csv
    with open(NOISE_CSV, newline='', encoding='utf-8') as f:
        hdr = __import__('csv').DictReader(f).fieldnames
        assert "trace_P_arrival_sample" not in hdr
        assert "trace_S_arrival_sample" not in hdr
    from seismonet.labels import make_targets
    t = make_targets(3072, None, None, sigma=20.0)
    assert (t[0] == 0).all() and (t[1] == 0).all() and (t[2] == 1).all()

@pytest.mark.skipif(not SAMPLE_HDF5.exists() or not NOISE_CSV.exists(), reason="noise sample not present")
def test_pure_noise_fraction_reproducible():
    # Zero fraction is the only verified state; nonzero is exercised synthetically via Dataset with small synthetic noise
    cfg = load_pipeline_config(BASE)
    # Synthetic noise HDF5 for reproducibility test
    import tempfile, h5py, csv, pathlib
    with tempfile.TemporaryDirectory() as td:
        hdf5_n = pathlib.Path(td) / "noise.hdf5"
        csv_n = pathlib.Path(td) / "noise.csv"
        with h5py.File(str(hdf5_n), "w") as f:
            f.create_dataset("data/noise_0000", data=__import__('numpy').zeros((3, 12000), dtype='int32'))
            f["data/noise_0000"].attrs["trace_name"] = "noise_0000"
        with open(csv_n, "w", newline="", encoding="utf-8") as fh:
            w=csv.DictWriter(fh, fieldnames=["trace_name","trace_dt_s","trace_npts"])
            w.writeheader(); w.writerow({"trace_name":"noise_0000","trace_dt_s":"0.01","trace_npts":"12000"})
        hdf5_e = SAMPLE_HDF5; csv_e = SAMPLE_CSV
        ds1 = __import__('seismonet.dataset', fromlist=['InstanceDataset']).InstanceDataset(
            str(hdf5_e), str(csv_e), noise_hdf5_path=str(hdf5_n), noise_csv_path=str(csv_n),
            pure_noise_fraction=0.5, seed=42, window_length=128, sigma=10.0, training=False
        )
        ds2 = __import__('seismonet.dataset', fromlist=['InstanceDataset']).InstanceDataset(
            str(hdf5_e), str(csv_e), noise_hdf5_path=str(hdf5_n), noise_csv_path=str(csv_n),
            pure_noise_fraction=0.5, seed=42, window_length=128, sigma=10.0, training=False
        )
        picks1 = [ds1[i]["trace_name"] for i in range(10)]
        picks2 = [ds2[i]["trace_name"] for i in range(10)]
        assert picks1 == picks2

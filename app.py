import streamlit as st
import torch
import numpy as np
import matplotlib.pyplot as plt
import json
import yaml
import csv
import h5py
from pathlib import Path
from seismonet.model import SeismoUnet1d
from seismonet.dataset import InstanceDataset
from seismonet.picking import PeakPickingConfig, pick_phase_diagnostics

# --- CONFIGURATION & PATHS ---
ROOT = Path(__file__).resolve().parents[0]
CHECKPOINT_PATH = ROOT / "runs" / "experiment_002_p_training" / "best.pt"
PILOT_RUN_PATH = ROOT / "runs" / "pilot_seed42" / "run.json"
PROTOCOL_PATH = ROOT / "runs" / "validation_protocol_candidate_seed42" / "protocol.json"

st.set_page_config(
    page_title="SeismoNet | AI Phase Picker",
    page_icon="🌋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Minimalist CSS for "Pinterest" look
st.markdown("""
    <style>
    .main {
        background-color: #fdfdfd;
    }
    .stMetric {
        background-color: #ffffff;
        border: 1px solid #efefef;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricValue"] {
        font-family: 'Inter', sans-serif;
        color: #1769aa;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #2d3436;
    }
    .stButton>button {
        border-radius: 20px;
        border: 1px solid #efefef;
        background-color: white;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        border-color: #1769aa;
        color: #1769aa;
    }
    </style>
""", unsafe_allow_html=True)

# --- CACHED LOADERS ---
@st.cache_resource
def load_model():
    device = torch.device("cpu")
    model = SeismoUnet1d(base=16, depth=4).to(device)
    state = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.eval()
    return model

@st.cache_data
def get_validation_traces():
    pilot = json.loads(PILOT_RUN_PATH.read_text(encoding="utf-8"))
    metadata_csv = Path(pilot["dataset"]["metadata_csv"])
    val_events = set(pilot["dataset"]["selected_validation_events"])

    rows = list(csv.DictReader(open(metadata_csv, encoding="utf-8")))
    val_rows = [r for r in rows if r.get("source_id", "").strip() in val_events]
    # Return a dictionary for easy lookup
    return {r["trace_name"]: r for r in val_rows}

@st.cache_data
def load_protocol():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

# --- APP LOGIC ---
def main():
    st.title("🌋 SeismoNet")
    st.markdown("#### Minimalist Seismic P & S Phase Picking via 1D U-Net")

    # Sidebar
    with st.sidebar:
        st.header("Control Panel")
        st.markdown("---")

        # Model Info
        st.subheader("Model State")
        st.info("Reference: Epoch 11\nArchitecture: U-Net 16/4\nStatus: Frozen")

        # Protocol Info
        protocol = load_protocol()
        st.subheader("Picking Protocol")
        st.write(f"**P Threshold:** {protocol['picking']['p_threshold']}")
        st.write(f"**S Threshold:** {protocol['picking']['s_threshold']}")
        st.write(f"**Tolerance:** {protocol['picking']['matching_tolerance_samples']} samples")

        st.markdown("---")
        st.caption("Developed for College Mini-Project")

    # Load assets
    model = load_model()
    traces_dict = get_validation_traces()
    trace_names = sorted(list(traces_dict.keys()))

    # Trace Selection
    selected_trace = st.selectbox("Select a seismic trace to analyze:", trace_names)

    if selected_trace:
        meta = traces_dict[selected_trace]

        # Load windowed data
        pilot = json.loads(PILOT_RUN_PATH.read_text(encoding="utf-8"))
        snap = yaml.safe_load((ROOT / "runs" / "pilot_seed42" / "config_snapshot.yaml").read_text(encoding="utf-8"))
        window_length = int(snap["input_shape"][2])

        ds = InstanceDataset(
            Path(pilot["dataset"]["hdf5"]),
            Path(pilot["dataset"]["metadata_csv"]),
            window_length=window_length,
            sigma=20.0,
            depth=4,
            training=False,
            seed=42,
            trace_names=[selected_trace],
            pure_noise_fraction=0.0,
        )

        sample = ds[0]
        waveform = sample["waveform"].numpy()
        w_start = int(sample["window_start"])

        # Inference
        with torch.no_grad():
            logits = model(torch.from_numpy(waveform).unsqueeze(0).float())
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

        # Picking logic
        cfg = PeakPickingConfig(
            p_threshold=protocol["picking"]["p_threshold"],
            s_threshold=protocol["picking"]["s_threshold"],
            min_peak_distance_samples=protocol["picking"]["min_peak_distance_samples"],
            matching_tolerance_samples=protocol["picking"]["matching_tolerance_samples"],
        )

        p_diag = pick_phase_diagnostics(probs[0], threshold=cfg.p_threshold, min_peak_distance_samples=cfg.min_peak_distance_samples)
        s_diag = pick_phase_diagnostics(probs[1], threshold=cfg.s_threshold, min_peak_distance_samples=cfg.min_peak_distance_samples)

        # UI Layout
        col1, col2 = st.columns([3, 1])

        with col1:
            # Plots
            fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True, dpi=100)
            x = np.arange(window_length) + w_start

            # Waveforms
            for ch in range(3):
                axes[ch].plot(x, waveform[ch], color="#2d3436", lw=0.7)
                axes[ch].set_ylabel(f"CH {ch}", fontsize=8)
                axes[ch].grid(True, alpha=0.1)

                # Reference picks
                p_abs = int(float(meta.get("trace_P_arrival_sample", 0))) if meta.get("trace_P_arrival_sample") else None
                s_abs = int(float(meta.get("trace_S_arrival_sample", 0))) if meta.get("trace_S_arrival_sample") else None

                if p_abs: axes[ch].axvline(p_abs, color="#1769aa", ls="--", lw=1, alpha=0.6)
                if s_abs: axes[ch].axvline(s_abs, color="#c2410c", ls="--", lw=1, alpha=0.6)

                # Predicted picks
                if p_diag.pick: axes[ch].axvline(w_start + p_diag.pick.index, color="#1769aa", ls="-", lw=1.2)
                if s_diag.pick: axes[ch].axvline(w_start + s_diag.pick.index, color="#c2410c", ls="-", lw=1.2)

            # Probabilities
            pax = axes[3]
            pax.plot(x, probs[0], color="#1769aa", label="P Prob", lw=1.5)
            pax.plot(x, probs[1], color="#c2410c", label="S Prob", lw=1.5)
            pax.plot(x, probs[2], color="#b2bec3", label="Noise", lw=1)
            pax.axhline(cfg.p_threshold, color="#1769aa", ls=":", alpha=0.5)
            pax.axhline(cfg.s_threshold, color="#c2410c", ls=":", alpha=0.5)
            pax.set_ylim(-0.05, 1.05)
            pax.legend(loc="upper right", fontsize=8)
            pax.set_xlabel("Sample Index")
            pax.set_ylabel("Probability")

            plt.tight_layout()
            st.pyplot(fig)

        with col2:
            st.markdown("### Analysis")

            # P-Wave Card
            st.markdown("**P-Wave**")
            p_ref = int(float(meta.get("trace_P_arrival_sample", 0))) if meta.get("trace_P_arrival_sample") else None
            p_pred = w_start + p_diag.pick.index if p_diag.pick else None

            if p_ref and p_pred:
                resid = p_pred - p_ref
                status = "✅ TP" if abs(resid) <= cfg.matching_tolerance_samples else "❌ FP"
                st.metric("Residual", f"{resid} samples", delta=f"{status}", delta_color="normal")
            else:
                st.write("Pick missing")

            st.markdown("---")

            # S-Wave Card
            st.markdown("**S-Wave**")
            s_ref = int(float(meta.get("trace_S_arrival_sample", 0))) if meta.get("trace_S_arrival_sample") else None
            s_pred = w_start + s_diag.pick.index if s_diag.pick else None

            if s_ref and s_pred:
                resid = s_pred - s_ref
                status = "✅ TP" if abs(resid) <= cfg.matching_tolerance_samples else "❌ FP"
                st.metric("Residual", f"{resid} samples", delta=f"{status}", delta_color="normal")
            else:
                st.write("Pick missing")

            st.markdown("---")
            st.caption("Blue: P-Wave | Orange: S-Wave")

if __name__ == "__main__":
    main()

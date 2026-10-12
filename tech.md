# SeismoNet Tech Stack Recommendation

*Companion to the SeismoNet PRD v0.1. Versions are not pinned here because current releases could not be checked; pin them in a lockfile (FR-R1).*

## The key point first

The PRD describes a **research pipeline**, not a web product. It has no requirement for a UI, a backend service, a database or a public API. It also explicitly excludes deployment claims (NG1) and real-time streaming (NG3). Recommending React plus Postgres plus Kubernetes would mean inventing requirements, so the stack is split into three tiers:

| Tier | What it covers | Status |
| --- | --- | --- |
| **Tier 1: Core** | Everything the PRD requires (data, model, training, evaluation, plots, reproducibility) | Needed |
| **Tier 2: Optional demo layer** | A small app to browse picks and failures, supporting US-12 and US-13 | Only if an interactive demo is wanted |
| **Tier 3: Scale-up path** | What would change if the project ever grows | Not needed now |

## 1. ML stack (Tier 1, the core of the project)

### Frameworks and libraries

| Component | Choice | Why |
| --- | --- | --- |
| Language | **Python 3.11 or 3.12** | The seismology and ML ecosystem is Python-first. |
| Deep learning | **PyTorch** | SeisBench and most published pickers use it. Easy to debug, plenty of examples. |
| Data and benchmarks | **SeisBench** | Standardised seismic datasets, ready-made model implementations (including PhaseNet), and pretrained weights for optional baselines (O2). Avoids hand-writing data loaders. |
| Seismic I/O and classical methods | **ObsPy** | The standard tool for reading waveform formats such as miniSEED and for the STA/LTA baseline (O1). |
| Numerics and picking | **NumPy, SciPy** | `scipy.signal.find_peaks` is enough for pick extraction (FR-K1). |
| Tables and metrics | **pandas** | Results tables and stratified reporting by SNR, distance and magnitude (FR-E8). |
| Plots | **Matplotlib** | Static, publication-quality figures for waveform, picks and probabilities. |

**Why plain PyTorch rather than PyTorch Lightning:** for a mini project, a \~50-line training loop is more transparent and easier to explain in a report. Lightning is a fine upgrade if multi-GPU training is added.

### Algorithms and model design

These are proposals. Several are marked open in the PRD (OQ-6 to OQ-10), so treat them as baselines that can be changed.

| Item | Recommendation | Why | PRD link |
| --- | --- | --- | --- |
| Architecture | **1D U-Net**, depth 4, base 16 channels, kernel 7, BatchNorm + ReLU | Matches the stated approach. A small model trains on a free GPU. | FR-M1 to M4 |
| Output | 3 channels (P, S, noise) with softmax | Probabilities sum to 1 per sample. | FR-L3 |
| Window | 3072 samples at 100 Hz | Divisible by 2^depth, so skip connections align. PhaseNet itself used 3001, so choose one and document it. | OQ-4, FR-M5 |
| Labels | Gaussian curves on P and S, noise = remainder, σ = 10 samples as baseline | Standard PhaseNet-style targets. σ is included in the ablation. | OQ-8, FR-L2 |
| Loss | **Soft cross-entropy** against the Gaussian targets | Works with probability-shaped labels. MSE is an optional ablation. | OQ-9 |
| Optimiser | **Adam or AdamW**, lr 1e-3 | Reliable default for this kind of network. | FR-T1 |
| Scheduler | `ReduceLROnPlateau` | Simple, with no schedule to tune. | FR-T5 |
| Regularisation | Augmentation plus early stopping; light dropout only if overfitting | Keeps the baseline simple. | FR-A1 |
| Speed | **Automatic mixed precision (AMP)** | Faster training on a free GPU with little code. | NFR-5 |
| Augmentation | Random shift via cropping, amplitude scaling, channel dropout, **switchable** noise addition | Each must be independently switchable for the ablations. | FR-A1, A2 |
| Picking | `find_peaks` on each probability channel, threshold chosen on validation data | Simple and standard. | FR-K1, K2 |
| Class imbalance | Monitor P/S metrics. Add class weighting only if the model collapses to all-noise. | Avoids tuning something not shown to be a problem. | E30, E31 |

### Baselines (optional but persuasive)

- **STA/LTA** through ObsPy: the classical reference point (O1).
- **Pretrained PhaseNet** through SeisBench: an external reference on the test set (O2). It was trained on other data, so this is a reference, not a like-for-like comparison.
- **EQTransformer** through SeisBench: only if a second deep learning reference is wanted. Not required.

### Experiment management

| Component | Choice | Why |
| --- | --- | --- |
| Config | **YAML files**, optionally with **Hydra or OmegaConf** | One config per experiment, saved with each checkpoint (FR-T4). Plain YAML is enough; Hydra helps once there are many ablation runs. |
| Tracking | **MLflow, run locally** (SQLite backend) | Free, no account, data stays on the local machine. Weights & Biases is easier to use but sends data to a third-party service. |
| Data versioning | **Saved split files plus Git** (DVC optional) | The real need is event-level splits stored on disk (FR-D5), which does not require a data versioning tool. |
| Seeds | Python, NumPy and PyTorch seeds set and logged | Required by FR-T3. |
| Checkpoints | **safetensors** for weights | Safer than pickle-based formats (see Security). |

## 2. Frontend (Tier 2, optional)

**Recommendation: Streamlit**, only if an interactive viewer is wanted. Gradio is a close alternative.

| Option | Verdict |
| --- | --- |
| **Streamlit** | **Recommended.** Python-only, so no JavaScript build chain. Quick for a sample browser, a threshold slider and a failure gallery, and renders Matplotlib or Plotly figures directly. |
| Gradio | Also simple, and slightly better for "upload a file, get a result" demos. |
| React or Next.js | Better for a polished multi-user product, but adds a second language, a build pipeline and a larger security surface. Not justified by the PRD. |
| Jupyter notebooks | Good for exploration (US-01), but not a user-facing app. |

**What the app would do (all drawn from existing PRD items):**

- Pick a test sample and see waveform, reference picks, predicted picks and probability curves (FR-V1, V2).
- Adjust the threshold and see the pick change.
- Browse success and failure galleries (FR-V4).

**Plotting library:** Plotly for the interactive app (zoom and pan on waveforms), Matplotlib for static report figures.

## 3. Backend and APIs (Tier 2, optional)

The PRD does not require a backend. For a demo that accepts a waveform and returns picks:

| Component | Choice | Why |
| --- | --- | --- |
| Framework | **FastAPI** | Strong input validation via Pydantic, auto-generated OpenAPI docs, and a straightforward way to wrap a PyTorch model. |
| Server | **Uvicorn** | Standard FastAPI server. |
| Inference runtime | **PyTorch on CPU** | The model is small. Moving to ONNX Runtime is an optimisation that can be skipped. |
| Input parsing | **ObsPy** for miniSEED, or a JSON array | Handles standard waveform formats. |

If only Streamlit is used, the model can be called directly in-process and FastAPI skipped. That is the simplest option.

### Minimal API design (proposed, not a PRD requirement)

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness check |
| `GET /model` | Model name, version, window length, sampling rate, config hash |
| `POST /picks` | Accept a 3-component window, return P and S pick times, optional probability curves, and model version |

**Input validation (important for correctness and security):**

- Enforce a maximum payload size.
- Require exactly 3 components, the expected sampling rate and the expected window length. Reject or explicitly resample anything else (edge cases E12, E18).
- Reject NaN/Inf and flat traces (E10, E11).
- Return "no pick" explicitly rather than a fake value (FR-K3).

**External APIs:** none are required. SeisBench downloads datasets, and that is the only outbound network dependency.

## 4. Database

**Recommendation: no database for the core project.**

| Need | Use | Why |
| --- | --- | --- |
| Waveforms and metadata | SeisBench's native format (**HDF5 plus CSV/Parquet metadata**) | Already optimised for this data. Duplicating it into a database adds work and no value. |
| Splits | CSV or Parquet of event IDs per split | Easy to inspect and diff; satisfies FR-D5. |
| Results tables | CSV or Parquet | Directly loadable in pandas. |
| Experiment records | MLflow with SQLite | Light and local. |
| Checkpoints | Local folder, optionally S3-compatible object storage | Simple. |

**Scale-up path (Tier 3):** if the demo needs to store user uploads or prediction history across multiple users, move to **PostgreSQL** and keep waveforms in object storage rather than in the database. Do not start there. SQLite is sufficient for a single-user demo.

## 5. Testing

This is where the PRD gives the clearest requirements, and where seismology-specific tests matter most.

| Layer | Tool | What to test | PRD link |
| --- | --- | --- | --- |
| Unit tests | **pytest** | Label generation (Gaussians sum correctly, noise = remainder, zero targets when no phase), pick extraction (no peak, several peaks), metric calculation (TP, FP and FN logic, zero denominators), window cropping keeps labels aligned with picks | FR-L, FR-K, FR-E, E32 |
| Data-leakage test | pytest | **Zero event IDs shared across train, validation and test** | FR-D5, SC-8 |
| Model tests | pytest | Output shape equals input shape, softmax sums to 1, depth and window compatibility assertion | FR-M3, FR-M5 |
| Sanity test | pytest or script | **Overfit a tiny batch** to near-zero loss | US-06 |
| Determinism test | pytest | Same seed and config give the same result on CPU, with documented tolerance on GPU | US-07, NFR-1 |
| Edge-case tests | pytest with parametrisation (optionally **hypothesis**) | NaN input, flat channel, missing component, pick at window edge, P after S | E5, E6, E10 to E12, E29 |
| API tests (if built) | **FastAPI TestClient or httpx** | Oversized payload, wrong shape, malformed file, valid input | Section 3 |
| Data validation | **pandera** or Pydantic (optional) | Metadata schema checks on load | FR-D3 |
| Code quality | **ruff** (lint and format), optionally **mypy** | Catches simple errors early | NFR-4 |

**Seismology-specific advice:** build a tiny **synthetic fixture** (a clean waveform with known P and S onsets) to test the full chain end to end. It is fast, and it gives ground truth you fully trust.

**CI:** **GitHub Actions** running ruff, then pytest on CPU with a tiny data fixture. It should not download the full dataset.

## 6. Deployment and reproducibility

### Core project (needed)

| Component | Choice | Why |
| --- | --- | --- |
| Environment | **uv or pip-tools** (or conda) with a **lockfile** | Pinned versions meet FR-R1. |
| Container | **Docker** | Same environment on any machine; helps a reviewer reproduce results (SC-6). |
| Entry points | **Makefile** (or a `just` file) | One command each for `make data`, `make train`, `make eval`, `make figures`. Satisfies FR-R3. |
| Training compute | **Colab, Kaggle or one cloud GPU** | Matches the free-tier assumption (A6). |

### Optional demo hosting (Tier 2)

| Option | Fit |
| --- | --- |
| **Hugging Face Spaces or Streamlit Community Cloud** | Simplest for a Streamlit or Gradio demo. Free tier, no servers to manage. |
| **Google Cloud Run, AWS App Runner or Azure Container Apps** | Best if a FastAPI service is containerised. Scales to zero, managed HTTPS, no cluster to run. |
| Kubernetes | Not justified. Only consider it for many users or batch workloads (Tier 3). |

### Scale-up path (Tier 3, not now)

- Batch inference over many windows: a job queue (e.g., Celery or a cloud batch service) with worker containers.
- Continuous data: needs a different design (sliding windows, overlap handling and multi-event logic), beyond the current PRD (A4, NG3, E21).
- Model serving: ONNX Runtime or TorchServe if latency matters.
- Storage: S3-compatible object storage and PostgreSQL for metadata.

## 7. Security

The PRD has no security section, so these are recommendations rather than requirements. Most risk in a project like this comes from loading untrusted files and dependencies.

| Risk | Mitigation |
| --- | --- |
| Malicious pickle in a downloaded model checkpoint (a known PyTorch risk) | Save weights in **safetensors**. If `torch.load` is used, set `weights_only=True`. Never load checkpoints from untrusted sources. |
| Malformed or oversized uploaded waveforms (demo only) | Enforce size limits, type checks, and shape and rate validation before parsing. Reject unknown formats. |
| Vulnerable dependencies | **pip-audit** and **Dependabot**, with the lockfile. |
| Secrets (API keys, tokens) | Environment variables or the host's secret manager. Never commit them. |
| Container risk | Run as a **non-root user** with a minimal base image. |
| Public demo abuse | HTTPS, rate limiting, and no storage of uploads unless needed. |
| Dataset licence | Check licence and citation terms for the chosen dataset (NFR-7). |

## 8. Summary: the recommended stack

| Layer | Recommendation | Priority |
| --- | --- | --- |
| Language | Python 3.11/3.12 | Core |
| ML | PyTorch, SeisBench, ObsPy, SciPy, NumPy, pandas, Matplotlib | Core |
| Model | 1D U-Net (PhaseNet-style), soft cross-entropy, Adam, AMP | Core |
| Experiments | YAML (or Hydra), local MLflow, safetensors | Core |
| Data and DB | HDF5 and Parquet/CSV files, no database | Core |
| Testing | pytest, ruff, GitHub Actions, synthetic fixtures | Core |
| Packaging | uv or pip-tools lockfile, Docker, Makefile | Core |
| Frontend | Streamlit (or Gradio) | Optional |
| Backend and API | FastAPI with Pydantic validation | Optional |
| Demo hosting | Hugging Face Spaces, or Cloud Run for a container | Optional |
| Scale-up | PostgreSQL, object storage, job queue, ONNX or TorchServe | Later |

**Why this ordering serves the three priorities:**

- **Simplicity:** one language, no database, no JavaScript toolchain, and optional pieces kept clearly separate.
- **Security:** no pickle checkpoints, validated inputs, locked dependencies, and no third-party tracking service required.
- **Scalability:** the model code is separate from any app layer, so FastAPI, a database or batch workers can be added later without rewriting the pipeline.

## 9. Decisions still needed

1. Is an interactive demo wanted at all, or is a report with static figures enough? That decides whether Tier 2 is built.
2. Which dataset (OQ-3)? It affects window length and I/O details.
3. Is training on Colab/Kaggle or on a local GPU?

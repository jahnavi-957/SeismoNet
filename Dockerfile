# syntax=docker/dockerfile:1
#
# Single-image deployment: this container serves the FastAPI API *and* the built React UI on one
# origin, so the frontend's relative "/api" calls need no proxy and no CORS configuration.
# Build and run locally:
#   docker build -t seismonet .
#   docker run --rm -p 8000:7860 seismonet        # then open http://127.0.0.1:8000
# See docs/DEPLOYMENT.md for hosted options.

# ── stage 1: build the React UI ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ── stage 2: Python runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# CPU-only PyTorch. The lockfile pins a CUDA build (~2.6 GB of CUDA runtime) that a CPU host
# cannot use; the network is tiny and runs fine on the CPU wheel.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml requirements.lock ./
COPY src ./src

# Install the locked dependencies minus the CUDA torch (done above) and minus the editable
# project line, which is installed from this source tree immediately afterwards.
RUN grep -viE '^(torch|nvidia-|triton)' requirements.lock | grep -v '^-e ' > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir -e .

# Application code and the frozen artefacts the demo needs (2.9 MB, tracked in git).
COPY backend ./backend
COPY configs ./configs
COPY runs/experiment_002_p_training/best.pt runs/experiment_002_p_training/run.json ./runs/experiment_002_p_training/
COPY runs/validation_protocol_candidate_seed42/protocol.json ./runs/validation_protocol_candidate_seed42/
COPY runs/pilot_seed42/run.json runs/pilot_seed42/config_snapshot.yaml ./runs/pilot_seed42/
COPY runs/eval_test_best/metrics.json ./runs/eval_test_best/
COPY runs/validation_inference_p6_seed42/predictions.json ./runs/validation_inference_p6_seed42/

# Built UI from stage 1 — backend.main mounts it when frontend/dist exists.
COPY --from=ui /ui/dist ./frontend/dist

ENV PORT=7860
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=6s --start-period=25s --retries=3 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','7860'), timeout=5).status == 200 else 1)"

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]

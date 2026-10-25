# Deploying SeismoNet

The application ships as **one container** that serves both the FastAPI API and the built React UI on
the same origin. That matters: the frontend calls `/api` *relatively*, so same-origin serving removes the
need for a proxy, CORS configuration, or a second host.

Measured on this machine (`docker build` + `docker run`):

| | |
|---|---|
| Image size | **1.93 GB** (CPU-only PyTorch; the pinned CUDA wheel would add ~2.6 GB of unusable runtime) |
| Memory, idle | **210 MiB** |
| Memory, peak during a 12-trace upload + inference | **228 MiB** |
| Cold start | ~8 s (PyTorch import dominates) |
| Inference output | identical to local — picks `1271/1674`, `1480/1449`, `1309/1656` for the demo file |

Because the peak is only ~230 MiB, a **512 MB free tier is enough** — no paid plan required.

---

## Option A — Render (simplest; recommended for a demo link)

1. Push this repository to GitHub (already done).
2. On <https://render.com> → **New → Web Service** → connect `jahnavi-957/SeismoNet`.
3. Settings:
   - **Runtime:** Docker (Render detects `Dockerfile` automatically)
   - **Instance type:** Free
   - **Health check path:** `/api/health`
   - Leave the port blank — Render sets `PORT`, and the container's `CMD` uses it.
4. **Create Web Service**. First build takes ~5–8 minutes.
5. Open `https://<name>.onrender.com` → the UI loads, `/api/health` returns JSON.

Free-tier notes: the service **sleeps after ~15 minutes idle**; the next visit takes ~30–60 s to wake
(PyTorch import). Warm the link a few minutes before you present.

---

## Option B — Hugging Face Spaces (free, no sleep, 16 GB RAM)

Preferred if you want a link that is always warm. Docker Spaces listen on port **7860**, which is already
the container default.

1. <https://huggingface.co/new-space> → **SDK: Docker** → Blank → Create.
2. Add the Space as a remote and push:
   ```powershell
   git remote add space https://huggingface.co/spaces/<your-user>/seismonet
   git push space main
   ```
3. Hugging Face requires `sdk: docker` in the Space's `README.md`. Replace the Space's README with:
   ```markdown
   ---
   title: SeismoNet
   emoji: 🌊
   colorFrom: blue
   colorTo: slate
   sdk: docker
   app_port: 7860
   pinned: false
   ---

   Seismic P/S phase picking demo. Source: https://github.com/jahnavi-957/SeismoNet
   ```
   Command-line equivalent, from a clone of the Space:
   ```powershell
   Copy-Item deploy\huggingface\README.md README.md -Force
   git add README.md; git commit -m "Add Space metadata"; git push
   ```
4. The Space builds and serves on its own URL.

Free CPU Spaces give 2 vCPU / 16 GB, so inference is faster than the 512 MB tiers.

---

## Option C — Split deployment (static UI + separate API)

Use this only if you want the UI on a CDN. Both halves must be configured to know about each other.

1. **API** on Render/Fly/Cloud Run using the same `Dockerfile`, but set:
   ```
   SEISMONET_CORS_ORIGINS=https://<your-ui-host>
   ```
2. **UI** on Vercel/Netlify:
   - Build command: `npm ci && npm run build` (root directory `frontend`)
   - Output directory: `dist`
   - Environment variable at **build** time:
     ```
     VITE_API_BASE_URL=https://<your-api-host>/api
     ```
3. Redeploy the UI after changing that variable — Vite inlines it at build time.

Same-origin (Options A/B) is less error-prone; prefer it unless you have a reason.

---

## Local rehearsal before you deploy

```powershell
docker build -t seismonet .
docker run --rm -p 8000:7860 seismonet
# open http://127.0.0.1:8000 — same container, same behaviour as production
```

Then walk the demo: **CSV Upload** → `samples/demo_12traces_predict.csv` → map **Trace ID → `trace_id`** →
**Validate CSV** → **Run real model analysis**.

---

## After deploying — checklist

| Check | Expected |
|---|---|
| `GET /api/health` | `"status": "online"`, `"checkpoint_available": true`, protocol `protocol-5fa5744aca58cc3c` |
| `GET /api/metrics` | P F1 `0.685`, S F1 `0.499` |
| `GET /api/traces` | 210 records |
| `/`, `/picker`, `/evaluation` | the app, not a 404 (deep links fall back to `index.html`) |
| Upload the demo CSV | 12 traces, P/S picks and probability curves |

If `/api/metrics` returns 503, the `runs/eval_test_best/metrics.json` file did not reach the image.
If the UI loads but requests fail, the frontend is being served by a different host than the API — use
Option A or B, or set `VITE_API_BASE_URL` and `SEISMONET_CORS_ORIGINS` as in Option C.

---

## What is deliberately not included

- **No authentication.** Anyone with the URL can upload files and consume CPU. Acceptable for a demo;
  do not leave it running unattended for a public audience.
- **Uploads are capped** at 50 MB / 100,000 rows / 3,072 samples per trace by the backend itself, so the
  service cannot be trivially filled from the UI.
- **No raw dataset.** The Phase Picker stays in its labelled `synthetic_demo_fallback` mode, exactly as it
  does locally; the CSV upload path runs the real frozen checkpoint.
- **One Uvicorn worker.** CPU inference per window is ~40 ms, so a single worker is fine for a demo; adding
  workers multiplies memory by ~230 MiB each.

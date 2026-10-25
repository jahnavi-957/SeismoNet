# 2026-10-25-009 — Deployable single container: static UI, CORS from env, CPU image

## A. Change identification

- Change ID: `2026-10-25-009`
- Date: 2026-10-25
- Short title: Deployable single container: static UI, CORS from env, CPU image
- Category: feature | configuration | bug fix | documentation
- Files created: `Dockerfile`, `.dockerignore`, `docs/DEPLOYMENT.md`, `deploy/huggingface/README.md`, this entry
- Files modified: `backend/main.py`, `requirements.lock`, `README.md`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`

## B. What was changed?

The application can now be deployed as a single container:

1. `backend/main.py` mounts `frontend/dist` when it exists — assets under `/assets`, every other path falls back
   to `index.html` so client-side routes deep-link, and `/api/*` still returns JSON (an unknown API path is a
   404, not the SPA shell). In local development the directory is absent and the block is skipped.
2. CORS origins can be extended at runtime with `SEISMONET_CORS_ORIGINS` (comma-separated), for a split
   static/API deployment.
3. `Dockerfile` (multi-stage): Node builds the UI, Python 3.12 installs **CPU-only** PyTorch plus the locked
   dependencies, then copies `backend/`, `configs/`, the seven frozen artefacts and the built UI.
4. `.dockerignore` keeps the context small; `docs/DEPLOYMENT.md` documents Render, Hugging Face Spaces and a
   split deployment, with a post-deploy checklist.

## C. Why was this change necessary?

The web client calls `/api` relatively, which works in development only because Vite proxies it. Any
deployment therefore needed either a same-origin server that also serves the build, or a configured
`VITE_API_BASE_URL` plus CORS. Serving both from FastAPI is the smaller, less error-prone option, and it lets
the whole demo run on a free 512 MB tier.

Two defects surfaced while packaging:

- `requirements.lock` contained `-e git+https://github.com/jahnavi-957/SeismoNet.git@eddb3b9…#egg=seismonet`.
  That commit is the pre-implementation documentation-only state of the repository, so anyone following the
  README would have installed a package with no `src/` at all. Replaced with `-e .`.
- The pinned `torch==2.14.1+cu126` pulls a ~2.6 GB CUDA runtime that a CPU host cannot use. The image installs
  the CPU wheel and filters the CUDA-specific entries from the lockfile.

## D. Why this approach was chosen?

A single image avoids the most common failure mode of this kind of project — a frontend that loads but cannot
reach its API — and keeps the deployment instructions to "connect the repository, pick Docker". CPU-only
PyTorch cuts both image size and memory. The SPA mount is guarded by `dist/` existing, so the development
workflow is unchanged.

## E. How was it implemented?

```python
_DIST_DIR = ROOT_DIR / "frontend" / "dist"
if _DIST_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (_DIST_DIR / full_path).resolve()
        if full_path and candidate.is_file() and _DIST_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_DIST_DIR / "index.html")
```

`Dockerfile` stage 1 runs `npm ci && npm run build`; stage 2 installs
`torch --index-url https://download.pytorch.org/whl/cpu`, then the lockfile minus `torch`/`nvidia-*`/`triton`
and minus the editable line, then `pip install -e .`, and finally copies the build and artefacts. It listens on
`${PORT:-7860}` and declares a `/api/health` healthcheck.

## F. How did this improve SeismoNet?

- **VERIFIED:** `docker run -p 8099:7860` serves the app; `/`, `/picker`, `/csv-upload`, `/evaluation` all
  return 200 (SPA fallback works), `/api/health` reports `online` with the checkpoint present, and
  `/api/metrics` returns P F1 `0.6850`.
- **VERIFIED:** a 12-trace upload in the container returns picks **identical** to the local run
  (`1271/1674`, `1480/1449`, `1309/1656`).
- **VERIFIED:** the container passes the full browser smoke suite — **14/14 steps, 0 console errors,
  0 failed requests**.
- **VERIFIED:** image **1.93 GB**, **210 MiB idle**, **228 MiB peak** during upload and inference, cold start
  ~8 s. A 512 MB free instance is sufficient.
- The `requirements.lock` defect is fixed, so the documented install no longer pulls a docs-only commit.

## G. Testing and verification

- `docker build -t seismonet .` → success; `docker run` → probes above.
- Browser smoke against `http://127.0.0.1:8099` → 14/14.
- `pytest` → **190 passed, 36 skipped**.
- Local dev path unchanged: Vite on 5173 still serves the UI, backend on 8000 still answers.

## H. Risks and side effects

The deployed service has **no authentication** and accepts uploads up to 50 MB; it is a demo, not a public
service. Hugging Face Spaces require `sdk: docker` in the Space's README, hence
`deploy/huggingface/README.md`. Free tiers sleep (Render) or are rate-limited (Spaces), so the demo link
should be warmed before presenting.

## I. Relationship to the PRD and roadmap

Local demonstration and delivery (`FR-049`–`FR-065`, `FR-077`). No model, artefact or reported number changed.

## J. Next steps

- Optional: an API key or a per-IP limit if the demo is left public for long.
- Optional: a `fly.toml`/Cloud Run profile for hosts that need one.

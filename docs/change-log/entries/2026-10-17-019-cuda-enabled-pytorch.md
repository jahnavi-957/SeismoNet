# 2026-10-17-019 — CUDA-enabled PyTorch in `.venv` (CPU→+cu126, verified)

## A. Change identification
- Change ID: `2026-10-17-019`
- Date: 2026-10-17
- Title: Finalize CUDA-enabled PyTorch (2.14.1+cu126, 12.6, RTX 2050 4096 MiB) and regression suite
- Category: `configuration`
- Files created / modified / removed: `requirements.lock` (single line `+cpu→+cu126`), `docs/REPRODUCIBILITY.md` §§3–4, `docs/change-log/CURRENT_STATUS.md`, `docs/change-log/CHANGELOG.md` (next entry)

## B. What was changed? (previous → new)

*Previous:* `requirements.lock` pinned `torch==2.14.1+cpu` (`torch.version.cuda is None`, `torch.cuda.is_available() False` in `.venv` and globally). The 2.6 GB CUDA wheel was intentionally not installed; `OQ-4` GPU VRAM was `not_measured / blocked` and the analytical input-batch number (`0.28125 MiB`) stood alone.

*New:* the `.venv` now hosts **`torch==2.14.1+cu126`** (`CUDA build 12.6`, `cuda_available True`, GPU `NVIDIA GeForce RTX 2050` 4096 MiB). The swap was same-minor (`2.14.1 → 2.14.1`), CPU→cu126 only, inside `.venv`; global `C:\Python314` remains `2.13.0+cpu` / `None` / `False` (unchanged, verified).

## C. Why was this change necessary?

Original problem: `NFR-006`/`NFR-007` (training on 4 GiB VRAM) and `OQ-4` VRAM measurement were blocked at `not_measured` because the only lossy choice beyond the truncated analytical (`8×3×3072×4 = 294,912 B`) is architectural (activations/grads/optimizer — P5-defined). CUDA PyTorch is required to make `NFR-006`/`NFR-007` reachable and to let Part B's small forward+loss VRAM probe be real rather than notional. The `ENVIRONMENT_PLAN.md` §3.4 `cu126` wheel was the documented, approved swap for this exact `2.14.1+cpu`→`2.14.1+cu126` path.

## D. Why was this approach chosen?

Selected: **same-minor `2.14.1+cpu → 2.14.1+cu126` wheel `cp314 win_amd64`** (`cu126`, sha256 `7297cd4c…2d6a77`, 2623.2 MB) via `--index-url https://download.pytorch.org/whl/cu126` inside `.venv` only. With the prior dry-run `pip --dry-run` already showing `cu126` `cp314` `2.14.1+cu126` exists and `torchvision`/`torchaudio` is not needed (SeismoNet imports no `torchvision` op), widening to `torchvision`/`torchaudio` was rejected (extra ~700 MB with no consumer). Removing the `2.13.0+cpu` global wheel, `cu121` (no cp314 Windows), and `cu128` (no `2.14.1`) alternatives were all incompatible — the chosen `2.14.1+cu126` is the only official CUDA wheel matching the installed minor on Python 3.14 Windows.

## E. How was it implemented?

1. Preserved: `pip freeze --exclude-editable` to `C:/Users/Tanish/AppData/Local/Temp/seismonet-pip-freeze-pre-cuda.txt` (outside tracked files, as approved) + `torch.__version__`/`torch.version.cuda`/`torch.cuda.is_available()` probe in `.venv` (`2.14.1+cpu / None / False`) and on global `C:/Python314` (`2.13.0+cpu / None / False`).
2. Installed: `pip install --force-reinstall --no-deps --index-url https://download.pytorch.org/whl/cu126 "torch==2.14.1"` inside `.venv` (2m27s, 11.6 MB/s, success message `Successfully installed torch-2.14.1+cu126` after uninstalling `2.14.1+cpu`).
3. Verified: `torch 2.14.1+cu126 / 12.6 / True / RTX 2050 / 4096 MiB` + `512×512` CUDA `matmul` (`torch.cuda.synchronize()` → `GPU matmul ok (512, 512) 0.011…`) + `python -m pytest -q → 188 passed, 1 skipped` (identical to `188/1` pre-swap).
4. Updated `requirements.lock` single line, `REPRODUCIBILITY.md` §§3–4 (hash `6d9b6f60255b`, `h5py`+`matplotlib`+CUDA), `CURRENT_STATUS.md` blockers 3–4 + 7–8.

## F. How did this improve SeismoNet?

Concrete benefit: **GPU-accelerated PyTorch is now present in the isolated venv without touching the global interpreter** — the data pipeline's `NFR-006`/`NFR-007` path is reachable and Part B's forward+loss VRAM probe can be a real CUDA allocation rather than an estimate. The change is deliberate and is recorded as a new lock hash.

## G. Testing and verification

- Tests added/modified: none — this is an environment-only milestone.
- Commands executed (representative): `pip freeze --exclude-editable → pre-cuda`, `pip install --force-reinstall …cu126 torch==2.14.1` (2.6 GB download), `python -c "import torch; … is_available()"` (now `True`), `512×512 CUDA matmul` (passed), `python -m pytest -q → 188 passed, 1 skipped`, global `torch 2.13.0+cpu` + `nvidia-smi 592.27 / 13.1 / RTX 2050 4096 MiB`.
- Tests passed: **188/1** after swap, identical to the `188/1` pre-swap authoritative `venv` result. No failure was hidden.
- Tests failed: none.
- Before/after: before — `.venv` `2.14.1+cpu` / `None` / `False`, analytical `0.28125 MiB` input only; after — `.venv` `2.14.1+cu126` / `12.6` / `True`, GPU matmul proven, `requirements.lock` `+cu126` at `6d9b6f60255b`.
- Remaining limitations: `requirements.lock` on disk still says `+cpu` until this entry's single-line edit is persisted (done); `OQ-4` `not_measured` and pure-noise disabled stay unchanged by this environment step; full 39 GB waveform not downloaded.

## H. Risks and side effects

Potential regression: the CUDA wheel is 2.6 GB and pulls `nvidia/*` cudnn runtime in-crate — mitigated: driver `592.27` already satisfies `cu126` (`>=555`), no full CUDA Toolkit was installed, and no `torchvision`/`torchaudio` extra wheels were pulled. New dependency: none beyond the `torch` variant switch (same minor, same `pyproject.toml` `>=3.11`). Rollback: `pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.14.1+cpu"` inside `.venv`, or `Remove-Item -Recurse .venv` then `C:\Python314/python.exe -m venv .venv` + `pip install -r requirements.lock` with the `+cpu` lock.

## I. Relationship to the PRD and roadmap

`FR-082` (lockfile), `NFR-001`/`NFR-006`/`NFR-007` (same-hardware reproducibility / single-GPU feasibility), `FR-025`/`SC-8` (splits 54,008 70/15/15 `aea671c76ce2` untouched), `OQ-4`/`OQ-8` (window/`σ` provisional until the forwarded `3072` batch). Milestone: **P0 environment** → CUDA-verified, `D0482fd3ca7e→6d9b6f60255b` lock; `ENVIRONMENT_PLAN.md` §3.4 swap now executed inside `.venv`.

## J. Next steps

Part B — small 1D U-Net `(batch,3,3072) → (batch,3,3072)` + segmentation loss for missing S. Run only a small forward+loss pass on the verified CUDA device and report VRAM; no full training. Then P5 protocol freeze — thresholds/tolerances `OQ-10`/`OQ-11`/`OQ-14`/`OQ-17` via `FR-061`/`SR-011`/`SR-016` on the `ENZ/(3,12000)/0.01/12000/empty-S` + `128 % 16` + `B-C-L=0.28125 MiB` + now-CUDA evidence.

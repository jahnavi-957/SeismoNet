# SeismoNet — Environment Compatibility Plan

**Document ID:** ENV-001  
**Version:** 1.0  
**Date:** 2026-10-17  
**Status:** Plan (P0) — no environment was modified, no package installed in this task  
**Related:** `tech.md` §1, `TECH_STACK.md`, `AUDIT_REPORT.md` §7, `REPRODUCIBILITY.md` §3–§4, PRD `FR-082`/`NFR-001`/`NFR-006`/`NFR-007`, roadmap P0

> Nothing in this document changes the interpreter or installs a package.
> The plan is deliberately presented for owner approval **before** any modification.

---

## 1. Verified base facts (2026-10-17)

| Item | Verified value | How verified | Consequence |
|---|---|---|---|
| `python` on `PATH` | **3.14.3** (CPython, `MSC v.1944 64-bit`, `C:\Python314\python.exe`) | `python --version`, `sys.executable` | This is the runtime for every check below; a co-existing 3.11/3.12 was **not** probed (out of scope for this plan) |
| `pip` | ships with that interpreter; `pip install --dry-run` was not invoked | — | Available but unused |
| `torch` | **2.13.0+cpu** (`torch.version.cuda is None`, `cuda_available is False`) | `import torch; torch.__version__` | Training would be CPU-bound; AMP does nothing; GPU present but unreachable from this build |
| NumPy / SciPy / scikit-learn | 2.4.3 / 1.17.1 / 1.8.0 | direct imports | Sufficient for the skeleton tests below; versions are newer than what most seismic packages pin |
| pandas / PyYAML / safetensors / pytest | present | import probes | Skeleton tests can run **without** adding a dependency |
| `obspy` / `seisbench` / `matplotlib` / `ruff` | **not installed** | `importlib.util.find_spec` → `None` | Any `import obspy` or `import seisbench` will fail until P0 installs them |
| GPU hardware | NVIDIA **GeForce RTX 2050**, **4096 MiB**, **driver 592.27**, **CUDA 13.1** reported by `nvidia-smi` | `nvidia-smi` | Hardware is present and idle (84 MiB in use by the desktop compositor); the limitation is the **PyTorch build**, not the device |
| OS / shell | Windows 11, win32, PowerShell 5.1, git 2.47.1 | earlier audit | Relevant for `.venv` creation (`py -3.x` launcher) and for activation policy |

No dataset, no `.venv`, no lockfile, no CI is present. The only dependencies with local state are the interpreter above and the `torch 2.13.0+cpu` wheel.

---

## 2. Compatibility of Python 3.14 with the seismic stack

The question that blocks P1 is whether the pictured 3.14 environment can host `obspy` and `seisbench` without forcing a downgrade. The answer was established **without installing anything**, by reading PyPI metadata (which is authoritative for `Requires-Python` and for `Classifier`):

| Package (latest PyPI) | `Requires-Python` | `Classifier` mentions 3.14 | Latest version checked | Verdict |
|---|---|---|---|---|
| `obspy` 1.5.1 | *(no `Requires-Python` upper bound; `numpy>=1.21, scipy>=1.7, matplotlib>=3.3, lxml, sqlalchemy, decorator, requests`)* | **yes** — `Python :: 3.14` listed, alongside 3.8–3.13 | 1.5.1 | **Compatible with 3.14** on paper. This is the strongest signal: ObsPy's own wheel claims 3.14. |
| `seisbench` (current) | `>=3.10` | `3.9` listed only (stale classifier, does not rule out 3.14) | current | **Declared compatible `>=3.10`**; 3.14 not explicitly listed but not excluded. SeisBench is tighter-coupled to PyTorch than to the interpreter, so the risky coupling is the torch build, not the interpreter minor. |
| `matplotlib` | `>=3.11` | not checked (irrelevant: `matplotlib` tracks CPython closely; 3.12+ support is routine) | current | Compatible |
| `torch` | `>=3.10` | not applicable (wheels per CUDA) | 2.9.x | Compatible |
| `scikit-learn` / `pandas` / `numpy` / `scipy` / `PyYAML` | `>=3.11` / `>=3.11` / `>=3.12` / `>=3.12` / `>=3.8` | — | current | Compatible at 3.14; the installed NumPy 2.4.3 *is* a NumPy 2.x line, which several seismic wheels have only recently started to tolerate — pinning will matter |
| `ruff` | `>=3.7` | — | current | Compatible (standalone binary) |

**Conclusion.** Python 3.14 is **not the blocker** the earlier audit feared. The 2024-vintage recommendation of 3.11/3.12 in `tech.md` is sound but no longer load-bearing: ObsPy now advertises 3.14, the rest declare `>=3.10`/`>=3.11`, and the installed 3.14 already hosts the core scientific wheels. Downgrading to 3.11/3.12 remains a valid fallback (`OQ-20` / `A-11`) if a wheel refuses to install, but it is **not the default plan**. The default is to keep 3.14 and add a CUDA-capable PyTorch build (see §3).

*Verification note.* PyPI metadata is necessary but not sufficient: an `sdist` that builds on 3.14 can still fail to import at runtime on a particular NumPy major. The definitive proof is a real `pip install` into a fresh `.venv`. That proof is deliberately deferred to the approved P0 execution (§5).

---

## 3. PyTorch: CPU-only today, CUDA tomorrow

### 3.1 The current build

`torch 2.13.0+cpu` — intentionally or accidentally a CPU-only wheel. It is usable for the skeleton tests (none of which need a GPU), but it makes `NFR-006`/`NFR-007` (feasible training on the available GPU) false by construction: the free 4 GiB device contributes nothing, and the only fallback is the free-tier-GPU assumption `A6` (Colab/Kaggle) that the architecture already documents.

### 3.2 Why not just keep CPU-only

* The minimum viable training experiment (EX-1, the baseline) is expected — not guaranteed, but expected — to be slow on CPU even on a dataset subset `FR-007`. The small-model guidance in `tech.md` (depth 4, base 16, kernel 7) and the subset limit both exist to **cope** with a CPU fallback, not to **prefer** it.
* AMP (`tech.md` §1 "Speed: Automatic mixed precision") is a no-op without CUDA.
* Reproducibility documentation (`REPRODUCIBILITY.md` §8.4) has to state `torch_cuda_available` per run anyway. Shipping a CPU-only build while a CUDA device is present just forces every report to carry the footnote "could have been faster if the right wheel had been installed".

### 3.3 The RTX 2050 question — is the device reachable at all

**Yes — the device is reachable.** `nvidia-smi` reports driver 592.27 and CUDA 13.1. PyTorch's CUDA wheels are decoupled from the host CUDA toolkit: a `cu121`/`cu124`/`cu126` wheel runs on any driver new enough for that CUDA major. Driver 592 is current (late 2025), so compatibility with `cu121`+ is expected.

**Constraint that matters:** the RTX 2050 has 4 GiB. That is small. The 1D U-Net proposal in `tech.md` (depth 4, ~16 base channels) was chosen precisely so 4 GiB is workable with a small window (3072 samples), a modest batch, and optional AMP. Nothing architectural needs to change; the CUDA build just lets `NFR-006`/`NFR-007` be tested for real.

### 3.4 Recommended PyTorch installation (to be executed only after approval)

Keep the current `torch 2.13.0+cpu` wheel **until** the owner approves the CUDA swap. When approved, P0 should do, in a **fresh `.venv`**, not in the global interpreter:

```powershell
# INSIDE the new .venv ONLY — do not touch the global interpreter
python -m pip install --upgrade pip
# CPU build is replaced, not supplemented
python -m pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no-cuda')"
# Expected (version numbers will be newer than 2.13): e.g. "2.9.x+cu121 True NVIDIA GeForce RTX 2050"
```

*Why `cu121` rather than `cu124`/`cu126`/`cu128`:* `cu121` has the broadest wheel coverage and the smallest download; any `cu12x` wheel that matches the PyTorch version is fine — the choice is not load-bearing. The command above uses the canonical PyTorch index, not `pip install torch[gpu]`.

*Why torchvision/torchaudio pinned together:* PyTorch's CUDA wheels are released as a matched triple. Installing only `torch` and leaving the previous CPU `torchvision` would silently keep a CPU dependency tree.

*What is NOT proposed here:* no change to the global `C:\Python314` interpreter; no change to `PATH`; no driver update; no CUDA toolkit install (the wheel is self-contained).

### 3.5 Alternatives considered

| Alternative | Assessment |
|---|---|
| Keep CPU-only and rely on free-tier cloud | Valid and already documented as assumption `A6`. Retained as the **fallback**, not the default. Adequate for the skeleton, inadequate for `NFR-006`. |
| Downgrade to Python 3.11 + CUDA torch (the 2024 recommendation) | Valid fallback. Requires re-creating the interpreter, re-verifying 4+ seismic packages on 3.11, and invalidating the compatibility finding in §2. Warranted only if 3.14 install proof fails. |
| Install a night-build or `cu128` cutting-edge torch | Unneeded churn for a P0 decision; pin to a stable release. |

---

## 4. Reproducibility and dependency versioning

`FR-082` requires a pinned dependency specification that a fresh environment installs from. That file does not exist yet and is **not** created by this plan (it will be created by the approved P0 execution). The policy this plan assumes is `REPRODUCIBILITY.md` §4:

* resolver-generated lock (not `pip freeze`);
* exact pins for direct and transitive deps;
* the interpreter version and platform recorded;
* CPU-only vs CUDA as separate pins;
* the lockfile hash recorded in `run.json`.

No version is guessed in this document. The only versions stated as fact are those in §1 that were read from the running interpreter.

---

## 5. Approved next steps (nothing runs until approved)

1. **Owner approves** this plan and confirms the `.venv`-local CUDA swap is acceptable (global interpreter untouched).
2. **Execute P0 in a clean `.venv`:**
   1. `py -3.14 -m venv .venv` (or `python -m venv .venv` — the exact launcher is host-specific; §1 notes only 3.14 is known on `PATH`).
   2. Activate (PowerShell `.\.venv\Scripts\Activate.ps1` — may require a one-time `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`).
   3. `python -m pip install -r requirements.lock` once the lock exists — until then, install only what the skeleton needs (`numpy`, `scipy`, `PyYAML`, `pytest`) and prove the seismic stack installs.
   4. Run the CUDA-swap command in §3.4 **inside** the `.venv`.
   5. Run `python -c "import torch; ..."` and `nvidia-smi` again; record both in `REPRODUCIBILITY.md`.
3. **Record.** Update `REPRODUCIBILITY.md` §3 with the interpreter actually created, the `pip install` log, and the post-swap `torch.cuda.is_available()` result. Pin the lock and commit it.
4. Proceed to Task 3 — the skeleton already assumes the outcome (NumPy-only code paths work on either build).

---

## 6. Risks and caveats

* **NumPy 2.x.** The installed `numpy 2.4.3` is a NumPy 2 major. ObsPy 1.5.1 lists `numpy>=1.21` and is therefore 2.x-tolerant *in declaration*, but a specific C-extension wheel can still assume NumPy 1 at runtime. If `import obspy` fails with an ABI error after `pip install`, the mitigation is a compatibility pin (`numpy<2` or `numpy==1.26.*`) in the lock — a known class of P0 friction, not a new finding.
* **RTX 2050 compute capability.** The device is a laptop Ampere (GA107). No issue for the 1D U-Net; only models with large attention or 3-D convolutions would probe its limits, and none are proposed.
* **Host CUDA 13.1 vs wheel `cu121`.** The host reports CUDA 13.1, but the wheel's `cu12x` refers to the **CUDA runtime bundled inside the wheel**, not the host toolkit. Driver 592 satisfies both.

---

## 7. Relationship to requirements

* `tech.md` §1 and `TECH_STACK.md` — the recommended stack; this plan finds Python 3.14 compatible with it, so the 3.11/3.12 recommendation becomes a fallback, not a prerequisite.
* PRD `FR-082`, `NFR-001`, `NFR-006`, `NFR-007` — the lockfile, reproducibility-on-same-hardware, and GPU feasibility obligations; this plan is the P0 execution that satisfies their preconditions.
* `DEVELOPMENT_ROADMAP.md` P0 — "Repository and environment setup"; `AUDIT_REPORT.md` §13 items 3–4. This plan is that phase's environment half.
* `REPRODUCIBILITY.md` §3 — the environment chapter this plan will update once executed.

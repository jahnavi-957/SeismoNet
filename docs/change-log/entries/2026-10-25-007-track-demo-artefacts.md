# 2026-10-25-007 — Track the frozen demo artefacts so a clone can run

## A. Change identification

- Change ID: `2026-10-25-007`
- Date: 2026-10-25
- Short title: Track the frozen demo artefacts so a clone can run
- Category: configuration | bug fix | documentation
- Files modified: `.gitignore`, `README.md`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`, this entry
- Files added (2.91 MB): `runs/experiment_002_p_training/{best.pt,run.json}`, `runs/validation_protocol_candidate_seed42/protocol.json`, `runs/pilot_seed42/{run.json,config_snapshot.yaml}`, `runs/eval_test_best/metrics.json`, `runs/validation_inference_p6_seed42/predictions.json`

## B. What was changed?

Seven files under `runs/` are now tracked. Everything else under `runs/` remains ignored, as before.

## C. Why was this change necessary?

The repository was pushed to GitHub, and a fresh clone could not run the web application at all:

```
FileNotFoundError: runs\experiment_002_p_training\best.pt
```

`backend/main.py` constructs `SeismoInferenceEngine` at import time, and that constructor loads the
checkpoint immediately, so uvicorn failed to start rather than degrading. `/api/metrics` would also have
returned 503 (no `eval_test_best/metrics.json`) and `/api/traces` would have exposed only the three-trace
fixture (no `predictions.json`).

The `.gitignore` policy was correct for training output but wrong for submission: a reviewer following the
README's "Try the demo in 60 seconds" section hit a crash.

## D. Why this approach was chosen?

Shipping the artefacts is the smallest change that makes the documented quick start true. They are *inputs*
to the demonstration, not regenerated output: the checkpoint is frozen, the protocol was frozen before the
test split was opened, and `metrics.json` is the recorded one-time evaluation. Nothing here is recomputed by
a run, so tracking them cannot make a result look different from what was reported.

The total is 2.91 MB — small enough for GitHub, and far smaller than the alternative of a download step that
break in a demo. A code change to degrade gracefully without a checkpoint was also considered and rejected:
it would add a failure mode to the demo path and still leave the app unable to pick.

`runs/` had to become `runs/*` in `.gitignore`, because Git cannot re-include a file whose parent directory
is excluded; the negations then apply per file.

## E. How was it implemented?

```diff
-runs/
+runs/*
```

plus an explicit exception block at the end of `.gitignore`, one `!` rule per tracked file. Verified with
`git add -An runs/`, which lists exactly the seven intended files and nothing else.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** `git clone` → `uvicorn backend.main:app` now imports and serves, instead of
  raising `FileNotFoundError`.
- **VERIFIED improvement:** the Model Evaluation page returns the recorded held-out metrics from a clone.
- **VERIFIED improvement:** the Phase Picker lists all 210 demo traces from a clone.
- Training output (per-epoch checkpoints, figures, other runs) remains untracked.

## G. Testing and verification

- `git add -An runs/` → exactly 7 files, **2.91 MB**, no unintended artefacts.
- Fresh clone into a temporary directory; `backend.main` imported successfully with the project `.venv`.
- `git check-ignore` confirms every other file under `runs/` is still ignored.
- No model, protocol, split, or metric value was modified — the files are byte-identical to the ones that
  produced the reported results (checkpoint SHA-256 `180FEE49…58B4`, `splits/split.json` `D435841A…F1B8`).

## H. Risks and side effects

The repository grows by ~2.9 MB and the checkpoint becomes public unless the repository itself is private.
The dataset is still absent, so the Phase Picker continues to use its labelled `synthetic_demo_fallback`;
this change does not make the demo use real waveforms.

## I. Relationship to the PRD and roadmap

Reproducibility and demonstration packaging (`FR-046`, `FR-077`, `FR-082`). No scientific artefact is altered;
the tracked files are the frozen inputs already described in `docs/REPRODUCIBILITY.md`.

## J. Next steps

- If the repository is public and the checkpoint should not be, make the repository private rather than
  untracking the file — the demo depends on it.

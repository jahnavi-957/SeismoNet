# 2026-10-25-008 — Make the cloned app importable without an editable install

## A. Change identification

- Change ID: `2026-10-25-008`
- Date: 2026-10-25
- Short title: Make the cloned app importable without an editable install
- Category: bug fix | documentation
- Files modified: `backend/main.py`, `scripts/make_demo_csv.py`, `README.md`, `docs/change-log/CHANGELOG.md`, `docs/change-log/CURRENT_STATUS.md`, this entry

## B. What was changed?

`backend/main.py` now inserts the repository's `src/` directory on `sys.path` before importing the research
package, and `scripts/make_demo_csv.py` does the same. The README's quick start states that
`pip install -e .` is optional as a result.

## C. Why was this change necessary?

Entry `2026-10-25-007` shipped the frozen artefacts so a clone could run, and a clone then imported
successfully **in this working copy** — but only because the existing `.venv` contains an editable install
(`__editable__.seismonet-0.1.0.pth` pointing at `src/`). Simulating a reviewer's environment by removing that
single path gave:

```
FileNotFoundError/ModuleNotFoundError: No module named 'seismonet'
```

`pyproject.toml` declares `pythonpath = ["src"]`, which applies to pytest only; a plain
`uvicorn backend.main:app` from a clean environment could therefore not import `seismonet`, and the README
said to install `requirements.lock` but never to install the project itself.

## D. Why this approach was chosen?

Four lines in the entry point are cheaper and more reliable than asking a reviewer to remember an install
step, and they cannot change behaviour in an environment where the package is already installed: the path is
only inserted if it exists and is not already present. Documenting `pip install -e .` remains correct and is
still offered, but the demo now works either way.

## E. How was it implemented?

```python
_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
```

placed above the `backend.*` imports in `backend/main.py`, and an equivalent `sys.path.insert` for `src/` in
`scripts/make_demo_csv.py`.

## F. How did this improve SeismoNet?

- **VERIFIED improvement:** with the editable install removed from `sys.path`, `import backend.main` now
  succeeds and reports `synthetic_demo_fallback`, the checkpoint present, protocol
  `protocol-5fa5744aca58cc3c`, and **210 traces available**.
- **VERIFIED improvement:** the README quick start is true for a reviewer with no prior install step.
- Local behaviour is unchanged: the app still imports, and the suite is still 190 passed.

## G. Testing and verification

- Simulated reviewer environment: copied `backend/` and `src/` into a fresh clone, stripped the editable
  `.pth` path, imported `backend.main` → success (see F).
- `.venv\Scripts\python -m pytest tests -q` → **190 passed, 36 skipped**.
- Local `import backend.main` → success, `data_source` still `synthetic_demo_fallback`.

## H. Risks and side effects

The bootstrap silently prefers the repository's own `src/` over any installed copy of `seismonet`, which is
the desired behaviour for a demo but would be surprising in an installed-package deployment. It only runs
when `src/` exists next to `backend/`, so a wheel-style deployment is unaffected.

## I. Relationship to the PRD and roadmap

Reproducibility of the demonstration (`FR-077`, `FR-082`). No scientific artefact or reported number changes.

## J. Next steps

- Consider a `make demo` / `scripts/run_demo.ps1` wrapper that starts both servers, so the two-terminal
  instructions become one command.

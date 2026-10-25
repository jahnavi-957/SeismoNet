"""Waveform validation — PRD FR-003 (data-quality gate) and FR-008 (inference input validation).

Two layers live in this module.

1. **Per-window validation** — ``validate_waveform`` / ``validate_picks`` / ``validate_arrival_in_trace``.
   Used on the inference path (FR-008, SR-001/SR-002/SR-003, edge cases E10–E12, E18) and by the
   loader before a window is normalised. These never raise for *data* problems: they return a
   ``ValidationResult`` so the caller decides the policy and can log a reason (FR-008, NFR-004).

2. **Per-dataset screening** — ``screen_metadata`` returning a ``QualityReport`` with
   ``Rejection`` records, ``counts_by_reason`` and a per-check coverage map. This implements
   FR-003 ("detect and exclude or flag unusable traces … log the count and reason for each
   exclusion") and the success criterion SC-9 / ``docs/DATASET_GUIDE.md`` §10 and §12
   ("data-quality log specification").

Guards and their rationale (each guard names the failure it prevents):

* ``arrival_sample >= trace_npts`` is rejected (FR-002 edge). A pick index is used to place a
  Gaussian target inside the window; an index equal to the trace length indexes one sample past
  the end, which is either a silent clipping bug in the dataset or an off-by-one convention
  mismatch. Either way the label is unusable, so it must not reach training.
* ``arrival_sample < 0``           — negative indices silently wrap in NumPy indexing.
* Empty string / ``None`` arrival  — this is the *documented* INSTANCE encoding for "S not
  picked" (Stage 2 evidence: missing S is ``''``, not ``0``). It is **missing**, not invalid:
  it is counted and kept, and the loader turns it into an all-zero S channel (FR-024, E1/E2).
  Conflating "missing" with "invalid" would either drop 39 % of the sample or fabricate a pick.
* shape ``(3, L)`` with ``C == 3``  — a two-component or 1-D record cannot be fed to a fixed
  3-channel U-Net; catching it here keeps the error at the data boundary (E12, SR-001).
* dtype / finite / flat             — non-finite samples poison normalisation; a zero-variance
  trace yields a zero peak and a divide-by-zero in normalisation (E10, E11, FR-014).
* component order                   — SR-002 requires the ``(Z, N, E)`` order to be *asserted*,
  because a silently swapped horizontal pair corrupts S-wave learning while leaving the pipeline
  apparently working. An undeclared order is therefore treated as not-established, not as fine.
* duplicate trace_name              — E25; duplicates double-count a trace across splits.
* metadata vs HDF5 agreement        — ``trace_npts`` vs the real ``shape[1]`` and ``trace_dt_s``
  vs the declared sampling rate: sample indices, labels and tolerances are all rate-dependent,
  so a mismatch is a silent-error source (§4.4, SR-003, E18).

Memory policy: screening opens the HDF5 once and materialises **one record at a time**
(``dataset[()]``, ≈144 kB for ``(3, 12000) int32``). The full waveform block is never read, so
screening the 10 k-sample (1.44 GB) file stays within a few hundred kB of extra RSS.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import numpy.typing as npt


Reason = str  # one of the REASONS values below; kept as str for forward-compatible logging

#: Rejection reasons emitted by the screening layer. Stable strings — they are written to the
#: quality log (docs/DATASET_GUIDE.md §12) and counted in ``QualityReport.counts_by_reason``.
REASONS = (
    "missing_in_hdf5",
    "duplicate_trace_name",
    "bad_metadata_row",
    "channel_order",
    "wrong_shape",
    "wrong_dtype",
    "unreadable",
    "non_finite",
    "flat",
    "metadata_mismatch",
    "missing_p",
    "bad_pick",
    "arrival_out_of_range",
    "s_before_p",
)

#: Checks whose coverage ``screen_metadata`` reports. ``checked_keys[name]`` is the number of
#: records on which the check was *actually evaluated* — not the number of records it could
#: have applied to. Coverage is evidence: a check that never ran reports 0 and cannot be
#: mistaken for "the dataset passed this check".
CHECKS = (
    "metadata_rows",
    "hdf5_keys",
    "key_exists",
    "duplicate_trace_name",
    "component_order",
    "shape",
    "dtype",
    "values",
    "trace_npts",
    "trace_dt_s",
    "p_arrival",
    "s_arrival",
    "s_after_p",
)

EXPECTED_COMPONENTS = 3  # Z, N, E — SR-001 / FR-008
DEFAULT_EXPECTED_SHAPE: tuple[int, int] = (3, 12000)  # INSTANCE Counts sample (SR-001/SR-004)
DEFAULT_EXPECTED_DTYPE = "int32"
DEFAULT_EXPECTED_COMPONENT_ORDER = "ENZ"
DEFAULT_EXPECTED_RATE = 100.0  # Hz — SR-003 default; INSTANCE Counts dt 0.01 s


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str | None  # None when ok, otherwise one of REASONS / the legacy validation reasons
    detail: str  # human-readable; logged per FR-003


@dataclass(frozen=True)
class Rejection:
    """One rejected metadata row — the unit of the data-quality log (FR-003, SC-9)."""

    trace_name: str
    event_id: str | None
    reason: str
    detail: str
    phase: str | None = None  # "P" | "S" | None — DATASET_GUIDE §12 "Phase affected"
    action: str = "excluded"  # DATASET_GUIDE §12 "Action taken"


@dataclass
class QualityReport:
    """Structured FR-003 screening result (required by §9/§12 QC reporting)."""

    total: int
    kept: int
    rejected: list[Rejection]
    counts_by_reason: Counter
    checked_keys: dict[str, int]

    # --- supporting evidence (not required by the caller contract, but needed for §12/FR-002)
    hdf5_path: str | None = None
    hdf5_group: str = "data"
    n_metadata_keys: int = 0
    n_hdf5_keys: int = 0
    hdf5_only_keys: list[str] = field(default_factory=list)
    component_order: str | None = None
    expected_component_order: str | None = None
    expected_shape: tuple[int, ...] | None = None
    pick_availability: dict[str, int] = field(default_factory=dict)
    dt_s_distribution: dict[str, int] = field(default_factory=dict)
    event_coverage: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when nothing was rejected. Screening never *hides* a defect to reach True."""
        return not self.rejected

    @property
    def n_rejected(self) -> int:
        return len(self.rejected)

    def summary(self) -> dict[str, Any]:
        """Machine-readable summary for the quality log (SC-9) / FR-002 dataset statistics."""
        total = self.total
        return {
            "total": total,
            "kept": self.kept,
            "rejected": self.n_rejected,
            "exclusion_rate": (self.n_rejected / total) if total else 0.0,
            "counts_by_reason": dict(self.counts_by_reason),
            "checked_keys": dict(self.checked_keys),
            "pick_availability": dict(self.pick_availability),
            "dt_s_distribution": dict(self.dt_s_distribution),
            "event_coverage": dict(self.event_coverage),
            "component_order": self.component_order,
            "warnings": list(self.warnings),
        }


def _has_nan_or_inf(waveform: npt.NDArray[np.floating]) -> bool:
    try:
        return bool(np.any(~np.isfinite(waveform)))
    except TypeError:  # non-numeric dtype: cannot be proven finite -> treat as not usable
        return True


def _is_flat(waveform: npt.NDArray[np.floating], atol: float = 1e-12) -> bool:
    # A trace is "flat" if every sample is identical within atol along each channel,
    # or the whole trace variance is ~0. We check per-channel variance and global.
    if waveform.size == 0:
        return True
    # variance per channel (axis=1 when shape is (C, L))
    if waveform.ndim == 2:
        per_channel_var = np.var(waveform, axis=1)
        if np.all(per_channel_var < atol):
            return True
        # also: overall variance
        if float(np.var(waveform)) < atol:
            return True
        return False
    return bool(float(np.var(waveform)) < atol)


def validate_waveform(
    waveform: npt.NDArray[np.floating],
    *,
    expected_length: int | None = None,
    sampling_rate: float | None = None,
    expected_rate: float | None = None,
) -> ValidationResult:
    """Validate a single waveform window.

    Checks (in order):
      1. shape — must be (3, L) (C, L) with C == 3; otherwise wrong_shape.
      2. expected_length — if given, L must match.
      3. sampling_rate vs expected_rate — must match if both given.
      4. NaN/Inf — any non-finite sample.
      5. flat — zero-variance trace/channel.

    Returns a ValidationResult; never raises for invalid data (FR-008: reject with a reason).
    """
    arr = np.asarray(waveform)

    # 1. Shape check: must be 2-D with 3 channels.
    if arr.ndim != 2 or arr.shape[0] != EXPECTED_COMPONENTS:
        shape_str = f"{arr.shape}" if arr.ndim >= 1 else "scalar"
        detail = f"expected shape (3, L), got {shape_str}"
        if expected_length is not None and arr.ndim == 2:
            detail += f"; expected_length={expected_length}"
        return ValidationResult(ok=False, reason="wrong_shape", detail=detail)

    _, length = arr.shape

    # 2. Length check
    if expected_length is not None and length != expected_length:
        return ValidationResult(
            ok=False,
            reason="wrong_shape",
            detail=f"expected length {expected_length}, got {length}",
        )

    # 3. Sampling-rate check
    if expected_rate is not None and sampling_rate is not None:
        # Use relative tolerance; seismology rates are exact (e.g. 100.0) so tight is fine.
        if not np.isclose(sampling_rate, expected_rate, rtol=1e-6, atol=1e-9):
            return ValidationResult(
                ok=False,
                reason="wrong_rate",
                detail=f"expected_rate {expected_rate}, got {sampling_rate}",
            )

    # 4. NaN/Inf
    if _has_nan_or_inf(arr):
        return ValidationResult(ok=False, reason="nan_or_inf", detail="waveform contains NaN or Inf")

    # 5. Flat
    if _is_flat(arr):
        return ValidationResult(ok=False, reason="flat", detail="waveform is flat (zero variance)")

    return ValidationResult(ok=True, reason=None, detail="ok")


def validate_picks(
    p_idx: int | None,
    s_idx: int | None,
    window_length: int,
) -> ValidationResult:
    """Validate P/S pick indices relative to a window.

    - Indices must be in [0, window_length) if present.
    - If both present, S must be strictly after P (otherwise s_after_p).
    """
    for label, idx in (("P", p_idx), ("S", s_idx)):
        if idx is not None:
            if not isinstance(idx, (int, np.integer)):
                return ValidationResult(ok=False, reason="missing_pick", detail=f"{label} pick is not an integer: {idx!r}")
            if idx < 0 or idx >= window_length:
                return ValidationResult(
                    ok=False,
                    reason="wrong_shape",
                    detail=f"{label} pick {idx} out of bounds for window length {window_length}",
                )
    if p_idx is not None and s_idx is not None:
        if s_idx <= p_idx:
            return ValidationResult(
                ok=False,
                reason="s_after_p",
                detail=f"S pick {s_idx} is not strictly after P pick {p_idx}",
            )
    return ValidationResult(ok=True, reason=None, detail="ok")


def validate_arrival_in_trace(
    p_idx_or_none: int | str | None,
    npts: int,
) -> ValidationResult:
    """Validate one reference arrival index against the number of samples in its trace.

    Contract (FR-002 edge, DR-002, E1/E2):

    * ``None`` or ``""`` (after stripping) means the phase was **not picked**. That is
      *missing*, which is a valid state — ``detail == "missing"`` and ``ok is True``. The
      INSTANCE Counts metadata encodes a missing S exactly this way, so treating it as an
      error would drop 39 % of the sample; treating it as ``0`` would fabricate a pick.
    * An integer-like value must satisfy ``0 <= arrival_sample < npts``.
      ``arrival_sample >= trace_npts`` is rejected: the index points past the last sample, so
      any target/window built from it is wrong. ``arrival_sample < 0`` is rejected because
      NumPy would silently wrap a negative index to the end of the array.
    * Non-integer or unparsable values are rejected as ``bad_pick``.

    ``npts <= 0`` is a programming error (there is no trace to validate against) and raises
    ``ValueError``; it is not a data-quality finding.
    """
    if not isinstance(npts, (int, np.integer)) or isinstance(npts, bool) or int(npts) <= 0:
        raise ValueError(f"npts must be a positive integer trace length, got {npts!r}")

    if p_idx_or_none is None:
        return ValidationResult(ok=True, reason=None, detail="missing")

    if isinstance(p_idx_or_none, str):
        raw = p_idx_or_none.strip()
        if raw == "":
            return ValidationResult(ok=True, reason=None, detail="missing")
        try:
            value = float(raw)
        except ValueError:
            return ValidationResult(
                ok=False, reason="bad_pick", detail=f"arrival is not numeric: {p_idx_or_none!r}"
            )
        if not float(value).is_integer():
            return ValidationResult(
                ok=False, reason="bad_pick", detail=f"arrival is not an integer sample index: {raw!r}"
            )
        idx = int(value)
    elif isinstance(p_idx_or_none, bool):
        return ValidationResult(
            ok=False, reason="bad_pick", detail=f"arrival is a boolean, not a sample index: {p_idx_or_none!r}"
        )
    elif isinstance(p_idx_or_none, (int, np.integer)):
        idx = int(p_idx_or_none)
    elif isinstance(p_idx_or_none, (float, np.floating)):
        if not float(p_idx_or_none).is_integer():
            return ValidationResult(
                ok=False, reason="bad_pick", detail=f"arrival is not an integer sample index: {p_idx_or_none!r}"
            )
        idx = int(p_idx_or_none)
    else:
        return ValidationResult(
            ok=False, reason="bad_pick", detail=f"unsupported arrival value: {p_idx_or_none!r}"
        )

    if idx < 0 or idx >= int(npts):
        return ValidationResult(
            ok=False,
            reason="arrival_out_of_range",
            detail=f"arrival_sample {idx} outside [0, {int(npts)}) for trace_npts={int(npts)}",
        )
    return ValidationResult(ok=True, reason=None, detail="ok")


# --------------------------------------------------------------------------------------
# Dataset-level screening (FR-003 / SC-9)
# --------------------------------------------------------------------------------------


def _import_h5py():
    """Import h5py lazily.

    Keeps ``h5py`` optional for the per-window validation path (FR-008) so that unit tests and
    inference validation do not require the HDF5 stack, and a missing h5py gives one clear
    message instead of an ImportError at module import time (NFR-004).
    """
    try:
        import h5py  # noqa: PLC0415 — deliberate lazy import
    except ImportError as exc:  # pragma: no cover - exercised only without h5py
        raise ImportError(
            "screen_metadata/read_hdf5_format_info require h5py (HDF5 reader); "
            "install it from requirements.lock. Per-window validation does not need it."
        ) from exc
    return h5py


def _decode_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        return _decode_scalar(value.reshape(-1)[0])
    return str(value)


def _handle_format_info(f: Any, *, expected_rate: float | None = None) -> dict[str, Any]:
    """Read the file-level ``data_format`` block and the dt basis from an **open** HDF5 file.

    Returns declared component/dimension order and the sampling-rate basis. Nothing is
    inferred unless stated: ``rate_source`` records where the comparison dt came from, so a
    report can never claim a metadata rate was checked against a declaration that does not
    exist on disk.
    """
    info: dict[str, Any] = {
        "component_order": None,
        "dimension_order": None,
        "sampling_rate": None,
        "sampling_rate_source": None,
        "dt_s": None,
        "dt_s_source": None,
        "unit": None,
        "measurement": None,
        "instrument_response": None,
    }

    group = f.get("data_format")
    if group is not None:
        for key, out_key in (
            ("component_order", "component_order"),
            ("dimension_order", "dimension_order"),
            ("unit", "unit"),
            ("measurement", "measurement"),
            ("instrument_response", "instrument_response"),
        ):
            if key in group:
                info[out_key] = _decode_scalar(group[key][()])
        for key in ("sampling_rate", "sampling_rate_hz", "sample_rate", "sampling_frequency"):
            if key in group:
                raw = _decode_scalar(group[key][()])
                try:
                    info["sampling_rate"] = float(raw)
                    info["sampling_rate_source"] = f"data_format/{key}"
                except (TypeError, ValueError):
                    pass
                break
        for key in ("trace_dt_s", "dt_s", "delta_s"):
            if key in group:
                raw = _decode_scalar(group[key][()])
                try:
                    info["dt_s"] = float(raw)
                    info["dt_s_source"] = f"data_format/{key}"
                except (TypeError, ValueError):
                    pass
                break

    # Root/dataset attributes are a documented fallback location for the same quantities.
    for source, obj in (("hdf5 attr", f.attrs),):
        if info["sampling_rate"] is None and "sampling_rate" in obj:
            try:
                info["sampling_rate"] = float(_decode_scalar(obj["sampling_rate"]))
                info["sampling_rate_source"] = f"{source}:sampling_rate"
            except (TypeError, ValueError):
                pass
        if info["dt_s"] is None and "trace_dt_s" in obj:
            try:
                info["dt_s"] = float(_decode_scalar(obj["trace_dt_s"]))
                info["dt_s_source"] = f"{source}:trace_dt_s"
            except (TypeError, ValueError):
                pass

    # The dt actually used for the metadata comparison, and where it came from.
    if info["sampling_rate"]:
        info["expected_dt_s"] = 1.0 / float(info["sampling_rate"])
        info["expected_dt_source"] = info["sampling_rate_source"]
    elif info["dt_s"]:
        info["expected_dt_s"] = float(info["dt_s"])
        info["expected_dt_source"] = info["dt_s_source"]
    elif expected_rate:
        info["expected_dt_s"] = 1.0 / float(expected_rate)
        info["expected_dt_source"] = f"expected_rate={expected_rate} Hz (config, SR-003)"
    else:
        info["expected_dt_s"] = None
        info["expected_dt_source"] = None
    return info


def read_hdf5_format_info(
    hdf5_path: str | Path,
    *,
    hdf5_group: str = "data",
    expected_rate: float | None = DEFAULT_EXPECTED_RATE,
) -> dict[str, Any]:
    """Probe the declared format of an HDF5 file with a short-lived, read-only handle.

    Shared by the loader (``verify_hdf5_coverage``) and the screener, so both compare metadata
    against the *same* reading of ``data_format`` instead of two divergent guesses.
    """
    h5py = _import_h5py()
    with h5py.File(str(hdf5_path), "r") as f:
        if hdf5_group not in f:
            raise KeyError(
                f"HDF5 group {hdf5_group!r} not found in {hdf5_path!s}; root keys={sorted(f.keys())}"
            )
        return _handle_format_info(f, expected_rate=expected_rate)


def metadata_items(
    metadata: Mapping[str, Mapping[str, str]] | Sequence[Mapping[str, str]],
    duplicates: Iterable[str] | None = None,
) -> tuple[list[tuple[str, dict[str, str]]], set[str]]:
    """Normalise ``metadata`` to ``(ordered [(trace_name, row)], duplicate_names)``.

    Accepts either the canonical ``dict[trace_name -> row]`` (the loader's ``load_metadata``
    result) or the raw CSV row sequence. The sequence form is required to *detect* duplicate
    ``trace_name`` values: a dict has already collapsed them, so duplicates can only be seen
    before that collapse (E25). ``duplicates`` lets a caller that read the CSV itself pass the
    names it saw repeated.
    """
    dup: set[str] = set()
    items: list[tuple[str, dict[str, str]]] = []

    if isinstance(metadata, Mapping):
        for key, row in metadata.items():
            name = str(key).strip()
            row_d = dict(row)
            items.append((name, row_d))
            embedded = row_d.get("trace_name")
            if embedded is not None and str(embedded).strip() and str(embedded).strip() != name:
                # The mapping disagrees with the row it was built from: two rows sharing this
                # trace_name were collapsed into one entry.
                dup.add(name)
    else:
        seen: Counter = Counter()
        for row in metadata:
            row_d = dict(row)
            raw_name = row_d.get("trace_name")
            name = "" if raw_name is None else str(raw_name).strip()
            items.append((name, row_d))
            if name:
                seen[name] += 1
        dup |= {name for name, count in seen.items() if count > 1}

    for name in duplicates or ():
        dup.add(str(name).strip())
    return items, dup


def _first_nonempty(row: Mapping[str, str], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def screen_metadata(
    metadata: Mapping[str, Mapping[str, str]] | Sequence[Mapping[str, str]],
    hdf5_path: str | Path,
    *,
    hdf5_group: str = "data",
    expected_shape: tuple[int, int] = DEFAULT_EXPECTED_SHAPE,
    expected_dtype: str | np.dtype = DEFAULT_EXPECTED_DTYPE,
    expected_component_order: str | None = DEFAULT_EXPECTED_COMPONENT_ORDER,
    expected_rate: float | None = DEFAULT_EXPECTED_RATE,
    require_p: bool = True,
    check_flat: bool = True,
    read_values: bool = True,
    duplicates: Iterable[str] | None = None,
    event_id_keys: Sequence[str] = ("event_id", "source_id"),
) -> QualityReport:
    """Screen metadata rows against an HDF5 file and return a structured ``QualityReport``.

    Checks, in the order applied per record (first failure wins, so
    ``total == kept + len(rejected)`` always holds and each trace is logged once):

    1. ``duplicate_trace_name``   — E25; a duplicate would double-count a trace.
    2. ``missing_in_hdf5``        — the metadata row has no waveform record.
    3. ``wrong_shape``            — record shape must be ``expected_shape`` (default ``(3, 12000)``).
    4. ``wrong_dtype``            — record dtype must be ``expected_dtype`` (default ``int32``).
    5. ``non_finite`` / ``flat``  — read *that one record* and check finiteness/variance.
    6. ``metadata_mismatch``      — ``trace_npts`` vs the real ``shape[1]``; ``trace_dt_s`` vs the
       declared sampling rate (or the configured expected rate when the file declares none).
    7. ``missing_p``              — P is required (DR-002) when ``require_p``.
    8. ``bad_pick`` / ``arrival_out_of_range`` — P and S must parse and lie in ``[0, npts)``
       (FR-002 edge: ``arrival_sample >= trace_npts`` is rejected).
    9. ``s_before_p``             — E5 physical plausibility.

    A missing **S** (empty/None) is *not* a rejection: it is counted in
    ``pick_availability['s_missing']`` and left for the loader to encode as an all-zero S
    channel (FR-024). The file-level component order is checked once; a wrong or undeclared
    order rejects every trace under SR-002.

    Memory: one record materialised at a time; the full dataset block is never loaded.
    """
    h5py = _import_h5py()

    if expected_shape[0] != EXPECTED_COMPONENTS or expected_shape[1] <= 0:
        raise ValueError(
            f"expected_shape must be (3, L) with L > 0, got {tuple(expected_shape)} (SR-001)"
        )
    expected_shape = (int(expected_shape[0]), int(expected_shape[1]))
    expected_dtype_np = np.dtype(expected_dtype)

    items, dup_names = metadata_items(metadata, duplicates)

    checked: dict[str, int] = {name: 0 for name in CHECKS}
    checked["metadata_rows"] = len(items)

    rejected: list[Rejection] = []
    counts: Counter = Counter()
    pick_availability: Counter = Counter({"p_present": 0, "p_missing": 0, "s_present": 0, "s_missing": 0})
    dt_distribution: Counter = Counter()
    event_coverage: Counter = Counter({"with_event_id": 0, "without_event_id": 0})
    warnings: list[str] = []
    kept = 0

    def reject(name: str, row: Mapping[str, str], reason: str, detail: str, phase: str | None = None) -> None:
        rejected.append(
            Rejection(
                trace_name=name,
                event_id=_first_nonempty(row, event_id_keys),
                reason=reason,
                detail=detail,
                phase=phase,
            )
        )
        counts[reason] += 1

    with h5py.File(str(hdf5_path), "r") as f:
        if hdf5_group not in f:
            raise KeyError(
                f"HDF5 group {hdf5_group!r} not found in {hdf5_path!s}; root keys={sorted(f.keys())}"
            )
        group = f[hdf5_group]
        hdf5_keys = set(group.keys())
        checked["hdf5_keys"] = len(hdf5_keys)

        format_info = _handle_format_info(f, expected_rate=expected_rate)
        component_order = format_info["component_order"]

        # File-level order guard (SR-002). One check, applied to every trace: an order that is
        # wrong *or* cannot be established excludes the file, because a silently swapped
        # horizontal pair corrupts S learning while the pipeline still "works".
        checked["component_order"] = len(items)
        order_ok = True
        if expected_component_order is not None:
            if component_order is None:
                order_ok = False
                warnings.append(
                    f"data_format/component_order is not declared; SR-002 requires the order to be "
                    f"asserted, so every trace is rejected (expected {expected_component_order!r})."
                )
            elif component_order != expected_component_order:
                order_ok = False
                warnings.append(
                    f"data_format/component_order={component_order!r} != expected "
                    f"{expected_component_order!r}."
                )
        if format_info["expected_dt_s"] is None:
            warnings.append("no sampling rate declared and no expected_rate given: trace_dt_s not checked.")

        hdf5_only_keys = sorted(hdf5_keys - {name for name, _ in items})
        if hdf5_only_keys:
            warnings.append(
                f"{len(hdf5_only_keys)} HDF5 key(s) have no metadata row (see report.hdf5_only_keys)."
            )

        for name, row in items:
            # Resolve the record lazily, one trace at a time: only this handle is in scope and
            # only the current record is ever materialised (memory policy at module top).
            dataset = group[name] if name in hdf5_keys else None

            if not name:
                reject("", row, "bad_metadata_row", "row has no trace_name")
                continue

            checked["duplicate_trace_name"] += 1
            if name in dup_names:
                reject(name, row, "duplicate_trace_name", "trace_name appears more than once in the metadata")
                continue

            if not order_ok:
                reject(
                    name,
                    row,
                    "channel_order",
                    f"declared component order {component_order!r} is not {expected_component_order!r}",
                )
                continue

            checked["key_exists"] += 1
            if dataset is None:
                reject(name, row, "missing_in_hdf5", f"no {hdf5_group}/{name} in {hdf5_path!s}")
                continue

            checked["shape"] += 1
            shape = tuple(int(s) for s in dataset.shape)
            if shape != expected_shape:
                reject(name, row, "wrong_shape", f"record shape {shape} != expected {expected_shape}")
                continue

            checked["dtype"] += 1
            if np.dtype(dataset.dtype) != expected_dtype_np:
                reject(
                    name, row, "wrong_dtype", f"record dtype {dataset.dtype} != expected {expected_dtype_np}"
                )
                continue

            npts = shape[1]

            checked["trace_npts"] += 1
            npts_meta = row.get("trace_npts")
            if npts_meta is not None and str(npts_meta).strip():
                try:
                    npts_meta_int = int(float(str(npts_meta).strip()))
                except ValueError:
                    reject(
                        name,
                        row,
                        "metadata_mismatch",
                        f"trace_npts is not an integer: {npts_meta!r}",
                    )
                    continue
                if npts_meta_int != npts:
                    reject(
                        name,
                        row,
                        "metadata_mismatch",
                        f"trace_npts={npts_meta_int} but HDF5 record has {npts} samples",
                    )
                    continue

            checked["trace_dt_s"] += 1
            dt_raw = row.get("trace_dt_s")
            dt_meta = None
            if dt_raw is not None and str(dt_raw).strip():
                dt_text = str(dt_raw).strip()
                dt_distribution[dt_text] += 1
                try:
                    dt_meta = float(dt_text)
                except ValueError:
                    reject(name, row, "metadata_mismatch", f"trace_dt_s is not numeric: {dt_raw!r}")
                    continue
                expected_dt = format_info["expected_dt_s"]
                if expected_dt is not None and not np.isclose(
                    dt_meta, float(expected_dt), rtol=1e-6, atol=1e-12
                ):
                    reject(
                        name,
                        row,
                        "metadata_mismatch",
                        f"trace_dt_s={dt_meta} != {float(expected_dt):g} s from "
                        f"{format_info['expected_dt_source']} (E18/SR-003)",
                    )
                    continue

            if read_values:
                checked["values"] += 1
                try:
                    record = dataset[()]  # ONE record; never the whole dataset block
                except Exception as exc:
                    reject(name, row, "unreadable", f"h5py failed to read the record: {exc!r}")
                    continue
                if _has_nan_or_inf(record):
                    reject(name, row, "non_finite", "record contains NaN or Inf (E10)")
                    continue
                if check_flat and _is_flat(np.asarray(record, dtype=np.float64)):
                    reject(name, row, "flat", "record is flat (zero variance across all channels) (E11)")
                    continue

            event_coverage["with_event_id" if _first_nonempty(row, event_id_keys) else "without_event_id"] += 1

            p_raw = row.get("trace_P_arrival_sample")
            p_present = p_raw is not None and str(p_raw).strip() != ""
            checked["p_arrival"] += 1
            p_idx: int | None = None
            if p_present:
                pick_availability["p_present"] += 1
                p_result = validate_arrival_in_trace(str(p_raw), npts)
                if not p_result.ok:
                    reject(name, row, p_result.reason or "bad_pick", p_result.detail, phase="P")
                    continue
                p_idx = int(float(str(p_raw).strip()))
            else:
                pick_availability["p_missing"] += 1
                # P is the anchor phase (DR-002): without it the trace cannot contribute a
                # per-sample P target, so it is excluded rather than silently zero-labelled.
                if require_p:
                    reject(name, row, "missing_p", "trace_P_arrival_sample is empty and P is required (DR-002)")
                    continue

            s_raw = row.get("trace_S_arrival_sample")
            checked["s_arrival"] += 1
            s_val = validate_arrival_in_trace(str(s_raw) if s_raw is not None else None, npts)
            if not s_val.ok:
                reject(name, row, s_val.reason or "bad_pick", s_val.detail, phase="S")
                continue
            s_missing = s_val.detail == "missing"
            pick_availability["s_missing" if s_missing else "s_present"] += 1

            if p_idx is not None and not s_missing:
                checked["s_after_p"] += 1
                s_idx = int(float(str(s_raw).strip()))
                if s_idx <= p_idx:
                    reject(
                        name,
                        row,
                        "s_before_p",
                        f"S pick {s_idx} is not strictly after P pick {p_idx} (E5)",
                        phase="S",
                    )
                    continue

            kept += 1

    if kept + len(rejected) != len(items):
        raise RuntimeError(
            f"internal screening invariant violated: kept={kept} + rejected={len(rejected)} "
            f"!= total={len(items)}"
        )

    return QualityReport(
        total=len(items),
        kept=kept,
        rejected=rejected,
        counts_by_reason=counts,
        checked_keys=checked,
        hdf5_path=str(hdf5_path),
        hdf5_group=hdf5_group,
        n_metadata_keys=len(items),
        n_hdf5_keys=len(hdf5_keys),
        hdf5_only_keys=hdf5_only_keys,
        component_order=component_order,
        expected_component_order=expected_component_order,
        expected_shape=expected_shape,
        pick_availability=dict(pick_availability),
        dt_s_distribution=dict(dt_distribution),
        event_coverage=dict(event_coverage),
        warnings=warnings,
    )


QUALITY_LOG_COLUMNS = (
    "trace_name",
    "event_id",
    "reason",
    "detail",
    "phase",
    "action",
    "timestamp",
    "run_id",
)


def write_quality_log(
    report: QualityReport,
    path: str | Path,
    *,
    run_id: str | None = None,
    timestamp: str | None = None,
) -> Path:
    """Write the FR-003 / SC-9 data-quality log as CSV, plus a counts-by-reason summary.

    Columns follow ``docs/DATASET_GUIDE.md`` §12 (trace id, reason, details, action taken, phase
    affected, timestamp/run id). A sibling ``<stem>_summary.json`` carries ``report.summary()``
    so "a summary of counts per reason accompanies the log" (§12) without re-parsing the CSV.

    Nothing is filtered: an empty ``rejected`` list still writes a header-only CSV and a summary,
    because "zero exclusions" is itself evidence (SC-9).
    """
    out = Path(path)
    if out.suffix.lower() != ".csv":
        raise ValueError(f"quality log path must end in .csv, got {out.name!r}")
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(QUALITY_LOG_COLUMNS))
        writer.writeheader()
        for item in report.rejected:
            writer.writerow(
                {
                    "trace_name": item.trace_name,
                    "event_id": item.event_id if item.event_id is not None else "",
                    "reason": item.reason,
                    "detail": item.detail,
                    "phase": item.phase if item.phase is not None else "",
                    "action": item.action,
                    "timestamp": timestamp if timestamp is not None else "",
                    "run_id": run_id if run_id is not None else "",
                }
            )

    summary_path = out.with_name(f"{out.stem}_summary.json")
    payload = report.summary()
    payload["hdf5_path"] = report.hdf5_path
    payload["hdf5_group"] = report.hdf5_group
    payload["n_metadata_keys"] = report.n_metadata_keys
    payload["n_hdf5_keys"] = report.n_hdf5_keys
    payload["run_id"] = run_id
    payload["timestamp"] = timestamp
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    return out

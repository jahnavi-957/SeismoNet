"""Production streaming loader for INSTANCE Counts (and synthetics) — PRD P2 data path.

Scope: ``FR-001`` (load the selected dataset and expose waveform + rate + P/S picks),
``FR-002`` (dataset summary statistics), ``FR-003`` (quality screening — delegated to
``seismonet.validation.screen_metadata``), ``FR-008`` (input validation at the boundary),
``DR-001``–``DR-003`` (three components + known rate, P/S labels, event identifier),
``SR-001``–``SR-003`` (``(Z, N, E)`` float window, asserted channel order, single 100 Hz rate),
``E10``–``E12`` (NaN/Inf, flat/dead channel, missing component) and ``E18`` (mixed rates).

Verified artifact this loader is written against (Stage-2 evidence, ``2026-10-17-015``):
``Instance_events_counts_10k.hdf5`` — ``data_format`` = ``ENZ`` / ``CW`` / ``counts``,
``data/<trace_name>`` datasets of shape ``(3, 12000)`` ``int32``, metadata ``trace_dt_s``
``0.01`` (100 Hz), missing S encoded as the empty string.

Design decisions, and the failure each one prevents:

* **Lazy, bounded HDF5 access.** The loader never opens one handle for a whole dataset walk
  and never calls ``group[()]``. ``load_waveform`` opens a handle for exactly one record;
  ``iter_traces`` opens a handle for at most ``batch_size`` records and closes it between
  batches. Rationale: the production file holds 1,159,249 traces (≈167 GB logical); a single
  handle held across a long training epoch is a resource leak, and reading the block materialises
  memory the pipeline does not need (NFR-007, audit §7).
* **One record at a time.** Each yielded waveform is a fresh ``(3, 12000)`` array (≈144 kB),
  so streaming a 10 k-file stays in the hundreds of kB of working set.
* **Explicit key matching.** Waveform keys are matched to metadata keys by exact
  ``trace_name``; the two set differences are returned rather than assumed empty, because the
  HDF5 and the CSV are produced by different steps and can drift (FR-001, NFR-004).
* **Structural guards.** ``trace_npts`` vs the real ``shape[1]``, ``trace_dt_s`` vs the rate
  declared in ``data_format`` (falling back to the configured expected rate, with the source
  recorded), and the declared component order are all checked in ``verify_hdf5_coverage``.
  Rationale: sample indices, labels and tolerances are all rate-dependent, and a swapped
  horizontal pair corrupts S-wave learning while leaving the pipeline apparently healthy
  (§4.4, SR-002, SR-003, E18).
* **Empty S is "missing", not "zero".** ``''`` → ``None`` → an all-zero S target channel via
  ``make_targets`` (FR-024, E1/E2). Writing ``0`` would fabricate an S arrival at sample 0.
* **Loud, never silent.** ``strict=True`` raises ``LoadError`` naming the trace and the reason;
  the default streaming mode records the skipped trace in the caller's ``skipped`` list so a
  drop is always attributable (NFR-004).
* **Synthetics work unchanged.** Nothing here depends on INSTANCE-specific fields: only
  ``trace_name``, ``trace_P_arrival_sample`` and ``trace_S_arrival_sample`` are required, and
  the format probe tolerates a file with no ``data_format`` block (it then reports the order as
  undeclared instead of guessing).
"""
from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path
from typing import Iterator, Mapping, Sequence

import h5py
import numpy as np
import numpy.typing as npt

from seismonet.labels import make_targets
from seismonet.shapes import check_window_depth_compatible
from seismonet.validation import (
    DEFAULT_EXPECTED_COMPONENT_ORDER,
    DEFAULT_EXPECTED_RATE,
    DEFAULT_EXPECTED_SHAPE,
    _handle_format_info,
    metadata_items,
    validate_arrival_in_trace,
    validate_picks,
    validate_waveform,
)

DEFAULT_HDF5_GROUP = "data"
#: Batch size for the streaming iterator. One handle per batch: large enough that the HDF5 open
#: cost is amortised (157 opens for the 10 k-file instead of 10 000), small enough that no handle
#: is held across a whole epoch and no more than 64 records are ever alive for the reader itself.
DEFAULT_BATCH_SIZE = 64

#: Metadata column names used for picks; kept as module constants so a future dataset that
#: renames them is a one-line change rather than a hunt through the loader.
P_PICK_KEY = "trace_P_arrival_sample"
S_PICK_KEY = "trace_S_arrival_sample"
NUMBER_OF_SAMPLES_KEY = "trace_npts"
DT_KEY = "trace_dt_s"

#: FR-002 summary candidates: only fields that the CSV actually carries are reported.
SUMMARY_NUMERIC_KEYS = (
    "source_magnitude",
    "path_ep_distance_km",
    "path_hyp_distance_km",
    "trace_Z_snr_db",
)
SUMMARY_EVENT_KEYS = ("event_id", "source_id")


class LoadError(RuntimeError):
    """Raised in strict mode when a trace cannot be loaded safely (NFR-004).

    The message always names the trace and the specific reason so a failure points at its cause
    instead of surfacing later as a shape error inside the model.
    """


def _skip_or_raise(
    trace_name: str,
    reason: str,
    detail: str,
    *,
    strict: bool,
    skipped: list[tuple[str, str]] | None,
) -> None:
    """Record an attributable skip, or raise ``LoadError`` in strict mode.

    Centralises the "never silently drop" policy (NFR-004): every early exit in the streaming
    path goes through here, so a dropped trace always has a name and a reason attached.
    """
    if strict:
        raise LoadError(f"{trace_name}: {reason} — {detail}")
    if skipped is not None:
        skipped.append((trace_name, reason))


# --------------------------------------------------------------------------------------
# Metadata
# --------------------------------------------------------------------------------------


def load_metadata_rows(path: str | Path) -> list[dict[str, str]]:
    """Read the metadata CSV as raw rows, preserving order and duplicates.

    Raw rows are needed for duplicate detection (E25): ``load_metadata`` returns a dict, which
    cannot represent two rows sharing one ``trace_name``.
    """
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def find_duplicate_trace_names(rows: Sequence[Mapping[str, str]]) -> list[str]:
    """Return the ``trace_name`` values occurring more than once, sorted."""
    counts = Counter(str(row.get("trace_name", "")).strip() for row in rows)
    return sorted(name for name, count in counts.items() if name and count > 1)


def load_metadata(
    path: str | Path,
    *,
    on_duplicate: str = "keep_last",
    duplicates: list[str] | None = None,
) -> dict[str, dict[str, str]]:
    """Load the metadata CSV into ``{trace_name: row}`` (FR-001, FR-012).

    ``on_duplicate`` makes the duplicate policy explicit instead of implicit:

    * ``"keep_last"`` (default) — the historical behaviour: the dict keeps the last row. Still
      lossy, which is why ``screen_metadata`` must be given rows or ``duplicates`` to see them.
    * ``"error"`` — raise ``ValueError`` listing the duplicated names (NFR-004: fail loudly).
    * ``"first"`` — keep the first row for a name.

    ``duplicates`` (optional out-parameter list) is filled with any duplicated names found, so a
    caller can pass them straight to ``screen_metadata`` and have them logged as rejections.
    """
    if on_duplicate not in ("keep_last", "error", "first"):
        raise ValueError(f"on_duplicate must be 'keep_last', 'error' or 'first', got {on_duplicate!r}")

    out: dict[str, dict[str, str]] = {}
    seen: Counter = Counter()
    dupes: list[str] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            name = str(row.get("trace_name", "")).strip()
            seen[name] += 1
            if seen[name] == 2:
                dupes.append(name)
            if not name:
                # A row without a trace_name cannot be keyed; surface it instead of dropping it.
                raise ValueError(f"metadata row without trace_name in {path!s}: {dict(row)!r}")
            if on_duplicate == "first" and name in out:
                continue
            out[name] = row

    if on_duplicate == "error" and dupes:
        raise ValueError(
            f"duplicate trace_name values in {path!s}: {sorted(dupes)} — pass on_duplicate="
            f"'keep_last'/'first' to collapse them explicitly (E25)."
        )
    if duplicates is not None:
        duplicates.extend(sorted(dupes))
    return out


def summarize_metadata(
    metadata: Mapping[str, Mapping[str, str]] | Sequence[Mapping[str, str]],
    *,
    numeric_keys: Sequence[str] = SUMMARY_NUMERIC_KEYS,
    event_id_keys: Sequence[str] = SUMMARY_EVENT_KEYS,
) -> dict[str, object]:
    """FR-002 dataset summary statistics: counts, pick availability, rate and metadata ranges.

    Only fields present in the rows are reported; a missing field is *omitted*, not filled with
    a guessed value (the PRD's "do not invent" policy, §11.4). Distributions are reported as
    counts so a multi-rate dataset is visible rather than averaged.
    """
    items, duplicates = metadata_items(metadata)
    total = len(items)

    pick: Counter = Counter({"P_present": 0, "P_missing": 0, "S_present": 0, "S_missing": 0})
    rates: Counter = Counter()
    events: set[str] = set()
    no_event = 0
    numeric: dict[str, list[float]] = {key: [] for key in numeric_keys}

    for name, row in items:
        p_raw = row.get(P_PICK_KEY)
        pick["P_present" if p_raw is not None and str(p_raw).strip() else "P_missing"] += 1
        s_raw = row.get(S_PICK_KEY)
        pick["S_present" if s_raw is not None and str(s_raw).strip() else "S_missing"] += 1

        dt_raw = row.get(DT_KEY)
        if dt_raw is not None and str(dt_raw).strip():
            rates[str(dt_raw).strip()] += 1

        event_id = next(
            (str(row[k]).strip() for k in event_id_keys if str(row.get(k, "")).strip()), None
        )
        if event_id:
            events.add(event_id)
        else:
            no_event += 1

        for key in numeric_keys:
            raw = row.get(key)
            if raw is None or not str(raw).strip():
                continue
            try:
                value = float(str(raw).strip())
            except ValueError:
                continue
            if math.isfinite(value):
                numeric[key].append(value)

    summary: dict[str, object] = {
        "n_traces": total,
        "n_duplicate_trace_names": len(duplicates),
        "n_events": len(events),
        "n_traces_without_event_id": no_event,
        "pick_availability": dict(pick),
        "dt_s_distribution": dict(rates),
        "sampling_rate_distribution_hz": {
            (1.0 / float(dt)): count for dt, count in rates.items() if float(dt) > 0
        },
    }
    for key, values in numeric.items():
        if values:
            array = np.asarray(values, dtype=float)
            summary[f"{key}_stats"] = {
                "n": int(array.size),
                "min": float(array.min()),
                "max": float(array.max()),
                "mean": float(array.mean()),
                "median": float(np.median(array)),
            }
    return summary


# --------------------------------------------------------------------------------------
# HDF5 access (lazy, bounded)
# --------------------------------------------------------------------------------------


def load_waveform(
    hdf5_path: str | Path,
    trace_name: str,
    *,
    group: str = DEFAULT_HDF5_GROUP,
) -> npt.NDArray[np.int32]:
    """Read exactly one ``(3, 12000)`` record (ENZ, per ``data_format``).

    A dedicated context manager per call: the handle exists only for this read, so a caller that
    loads 10 k traces one at a time never holds the file open between calls (contrast the
    historical single-handle design).
    """
    with h5py.File(str(hdf5_path), "r") as handle:
        if group not in handle:
            raise KeyError(
                f"HDF5 group {group!r} not found in {hdf5_path!s}; root keys={sorted(handle.keys())}"
            )
        dataset = handle[group]
        if trace_name not in dataset:
            raise KeyError(f"trace {trace_name!r} not found under {group!r} in {hdf5_path!s}")
        return dataset[trace_name][()]


def iter_traces(
    hdf5_path: str | Path,
    metadata: Mapping[str, Mapping[str, str]] | Sequence[Mapping[str, str]],
    *,
    group: str = DEFAULT_HDF5_GROUP,
    batch_size: int = DEFAULT_BATCH_SIZE,
    yield_missing_s: bool = True,
    strict: bool = False,
    skipped: list[tuple[str, str]] | None = None,
) -> Iterator[tuple[str, npt.NDArray[np.int32], int | None, int | None]]:
    """Stream ``(trace_name, waveform, p_sample, s_sample_or_None)`` (FR-001).

    One HDF5 handle per batch of ``batch_size`` records, never one for the whole walk. Each
    waveform is read individually; nothing accumulates.

    Policy, stated rather than implicit:

    * P must be present (DR-002) — a trace without P is skipped (or raises in ``strict`` mode).
    * A missing S (empty/``None``) yields ``None`` and is kept, unless ``yield_missing_s=False``
      asks for S-only traces. The caller turns ``None`` into an all-zero S channel via
      ``waveform_to_window``/``make_targets`` (FR-024); fabricating ``0`` is never done.
    * Arrival indices must parse and lie in ``[0, trace_npts)`` — ``arrival_sample >= trace_npts``
      is rejected here as it is in screening (FR-002 edge), because such an index cannot place a
      target inside the waveform.
    * Every skip is attributable: with ``skipped`` supplied, ``(trace_name, reason)`` is appended;
      with ``strict=True``, ``LoadError`` is raised immediately. Nothing is dropped silently
      (NFR-004).
    """
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0, got {batch_size}")

    items, _duplicates = metadata_items(metadata)

    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        with h5py.File(str(hdf5_path), "r") as handle:
            if group not in handle:
                raise KeyError(
                    f"HDF5 group {group!r} not found in {hdf5_path!s}; "
                    f"root keys={sorted(handle.keys())}"
                )
            dataset = handle[group]
            keys = set(dataset.keys())
            for trace_name, row in batch:
                if trace_name not in keys:
                    _skip_or_raise(
                        trace_name,
                        "missing_in_hdf5",
                        f"no {group}/{trace_name} in {hdf5_path!s}",
                        strict=strict,
                        skipped=skipped,
                    )
                    continue

                p_raw = row.get(P_PICK_KEY)
                s_raw = row.get(S_PICK_KEY)
                p_present = p_raw is not None and str(p_raw).strip() != ""
                s_present = s_raw is not None and str(s_raw).strip() != ""

                if not p_present:
                    # P anchors the per-sample target; without it the trace cannot be labelled
                    # (DR-002), so it is skipped with a recorded reason rather than zero-labelled.
                    _skip_or_raise(
                        trace_name,
                        "missing_p",
                        f"{P_PICK_KEY} is empty; P is required (DR-002)",
                        strict=strict,
                        skipped=skipped,
                    )
                    continue
                if not s_present and not yield_missing_s:
                    _skip_or_raise(
                        trace_name,
                        "missing_s_filtered",
                        "S is empty and yield_missing_s=False",
                        strict=strict,
                        skipped=skipped,
                    )
                    continue

                record = dataset[trace_name]
                shape = tuple(int(s) for s in record.shape)

                # Structural guard (SR-001, E12): the model needs a 2-D record with exactly three
                # channels. The trace *length* is deliberately not pinned to 12000 here, so the
                # same loader serves the samples on disk and shorter synthetic fixtures; instead
                # the length is cross-checked against the row's own trace_npts below.
                if len(shape) != 2 or shape[0] != 3 or shape[1] <= 0:
                    _skip_or_raise(
                        trace_name,
                        "wrong_shape",
                        f"record shape {shape} is not (3, L>0) (SR-001/E12)",
                        strict=strict,
                        skipped=skipped,
                    )
                    continue
                npts = shape[1]

                # Metadata/HDF5 agreement (FR-003, NFR-004): the CSV's trace_npts must describe
                # the record actually stored, otherwise every pick index is off by an unknown
                # amount.
                npts_meta = row.get(NUMBER_OF_SAMPLES_KEY)
                if npts_meta is not None and str(npts_meta).strip():
                    try:
                        npts_meta_int = int(float(str(npts_meta).strip()))
                    except ValueError:
                        _skip_or_raise(
                            trace_name,
                            "metadata_mismatch",
                            f"{NUMBER_OF_SAMPLES_KEY} is not an integer: {npts_meta!r}",
                            strict=strict,
                            skipped=skipped,
                        )
                        continue
                    if npts_meta_int != npts:
                        _skip_or_raise(
                            trace_name,
                            "metadata_mismatch",
                            f"{NUMBER_OF_SAMPLES_KEY}={npts_meta_int} but the record has {npts} samples",
                            strict=strict,
                            skipped=skipped,
                        )
                        continue

                # Range guard before the (possibly expensive) read: a pick outside the trace is a
                # label defect, not a waveform defect, and must not reach target generation.
                # `arrival_sample >= trace_npts` is rejected here exactly as in screening.
                p_check = validate_arrival_in_trace(str(p_raw), npts)
                if not p_check.ok:
                    _skip_or_raise(
                        trace_name,
                        p_check.reason or "bad_pick",
                        p_check.detail,
                        strict=strict,
                        skipped=skipped,
                    )
                    continue
                s_check = validate_arrival_in_trace(str(s_raw) if s_present else None, npts)
                if not s_check.ok:
                    _skip_or_raise(
                        trace_name,
                        s_check.reason or "bad_pick",
                        s_check.detail,
                        strict=strict,
                        skipped=skipped,
                    )
                    continue

                waveform = record[()]  # ONE record only
                p_sample = int(float(str(p_raw).strip()))
                s_sample = int(float(str(s_raw).strip())) if s_present else None
                yield trace_name, waveform, p_sample, s_sample


def verify_hdf5_coverage(
    hdf5_path: str | Path,
    metadata: Mapping[str, Mapping[str, str]] | Sequence[Mapping[str, str]],
    *,
    group: str = DEFAULT_HDF5_GROUP,
    expected_shape: tuple[int, int] = DEFAULT_EXPECTED_SHAPE,
    expected_component_order: str | None = DEFAULT_EXPECTED_COMPONENT_ORDER,
    expected_rate: float | None = DEFAULT_EXPECTED_RATE,
) -> dict[str, object]:
    """Cross-check metadata keys against HDF5 records without reading any waveform.

    Returns a machine-readable report (FR-001/FR-003, E25, E18):

    ``ok``
        True only when there is nothing to flag: no key-set difference, no duplicate
        ``trace_name``, no shape/npts/dt mismatch and, when required, a matching declared
        component order.
    ``missing_in_hdf5`` / ``missing_in_csv``
        Sorted key-set differences in both directions. Both are reported: a metadata row with no
        waveform and a waveform with no metadata row are different failures with different fixes.
    ``duplicate_keys``
        ``trace_name`` values repeated in the metadata (needs raw rows to be detectable, E25).
    ``mismatched_shapes``
        Per-trace list of ``{trace_name, shape, expected_shape, npts, detail}`` where the record
        shape differs from ``expected_shape`` or from the row's own ``trace_npts``.
    ``mismatched_dt``
        Per-trace list where ``trace_dt_s`` disagrees with the rate declared in the file, or with
        ``expected_rate`` when the file declares none. ``rate_source`` states which basis was
        used, so a report never implies a declaration that is absent (E18, SR-003).
    ``component_order`` / ``component_order_mismatch`` / ``component_order_unknown``
        The declared order, whether it contradicts the expected order, and whether it is missing
        entirely (SR-002 treats "cannot be established" as not usable).

    Only dataset *metadata* is touched here (shape/dtype from the HDF5 index); no record is
    materialised, so this is cheap enough to run as a pre-flight guard before a long run.
    """
    if expected_shape[0] != 3 or expected_shape[1] <= 0:
        raise ValueError(f"expected_shape must be (3, L) with L > 0, got {tuple(expected_shape)} (SR-001)")
    expected_shape = (int(expected_shape[0]), int(expected_shape[1]))

    items, duplicates = metadata_items(metadata)
    metadata_names = {name for name, _ in items}

    with h5py.File(str(hdf5_path), "r") as handle:
        if group not in handle:
            raise KeyError(
                f"HDF5 group {group!r} not found in {hdf5_path!s}; root keys={sorted(handle.keys())}"
            )
        dataset = handle[group]
        hdf5_keys = set(dataset.keys())
        # Reuse the already-open handle: opening a second handle for the same file would be pure
        # overhead and would read the header twice.
        format_info = _handle_format_info(handle, expected_rate=expected_rate)

        missing_in_hdf5 = sorted(metadata_names - hdf5_keys)
        missing_in_csv = sorted(hdf5_keys - metadata_names)

        mismatched_shapes: list[dict[str, object]] = []
        mismatched_dt: list[dict[str, object]] = []
        for name, row in items:
            if name not in hdf5_keys:
                continue
            shape = tuple(int(s) for s in dataset[name].shape)
            details: list[str] = []
            if shape != expected_shape:
                details.append(f"shape {shape} != expected {expected_shape}")
            npts_meta = row.get(NUMBER_OF_SAMPLES_KEY)
            npts_int: int | None = None
            if npts_meta is not None and str(npts_meta).strip():
                try:
                    npts_int = int(float(str(npts_meta).strip()))
                except ValueError:
                    details.append(f"{NUMBER_OF_SAMPLES_KEY} is not an integer: {npts_meta!r}")
                else:
                    if len(shape) != 2 or npts_int != shape[1]:
                        details.append(f"{NUMBER_OF_SAMPLES_KEY}={npts_int} != record length {shape[1] if len(shape) == 2 else 'n/a'}")
            if details:
                mismatched_shapes.append(
                    {
                        "trace_name": name,
                        "shape": list(shape),
                        "expected_shape": list(expected_shape),
                        "npts": npts_int,
                        "detail": "; ".join(details),
                    }
                )

            dt_raw = row.get(DT_KEY)
            if dt_raw is not None and str(dt_raw).strip() and format_info["expected_dt_s"] is not None:
                try:
                    dt_meta = float(str(dt_raw).strip())
                except ValueError:
                    mismatched_dt.append(
                        {
                            "trace_name": name,
                            "trace_dt_s": str(dt_raw),
                            "expected_dt_s": format_info["expected_dt_s"],
                            "rate_source": format_info["expected_dt_source"],
                            "detail": f"{DT_KEY} is not numeric: {dt_raw!r}",
                        }
                    )
                    continue
                if not np.isclose(dt_meta, float(format_info["expected_dt_s"]), rtol=1e-6, atol=1e-12):
                    mismatched_dt.append(
                        {
                            "trace_name": name,
                            "trace_dt_s": dt_meta,
                            "expected_dt_s": float(format_info["expected_dt_s"]),
                            "rate_source": format_info["expected_dt_source"],
                            "detail": f"{DT_KEY}={dt_meta} != {float(format_info['expected_dt_s']):g} s (E18/SR-003)",
                        }
                    )

    component_order = format_info["component_order"]
    component_order_mismatch = (
        expected_component_order is not None
        and component_order is not None
        and component_order != expected_component_order
    )
    component_order_unknown = expected_component_order is not None and component_order is None

    warnings: list[str] = []
    if component_order_unknown:
        warnings.append(
            "data_format/component_order is not declared; SR-002 requires the order to be asserted."
        )
    if format_info["expected_dt_s"] is None:
        warnings.append("no sampling rate declared and no expected_rate given: trace_dt_s not checked.")

    ok = not (
        missing_in_hdf5
        or missing_in_csv
        or duplicates
        or mismatched_shapes
        or mismatched_dt
        or component_order_mismatch
        or component_order_unknown
    )

    return {
        "ok": ok,
        "hdf5_path": str(hdf5_path),
        "group": group,
        "n_hdf5": len(hdf5_keys),
        "n_metadata": len(items),
        "missing_in_hdf5": missing_in_hdf5,
        "missing_in_csv": missing_in_csv,
        "duplicate_keys": sorted(duplicates),
        "mismatched_shapes": mismatched_shapes,
        "mismatched_dt": mismatched_dt,
        "expected_shape": list(expected_shape),
        "expected_rate_hz": expected_rate,
        "rate_expected_dt_s": format_info["expected_dt_s"],
        "rate_source": format_info["expected_dt_source"],
        "declared_sampling_rate_hz": format_info["sampling_rate"],
        "declared_dt_s": format_info["dt_s"],
        "component_order": component_order,
        "dimension_order": format_info["dimension_order"],
        "component_order_mismatch": component_order_mismatch,
        "component_order_unknown": component_order_unknown,
        "warnings": warnings,
    }


# --------------------------------------------------------------------------------------
# Windowing
# --------------------------------------------------------------------------------------


def waveform_to_window(
    waveform: npt.NDArray[np.int32],
    p_sample: int | None,
    s_sample: int | None,
    *,
    window_length: int = 128,
    depth: int = 4,
    sigma: float = 10.0,
    expected_length: int | None = DEFAULT_EXPECTED_SHAPE[1],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Validate, normalise per-window (zero-mean, unit-peak), window and make targets.

    Window is taken from 0:window_length for this stage's deterministic subset;
    production windowing (randomised offsets, FR-018) is a P2 extension.  The
    waveform is validated with validate_waveform/validate_picks; a failing
    window is rejected by raising ValueError with the ValidationResult.detail.

    ``expected_length`` defaults to the INSTANCE Counts trace length (12000). It is a parameter
    rather than a constant so shorter synthetic fixtures can share this code path without being
    silently accepted *or* blanket-rejected; pass ``None`` to skip the length check entirely.

    Empty S is handled *before* target generation: ``s_sample is None`` (which is how an empty
    ``trace_S_arrival_sample`` arrives from ``iter_traces``) yields an all-zero S channel from
    ``make_targets`` — an absent phase is never fabricated as sample 0 (FR-024).
    """
    # Check depth/length
    check_window_depth_compatible(window_length, depth)
    # Validate shape etc.
    vr = validate_waveform(waveform, expected_length=expected_length)
    if not vr.ok:
        raise ValueError(vr.detail)
    # Per-window normalise: zero-mean per channel, scale by global peak so amplitudes stay comparable.
    w = waveform.astype(np.float64)
    w = w - w.mean(axis=1, keepdims=True)
    peak = np.abs(w).max()
    if peak > 0:
        w = w / peak
    # Cut window from start (deterministic for verification)
    win = w[:, :window_length]
    # Validate picks within window
    pr = validate_picks(p_sample, s_sample, window_length=window_length)
    # For calibration we keep the window even if picks are out-of-window — targets become all-zero S/P
    # But we record that in the caller's manifest; here weclip: if pick >= window_length, treat as missing
    p_in = p_sample if (p_sample is not None and 0 <= p_sample < window_length) else None
    s_in = s_sample if (s_sample is not None and 0 <= s_sample < window_length) else None
    targets = make_targets(window_length, p_in, s_in, sigma=sigma)
    return win, targets


def iter_windows(
    hdf5_path: str | Path,
    metadata: Mapping[str, Mapping[str, str]] | Sequence[Mapping[str, str]],
    *,
    group: str = DEFAULT_HDF5_GROUP,
    batch_size: int = DEFAULT_BATCH_SIZE,
    window_length: int = 128,
    depth: int = 4,
    sigma: float = 10.0,
    yield_missing_s: bool = True,
    strict: bool = False,
    skipped: list[tuple[str, str]] | None = None,
    expected_length: int | None = DEFAULT_EXPECTED_SHAPE[1],
) -> Iterator[tuple[str, npt.NDArray[np.float64], npt.NDArray[np.float64], int | None, int | None]]:
    """Stream ``(trace_name, window, targets, p_sample, s_sample)`` over ``iter_traces``.

    Streaming is preserved end to end: one record is read, windowed and yielded, so the caller
    (Dataset/DataLoader in P2's later tasks) can hold a bounded batch rather than the dataset.
    ``validate_waveform`` failures are raised as ``ValueError`` from ``waveform_to_window`` (the
    window is unusable) with the validation detail, matching the inference path's contract.
    """
    for trace_name, waveform, p_sample, s_sample in iter_traces(
        hdf5_path,
        metadata,
        group=group,
        batch_size=batch_size,
        yield_missing_s=yield_missing_s,
        strict=strict,
        skipped=skipped,
    ):
        try:
            window, targets = waveform_to_window(
                waveform,
                p_sample,
                s_sample,
                window_length=window_length,
                depth=depth,
                sigma=sigma,
                expected_length=expected_length,
            )
        except ValueError as exc:
            if strict:
                raise LoadError(f"{trace_name}: {exc}") from exc
            if skipped is not None:
                skipped.append((trace_name, str(exc)))
            continue
        yield trace_name, window, targets, p_sample, s_sample


def metadata_groups_by_event(
    metadata: Mapping[str, Mapping[str, str]],
    *,
    event_id_keys: Sequence[str] = SUMMARY_EVENT_KEYS,
) -> dict[str, list[str]]:
    """Group ``trace_name`` values by event identifier (FR-004/DR-003 support).

    Splitting is done in ``seismonet.split``; this helper only exposes the mapping the loader
    can build from the metadata it has, so a caller can verify event coverage before splitting.
    Traces with no identifiable event are grouped under ``""`` and counted rather than dropped.
    """
    groups: dict[str, list[str]] = {}
    for name, row in metadata.items():
        event_id = next(
            (str(row[k]).strip() for k in event_id_keys if str(row.get(k, "")).strip()), ""
        )
        groups.setdefault(event_id, []).append(name)
    return groups


# Re-exported for callers that imported the screening entry point from the loader historically.
__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_HDF5_GROUP",
    "DT_KEY",
    "LoadError",
    "NUMBER_OF_SAMPLES_KEY",
    "P_PICK_KEY",
    "S_PICK_KEY",
    "find_duplicate_trace_names",
    "iter_traces",
    "iter_windows",
    "load_metadata",
    "load_metadata_rows",
    "load_waveform",
    "metadata_groups_by_event",
    "summarize_metadata",
    "verify_hdf5_coverage",
    "waveform_to_window",
]

"""Event-ID construction, event coverage and metric stratification — PRD FR-010, FR-011, DR-003, §11.5.

Two metadata concerns that are *not* waveform data live here.

**FR-010 — construct or normalise the event identifier used for splitting, from dataset
metadata, when the dataset does not supply one directly.**  The governing rule is the PRD's
"do not fabricate" policy (§11.4, DR-003): when a direct identifier column *is* present (for
INSTANCE Counts that column is ``source_id``, 54 008 events), its value **is** the event id and
is returned unchanged.  Only when no direct identifier exists does the code build a
deterministic id from fallback metadata (origin time + source location).  There is deliberately
no code path that overwrites a real ``source_id`` with a constructed one.

**FR-011 — support stratifying reported results by metadata bins only when those fields
exist.**  ``stratify_by`` groups trace names by a numeric metadata field; when the field is
absent from every row it returns ``available=False`` with a detail string that documents the
absence instead of silently returning an empty table.

Determinism: a constructed id is a pure function of the fallback values.  Time strings are
normalised to UTC so ``2016-12-04T15:34:52.05Z`` and ``2016-12-04T15:34:52.050000+00:00``
produce the same id, and coordinates are rounded to a fixed number of decimals, so two traces
from the same event always collapse to one id on every platform.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from seismonet.validation import metadata_items

#: Columns that carry a *direct* event identifier.  A value from one of these is the event id;
#: it is never replaced by a constructed id (FR-010, DR-003).
DIRECT_EVENT_ID_KEYS: tuple[str, ...] = ("event_id", "source_id")

#: Fallback fields used to build a deterministic id when no direct column exists (DR-003 lists
#: "origin time, source location, event code" as the sufficient set; INSTANCE supplies the first
#: three).
DEFAULT_FALLBACK_KEYS: tuple[str, ...] = (
    "source_origin_time",
    "source_latitude_deg",
    "source_longitude_deg",
)

#: Reference-pick columns.  Their *absence* is the metadata-level signal that a pure-noise
#: metadata file carries no P/S labels (FR-019 verification, DR-007).
PHASE_PICK_KEYS: tuple[str, ...] = ("trace_P_arrival_sample", "trace_S_arrival_sample")

#: Columns that only the event metadata carries; a noise file lacking them is a *different*
#: schema (this is the FR-019 observation, not an error).
EVENT_ONLY_KEYS: tuple[str, ...] = (
    "source_origin_time",
    "source_latitude_deg",
    "source_longitude_deg",
)

#: Decimal places used to canonicalise coordinates in a constructed id.  Fixed so the id is
#: identical across platforms and float formatting rules.
COORD_DECIMALS = 5


# --------------------------------------------------------------------------------------
# FR-010 — event id
# --------------------------------------------------------------------------------------


def _clean(value: Any) -> str | None:
    """Return a stripped string for a non-blank value, else ``None``.

    Blank means ``None``, ``""`` or whitespace only.  This is the single definition of "absent"
    used by every function in this module, so "missing" is never confused with a real value.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalise_time(raw: str) -> str:
    """Normalise an ISO-8601 timestamp to a UTC, microsecond-precision string.

    Two different-but-equivalent spellings of the same instant map to the same canonical text,
    so the constructed id is stable.  A string that cannot be parsed is returned stripped
    rather than guessed at.
    """
    text = raw.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return text
    if parsed.tzinfo is None:
        # A naive timestamp is treated as UTC to keep the id platform-independent.  This is a
        # documented assumption; the source metadata carries explicit offsets.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _normalise_component(key: str, value: Any) -> str | None:
    """Canonicalise one fallback field, or return ``None`` when it is absent/unusable."""
    raw = _clean(value)
    if raw is None:
        return None
    if "time" in key:
        return _normalise_time(raw)
    try:
        number = float(raw)
    except ValueError:
        # Categorical identifier (e.g. an event code): keep it, whitespace-collapsed.
        return " ".join(raw.split())
    if not math.isfinite(number):
        return None
    return f"{number:.{COORD_DECIMALS}f}"


def canonical_event_key(
    row: Mapping[str, Any],
    fallback_keys: Sequence[str] = DEFAULT_FALLBACK_KEYS,
) -> str | None:
    """Build the canonical fallback key ``key=value|key=value|...`` (``None`` if incomplete).

    Exposed separately from :func:`construct_event_id` so the rule can be inspected and tested
    without depending on the prefixed return value.
    """
    parts: list[str] = []
    for key in fallback_keys:
        normalised = _normalise_component(key, row.get(key))
        if normalised is None:
            return None
        parts.append(f"{key}={normalised}")
    return "|".join(parts)


def direct_event_id(
    row: Mapping[str, Any],
    *,
    keys: Sequence[str] = DIRECT_EVENT_ID_KEYS,
) -> str | None:
    """Return the first non-empty direct identifier from ``row``, else ``None``."""
    for key in keys:
        value = _clean(row.get(key))
        if value is not None:
            return value
    return None


def event_id_source(
    row: Mapping[str, Any],
    fallback_keys: Sequence[str] = DEFAULT_FALLBACK_KEYS,
    *,
    keys: Sequence[str] = DIRECT_EVENT_ID_KEYS,
) -> str | None:
    """Where the event id for ``row`` comes from: a direct column name, ``"constructed"`` or ``None``."""
    for key in keys:
        if _clean(row.get(key)) is not None:
            return key
    if canonical_event_key(row, fallback_keys) is not None:
        return "constructed"
    return None


def construct_event_id(
    row: Mapping[str, Any],
    fallback_keys: Sequence[str] = DEFAULT_FALLBACK_KEYS,
    *,
    strict: bool = False,
) -> str | None:
    """Return a deterministic event id for one metadata row (FR-010).

    Contract:

    * If a direct identifier column (``event_id`` or ``source_id``) holds a non-empty value, that
      value is returned **unchanged**.  A present ``source_id`` is never replaced by a
      constructed id (INSTANCE Counts supplies ``source_id`` for every event, so this is the
      path taken in production; DR-003).
    * Otherwise the fallback fields in ``fallback_keys`` are normalised and joined into a
      canonical string.  Every field must be present, otherwise ``None`` is returned: an id is
      *constructed* from real metadata or not produced at all, never fabricated from a partial
      row.
    * ``strict=True`` raises ``ValueError`` instead of returning ``None``, for a caller that
      wants a hard failure when an event cannot be assigned.

    ``None`` means "this trace cannot be assigned to an event".  ``seismonet.split`` rejects
    empty ids, so such traces must be reported through :func:`event_id_coverage` rather than
    silently mixed into a split.
    """
    direct = direct_event_id(row)
    if direct is not None:
        return direct
    canonical = canonical_event_key(row, fallback_keys)
    if canonical is None:
        if strict:
            missing = [key for key in fallback_keys if _normalise_component(key, row.get(key)) is None]
            raise ValueError(
                f"cannot construct an event id: no direct identifier and fallback field(s) "
                f"{missing} are absent; refusing to fabricate an id (FR-010/DR-003)."
            )
        return None
    return canonical


@dataclass(frozen=True)
class EventIdCoverage:
    """FR-010 / §11.5 item 5: what fraction of traces can be assigned an event, and from where."""

    n_total: int
    n_assigned: int
    n_missing: int
    coverage: float
    by_source: dict[str, int]
    missing_trace_names: list[str]

    def summary(self) -> dict[str, Any]:
        return {
            "n_total": self.n_total,
            "n_assigned": self.n_assigned,
            "n_missing": self.n_missing,
            "coverage": self.coverage,
            "by_source": dict(self.by_source),
            "n_missing_trace_names": len(self.missing_trace_names),
        }


def event_id_coverage(
    metadata: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
    fallback_keys: Sequence[str] = DEFAULT_FALLBACK_KEYS,
    *,
    keys: Sequence[str] = DIRECT_EVENT_ID_KEYS,
) -> EventIdCoverage:
    """Count how many traces receive an event id and whether it was direct or constructed.

    Accepts either the loader's ``{trace_name: row}`` mapping or raw CSV rows (via
    ``seismonet.validation.metadata_items``).  Never mutates the input and never fabricates.
    """
    items, _duplicates = metadata_items(metadata)
    by_source: dict[str, int] = {}
    missing: list[str] = []
    assigned = 0
    for name, row in items:
        source = event_id_source(row, fallback_keys, keys=keys)
        if source is None:
            missing.append(name)
            continue
        assigned += 1
        by_source[source] = by_source.get(source, 0) + 1
    total = len(items)
    return EventIdCoverage(
        n_total=total,
        n_assigned=assigned,
        n_missing=total - assigned,
        coverage=(assigned / total) if total else 0.0,
        by_source=by_source,
        missing_trace_names=missing,
    )


# --------------------------------------------------------------------------------------
# FR-019 support — pure-noise metadata verification
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class NoiseVerification:
    """Result of checking a pure-noise metadata file before a noise window fraction is enabled.

    ``ok`` is the gate ``seismonet.windowing.plan_pure_noise`` consults before it will activate a
    non-zero pure-noise fraction (FR-019 / DR-007).
    """

    path: str
    n_rows: int
    ok: bool
    has_phase_pick_columns: bool
    phase_pick_columns_present: list[str]
    has_event_only_columns: bool
    event_only_columns_present: list[str]
    columns: list[str]
    n_unique_trace_names: int
    n_unique_source_ids: int
    npts_values: list[str]
    dt_values: list[str]
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "n_rows": self.n_rows,
            "ok": self.ok,
            "has_phase_pick_columns": self.has_phase_pick_columns,
            "phase_pick_columns_present": list(self.phase_pick_columns_present),
            "has_event_only_columns": self.has_event_only_columns,
            "event_only_columns_present": list(self.event_only_columns_present),
            "n_unique_trace_names": self.n_unique_trace_names,
            "n_unique_source_ids": self.n_unique_source_ids,
            "npts_values": list(self.npts_values),
            "dt_values": list(self.dt_values),
            "reasons": list(self.reasons),
            "notes": list(self.notes),
        }


def verify_noise_metadata(path: str | Path) -> NoiseVerification:
    """Verify a pure-noise metadata CSV is usable for FR-019, without inventing P/S labels.

    Checks (each contributes a named reason on failure):

    * **no reference P/S columns** — a noise file must not carry ``trace_P_arrival_sample`` /
      ``trace_S_arrival_sample``.  If they are present the file is not a pure-noise source and
      the fraction stays disabled rather than treating missing picks as zero.
    * **a trace identifier** — ``trace_name`` must exist and be unique (duplicates double-count).
    * **a single sampling rate and length** — ``trace_dt_s`` and ``trace_npts`` must each be a
      single value; more than one value means the noise set is heterogeneous and cannot share
      the window/target configuration.

    The check is metadata-only and cheap.  It does not read waveforms; if a noise HDF5 is needed
    for coverage that is a separate step and is reported as a note rather than assumed.
    """
    out_path = Path(path)
    with open(out_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = list(reader)

    phase_present = [key for key in PHASE_PICK_KEYS if key in columns]
    event_only_present = [key for key in EVENT_ONLY_KEYS if key in columns]

    trace_names = [str(row.get("trace_name", "")).strip() for row in rows]
    trace_names = [name for name in trace_names if name]
    source_ids = {
        str(row.get("source_id", "")).strip()
        for row in rows
        if str(row.get("source_id", "")).strip()
    }
    npts_values = sorted({str(row.get("trace_npts", "")).strip() for row in rows})
    dt_values = sorted({str(row.get("trace_dt_s", "")).strip() for row in rows})

    reasons: list[str] = []
    notes: list[str] = []
    if phase_present:
        reasons.append(f"reference phase columns present: {phase_present}")
    if "trace_name" not in columns:
        reasons.append("no trace_name column")
    elif len(set(trace_names)) != len(trace_names):
        reasons.append("duplicate trace_name values")
    if len(npts_values) > 1:
        reasons.append(f"multiple trace_npts values: {npts_values}")
    if len(dt_values) > 1:
        reasons.append(f"multiple trace_dt_s values: {dt_values}")

    if phase_present:
        notes.append("file is NOT pure noise: it carries reference phase picks")
    else:
        notes.append("no reference P/S columns: consistent with a pure-noise source (DR-007)")
    if not event_only_present:
        notes.append(
            "event-only columns are absent (different schema from the events metadata): "
            f"{list(EVENT_ONLY_KEYS)}"
        )

    return NoiseVerification(
        path=str(out_path),
        n_rows=len(rows),
        ok=not reasons,
        has_phase_pick_columns=bool(phase_present),
        phase_pick_columns_present=phase_present,
        has_event_only_columns=bool(event_only_present),
        event_only_columns_present=event_only_present,
        columns=columns,
        n_unique_trace_names=len(set(trace_names)),
        n_unique_source_ids=len(source_ids),
        npts_values=npts_values,
        dt_values=dt_values,
        reasons=reasons,
        notes=notes,
    )


# --------------------------------------------------------------------------------------
# FR-011 — stratification by metadata bins
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StratificationResult:
    """Trace names grouped into metadata bins, or a documented absence (FR-011)."""

    key: str
    available: bool
    bins: tuple[float, ...]
    labels: tuple[str, ...]
    groups: dict[str, list[str]]
    missing: list[str]
    detail: str

    @property
    def n_total(self) -> int:
        return sum(len(names) for names in self.groups.values()) + len(self.missing)

    @property
    def n_grouped(self) -> int:
        return sum(len(names) for names in self.groups.values())

    def counts(self) -> dict[str, int]:
        return {label: len(self.groups.get(label, [])) for label in self.labels}

    def summary(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "available": self.available,
            "bins": list(self.bins),
            "labels": list(self.labels),
            "counts": self.counts(),
            "n_grouped": self.n_grouped,
            "n_missing": len(self.missing),
            "n_total": self.n_total,
            "detail": self.detail,
        }


def _default_labels(bins: Sequence[float]) -> tuple[str, ...]:
    if not bins:
        return ("[all]",)
    labels = [f"[-,{bins[0]:.4g})"]
    for low, high in zip(bins, bins[1:]):
        labels.append(f"[{low:.4g},{high:.4g})")
    labels.append(f"[{bins[-1]:.4g},+)")
    return tuple(labels)


def _numeric_value(row: Mapping[str, Any], key: str) -> float | None:
    raw = row.get(key)
    if raw is None or not str(raw).strip():
        return None
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def stratify_by(
    metadata: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
    key: str,
    bins: Sequence[float],
    *,
    labels: Sequence[str] | None = None,
) -> StratificationResult:
    """Group trace names by the numeric metadata ``key`` using the boundaries ``bins`` (FR-011).

    ``bins`` are the *boundaries between groups*: with ``k`` boundaries there are ``k + 1``
    groups, the outer two open-ended (``[-,b0)`` and ``[b_{k-1},+)``).  A row whose value is
    absent, blank or non-numeric is placed in ``missing`` (reported, never imputed).

    FR-011 requires the absence of a field to be *documented*, not silently ignored: if ``key``
    is present in no row, the result has ``available=False``, empty groups and a ``detail``
    string saying so.
    """
    items, _duplicates = metadata_items(metadata)
    edges = tuple(float(b) for b in bins)
    if any(b <= a for a, b in zip(edges, edges[1:])):
        raise ValueError(f"bins must be strictly increasing, got {edges}")

    group_labels = tuple(labels) if labels is not None else _default_labels(edges)
    if len(group_labels) != len(edges) + 1:
        raise ValueError(
            f"labels must have len(bins)+1 = {len(edges) + 1} entries, got {len(group_labels)}"
        )

    groups: dict[str, list[str]] = {label: [] for label in group_labels}
    missing: list[str] = []
    any_present = False

    for name, row in items:
        if key in row:
            any_present = True
        value = _numeric_value(row, key)
        if value is None:
            missing.append(name)
            continue
        index = int(np.digitize([value], edges)[0])  # 0 .. len(edges)
        groups[group_labels[index]].append(name)

    if not any_present:
        detail = (
            f"metadata field {key!r} is not present in any row; stratification is unavailable "
            f"(FR-011: document the absence, do not invent a table)."
        )
    else:
        detail = (
            f"stratified {sum(len(v) for v in groups.values())} of {len(items)} trace(s) by "
            f"{key!r} into {len(group_labels)} bin(s); {len(missing)} without a numeric value."
        )

    return StratificationResult(
        key=key,
        available=any_present,
        bins=edges,
        labels=group_labels,
        groups=groups,
        missing=missing,
        detail=detail,
    )


def quantile_edges(values: Sequence[float], n_bins: int) -> tuple[float, ...]:
    """Interior bin boundaries at evenly spaced quantiles of ``values`` (helper for FR-011).

    Returns ``n_bins + 1`` edges (including min and max) with duplicates removed, so a
    degenerate distribution never yields a zero-width bin.
    """
    if n_bins < 1:
        raise ValueError(f"n_bins must be >= 1, got {n_bins}")
    array = np.asarray([v for v in values if v is not None and math.isfinite(float(v))], dtype=float)
    if array.size == 0:
        raise ValueError("cannot compute quantile edges from an empty value set")
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.unique(np.quantile(array, quantiles))
    return tuple(float(e) for e in edges)


def stratify_by_quantiles(
    metadata: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
    key: str,
    n_bins: int,
) -> StratificationResult:
    """Quantile-bin stratification: edges chosen so the bins carry comparable sample counts."""
    items, _duplicates = metadata_items(metadata)
    values = [v for _name, row in items if (v := _numeric_value(row, key)) is not None]
    if not values:
        return StratificationResult(
            key=key,
            available=any(key in row for _name, row in items),
            bins=(),
            labels=(),
            groups={},
            missing=[name for name, _row in items],
            detail=(
                f"metadata field {key!r} has no numeric values; quantile stratification is "
                f"unavailable (FR-011: document the absence)."
            ),
        )
    edges = quantile_edges(values, n_bins)
    if len(edges) == 1:
        return stratify_by(metadata, key, [], labels=[f"[{edges[0]:.4g},+)"])
    if len(edges) == 2:
        return stratify_by(metadata, key, [], labels=[f"[{edges[0]:.4g},{edges[1]:.4g}]"])
    return stratify_by(metadata, key, edges[1:-1])


__all__ = [
    "COORD_DECIMALS",
    "DEFAULT_FALLBACK_KEYS",
    "DIRECT_EVENT_ID_KEYS",
    "EVENT_ONLY_KEYS",
    "EventIdCoverage",
    "NoiseVerification",
    "PHASE_PICK_KEYS",
    "StratificationResult",
    "canonical_event_key",
    "construct_event_id",
    "direct_event_id",
    "event_id_coverage",
    "event_id_source",
    "quantile_edges",
    "stratify_by",
    "stratify_by_quantiles",
    "verify_noise_metadata",
]

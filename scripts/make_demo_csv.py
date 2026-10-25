"""Generate a multi-trace CSV that the web demo can upload.

The frozen checkpoint and the demo trace metadata are tracked, but the raw INSTANCE waveforms are not
shipped, so this script synthesises demonstration windows from the recorded reference arrivals using
``SeismoInferenceEngine._analyze_demo_trace``. The output exercises the real CSV path end to end —
parsing, contract checks, normalisation, frozen inference, thresholding — but it is *not* a scientific
evaluation: the samples are generated, not recorded.

Usage:
    python scripts/make_demo_csv.py --traces 12 --out samples/demo_12traces_predict.csv
    python scripts/make_demo_csv.py --traces 12 --labeled --out samples/demo_12traces_labeled.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from backend.inference import SeismoInferenceEngine  # noqa: E402

WINDOW_LENGTH = 3072
MAX_TRACES_PER_FILE = 32  # 100,000-row upload limit / 3,072 samples


def select_traces(engine: SeismoInferenceEngine, count: int) -> list[dict]:
    """Prefer one trace per event, then fill from the largest events."""
    traces = engine.get_available_traces()
    if not traces:
        raise SystemExit("No demo traces available; the tracked demo predictions file is missing.")

    by_event: dict[str, list[dict]] = {}
    for trace in traces:
        by_event.setdefault(trace.get("event_id") or "unknown", []).append(trace)

    selected: list[dict] = [group[0] for _, group in sorted(by_event.items())]
    chosen = {trace["trace_id"] for trace in selected}
    for trace in sorted(traces, key=lambda t: -len(by_event[t.get("event_id") or "unknown"])):
        if len(selected) >= count:
            break
        if trace["trace_id"] not in chosen:
            selected.append(trace)
            chosen.add(trace["trace_id"])
    return selected[:count]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--traces", type=int, default=12, help=f"how many traces (max {MAX_TRACES_PER_FILE})")
    parser.add_argument("--out", type=Path, default=ROOT / "samples" / "demo_12traces_predict.csv")
    parser.add_argument("--labeled", action="store_true", help="include p_arrival_sample / s_arrival_sample columns")
    args = parser.parse_args()

    if not 1 <= args.traces <= MAX_TRACES_PER_FILE:
        raise SystemExit(f"--traces must be between 1 and {MAX_TRACES_PER_FILE} (upload row limit)")

    engine = SeismoInferenceEngine(ROOT)
    if engine.real_dataset_available:
        print("NOTE: the raw dataset is present, but this script still generates synthetic demo windows.")

    selected = select_traces(engine, args.traces)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    header = ["trace_id", "sample_index", "E", "N", "Z"]
    if args.labeled:
        header += ["p_arrival_sample", "s_arrival_sample"]

    rows_written = 0
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for trace in selected:
            analysis = engine._analyze_demo_trace(trace["trace_id"])  # synthesised demo window
            waveform = analysis["waveform"]  # [E, N, Z]
            if len(waveform[0]) != WINDOW_LENGTH:
                raise SystemExit(f"unexpected window length {len(waveform[0])}")
            p_ref = trace.get("p_ref") or ""
            s_ref = trace.get("s_ref") or ""
            for index in range(WINDOW_LENGTH):
                row = [trace["trace_id"], index,
                       f"{waveform[0][index]:.7f}", f"{waveform[1][index]:.7f}", f"{waveform[2][index]:.7f}"]
                if args.labeled:
                    row += [p_ref, s_ref]
                writer.writerow(row)
            rows_written += WINDOW_LENGTH

    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} kB)")
    print(f"  traces: {len(selected)}  rows: {rows_written:,}  columns: {len(header)}  labelled: {args.labeled}")
    print(f"  events covered: {len({t.get('event_id') for t in selected})}")
    print("  Upload with Trace ID -> trace_id on the mapping step.")
    print("  Demonstration data only: these samples are generated, not recorded field data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

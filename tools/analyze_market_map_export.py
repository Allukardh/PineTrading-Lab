#!/usr/bin/env python3
"""Analyze TradingView CSV exports produced by Market Map MM-0.

The script uses only Python's standard library. It is intentionally an
engineering validator, not a strategy backtester and not a profitability
calculator.

Examples:
    python tools/analyze_market_map_export.py BTCUSDT_15m.csv BTCUSDT_1h.csv
    python tools/analyze_market_map_export.py --json report.json BTCUSDT_4h.csv
    python tools/analyze_market_map_export.py --compare before_reload.csv after_reload.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


MODEL_NAMES = {
    0: "NONE",
    1: "FIB",
    2: "ADAPT",
    3: "LIVE/FIB",
    4: "LIVE/ADAPT",
}

AUDIT_NEEDLES = {
    "map_dir": ("mm audit • mapdir", "audit • mapdir"),
    "atr": ("mm audit • atr", "audit • atr"),
    "model": ("mm audit • modelo", "audit • modelo"),
    "samples": ("mm audit • amostras adaptativas", "amostras adaptativas"),
    "corr_top": ("mm audit • correção topo", "correcao topo"),
    "corr_bottom": ("mm audit • correção fundo", "correcao fundo"),
    "destination": ("mm audit • destino 1", "destino 1"),
    "invalidation": ("mm audit • invalidação", "invalidacao"),
    "confluence": ("mm audit • confluências", "confluencias"),
    "new_thesis": ("mm audit • nova tese evt", "nova tese evt"),
    "zone_touch": ("mm audit • toque zona evt", "toque zona evt"),
    "zone_to_dest": ("mm audit • zona→destino evt", "zona->destino evt", "zona destino evt"),
    "zone_to_inv": ("mm audit • zona→invalidação evt", "zona->invalidacao evt", "zona invalidacao evt"),
    "ambiguous": ("mm audit • ambíguo evt", "ambiguo evt"),
}

OHLC_NEEDLES = {
    "time": ("time", "datetime", "date"),
    "open": ("open", "abertura", "abr"),
    "high": ("high", "máxima", "maxima", "máx", "max"),
    "low": ("low", "mínima", "minima", "mín", "min"),
    "close": ("close", "fechamento", "fech", "fch"),
}


def _norm(value: str) -> str:
    value = value.replace("\ufeff", "").strip().lower()
    value = value.replace("→", "->")
    value = "".join(
        ch for ch in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(ch)
    )
    return " ".join(value.split())


def _num(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip().replace("\u2212", "-")
    if not text or text.lower() in {"na", "nan", "null", "none", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    if "," in text and "." not in text:
        try:
            return float(text.replace(",", "."))
        except ValueError:
            return None
    # Last-resort handling for conventional thousands separators.
    if "," in text and "." in text:
        try:
            return float(text.replace(",", ""))
        except ValueError:
            return None
    return None


def _flag(value: float | None) -> bool:
    return value is not None and abs(value) >= 0.5


def _intish(value: float | None) -> int | None:
    return None if value is None else int(round(value))


def _quantiles(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "p25": None, "median": None, "p75": None, "max": None}
    vals = sorted(values)

    def q(frac: float) -> float:
        if len(vals) == 1:
            return vals[0]
        pos = (len(vals) - 1) * frac
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            return vals[lo]
        return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)

    return {
        "min": vals[0],
        "p25": q(0.25),
        "median": q(0.50),
        "p75": q(0.75),
        "max": vals[-1],
    }


def _fmt_pct(n: int, d: int) -> str:
    return "n/a" if d <= 0 else f"{100.0 * n / d:.1f}%"


def _fmt_num(v: float | None, digits: int = 2) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


@dataclass
class LoadedCsv:
    path: Path
    header: list[str]
    rows: list[list[str]]
    columns: dict[str, int]


def _read_csv(path: Path) -> LoadedCsv:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as fh:
        reader = csv.reader(fh, dialect)
        rows = list(reader)

    if not rows:
        raise ValueError(f"{path}: empty CSV")

    header = rows[0]
    data = [row + [""] * (len(header) - len(row)) for row in rows[1:] if any(x.strip() for x in row)]

    norm_header = [_norm(h) for h in header]
    columns: dict[str, int] = {}

    def find(name: str, needles: Iterable[str]) -> None:
        n_norm = [_norm(n) for n in needles]
        # Exact normalized match first.
        for i, h in enumerate(norm_header):
            if h in n_norm:
                columns[name] = i
                return
        # Then suffix/substring, useful when TradingView prefixes script names.
        candidates: list[int] = []
        for i, h in enumerate(norm_header):
            if any(h.endswith(n) or n in h for n in n_norm):
                candidates.append(i)
        if candidates:
            columns[name] = candidates[0]

    for name, needles in OHLC_NEEDLES.items():
        find(name, needles)
    for name, needles in AUDIT_NEEDLES.items():
        find(name, needles)

    required = ["time", "close", *AUDIT_NEEDLES.keys()]
    missing = [name for name in required if name not in columns]
    if missing:
        available = "\n  - ".join(header)
        raise ValueError(
            f"{path}: missing required Market Map export columns: {', '.join(missing)}\n"
            f"Available columns:\n  - {available}"
        )

    return LoadedCsv(path=path, header=header, rows=data, columns=columns)


def _cell(data: LoadedCsv, row: list[str], key: str) -> str | None:
    idx = data.columns.get(key)
    return None if idx is None or idx >= len(row) else row[idx]


def _value(data: LoadedCsv, row: list[str], key: str) -> float | None:
    return _num(_cell(data, row, key))


def analyze(path: Path) -> dict:
    data = _read_csv(path)

    direction_counts: Counter[str] = Counter()
    model_touch_counts: Counter[str] = Counter()
    confluence_touch_counts: Counter[str] = Counter()
    outcomes_by_direction: dict[str, Counter[str]] = defaultdict(Counter)
    outcomes_by_model: dict[str, Counter[str]] = defaultdict(Counter)

    thesis_count = 0
    touch_count = 0
    dest_outcomes = 0
    inv_outcomes = 0
    ambiguous = 0
    superseded_after_touch = 0

    zone_width_atr: list[float] = []
    dest_distance_atr: list[float] = []
    invalidation_distance_atr: list[float] = []
    bars_to_outcome: list[int] = []

    pathology = Counter()

    active: dict | None = None
    start_time = _cell(data, data.rows[0], "time") if data.rows else None
    end_time = _cell(data, data.rows[-1], "time") if data.rows else None

    for idx, row in enumerate(data.rows):
        close = _value(data, row, "close")
        map_dir = _intish(_value(data, row, "map_dir")) or 0
        atr = _value(data, row, "atr")
        model_code = _intish(_value(data, row, "model")) or 0
        model_name = MODEL_NAMES.get(model_code, f"UNKNOWN({model_code})")
        corr_top = _value(data, row, "corr_top")
        corr_bottom = _value(data, row, "corr_bottom")
        destination = _value(data, row, "destination")
        invalidation = _value(data, row, "invalidation")
        confluence = _intish(_value(data, row, "confluence"))

        new_thesis = _flag(_value(data, row, "new_thesis"))
        zone_touch = _flag(_value(data, row, "zone_touch"))
        zone_to_dest = _flag(_value(data, row, "zone_to_dest"))
        zone_to_inv = _flag(_value(data, row, "zone_to_inv"))
        ambiguous_evt = _flag(_value(data, row, "ambiguous"))

        if corr_top is not None and corr_bottom is not None:
            if corr_top < corr_bottom:
                pathology["inverted_correction_zone"] += 1
            if atr and atr > 0:
                zone_width_atr.append((corr_top - corr_bottom) / atr)

        if destination is not None and close is not None:
            if map_dir == 1 and destination <= close:
                pathology["bull_destination_not_above_close"] += 1
            elif map_dir == -1 and destination >= close:
                pathology["bear_destination_not_below_close"] += 1
            if atr and atr > 0:
                dest_distance_atr.append(abs(destination - close) / atr)

        if invalidation is not None and close is not None and atr and atr > 0:
            signed = close - invalidation if map_dir == 1 else invalidation - close if map_dir == -1 else None
            if signed is not None:
                invalidation_distance_atr.append(signed / atr)

        if invalidation is not None and corr_bottom is not None and corr_top is not None:
            if map_dir == 1 and invalidation >= corr_bottom:
                pathology["bull_invalidation_inside_or_above_zone"] += 1
            elif map_dir == -1 and invalidation <= corr_top:
                pathology["bear_invalidation_inside_or_below_zone"] += 1

        if new_thesis:
            if active and active.get("touched") and not active.get("resolved"):
                superseded_after_touch += 1
            thesis_count += 1
            direction = "LONG" if map_dir == 1 else "SHORT" if map_dir == -1 else "NONE"
            direction_counts[direction] += 1
            active = {
                "direction": direction,
                "model": model_name,
                "touched": False,
                "resolved": False,
                "touch_index": None,
                "confluence": None,
            }

        # Be tolerant if an export starts after a thesis was already active.
        if active is None and (zone_touch or zone_to_dest or zone_to_inv or ambiguous_evt):
            direction = "LONG" if map_dir == 1 else "SHORT" if map_dir == -1 else "NONE"
            active = {
                "direction": direction,
                "model": model_name,
                "touched": False,
                "resolved": False,
                "touch_index": None,
                "confluence": None,
            }

        if zone_touch:
            touch_count += 1
            if active is not None:
                active["touched"] = True
                active["touch_index"] = idx
                active["model"] = model_name
                active["confluence"] = confluence
                model_touch_counts[model_name] += 1
                if confluence is not None:
                    confluence_touch_counts[str(confluence)] += 1

        def resolve(kind: str) -> None:
            nonlocal dest_outcomes, inv_outcomes, ambiguous
            if kind == "DEST":
                dest_outcomes += 1
            elif kind == "INV":
                inv_outcomes += 1
            else:
                ambiguous += 1
            if active is not None:
                direction = active.get("direction", "NONE")
                model = active.get("model", "NONE")
                outcomes_by_direction[direction][kind] += 1
                outcomes_by_model[model][kind] += 1
                touch_index = active.get("touch_index")
                if kind in {"DEST", "INV"} and touch_index is not None:
                    bars_to_outcome.append(idx - touch_index)
                active["resolved"] = True

        # Pine guarantees mutually exclusive resolved event flags. Keep a
        # defensive check here so malformed exports are visible.
        events = sum([zone_to_dest, zone_to_inv, ambiguous_evt])
        if events > 1:
            pathology["multiple_outcome_events_same_row"] += 1

        if ambiguous_evt:
            resolve("AMB")
        elif zone_to_dest:
            resolve("DEST")
        elif zone_to_inv:
            resolve("INV")

    open_at_end = 1 if active and active.get("touched") and not active.get("resolved") else 0
    resolved = dest_outcomes + inv_outcomes

    return {
        "file": str(path),
        "rows": len(data.rows),
        "start": start_time,
        "end": end_time,
        "counts": {
            "theses": thesis_count,
            "zone_touches": touch_count,
            "destination_outcomes": dest_outcomes,
            "invalidation_outcomes": inv_outcomes,
            "resolved_non_ambiguous": resolved,
            "ambiguous": ambiguous,
            "superseded_after_touch": superseded_after_touch,
            "open_at_export_end": open_at_end,
        },
        "rates": {
            "theses_with_zone_touch_pct": (100.0 * touch_count / thesis_count) if thesis_count else None,
            "zone_to_destination_pct_resolved": (100.0 * dest_outcomes / resolved) if resolved else None,
            "ambiguous_pct_of_touches": (100.0 * ambiguous / touch_count) if touch_count else None,
        },
        "direction_theses": dict(direction_counts),
        "touch_models": dict(model_touch_counts),
        "touch_confluence": dict(confluence_touch_counts),
        "outcomes_by_direction": {k: dict(v) for k, v in outcomes_by_direction.items()},
        "outcomes_by_model": {k: dict(v) for k, v in outcomes_by_model.items()},
        "distributions": {
            "zone_width_atr": _quantiles(zone_width_atr),
            "destination_distance_atr": _quantiles(dest_distance_atr),
            "invalidation_distance_atr": _quantiles(invalidation_distance_atr),
            "bars_touch_to_outcome": _quantiles([float(x) for x in bars_to_outcome]),
        },
        "pathologies": dict(pathology),
        "columns": {k: data.header[v] for k, v in data.columns.items()},
    }


def compare_reload(before: Path, after: Path) -> dict:
    a = _read_csv(before)
    b = _read_csv(after)

    compare_keys = [
        "map_dir", "model", "samples", "corr_top", "corr_bottom", "destination",
        "invalidation", "confluence", "new_thesis", "zone_touch",
        "zone_to_dest", "zone_to_inv", "ambiguous",
    ]

    def row_map(data: LoadedCsv) -> dict[str, list[str]]:
        return {_cell(data, row, "time") or f"row:{i}": row for i, row in enumerate(data.rows)}

    ma = row_map(a)
    mb = row_map(b)
    common = sorted(set(ma) & set(mb))
    if len(common) > 1:
        # Exclude the newest common bar by default because it may have been
        # unconfirmed during one of the exports.
        common = common[:-1]

    mismatches = Counter()
    examples: dict[str, list[dict]] = defaultdict(list)

    def same(x: float | None, y: float | None) -> bool:
        if x is None or y is None:
            return x is None and y is None
        tol = max(1e-9, 1e-8 * max(1.0, abs(x), abs(y)))
        return abs(x - y) <= tol

    for t in common:
        ra, rb = ma[t], mb[t]
        for key in compare_keys:
            va, vb = _value(a, ra, key), _value(b, rb, key)
            if not same(va, vb):
                mismatches[key] += 1
                if len(examples[key]) < 5:
                    examples[key].append({"time": t, "before": va, "after": vb})

    return {
        "before": str(before),
        "after": str(after),
        "common_confirmed_rows_compared": len(common),
        "mismatch_counts": dict(mismatches),
        "examples": dict(examples),
        "pass": not mismatches,
    }


def print_report(report: dict) -> None:
    counts = report["counts"]
    rates = report["rates"]
    print(f"\n=== {report['file']} ===")
    print(f"Rows: {report['rows']} | {report['start']} -> {report['end']}")
    print(
        "Theses: {theses} | zone touches: {zone_touches} ({touch}) | "
        "resolved: {resolved_non_ambiguous} | ambiguous: {ambiguous} | "
        "superseded/open: {superseded_after_touch}/{open_at_export_end}".format(
            **counts,
            touch=_fmt_num(rates["theses_with_zone_touch_pct"]),
        )
    )
    print(
        "Zone -> destination among resolved: "
        + ("n/a" if rates["zone_to_destination_pct_resolved"] is None
           else f"{rates['zone_to_destination_pct_resolved']:.1f}%")
    )
    print(f"Direction theses: {report['direction_theses']}")
    print(f"Touch models: {report['touch_models']}")
    print(f"Touch confluence: {report['touch_confluence']}")
    print(f"Outcomes by direction: {report['outcomes_by_direction']}")
    print(f"Outcomes by model: {report['outcomes_by_model']}")
    print("Distributions:")
    for name, stats in report["distributions"].items():
        print(f"  {name}: {stats}")
    if report["pathologies"]:
        print(f"PATHOLOGIES: {report['pathologies']}")
    else:
        print("Pathology checks: none detected")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="TradingView CSV export(s)")
    parser.add_argument("--json", type=Path, help="Write machine-readable report")
    parser.add_argument(
        "--compare", nargs=2, metavar=("BEFORE", "AFTER"), type=Path,
        help="Compare two exports for confirmed-history reload parity",
    )
    args = parser.parse_args()

    if args.compare:
        report = compare_reload(*args.compare)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if args.json:
            args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0 if report["pass"] else 2

    if not args.files:
        parser.error("provide at least one CSV file or use --compare")

    reports = []
    for path in args.files:
        try:
            report = analyze(path)
        except Exception as exc:  # concise CLI error, traceback is not useful to operator
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        reports.append(report)
        print_report(report)

    output = {"reports": reports}
    if args.json:
        args.json.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON report written to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

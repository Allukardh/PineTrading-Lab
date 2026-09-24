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
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


EXPECTED_AUDIT_SCHEMA = 2

MODEL_NAMES = {
    0: "NONE",
    1: "FIB",
    2: "ADAPT",
    3: "LIVE/FIB",
    4: "LIVE/ADAPT",
}

AUDIT_NEEDLES = {
    "schema": ("mm audit • schema", "audit • schema"),
    "confirmed": ("mm audit • confirmado", "audit • confirmado"),
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
    "reclaim": ("mm audit • sweep reclaim evt", "sweep reclaim evt"),
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


def _append_example(store: dict[str, list[dict]], key: str, example: dict, limit: int = 2) -> None:
    bucket = store.setdefault(key, [])
    if len(bucket) < limit:
        bucket.append(example)


def _speed_bucket(bars: int | None) -> str:
    if bars is None:
        return "UNKNOWN"
    if bars <= 3:
        return "LE3"
    if bars <= 10:
        return "4_10"
    return "GT10"


def _classify_same_touch_order(
    *,
    direction: str,
    reason: str,
    open_value: float | None,
    correction_top: float | None,
    correction_bottom: float | None,
    frozen_target: float | None,
    invalidation: float | None,
) -> str:
    """Classify what OHLC topology can and cannot prove on the touch bar."""

    if reason == "TARGET_AND_INVALIDATION":
        return "BOTH_TARGET_INVALIDATION"

    if open_value is None or correction_top is None or correction_bottom is None:
        return "UNKNOWN_GEOMETRY"

    if reason == "TARGET":
        if frozen_target is None:
            return "UNKNOWN_TARGET"

        if direction == "LONG":
            if correction_bottom <= frozen_target <= correction_top:
                return "TARGET_INSIDE_ZONE"
            if frozen_target < correction_bottom:
                return "TARGET_BEHIND_ZONE"
            if open_value <= correction_top:
                return "ZONE_FIRST_TARGET_INFERABLE"
            if open_value >= frozen_target:
                return "TARGET_FIRST_AT_OPEN"
            return "UNORDERED_TARGET"

        if direction == "SHORT":
            if correction_bottom <= frozen_target <= correction_top:
                return "TARGET_INSIDE_ZONE"
            if frozen_target > correction_top:
                return "TARGET_BEHIND_ZONE"
            if open_value >= correction_bottom:
                return "ZONE_FIRST_TARGET_INFERABLE"
            if open_value <= frozen_target:
                return "TARGET_FIRST_AT_OPEN"
            return "UNORDERED_TARGET"

    if reason == "INVALIDATION":
        if invalidation is None:
            return "UNKNOWN_INVALIDATION"

        if direction == "LONG":
            if invalidation >= correction_bottom:
                return "INVALIDATION_NOT_BEYOND_ZONE"
            if open_value >= correction_bottom:
                return "ZONE_FIRST_INVALIDATION_INFERABLE"
            if open_value <= invalidation:
                return "INVALIDATION_FIRST_AT_OPEN"
            return "UNORDERED_INVALIDATION"

        if direction == "SHORT":
            if invalidation <= correction_top:
                return "INVALIDATION_NOT_BEYOND_ZONE"
            if open_value <= correction_top:
                return "ZONE_FIRST_INVALIDATION_INFERABLE"
            if open_value >= invalidation:
                return "INVALIDATION_FIRST_AT_OPEN"
            return "UNORDERED_INVALIDATION"

    return "UNRESOLVED_FROM_VISIBLE_ROW"


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
    ambiguous_timing: Counter[str] = Counter()
    ambiguous_timing_by_model: dict[str, Counter[str]] = defaultdict(Counter)
    ambiguous_reasons: Counter[str] = Counter()
    same_touch_order: Counter[str] = Counter()
    same_touch_order_by_model: dict[str, Counter[str]] = defaultdict(Counter)
    supersession_transitions: Counter[str] = Counter()
    superseded_touch_models: Counter[str] = Counter()
    supersession_speed: Counter[str] = Counter()
    supersession_transition_speed: dict[str, Counter[str]] = defaultdict(Counter)
    ambiguity_examples: dict[str, list[dict]] = {}
    supersession_examples: dict[str, list[dict]] = {}

    thesis_count = 0
    touch_count = 0
    dest_outcomes = 0
    inv_outcomes = 0
    ambiguous = 0
    superseded_after_touch = 0
    zone_touch_with_reclaim = 0
    reclaim_counts: Counter[str] = Counter()

    zone_width_atr: list[float] = []
    dest_distance_atr: list[float] = []
    invalidation_distance_atr: list[float] = []
    bars_to_outcome: list[int] = []
    bars_touch_to_supersession: list[int] = []

    pathology = Counter()

    schema_values = {
        _intish(_value(data, row, "schema"))
        for row in data.rows
        if _value(data, row, "schema") is not None
    }
    if schema_values != {EXPECTED_AUDIT_SCHEMA}:
        raise ValueError(
            f"{path}: unsupported or mixed Market Map audit schema: {sorted(schema_values)}; "
            f"expected {EXPECTED_AUDIT_SCHEMA}"
        )

    active: dict | None = None
    start_time = _cell(data, data.rows[0], "time") if data.rows else None
    end_time = _cell(data, data.rows[-1], "time") if data.rows else None

    confirmed_rows = 0
    provisional_rows = 0
    prev_map_dir: int | None = None
    prev_destination: float | None = None

    for idx, row in enumerate(data.rows):
        confirmed = _flag(_value(data, row, "confirmed"))
        if confirmed:
            confirmed_rows += 1
        else:
            provisional_rows += 1

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
        time_value = _cell(data, row, "time")
        open_value = _value(data, row, "open")
        high_value = _value(data, row, "high")
        low_value = _value(data, row, "low")
        close_value = close
        samples = _intish(_value(data, row, "samples"))
        row_snapshot = {
            "index": idx,
            "time": time_value,
            "direction": "LONG" if map_dir == 1 else "SHORT" if map_dir == -1 else "NONE",
            "model": model_name,
            "samples": samples,
            "ohlc": {
                "open": open_value,
                "high": high_value,
                "low": low_value,
                "close": close_value,
            },
            "atr": atr,
            "correction_top": corr_top,
            "correction_bottom": corr_bottom,
            "destination": destination,
            "invalidation": invalidation,
            "confluence": confluence,
        }

        if confirmed:
            if map_dir not in {-1, 0, 1}:
                pathology["invalid_map_dir"] += 1
            if model_code not in MODEL_NAMES:
                pathology["unknown_model_code"] += 1
            if confluence is not None and not 0 <= confluence <= 6:
                pathology["invalid_confluence_count"] += 1
            if model_code in {2, 4} and _intish(_value(data, row, "samples")) is not None and _intish(_value(data, row, "samples")) < 5:
                pathology["adaptive_model_below_min_samples"] += 1
            if model_code in {1, 3} and (_intish(_value(data, row, "samples")) or 0) >= 5:
                pathology["fib_model_despite_adaptive_samples"] += 1
            if map_dir == 0 and (destination is not None or corr_top is not None or corr_bottom is not None):
                pathology["directionless_map_has_directional_geometry"] += 1

        new_thesis = _flag(_value(data, row, "new_thesis"))
        zone_touch = _flag(_value(data, row, "zone_touch"))
        zone_to_dest = _flag(_value(data, row, "zone_to_dest"))
        zone_to_inv = _flag(_value(data, row, "zone_to_inv"))
        ambiguous_evt = _flag(_value(data, row, "ambiguous"))
        reclaim_dir = _intish(_value(data, row, "reclaim")) or 0

        if confirmed:
            if reclaim_dir == 1:
                reclaim_counts["BULL_RECLAIM"] += 1
            elif reclaim_dir == -1:
                reclaim_counts["BEAR_RECLAIM"] += 1
            elif reclaim_dir != 0:
                pathology["invalid_reclaim_direction"] += 1
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
            direction = "LONG" if map_dir == 1 else "SHORT" if map_dir == -1 else "NONE"
            if active and active.get("touched") and not active.get("resolved"):
                superseded_after_touch += 1
                prior_direction = active.get("direction", "NONE")
                prior_model = active.get("model", "NONE")
                transition = f"{prior_direction}->{direction}"
                supersession_transitions[transition] += 1
                superseded_touch_models[prior_model] += 1
                touch_index = active.get("touch_index")
                bars_since_touch = idx - touch_index if touch_index is not None else None
                if bars_since_touch is not None:
                    bars_touch_to_supersession.append(bars_since_touch)
                speed_bucket = _speed_bucket(bars_since_touch)
                supersession_speed[speed_bucket] += 1
                supersession_transition_speed[transition][speed_bucket] += 1
                example_key = f"{transition}|{prior_model}|{speed_bucket}"
                _append_example(
                    supersession_examples,
                    example_key,
                    {
                        "transition": transition,
                        "prior_model": prior_model,
                        "bars_touch_to_supersession": bars_since_touch,
                        "prior_thesis_time": active.get("new_time"),
                        "touch": active.get("touch_snapshot"),
                        "prior_last": active.get("latest_snapshot"),
                        "new_thesis": row_snapshot,
                    },
                )
            thesis_count += 1
            direction_counts[direction] += 1
            active = {
                "direction": direction,
                "model": model_name,
                "touched": False,
                "resolved": False,
                "touch_index": None,
                "confluence": None,
                "new_time": time_value,
                "touch_snapshot": None,
                "frozen_target": None,
                "latest_snapshot": None,
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
                "new_time": None,
                "touch_snapshot": None,
                "frozen_target": None,
                "latest_snapshot": None,
            }

        if zone_touch:
            touch_count += 1
            if reclaim_dir != 0:
                zone_touch_with_reclaim += 1
            if active is not None:
                frozen_target = (
                    prev_destination
                    if prev_map_dir == map_dir and prev_destination is not None
                    else destination
                )
                touch_snapshot = dict(row_snapshot)
                touch_snapshot["frozen_target"] = frozen_target
                active["touched"] = True
                active["touch_index"] = idx
                active["model"] = model_name
                active["confluence"] = confluence
                active["touch_snapshot"] = touch_snapshot
                active["frozen_target"] = frozen_target
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
            ambiguity_class = "SAME_TOUCH" if zone_touch else "POST_TOUCH_BOTH_BOUNDS"
            ambiguous_timing[ambiguity_class] += 1
            ambiguity_model = active.get("model", model_name) if active is not None else model_name
            ambiguity_direction = active.get("direction", row_snapshot["direction"]) if active is not None else row_snapshot["direction"]
            ambiguous_timing_by_model[ambiguity_model][ambiguity_class] += 1
            frozen_target = active.get("frozen_target") if active is not None else None
            target_hit = bool(
                frozen_target is not None
                and (
                    (ambiguity_direction == "LONG" and high_value is not None and high_value >= frozen_target)
                    or (ambiguity_direction == "SHORT" and low_value is not None and low_value <= frozen_target)
                )
            )
            invalidation_hit = bool(
                invalidation is not None
                and close_value is not None
                and (
                    (ambiguity_direction == "LONG" and close_value < invalidation)
                    or (ambiguity_direction == "SHORT" and close_value > invalidation)
                )
            )
            reason = (
                "TARGET_AND_INVALIDATION"
                if target_hit and invalidation_hit
                else "TARGET"
                if target_hit
                else "INVALIDATION"
                if invalidation_hit
                else "UNRESOLVED_FROM_VISIBLE_ROW"
            )
            ambiguous_reasons[reason] += 1
            order_class = None
            if ambiguity_class == "SAME_TOUCH":
                touch_snapshot = active.get("touch_snapshot") if active is not None else None
                touch_open = (
                    touch_snapshot.get("ohlc", {}).get("open")
                    if touch_snapshot is not None
                    else open_value
                )
                touch_top = (
                    touch_snapshot.get("correction_top")
                    if touch_snapshot is not None
                    else corr_top
                )
                touch_bottom = (
                    touch_snapshot.get("correction_bottom")
                    if touch_snapshot is not None
                    else corr_bottom
                )
                touch_invalidation = (
                    touch_snapshot.get("invalidation")
                    if touch_snapshot is not None
                    else invalidation
                )
                order_class = _classify_same_touch_order(
                    direction=ambiguity_direction,
                    reason=reason,
                    open_value=touch_open,
                    correction_top=touch_top,
                    correction_bottom=touch_bottom,
                    frozen_target=frozen_target,
                    invalidation=touch_invalidation,
                )
                same_touch_order[order_class] += 1
                same_touch_order_by_model[ambiguity_model][order_class] += 1
            touch_index = active.get("touch_index") if active is not None else None
            example_key = f"{ambiguity_class}|{ambiguity_model}|{ambiguity_direction}"
            _append_example(
                ambiguity_examples,
                example_key,
                {
                    "class": ambiguity_class,
                    "model": ambiguity_model,
                    "direction": ambiguity_direction,
                    "reason_from_visible_row": reason,
                    "same_touch_order_class": order_class,
                    "bars_from_touch": idx - touch_index if touch_index is not None else None,
                    "touch": active.get("touch_snapshot") if active is not None else None,
                    "event": row_snapshot,
                    "frozen_target": frozen_target,
                },
            )
            resolve("AMB")
        elif zone_to_dest:
            resolve("DEST")
        elif zone_to_inv:
            resolve("INV")

        if active is not None:
            active["latest_snapshot"] = row_snapshot
        prev_map_dir = map_dir
        prev_destination = destination

    open_at_end = 1 if active and active.get("touched") and not active.get("resolved") else 0
    resolved = dest_outcomes + inv_outcomes
    accounted_touches = resolved + ambiguous + superseded_after_touch + open_at_end
    if accounted_touches != touch_count:
        pathology["outcome_accounting_mismatch"] += abs(accounted_touches - touch_count)

    return {
        "file": str(path),
        "rows": len(data.rows),
        "confirmed_rows": confirmed_rows,
        "provisional_rows": provisional_rows,
        "audit_schema": EXPECTED_AUDIT_SCHEMA,
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
            "zone_touch_with_reclaim": zone_touch_with_reclaim,
        },
        "rates": {
            "theses_with_zone_touch_pct": (100.0 * touch_count / thesis_count) if thesis_count else None,
            # Conditional engineering statistic only. This excludes ambiguous,
            # superseded/censored and still-open touched theses; never read it
            # as a trade win rate.
            "zone_to_destination_pct_resolved": (100.0 * dest_outcomes / resolved) if resolved else None,
            "resolved_non_ambiguous_pct_of_touches": (100.0 * resolved / touch_count) if touch_count else None,
            "destination_pct_of_touches": (100.0 * dest_outcomes / touch_count) if touch_count else None,
            "invalidation_pct_of_touches": (100.0 * inv_outcomes / touch_count) if touch_count else None,
            "ambiguous_pct_of_touches": (100.0 * ambiguous / touch_count) if touch_count else None,
            "superseded_pct_of_touches": (100.0 * superseded_after_touch / touch_count) if touch_count else None,
            "open_at_export_end_pct_of_touches": (100.0 * open_at_end / touch_count) if touch_count else None,
            "zone_touch_with_reclaim_pct": (100.0 * zone_touch_with_reclaim / touch_count) if touch_count else None,
        },
        "direction_theses": dict(direction_counts),
        "reclaim_events": dict(reclaim_counts),
        "touch_models": dict(model_touch_counts),
        "touch_confluence": dict(confluence_touch_counts),
        "outcomes_by_direction": {k: dict(v) for k, v in outcomes_by_direction.items()},
        "outcomes_by_model": {k: dict(v) for k, v in outcomes_by_model.items()},
        "ambiguous_timing": dict(ambiguous_timing),
        "ambiguous_timing_by_model": {k: dict(v) for k, v in ambiguous_timing_by_model.items()},
        "ambiguous_reasons": dict(ambiguous_reasons),
        "same_touch_order": dict(same_touch_order),
        "same_touch_order_by_model": {k: dict(v) for k, v in same_touch_order_by_model.items()},
        "supersession_transitions": dict(supersession_transitions),
        "superseded_touch_models": dict(superseded_touch_models),
        "supersession_speed": dict(supersession_speed),
        "supersession_transition_speed": {k: dict(v) for k, v in supersession_transition_speed.items()},
        "lifecycle_examples": {
            "ambiguity": ambiguity_examples,
            "supersession": supersession_examples,
        },
        "distributions": {
            "zone_width_atr": _quantiles(zone_width_atr),
            "destination_distance_atr": _quantiles(dest_distance_atr),
            "invalidation_distance_atr": _quantiles(invalidation_distance_atr),
            "bars_touch_to_outcome": _quantiles([float(x) for x in bars_to_outcome]),
            "bars_touch_to_supersession": _quantiles([float(x) for x in bars_touch_to_supersession]),
        },
        "pathologies": dict(pathology),
        "columns": {k: data.header[v] for k, v in data.columns.items()},
    }


def compare_reload(before: Path, after: Path) -> dict:
    a = _read_csv(before)
    b = _read_csv(after)

    compare_keys = [
        "schema", "map_dir", "model", "samples", "corr_top", "corr_bottom", "destination",
        "invalidation", "confluence", "new_thesis", "zone_touch",
        "zone_to_dest", "zone_to_inv", "ambiguous", "reclaim",
    ]

    def row_map(data: LoadedCsv) -> dict[str, list[str]]:
        return {_cell(data, row, "time") or f"row:{i}": row for i, row in enumerate(data.rows)}

    ma = row_map(a)
    mb = row_map(b)
    common = []
    for i, row in enumerate(a.rows):
        t = _cell(a, row, "time") or f"row:{i}"
        if t in mb and _flag(_value(a, row, "confirmed")) and _flag(_value(b, mb[t], "confirmed")):
            common.append(t)

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


def aggregate_reports(reports: Sequence[dict]) -> dict:
    totals = Counter()
    aggregate_pathologies = Counter()
    review_flags: list[str] = []

    direction = Counter()
    touch_models = Counter()
    reclaim_events = Counter()
    ambiguous_timing = Counter()
    ambiguous_reasons = Counter()
    same_touch_order = Counter()
    supersession_transitions = Counter()
    superseded_touch_models = Counter()
    supersession_speed = Counter()
    supersession_transition_speed: dict[str, Counter[str]] = defaultdict(Counter)
    resolved_dest = 0
    resolved_inv = 0

    for report in reports:
        totals.update(report["counts"])
        aggregate_pathologies.update(report["pathologies"])
        direction.update(report["direction_theses"])
        touch_models.update(report["touch_models"])
        reclaim_events.update(report["reclaim_events"])
        ambiguous_timing.update(report.get("ambiguous_timing", {}))
        ambiguous_reasons.update(report.get("ambiguous_reasons", {}))
        same_touch_order.update(report.get("same_touch_order", {}))
        supersession_transitions.update(report.get("supersession_transitions", {}))
        superseded_touch_models.update(report.get("superseded_touch_models", {}))
        supersession_speed.update(report.get("supersession_speed", {}))
        for transition, speeds in report.get("supersession_transition_speed", {}).items():
            supersession_transition_speed[transition].update(speeds)
        resolved_dest += report["counts"]["destination_outcomes"]
        resolved_inv += report["counts"]["invalidation_outcomes"]

        c = report["counts"]
        r = report["rates"]
        if c["resolved_non_ambiguous"] < 10:
            review_flags.append(f"{report['file']}: small resolved sample ({c['resolved_non_ambiguous']})")
        touch_pct = r["theses_with_zone_touch_pct"]
        if touch_pct is not None and (touch_pct < 5.0 or touch_pct > 95.0):
            review_flags.append(f"{report['file']}: extreme zone-touch rate ({touch_pct:.1f}%)")
        amb_pct = r["ambiguous_pct_of_touches"]
        if amb_pct is not None and amb_pct > 25.0:
            review_flags.append(f"{report['file']}: high OHLC ambiguity share ({amb_pct:.1f}%)")
        if c["zone_touches"] >= 20:
            adaptive_touches = (
                report["touch_models"].get("ADAPT", 0)
                + report["touch_models"].get("LIVE/ADAPT", 0)
            )
            if adaptive_touches == 0:
                review_flags.append(f"{report['file']}: no adaptive-zone touches despite {c['zone_touches']} touches")

        width_med = report["distributions"]["zone_width_atr"]["median"]
        if width_med is not None and width_med > 2.0:
            review_flags.append(f"{report['file']}: median correction-zone width is broad ({width_med:.2f} ATR)")

    resolved = resolved_dest + resolved_inv
    touches = totals["zone_touches"]
    accounted = (
        totals["resolved_non_ambiguous"]
        + totals["ambiguous"]
        + totals["superseded_after_touch"]
        + totals["open_at_export_end"]
    )
    return {
        "files": len(reports),
        "counts": dict(totals),
        "direction_theses": dict(direction),
        "touch_models": dict(touch_models),
        "reclaim_events": dict(reclaim_events),
        "ambiguous_timing": dict(ambiguous_timing),
        "ambiguous_reasons": dict(ambiguous_reasons),
        "same_touch_order": dict(same_touch_order),
        "supersession_transitions": dict(supersession_transitions),
        "superseded_touch_models": dict(superseded_touch_models),
        "supersession_speed": dict(supersession_speed),
        "supersession_transition_speed": {k: dict(v) for k, v in supersession_transition_speed.items()},
        # Conditional on the small subset that resolved non-ambiguously.
        "zone_to_destination_pct_resolved": (100.0 * resolved_dest / resolved) if resolved else None,
        "touch_outcome_accounting": {
            "resolved_non_ambiguous_pct": (100.0 * totals["resolved_non_ambiguous"] / touches) if touches else None,
            "destination_pct": (100.0 * totals["destination_outcomes"] / touches) if touches else None,
            "invalidation_pct": (100.0 * totals["invalidation_outcomes"] / touches) if touches else None,
            "ambiguous_pct": (100.0 * totals["ambiguous"] / touches) if touches else None,
            "superseded_pct": (100.0 * totals["superseded_after_touch"] / touches) if touches else None,
            "open_pct": (100.0 * totals["open_at_export_end"] / touches) if touches else None,
            "accounted_pct": (100.0 * accounted / touches) if touches else None,
        },
        "pathologies": dict(aggregate_pathologies),
        "hard_pass": not aggregate_pathologies,
        "review_flags": review_flags,
    }


def print_aggregate(aggregate: dict) -> None:
    print("\n=== AGGREGATE ===")
    print(f"Files: {aggregate['files']}")
    c = aggregate["counts"]
    print(
        f"Theses: {c.get('theses', 0)} | touches: {c.get('zone_touches', 0)} | "
        f"resolved: {c.get('resolved_non_ambiguous', 0)} | ambiguous: {c.get('ambiguous', 0)}"
    )
    pct = aggregate["zone_to_destination_pct_resolved"]
    print(
        "Zone -> destination among non-ambiguous resolved only: "
        + ("n/a" if pct is None else f"{pct:.1f}%")
    )
    a = aggregate["touch_outcome_accounting"]
    if a["accounted_pct"] is not None:
        print(
            "All-touch accounting: "
            f"destination={a['destination_pct']:.1f}% | "
            f"invalidation={a['invalidation_pct']:.1f}% | "
            f"ambiguous={a['ambiguous_pct']:.1f}% | "
            f"superseded/censored={a['superseded_pct']:.1f}% | "
            f"open={a['open_pct']:.1f}%"
        )
    print(f"Directions: {aggregate['direction_theses']}")
    print(f"Touch models: {aggregate['touch_models']}")
    print(f"Reclaim events: {aggregate['reclaim_events']}")
    print(f"Ambiguous timing: {aggregate.get('ambiguous_timing', {})}")
    print(f"Ambiguous reasons: {aggregate.get('ambiguous_reasons', {})}")
    print(f"Same-touch order classes: {aggregate.get('same_touch_order', {})}")
    print(f"Supersession transitions: {aggregate.get('supersession_transitions', {})}")
    print(f"Superseded touch models: {aggregate.get('superseded_touch_models', {})}")
    print(f"Supersession speed: {aggregate.get('supersession_speed', {})}")
    print(f"Supersession transition/speed: {aggregate.get('supersession_transition_speed', {})}")
    if aggregate["pathologies"]:
        print(f"HARD FAIL pathologies: {aggregate['pathologies']}")
    else:
        print("Hard structural checks: PASS")
    if aggregate["review_flags"]:
        print("Review flags:")
        for flag in aggregate["review_flags"]:
            print(f"  - {flag}")
    else:
        print("Review flags: none")


def print_report(report: dict) -> None:
    counts = report["counts"]
    rates = report["rates"]
    print(f"\n=== {report['file']} ===")
    print(
        f"Rows: {report['rows']} "
        f"(confirmed={report['confirmed_rows']}, provisional={report['provisional_rows']}) "
        f"| schema={report['audit_schema']} | {report['start']} -> {report['end']}"
    )
    print(
        "Theses: {theses} | zone touches: {zone_touches} ({touch}) | "
        "resolved: {resolved_non_ambiguous} | ambiguous: {ambiguous} | "
        "superseded/open: {superseded_after_touch}/{open_at_export_end}".format(
            **counts,
            touch=_fmt_num(rates["theses_with_zone_touch_pct"]),
        )
    )
    print(
        "Zone -> destination among non-ambiguous resolved only: "
        + ("n/a" if rates["zone_to_destination_pct_resolved"] is None
           else f"{rates['zone_to_destination_pct_resolved']:.1f}%")
    )
    if rates["destination_pct_of_touches"] is not None:
        print(
            "All-touch accounting: "
            f"destination={rates['destination_pct_of_touches']:.1f}% | "
            f"invalidation={rates['invalidation_pct_of_touches']:.1f}% | "
            f"ambiguous={rates['ambiguous_pct_of_touches']:.1f}% | "
            f"superseded/censored={rates['superseded_pct_of_touches']:.1f}% | "
            f"open={rates['open_at_export_end_pct_of_touches']:.1f}%"
        )
    print(f"Direction theses: {report['direction_theses']}")
    print(f"Reclaim events: {report['reclaim_events']}")
    print(f"Touch models: {report['touch_models']}")
    print(f"Touch confluence: {report['touch_confluence']}")
    print(f"Outcomes by direction: {report['outcomes_by_direction']}")
    print(f"Outcomes by model: {report['outcomes_by_model']}")
    print(f"Ambiguous timing: {report.get('ambiguous_timing', {})}")
    print(f"Ambiguous timing by model: {report.get('ambiguous_timing_by_model', {})}")
    print(f"Supersession transitions: {report.get('supersession_transitions', {})}")
    print(f"Superseded touch models: {report.get('superseded_touch_models', {})}")
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

    aggregate = aggregate_reports(reports)
    if len(reports) > 1:
        print_aggregate(aggregate)

    output = {"reports": reports, "aggregate": aggregate}
    if args.json:
        args.json.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON report written to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

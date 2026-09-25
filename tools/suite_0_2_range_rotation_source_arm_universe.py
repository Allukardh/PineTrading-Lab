#!/usr/bin/env python3
"""15-symbol 1D robustness for accepted EARLY_ANY1 RANGE_ROTATION readiness.

Uses the exact same structural detector, source ignition rule and +1 ACCEPTED
confirmation for every symbol. No per-symbol tuning.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, pct, sha256_file
from tools.range_rotation_readiness_reference import RangeReadinessVariant
from tools.suite_0_2_range_rotation_source_arm import analyze


SYMBOLS = (
    "BTCUSDT", "ETHUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT",
    "ADAUSDT", "XRPUSDT", "SOLUSDT", "UNIUSDT", "NEARUSDT",
    "AAVEUSDT", "HBARUSDT", "LINKUSDT", "SUIUSDT", "LTCUSDT",
)
VARIANT = RangeReadinessVariant.EARLY_ANY1.value


def _count_from_pct(value: float | None, total: int) -> int:
    if value is None or total <= 0:
        return 0
    return int(round(value * total / 100.0))


def _dist(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None}
    xs = sorted(values)
    n = len(xs)
    median = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0
    return {"count": n, "min": xs[0], "median": median, "max": xs[-1]}


def aggregate(per_symbol: dict[str, dict]) -> dict:
    rows = 0
    episodes = 0
    accepted = 0
    confirms = 0
    failed_confirms = 0
    symbols_with_episodes = 0
    symbols_with_accepted = 0
    symbols_with_confirms = 0
    directions = Counter()
    outcomes = Counter()
    before_mid = same_mid = after_mid = 0
    cancels = 0
    armed = 0
    prep = 0
    quick_armed = 0
    quick_prep = 0
    room_medians = []

    for symbol, item in per_symbol.items():
        rows += item["rows"]
        episodes += item["episodes"]
        accepted += item["accepted_next_bar"]
        if item["episodes"] > 0:
            symbols_with_episodes += 1
        if item["accepted_next_bar"] > 0:
            symbols_with_accepted += 1

        v = item["variants"][VARIANT]
        c = v["confirmed_count"]
        confirms += c
        if c > 0:
            symbols_with_confirms += 1
        failed_confirms += v["failed_before_mid_confirmed"]
        directions.update(v["confirm_direction_counts"])
        outcomes.update(v["structural_confirmed"]["outcome_counts"])

        before_mid += _count_from_pct(v["confirm_before_midpoint_pct"], c)
        same_mid += _count_from_pct(v["confirm_same_midpoint_pct"], c)
        after_mid += _count_from_pct(v["confirm_after_midpoint_pct"], c)

        ev = v["event_load"]["events"]
        cancels += ev.get("CANCELED", 0)
        armed += ev.get("ARMED_ENTERED", 0)
        prep += ev.get("PREPARING_ENTERED", 0)
        quick_armed += v["event_load"]["quick_armed_cancel_3"]
        quick_prep += v["event_load"]["quick_prep_cancel_3"]

        median_room = v["confirm_room_to_opposite_atr"]["median"]
        if median_room is not None:
            room_medians.append(float(median_room))

    midpoint_or_better = outcomes["MID_REACHED"] + outcomes["OPPOSITE_REACHED"]

    return {
        "rows": rows,
        "episodes": episodes,
        "accepted_next_bar": accepted,
        "accepted_next_bar_pct": pct(accepted, episodes),
        "confirms": confirms,
        "confirm_pct": pct(confirms, episodes),
        "symbols_with_episodes": symbols_with_episodes,
        "symbols_with_accepted": symbols_with_accepted,
        "symbols_with_confirms": symbols_with_confirms,
        "failed_before_mid_confirmed": failed_confirms,
        "confirmed_outcome_counts": dict(sorted(outcomes.items())),
        "confirmed_midpoint_or_better_pct": pct(midpoint_or_better, confirms),
        "confirmed_opposite_reached_pct": pct(outcomes["OPPOSITE_REACHED"], confirms),
        "confirmed_censored_pct": pct(outcomes["CENSORED"], confirms),
        "confirm_direction_counts": dict(sorted(directions.items())),
        "confirm_before_midpoint_count": before_mid,
        "confirm_before_midpoint_pct": pct(before_mid, confirms),
        "confirm_same_midpoint_count": same_mid,
        "confirm_same_midpoint_pct": pct(same_mid, confirms),
        "confirm_after_midpoint_count": after_mid,
        "confirm_after_midpoint_pct": pct(after_mid, confirms),
        "events": {
            "PREPARING_ENTERED": prep,
            "ARMED_ENTERED": armed,
            "CONFIRM": confirms,
            "CANCELED": cancels,
        },
        "events_per_1000": {
            "PREPARING_ENTERED": None if not rows else prep * 1000.0 / rows,
            "ARMED_ENTERED": None if not rows else armed * 1000.0 / rows,
            "CONFIRM": None if not rows else confirms * 1000.0 / rows,
            "CANCELED": None if not rows else cancels * 1000.0 / rows,
        },
        "quick_prep_cancel_3": quick_prep,
        "quick_armed_cancel_3": quick_armed,
        "per_symbol_confirm_room_median_atr": _dist(room_medians),
    }


def _fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown(report: dict) -> str:
    a = report["aggregate"]
    lines = [
        "# Suite 0.2 — 15-symbol 1D EARLY_ANY1 RANGE_ROTATION robustness",
        "",
        "Same structural detector and readiness rule for every symbol. No per-symbol retuning.",
        "",
        f"- symbols: **{len(report['symbols'])}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Aggregate",
        "",
        f"- EDGE_REJECTION episodes: **{a['episodes']}**",
        f"- symbols with episodes: **{a['symbols_with_episodes']} / 15**",
        f"- +1 structurally ACCEPTED: **{a['accepted_next_bar']} ({_fmt(a['accepted_next_bar_pct'])}%)**",
        f"- symbols with +1 ACCEPTED: **{a['symbols_with_accepted']} / 15**",
        f"- EARLY_ANY1 CONFIRMA: **{a['confirms']} ({_fmt(a['confirm_pct'])}% of episodes)**",
        f"- symbols with at least one CONFIRMA: **{a['symbols_with_confirms']} / 15**",
        f"- FAILED_BEFORE_MID confirmations: **{a['failed_before_mid_confirmed']}**",
        f"- confirmed midpoint-or-better: **{_fmt(a['confirmed_midpoint_or_better_pct'])}%**",
        f"- confirmed opposite edge: **{_fmt(a['confirmed_opposite_reached_pct'])}%**",
        f"- confirmed censored: **{_fmt(a['confirmed_censored_pct'])}%**",
        f"- confirmation timing before / same / after midpoint: **{a['confirm_before_midpoint_count']} / {a['confirm_same_midpoint_count']} / {a['confirm_after_midpoint_count']}**",
        f"- LONG / SHORT confirms: **{a['confirm_direction_counts'].get('LONG',0)} / {a['confirm_direction_counts'].get('SHORT',0)}**",
        f"- CONFIRMA / 1000 bars: **{_fmt(a['events_per_1000']['CONFIRM'])}**",
        f"- CANCEL / 1000 bars: **{_fmt(a['events_per_1000']['CANCELED'])}**",
        f"- median of per-symbol confirm-room medians: **{_fmt(a['per_symbol_confirm_room_median_atr']['median'])} ATR**",
        "",
        "## Per-symbol",
        "",
        "| symbol | episodes | accepted +1 | confirms | confirm % | failed confirms | midpoint+ confirmed % | opposite confirmed % | before/same/after mid | room ATR med | cancel/1000 | LONG | SHORT |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]

    for symbol in SYMBOLS:
        item = report["symbols"][symbol]
        v = item["variants"][VARIANT]
        c = v["confirmed_count"]
        before = _count_from_pct(v["confirm_before_midpoint_pct"], c)
        same = _count_from_pct(v["confirm_same_midpoint_pct"], c)
        after = _count_from_pct(v["confirm_after_midpoint_pct"], c)
        s = v["structural_confirmed"]
        lines.append(
            "| {symbol} | {episodes} | {accepted} | {confirms} | {cpct} | {failed} | {mid} | {opp} | {before}/{same}/{after} | {room} | {cancel} | {long} | {short} |".format(
                symbol=symbol,
                episodes=item["episodes"],
                accepted=item["accepted_next_bar"],
                confirms=c,
                cpct=_fmt(v["confirmed_pct"]),
                failed=v["failed_before_mid_confirmed"],
                mid=_fmt(s["midpoint_or_better_pct"]),
                opp=_fmt(s["opposite_reached_pct"]),
                before=before,
                same=same,
                after=after,
                room=_fmt(v["confirm_room_to_opposite_atr"]["median"]),
                cancel=_fmt(v["event_load"]["events_per_1000"].get("CANCELED")),
                long=v["confirm_direction_counts"].get("LONG", 0),
                short=v["confirm_direction_counts"].get("SHORT", 0),
            )
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- EARLY_ANY1 is unchanged from the BTC/ETH/AVAX 4H gate.",
        "- EDGE_REJECTION detector, range thresholds and +1 ACCEPTED lifecycle are unchanged.",
        "- No per-symbol tuning.",
        "- HTF RSI remains context, not a readiness veto.",
        "- MTE/RSE/PSE state definitions are unchanged.",
        "- Frozen Execution 0.1 and accepted breakout/reacceleration Opportunity v2 are unchanged.",
        "- Structural outcomes are not profitability or trade win-rate claims.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    ap.add_argument("--code-sha", default="unknown")
    ap.add_argument("--tick-size", type=float, default=0.01)
    args = ap.parse_args()

    per_symbol = {}
    meta = {}
    for symbol in SYMBOLS:
        datasets = {}
        meta[symbol] = {}
        for tf in ("1d", "1w"):
            p = args.data_root / "spot" / symbol / "consolidated" / f"{symbol}_{tf}.parquet"
            if not p.is_file():
                raise SystemExit(f"missing dataset: {p}")
            ds = load_dataset(p)
            datasets[tf] = ds
            meta[symbol][tf] = {"rows": len(ds["close"]), "sha256": sha256_file(p)}
        per_symbol[symbol] = analyze("1d", datasets, args.tick_size)

    report = {
        "metadata": {
            "code_sha": args.code_sha,
            "timeframe": "1d",
            "symbols": list(SYMBOLS),
            "dataset_meta": meta,
            "accepted_4h_range_readiness_head": "827798c9f09472d67ed4bd609fdb2bb9738ad329",
        },
        "symbols": per_symbol,
        "aggregate": aggregate(per_symbol),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md = markdown(report)
    args.output_md.write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

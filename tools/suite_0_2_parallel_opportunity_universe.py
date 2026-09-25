#!/usr/bin/env python3
"""15-symbol 1D robustness for Suite 0.2 parallel Opportunity Readiness.

Uses the exact same Opportunity composition v2 for every symbol.
No per-symbol tuning.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, pct, sha256_file
from tools.suite_0_2_parallel_opportunity_evidence import analyze_timeframe


SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "AVAXUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "ADAUSDT",
    "XRPUSDT",
    "SOLUSDT",
    "UNIUSDT",
    "NEARUSDT",
    "AAVEUSDT",
    "HBARUSDT",
    "LINKUSDT",
    "SUIUSDT",
    "LTCUSDT",
)

OPPORTUNITIES = (
    "BREAKOUT_CANDIDATE",
    "REACCELERATION",
    "REGIME_REVERSAL",
)


def _count_from_pct(value: float | None, total: int) -> int:
    if value is None or total <= 0:
        return 0
    return int(round(value * total / 100.0))


def _aggregate_opportunity(per_symbol: dict, kind: str) -> dict:
    episodes = 0
    baseline = 0
    opp_path = 0
    expanded = 0
    positive_symbols = 0
    zero_symbols = 0

    for item in per_symbol.values():
        row = item["by_opportunity"].get(kind)
        if row is None:
            continue
        n = int(row["episodes"])
        episodes += n
        baseline += _count_from_pct(row["baseline_covered_pct"], n)
        opp_path += _count_from_pct(row["opportunity_path_covered_pct"], n)
        expanded += _count_from_pct(row["expanded_covered_pct"], n)
        gain = _count_from_pct(row["opportunity_only_covered_pct"], n)
        if gain > 0:
            positive_symbols += 1
        else:
            zero_symbols += 1

    return {
        "episodes": episodes,
        "baseline_covered": baseline,
        "opportunity_path_covered": opp_path,
        "expanded_covered": expanded,
        "baseline_covered_pct": pct(baseline, episodes),
        "opportunity_path_covered_pct": pct(opp_path, episodes),
        "expanded_covered_pct": pct(expanded, episodes),
        "opportunity_only_gain_pct": pct(expanded - baseline, episodes),
        "symbols_with_positive_gain": positive_symbols,
        "symbols_with_zero_gain": zero_symbols,
    }


def _aggregate_breakout_outcome(per_symbol: dict, outcome: str) -> dict:
    episodes = 0
    baseline = 0
    opp = 0
    expanded = 0
    for item in per_symbol.values():
        row = item["breakout_outcome_coverage"][outcome]
        n = int(row["episodes"])
        episodes += n
        baseline += _count_from_pct(row["baseline_covered_pct"], n)
        opp += _count_from_pct(row["opportunity_path_covered_pct"], n)
        expanded += _count_from_pct(row["expanded_covered_pct"], n)
    return {
        "episodes": episodes,
        "baseline_covered": baseline,
        "opportunity_path_covered": opp,
        "expanded_covered": expanded,
        "baseline_covered_pct": pct(baseline, episodes),
        "opportunity_path_covered_pct": pct(opp, episodes),
        "expanded_covered_pct": pct(expanded, episodes),
    }


def _aggregate_path(per_symbol: dict) -> dict:
    rows = 0
    events = Counter()
    directions = Counter()
    quick_prep = 0
    quick_armed = 0
    for item in per_symbol.values():
        rows += int(item["rows"])
        events.update(item["opportunity_path"]["events"])
        directions.update(item["opportunity_path"].get("confirm_direction_counts", {}))
        quick_prep += int(item["opportunity_path"]["quick_prep_cancel_3"])
        quick_armed += int(item["opportunity_path"]["quick_armed_cancel_3"])

    confirms = events["CONFIRM"]
    return {
        "rows": rows,
        "events": dict(sorted(events.items())),
        "events_per_1000": {
            k: (None if not rows else v * 1000.0 / rows)
            for k, v in sorted(events.items())
        },
        "confirm_direction_counts": dict(sorted(directions.items())),
        "long_share_pct": pct(directions["LONG"], confirms),
        "short_share_pct": pct(directions["SHORT"], confirms),
        "quick_prep_cancel_3": quick_prep,
        "quick_armed_cancel_3": quick_armed,
    }


def markdown_report(report: dict) -> str:
    agg = report["aggregate"]
    lines = [
        "# Suite 0.2 — 15-symbol 1D Opportunity v2 robustness",
        "",
        "Same composition for every symbol. No per-symbol retuning.",
        "",
        f"- symbols: **{len(report['symbols'])}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Aggregate opportunity coverage",
        "",
        "| opportunity | episodes | 0.1 covered % | opp-path covered % | expanded covered % | opp-only gain % | symbols +gain | symbols zero |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for kind in OPPORTUNITIES:
        x = agg["by_opportunity"][kind]
        lines.append(
            "| {k} | {n} | {b:.2f} | {o:.2f} | {e:.2f} | {g:.2f} | {p} | {z} |".format(
                k=kind,
                n=x["episodes"],
                b=x["baseline_covered_pct"] or 0.0,
                o=x["opportunity_path_covered_pct"] or 0.0,
                e=x["expanded_covered_pct"] or 0.0,
                g=x["opportunity_only_gain_pct"] or 0.0,
                p=x["symbols_with_positive_gain"],
                z=x["symbols_with_zero_gain"],
            )
        )

    lines += [
        "",
        "## Breakout held/fakeout",
        "",
        "| outcome | episodes | 0.1 covered % | opp-path covered % | expanded covered % |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for outcome in ("BREAKOUT_HELD", "BREAKOUT_FAKEOUT"):
        x = agg["breakout_outcomes"][outcome]
        lines.append(
            "| {o} | {n} | {b:.2f} | {p:.2f} | {e:.2f} |".format(
                o=outcome,
                n=x["episodes"],
                b=x["baseline_covered_pct"] or 0.0,
                p=x["opportunity_path_covered_pct"] or 0.0,
                e=x["expanded_covered_pct"] or 0.0,
            )
        )

    path = agg["opportunity_path"]
    lines += [
        "",
        "## Opportunity path load",
        "",
        f"- rows: **{path['rows']}**",
        f"- PREPARANDO/1000: **{(path['events_per_1000'].get('PREPARING_ENTERED') or 0):.2f}**",
        f"- ARMADO/1000: **{(path['events_per_1000'].get('ARMED_ENTERED') or 0):.2f}**",
        f"- CONFIRMA/1000: **{(path['events_per_1000'].get('CONFIRM') or 0):.2f}**",
        f"- CANCEL/1000: **{(path['events_per_1000'].get('CANCELED') or 0):.2f}**",
        f"- LONG confirmations: **{path['confirm_direction_counts'].get('LONG', 0)}**",
        f"- SHORT confirmations: **{path['confirm_direction_counts'].get('SHORT', 0)}**",
        "",
        "## Per-symbol daily summary",
        "",
        "| symbol | breakout episodes | breakout opp-only gain % | reaccel episodes | reaccel opp-only gain % | opp CONFIRMA | cancel/1000 | LONG | SHORT |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for symbol in SYMBOLS:
        item = report["symbols"][symbol]
        b = item["by_opportunity"].get("BREAKOUT_CANDIDATE", {})
        r = item["by_opportunity"].get("REACCELERATION", {})
        path = item["opportunity_path"]
        rows = item["rows"]
        cancels = path["events"].get("CANCELED", 0)
        lines.append(
            "| {s} | {bn} | {bg:.2f} | {rn} | {rg:.2f} | {c} | {cx:.2f} | {l} | {sh} |".format(
                s=symbol,
                bn=b.get("episodes", 0),
                bg=b.get("opportunity_only_covered_pct") or 0.0,
                rn=r.get("episodes", 0),
                rg=r.get("opportunity_only_covered_pct") or 0.0,
                c=path["events"].get("CONFIRM", 0),
                cx=(0.0 if not rows else cancels * 1000.0 / rows),
                l=path.get("confirm_direction_counts", {}).get("LONG", 0),
                sh=path.get("confirm_direction_counts", {}).get("SHORT", 0),
            )
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Frozen 0.1 remains independent for every symbol.",
        "- Same v2 composition is used for all 15 symbols.",
        "- No per-symbol threshold/default/profile tuning.",
        "- Breakout held/fakeout is retrospective structural evidence, not a trade win rate.",
        "- Small per-symbol REACCELERATION samples are interpreted through aggregate robustness, not isolated percentages.",
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
    dataset_meta = {}

    for symbol in SYMBOLS:
        datasets = {}
        dataset_meta[symbol] = {}
        for tf in ("1d", "1w"):
            path = args.data_root / "spot" / symbol / "consolidated" / f"{symbol}_{tf}.parquet"
            if not path.is_file():
                raise SystemExit(f"missing dataset: {path}")
            datasets[tf] = load_dataset(path)
            dataset_meta[symbol][tf] = {
                "rows": len(datasets[tf]["close"]),
                "sha256": sha256_file(path),
            }
        per_symbol[symbol] = analyze_timeframe("1d", datasets, args.tick_size)

    report = {
        "metadata": {
            "code_sha": args.code_sha,
            "timeframe": "1d",
            "symbols": list(SYMBOLS),
            "dataset_meta": dataset_meta,
            "frozen_market_map_promotion": "0eeb0d37b256a950cfb38f627fa3521bb213d380",
            "frozen_execution_promotion": "a7557df2d0142441ea782dba4b8c3f95ebc38371",
        },
        "symbols": per_symbol,
        "aggregate": {
            "by_opportunity": {
                kind: _aggregate_opportunity(per_symbol, kind)
                for kind in OPPORTUNITIES
            },
            "breakout_outcomes": {
                outcome: _aggregate_breakout_outcome(per_symbol, outcome)
                for outcome in ("BREAKOUT_HELD", "BREAKOUT_FAKEOUT")
            },
            "opportunity_path": _aggregate_path(per_symbol),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md = markdown_report(report)
    args.output_md.write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

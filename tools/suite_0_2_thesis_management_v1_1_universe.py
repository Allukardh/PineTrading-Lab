#!/usr/bin/env python3
"""15-symbol 1D robustness for capability-aware Thesis Management V1.1.

Reuses the exact V1.1 analyze("1d", ...) implementation for every symbol.
No per-symbol retuning. No synthetic anchors.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, pct, sha256_file
from tools.suite_0_2_thesis_management_v1_1_evidence import analyze


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


def _sum_counter(per_symbol: dict, path: tuple[str, ...]) -> Counter:
    out = Counter()
    for item in per_symbol.values():
        obj = item
        for key in path:
            obj = obj[key]
        out.update(obj)
    return out


def aggregate(per_symbol: dict) -> dict:
    confirms = sum(x["operator_confirm_bars"] for x in per_symbol.values())
    episodes = sum(x["management_episodes"] for x in per_symbol.values())

    anchor_classes = _sum_counter(
        per_symbol, ("summary", "anchor_class_counts")
    )
    outcomes = _sum_counter(per_symbol, ("summary", "outcomes"))
    sources = _sum_counter(per_symbol, ("summary", "source_counts"))
    directions = _sum_counter(per_symbol, ("summary", "direction_counts"))
    states = _sum_counter(per_symbol, ("summary", "state_counts"))
    strengths = _sum_counter(per_symbol, ("summary", "strength_counts"))

    bars_live = sum(x["summary"]["bars_live"] for x in per_symbol.values())
    target_capable = sum(x["summary"]["target_capable"] for x in per_symbol.values())
    invalid_capable = sum(
        x["summary"]["invalidation_capable"] for x in per_symbol.values()
    )

    parity_checked = sum(
        x["full_anchor_v1_parity"]["checked_full_episodes"]
        for x in per_symbol.values()
    )
    parity_mismatches = sum(
        x["full_anchor_v1_parity"]["mismatches"]
        for x in per_symbol.values()
    )

    invalidated_total = sum(
        x["summary"]["invalidated_protect"]["episodes"]
        for x in per_symbol.values()
    )
    invalidated_protect_reached = sum(
        x["summary"]["invalidated_protect"]["reached"]
        for x in per_symbol.values()
    )
    invalidated_realization_reached = sum(
        x["summary"]["invalidated_realization"]["reached"]
        for x in per_symbol.values()
    )
    completed_total = sum(
        x["summary"]["completed_realization"]["episodes"]
        for x in per_symbol.values()
    )
    completed_realization_reached = sum(
        x["summary"]["completed_realization"]["reached"]
        for x in per_symbol.values()
    )

    realization_eps = sum(
        x["summary"]["realization_persistence"]["episodes_with_realization"]
        for x in per_symbol.values()
    )
    realization_entries = sum(
        x["summary"]["realization_persistence"]["total_entries"]
        for x in per_symbol.values()
    )
    realization_bars = sum(
        x["summary"]["realization_persistence"]["total_realization_bars"]
        for x in per_symbol.values()
    )
    realization_max_run = max(
        (
            x["summary"]["realization_persistence"]["max_run_overall"]
            for x in per_symbol.values()
        ),
        default=0,
    )

    symbols_with_realization = sum(
        x["summary"]["realization_persistence"]["episodes_with_realization"] > 0
        for x in per_symbol.values()
    )
    symbols_with_protect = sum(
        x["summary"]["state_counts"].get("PROTECT", 0) > 0
        for x in per_symbol.values()
    )

    issue_counts = Counter()
    multi_source_confirms = 0
    for x in per_symbol.values():
        issue_counts.update(x["anchor_issue_counts"])
        multi_source_confirms += x["multi_source_confirms"]

    return {
        "symbols": len(per_symbol),
        "operator_confirms": confirms,
        "management_episodes": episodes,
        "management_episode_pct": pct(episodes, confirms),
        "anchor_class_counts": dict(sorted(anchor_classes.items())),
        "target_capable": target_capable,
        "target_capable_pct": pct(target_capable, episodes),
        "invalidation_capable": invalid_capable,
        "invalidation_capable_pct": pct(invalid_capable, episodes),
        "full_anchor_parity_checked": parity_checked,
        "full_anchor_parity_mismatches": parity_mismatches,
        "full_anchor_parity_pct": pct(
            parity_checked - parity_mismatches, parity_checked
        ),
        "outcomes": dict(sorted(outcomes.items())),
        "source_counts": dict(sorted(sources.items())),
        "direction_counts": dict(sorted(directions.items())),
        "bars_live": bars_live,
        "state_counts": dict(sorted(states.items())),
        "state_pct": {
            k: pct(v, bars_live) for k, v in sorted(states.items())
        },
        "strength_counts": dict(sorted(strengths.items())),
        "invalidated_episodes_capable": invalidated_total,
        "invalidated_protect_reached": invalidated_protect_reached,
        "invalidated_protect_pct": pct(
            invalidated_protect_reached, invalidated_total
        ),
        "invalidated_realization_reached": invalidated_realization_reached,
        "invalidated_realization_pct": pct(
            invalidated_realization_reached, invalidated_total
        ),
        "completed_episodes_capable": completed_total,
        "completed_realization_reached": completed_realization_reached,
        "completed_realization_pct": pct(
            completed_realization_reached, completed_total
        ),
        "realization_persistence": {
            "symbols_with_realization": symbols_with_realization,
            "episodes_with_realization": realization_eps,
            "total_entries": realization_entries,
            "total_realization_bars": realization_bars,
            "max_run_overall": realization_max_run,
        },
        "symbols_with_protect": symbols_with_protect,
        "multi_source_confirms": multi_source_confirms,
        "anchor_issue_counts": dict(sorted(issue_counts.items())),
    }


def _fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown(report: dict) -> str:
    a = report["aggregate"]
    caps = a["anchor_class_counts"]
    states = a["state_pct"]

    lines = [
        "# Suite 0.2 — 15-symbol 1D Thesis Management V1.1",
        "",
        "Capability-aware daily robustness. Every directional CONFIRMA creates a management thesis; anchors are never synthesized.",
        "",
        f"- symbols: **{a['symbols']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Aggregate capability / parity",
        "",
        f"- operator confirms: **{a['operator_confirms']}**",
        f"- management episodes: **{a['management_episodes']} ({_fmt(a['management_episode_pct'])}%)**",
        f"- FULL: **{caps.get('FULL',0)}**",
        f"- INVALIDATION_ONLY: **{caps.get('INVALIDATION_ONLY',0)}**",
        f"- TARGET_ONLY: **{caps.get('TARGET_ONLY',0)}**",
        f"- NONE: **{caps.get('NONE',0)}**",
        f"- target-capable: **{a['target_capable']} ({_fmt(a['target_capable_pct'])}%)**",
        f"- invalidation-capable: **{a['invalidation_capable']} ({_fmt(a['invalidation_capable_pct'])}%)**",
        f"- FULL V1 parity: **{a['full_anchor_parity_checked']-a['full_anchor_parity_mismatches']}/{a['full_anchor_parity_checked']} ({_fmt(a['full_anchor_parity_pct'])}%)**",
        "",
        "## Aggregate management behavior",
        "",
        f"- CONTINUATION: **{_fmt(states.get('CONTINUATION'))}%**",
        f"- PROTECT: **{_fmt(states.get('PROTECT'))}%**",
        f"- REALIZATION_RISK: **{_fmt(states.get('REALIZATION_RISK'))}%**",
        f"- invalidated episodes with PROTECT: **{a['invalidated_protect_reached']}/{a['invalidated_episodes_capable']} ({_fmt(a['invalidated_protect_pct'])}%)**",
        f"- completed episodes with REALIZATION_RISK: **{a['completed_realization_reached']}/{a['completed_episodes_capable']} ({_fmt(a['completed_realization_pct'])}%)**",
        f"- invalidated episodes with REALIZATION_RISK: **{a['invalidated_realization_reached']}/{a['invalidated_episodes_capable']} ({_fmt(a['invalidated_realization_pct'])}%)**",
        "",
        "## REALIZATION persistence",
        "",
        f"- symbols with any REALIZATION_RISK: **{a['realization_persistence']['symbols_with_realization']} / {a['symbols']}**",
        f"- episodes with REALIZATION_RISK: **{a['realization_persistence']['episodes_with_realization']}**",
        f"- realization entries: **{a['realization_persistence']['total_entries']}**",
        f"- realization bars: **{a['realization_persistence']['total_realization_bars']}**",
        f"- max consecutive realization run: **{a['realization_persistence']['max_run_overall']}**",
        "",
        "## Per-symbol daily summary",
        "",
        "| symbol | confirms | mgmt % | FULL | INV only | TARGET only | NONE | PROTECT % | REALIZATION % | invalidated PROTECT % | completed REALIZATION % | realization episodes | V1 parity % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for symbol in SYMBOLS:
        x = report["symbols"][symbol]
        s = x["summary"]
        c = s["anchor_class_counts"]
        p = s["state_pct"]
        ip = s["invalidated_protect"]
        cr = s["completed_realization"]
        rp = s["realization_persistence"]
        lines.append(
            "| {symbol} | {conf} | {mgmt} | {full} | {inv} | {target} | {none} | {protect} | {real} | {ip} | {cr} | {reps} | {parity} |".format(
                symbol=symbol,
                conf=x["operator_confirm_bars"],
                mgmt=_fmt(x["management_episode_pct"]),
                full=c.get("FULL",0),
                inv=c.get("INVALIDATION_ONLY",0),
                target=c.get("TARGET_ONLY",0),
                none=c.get("NONE",0),
                protect=_fmt(p.get("PROTECT")),
                real=_fmt(p.get("REALIZATION_RISK")),
                ip=_fmt(ip["reached_pct"]),
                cr=_fmt(cr["reached_pct"]),
                reps=rp["episodes_with_realization"],
                parity=_fmt(x["full_anchor_v1_parity"]["parity_pct"]),
            )
        )

    lines += [
        "",
        "## REALIZATION_RISK episode diagnostics",
        "",
        "| symbol | source | kind | dir | capability | outcome | live bars | realization bars | entries | runs | max run | first progress | lead bars | warning->continuation |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["realization_episode_details"]:
        lines.append(
            "| {symbol} | {source} | {kind} | {direction} | {cap} | {outcome} | {live} | {rb} | {entries} | {runs} | {maxrun} | {progress} | {lead} | {back} |".format(
                symbol=row["symbol"],
                source=row["source"],
                kind=row["opportunity_kind"],
                direction=row["direction"],
                cap=row["anchor_capability"],
                outcome=row["outcome"],
                live=row["bars_live"],
                rb=row["realization_bars"],
                entries=row["realization_entries"],
                runs=row["realization_run_count"],
                maxrun=row["realization_max_run"],
                progress=_fmt(row["first_realization_progress"]),
                lead=_fmt(row["realization_lead_bars"]),
                back=row["warning_to_continuation_transitions"],
            )
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Same V1.1 logic for all 15 symbols.",
        "- No per-asset retuning.",
        "- No synthetic target or invalidation.",
        "- FULL-anchor episodes must remain exact V1 parity.",
        "- PROTECT/REALIZATION denominators are capability-aware.",
        "- REALIZATION_RISK is a thesis-management warning, not an automatic sell/short command.",
        "- No production Pine/default/profile/panel changes.",
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
        for tf in ("1d","1w"):
            p = args.data_root / "spot" / symbol / "consolidated" / f"{symbol}_{tf}.parquet"
            if not p.is_file():
                raise SystemExit(f"missing dataset: {p}")
            ds = load_dataset(p)
            datasets[tf] = ds
            dataset_meta[symbol][tf] = {
                "rows": len(ds["close"]),
                "sha256": sha256_file(p),
            }
        per_symbol[symbol] = analyze("1d", datasets, args.tick_size)

    realization_episode_details = []
    for symbol, item in per_symbol.items():
        for row in item["results"]:
            if row["first_realization_bar"] is None:
                continue
            realization_episode_details.append({
                "symbol": symbol,
                "thesis_id": row["thesis_id"],
                "source": row["source"],
                "opportunity_kind": row["opportunity_kind"],
                "direction": "LONG" if row["direction"] == 1 else "SHORT",
                "anchor_capability": row["anchor_capability"],
                "outcome": row["outcome"],
                "bars_live": row["bars_live"],
                "first_realization_bar": row["first_realization_bar"],
                "first_realization_progress": row["first_realization_progress"],
                "realization_lead_bars": row["realization_lead_bars"],
                "realization_bars": row["realization_bars"],
                "realization_entries": row["realization_entries"],
                "realization_run_count": row["realization_run_count"],
                "realization_max_run": row["realization_max_run"],
                "realization_median_run": row["realization_median_run"],
                "warning_to_continuation_transitions": row["warning_to_continuation_transitions"],
            })

    report = {
        "metadata": {
            "code_sha": args.code_sha,
            "timeframe": "1d",
            "symbols": list(SYMBOLS),
            "dataset_meta": dataset_meta,
            "contract": "capability-aware Management V1.1",
        },
        "symbols": per_symbol,
        "aggregate": aggregate(per_symbol),
        "realization_episode_details": sorted(
            realization_episode_details,
            key=lambda x: (-x["realization_bars"], x["symbol"], x["thesis_id"]),
        ),
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

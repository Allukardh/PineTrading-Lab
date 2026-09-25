#!/usr/bin/env python3
"""15-symbol 1D robustness for preregistered Thesis Management V1.

Uses identical V1 semantics and exact accepted daily/weekly production data.
No per-symbol tuning.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import distribution, pct, sha256_file, load_dataset
from tools.suite_0_2_thesis_management_v1_evidence import analyze


SYMBOLS=(
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT",
    "ADAUSDT","XRPUSDT","SOLUSDT","UNIUSDT","NEARUSDT",
    "AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)


def _dist(values):
    return distribution([float(v) for v in values if v is not None])


def _aggregate(per_symbol):
    total_confirms=sum(x["operator_confirm_bars"] for x in per_symbol.values())
    supported=sum(x["supported_management_episodes"] for x in per_symbol.values())
    unsupported=Counter()
    outcomes=Counter()
    state_counts=Counter()
    source_counts=Counter()
    direction_counts=Counter()
    all_results=[]
    live=0
    transitions=0
    warning_back=0

    for x in per_symbol.values():
        unsupported.update(x["unsupported"])
        s=x["summary"]
        outcomes.update(s["outcomes"])
        state_counts.update(s["state_counts"])
        source_counts.update(s["source_counts"])
        direction_counts.update(s["direction_counts"])
        live+=s["bars_live"]
        transitions+=s["transitions"]
        warning_back+=s["warning_to_continuation_transitions"]
        all_results.extend(x["results"])

    completed=[r for r in all_results if r["outcome"]=="COMPLETED"]
    invalidated=[r for r in all_results if r["outcome"]=="INVALIDATED"]
    superseded=[r for r in all_results if r["outcome"]=="SUPERSEDED"]

    def reach(rows,key,lead_key,progress_key):
        hit=[r for r in rows if r[key] is not None]
        return {
            "episodes":len(rows),
            "reached":len(hit),
            "reached_pct":pct(len(hit),len(rows)),
            "lead_bars":_dist([r[lead_key] for r in hit]),
            "first_progress":_dist([r[progress_key] for r in hit]),
        }

    return {
        "operator_confirms":total_confirms,
        "supported":supported,
        "support_pct":pct(supported,total_confirms),
        "unsupported":dict(sorted(unsupported.items())),
        "outcomes":dict(sorted(outcomes.items())),
        "live_bars":live,
        "state_counts":dict(sorted(state_counts.items())),
        "state_pct":{k:pct(v,live) for k,v in sorted(state_counts.items())},
        "source_counts":dict(sorted(source_counts.items())),
        "direction_counts":dict(sorted(direction_counts.items())),
        "transitions_per_1000_live_bars":None if not live else 1000*transitions/live,
        "warning_back_per_1000_live_bars":None if not live else 1000*warning_back/live,
        "completed_realization":reach(
            completed,"first_realization_bar","realization_lead_bars","first_realization_progress"
        ),
        "completed_protect":reach(
            completed,"first_protect_bar","protect_lead_bars","first_protect_progress"
        ),
        "invalidated_protect":reach(
            invalidated,"first_protect_bar","protect_lead_bars","first_protect_progress"
        ),
        "invalidated_realization":reach(
            invalidated,"first_realization_bar","realization_lead_bars","first_realization_progress"
        ),
        "superseded_protect":reach(
            superseded,"first_protect_bar","protect_lead_bars","first_protect_progress"
        ),
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    a=report["aggregate"]
    lines=[
        "# Suite 0.2 — 15-symbol 1D Thesis Management V1",
        "",
        "Same preregistered V1 for every symbol. No per-symbol tuning.",
        "",
        f"- symbols: **{len(report['symbols'])}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Aggregate",
        "",
        f"- operator confirms: **{a['operator_confirms']}**",
        f"- supported anchored management episodes: **{a['supported']} ({_fmt(a['support_pct'])}%)**",
        f"- outcomes: `{json.dumps(a['outcomes'],sort_keys=True)}`",
        f"- directions: `{json.dumps(a['direction_counts'],sort_keys=True)}`",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| CONTINUATION live-bar % | {_fmt(a['state_pct'].get('CONTINUATION'))} |",
        f"| PROTECT live-bar % | {_fmt(a['state_pct'].get('PROTECT'))} |",
        f"| REALIZATION_RISK live-bar % | {_fmt(a['state_pct'].get('REALIZATION_RISK'))} |",
        f"| transitions / 1000 live bars | {_fmt(a['transitions_per_1000_live_bars'])} |",
        f"| warning -> CONT / 1000 | {_fmt(a['warning_back_per_1000_live_bars'])} |",
        f"| invalidated with PROTECT % | {_fmt(a['invalidated_protect']['reached_pct'])} |",
        f"| invalidation PROTECT lead median | {_fmt(a['invalidated_protect']['lead_bars']['median'])} |",
        f"| completed with REALIZATION_RISK % | {_fmt(a['completed_realization']['reached_pct'])} |",
        f"| realization lead median | {_fmt(a['completed_realization']['lead_bars']['median'])} |",
        f"| invalidated with REALIZATION_RISK % | {_fmt(a['invalidated_realization']['reached_pct'])} |",
        "",
        "## Per-symbol 1D",
        "",
        "| symbol | confirms | support % | completed | invalidated | PROTECT % | REALIZATION % | invalidated PROTECT % | completed REALIZATION % | invalidated REALIZATION |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for symbol in SYMBOLS:
        x=report["symbols"][symbol];s=x["summary"];o=s["outcomes"];p=s["state_pct"]
        ip=s["invalidated"]["protect"]; cr=s["completed"]["realization"]; ir=s["invalidated"]["realization"]
        lines.append(
            f"| {symbol} | {x['operator_confirm_bars']} | {_fmt(pct(x['supported_management_episodes'],x['operator_confirm_bars']))} | {o.get('COMPLETED',0)} | {o.get('INVALIDATED',0)} | {_fmt(p.get('PROTECT'))} | {_fmt(p.get('REALIZATION_RISK'))} | {_fmt(ip['reached_pct'])} | {_fmt(cr['reached_pct'])} | {ir['reached']} |"
        )

    lines += [
        "",
        "## Unsupported anchors",
        "",
    ]
    for key,value in a["unsupported"].items():
        lines.append(f"- `{key}`: **{value}**")

    lines += [
        "",
        "## Guardrails",
        "",
        "- V1 semantics are identical for all 15 symbols.",
        "- Only accepted 1D/1W production Parquets are used.",
        "- No per-symbol fallback/retuning.",
        "- Missing anchors remain explicit; no synthetic target/invalidation is invented.",
        "- Metrics describe thesis-management behavior, not trading profitability.",
        "- No production Pine/default/profile/panel change.",
        "",
    ]
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",type=Path,required=True)
    ap.add_argument("--output-json",type=Path,required=True)
    ap.add_argument("--output-md",type=Path,required=True)
    ap.add_argument("--code-sha",default="unknown")
    ap.add_argument("--tick-size",type=float,default=.01)
    a=ap.parse_args()

    per_symbol={}
    meta={}
    for symbol in SYMBOLS:
        datasets={}
        meta[symbol]={}
        for tf in ("1d","1w"):
            p=a.data_root/"spot"/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
            if not p.is_file():raise SystemExit(f"missing dataset: {p}")
            ds=load_dataset(p)
            datasets[tf]=ds
            meta[symbol][tf]={"rows":len(ds["close"]),"sha256":sha256_file(p)}
        per_symbol[symbol]=analyze("1d",datasets,a.tick_size)

    report={
        "metadata":{"code_sha":a.code_sha,"timeframe":"1d","dataset_meta":meta},
        "symbols":per_symbol,
        "aggregate":_aggregate(per_symbol),
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report);a.output_md.write_text(md+"\n");print(md)
    return 0

if __name__=="__main__":
    raise SystemExit(main())

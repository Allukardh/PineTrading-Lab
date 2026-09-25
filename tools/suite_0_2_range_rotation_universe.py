#!/usr/bin/env python3
"""15-symbol 1D robustness for structural RANGE_ROTATION.

Primary contract under test: EDGE_REJECTION.
SWEEP_RECLAIM is retained only as auxiliary telemetry.
No per-symbol tuning.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, pct, sha256_file
from tools.suite_0_2_range_rotation_evidence import analyze_timeframe


SYMBOLS = (
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT",
    "ADAUSDT","XRPUSDT","SOLUSDT","UNIUSDT","NEARUSDT",
    "AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)


def aggregate_edge(per_symbol: dict) -> dict:
    episodes = 0
    outcomes = Counter()
    directions = Counter()
    baseline_covered = 0
    positive_symbols = 0
    regime = {}

    for symbol, item in per_symbol.items():
        edge = item["by_trigger"].get("EDGE_REJECTION")
        if edge is None:
            continue
        s = edge["structural"]
        b = edge["frozen_0_1_response"]
        n = s["episodes"]
        episodes += n
        outcomes.update(s["outcome_counts"])
        directions.update(s["direction_counts"])
        baseline_covered += int(b.get("covered_count", 0))
        if n > 0:
            positive_symbols += 1

        for relation in ("NEUTRAL","WITH_REGIME","AGAINST_REGIME"):
            key=f"EDGE_REJECTION/{relation}"
            row=item["by_trigger_and_regime_relation"].get(key)
            if row is None:
                continue
            r=regime.setdefault(relation,{
                "episodes":0,"outcomes":Counter(),"directions":Counter(),
            })
            rs=row["structural"]
            r["episodes"] += rs["episodes"]
            r["outcomes"].update(rs["outcome_counts"])
            r["directions"].update(rs["direction_counts"])

    def summary(n, counts):
        mid_or_better = counts["MID_REACHED"] + counts["OPPOSITE_REACHED"]
        return {
            "episodes": n,
            "outcome_counts": dict(sorted(counts.items())),
            "midpoint_or_better_pct": pct(mid_or_better,n),
            "opposite_reached_pct": pct(counts["OPPOSITE_REACHED"],n),
            "failed_before_mid_pct": pct(counts["FAILED_BEFORE_MID"],n),
            "censored_pct": pct(counts["CENSORED"],n),
        }

    out=summary(episodes,outcomes)
    out["direction_counts"]=dict(sorted(directions.items()))
    out["frozen_0_1_covered_count"]=baseline_covered
    out["frozen_0_1_covered_pct"]=pct(baseline_covered,episodes)
    out["symbols_with_edge_episodes"]=positive_symbols
    out["by_regime_relation"]={}
    for name,r in sorted(regime.items()):
        x=summary(r["episodes"],r["outcomes"])
        x["direction_counts"]=dict(sorted(r["directions"].items()))
        out["by_regime_relation"][name]=x
    return out


def markdown(report):
    agg=report["aggregate"]["edge_rejection"]
    lines=[
        "# Suite 0.2 — 15-symbol 1D RANGE_ROTATION robustness",
        "",
        "Primary contract: EDGE_REJECTION. Same thresholds for every symbol.",
        "",
        f"- symbols: **{len(report['symbols'])}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Aggregate EDGE_REJECTION",
        "",
        f"- episodes: **{agg['episodes']}**",
        f"- symbols with episodes: **{agg['symbols_with_edge_episodes']} / {len(report['symbols'])}**",
        f"- midpoint or better: **{agg['midpoint_or_better_pct']:.2f}%**",
        f"- opposite edge reached: **{agg['opposite_reached_pct']:.2f}%**",
        f"- failed before midpoint: **{agg['failed_before_mid_pct']:.2f}%**",
        f"- censored: **{agg['censored_pct']:.2f}%**",
        f"- frozen 0.1 covered: **{agg['frozen_0_1_covered_pct']:.2f}%**",
        f"- LONG/SHORT: **{agg['direction_counts'].get('LONG',0)} / {agg['direction_counts'].get('SHORT',0)}**",
        "",
        "## Regime relation",
        "",
        "| relation | episodes | midpoint+ % | opposite % | fail before mid % |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name,x in agg["by_regime_relation"].items():
        lines.append(
            f"| {name} | {x['episodes']} | {x['midpoint_or_better_pct']:.2f} | {x['opposite_reached_pct']:.2f} | {x['failed_before_mid_pct']:.2f} |"
        )

    lines += [
        "",
        "## Per-symbol EDGE_REJECTION",
        "",
        "| symbol | episodes | midpoint+ % | opposite % | fail before mid % | 0.1 covered % | LONG | SHORT |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for symbol in SYMBOLS:
        item=report["symbols"][symbol]
        edge=item["by_trigger"].get("EDGE_REJECTION")
        if edge is None:
            lines.append(f"| {symbol} | 0 | n/a | n/a | n/a | n/a | 0 | 0 |")
            continue
        s=edge["structural"]; b=edge["frozen_0_1_response"]
        lines.append(
            f"| {symbol} | {s['episodes']} | {s['midpoint_or_better_pct']:.2f} | {s['opposite_reached_pct']:.2f} | {s['failed_before_mid_pct']:.2f} | {b['confirmed_or_already_aligned_pct']:.2f} | {s['direction_counts'].get('LONG',0)} | {s['direction_counts'].get('SHORT',0)} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Same structural box / edge-rejection contract for all symbols.",
        "- No per-symbol retuning.",
        "- SWEEP_RECLAIM is not a primary trigger in this gate.",
        "- Outcome is structural follow-through, not profitability.",
        "- Frozen Execution 0.1 is measured only as existing coverage.",
        "- No Opportunity v2 integration or production Pine change occurs here.",
        "",
    ]
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",type=Path,required=True)
    ap.add_argument("--output-json",type=Path,required=True)
    ap.add_argument("--output-md",type=Path,required=True)
    ap.add_argument("--code-sha",default="unknown")
    ap.add_argument("--tick-size",type=float,default=0.01)
    args=ap.parse_args()

    per_symbol={}
    meta={}
    for symbol in SYMBOLS:
        datasets={}
        meta[symbol]={}
        for tf in ("1d","1w"):
            path=args.data_root/"spot"/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
            if not path.is_file():
                raise SystemExit(f"missing dataset: {path}")
            data=load_dataset(path)
            datasets[tf]=data
            meta[symbol][tf]={
                "rows":len(data["close"]),
                "sha256":sha256_file(path),
            }
        per_symbol[symbol]=analyze_timeframe("1d",datasets,args.tick_size)

    report={
        "metadata":{
            "code_sha":args.code_sha,
            "timeframe":"1d",
            "symbols":list(SYMBOLS),
            "datasets":meta,
        },
        "symbols":per_symbol,
        "aggregate":{
            "edge_rejection":aggregate_edge(per_symbol),
        },
    }
    args.output_json.parent.mkdir(parents=True,exist_ok=True)
    args.output_md.parent.mkdir(parents=True,exist_ok=True)
    args.output_json.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    md=markdown(report)
    args.output_md.write_text(md+"\n",encoding="utf-8")
    print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

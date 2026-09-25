#!/usr/bin/env python3
"""15-symbol 1D robustness for ANTECIPADO_TREND.

Reuses the exact refined responsiveness/profile analysis on the daily horizon.
No per-symbol tuning. PADRAO remains the accepted comparator; removed profiles
are not reconsidered here.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from tools.execution_historical_evidence import distribution, load_dataset, pct, sha256_file
from tools.suite_0_2_responsiveness_profile_quality import analyze


SYMBOLS=(
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT",
    "ADAUSDT","XRPUSDT","SOLUSDT","UNIUSDT","NEARUSDT",
    "AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)
KINDS=("BREAKOUT_EXPANSION","REACCELERATION","REGIME_REVERSAL")


def _dist(xs):
    return distribution([float(x) for x in xs if x is not None])


def aggregate(per_symbol):
    rows=[]
    per_kind={}
    all_dirs=Counter()
    symbols_with_events=0
    symbols_with_breakout=0
    symbols_with_reacc=0

    for symbol,item in per_symbol.items():
        a=item["ANTECIPADO_TREND"]
        if a["events"]:
            symbols_with_events+=1
        if a["by_kind"]["BREAKOUT_EXPANSION"]["all"]["events"]:
            symbols_with_breakout+=1
        if a["by_kind"]["REACCELERATION"]["all"]["events"]:
            symbols_with_reacc+=1
        all_dirs.update(a["direction_counts"])
        for r in a["rows"]:
            rows.append({"symbol":symbol,**r})

    for kind in KINDS:
        kr=[r for r in rows if r["kind"]==kind]
        conv=[r for r in kr if r["converted"]]
        non=[r for r in kr if not r["converted"]]

        def outcomes(xs):
            c=Counter(r["outcome"] for r in xs)
            resolved=c["BREAKOUT_HELD"]+c["BREAKOUT_FAKEOUT"]
            return {
                "events":len(xs),
                "outcome_counts":dict(sorted(c.items())),
                "held":c["BREAKOUT_HELD"],
                "fakeout":c["BREAKOUT_FAKEOUT"],
                "unresolved":c["BREAKOUT_UNRESOLVED"],
                "not_applicable":c["NOT_APPLICABLE"],
                "held_pct_resolved":pct(c["BREAKOUT_HELD"],resolved),
            }

        quick=sum(
            r["nonconverted_duration_bars"] is not None
            and r["nonconverted_duration_bars"]<=3
            for r in non
        )
        per_kind[kind]={
            "all":outcomes(kr),
            "converted":outcomes(conv),
            "nonconverted":outcomes(non),
            "conversion_pct":pct(len(conv),len(kr)),
            "quick_nonconverted_le_3":quick,
            "quick_nonconverted_le_3_pct":pct(quick,len(non)),
            "bars_saved":_dist([r["bars_to_confirm"] for r in conv]),
            "move_waiting_atr":_dist([
                r["directional_displacement_to_confirm_atr"] for r in conv
            ]),
        }

    converted=[r for r in rows if r["converted"]]
    non=[r for r in rows if not r["converted"]]
    quick=sum(
        r["nonconverted_duration_bars"] is not None
        and r["nonconverted_duration_bars"]<=3
        for r in non
    )

    return {
        "events":len(rows),
        "symbols_with_any_event":symbols_with_events,
        "symbols_with_breakout":symbols_with_breakout,
        "symbols_with_reacceleration":symbols_with_reacc,
        "converted":len(converted),
        "conversion_pct":pct(len(converted),len(rows)),
        "nonconverted":len(non),
        "quick_nonconverted_le_3":quick,
        "quick_nonconverted_le_3_pct":pct(quick,len(non)),
        "direction_counts":dict(sorted(all_dirs.items())),
        "by_kind":per_kind,
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    a=report["aggregate"]
    lines=[
        "# Suite 0.2 — 15-symbol 1D ANTECIPADO_TREND robustness",
        "",
        "Unchanged early TREND posture across the accepted daily universe. No per-symbol tuning.",
        "",
        f"- symbols: **{len(SYMBOLS)}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        f"- symbols with any early TREND event: **{a['symbols_with_any_event']} / {len(SYMBOLS)}**",
        f"- LONG / SHORT: **{a['direction_counts'].get('LONG',0)} / {a['direction_counts'].get('SHORT',0)}**",
        "",
        "## Aggregate quality",
        "",
        "| kind | events | conversion % | converted HELD/FAKEOUT | converted HELD % | nonconverted HELD/FAKEOUT | nonconverted HELD % | quick nonconverted <=3 % | lead bars med | move waiting ATR med |",
        "| --- | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for kind in KINDS:
        g=a["by_kind"][kind];c=g["converted"];n=g["nonconverted"]
        lines.append(
            f"| {kind} | {g['all']['events']} | {_fmt(g['conversion_pct'])} | {c['held']}/{c['fakeout']} | {_fmt(c['held_pct_resolved'])} | {n['held']}/{n['fakeout']} | {_fmt(n['held_pct_resolved'])} | {_fmt(g['quick_nonconverted_le_3_pct'])} | {_fmt(g['bars_saved']['median'])} | {_fmt(g['move_waiting_atr']['median'])} |"
        )

    lines += [
        "",
        "## Per-symbol daily breadth",
        "",
        "| symbol | events | conversion % | quick nonconverted <=3 % | breakout events | reaccel events | LONG | SHORT |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for symbol in SYMBOLS:
        x=report["symbols"][symbol]["ANTECIPADO_TREND"]
        lines.append(
            f"| {symbol} | {x['events']} | {_fmt(x['conversion_pct'])} | {_fmt(x['quick_nonconverted_le_3_pct_of_nonconverted'])} | {x['by_kind']['BREAKOUT_EXPANSION']['all']['events']} | {x['by_kind']['REACCELERATION']['all']['events']} | {x['direction_counts'].get('LONG',0)} | {x['direction_counts'].get('SHORT',0)} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Only TREND_OPPORTUNITY_V2 newly-ARMED events are eligible.",
        "- Conversion must be earned by the TREND path itself.",
        "- HELD/FAKEOUT are retrospective structural diagnostics, not trade profitability.",
        "- REGIME_REVERSAL is not scored as HELD/FAKEOUT.",
        "- PADRÃO remains unchanged.",
        "- No per-symbol retuning.",
        "- No production Pine/default/profile/panel changes.",
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

    per_symbol={}; meta={}
    for symbol in SYMBOLS:
        datasets={};meta[symbol]={}
        for tf in ("1d","1w"):
            p=a.data_root/"spot"/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
            if not p.is_file():
                raise SystemExit(f"missing dataset: {p}")
            ds=load_dataset(p)
            datasets[tf]=ds
            meta[symbol][tf]={"rows":len(ds["close"]),"sha256":sha256_file(p)}
        per_symbol[symbol]=analyze("1d",datasets,a.tick_size)

    report={
        "metadata":{
            "code_sha":a.code_sha,
            "timeframe":"1d",
            "symbols":list(SYMBOLS),
            "dataset_meta":meta,
        },
        "symbols":per_symbol,
        "aggregate":aggregate(per_symbol),
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report);a.output_md.write_text(md+"\n");print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

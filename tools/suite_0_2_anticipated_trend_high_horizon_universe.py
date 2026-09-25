#!/usr/bin/env python3
"""15-symbol 3D/1W robustness for unchanged ANTECIPADO_TREND.

Uses the accepted high-horizon Market Map contract:
- daily reference levels are disabled on 3D/1W;
- the 3D dataset may occupy the unused daily constructor slot;
- exact 1W data remains the weekly/context dataset.

No per-symbol or per-horizon tuning.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import distribution, load_dataset, pct
from tools.suite_0_2_responsiveness_profile_quality import (
    _projections,
    _trend_early_quality,
)
from tools.suite_0_2_thesis_management_evidence import _build_operator_paths


SYMBOLS=(
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT","ADAUSDT","XRPUSDT",
    "SOLUSDT","UNIUSDT","NEARUSDT","AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)
TFS=("3d","1w")
KINDS=("BREAKOUT_EXPANSION","REACCELERATION","REGIME_REVERSAL")


def _dist(xs):
    return distribution([float(x) for x in xs if x is not None])


def analyze(tf,datasets,tick):
    ctx=_build_operator_paths(tf,datasets,tick)
    projections,path_rows=_projections(ctx)
    a=_trend_early_quality(ctx,projections,path_rows)
    a["rows"]=len(ctx["data"]["close"])
    return a


def aggregate_tf(per_symbol,tf):
    rows=[]
    dirs=Counter()
    symbols_with_events=0
    for symbol,item in per_symbol.items():
        a=item[tf]
        if a["events"]:
            symbols_with_events+=1
        dirs.update(a["direction_counts"])
        for r in a["rows"]:
            rows.append({"symbol":symbol,**r})

    by_kind={}
    for kind in KINDS:
        kr=[r for r in rows if r["kind"]==kind]
        conv=[r for r in kr if r["converted"]]
        non=[r for r in kr if not r["converted"]]

        def summary(xs):
            c=Counter(r["outcome"] for r in xs)
            resolved=c["BREAKOUT_HELD"]+c["BREAKOUT_FAKEOUT"]
            return {
                "events":len(xs),
                "held":c["BREAKOUT_HELD"],
                "fakeout":c["BREAKOUT_FAKEOUT"],
                "unresolved":c["BREAKOUT_UNRESOLVED"],
                "not_applicable":c["NOT_APPLICABLE"],
                "held_pct_resolved":pct(c["BREAKOUT_HELD"],resolved),
                "outcomes":dict(sorted(c.items())),
            }

        quick=sum(
            r["nonconverted_duration_bars"] is not None
            and r["nonconverted_duration_bars"]<=3
            for r in non
        )
        by_kind[kind]={
            "all":summary(kr),
            "converted":summary(conv),
            "nonconverted":summary(non),
            "conversion_pct":pct(len(conv),len(kr)),
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
        "symbols_with_events":symbols_with_events,
        "converted":len(converted),
        "conversion_pct":pct(len(converted),len(rows)),
        "nonconverted":len(non),
        "quick_nonconverted_le_3_pct":pct(quick,len(non)),
        "direction_counts":dict(sorted(dirs.items())),
        "by_kind":by_kind,
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — 15-symbol 3D / 1W ANTECIPADO_TREND robustness",
        "",
        "Final Phase E high-horizon gate. Unchanged posture; no per-symbol/horizon tuning.",
        "",
        f"- symbols: **{len(SYMBOLS)}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Aggregate load",
        "",
        "| TF | events | symbols with events | conversion % | quick nonconverted <=3 % | LONG | SHORT |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,a in report["aggregate"].items():
        d=a["direction_counts"]
        lines.append(
            f"| {tf} | {a['events']} | {a['symbols_with_events']} | {_fmt(a['conversion_pct'])} | {_fmt(a['quick_nonconverted_le_3_pct'])} | {d.get('LONG',0)} | {d.get('SHORT',0)} |"
        )

    lines += [
        "",
        "## Structural quality",
        "",
        "| TF | kind | events | conversion % | converted HELD/FAKEOUT | converted HELD % | nonconverted HELD/FAKEOUT | nonconverted HELD % | lead bars med | move waiting ATR med |",
        "| --- | --- | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for tf,a in report["aggregate"].items():
        for kind,g in a["by_kind"].items():
            c=g["converted"];n=g["nonconverted"]
            lines.append(
                f"| {tf} | {kind} | {g['all']['events']} | {_fmt(g['conversion_pct'])} | {c['held']}/{c['fakeout']} | {_fmt(c['held_pct_resolved'])} | {n['held']}/{n['fakeout']} | {_fmt(n['held_pct_resolved'])} | {_fmt(g['bars_saved']['median'])} | {_fmt(g['move_waiting_atr']['median'])} |"
            )

    lines += [
        "",
        "## Per-symbol breadth",
        "",
        "| symbol | 3D events | 3D conversion % | 3D breakout/reaccel | 1W events | 1W conversion % | 1W breakout/reaccel |",
        "| --- | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for symbol in SYMBOLS:
        x=report["symbols"][symbol]
        d3=x["3d"];w=x["1w"]
        lines.append(
            f"| {symbol} | {d3['events']} | {_fmt(d3['conversion_pct'])} | {d3['by_kind']['BREAKOUT_EXPANSION']['all']['events']}/{d3['by_kind']['REACCELERATION']['all']['events']} | {w['events']} | {_fmt(w['conversion_pct'])} | {w['by_kind']['BREAKOUT_EXPANSION']['all']['events']}/{w['by_kind']['REACCELERATION']['all']['events']} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Same ANTECIPADO_TREND contract as lower horizons.",
        "- 3D/1W use the accepted high-horizon Market Map contract.",
        "- Daily reference levels remain disabled; no synthetic daily market evidence is created.",
        "- HELD/FAKEOUT are structural diagnostics, not profitability.",
        "- REGIME_REVERSAL remains outside HELD/FAKEOUT scoring.",
        "- No tuning, Pine/default/profile/panel production change.",
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

    per={}
    for symbol in SYMBOLS:
        base=a.data_root/"spot"/symbol/"consolidated"
        d3=load_dataset(base/f"{symbol}_3d.parquet")
        w=load_dataset(base/f"{symbol}_1w.parquet")
        datasets={"3d":d3,"1w":w,"1d":d3}
        per[symbol]={tf:analyze(tf,datasets,a.tick_size) for tf in TFS}

    report={
        "metadata":{
            "code_sha":a.code_sha,
            "symbols":list(SYMBOLS),
            "timeframes":list(TFS),
        },
        "symbols":per,
        "aggregate":{tf:aggregate_tf(per,tf) for tf in TFS},
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report)
    a.output_md.write_text(md+"\n")
    print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

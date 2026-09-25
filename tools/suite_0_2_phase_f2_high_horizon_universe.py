#!/usr/bin/env python3
"""15-symbol high-horizon Thesis Management V1.1 robustness.

Runs the accepted capability-aware management engine unchanged on 3D and 1W.
Each symbol uses exact accepted 1D/3D/1W datasets.

No per-symbol/timeframe retuning.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, pct, sha256_file
from tools.suite_0_2_thesis_management_v1_1_evidence import analyze as analyze_v11


SYMBOLS=(
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT",
    "ADAUSDT","XRPUSDT","SOLUSDT","UNIUSDT","NEARUSDT",
    "AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)
TIMEFRAMES=("3d","1w")
REQUIRED=("1d","3d","1w")


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def _load_symbol(data_root:Path,symbol:str):
    out={}
    meta={}
    for tf in REQUIRED:
        p=data_root/"spot"/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        if not p.is_file():
            raise SystemExit(f"missing dataset: {p}")
        out[tf]=load_dataset(p)
        meta[tf]={"rows":len(out[tf]["close"]),"sha256":sha256_file(p)}
    return out,meta


def _compact(x):
    x=dict(x)
    x.pop("results",None)
    inv={
        "every_confirm_has_management":x["operator_confirm_bars"]==x["management_episodes"],
        "full_v1_mismatches_zero":x["full_anchor_v1_parity"]["mismatches"]==0,
        "full_v1_parity_100":x["full_anchor_v1_parity"]["parity_pct"] in (None,100.0),
    }
    if not all(inv.values()):
        raise AssertionError(f"management invariant failure: {inv}")
    x["invariants"]=inv
    return x


def _aggregate(per_symbol,tf):
    confirms=mgmt=multi=bars_live=0
    caps=Counter();states=Counter();outcomes=Counter();sources=Counter();dirs=Counter()
    target_cap=inv_cap=0
    full_checked=full_mismatches=0
    inv_eps=inv_protect=0
    comp_eps=comp_real=0
    real_eps=real_entries=real_bars=0
    max_real_run=0
    transitions=warning_back=0
    symbols_with_confirms=0

    for symbol,item in per_symbol.items():
        x=item[tf];s=x["summary"]
        confirms+=x["operator_confirm_bars"];mgmt+=x["management_episodes"]
        multi+=x["multi_source_confirms"]
        if x["operator_confirm_bars"]:
            symbols_with_confirms+=1
        caps.update(s["anchor_class_counts"])
        states.update(s["state_counts"])
        outcomes.update(s["outcomes"])
        sources.update(s["source_counts"])
        dirs.update(s["direction_counts"])
        bars_live+=s["bars_live"]
        target_cap+=s["target_capable"];inv_cap+=s["invalidation_capable"]

        p=x["full_anchor_v1_parity"]
        full_checked+=p["checked_full_episodes"]
        full_mismatches+=p["mismatches"]

        ip=s["invalidated_protect"]
        inv_eps+=ip["episodes"];inv_protect+=ip["reached"]

        cr=s["completed_realization"]
        comp_eps+=cr["episodes"];comp_real+=cr["reached"]

        rp=s["realization_persistence"]
        real_eps+=rp["episodes_with_realization"]
        real_entries+=rp["total_entries"]
        real_bars+=rp["total_realization_bars"]
        max_real_run=max(max_real_run,rp["max_run_overall"])

        if s["transitions_per_1000_live_bars"] is not None:
            transitions+=round(s["transitions_per_1000_live_bars"]*s["bars_live"]/1000)
        if s["warning_back_per_1000_live_bars"] is not None:
            warning_back+=round(s["warning_back_per_1000_live_bars"]*s["bars_live"]/1000)

    return {
        "symbols_with_confirms":symbols_with_confirms,
        "confirms":confirms,
        "management_episodes":mgmt,
        "management_coverage_pct":pct(mgmt,confirms),
        "multi_source_confirms":multi,
        "anchor_class_counts":dict(sorted(caps.items())),
        "target_capable_pct":pct(target_cap,mgmt),
        "invalidation_capable_pct":pct(inv_cap,mgmt),
        "full_anchor_checked":full_checked,
        "full_anchor_mismatches":full_mismatches,
        "full_anchor_parity_pct":pct(full_checked-full_mismatches,full_checked),
        "bars_live":bars_live,
        "state_counts":dict(sorted(states.items())),
        "state_pct":{k:pct(v,bars_live) for k,v in sorted(states.items())},
        "outcomes":dict(sorted(outcomes.items())),
        "source_counts":dict(sorted(sources.items())),
        "direction_counts":dict(sorted(dirs.items())),
        "transitions_per_1000_live_bars":None if not bars_live else 1000*transitions/bars_live,
        "warning_back_per_1000_live_bars":None if not bars_live else 1000*warning_back/bars_live,
        "invalidated_protect":{
            "episodes":inv_eps,
            "reached":inv_protect,
            "reached_pct":pct(inv_protect,inv_eps),
        },
        "completed_realization":{
            "episodes":comp_eps,
            "reached":comp_real,
            "reached_pct":pct(comp_real,comp_eps),
        },
        "realization_persistence":{
            "episodes_with_realization":real_eps,
            "total_entries":real_entries,
            "total_realization_bars":real_bars,
            "max_run_overall":max_real_run,
        },
    }


def markdown(report):
    lines=[
        "# Suite 0.2 — 15-symbol 3D/1W Thesis Management V1.1",
        "",
        "Same capability-aware management semantics on every symbol/horizon. No retuning.",
        "",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        f"- symbols: **{len(report['symbols'])}**",
        "",
        "## Aggregate capability / parity",
        "",
        "| TF | symbols w/ confirms | confirms | mgmt | FULL | INV only | TARGET only | NONE | target cap % | invalid cap % | FULL parity % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,a in report["aggregate"].items():
        c=a["anchor_class_counts"]
        lines.append(
            f"| {tf} | {a['symbols_with_confirms']} | {a['confirms']} | {a['management_episodes']} | {c.get('FULL',0)} | {c.get('INVALIDATION_ONLY',0)} | {c.get('TARGET_ONLY',0)} | {c.get('NONE',0)} | {_fmt(a['target_capable_pct'])} | {_fmt(a['invalidation_capable_pct'])} | {_fmt(a['full_anchor_parity_pct'])} |"
        )

    lines += [
        "",
        "## Aggregate management behavior",
        "",
        "| TF | live bars | CONT % | PROTECT % | REALIZATION % | trans/1000 | warn->CONT/1000 | completed | invalidated | superseded | open-end | inv with PROTECT % | completed with REALIZATION % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,a in report["aggregate"].items():
        p=a["state_pct"];o=a["outcomes"]
        lines.append(
            f"| {tf} | {a['bars_live']} | {_fmt(p.get('CONTINUATION'))} | {_fmt(p.get('PROTECT'))} | {_fmt(p.get('REALIZATION_RISK'))} | {_fmt(a['transitions_per_1000_live_bars'])} | {_fmt(a['warning_back_per_1000_live_bars'])} | {o.get('COMPLETED',0)} | {o.get('INVALIDATED',0)} | {o.get('SUPERSEDED',0)} | {o.get('OPEN_END',0)} | {_fmt(a['invalidated_protect']['reached_pct'])} | {_fmt(a['completed_realization']['reached_pct'])} |"
        )

    lines += [
        "",
        "## Source / direction",
        "",
        "| TF | LONG | SHORT | source counts | REALIZATION episodes | max realization run |",
        "| --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for tf,a in report["aggregate"].items():
        d=a["direction_counts"];rp=a["realization_persistence"]
        lines.append(
            f"| {tf} | {d.get('LONG',0)} | {d.get('SHORT',0)} | `{json.dumps(a['source_counts'],sort_keys=True)}` | {rp['episodes_with_realization']} | {rp['max_run_overall']} |"
        )

    lines += [
        "",
        "## Per-symbol thesis breadth",
        "",
        "| Symbol | 3D confirms | 3D FULL | 1W confirms | 1W FULL |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for symbol in SYMBOLS:
        x=report["symbols"][symbol]
        lines.append(
            f"| {symbol} | {x['3d']['operator_confirm_bars']} | {x['3d']['summary']['anchor_class_counts'].get('FULL',0)} | {x['1w']['operator_confirm_bars']} | {x['1w']['summary']['anchor_class_counts'].get('FULL',0)} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Management begins only at unified PADRÃO CONFIRMA.",
        "- No synthetic anchors.",
        "- FULL-anchor V1 parity is checked per symbol.",
        "- Same V1.1 thresholds/semantics on all 15 symbols.",
        "- 1M remains outside execution management.",
        "- Percentages are capability-aware thesis diagnostics, not profitability claims.",
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

    per_symbol={};meta={}
    for symbol in SYMBOLS:
        datasets,m=_load_symbol(a.data_root,symbol)
        meta[symbol]=m
        per_symbol[symbol]={}
        for tf in TIMEFRAMES:
            per_symbol[symbol][tf]=_compact(
                analyze_v11(tf,datasets,a.tick_size)
            )

    report={
        "metadata":{
            "code_sha":a.code_sha,
            "phase":"F2 high-horizon universe",
            "symbols":list(SYMBOLS),
            "datasets":meta,
        },
        "symbols":per_symbol,
        "aggregate":{
            tf:_aggregate(per_symbol,tf)
            for tf in TIMEFRAMES
        },
    }

    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(
        json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
    )
    md=markdown(report)
    a.output_md.write_text(md+"\n")
    print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

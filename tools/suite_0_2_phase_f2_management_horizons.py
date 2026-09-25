#!/usr/bin/env python3
"""Phase F2 native-horizon Thesis Management V1.1 evidence.

Runs the accepted capability-aware management engine unchanged on:
- 15m
- 1h
- 3d
- 1w

4H / 1D remain accepted reference horizons and are not retuned here.
1M remains macro/cycle awareness and is intentionally excluded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, sha256_file
from tools.suite_0_2_thesis_management_v1_1_evidence import analyze as analyze_v11


TIMEFRAMES=("15m","1h","3d","1w")
ALL_DATASETS=("15m","1h","4h","1d","3d","1w")


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def analyze(tf,datasets,tick):
    x=analyze_v11(tf,datasets,tick)

    invariants={
        "every_confirm_has_management":(
            x["operator_confirm_bars"]==x["management_episodes"]
        ),
        "management_coverage_100":(
            x["management_episode_pct"] in (None,100.0)
        ),
        "full_v1_parity_100":(
            x["full_anchor_v1_parity"]["parity_pct"] in (None,100.0)
        ),
        "full_v1_mismatches_zero":(
            x["full_anchor_v1_parity"]["mismatches"]==0
        ),
    }
    if not all(invariants.values()):
        bad=[k for k,v in invariants.items() if not v]
        raise AssertionError(f"{tf}: Phase F2 invariant failure: {bad}")

    # Keep artifact compact; summaries retain every metric used by this gate.
    x.pop("results",None)
    x["invariants"]=invariants
    return x


def markdown(report):
    lines=[
        "# Suite 0.2 — Phase F2 Thesis Management V1.1 horizon evidence",
        "",
        "Unchanged capability-aware management semantics. No per-horizon retuning.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Capability / parity",
        "",
        "| TF | confirms | mgmt | FULL | INV only | TARGET only | NONE | target cap % | invalid cap % | FULL V1 parity % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"];c=s["anchor_class_counts"]
        lines.append(
            f"| {tf} | {x['operator_confirm_bars']} | {x['management_episodes']} | {c.get('FULL',0)} | {c.get('INVALIDATION_ONLY',0)} | {c.get('TARGET_ONLY',0)} | {c.get('NONE',0)} | {_fmt(s['target_capable_pct'])} | {_fmt(s['invalidation_capable_pct'])} | {_fmt(x['full_anchor_v1_parity']['parity_pct'])} |"
        )

    lines += [
        "",
        "## State / outcome behavior",
        "",
        "| TF | live bars | CONT % | PROTECT % | REALIZATION % | trans/1000 | warn->CONT/1000 | completed | invalidated | superseded | open end | invalidated with PROTECT % | completed with REALIZATION % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"];p=s["state_pct"];o=s["outcomes"]
        lines.append(
            "| {tf} | {live} | {cont} | {prot} | {real} | {tr} | {back} | {comp} | {inv} | {sup} | {open} | {ip} | {cr} |".format(
                tf=tf,
                live=s["bars_live"],
                cont=_fmt(p.get("CONTINUATION")),
                prot=_fmt(p.get("PROTECT")),
                real=_fmt(p.get("REALIZATION_RISK")),
                tr=_fmt(s["transitions_per_1000_live_bars"]),
                back=_fmt(s["warning_back_per_1000_live_bars"]),
                comp=o.get("COMPLETED",0),
                inv=o.get("INVALIDATED",0),
                sup=o.get("SUPERSEDED",0),
                open=o.get("OPEN_END",0),
                ip=_fmt(s["invalidated_protect"]["reached_pct"]),
                cr=_fmt(s["completed_realization"]["reached_pct"]),
            )
        )

    lines += [
        "",
        "## REALIZATION persistence",
        "",
        "| TF | episodes | entries | bars | max run | median episode max run |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        r=x["summary"]["realization_persistence"]
        lines.append(
            f"| {tf} | {r['episodes_with_realization']} | {r['total_entries']} | {r['total_realization_bars']} | {r['max_run_overall']} | {_fmt(r['episode_max_run_distribution']['median'])} |"
        )

    lines += [
        "",
        "## Source / direction",
        "",
        "| TF | LONG | SHORT | source counts |",
        "| --- | ---: | ---: | --- |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"];d=s["direction_counts"]
        lines.append(
            f"| {tf} | {d.get('LONG',0)} | {d.get('SHORT',0)} | `{json.dumps(s['source_counts'],sort_keys=True)}` |"
        )

    lines += [
        "",
        "## Invariants",
        "",
        "| TF | every confirm managed | coverage 100% | FULL V1 parity | mismatches zero |",
        "| --- | --- | --- | --- | --- |",
    ]
    for tf,x in report["timeframes"].items():
        v=x["invariants"]
        lines.append(
            f"| {tf} | {v['every_confirm_has_management']} | {v['management_coverage_100']} | {v['full_v1_parity_100']} | {v['full_v1_mismatches_zero']} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Management begins only from unified PADRÃO CONFIRMA.",
        "- No synthetic target or invalidation is created.",
        "- Missing anchors remain explicit through capability classes.",
        "- FULL-anchor episodes must preserve V1 behavior exactly.",
        "- The same V1.1 state thresholds are used on every tested horizon.",
        "- 1M is intentionally outside execution management.",
        "- Metrics are thesis-behavior diagnostics, not profitability claims.",
        "- No production Pine/default/profile/panel changes.",
        "",
    ]
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",type=Path,required=True)
    ap.add_argument("--symbol",required=True)
    ap.add_argument("--canonical-manifest",type=Path,required=True)
    ap.add_argument("--output-json",type=Path,required=True)
    ap.add_argument("--output-md",type=Path,required=True)
    ap.add_argument("--code-sha",default="unknown")
    ap.add_argument("--tick-size",type=float,default=.01)
    a=ap.parse_args()

    canonical=json.loads(a.canonical_manifest.read_text())
    expected={d["timeframe"]:d for d in canonical["datasets"]}
    symbol=a.symbol.upper();market=canonical.get("market","spot")

    datasets={};meta={}
    for tf in ALL_DATASETS:
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        if not p.is_file():
            raise SystemExit(f"missing dataset: {p}")
        dig=sha256_file(p);exp=expected[tf]
        if dig!=exp["dataset_sha256"]:
            raise SystemExit(f"{symbol} {tf}: SHA mismatch")
        ds=load_dataset(p)
        if len(ds["close"])!=exp["candles"]:
            raise SystemExit(f"{symbol} {tf}: row mismatch")
        datasets[tf]=ds
        meta[tf]={"rows":len(ds["close"]),"sha256":dig}

    report={
        "metadata":{
            "symbol":symbol,
            "code_sha":a.code_sha,
            "phase":"F2",
            "contract":"Capability-aware Thesis Management V1.1",
            "datasets":meta,
        },
        "timeframes":{
            tf:analyze(tf,datasets,a.tick_size)
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

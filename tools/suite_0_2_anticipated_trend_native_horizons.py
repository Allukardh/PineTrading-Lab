#!/usr/bin/env python3
"""Native-horizon validation for the unchanged ANTECIPADO_TREND posture.

Horizons:
- 15m
- 1h
- 3d
- 1w

Reuses the exact accepted OPERATOR_READINESS_V1 paths and the same refined
ANTECIPADO_TREND structural-quality function used on 4H/1D.

No per-horizon tuning.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, sha256_file
from tools.suite_0_2_responsiveness_profile_quality import (
    _projections,
    _trend_early_quality,
)
from tools.suite_0_2_thesis_management_evidence import _build_operator_paths


TIMEFRAMES=("15m","1h","3d","1w")


def _per1000(n,rows):
    return None if not rows else 1000.0*n/rows


def analyze(tf,datasets,tick):
    ctx=_build_operator_paths(tf,datasets,tick)
    projections,path_rows=_projections(ctx)
    trend=_trend_early_quality(ctx,projections,path_rows)
    trend["rows"]=len(ctx["data"]["close"])
    trend["events_per_1000"]=_per1000(trend["events"],trend["rows"])
    return trend


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — ANTECIPADO_TREND native-horizon evidence",
        "",
        "Unchanged early TREND posture. No per-timeframe or per-asset tuning.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Event load",
        "",
        "| TF | rows | events | events/1000 | conversion % | nonconverted | quick nonconverted <=3 % | LONG | SHORT |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        d=x["direction_counts"]
        lines.append(
            f"| {tf} | {x['rows']} | {x['events']} | {_fmt(x['events_per_1000'])} | {_fmt(x['conversion_pct'])} | {x['nonconverted']} | {_fmt(x['quick_nonconverted_le_3_pct_of_nonconverted'])} | {d.get('LONG',0)} | {d.get('SHORT',0)} |"
        )

    lines += [
        "",
        "## Structural quality by opportunity kind",
        "",
        "| TF | kind | events | conversion % | converted HELD/FAKEOUT | converted HELD % | nonconverted HELD/FAKEOUT | nonconverted HELD % | lead bars med | move waiting ATR med |",
        "| --- | --- | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        for kind,g in x["by_kind"].items():
            c=g["converted"];n=g["nonconverted"]
            lines.append(
                f"| {tf} | {kind} | {g['all']['events']} | {_fmt(g['conversion_pct'])} | {c['held']}/{c['fakeout']} | {_fmt(c['held_pct_resolved'])} | {n['held']}/{n['fakeout']} | {_fmt(n['held_pct_resolved'])} | {_fmt(g['bars_saved']['median'])} | {_fmt(g['move_waiting_atr']['median'])} |"
            )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Same ANTECIPADO_TREND contract as the accepted 4H/1D research candidate.",
        "- Conversion is earned only by TREND_OPPORTUNITY_V2.",
        "- HELD/FAKEOUT are retrospective structural diagnostics, not profitability.",
        "- Strict REGIME_REVERSAL is not scored as HELD/FAKEOUT.",
        "- No per-timeframe tuning.",
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
    for tf in ("15m","1h","4h","1d","3d","1w"):
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

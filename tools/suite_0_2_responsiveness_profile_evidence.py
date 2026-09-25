#!/usr/bin/env python3
"""Suite 0.2 responsiveness/profile first-pass evidence.

Profiles are action postures over the accepted OPERATOR_READINESS_V1:
- ANTECIPADO: newly ARMED
- PADRAO: current unified CONFIRMA
- CONFIRMADO: PADRAO + one-bar confirming-source persistence

No internal path is retuned or mutated.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from tools.execution_historical_evidence import distribution, load_dataset, pct, sha256_file
from tools.operator_readiness_reference import from_sample, project
from tools.responsiveness_profile_reference import (
    anticipated_events,
    resolve_anticipated,
    resolve_confirmed,
    standard_events,
)
from tools.suite_0_2_thesis_management_evidence import (
    PATH_NAMES,
    _build_operator_paths,
    _range_anchor,
)


TIMEFRAMES=("4h","1d")


def _dist(values):
    return distribution([float(v) for v in values if v is not None])


def _per1000(n,rows):
    return None if not rows else 1000.0*n/rows


def _projection_series(ctx):
    paths=ctx["paths"]
    projections=[]
    path_rows=[]
    for i in range(len(ctx["data"]["close"])):
        rows={name:from_sample(name,paths[name][i]) for name in PATH_NAMES}
        path_rows.append(rows)
        projections.append(project(rows.values()))
    return projections,path_rows


def _target_for_sources(ctx,bar,direction,sources):
    values=[]
    snaps=ctx["snaps"]
    for source in sources:
        target=None
        if source in {"FROZEN_0_1","TREND_OPPORTUNITY_V2"}:
            target=snaps[bar].destination
        elif source=="RANGE_EARLY_ANY1":
            anchor=_range_anchor(
                bar,direction,ctx["range_frames"][bar],ctx["range_eps"]
            )
            if anchor is not None:
                target=anchor[0]
        if target is not None:
            values.append(float(target))

    if not values:
        return None
    first=values[0]
    tol=1e-9*max(1.0,abs(first),*(abs(x) for x in values))
    if any(abs(x-first)>tol for x in values[1:]):
        return None
    return first


def _room_atr(ctx,bar,direction,sources):
    target=_target_for_sources(ctx,bar,direction,sources)
    atr=ctx["snaps"][bar].atr
    if target is None or atr is None or atr<=0:
        return None
    room=direction*(target-float(ctx["data"]["close"][bar]))/atr
    return room


def _source_key(sources):
    return "+".join(sorted(sources)) if sources else "NONE"


def analyze(tf,datasets,tick):
    ctx=_build_operator_paths(tf,datasets,tick)
    data=ctx["data"];snaps=ctx["snaps"]
    projections,path_rows=_projection_series(ctx)
    rows=len(projections)

    early=anticipated_events(projections)
    standard=standard_events(projections)
    early_res=[resolve_anticipated(e,path_rows) for e in early]
    confirmed_res=[resolve_confirmed(e,projections,path_rows) for e in standard]

    converted=[r for r in early_res if r.converted]
    nonconverted=[r for r in early_res if not r.converted]
    survived=[r for r in confirmed_res if r.survived]
    rejected=[r for r in confirmed_res if not r.survived]

    lead_bars=[r.bars_to_confirm for r in converted]
    lead_disp=[]
    early_room=[]
    standard_room=[]
    confirmed_room=[]
    confirmed_disp=[]

    for r in converted:
        e=r.event
        j=r.confirm_bar
        atr=snaps[e.bar].atr
        if j is not None and atr is not None and atr>0:
            lead_disp.append(
                e.direction*(float(data["close"][j])-float(data["close"][e.bar]))/atr
            )

    for e in early:
        early_room.append(_room_atr(ctx,e.bar,e.direction,e.sources))
    for e in standard:
        standard_room.append(_room_atr(ctx,e.bar,e.direction,e.sources))
    for r in survived:
        ce=r.confirmed_event
        assert ce is not None
        confirmed_room.append(_room_atr(ctx,ce.bar,ce.direction,ce.sources))
        std=r.standard_event
        atr=snaps[std.bar].atr
        if atr is not None and atr>0:
            confirmed_disp.append(
                std.direction*(float(data["close"][ce.bar])-float(data["close"][std.bar]))/atr
            )

    nonconverted_duration=[
        None if r.end_bar is None else r.end_bar-r.event.bar
        for r in nonconverted
    ]
    quick_nonconverted=sum(
        d is not None and d<=3 for d in nonconverted_duration
    )

    early_by_source=defaultdict(lambda:{"events":0,"converted":0})
    for r in early_res:
        k=_source_key(r.event.sources)
        early_by_source[k]["events"]+=1
        early_by_source[k]["converted"]+=int(r.converted)
    for v in early_by_source.values():
        v["conversion_pct"]=pct(v["converted"],v["events"])

    std_by_source=Counter(_source_key(e.sources) for e in standard)
    conf_by_source=Counter(
        _source_key(r.confirmed_event.sources)
        for r in survived if r.confirmed_event is not None
    )

    failure_reasons=Counter(r.reason for r in rejected)

    # Explicit parity lock: PADRAO events are exactly unified confirmations.
    operator_confirm_bars=sum(p.confirm for p in projections)
    if len(standard)!=operator_confirm_bars:
        raise AssertionError("PADRAO event count diverged from operator confirmations")

    return {
        "rows":rows,
        "ANTECIPADO":{
            "events":len(early),
            "events_per_1000":_per1000(len(early),rows),
            "converted_to_padrao":len(converted),
            "conversion_pct":pct(len(converted),len(early)),
            "nonconverted":len(nonconverted),
            "nonconverted_pct":pct(len(nonconverted),len(early)),
            "quick_nonconverted_le_3":quick_nonconverted,
            "quick_nonconverted_pct":pct(quick_nonconverted,len(early)),
            "bars_saved_vs_padrao":_dist(lead_bars),
            "directional_displacement_to_padrao_atr":_dist(lead_disp),
            "remaining_room_atr":_dist(early_room),
            "by_source":dict(sorted(early_by_source.items())),
            "direction_counts":dict(sorted(Counter(
                "LONG" if e.direction==1 else "SHORT" for e in early
            ).items())),
        },
        "PADRAO":{
            "events":len(standard),
            "events_per_1000":_per1000(len(standard),rows),
            "operator_confirm_bars":operator_confirm_bars,
            "exact_parity_pct":pct(len(standard),operator_confirm_bars),
            "remaining_room_atr":_dist(standard_room),
            "by_source":dict(sorted(std_by_source.items())),
            "direction_counts":dict(sorted(Counter(
                "LONG" if e.direction==1 else "SHORT" for e in standard
            ).items())),
        },
        "CONFIRMADO":{
            "standard_events":len(standard),
            "survived":len(survived),
            "survival_pct":pct(len(survived),len(standard)),
            "rejected":len(rejected),
            "rejection_pct":pct(len(rejected),len(standard)),
            "failure_reasons":dict(sorted(failure_reasons.items())),
            "extra_wait_bars":1,
            "directional_displacement_after_padrao_atr":_dist(confirmed_disp),
            "remaining_room_atr":_dist(confirmed_room),
            "by_source":dict(sorted(conf_by_source.items())),
            "direction_counts":dict(sorted(Counter(
                "LONG" if r.confirmed_event.direction==1 else "SHORT"
                for r in survived if r.confirmed_event is not None
            ).items())),
        },
        "internal_paths_mutated":False,
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — Responsiveness profile first-pass evidence",
        "",
        "Action-posture counterfactual over accepted OPERATOR_READINESS_V1. No path thresholds are changed.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Profile event tradeoff",
        "",
        "| TF | ANTECIPADO events | conversion to PADRÃO % | quick nonconverted <=3 % | median bars saved | median move while waiting ATR | PADRÃO events | CONFIRMADO survival % | CONFIRMADO rejects | +1 move ATR median |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        a=x["ANTECIPADO"];p=x["PADRAO"];c=x["CONFIRMADO"]
        lines.append(
            f"| {tf} | {a['events']} | {_fmt(a['conversion_pct'])} | {_fmt(a['quick_nonconverted_pct'])} | {_fmt(a['bars_saved_vs_padrao']['median'])} | {_fmt(a['directional_displacement_to_padrao_atr']['median'])} | {p['events']} | {_fmt(c['survival_pct'])} | {c['rejected']} | {_fmt(c['directional_displacement_after_padrao_atr']['median'])} |"
        )

    lines += [
        "",
        "## Remaining structural room",
        "",
        "| TF | ANTECIPADO room ATR median | PADRÃO room ATR median | CONFIRMADO room ATR median |",
        "| --- | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        lines.append(
            f"| {tf} | {_fmt(x['ANTECIPADO']['remaining_room_atr']['median'])} | {_fmt(x['PADRAO']['remaining_room_atr']['median'])} | {_fmt(x['CONFIRMADO']['remaining_room_atr']['median'])} |"
        )

    lines += [
        "",
        "## Source contribution",
        "",
    ]
    for tf,x in report["timeframes"].items():
        lines += [f"### {tf}","",
                  f"- ANTECIPADO: {json.dumps(x['ANTECIPADO']['by_source'],sort_keys=True)}",
                  f"- PADRÃO: {json.dumps(x['PADRAO']['by_source'],sort_keys=True)}",
                  f"- CONFIRMADO: {json.dumps(x['CONFIRMADO']['by_source'],sort_keys=True)}",
                  f"- CONFIRMADO rejections: {json.dumps(x['CONFIRMADO']['failure_reasons'],sort_keys=True)}",
                  ""]

    lines += [
        "## Guardrails",
        "",
        "- ANTECIPADO means an earlier action posture at newly ARMED; it is not relabeled as historical CONFIRMA.",
        "- Nonconverted ANTECIPADO events are not called losing trades; this first pass measures readiness conversion/churn only.",
        "- PADRÃO is exact parity with accepted unified CONFIRMA.",
        "- CONFIRMADO adds exactly one bar and requires persistence of at least one source that actually confirmed.",
        "- No EMA/ATR/RSI/PSE/pivot threshold is changed.",
        "- No lookahead/backdating.",
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
    for tf in ("4h","1d","1w"):
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        dig=sha256_file(p);exp=expected[tf]
        if dig!=exp["dataset_sha256"]:raise SystemExit(f"{symbol} {tf}: SHA mismatch")
        ds=load_dataset(p)
        if len(ds["close"])!=exp["candles"]:raise SystemExit(f"{symbol} {tf}: row mismatch")
        datasets[tf]=ds;meta[tf]={"rows":len(ds["close"]),"sha256":dig}

    report={
        "metadata":{"symbol":symbol,"code_sha":a.code_sha,"datasets":meta},
        "timeframes":{tf:analyze(tf,datasets,a.tick_size) for tf in TIMEFRAMES},
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    md=markdown(report);a.output_md.write_text(md+"\n");print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

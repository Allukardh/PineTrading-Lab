#!/usr/bin/env python3
"""Validate OPERATOR_READINESS_V1 over the three accepted independent paths.

The projection is stateless and research-only. Internal path outputs are
computed exactly as their accepted baselines and never mutated.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import build_context_dirs, load_dataset, pct, sha256_file
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.execution_state_reference import Readiness
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.operator_readiness_reference import OperatorReadiness, from_sample, project
from tools.opportunity_episode_reference import detect_episodes
from tools.opportunity_execution_counterfactual import OpportunityKind, build_opportunity_frames
from tools.opportunity_readiness_reference import calculate_opportunity_readiness
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.range_rotation_opportunity_reference import RangeIntegrationVariant, build_range_opportunity_frames
from tools.range_rotation_readiness_reference import RangeReadinessVariant, calculate_range_readiness
from tools.range_rotation_reference import RangeTrigger, detect_range_rotations
from tools.rsi_state_reference import calculate as calculate_rsi


TIMEFRAMES=("4h","1d")
PATH_NAMES=("FROZEN_0_1","TREND_OPPORTUNITY_V2","RANGE_EARLY_ANY1")
EXAMPLE_LIMIT=10


def _per1000(n,rows):
    return None if not rows else n*1000.0/rows


def _time(v):
    try:return v.isoformat()
    except Exception:return str(v)


def _dir(d):
    return "LONG" if d==1 else "SHORT" if d==-1 else "NONE"


def _path_state(sample):
    return {
        "readiness":sample.result.state.readiness.name,
        "direction":_dir(sample.result.state.direction),
        "confirm":bool(sample.result.events.confirm),
    }


def _projection_row(i,data,projection,paths,locs,trend_frames,range_frames):
    return {
        "bar":i,
        "time":_time(data["open_time"][i]),
        "close":float(data["close"][i]),
        "projection":{
            "readiness":projection.readiness.value,
            "direction":_dir(projection.direction),
            "conflict":projection.conflict,
            "confirm":projection.confirm,
            "active_sources":list(projection.active_sources),
            "selected_sources":list(projection.selected_sources),
            "confirming_sources":list(projection.confirming_sources),
            "suppressed_confirm_sources":list(projection.suppressed_confirm_sources),
        },
        "frozen_location":locs[i].name,
        "paths":{name:_path_state(paths[name][i]) for name in PATH_NAMES},
        "trend_frame":{
            "kind":trend_frames[i].kind.name,
            "stage":trend_frames[i].stage.name,
            "direction":_dir(trend_frames[i].direction),
            "source_bar":trend_frames[i].source_bar,
        },
        "range_frame":{
            "kind":range_frames[i].kind.name,
            "stage":range_frames[i].stage.name,
            "direction":_dir(range_frames[i].direction),
            "source_bar":range_frames[i].source_bar,
        },
    }


def analyze(tf,datasets,tick):
    data=datasets[tf]
    snaps=[]
    Kernel(
        to_mm_candles(data),
        to_mm_candles(datasets[CONTEXT_TF[tf]]),
        to_mm_candles(datasets["1d"]),
        to_mm_candles(datasets["1w"]),
        tf,tick=tick
    ).run(integration_rows=snaps,emit_audit=False)

    locs=build_market_locations(snaps)
    rsi_cache={k:calculate_rsi(v["close"]) for k,v in datasets.items()}
    ctx=build_context_dirs(tf,datasets,rsi_cache)
    bars=[
        ExecutionResearchBar(
            float(o),float(h),float(l),float(c),float(v),
            s.map_dir,loc,ctx[i],
            s.thesis_invalidated,s.structural_conflict,True
        )
        for i,(o,h,l,c,v,s,loc) in enumerate(zip(
            data["open"],data["high"],data["low"],data["close"],data["volume"],snaps,locs
        ))
    ]

    frozen=calculate_execution(bars)

    trend_eps=detect_episodes(snaps,data["high"],data["low"])
    pb=[ParticipationBar(float(h),float(l),float(c),float(v))
        for h,l,c,v in zip(data["high"],data["low"],data["close"],data["volume"])]
    canonical_pse=calculate_participation(pb,[s.map_dir for s in snaps])
    trend_frames=build_opportunity_frames(trend_eps,snaps,data["close"],locs,canonical_pse)
    trend=calculate_opportunity_readiness(bars,trend_frames)

    range_eps=[
        e for e in detect_range_rotations(snaps,data["high"],data["low"],data["close"])
        if e.trigger==RangeTrigger.EDGE_REJECTION
    ]
    range_frames=build_range_opportunity_frames(
        range_eps,snaps,data["high"],data["low"],data["close"],
        variant=RangeIntegrationVariant.ALL_EDGE
    )
    range_samples=calculate_range_readiness(
        bars,range_frames,variant=RangeReadinessVariant.EARLY_ANY1
    )

    paths={
        "FROZEN_0_1":frozen,
        "TREND_OPPORTUNITY_V2":trend,
        "RANGE_EARLY_ANY1":range_samples,
    }

    rows=len(bars)
    operator_states=Counter()
    active_source_counts=Counter()
    selected_source_counts=Counter()
    confirming_source_counts=Counter()
    selected_context_counts=Counter()

    single_active=single_parity_mismatch=0
    same_dir_multi=0
    fresh_over_aligned=0
    fresh_over_aligned_surface_ok=0
    conflict_bars=0
    conflict_with_raw_confirm=0

    raw_confirm_events=0
    raw_confirm_bars=0
    operator_confirms=0
    collapsed_same_bar_confirm_events=0
    suppressed_confirm_events_by_conflict=0
    opposite_same_bar_confirm_bars=0

    conflict_examples=[]
    fresh_examples=[]
    multi_confirm_examples=[]

    for i in range(rows):
        inputs=[from_sample(name,paths[name][i]) for name in PATH_NAMES]
        p=project(inputs)
        operator_states[p.readiness.value]+=1
        for x in p.active_sources:active_source_counts[x]+=1
        for x in p.selected_sources:selected_source_counts[x]+=1
        for x in p.confirming_sources:confirming_source_counts[x]+=1

        if "FROZEN_0_1" in p.selected_sources:
            selected_context_counts[f"FROZEN_0_1/{locs[i].name}"]+=1
        if "TREND_OPPORTUNITY_V2" in p.selected_sources:
            selected_context_counts[f"TREND_OPPORTUNITY_V2/{trend_frames[i].kind.name}"]+=1
        if "RANGE_EARLY_ANY1" in p.selected_sources:
            selected_context_counts["RANGE_EARLY_ANY1/RANGE_ROTATION"]+=1

        active=[x for x in inputs if x.readiness!=Readiness.WAIT]
        if len(active)==1:
            single_active+=1
            a=active[0]
            if not (
                p.readiness.value==a.readiness.name
                and p.direction==a.direction
                and not p.conflict
            ):
                single_parity_mismatch+=1

        dirs={x.direction for x in active}
        if len(active)>=2 and len(dirs)==1:
            same_dir_multi+=1
            has_aligned=any(x.readiness==Readiness.ALIGNED for x in active)
            has_fresh=any(
                x.readiness in {Readiness.PREP,Readiness.ARMED,Readiness.CONFIRMED}
                for x in active
            )
            if has_aligned and has_fresh:
                fresh_over_aligned+=1
                if p.readiness in {
                    OperatorReadiness.PREP,
                    OperatorReadiness.ARMED,
                    OperatorReadiness.CONFIRMED,
                }:
                    fresh_over_aligned_surface_ok+=1
                if len(fresh_examples)<EXAMPLE_LIMIT:
                    fresh_examples.append(
                        _projection_row(i,data,p,paths,locs,trend_frames,range_frames)
                    )

        if p.conflict:
            conflict_bars+=1
            if p.confirming_sources:
                conflict_with_raw_confirm+=1
                suppressed_confirm_events_by_conflict+=len(p.confirming_sources)
            if len(conflict_examples)<EXAMPLE_LIMIT:
                conflict_examples.append(
                    _projection_row(i,data,p,paths,locs,trend_frames,range_frames)
                )

        confirms=[x for x in inputs if x.confirm]
        raw_confirm_events+=len(confirms)
        if confirms:
            raw_confirm_bars+=1
        if p.confirm:
            operator_confirms+=1

        if len(confirms)>=2:
            confirm_dirs={x.direction for x in confirms}
            if len(confirm_dirs)==1 and not p.conflict:
                collapsed_same_bar_confirm_events+=len(confirms)-1
            else:
                opposite_same_bar_confirm_bars+=1
            if len(multi_confirm_examples)<EXAMPLE_LIMIT:
                multi_confirm_examples.append(
                    _projection_row(i,data,p,paths,locs,trend_frames,range_frames)
                )

    return {
        "rows":rows,
        "operator_state_counts":dict(sorted(operator_states.items())),
        "single_active":{
            "bars":single_active,
            "parity_mismatches":single_parity_mismatch,
            "parity_pct":pct(single_active-single_parity_mismatch,single_active),
        },
        "same_direction_multi_active":{
            "bars":same_dir_multi,
            "fresh_over_background_aligned_bars":fresh_over_aligned,
            "fresh_surface_ok_bars":fresh_over_aligned_surface_ok,
            "fresh_surface_ok_pct":pct(fresh_over_aligned_surface_ok,fresh_over_aligned),
        },
        "conflicts":{
            "bars":conflict_bars,
            "bars_per_1000":_per1000(conflict_bars,rows),
            "bars_with_raw_confirm":conflict_with_raw_confirm,
            "suppressed_raw_confirm_events":suppressed_confirm_events_by_conflict,
        },
        "confirm_projection":{
            "raw_confirm_events":raw_confirm_events,
            "raw_confirm_bars":raw_confirm_bars,
            "operator_confirm_events":operator_confirms,
            "collapsed_same_bar_same_direction_extra_events":collapsed_same_bar_confirm_events,
            "opposite_same_bar_multi_confirm_bars":opposite_same_bar_confirm_bars,
            "preserved_confirm_bar_pct":pct(operator_confirms,raw_confirm_bars),
        },
        "source_contribution":{
            "active_source_bar_counts":dict(sorted(active_source_counts.items())),
            "selected_source_bar_counts":dict(sorted(selected_source_counts.items())),
            "raw_confirm_source_counts":dict(sorted(confirming_source_counts.items())),
            "selected_context_counts":dict(sorted(selected_context_counts.items())),
        },
        "examples":{
            "opposite_direction_conflicts":conflict_examples,
            "fresh_setup_over_background_aligned":fresh_examples,
            "same_bar_multi_confirm":multi_confirm_examples,
        },
        "internal_paths_mutated":False,
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — OPERATOR_READINESS_V1 evidence",
        "",
        "Stateless operator projection over three independently computed accepted paths.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Projection integrity",
        "",
        "| TF | single-active bars | parity % | same-dir multi-active | fresh-over-ALIGNED | fresh surfaced % | conflict bars | conflict/1000 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        lines.append(
            f"| {tf} | {x['single_active']['bars']} | {_fmt(x['single_active']['parity_pct'])} | {x['same_direction_multi_active']['bars']} | {x['same_direction_multi_active']['fresh_over_background_aligned_bars']} | {_fmt(x['same_direction_multi_active']['fresh_surface_ok_pct'])} | {x['conflicts']['bars']} | {_fmt(x['conflicts']['bars_per_1000'])} |"
        )

    lines += [
        "",
        "## Confirmation projection",
        "",
        "| TF | raw confirm events | raw confirm bars | operator confirms | same-bar collapsed extras | conflicts suppressing raw confirms | preserved confirm bars % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        c=x["confirm_projection"]
        lines.append(
            f"| {tf} | {c['raw_confirm_events']} | {c['raw_confirm_bars']} | {c['operator_confirm_events']} | {c['collapsed_same_bar_same_direction_extra_events']} | {x['conflicts']['suppressed_raw_confirm_events']} | {_fmt(c['preserved_confirm_bar_pct'])} |"
        )

    lines += [
        "",
        "## Operator state counts",
        "",
        "| TF | WAIT | PREP | ARMED | CONFIRMED | ALIGNED | CONFLICT |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        c=x["operator_state_counts"]
        lines.append(
            f"| {tf} | {c.get('WAIT',0)} | {c.get('PREP',0)} | {c.get('ARMED',0)} | {c.get('CONFIRMED',0)} | {c.get('ALIGNED',0)} | {c.get('CONFLICT',0)} |"
        )

    lines += [
        "",
        "## Selected-source contribution",
        "",
        "| TF | frozen selected bars | trend selected bars | range selected bars | frozen raw confirms | trend raw confirms | range raw confirms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["source_contribution"]
        sel=s["selected_source_bar_counts"]; conf=s["raw_confirm_source_counts"]
        lines.append(
            f"| {tf} | {sel.get('FROZEN_0_1',0)} | {sel.get('TREND_OPPORTUNITY_V2',0)} | {sel.get('RANGE_EARLY_ANY1',0)} | {conf.get('FROZEN_0_1',0)} | {conf.get('TREND_OPPORTUNITY_V2',0)} | {conf.get('RANGE_EARLY_ANY1',0)} |"
        )

    lines += [
        "",
        "## Representative cases",
        "",
        "| TF | conflict examples | fresh-over-ALIGNED examples | same-bar multi-confirm examples |",
        "| --- | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        e=x["examples"]
        lines.append(
            f"| {tf} | {len(e['opposite_direction_conflicts'])} | {len(e['fresh_setup_over_background_aligned'])} | {len(e['same_bar_multi_confirm'])} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Internal paths are computed independently and are not mutated.",
        "- Operational urgency is CONFIRMED > ARMED > PREP > ALIGNED > WAIT.",
        "- Opposite active directions produce non-actionable CONFLICT rather than choosing a winner.",
        "- Same-bar same-direction multiple confirms collapse to one operator event while retaining sources.",
        "- Different-bar confirmations are not deduplicated merely by proximity.",
        "- Strength arbitration is outside this experiment.",
        "- No production Pine/default/profile changes.",
        "",
    ]
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",type=Path,required=True)
    ap.add_argument("--symbol",default="BTCUSDT")
    ap.add_argument("--canonical-manifest",type=Path,required=True)
    ap.add_argument("--output-json",type=Path,required=True)
    ap.add_argument("--output-md",type=Path,required=True)
    ap.add_argument("--code-sha",default="unknown")
    ap.add_argument("--tick-size",type=float,default=.01)
    a=ap.parse_args()

    canonical=json.loads(a.canonical_manifest.read_text())
    expected={d["timeframe"]:d for d in canonical["datasets"]}
    symbol=a.symbol.upper(); market=canonical.get("market","spot")
    datasets={};meta={}
    for tf in ("4h","1d","1w"):
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        dig=sha256_file(p);exp=expected[tf]
        if dig!=exp["dataset_sha256"]:raise SystemExit(f"{symbol} {tf}: SHA mismatch")
        ds=load_dataset(p)
        if len(ds["close"])!=exp["candles"]:raise SystemExit(f"{symbol} {tf}: row mismatch")
        datasets[tf]=ds;meta[tf]={"rows":len(ds["close"]),"sha256":dig}

    report={
        "metadata":{
            "symbol":symbol,
            "code_sha":a.code_sha,
            "datasets":meta,
            "frozen_execution_promotion":"a7557df2d0142441ea782dba4b8c3f95ebc38371",
            "accepted_trend_opportunity_head":"329cdcac039f11cd1a81bf9138cfe67ab83a142f",
            "accepted_range_readiness_head":"bac1d0374a141dfe80fb1307540e7ef84682ddc8",
            "operator_readiness_preregistration":"e1a44d5e7d31c6b5c9c027eebc94c040206c95c6",
        },
        "timeframes":{tf:analyze(tf,datasets,a.tick_size) for tf in TIMEFRAMES},
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report);a.output_md.write_text(md+"\n");print(md)
    return 0

if __name__=="__main__":
    raise SystemExit(main())

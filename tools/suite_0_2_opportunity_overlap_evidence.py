#!/usr/bin/env python3
"""Measure overlap/conflict across the three accepted research paths.

Paths:
1. frozen Execution 0.1 — correction/retest/reclaim
2. accepted Opportunity v2 trend path — breakout/reacceleration/reversal
3. accepted RANGE_ROTATION EARLY_ANY1

This is observational only. It defines no arbitration priority and mutates no
accepted path.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import build_context_dirs, load_dataset, pct, sha256_file
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.execution_state_reference import RELEVANT_LOCATIONS, Readiness
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.opportunity_episode_reference import detect_episodes
from tools.opportunity_execution_counterfactual import (
    OpportunityKind,
    OpportunityStage,
    build_opportunity_frames,
)
from tools.opportunity_overlap_reference import (
    confirm_events,
    match_near_confirms,
    match_near_opposite_confirms,
    pairwise_overlap,
    readiness_active,
    triple_overlap,
)
from tools.opportunity_readiness_reference import calculate_opportunity_readiness
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.range_rotation_opportunity_reference import (
    RangeIntegrationVariant,
    build_range_opportunity_frames,
)
from tools.range_rotation_readiness_reference import (
    RangeReadinessVariant,
    calculate_range_readiness,
)
from tools.range_rotation_reference import RangeTrigger, detect_range_rotations
from tools.rsi_state_reference import calculate as calculate_rsi


TIMEFRAMES=("4h","1d")
EXAMPLE_LIMIT=10


def _per1000(n,rows):
    return None if not rows else n*1000.0/rows


def _event_counts(samples):
    c=Counter()
    for s in samples:
        e=s.result.events
        c["PREPARING_ENTERED"]+=int(e.preparing_entered)
        c["ARMED_ENTERED"]+=int(e.armed_entered)
        c["CONFIRM"]+=int(e.confirm)
        c["CANCELED"]+=int(e.canceled)
    return c


def _path_summary(samples,rows):
    ev=_event_counts(samples)
    active=sum(readiness_active(s) for s in samples)
    armed=sum(s.result.state.readiness>=Readiness.ARMED for s in samples)
    return {
        "active_bars":active,
        "active_pct":pct(active,rows),
        "armed_or_better_bars":armed,
        "armed_or_better_pct":pct(armed,rows),
        "events":dict(sorted(ev.items())),
        "events_per_1000":{k:_per1000(v,rows) for k,v in sorted(ev.items())},
    }


def _pair_summary(a,b,rows):
    x=pairwise_overlap(a,b)
    ae=confirm_events(a); be=confirm_events(b)
    same=match_near_confirms(ae,be,window_bars=3)
    opp=match_near_opposite_confirms(ae,be,window_bars=3)
    combos=Counter(
        f"{sa.result.state.readiness.name}__{sb.result.state.readiness.name}"
        for sa,sb in zip(a,b)
        if readiness_active(sa) and readiness_active(sb)
    )
    x.update({
        "both_active_pct":pct(x["both_active_bars"],rows),
        "same_direction_active_pct":pct(x["same_direction_active_bars"],rows),
        "opposite_direction_active_pct":pct(x["opposite_direction_active_bars"],rows),
        "state_combination_counts":dict(sorted(combos.items())),
        "near_same_direction_confirms_3":len(same),
        "near_opposite_direction_confirms_3":len(opp),
        "near_same_distance_counts":dict(sorted(Counter(m.distance_bars for m in same).items())),
        "near_opposite_distance_counts":dict(sorted(Counter(m.distance_bars for m in opp).items())),
    })
    return x,same,opp


def _time(v):
    try:
        return v.isoformat()
    except Exception:
        return str(v)


def _dir_name(d):
    return "LONG" if d==1 else "SHORT" if d==-1 else "NONE"


def _sample_state(s):
    return {
        "readiness":s.result.state.readiness.name,
        "direction":_dir_name(s.result.state.direction),
        "confirm":bool(s.result.events.confirm),
    }


def _frame_state(f):
    return {
        "kind":f.kind.name,
        "stage":f.stage.name,
        "direction":_dir_name(f.direction),
        "source_bar":f.source_bar,
    }


def _example(i,data,locations,baseline,trend,range_samples,trend_frames,range_frames):
    return {
        "bar":i,
        "time":_time(data["open_time"][i]),
        "close":float(data["close"][i]),
        "baseline_location":locations[i].name,
        "frozen_0_1":_sample_state(baseline[i]),
        "trend_opportunity":_sample_state(trend[i]),
        "range_rotation":_sample_state(range_samples[i]),
        "trend_frame":_frame_state(trend_frames[i]),
        "range_frame":_frame_state(range_frames[i]),
    }


def _collect_examples(data,locations,baseline,trend,range_samples,trend_frames,range_frames):
    same=[]; opposite=[]; simultaneous=[]
    rows=len(baseline)
    for i in range(rows):
        paths=[baseline[i],trend[i],range_samples[i]]
        active=[p for p in paths if readiness_active(p)]
        dirs=[p.result.state.direction for p in active if p.result.state.direction in (-1,1)]
        if len(active)>=2 and len(set(dirs))==1 and dirs and len(same)<EXAMPLE_LIMIT:
            same.append(_example(i,data,locations,baseline,trend,range_samples,trend_frames,range_frames))
        if len(active)>=2 and len(set(dirs))>1 and len(opposite)<EXAMPLE_LIMIT:
            opposite.append(_example(i,data,locations,baseline,trend,range_samples,trend_frames,range_frames))
        confirms=[p for p in paths if p.result.events.confirm]
        if len(confirms)>=2 and len(simultaneous)<EXAMPLE_LIMIT:
            simultaneous.append(_example(i,data,locations,baseline,trend,range_samples,trend_frames,range_frames))
    return {
        "same_direction_multi_active":same,
        "opposite_direction_conflicts":opposite,
        "simultaneous_confirms":simultaneous,
    }


def _match_examples(matches,a_name,b_name,data,limit=EXAMPLE_LIMIT):
    return [
        {
            "path_a":a_name,
            "path_b":b_name,
            "a_bar":m.a_bar,
            "b_bar":m.b_bar,
            "direction":_dir_name(m.direction),
            "distance_bars":m.distance_bars,
            "a_time":_time(data["open_time"][m.a_bar]),
            "b_time":_time(data["open_time"][m.b_bar]),
            "a_close":float(data["close"][m.a_bar]),
            "b_close":float(data["close"][m.b_bar]),
        }
        for m in matches[:limit]
    ]


def analyze(tf,datasets,tick):
    data=datasets[tf]
    snaps=[]
    Kernel(
        to_mm_candles(data),
        to_mm_candles(datasets[CONTEXT_TF[tf]]),
        to_mm_candles(datasets["1d"]),
        to_mm_candles(datasets["1w"]),
        tf,
        tick=tick,
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

    # Path 1: frozen Execution 0.1.
    baseline=calculate_execution(bars)

    # Path 2: accepted trend Opportunity v2, unchanged.
    trend_episodes=detect_episodes(snaps,data["high"],data["low"])
    pb=[
        ParticipationBar(float(h),float(l),float(c),float(v))
        for h,l,c,v in zip(data["high"],data["low"],data["close"],data["volume"])
    ]
    canonical_pse=calculate_participation(pb,[s.map_dir for s in snaps])
    trend_frames=build_opportunity_frames(
        trend_episodes,snaps,data["close"],locs,canonical_pse
    )
    trend=calculate_opportunity_readiness(bars,trend_frames)

    # Path 3: accepted RANGE_ROTATION EARLY_ANY1, unchanged.
    range_eps=[
        e for e in detect_range_rotations(
            snaps,data["high"],data["low"],data["close"]
        )
        if e.trigger==RangeTrigger.EDGE_REJECTION
    ]
    range_frames=build_range_opportunity_frames(
        range_eps,snaps,data["high"],data["low"],data["close"],
        variant=RangeIntegrationVariant.ALL_EDGE,
    )
    range_samples=calculate_range_readiness(
        bars,range_frames,variant=RangeReadinessVariant.EARLY_ANY1
    )

    paths={
        "FROZEN_0_1":baseline,
        "TREND_OPPORTUNITY_V2":trend,
        "RANGE_EARLY_ANY1":range_samples,
    }
    rows=len(bars)

    pair_data={}
    near_examples={}
    pairs=[
        ("FROZEN_0_1","TREND_OPPORTUNITY_V2"),
        ("FROZEN_0_1","RANGE_EARLY_ANY1"),
        ("TREND_OPPORTUNITY_V2","RANGE_EARLY_ANY1"),
    ]
    for a,b in pairs:
        summary,same,opp=_pair_summary(paths[a],paths[b],rows)
        key=f"{a}__{b}"
        pair_data[key]=summary
        near_examples[key]={
            "same_direction_confirm_matches":_match_examples(same,a,b,data),
            "opposite_direction_confirm_matches":_match_examples(opp,a,b,data),
        }

    tr=triple_overlap(baseline,trend,range_samples)
    tr.update({
        "all_active_pct":pct(tr["all_active_bars"],rows),
        "direction_conflict_pct":pct(tr["direction_conflict_bars"],rows),
    })

    trend_frame_active=[
        f.kind!=OpportunityKind.NONE and f.stage!=OpportunityStage.NONE
        for f in trend_frames
    ]
    range_frame_active=[
        f.kind==OpportunityKind.RANGE_ROTATION and f.stage!=OpportunityStage.NONE
        for f in range_frames
    ]
    trend_sources={
        i for i,f in enumerate(trend_frames)
        if trend_frame_active[i] and f.source_bar==i
    }
    range_sources={
        i for i,f in enumerate(range_frames)
        if range_frame_active[i] and f.source_bar==i
    }
    frame_overlap=sum(t and r for t,r in zip(trend_frame_active,range_frame_active))
    frame_same=sum(
        t and r and trend_frames[i].direction==range_frames[i].direction
        for i,(t,r) in enumerate(zip(trend_frame_active,range_frame_active))
    )
    frame_opp=sum(
        t and r and trend_frames[i].direction==-range_frames[i].direction
        for i,(t,r) in enumerate(zip(trend_frame_active,range_frame_active))
    )
    exact_sources=trend_sources & range_sources
    range_source_inside_trend=sum(trend_frame_active[i] for i in range_sources)
    trend_source_inside_range=sum(range_frame_active[i] for i in trend_sources)

    baseline_relevant=[loc in RELEVANT_LOCATIONS for loc in locs]
    context_overlap={
        "trend_frame_active_bars":sum(trend_frame_active),
        "range_frame_active_bars":sum(range_frame_active),
        "trend_range_frame_overlap_bars":frame_overlap,
        "trend_range_frame_same_direction_bars":frame_same,
        "trend_range_frame_opposite_direction_bars":frame_opp,
        "exact_source_source_overlap_count":len(exact_sources),
        "range_sources":len(range_sources),
        "trend_sources":len(trend_sources),
        "range_source_inside_trend_frame_count":range_source_inside_trend,
        "trend_source_inside_range_frame_count":trend_source_inside_range,
        "trend_frame_on_frozen_relevant_location_bars":sum(
            t and br for t,br in zip(trend_frame_active,baseline_relevant)
        ),
        "range_frame_on_frozen_relevant_location_bars":sum(
            r and br for r,br in zip(range_frame_active,baseline_relevant)
        ),
        "frozen_relevant_location_bars":sum(baseline_relevant),
    }
    for k in list(context_overlap):
        if k.endswith("_bars") and k!="frozen_relevant_location_bars":
            context_overlap[k+"_pct_of_all"]=pct(context_overlap[k],rows)

    examples=_collect_examples(
        data,locs,baseline,trend,range_samples,trend_frames,range_frames
    )
    examples["near_confirm_pairs"]=near_examples
    examples["source_overlap"]=[
        _example(i,data,locs,baseline,trend,range_samples,trend_frames,range_frames)
        for i in sorted(
            exact_sources |
            {i for i in range_sources if trend_frame_active[i]} |
            {i for i in trend_sources if range_frame_active[i]}
        )[:EXAMPLE_LIMIT]
    ]

    return {
        "rows":rows,
        "path_load":{
            name:_path_summary(samples,rows)
            for name,samples in paths.items()
        },
        "pairwise_readiness_overlap":pair_data,
        "triple_readiness_overlap":tr,
        "frame_source_overlap":context_overlap,
        "examples":examples,
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — Opportunity path overlap / arbitration evidence",
        "",
        "Observational only. No arbitration policy is encoded here.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Path load",
        "",
        "| TF | path | active bars % | armed+ bars % | CONFIRMA | CONFIRMA/1000 | CANCEL/1000 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,item in report["timeframes"].items():
        for name,x in item["path_load"].items():
            lines.append(
                f"| {tf} | {name} | {_fmt(x['active_pct'])} | {_fmt(x['armed_or_better_pct'])} | {x['events'].get('CONFIRM',0)} | {_fmt(x['events_per_1000'].get('CONFIRM'))} | {_fmt(x['events_per_1000'].get('CANCELED'))} |"
            )

    lines += [
        "",
        "## Pairwise readiness overlap",
        "",
        "| TF | pair | both active | same dir | opposite dir | both armed+ | simultaneous confirms | near same-dir confirms ±3 | near opposite confirms ±3 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,item in report["timeframes"].items():
        for name,x in item["pairwise_readiness_overlap"].items():
            lines.append(
                f"| {tf} | {name} | {x['both_active_bars']} | {x['same_direction_active_bars']} | {x['opposite_direction_active_bars']} | {x['both_armed_or_better_bars']} | {x['simultaneous_confirms']} | {x['near_same_direction_confirms_3']} | {x['near_opposite_direction_confirms_3']} |"
            )

    lines += [
        "",
        "## Context/source overlap",
        "",
        "| TF | trend-range frame overlap | same dir | opposite dir | exact source/source | range source inside trend frame | trend source inside range frame | trend frame on frozen relevant | range frame on frozen relevant |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,item in report["timeframes"].items():
        x=item["frame_source_overlap"]
        lines.append(
            f"| {tf} | {x['trend_range_frame_overlap_bars']} | {x['trend_range_frame_same_direction_bars']} | {x['trend_range_frame_opposite_direction_bars']} | {x['exact_source_source_overlap_count']} | {x['range_source_inside_trend_frame_count']} | {x['trend_source_inside_range_frame_count']} | {x['trend_frame_on_frozen_relevant_location_bars']} | {x['range_frame_on_frozen_relevant_location_bars']} |"
        )

    lines += [
        "",
        "## Representative-case counts",
        "",
        "| TF | same-direction multi-active examples | opposite-direction conflict examples | simultaneous-confirm examples | source-overlap examples |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for tf,item in report["timeframes"].items():
        e=item["examples"]
        lines.append(
            f"| {tf} | {len(e['same_direction_multi_active'])} | {len(e['opposite_direction_conflicts'])} | {len(e['simultaneous_confirms'])} | {len(e['source_overlap'])} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- The three accepted paths are computed independently.",
        "- This report defines no winner/priority/arbitration rule.",
        "- Non-WAIT overlap and ARMED+ overlap are reported separately.",
        "- Same-direction confirmations within ±3 bars are treated as possible duplicates, not automatically merged.",
        "- Opposite-direction confirmations within ±3 bars are treated as conflict evidence, not automatically canceled.",
        "- Frame/source overlap is separate from readiness overlap.",
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
    datasets={}; meta={}
    for tf in ("4h","1d","1w"):
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        dig=sha256_file(p); exp=expected[tf]
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
            "frozen_execution_promotion":"a7557df2d0142441ea782dba4b8c3f95ebc38371",
            "accepted_trend_opportunity_head":"329cdcac039f11cd1a81bf9138cfe67ab83a142f",
            "accepted_range_readiness_head":"bac1d0374a141dfe80fb1307540e7ef84682ddc8",
        },
        "timeframes":{
            tf:analyze(tf,datasets,a.tick_size)
            for tf in TIMEFRAMES
        },
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report); a.output_md.write_text(md+"\n"); print(md)
    return 0

if __name__=="__main__":
    raise SystemExit(main())

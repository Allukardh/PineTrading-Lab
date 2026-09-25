#!/usr/bin/env python3
"""Native-horizon robustness for accepted Suite 0.2 research semantics.

Unchanged paths:
- frozen Execution 0.1
- Opportunity v2 trend
- RANGE_ROTATION EARLY_ANY1
- OPERATOR_READINESS_V1

Horizons: 15m / 1h / 3d / 1w.

No tuning or production changes.
"""
from __future__ import annotations

import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import build_context_dirs,distribution,load_dataset,pct,sha256_file
from tools.execution_integrated_evidence import build_market_locations,to_mm_candles
from tools.execution_state_reference import Readiness
from tools.market_map_offline_core import CONTEXT_TF,IntegrationSnapshot,Kernel
from tools.operator_readiness_reference import OperatorReadiness,from_sample,project
from tools.opportunity_episode_reference import BreakContext,OpportunityType,detect_episodes
from tools.opportunity_execution_counterfactual import OpportunityKind,OpportunityStage,build_opportunity_frames
from tools.opportunity_outcome_reference import CandidateOutcome,classify_all
from tools.opportunity_readiness_reference import calculate_opportunity_readiness
from tools.participation_reference import ParticipationBar,calculate as calculate_participation
from tools.range_rotation_opportunity_reference import RangeIntegrationVariant,build_range_opportunity_frames
from tools.range_rotation_readiness_reference import RangeReadinessVariant,calculate_range_readiness
from tools.range_rotation_reference import RangeOutcome,RangeTrigger,classify_range_rotation,detect_range_rotations
from tools.rsi_state_reference import calculate as calculate_rsi


TIMEFRAMES=("15m","1h","3d","1w")
TF_MINUTES={"15m":15,"1h":60,"3d":3*24*60,"1w":7*24*60,"1M":30*24*60}


def _per1000(n,rows): return None if not rows else n*1000.0/rows
def _fmt(x,d=2): return "n/a" if x is None else f"{x:.{d}f}"


def _event_counts(samples):
    c=Counter()
    for s in samples:
        e=s.result.events
        c["PREPARING_ENTERED"]+=int(e.preparing_entered)
        c["ARMED_ENTERED"]+=int(e.armed_entered)
        c["CONFIRM"]+=int(e.confirm)
        c["CANCELED"]+=int(e.canceled)
    return c


def _event_load(samples,rows):
    c=_event_counts(samples)
    return {
        "events":dict(sorted(c.items())),
        "per_1000":{k:_per1000(v,rows) for k,v in sorted(c.items())},
    }


def _logical_kind(e):
    if e.opportunity_type==OpportunityType.REACCELERATION:
        return OpportunityKind.REACCELERATION
    if e.opportunity_type==OpportunityType.REGIME_REVERSAL:
        return OpportunityKind.REGIME_REVERSAL
    if (
        e.opportunity_type==OpportunityType.BREAKOUT_CANDIDATE
        and e.break_context in {BreakContext.FRESH_EXPANSION.value,BreakContext.OTHER.value}
    ):
        return OpportunityKind.BREAKOUT_EXPANSION
    return None


def _trend_metrics(episodes,outcomes,frames,samples,rows,tf):
    candidates=defaultdict(list)
    source_map={}
    for e in episodes:
        k=_logical_kind(e)
        if k is None: continue
        candidates[k.name].append(e)
        source_map.setdefault((k.name,e.confirmation_bar,e.direction),e)

    cand_outcomes={}
    for kind,eps in candidates.items():
        cand_outcomes[kind]=dict(sorted(Counter(outcomes[e.episode_id].outcome.value for e in eps).items()))

    confirms=Counter()
    confirm_outcomes=defaultdict(Counter)
    latency=defaultdict(list)
    unmapped=0
    directions=Counter()

    for i,s in enumerate(samples):
        if not s.result.events.confirm: continue
        f=frames[i]
        kind=f.kind.name
        confirms[kind]+=1
        directions[f"{kind}/{'LONG' if s.result.state.direction==1 else 'SHORT'}"]+=1
        if f.source_bar is not None:
            latency[kind].append(i-f.source_bar)
        e=source_map.get((kind,f.source_bar,f.direction))
        if e is None:
            unmapped+=1
        else:
            confirm_outcomes[kind][outcomes[e.episode_id].outcome.value]+=1

    def coverage(kind,outcome_name):
        total=cand_outcomes.get(kind,{}).get(outcome_name,0)
        selected=confirm_outcomes.get(kind,{}).get(outcome_name,0)
        return pct(selected,total)

    active_kind=Counter(
        f.kind.name for f in frames
        if f.kind!=OpportunityKind.NONE and f.stage!=OpportunityStage.NONE
    )
    ev=_event_load(samples,rows)
    return {
        "candidate_counts":{k:len(v) for k,v in sorted(candidates.items())},
        "candidate_outcomes":cand_outcomes,
        "confirm_counts":dict(sorted(confirms.items())),
        "confirm_outcomes":{k:dict(sorted(v.items())) for k,v in sorted(confirm_outcomes.items())},
        "confirm_direction_counts":dict(sorted(directions.items())),
        "frame_active_bar_counts":dict(sorted(active_kind.items())),
        "unmapped_confirm_sources":unmapped,
        "breakout_expansion":{
            "held_confirm_coverage_pct":coverage("BREAKOUT_EXPANSION","BREAKOUT_HELD"),
            "fakeout_confirm_coverage_pct":coverage("BREAKOUT_EXPANSION","BREAKOUT_FAKEOUT"),
            "latency_bars":distribution(latency.get("BREAKOUT_EXPANSION",[])),
            "latency_minutes":distribution([x*TF_MINUTES[tf] for x in latency.get("BREAKOUT_EXPANSION",[])]),
        },
        "reacceleration":{
            "held_confirm_coverage_pct":coverage("REACCELERATION","BREAKOUT_HELD"),
            "fakeout_confirm_coverage_pct":coverage("REACCELERATION","BREAKOUT_FAKEOUT"),
            "latency_bars":distribution(latency.get("REACCELERATION",[])),
            "latency_minutes":distribution([x*TF_MINUTES[tf] for x in latency.get("REACCELERATION",[])]),
        },
        "event_load":ev,
    }


def _range_metrics(eps,outs,frames,samples,data,rows,tf):
    outcome_by={o.episode_id:o for o in outs}
    accepted=0; confirmed=[]; confirm_dirs=Counter()
    latency=[]; room=[]; disp=[]
    before=same=after=0

    for e in eps:
        ab=e.confirmation_bar+1
        if (
            ab<len(frames)
            and frames[ab].source_bar==e.confirmation_bar
            and frames[ab].stage==OpportunityStage.ACCEPTED
        ):
            accepted+=1

        cb=None
        for i in range(e.confirmation_bar,min(len(samples),e.confirmation_bar+3)):
            f=frames[i]
            if f.source_bar!=e.confirmation_bar: continue
            if samples[i].result.events.confirm and samples[i].result.state.direction==e.direction:
                cb=i;break
        if cb is None: continue
        o=outcome_by[e.episode_id]
        confirmed.append((e,o,cb))
        confirm_dirs["LONG" if e.direction==1 else "SHORT"]+=1
        latency.append(cb-e.confirmation_bar)
        if e.atr is not None and e.atr>0:
            dest=e.range_high-e.edge_band if e.direction==1 else e.range_low+e.edge_band
            room.append(e.direction*(dest-float(data["close"][cb]))/e.atr)
            disp.append(e.direction*(float(data["close"][cb])-e.reference_price)/e.atr)
        if o.midpoint_bar is None or cb<o.midpoint_bar: before+=1
        elif cb==o.midpoint_bar: same+=1
        else: after+=1

    oc=Counter(o.outcome.value for _,o,_ in confirmed)
    allc=Counter(o.outcome.value for o in outs)
    ev=_event_load(samples,rows)
    return {
        "episodes":len(eps),
        "structural_outcomes":dict(sorted(allc.items())),
        "accepted_next_bar":accepted,
        "accepted_next_bar_pct":pct(accepted,len(eps)),
        "confirmed":len(confirmed),
        "confirmed_pct":pct(len(confirmed),len(eps)),
        "confirmed_outcomes":dict(sorted(oc.items())),
        "confirmed_midpoint_or_better_pct":pct(oc["MID_REACHED"]+oc["OPPOSITE_REACHED"],len(confirmed)),
        "confirmed_opposite_reached_pct":pct(oc["OPPOSITE_REACHED"],len(confirmed)),
        "failed_before_mid_confirmed":oc["FAILED_BEFORE_MID"],
        "confirmed_censored_pct":pct(oc["CENSORED"],len(confirmed)),
        "confirm_direction_counts":dict(sorted(confirm_dirs.items())),
        "confirm_before_midpoint_pct":pct(before,len(confirmed)),
        "confirm_same_midpoint_pct":pct(same,len(confirmed)),
        "confirm_after_midpoint_pct":pct(after,len(confirmed)),
        "latency_bars":distribution(latency),
        "latency_minutes":distribution([x*TF_MINUTES[tf] for x in latency]),
        "confirm_room_to_opposite_atr":distribution(room),
        "confirm_displacement_atr":distribution(disp),
        "event_load":ev,
    }


def _operator_metrics(paths,rows):
    single=single_miss=same_multi=fresh=fresh_ok=conflicts=0
    raw_events=raw_bars=operator_confirms=suppressed=0
    states=Counter()
    conflict_pairs=Counter()

    for i in range(rows):
        ins=[from_sample(name,samples[i]) for name,samples in paths.items()]
        p=project(ins)
        states[p.readiness.value]+=1
        active=[x for x in ins if x.readiness!=Readiness.WAIT]
        if len(active)==1:
            single+=1
            a=active[0]
            if not (p.readiness.value==a.readiness.name and p.direction==a.direction and not p.conflict):
                single_miss+=1
        dirs={x.direction for x in active}
        if len(active)>=2 and len(dirs)==1:
            same_multi+=1
            has_aligned=any(x.readiness==Readiness.ALIGNED for x in active)
            has_fresh=any(x.readiness in {Readiness.PREP,Readiness.ARMED,Readiness.CONFIRMED} for x in active)
            if has_aligned and has_fresh:
                fresh+=1
                if p.readiness in {OperatorReadiness.PREP,OperatorReadiness.ARMED,OperatorReadiness.CONFIRMED}:
                    fresh_ok+=1
        if p.conflict:
            conflicts+=1
            names=sorted(x.path for x in active)
            conflict_pairs["+".join(names)]+=1
            suppressed+=len(p.suppressed_confirm_sources)
        nconf=sum(x.confirm for x in ins)
        raw_events+=nconf
        raw_bars+=int(nconf>0)
        operator_confirms+=int(p.confirm)

    return {
        "single_active_bars":single,
        "single_active_parity_pct":pct(single-single_miss,single),
        "single_active_mismatches":single_miss,
        "same_direction_multi_active_bars":same_multi,
        "fresh_over_aligned_bars":fresh,
        "fresh_surface_ok_pct":pct(fresh_ok,fresh),
        "conflict_bars":conflicts,
        "conflict_bars_per_1000":_per1000(conflicts,rows),
        "conflict_path_counts":dict(sorted(conflict_pairs.items())),
        "raw_confirm_events":raw_events,
        "raw_confirm_bars":raw_bars,
        "operator_confirm_events":operator_confirms,
        "confirm_bar_preservation_pct":pct(operator_confirms,raw_bars),
        "suppressed_raw_confirms_by_conflict":suppressed,
        "operator_state_counts":dict(sorted(states.items())),
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
        ExecutionResearchBar(float(o),float(h),float(l),float(c),float(v),s.map_dir,loc,ctx[i],
                             s.thesis_invalidated,s.structural_conflict,True)
        for i,(o,h,l,c,v,s,loc) in enumerate(zip(
            data["open"],data["high"],data["low"],data["close"],data["volume"],snaps,locs
        ))
    ]
    rows=len(bars)

    frozen=calculate_execution(bars)

    trend_eps=detect_episodes(snaps,data["high"],data["low"])
    trend_out=classify_all(trend_eps,snaps)
    pb=[ParticipationBar(float(h),float(l),float(c),float(v))
        for h,l,c,v in zip(data["high"],data["low"],data["close"],data["volume"])]
    pse=calculate_participation(pb,[s.map_dir for s in snaps])
    trend_frames=build_opportunity_frames(trend_eps,snaps,data["close"],locs,pse)
    trend=calculate_opportunity_readiness(bars,trend_frames)

    range_eps=[e for e in detect_range_rotations(snaps,data["high"],data["low"],data["close"])
               if e.trigger==RangeTrigger.EDGE_REJECTION]
    range_out=[classify_range_rotation(e,snaps,data["high"],data["low"],data["close"]) for e in range_eps]
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
    return {
        "rows":rows,
        "frozen_0_1":{"event_load":_event_load(frozen,rows)},
        "trend_opportunity_v2":_trend_metrics(trend_eps,trend_out,trend_frames,trend,rows,tf),
        "range_early_any1":_range_metrics(range_eps,range_out,range_frames,range_samples,data,rows,tf),
        "operator_readiness_v1":_operator_metrics(paths,rows),
    }


def markdown(report):
    lines=[
        "# Suite 0.2 — Native horizon robustness",
        "",
        "Accepted semantics unchanged. No per-timeframe retuning.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Path event load",
        "",
        "| TF | rows | 0.1 CONF/1000 | trend CONF/1000 | range CONF/1000 | operator conflicts/1000 | operator confirm preservation % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        f=x["frozen_0_1"]["event_load"]["per_1000"]
        t=x["trend_opportunity_v2"]["event_load"]["per_1000"]
        r=x["range_early_any1"]["event_load"]["per_1000"]
        o=x["operator_readiness_v1"]
        lines.append(
            f"| {tf} | {x['rows']} | {_fmt(f.get('CONFIRM'))} | {_fmt(t.get('CONFIRM'))} | {_fmt(r.get('CONFIRM'))} | {_fmt(o['conflict_bars_per_1000'])} | {_fmt(o['confirm_bar_preservation_pct'])} |"
        )

    lines += [
        "",
        "## Trend opportunity discrimination",
        "",
        "| TF | breakout episodes | held confirm cov % | fakeout confirm cov % | breakout latency bars | breakout latency clock | reaccel episodes | held confirm cov % | fakeout confirm cov % | reaccel latency bars |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        t=x["trend_opportunity_v2"]; b=t["breakout_expansion"]; r=t["reacceleration"]
        bc=t["candidate_counts"].get("BREAKOUT_EXPANSION",0)
        rc=t["candidate_counts"].get("REACCELERATION",0)
        mins=b["latency_minutes"]["median"]
        clock="n/a" if mins is None else f"{mins/60:.2f}h"
        lines.append(
            f"| {tf} | {bc} | {_fmt(b['held_confirm_coverage_pct'])} | {_fmt(b['fakeout_confirm_coverage_pct'])} | {_fmt(b['latency_bars']['median'])} | {clock} | {rc} | {_fmt(r['held_confirm_coverage_pct'])} | {_fmt(r['fakeout_confirm_coverage_pct'])} | {_fmt(r['latency_bars']['median'])} |"
        )

    lines += [
        "",
        "## RANGE_ROTATION",
        "",
        "| TF | episodes | accepted +1 % | confirms | failed confirms | midpoint+ confirmed % | opposite confirmed % | latency bars | latency clock | room ATR med |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        r=x["range_early_any1"]; mins=r["latency_minutes"]["median"]
        clock="n/a" if mins is None else (
            f"{mins/60:.2f}h" if mins<24*60 else f"{mins/(24*60):.2f}d"
        )
        lines.append(
            f"| {tf} | {r['episodes']} | {_fmt(r['accepted_next_bar_pct'])} | {r['confirmed']} | {r['failed_before_mid_confirmed']} | {_fmt(r['confirmed_midpoint_or_better_pct'])} | {_fmt(r['confirmed_opposite_reached_pct'])} | {_fmt(r['latency_bars']['median'])} | {clock} | {_fmt(r['confirm_room_to_opposite_atr']['median'])} |"
        )

    lines += [
        "",
        "## Operator projection",
        "",
        "| TF | single-active parity % | fresh-over-ALIGNED | fresh surfaced % | conflict bars | raw confirm bars | operator confirms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        o=x["operator_readiness_v1"]
        lines.append(
            f"| {tf} | {_fmt(o['single_active_parity_pct'])} | {o['fresh_over_aligned_bars']} | {_fmt(o['fresh_surface_ok_pct'])} | {o['conflict_bars']} | {o['raw_confirm_bars']} | {o['operator_confirm_events']} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- All accepted 4H/1D semantics are unchanged.",
        "- No per-timeframe tuning or profiles.",
        "- Held/fakeout and range outcomes are structural diagnostics, not trade win rates.",
        "- Latency clock time is bar latency multiplied by the native timeframe.",
        "- Small samples are not used to justify semantic changes.",
        "- No production Pine/default/profile changes.",
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

    can=json.loads(a.canonical_manifest.read_text())
    exp={d["timeframe"]:d for d in can["datasets"]}
    symbol=a.symbol.upper();market=can.get("market","spot")
    datasets={};meta={}
    for tf in ("15m","1h","4h","1d","3d","1w"):
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        if not p.is_file():raise SystemExit(f"missing dataset: {p}")
        dig=sha256_file(p)
        if dig!=exp[tf]["dataset_sha256"]:raise SystemExit(f"{symbol} {tf}: SHA mismatch")
        ds=load_dataset(p)
        if len(ds["close"])!=exp[tf]["candles"]:raise SystemExit(f"{symbol} {tf}: rows mismatch")
        datasets[tf]=ds;meta[tf]={"rows":len(ds["close"]),"sha256":dig}

    report={
        "metadata":{
            "symbol":symbol,"code_sha":a.code_sha,"datasets":meta,
            "accepted_operator_readiness_head":"32262d55687813c2036cf5359b31b1c30590cc80",
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

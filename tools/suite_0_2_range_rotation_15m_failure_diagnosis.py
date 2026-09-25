#!/usr/bin/env python3
"""Targeted 15m RANGE_ROTATION failure diagnosis.

No threshold/state/readiness semantics are changed. The runner decomposes:
EDGE_REJECTION -> +1 structural ACCEPTED -> EARLY_ANY1 CONFIRMA

It compares structural failure contamination at each stage and exports every
confirmed FAILED_BEFORE_MID case with auditable source/+1 component evidence.
"""
from __future__ import annotations

import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar
from tools.execution_historical_evidence import build_context_dirs,distribution,load_dataset,pct,sha256_file
from tools.execution_integrated_evidence import build_market_locations,to_mm_candles
from tools.execution_state_reference import Participation,_momentum_aligned,_momentum_strongly_opposes
from tools.market_map_offline_core import IntegrationSnapshot,Kernel
from tools.momentum_turn_reference import Bar as MomentumBar,calculate as calculate_momentum
from tools.participation_reference import ParticipationBar,calculate as calculate_participation
from tools.range_rotation_opportunity_reference import RangeIntegrationVariant,build_range_opportunity_frames
from tools.range_rotation_readiness_reference import (
    RangeReadinessVariant,calculate_range_readiness,dual_opposition,ignition_count,
)
from tools.range_rotation_reference import (
    RangeOutcome,RangeTrigger,classify_range_rotation,detect_range_rotations,
)
from tools.rsi_state_reference import calculate as calculate_rsi,local_opposes,local_supports


TF="15m"


def _dist(xs): return distribution([float(x) for x in xs if x is not None])
def _fmt_time(v):
    try:return v.isoformat()
    except Exception:return str(v)


def _pse_for(direction,long_samples,short_samples):
    return long_samples if direction==1 else short_samples


def _features(direction,mte,rsi,ctx,pse):
    ma=_momentum_aligned(direction,mte.state)
    rs=local_supports(direction,rsi.state)
    pc=pse.state==Participation.CONFIRM
    return {
        "mte_state":mte.state.name,
        "mte_aligned":ma,
        "mte_strongly_opposed":_momentum_strongly_opposes(direction,mte.state),
        "rsi_state":rsi.state.name,
        "rsi_local_supportive":rs,
        "rsi_local_opposing":local_opposes(direction,rsi.state),
        "htf_relation":"ALIGNED" if ctx==direction else "OPPOSING" if ctx==-direction else "NEUTRAL",
        "pse_state":pse.state.name,
        "relative_volume":pse.relative_volume,
        "directional_pressure":pse.directional_pressure,
        "ignition_count":ignition_count(direction,mte.state,rsi.state,pse.state),
        "dual_opposition":dual_opposition(direction,mte.state,rsi.state),
        "ignition_signature":"".join([
            "M" if ma else "-",
            "R" if rs else "-",
            "P" if pc else "-",
        ]),
    }


def _candle(data,i):
    return {
        "open":float(data["open"][i]),
        "high":float(data["high"][i]),
        "low":float(data["low"][i]),
        "close":float(data["close"][i]),
        "volume":float(data["volume"][i]),
    }


def _summary(rows):
    n=len(rows)
    outcomes=Counter(r["outcome"] for r in rows)
    sig=Counter(r["source"]["ignition_signature"] for r in rows)
    counts=Counter(str(r["source"]["ignition_count"]) for r in rows)
    relation=Counter(r["regime_relation"] for r in rows)
    source_mte=Counter(r["source"]["mte_state"] for r in rows)
    source_rsi=Counter(r["source"]["rsi_state"] for r in rows)
    source_pse=Counter(r["source"]["pse_state"] for r in rows)
    accepted_mte=Counter(r["accepted"]["mte_state"] for r in rows if r["accepted"] is not None)
    accepted_rsi=Counter(r["accepted"]["rsi_state"] for r in rows if r["accepted"] is not None)
    accepted_pse=Counter(r["accepted"]["pse_state"] for r in rows if r["accepted"] is not None)
    return {
        "episodes":n,
        "outcome_counts":dict(sorted(outcomes.items())),
        "failed_before_mid_count":outcomes["FAILED_BEFORE_MID"],
        "failed_before_mid_pct":pct(outcomes["FAILED_BEFORE_MID"],n),
        "midpoint_or_better_pct":pct(outcomes["MID_REACHED"]+outcomes["OPPOSITE_REACHED"],n),
        "opposite_reached_pct":pct(outcomes["OPPOSITE_REACHED"],n),
        "censored_pct":pct(outcomes["CENSORED"],n),
        "source_ignition_signatures":dict(sorted(sig.items())),
        "source_ignition_count":dict(sorted(counts.items())),
        "regime_relation":dict(sorted(relation.items())),
        "source_mte_states":dict(sorted(source_mte.items())),
        "source_rsi_states":dict(sorted(source_rsi.items())),
        "source_pse_states":dict(sorted(source_pse.items())),
        "accepted_mte_states":dict(sorted(accepted_mte.items())),
        "accepted_rsi_states":dict(sorted(accepted_rsi.items())),
        "accepted_pse_states":dict(sorted(accepted_pse.items())),
        "range_height_atr":_dist([r["range_height_atr"] for r in rows]),
        "boundary_drift_ratio":_dist([r["boundary_drift_ratio"] for r in rows]),
        "source_range_atr":_dist([r["source_range_atr"] for r in rows]),
        "source_body_directional_atr":_dist([r["source_body_directional_atr"] for r in rows]),
        "accepted_displacement_atr":_dist([r["accepted_displacement_atr"] for r in rows]),
        "accepted_room_to_opposite_atr":_dist([r["accepted_room_to_opposite_atr"] for r in rows]),
        "failure_latency_bars":_dist([r["outcome_latency_bars"] for r in rows if r["outcome"]=="FAILED_BEFORE_MID"]),
    }


def _signature_failure(rows):
    out={}
    groups=defaultdict(list)
    for r in rows:groups[r["source"]["ignition_signature"]].append(r)
    for sig,xs in sorted(groups.items()):
        out[sig]={
            "episodes":len(xs),
            "failed":sum(r["outcome"]=="FAILED_BEFORE_MID" for r in xs),
            "failed_pct":pct(sum(r["outcome"]=="FAILED_BEFORE_MID" for r in xs),len(xs)),
            "midpoint_or_better":sum(r["outcome"] in {"MID_REACHED","OPPOSITE_REACHED"} for r in xs),
            "midpoint_or_better_pct":pct(sum(r["outcome"] in {"MID_REACHED","OPPOSITE_REACHED"} for r in xs),len(xs)),
        }
    return out


def analyze(datasets,tick):
    data=datasets["15m"];snaps=[]
    Kernel(
        to_mm_candles(data),to_mm_candles(datasets["1h"]),
        to_mm_candles(datasets["1d"]),to_mm_candles(datasets["1w"]),
        "15m",tick=tick
    ).run(integration_rows=snaps,emit_audit=False)

    locs=build_market_locations(snaps)
    rsi_cache={tf:calculate_rsi(ds["close"]) for tf,ds in datasets.items()}
    ctx=build_context_dirs("15m",datasets,rsi_cache)
    rsi=rsi_cache["15m"]
    mte=calculate_momentum([
        MomentumBar(float(o),float(h),float(l),float(c))
        for o,h,l,c in zip(data["open"],data["high"],data["low"],data["close"])
    ])
    pb=[
        ParticipationBar(float(h),float(l),float(c),float(v))
        for h,l,c,v in zip(data["high"],data["low"],data["close"],data["volume"])
    ]
    pse_long=calculate_participation(pb,[1]*len(pb))
    pse_short=calculate_participation(pb,[-1]*len(pb))

    bars=[
        ExecutionResearchBar(
            float(o),float(h),float(l),float(c),float(v),s.map_dir,loc,ctx[i],
            s.thesis_invalidated,s.structural_conflict,True
        )
        for i,(o,h,l,c,v,s,loc) in enumerate(zip(
            data["open"],data["high"],data["low"],data["close"],data["volume"],snaps,locs
        ))
    ]

    eps=[
        e for e in detect_range_rotations(snaps,data["high"],data["low"],data["close"])
        if e.trigger==RangeTrigger.EDGE_REJECTION
    ]
    outs={
        e.episode_id:classify_range_rotation(e,snaps,data["high"],data["low"],data["close"])
        for e in eps
    }
    frames=build_range_opportunity_frames(
        eps,snaps,data["high"],data["low"],data["close"],
        variant=RangeIntegrationVariant.ALL_EDGE
    )
    samples=calculate_range_readiness(
        bars,frames,variant=RangeReadinessVariant.EARLY_ANY1
    )

    rows=[]
    for e in eps:
        i=e.confirmation_bar
        o=outs[e.episode_id]
        pse=_pse_for(e.direction,pse_long,pse_short)
        sf=_features(e.direction,mte[i],rsi[i],ctx[i],pse[i])

        ai=i+1
        accepted=(
            ai<len(frames)
            and frames[ai].source_bar==i
            and frames[ai].stage.name=="ACCEPTED"
        )
        af=_features(e.direction,mte[ai],rsi[ai],ctx[ai],pse[ai]) if accepted else None

        cb=None
        for j in range(i,min(len(samples),i+3)):
            if frames[j].source_bar!=i:continue
            if samples[j].result.events.confirm and samples[j].result.state.direction==e.direction:
                cb=j;break
        confirmed=cb is not None

        atr=e.atr
        accepted_disp=None
        accepted_room=None
        if accepted and atr is not None and atr>0:
            accepted_disp=e.direction*(float(data["close"][ai])-e.reference_price)/atr
            dest=e.range_high-e.edge_band if e.direction==1 else e.range_low+e.edge_band
            accepted_room=e.direction*(dest-float(data["close"][ai]))/atr

        src_range=None;src_body=None
        if atr is not None and atr>0:
            src_range=(float(data["high"][i])-float(data["low"][i]))/atr
            src_body=e.direction*(float(data["close"][i])-float(data["open"][i]))/atr

        row={
            "episode_id":e.episode_id,
            "source_bar":i,
            "source_time":_fmt_time(data["open_time"][i]),
            "direction":"LONG" if e.direction==1 else "SHORT",
            "regime_relation":e.regime_relation.value,
            "outcome":o.outcome.value,
            "outcome_bar":o.outcome_bar,
            "outcome_time":None if o.outcome_bar is None else _fmt_time(data["open_time"][o.outcome_bar]),
            "outcome_latency_bars":None if o.outcome_bar is None else o.outcome_bar-i,
            "midpoint_bar":o.midpoint_bar,
            "invalidation_bar":o.invalidation_bar,
            "accepted":accepted,
            "accepted_bar":ai if accepted else None,
            "accepted_time":_fmt_time(data["open_time"][ai]) if accepted else None,
            "confirmed":confirmed,
            "confirm_bar":cb,
            "confirm_time":_fmt_time(data["open_time"][cb]) if cb is not None else None,
            "range_high":e.range_high,
            "range_low":e.range_low,
            "range_mid":e.range_mid,
            "range_height_atr":e.height_atr,
            "boundary_drift_ratio":e.boundary_drift_ratio,
            "source_range_atr":src_range,
            "source_body_directional_atr":src_body,
            "accepted_displacement_atr":accepted_disp,
            "accepted_room_to_opposite_atr":accepted_room,
            "source":sf,
            "accepted_features":af,
            "accepted":af,
            "source_candle":_candle(data,i),
            "accepted_candle":_candle(data,ai) if accepted else None,
        }
        rows.append(row)

    all_rows=rows
    accepted_rows=[r for r in rows if r["accepted"] is not None]
    confirmed_rows=[r for r in rows if r["confirmed"]]
    confirmed_failed=[r for r in confirmed_rows if r["outcome"]=="FAILED_BEFORE_MID"]
    confirmed_success=[r for r in confirmed_rows if r["outcome"] in {"MID_REACHED","OPPOSITE_REACHED"}]
    confirmed_censored=[r for r in confirmed_rows if r["outcome"]=="CENSORED"]

    return {
        "episodes":len(all_rows),
        "funnel":{
            "all_edge":_summary(all_rows),
            "accepted_plus1":_summary(accepted_rows),
            "confirmed_early_any1":_summary(confirmed_rows),
            "confirmed_success":_summary(confirmed_success),
            "confirmed_failed":_summary(confirmed_failed),
            "confirmed_censored":_summary(confirmed_censored),
        },
        "selection_effect":{
            "accepted_failure_pct":_summary(accepted_rows)["failed_before_mid_pct"],
            "confirmed_failure_pct":_summary(confirmed_rows)["failed_before_mid_pct"],
            "failure_delta_pp":(
                None if not accepted_rows or not confirmed_rows else
                _summary(confirmed_rows)["failed_before_mid_pct"]-_summary(accepted_rows)["failed_before_mid_pct"]
            ),
        },
        "confirmed_signature_outcomes":_signature_failure(confirmed_rows),
        "failed_confirm_cases":confirmed_failed,
    }


def markdown(report):
    x=report["diagnosis"];f=x["funnel"]
    lines=[
        "# Suite 0.2 — 15m RANGE_ROTATION failure diagnosis",
        "",
        "Diagnostic only. No rule or threshold changed.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Structural funnel",
        "",
        "| stage | episodes | fail-before-mid % | midpoint+ % | opposite % | censored % |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key,label in [
        ("all_edge","EDGE_REJECTION"),
        ("accepted_plus1","+1 ACCEPTED"),
        ("confirmed_early_any1","EARLY_ANY1 CONFIRMA"),
        ("confirmed_success","confirmed success"),
        ("confirmed_failed","confirmed failure"),
        ("confirmed_censored","confirmed censored"),
    ]:
        s=f[key]
        lines.append(
            f"| {label} | {s['episodes']} | {s['failed_before_mid_pct'] if s['failed_before_mid_pct'] is not None else 'n/a'} | {s['midpoint_or_better_pct'] if s['midpoint_or_better_pct'] is not None else 'n/a'} | {s['opposite_reached_pct'] if s['opposite_reached_pct'] is not None else 'n/a'} | {s['censored_pct'] if s['censored_pct'] is not None else 'n/a'} |"
        )
    se=x["selection_effect"]
    lines += [
        "",
        "## Selection effect",
        "",
        f"- +1 ACCEPTED fail contamination: **{se['accepted_failure_pct']}%**",
        f"- EARLY_ANY1 confirmed fail contamination: **{se['confirmed_failure_pct']}%**",
        f"- delta: **{se['failure_delta_pp']} pp**",
        "",
        "## Confirmed source signatures",
        "",
        "| ignition signature | confirms | failed | fail % | midpoint+ % |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for sig,s in x["confirmed_signature_outcomes"].items():
        lines.append(f"| {sig} | {s['episodes']} | {s['failed']} | {s['failed_pct']} | {s['midpoint_or_better_pct']} |")

    lines += ["","## Failed confirmed cases",""]
    for c in x["failed_confirm_cases"]:
        lines += [
            f"- **{c['source_time']} {c['direction']}**",
            f"  - regime: {c['regime_relation']}; source ignition: {c['source']['ignition_signature']} ({c['source']['ignition_count']})",
            f"  - source states: MTE={c['source']['mte_state']}, RSI={c['source']['rsi_state']}, PSE={c['source']['pse_state']}, HTF={c['source']['htf_relation']}",
            f"  - accepted states: MTE={c['accepted']['mte_state']}, RSI={c['accepted']['rsi_state']}, PSE={c['accepted']['pse_state']}, HTF={c['accepted']['htf_relation']}",
            f"  - range height={c['range_height_atr']:.3f} ATR; drift={c['boundary_drift_ratio']:.4f}; source range={c['source_range_atr']:.3f} ATR",
            f"  - accepted displacement={c['accepted_displacement_atr']:.3f} ATR; room={c['accepted_room_to_opposite_atr']:.3f} ATR",
            f"  - failure latency={c['outcome_latency_bars']} bars; outcome time={c['outcome_time']}",
        ]
    lines += [
        "",
        "## Guardrails",
        "",
        "- No 15m threshold is tuned from these cases.",
        "- Source ignition signatures: M=MTE aligned, R=local RSI supportive, P=PSE CONFIRM.",
        "- The +1 ACCEPTED gate and EARLY_ANY1 semantics are unchanged.",
        "- 1H/4H/1D are not reopened by this diagnostic.",
        "- Structural outcome is not a trade win-rate claim.",
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
    for tf in ("15m","1h","1d","1w"):
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        if not p.is_file():raise SystemExit(f"missing {p}")
        dig=sha256_file(p)
        if dig!=exp[tf]["dataset_sha256"]:raise SystemExit(f"{symbol} {tf}: SHA mismatch")
        ds=load_dataset(p)
        if len(ds["close"])!=exp[tf]["candles"]:raise SystemExit(f"{symbol} {tf}: row mismatch")
        datasets[tf]=ds;meta[tf]={"rows":len(ds["close"]),"sha256":dig}
    report={
        "metadata":{"symbol":symbol,"code_sha":a.code_sha,"datasets":meta},
        "diagnosis":analyze(datasets,a.tick_size),
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report);a.output_md.write_text(md+"\n");print(md)
    return 0

if __name__=="__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Prior-completed 1M macro context over accepted 3D/1W opportunities.

Descriptive research only:
- accepted 3D/1W Opportunity v2 semantics remain unchanged;
- monthly state is mapped from the prior completed calendar month only;
- no hard filtering;
- no per-symbol tuning;
- no production Pine/default/profile changes.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar
from tools.execution_historical_evidence import (
    build_context_dirs,
    confirmed_context_indices,
    load_dataset,
    pct,
    sha256_file,
)
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.monthly_aggregation_reference import aggregate_calendar_month, logical_sha256
from tools.opportunity_episode_reference import (
    BreakContext,
    OpportunityType,
    detect_episodes,
)
from tools.opportunity_execution_counterfactual import (
    OpportunityKind,
    build_opportunity_frames,
)
from tools.opportunity_outcome_reference import classify_all
from tools.opportunity_readiness_reference import calculate_opportunity_readiness
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi


SYMBOLS=(
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT","ADAUSDT","XRPUSDT",
    "SOLUSDT","UNIUSDT","NEARUSDT","AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)
TIMEFRAMES=("3d","1w")
MONTHLY_VARIANTS={
    "FIXED_21_50_200":(50,200),
    "WEEK_EQUIV_5_12_46":(12,46),
}
DESCRIPTORS=("regime","map")


def _logical_kind(e):
    if e.opportunity_type==OpportunityType.REACCELERATION:
        return OpportunityKind.REACCELERATION
    if e.opportunity_type==OpportunityType.REGIME_REVERSAL:
        return OpportunityKind.REGIME_REVERSAL
    if (
        e.opportunity_type==OpportunityType.BREAKOUT_CANDIDATE
        and e.break_context in {
            BreakContext.FRESH_EXPANSION.value,
            BreakContext.OTHER.value,
        }
    ):
        return OpportunityKind.BREAKOUT_EXPANSION
    return None


def _relation(direction,monthly_dir,available):
    if not available:
        return "UNAVAILABLE"
    if monthly_dir==0:
        return "NEUTRAL"
    if monthly_dir==direction:
        return "ALIGNED"
    return "OPPOSING"


def _monthly_state(monthly,mid_len,slow_len,tick):
    cs=to_mm_candles(monthly)
    snaps=[]
    Kernel(
        cs,cs,cs,cs,"1M",tick=tick,mid_len=mid_len,slow_len=slow_len
    ).run(integration_rows=snaps,emit_audit=False)
    return {
        "regime":[s.regime_dir for s in snaps],
        "map":[s.map_dir for s in snaps],
    }


def _accepted_horizon(tf,datasets,tick):
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
            s.map_dir,loc,ctx[i],s.thesis_invalidated,s.structural_conflict,True
        )
        for i,(o,h,l,c,v,s,loc) in enumerate(zip(
            data["open"],data["high"],data["low"],data["close"],data["volume"],
            snaps,locs
        ))
    ]

    eps=detect_episodes(snaps,data["high"],data["low"])
    outcomes=classify_all(eps,snaps)

    pb=[
        ParticipationBar(float(h),float(l),float(c),float(v))
        for h,l,c,v in zip(data["high"],data["low"],data["close"],data["volume"])
    ]
    pse=calculate_participation(pb,[s.map_dir for s in snaps])
    frames=build_opportunity_frames(eps,snaps,data["close"],locs,pse)
    samples=calculate_opportunity_readiness(bars,frames)

    confirmed_keys=set()
    for sample,frame in zip(samples,frames):
        if sample.result.events.confirm and frame.source_bar is not None:
            confirmed_keys.add((frame.kind.name,frame.source_bar,frame.direction))

    return eps,outcomes,confirmed_keys


def _record_candidates(sym,tf,datasets,monthly,monthly_states):
    data=datasets[tf]
    eps,outcomes,confirmed_keys=_accepted_horizon(tf,datasets,0.01)
    month_idx=confirmed_context_indices(data["open_time"],monthly["open_time"])

    records=[]
    for e in eps:
        kind=_logical_kind(e)
        if kind is None:
            continue
        key=(kind.name,e.confirmation_bar,e.direction)
        confirmed=key in confirmed_keys
        outcome=outcomes[e.episode_id].outcome.value
        mi=month_idx[e.confirmation_bar]
        for variant,states in monthly_states.items():
            for descriptor in DESCRIPTORS:
                available=mi is not None
                md=0 if mi is None else states[descriptor][mi]
                records.append({
                    "symbol":sym,
                    "timeframe":tf,
                    "variant":variant,
                    "descriptor":descriptor,
                    "kind":kind.name,
                    "direction":"LONG" if e.direction==1 else "SHORT",
                    "relation":_relation(e.direction,md,available),
                    "outcome":outcome,
                    "confirmed":confirmed,
                    "monthly_index":mi,
                })
    return records


def _summary(rows):
    n=len(rows)
    oc=Counter(r["outcome"] for r in rows)
    confirmed=[r for r in rows if r["confirmed"]]
    cc=Counter(r["outcome"] for r in confirmed)
    held=oc["BREAKOUT_HELD"]; fake=oc["BREAKOUT_FAKEOUT"]
    return {
        "candidates":n,
        "symbols":len({r["symbol"] for r in rows}),
        "direction_counts":dict(sorted(Counter(r["direction"] for r in rows).items())),
        "outcome_counts":dict(sorted(oc.items())),
        "resolved_held_share_pct":pct(held,held+fake),
        "confirmed":len(confirmed),
        "confirmed_outcomes":dict(sorted(cc.items())),
        "held_confirm_coverage_pct":pct(cc["BREAKOUT_HELD"],held),
        "fakeout_confirm_coverage_pct":pct(cc["BREAKOUT_FAKEOUT"],fake),
    }


def _aggregate(records):
    out={}
    for tf in TIMEFRAMES:
        out[tf]={}
        for variant in MONTHLY_VARIANTS:
            out[tf][variant]={}
            for descriptor in DESCRIPTORS:
                d={}
                subset=[
                    r for r in records
                    if r["timeframe"]==tf
                    and r["variant"]==variant
                    and r["descriptor"]==descriptor
                ]
                for kind in sorted({r["kind"] for r in subset}):
                    kr=[r for r in subset if r["kind"]==kind]
                    d[kind]={
                        rel:_summary([r for r in kr if r["relation"]==rel])
                        for rel in ("ALIGNED","NEUTRAL","OPPOSING","UNAVAILABLE")
                    }
                out[tf][variant][descriptor]=d
    return out


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — prior-completed 1M macro context for 3D / 1W",
        "",
        "Descriptive only. Accepted 3D/1W readiness is unchanged.",
        "",
        f"- symbols: **{len(report['symbols'])}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "- monthly mapping: **prior completed month only**",
        "- no hard filter",
        "",
    ]

    for tf in TIMEFRAMES:
        lines += [f"## {tf}",""]
        for variant in MONTHLY_VARIANTS:
            for descriptor in DESCRIPTORS:
                lines += [
                    f"### {variant} / monthly {descriptor}",
                    "",
                    "| opportunity | relation | candidates | symbols | held/fakeout | held share resolved % | confirms | confirm held/fakeout | held cov % | fakeout cov % |",
                    "| --- | --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: |",
                ]
                d=report["aggregate"][tf][variant][descriptor]
                for kind,relations in d.items():
                    for rel,row in relations.items():
                        oc=row["outcome_counts"]; cc=row["confirmed_outcomes"]
                        lines.append(
                            f"| {kind} | {rel} | {row['candidates']} | {row['symbols']} | {oc.get('BREAKOUT_HELD',0)}/{oc.get('BREAKOUT_FAKEOUT',0)} | {_fmt(row['resolved_held_share_pct'])} | {row['confirmed']} | {cc.get('BREAKOUT_HELD',0)}/{cc.get('BREAKOUT_FAKEOUT',0)} | {_fmt(row['held_confirm_coverage_pct'])} | {_fmt(row['fakeout_confirm_coverage_pct'])} |"
                        )
                lines.append("")

    lines += [
        "## Guardrails",
        "",
        "- UNAVAILABLE means no prior completed monthly observation; it is not NEUTRAL.",
        "- Monthly state never uses the current incomplete month.",
        "- 3D/1W Opportunity frames/readiness are calculated exactly as accepted before this study.",
        "- HELD/FAKEOUT are retrospective structural labels, not trade win rates.",
        "- The study is descriptive; no relation blocks or boosts a signal here.",
        "- Fixed 50/200 and 12/46 are compared as context descriptors only.",
        "- No production Pine/default/profile or per-symbol tuning changed.",
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

    records=[]
    symbols_meta={}
    for sym in SYMBOLS:
        datasets={}
        for tf in ("1d","3d","1w"):
            p=a.data_root/"spot"/sym/"consolidated"/f"{sym}_{tf}.parquet"
            datasets[tf]=load_dataset(p)

        monthly,prov=aggregate_calendar_month(datasets["1d"])
        states={
            name:_monthly_state(monthly,mid,slow,a.tick_size)
            for name,(mid,slow) in MONTHLY_VARIANTS.items()
        }

        for tf in TIMEFRAMES:
            # accepted high-horizon semantics use existing self-context mapping.
            records.extend(_record_candidates(sym,tf,datasets,monthly,states))

        symbols_meta[sym]={
            "monthly_rows":len(monthly["close"]),
            "monthly_logical_sha256":logical_sha256(monthly),
            "partial_months":sum(
                not (p["starts_on_calendar_day_1"] and p["ends_on_calendar_month_end"])
                for p in prov
            ),
        }

    report={
        "metadata":{
            "code_sha":a.code_sha,
            "monthly_variants":{
                "FIXED_21_50_200":{"mid":50,"slow":200},
                "WEEK_EQUIV_5_12_46":{"mid":12,"slow":46},
            },
            "mapping":"prior_completed_month",
        },
        "symbols":symbols_meta,
        "aggregate":_aggregate(records),
    }

    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report); a.output_md.write_text(md+"\n"); print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""BTC 4H/1D evidence for preregistered Thesis Management V0.

A management episode starts at unified OPERATOR_READINESS_V1 CONFIRMA and
freezes its structural target/invalidation anchors at that bar.

This is market-thesis research, not account-position inference or PnL testing.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import (
    build_context_dirs,
    distribution,
    load_dataset,
    pct,
    sha256_file,
)
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.execution_state_reference import Strength
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.momentum_turn_reference import Bar as MomentumBar, calculate as calculate_momentum
from tools.operator_readiness_reference import from_sample, project
from tools.opportunity_episode_reference import detect_episodes
from tools.opportunity_execution_counterfactual import OpportunityKind, build_opportunity_frames
from tools.opportunity_readiness_reference import calculate_opportunity_readiness
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.range_rotation_opportunity_reference import RangeIntegrationVariant, build_range_opportunity_frames
from tools.range_rotation_readiness_reference import RangeReadinessVariant, calculate_range_readiness
from tools.range_rotation_reference import RangeTrigger, detect_range_rotations
from tools.rsi_state_reference import calculate as calculate_rsi
from tools.thesis_management_reference import (
    ManagementState,
    classify_management_bar,
)


TIMEFRAMES=("4h","1d")
PATH_NAMES=("FROZEN_0_1","TREND_OPPORTUNITY_V2","RANGE_EARLY_ANY1")


@dataclass(frozen=True)
class ThesisEpisode:
    thesis_id: str
    confirm_bar: int
    direction: int
    source: str
    opportunity_kind: str
    target: float
    invalidation: float
    source_bar: int | None


@dataclass(frozen=True)
class ThesisResult:
    thesis_id: str
    source: str
    opportunity_kind: str
    direction: int
    confirm_bar: int
    end_bar: int
    outcome: str
    bars_live: int
    first_fading_bar: int | None
    first_exhausted_bar: int | None
    first_protect_bar: int | None
    first_realization_bar: int | None
    first_target_near_bar: int | None
    first_invalidation_near_bar: int | None
    first_structural_warning_bar: int | None
    protect_lead_bars: int | None
    realization_lead_bars: int | None
    fading_lead_bars: int | None
    first_fading_progress: float | None
    first_exhausted_progress: float | None
    first_protect_progress: float | None
    first_structural_warning_progress: float | None
    first_protect_strict_bar: int | None
    first_protect_strict_progress: float | None
    first_favorable_fading_bar: int | None
    first_favorable_fading_progress: float | None
    first_favorable_exhausted_bar: int | None
    first_favorable_exhausted_progress: float | None
    protect_strict_bars: int
    favorable_fading_bars: int
    favorable_exhausted_bars: int
    protect_strict_transitions: int
    favorable_fading_transitions: int
    favorable_exhausted_transitions: int
    state_transitions: int
    warning_to_continuation_transitions: int
    protect_bars: int
    realization_bars: int
    continuation_bars: int
    fading_bars: int


def _time(v):
    try:return v.isoformat()
    except Exception:return str(v)


def _dist(values):
    return distribution([float(v) for v in values if v is not None])


def _directional_valid(direction,target,invalidation,close):
    if direction==1:
        return target>close and invalidation<close
    if direction==-1:
        return target<close and invalidation>close
    return False


def _build_operator_paths(tf,datasets,tick):
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
            s.map_dir,loc,ctx[i],s.thesis_invalidated,s.structural_conflict,True
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

    return {
        "data":data,"snaps":snaps,"locs":locs,"ctx":ctx,"bars":bars,
        "paths":{
            "FROZEN_0_1":frozen,
            "TREND_OPPORTUNITY_V2":trend,
            "RANGE_EARLY_ANY1":range_samples,
        },
        "trend_frames":trend_frames,
        "range_frames":range_frames,
        "range_eps":range_eps,
    }


def _range_anchor(i,direction,frame,range_eps):
    if frame.source_bar is None:
        return None
    candidates=[
        e for e in range_eps
        if e.confirmation_bar==frame.source_bar and e.direction==direction
    ]
    if len(candidates)!=1:
        return None
    e=candidates[0]
    target=e.range_high-e.edge_band if direction==1 else e.range_low+e.edge_band
    invalidation=e.range_low if direction==1 else e.range_high
    return target,invalidation,e.confirmation_bar


def _build_theses(ctx):
    data=ctx["data"];snaps=ctx["snaps"];paths=ctx["paths"]
    trend_frames=ctx["trend_frames"];range_frames=ctx["range_frames"]
    range_eps=ctx["range_eps"]

    theses=[]
    unsupported=Counter()
    confirm_rows=[]

    for i in range(len(data["close"])):
        inputs=[from_sample(name,paths[name][i]) for name in PATH_NAMES]
        p=project(inputs)
        if not p.confirm:
            continue

        confirm_rows.append(i)
        sources=tuple(p.confirming_sources)
        if len(sources)!=1:
            unsupported["MULTI_SOURCE_CONFIRM"]+=1
            continue

        source=sources[0]
        direction=p.direction
        close=float(data["close"][i])
        target=invalidation=None
        source_bar=None
        kind=source

        if source in {"FROZEN_0_1","TREND_OPPORTUNITY_V2"}:
            target=snaps[i].destination
            invalidation=snaps[i].invalidation
            if source=="TREND_OPPORTUNITY_V2":
                kind=trend_frames[i].kind.name
                source_bar=trend_frames[i].source_bar
            else:
                kind="PULLBACK_RETEST_0_1"
                source_bar=snaps[i].thesis_key
        elif source=="RANGE_EARLY_ANY1":
            anchor=_range_anchor(i,direction,range_frames[i],range_eps)
            if anchor is not None:
                target,invalidation,source_bar=anchor
                kind="RANGE_ROTATION"

        if target is None or invalidation is None:
            unsupported["MISSING_ANCHOR"]+=1
            continue
        target=float(target);invalidation=float(invalidation)
        if not _directional_valid(direction,target,invalidation,close):
            unsupported["INVALID_GEOMETRY"]+=1
            continue

        theses.append(ThesisEpisode(
            thesis_id=f"{source}:{direction}:{i}",
            confirm_bar=i,
            direction=direction,
            source=source,
            opportunity_kind=kind,
            target=target,
            invalidation=invalidation,
            source_bar=source_bar,
        ))

    return theses,unsupported,confirm_rows


def _structural_warning(thesis,i,ctx):
    snap=ctx["snaps"][i]
    if thesis.source=="RANGE_EARLY_ANY1":
        f=ctx["range_frames"][i]
        return not (
            f.kind==OpportunityKind.RANGE_ROTATION
            and f.source_bar==thesis.source_bar
            and f.direction==thesis.direction
        )
    return bool(
        snap.structural_conflict
        or snap.map_dir!=thesis.direction
        or snap.thesis_invalidated
    )


def _evaluate(theses,confirm_rows,ctx):
    data=ctx["data"];snaps=ctx["snaps"]
    n=len(data["close"])

    momentum=calculate_momentum([
        MomentumBar(float(o),float(h),float(l),float(c))
        for o,h,l,c in zip(data["open"],data["high"],data["low"],data["close"])
    ])
    rsi=calculate_rsi(data["close"])
    pb=[ParticipationBar(float(h),float(l),float(c),float(v))
        for h,l,c,v in zip(data["high"],data["low"],data["close"],data["volume"])]
    pse_long=calculate_participation(pb,[1]*n)
    pse_short=calculate_participation(pb,[-1]*n)

    next_confirm={}
    for a,b in zip(confirm_rows,confirm_rows[1:]):
        next_confirm[a]=b

    results=[]
    bar_state_counts=Counter()
    bar_strength_counts=Counter()
    protect_cause_counts=Counter()
    target_near_bars=0
    invalidation_near_bars=0

    for th in theses:
        stop_before=next_confirm.get(th.confirm_bar,n)
        first_fading=first_exhausted=first_protect=first_realization=None
        first_tnear=first_inear=first_struct=None
        first_fading_progress=first_exhausted_progress=first_protect_progress=first_struct_progress=None
        first_protect_strict=first_favorable_fading=first_favorable_exhausted=None
        first_protect_strict_progress=first_favorable_fading_progress=first_favorable_exhausted_progress=None
        confirm_close=float(data["close"][th.confirm_bar])
        initial_target_distance=th.direction*(th.target-confirm_close)
        state_trans=warning_back=0
        protect_bars=realization_bars=continuation_bars=fading_bars=0
        protect_strict_bars=favorable_fading_bars=favorable_exhausted_bars=0
        protect_strict_trans=favorable_fading_trans=favorable_exhausted_trans=0
        prev_protect_strict=prev_favorable_fading=prev_favorable_exhausted=False
        prev_nonterminal=None
        outcome="OPEN_END"
        end=min(n-1,stop_before-1)

        for i in range(th.confirm_bar,stop_before):
            pse=pse_long if th.direction==1 else pse_short
            mb=classify_management_bar(
                direction=th.direction,
                high=float(data["high"][i]),
                low=float(data["low"][i]),
                close=float(data["close"][i]),
                atr=snaps[i].atr,
                target=th.target,
                invalidation=th.invalidation,
                momentum=momentum[i].state,
                rsi=rsi[i].state,
                participation=pse[i].state,
                structural_warning=_structural_warning(th,i,ctx),
                bar_confirmed=True,
            )

            bar_state_counts[mb.state.value]+=1
            bar_strength_counts[mb.strength.name]+=1

            progress=(
                None if initial_target_distance<=0
                else th.direction*(float(data["close"][i])-confirm_close)/initial_target_distance
            )
            if mb.target_near:
                target_near_bars+=1
            if mb.invalidation_near:
                invalidation_near_bars+=1

            terminal=mb.state in {
                ManagementState.COMPLETED,
                ManagementState.INVALIDATED,
                ManagementState.AMBIGUOUS,
            }
            protect_strict=bool(
                not terminal and (
                    mb.invalidation_near
                    or mb.strength==Strength.EXHAUSTED
                    or (
                        mb.structural_warning
                        and mb.strength in {
                            Strength.FADING,
                            Strength.EXHAUSTED,
                            Strength.REACTION_RISK,
                        }
                    )
                )
            )
            favorable_fading=bool(
                not terminal
                and progress is not None
                and progress>0
                and mb.strength in {
                    Strength.FADING,
                    Strength.EXHAUSTED,
                    Strength.REACTION_RISK,
                }
            )
            favorable_exhausted=bool(
                not terminal
                and progress is not None
                and progress>0
                and mb.strength in {
                    Strength.EXHAUSTED,
                    Strength.REACTION_RISK,
                }
            )

            if protect_strict:
                protect_strict_bars+=1
                if first_protect_strict is None:
                    first_protect_strict=i
                    first_protect_strict_progress=progress
            if favorable_fading:
                favorable_fading_bars+=1
                if first_favorable_fading is None:
                    first_favorable_fading=i
                    first_favorable_fading_progress=progress
            if favorable_exhausted:
                favorable_exhausted_bars+=1
                if first_favorable_exhausted is None:
                    first_favorable_exhausted=i
                    first_favorable_exhausted_progress=progress

            if i>th.confirm_bar:
                protect_strict_trans+=int(protect_strict!=prev_protect_strict)
                favorable_fading_trans+=int(favorable_fading!=prev_favorable_fading)
                favorable_exhausted_trans+=int(favorable_exhausted!=prev_favorable_exhausted)
            prev_protect_strict=protect_strict
            prev_favorable_fading=favorable_fading
            prev_favorable_exhausted=favorable_exhausted

            if mb.strength==Strength.FADING:
                fading_bars+=1
                if first_fading is None:
                    first_fading=i
                    first_fading_progress=progress
            if mb.strength==Strength.EXHAUSTED and first_exhausted is None:
                first_exhausted=i
                first_exhausted_progress=progress
            if mb.target_near and first_tnear is None:first_tnear=i
            if mb.invalidation_near and first_inear is None:first_inear=i
            if mb.structural_warning and first_struct is None:
                first_struct=i
                first_struct_progress=progress
            if mb.state==ManagementState.PROTECT:
                protect_bars+=1
                causes=[]
                if mb.strength==Strength.EXHAUSTED:causes.append("EXHAUSTED")
                if mb.invalidation_near:causes.append("INVALIDATION_NEAR")
                if mb.structural_warning:causes.append("STRUCTURAL_WARNING")
                protect_cause_counts["+".join(causes) if causes else "OTHER"]+=1
                if first_protect is None:
                    first_protect=i
                    first_protect_progress=progress
            elif mb.state==ManagementState.REALIZATION_RISK:
                realization_bars+=1
                if first_realization is None:first_realization=i
            elif mb.state==ManagementState.CONTINUATION:
                continuation_bars+=1

            if mb.state not in {
                ManagementState.COMPLETED,
                ManagementState.INVALIDATED,
                ManagementState.AMBIGUOUS,
            }:
                if prev_nonterminal is not None and mb.state!=prev_nonterminal:
                    state_trans+=1
                    if (
                        prev_nonterminal in {ManagementState.PROTECT,ManagementState.REALIZATION_RISK}
                        and mb.state==ManagementState.CONTINUATION
                    ):
                        warning_back+=1
                prev_nonterminal=mb.state

            if mb.state==ManagementState.COMPLETED:
                outcome="COMPLETED";end=i;break
            if mb.state==ManagementState.INVALIDATED:
                outcome="INVALIDATED";end=i;break
            if mb.state==ManagementState.AMBIGUOUS:
                outcome="AMBIGUOUS";end=i;break
        else:
            if stop_before<n:
                outcome="SUPERSEDED"
                end=stop_before-1

        def lead(first):
            return None if first is None or outcome not in {"COMPLETED","INVALIDATED","AMBIGUOUS"} else end-first

        results.append(ThesisResult(
            thesis_id=th.thesis_id,
            source=th.source,
            opportunity_kind=th.opportunity_kind,
            direction=th.direction,
            confirm_bar=th.confirm_bar,
            end_bar=end,
            outcome=outcome,
            bars_live=end-th.confirm_bar+1,
            first_fading_bar=first_fading,
            first_exhausted_bar=first_exhausted,
            first_protect_bar=first_protect,
            first_realization_bar=first_realization,
            first_target_near_bar=first_tnear,
            first_invalidation_near_bar=first_inear,
            first_structural_warning_bar=first_struct,
            protect_lead_bars=lead(first_protect),
            realization_lead_bars=lead(first_realization),
            fading_lead_bars=lead(first_fading),
            first_fading_progress=first_fading_progress,
            first_exhausted_progress=first_exhausted_progress,
            first_protect_progress=first_protect_progress,
            first_structural_warning_progress=first_struct_progress,
            first_protect_strict_bar=first_protect_strict,
            first_protect_strict_progress=first_protect_strict_progress,
            first_favorable_fading_bar=first_favorable_fading,
            first_favorable_fading_progress=first_favorable_fading_progress,
            first_favorable_exhausted_bar=first_favorable_exhausted,
            first_favorable_exhausted_progress=first_favorable_exhausted_progress,
            protect_strict_bars=protect_strict_bars,
            favorable_fading_bars=favorable_fading_bars,
            favorable_exhausted_bars=favorable_exhausted_bars,
            protect_strict_transitions=protect_strict_trans,
            favorable_fading_transitions=favorable_fading_trans,
            favorable_exhausted_transitions=favorable_exhausted_trans,
            state_transitions=state_trans,
            warning_to_continuation_transitions=warning_back,
            protect_bars=protect_bars,
            realization_bars=realization_bars,
            continuation_bars=continuation_bars,
            fading_bars=fading_bars,
        ))

    return results,bar_state_counts,bar_strength_counts,protect_cause_counts,target_near_bars,invalidation_near_bars


def _channel_summary(results, first_bar_key, first_progress_key, bars_key, transitions_key):
    live=sum(r.bars_live for r in results)
    def subset(outcome):
        return [r for r in results if r.outcome==outcome]
    def stats(rows):
        reached=[r for r in rows if getattr(r,first_bar_key) is not None]
        leads=[
            r.end_bar-getattr(r,first_bar_key)
            for r in reached
            if r.outcome in {"COMPLETED","INVALIDATED","AMBIGUOUS"}
        ]
        return {
            "episodes":len(rows),
            "reached":len(reached),
            "reached_pct":pct(len(reached),len(rows)),
            "lead_bars":_dist(leads),
            "first_progress":_dist([getattr(r,first_progress_key) for r in reached]),
        }
    bars=sum(getattr(r,bars_key) for r in results)
    transitions=sum(getattr(r,transitions_key) for r in results)
    return {
        "bars":bars,
        "bar_saturation_pct":pct(bars,live),
        "transitions":transitions,
        "transitions_per_1000_live_bars":None if not live else 1000*transitions/live,
        "completed":stats(subset("COMPLETED")),
        "invalidated":stats(subset("INVALIDATED")),
        "superseded":stats(subset("SUPERSEDED")),
    }


def _summary(results,bar_states,bar_strengths,protect_causes=None,target_near_bars=0,invalidation_near_bars=0):
    outcomes=Counter(r.outcome for r in results)
    total_live=sum(r.bars_live for r in results)
    completed=[r for r in results if r.outcome=="COMPLETED"]
    invalidated=[r for r in results if r.outcome=="INVALIDATED"]
    resolved=[r for r in results if r.outcome in {"COMPLETED","INVALIDATED","AMBIGUOUS"}]

    protect_causes=protect_causes or Counter()
    return {
        "episodes":len(results),
        "outcomes":dict(sorted(outcomes.items())),
        "source_counts":dict(sorted(Counter(r.source for r in results).items())),
        "kind_counts":dict(sorted(Counter(r.opportunity_kind for r in results).items())),
        "direction_counts":dict(sorted(Counter("LONG" if r.direction==1 else "SHORT" for r in results).items())),
        "bars_live":total_live,
        "bar_state_counts":dict(sorted(bar_states.items())),
        "bar_state_pct":{
            k:pct(v,total_live) for k,v in sorted(bar_states.items())
        },
        "bar_strength_counts":dict(sorted(bar_strengths.items())),
        "protect_cause_counts":dict(sorted(protect_causes.items())),
        "target_near_bars":target_near_bars,
        "invalidation_near_bars":invalidation_near_bars,
        "first_fading_progress":_dist([r.first_fading_progress for r in results]),
        "first_exhausted_progress":_dist([r.first_exhausted_progress for r in results]),
        "first_protect_progress":_dist([r.first_protect_progress for r in results]),
        "first_structural_warning_progress":_dist([r.first_structural_warning_progress for r in results]),
        "candidate_channels":{
            "PROTECT_STRICT":_channel_summary(
                results,"first_protect_strict_bar","first_protect_strict_progress",
                "protect_strict_bars","protect_strict_transitions"
            ),
            "FAVORABLE_FADING":_channel_summary(
                results,"first_favorable_fading_bar","first_favorable_fading_progress",
                "favorable_fading_bars","favorable_fading_transitions"
            ),
            "FAVORABLE_EXHAUSTED":_channel_summary(
                results,"first_favorable_exhausted_bar","first_favorable_exhausted_progress",
                "favorable_exhausted_bars","favorable_exhausted_transitions"
            ),
        },
        "state_transitions":sum(r.state_transitions for r in results),
        "warning_to_continuation_transitions":sum(r.warning_to_continuation_transitions for r in results),
        "transitions_per_1000_live_bars":None if not total_live else 1000*sum(r.state_transitions for r in results)/total_live,
        "warning_back_per_1000_live_bars":None if not total_live else 1000*sum(r.warning_to_continuation_transitions for r in results)/total_live,
        "bars_live_distribution":_dist([r.bars_live for r in results]),
        "completed":{
            "episodes":len(completed),
            "with_realization_risk":sum(r.first_realization_bar is not None for r in completed),
            "with_realization_risk_pct":pct(sum(r.first_realization_bar is not None for r in completed),len(completed)),
            "realization_lead_bars":_dist([r.realization_lead_bars for r in completed]),
            "with_protect":sum(r.first_protect_bar is not None for r in completed),
            "with_fading":sum(r.first_fading_bar is not None for r in completed),
        },
        "invalidated":{
            "episodes":len(invalidated),
            "with_protect":sum(r.first_protect_bar is not None for r in invalidated),
            "with_protect_pct":pct(sum(r.first_protect_bar is not None for r in invalidated),len(invalidated)),
            "protect_lead_bars":_dist([r.protect_lead_bars for r in invalidated]),
            "with_fading":sum(r.first_fading_bar is not None for r in invalidated),
            "with_fading_pct":pct(sum(r.first_fading_bar is not None for r in invalidated),len(invalidated)),
            "fading_lead_bars":_dist([r.fading_lead_bars for r in invalidated]),
        },
        "resolved_episodes":len(resolved),
    }


def analyze(tf,datasets,tick):
    ctx=_build_operator_paths(tf,datasets,tick)
    theses,unsupported,confirm_rows=_build_theses(ctx)
    results,bar_states,bar_strengths,protect_causes,target_near_bars,invalidation_near_bars=_evaluate(theses,confirm_rows,ctx)

    by_source={}
    for source in PATH_NAMES:
        subset=[r for r in results if r.source==source]
        if subset:
            # Reconstruct state counts from episode bar totals where possible.
            pseudo_states=Counter({
                "CONTINUATION":sum(r.continuation_bars for r in subset),
                "PROTECT":sum(r.protect_bars for r in subset),
                "REALIZATION_RISK":sum(r.realization_bars for r in subset),
            })
            # Terminal bars are intentionally omitted in per-source saturation;
            # aggregate summary carries exact terminal state counts.
            by_source[source]=_summary(subset,pseudo_states,Counter())

    examples=[]
    data=ctx["data"]
    for r in results:
        if len(examples)>=12:break
        if r.outcome in {"INVALIDATED","COMPLETED","AMBIGUOUS"} and (
            r.first_protect_bar is not None or r.first_realization_bar is not None
        ):
            examples.append({
                "thesis_id":r.thesis_id,
                "source":r.source,
                "kind":r.opportunity_kind,
                "direction":"LONG" if r.direction==1 else "SHORT",
                "confirm_time":_time(data["open_time"][r.confirm_bar]),
                "end_time":_time(data["open_time"][r.end_bar]),
                "outcome":r.outcome,
                "bars_live":r.bars_live,
                "protect_lead_bars":r.protect_lead_bars,
                "realization_lead_bars":r.realization_lead_bars,
                "fading_lead_bars":r.fading_lead_bars,
            })

    return {
        "rows":len(ctx["data"]["close"]),
        "operator_confirm_bars":len(confirm_rows),
        "supported_management_episodes":len(theses),
        "unsupported":dict(sorted(unsupported.items())),
        "summary":_summary(results,bar_states,bar_strengths,protect_causes,target_near_bars,invalidation_near_bars),
        "by_source":by_source,
        "examples":examples,
        "results":[asdict(r) for r in results],
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — Thesis Management V0 evidence",
        "",
        "Research-only market-thesis management after unified operator CONFIRMA.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Episode coverage / outcomes",
        "",
        "| TF | operator confirms | supported | completed | invalidated | ambiguous | superseded | open-end |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        o=x["summary"]["outcomes"]
        lines.append(
            f"| {tf} | {x['operator_confirm_bars']} | {x['supported_management_episodes']} | {o.get('COMPLETED',0)} | {o.get('INVALIDATED',0)} | {o.get('AMBIGUOUS',0)} | {o.get('SUPERSEDED',0)} | {o.get('OPEN_END',0)} |"
        )

    lines += [
        "",
        "## Warning reachability / timing",
        "",
        "| TF | live bars | CONT % | PROTECT % | REALIZATION % | transitions/1000 | warn->CONT/1000 | completed with realization % | realization lead median | invalidated with PROTECT % | PROTECT lead median | invalidated with FADING % | FADING lead median |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"];p=s["bar_state_pct"];c=s["completed"];inv=s["invalidated"]
        lines.append(
            "| {tf} | {live} | {cont} | {prot} | {real} | {trans} | {back} | {cr} | {crl} | {ip} | {ipl} | {ifd} | {ifdl} |".format(
                tf=tf,live=s["bars_live"],
                cont=_fmt(p.get("CONTINUATION")),prot=_fmt(p.get("PROTECT")),real=_fmt(p.get("REALIZATION_RISK")),
                trans=_fmt(s["transitions_per_1000_live_bars"]),back=_fmt(s["warning_back_per_1000_live_bars"]),
                cr=_fmt(c["with_realization_risk_pct"]),crl=_fmt(c["realization_lead_bars"]["median"]),
                ip=_fmt(inv["with_protect_pct"]),ipl=_fmt(inv["protect_lead_bars"]["median"]),
                ifd=_fmt(inv["with_fading_pct"]),ifdl=_fmt(inv["fading_lead_bars"]["median"]),
            )
        )

    lines += [
        "",
        "## Source contribution",
        "",
        "| TF | source | episodes | completed | invalidated | superseded |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        for source,row in x["by_source"].items():
            o=row["outcomes"]
            lines.append(
                f"| {tf} | {source} | {row['episodes']} | {o.get('COMPLETED',0)} | {o.get('INVALIDATED',0)} | {o.get('SUPERSEDED',0)} |"
            )

    lines += [
        "",
        "## V0 cause / progress diagnostics",
        "",
        "| TF | target-near bars | invalid-near bars | EXHAUSTED-only-ish cause bars | structural-warning cause bars | first FADING progress med | first EXHAUSTED progress med | first PROTECT progress med |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"];causes=s["protect_cause_counts"]
        exhausted=sum(v for k,v in causes.items() if "EXHAUSTED" in k)
        structural=sum(v for k,v in causes.items() if "STRUCTURAL_WARNING" in k)
        lines.append(
            f"| {tf} | {s['target_near_bars']} | {s['invalidation_near_bars']} | {exhausted} | {structural} | {_fmt(s['first_fading_progress']['median'])} | {_fmt(s['first_exhausted_progress']['median'])} | {_fmt(s['first_protect_progress']['median'])} |"
        )

    lines += [
        "",
        "## Candidate warning channels — diagnostic only",
        "",
        "| TF | channel | bar saturation % | transitions/1000 | completed reach % | completed lead med | invalidated reach % | invalidated lead med | first progress med |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        for name,c in x["summary"]["candidate_channels"].items():
            all_progress=[]
            for outcome in ("completed","invalidated","superseded"):
                d=c[outcome]["first_progress"]
                if d["count"] and d["median"] is not None:
                    all_progress.append(d["median"])
            progress_med=None if not all_progress else sum(all_progress)/len(all_progress)
            lines.append(
                f"| {tf} | {name} | {_fmt(c['bar_saturation_pct'])} | {_fmt(c['transitions_per_1000_live_bars'])} | {_fmt(c['completed']['reached_pct'])} | {_fmt(c['completed']['lead_bars']['median'])} | {_fmt(c['invalidated']['reached_pct'])} | {_fmt(c['invalidated']['lead_bars']['median'])} | {_fmt(progress_med)} |"
            )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Each episode starts from unified OPERATOR_READINESS_V1 CONFIRMA.",
        "- A later operator CONFIRMA supersedes the previous still-open management thesis.",
        "- Target/invalidation anchors are frozen at confirmation and never moved retrospectively.",
        "- Target hit uses structural intrabar reach; invalidation uses confirmed close, matching accepted Market Map truth semantics.",
        "- Same-bar target + confirmed invalidation is AMBIGUOUS.",
        "- FADING remains diagnostic only in V0.",
        "- Metrics are thesis-behavior diagnostics, not trade profitability or win probability.",
        "- No production Pine/default/profile/panel change.",
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
        "metadata":{
            "symbol":symbol,"code_sha":a.code_sha,"datasets":meta,
            "contract":"docs/design/THESIS_MANAGEMENT.md",
            "operator_readiness":"OPERATOR_READINESS_V1",
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

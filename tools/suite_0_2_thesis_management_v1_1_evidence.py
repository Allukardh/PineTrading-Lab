#!/usr/bin/env python3
"""Capability-aware Thesis Management V1.1 evidence.

Every unified directional operator confirmation creates a management thesis.
Target and invalidation are frozen independently when honestly available.

No synthetic anchors. V1 state thresholds are unchanged.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Sequence

from tools.execution_historical_evidence import distribution, load_dataset, pct, sha256_file
from tools.execution_state_reference import Strength
from tools.momentum_turn_reference import Bar as MomentumBar, calculate as calculate_momentum
from tools.operator_readiness_reference import from_sample, project
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi
from tools.suite_0_2_thesis_management_evidence import (
    PATH_NAMES,
    _build_operator_paths,
    _range_anchor,
    _structural_warning,
)
from tools.suite_0_2_thesis_management_v1_evidence import analyze as analyze_v1
from tools.thesis_management_anchor_reference import (
    AnchorCapability,
    resolve_anchors,
)
from tools.thesis_management_reference import (
    ManagementState,
    classify_management_v1_bar,
)


TIMEFRAMES=("4h","1d")


@dataclass(frozen=True)
class CapabilityThesis:
    thesis_id: str
    confirm_bar: int
    direction: int
    source: str
    opportunity_kind: str
    source_bar: int | None
    target: float | None
    invalidation: float | None
    anchor_capability: str
    target_issue: str | None
    invalidation_issue: str | None


@dataclass(frozen=True)
class V11EpisodeResult:
    thesis_id: str
    source: str
    opportunity_kind: str
    direction: int
    anchor_capability: str
    target_capable: bool
    invalidation_capable: bool
    confirm_bar: int
    end_bar: int
    outcome: str
    bars_live: int
    first_protect_bar: int | None
    first_realization_bar: int | None
    first_protect_progress: float | None
    first_realization_progress: float | None
    protect_lead_bars: int | None
    realization_lead_bars: int | None
    protect_bars: int
    realization_bars: int
    continuation_bars: int
    state_transitions: int
    warning_to_continuation_transitions: int
    realization_entries: int
    realization_run_count: int
    realization_max_run: int
    realization_median_run: float | None


def _dist(values):
    return distribution([float(v) for v in values if v is not None])


def _same_level(a: float,b: float) -> bool:
    tol=1e-9*max(1.0,abs(a),abs(b))
    return abs(a-b)<=tol


def _merge_values(values: Sequence[float]) -> tuple[float | None,bool]:
    xs=[float(v) for v in values]
    if not xs:
        return None,False
    first=xs[0]
    if all(_same_level(first,x) for x in xs[1:]):
        return first,False
    return None,True


def _source_anchor(i,source,direction,ctx):
    snaps=ctx["snaps"]
    trend_frames=ctx["trend_frames"]
    range_frames=ctx["range_frames"]
    range_eps=ctx["range_eps"]

    if source=="FROZEN_0_1":
        return {
            "target":snaps[i].destination,
            "invalidation":snaps[i].invalidation,
            "kind":"PULLBACK_RETEST_0_1",
            "source_bar":snaps[i].thesis_key,
            "target_missing_issue":"TARGET_MISSING",
            "invalidation_missing_issue":"INVALIDATION_MISSING",
        }
    if source=="TREND_OPPORTUNITY_V2":
        f=trend_frames[i]
        return {
            "target":snaps[i].destination,
            "invalidation":snaps[i].invalidation,
            "kind":f.kind.name,
            "source_bar":f.source_bar,
            "target_missing_issue":"TARGET_MISSING",
            "invalidation_missing_issue":"INVALIDATION_MISSING",
        }
    if source=="RANGE_EARLY_ANY1":
        anchor=_range_anchor(i,direction,range_frames[i],range_eps)
        if anchor is None:
            return {
                "target":None,"invalidation":None,"kind":"RANGE_ROTATION",
                "source_bar":range_frames[i].source_bar,
                "target_missing_issue":"RANGE_SOURCE_MAPPING_MISSING",
                "invalidation_missing_issue":"RANGE_SOURCE_MAPPING_MISSING",
            }
        target,invalidation,source_bar=anchor
        return {
            "target":target,"invalidation":invalidation,"kind":"RANGE_ROTATION",
            "source_bar":source_bar,
            "target_missing_issue":"TARGET_MISSING",
            "invalidation_missing_issue":"INVALIDATION_MISSING",
        }
    raise ValueError(f"unknown source {source}")


def _build_capability_theses(ctx):
    data=ctx["data"];paths=ctx["paths"]
    theses=[]
    confirm_rows=[]
    issue_counts=Counter()
    multi_source_count=0

    for i in range(len(data["close"])):
        inputs=[from_sample(name,paths[name][i]) for name in PATH_NAMES]
        p=project(inputs)
        if not p.confirm:
            continue
        confirm_rows.append(i)

        sources=tuple(p.confirming_sources)
        direction=p.direction
        close=float(data["close"][i])
        if direction not in (-1,1):
            issue_counts["NON_DIRECTIONAL_CONFIRM"]+=1
            continue
        if not sources:
            issue_counts["CONFIRM_WITHOUT_SOURCE"]+=1
            continue

        candidates=[]
        for source in sources:
            raw=_source_anchor(i,source,direction,ctx)
            resolved=resolve_anchors(
                direction=direction,
                confirm_close=close,
                target=raw["target"],
                invalidation=raw["invalidation"],
                target_issue_if_missing=raw["target_missing_issue"],
                invalidation_issue_if_missing=raw["invalidation_missing_issue"],
            )
            candidates.append((source,raw,resolved))

        if len(candidates)==1:
            source,raw,resolved=candidates[0]
            source_name=source
            kind=raw["kind"]
            source_bar=raw["source_bar"]
            target=resolved.target
            invalidation=resolved.invalidation
            target_issue=resolved.target_issue
            invalidation_issue=resolved.invalidation_issue
            capability=resolved.capability
        else:
            multi_source_count+=1
            source_name="+".join(sorted(x[0] for x in candidates))
            kind="+".join(sorted(set(x[1]["kind"] for x in candidates)))
            source_bar=None

            target_values=[x[2].target for x in candidates if x[2].target is not None]
            invalid_values=[x[2].invalidation for x in candidates if x[2].invalidation is not None]
            target,target_conflict=_merge_values(target_values)
            invalidation,invalid_conflict=_merge_values(invalid_values)

            target_issue=(
                "MULTI_SOURCE_TARGET_CONFLICT" if target_conflict
                else "TARGET_MISSING_ALL" if target is None else None
            )
            invalidation_issue=(
                "MULTI_SOURCE_INVALIDATION_CONFLICT" if invalid_conflict
                else "INVALIDATION_MISSING_ALL" if invalidation is None else None
            )
            merged=resolve_anchors(
                direction=direction,
                confirm_close=close,
                target=target,
                invalidation=invalidation,
                target_issue_if_missing=target_issue or "TARGET_MISSING_ALL",
                invalidation_issue_if_missing=invalidation_issue or "INVALIDATION_MISSING_ALL",
            )
            target=merged.target
            invalidation=merged.invalidation
            target_issue=merged.target_issue
            invalidation_issue=merged.invalidation_issue
            capability=merged.capability

        if target_issue:
            issue_counts[f"{source_name}/{kind}/{target_issue}"]+=1
        if invalidation_issue:
            issue_counts[f"{source_name}/{kind}/{invalidation_issue}"]+=1

        theses.append(CapabilityThesis(
            thesis_id=f"{source_name}:{direction}:{i}",
            confirm_bar=i,
            direction=direction,
            source=source_name,
            opportunity_kind=kind,
            source_bar=source_bar,
            target=target,
            invalidation=invalidation,
            anchor_capability=capability.value,
            target_issue=target_issue,
            invalidation_issue=invalidation_issue,
        ))

    return theses,confirm_rows,issue_counts,multi_source_count


def _range_structural_warning(thesis,i,ctx):
    if thesis.source!="RANGE_EARLY_ANY1":
        return _structural_warning(thesis,i,ctx)

    f=ctx["range_frames"][i]
    return not (
        f.kind.name=="RANGE_ROTATION"
        and f.source_bar==thesis.source_bar
        and f.direction==thesis.direction
    )


def _realization_runs(states):
    runs=[]
    current=0
    entries=0
    prev=False
    for state in states:
        on=state==ManagementState.REALIZATION_RISK
        if on:
            current+=1
            if not prev:
                entries+=1
        elif current:
            runs.append(current);current=0
        prev=on
    if current:runs.append(current)
    return entries,runs


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

    next_confirm={a:b for a,b in zip(confirm_rows,confirm_rows[1:])}
    results=[]
    state_counts=Counter()
    strength_counts=Counter()

    for th in theses:
        stop_before=next_confirm.get(th.confirm_bar,n)
        confirm_close=float(data["close"][th.confirm_bar])
        initial_target_distance=(
            None if th.target is None
            else th.direction*(th.target-confirm_close)
        )

        first_protect=first_real=None
        first_protect_progress=first_real_progress=None
        protect_bars=real_bars=continuation_bars=0
        transitions=warning_back=0
        prev=None
        states=[]
        outcome="OPEN_END"
        end=min(n-1,stop_before-1)

        for i in range(th.confirm_bar,stop_before):
            pse=pse_long if th.direction==1 else pse_short
            progress=(
                None
                if initial_target_distance is None or initial_target_distance<=0
                else th.direction*(float(data["close"][i])-confirm_close)/initial_target_distance
            )

            mb=classify_management_v1_bar(
                direction=th.direction,
                high=float(data["high"][i]),
                low=float(data["low"][i]),
                close=float(data["close"][i]),
                atr=snaps[i].atr,
                target=th.target,
                invalidation=th.invalidation,
                path_progress=progress,
                momentum=momentum[i].state,
                rsi=rsi[i].state,
                participation=pse[i].state,
                structural_warning=_range_structural_warning(th,i,ctx),
                bar_confirmed=True,
            )
            states.append(mb.state)
            state_counts[mb.state.value]+=1
            strength_counts[mb.strength.name]+=1

            if mb.state==ManagementState.PROTECT:
                protect_bars+=1
                if first_protect is None:
                    first_protect=i;first_protect_progress=progress
            elif mb.state==ManagementState.REALIZATION_RISK:
                real_bars+=1
                if first_real is None:
                    first_real=i;first_real_progress=progress
            elif mb.state==ManagementState.CONTINUATION:
                continuation_bars+=1

            if mb.state not in {
                ManagementState.COMPLETED,
                ManagementState.INVALIDATED,
                ManagementState.AMBIGUOUS,
            }:
                if prev is not None and mb.state!=prev:
                    transitions+=1
                    if (
                        prev in {ManagementState.PROTECT,ManagementState.REALIZATION_RISK}
                        and mb.state==ManagementState.CONTINUATION
                    ):
                        warning_back+=1
                prev=mb.state

            if mb.state==ManagementState.COMPLETED:
                outcome="COMPLETED";end=i;break
            if mb.state==ManagementState.INVALIDATED:
                outcome="INVALIDATED";end=i;break
            if mb.state==ManagementState.AMBIGUOUS:
                outcome="AMBIGUOUS";end=i;break
        else:
            if stop_before<n:
                outcome="SUPERSEDED";end=stop_before-1

        entries,runs=_realization_runs(states)

        def lead(bar):
            return (
                None if bar is None or outcome not in {"COMPLETED","INVALIDATED","AMBIGUOUS"}
                else end-bar
            )

        results.append(V11EpisodeResult(
            thesis_id=th.thesis_id,
            source=th.source,
            opportunity_kind=th.opportunity_kind,
            direction=th.direction,
            anchor_capability=th.anchor_capability,
            target_capable=th.target is not None,
            invalidation_capable=th.invalidation is not None,
            confirm_bar=th.confirm_bar,
            end_bar=end,
            outcome=outcome,
            bars_live=end-th.confirm_bar+1,
            first_protect_bar=first_protect,
            first_realization_bar=first_real,
            first_protect_progress=first_protect_progress,
            first_realization_progress=first_real_progress,
            protect_lead_bars=lead(first_protect),
            realization_lead_bars=lead(first_real),
            protect_bars=protect_bars,
            realization_bars=real_bars,
            continuation_bars=continuation_bars,
            state_transitions=transitions,
            warning_to_continuation_transitions=warning_back,
            realization_entries=entries,
            realization_run_count=len(runs),
            realization_max_run=max(runs) if runs else 0,
            realization_median_run=(
                None if not runs
                else float(sorted(runs)[len(runs)//2])
                if len(runs)%2
                else (sorted(runs)[len(runs)//2-1]+sorted(runs)[len(runs)//2])/2.0
            ),
        ))

    return results,state_counts,strength_counts


def _episode_stats(rows,first_key,lead_key,progress_key):
    reached=[r for r in rows if getattr(r,first_key) is not None]
    return {
        "episodes":len(rows),
        "reached":len(reached),
        "reached_pct":pct(len(reached),len(rows)),
        "lead_bars":_dist([getattr(r,lead_key) for r in reached]),
        "first_progress":_dist([getattr(r,progress_key) for r in reached]),
    }


def _summary(results,state_counts,strength_counts):
    live=sum(r.bars_live for r in results)
    outcomes=Counter(r.outcome for r in results)
    caps=Counter(r.anchor_capability for r in results)
    target_cap=[r for r in results if r.target_capable]
    inv_cap=[r for r in results if r.invalidation_capable]
    completed=[r for r in target_cap if r.outcome=="COMPLETED"]
    invalidated=[r for r in inv_cap if r.outcome=="INVALIDATED"]

    realization_eps=[r for r in results if r.first_realization_bar is not None]
    all_realization_runs=[]
    for r in realization_eps:
        # Per-episode median/max are sufficient for robust persistence summary.
        if r.realization_run_count:
            all_realization_runs.append(r.realization_max_run)

    return {
        "episodes":len(results),
        "anchor_class_counts":dict(sorted(caps.items())),
        "target_capable":len(target_cap),
        "target_capable_pct":pct(len(target_cap),len(results)),
        "invalidation_capable":len(inv_cap),
        "invalidation_capable_pct":pct(len(inv_cap),len(results)),
        "full_anchor":caps["FULL"],
        "full_anchor_pct":pct(caps["FULL"],len(results)),
        "outcomes":dict(sorted(outcomes.items())),
        "source_counts":dict(sorted(Counter(r.source for r in results).items())),
        "direction_counts":dict(sorted(Counter("LONG" if r.direction==1 else "SHORT" for r in results).items())),
        "bars_live":live,
        "state_counts":dict(sorted(state_counts.items())),
        "state_pct":{k:pct(v,live) for k,v in sorted(state_counts.items())},
        "strength_counts":dict(sorted(strength_counts.items())),
        "transitions_per_1000_live_bars":None if not live else 1000*sum(r.state_transitions for r in results)/live,
        "warning_back_per_1000_live_bars":None if not live else 1000*sum(r.warning_to_continuation_transitions for r in results)/live,
        "completed_realization":_episode_stats(
            completed,"first_realization_bar","realization_lead_bars","first_realization_progress"
        ),
        "completed_protect":_episode_stats(
            completed,"first_protect_bar","protect_lead_bars","first_protect_progress"
        ),
        "invalidated_protect":_episode_stats(
            invalidated,"first_protect_bar","protect_lead_bars","first_protect_progress"
        ),
        "invalidated_realization":_episode_stats(
            invalidated,"first_realization_bar","realization_lead_bars","first_realization_progress"
        ),
        "realization_persistence":{
            "episodes_with_realization":len(realization_eps),
            "total_entries":sum(r.realization_entries for r in realization_eps),
            "total_realization_bars":sum(r.realization_bars for r in realization_eps),
            "max_run_overall":max((r.realization_max_run for r in realization_eps),default=0),
            "episode_max_run_distribution":_dist(all_realization_runs),
        },
    }


def _full_parity(v11_results,v1_report):
    old={r["thesis_id"]:r for r in v1_report["results"]}
    fields=(
        "outcome","end_bar","first_protect_bar","first_realization_bar",
        "protect_bars","realization_bars","continuation_bars",
        "state_transitions","warning_to_continuation_transitions",
    )
    checked=0;mismatches=[]
    for r in v11_results:
        if r.anchor_capability!="FULL":
            continue
        o=old.get(r.thesis_id)
        if o is None:
            mismatches.append({"thesis_id":r.thesis_id,"reason":"MISSING_IN_V1"})
            continue
        checked+=1
        diffs={f:{"v11":getattr(r,f),"v1":o.get(f)} for f in fields if getattr(r,f)!=o.get(f)}
        if diffs:
            mismatches.append({"thesis_id":r.thesis_id,"diffs":diffs})
    return {
        "checked_full_episodes":checked,
        "mismatches":len(mismatches),
        "parity_pct":pct(checked-len(mismatches),checked),
        "examples":mismatches[:10],
    }


def analyze(tf,datasets,tick):
    ctx=_build_operator_paths(tf,datasets,tick)
    theses,confirm_rows,issues,multi=_build_capability_theses(ctx)
    results,state_counts,strength_counts=_evaluate(theses,confirm_rows,ctx)

    # Frozen V1 comparator for FULL-anchor parity only.
    v1=analyze_v1(tf,datasets,tick)

    return {
        "rows":len(ctx["data"]["close"]),
        "operator_confirm_bars":len(confirm_rows),
        "management_episodes":len(theses),
        "management_episode_pct":pct(len(theses),len(confirm_rows)),
        "multi_source_confirms":multi,
        "anchor_issue_counts":dict(sorted(issues.items())),
        "summary":_summary(results,state_counts,strength_counts),
        "full_anchor_v1_parity":_full_parity(results,v1),
        "results":[asdict(r) for r in results],
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — Capability-aware Thesis Management V1.1",
        "",
        "Every unified directional CONFIRMA creates a management thesis. Missing anchors remain explicit.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Capability / parity",
        "",
        "| TF | confirms | mgmt episodes | mgmt % | FULL | INV only | TARGET only | NONE | target capable % | invalid capable % | FULL V1 parity % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"];c=s["anchor_class_counts"]
        lines.append(
            f"| {tf} | {x['operator_confirm_bars']} | {x['management_episodes']} | {_fmt(x['management_episode_pct'])} | {c.get('FULL',0)} | {c.get('INVALIDATION_ONLY',0)} | {c.get('TARGET_ONLY',0)} | {c.get('NONE',0)} | {_fmt(s['target_capable_pct'])} | {_fmt(s['invalidation_capable_pct'])} | {_fmt(x['full_anchor_v1_parity']['parity_pct'])} |"
        )

    lines += [
        "",
        "## Management state / outcome",
        "",
        "| TF | CONT % | PROTECT % | REALIZATION % | completed | invalidated | superseded | open-end | invalidated PROTECT % | completed REALIZATION % | invalidated REALIZATION % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"];p=s["state_pct"];o=s["outcomes"]
        ip=s["invalidated_protect"];cr=s["completed_realization"];ir=s["invalidated_realization"]
        lines.append(
            f"| {tf} | {_fmt(p.get('CONTINUATION'))} | {_fmt(p.get('PROTECT'))} | {_fmt(p.get('REALIZATION_RISK'))} | {o.get('COMPLETED',0)} | {o.get('INVALIDATED',0)} | {o.get('SUPERSEDED',0)} | {o.get('OPEN_END',0)} | {_fmt(ip['reached_pct'])} | {_fmt(cr['reached_pct'])} | {_fmt(ir['reached_pct'])} |"
        )

    lines += [
        "",
        "## REALIZATION persistence",
        "",
        "| TF | episodes with realization | entries | realization bars | max consecutive run | median episode max-run |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        r=x["summary"]["realization_persistence"]
        lines.append(
            f"| {tf} | {r['episodes_with_realization']} | {r['total_entries']} | {r['total_realization_bars']} | {r['max_run_overall']} | {_fmt(r['episode_max_run_distribution']['median'])} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- No synthetic target or invalidation is created.",
        "- Missing target disables target-progress / COMPLETED semantics only.",
        "- Missing invalidation disables invalidation-near / INVALIDATED semantics only.",
        "- Strength-based CONTINUATION / PROTECT remains available to all directional management theses.",
        "- FULL-anchor episodes must exactly match V1.",
        "- Outcome denominators are capability-aware.",
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
        "metadata":{
            "symbol":symbol,"code_sha":a.code_sha,"datasets":meta,
            "contract":"capability-aware Management V1.1",
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

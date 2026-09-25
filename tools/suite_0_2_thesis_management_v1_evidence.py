#!/usr/bin/env python3
"""Cross-asset evidence for preregistered Thesis Management V1.

Uses the same operator-confirm thesis episodes and frozen anchors as V0.
No production Pine/default/profile/panel changes.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

from tools.execution_historical_evidence import distribution, load_dataset, pct, sha256_file
from tools.execution_state_reference import Strength
from tools.momentum_turn_reference import Bar as MomentumBar, calculate as calculate_momentum
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi
from tools.suite_0_2_thesis_management_evidence import (
    PATH_NAMES,
    _build_operator_paths,
    _build_theses,
    _structural_warning,
)
from tools.thesis_management_reference import (
    ManagementState,
    classify_management_v1_bar,
)


TIMEFRAMES=("4h","1d")


@dataclass(frozen=True)
class V1EpisodeResult:
    thesis_id: str
    source: str
    opportunity_kind: str
    direction: int
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


def _dist(values):
    return distribution([float(v) for v in values if v is not None])


def _evaluate_v1(theses,confirm_rows,ctx):
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
    state_counts=Counter()
    strength_counts=Counter()

    for th in theses:
        stop_before=next_confirm.get(th.confirm_bar,n)
        confirm_close=float(data["close"][th.confirm_bar])
        initial_target_distance=th.direction*(th.target-confirm_close)

        first_protect=first_real=None
        first_protect_progress=first_real_progress=None
        protect_bars=real_bars=continuation_bars=0
        transitions=warning_back=0
        prev=None
        outcome="OPEN_END"
        end=min(n-1,stop_before-1)

        for i in range(th.confirm_bar,stop_before):
            pse=pse_long if th.direction==1 else pse_short
            progress=(
                None if initial_target_distance<=0
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
                structural_warning=_structural_warning(th,i,ctx),
                bar_confirmed=True,
            )

            state_counts[mb.state.value]+=1
            strength_counts[mb.strength.name]+=1

            if mb.state==ManagementState.PROTECT:
                protect_bars+=1
                if first_protect is None:
                    first_protect=i
                    first_protect_progress=progress
            elif mb.state==ManagementState.REALIZATION_RISK:
                real_bars+=1
                if first_real is None:
                    first_real=i
                    first_real_progress=progress
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
                outcome="SUPERSEDED"
                end=stop_before-1

        def lead(bar):
            return None if bar is None or outcome not in {"COMPLETED","INVALIDATED","AMBIGUOUS"} else end-bar

        results.append(V1EpisodeResult(
            thesis_id=th.thesis_id,
            source=th.source,
            opportunity_kind=th.opportunity_kind,
            direction=th.direction,
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
    completed=[r for r in results if r.outcome=="COMPLETED"]
    invalidated=[r for r in results if r.outcome=="INVALIDATED"]
    superseded=[r for r in results if r.outcome=="SUPERSEDED"]

    return {
        "episodes":len(results),
        "outcomes":dict(sorted(outcomes.items())),
        "source_counts":dict(sorted(Counter(r.source for r in results).items())),
        "kind_counts":dict(sorted(Counter(r.opportunity_kind for r in results).items())),
        "direction_counts":dict(sorted(Counter("LONG" if r.direction==1 else "SHORT" for r in results).items())),
        "bars_live":live,
        "state_counts":dict(sorted(state_counts.items())),
        "state_pct":{k:pct(v,live) for k,v in sorted(state_counts.items())},
        "strength_counts":dict(sorted(strength_counts.items())),
        "transitions":sum(r.state_transitions for r in results),
        "transitions_per_1000_live_bars":None if not live else 1000*sum(r.state_transitions for r in results)/live,
        "warning_to_continuation_transitions":sum(r.warning_to_continuation_transitions for r in results),
        "warning_back_per_1000_live_bars":None if not live else 1000*sum(r.warning_to_continuation_transitions for r in results)/live,
        "completed":{
            "protect":_episode_stats(completed,"first_protect_bar","protect_lead_bars","first_protect_progress"),
            "realization":_episode_stats(completed,"first_realization_bar","realization_lead_bars","first_realization_progress"),
        },
        "invalidated":{
            "protect":_episode_stats(invalidated,"first_protect_bar","protect_lead_bars","first_protect_progress"),
            "realization":_episode_stats(invalidated,"first_realization_bar","realization_lead_bars","first_realization_progress"),
        },
        "superseded":{
            "protect":_episode_stats(superseded,"first_protect_bar","protect_lead_bars","first_protect_progress"),
            "realization":_episode_stats(superseded,"first_realization_bar","realization_lead_bars","first_realization_progress"),
        },
    }


def _source_summary(results):
    out={}
    for source in PATH_NAMES:
        rows=[r for r in results if r.source==source]
        if not rows:continue
        out[source]={
            "episodes":len(rows),
            "outcomes":dict(sorted(Counter(r.outcome for r in rows).items())),
            "protect_reach":sum(r.first_protect_bar is not None for r in rows),
            "realization_reach":sum(r.first_realization_bar is not None for r in rows),
        }
    return out


def analyze(tf,datasets,tick):
    ctx=_build_operator_paths(tf,datasets,tick)
    theses,unsupported,confirm_rows=_build_theses(ctx)
    results,state_counts,strength_counts=_evaluate_v1(theses,confirm_rows,ctx)
    return {
        "rows":len(ctx["data"]["close"]),
        "operator_confirm_bars":len(confirm_rows),
        "supported_management_episodes":len(theses),
        "unsupported":dict(sorted(unsupported.items())),
        "unsupported_pct":pct(sum(unsupported.values()),len(confirm_rows)),
        "summary":_summary(results,state_counts,strength_counts),
        "by_source":_source_summary(results),
        "results":[asdict(r) for r in results],
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — Thesis Management V1 evidence",
        "",
        "Preregistered V1; same operator-confirm episodes and frozen anchors as V0.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## State / outcome summary",
        "",
        "| TF | confirms | supported | unsupported % | completed | invalidated | superseded | CONT % | PROTECT % | REALIZATION % | transitions/1000 | warn->CONT/1000 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"];o=s["outcomes"];p=s["state_pct"]
        lines.append(
            f"| {tf} | {x['operator_confirm_bars']} | {x['supported_management_episodes']} | {_fmt(x['unsupported_pct'])} | {o.get('COMPLETED',0)} | {o.get('INVALIDATED',0)} | {o.get('SUPERSEDED',0)} | {_fmt(p.get('CONTINUATION'))} | {_fmt(p.get('PROTECT'))} | {_fmt(p.get('REALIZATION_RISK'))} | {_fmt(s['transitions_per_1000_live_bars'])} | {_fmt(s['warning_back_per_1000_live_bars'])} |"
        )

    lines += [
        "",
        "## Outcome-conditioned warning reach",
        "",
        "| TF | completed realization % | realization lead med | invalidated realization % | invalidated PROTECT % | PROTECT lead med | completed PROTECT % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        s=x["summary"]
        cr=s["completed"]["realization"]; ir=s["invalidated"]["realization"]
        ip=s["invalidated"]["protect"]; cp=s["completed"]["protect"]
        lines.append(
            f"| {tf} | {_fmt(cr['reached_pct'])} | {_fmt(cr['lead_bars']['median'])} | {_fmt(ir['reached_pct'])} | {_fmt(ip['reached_pct'])} | {_fmt(ip['lead_bars']['median'])} | {_fmt(cp['reached_pct'])} |"
        )

    lines += [
        "",
        "## Source breadth",
        "",
        "| TF | source | episodes | completed | invalidated | protect reach | realization reach |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        for source,row in x["by_source"].items():
            o=row["outcomes"]
            lines.append(
                f"| {tf} | {source} | {row['episodes']} | {o.get('COMPLETED',0)} | {o.get('INVALIDATED',0)} | {row['protect_reach']} | {row['realization_reach']} |"
            )

    lines += [
        "",
        "## Guardrails",
        "",
        "- V1 was preregistered before this implementation.",
        "- 0.50 is the frozen structural midpoint; no threshold search.",
        "- Structural warning is telemetry only and cannot directly surface PROTECT.",
        "- Invalidation-near overrides favorable realization classification.",
        "- Target/invalidation anchors remain frozen at operator CONFIRMA.",
        "- Same-bar target + confirmed invalidation remains AMBIGUOUS.",
        "- Metrics are thesis-behavior diagnostics, not trade win probability.",
        "- No production Pine/default/profile/panel change.",
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
            "symbol":symbol,
            "code_sha":a.code_sha,
            "datasets":meta,
            "contract":"Management V1 preregistered in docs/worklog/2026-09-25-suite-0.2-thesis-management.md",
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

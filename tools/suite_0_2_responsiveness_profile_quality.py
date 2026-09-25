#!/usr/bin/env python3
"""Refined Suite 0.2 responsiveness/profile quality evidence.

Closes two preregistered BTC discriminants:

1) ANTECIPADO_TREND
   - only unified newly-ARMED events whose selected source includes
     TREND_OPPORTUNITY_V2;
   - conversion is resolved against TREND_OPPORTUNITY_V2 itself;
   - retrospective structural outcome is attached from the independent
     Opportunity episode label.

2) CONFIRMADO +1 quality
   - PADRAO remains exact unified CONFIRMA;
   - +1 persistence survival/rejection is compared against capability-aware
     Thesis Management V1.1 outcomes.

Research-only. No internal path, threshold, Pine, default or panel is changed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from tools.execution_historical_evidence import distribution, load_dataset, pct, sha256_file
from tools.operator_readiness_reference import from_sample, project
from tools.opportunity_episode_reference import OpportunityType, detect_episodes
from tools.opportunity_outcome_reference import classify_all
from tools.opportunity_execution_counterfactual import OpportunityKind
from tools.responsiveness_profile_reference import (
    ProfileEvent,
    ProfileMode,
    anticipated_events,
    resolve_anticipated,
    resolve_confirmed,
    standard_events,
)
from tools.suite_0_2_thesis_management_evidence import PATH_NAMES, _build_operator_paths
from tools.suite_0_2_thesis_management_v1_1_evidence import analyze as analyze_management_v11


TIMEFRAMES=("4h","1d")
TREND_PATH="TREND_OPPORTUNITY_V2"


def _dist(values):
    return distribution([float(v) for v in values if v is not None])


def _projections(ctx):
    paths=ctx["paths"]
    ps=[]; rows=[]
    for i in range(len(ctx["data"]["close"])):
        row={name:from_sample(name,paths[name][i]) for name in PATH_NAMES}
        rows.append(row)
        ps.append(project(row.values()))
    return ps,rows


def _kind_to_type(kind: OpportunityKind):
    if kind==OpportunityKind.BREAKOUT_EXPANSION:
        return OpportunityType.BREAKOUT_CANDIDATE
    if kind==OpportunityKind.REACCELERATION:
        return OpportunityType.REACCELERATION
    if kind==OpportunityKind.REGIME_REVERSAL:
        return OpportunityType.REGIME_REVERSAL
    return None


def _match_episode(event,ctx,episodes):
    frame=ctx["trend_frames"][event.bar]
    expected=_kind_to_type(frame.kind)
    if (
        expected is None
        or frame.source_bar is None
        or frame.direction!=event.direction
    ):
        return None

    matches=[
        e for e in episodes
        if e.opportunity_type==expected
        and e.confirmation_bar==frame.source_bar
        and e.direction==event.direction
    ]
    return matches[0] if len(matches)==1 else None


def _structural_group(rows):
    n=len(rows)
    outcomes=Counter(r["outcome"] for r in rows)
    return {
        "events":n,
        "outcome_counts":dict(sorted(outcomes.items())),
        "held":outcomes["BREAKOUT_HELD"],
        "fakeout":outcomes["BREAKOUT_FAKEOUT"],
        "unresolved":outcomes["BREAKOUT_UNRESOLVED"],
        "not_applicable":outcomes["NOT_APPLICABLE"],
        "held_pct_resolved":pct(
            outcomes["BREAKOUT_HELD"],
            outcomes["BREAKOUT_HELD"]+outcomes["BREAKOUT_FAKEOUT"],
        ),
        "fakeout_pct_resolved":pct(
            outcomes["BREAKOUT_FAKEOUT"],
            outcomes["BREAKOUT_HELD"]+outcomes["BREAKOUT_FAKEOUT"],
        ),
    }


def _trend_early_quality(ctx,projections,path_rows):
    data=ctx["data"]; snaps=ctx["snaps"]
    all_early=anticipated_events(projections)
    early=[
        e for e in all_early
        if TREND_PATH in e.sources
        and ctx["trend_frames"][e.bar].kind in {
            OpportunityKind.BREAKOUT_EXPANSION,
            OpportunityKind.REACCELERATION,
            OpportunityKind.REGIME_REVERSAL,
        }
    ]

    # Conversion must be earned by TREND itself; another accepted path cannot
    # rescue an early TREND posture.
    trend_events=[
        ProfileEvent(
            ProfileMode.ANTECIPADO,
            e.bar,
            e.direction,
            (TREND_PATH,),
            None,
        )
        for e in early
    ]
    resolved=[resolve_anticipated(e,path_rows) for e in trend_events]

    episodes=detect_episodes(snaps,data["high"],data["low"])
    outcomes=classify_all(episodes,snaps)

    rows=[]
    unmatched=0
    for original,trend_event,res in zip(early,trend_events,resolved):
        ep=_match_episode(original,ctx,episodes)
        if ep is None:
            unmatched+=1
            continue
        out=outcomes[ep.episode_id]
        kind=ctx["trend_frames"][original.bar].kind.name

        displacement=None
        if res.converted and res.confirm_bar is not None:
            atr=snaps[original.bar].atr
            if atr is not None and atr>0:
                displacement=(
                    original.direction*(
                        float(data["close"][res.confirm_bar])
                        -float(data["close"][original.bar])
                    )/atr
                )
        duration=(
            None if res.end_bar is None
            else res.end_bar-original.bar
        )

        rows.append({
            "bar":original.bar,
            "direction":original.direction,
            "kind":kind,
            "source_bar":ctx["trend_frames"][original.bar].source_bar,
            "episode_id":ep.episode_id,
            "outcome":out.outcome.value,
            "converted":res.converted,
            "confirm_bar":res.confirm_bar,
            "bars_to_confirm":res.bars_to_confirm,
            "directional_displacement_to_confirm_atr":displacement,
            "nonconverted_duration_bars":None if res.converted else duration,
        })

    groups={}
    for kind in ("BREAKOUT_EXPANSION","REACCELERATION","REGIME_REVERSAL"):
        kr=[r for r in rows if r["kind"]==kind]
        converted=[r for r in kr if r["converted"]]
        nonconverted=[r for r in kr if not r["converted"]]
        groups[kind]={
            "all":_structural_group(kr),
            "converted":_structural_group(converted),
            "nonconverted":_structural_group(nonconverted),
            "conversion_pct":pct(len(converted),len(kr)),
            "bars_saved":_dist([r["bars_to_confirm"] for r in converted]),
            "move_waiting_atr":_dist([
                r["directional_displacement_to_confirm_atr"]
                for r in converted
            ]),
            "nonconverted_duration":_dist([
                r["nonconverted_duration_bars"] for r in nonconverted
            ]),
            "quick_nonconverted_le_3_pct":pct(
                sum(
                    r["nonconverted_duration_bars"] is not None
                    and r["nonconverted_duration_bars"]<=3
                    for r in nonconverted
                ),
                len(kr),
            ),
        }

    converted=[r for r in rows if r["converted"]]
    nonconverted=[r for r in rows if not r["converted"]]
    return {
        "events":len(rows),
        "unmatched_events":unmatched,
        "converted":len(converted),
        "conversion_pct":pct(len(converted),len(rows)),
        "nonconverted":len(nonconverted),
        "by_kind":groups,
        "rows":rows,
    }


def _management_quality(ctx,projections,path_rows,datasets,tf,tick):
    standard=standard_events(projections)
    resolutions=[resolve_confirmed(e,projections,path_rows) for e in standard]

    management=analyze_management_v11(tf,datasets,tick)
    mgmt_rows=management["results"]
    by_key=defaultdict(list)
    for r in mgmt_rows:
        by_key[(r["confirm_bar"],r["direction"])].append(r)

    joined=[]
    unmatched=0
    for ev,res in zip(standard,resolutions):
        matches=by_key[(ev.bar,ev.direction)]
        if len(matches)!=1:
            unmatched+=1
            continue
        m=matches[0]
        joined.append({
            "bar":ev.bar,
            "direction":ev.direction,
            "sources":list(ev.sources),
            "survived":res.survived,
            "reason":res.reason,
            "confirmed_bar":(
                None if res.confirmed_event is None
                else res.confirmed_event.bar
            ),
            "outcome":m["outcome"],
            "anchor_capability":m["anchor_capability"],
            "management_source":m["source"],
            "opportunity_kind":m["opportunity_kind"],
            "bars_live":m["bars_live"],
            "first_protect_bar":m["first_protect_bar"],
            "first_realization_bar":m["first_realization_bar"],
        })

    survived=[r for r in joined if r["survived"]]
    rejected=[r for r in joined if not r["survived"]]

    def group(xs):
        return {
            "events":len(xs),
            "outcomes":dict(sorted(Counter(r["outcome"] for r in xs).items())),
            "anchor_classes":dict(sorted(Counter(
                r["anchor_capability"] for r in xs
            ).items())),
            "management_sources":dict(sorted(Counter(
                r["management_source"] for r in xs
            ).items())),
            "opportunity_kinds":dict(sorted(Counter(
                r["opportunity_kind"] for r in xs
            ).items())),
            "direction_counts":dict(sorted(Counter(
                "LONG" if r["direction"]==1 else "SHORT" for r in xs
            ).items())),
        }

    return {
        "padrao_events":len(standard),
        "matched":len(joined),
        "unmatched":unmatched,
        "survived":group(survived),
        "rejected":group(rejected),
        "rejection_reasons":dict(sorted(Counter(
            r["reason"] for r in rejected
        ).items())),
        "rows":joined,
    }


def analyze(tf,datasets,tick):
    ctx=_build_operator_paths(tf,datasets,tick)
    projections,path_rows=_projections(ctx)

    return {
        "ANTECIPADO_TREND":_trend_early_quality(
            ctx,projections,path_rows
        ),
        "CONFIRMADO_QUALITY":_management_quality(
            ctx,projections,path_rows,datasets,tf,tick
        ),
        "PADRAO_operator_confirms":sum(p.confirm for p in projections),
        "internal_paths_mutated":False,
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — Refined responsiveness/profile quality evidence",
        "",
        "BTC-only preregistered quality gate. No internal path or threshold changed.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## ANTECIPADO_TREND structural quality",
        "",
        "| TF | kind | events | conversion % | converted held/fakeout | converted held % resolved | nonconverted held/fakeout | nonconverted held % resolved | lead bars med | move waiting ATR med |",
        "| --- | --- | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        for kind,g in x["ANTECIPADO_TREND"]["by_kind"].items():
            c=g["converted"];n=g["nonconverted"]
            lines.append(
                f"| {tf} | {kind} | {g['all']['events']} | {_fmt(g['conversion_pct'])} | {c['held']}/{c['fakeout']} | {_fmt(c['held_pct_resolved'])} | {n['held']}/{n['fakeout']} | {_fmt(n['held_pct_resolved'])} | {_fmt(g['bars_saved']['median'])} | {_fmt(g['move_waiting_atr']['median'])} |"
            )

    lines += [
        "",
        "## CONFIRMADO +1 thesis quality",
        "",
        "| TF | PADRÃO | +1 survived | +1 rejected | survived outcomes | rejected outcomes | rejected reasons |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for tf,x in report["timeframes"].items():
        q=x["CONFIRMADO_QUALITY"]
        lines.append(
            f"| {tf} | {q['padrao_events']} | {q['survived']['events']} | {q['rejected']['events']} | {json.dumps(q['survived']['outcomes'],sort_keys=True)} | {json.dumps(q['rejected']['outcomes'],sort_keys=True)} | {json.dumps(q['rejection_reasons'],sort_keys=True)} |"
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- ANTECIPADO_TREND conversion is earned only by TREND_OPPORTUNITY_V2; another path cannot rescue it.",
        "- BREAKOUT_HELD/FAKEOUT diagnostics are retrospective structural labels, not trade win rates.",
        "- Strict REGIME_REVERSAL remains NOT_APPLICABLE to held/fakeout quality.",
        "- CONFIRMADO quality uses capability-aware Management V1.1 outcomes; missing anchors are not synthesized.",
        "- PADRÃO remains exact OPERATOR_READINESS_V1 confirmation.",
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
    symbol=a.symbol.upper(); market=canonical.get("market","spot")
    datasets={};meta={}
    for tf in ("4h","1d","1w"):
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        dig=sha256_file(p); exp=expected[tf]
        if dig!=exp["dataset_sha256"]:
            raise SystemExit(f"{symbol} {tf}: SHA mismatch")
        ds=load_dataset(p)
        if len(ds["close"])!=exp["candles"]:
            raise SystemExit(f"{symbol} {tf}: row mismatch")
        datasets[tf]=ds; meta[tf]={"rows":len(ds["close"]),"sha256":dig}

    report={
        "metadata":{"symbol":symbol,"code_sha":a.code_sha,"datasets":meta},
        "timeframes":{tf:analyze(tf,datasets,a.tick_size) for tf in TIMEFRAMES},
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report); a.output_md.write_text(md+"\n"); print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

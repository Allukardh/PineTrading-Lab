#!/usr/bin/env python3
"""Phase F1 integrated readiness/profile evidence.

This gate composes accepted Suite 0.2 research layers without retuning them:
- frozen Execution 0.1
- TREND_OPPORTUNITY_V2
- RANGE_EARLY_ANY1
- OPERATOR_READINESS_V1
- final Phase E profile policy
- capability-aware Thesis Management V1.1 thesis creation

The purpose is invariant/integration validation, not profitability scoring.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, pct, sha256_file
from tools.execution_state_reference import Readiness
from tools.operator_readiness_reference import OperatorReadiness
from tools.responsiveness_profile_reference import (
    ProfileEvent,
    ProfileMode,
    anticipated_events,
    anticipated_trend_supported,
    standard_events,
)
from tools.suite_0_2_responsiveness_profile_quality import (
    TREND_PATH,
    _projections,
)
from tools.suite_0_2_thesis_management_evidence import (
    PATH_NAMES,
    _build_operator_paths,
)
from tools.suite_0_2_thesis_management_v1_1_evidence import (
    _build_capability_theses,
)


TIMEFRAMES=("15m","1h","4h","1d","3d","1w")


def _per1000(n,rows):
    return None if not rows else 1000.0*n/rows


def _supported_early_events(tf,ctx,projections):
    raw=anticipated_events(projections)
    supported=[]
    suppressed=Counter()
    raw_trend=0
    multi_source=0

    for e in raw:
        if TREND_PATH not in e.sources:
            suppressed["NON_TREND_SOURCE"]+=1
            continue

        raw_trend+=1
        if len(e.sources)>1:
            multi_source+=1

        frame=ctx["trend_frames"][e.bar]
        kind=frame.kind.name

        if not anticipated_trend_supported(tf,kind):
            if tf=="1w":
                suppressed["UNSUPPORTED_HORIZON_1W"]+=1
            else:
                suppressed[f"UNSUPPORTED_KIND/{kind}"]+=1
            continue

        # Canonical profile event is owned by the TREND path even if another
        # same-direction path happens to share the unified ARMED urgency.
        supported.append(ProfileEvent(
            ProfileMode.ANTECIPADO,
            e.bar,
            e.direction,
            (TREND_PATH,),
            None,
        ))

    return raw,supported,suppressed,raw_trend,multi_source


def analyze(tf,datasets,tick):
    ctx=_build_operator_paths(tf,datasets,tick)
    projections,path_rows=_projections(ctx)
    rows=len(ctx["data"]["close"])

    standard=standard_events(projections)
    raw_early,early,suppressed,raw_trend,multi_source_early=_supported_early_events(
        tf,ctx,projections
    )

    # Projection integrity.
    single_active=0
    single_mismatch=0
    conflict_bars=0
    raw_confirm_bars=0
    raw_confirm_events=0
    raw_confirm_nonconflict_bars=0
    preserved_nonconflict_confirm_bars=0

    for i,(p,row) in enumerate(zip(projections,path_rows)):
        active=[x for x in row.values() if x.readiness!=Readiness.WAIT]
        confirms=[x for x in row.values() if x.confirm]

        if len(active)==1:
            single_active+=1
            x=active[0]
            mapped=OperatorReadiness[x.readiness.name]
            if not (
                p.readiness==mapped
                and p.direction==x.direction
                and not p.conflict
            ):
                single_mismatch+=1

        if p.conflict:
            conflict_bars+=1

        if confirms:
            raw_confirm_bars+=1
            raw_confirm_events+=len(confirms)
            if not p.conflict:
                raw_confirm_nonconflict_bars+=1
                if p.confirm:
                    preserved_nonconflict_confirm_bars+=1

    # PADRÃO is literal unified confirm.
    standard_bars=[e.bar for e in standard]
    projection_confirm_bars=[
        i for i,p in enumerate(projections) if p.confirm
    ]

    # Capability-aware management must be rooted only in unified CONFIRMA.
    theses,management_confirm_rows,anchor_issues,multi_confirms=_build_capability_theses(ctx)
    thesis_bars=[x.confirm_bar for x in theses]

    early_bars=[e.bar for e in early]
    early_kinds=Counter(ctx["trend_frames"][e.bar].kind.name for e in early)
    early_dirs=Counter("LONG" if e.direction==1 else "SHORT" for e in early)

    early_on_conflict=sum(projections[e.bar].conflict for e in early)
    early_same_bar_standard=len(set(early_bars)&set(standard_bars))
    early_same_bar_management=len(set(early_bars)&set(thesis_bars))

    # Explicit policy checks.
    policy_violations=[]
    for e in early:
        f=ctx["trend_frames"][e.bar]
        if TREND_PATH not in e.sources:
            policy_violations.append(f"{e.bar}:NON_TREND")
        if not anticipated_trend_supported(tf,f.kind.name):
            policy_violations.append(f"{e.bar}:UNSUPPORTED/{f.kind.name}")
        if projections[e.bar].readiness!=OperatorReadiness.ARMED:
            policy_violations.append(f"{e.bar}:NOT_UNIFIED_ARMED")
        if projections[e.bar].conflict:
            policy_violations.append(f"{e.bar}:CONFLICT")

    invariants={
        "single_active_parity":single_mismatch==0,
        "padrao_matches_projection_confirms":standard_bars==projection_confirm_bars,
        "management_confirm_rows_match_padrao":management_confirm_rows==standard_bars,
        "management_episode_for_every_confirm":len(theses)==len(management_confirm_rows),
        "anticipated_policy_clean":len(policy_violations)==0,
        "anticipated_never_on_conflict":early_on_conflict==0,
        "anticipated_not_same_bar_as_padrao":early_same_bar_standard==0,
        "anticipated_does_not_start_management":early_same_bar_management==0,
        "nonconflict_raw_confirm_bars_preserved":(
            raw_confirm_nonconflict_bars==preserved_nonconflict_confirm_bars
        ),
        "unsupported_1w_override_zero":(
            True if tf!="1w" else len(early)==0
        ),
    }

    if not all(invariants.values()):
        bad=[k for k,v in invariants.items() if not v]
        raise AssertionError(f"{tf}: Phase F1 invariant failure: {bad}")

    return {
        "rows":rows,
        "invariants":invariants,
        "projection":{
            "single_active_bars":single_active,
            "single_active_mismatches":single_mismatch,
            "conflict_bars":conflict_bars,
            "conflict_bars_per_1000":_per1000(conflict_bars,rows),
            "raw_confirm_events":raw_confirm_events,
            "raw_confirm_bars":raw_confirm_bars,
            "raw_confirm_nonconflict_bars":raw_confirm_nonconflict_bars,
            "operator_confirm_bars":len(standard_bars),
            "preserved_nonconflict_confirm_pct":pct(
                preserved_nonconflict_confirm_bars,
                raw_confirm_nonconflict_bars,
            ),
        },
        "profiles":{
            "padrao_events":len(standard),
            "raw_unified_armed_events":len(raw_early),
            "raw_trend_armed_events":raw_trend,
            "anticipated_supported_events":len(early),
            "anticipated_events_per_1000":_per1000(len(early),rows),
            "anticipated_kind_counts":dict(sorted(early_kinds.items())),
            "anticipated_direction_counts":dict(sorted(early_dirs.items())),
            "suppressed_candidate_counts":dict(sorted(suppressed.items())),
            "multi_selected_source_raw_trend_armed":multi_source_early,
            "policy_violations":policy_violations,
        },
        "management_root":{
            "confirm_rows":len(management_confirm_rows),
            "theses":len(theses),
            "coverage_pct":pct(len(theses),len(management_confirm_rows)),
            "multi_source_confirms":multi_confirms,
            "anchor_issue_counts":dict(sorted(anchor_issues.items())),
            "anticipated_same_bar_management_starts":early_same_bar_management,
        },
        "internal_paths_mutated":False,
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — Phase F1 integrated readiness/profile evidence",
        "",
        "Composition/invariant gate. No engine threshold or production Pine behavior is changed.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Integrated projection",
        "",
        "| TF | rows | PADRÃO confirms | raw trend ARMED | ANTECIPADO supported | early/1000 | conflicts/1000 | nonconflict confirm preserved % | mgmt coverage % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,x in report["timeframes"].items():
        p=x["projection"];q=x["profiles"];m=x["management_root"]
        lines.append(
            f"| {tf} | {x['rows']} | {q['padrao_events']} | {q['raw_trend_armed_events']} | {q['anticipated_supported_events']} | {_fmt(q['anticipated_events_per_1000'])} | {_fmt(p['conflict_bars_per_1000'])} | {_fmt(p['preserved_nonconflict_confirm_pct'])} | {_fmt(m['coverage_pct'])} |"
        )

    lines += [
        "",
        "## ANTECIPADO scope",
        "",
        "| TF | supported kind counts | LONG | SHORT | suppressed candidates |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for tf,x in report["timeframes"].items():
        q=x["profiles"];d=q["anticipated_direction_counts"]
        lines.append(
            f"| {tf} | `{json.dumps(q['anticipated_kind_counts'],sort_keys=True)}` | {d.get('LONG',0)} | {d.get('SHORT',0)} | `{json.dumps(q['suppressed_candidate_counts'],sort_keys=True)}` |"
        )

    lines += [
        "",
        "## Invariants",
        "",
        "| TF | single-path parity | PADRÃO exact | mgmt rooted in PADRÃO | early policy clean | early conflict-free | early does not start mgmt | 1W override zero |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for tf,x in report["timeframes"].items():
        v=x["invariants"]
        lines.append(
            f"| {tf} | {v['single_active_parity']} | {v['padrao_matches_projection_confirms']} | {v['management_confirm_rows_match_padrao'] and v['management_episode_for_every_confirm']} | {v['anticipated_policy_clean']} | {v['anticipated_never_on_conflict']} | {v['anticipated_does_not_start_management']} | {v['unsupported_1w_override_zero']} |"
        )

    lines += [
        "",
        "## Product semantics under test",
        "",
        "- PADRÃO remains literal unified CONFIRMA.",
        "- ANTECIPADO is an early TREND action posture only for BREAKOUT_EXPANSION / REACCELERATION on 15m/1H/4H/1D/3D.",
        "- 1W, RANGE_ROTATION, pullback/retest/reclaim and strict REGIME_REVERSAL retain PADRÃO semantics.",
        "- ANTECIPADO never creates a Thesis Management episode by itself.",
        "- Opposite active directions remain non-actionable CONFLICT.",
        "- Internal paths remain independently computed.",
        "- 1M remains macro/cycle awareness and is outside this execution-profile gate.",
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
    for tf in TIMEFRAMES:
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        if not p.is_file():
            raise SystemExit(f"missing dataset: {p}")
        dig=sha256_file(p);exp=expected[tf]
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
            "phase":"F1",
            "profile_policy":"PADRAO + scoped ANTECIPADO TREND",
        },
        "timeframes":{
            tf:analyze(tf,datasets,a.tick_size)
            for tf in TIMEFRAMES
        },
    }

    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(
        json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
    )
    md=markdown(report)
    a.output_md.write_text(md+"\n")
    print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""RANGE_ROTATION component-evidence diagnostics.

Measures accepted MTE/RSE/PSE states around structural EDGE_REJECTION
rotations without changing any state definition or readiness rule.
"""
from __future__ import annotations

import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

from tools.execution_historical_evidence import build_context_dirs, load_dataset, pct, sha256_file
from tools.execution_integrated_evidence import to_mm_candles
from tools.execution_state_reference import (
    Momentum, Participation,
    _momentum_aligned, _momentum_strongly_opposes,
)
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.momentum_turn_reference import Bar as MomentumBar, calculate as calculate_momentum
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.range_rotation_opportunity_reference import RangeIntegrationVariant, build_range_opportunity_frames
from tools.range_rotation_reference import (
    RangeOutcome, RangeTrigger, classify_range_rotation, detect_range_rotations,
)
from tools.rsi_state_reference import calculate as calculate_rsi, local_opposes, local_supports


TIMEFRAMES=("4h","1d")


def _feature_row(direction, mte, rse, ctx, pse):
    return {
        "mte_state": mte.state.name,
        "mte_aligned": _momentum_aligned(direction, mte.state),
        "mte_opposed": _momentum_strongly_opposes(direction, mte.state),
        "rsi_state": rse.state.name,
        "rsi_local_supportive": local_supports(direction, rse.state),
        "rsi_local_opposing": local_opposes(direction, rse.state),
        "htf_relation": "ALIGNED" if ctx==direction else "OPPOSING" if ctx==-direction else "NEUTRAL",
        "pse_state": pse.state.name,
    }


def _aggregate(rows):
    n=len(rows)
    if not n:
        return {"episodes":0}
    def count_bool(k): return sum(bool(r[k]) for r in rows)
    return {
        "episodes":n,
        "mte_states":dict(sorted(Counter(r["mte_state"] for r in rows).items())),
        "rsi_states":dict(sorted(Counter(r["rsi_state"] for r in rows).items())),
        "htf_relation":dict(sorted(Counter(r["htf_relation"] for r in rows).items())),
        "pse_states":dict(sorted(Counter(r["pse_state"] for r in rows).items())),
        "mte_aligned_pct":pct(count_bool("mte_aligned"),n),
        "mte_opposed_pct":pct(count_bool("mte_opposed"),n),
        "rsi_local_supportive_pct":pct(count_bool("rsi_local_supportive"),n),
        "rsi_local_opposing_pct":pct(count_bool("rsi_local_opposing"),n),
    }


def _window_aggregate(rows):
    n=len(rows)
    if not n: return {"episodes":0}
    keys=("any_mte_aligned","any_rsi_supportive","any_pse_confirm","any_one_family","any_two_families_same_bar","any_three_families_same_bar")
    return {"episodes":n, **{k+"_pct":pct(sum(r[k] for r in rows),n) for k in keys}}


def analyze(tf,datasets,tick):
    data=datasets[tf]
    snaps=[]
    Kernel(to_mm_candles(data),to_mm_candles(datasets[CONTEXT_TF[tf]]),
           to_mm_candles(datasets["1d"]),to_mm_candles(datasets["1w"]),tf,tick=tick).run(
        integration_rows=snaps,emit_audit=False)

    episodes=[e for e in detect_range_rotations(snaps,data["high"],data["low"],data["close"])
              if e.trigger==RangeTrigger.EDGE_REJECTION]
    outcomes={e.episode_id:classify_range_rotation(e,snaps,data["high"],data["low"],data["close"]) for e in episodes}
    frames=build_range_opportunity_frames(episodes,snaps,data["high"],data["low"],data["close"],
                                          variant=RangeIntegrationVariant.ALL_EDGE)

    mte=calculate_momentum([MomentumBar(float(o),float(h),float(l),float(c))
                            for o,h,l,c in zip(data["open"],data["high"],data["low"],data["close"])])
    rsi_cache={k:calculate_rsi(v["close"]) for k,v in datasets.items()}
    rse=rsi_cache[tf]
    ctx=build_context_dirs(tf,datasets,rsi_cache)
    pb=[ParticipationBar(float(h),float(l),float(c),float(v))
        for h,l,c,v in zip(data["high"],data["low"],data["close"],data["volume"])]
    pse_long=calculate_participation(pb,[1]*len(pb))
    pse_short=calculate_participation(pb,[-1]*len(pb))

    source_rows=[]; accepted_rows=[]; window_rows=[]
    grouped_source=defaultdict(list); grouped_acc=defaultdict(list); grouped_win=defaultdict(list)
    accepted_count=0

    for e in episodes:
        o=outcomes[e.episode_id]
        pse=pse_long if e.direction==1 else pse_short
        label=o.outcome.value

        sr=_feature_row(e.direction,mte[e.confirmation_bar],rse[e.confirmation_bar],ctx[e.confirmation_bar],pse[e.confirmation_bar])
        source_rows.append(sr); grouped_source[label].append(sr)

        ab=e.confirmation_bar+1
        accepted=(ab<len(frames) and frames[ab].source_bar==e.confirmation_bar and frames[ab].stage.name=="ACCEPTED")
        if not accepted:
            continue
        accepted_count+=1
        ar=_feature_row(e.direction,mte[ab],rse[ab],ctx[ab],pse[ab])
        accepted_rows.append(ar); grouped_acc[label].append(ar)

        # Strictly before midpoint; if no midpoint, inspect until structural outcome/end.
        if o.midpoint_bar is not None:
            end=o.midpoint_bar-1
        elif o.outcome_bar is not None:
            end=o.outcome_bar
        else:
            end=min(len(frames)-1,ab+24)
        end=max(ab,end)

        flags={
            "any_mte_aligned":False,"any_rsi_supportive":False,"any_pse_confirm":False,
            "any_one_family":False,"any_two_families_same_bar":False,"any_three_families_same_bar":False,
        }
        for i in range(ab,end+1):
            fm=frames[i]
            if fm.source_bar!=e.confirmation_bar:
                break
            ma=_momentum_aligned(e.direction,mte[i].state)
            rs=local_supports(e.direction,rse[i].state) and ctx[i] != -e.direction
            pc=pse[i].state==Participation.CONFIRM
            families=int(ma)+int(rs)+int(pc)
            flags["any_mte_aligned"] |= ma
            flags["any_rsi_supportive"] |= rs
            flags["any_pse_confirm"] |= pc
            flags["any_one_family"] |= families>=1
            flags["any_two_families_same_bar"] |= families>=2
            flags["any_three_families_same_bar"] |= families>=3
        window_rows.append(flags); grouped_win[label].append(flags)

    return {
        "episodes":len(episodes),
        "accepted_next_bar":accepted_count,
        "accepted_next_bar_pct":pct(accepted_count,len(episodes)),
        "source":_aggregate(source_rows),
        "accepted":_aggregate(accepted_rows),
        "pre_midpoint_window":_window_aggregate(window_rows),
        "by_outcome":{
            k:{
                "source":_aggregate(grouped_source[k]),
                "accepted":_aggregate(grouped_acc[k]),
                "pre_midpoint_window":_window_aggregate(grouped_win[k]),
            } for k in sorted(grouped_source)
        }
    }


def _fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def markdown(report):
    lines=["# Suite 0.2 — RANGE_ROTATION component evidence","",
           "No readiness rule is changed by this report.","",
           f"- symbol: **{report['metadata']['symbol']}**",
           f"- code SHA: `{report['metadata']['code_sha']}`","",
           "## Stage diagnostics","",
           "| TF | episodes | accepted +1 % | source MTE aligned % | source MTE opposed % | accepted RSI supportive % | accepted RSI opposing % | accepted PSE CONFIRM % |",
           "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for tf,x in report["timeframes"].items():
        p=x["accepted"]["pse_states"]; n=x["accepted"].get("episodes",0)
        pse=pct(p.get("CONFIRM",0),n) if n else None
        lines.append(f"| {tf} | {x['episodes']} | {_fmt(x['accepted_next_bar_pct'])} | {_fmt(x['source'].get('mte_aligned_pct'))} | {_fmt(x['source'].get('mte_opposed_pct'))} | {_fmt(x['accepted'].get('rsi_local_supportive_pct'))} | {_fmt(x['accepted'].get('rsi_local_opposing_pct'))} | {_fmt(pse)} |")

    lines+=["","## Evidence observable before midpoint","",
            "| TF | accepted episodes | any MTE aligned % | any RSI supportive % | any PSE confirm % | any 1 family % | any 2 same bar % | all 3 same bar % |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for tf,x in report["timeframes"].items():
        w=x["pre_midpoint_window"]
        lines.append(f"| {tf} | {w['episodes']} | {_fmt(w.get('any_mte_aligned_pct'))} | {_fmt(w.get('any_rsi_supportive_pct'))} | {_fmt(w.get('any_pse_confirm_pct'))} | {_fmt(w.get('any_one_family_pct'))} | {_fmt(w.get('any_two_families_same_bar_pct'))} | {_fmt(w.get('any_three_families_same_bar_pct'))} |")

    lines+=["","## Raw accepted-bar states by structural outcome",""]
    for tf,x in report["timeframes"].items():
        lines += [f"### {tf}",""]
        for outcome,row in x["by_outcome"].items():
            a=row["accepted"]; w=row["pre_midpoint_window"]
            lines += [
                f"- **{outcome}** — accepted episodes: {a.get('episodes',0)}",
                f"  - RSI states: {a.get('rsi_states',{})}",
                f"  - HTF relation: {a.get('htf_relation',{})}",
                f"  - PSE states: {a.get('pse_states',{})}",
                f"  - pre-midpoint any 1 / any 2 same-bar / all 3: {_fmt(w.get('any_one_family_pct'))}% / {_fmt(w.get('any_two_families_same_bar_pct'))}% / {_fmt(w.get('any_three_families_same_bar_pct'))}%",
            ]
    lines += ["","## Guardrails","",
              "- MTE/RSE/PSE definitions are unchanged.",
              "- PSE is evaluated in the rotation direction, not blindly in map direction.",
              "- 'Before midpoint' excludes the midpoint bar when a midpoint is observed.",
              "- Structural outcomes are not profitability claims.",
              "- This report is diagnostic only; it does not authorize a new readiness rule.",""]
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",type=Path,required=True); ap.add_argument("--symbol",default="BTCUSDT")
    ap.add_argument("--canonical-manifest",type=Path,required=True)
    ap.add_argument("--output-json",type=Path,required=True); ap.add_argument("--output-md",type=Path,required=True)
    ap.add_argument("--code-sha",default="unknown"); ap.add_argument("--tick-size",type=float,default=0.01)
    a=ap.parse_args()
    canonical=json.loads(a.canonical_manifest.read_text())
    expected={d["timeframe"]:d for d in canonical["datasets"]}; symbol=a.symbol.upper(); market=canonical.get("market","spot")
    datasets={}; meta={}
    for tf in ("4h","1d","1w"):
        p=a.data_root/market/symbol/"consolidated"/f"{symbol}_{tf}.parquet"
        digest=sha256_file(p); exp=expected[tf]
        if digest!=exp["dataset_sha256"]: raise SystemExit(f"{symbol} {tf}: SHA mismatch")
        ds=load_dataset(p)
        if len(ds["close"])!=exp["candles"]: raise SystemExit(f"{symbol} {tf}: row mismatch")
        datasets[tf]=ds; meta[tf]={"rows":len(ds["close"]),"sha256":digest}
    report={"metadata":{"symbol":symbol,"code_sha":a.code_sha,"datasets":meta},
            "timeframes":{tf:analyze(tf,datasets,a.tick_size) for tf in TIMEFRAMES}}
    a.output_json.parent.mkdir(parents=True,exist_ok=True); a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    md=markdown(report); a.output_md.write_text(md+"\n"); print(md)
    return 0
if __name__=="__main__": raise SystemExit(main())

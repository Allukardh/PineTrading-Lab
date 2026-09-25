#!/usr/bin/env python3
"""15-symbol 3D/1W robustness for accepted Suite 0.2 semantics.

The 3D/1W Market Map contract disables daily reference levels. Therefore this
runner may supply 3D chart data in the unused daily-data constructor slot while
using exact canonical 1W data for weekly levels. This does not change 3D/1W
semantics.

No retuning; research-only.
"""
from __future__ import annotations

import argparse,json,statistics
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import load_dataset,pct
from tools.suite_0_2_native_horizon_evidence import analyze


SYMBOLS=(
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT","ADAUSDT","XRPUSDT",
    "SOLUSDT","UNIUSDT","NEARUSDT","AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)
TFS=("3d","1w")


def _median(xs):
    xs=[float(x) for x in xs if x is not None]
    return None if not xs else statistics.median(xs)


def _aggregate_tf(per_symbol,tf):
    rows=0
    trend_candidates=Counter()
    trend_candidate_outcomes={}
    trend_confirm_counts=Counter()
    trend_confirm_outcomes={}
    symbols_with_trend_confirm=0
    symbols_with_breakout_candidate=0
    symbols_with_range_episode=0
    symbols_with_range_confirm=0

    range_episodes=range_accepted=range_confirms=range_fail=0
    range_outcomes=Counter()
    range_confirm_outcomes=Counter()
    range_room_medians=[]
    range_latency_medians=[]

    op_single_mismatch=op_single_bars=0
    op_conflicts=op_suppressed=op_raw_confirm_bars=op_confirms=0
    fresh_total=fresh_ok=0
    conflict_paths=Counter()

    breakout_latency_medians=[]
    reaccel_latency_medians=[]

    for symbol,item in per_symbol.items():
        x=item[tf];rows+=x["rows"]
        t=x["trend_opportunity_v2"]
        trend_candidates.update(t["candidate_counts"])
        for kind,c in t["candidate_outcomes"].items():
            trend_candidate_outcomes.setdefault(kind,Counter()).update(c)
        trend_confirm_counts.update(t["confirm_counts"])
        for kind,c in t["confirm_outcomes"].items():
            trend_confirm_outcomes.setdefault(kind,Counter()).update(c)
        if sum(t["confirm_counts"].values()):symbols_with_trend_confirm+=1
        if t["candidate_counts"].get("BREAKOUT_EXPANSION",0):symbols_with_breakout_candidate+=1
        breakout_latency_medians.append(t["breakout_expansion"]["latency_minutes"]["median"])
        reaccel_latency_medians.append(t["reacceleration"]["latency_minutes"]["median"])

        r=x["range_early_any1"]
        range_episodes+=r["episodes"]
        range_accepted+=r["accepted_next_bar"]
        range_confirms+=r["confirmed"]
        range_fail+=r["failed_before_mid_confirmed"]
        range_outcomes.update(r["structural_outcomes"])
        range_confirm_outcomes.update(r["confirmed_outcomes"])
        if r["episodes"]:symbols_with_range_episode+=1
        if r["confirmed"]:symbols_with_range_confirm+=1
        range_room_medians.append(r["confirm_room_to_opposite_atr"]["median"])
        range_latency_medians.append(r["latency_minutes"]["median"])

        o=x["operator_readiness_v1"]
        op_single_mismatch+=o["single_active_mismatches"]
        op_single_bars+=o["single_active_bars"]
        op_conflicts+=o["conflict_bars"]
        op_suppressed+=o["suppressed_raw_confirms_by_conflict"]
        op_raw_confirm_bars+=o["raw_confirm_bars"]
        op_confirms+=o["operator_confirm_events"]
        fresh_total+=o["fresh_over_aligned_bars"]
        if o["fresh_surface_ok_pct"] is not None:
            fresh_ok+=round(o["fresh_surface_ok_pct"]*o["fresh_over_aligned_bars"]/100.0)
        conflict_paths.update(o["conflict_path_counts"])

    bo=trend_candidate_outcomes.get("BREAKOUT_EXPANSION",Counter())
    bc=trend_confirm_outcomes.get("BREAKOUT_EXPANSION",Counter())
    ro=trend_candidate_outcomes.get("REACCELERATION",Counter())
    rc=trend_confirm_outcomes.get("REACCELERATION",Counter())

    return {
        "rows":rows,
        "trend":{
            "candidate_counts":dict(sorted(trend_candidates.items())),
            "confirm_counts":dict(sorted(trend_confirm_counts.items())),
            "symbols_with_any_confirm":symbols_with_trend_confirm,
            "symbols_with_breakout_candidate":symbols_with_breakout_candidate,
            "breakout":{
                "held_candidates":bo["BREAKOUT_HELD"],
                "fakeout_candidates":bo["BREAKOUT_FAKEOUT"],
                "held_confirms":bc["BREAKOUT_HELD"],
                "fakeout_confirms":bc["BREAKOUT_FAKEOUT"],
                "held_confirm_coverage_pct":pct(bc["BREAKOUT_HELD"],bo["BREAKOUT_HELD"]),
                "fakeout_confirm_coverage_pct":pct(bc["BREAKOUT_FAKEOUT"],bo["BREAKOUT_FAKEOUT"]),
                "median_of_symbol_latency_medians_minutes":_median(breakout_latency_medians),
            },
            "reacceleration":{
                "held_candidates":ro["BREAKOUT_HELD"],
                "fakeout_candidates":ro["BREAKOUT_FAKEOUT"],
                "held_confirms":rc["BREAKOUT_HELD"],
                "fakeout_confirms":rc["BREAKOUT_FAKEOUT"],
                "held_confirm_coverage_pct":pct(rc["BREAKOUT_HELD"],ro["BREAKOUT_HELD"]),
                "fakeout_confirm_coverage_pct":pct(rc["BREAKOUT_FAKEOUT"],ro["BREAKOUT_FAKEOUT"]),
                "median_of_symbol_latency_medians_minutes":_median(reaccel_latency_medians),
            },
        },
        "range":{
            "episodes":range_episodes,
            "symbols_with_episode":symbols_with_range_episode,
            "accepted_next_bar":range_accepted,
            "accepted_next_bar_pct":pct(range_accepted,range_episodes),
            "confirmed":range_confirms,
            "confirmed_pct":pct(range_confirms,range_episodes),
            "symbols_with_confirm":symbols_with_range_confirm,
            "failed_before_mid_confirmed":range_fail,
            "failed_before_mid_confirmed_pct":pct(range_fail,range_confirms),
            "structural_outcomes":dict(sorted(range_outcomes.items())),
            "confirmed_outcomes":dict(sorted(range_confirm_outcomes.items())),
            "confirmed_midpoint_or_better_pct":pct(
                range_confirm_outcomes["MID_REACHED"]+range_confirm_outcomes["OPPOSITE_REACHED"],
                range_confirms,
            ),
            "confirmed_opposite_reached_pct":pct(range_confirm_outcomes["OPPOSITE_REACHED"],range_confirms),
            "median_of_symbol_room_medians_atr":_median(range_room_medians),
            "median_of_symbol_latency_medians_minutes":_median(range_latency_medians),
        },
        "operator":{
            "single_active_bars":op_single_bars,
            "single_active_mismatches":op_single_mismatch,
            "single_active_parity_pct":pct(op_single_bars-op_single_mismatch,op_single_bars),
            "fresh_over_aligned_bars":fresh_total,
            "fresh_surface_ok_pct":pct(fresh_ok,fresh_total),
            "conflict_bars":op_conflicts,
            "conflict_bars_per_1000":None if not rows else op_conflicts*1000.0/rows,
            "conflict_path_counts":dict(sorted(conflict_paths.items())),
            "raw_confirm_bars":op_raw_confirm_bars,
            "operator_confirms":op_confirms,
            "confirm_preservation_pct":pct(op_confirms,op_raw_confirm_bars),
            "suppressed_raw_confirms":op_suppressed,
        },
    }


def markdown(report):
    lines=[
        "# Suite 0.2 — 15-symbol 3D / 1W robustness",
        "",
        "Accepted semantics unchanged across all symbols. No per-symbol/horizon retuning.",
        "",
        f"- symbols: **{len(report['symbols'])}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Trend Opportunity",
        "",
        "| TF | breakout candidates | held/fakeout confirms | held cov % | fakeout cov % | reaccel candidates | held/fakeout confirms | held cov % | fakeout cov % | symbols any trend confirm |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for tf,a in report["aggregate"].items():
        t=a["trend"];b=t["breakout"];r=t["reacceleration"]
        rc=t["candidate_counts"].get("REACCELERATION",0)
        lines.append(
            f"| {tf} | {t['candidate_counts'].get('BREAKOUT_EXPANSION',0)} | {b['held_confirms']}/{b['fakeout_confirms']} | {b['held_confirm_coverage_pct'] if b['held_confirm_coverage_pct'] is not None else 'n/a'} | {b['fakeout_confirm_coverage_pct'] if b['fakeout_confirm_coverage_pct'] is not None else 'n/a'} | {rc} | {r['held_confirms']}/{r['fakeout_confirms']} | {r['held_confirm_coverage_pct'] if r['held_confirm_coverage_pct'] is not None else 'n/a'} | {r['fakeout_confirm_coverage_pct'] if r['fakeout_confirm_coverage_pct'] is not None else 'n/a'} | {t['symbols_with_any_confirm']} |"
        )

    lines += [
        "",
        "## RANGE_ROTATION",
        "",
        "| TF | episodes | symbols with episodes | +1 accepted % | confirms | symbols with confirms | failed confirms | midpoint+ confirmed % | opposite confirmed % | room ATR med-of-medians |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,a in report["aggregate"].items():
        r=a["range"]
        lines.append(
            f"| {tf} | {r['episodes']} | {r['symbols_with_episode']} | {r['accepted_next_bar_pct'] if r['accepted_next_bar_pct'] is not None else 'n/a'} | {r['confirmed']} | {r['symbols_with_confirm']} | {r['failed_before_mid_confirmed']} | {r['confirmed_midpoint_or_better_pct'] if r['confirmed_midpoint_or_better_pct'] is not None else 'n/a'} | {r['confirmed_opposite_reached_pct'] if r['confirmed_opposite_reached_pct'] is not None else 'n/a'} | {r['median_of_symbol_room_medians_atr'] if r['median_of_symbol_room_medians_atr'] is not None else 'n/a'} |"
        )

    lines += [
        "",
        "## OPERATOR_READINESS_V1",
        "",
        "| TF | single parity % | fresh-over-ALIGNED | fresh surfaced % | conflicts | conflict/1000 | raw confirm bars | operator confirms | suppressed by conflict |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf,a in report["aggregate"].items():
        o=a["operator"]
        lines.append(
            f"| {tf} | {o['single_active_parity_pct'] if o['single_active_parity_pct'] is not None else 'n/a'} | {o['fresh_over_aligned_bars']} | {o['fresh_surface_ok_pct'] if o['fresh_surface_ok_pct'] is not None else 'n/a'} | {o['conflict_bars']} | {o['conflict_bars_per_1000']:.3f} | {o['raw_confirm_bars']} | {o['operator_confirms']} | {o['suppressed_raw_confirms']} |"
        )

    lines += [
        "",
        "## Per-symbol breadth",
        "",
        "| symbol | 3D breakout/reaccel/range episodes | 3D trend/range confirms | 1W breakout/reaccel/range episodes | 1W trend/range confirms |",
        "| --- | --- | --- | --- | --- |",
    ]
    for s,x in report["symbols"].items():
        def side(tf):
            t=x[tf]["trend_opportunity_v2"];r=x[tf]["range_early_any1"]
            episodes=f"{t['candidate_counts'].get('BREAKOUT_EXPANSION',0)}/{t['candidate_counts'].get('REACCELERATION',0)}/{r['episodes']}"
            confirms=f"{sum(t['confirm_counts'].values())}/{r['confirmed']}"
            return episodes,confirms
        e3,c3=side("3d");ew,cw=side("1w")
        lines.append(f"| {s} | {e3} | {c3} | {ew} | {cw} |")

    lines += [
        "",
        "## Guardrails",
        "",
        "- 3D and 1W use self-confirmed HTF context per the accepted kernel.",
        "- Daily reference levels are disabled on 3D/1W by contract; the runner does not invent daily inputs.",
        "- Structural outcomes are not profitability claims.",
        "- Sparse per-symbol rows are interpreted through the aggregate universe.",
        "- No tuning, profiles or production Pine changes.",
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

    per={}
    for symbol in SYMBOLS:
        base=a.data_root/"spot"/symbol/"consolidated"
        d3=load_dataset(base/f"{symbol}_3d.parquet")
        w=load_dataset(base/f"{symbol}_1w.parquet")
        # daily slot is unused on 3D/1W because DAY_LEVEL_TFS excludes both.
        datasets={"3d":d3,"1w":w,"1d":d3}
        per[symbol]={
            tf:analyze(tf,datasets,a.tick_size)
            for tf in TFS
        }

    report={
        "metadata":{
            "code_sha":a.code_sha,
            "symbols":list(SYMBOLS),
            "timeframes":list(TFS),
        },
        "symbols":per,
        "aggregate":{
            tf:_aggregate_tf(per,tf)
            for tf in TFS
        },
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report);a.output_md.write_text(md+"\n");print(md)
    return 0

if __name__=="__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare fixed vs elapsed-time-equivalent monthly Market Map regime basis.

Pre-registered variants:
- FIXED_21_50_200: regime actually consumes MID=50 / SLOW=200.
- WEEK_EQUIV_5_12_46: regime consumes MID=12 / SLOW=46.
  FAST=5 is conceptual/visual equivalence only; current regime does not use FAST.

Monthly OHLCV is deterministically derived from accepted 1D data.
No lower-horizon semantics, production Pine, profiles or per-symbol tuning.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.execution_historical_evidence import load_dataset, pct
from tools.execution_integrated_evidence import to_mm_candles
from tools.market_map_offline_core import Kernel
from tools.monthly_aggregation_reference import aggregate_calendar_month, logical_sha256
from tools.suite_0_2_high_horizon_universe import _aggregate_tf
from tools.suite_0_2_native_horizon_evidence import analyze


SYMBOLS=(
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT","ADAUSDT","XRPUSDT",
    "SOLUSDT","UNIUSDT","NEARUSDT","AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)
VARIANTS={
    "FIXED_21_50_200": (50,200),
    "WEEK_EQUIV_5_12_46": (12,46),
}


def _regime_metrics(data,mid_len,slow_len,tick):
    cs=to_mm_candles(data)
    snaps=[]
    Kernel(
        cs,cs,cs,cs,"1M",tick=tick,mid_len=mid_len,slow_len=slow_len
    ).run(integration_rows=snaps,emit_audit=False)

    regime=[s.regime_dir for s in snaps]
    map_dirs=[s.map_dir for s in snaps]
    reg_counts=Counter(regime)
    map_counts=Counter(map_dirs)

    state_changes=sum(regime[i]!=regime[i-1] for i in range(1,len(regime)))
    flips=sum(
        regime[i] in (-1,1) and regime[i-1] in (-1,1) and regime[i]!=regime[i-1]
        for i in range(1,len(regime))
    )
    map_changes=sum(map_dirs[i]!=map_dirs[i-1] for i in range(1,len(map_dirs)))

    first_nonzero=next((i for i,x in enumerate(regime) if x!=0),None)
    first_time=None if first_nonzero is None else data["open_time"][first_nonzero].isoformat()

    n=len(regime)
    directional=reg_counts[1]+reg_counts[-1]
    return {
        "rows":n,
        "mid_len":mid_len,
        "slow_len":slow_len,
        "full_nominal_slow_span_bars":max(0,n-slow_len+1),
        "has_full_nominal_slow_span":n>=slow_len,
        "regime_counts":{
            "BULL":reg_counts[1],
            "NEUTRAL":reg_counts[0],
            "BEAR":reg_counts[-1],
        },
        "regime_directional_pct":pct(directional,n),
        "regime_bull_share_of_directional_pct":pct(reg_counts[1],directional),
        "regime_bear_share_of_directional_pct":pct(reg_counts[-1],directional),
        "regime_state_changes":state_changes,
        "regime_state_changes_per_100":None if not n else state_changes*100.0/n,
        "regime_direction_flips":flips,
        "first_directional_regime_bar":first_nonzero,
        "first_directional_regime_time":first_time,
        "map_counts":{
            "LONG":map_counts[1],
            "NEUTRAL":map_counts[0],
            "SHORT":map_counts[-1],
        },
        "map_directional_pct":pct(map_counts[1]+map_counts[-1],n),
        "map_state_changes":map_changes,
        "map_state_changes_per_100":None if not n else map_changes*100.0/n,
        "structural_conflict_bars":sum(s.structural_conflict for s in snaps),
    }


def _aggregate_regime(per_symbol,variant):
    rows=directional=bull=bear=changes=flips=mapdir=mapchanges=conflicts=0
    symbols_regime=0
    symbols_full_span=0
    first_indices=[]
    for sym,x in per_symbol.items():
        r=x["variants"][variant]["regime"]
        rows+=r["rows"]
        d=r["regime_counts"]["BULL"]+r["regime_counts"]["BEAR"]
        directional+=d
        bull+=r["regime_counts"]["BULL"]
        bear+=r["regime_counts"]["BEAR"]
        changes+=r["regime_state_changes"]
        flips+=r["regime_direction_flips"]
        mapdir+=r["map_counts"]["LONG"]+r["map_counts"]["SHORT"]
        mapchanges+=r["map_state_changes"]
        conflicts+=r["structural_conflict_bars"]
        symbols_regime+=int(d>0)
        symbols_full_span+=int(r["has_full_nominal_slow_span"])
        if r["first_directional_regime_bar"] is not None:
            first_indices.append(r["first_directional_regime_bar"])
    return {
        "rows":rows,
        "symbols_with_directional_regime":symbols_regime,
        "symbols_with_full_nominal_slow_span":symbols_full_span,
        "directional_regime_pct":pct(directional,rows),
        "bull_share_of_directional_pct":pct(bull,directional),
        "bear_share_of_directional_pct":pct(bear,directional),
        "regime_state_changes":changes,
        "regime_state_changes_per_100":None if not rows else changes*100.0/rows,
        "direction_flips":flips,
        "map_directional_pct":pct(mapdir,rows),
        "map_state_changes_per_100":None if not rows else mapchanges*100.0/rows,
        "structural_conflict_bars":conflicts,
        "median_first_directional_bar":(
            None if not first_indices else sorted(first_indices)[len(first_indices)//2]
        ),
    }


def _variant_aggregate(per_symbol,variant):
    shaped={
        sym:{"1M":x["variants"][variant]["evidence"]}
        for sym,x in per_symbol.items()
    }
    return {
        "regime":_aggregate_regime(per_symbol,variant),
        "suite":_aggregate_tf(shaped,"1M"),
    }


def _fmt(x,d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines=[
        "# Suite 0.2 — monthly regime basis comparison",
        "",
        "Pre-registered control vs elapsed-time-equivalent monthly candidate.",
        "",
        f"- symbols: **{len(report['symbols'])}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "- source: deterministic 1M from accepted 1D production candles",
        "",
        "## Direct regime audit",
        "",
        "| variant | symbols directional | symbols full nominal slow span | directional regime % | bull/bear share % | regime changes/100 | direction flips | map directional % | conflicts |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for name,v in report["aggregate"].items():
        r=v["regime"]
        lines.append(
            f"| {name} | {r['symbols_with_directional_regime']} | {r['symbols_with_full_nominal_slow_span']} | {_fmt(r['directional_regime_pct'])} | {_fmt(r['bull_share_of_directional_pct'])}/{_fmt(r['bear_share_of_directional_pct'])} | {_fmt(r['regime_state_changes_per_100'])} | {r['direction_flips']} | {_fmt(r['map_directional_pct'])} | {r['structural_conflict_bars']} |"
        )

    lines += ["","## Trend Opportunity v2","",
        "| variant | breakout candidates | held/fakeout confirms | held cov % | fakeout cov % | reaccel candidates | held/fakeout confirms | held cov % | fakeout cov % | symbols any trend confirm |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |"]
    for name,v in report["aggregate"].items():
        t=v["suite"]["trend"]; b=t["breakout"]; r=t["reacceleration"]
        lines.append(
            f"| {name} | {t['candidate_counts'].get('BREAKOUT_EXPANSION',0)} | {b['held_confirms']}/{b['fakeout_confirms']} | {_fmt(b['held_confirm_coverage_pct'])} | {_fmt(b['fakeout_confirm_coverage_pct'])} | {t['candidate_counts'].get('REACCELERATION',0)} | {r['held_confirms']}/{r['fakeout_confirms']} | {_fmt(r['held_confirm_coverage_pct'])} | {_fmt(r['fakeout_confirm_coverage_pct'])} | {t['symbols_with_any_confirm']} |"
        )

    lines += ["","## RANGE_ROTATION / Operator","",
        "| variant | range episodes | +1 accepted % | range confirms | failed confirms | midpoint+ confirmed % | operator parity % | conflicts | raw/operator confirms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for name,v in report["aggregate"].items():
        rr=v["suite"]["range"]; o=v["suite"]["operator"]
        lines.append(
            f"| {name} | {rr['episodes']} | {_fmt(rr['accepted_next_bar_pct'])} | {rr['confirmed']} | {rr['failed_before_mid_confirmed']} | {_fmt(rr['confirmed_midpoint_or_better_pct'])} | {_fmt(o['single_active_parity_pct'])} | {o['conflict_bars']} | {o['raw_confirm_bars']}/{o['operator_confirms']} |"
        )

    lines += ["","## Per-symbol regime breadth","",
        "| symbol | months | fixed directional % | 12/46 directional % | fixed changes/100 | 12/46 changes/100 | 46-month full span? | fixed/12-46 trend confirms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for sym,x in report["symbols"].items():
        a=x["variants"]["FIXED_21_50_200"]; b=x["variants"]["WEEK_EQUIV_5_12_46"]
        ac=sum(a["evidence"]["trend_opportunity_v2"]["confirm_counts"].values())
        bc=sum(b["evidence"]["trend_opportunity_v2"]["confirm_counts"].values())
        lines.append(
            f"| {sym} | {x['monthly_rows']} | {_fmt(a['regime']['regime_directional_pct'])} | {_fmt(b['regime']['regime_directional_pct'])} | {_fmt(a['regime']['regime_state_changes_per_100'])} | {_fmt(b['regime']['regime_state_changes_per_100'])} | {'YES' if b['regime']['has_full_nominal_slow_span'] else 'NO'} | {ac}/{bc} |"
        )

    lines += ["","## Guardrails","",
        "- The offline EMA is recursively seeded; full nominal slow-span coverage is reported separately from numeric EMA availability.",
        "- WEEK_EQUIV_5_12_46 changes only the regime MID/SLOW lengths to 12/46; FAST=5 is conceptual because FAST is not in regimeDir.",
        "- More signals are not automatically better.",
        "- Candidate acceptance requires usable regime breadth without pathological churn and preserved held/fakeout discrimination.",
        "- SUI has fewer than 46 monthly rows and is explicitly treated as short-history evidence.",
        "- No lower-horizon, production Pine, profile or per-symbol setting changed.",
        ""]
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
    for sym in SYMBOLS:
        daily=load_dataset(a.data_root/"spot"/sym/"consolidated"/f"{sym}_1d.parquet")
        monthly,prov=aggregate_calendar_month(daily)
        datasets={"1M":monthly,"1d":monthly,"1w":monthly}

        variants={}
        for name,(mid,slow) in VARIANTS.items():
            variants[name]={
                "regime":_regime_metrics(monthly,mid,slow,a.tick_size),
                "evidence":analyze(
                    "1M",datasets,a.tick_size,
                    regime_mid_len=mid,
                    regime_slow_len=slow,
                ),
            }

        per[sym]={
            "monthly_rows":len(monthly["close"]),
            "logical_sha256":logical_sha256(monthly),
            "partial_months":sum(
                not (p["starts_on_calendar_day_1"] and p["ends_on_calendar_month_end"])
                for p in prov
            ),
            "variants":variants,
        }

    report={
        "metadata":{
            "code_sha":a.code_sha,
            "variants":{
                "FIXED_21_50_200":{"mid":50,"slow":200},
                "WEEK_EQUIV_5_12_46":{"fast_conceptual":5,"mid":12,"slow":46},
            },
        },
        "symbols":per,
        "aggregate":{
            name:_variant_aggregate(per,name)
            for name in VARIANTS
        },
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report); a.output_md.write_text(md+"\n"); print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

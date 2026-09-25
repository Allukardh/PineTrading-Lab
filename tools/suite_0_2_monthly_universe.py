#!/usr/bin/env python3
"""15-symbol deterministic 1M derivation + Suite 0.2 evidence.

Research-only:
- derives UTC calendar-month OHLCV from accepted 1D production candles;
- never substitutes weekly bars for monthly bars;
- uses self-confirmed monthly context;
- disables daily and weekly reference levels on 1M;
- no per-symbol/horizon retuning;
- no production Pine/default/profile changes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.execution_historical_evidence import load_dataset
from tools.monthly_aggregation_reference import (
    aggregate_calendar_month,
    logical_sha256,
    write_monthly_parquet,
)
from tools.suite_0_2_high_horizon_universe import _aggregate_tf
from tools.suite_0_2_native_horizon_evidence import analyze


SYMBOLS=(
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT","ADAUSDT","XRPUSDT",
    "SOLUSDT","UNIUSDT","NEARUSDT","AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)
TF="1M"


def _prov_summary(prov):
    if not prov:
        return {
            "months":0,
            "full_calendar_months":0,
            "partial_months":0,
            "first_month_partial":None,
            "last_month_partial":None,
        }
    full=sum(
        p["starts_on_calendar_day_1"] and p["ends_on_calendar_month_end"]
        for p in prov
    )
    return {
        "months":len(prov),
        "full_calendar_months":full,
        "partial_months":len(prov)-full,
        "first_month_partial":not (
            prov[0]["starts_on_calendar_day_1"]
            and prov[0]["ends_on_calendar_month_end"]
        ),
        "last_month_partial":not (
            prov[-1]["starts_on_calendar_day_1"]
            and prov[-1]["ends_on_calendar_month_end"]
        ),
        "first_month":f"{prov[0]['year']:04d}-{prov[0]['month']:02d}",
        "last_month":f"{prov[-1]['year']:04d}-{prov[-1]['month']:02d}",
    }


def markdown(report):
    a=report["aggregate"]
    lines=[
        "# Suite 0.2 — deterministic 1M evidence",
        "",
        "Calendar-month OHLCV derived from accepted 1D production data. No weekly substitution.",
        "",
        f"- symbols: **{len(report['symbols'])}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "- 1M context: **self-confirmed monthly**",
        "- daily reference levels: **OFF**",
        "- weekly reference levels: **OFF**",
        "",
        "## Monthly derivation provenance",
        "",
        "| symbol | 1D rows | 1M rows | full months | partial months | EMA200 history available? | logical SHA (12) | parquet SHA (12) |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for sym,x in report["symbols"].items():
        p=x["provenance"]
        lines.append(
            f"| {sym} | {x['daily_rows']} | {x['monthly_rows']} | {p['full_calendar_months']} | {p['partial_months']} | {'YES' if x['ema200_history_available'] else 'NO'} | {x['logical_sha256'][:12]} | {x['parquet_sha256'][:12]} |"
        )

    t=a["trend"]
    b=t["breakout"]; r=t["reacceleration"]
    lines += [
        "",
        "## Trend Opportunity v2",
        "",
        f"- candidate counts: `{json.dumps(t['candidate_counts'],sort_keys=True)}`",
        f"- confirm counts: `{json.dumps(t['confirm_counts'],sort_keys=True)}`",
        f"- symbols with any trend confirmation: **{t['symbols_with_any_confirm']} / {len(report['symbols'])}**",
        "",
        "| class | HELD candidates | FAKEOUT candidates | HELD confirms | FAKEOUT confirms | HELD cov % | FAKEOUT cov % | nominal latency med-of-medians |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| BREAKOUT_EXPANSION | {b['held_candidates']} | {b['fakeout_candidates']} | {b['held_confirms']} | {b['fakeout_confirms']} | {b['held_confirm_coverage_pct'] if b['held_confirm_coverage_pct'] is not None else 'n/a'} | {b['fakeout_confirm_coverage_pct'] if b['fakeout_confirm_coverage_pct'] is not None else 'n/a'} | {b['median_of_symbol_latency_medians_minutes'] if b['median_of_symbol_latency_medians_minutes'] is not None else 'n/a'} min |",
        f"| REACCELERATION | {r['held_candidates']} | {r['fakeout_candidates']} | {r['held_confirms']} | {r['fakeout_confirms']} | {r['held_confirm_coverage_pct'] if r['held_confirm_coverage_pct'] is not None else 'n/a'} | {r['fakeout_confirm_coverage_pct'] if r['fakeout_confirm_coverage_pct'] is not None else 'n/a'} | {r['median_of_symbol_latency_medians_minutes'] if r['median_of_symbol_latency_medians_minutes'] is not None else 'n/a'} min |",
    ]

    rr=a["range"]
    lines += [
        "",
        "## RANGE_ROTATION EARLY_ANY1",
        "",
        f"- episodes: **{rr['episodes']}**",
        f"- symbols with episodes: **{rr['symbols_with_episode']} / {len(report['symbols'])}**",
        f"- +1 accepted: **{rr['accepted_next_bar']} / {rr['episodes']}** ({rr['accepted_next_bar_pct'] if rr['accepted_next_bar_pct'] is not None else 'n/a'}%)",
        f"- confirmations: **{rr['confirmed']}** across **{rr['symbols_with_confirm']}** symbols",
        f"- FAILED_BEFORE_MID confirmed: **{rr['failed_before_mid_confirmed']}**",
        f"- confirmed midpoint+: **{rr['confirmed_midpoint_or_better_pct'] if rr['confirmed_midpoint_or_better_pct'] is not None else 'n/a'}%**",
        f"- confirmed opposite edge: **{rr['confirmed_opposite_reached_pct'] if rr['confirmed_opposite_reached_pct'] is not None else 'n/a'}%**",
        f"- room at confirmation, median-of-symbol medians: **{rr['median_of_symbol_room_medians_atr'] if rr['median_of_symbol_room_medians_atr'] is not None else 'n/a'} ATR**",
    ]

    o=a["operator"]
    lines += [
        "",
        "## OPERATOR_READINESS_V1",
        "",
        f"- single-active parity: **{o['single_active_parity_pct'] if o['single_active_parity_pct'] is not None else 'n/a'}%**",
        f"- fresh-over-ALIGNED surfaced: **{o['fresh_surface_ok_pct'] if o['fresh_surface_ok_pct'] is not None else 'n/a'}%**",
        f"- conflict bars: **{o['conflict_bars']}**",
        f"- raw confirm bars: **{o['raw_confirm_bars']}**",
        f"- operator confirms: **{o['operator_confirms']}**",
        f"- suppressed by conflict: **{o['suppressed_raw_confirms']}**",
        "",
        "## Per-symbol breadth",
        "",
        "| symbol | months | breakout/reaccel/range episodes | trend/range confirms | operator conflicts |",
        "| --- | ---: | --- | --- | ---: |",
    ]
    for sym,x in report["symbols"].items():
        ev=x["evidence"]; t=ev["trend_opportunity_v2"]; rr=ev["range_early_any1"]; op=ev["operator_readiness_v1"]
        episodes=f"{t['candidate_counts'].get('BREAKOUT_EXPANSION',0)}/{t['candidate_counts'].get('REACCELERATION',0)}/{rr['episodes']}"
        confirms=f"{sum(t['confirm_counts'].values())}/{rr['confirmed']}"
        lines.append(f"| {sym} | {x['monthly_rows']} | {episodes} | {confirms} | {op['conflict_bars']} |")

    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- Monthly bars are derived from accepted 1D candles with no synthesized missing days.",
        "- First listing month may be partial; provenance records it explicitly.",
        "- Parquet SHA is writer-byte provenance; logical SHA is stable content provenance.",
        "- 1M uses self-confirmed context only in this research gate.",
        "- Daily and weekly reference levels are disabled on 1M to avoid tactical-level contamination.",
        "- Nominal monthly latency uses 30 days/bar only for scale comparison; actual calendar months vary.",
        "- EMA200 readiness is reported because available monthly history may be structurally insufficient.",
        "- Structural outcomes are not profitability claims.",
        "- No tuning, profiles or production Pine changes.",
        "",
    ]
    return "\n".join(lines)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",type=Path,required=True)
    ap.add_argument("--derived-root",type=Path,required=True)
    ap.add_argument("--output-json",type=Path,required=True)
    ap.add_argument("--output-md",type=Path,required=True)
    ap.add_argument("--code-sha",default="unknown")
    ap.add_argument("--tick-size",type=float,default=.01)
    a=ap.parse_args()

    per={}
    for sym in SYMBOLS:
        src=a.data_root/"spot"/sym/"consolidated"/f"{sym}_1d.parquet"
        daily=load_dataset(src)
        monthly,prov=aggregate_calendar_month(daily)

        dst=a.derived_root/"spot"/sym/"derived"/f"{sym}_1M.parquet"
        parquet_sha=write_monthly_parquet(monthly,dst)
        logical_sha=logical_sha256(monthly)

        # Daily/weekly constructor slots are unused on 1M by the research
        # contract. Supplying monthly data avoids inventing an unrelated source.
        datasets={"1M":monthly,"1d":monthly,"1w":monthly}
        evidence=analyze("1M",datasets,a.tick_size)

        per[sym]={
            "daily_rows":len(daily["close"]),
            "monthly_rows":len(monthly["close"]),
            "logical_sha256":logical_sha,
            "parquet_sha256":parquet_sha,
            "ema200_history_available":len(monthly["close"])>=200,
            "provenance":_prov_summary(prov),
            "evidence":evidence,
        }

    shaped={sym:{"1M":x["evidence"]} for sym,x in per.items()}
    report={
        "metadata":{
            "code_sha":a.code_sha,
            "source_timeframe":"1d",
            "derived_timeframe":"1M",
            "calendar":"UTC",
            "monthly_context":"self_confirmed",
            "daily_reference_levels":False,
            "weekly_reference_levels":False,
        },
        "symbols":per,
        "aggregate":_aggregate_tf(shaped,"1M"),
    }

    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_md.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    md=markdown(report);a.output_md.write_text(md+"\n");print(md)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

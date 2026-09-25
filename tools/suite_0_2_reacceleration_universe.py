#!/usr/bin/env python3
"""Daily REACCELERATION robustness across the accepted 15-symbol universe.

Research-only:
- frozen Market Map 0.1 / Execution 0.1 response
- sequence-based REACCELERATION episode label
- retrospective structural held/fakeout diagnostic
- two-close HOLD_2 structural acceptance

No production Pine/default/profile is changed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from tools.breakout_acceptance_reference import follow_through_bar
from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import build_context_dirs, load_dataset, sha256_file
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.market_map_offline_core import IntegrationSnapshot, Kernel
from tools.opportunity_episode_reference import OpportunityType, detect_episodes
from tools.opportunity_latency_reference import measure_all
from tools.opportunity_outcome_reference import CandidateOutcome, classify_all
from tools.rsi_state_reference import calculate as calculate_rsi
from tools.suite_0_2_latency_baseline import _response_summary


DEFAULT_SYMBOLS = (
    "BTCUSDT","ETHUSDT","AVAXUSDT","DOGEUSDT","DOTUSDT",
    "ADAUSDT","XRPUSDT","SOLUSDT","UNIUSDT","NEARUSDT",
    "AAVEUSDT","HBARUSDT","LINKUSDT","SUIUSDT","LTCUSDT",
)


def _pct(a: int, b: int) -> float | None:
    return None if not b else 100.0 * a / b


def _fmt(v, digits=2):
    return "n/a" if v is None else f"{v:.{digits}f}"


def analyze_symbol(data_root: Path, symbol: str, *, tick_size: float) -> tuple[dict, list]:
    one_d_path = data_root / "spot" / symbol / "consolidated" / f"{symbol}_1d.parquet"
    one_w_path = data_root / "spot" / symbol / "consolidated" / f"{symbol}_1w.parquet"
    if not one_d_path.is_file() or not one_w_path.is_file():
        raise SystemExit(f"{symbol}: missing 1d/1w dataset")

    daily = load_dataset(one_d_path)
    weekly = load_dataset(one_w_path)
    datasets = {"1d": daily, "1w": weekly}

    chart = to_mm_candles(daily)
    week = to_mm_candles(weekly)
    snapshots: list[IntegrationSnapshot] = []
    Kernel(
        chart,
        week,
        chart,
        week,
        "1d",
        tick=tick_size,
    ).run(integration_rows=snapshots, emit_audit=False)

    locations = build_market_locations(snapshots)
    rsi_cache = {
        "1d": calculate_rsi(daily["close"]),
        "1w": calculate_rsi(weekly["close"]),
    }
    context_dirs = build_context_dirs("1d", datasets, rsi_cache)

    bars = [
        ExecutionResearchBar(
            open=o,
            high=h,
            low=l,
            close=c,
            volume=v,
            map_dir=snap.map_dir,
            location=loc,
            rsi_context_dir=context_dirs[i],
            thesis_invalidated=snap.thesis_invalidated,
            structural_conflict=snap.structural_conflict,
            bar_confirmed=True,
        )
        for i, (o,h,l,c,v,snap,loc) in enumerate(zip(
            daily["open"], daily["high"], daily["low"], daily["close"],
            daily["volume"], snapshots, locations
        ))
    ]
    samples = calculate_execution(bars)

    episodes = detect_episodes(snapshots, daily["high"], daily["low"])
    reacc = [e for e in episodes if e.opportunity_type == OpportunityType.REACCELERATION]
    responses = measure_all(
        reacc,
        snapshots,
        locations,
        samples,
        context_dirs,
        daily["close"],
        response_window_bars=24,
    )
    outcomes = classify_all(reacc, snapshots)

    outcome_counts = Counter()
    accepted_outcomes = Counter()
    hold2_delays = []
    for e in reacc:
        outcome = outcomes[e.episode_id].outcome.value
        outcome_counts[outcome] += 1
        accepted_bar = follow_through_bar(e, snapshots, daily["close"], 2)
        if accepted_bar is not None:
            accepted_outcomes[outcome] += 1
            hold2_delays.append(accepted_bar - e.confirmation_bar)

    held = outcome_counts[CandidateOutcome.BREAKOUT_HELD.value]
    fake = outcome_counts[CandidateOutcome.BREAKOUT_FAKEOUT.value]
    acc_held = accepted_outcomes[CandidateOutcome.BREAKOUT_HELD.value]
    acc_fake = accepted_outcomes[CandidateOutcome.BREAKOUT_FAKEOUT.value]

    item = {
        "rows_1d": len(daily["close"]),
        "rows_1w": len(weekly["close"]),
        "sha256_1d": sha256_file(one_d_path),
        "sha256_1w": sha256_file(one_w_path),
        "first_1d": daily["open_time"][0].isoformat() if len(daily["open_time"]) else None,
        "last_1d": daily["open_time"][-1].isoformat() if len(daily["open_time"]) else None,
        "episodes": len(reacc),
        "outcomes": dict(sorted(outcome_counts.items())),
        "frozen_0_1_response": _response_summary(responses),
        "hold_2": {
            "accepted_outcomes": dict(sorted(accepted_outcomes.items())),
            "held_recall_pct": _pct(acc_held, held),
            "fakeout_acceptance_pct": _pct(acc_fake, fake),
            "accepted_held_share_pct": _pct(acc_held, acc_held + acc_fake),
        },
    }
    return item, responses


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    ap.add_argument("--code-sha", default="unknown")
    ap.add_argument("--tick-size", type=float, default=0.01)
    args = ap.parse_args()

    symbols = tuple(x.strip().upper() for x in args.symbols.split(",") if x.strip())
    per_symbol = {}
    all_responses = []
    total_outcomes = Counter()
    total_accepted = Counter()

    for symbol in symbols:
        item, responses = analyze_symbol(args.data_root, symbol, tick_size=args.tick_size)
        per_symbol[symbol] = item
        all_responses.extend(responses)
        total_outcomes.update(item["outcomes"])
        total_accepted.update(item["hold_2"]["accepted_outcomes"])

    held = total_outcomes[CandidateOutcome.BREAKOUT_HELD.value]
    fake = total_outcomes[CandidateOutcome.BREAKOUT_FAKEOUT.value]
    acc_held = total_accepted[CandidateOutcome.BREAKOUT_HELD.value]
    acc_fake = total_accepted[CandidateOutcome.BREAKOUT_FAKEOUT.value]

    report = {
        "metadata": {
            "code_sha": args.code_sha,
            "symbols": list(symbols),
            "timeframe": "1d",
            "context_timeframe": "1w",
            "frozen_market_map_promotion": "0eeb0d37b256a950cfb38f627fa3521bb213d380",
            "frozen_execution_promotion": "a7557df2d0142441ea782dba4b8c3f95ebc38371",
            "episode_contract": "sequence-based REACCELERATION",
        },
        "aggregate": {
            "episodes": len(all_responses),
            "outcomes": dict(sorted(total_outcomes.items())),
            "frozen_0_1_response": _response_summary(all_responses),
            "hold_2": {
                "accepted_outcomes": dict(sorted(total_accepted.items())),
                "held_recall_pct": _pct(acc_held, held),
                "fakeout_acceptance_pct": _pct(acc_fake, fake),
                "accepted_held_share_pct": _pct(acc_held, acc_held + acc_fake),
            },
        },
        "symbols": per_symbol,
    }

    lines = [
        "# Suite 0.2 — 1D REACCELERATION universe robustness",
        "",
        "Frozen 0.1 response + structural follow-through on the accepted 15-symbol universe.",
        "",
        f"- code SHA: `{args.code_sha}`",
        f"- symbols: **{len(symbols)}**",
        "- timeframe/context: **1D / confirmed 1W**",
        "",
        "## Aggregate",
        "",
    ]
    agg = report["aggregate"]
    resp = agg["frozen_0_1_response"]
    h2 = agg["hold_2"]
    lines += [
        f"- REACCELERATION episodes: **{agg['episodes']}**",
        f"- retrospective outcomes: `{json.dumps(agg['outcomes'], sort_keys=True)}`",
        f"- frozen 0.1 already PREP+: **{_fmt(resp['already_preparing_or_better_pct'])}%**",
        f"- frozen 0.1 reached ARMED: **{_fmt(resp['reached_armed_pct'])}%**",
        f"- frozen 0.1 CONFIRMA or already ALIGNED: **{_fmt(resp['confirmed_or_already_aligned_pct'])}%**",
        f"- dominant miss: **{max(resp['missed_reason_counts'], key=resp['missed_reason_counts'].get) if resp['missed_reason_counts'] else '—'}**",
        f"- HOLD_2 held recall: **{_fmt(h2['held_recall_pct'])}%**",
        f"- HOLD_2 fakeout accepted: **{_fmt(h2['fakeout_acceptance_pct'])}%**",
        f"- HOLD_2 held share among accepted resolved: **{_fmt(h2['accepted_held_share_pct'])}%**",
        "",
        "## Per symbol",
        "",
        "| symbol | episodes | held | fakeout | 0.1 PREP+ % | 0.1 covered % | dominant miss | HOLD_2 held recall % | HOLD_2 fakeout % | HOLD_2 held share % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]

    for symbol, item in per_symbol.items():
        r = item["frozen_0_1_response"]
        miss = r["missed_reason_counts"]
        dominant = max(miss, key=miss.get) if miss else "—"
        h = item["hold_2"]
        lines.append(
            "| {s} | {n} | {held} | {fake} | {prep} | {covered} | {miss} | {hr} | {fa} | {hs} |".format(
                s=symbol,
                n=item["episodes"],
                held=item["outcomes"].get(CandidateOutcome.BREAKOUT_HELD.value, 0),
                fake=item["outcomes"].get(CandidateOutcome.BREAKOUT_FAKEOUT.value, 0),
                prep=_fmt(r["already_preparing_or_better_pct"]),
                covered=_fmt(r["confirmed_or_already_aligned_pct"]),
                miss=dominant,
                hr=_fmt(h["held_recall_pct"]),
                fa=_fmt(h["fakeout_acceptance_pct"]),
                hs=_fmt(h["accepted_held_share_pct"]),
            )
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- REACCELERATION is labeled from structural sequence, not Execution output.",
        "- HOLD_2 is later follow-through evidence and never backdates the opportunity bar.",
        "- held/fakeout is a structural diagnostic, not trade win rate.",
        "- no per-symbol retuning is performed.",
        "- no production Pine/default/profile is changed.",
        "",
    ]

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

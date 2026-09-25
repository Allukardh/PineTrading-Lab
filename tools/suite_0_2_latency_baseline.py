#!/usr/bin/env python3
"""Suite 0.2 frozen-0.1 opportunity coverage / latency baseline.

This runner does NOT change candidate behavior. It measures the accepted
Market Map 0.1 + Execution 0.1 reference stack against independent structural
opportunity episodes.

Primary first-pass horizons: 4h / 1d.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Sequence

from tools.execution_candidate_reference import (
    ExecutionResearchBar,
    calculate as calculate_execution,
)
from tools.execution_historical_evidence import (
    build_context_dirs,
    distribution,
    load_dataset,
    pct,
    sha256_file,
)
from tools.execution_integrated_evidence import (
    build_market_locations,
    to_mm_candles,
)
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.opportunity_episode_reference import detect_episodes
from tools.opportunity_latency_reference import measure_all
from tools.opportunity_outcome_reference import classify_all
from tools.rsi_state_reference import calculate as calculate_rsi


DEFAULT_TIMEFRAMES = ("4h", "1d")


def _dist(values: Sequence[float | int | None]) -> dict:
    return distribution([float(v) for v in values if v is not None])


def _response_summary(responses: Sequence) -> dict:
    if not responses:
        return {
            "episodes": 0,
            "direction_counts": {},
            "already_preparing_or_better_pct": None,
            "already_armed_or_better_pct": None,
            "already_aligned_pct": None,
            "reached_preparing_pct": None,
            "reached_armed_pct": None,
            "confirmed_after_episode_pct": None,
            "confirmed_or_already_aligned_pct": None,
            "prep_latency_bars": _dist([]),
            "armed_latency_bars": _dist([]),
            "confirm_latency_bars": _dist([]),
            "confirm_displacement_atr": _dist([]),
            "confirm_room_to_destination_atr": _dist([]),
            "onset_to_confirmation_bars": _dist([]),
            "deepest_state_counts": {},
            "missed_reason_counts": {},
            "terminated_by_counts": {},
        }

    n = len(responses)
    dirs = Counter("LONG" if r.direction == 1 else "SHORT" for r in responses)
    deepest = Counter(r.deepest_state for r in responses)
    missed = Counter(r.missed_reason for r in responses if r.missed_reason is not None)
    terminated = Counter(r.terminated_by for r in responses)

    reached_prep = sum(r.prep_bar is not None for r in responses)
    reached_armed = sum(r.armed_bar is not None for r in responses)
    confirmed = sum(r.confirm_bar is not None for r in responses)
    already_aligned = sum(r.already_aligned for r in responses)

    return {
        "episodes": n,
        "direction_counts": dict(sorted(dirs.items())),
        "already_preparing_or_better_pct": pct(
            sum(r.already_preparing_or_better for r in responses), n
        ),
        "already_armed_or_better_pct": pct(
            sum(r.already_armed_or_better for r in responses), n
        ),
        "already_aligned_pct": pct(already_aligned, n),
        "reached_preparing_pct": pct(reached_prep, n),
        "reached_armed_pct": pct(reached_armed, n),
        "confirmed_after_episode_pct": pct(confirmed, n),
        "confirmed_or_already_aligned_pct": pct(
            sum((r.confirm_bar is not None) or r.already_aligned for r in responses),
            n,
        ),
        "prep_latency_bars": _dist([r.prep_latency_bars for r in responses]),
        "armed_latency_bars": _dist([r.armed_latency_bars for r in responses]),
        "confirm_latency_bars": _dist([r.confirm_latency_bars for r in responses]),
        "prep_displacement_atr": _dist([r.prep_displacement_atr for r in responses]),
        "armed_displacement_atr": _dist([r.armed_displacement_atr for r in responses]),
        "confirm_displacement_atr": _dist(
            [r.confirm_displacement_atr for r in responses]
        ),
        "prep_room_to_destination_atr": _dist(
            [r.prep_room_to_destination_atr for r in responses]
        ),
        "armed_room_to_destination_atr": _dist(
            [r.armed_room_to_destination_atr for r in responses]
        ),
        "confirm_room_to_destination_atr": _dist(
            [r.confirm_room_to_destination_atr for r in responses]
        ),
        "onset_to_confirmation_bars": _dist(
            [r.confirmation_bar - r.onset_bar for r in responses]
        ),
        "deepest_state_counts": dict(sorted(deepest.items())),
        "missed_reason_counts": dict(sorted(missed.items())),
        "terminated_by_counts": dict(sorted(terminated.items())),
    }


def _examples(
    responses: Sequence,
    times: Sequence,
    *,
    limit: int = 5,
) -> dict:
    confirmed = []
    missed = []
    anticipated = []

    for r in responses:
        row = {
            "episode_id": r.episode_id,
            "type": r.opportunity_type,
            "direction": "LONG" if r.direction == 1 else "SHORT",
            "onset_time": times[r.onset_bar].isoformat(),
            "confirmation_time": times[r.confirmation_bar].isoformat(),
            "state_at_confirmation": r.state_at_confirmation,
            "prep_latency_bars": r.prep_latency_bars,
            "armed_latency_bars": r.armed_latency_bars,
            "confirm_latency_bars": r.confirm_latency_bars,
            "confirm_displacement_atr": r.confirm_displacement_atr,
            "missed_reason": r.missed_reason,
            "terminated_by": r.terminated_by,
        }
        if r.already_aligned and len(anticipated) < limit:
            anticipated.append(row)
        elif r.confirm_bar is not None and len(confirmed) < limit:
            confirmed.append(row)
        elif r.confirm_bar is None and len(missed) < limit:
            missed.append(row)

    return {
        "anticipated": anticipated,
        "confirmed_after_episode": confirmed,
        "not_confirmed": missed,
    }


def analyze_timeframe(
    timeframe: str,
    datasets: dict[str, dict],
    *,
    tick_size: float,
    response_window_bars: int,
) -> dict:
    data = datasets[timeframe]
    chart = to_mm_candles(data)
    context = to_mm_candles(datasets[CONTEXT_TF[timeframe]])
    daily = to_mm_candles(datasets["1d"])
    weekly = to_mm_candles(datasets["1w"])

    snapshots: list[IntegrationSnapshot] = []
    Kernel(
        chart,
        context,
        daily,
        weekly,
        timeframe,
        tick=tick_size,
    ).run(integration_rows=snapshots, emit_audit=False)

    if len(snapshots) != len(chart):
        raise AssertionError("Market Map snapshot length mismatch")

    locations = build_market_locations(snapshots)

    rsi_cache = {
        tf: calculate_rsi(ds["close"])
        for tf, ds in datasets.items()
    }
    context_dirs = build_context_dirs(timeframe, datasets, rsi_cache)

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
        for i, (o, h, l, c, v, snap, loc) in enumerate(
            zip(
                data["open"],
                data["high"],
                data["low"],
                data["close"],
                data["volume"],
                snapshots,
                locations,
            )
        )
    ]
    samples = calculate_execution(bars)

    episodes = detect_episodes(
        snapshots,
        data["high"],
        data["low"],
    )
    responses = measure_all(
        episodes,
        snapshots,
        locations,
        samples,
        context_dirs,
        data["close"],
        response_window_bars=response_window_bars,
    )

    outcomes = classify_all(episodes, snapshots)
    by_type = defaultdict(list)
    by_outcome = defaultdict(list)
    outcome_counts = Counter()
    outcome_latency = defaultdict(list)

    for response in responses:
        by_type[response.opportunity_type].append(response)
        outcome_obj = outcomes[response.episode_id]
        outcome = outcome_obj.outcome.value
        outcome_counts[outcome] += 1
        if outcome != "NOT_APPLICABLE":
            by_outcome[outcome].append(response)
            if outcome_obj.outcome_bar is not None:
                outcome_latency[outcome].append(
                    outcome_obj.outcome_bar - response.confirmation_bar
                )

    return {
        "rows": len(chart),
        "episode_count": len(episodes),
        "overall": _response_summary(responses),
        "by_opportunity": {
            kind: _response_summary(items)
            for kind, items in sorted(by_type.items())
        },
        "candidate_outcomes": {
            "counts": dict(sorted(outcome_counts.items())),
            "outcome_latency_bars": {
                outcome: _dist(values)
                for outcome, values in sorted(outcome_latency.items())
            },
            "response_by_outcome": {
                outcome: _response_summary(items)
                for outcome, items in sorted(by_outcome.items())
            },
        },
        "examples": _examples(responses, data["open_time"]),
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Suite 0.2 — Frozen 0.1 opportunity coverage / latency baseline",
        "",
        "This report measures the accepted 0.1 engines. It does not tune them.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- response window: **{report['metadata']['response_window_bars']} bars**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Summary",
        "",
        "| TF | opportunity | episodes | already PREP+ % | reached ARMED % | confirm/new % | confirm or already aligned % | confirm latency median | confirm displacement ATR median | dominant miss |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for tf, item in report["timeframes"].items():
        for kind, s in item["by_opportunity"].items():
            miss = s["missed_reason_counts"]
            dominant = max(miss, key=miss.get) if miss else "—"
            lines.append(
                "| {tf} | {kind} | {episodes} | {prep} | {armed} | {confirm} | {covered} | {lat} | {disp} | {miss} |".format(
                    tf=tf,
                    kind=kind,
                    episodes=s["episodes"],
                    prep=_fmt(s["already_preparing_or_better_pct"]),
                    armed=_fmt(s["reached_armed_pct"]),
                    confirm=_fmt(s["confirmed_after_episode_pct"]),
                    covered=_fmt(s["confirmed_or_already_aligned_pct"]),
                    lat=_fmt(s["confirm_latency_bars"]["median"]),
                    disp=_fmt(s["confirm_displacement_atr"]["median"]),
                    miss=dominant,
                )
            )

    lines += [
        "",
        "## Candidate outcome diagnostics",
        "",
        "| TF | retrospective outcome | episodes | outcome lag median | already PREP+ % | reached ARMED % | confirm or already aligned % |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for tf, item in report["timeframes"].items():
        for outcome, summary in item["candidate_outcomes"]["response_by_outcome"].items():
            lines.append(
                "| {tf} | {outcome} | {episodes} | {lag} | {prep} | {armed} | {covered} |".format(
                    tf=tf,
                    outcome=outcome,
                    episodes=summary["episodes"],
                    lag=_fmt(
                        item["candidate_outcomes"]["outcome_latency_bars"]
                        .get(outcome, {})
                        .get("median")
                    ),
                    prep=_fmt(summary["already_preparing_or_better_pct"]),
                    armed=_fmt(summary["reached_armed_pct"]),
                    covered=_fmt(summary["confirmed_or_already_aligned_pct"]),
                )
            )

    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- Opportunity labels are independent of Execution readiness/result.",
        "- Candidate outcomes are retrospective diagnostics only and never backdate live knowledge.",
        "- REGIME_REVERSAL onset may precede confirmation; actionable comparisons use the confirmation bar.",
        "- A missing CONFIRMA is not automatically a defect; miss reasons identify the blocking semantic.",
        "- No metric here is a trade win rate or profitability claim.",
        "- Frozen 0.1 Pine/defaults are not changed by this report.",
        "",
    ]
    return "\n".join(lines)


def _fmt(value, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--canonical-manifest", type=Path, required=True)
    ap.add_argument("--timeframes", default="4h,1d")
    ap.add_argument("--response-window-bars", type=int, default=24)
    ap.add_argument("--tick-size", type=float, default=0.01)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    ap.add_argument("--code-sha", default="unknown")
    args = ap.parse_args()

    requested = tuple(x.strip() for x in args.timeframes.split(",") if x.strip())
    if not requested:
        raise SystemExit("no timeframes requested")
    unsupported = [tf for tf in requested if tf not in DEFAULT_TIMEFRAMES]
    if unsupported:
        raise SystemExit(
            "first-pass baseline currently supports only "
            f"{DEFAULT_TIMEFRAMES}; got {unsupported}"
        )

    canonical = json.loads(args.canonical_manifest.read_text(encoding="utf-8"))
    expected = {d["timeframe"]: d for d in canonical["datasets"]}
    symbol = args.symbol.upper()
    market = canonical.get("market", "spot")

    # Load the full accepted 0.1 context set required by 4h/1d analysis.
    required = ("4h", "1d", "1w")
    datasets = {}
    dataset_meta = {}
    for tf in required:
        path = args.data_root / market / symbol / "consolidated" / f"{symbol}_{tf}.parquet"
        if not path.is_file():
            raise SystemExit(f"missing dataset: {path}")
        actual = sha256_file(path)
        exp = expected[tf]
        if actual != exp["dataset_sha256"]:
            raise SystemExit(
                f"{symbol} {tf}: SHA mismatch {actual} != {exp['dataset_sha256']}"
            )
        data = load_dataset(path)
        if len(data["close"]) != exp["candles"]:
            raise SystemExit(
                f"{symbol} {tf}: row mismatch {len(data['close'])} != {exp['candles']}"
            )
        datasets[tf] = data
        dataset_meta[tf] = {
            "rows": len(data["close"]),
            "sha256": actual,
            "first_date": exp["first_date"],
            "last_date": exp["last_date"],
        }

    report = {
        "metadata": {
            "symbol": symbol,
            "market": market,
            "code_sha": args.code_sha,
            "canonical_manifest": str(args.canonical_manifest),
            "canonical_materialization_run": canonical["materialization"]["github_actions_run_id"],
            "frozen_market_map_promotion": "0eeb0d37b256a950cfb38f627fa3521bb213d380",
            "frozen_execution_promotion": "a7557df2d0142441ea782dba4b8c3f95ebc38371",
            "timeframes": list(requested),
            "response_window_bars": args.response_window_bars,
            "datasets": dataset_meta,
        },
        "timeframes": {},
    }

    for tf in requested:
        report["timeframes"][tf] = analyze_timeframe(
            tf,
            datasets,
            tick_size=args.tick_size,
            response_window_bars=args.response_window_bars,
        )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md = markdown_report(report)
    args.output_md.write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

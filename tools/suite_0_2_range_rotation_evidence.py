#!/usr/bin/env python3
"""BTC 4H/1D structural RANGE_ROTATION evidence for Suite 0.2.

This runner validates the independent range-rotation episode contract before
any integration into Opportunity Engine v2.

No production Pine/default/profile changes.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import (
    build_context_dirs,
    distribution,
    load_dataset,
    pct,
    sha256_file,
)
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.opportunity_latency_reference import measure_all
from tools.range_rotation_reference import (
    RangeOutcome,
    RegimeRelation,
    RangeTrigger,
    as_opportunity_episode,
    classify_range_rotation,
    detect_range_rotations,
)
from tools.rsi_state_reference import calculate as calculate_rsi


TIMEFRAMES = ("4h", "1d")


def _dist(values):
    return distribution([float(v) for v in values if v is not None])


def _outcome_summary(episodes, outcomes) -> dict:
    counts = Counter(o.outcome.value for o in outcomes)
    n = len(episodes)
    midpoint_or_better = sum(
        o.outcome in {RangeOutcome.MID_REACHED, RangeOutcome.OPPOSITE_REACHED}
        for o in outcomes
    )
    opposite = sum(o.outcome == RangeOutcome.OPPOSITE_REACHED for o in outcomes)
    failed = sum(o.outcome == RangeOutcome.FAILED_BEFORE_MID for o in outcomes)

    bars_mid = []
    bars_opp = []
    for e, o in zip(episodes, outcomes):
        if o.midpoint_bar is not None:
            bars_mid.append(o.midpoint_bar - e.confirmation_bar)
        if o.opposite_bar is not None:
            bars_opp.append(o.opposite_bar - e.confirmation_bar)

    return {
        "episodes": n,
        "outcome_counts": dict(sorted(counts.items())),
        "midpoint_or_better_pct": pct(midpoint_or_better, n),
        "opposite_reached_pct": pct(opposite, n),
        "failed_before_mid_pct": pct(failed, n),
        "midpoint_latency_bars": _dist(bars_mid),
        "opposite_latency_bars": _dist(bars_opp),
        "range_height_atr": _dist([e.height_atr for e in episodes]),
        "boundary_drift_ratio": _dist([e.boundary_drift_ratio for e in episodes]),
        "direction_counts": dict(sorted(Counter(
            "LONG" if e.direction == 1 else "SHORT" for e in episodes
        ).items())),
    }


def _baseline_response_summary(responses) -> dict:
    n = len(responses)
    if not n:
        return {
            "episodes": 0,
            "already_preparing_or_better_pct": None,
            "reached_armed_pct": None,
            "confirmed_or_already_aligned_pct": None,
            "missed_reason_counts": {},
        }
    missed = Counter(r.missed_reason for r in responses if r.missed_reason)
    return {
        "episodes": n,
        "already_preparing_or_better_pct": pct(
            sum(r.already_preparing_or_better for r in responses), n
        ),
        "reached_armed_pct": pct(
            sum(r.armed_bar is not None for r in responses), n
        ),
        "confirmed_or_already_aligned_pct": pct(
            sum((r.confirm_bar is not None) or r.already_aligned for r in responses), n
        ),
        "confirm_latency_bars": _dist([r.confirm_latency_bars for r in responses]),
        "missed_reason_counts": dict(sorted(missed.items())),
    }


def _group_indices(episodes, attr):
    groups = defaultdict(list)
    for i, e in enumerate(episodes):
        groups[str(getattr(e, attr).value)].append(i)
    return groups


def analyze_timeframe(timeframe: str, datasets: dict[str, dict], tick_size: float) -> dict:
    data = datasets[timeframe]
    chart = to_mm_candles(data)
    context = to_mm_candles(datasets[CONTEXT_TF[timeframe]])
    daily = to_mm_candles(datasets["1d"])
    weekly = to_mm_candles(datasets["1w"])

    snapshots: list[IntegrationSnapshot] = []
    Kernel(chart, context, daily, weekly, timeframe, tick=tick_size).run(
        integration_rows=snapshots,
        emit_audit=False,
    )

    episodes = detect_range_rotations(
        snapshots,
        data["high"],
        data["low"],
        data["close"],
    )
    outcomes = [
        classify_range_rotation(
            e,
            snapshots,
            data["high"],
            data["low"],
            data["close"],
        )
        for e in episodes
    ]

    locations = build_market_locations(snapshots)
    rsi_cache = {tf: calculate_rsi(ds["close"]) for tf, ds in datasets.items()}
    context_dirs = build_context_dirs(timeframe, datasets, rsi_cache)

    bars = [
        ExecutionResearchBar(
            open=float(o),
            high=float(h),
            low=float(l),
            close=float(c),
            volume=float(v),
            map_dir=s.map_dir,
            location=loc,
            rsi_context_dir=context_dirs[i],
            thesis_invalidated=s.thesis_invalidated,
            structural_conflict=s.structural_conflict,
            bar_confirmed=True,
        )
        for i, (o, h, l, c, v, s, loc) in enumerate(zip(
            data["open"], data["high"], data["low"], data["close"], data["volume"],
            snapshots, locations
        ))
    ]
    baseline_samples = calculate_execution(bars)
    opp_episodes = [as_opportunity_episode(e) for e in episodes]
    responses = measure_all(
        opp_episodes,
        snapshots,
        locations,
        baseline_samples,
        context_dirs,
        data["close"],
    )

    result = {
        "rows": len(chart),
        "episodes": len(episodes),
        "overall": _outcome_summary(episodes, outcomes),
        "frozen_0_1_response": _baseline_response_summary(responses),
        "by_trigger": {},
        "by_regime_relation": {},
    }

    for name, indices in _group_indices(episodes, "trigger").items():
        es = [episodes[i] for i in indices]
        os = [outcomes[i] for i in indices]
        rs = [responses[i] for i in indices]
        result["by_trigger"][name] = {
            "structural": _outcome_summary(es, os),
            "frozen_0_1_response": _baseline_response_summary(rs),
        }

    for name, indices in _group_indices(episodes, "regime_relation").items():
        es = [episodes[i] for i in indices]
        os = [outcomes[i] for i in indices]
        rs = [responses[i] for i in indices]
        result["by_regime_relation"][name] = {
            "structural": _outcome_summary(es, os),
            "frozen_0_1_response": _baseline_response_summary(rs),
        }

    return result


def _fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown_report(report: dict) -> str:
    lines = [
        "# Suite 0.2 — RANGE_ROTATION structural evidence",
        "",
        "Independent episode/outcome research. No Opportunity v2 integration yet.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Overall",
        "",
        "| TF | episodes | midpoint+ % | opposite edge % | fail before mid % | mid latency median | opposite latency median | 0.1 PREP+ % | 0.1 covered % | dominant 0.1 miss |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for tf, item in report["timeframes"].items():
        s = item["overall"]
        b = item["frozen_0_1_response"]
        miss = b["missed_reason_counts"]
        dominant = max(miss, key=miss.get) if miss else "—"
        lines.append(
            "| {tf} | {n} | {mid} | {opp} | {fail} | {ml} | {ol} | {prep} | {cov} | {miss} |".format(
                tf=tf,
                n=s["episodes"],
                mid=_fmt(s["midpoint_or_better_pct"]),
                opp=_fmt(s["opposite_reached_pct"]),
                fail=_fmt(s["failed_before_mid_pct"]),
                ml=_fmt(s["midpoint_latency_bars"]["median"]),
                ol=_fmt(s["opposite_latency_bars"]["median"]),
                prep=_fmt(b["already_preparing_or_better_pct"]),
                cov=_fmt(b["confirmed_or_already_aligned_pct"]),
                miss=dominant,
            )
        )

    lines += [
        "",
        "## By trigger",
        "",
        "| TF | trigger | episodes | midpoint+ % | opposite % | fail before mid % |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        for name, row in sorted(item["by_trigger"].items()):
            s = row["structural"]
            lines.append(
                f"| {tf} | {name} | {s['episodes']} | {_fmt(s['midpoint_or_better_pct'])} | {_fmt(s['opposite_reached_pct'])} | {_fmt(s['failed_before_mid_pct'])} |"
            )

    lines += [
        "",
        "## By regime relation",
        "",
        "| TF | relation | episodes | midpoint+ % | opposite % | fail before mid % | 0.1 covered % |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        for name, row in sorted(item["by_regime_relation"].items()):
            s = row["structural"]
            b = row["frozen_0_1_response"]
            lines.append(
                f"| {tf} | {name} | {s['episodes']} | {_fmt(s['midpoint_or_better_pct'])} | {_fmt(s['opposite_reached_pct'])} | {_fmt(s['failed_before_mid_pct'])} | {_fmt(b['confirmed_or_already_aligned_pct'])} |"
            )

    lines += [
        "",
        "## Guardrails",
        "",
        "- A range requires two confirmed swing-high and two confirmed swing-low cycles.",
        "- Boundary drift <= 20% of range height and range height >= 2 ATR are pre-registered research constraints, not tuned outputs.",
        "- Rotation requires an edge interaction plus close back into the range; SWEEP_RECLAIM is reported separately from generic EDGE_REJECTION.",
        "- Same-edge candidates reset only after price traverses back through range midpoint.",
        "- A new compatible pivot may update the box without ending range identity.",
        "- Outcome is retrospective structural behavior, not trade profitability.",
        "- Counter-regime rotation is not assumed bad or good; it is measured separately.",
        "- No production Pine/default/profile changed.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--canonical-manifest", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    ap.add_argument("--code-sha", default="unknown")
    ap.add_argument("--tick-size", type=float, default=0.01)
    args = ap.parse_args()

    canonical = json.loads(args.canonical_manifest.read_text(encoding="utf-8"))
    expected = {d["timeframe"]: d for d in canonical["datasets"]}
    symbol = args.symbol.upper()
    market = canonical.get("market", "spot")

    datasets = {}
    meta = {}
    for tf in ("4h", "1d", "1w"):
        path = args.data_root / market / symbol / "consolidated" / f"{symbol}_{tf}.parquet"
        if not path.is_file():
            raise SystemExit(f"missing dataset: {path}")
        digest = sha256_file(path)
        exp = expected[tf]
        if digest != exp["dataset_sha256"]:
            raise SystemExit(f"{symbol} {tf}: SHA mismatch")
        data = load_dataset(path)
        if len(data["close"]) != exp["candles"]:
            raise SystemExit(f"{symbol} {tf}: row mismatch")
        datasets[tf] = data
        meta[tf] = {
            "rows": len(data["close"]),
            "sha256": digest,
            "first_date": exp["first_date"],
            "last_date": exp["last_date"],
        }

    report = {
        "metadata": {
            "symbol": symbol,
            "market": market,
            "code_sha": args.code_sha,
            "datasets": meta,
        },
        "timeframes": {
            tf: analyze_timeframe(tf, datasets, args.tick_size)
            for tf in TIMEFRAMES
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md = markdown_report(report)
    args.output_md.write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare frozen Execution 0.1 with the first Suite 0.2 Opportunity Engine counterfactual.

Research-only:
- no production Pine/default/profile changes;
- accepted MTE/RSE/PSE and Execution state transitions remain unchanged;
- only additional opportunity relevance is supplied outside the old
  correction/retest/reclaim vocabulary.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import build_context_dirs, load_dataset, pct, sha256_file
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.execution_state_reference import RELEVANT_LOCATIONS, Readiness
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.opportunity_episode_reference import OpportunityType, detect_episodes
from tools.opportunity_execution_counterfactual import (
    OpportunityKind,
    OpportunityStage,
    build_opportunity_frames,
    calculate_counterfactual,
)
from tools.opportunity_latency_reference import measure_all
from tools.opportunity_outcome_reference import CandidateOutcome, classify_all
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi
from tools.suite_0_2_latency_baseline import _response_summary


TIMEFRAMES = ("4h", "1d")


def _event_counts(samples) -> Counter:
    c = Counter()
    for s in samples:
        e = s.result.events
        c["PREPARING_ENTERED"] += int(e.preparing_entered)
        c["ARMED_ENTERED"] += int(e.armed_entered)
        c["CONFIRM"] += int(e.confirm)
        c["CANCELED"] += int(e.canceled)
    return c


def _per_1000(count: int, rows: int) -> float | None:
    return None if not rows else count * 1000.0 / rows


def _quick_cancel(samples, entered_attr: str, max_bars: int = 3) -> int:
    starts = [
        i for i, s in enumerate(samples)
        if getattr(s.result.events, entered_attr)
    ]
    n = 0
    for start in starts:
        for j in range(start + 1, min(len(samples), start + max_bars + 1)):
            ev = samples[j].result.events
            if ev.confirm:
                break
            if ev.canceled:
                n += 1
                break
    return n


def _summary_by_type(responses) -> dict:
    grouped = defaultdict(list)
    for r in responses:
        grouped[r.opportunity_type].append(r)
    return {
        k: _response_summary(v)
        for k, v in sorted(grouped.items())
    }


def _delta(a, b) -> float | None:
    if a is None or b is None:
        return None
    return b - a


def _comparison(baseline: dict, counterfactual: dict) -> dict:
    return {
        "episodes": baseline["episodes"],
        "baseline_covered_pct": baseline["confirmed_or_already_aligned_pct"],
        "counterfactual_covered_pct": counterfactual["confirmed_or_already_aligned_pct"],
        "covered_delta_pp": _delta(
            baseline["confirmed_or_already_aligned_pct"],
            counterfactual["confirmed_or_already_aligned_pct"],
        ),
        "baseline_prep_pct": baseline["reached_preparing_pct"],
        "counterfactual_prep_pct": counterfactual["reached_preparing_pct"],
        "prep_delta_pp": _delta(
            baseline["reached_preparing_pct"],
            counterfactual["reached_preparing_pct"],
        ),
        "baseline_armed_pct": baseline["reached_armed_pct"],
        "counterfactual_armed_pct": counterfactual["reached_armed_pct"],
        "armed_delta_pp": _delta(
            baseline["reached_armed_pct"],
            counterfactual["reached_armed_pct"],
        ),
        "baseline_confirm_latency_median": baseline["confirm_latency_bars"]["median"],
        "counterfactual_confirm_latency_median": counterfactual["confirm_latency_bars"]["median"],
        "baseline_confirm_displacement_atr_median": baseline["confirm_displacement_atr"]["median"],
        "counterfactual_confirm_displacement_atr_median": counterfactual["confirm_displacement_atr"]["median"],
        "baseline_miss_reasons": baseline["missed_reason_counts"],
        "counterfactual_miss_reasons": counterfactual["missed_reason_counts"],
    }


def _breakout_outcome_coverage(episodes, outcomes, baseline_responses, cf_responses):
    b = {r.episode_id: r for r in baseline_responses}
    c = {r.episode_id: r for r in cf_responses}
    out = {}
    for outcome_name in (
        CandidateOutcome.BREAKOUT_HELD,
        CandidateOutcome.BREAKOUT_FAKEOUT,
    ):
        ids = [
            e.episode_id for e in episodes
            if e.opportunity_type == OpportunityType.BREAKOUT_CANDIDATE
            and outcomes[e.episode_id].outcome == outcome_name
        ]
        def covered(row):
            return row.confirm_bar is not None or row.already_aligned
        out[outcome_name.value] = {
            "episodes": len(ids),
            "baseline_covered_pct": pct(sum(covered(b[i]) for i in ids), len(ids)),
            "counterfactual_covered_pct": pct(sum(covered(c[i]) for i in ids), len(ids)),
        }
    return out


def analyze_timeframe(timeframe: str, datasets: dict[str, dict], tick_size: float) -> dict:
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
            map_dir=snap.map_dir,
            location=loc,
            rsi_context_dir=context_dirs[i],
            thesis_invalidated=snap.thesis_invalidated,
            structural_conflict=snap.structural_conflict,
            bar_confirmed=True,
        )
        for i, (o, h, l, c, v, snap, loc) in enumerate(
            zip(
                data["open"], data["high"], data["low"], data["close"],
                data["volume"], snapshots, locations
            )
        )
    ]

    baseline_samples = calculate_execution(bars)

    episodes = detect_episodes(snapshots, data["high"], data["low"])
    outcomes = classify_all(episodes, snapshots)

    p_bars = [
        ParticipationBar(float(h), float(l), float(c), float(v))
        for h, l, c, v in zip(
            data["high"], data["low"], data["close"], data["volume"]
        )
    ]
    pse = calculate_participation(p_bars, [s.map_dir for s in snapshots])

    frames = build_opportunity_frames(
        episodes,
        snapshots,
        data["close"],
        locations,
        pse,
    )
    cf_samples = calculate_counterfactual(bars, frames)
    cf_locations = [s.effective_location for s in cf_samples]

    baseline_responses = measure_all(
        episodes,
        snapshots,
        locations,
        baseline_samples,
        context_dirs,
        data["close"],
    )
    cf_responses = measure_all(
        episodes,
        snapshots,
        cf_locations,
        cf_samples,
        context_dirs,
        data["close"],
    )

    baseline_by_type = _summary_by_type(baseline_responses)
    cf_by_type = _summary_by_type(cf_responses)
    comparisons = {
        kind: _comparison(baseline_by_type[kind], cf_by_type[kind])
        for kind in sorted(set(baseline_by_type) & set(cf_by_type))
    }

    b_events = _event_counts(baseline_samples)
    c_events = _event_counts(cf_samples)
    rows = len(bars)

    frame_kind = Counter(f.kind.name for f in frames if f.kind != OpportunityKind.NONE)
    frame_stage = Counter(f.stage.name for f in frames if f.stage != OpportunityStage.NONE)
    overlay_bars = sum(s.opportunity_overlay for s in cf_samples)

    # Regression watch: the old pullback/retest family must not lose coverage.
    pullback = comparisons.get(OpportunityType.PULLBACK_RETEST.value)
    pullback_regression = (
        None
        if pullback is None
        else pullback["covered_delta_pp"] is not None
        and pullback["covered_delta_pp"] < 0
    )

    # State divergence on bars where 0.1 already owns a relevant location.
    relevant_bars = [
        i for i, loc in enumerate(locations)
        if loc in RELEVANT_LOCATIONS
    ]
    relevant_state_divergence = sum(
        baseline_samples[i].result.state != cf_samples[i].result.state
        for i in relevant_bars
    )

    return {
        "rows": rows,
        "episodes": len(episodes),
        "opportunity_frames": {
            "overlay_bars": overlay_bars,
            "overlay_pct": pct(overlay_bars, rows),
            "kind_counts": dict(sorted(frame_kind.items())),
            "stage_counts": dict(sorted(frame_stage.items())),
        },
        "by_opportunity": comparisons,
        "global_state_machine": {
            "baseline_events": dict(b_events),
            "counterfactual_events": dict(c_events),
            "baseline_events_per_1000": {
                k: _per_1000(v, rows) for k, v in sorted(b_events.items())
            },
            "counterfactual_events_per_1000": {
                k: _per_1000(v, rows) for k, v in sorted(c_events.items())
            },
            "baseline_quick_prep_cancel_3": _quick_cancel(
                baseline_samples, "preparing_entered"
            ),
            "counterfactual_quick_prep_cancel_3": _quick_cancel(
                cf_samples, "preparing_entered"
            ),
            "baseline_quick_armed_cancel_3": _quick_cancel(
                baseline_samples, "armed_entered"
            ),
            "counterfactual_quick_armed_cancel_3": _quick_cancel(
                cf_samples, "armed_entered"
            ),
        },
        "preservation_watch": {
            "pullback_coverage_regression": pullback_regression,
            "baseline_relevant_bars": len(relevant_bars),
            "relevant_state_divergence_bars": relevant_state_divergence,
            "relevant_state_divergence_pct": pct(
                relevant_state_divergence, len(relevant_bars)
            ),
        },
        "breakout_outcome_coverage": _breakout_outcome_coverage(
            episodes, outcomes, baseline_responses, cf_responses
        ),
    }


def _fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown_report(report: dict) -> str:
    lines = [
        "# Suite 0.2 — Opportunity Engine counterfactual vs frozen 0.1",
        "",
        "Research-only. No production Pine/default/profile changed.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Opportunity response",
        "",
        "| TF | opportunity | episodes | 0.1 covered % | CF covered % | delta pp | 0.1 ARMED % | CF ARMED % | 0.1 confirm latency | CF confirm latency |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        for kind, c in item["by_opportunity"].items():
            lines.append(
                "| {tf} | {kind} | {n} | {b} | {cfx} | {d} | {ba} | {ca} | {bl} | {cl} |".format(
                    tf=tf, kind=kind, n=c["episodes"],
                    b=_fmt(c["baseline_covered_pct"]),
                    cfx=_fmt(c["counterfactual_covered_pct"]),
                    d=_fmt(c["covered_delta_pp"]),
                    ba=_fmt(c["baseline_armed_pct"]),
                    ca=_fmt(c["counterfactual_armed_pct"]),
                    bl=_fmt(c["baseline_confirm_latency_median"]),
                    cl=_fmt(c["counterfactual_confirm_latency_median"]),
                )
            )

    lines += [
        "",
        "## Global churn / preservation",
        "",
        "| TF | overlay % | 0.1 confirms/1000 | CF confirms/1000 | 0.1 cancels/1000 | CF cancels/1000 | quick ARM cancel 0.1/CF | pullback regression? | relevant-state divergence % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        g = item["global_state_machine"]
        p = item["preservation_watch"]
        lines.append(
            "| {tf} | {ov} | {bc} | {cc} | {bx} | {cx} | {qa}/{qb} | {pr} | {div} |".format(
                tf=tf,
                ov=_fmt(item["opportunity_frames"]["overlay_pct"]),
                bc=_fmt(g["baseline_events_per_1000"].get("CONFIRM")),
                cc=_fmt(g["counterfactual_events_per_1000"].get("CONFIRM")),
                bx=_fmt(g["baseline_events_per_1000"].get("CANCELED")),
                cx=_fmt(g["counterfactual_events_per_1000"].get("CANCELED")),
                qa=g["baseline_quick_armed_cancel_3"],
                qb=g["counterfactual_quick_armed_cancel_3"],
                pr=p["pullback_coverage_regression"],
                div=_fmt(p["relevant_state_divergence_pct"]),
            )
        )

    lines += [
        "",
        "## Breakout held/fakeout diagnostic",
        "",
        "| TF | outcome | episodes | 0.1 covered % | CF covered % |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        for outcome, x in item["breakout_outcome_coverage"].items():
            lines.append(
                f"| {tf} | {outcome} | {x['episodes']} | {_fmt(x['baseline_covered_pct'])} | {_fmt(x['counterfactual_covered_pct'])} |"
            )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Frozen 0.1 remains the comparator and is not modified.",
        "- Counterfactual CANDIDATE/STRONG opportunity frames cannot satisfy final PSE confirmation; ACCEPTED is required.",
        "- Old correction/retest/reclaim location has priority whenever it is present.",
        "- More confirmations are not automatically better; churn and fakeout coverage are reported beside coverage.",
        "- Breakout held/fakeout is retrospective diagnostic evidence, not a trade win rate.",
        "- Profiles remain outside this block.",
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
            "frozen_market_map_promotion": "0eeb0d37b256a950cfb38f627fa3521bb213d380",
            "frozen_execution_promotion": "a7557df2d0142441ea782dba4b8c3f95ebc38371",
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

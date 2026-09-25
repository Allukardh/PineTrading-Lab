#!/usr/bin/env python3
"""Evidence for the parallel Suite 0.2 Opportunity Readiness path.

Frozen Execution 0.1 remains untouched and continues to own
correction/retest/reclaim. The new opportunity path independently evaluates
BREAKOUT_EXPANSION, REACCELERATION and strict REGIME_REVERSAL frames.

No production Pine/default/profile changes.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import build_context_dirs, load_dataset, pct, sha256_file
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.execution_state_reference import Location
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.opportunity_episode_reference import OpportunityType, detect_episodes
from tools.opportunity_execution_counterfactual import (
    OpportunityKind,
    OpportunityStage,
    build_opportunity_frames,
)
from tools.opportunity_latency_reference import measure_all
from tools.opportunity_outcome_reference import CandidateOutcome, classify_all
from tools.opportunity_readiness_reference import calculate_opportunity_readiness
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi
from tools.suite_0_2_latency_baseline import _response_summary


TIMEFRAMES = ("4h", "1d")
NEW_PATH_TYPES = {
    OpportunityType.BREAKOUT_CANDIDATE.value,
    OpportunityType.REACCELERATION.value,
    OpportunityType.REGIME_REVERSAL.value,
}


def _covered(r) -> bool:
    return r.confirm_bar is not None or r.already_aligned


def _event_counts(samples) -> Counter:
    c = Counter()
    for s in samples:
        e = s.result.events
        c["PREPARING_ENTERED"] += int(e.preparing_entered)
        c["ARMED_ENTERED"] += int(e.armed_entered)
        c["CONFIRM"] += int(e.confirm)
        c["CANCELED"] += int(e.canceled)
    return c


def _confirm_direction_counts(samples) -> Counter:
    c = Counter()
    for s in samples:
        if not s.result.events.confirm:
            continue
        direction = s.result.state.direction
        if direction == 1:
            c["LONG"] += 1
        elif direction == -1:
            c["SHORT"] += 1
        else:
            c["NONE"] += 1
    return c


def _quick_cancel(samples, entered_attr: str, max_bars: int = 3) -> int:
    starts = [i for i, s in enumerate(samples) if getattr(s.result.events, entered_attr)]
    total = 0
    for start in starts:
        for j in range(start + 1, min(len(samples), start + max_bars + 1)):
            ev = samples[j].result.events
            if ev.confirm:
                break
            if ev.canceled:
                total += 1
                break
    return total


def _per_1000(value: int, rows: int) -> float | None:
    return None if not rows else value * 1000.0 / rows


def _group(responses) -> dict[str, list]:
    out = defaultdict(list)
    for r in responses:
        out[r.opportunity_type].append(r)
    return out


def _expanded_summary(baseline_rows, opportunity_rows, *, allow_new_path: bool) -> dict:
    b = {r.episode_id: r for r in baseline_rows}
    o = {r.episode_id: r for r in opportunity_rows}
    ids = list(b)

    baseline_covered = sum(_covered(b[i]) for i in ids)
    opportunity_covered = sum(_covered(o[i]) for i in ids) if allow_new_path else 0
    expanded_covered = sum(
        _covered(b[i]) or (allow_new_path and _covered(o[i]))
        for i in ids
    )
    opportunity_only = sum(
        (not _covered(b[i])) and allow_new_path and _covered(o[i])
        for i in ids
    )

    def first_latency(name: str):
        values = []
        for i in ids:
            candidates = [getattr(b[i], name)]
            if allow_new_path:
                candidates.append(getattr(o[i], name))
            candidates = [x for x in candidates if x is not None]
            if candidates:
                values.append(min(candidates))
        if not values:
            return None
        values.sort()
        n = len(values)
        return float(values[n // 2]) if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2.0

    return {
        "episodes": len(ids),
        "baseline_covered_pct": pct(baseline_covered, len(ids)),
        "opportunity_path_covered_pct": (
            pct(opportunity_covered, len(ids)) if allow_new_path else None
        ),
        "expanded_covered_pct": pct(expanded_covered, len(ids)),
        "opportunity_only_covered_pct": (
            pct(opportunity_only, len(ids)) if allow_new_path else 0.0
        ),
        "expanded_prep_latency_median": first_latency("prep_latency_bars"),
        "expanded_armed_latency_median": first_latency("armed_latency_bars"),
        "expanded_confirm_latency_median": first_latency("confirm_latency_bars"),
    }


def _event_stage_diagnostics(samples) -> dict:
    out = {
        "PREPARING_ENTERED": Counter(),
        "ARMED_ENTERED": Counter(),
        "CONFIRM": Counter(),
        "CANCELED": Counter(),
    }
    for s in samples:
        key = f"{s.frame.kind.name}/{s.frame.stage.name}"
        e = s.result.events
        if e.preparing_entered:
            out["PREPARING_ENTERED"][key] += 1
        if e.armed_entered:
            if s.frame.stage < OpportunityStage.STRONG:
                raise AssertionError("ARMED occurred before STRONG opportunity stage")
            out["ARMED_ENTERED"][key] += 1
        if e.confirm:
            if s.frame.stage < OpportunityStage.ACCEPTED:
                raise AssertionError("CONFIRM occurred before ACCEPTED opportunity stage")
            out["CONFIRM"][key] += 1
        if e.canceled:
            out["CANCELED"][key] += 1
    return {k: dict(sorted(v.items())) for k, v in out.items()}


def _breakout_outcomes(episodes, outcomes, b_by_id, o_by_id):
    result = {}
    for outcome in (CandidateOutcome.BREAKOUT_HELD, CandidateOutcome.BREAKOUT_FAKEOUT):
        ids = [
            e.episode_id for e in episodes
            if e.opportunity_type == OpportunityType.BREAKOUT_CANDIDATE
            and outcomes[e.episode_id].outcome == outcome
        ]
        baseline = sum(_covered(b_by_id[i]) for i in ids)
        opp = sum(_covered(o_by_id[i]) for i in ids)
        expanded = sum(_covered(b_by_id[i]) or _covered(o_by_id[i]) for i in ids)
        result[outcome.value] = {
            "episodes": len(ids),
            "baseline_covered_pct": pct(baseline, len(ids)),
            "opportunity_path_covered_pct": pct(opp, len(ids)),
            "expanded_covered_pct": pct(expanded, len(ids)),
        }
    return result


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

    baseline_locations = build_market_locations(snapshots)
    rsi_cache = {tf: calculate_rsi(ds["close"]) for tf, ds in datasets.items()}
    context_dirs = build_context_dirs(timeframe, datasets, rsi_cache)

    bars = [
        ExecutionResearchBar(
            open=float(o), high=float(h), low=float(l), close=float(c),
            volume=float(v), map_dir=s.map_dir, location=loc,
            rsi_context_dir=context_dirs[i],
            thesis_invalidated=s.thesis_invalidated,
            structural_conflict=s.structural_conflict,
            bar_confirmed=True,
        )
        for i, (o, h, l, c, v, s, loc) in enumerate(zip(
            data["open"], data["high"], data["low"], data["close"], data["volume"],
            snapshots, baseline_locations
        ))
    ]

    # Frozen comparator.
    baseline_samples = calculate_execution(bars)

    episodes = detect_episodes(snapshots, data["high"], data["low"])
    outcomes = classify_all(episodes, snapshots)

    # Frame construction uses the same accepted PSE semantics.
    p_bars = [
        ParticipationBar(float(h), float(l), float(c), float(v))
        for h, l, c, v in zip(data["high"], data["low"], data["close"], data["volume"])
    ]
    canonical_pse = calculate_participation(p_bars, [s.map_dir for s in snapshots])
    frames = build_opportunity_frames(
        episodes,
        snapshots,
        data["close"],
        baseline_locations,
        canonical_pse,
    )

    opportunity_samples = calculate_opportunity_readiness(bars, frames)

    # For latency accounting only, a live OpportunityFrame is represented as a
    # relevant synthetic location. This does NOT feed the state machine; it is
    # only an input to the generic response measurement helper.
    opportunity_locations = [
        Location.APPROACHING
        if f.stage != OpportunityStage.NONE and f.direction in (-1, 1)
        else Location.OUTSIDE
        for f in frames
    ]

    baseline_responses = measure_all(
        episodes, snapshots, baseline_locations, baseline_samples,
        context_dirs, data["close"]
    )
    opportunity_responses = measure_all(
        episodes, snapshots, opportunity_locations, opportunity_samples,
        context_dirs, data["close"]
    )

    bg = _group(baseline_responses)
    og = _group(opportunity_responses)
    by_type = {}
    for kind in sorted(bg):
        by_type[kind] = _expanded_summary(
            bg[kind],
            og[kind],
            allow_new_path=kind in NEW_PATH_TYPES,
        )

    b_by_id = {r.episode_id: r for r in baseline_responses}
    o_by_id = {r.episode_id: r for r in opportunity_responses}

    b_events = _event_counts(baseline_samples)
    o_events = _event_counts(opportunity_samples)
    rows = len(bars)

    frame_kinds = Counter(f.kind.name for f in frames if f.kind != OpportunityKind.NONE)
    frame_stages = Counter(f.stage.name for f in frames if f.stage != OpportunityStage.NONE)

    # Exact baseline parity is structural here: baseline_samples are calculated
    # once and never passed through opportunity logic.
    return {
        "rows": rows,
        "episodes": len(episodes),
        "baseline_path": {
            "mutated": False,
            "events": dict(b_events),
            "events_per_1000": {k: _per_1000(v, rows) for k, v in sorted(b_events.items())},
        },
        "opportunity_path": {
            "events": dict(o_events),
            "confirm_direction_counts": dict(sorted(_confirm_direction_counts(opportunity_samples).items())),
            "events_per_1000": {k: _per_1000(v, rows) for k, v in sorted(o_events.items())},
            "quick_prep_cancel_3": _quick_cancel(opportunity_samples, "preparing_entered"),
            "quick_armed_cancel_3": _quick_cancel(opportunity_samples, "armed_entered"),
            "event_stage_diagnostics": _event_stage_diagnostics(opportunity_samples),
            "frame_kind_counts": dict(sorted(frame_kinds.items())),
            "frame_stage_counts": dict(sorted(frame_stages.items())),
        },
        "by_opportunity": by_type,
        "breakout_outcome_coverage": _breakout_outcomes(
            episodes, outcomes, b_by_id, o_by_id
        ),
    }


def _fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown_report(report: dict) -> str:
    lines = [
        "# Suite 0.2 — Parallel Opportunity Readiness vs frozen 0.1",
        "",
        "Research-only. Frozen 0.1 is calculated independently and cannot be mutated by the new path.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Opportunity coverage",
        "",
        "| TF | opportunity | episodes | 0.1 covered % | opp-path covered % | expanded covered % | opp-only gain % | expanded prep latency | expanded armed latency | expanded confirm latency |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        for kind, s in item["by_opportunity"].items():
            lines.append(
                "| {tf} | {kind} | {n} | {b} | {o} | {x} | {g} | {pl} | {al} | {cl} |".format(
                    tf=tf, kind=kind, n=s["episodes"],
                    b=_fmt(s["baseline_covered_pct"]),
                    o=_fmt(s["opportunity_path_covered_pct"]),
                    x=_fmt(s["expanded_covered_pct"]),
                    g=_fmt(s["opportunity_only_covered_pct"]),
                    pl=_fmt(s["expanded_prep_latency_median"]),
                    al=_fmt(s["expanded_armed_latency_median"]),
                    cl=_fmt(s["expanded_confirm_latency_median"]),
                )
            )

    lines += [
        "",
        "## Path event load",
        "",
        "| TF | frozen 0.1 confirms/1000 | opportunity confirms/1000 | opp cancels/1000 | opp quick PREP cancel <=3 | opp quick ARMED cancel <=3 | baseline mutated? |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for tf, item in report["timeframes"].items():
        b = item["baseline_path"]["events_per_1000"]
        o = item["opportunity_path"]["events_per_1000"]
        lines.append(
            "| {tf} | {bc} | {oc} | {ox} | {qp} | {qa} | {m} |".format(
                tf=tf,
                bc=_fmt(b.get("CONFIRM")),
                oc=_fmt(o.get("CONFIRM")),
                ox=_fmt(o.get("CANCELED")),
                qp=item["opportunity_path"]["quick_prep_cancel_3"],
                qa=item["opportunity_path"]["quick_armed_cancel_3"],
                m=item["baseline_path"]["mutated"],
            )
        )

    lines += [
        "",
        "## Breakout held/fakeout coverage",
        "",
        "| TF | outcome | episodes | 0.1 covered % | opp-path covered % | expanded covered % |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        for outcome, s in item["breakout_outcome_coverage"].items():
            lines.append(
                f"| {tf} | {outcome} | {s['episodes']} | {_fmt(s['baseline_covered_pct'])} | {_fmt(s['opportunity_path_covered_pct'])} | {_fmt(s['expanded_covered_pct'])} |"
            )

    lines += [
        "",
        "## Guardrails",
        "",
        "- Pullback/retest stays on frozen Execution 0.1 only.",
        "- Raw REGIME_TRANSITION_CANDIDATE stays non-actionable.",
        "- CANDIDATE may only PREPARE.",
        "- STRONG may ARM but cannot CONFIRM.",
        "- ACCEPTED is required for Opportunity CONFIRMA.",
        "- MTE/RSE/PSE semantics are unchanged.",
        "- Opportunity events are reported separately rather than hidden inside 0.1 counts.",
        "- Held/fakeout is a structural retrospective diagnostic, not a trade win rate.",
        "- Profiles remain unapproved.",
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

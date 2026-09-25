#!/usr/bin/env python3
"""RANGE_ROTATION -> Opportunity v2 integration A/B evidence.

Compares two pre-registered range integration variants on BTC 4H/1D:
- ALL_EDGE: every structural EDGE_REJECTION is actionable
- CONTEXT_GUARDED: AGAINST_REGIME remains awareness-only

The accepted breakout/reacceleration Opportunity v2 frame builder is measured
unchanged and is not mutated by this experiment. Frozen Execution 0.1 remains
independent.

No production Pine/default/profile changes.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import (
    build_context_dirs,
    distribution,
    load_dataset,
    pct,
    sha256_file,
)
from tools.execution_integrated_evidence import build_market_locations, to_mm_candles
from tools.execution_state_reference import Readiness
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.opportunity_episode_reference import detect_episodes
from tools.opportunity_execution_counterfactual import (
    OpportunityKind,
    OpportunityStage,
    build_opportunity_frames,
)
from tools.opportunity_readiness_reference import calculate_opportunity_readiness
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.range_rotation_opportunity_reference import (
    RangeIntegrationVariant,
    actionable,
    ambiguous_source_bars,
    build_range_opportunity_frames,
)
from tools.range_rotation_reference import (
    RangeOutcome,
    RangeRotationEpisode,
    RangeRotationOutcome,
    RangeTrigger,
    classify_range_rotation,
    detect_range_rotations,
)
from tools.rsi_state_reference import calculate as calculate_rsi


TIMEFRAMES = ("4h", "1d")


@dataclass(frozen=True)
class RangeExecutionResponse:
    episode_id: str
    direction: int
    regime_relation: str
    structural_outcome: str
    actionable: bool
    prep_bar: int | None
    armed_bar: int | None
    confirm_bar: int | None
    prep_latency_bars: int | None
    armed_latency_bars: int | None
    confirm_latency_bars: int | None
    confirm_displacement_atr: float | None
    confirm_room_to_opposite_atr: float | None
    confirm_before_midpoint: bool
    confirm_same_bar_as_midpoint: bool


def _dist(values) -> dict:
    return distribution([float(v) for v in values if v is not None])


def _event_counts(samples) -> Counter:
    c = Counter()
    for s in samples:
        e = s.result.events
        c["PREPARING_ENTERED"] += int(e.preparing_entered)
        c["ARMED_ENTERED"] += int(e.armed_entered)
        c["CONFIRM"] += int(e.confirm)
        c["CANCELED"] += int(e.canceled)
    return c


def _quick_cancel(samples, entered_attr: str, max_bars: int = 3) -> int:
    starts = [
        i for i, s in enumerate(samples)
        if getattr(s.result.events, entered_attr)
    ]
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
    return None if rows == 0 else value * 1000.0 / rows


def _structural_summary(
    episodes: Sequence[RangeRotationEpisode],
    outcomes: Sequence[RangeRotationOutcome],
) -> dict:
    n = len(episodes)
    counts = Counter(o.outcome.value for o in outcomes)
    midpoint = sum(
        o.outcome in {RangeOutcome.MID_REACHED, RangeOutcome.OPPOSITE_REACHED}
        for o in outcomes
    )
    opposite = sum(o.outcome == RangeOutcome.OPPOSITE_REACHED for o in outcomes)
    failed = sum(o.outcome == RangeOutcome.FAILED_BEFORE_MID for o in outcomes)
    return {
        "episodes": n,
        "midpoint_or_better_pct": pct(midpoint, n),
        "opposite_reached_pct": pct(opposite, n),
        "failed_before_mid_pct": pct(failed, n),
        "censored_pct": pct(counts["CENSORED"], n),
        "outcome_counts": dict(sorted(counts.items())),
    }


def _measure_responses(
    episodes: Sequence[RangeRotationEpisode],
    outcomes: Sequence[RangeRotationOutcome],
    frames,
    samples,
    closes: Sequence[float],
    *,
    variant: RangeIntegrationVariant,
) -> list[RangeExecutionResponse]:
    outcome_by_id = {o.episode_id: o for o in outcomes}
    out: list[RangeExecutionResponse] = []

    for e in episodes:
        o = outcome_by_id[e.episode_id]
        is_actionable = actionable(e, variant)
        prep_bar = armed_bar = confirm_bar = None

        if is_actionable:
            end = o.outcome_bar if o.outcome_bar is not None else len(samples) - 1
            end = min(end, len(samples) - 1)

            for i in range(e.confirmation_bar, end + 1):
                frame = frames[i]
                sample = samples[i]
                owns_bar = (
                    frame.kind == OpportunityKind.RANGE_ROTATION
                    and frame.source_bar == e.confirmation_bar
                    and frame.direction == e.direction
                )
                if not owns_bar:
                    continue

                state = sample.result.state
                if (
                    prep_bar is None
                    and state.direction == e.direction
                    and state.readiness >= Readiness.PREP
                ):
                    prep_bar = i
                if (
                    armed_bar is None
                    and state.direction == e.direction
                    and state.readiness >= Readiness.ARMED
                ):
                    armed_bar = i
                if sample.result.events.confirm and state.direction == e.direction:
                    confirm_bar = i
                    break

        def latency(bar):
            return None if bar is None else bar - e.confirmation_bar

        displacement = None
        room = None
        before_mid = False
        same_mid = False
        if confirm_bar is not None:
            if e.atr is not None and e.atr > 0:
                displacement = (
                    e.direction * (float(closes[confirm_bar]) - e.reference_price) / e.atr
                )
                destination = (
                    e.range_high - e.edge_band
                    if e.direction == 1
                    else e.range_low + e.edge_band
                )
                room = e.direction * (destination - float(closes[confirm_bar])) / e.atr
            if o.midpoint_bar is None:
                before_mid = True
            else:
                before_mid = confirm_bar < o.midpoint_bar
                same_mid = confirm_bar == o.midpoint_bar

        out.append(
            RangeExecutionResponse(
                episode_id=e.episode_id,
                direction=e.direction,
                regime_relation=e.regime_relation.value,
                structural_outcome=o.outcome.value,
                actionable=is_actionable,
                prep_bar=prep_bar,
                armed_bar=armed_bar,
                confirm_bar=confirm_bar,
                prep_latency_bars=latency(prep_bar),
                armed_latency_bars=latency(armed_bar),
                confirm_latency_bars=latency(confirm_bar),
                confirm_displacement_atr=displacement,
                confirm_room_to_opposite_atr=room,
                confirm_before_midpoint=before_mid,
                confirm_same_bar_as_midpoint=same_mid,
            )
        )

    return out


def _response_summary(responses: Sequence[RangeExecutionResponse]) -> dict:
    actionable_rows = [r for r in responses if r.actionable]
    n = len(actionable_rows)
    prep = [r for r in actionable_rows if r.prep_bar is not None]
    armed = [r for r in actionable_rows if r.armed_bar is not None]
    confirmed = [r for r in actionable_rows if r.confirm_bar is not None]

    return {
        "episodes_total": len(responses),
        "actionable_episodes": n,
        "awareness_only_episodes": len(responses) - n,
        "reached_prep_pct": pct(len(prep), n),
        "reached_armed_pct": pct(len(armed), n),
        "confirmed_pct": pct(len(confirmed), n),
        "confirmed_count": len(confirmed),
        "confirm_before_midpoint_count": sum(r.confirm_before_midpoint for r in confirmed),
        "confirm_before_midpoint_pct": pct(
            sum(r.confirm_before_midpoint for r in confirmed),
            len(confirmed),
        ),
        "confirm_same_bar_as_midpoint_count": sum(
            r.confirm_same_bar_as_midpoint for r in confirmed
        ),
        "prep_latency_bars": _dist([r.prep_latency_bars for r in prep]),
        "armed_latency_bars": _dist([r.armed_latency_bars for r in armed]),
        "confirm_latency_bars": _dist([r.confirm_latency_bars for r in confirmed]),
        "confirm_displacement_atr": _dist([
            r.confirm_displacement_atr for r in confirmed
        ]),
        "confirm_room_to_opposite_atr": _dist([
            r.confirm_room_to_opposite_atr for r in confirmed
        ]),
        "confirm_direction_counts": dict(sorted(Counter(
            "LONG" if r.direction == 1 else "SHORT"
            for r in confirmed
        ).items())),
    }


def _structural_by_confirmation(
    episodes: Sequence[RangeRotationEpisode],
    outcomes: Sequence[RangeRotationOutcome],
    responses: Sequence[RangeExecutionResponse],
) -> dict:
    response_by_id = {r.episode_id: r for r in responses}
    confirmed_e = []
    confirmed_o = []
    missed_e = []
    missed_o = []

    for e, o in zip(episodes, outcomes):
        r = response_by_id[e.episode_id]
        if not r.actionable:
            continue
        if r.confirm_bar is not None:
            confirmed_e.append(e)
            confirmed_o.append(o)
        else:
            missed_e.append(e)
            missed_o.append(o)

    return {
        "confirmed": _structural_summary(confirmed_e, confirmed_o),
        "not_confirmed": _structural_summary(missed_e, missed_o),
    }


def _by_relation(
    episodes: Sequence[RangeRotationEpisode],
    outcomes: Sequence[RangeRotationOutcome],
    responses: Sequence[RangeExecutionResponse],
) -> dict:
    response_by_id = {r.episode_id: r for r in responses}
    out = {}
    for relation in sorted({e.regime_relation.value for e in episodes}):
        idx = [i for i, e in enumerate(episodes) if e.regime_relation.value == relation]
        es = [episodes[i] for i in idx]
        os = [outcomes[i] for i in idx]
        rs = [response_by_id[e.episode_id] for e in es]
        out[relation] = {
            "structural": _structural_summary(es, os),
            "execution": _response_summary(rs),
        }
    return out


def analyze_timeframe(
    timeframe: str,
    datasets: dict[str, dict],
    *,
    tick_size: float,
) -> dict:
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

    # Frozen 0.1 comparator is calculated independently and never mutated.
    baseline_samples = calculate_execution(bars)

    # Accepted Opportunity v2 baseline remains unchanged; used only to measure
    # overlap/arbitration pressure from the new range class.
    canonical_pse = calculate_participation(
        [
            ParticipationBar(float(h), float(l), float(c), float(v))
            for h, l, c, v in zip(
                data["high"], data["low"], data["close"], data["volume"]
            )
        ],
        [s.map_dir for s in snapshots],
    )
    base_episodes = detect_episodes(snapshots, data["high"], data["low"])
    base_frames = build_opportunity_frames(
        base_episodes,
        snapshots,
        data["close"],
        locations,
        canonical_pse,
    )
    base_opportunity_samples = calculate_opportunity_readiness(bars, base_frames)

    range_all = detect_range_rotations(
        snapshots,
        data["high"],
        data["low"],
        data["close"],
    )
    range_episodes = [e for e in range_all if e.trigger == RangeTrigger.EDGE_REJECTION]
    outcomes = [
        classify_range_rotation(
            e,
            snapshots,
            data["high"],
            data["low"],
            data["close"],
        )
        for e in range_episodes
    ]

    variants = {}
    for variant in RangeIntegrationVariant:
        frames = build_range_opportunity_frames(
            range_episodes,
            snapshots,
            data["high"],
            data["low"],
            data["close"],
            variant=variant,
        )
        samples = calculate_opportunity_readiness(bars, frames)
        responses = _measure_responses(
            range_episodes,
            outcomes,
            frames,
            samples,
            data["close"],
            variant=variant,
        )

        active_range_bars = [
            i for i, f in enumerate(frames)
            if f.kind == OpportunityKind.RANGE_ROTATION
        ]
        overlap_bars = sum(
            base_frames[i].kind != OpportunityKind.NONE
            for i in active_range_bars
        )
        actionable_sources = [
            e for e in range_episodes if actionable(e, variant)
        ]
        source_overlap = sum(
            base_frames[e.confirmation_bar].kind != OpportunityKind.NONE
            for e in actionable_sources
        )

        events = _event_counts(samples)
        variants[variant.value] = {
            "response": _response_summary(responses),
            "structural_by_confirmation": _structural_by_confirmation(
                range_episodes, outcomes, responses
            ),
            "by_regime_relation": _by_relation(
                range_episodes, outcomes, responses
            ),
            "event_load": {
                "events": dict(sorted(events.items())),
                "events_per_1000": {
                    k: _per_1000(v, len(bars))
                    for k, v in sorted(events.items())
                },
                "quick_prep_cancel_3": _quick_cancel(samples, "preparing_entered"),
                "quick_armed_cancel_3": _quick_cancel(samples, "armed_entered"),
            },
            "overlap_with_accepted_opportunity_v2": {
                "active_range_bars": len(active_range_bars),
                "overlap_bars": overlap_bars,
                "overlap_bar_pct": pct(overlap_bars, len(active_range_bars)),
                "actionable_sources": len(actionable_sources),
                "source_overlap_count": source_overlap,
                "source_overlap_pct": pct(source_overlap, len(actionable_sources)),
            },
            "ambiguous_source_bars": ambiguous_source_bars(
                range_episodes,
                variant=variant,
            ),
        }

    return {
        "rows": len(bars),
        "range_edge_episodes": len(range_episodes),
        "structural_all_edge": _structural_summary(range_episodes, outcomes),
        "frozen_0_1": {
            "events": dict(sorted(_event_counts(baseline_samples).items())),
            "mutated": False,
        },
        "accepted_opportunity_v2": {
            "events": dict(sorted(_event_counts(base_opportunity_samples).items())),
            "mutated": False,
        },
        "variants": variants,
    }


def _fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown_report(report: dict) -> str:
    lines = [
        "# Suite 0.2 — RANGE_ROTATION Opportunity v2 integration A/B",
        "",
        "Research-only. Frozen 0.1 and accepted breakout/reacceleration Opportunity v2 are independent comparators.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "## Variant summary",
        "",
        "| TF | variant | actionable | PREP % | ARMED % | CONFIRM % | confirms | before midpoint % | confirm latency med | room to opposite ATR med | cancel/1000 | quick PREP cancel | source overlap % |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for tf, item in report["timeframes"].items():
        for name, v in item["variants"].items():
            r = v["response"]
            e = v["event_load"]
            ov = v["overlap_with_accepted_opportunity_v2"]
            lines.append(
                "| {tf} | {name} | {n} | {p} | {a} | {c} | {cc} | {bm} | {lat} | {room} | {cancel} | {qp} | {overlap} |".format(
                    tf=tf,
                    name=name,
                    n=r["actionable_episodes"],
                    p=_fmt(r["reached_prep_pct"]),
                    a=_fmt(r["reached_armed_pct"]),
                    c=_fmt(r["confirmed_pct"]),
                    cc=r["confirmed_count"],
                    bm=_fmt(r["confirm_before_midpoint_pct"]),
                    lat=_fmt(r["confirm_latency_bars"]["median"]),
                    room=_fmt(r["confirm_room_to_opposite_atr"]["median"]),
                    cancel=_fmt(e["events_per_1000"].get("CANCELED")),
                    qp=e["quick_prep_cancel_3"],
                    overlap=_fmt(ov["source_overlap_pct"]),
                )
            )

    lines += [
        "",
        "## Structural discrimination among actionable episodes",
        "",
        "| TF | variant | group | episodes | midpoint+ % | opposite % | fail before mid % | censored % |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        for name, v in item["variants"].items():
            for group, s in v["structural_by_confirmation"].items():
                lines.append(
                    f"| {tf} | {name} | {group} | {s['episodes']} | {_fmt(s['midpoint_or_better_pct'])} | {_fmt(s['opposite_reached_pct'])} | {_fmt(s['failed_before_mid_pct'])} | {_fmt(s['censored_pct'])} |"
                )

    lines += [
        "",
        "## Regime relation",
        "",
        "| TF | variant | relation | episodes | actionable | confirm % | midpoint+ % | fail-before-mid % |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf, item in report["timeframes"].items():
        for name, v in item["variants"].items():
            for relation, row in v["by_regime_relation"].items():
                s = row["structural"]
                r = row["execution"]
                lines.append(
                    f"| {tf} | {name} | {relation} | {s['episodes']} | {r['actionable_episodes']} | {_fmt(r['confirmed_pct'])} | {_fmt(s['midpoint_or_better_pct'])} | {_fmt(s['failed_before_mid_pct'])} |"
                )

    lines += [
        "",
        "## Guardrails",
        "",
        "- EDGE_REJECTION is the only primary RANGE_ROTATION trigger in this integration.",
        "- Source bar starts STRONG; next-bar structural persistence + directional progress is required for ACCEPTED.",
        "- Opposite-edge arrival clears the frame before a late close-confirmation can be counted.",
        "- ALL_EDGE and CONTEXT_GUARDED differ only in whether AGAINST_REGIME may enter readiness.",
        "- Accepted breakout/reacceleration Opportunity v2 is not retuned.",
        "- Frozen Execution 0.1 is not mutated.",
        "- Structural outcomes are not profitability/win-rate claims.",
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
            "accepted_opportunity_v2_head": "329cdcac039f11cd1a81bf9138cfe67ab83a142f",
            "accepted_range_research_head": "905fc9adf190b0c1b12d17d2109027302ee8a410",
        },
        "timeframes": {
            tf: analyze_timeframe(tf, datasets, tick_size=args.tick_size)
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

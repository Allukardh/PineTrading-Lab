#!/usr/bin/env python3
"""Evaluate minimal Suite 0.2 breakout acceptance/follow-through contracts.

The frozen 0.1 production baseline is not modified. Later breakout outcome is
used only to evaluate a rule that emits at candidate-close or a later confirmed
follow-through bar.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from tools.breakout_acceptance_reference import (
    BreakoutAcceptance,
    decide,
)
from tools.execution_historical_evidence import (
    build_context_dirs,
    distribution,
    load_dataset,
    sha256_file,
)
from tools.market_map_offline_core import (
    CONTEXT_TF,
    Candle,
    IntegrationSnapshot,
    Kernel,
)
from tools.momentum_turn_reference import Bar as MomentumBar, calculate as calculate_momentum
from tools.opportunity_candidate_features import extract_features
from tools.opportunity_episode_reference import OpportunityType, detect_episodes
from tools.opportunity_outcome_reference import CandidateOutcome, classify_all
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi


TIMEFRAMES = ("4h", "1d")


def to_mm_candles(data: dict) -> list[Candle]:
    return [
        Candle(
            int(round(t.timestamp() * 1_000_000.0)),
            float(o),
            float(h),
            float(l),
            float(c),
            float(v),
        )
        for t, o, h, l, c, v in zip(
            data["open_time"],
            data["open"],
            data["high"],
            data["low"],
            data["close"],
            data["volume"],
        )
    ]


def _pct(a: int, b: int) -> float | None:
    return None if not b else 100.0 * a / b


def _fmt(value, digits=2):
    return "n/a" if value is None else f"{value:.{digits}f}"


def _metric_for_rule(
    rule: BreakoutAcceptance,
    episodes,
    features_by_id,
    outcomes,
    snapshots,
    closes,
) -> dict:
    held_total = fakeout_total = unresolved_total = 0
    accepted_held = accepted_fakeout = accepted_unresolved = 0
    delays = []
    delay_counts = Counter()
    displacements = []

    for episode in episodes:
        outcome = outcomes[episode.episode_id].outcome
        if outcome == CandidateOutcome.BREAKOUT_HELD:
            held_total += 1
        elif outcome == CandidateOutcome.BREAKOUT_FAKEOUT:
            fakeout_total += 1
        else:
            unresolved_total += 1

        decision = decide(
            rule,
            episode,
            features_by_id[episode.episode_id],
            snapshots,
            closes,
        )
        if not decision.accepted:
            continue

        if outcome == CandidateOutcome.BREAKOUT_HELD:
            accepted_held += 1
        elif outcome == CandidateOutcome.BREAKOUT_FAKEOUT:
            accepted_fakeout += 1
        else:
            accepted_unresolved += 1

        if decision.delay_bars is not None:
            delays.append(float(decision.delay_bars))
            delay_counts[str(decision.delay_bars)] += 1

        bar = decision.accepted_bar
        if (
            bar is not None
            and episode.atr is not None
            and episode.atr > 0
        ):
            displacement = (
                episode.direction
                * (float(closes[bar]) - episode.reference_price)
                / episode.atr
            )
            if math.isfinite(displacement):
                displacements.append(displacement)

    accepted_resolved = accepted_held + accepted_fakeout
    resolved = held_total + fakeout_total
    base_held_share = _pct(held_total, resolved)
    held_share = _pct(accepted_held, accepted_resolved)
    lift = (
        None
        if base_held_share is None or held_share is None or base_held_share == 0
        else held_share / base_held_share
    )

    return {
        "rule": rule.value,
        "held_total": held_total,
        "fakeout_total": fakeout_total,
        "unresolved_total": unresolved_total,
        "accepted_held": accepted_held,
        "accepted_fakeout": accepted_fakeout,
        "accepted_unresolved": accepted_unresolved,
        "held_recall_pct": _pct(accepted_held, held_total),
        "fakeout_acceptance_pct": _pct(accepted_fakeout, fakeout_total),
        "accepted_resolved_held_share_pct": held_share,
        "base_resolved_held_share_pct": base_held_share,
        "held_share_lift_vs_base": lift,
        "delay_bars": distribution(delays),
        "delay_counts": dict(sorted(delay_counts.items())),
        "acceptance_displacement_atr": distribution(displacements),
    }


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

    episodes = [
        e for e in detect_episodes(snapshots, data["high"], data["low"])
        if e.opportunity_type == OpportunityType.BREAKOUT_CANDIDATE
    ]
    outcomes = classify_all(episodes, snapshots)

    momentum = calculate_momentum(
        [
            MomentumBar(float(o), float(h), float(l), float(c))
            for o, h, l, c in zip(
                data["open"], data["high"], data["low"], data["close"]
            )
        ]
    )
    rsi = calculate_rsi(data["close"])
    rsi_cache = {tf: calculate_rsi(ds["close"]) for tf, ds in datasets.items()}
    context_dirs = build_context_dirs(timeframe, datasets, rsi_cache)

    p_bars = [
        ParticipationBar(float(h), float(l), float(c), float(v))
        for h, l, c, v in zip(
            data["high"], data["low"], data["close"], data["volume"]
        )
    ]
    pse_long = calculate_participation(p_bars, [1] * len(p_bars))
    pse_short = calculate_participation(p_bars, [-1] * len(p_bars))

    features_by_id = {}
    for e in episodes:
        pse = pse_long if e.direction == 1 else pse_short
        features_by_id[e.episode_id] = extract_features(
            e,
            snapshots,
            data["open"],
            data["high"],
            data["low"],
            data["close"],
            momentum,
            rsi,
            pse,
            context_dirs,
        )

    rules = [
        BreakoutAcceptance.PENETRATION,
        BreakoutAcceptance.PENETRATION_PSE,
        BreakoutAcceptance.PENETRATION_MTE,
        BreakoutAcceptance.PENETRATION_PSE_MTE,
        BreakoutAcceptance.HOLD_1,
        BreakoutAcceptance.HOLD_2,
        BreakoutAcceptance.PSE_OR_HOLD_1,
        BreakoutAcceptance.PSE_MTE_OR_HOLD_1,
        BreakoutAcceptance.PSE_OR_HOLD_2,
        BreakoutAcceptance.PSE_MTE_OR_HOLD_2,
    ]

    return {
        "episodes": len(episodes),
        "outcomes": dict(
            Counter(outcomes[e.episode_id].outcome.value for e in episodes)
        ),
        "rules": {
            rule.value: _metric_for_rule(
                rule,
                episodes,
                features_by_id,
                outcomes,
                snapshots,
                data["close"],
            )
            for rule in rules
        },
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Suite 0.2 — Breakout acceptance / follow-through evidence",
        "",
        "Research-only. No production Pine/default/profile is changed.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
        "Rules use only information available when they emit. Outcome is retrospective evaluation only.",
        "",
    ]

    for tf, item in report["timeframes"].items():
        lines += [
            f"## {tf}",
            "",
            f"- breakout candidates: **{item['episodes']}**",
            f"- outcomes: `{json.dumps(item['outcomes'], sort_keys=True)}`",
            "",
            "| rule | held recall % | fakeout accepted % | held share among accepted % | lift vs base | delay-path counts | median delay bars | median displacement ATR |",
            "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
        for rule, metric in item["rules"].items():
            lines.append(
                "| {rule} | {rec} | {fake} | {share} | {lift} | {paths} | {delay} | {disp} |".format(
                    rule=rule,
                    rec=_fmt(metric["held_recall_pct"]),
                    fake=_fmt(metric["fakeout_acceptance_pct"]),
                    share=_fmt(metric["accepted_resolved_held_share_pct"]),
                    lift=_fmt(metric["held_share_lift_vs_base"], 3),
                    paths=json.dumps(metric["delay_counts"], sort_keys=True),
                    delay=_fmt(metric["delay_bars"]["median"]),
                    disp=_fmt(metric["acceptance_displacement_atr"]["median"]),
                )
            )
        lines.append("")

    lines += [
        "## Guardrails",
        "",
        "- PENETRATION uses a fixed 0.50 ATR structural-depth research threshold.",
        "- PSE means the already-accepted PSE CONFIRM semantic; no new volume threshold is invented here.",
        "- MTE aligned means accepted directional TURN/ACCEL semantics.",
        "- HOLD_1 / HOLD_2 emit one/two confirmed bars later and never backdate.",
        "- High held-share with tiny held recall is not automatically useful.",
        "- This report chooses no production rule by itself.",
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

    required = ("4h", "1d", "1w")
    datasets = {}
    metadata = {}
    for tf in required:
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
        metadata[tf] = {
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
            "datasets": metadata,
            "frozen_market_map_promotion": "0eeb0d37b256a950cfb38f627fa3521bb213d380",
            "frozen_execution_promotion": "a7557df2d0142441ea782dba4b8c3f95ebc38371",
        },
        "timeframes": {},
    }

    for tf in TIMEFRAMES:
        report["timeframes"][tf] = analyze_timeframe(
            tf,
            datasets,
            args.tick_size,
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

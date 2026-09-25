#!/usr/bin/env python3
"""Suite 0.2 contemporaneous feature/outcome discriminant study.

Purpose:
- measure which evidence already available on a candidate bar differs between
  later-held vs fakeout breakouts;
- measure which evidence differs between regime-transition candidates that
  mature into a coherent reversal within 12/24/48 bars and those that do not.

This is feature diagnostics, not a trained predictor and not threshold tuning.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence

from tools.execution_historical_evidence import (
    build_context_dirs,
    distribution,
    load_dataset,
    sha256_file,
)
from tools.execution_integrated_evidence import to_mm_candles
from tools.market_map_offline_core import CONTEXT_TF, IntegrationSnapshot, Kernel
from tools.momentum_turn_reference import Bar as MomentumBar
from tools.momentum_turn_reference import calculate as calculate_momentum
from tools.opportunity_candidate_features import CandidateFeatures, extract_features
from tools.opportunity_episode_reference import OpportunityType, detect_episodes
from tools.opportunity_outcome_reference import CandidateOutcome, classify_all
from tools.participation_reference import (
    ParticipationBar,
    calculate as calculate_participation,
)
from tools.rsi_state_reference import calculate as calculate_rsi


TIMEFRAMES = ("4h", "1d")
CONTINUOUS_FEATURES = (
    "prior_regime_bars",
    "break_penetration_atr",
    "candle_body_direction_atr",
    "candle_range_atr",
    "close_location_directional",
    "mte_core_directional",
    "mte_acceleration_directional",
    "rsi_center_directional",
    "rsi_step_directional",
    "relative_volume",
    "directional_pressure",
    "destination_room_atr",
    "invalidation_distance_atr",
)
CATEGORICAL_FEATURES = (
    "momentum_state",
    "rsi_state",
    "participation_state",
    "htf_context_alignment",
    "strong_volume_expansion",
)


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _auc(positive: Sequence[float], negative: Sequence[float]) -> float | None:
    """Mann-Whitney probability that a positive value exceeds a negative."""
    pos = [float(v) for v in positive if _finite(v)]
    neg = [float(v) for v in negative if _finite(v)]
    if not pos or not neg:
        return None

    combined = [(v, 1) for v in pos] + [(v, 0) for v in neg]
    combined.sort(key=lambda x: x[0])

    rank = 1
    pos_rank_sum = 0.0
    i = 0
    while i < len(combined):
        j = i + 1
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (rank + (rank + (j - i) - 1)) / 2.0
        pos_rank_sum += avg_rank * sum(label for _, label in combined[i:j])
        rank += j - i
        i = j

    n_pos = len(pos)
    n_neg = len(neg)
    u = pos_rank_sum - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def _continuous_compare(
    positive: Sequence[CandidateFeatures],
    negative: Sequence[CandidateFeatures],
) -> dict:
    out = {}
    for name in CONTINUOUS_FEATURES:
        pos = [getattr(x, name) for x in positive if _finite(getattr(x, name))]
        neg = [getattr(x, name) for x in negative if _finite(getattr(x, name))]
        auc = _auc(pos, neg)
        oriented = None if auc is None else max(auc, 1.0 - auc)
        orientation = (
            None
            if auc is None
            else "HIGHER_IN_POSITIVE"
            if auc >= 0.5
            else "LOWER_IN_POSITIVE"
        )
        out[name] = {
            "positive": distribution([float(v) for v in pos]),
            "negative": distribution([float(v) for v in neg]),
            "auc_positive_gt_negative": auc,
            "oriented_auc": oriented,
            "orientation": orientation,
        }
    return out


def _categorical_compare(
    positive: Sequence[CandidateFeatures],
    negative: Sequence[CandidateFeatures],
) -> dict:
    out = {}
    for name in CATEGORICAL_FEATURES:
        pc = Counter(str(getattr(x, name)) for x in positive)
        nc = Counter(str(getattr(x, name)) for x in negative)
        out[name] = {
            "positive_counts": dict(sorted(pc.items())),
            "negative_counts": dict(sorted(nc.items())),
            "positive_pct": {
                k: 100.0 * v / len(positive) if positive else None
                for k, v in sorted(pc.items())
            },
            "negative_pct": {
                k: 100.0 * v / len(negative) if negative else None
                for k, v in sorted(nc.items())
            },
        }
    return out


def _comparison(
    positive: Sequence[CandidateFeatures],
    negative: Sequence[CandidateFeatures],
) -> dict:
    return {
        "positive_count": len(positive),
        "negative_count": len(negative),
        "continuous": _continuous_compare(positive, negative),
        "categorical": _categorical_compare(positive, negative),
    }


def _feature_row(f: CandidateFeatures) -> dict:
    return {
        name: getattr(f, name)
        for name in (
            "episode_id",
            "opportunity_type",
            "direction",
            "bar_index",
            *CONTINUOUS_FEATURES,
            *CATEGORICAL_FEATURES,
        )
    }


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
    Kernel(
        chart,
        context,
        daily,
        weekly,
        timeframe,
        tick=tick_size,
    ).run(integration_rows=snapshots, emit_audit=False)

    episodes = detect_episodes(snapshots, data["high"], data["low"])
    outcomes = classify_all(episodes, snapshots)

    momentum = calculate_momentum(
        [
            MomentumBar(o, h, l, c)
            for o, h, l, c in zip(
                data["open"], data["high"], data["low"], data["close"]
            )
        ]
    )
    rsi = calculate_rsi(data["close"])
    rsi_cache = {tf: calculate_rsi(ds["close"]) for tf, ds in datasets.items()}
    context_dirs = build_context_dirs(timeframe, datasets, rsi_cache)

    p_bars = [
        ParticipationBar(h, l, c, v)
        for h, l, c, v in zip(
            data["high"], data["low"], data["close"], data["volume"]
        )
    ]
    pse_long = calculate_participation(p_bars, [1] * len(p_bars))
    pse_short = calculate_participation(p_bars, [-1] * len(p_bars))

    feature_by_id: dict[str, CandidateFeatures] = {}
    episode_by_id = {e.episode_id: e for e in episodes}

    for episode in episodes:
        if episode.opportunity_type not in {
            OpportunityType.BREAKOUT_CANDIDATE,
            OpportunityType.REGIME_TRANSITION_CANDIDATE,
        }:
            continue
        pse = pse_long if episode.direction == 1 else pse_short
        feature_by_id[episode.episode_id] = extract_features(
            episode,
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

    # Breakout: accepted MM fakeout window gives a clean held-vs-fakeout
    # retrospective diagnostic.
    breakout_held = []
    breakout_fakeout = []
    for episode_id, features in feature_by_id.items():
        episode = episode_by_id[episode_id]
        if episode.opportunity_type != OpportunityType.BREAKOUT_CANDIDATE:
            continue
        outcome = outcomes[episode_id].outcome
        if outcome == CandidateOutcome.BREAKOUT_HELD:
            breakout_held.append(features)
        elif outcome == CandidateOutcome.BREAKOUT_FAKEOUT:
            breakout_fakeout.append(features)

    comparisons = {
        "BREAKOUT_HELD_vs_FAKEOUT": _comparison(
            breakout_held,
            breakout_fakeout,
        )
    }

    # Regime transition: target is FAST maturation into the strict coherent
    # reversal, not eventual maturation months later.
    transitions = [
        e
        for e in episodes
        if e.opportunity_type == OpportunityType.REGIME_TRANSITION_CANDIDATE
        and e.episode_id in feature_by_id
    ]
    for horizon in (12, 24, 48):
        positive = []
        negative = []
        for episode in transitions:
            if episode.confirmation_bar + horizon >= len(snapshots):
                continue
            outcome = outcomes[episode.episode_id]
            matured = (
                outcome.outcome == CandidateOutcome.REGIME_MATURED
                and outcome.outcome_bar is not None
                and outcome.outcome_bar - episode.confirmation_bar <= horizon
            )
            (positive if matured else negative).append(
                feature_by_id[episode.episode_id]
            )
        comparisons[f"REGIME_MATURED_WITHIN_{horizon}_vs_NOT"] = _comparison(
            positive,
            negative,
        )

    # Compact top-feature ranking by univariate separation. This is a
    # diagnostic shortlist only; it is not a model and does not select a
    # production threshold.
    rankings = {}
    for name, comp in comparisons.items():
        rows = []
        for feature, stat in comp["continuous"].items():
            if stat["oriented_auc"] is None:
                continue
            rows.append(
                {
                    "feature": feature,
                    "oriented_auc": stat["oriented_auc"],
                    "orientation": stat["orientation"],
                    "positive_median": stat["positive"]["median"],
                    "negative_median": stat["negative"]["median"],
                }
            )
        rows.sort(key=lambda r: r["oriented_auc"], reverse=True)
        rankings[name] = rows

    # Representative rows aid semantic inspection without dumping the whole
    # dataset into the report.
    examples = {}
    for name, comp in comparisons.items():
        if name.startswith("BREAKOUT"):
            pos = breakout_held[:5]
            neg = breakout_fakeout[:5]
        else:
            horizon = int(name.split("_WITHIN_")[1].split("_")[0])
            pos = []
            neg = []
            for episode in transitions:
                if episode.confirmation_bar + horizon >= len(snapshots):
                    continue
                outcome = outcomes[episode.episode_id]
                matured = (
                    outcome.outcome == CandidateOutcome.REGIME_MATURED
                    and outcome.outcome_bar is not None
                    and outcome.outcome_bar - episode.confirmation_bar <= horizon
                )
                target = pos if matured else neg
                if len(target) < 5:
                    target.append(feature_by_id[episode.episode_id])
                if len(pos) >= 5 and len(neg) >= 5:
                    break
        examples[name] = {
            "positive": [_feature_row(x) for x in pos],
            "negative": [_feature_row(x) for x in neg],
        }

    return {
        "rows": len(chart),
        "candidate_feature_rows": len(feature_by_id),
        "comparisons": comparisons,
        "rankings": rankings,
        "examples": examples,
    }


def _fmt(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown_report(report: dict) -> str:
    lines = [
        "# Suite 0.2 — Candidate feature discriminant evidence",
        "",
        "Contemporaneous feature diagnostics only. No production threshold is selected.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        "",
    ]

    for tf, item in report["timeframes"].items():
        lines += [f"## {tf}", ""]
        for comparison, comp in item["comparisons"].items():
            lines += [
                f"### {comparison}",
                "",
                f"- positive rows: **{comp['positive_count']}**",
                f"- negative rows: **{comp['negative_count']}**",
                "",
                "| feature | oriented AUC | orientation | positive median | negative median |",
                "| --- | ---: | --- | ---: | ---: |",
            ]
            for row in item["rankings"][comparison][:8]:
                lines.append(
                    "| {feature} | {auc} | {orientation} | {pm} | {nm} |".format(
                        feature=row["feature"],
                        auc=_fmt(row["oriented_auc"]),
                        orientation=row["orientation"],
                        pm=_fmt(row["positive_median"]),
                        nm=_fmt(row["negative_median"]),
                    )
                )
            lines.append("")

    lines += [
        "## Guardrails",
        "",
        "- All features are available on the candidate confirmation bar.",
        "- Outcomes are retrospective and are never used to backdate live knowledge.",
        "- Oriented AUC is a univariate separation diagnostic, not a trade probability and not a production model.",
        "- No threshold/profile/default is tuned by this report.",
        "- Small positive samples, especially fast regime maturation on 1D, must not drive decisions alone.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--canonical-manifest", type=Path, required=True)
    ap.add_argument("--timeframes", default="4h,1d")
    ap.add_argument("--tick-size", type=float, default=0.01)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    ap.add_argument("--code-sha", default="unknown")
    args = ap.parse_args()

    requested = tuple(x.strip() for x in args.timeframes.split(",") if x.strip())
    unsupported = [tf for tf in requested if tf not in TIMEFRAMES]
    if unsupported:
        raise SystemExit(f"unsupported first-pass timeframes: {unsupported}")

    canonical = json.loads(args.canonical_manifest.read_text(encoding="utf-8"))
    expected = {d["timeframe"]: d for d in canonical["datasets"]}
    symbol = args.symbol.upper()
    market = canonical.get("market", "spot")

    required = ("4h", "1d", "1w")
    datasets = {}
    meta = {}
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
            "timeframes": list(requested),
            "datasets": meta,
            "frozen_market_map_promotion": "0eeb0d37b256a950cfb38f627fa3521bb213d380",
            "frozen_execution_promotion": "a7557df2d0142441ea782dba4b8c3f95ebc38371",
        },
        "timeframes": {},
    }

    for tf in requested:
        report["timeframes"][tf] = analyze_timeframe(
            tf,
            datasets,
            tick_size=args.tick_size,
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

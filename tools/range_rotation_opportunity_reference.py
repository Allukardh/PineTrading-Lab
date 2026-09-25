#!/usr/bin/env python3
"""Research-only RANGE_ROTATION -> Opportunity v2 frame timeline.

The accepted structural RANGE_ROTATION label is kept independent from the
frozen Execution 0.1 path and from the already accepted breakout /
reacceleration Opportunity v2 frame builder.

Lifecycle:
- confirmed EDGE_REJECTION -> STRONG
- next bar must preserve the same compatible range and make directional
  progress while remaining inside the range -> ACCEPTED
- incompatible range, confirmed edge invalidation, or opposite-edge arrival
  clears the frame
- no backdating

Two pre-registered variants:
- ALL_EDGE: every EDGE_REJECTION is actionable
- CONTEXT_GUARDED: AGAINST_REGIME remains awareness-only
"""
from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import Sequence

from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_execution_counterfactual import (
    OpportunityFrame,
    OpportunityKind,
    OpportunityStage,
)
from tools.range_rotation_reference import (
    RangeRotationEpisode,
    RangeTrigger,
    RegimeRelation,
    box_compatible_with_episode,
    box_from_snapshot,
)


class RangeIntegrationVariant(str, Enum):
    ALL_EDGE = "ALL_EDGE"
    CONTEXT_GUARDED = "CONTEXT_GUARDED"


def actionable(
    episode: RangeRotationEpisode,
    variant: RangeIntegrationVariant,
) -> bool:
    if episode.trigger != RangeTrigger.EDGE_REJECTION:
        return False
    if (
        variant == RangeIntegrationVariant.CONTEXT_GUARDED
        and episode.regime_relation == RegimeRelation.AGAINST_REGIME
    ):
        return False
    return True


def _inside(e: RangeRotationEpisode, close: float) -> bool:
    return e.range_low <= close <= e.range_high


def _directional_progress(e: RangeRotationEpisode, close: float) -> bool:
    return (
        close > e.reference_price
        if e.direction == 1
        else close < e.reference_price
    )


def _opposite_reached(
    e: RangeRotationEpisode,
    high: float,
    low: float,
) -> bool:
    if e.direction == 1:
        return high >= e.range_high - e.edge_band
    return low <= e.range_low + e.edge_band


def _invalidated(e: RangeRotationEpisode, close: float) -> bool:
    if e.direction == 1:
        return close < e.range_low
    return close > e.range_high


def build_range_opportunity_frames(
    episodes: Sequence[RangeRotationEpisode],
    snapshots: Sequence[IntegrationSnapshot],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    variant: RangeIntegrationVariant,
) -> list[OpportunityFrame]:
    n = len(snapshots)
    if not (n == len(highs) == len(lows) == len(closes)):
        raise ValueError("range opportunity series length mismatch")

    by_bar: dict[int, list[RangeRotationEpisode]] = defaultdict(list)
    for e in episodes:
        if actionable(e, variant):
            by_bar[e.confirmation_bar].append(e)

    out: list[OpportunityFrame] = []
    active_episode: RangeRotationEpisode | None = None
    active_stage = OpportunityStage.NONE

    def clear() -> None:
        nonlocal active_episode, active_stage
        active_episode = None
        active_stage = OpportunityStage.NONE

    for i, snap in enumerate(snapshots):
        # First evolve / terminate the existing range opportunity.
        if active_episode is not None:
            e = active_episode
            box = box_from_snapshot(snap)
            close = float(closes[i])
            high = float(highs[i])
            low = float(lows[i])

            invalid = (
                box is None
                or not box_compatible_with_episode(box, e)
                or _invalidated(e, close)
                or _opposite_reached(e, high, low)
            )
            if invalid:
                clear()
            else:
                age = i - e.confirmation_bar
                if active_stage == OpportunityStage.STRONG and age >= 1:
                    # Acceptance is deliberately one-bar structural
                    # persistence/progress, not a second oscillator filter.
                    if (
                        age == 1
                        and _inside(e, close)
                        and _directional_progress(e, close)
                    ):
                        active_stage = OpportunityStage.ACCEPTED
                    else:
                        clear()

        # A new actionable edge event supersedes older range context.
        events = by_bar.get(i, [])
        if events:
            # If one candle creates opposing actionable rotations from both
            # edges, direction is structurally ambiguous at that close.
            dirs = {e.direction for e in events}
            if len(dirs) == 1:
                chosen = events[0]
                active_episode = chosen
                active_stage = OpportunityStage.STRONG
            else:
                clear()

        if active_episode is None:
            out.append(OpportunityFrame())
        else:
            out.append(
                OpportunityFrame(
                    kind=OpportunityKind.RANGE_ROTATION,
                    stage=active_stage,
                    direction=active_episode.direction,
                    source_bar=active_episode.confirmation_bar,
                    break_level=None,
                    source_strong=False,
                )
            )

    return out


def ambiguous_source_bars(
    episodes: Sequence[RangeRotationEpisode],
    *,
    variant: RangeIntegrationVariant,
) -> int:
    by_bar: dict[int, set[int]] = defaultdict(set)
    for e in episodes:
        if actionable(e, variant):
            by_bar[e.confirmation_bar].add(e.direction)
    return sum(len(directions) > 1 for directions in by_bar.values())

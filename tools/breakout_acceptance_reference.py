#!/usr/bin/env python3
"""Minimal breakout-acceptance contracts for Suite 0.2 research.

These contracts are research-only and never backdate later knowledge.

Candidate bar semantics use only information available at the structural-break
close. Follow-through contracts may accept one or two confirmed bars later,
but never relabel the original breakout bar as accepted.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from tools.execution_state_reference import Momentum, Participation
from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_candidate_features import CandidateFeatures
from tools.opportunity_episode_reference import OpportunityEpisode, OpportunityType


DECISIVE_BREAK_ATR = 0.50


class BreakoutAcceptance(str, Enum):
    PENETRATION = "PENETRATION"
    PENETRATION_PSE = "PENETRATION_PSE"
    PENETRATION_MTE = "PENETRATION_MTE"
    PENETRATION_PSE_MTE = "PENETRATION_PSE_MTE"
    HOLD_1 = "HOLD_1"
    HOLD_2 = "HOLD_2"
    PSE_OR_HOLD_1 = "PSE_OR_HOLD_1"
    PSE_MTE_OR_HOLD_1 = "PSE_MTE_OR_HOLD_1"
    PSE_OR_HOLD_2 = "PSE_OR_HOLD_2"
    PSE_MTE_OR_HOLD_2 = "PSE_MTE_OR_HOLD_2"
    PSE_HOLD_1_ELSE_HOLD_2 = "PSE_HOLD_1_ELSE_HOLD_2"
    PSE_MTE_HOLD_1_ELSE_HOLD_2 = "PSE_MTE_HOLD_1_ELSE_HOLD_2"


@dataclass(frozen=True)
class AcceptanceDecision:
    rule: BreakoutAcceptance
    accepted: bool
    accepted_bar: int | None
    delay_bars: int | None


def _momentum_aligned(direction: int, state_name: str) -> bool:
    state = Momentum[state_name]
    if direction == 1:
        return state in {Momentum.TURN_UP, Momentum.UP_ACCEL}
    if direction == -1:
        return state in {Momentum.TURN_DOWN, Momentum.DOWN_ACCEL}
    return False


def _penetration(features: CandidateFeatures) -> bool:
    return bool(
        features.break_penetration_atr is not None
        and features.break_penetration_atr >= DECISIVE_BREAK_ATR
    )


def _pse_confirm(features: CandidateFeatures) -> bool:
    return Participation[features.participation_state] == Participation.CONFIRM


def immediate_accepts(
    rule: BreakoutAcceptance,
    features: CandidateFeatures,
) -> bool:
    if rule == BreakoutAcceptance.PENETRATION:
        return _penetration(features)
    if rule == BreakoutAcceptance.PENETRATION_PSE:
        return _penetration(features) and _pse_confirm(features)
    if rule == BreakoutAcceptance.PENETRATION_MTE:
        return _penetration(features) and _momentum_aligned(
            features.direction, features.momentum_state
        )
    if rule == BreakoutAcceptance.PENETRATION_PSE_MTE:
        return (
            _penetration(features)
            and _pse_confirm(features)
            and _momentum_aligned(features.direction, features.momentum_state)
        )
    return False


def _holds_level(
    direction: int,
    close: float,
    break_level: float | None,
) -> bool:
    if break_level is None:
        return False
    if direction == 1:
        return close > break_level
    if direction == -1:
        return close < break_level
    return False


def follow_through_bar(
    episode: OpportunityEpisode,
    snapshots: Sequence[IntegrationSnapshot],
    closes: Sequence[float],
    bars: int,
) -> int | None:
    """Return the first bar where 1/2 confirmed closes have held the break."""
    if episode.opportunity_type != OpportunityType.BREAKOUT_CANDIDATE:
        return None
    if bars not in (1, 2):
        raise ValueError("bars must be 1 or 2")
    if len(snapshots) != len(closes):
        raise ValueError("snapshots/closes length mismatch")

    start = episode.confirmation_bar
    if start + bars >= len(snapshots):
        return None

    level = snapshots[start].structural_break_level
    if level is None:
        return None

    for offset in range(1, bars + 1):
        i = start + offset
        snap = snapshots[i]

        # A known fakeout/invalidation before acceptance kills the candidate.
        if snap.fakeout_event or snap.thesis_invalidated:
            return None

        if not _holds_level(episode.direction, float(closes[i]), level):
            return None

    return start + bars


def decide(
    rule: BreakoutAcceptance,
    episode: OpportunityEpisode,
    features: CandidateFeatures,
    snapshots: Sequence[IntegrationSnapshot],
    closes: Sequence[float],
) -> AcceptanceDecision:
    if episode.opportunity_type != OpportunityType.BREAKOUT_CANDIDATE:
        return AcceptanceDecision(rule, False, None, None)

    start = episode.confirmation_bar

    if immediate_accepts(rule, features):
        return AcceptanceDecision(rule, True, start, 0)

    follow_bars = None
    if rule == BreakoutAcceptance.HOLD_1:
        follow_bars = 1
    elif rule == BreakoutAcceptance.HOLD_2:
        follow_bars = 2
    elif rule in {
        BreakoutAcceptance.PSE_OR_HOLD_1,
        BreakoutAcceptance.PSE_MTE_OR_HOLD_1,
        BreakoutAcceptance.PSE_OR_HOLD_2,
        BreakoutAcceptance.PSE_MTE_OR_HOLD_2,
    }:
        pse_only = rule in {
            BreakoutAcceptance.PSE_OR_HOLD_1,
            BreakoutAcceptance.PSE_OR_HOLD_2,
        }
        immediate_rule = (
            BreakoutAcceptance.PENETRATION_PSE
            if pse_only
            else BreakoutAcceptance.PENETRATION_PSE_MTE
        )
        if immediate_accepts(immediate_rule, features):
            return AcceptanceDecision(rule, True, start, 0)
        follow_bars = (
            1
            if rule in {
                BreakoutAcceptance.PSE_OR_HOLD_1,
                BreakoutAcceptance.PSE_MTE_OR_HOLD_1,
            }
            else 2
        )

    if rule in {
        BreakoutAcceptance.PSE_HOLD_1_ELSE_HOLD_2,
        BreakoutAcceptance.PSE_MTE_HOLD_1_ELSE_HOLD_2,
    }:
        strong_rule = (
            BreakoutAcceptance.PENETRATION_PSE
            if rule == BreakoutAcceptance.PSE_HOLD_1_ELSE_HOLD_2
            else BreakoutAcceptance.PENETRATION_PSE_MTE
        )
        hold1 = follow_through_bar(episode, snapshots, closes, 1)
        if immediate_accepts(strong_rule, features) and hold1 is not None:
            return AcceptanceDecision(rule, True, hold1, 1)

        hold2 = follow_through_bar(episode, snapshots, closes, 2)
        if hold2 is not None:
            return AcceptanceDecision(rule, True, hold2, 2)

        return AcceptanceDecision(rule, False, None, None)

    if follow_bars is not None:
        bar = follow_through_bar(
            episode,
            snapshots,
            closes,
            follow_bars,
        )
        if bar is not None:
            return AcceptanceDecision(rule, True, bar, bar - start)

    return AcceptanceDecision(rule, False, None, None)

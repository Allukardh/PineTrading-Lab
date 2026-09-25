#!/usr/bin/env python3
"""Suite 0.2 research-only thesis-management V0 semantics.

The model describes market-thesis quality after an operator-facing confirmation.
It never infers an account position and does not create entry signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tools.execution_state_reference import (
    Evidence,
    Location,
    Momentum,
    Participation,
    RsiState,
    Strength,
    classify_strength,
)


TARGET_NEAR_ATR = 0.30
INVALID_WARN_ATR = 0.20


class ManagementState(str, Enum):
    CONTINUATION = "CONTINUATION"
    PROTECT = "PROTECT"
    REALIZATION_RISK = "REALIZATION_RISK"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class ManagementBar:
    state: ManagementState
    strength: Strength
    target_hit: bool
    invalidated: bool
    target_near: bool
    invalidation_near: bool
    structural_warning: bool
    target_room_atr: float | None
    invalidation_buffer_atr: float | None


def _valid_direction(direction: int) -> bool:
    return direction in (-1, 1)


def target_hit(direction: int, high: float, low: float, target: float | None) -> bool:
    if target is None or not _valid_direction(direction):
        return False
    return high >= target if direction == 1 else low <= target


def invalidation_broken(
    direction: int,
    close: float,
    invalidation: float | None,
    *,
    bar_confirmed: bool = True,
) -> bool:
    if (
        invalidation is None
        or not _valid_direction(direction)
        or not bar_confirmed
    ):
        return False
    return close < invalidation if direction == 1 else close > invalidation


def target_room_atr(
    direction: int,
    close: float,
    target: float | None,
    atr: float | None,
) -> float | None:
    if (
        target is None
        or atr is None
        or atr <= 0
        or not _valid_direction(direction)
    ):
        return None
    return direction * (target - close) / atr


def invalidation_buffer_atr(
    direction: int,
    close: float,
    invalidation: float | None,
    atr: float | None,
) -> float | None:
    if (
        invalidation is None
        or atr is None
        or atr <= 0
        or not _valid_direction(direction)
    ):
        return None
    return direction * (close - invalidation) / atr


def classify_management_bar(
    *,
    direction: int,
    high: float,
    low: float,
    close: float,
    atr: float | None,
    target: float | None,
    invalidation: float | None,
    momentum: Momentum,
    rsi: RsiState,
    participation: Participation,
    structural_warning: bool = False,
    bar_confirmed: bool = True,
) -> ManagementBar:
    if not _valid_direction(direction):
        raise ValueError("direction must be -1/+1")

    hit = target_hit(direction, high, low, target)
    invalid = invalidation_broken(
        direction,
        close,
        invalidation,
        bar_confirmed=bar_confirmed,
    )

    room = target_room_atr(direction, close, target, atr)
    buffer = invalidation_buffer_atr(direction, close, invalidation, atr)

    near_target = bool(
        room is not None
        and room >= 0
        and room <= TARGET_NEAR_ATR
        and not hit
    )
    near_invalidation = bool(
        buffer is not None
        and buffer >= 0
        and buffer <= INVALID_WARN_ATR
        and not invalid
    )

    evidence = Evidence(
        map_dir=direction,
        location=Location.DESTINATION_NEAR if near_target else Location.OUTSIDE,
        momentum=momentum,
        rsi=rsi,
        rsi_context_dir=0,
        participation=participation,
        bar_confirmed=bar_confirmed,
    )
    strength = classify_strength(direction, evidence)

    if hit and invalid:
        state = ManagementState.AMBIGUOUS
    elif hit:
        state = ManagementState.COMPLETED
    elif invalid:
        state = ManagementState.INVALIDATED
    elif near_target and strength == Strength.REACTION_RISK:
        state = ManagementState.REALIZATION_RISK
    elif (
        strength == Strength.EXHAUSTED
        or near_invalidation
        or structural_warning
    ):
        state = ManagementState.PROTECT
    else:
        state = ManagementState.CONTINUATION

    return ManagementBar(
        state=state,
        strength=strength,
        target_hit=hit,
        invalidated=invalid,
        target_near=near_target,
        invalidation_near=near_invalidation,
        structural_warning=structural_warning,
        target_room_atr=room,
        invalidation_buffer_atr=buffer,
    )

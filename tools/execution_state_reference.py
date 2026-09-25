#!/usr/bin/env python3
"""Reference semantic state machine for Execution 0.1.0.

This is deliberately independent of Pine and market-formula implementation.
It validates the *contract* between already-classified evidence families.

It is not a trading strategy, does not calculate PnL, and is not shipped to
TradingView. Production Pine must later reproduce these transition semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Location(IntEnum):
    OUTSIDE = 0
    APPROACHING = 1
    IN_CORRECTION = 2
    RETEST = 3
    RECLAIM = 4
    DESTINATION_NEAR = 5


class Momentum(IntEnum):
    NEUTRAL = 0
    TURN_UP = 1
    UP_ACCEL = 2
    UP_DECEL = 3
    TURN_DOWN = -1
    DOWN_ACCEL = -2
    DOWN_DECEL = -3


class RsiState(IntEnum):
    NEUTRAL = 0
    BULL = 1
    BEAR = -1
    RECOVERING_OVERSOLD = 2
    FADING_OVERBOUGHT = -2
    RECOVERING_OVERBOUGHT = 3
    FADING_OVERSOLD = -3
    EXTREME_OVERBOUGHT = 4
    EXTREME_OVERSOLD = -4


class Participation(IntEnum):
    NEUTRAL = 0
    CONFIRM = 1
    WEAK = 2
    CONTRARY = -1


class Readiness(IntEnum):
    WAIT = 0
    PREP = 1
    ARMED = 2
    CONFIRMED = 3  # one-bar transition state
    ALIGNED = 4


class Strength(IntEnum):
    NORMAL = 0
    FADING = 1
    EXHAUSTED = 2
    REACTION_RISK = 3


@dataclass(frozen=True)
class Evidence:
    map_dir: int
    location: Location
    momentum: Momentum
    rsi: RsiState
    rsi_context_dir: int = 0
    participation: Participation = Participation.NEUTRAL
    bar_confirmed: bool = True
    thesis_invalidated: bool = False
    structural_conflict: bool = False


@dataclass(frozen=True)
class State:
    readiness: Readiness = Readiness.WAIT
    direction: int = 0
    strength: Strength = Strength.NORMAL


@dataclass(frozen=True)
class Events:
    preparing_entered: bool = False
    armed_entered: bool = False
    confirm: bool = False
    canceled: bool = False
    reaction_risk_entered: bool = False


@dataclass(frozen=True)
class Result:
    state: State
    events: Events


RELEVANT_LOCATIONS = {
    Location.APPROACHING,
    Location.IN_CORRECTION,
    Location.RETEST,
    Location.RECLAIM,
}


def _valid_dir(direction: int) -> bool:
    return direction in (-1, 1)


def _momentum_aligned(direction: int, momentum: Momentum) -> bool:
    if direction == 1:
        return momentum in {Momentum.TURN_UP, Momentum.UP_ACCEL}
    if direction == -1:
        return momentum in {Momentum.TURN_DOWN, Momentum.DOWN_ACCEL}
    return False


def _momentum_acceptable_after_confirm(direction: int, momentum: Momentum) -> bool:
    if direction == 1:
        return momentum in {
            Momentum.TURN_UP,
            Momentum.UP_ACCEL,
            Momentum.UP_DECEL,
            Momentum.NEUTRAL,
        }
    if direction == -1:
        return momentum in {
            Momentum.TURN_DOWN,
            Momentum.DOWN_ACCEL,
            Momentum.DOWN_DECEL,
            Momentum.NEUTRAL,
        }
    return False


def _momentum_strongly_opposes(direction: int, momentum: Momentum) -> bool:
    if direction == 1:
        return momentum in {Momentum.TURN_DOWN, Momentum.DOWN_ACCEL}
    if direction == -1:
        return momentum in {Momentum.TURN_UP, Momentum.UP_ACCEL}
    return True


def _rsi_supportive(direction: int, rsi: RsiState, context_dir: int = 0) -> bool:
    if context_dir not in (-1, 0, 1):
        raise ValueError(f"rsi_context_dir must be -1/0/+1, got {context_dir}")

    if direction == 1:
        local = rsi in {
            RsiState.BULL,
            RsiState.RECOVERING_OVERSOLD,
            RsiState.RECOVERING_OVERBOUGHT,
        }
    elif direction == -1:
        local = rsi in {
            RsiState.BEAR,
            RsiState.FADING_OVERBOUGHT,
            RsiState.FADING_OVERSOLD,
        }
    else:
        return False

    return local and context_dir != -direction


def _rsi_opposes(direction: int, rsi: RsiState, context_dir: int = 0) -> bool:
    if context_dir not in (-1, 0, 1):
        raise ValueError(f"rsi_context_dir must be -1/0/+1, got {context_dir}")

    if direction == 1:
        local = rsi in {
            RsiState.BEAR,
            RsiState.FADING_OVERBOUGHT,
            RsiState.EXTREME_OVERBOUGHT,
        }
    elif direction == -1:
        local = rsi in {
            RsiState.BULL,
            RsiState.RECOVERING_OVERSOLD,
            RsiState.EXTREME_OVERSOLD,
        }
    else:
        return True

    return local or context_dir == -direction


def _momentum_deteriorates(direction: int, momentum: Momentum) -> bool:
    if direction == 1:
        return momentum in {
            Momentum.UP_DECEL,
            Momentum.TURN_DOWN,
            Momentum.DOWN_ACCEL,
            Momentum.DOWN_DECEL,
        }
    if direction == -1:
        return momentum in {
            Momentum.DOWN_DECEL,
            Momentum.TURN_UP,
            Momentum.UP_ACCEL,
            Momentum.UP_DECEL,
        }
    return False


def _rsi_deteriorates(direction: int, rsi: RsiState) -> bool:
    if direction == 1:
        return rsi in {RsiState.FADING_OVERBOUGHT, RsiState.EXTREME_OVERBOUGHT}
    if direction == -1:
        return rsi in {RsiState.RECOVERING_OVERSOLD, RsiState.EXTREME_OVERSOLD}
    return False


def classify_strength(direction: int, evidence: Evidence) -> Strength:
    """Classify continuation quality independently from readiness."""
    if not _valid_dir(direction):
        return Strength.NORMAL

    momentum_deteriorates = _momentum_deteriorates(direction, evidence.momentum)
    rsi_deteriorates = _rsi_deteriorates(direction, evidence.rsi)

    # Low participation is not the same as directional participation against
    # the thesis. For generic continuation strength only CONTRARY is an
    # independent PSE deterioration family.
    generic_deterioration = sum(
        [
            momentum_deteriorates,
            rsi_deteriorates,
            evidence.participation == Participation.CONTRARY,
        ]
    )

    # Near an explicit Market Map destination, however, participation failing
    # to expand is contextually meaningful exhaustion evidence. WEAK may
    # therefore contribute to REACTION_RISK only at DESTINATION_NEAR.
    destination_deterioration = sum(
        [
            momentum_deteriorates,
            rsi_deteriorates,
            evidence.participation in {Participation.WEAK, Participation.CONTRARY},
        ]
    )

    if evidence.location == Location.DESTINATION_NEAR and destination_deterioration >= 2:
        return Strength.REACTION_RISK
    if generic_deterioration >= 2:
        return Strength.EXHAUSTED
    if generic_deterioration == 1:
        return Strength.FADING
    return Strength.NORMAL


def step(previous: State, evidence: Evidence) -> Result:
    """Advance exactly one chart update/bar through the semantic contract."""
    if evidence.map_dir not in (-1, 0, 1):
        raise ValueError(f"map_dir must be -1/0/+1, got {evidence.map_dir}")
    if evidence.rsi_context_dir not in (-1, 0, 1):
        raise ValueError(
            f"rsi_context_dir must be -1/0/+1, got {evidence.rsi_context_dir}"
        )

    coherent_map = (
        _valid_dir(evidence.map_dir)
        and not evidence.thesis_invalidated
        and not evidence.structural_conflict
    )

    # Hard map invalidation always wins over local oscillators.
    if not coherent_map:
        canceled = previous.readiness != Readiness.WAIT
        return Result(
            State(Readiness.WAIT, 0, Strength.NORMAL),
            Events(canceled=canceled),
        )

    direction = evidence.map_dir
    strength = classify_strength(direction, evidence)
    reaction_edge = (
        strength == Strength.REACTION_RISK
        and previous.strength != Strength.REACTION_RISK
    )

    # A canonical map-direction change is a reset boundary. The engine must not
    # morph a LONG setup directly into a SHORT setup in one transition.
    if _valid_dir(previous.direction) and previous.direction != direction:
        return Result(
            State(Readiness.WAIT, 0, strength),
            Events(canceled=True, reaction_risk_entered=reaction_edge),
        )

    stage = previous.readiness

    if stage == Readiness.WAIT:
        if (
            evidence.location in RELEVANT_LOCATIONS
            and not _momentum_strongly_opposes(direction, evidence.momentum)
        ):
            return Result(
                State(Readiness.PREP, direction, strength),
                Events(
                    preparing_entered=True,
                    reaction_risk_entered=reaction_edge,
                ),
            )
        return Result(
            State(Readiness.WAIT, 0, strength),
            Events(reaction_risk_entered=reaction_edge),
        )

    if stage == Readiness.PREP:
        if (
            evidence.location not in RELEVANT_LOCATIONS
            or _momentum_strongly_opposes(direction, evidence.momentum)
            or evidence.participation == Participation.CONTRARY
        ):
            return Result(
                State(Readiness.WAIT, 0, strength),
                Events(canceled=True, reaction_risk_entered=reaction_edge),
            )

        if (
            _momentum_aligned(direction, evidence.momentum)
            and _rsi_supportive(
                direction,
                evidence.rsi,
                evidence.rsi_context_dir,
            )
        ):
            return Result(
                State(Readiness.ARMED, direction, strength),
                Events(
                    armed_entered=True,
                    reaction_risk_entered=reaction_edge,
                ),
            )

        return Result(
            State(Readiness.PREP, direction, strength),
            Events(reaction_risk_entered=reaction_edge),
        )

    if stage == Readiness.ARMED:
        if (
            evidence.location not in RELEVANT_LOCATIONS
            or _momentum_strongly_opposes(direction, evidence.momentum)
            or _rsi_opposes(
                direction,
                evidence.rsi,
                evidence.rsi_context_dir,
            )
            or evidence.participation == Participation.CONTRARY
        ):
            return Result(
                State(Readiness.WAIT, 0, strength),
                Events(canceled=True, reaction_risk_entered=reaction_edge),
            )

        if (
            evidence.bar_confirmed
            and _momentum_aligned(direction, evidence.momentum)
            and _rsi_supportive(
                direction,
                evidence.rsi,
                evidence.rsi_context_dir,
            )
            and evidence.participation == Participation.CONFIRM
        ):
            return Result(
                State(Readiness.CONFIRMED, direction, strength),
                Events(confirm=True, reaction_risk_entered=reaction_edge),
            )

        return Result(
            State(Readiness.ARMED, direction, strength),
            Events(reaction_risk_entered=reaction_edge),
        )

    if stage == Readiness.CONFIRMED:
        # CONFIRMED is intentionally one bar. If the map is still coherent,
        # persistence is expressed as ALIGNED on the next step.
        return Result(
            State(Readiness.ALIGNED, direction, strength),
            Events(reaction_risk_entered=reaction_edge),
        )

    if stage == Readiness.ALIGNED:
        # Do not cancel a confirmed direction because one oscillator wiggles.
        # Require two independent opposing families.
        confirmed_opposition = (
            _momentum_strongly_opposes(direction, evidence.momentum)
            and _rsi_opposes(
                direction,
                evidence.rsi,
                evidence.rsi_context_dir,
            )
        )
        if confirmed_opposition:
            return Result(
                State(Readiness.WAIT, 0, strength),
                Events(canceled=True, reaction_risk_entered=reaction_edge),
            )

        # Momentum can decelerate/neutralize while readiness remains aligned;
        # that deterioration is communicated through Strength.
        _ = _momentum_acceptable_after_confirm(direction, evidence.momentum)
        return Result(
            State(Readiness.ALIGNED, direction, strength),
            Events(reaction_risk_entered=reaction_edge),
        )

    raise AssertionError(f"Unhandled readiness stage: {stage}")

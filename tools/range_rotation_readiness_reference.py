#!/usr/bin/env python3
"""RANGE_ROTATION-specific research readiness.

This module composes the already-accepted MTE/RSE/PSE states for the accepted
structural RANGE_ROTATION lifecycle. It does not change indicator semantics.

Pre-registered variants:
- EARLY_ANY1: >=1 source ignition family -> ARMED
- SELECTIVE_ANY2: 1 family -> PREP, >=2 -> ARMED

For both:
- dual MTE + local-RSI opposition blocks source readiness
- next-bar structural ACCEPTED confirms only an already-ARMED setup
- HTF RSI is context, not a readiness veto
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from tools.execution_candidate_reference import ExecutionResearchBar
from tools.execution_state_reference import (
    Evidence,
    Events,
    Location,
    Participation,
    Readiness,
    Result,
    State,
    Strength,
    _momentum_aligned,
    _momentum_strongly_opposes,
    classify_strength,
)
from tools.momentum_turn_reference import Bar as MomentumBar, calculate as calculate_momentum
from tools.opportunity_execution_counterfactual import OpportunityFrame, OpportunityKind, OpportunityStage
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi, local_opposes, local_supports


class RangeReadinessVariant(str, Enum):
    EARLY_ANY1 = "EARLY_ANY1"
    SELECTIVE_ANY2 = "SELECTIVE_ANY2"


@dataclass(frozen=True)
class RangeReadinessSample:
    state_before: State
    result: Result
    frame: OpportunityFrame
    source_reset: bool
    ignition_family_count: int
    momentum_state_name: str
    rsi_state_name: str
    participation_state_name: str
    htf_context_dir: int
    momentum_core: float | None
    rsi_value: float | None
    relative_volume: float | None


def _valid_range_frame(frame: OpportunityFrame) -> bool:
    return (
        frame.kind == OpportunityKind.RANGE_ROTATION
        and frame.direction in (-1, 1)
        and frame.stage in {OpportunityStage.STRONG, OpportunityStage.ACCEPTED}
        and frame.source_bar is not None
    )


def _strength(frame, momentum, rsi, context_dir, participation):
    if not _valid_range_frame(frame):
        return Strength.NORMAL
    return classify_strength(
        frame.direction,
        Evidence(
            map_dir=frame.direction,
            location=Location.OUTSIDE,
            momentum=momentum,
            rsi=rsi,
            rsi_context_dir=context_dir,
            participation=participation,
            bar_confirmed=True,
        ),
    )


def ignition_count(direction, momentum, rsi, participation) -> int:
    return sum([
        _momentum_aligned(direction, momentum),
        local_supports(direction, rsi),
        participation == Participation.CONFIRM,
    ])


def dual_opposition(direction, momentum, rsi) -> bool:
    return (
        _momentum_strongly_opposes(direction, momentum)
        and local_opposes(direction, rsi)
    )


def step_range_readiness(
    previous: State,
    frame: OpportunityFrame,
    *,
    momentum,
    rsi,
    rsi_context_dir: int,
    participation: Participation,
    variant: RangeReadinessVariant,
    bar_confirmed: bool = True,
    source_reset: bool = False,
) -> Result:
    canceled_old = source_reset and previous.readiness != Readiness.WAIT
    if source_reset:
        previous = State()

    if not _valid_range_frame(frame):
        return Result(
            State(Readiness.WAIT, 0, Strength.NORMAL),
            Events(canceled=canceled_old or previous.readiness != Readiness.WAIT),
        )

    direction = frame.direction
    strength = _strength(frame, momentum, rsi, rsi_context_dir, participation)

    if previous.direction in (-1, 1) and previous.direction != direction:
        canceled_old = True
        previous = State()

    count = ignition_count(direction, momentum, rsi, participation)
    hard_opposition = dual_opposition(direction, momentum, rsi)

    if frame.stage == OpportunityStage.STRONG:
        if hard_opposition:
            return Result(
                State(Readiness.WAIT, 0, strength),
                Events(canceled=canceled_old),
            )

        if variant == RangeReadinessVariant.EARLY_ANY1:
            if count >= 1:
                return Result(
                    State(Readiness.ARMED, direction, strength),
                    Events(armed_entered=True, canceled=canceled_old),
                )
            return Result(
                State(Readiness.WAIT, 0, strength),
                Events(canceled=canceled_old),
            )

        if count >= 2:
            return Result(
                State(Readiness.ARMED, direction, strength),
                Events(armed_entered=True, canceled=canceled_old),
            )
        if count == 1:
            return Result(
                State(Readiness.PREP, direction, strength),
                Events(preparing_entered=True, canceled=canceled_old),
            )
        return Result(
            State(Readiness.WAIT, 0, strength),
            Events(canceled=canceled_old),
        )

    # ACCEPTED is structural final confirmation. It does not demand a fresh
    # oscillator coincidence after the range has already rotated toward mid.
    if previous.readiness == Readiness.ARMED and previous.direction == direction:
        if bar_confirmed:
            return Result(
                State(Readiness.CONFIRMED, direction, strength),
                Events(confirm=True, canceled=canceled_old),
            )
        return Result(
            State(Readiness.ARMED, direction, strength),
            Events(canceled=canceled_old),
        )

    if previous.readiness == Readiness.CONFIRMED and previous.direction == direction:
        return Result(
            State(Readiness.ALIGNED, direction, strength),
            Events(canceled=canceled_old),
        )

    if previous.readiness == Readiness.ALIGNED and previous.direction == direction:
        return Result(
            State(Readiness.ALIGNED, direction, strength),
            Events(canceled=canceled_old),
        )

    # PREP is deliberately not upgraded into a late entry merely because the
    # +1 bar accepted structurally; midpoint may already have been traversed.
    if previous.readiness == Readiness.PREP and previous.direction == direction:
        return Result(
            State(Readiness.PREP, direction, strength),
            Events(canceled=canceled_old),
        )

    return Result(
        State(Readiness.WAIT, 0, strength),
        Events(canceled=canceled_old),
    )


def calculate_range_readiness(
    bars: Sequence[ExecutionResearchBar],
    frames: Sequence[OpportunityFrame],
    *,
    variant: RangeReadinessVariant,
) -> list[RangeReadinessSample]:
    if len(bars) != len(frames):
        raise ValueError("bars/frames length mismatch")
    if not bars:
        return []

    momentum = calculate_momentum([
        MomentumBar(b.open, b.high, b.low, b.close) for b in bars
    ])
    rsi = calculate_rsi([b.close for b in bars])
    directions = [
        f.direction if _valid_range_frame(f) else 0
        for f in frames
    ]
    participation = calculate_participation(
        [ParticipationBar(b.high, b.low, b.close, b.volume) for b in bars],
        directions,
    )

    state = State()
    previous_source = None
    out=[]

    for bar, frame, mte, rse, pse in zip(bars, frames, momentum, rsi, participation):
        source = frame.source_bar if _valid_range_frame(frame) else None
        reset = source is not None and previous_source is not None and source != previous_source

        before=state
        result=step_range_readiness(
            before,
            frame,
            momentum=mte.state,
            rsi=rse.state,
            rsi_context_dir=bar.rsi_context_dir,
            participation=pse.state,
            variant=variant,
            bar_confirmed=bar.bar_confirmed,
            source_reset=reset,
        )
        state=result.state
        count=(
            ignition_count(frame.direction,mte.state,rse.state,pse.state)
            if _valid_range_frame(frame) else 0
        )
        out.append(RangeReadinessSample(
            state_before=before,
            result=result,
            frame=frame,
            source_reset=reset,
            ignition_family_count=count,
            momentum_state_name=mte.state.name,
            rsi_state_name=rse.state.name,
            participation_state_name=pse.state.name,
            htf_context_dir=bar.rsi_context_dir,
            momentum_core=mte.core,
            rsi_value=rse.value,
            relative_volume=pse.relative_volume,
        ))
        previous_source=source

    return out

#!/usr/bin/env python3
"""Research-only readiness state machine for Suite 0.2 opportunity paths.

This machine is deliberately parallel to frozen Execution 0.1.

It reuses the accepted semantic meanings of:
- MTE momentum states;
- RSE RSI states + confirmed HTF context;
- PSE participation states;
- chart-close confirmation.

It does NOT mutate or replace the frozen correction/retest/reclaim state path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tools.execution_candidate_reference import ExecutionResearchBar
from tools.execution_state_reference import (
    Evidence,
    Events,
    Location,
    Momentum,
    Participation,
    Readiness,
    Result,
    RsiState,
    State,
    Strength,
    _momentum_aligned,
    _momentum_strongly_opposes,
    _rsi_opposes,
    _rsi_supportive,
    classify_strength,
)
from tools.momentum_turn_reference import Bar as MomentumBar, calculate as calculate_momentum
from tools.opportunity_execution_counterfactual import (
    OpportunityFrame,
    OpportunityStage,
)
from tools.participation_reference import ParticipationBar, calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi


@dataclass(frozen=True)
class OpportunityReadinessSample:
    state_before: State
    result: Result
    frame: OpportunityFrame
    momentum_state_name: str
    rsi_state_name: str
    participation_state_name: str
    momentum_core: float | None
    rsi_value: float | None
    relative_volume: float | None


def _valid_frame(frame: OpportunityFrame) -> bool:
    return (
        frame.direction in (-1, 1)
        and frame.stage != OpportunityStage.NONE
    )


def _strength(
    frame: OpportunityFrame,
    momentum: Momentum,
    rsi: RsiState,
    context_dir: int,
    participation: Participation,
) -> Strength:
    if not _valid_frame(frame):
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


def step_opportunity(
    previous: State,
    frame: OpportunityFrame,
    *,
    momentum: Momentum,
    rsi: RsiState,
    rsi_context_dir: int,
    participation: Participation,
    bar_confirmed: bool = True,
) -> Result:
    if rsi_context_dir not in (-1, 0, 1):
        raise ValueError("rsi_context_dir must be -1/0/+1")

    if not _valid_frame(frame):
        return Result(
            State(Readiness.WAIT, 0, Strength.NORMAL),
            Events(canceled=previous.readiness != Readiness.WAIT),
        )

    direction = frame.direction
    strength = _strength(
        frame,
        momentum,
        rsi,
        rsi_context_dir,
        participation,
    )

    if previous.direction in (-1, 1) and previous.direction != direction:
        return Result(
            State(Readiness.WAIT, 0, strength),
            Events(canceled=True),
        )

    stage = previous.readiness

    if stage == Readiness.WAIT:
        if not _momentum_strongly_opposes(direction, momentum):
            return Result(
                State(Readiness.PREP, direction, strength),
                Events(preparing_entered=True),
            )
        return Result(State(Readiness.WAIT, 0, strength), Events())

    if stage == Readiness.PREP:
        if (
            _momentum_strongly_opposes(direction, momentum)
            or participation == Participation.CONTRARY
        ):
            return Result(
                State(Readiness.WAIT, 0, strength),
                Events(canceled=True),
            )

        # CANDIDATE is intentionally preparation-only.
        if frame.stage >= OpportunityStage.STRONG and (
            _momentum_aligned(direction, momentum)
            and _rsi_supportive(direction, rsi, rsi_context_dir)
        ):
            return Result(
                State(Readiness.ARMED, direction, strength),
                Events(armed_entered=True),
            )

        return Result(State(Readiness.PREP, direction, strength), Events())

    if stage == Readiness.ARMED:
        if (
            _momentum_strongly_opposes(direction, momentum)
            or _rsi_opposes(direction, rsi, rsi_context_dir)
            or participation == Participation.CONTRARY
        ):
            return Result(
                State(Readiness.WAIT, 0, strength),
                Events(canceled=True),
            )

        # Final confirmation requires structural opportunity acceptance.
        if (
            frame.stage >= OpportunityStage.ACCEPTED
            and bar_confirmed
            and _momentum_aligned(direction, momentum)
            and _rsi_supportive(direction, rsi, rsi_context_dir)
            and participation == Participation.CONFIRM
        ):
            return Result(
                State(Readiness.CONFIRMED, direction, strength),
                Events(confirm=True),
            )

        return Result(State(Readiness.ARMED, direction, strength), Events())

    if stage == Readiness.CONFIRMED:
        return Result(
            State(Readiness.ALIGNED, direction, strength),
            Events(),
        )

    if stage == Readiness.ALIGNED:
        if (
            _momentum_strongly_opposes(direction, momentum)
            and _rsi_opposes(direction, rsi, rsi_context_dir)
        ):
            return Result(
                State(Readiness.WAIT, 0, strength),
                Events(canceled=True),
            )
        return Result(
            State(Readiness.ALIGNED, direction, strength),
            Events(),
        )

    raise AssertionError(f"Unhandled readiness state: {stage}")


def calculate_opportunity_readiness(
    bars: Sequence[ExecutionResearchBar],
    frames: Sequence[OpportunityFrame],
    *,
    initial_state: State | None = None,
) -> list[OpportunityReadinessSample]:
    if len(bars) != len(frames):
        raise ValueError("bars/frames length mismatch")
    if not bars:
        return []

    momentum = calculate_momentum([
        MomentumBar(b.open, b.high, b.low, b.close) for b in bars
    ])
    rsi = calculate_rsi([b.close for b in bars])

    # During an opportunity frame PSE must be interpreted in the opportunity
    # direction. Outside a frame its value is irrelevant, so fall back to
    # canonical map direction for deterministic continuity.
    directions = [
        f.direction if _valid_frame(f) else b.map_dir
        for b, f in zip(bars, frames)
    ]
    participation = calculate_participation(
        [ParticipationBar(b.high, b.low, b.close, b.volume) for b in bars],
        directions,
    )

    state = initial_state or State()
    out: list[OpportunityReadinessSample] = []

    for bar, frame, mte, rse, pse in zip(
        bars, frames, momentum, rsi, participation
    ):
        previous = state
        result = step_opportunity(
            previous,
            frame,
            momentum=mte.state,
            rsi=rse.state,
            rsi_context_dir=bar.rsi_context_dir,
            participation=pse.state,
            bar_confirmed=bar.bar_confirmed,
        )
        state = result.state
        out.append(
            OpportunityReadinessSample(
                state_before=previous,
                result=result,
                frame=frame,
                momentum_state_name=mte.state.name,
                rsi_state_name=rse.state.name,
                participation_state_name=pse.state.name,
                momentum_core=mte.core,
                rsi_value=rse.value,
                relative_volume=pse.relative_volume,
            )
        )

    return out

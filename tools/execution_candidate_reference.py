#!/usr/bin/env python3
"""Integrated reference harness for Execution research candidates.

This composes:
- Market Map semantic inputs supplied by the caller
- MTE-A Momentum Turn
- RSE-A local RSI
- PSE-A reload-safe Participation
- the canonical Execution state machine

It exists to prove end-to-end semantic reachability before production Pine.
It is not a strategy/backtester and does not compute returns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tools.execution_state_reference import (
    Evidence,
    Location,
    Result,
    State,
    step,
)
from tools.momentum_turn_reference import Bar as MomentumBar
from tools.momentum_turn_reference import calculate as calculate_momentum
from tools.participation_reference import ParticipationBar
from tools.participation_reference import calculate as calculate_participation
from tools.rsi_state_reference import calculate as calculate_rsi


@dataclass(frozen=True)
class ExecutionResearchBar:
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    map_dir: int
    location: Location
    rsi_context_dir: int = 0
    thesis_invalidated: bool = False
    structural_conflict: bool = False
    bar_confirmed: bool = True


@dataclass(frozen=True)
class ExecutionResearchSample:
    state_before: State
    result: Result
    momentum_ready: bool
    momentum_core: float | None
    momentum_state_name: str
    rsi_ready: bool
    rsi_value: float | None
    rsi_state_name: str
    participation_ready: bool
    relative_volume: float | None
    participation_state_name: str


def calculate(
    bars: Sequence[ExecutionResearchBar],
    *,
    initial_state: State | None = None,
) -> list[ExecutionResearchSample]:
    if not bars:
        return []

    momentum_bars = [
        MomentumBar(
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
        )
        for bar in bars
    ]
    participation_bars = [
        ParticipationBar(
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        for bar in bars
    ]

    momentum = calculate_momentum(momentum_bars)
    rsi = calculate_rsi([bar.close for bar in bars])
    participation = calculate_participation(
        participation_bars,
        [bar.map_dir for bar in bars],
    )

    state = initial_state or State()
    out: list[ExecutionResearchSample] = []

    for bar, mte, rse, pse in zip(bars, momentum, rsi, participation):
        evidence = Evidence(
            map_dir=bar.map_dir,
            location=bar.location,
            momentum=mte.state,
            rsi=rse.state,
            rsi_context_dir=bar.rsi_context_dir,
            participation=pse.state,
            bar_confirmed=bar.bar_confirmed,
            thesis_invalidated=bar.thesis_invalidated,
            structural_conflict=bar.structural_conflict,
        )

        previous = state
        result = step(previous, evidence)
        state = result.state

        out.append(
            ExecutionResearchSample(
                state_before=previous,
                result=result,
                momentum_ready=mte.ready,
                momentum_core=mte.core,
                momentum_state_name=mte.state.name,
                rsi_ready=rse.ready,
                rsi_value=rse.value,
                rsi_state_name=rse.state.name,
                participation_ready=pse.ready,
                relative_volume=pse.relative_volume,
                participation_state_name=pse.state.name,
            )
        )

    return out

#!/usr/bin/env python3
"""Research-only Opportunity Engine -> Execution counterfactual.

The frozen 0.1 state machine and MTE/RSE/PSE semantics are reused unchanged.
This layer only supplies additional *opportunity relevance* when frozen 0.1
Market Map location is OUTSIDE the correction/retest vocabulary.

No production Pine/default/profile is changed by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Sequence

from tools.breakout_acceptance_reference import DECISIVE_BREAK_ATR
from tools.execution_candidate_reference import ExecutionResearchBar
from tools.execution_state_reference import (
    Evidence,
    Location,
    Participation,
    RELEVANT_LOCATIONS,
    Result,
    State,
    step,
)
from tools.market_map_offline_core import IntegrationSnapshot
from tools.momentum_turn_reference import Bar as MomentumBar, calculate as calculate_momentum
from tools.opportunity_episode_reference import (
    BreakContext,
    OpportunityEpisode,
    OpportunityType,
)
from tools.participation_reference import (
    ParticipationBar,
    ParticipationSample,
    calculate as calculate_participation,
)
from tools.rsi_state_reference import calculate as calculate_rsi


class OpportunityKind(IntEnum):
    NONE = 0
    BREAKOUT_EXPANSION = 1
    REACCELERATION = 2
    REGIME_REVERSAL = 3


class OpportunityStage(IntEnum):
    NONE = 0
    CANDIDATE = 1
    STRONG = 2
    ACCEPTED = 3


@dataclass(frozen=True)
class OpportunityFrame:
    kind: OpportunityKind = OpportunityKind.NONE
    stage: OpportunityStage = OpportunityStage.NONE
    direction: int = 0
    source_bar: int | None = None
    break_level: float | None = None


@dataclass(frozen=True)
class CounterfactualSample:
    state_before: State
    result: Result
    frame: OpportunityFrame
    baseline_location: Location
    effective_location: Location
    opportunity_overlay: bool

    momentum_ready: bool
    momentum_core: float | None
    momentum_state_name: str
    rsi_ready: bool
    rsi_value: float | None
    rsi_state_name: str
    participation_ready: bool
    relative_volume: float | None
    participation_state_name: str


def _holds(direction: int, close: float, level: float | None) -> bool:
    if level is None:
        return False
    if direction == 1:
        return close > level
    if direction == -1:
        return close < level
    return False


def _valid_frame(frame: OpportunityFrame) -> bool:
    return (
        frame.kind != OpportunityKind.NONE
        and frame.stage != OpportunityStage.NONE
        and frame.direction in (-1, 1)
    )


def _generic_breakout_episode(e: OpportunityEpisode) -> bool:
    return (
        e.opportunity_type == OpportunityType.BREAKOUT_CANDIDATE
        and e.break_context in {
            BreakContext.FRESH_EXPANSION.value,
            BreakContext.OTHER.value,
        }
    )


def build_opportunity_frames(
    episodes: Sequence[OpportunityEpisode],
    snapshots: Sequence[IntegrationSnapshot],
    closes: Sequence[float],
    baseline_locations: Sequence[Location],
    participation: Sequence[ParticipationSample],
) -> list[OpportunityFrame]:
    """Build a deterministic opportunity timeline from past/current evidence.

    Lifecycle for BREAKOUT_EXPANSION / REACCELERATION:
      break close -> CANDIDATE
      +1 held close + decisive/PSE candidate quality -> STRONG
      +2 held closes -> ACCEPTED

    ACCEPTED then persists while the same map thesis remains coherent and no
    new reaction/opposite structural event/destination condition takes over.

    Strict REGIME_REVERSAL begins at ACCEPTED because its own label is already
    delayed until the accepted Market Map confirms the new coherent regime.
    """
    n = len(snapshots)
    if not (
        len(closes) == n
        and len(baseline_locations) == n
        and len(participation) == n
    ):
        raise ValueError("opportunity timeline series length mismatch")

    by_bar: dict[int, list[OpportunityEpisode]] = {}
    for e in episodes:
        if (
            _generic_breakout_episode(e)
            or e.opportunity_type == OpportunityType.REACCELERATION
            or e.opportunity_type == OpportunityType.REGIME_REVERSAL
        ):
            by_bar.setdefault(e.confirmation_bar, []).append(e)

    frames: list[OpportunityFrame] = []
    active = OpportunityFrame()
    strong_at_source = False

    def clear() -> None:
        nonlocal active, strong_at_source
        active = OpportunityFrame()
        strong_at_source = False

    for i, snap in enumerate(snapshots):
        # Evolve / terminate the previous opportunity before applying a new
        # event on this bar.
        if _valid_frame(active):
            invalid = (
                snap.map_dir != active.direction
                or snap.thesis_invalidated
                or snap.structural_conflict
                or snap.fakeout_event
                or snap.destination_near
                or baseline_locations[i] in RELEVANT_LOCATIONS
            )
            if invalid:
                clear()
            elif active.kind in {
                OpportunityKind.BREAKOUT_EXPANSION,
                OpportunityKind.REACCELERATION,
            }:
                assert active.source_bar is not None
                age = i - active.source_bar

                if age == 1:
                    if not _holds(active.direction, float(closes[i]), active.break_level):
                        clear()
                    else:
                        active = OpportunityFrame(
                            kind=active.kind,
                            stage=(
                                OpportunityStage.STRONG
                                if strong_at_source
                                else OpportunityStage.CANDIDATE
                            ),
                            direction=active.direction,
                            source_bar=active.source_bar,
                            break_level=active.break_level,
                        )
                elif age == 2:
                    source = active.source_bar
                    held_1 = _holds(
                        active.direction,
                        float(closes[source + 1]),
                        active.break_level,
                    )
                    held_2 = _holds(
                        active.direction,
                        float(closes[i]),
                        active.break_level,
                    )
                    failed = any(
                        snapshots[j].fakeout_event or snapshots[j].thesis_invalidated
                        for j in range(source + 1, i + 1)
                    )
                    if held_1 and held_2 and not failed:
                        active = OpportunityFrame(
                            kind=active.kind,
                            stage=OpportunityStage.ACCEPTED,
                            direction=active.direction,
                            source_bar=source,
                            break_level=active.break_level,
                        )
                    else:
                        clear()
                elif age > 2 and active.stage != OpportunityStage.ACCEPTED:
                    clear()

        # New event on this bar supersedes an older opportunity context.
        events = by_bar.get(i, [])
        if events:
            # Most specific directionally coherent event wins.
            reversal = next(
                (e for e in events if e.opportunity_type == OpportunityType.REGIME_REVERSAL),
                None,
            )
            reacc = next(
                (e for e in events if e.opportunity_type == OpportunityType.REACCELERATION),
                None,
            )
            breakout = next((e for e in events if _generic_breakout_episode(e)), None)

            chosen = reversal or reacc or breakout
            if chosen is not None:
                if chosen.opportunity_type == OpportunityType.REGIME_REVERSAL:
                    active = OpportunityFrame(
                        OpportunityKind.REGIME_REVERSAL,
                        OpportunityStage.ACCEPTED,
                        chosen.direction,
                        chosen.confirmation_bar,
                        None,
                    )
                    strong_at_source = False
                else:
                    kind = (
                        OpportunityKind.REACCELERATION
                        if chosen.opportunity_type == OpportunityType.REACCELERATION
                        else OpportunityKind.BREAKOUT_EXPANSION
                    )
                    level = snapshots[i].structural_break_level
                    atr = snapshots[i].atr
                    penetration = (
                        None
                        if level is None or atr is None or atr <= 0
                        else chosen.direction * (float(closes[i]) - level) / atr
                    )
                    strong_at_source = bool(
                        penetration is not None
                        and penetration >= DECISIVE_BREAK_ATR
                        and participation[i].state == Participation.CONFIRM
                    )
                    active = OpportunityFrame(
                        kind,
                        OpportunityStage.CANDIDATE,
                        chosen.direction,
                        chosen.confirmation_bar,
                        level,
                    )

        frames.append(active)

    return frames


def project_for_state_machine(
    baseline_location: Location,
    frame: OpportunityFrame,
    participation: Participation,
) -> tuple[Location, Participation, bool]:
    """Project only relevance into 0.1 without faking early confirmation."""
    overlay = (
        baseline_location not in RELEVANT_LOCATIONS
        and baseline_location != Location.DESTINATION_NEAR
        and _valid_frame(frame)
    )
    if not overlay:
        return baseline_location, participation, False

    # APPROACHING is used only as an internal "relevant context" carrier for
    # the unchanged 0.1 state machine. The research sample retains the real
    # opportunity kind/stage separately; no UI/semantic claim calls this a
    # correction-zone approach.
    effective_location = Location.APPROACHING

    # CANDIDATE / STRONG may prepare and arm, but cannot satisfy the final PSE
    # confirmation gate. CONTRARY is preserved so invalid evidence can cancel.
    effective_participation = participation
    if (
        frame.stage != OpportunityStage.ACCEPTED
        and participation == Participation.CONFIRM
    ):
        effective_participation = Participation.NEUTRAL

    return effective_location, effective_participation, True


def calculate_counterfactual(
    bars: Sequence[ExecutionResearchBar],
    frames: Sequence[OpportunityFrame],
    *,
    initial_state: State | None = None,
) -> list[CounterfactualSample]:
    if len(bars) != len(frames):
        raise ValueError("bars/frames length mismatch")
    if not bars:
        return []

    momentum = calculate_momentum([
        MomentumBar(b.open, b.high, b.low, b.close) for b in bars
    ])
    rsi = calculate_rsi([b.close for b in bars])
    participation = calculate_participation(
        [
            ParticipationBar(b.high, b.low, b.close, b.volume)
            for b in bars
        ],
        [b.map_dir for b in bars],
    )

    state = initial_state or State()
    out: list[CounterfactualSample] = []

    for bar, frame, mte, rse, pse in zip(bars, frames, momentum, rsi, participation):
        effective_location, effective_pse, overlay = project_for_state_machine(
            bar.location,
            frame,
            pse.state,
        )
        previous = state
        result = step(
            previous,
            Evidence(
                map_dir=bar.map_dir,
                location=effective_location,
                momentum=mte.state,
                rsi=rse.state,
                rsi_context_dir=bar.rsi_context_dir,
                participation=effective_pse,
                bar_confirmed=bar.bar_confirmed,
                thesis_invalidated=bar.thesis_invalidated,
                structural_conflict=bar.structural_conflict,
            ),
        )
        state = result.state
        out.append(
            CounterfactualSample(
                state_before=previous,
                result=result,
                frame=frame,
                baseline_location=bar.location,
                effective_location=effective_location,
                opportunity_overlay=overlay,
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

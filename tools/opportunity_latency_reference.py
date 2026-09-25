#!/usr/bin/env python3
"""Measure frozen Execution 0.1 response to independent opportunity episodes."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Sequence

from tools.execution_state_reference import (
    Location,
    Momentum,
    Participation,
    Readiness,
    RsiState,
    RELEVANT_LOCATIONS,
)
from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_episode_reference import OpportunityEpisode


RESPONSE_WINDOW_BARS = 24


@dataclass(frozen=True)
class EpisodeResponse:
    episode_id: str
    opportunity_type: str
    direction: int
    onset_bar: int
    confirmation_bar: int
    state_at_confirmation: str
    state_direction_at_confirmation: int
    already_preparing_or_better: bool
    already_armed_or_better: bool
    already_aligned: bool
    prep_bar: int | None
    armed_bar: int | None
    confirm_bar: int | None
    prep_latency_bars: int | None
    armed_latency_bars: int | None
    confirm_latency_bars: int | None
    prep_displacement_atr: float | None
    armed_displacement_atr: float | None
    confirm_displacement_atr: float | None
    prep_room_to_destination_atr: float | None
    armed_room_to_destination_atr: float | None
    confirm_room_to_destination_atr: float | None
    deepest_state: str
    missed_reason: str | None
    window_end_bar: int
    terminated_by: str


def _momentum_strongly_opposes(direction: int, state: Momentum) -> bool:
    if direction == 1:
        return state in {Momentum.TURN_DOWN, Momentum.DOWN_ACCEL}
    if direction == -1:
        return state in {Momentum.TURN_UP, Momentum.UP_ACCEL}
    return True


def _momentum_aligned(direction: int, state: Momentum) -> bool:
    if direction == 1:
        return state in {Momentum.TURN_UP, Momentum.UP_ACCEL}
    if direction == -1:
        return state in {Momentum.TURN_DOWN, Momentum.DOWN_ACCEL}
    return False


def _rsi_local_supportive(direction: int, state: RsiState) -> bool:
    if direction == 1:
        return state in {
            RsiState.BULL,
            RsiState.RECOVERING_OVERSOLD,
            RsiState.RECOVERING_OVERBOUGHT,
        }
    if direction == -1:
        return state in {
            RsiState.BEAR,
            RsiState.FADING_OVERBOUGHT,
            RsiState.FADING_OVERSOLD,
        }
    return False


def _rsi_opposes(direction: int, state: RsiState, context_dir: int) -> bool:
    if direction == 1:
        return (
            state
            in {
                RsiState.BEAR,
                RsiState.FADING_OVERBOUGHT,
                RsiState.EXTREME_OVERBOUGHT,
            }
            or context_dir == -1
        )
    if direction == -1:
        return (
            state
            in {
                RsiState.BULL,
                RsiState.RECOVERING_OVERSOLD,
                RsiState.EXTREME_OVERSOLD,
            }
            or context_dir == 1
        )
    return True


def _metric_atr(
    direction: int,
    value: float,
    reference: float,
    atr: float | None,
) -> float | None:
    if atr is None or atr <= 0:
        return None
    return direction * (value - reference) / atr


def _room_atr(
    direction: int,
    close: float,
    destination: float | None,
    atr: float | None,
) -> float | None:
    if destination is None or atr is None or atr <= 0:
        return None
    return direction * (destination - close) / atr


def _barrier_reason(
    i: int,
    direction: int,
    stage: Readiness,
    snapshots: Sequence[IntegrationSnapshot],
    locations: Sequence[Location],
    samples: Sequence,
    context_dirs: Sequence[int],
) -> str:
    snap = snapshots[i]
    sample = samples[i]

    if (
        snap.map_dir != direction
        or snap.thesis_invalidated
        or snap.structural_conflict
    ):
        return "NO_COHERENT_MAP"

    if locations[i] == Location.DESTINATION_NEAR:
        return "DESTINATION_TOO_NEAR"

    if stage in {Readiness.WAIT, Readiness.PREP, Readiness.ARMED}:
        if locations[i] not in RELEVANT_LOCATIONS:
            return "LOCATION_NOT_RELEVANT"

    momentum = Momentum[sample.momentum_state_name]
    if _momentum_strongly_opposes(direction, momentum):
        return "MOMENTUM_OPPOSED"

    if stage in {Readiness.PREP, Readiness.ARMED}:
        rsi = RsiState[sample.rsi_state_name]
        if context_dirs[i] == -direction:
            return "HTF_BLOCKED"
        if not _rsi_local_supportive(direction, rsi):
            return "RSI_OPPOSED"

    participation = Participation[sample.participation_state_name]
    if stage == Readiness.PREP and participation == Participation.CONTRARY:
        return "PARTICIPATION_NOT_CONFIRMING"
    if stage == Readiness.ARMED and participation != Participation.CONFIRM:
        return "PARTICIPATION_NOT_CONFIRMING"

    if stage == Readiness.ARMED and not _momentum_aligned(direction, momentum):
        return "MOMENTUM_OPPOSED"

    return "OTHER"


def measure_episode(
    episode: OpportunityEpisode,
    snapshots: Sequence[IntegrationSnapshot],
    locations: Sequence[Location],
    samples: Sequence,
    context_dirs: Sequence[int],
    closes: Sequence[float],
    *,
    response_window_bars: int = RESPONSE_WINDOW_BARS,
) -> EpisodeResponse:
    n = len(snapshots)
    if not (
        n
        == len(locations)
        == len(samples)
        == len(context_dirs)
        == len(closes)
    ):
        raise ValueError("all response series must have identical length")

    start = episode.confirmation_bar
    if not 0 <= start < n:
        raise ValueError("episode confirmation_bar out of range")
    if response_window_bars < 0:
        raise ValueError("response_window_bars must be >= 0")

    state0 = samples[start].result.state
    same_dir0 = state0.direction == episode.direction
    already_prep = same_dir0 and state0.readiness >= Readiness.PREP
    already_armed = same_dir0 and state0.readiness >= Readiness.ARMED
    already_aligned = same_dir0 and state0.readiness == Readiness.ALIGNED

    prep_bar = start if already_prep else None
    armed_bar = start if already_armed else None
    # CONFIRMA is deliberately event-based. Existing ALINHADO means the engine
    # anticipated the episode; it must not be relabeled as a new confirmation.
    confirm_bar = None

    deepest = state0.readiness if same_dir0 else Readiness.WAIT
    barrier_counts: Counter[str] = Counter()

    end_limit = min(n - 1, start + response_window_bars)
    end = start
    terminated_by = "WINDOW_END"

    for i in range(start, end_limit + 1):
        snap = snapshots[i]

        if i > start:
            if snap.thesis_invalidated:
                end = i
                terminated_by = "INVALIDATED"
                break
            if snap.structural_conflict:
                end = i
                terminated_by = "STRUCTURAL_CONFLICT"
                break
            if snap.map_dir not in (episode.direction,):
                end = i
                terminated_by = "MAP_DIRECTION_LOST"
                break
            if (
                episode.thesis_key is not None
                and snap.new_thesis_event
                and snap.thesis_key is not None
                and snap.thesis_key != episode.thesis_key
            ):
                end = i
                terminated_by = "THESIS_REPLACED"
                break

        sample = samples[i]
        state = sample.result.state

        if state.direction == episode.direction:
            if state.readiness > deepest:
                deepest = state.readiness
            if prep_bar is None and state.readiness >= Readiness.PREP:
                prep_bar = i
            if armed_bar is None and state.readiness >= Readiness.ARMED:
                armed_bar = i

        if sample.result.events.confirm and state.direction == episode.direction:
            confirm_bar = i
            if state.readiness > deepest:
                deepest = state.readiness

        stage_for_barrier = (
            Readiness.ARMED
            if armed_bar is not None and confirm_bar is None
            else Readiness.PREP
            if prep_bar is not None and armed_bar is None
            else Readiness.WAIT
        )
        if confirm_bar is None:
            barrier_counts[
                _barrier_reason(
                    i,
                    episode.direction,
                    stage_for_barrier,
                    snapshots,
                    locations,
                    samples,
                    context_dirs,
                )
            ] += 1

        end = i
        if confirm_bar is not None:
            terminated_by = "CONFIRMED"
            break

    if confirm_bar is not None:
        missed_reason = None
    elif terminated_by == "THESIS_REPLACED":
        missed_reason = "THESIS_REPLACED"
    elif barrier_counts:
        # Deterministic tie-break: count first, then stable taxonomy order.
        order = [
            "NO_COHERENT_MAP",
            "LOCATION_NOT_RELEVANT",
            "MOMENTUM_OPPOSED",
            "RSI_OPPOSED",
            "HTF_BLOCKED",
            "PARTICIPATION_NOT_CONFIRMING",
            "DESTINATION_TOO_NEAR",
            "OTHER",
        ]
        missed_reason = max(
            order,
            key=lambda reason: (barrier_counts[reason], -order.index(reason)),
        )
    else:
        missed_reason = "OTHER"

    def latency(bar: int | None) -> int | None:
        return None if bar is None else bar - start

    def displacement(bar: int | None) -> float | None:
        if bar is None:
            return None
        return _metric_atr(
            episode.direction,
            float(closes[bar]),
            episode.reference_price,
            episode.atr,
        )

    def room(bar: int | None) -> float | None:
        if bar is None:
            return None
        return _room_atr(
            episode.direction,
            float(closes[bar]),
            episode.destination,
            snapshots[bar].atr,
        )

    return EpisodeResponse(
        episode_id=episode.episode_id,
        opportunity_type=episode.opportunity_type.value,
        direction=episode.direction,
        onset_bar=episode.onset_bar,
        confirmation_bar=start,
        state_at_confirmation=state0.readiness.name,
        state_direction_at_confirmation=state0.direction,
        already_preparing_or_better=already_prep,
        already_armed_or_better=already_armed,
        already_aligned=already_aligned,
        prep_bar=prep_bar,
        armed_bar=armed_bar,
        confirm_bar=confirm_bar,
        prep_latency_bars=latency(prep_bar),
        armed_latency_bars=latency(armed_bar),
        confirm_latency_bars=latency(confirm_bar),
        prep_displacement_atr=displacement(prep_bar),
        armed_displacement_atr=displacement(armed_bar),
        confirm_displacement_atr=displacement(confirm_bar),
        prep_room_to_destination_atr=room(prep_bar),
        armed_room_to_destination_atr=room(armed_bar),
        confirm_room_to_destination_atr=room(confirm_bar),
        deepest_state=deepest.name,
        missed_reason=missed_reason,
        window_end_bar=end,
        terminated_by=terminated_by,
    )


def measure_all(
    episodes: Sequence[OpportunityEpisode],
    snapshots: Sequence[IntegrationSnapshot],
    locations: Sequence[Location],
    samples: Sequence,
    context_dirs: Sequence[int],
    closes: Sequence[float],
    *,
    response_window_bars: int = RESPONSE_WINDOW_BARS,
) -> list[EpisodeResponse]:
    return [
        measure_episode(
            e,
            snapshots,
            locations,
            samples,
            context_dirs,
            closes,
            response_window_bars=response_window_bars,
        )
        for e in episodes
    ]


def response_as_dict(response: EpisodeResponse) -> dict:
    return asdict(response)

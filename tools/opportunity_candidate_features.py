#!/usr/bin/env python3
"""Contemporaneous feature extraction for Suite 0.2 opportunity candidates.

All features in this module are available on the candidate confirmation bar.
Retrospective outcomes are attached elsewhere and must never leak back into
feature calculation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from tools.market_map_offline_core import IntegrationSnapshot
from tools.momentum_turn_reference import MomentumSample
from tools.opportunity_episode_reference import OpportunityEpisode
from tools.participation_reference import ParticipationSample
from tools.rsi_state_reference import RsiSample


@dataclass(frozen=True)
class CandidateFeatures:
    episode_id: str
    opportunity_type: str
    direction: int
    bar_index: int
    prior_regime_bars: int | None

    break_penetration_atr: float | None
    candle_body_direction_atr: float | None
    candle_range_atr: float | None
    close_location_directional: float | None

    mte_core_directional: float | None
    mte_acceleration_directional: float | None
    rsi_center_directional: float | None
    rsi_step_directional: float | None
    htf_context_alignment: int

    relative_volume: float | None
    directional_pressure: float | None
    strong_volume_expansion: bool | None

    destination_room_atr: float | None
    invalidation_distance_atr: float | None


def _norm(value: float, atr: float | None) -> float | None:
    if atr is None or atr <= 0:
        return None
    return value / atr


def extract_features(
    episode: OpportunityEpisode,
    snapshots: Sequence[IntegrationSnapshot],
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    momentum: Sequence[MomentumSample],
    rsi: Sequence[RsiSample],
    participation_by_candidate_dir: Sequence[ParticipationSample],
    context_dirs: Sequence[int],
) -> CandidateFeatures:
    i = episode.confirmation_bar
    n = len(snapshots)
    series = (
        opens,
        highs,
        lows,
        closes,
        momentum,
        rsi,
        participation_by_candidate_dir,
        context_dirs,
    )
    if any(len(xs) != n for xs in series):
        raise ValueError("candidate feature series length mismatch")
    if not 0 <= i < n:
        raise ValueError("episode confirmation bar out of range")

    snap = snapshots[i]
    atr = snap.atr
    direction = episode.direction

    break_penetration = None
    if snap.structural_break_level is not None:
        break_penetration = _norm(
            direction * (float(closes[i]) - snap.structural_break_level),
            atr,
        )

    body = _norm(direction * (float(closes[i]) - float(opens[i])), atr)
    bar_range = _norm(float(highs[i]) - float(lows[i]), atr)

    span = float(highs[i]) - float(lows[i])
    close_location = (
        0.0
        if span <= 0
        else direction
        * (2.0 * float(closes[i]) - float(highs[i]) - float(lows[i]))
        / span
    )

    m = momentum[i]
    rr = rsi[i]
    p = participation_by_candidate_dir[i]

    destination_room = None
    if snap.destination is not None:
        destination_room = _norm(
            direction * (snap.destination - float(closes[i])),
            atr,
        )

    invalidation_distance = None
    if snap.invalidation is not None:
        invalidation_distance = _norm(
            direction * (float(closes[i]) - snap.invalidation),
            atr,
        )

    return CandidateFeatures(
        episode_id=episode.episode_id,
        opportunity_type=episode.opportunity_type.value,
        direction=direction,
        bar_index=i,
        prior_regime_bars=episode.prior_regime_bars,
        break_penetration_atr=break_penetration,
        candle_body_direction_atr=body,
        candle_range_atr=bar_range,
        close_location_directional=close_location,
        mte_core_directional=(
            None if m.core is None else direction * m.core
        ),
        mte_acceleration_directional=(
            None if m.acceleration is None else direction * m.acceleration
        ),
        rsi_center_directional=(
            None if rr.value is None else direction * (rr.value - 50.0)
        ),
        rsi_step_directional=(
            None if rr.step is None else direction * rr.step
        ),
        htf_context_alignment=direction * int(context_dirs[i]),
        relative_volume=p.relative_volume,
        directional_pressure=p.directional_pressure,
        strong_volume_expansion=(
            p.strong_expansion if p.ready else None
        ),
        destination_room_atr=destination_room,
        invalidation_distance_atr=invalidation_distance,
    )


def as_dict(features: CandidateFeatures) -> dict:
    return asdict(features)

#!/usr/bin/env python3
"""Deterministic structural RANGE_ROTATION research contract.

A range is not inferred from low trend strength alone. It requires two
confirmed swing highs and two confirmed swing lows forming a stable box.

A rotation candidate is known only when price interacts with a box edge and
closes back into the range. Retrospective outcome is classified separately.

Research-only; no production Pine/default/profile changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_episode_reference import OpportunityEpisode, OpportunityType


RANGE_BOUNDARY_DRIFT_MAX = 0.20
RANGE_MIN_HEIGHT_ATR = 2.0
RANGE_EDGE_FRACTION = 0.20


class RangeTrigger(str, Enum):
    SWEEP_RECLAIM = "SWEEP_RECLAIM"
    EDGE_REJECTION = "EDGE_REJECTION"


class RegimeRelation(str, Enum):
    NEUTRAL = "NEUTRAL"
    WITH_REGIME = "WITH_REGIME"
    AGAINST_REGIME = "AGAINST_REGIME"


class RangeOutcome(str, Enum):
    OPPOSITE_REACHED = "OPPOSITE_REACHED"
    MID_REACHED = "MID_REACHED"
    FAILED_BEFORE_MID = "FAILED_BEFORE_MID"
    CENSORED = "CENSORED"


@dataclass(frozen=True)
class RangeBox:
    key: tuple[int, int, int, int]
    high: float
    low: float
    mid: float
    height: float
    height_atr: float
    boundary_drift_ratio: float
    edge_band: float


@dataclass(frozen=True)
class RangeRotationEpisode:
    episode_id: str
    direction: int
    confirmation_bar: int
    range_key: tuple[int, int, int, int]
    range_high: float
    range_low: float
    range_mid: float
    edge_band: float
    height_atr: float
    boundary_drift_ratio: float
    trigger: RangeTrigger
    regime_relation: RegimeRelation
    reference_price: float
    atr: float | None


@dataclass(frozen=True)
class RangeRotationOutcome:
    episode_id: str
    outcome: RangeOutcome
    outcome_bar: int | None
    midpoint_bar: int | None
    opposite_bar: int | None
    invalidation_bar: int | None


def box_from_snapshot(s: IntegrationSnapshot) -> RangeBox | None:
    vals = (
        s.prev_swing_high,
        s.last_swing_high,
        s.prev_swing_low,
        s.last_swing_low,
        s.prev_swing_high_bar,
        s.last_swing_high_bar,
        s.prev_swing_low_bar,
        s.last_swing_low_bar,
    )
    if any(v is None for v in vals):
        return None
    if s.atr is None or s.atr <= 0:
        return None

    ph = float(s.prev_swing_high)
    lh = float(s.last_swing_high)
    pl = float(s.prev_swing_low)
    ll = float(s.last_swing_low)
    phb = int(s.prev_swing_high_bar)
    lhb = int(s.last_swing_high_bar)
    plb = int(s.prev_swing_low_bar)
    llb = int(s.last_swing_low_bar)

    if not (phb < lhb and plb < llb):
        return None

    # Require two complete boundary cycles rather than two same-side pivots
    # clustered before the other side was ever revisited.
    if max(phb, plb) >= min(lhb, llb):
        return None

    # All highs must remain structurally above all lows.
    if min(ph, lh) <= max(pl, ll):
        return None

    high = (ph + lh) / 2.0
    low = (pl + ll) / 2.0
    height = high - low
    if height <= 0:
        return None

    height_atr = height / s.atr
    if height_atr < RANGE_MIN_HEIGHT_ATR:
        return None

    drift = max(abs(ph - lh), abs(pl - ll)) / height
    if drift > RANGE_BOUNDARY_DRIFT_MAX:
        return None

    edge = height * RANGE_EDGE_FRACTION
    return RangeBox(
        key=(phb, lhb, plb, llb),
        high=high,
        low=low,
        mid=(high + low) / 2.0,
        height=height,
        height_atr=height_atr,
        boundary_drift_ratio=drift,
        edge_band=edge,
    )


def _relation(direction: int, regime_dir: int) -> RegimeRelation:
    if regime_dir == 0:
        return RegimeRelation.NEUTRAL
    if regime_dir == direction:
        return RegimeRelation.WITH_REGIME
    return RegimeRelation.AGAINST_REGIME


def _close_location_directional(
    direction: int,
    high: float,
    low: float,
    close: float,
) -> float:
    span = high - low
    if span <= 0:
        return 0.0
    return direction * (2.0 * close - high - low) / span


def detect_range_rotations(
    snapshots: Sequence[IntegrationSnapshot],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> list[RangeRotationEpisode]:
    if not (
        len(snapshots) == len(highs) == len(lows) == len(closes)
    ):
        raise ValueError("range-rotation series length mismatch")

    episodes: list[RangeRotationEpisode] = []

    # Same-edge opportunities do not repeat until price has travelled back
    # through the range midpoint. This is a market-sequence reset, not a fixed
    # cooldown in bars.
    active_key: tuple[int, int, int, int] | None = None
    lower_ready = True
    upper_ready = True

    for i, snap in enumerate(snapshots):
        box = box_from_snapshot(snap)
        if box is None:
            active_key = None
            lower_ready = upper_ready = True
            continue

        if box.key != active_key:
            active_key = box.key
            lower_ready = upper_ready = True

        close = float(closes[i])
        high = float(highs[i])
        low = float(lows[i])

        # A confirmed close outside the box means rotation semantics no longer
        # describe the current bar. Wait for a new confirmed range structure.
        if close < box.low or close > box.high:
            continue

        if close >= box.mid:
            lower_ready = True
        if close <= box.mid:
            upper_ready = True

        lower_touch = low <= box.low + box.edge_band
        upper_touch = high >= box.high - box.edge_band

        long_reclaim = bool(
            snap.raw_lower_reclaim_level is not None
            and low <= box.low + box.edge_band
            and close > box.low
        )
        short_reclaim = bool(
            snap.raw_upper_reclaim_level is not None
            and high >= box.high - box.edge_band
            and close < box.high
        )

        long_rejection = bool(
            lower_touch
            and close >= box.low + box.edge_band
            and _close_location_directional(1, high, low, close) > 0
        )
        short_rejection = bool(
            upper_touch
            and close <= box.high - box.edge_band
            and _close_location_directional(-1, high, low, close) > 0
        )

        if lower_ready and (long_reclaim or long_rejection):
            trigger = (
                RangeTrigger.SWEEP_RECLAIM
                if long_reclaim
                else RangeTrigger.EDGE_REJECTION
            )
            episodes.append(
                RangeRotationEpisode(
                    episode_id=f"RANGE_ROTATION:+1:{i}:{box.key}",
                    direction=1,
                    confirmation_bar=i,
                    range_key=box.key,
                    range_high=box.high,
                    range_low=box.low,
                    range_mid=box.mid,
                    edge_band=box.edge_band,
                    height_atr=box.height_atr,
                    boundary_drift_ratio=box.boundary_drift_ratio,
                    trigger=trigger,
                    regime_relation=_relation(1, snap.regime_dir),
                    reference_price=close,
                    atr=snap.atr,
                )
            )
            lower_ready = False

        if upper_ready and (short_reclaim or short_rejection):
            trigger = (
                RangeTrigger.SWEEP_RECLAIM
                if short_reclaim
                else RangeTrigger.EDGE_REJECTION
            )
            episodes.append(
                RangeRotationEpisode(
                    episode_id=f"RANGE_ROTATION:-1:{i}:{box.key}",
                    direction=-1,
                    confirmation_bar=i,
                    range_key=box.key,
                    range_high=box.high,
                    range_low=box.low,
                    range_mid=box.mid,
                    edge_band=box.edge_band,
                    height_atr=box.height_atr,
                    boundary_drift_ratio=box.boundary_drift_ratio,
                    trigger=trigger,
                    regime_relation=_relation(-1, snap.regime_dir),
                    reference_price=close,
                    atr=snap.atr,
                )
            )
            upper_ready = False

    return episodes


def classify_range_rotation(
    episode: RangeRotationEpisode,
    snapshots: Sequence[IntegrationSnapshot],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> RangeRotationOutcome:
    start = episode.confirmation_bar
    midpoint_bar = None

    for i in range(start + 1, len(snapshots)):
        box = box_from_snapshot(snapshots[i])

        # Once a new structural box replaces the source box, the original
        # rotation thesis is censored unless it already produced a decisive
        # midpoint/opposite result.
        if box is None or box.key != episode.range_key:
            return RangeRotationOutcome(
                episode.episode_id,
                RangeOutcome.MID_REACHED if midpoint_bar is not None else RangeOutcome.CENSORED,
                i,
                midpoint_bar,
                None,
                None,
            )

        hi = float(highs[i])
        lo = float(lows[i])
        close = float(closes[i])

        if episode.direction == 1:
            if midpoint_bar is None and hi >= episode.range_mid:
                midpoint_bar = i
            opposite = hi >= episode.range_high - episode.edge_band
            invalid = close < episode.range_low
        else:
            if midpoint_bar is None and lo <= episode.range_mid:
                midpoint_bar = i
            opposite = lo <= episode.range_low + episode.edge_band
            invalid = close > episode.range_high

        # Opposite edge is intrabar evidence; invalidation is a confirmed
        # close. If both happen on one bar, the rotation reached its objective
        # before the close invalidated the old range thesis.
        if opposite:
            return RangeRotationOutcome(
                episode.episode_id,
                RangeOutcome.OPPOSITE_REACHED,
                i,
                midpoint_bar,
                i,
                i if invalid else None,
            )

        if invalid:
            return RangeRotationOutcome(
                episode.episode_id,
                RangeOutcome.MID_REACHED if midpoint_bar is not None else RangeOutcome.FAILED_BEFORE_MID,
                i,
                midpoint_bar,
                None,
                i,
            )

    return RangeRotationOutcome(
        episode.episode_id,
        RangeOutcome.MID_REACHED if midpoint_bar is not None else RangeOutcome.CENSORED,
        None,
        midpoint_bar,
        None,
        None,
    )


def as_opportunity_episode(e: RangeRotationEpisode) -> OpportunityEpisode:
    return OpportunityEpisode(
        episode_id=e.episode_id,
        opportunity_type=OpportunityType.RANGE_ROTATION,
        direction=e.direction,
        onset_bar=e.confirmation_bar,
        confirmation_bar=e.confirmation_bar,
        thesis_key=None,
        reference_price=e.reference_price,
        atr=e.atr,
        destination=(
            e.range_high - e.edge_band
            if e.direction == 1
            else e.range_low + e.edge_band
        ),
        invalidation=e.range_low if e.direction == 1 else e.range_high,
    )

#!/usr/bin/env python3
"""Deterministic opportunity-episode labels for Suite 0.2 research.

These labels are deliberately independent of Execution readiness/results.
They describe market-structure episodes that the frozen 0.1 Execution can be
measured against.

This first contract intentionally starts with the three strongest event
families already observable from accepted MM-0 semantics:
- REGIME_TRANSITION_CANDIDATE
- REGIME_REVERSAL
- BREAKOUT_CANDIDATE
- PULLBACK_RETEST

REACCELERATION and RANGE_ROTATION are deferred until these episode semantics
and the 0.1 latency harness are proven stable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from tools.market_map_offline_core import IntegrationSnapshot


REVERSAL_PRIOR_REGIME_MIN_BARS = 8


class OpportunityType(str, Enum):
    REGIME_TRANSITION_CANDIDATE = "REGIME_TRANSITION_CANDIDATE"
    REGIME_REVERSAL = "REGIME_REVERSAL"
    BREAKOUT_CANDIDATE = "BREAKOUT_CANDIDATE"
    PULLBACK_RETEST = "PULLBACK_RETEST"


@dataclass(frozen=True)
class OpportunityEpisode:
    episode_id: str
    opportunity_type: OpportunityType
    direction: int
    onset_bar: int
    confirmation_bar: int
    thesis_key: int | None
    reference_price: float
    atr: float | None
    destination: float | None
    invalidation: float | None
    prior_regime_bars: int | None = None


def _valid_direction(value: int) -> bool:
    return value in (-1, 1)


def _zone_touch(
    snap: IntegrationSnapshot,
    high: float,
    low: float,
) -> bool:
    return bool(
        snap.correction_active
        and snap.primary_top is not None
        and snap.primary_bottom is not None
        and high >= snap.primary_bottom
        and low <= snap.primary_top
    )


def detect_episodes(
    snapshots: Sequence[IntegrationSnapshot],
    highs: Sequence[float],
    lows: Sequence[float],
) -> list[OpportunityEpisode]:
    """Return deterministic market-opportunity episodes.

    Timing contract:
    - REGIME_TRANSITION_CANDIDATE is known at the first opposite structural
      break against a mature prior regime.
    - BREAKOUT_CANDIDATE is known at the structural-break close.
    - PULLBACK_RETEST is known on the first accepted reaction/touch bar for a
      thesis.
    - REGIME_REVERSAL is known only when the opposite confirmed regime appears.
      onset_bar may point to an earlier opposite structural break, but
      confirmation_bar is the earliest bar at which the reversal label is
      considered known. Consumers must never backdate an actionable result to
      onset_bar.
    """
    if not (len(snapshots) == len(highs) == len(lows)):
        raise ValueError("snapshots/highs/lows must have identical length")

    episodes: list[OpportunityEpisode] = []
    seen_reaction_theses: set[int] = set()

    # Regime bookkeeping deliberately tolerates a neutral/transition gap.
    current_regime_dir = 0
    current_regime_len = 0
    previous_regime_dir = 0
    previous_regime_len = 0
    previous_regime_end: int | None = None
    last_break_bar = {1: None, -1: None}
    pending_reversal: tuple[int, int] | None = None

    def add(
        kind: OpportunityType,
        direction: int,
        onset: int,
        confirmation: int,
        snap: IntegrationSnapshot,
        *,
        prior_regime_bars: int | None = None,
    ) -> None:
        episodes.append(
            OpportunityEpisode(
                episode_id=f"{kind.value}:{direction:+d}:{confirmation}",
                opportunity_type=kind,
                direction=direction,
                onset_bar=onset,
                confirmation_bar=confirmation,
                thesis_key=snap.thesis_key,
                reference_price=snap.close,
                atr=snap.atr,
                destination=snap.destination,
                invalidation=snap.invalidation,
                prior_regime_bars=prior_regime_bars,
            )
        )

    for i, snap in enumerate(snapshots):
        if snap.structural_break_dir in (-1, 1):
            last_break_bar[snap.structural_break_dir] = i

            # Early regime-transition candidate: opposite structural break
            # against a sufficiently mature confirmed regime. This is known at
            # the break close and is intentionally distinct from a later,
            # fully coherent REGIME_REVERSAL.
            mature_dir = 0
            if (
                _valid_direction(current_regime_dir)
                and current_regime_len >= REVERSAL_PRIOR_REGIME_MIN_BARS
            ):
                mature_dir = current_regime_dir
            elif (
                current_regime_dir == 0
                and _valid_direction(previous_regime_dir)
                and previous_regime_len >= REVERSAL_PRIOR_REGIME_MIN_BARS
            ):
                mature_dir = previous_regime_dir

            if mature_dir == -snap.structural_break_dir:
                add(
                    OpportunityType.REGIME_TRANSITION_CANDIDATE,
                    snap.structural_break_dir,
                    i,
                    i,
                    snap,
                    prior_regime_bars=(
                        current_regime_len
                        if current_regime_dir == mature_dir
                        else previous_regime_len
                    ),
                )

        # A structural break itself is a valid expansion episode only if MM-0
        # already regards the resulting direction as coherent on that bar.
        if (
            snap.structural_break_dir in (-1, 1)
            and snap.map_dir == snap.structural_break_dir
            and not snap.structural_conflict
            and not snap.thesis_invalidated
        ):
            add(
                OpportunityType.BREAKOUT_CANDIDATE,
                snap.structural_break_dir,
                i,
                i,
                snap,
            )

        # First correction-zone/retest/reclaim reaction per MM thesis.
        if (
            snap.thesis_key is not None
            and snap.thesis_key not in seen_reaction_theses
            and _valid_direction(snap.map_dir)
            and not snap.structural_conflict
            and not snap.thesis_invalidated
            and (
                snap.retest_event
                or snap.reclaim_event
                or (
                    not snap.new_thesis_event
                    and _zone_touch(snap, float(highs[i]), float(lows[i]))
                )
            )
        ):
            seen_reaction_theses.add(snap.thesis_key)
            add(
                OpportunityType.PULLBACK_RETEST,
                snap.map_dir,
                i,
                i,
                snap,
            )

        regime = snap.regime_dir

        # A pending reversal becomes a confirmed opportunity only when the
        # accepted Market Map itself is coherent in the new regime direction.
        if pending_reversal is not None:
            pending_dir, pending_onset = pending_reversal
            if (
                regime == pending_dir
                and snap.map_dir == pending_dir
                and not snap.structural_conflict
                and not snap.thesis_invalidated
            ):
                add(
                    OpportunityType.REGIME_REVERSAL,
                    pending_dir,
                    pending_onset,
                    i,
                    snap,
                )
                pending_reversal = None
            elif regime not in (0, pending_dir):
                pending_reversal = None

        if regime == current_regime_dir and _valid_direction(regime):
            current_regime_len += 1
            continue

        if regime == 0:
            if _valid_direction(current_regime_dir):
                previous_regime_dir = current_regime_dir
                previous_regime_len = current_regime_len
                previous_regime_end = i - 1
            current_regime_dir = 0
            current_regime_len = 0
            continue

        # Entering a new non-zero regime.
        if _valid_direction(current_regime_dir):
            previous_regime_dir = current_regime_dir
            previous_regime_len = current_regime_len
            previous_regime_end = i - 1

        if (
            previous_regime_dir == -regime
            and previous_regime_len >= REVERSAL_PRIOR_REGIME_MIN_BARS
        ):
            candidate_break = last_break_bar[regime]
            onset = (
                candidate_break
                if candidate_break is not None
                and (
                    previous_regime_end is None
                    or candidate_break > previous_regime_end
                )
                else i
            )
            pending_reversal = (regime, onset)

            if (
                snap.map_dir == regime
                and not snap.structural_conflict
                and not snap.thesis_invalidated
            ):
                add(
                    OpportunityType.REGIME_REVERSAL,
                    regime,
                    onset,
                    i,
                    snap,
                )
                pending_reversal = None

        current_regime_dir = regime
        current_regime_len = 1

    episodes.sort(
        key=lambda e: (
            e.confirmation_bar,
            e.opportunity_type.value,
            e.direction,
        )
    )
    return episodes

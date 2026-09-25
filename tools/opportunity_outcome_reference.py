#!/usr/bin/env python3
"""Later outcome classification for Suite 0.2 opportunity candidates.

Outcome labels are retrospective diagnostics only. They must never be used to
backdate live opportunity knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from tools.market_map_offline_core import FAIL_MAX_BARS, IntegrationSnapshot
from tools.opportunity_episode_reference import (
    OpportunityEpisode,
    OpportunityType,
)


class CandidateOutcome(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BREAKOUT_HELD = "BREAKOUT_HELD"
    BREAKOUT_FAKEOUT = "BREAKOUT_FAKEOUT"
    BREAKOUT_UNRESOLVED = "BREAKOUT_UNRESOLVED"
    REGIME_MATURED = "REGIME_MATURED"
    REGIME_FAILED = "REGIME_FAILED"
    REGIME_UNRESOLVED = "REGIME_UNRESOLVED"


@dataclass(frozen=True)
class EpisodeOutcome:
    episode_id: str
    outcome: CandidateOutcome
    outcome_bar: int | None


def classify_breakout(
    episode: OpportunityEpisode,
    snapshots: Sequence[IntegrationSnapshot],
) -> EpisodeOutcome:
    if episode.opportunity_type != OpportunityType.BREAKOUT_CANDIDATE:
        return EpisodeOutcome(
            episode.episode_id,
            CandidateOutcome.NOT_APPLICABLE,
            None,
        )

    start = episode.confirmation_bar
    end = min(len(snapshots) - 1, start + FAIL_MAX_BARS)

    for i in range(start + 1, end + 1):
        snap = snapshots[i]
        if snap.fakeout_event:
            return EpisodeOutcome(
                episode.episode_id,
                CandidateOutcome.BREAKOUT_FAKEOUT,
                i,
            )

    if end < start + FAIL_MAX_BARS:
        return EpisodeOutcome(
            episode.episode_id,
            CandidateOutcome.BREAKOUT_UNRESOLVED,
            None,
        )

    terminal = snapshots[end]
    if terminal.structure_dir == episode.direction or terminal.map_dir == episode.direction:
        return EpisodeOutcome(
            episode.episode_id,
            CandidateOutcome.BREAKOUT_HELD,
            end,
        )

    return EpisodeOutcome(
        episode.episode_id,
        CandidateOutcome.BREAKOUT_UNRESOLVED,
        end,
    )


def classify_regime_transitions(
    episodes: Sequence[OpportunityEpisode],
) -> dict[str, EpisodeOutcome]:
    """Classify transition candidates by the next decisive regime event.

    A candidate MATURES when a strict coherent REGIME_REVERSAL in the same
    direction occurs before an opposite transition candidate.

    It FAILS when an opposite transition candidate arrives first.

    No arbitrary bar horizon is imposed here.
    """
    ordered = sorted(
        episodes,
        key=lambda e: (
            e.confirmation_bar,
            e.opportunity_type.value,
            e.direction,
        ),
    )
    transitions = [
        e
        for e in ordered
        if e.opportunity_type == OpportunityType.REGIME_TRANSITION_CANDIDATE
    ]

    out: dict[str, EpisodeOutcome] = {}

    for candidate in transitions:
        decisive: EpisodeOutcome | None = None
        for other in ordered:
            if other.confirmation_bar <= candidate.confirmation_bar:
                continue

            if (
                other.opportunity_type == OpportunityType.REGIME_REVERSAL
                and other.direction == candidate.direction
            ):
                decisive = EpisodeOutcome(
                    candidate.episode_id,
                    CandidateOutcome.REGIME_MATURED,
                    other.confirmation_bar,
                )
                break

            if (
                other.opportunity_type
                == OpportunityType.REGIME_TRANSITION_CANDIDATE
                and other.direction == -candidate.direction
            ):
                decisive = EpisodeOutcome(
                    candidate.episode_id,
                    CandidateOutcome.REGIME_FAILED,
                    other.confirmation_bar,
                )
                break

        out[candidate.episode_id] = decisive or EpisodeOutcome(
            candidate.episode_id,
            CandidateOutcome.REGIME_UNRESOLVED,
            None,
        )

    return out


def classify_all(
    episodes: Sequence[OpportunityEpisode],
    snapshots: Sequence[IntegrationSnapshot],
) -> dict[str, EpisodeOutcome]:
    regime = classify_regime_transitions(episodes)
    out: dict[str, EpisodeOutcome] = {}

    for episode in episodes:
        if episode.opportunity_type == OpportunityType.BREAKOUT_CANDIDATE:
            out[episode.episode_id] = classify_breakout(episode, snapshots)
        elif episode.opportunity_type == OpportunityType.REGIME_TRANSITION_CANDIDATE:
            out[episode.episode_id] = regime[episode.episode_id]
        else:
            out[episode.episode_id] = EpisodeOutcome(
                episode.episode_id,
                CandidateOutcome.NOT_APPLICABLE,
                None,
            )

    return out

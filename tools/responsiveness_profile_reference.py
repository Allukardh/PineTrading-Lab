#!/usr/bin/env python3
"""Research-only responsiveness/profile posture over OPERATOR_READINESS_V1.

Profiles do not mutate any Market Map / Execution / Opportunity path.

ANTECIPADO:
- event when the unified operator projection newly enters ARMED.

PADRAO:
- existing unified operator CONFIRMA event.

CONFIRMADO:
- one bar after PADRAO only if at least one source that confirmed remains
  active in the same direction and the unified projection is not in conflict.

These are action-posture counterfactuals, not new indicator thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from tools.execution_state_reference import Readiness
from tools.operator_readiness_reference import (
    OperatorProjection,
    OperatorReadiness,
    PathReadiness,
)


class ProfileMode(str, Enum):
    ANTECIPADO = "ANTECIPADO"
    PADRAO = "PADRAO"
    CONFIRMADO = "CONFIRMADO"


@dataclass(frozen=True)
class ProfileEvent:
    mode: ProfileMode
    bar: int
    direction: int
    sources: tuple[str, ...]
    reference_confirm_bar: int | None = None


@dataclass(frozen=True)
class AnticipatedResolution:
    event: ProfileEvent
    converted: bool
    confirm_bar: int | None
    end_bar: int | None
    bars_to_confirm: int | None


@dataclass(frozen=True)
class ConfirmedResolution:
    standard_event: ProfileEvent
    survived: bool
    confirmed_event: ProfileEvent | None
    reason: str


def anticipated_events(
    projections: Sequence[OperatorProjection],
) -> list[ProfileEvent]:
    out=[]
    prev:OperatorProjection|None=None
    for i,p in enumerate(projections):
        newly_armed=(
            p.readiness==OperatorReadiness.ARMED
            and p.direction in (-1,1)
            and (
                prev is None
                or prev.readiness not in {
                    OperatorReadiness.ARMED,
                    OperatorReadiness.CONFIRMED,
                }
                or prev.direction!=p.direction
            )
        )
        if newly_armed:
            out.append(ProfileEvent(
                ProfileMode.ANTECIPADO,
                i,
                p.direction,
                tuple(p.selected_sources),
                None,
            ))
        prev=p
    return out


def standard_events(
    projections: Sequence[OperatorProjection],
) -> list[ProfileEvent]:
    out=[]
    for i,p in enumerate(projections):
        if p.confirm and p.direction in (-1,1):
            out.append(ProfileEvent(
                ProfileMode.PADRAO,
                i,
                p.direction,
                tuple(p.confirming_sources),
                i,
            ))
    return out


def resolve_anticipated(
    event: ProfileEvent,
    path_rows: Sequence[dict[str,PathReadiness]],
) -> AnticipatedResolution:
    """Resolve an ARMED event against its source paths only."""
    for j in range(event.bar, len(path_rows)):
        rows=path_rows[j]
        candidates=[rows[s] for s in event.sources if s in rows]

        if any(
            p.confirm and p.direction==event.direction
            for p in candidates
        ):
            return AnticipatedResolution(
                event=event,
                converted=True,
                confirm_bar=j,
                end_bar=j,
                bars_to_confirm=j-event.bar,
            )

        alive=any(
            p.readiness!=Readiness.WAIT and p.direction==event.direction
            for p in candidates
        )
        if not alive:
            return AnticipatedResolution(
                event=event,
                converted=False,
                confirm_bar=None,
                end_bar=j,
                bars_to_confirm=None,
            )

    return AnticipatedResolution(
        event=event,
        converted=False,
        confirm_bar=None,
        end_bar=len(path_rows)-1 if path_rows else None,
        bars_to_confirm=None,
    )


def resolve_confirmed(
    event: ProfileEvent,
    projections: Sequence[OperatorProjection],
    path_rows: Sequence[dict[str,PathReadiness]],
) -> ConfirmedResolution:
    j=event.bar+1
    if j>=len(projections):
        return ConfirmedResolution(event,False,None,"END_OF_DATA")

    p=projections[j]
    if p.conflict:
        return ConfirmedResolution(event,False,None,"OPERATOR_CONFLICT")

    if p.direction!=event.direction:
        return ConfirmedResolution(event,False,None,"DIRECTION_LOST")

    rows=path_rows[j]
    candidates=[rows[s] for s in event.sources if s in rows]
    persistent=tuple(
        x.path for x in candidates
        if x.readiness!=Readiness.WAIT and x.direction==event.direction
    )
    if not persistent:
        return ConfirmedResolution(event,False,None,"CONFIRMING_SOURCE_DIED")

    return ConfirmedResolution(
        event,
        True,
        ProfileEvent(
            ProfileMode.CONFIRMADO,
            j,
            event.direction,
            persistent,
            event.bar,
        ),
        "PERSISTED",
    )

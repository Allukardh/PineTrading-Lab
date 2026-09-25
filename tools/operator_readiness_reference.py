#!/usr/bin/env python3
"""Operator-facing readiness projection across accepted independent paths.

Research-only projection. It owns no market logic and mutates no path.

Operational urgency is intentionally NOT the numeric Readiness enum order:
current CONFIRMED > ARMED > PREP > ALIGNED > WAIT.

If active paths disagree on direction, the projection is CONFLICT and emits no
actionable unified confirmation. Raw path events remain available to telemetry.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from tools.execution_state_reference import Readiness


class OperatorReadiness(str, Enum):
    WAIT = "WAIT"
    PREP = "PREP"
    ARMED = "ARMED"
    CONFIRMED = "CONFIRMED"
    ALIGNED = "ALIGNED"
    CONFLICT = "CONFLICT"


URGENCY = {
    Readiness.WAIT: 0,
    Readiness.ALIGNED: 1,
    Readiness.PREP: 2,
    Readiness.ARMED: 3,
    Readiness.CONFIRMED: 4,
}


@dataclass(frozen=True)
class PathReadiness:
    path: str
    readiness: Readiness
    direction: int
    confirm: bool = False


@dataclass(frozen=True)
class OperatorProjection:
    readiness: OperatorReadiness
    direction: int
    conflict: bool
    confirm: bool
    active_sources: tuple[str, ...]
    selected_sources: tuple[str, ...]
    confirming_sources: tuple[str, ...]
    suppressed_confirm_sources: tuple[str, ...]
    background_aligned_sources: tuple[str, ...]


def _validate(paths: Iterable[PathReadiness]) -> tuple[PathReadiness, ...]:
    xs=tuple(paths)
    seen=set()
    for p in xs:
        if p.path in seen:
            raise ValueError(f"duplicate path: {p.path}")
        seen.add(p.path)
        if p.direction not in (-1,0,1):
            raise ValueError("direction must be -1/0/+1")
        if p.readiness != Readiness.WAIT and p.direction not in (-1,1):
            raise ValueError("active readiness requires directional path")
    return xs


def project(paths: Iterable[PathReadiness]) -> OperatorProjection:
    xs=_validate(paths)
    active=tuple(p for p in xs if p.readiness != Readiness.WAIT)
    confirming=tuple(p.path for p in xs if p.confirm)

    if not active:
        return OperatorProjection(
            readiness=OperatorReadiness.WAIT,
            direction=0,
            conflict=False,
            confirm=False,
            active_sources=(),
            selected_sources=(),
            confirming_sources=confirming,
            suppressed_confirm_sources=(),
            background_aligned_sources=(),
        )

    directions={p.direction for p in active}
    active_sources=tuple(p.path for p in active)
    background_aligned=tuple(
        p.path for p in active if p.readiness==Readiness.ALIGNED
    )

    if len(directions)>1:
        return OperatorProjection(
            readiness=OperatorReadiness.CONFLICT,
            direction=0,
            conflict=True,
            confirm=False,
            active_sources=active_sources,
            selected_sources=active_sources,
            confirming_sources=confirming,
            suppressed_confirm_sources=confirming,
            background_aligned_sources=background_aligned,
        )

    direction=next(iter(directions))
    max_urgency=max(URGENCY[p.readiness] for p in active)
    selected=tuple(
        p.path for p in active if URGENCY[p.readiness]==max_urgency
    )
    selected_readiness=next(
        p.readiness for p in active if URGENCY[p.readiness]==max_urgency
    )

    mapped=OperatorReadiness[selected_readiness.name]
    return OperatorProjection(
        readiness=mapped,
        direction=direction,
        conflict=False,
        confirm=bool(confirming),
        active_sources=active_sources,
        selected_sources=selected,
        confirming_sources=confirming,
        suppressed_confirm_sources=(),
        background_aligned_sources=background_aligned,
    )


def from_sample(path: str, sample) -> PathReadiness:
    return PathReadiness(
        path=path,
        readiness=sample.result.state.readiness,
        direction=sample.result.state.direction,
        confirm=bool(sample.result.events.confirm),
    )

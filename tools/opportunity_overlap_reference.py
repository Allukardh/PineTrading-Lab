#!/usr/bin/env python3
"""Pure overlap diagnostics for independent PineTrading readiness paths.

This module does not arbitrate and does not mutate any path. It only measures
coexistence, directional conflict and near-duplicate confirmations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tools.execution_state_reference import Readiness


@dataclass(frozen=True)
class ConfirmEvent:
    bar: int
    direction: int


@dataclass(frozen=True)
class NearConfirmMatch:
    a_bar: int
    b_bar: int
    direction: int
    distance_bars: int


def readiness_active(sample) -> bool:
    return sample.result.state.readiness != Readiness.WAIT


def armed_or_better(sample) -> bool:
    return sample.result.state.readiness >= Readiness.ARMED


def confirm_events(samples: Sequence) -> list[ConfirmEvent]:
    out=[]
    for i,s in enumerate(samples):
        if s.result.events.confirm and s.result.state.direction in (-1,1):
            out.append(ConfirmEvent(i,s.result.state.direction))
    return out


def pairwise_overlap(a: Sequence, b: Sequence) -> dict:
    if len(a)!=len(b):
        raise ValueError("path lengths must match")
    both_active=same=opposite=both_armed=0
    simultaneous=sim_same=sim_opp=0
    for sa,sb in zip(a,b):
        aa=readiness_active(sa); bb=readiness_active(sb)
        if aa and bb:
            both_active+=1
            da=sa.result.state.direction; db=sb.result.state.direction
            if da in (-1,1) and db in (-1,1):
                if da==db: same+=1
                else: opposite+=1
            if armed_or_better(sa) and armed_or_better(sb):
                both_armed+=1
        ca=sa.result.events.confirm
        cb=sb.result.events.confirm
        if ca and cb:
            simultaneous+=1
            da=sa.result.state.direction; db=sb.result.state.direction
            if da in (-1,1) and db in (-1,1):
                if da==db: sim_same+=1
                else: sim_opp+=1
    return {
        "both_active_bars":both_active,
        "same_direction_active_bars":same,
        "opposite_direction_active_bars":opposite,
        "both_armed_or_better_bars":both_armed,
        "simultaneous_confirms":simultaneous,
        "simultaneous_same_direction_confirms":sim_same,
        "simultaneous_opposite_direction_confirms":sim_opp,
    }


def match_near_confirms(
    a: Sequence[ConfirmEvent],
    b: Sequence[ConfirmEvent],
    *,
    window_bars: int=3,
) -> list[NearConfirmMatch]:
    if window_bars<0:
        raise ValueError("window_bars must be >= 0")

    candidates=[]
    for ia,ea in enumerate(a):
        for ib,eb in enumerate(b):
            if ea.direction!=eb.direction:
                continue
            dist=abs(ea.bar-eb.bar)
            if dist<=window_bars:
                candidates.append((dist,ea.bar,eb.bar,ia,ib,ea.direction))

    # Greedy deterministic one-to-one matching, closest events first.
    candidates.sort()
    used_a=set(); used_b=set(); out=[]
    for dist,abar,bbar,ia,ib,direction in candidates:
        if ia in used_a or ib in used_b:
            continue
        used_a.add(ia); used_b.add(ib)
        out.append(NearConfirmMatch(abar,bbar,direction,dist))
    return out


def triple_overlap(a: Sequence,b: Sequence,c: Sequence) -> dict:
    if not (len(a)==len(b)==len(c)):
        raise ValueError("path lengths must match")
    all_active=all_same=direction_conflict=0
    all_armed=0
    for sa,sb,sc in zip(a,b,c):
        if not (readiness_active(sa) and readiness_active(sb) and readiness_active(sc)):
            continue
        all_active+=1
        dirs=[x.result.state.direction for x in (sa,sb,sc)]
        real=[d for d in dirs if d in (-1,1)]
        if len(real)==3 and len(set(real))==1:
            all_same+=1
        elif len(set(real))>1:
            direction_conflict+=1
        if all(armed_or_better(x) for x in (sa,sb,sc)):
            all_armed+=1
    return {
        "all_active_bars":all_active,
        "all_same_direction_bars":all_same,
        "direction_conflict_bars":direction_conflict,
        "all_armed_or_better_bars":all_armed,
    }

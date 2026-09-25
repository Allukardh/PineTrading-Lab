#!/usr/bin/env python3
"""Reference Market Map -> Execution location bridge.

This models semantic integration only. It does not calculate Market Map
structure itself and is not a TradingView production artifact.
"""
from __future__ import annotations

from dataclasses import dataclass

from tools.execution_state_reference import Location


APPROACH_ATR = 0.50
EVENT_HOLD_BARS = 3
# Preserve the original 3-bar memory through the primary 15m/1h/4h
# Execution matrix, but never let a reaction event remain "fresh" for days
# or weeks solely because the chart timeframe is large.
EVENT_HOLD_MAX_MS = 12 * 60 * 60 * 1000


@dataclass(frozen=True)
class MapEvidence:
    bar_index: int
    map_dir: int
    atr: float | None
    close: float | None

    correction_active: bool
    bar_time_ms: int | None = None
    thesis_invalidated: bool = False
    structural_conflict: bool = False

    t1_top: float | None = None
    t1_bottom: float | None = None
    primary_top: float | None = None
    primary_bottom: float | None = None
    t3_top: float | None = None
    t3_bottom: float | None = None

    retest_event: bool = False
    reclaim_event: bool = False
    destination_near: bool = False


@dataclass(frozen=True)
class BridgeMemory:
    direction: int = 0
    last_retest_bar: int | None = None
    last_reclaim_bar: int | None = None
    last_retest_time_ms: int | None = None
    last_reclaim_time_ms: int | None = None


@dataclass(frozen=True)
class BridgeResult:
    location: Location
    memory: BridgeMemory


def _finite_positive(value: float | None) -> bool:
    return value is not None and value > 0


def _valid_map(e: MapEvidence) -> bool:
    return (
        e.map_dir in (-1, 1)
        and not e.thesis_invalidated
        and not e.structural_conflict
        and _finite_positive(e.atr)
        and e.close is not None
    )


def _envelope(e: MapEvidence) -> tuple[float, float] | None:
    tops = [e.t1_top, e.primary_top, e.t3_top]
    bottoms = [e.t1_bottom, e.primary_bottom, e.t3_bottom]

    if any(v is None for v in tops + bottoms):
        return None

    top = max(v for v in tops if v is not None)
    bottom = min(v for v in bottoms if v is not None)

    if top < bottom:
        return None

    return top, bottom


def _event_is_fresh(
    last_bar: int | None,
    last_time_ms: int | None,
    current_bar: int,
    current_time_ms: int | None,
) -> bool:
    if last_bar is None or not (0 <= current_bar - last_bar <= EVENT_HOLD_BARS):
        return False

    # Synthetic/unit callers may omit timestamps; preserve the original
    # bar-count contract in that case. Real integrated evidence supplies time.
    if last_time_ms is None or current_time_ms is None:
        return True

    elapsed = current_time_ms - last_time_ms
    return 0 <= elapsed <= EVENT_HOLD_MAX_MS


def classify(previous: BridgeMemory, evidence: MapEvidence) -> BridgeResult:
    """Classify one bar/update into the canonical Execution location semantic."""
    if evidence.map_dir not in (-1, 0, 1):
        raise ValueError(f"map_dir must be -1/0/+1, got {evidence.map_dir}")

    if not _valid_map(evidence):
        return BridgeResult(Location.OUTSIDE, BridgeMemory())

    # Direction change is a hard event-memory boundary.
    if previous.direction not in (0, evidence.map_dir):
        previous = BridgeMemory()

    last_retest = previous.last_retest_bar
    last_reclaim = previous.last_reclaim_bar
    last_retest_time = previous.last_retest_time_ms
    last_reclaim_time = previous.last_reclaim_time_ms

    if evidence.retest_event:
        last_retest = evidence.bar_index
        last_retest_time = evidence.bar_time_ms
    if evidence.reclaim_event:
        last_reclaim = evidence.bar_index
        last_reclaim_time = evidence.bar_time_ms

    memory = BridgeMemory(
        direction=evidence.map_dir,
        last_retest_bar=last_retest,
        last_reclaim_bar=last_reclaim,
        last_retest_time_ms=last_retest_time,
        last_reclaim_time_ms=last_reclaim_time,
    )

    # Specific confirmed reaction semantics outrank geometry while they remain
    # fresh in both chart bars and real elapsed time.
    if _event_is_fresh(
        last_reclaim,
        last_reclaim_time,
        evidence.bar_index,
        evidence.bar_time_ms,
    ):
        return BridgeResult(Location.RECLAIM, memory)

    if _event_is_fresh(
        last_retest,
        last_retest_time,
        evidence.bar_index,
        evidence.bar_time_ms,
    ):
        return BridgeResult(Location.RETEST, memory)

    env = _envelope(evidence) if evidence.correction_active else None
    if env is not None:
        top, bottom = env
        close = evidence.close
        assert close is not None
        atr = evidence.atr
        assert atr is not None

        if bottom <= close <= top:
            return BridgeResult(Location.IN_CORRECTION, memory)

        if evidence.map_dir == 1 and close > top:
            if close - top <= atr * APPROACH_ATR:
                return BridgeResult(Location.APPROACHING, memory)

        if evidence.map_dir == -1 and close < bottom:
            if bottom - close <= atr * APPROACH_ATR:
                return BridgeResult(Location.APPROACHING, memory)

    if evidence.destination_near:
        return BridgeResult(Location.DESTINATION_NEAR, memory)

    return BridgeResult(Location.OUTSIDE, memory)

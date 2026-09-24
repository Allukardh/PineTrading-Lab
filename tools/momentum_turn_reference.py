#!/usr/bin/env python3
"""Reference implementation for Momentum Turn Engine candidate MTE-A.

This module validates clean-room momentum mechanics independently of Pine.

It is NOT a trading strategy, does not calculate PnL, and is not a production
TradingView artifact.

Candidate formula:
    source = HLC3
    fast   = EMA(source, 8)
    slow   = EMA(source, 21)
    atr    = RMA(TrueRange, 14)
    core   = (fast - slow) / atr

State thresholds:
    core_activity  = RMA(abs(core), 20)
    neutral_band   = 0.15 * core_activity
    accel          = core - core[1]
    accel_activity = RMA(abs(accel), 20)
    turn_band      = max(0.02, 0.50 * accel_activity)

The explicit SMA-seeded EMA/RMA helpers give deterministic research behavior.
Production Pine must later be checked against the reference output before the
candidate can be promoted.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from tools.execution_state_reference import Momentum


FAST_EMA = 8
SLOW_EMA = 21
ATR_LEN = 14
ACTIVITY_LEN = 20
NEUTRAL_FACTOR = 0.15
TURN_FACTOR = 0.50
TURN_FLOOR = 0.02
ACCEL_EPS = 1e-9


@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class MomentumSample:
    ready: bool
    core: float | None
    acceleration: float | None
    neutral_band: float | None
    turn_band: float | None
    state: Momentum


def _sma_seeded_ema(values: Sequence[float | None], length: int) -> list[float | None]:
    if length <= 0:
        raise ValueError("length must be > 0")

    out: list[float | None] = [None] * len(values)
    seed: list[float] = []
    prev: float | None = None
    alpha = 2.0 / (length + 1.0)

    for i, value in enumerate(values):
        if value is None:
            continue

        if prev is None:
            seed.append(value)
            if len(seed) == length:
                prev = sum(seed) / length
                out[i] = prev
        else:
            prev = alpha * value + (1.0 - alpha) * prev
            out[i] = prev

    return out


def _sma_seeded_rma(values: Sequence[float | None], length: int) -> list[float | None]:
    if length <= 0:
        raise ValueError("length must be > 0")

    out: list[float | None] = [None] * len(values)
    seed: list[float] = []
    prev: float | None = None
    alpha = 1.0 / length

    for i, value in enumerate(values):
        if value is None:
            continue

        if prev is None:
            seed.append(value)
            if len(seed) == length:
                prev = sum(seed) / length
                out[i] = prev
        else:
            prev = alpha * value + (1.0 - alpha) * prev
            out[i] = prev

    return out


def _true_range(bars: Sequence[Bar]) -> list[float]:
    tr: list[float] = []

    for i, bar in enumerate(bars):
        prev_close = bars[i - 1].close if i > 0 else bar.close
        tr.append(
            max(
                bar.high - bar.low,
                abs(bar.high - prev_close),
                abs(bar.low - prev_close),
            )
        )

    return tr


def _abs_series(values: Sequence[float | None]) -> list[float | None]:
    return [None if value is None else abs(value) for value in values]


def calculate(bars: Sequence[Bar]) -> list[MomentumSample]:
    """Calculate MTE-A samples for an OHLC sequence."""
    if not bars:
        return []

    for bar in bars:
        if bar.high < bar.low:
            raise ValueError("bar.high must be >= bar.low")
        if not (bar.low <= bar.open <= bar.high):
            raise ValueError("bar.open must be inside [low, high]")
        if not (bar.low <= bar.close <= bar.high):
            raise ValueError("bar.close must be inside [low, high]")

    source = [(bar.high + bar.low + bar.close) / 3.0 for bar in bars]

    fast = _sma_seeded_ema(source, FAST_EMA)
    slow = _sma_seeded_ema(source, SLOW_EMA)
    atr = _sma_seeded_rma(_true_range(bars), ATR_LEN)

    core: list[float | None] = []
    for f, s, a in zip(fast, slow, atr):
        if f is None or s is None or a is None or a <= 0.0:
            core.append(None)
        else:
            core.append((f - s) / a)

    core_activity = _sma_seeded_rma(_abs_series(core), ACTIVITY_LEN)

    acceleration: list[float | None] = []
    for i, value in enumerate(core):
        previous = core[i - 1] if i > 0 else None
        acceleration.append(
            None if value is None or previous is None else value - previous
        )

    accel_activity = _sma_seeded_rma(
        _abs_series(acceleration),
        ACTIVITY_LEN,
    )

    result: list[MomentumSample] = []

    for value, activity, accel, accel_activity_value in zip(
        core,
        core_activity,
        acceleration,
        accel_activity,
    ):
        ready = (
            value is not None
            and activity is not None
            and accel is not None
            and accel_activity_value is not None
            and activity > 0.0
        )

        if not ready:
            result.append(
                MomentumSample(
                    ready=False,
                    core=value,
                    acceleration=accel,
                    neutral_band=None,
                    turn_band=None,
                    state=Momentum.NEUTRAL,
                )
            )
            continue

        assert value is not None
        assert activity is not None
        assert accel is not None
        assert accel_activity_value is not None

        neutral_band = NEUTRAL_FACTOR * activity
        turn_band = max(TURN_FLOOR, TURN_FACTOR * accel_activity_value)

        # Numerical sign noise around zero must not flip semantic states after
        # price scaling/translation. This is an arithmetic epsilon, not a
        # market threshold.
        accel_semantic = 0.0 if abs(accel) <= ACCEL_EPS else accel

        if abs(value) <= neutral_band:
            state = Momentum.NEUTRAL
        elif value > 0.0:
            if accel_semantic < -turn_band:
                state = Momentum.TURN_DOWN
            elif accel_semantic < 0.0:
                state = Momentum.UP_DECEL
            else:
                state = Momentum.UP_ACCEL
        else:
            if accel_semantic > turn_band:
                state = Momentum.TURN_UP
            elif accel_semantic > 0.0:
                state = Momentum.DOWN_DECEL
            else:
                state = Momentum.DOWN_ACCEL

        result.append(
            MomentumSample(
                ready=True,
                core=value,
                acceleration=accel,
                neutral_band=neutral_band,
                turn_band=turn_band,
                state=state,
            )
        )

    return result


def transform_scale(bars: Iterable[Bar], factor: float) -> list[Bar]:
    if factor <= 0:
        raise ValueError("factor must be > 0")

    return [
        Bar(
            open=bar.open * factor,
            high=bar.high * factor,
            low=bar.low * factor,
            close=bar.close * factor,
        )
        for bar in bars
    ]


def transform_translate(bars: Iterable[Bar], offset: float) -> list[Bar]:
    return [
        Bar(
            open=bar.open + offset,
            high=bar.high + offset,
            low=bar.low + offset,
            close=bar.close + offset,
        )
        for bar in bars
    ]

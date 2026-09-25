#!/usr/bin/env python3
"""Reference Participation Engine candidate PSE-A.

PSE-A uses only reload-safe OHLCV evidence for production semantics:
- relative volume vs prior confirmed EMA20 baseline
- candle close-location pressure proxy

Binance taker-buy imbalance is exposed only as an offline validation helper.
It is NOT a production Pine dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tools.execution_state_reference import Participation


VOLUME_EMA_LEN = 20
CONTRACTED_BELOW = 0.80
EXPANDED_AT_OR_ABOVE = 1.20
STRONG_AT_OR_ABOVE = 1.50
PRESSURE_MIN = 0.20


@dataclass(frozen=True)
class ParticipationBar:
    high: float
    low: float
    close: float
    volume: float | None


@dataclass(frozen=True)
class ParticipationSample:
    ready: bool
    relative_volume: float | None
    pressure_proxy: float
    directional_pressure: float | None
    strong_expansion: bool
    state: Participation


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
        if value < 0.0:
            raise ValueError("volume cannot be negative")

        if prev is None:
            seed.append(value)
            if len(seed) == length:
                prev = sum(seed) / length
                out[i] = prev
        else:
            prev = alpha * value + (1.0 - alpha) * prev
            out[i] = prev

    return out


def close_location_pressure(high: float, low: float, close: float) -> float:
    if high < low:
        raise ValueError("high must be >= low")
    if close < low or close > high:
        raise ValueError("close must be inside [low, high]")

    span = high - low
    if span == 0.0:
        return 0.0

    value = (2.0 * close - high - low) / span

    # Floating arithmetic should never create a semantic value outside the
    # theoretical [-1, +1] range.
    return max(-1.0, min(1.0, value))


def taker_imbalance(
    volume: float | None,
    taker_buy_base_volume: float | None,
) -> float | None:
    """Validation-only Binance taker imbalance; not used by PSE-A state."""
    if volume is None or taker_buy_base_volume is None:
        return None
    if volume <= 0.0:
        return None
    if taker_buy_base_volume < 0.0 or taker_buy_base_volume > volume:
        raise ValueError("taker buy base volume must be inside [0, volume]")

    value = 2.0 * taker_buy_base_volume / volume - 1.0
    return max(-1.0, min(1.0, value))


def calculate(
    bars: Sequence[ParticipationBar],
    map_dirs: Sequence[int],
) -> list[ParticipationSample]:
    if len(bars) != len(map_dirs):
        raise ValueError("bars and map_dirs must have identical length")

    for direction in map_dirs:
        if direction not in (-1, 0, 1):
            raise ValueError("map direction must be -1/0/+1")

    volumes = [bar.volume for bar in bars]
    ema = _sma_seeded_ema(volumes, VOLUME_EMA_LEN)

    result: list[ParticipationSample] = []

    for i, (bar, direction) in enumerate(zip(bars, map_dirs)):
        pressure = close_location_pressure(bar.high, bar.low, bar.close)
        prior_baseline = ema[i - 1] if i > 0 else None

        ready = (
            direction in (-1, 1)
            and bar.volume is not None
            and bar.volume >= 0.0
            and prior_baseline is not None
            and prior_baseline > 0.0
        )

        if not ready:
            result.append(
                ParticipationSample(
                    ready=False,
                    relative_volume=None,
                    pressure_proxy=pressure,
                    directional_pressure=None,
                    strong_expansion=False,
                    state=Participation.NEUTRAL,
                )
            )
            continue

        assert bar.volume is not None
        assert prior_baseline is not None

        relative_volume = bar.volume / prior_baseline
        directional_pressure = pressure * direction
        strong = relative_volume >= STRONG_AT_OR_ABOVE

        if relative_volume < CONTRACTED_BELOW:
            state = Participation.WEAK
        elif (
            relative_volume >= EXPANDED_AT_OR_ABOVE
            and directional_pressure >= PRESSURE_MIN
        ):
            state = Participation.CONFIRM
        elif (
            relative_volume >= EXPANDED_AT_OR_ABOVE
            and directional_pressure <= -PRESSURE_MIN
        ):
            state = Participation.CONTRARY
        else:
            state = Participation.NEUTRAL

        result.append(
            ParticipationSample(
                ready=True,
                relative_volume=relative_volume,
                pressure_proxy=pressure,
                directional_pressure=directional_pressure,
                strong_expansion=strong,
                state=state,
            )
        )

    return result

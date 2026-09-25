#!/usr/bin/env python3
"""Reference RSI State Engine candidate RSE-A.

The module validates RSI semantics independently of Pine/TradingView syntax.
It uses a deterministic Wilder RSI implementation and the suite's existing
RsiState enum.

This is research infrastructure, not a trading strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tools.execution_state_reference import RsiState


RSI_LEN = 14
CENTER_LOW = 48.0
CENTER_HIGH = 52.0
OVERBOUGHT = 70.0
OVERSOLD = 30.0
EXTREME_OVERBOUGHT = 80.0
EXTREME_OVERSOLD = 20.0
MIN_STEP = 0.25
ZONE_MEMORY_BARS = 2


@dataclass(frozen=True)
class RsiSample:
    ready: bool
    value: float | None
    step: float | None
    state: RsiState


def wilder_rsi(closes: Sequence[float], length: int = RSI_LEN) -> list[float | None]:
    if length <= 0:
        raise ValueError("length must be > 0")
    if not closes:
        return []

    out: list[float | None] = [None] * len(closes)
    if len(closes) <= length:
        return out

    gains: list[float] = []
    losses: list[float] = []

    for i in range(1, length + 1):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains) / length
    avg_loss = sum(losses) / length

    def value(gain: float, loss: float) -> float:
        if gain == 0.0 and loss == 0.0:
            return 50.0
        if loss == 0.0:
            return 100.0
        if gain == 0.0:
            return 0.0
        rs = gain / loss
        return 100.0 - (100.0 / (1.0 + rs))

    out[length] = value(avg_gain, avg_loss)

    for i in range(length + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        avg_gain = ((length - 1) * avg_gain + gain) / length
        avg_loss = ((length - 1) * avg_loss + loss) / length
        out[i] = value(avg_gain, avg_loss)

    return out


def context_direction(rsi_value: float | None) -> int:
    if rsi_value is None:
        return 0
    if rsi_value >= CENTER_HIGH:
        return 1
    if rsi_value <= CENTER_LOW:
        return -1
    return 0


def _recent_zone(
    values: Sequence[float | None],
    index: int,
    *,
    low_zone: bool,
) -> bool:
    start = max(0, index - ZONE_MEMORY_BARS)

    for j in range(start, index + 1):
        value = values[j]
        if value is None:
            continue
        if low_zone and value <= OVERSOLD:
            return True
        if not low_zone and value >= OVERBOUGHT:
            return True

    return False


def classify_rsi_values(values: Sequence[float | None]) -> list[RsiSample]:
    result: list[RsiSample] = []

    for i, current in enumerate(values):
        previous = values[i - 1] if i > 0 else None
        step = (
            None
            if current is None or previous is None
            else current - previous
        )

        if current is None or step is None:
            result.append(
                RsiSample(
                    ready=False,
                    value=current,
                    step=step,
                    state=RsiState.NEUTRAL,
                )
            )
            continue

        recent_oversold = _recent_zone(values, i, low_zone=True)
        recent_overbought = _recent_zone(values, i, low_zone=False)

        if current >= EXTREME_OVERBOUGHT:
            state = RsiState.EXTREME_OVERBOUGHT
        elif current <= EXTREME_OVERSOLD:
            state = RsiState.EXTREME_OVERSOLD
        elif (
            recent_oversold
            and current < CENTER_HIGH
            and step >= MIN_STEP
        ):
            state = RsiState.RECOVERING_OVERSOLD
        elif (
            recent_overbought
            and current > CENTER_LOW
            and step <= -MIN_STEP
        ):
            state = RsiState.FADING_OVERBOUGHT
        elif current >= OVERBOUGHT and step >= MIN_STEP:
            state = RsiState.RECOVERING_OVERBOUGHT
        elif current <= OVERSOLD and step <= -MIN_STEP:
            state = RsiState.FADING_OVERSOLD
        elif current >= CENTER_HIGH:
            state = RsiState.BULL
        elif current <= CENTER_LOW:
            state = RsiState.BEAR
        else:
            state = RsiState.NEUTRAL

        result.append(
            RsiSample(
                ready=True,
                value=current,
                step=step,
                state=state,
            )
        )

    return result


def calculate(closes: Sequence[float]) -> list[RsiSample]:
    return classify_rsi_values(wilder_rsi(closes, RSI_LEN))


def local_supports(direction: int, state: RsiState) -> bool:
    if direction == 1:
        return state in {
            RsiState.BULL,
            RsiState.RECOVERING_OVERSOLD,
            RsiState.RECOVERING_OVERBOUGHT,
        }
    if direction == -1:
        return state in {
            RsiState.BEAR,
            RsiState.FADING_OVERBOUGHT,
            RsiState.FADING_OVERSOLD,
        }
    return False


def local_opposes(direction: int, state: RsiState) -> bool:
    if direction == 1:
        return state in {
            RsiState.BEAR,
            RsiState.FADING_OVERBOUGHT,
            RsiState.EXTREME_OVERBOUGHT,
        }
    if direction == -1:
        return state in {
            RsiState.BULL,
            RsiState.RECOVERING_OVERSOLD,
            RsiState.EXTREME_OVERSOLD,
        }
    return True


def context_allows(direction: int, context_dir: int) -> bool:
    if direction not in (-1, 1):
        return False
    if context_dir not in (-1, 0, 1):
        raise ValueError("context_dir must be -1/0/+1")
    return context_dir != -direction


def context_opposes(direction: int, context_dir: int) -> bool:
    if direction not in (-1, 1):
        return True
    if context_dir not in (-1, 0, 1):
        raise ValueError("context_dir must be -1/0/+1")
    return context_dir == -direction


def supports(direction: int, state: RsiState, context_dir: int) -> bool:
    return local_supports(direction, state) and context_allows(direction, context_dir)


def opposes(direction: int, state: RsiState, context_dir: int) -> bool:
    return local_opposes(direction, state) or context_opposes(direction, context_dir)

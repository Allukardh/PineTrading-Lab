#!/usr/bin/env python3
from __future__ import annotations

import math
import unittest

from tools.execution_state_reference import Momentum
from tools.momentum_turn_reference import (
    ACTIVITY_LEN,
    ATR_LEN,
    FAST_EMA,
    NEUTRAL_FACTOR,
    SLOW_EMA,
    TURN_FACTOR,
    TURN_FLOOR,
    Bar,
    calculate,
    transform_scale,
    transform_translate,
)


def trend_bars(
    count: int,
    *,
    start: float = 100.0,
    step: float = 0.25,
    wick: float = 0.40,
) -> list[Bar]:
    bars: list[Bar] = []
    price = start

    for _ in range(count):
        open_ = price
        close = price + step
        high = max(open_, close) + wick
        low = min(open_, close) - wick
        bars.append(Bar(open_, high, low, close))
        price = close

    return bars


def reversal_bars(
    up_count: int = 130,
    down_count: int = 130,
) -> list[Bar]:
    first = trend_bars(up_count, start=100.0, step=0.25)

    start = first[-1].close
    second = trend_bars(down_count, start=start, step=-0.30)

    return first + second


def mirror_reversal_bars(
    down_count: int = 130,
    up_count: int = 130,
) -> list[Bar]:
    first = trend_bars(down_count, start=200.0, step=-0.25)

    start = first[-1].close
    second = trend_bars(up_count, start=start, step=0.30)

    return first + second


class MomentumTurnReferenceTests(unittest.TestCase):
    def assert_series_close(self, a, b, places=10):
        self.assertEqual(len(a), len(b))
        for left, right in zip(a, b):
            self.assertEqual(left.ready, right.ready)
            self.assertEqual(left.state, right.state)

            if left.core is None or right.core is None:
                self.assertIs(left.core, right.core)
            else:
                self.assertAlmostEqual(left.core, right.core, places=places)

            if left.acceleration is None or right.acceleration is None:
                self.assertIs(left.acceleration, right.acceleration)
            else:
                self.assertAlmostEqual(
                    left.acceleration,
                    right.acceleration,
                    places=places,
                )

    def test_candidate_constants_are_explicit(self):
        self.assertEqual(FAST_EMA, 8)
        self.assertEqual(SLOW_EMA, 21)
        self.assertEqual(ATR_LEN, 14)
        self.assertEqual(ACTIVITY_LEN, 20)
        self.assertAlmostEqual(NEUTRAL_FACTOR, 0.15)
        self.assertAlmostEqual(TURN_FACTOR, 0.50)
        self.assertAlmostEqual(TURN_FLOOR, 0.02)

    def test_scale_invariance(self):
        bars = reversal_bars()
        base = calculate(bars)
        scaled = calculate(transform_scale(bars, 137.0))

        self.assert_series_close(base, scaled, places=9)

    def test_translation_invariance(self):
        bars = reversal_bars()
        base = calculate(bars)
        shifted = calculate(transform_translate(bars, 50_000.0))

        self.assert_series_close(base, shifted, places=8)

    def test_flat_market_is_honest_and_non_actionable(self):
        bars = [
            Bar(open=100.0, high=100.0, low=100.0, close=100.0)
            for _ in range(200)
        ]

        samples = calculate(bars)

        self.assertTrue(samples)
        self.assertTrue(all(not sample.ready for sample in samples))
        self.assertTrue(
            all(sample.state == Momentum.NEUTRAL for sample in samples)
        )

    def test_constant_uptrend_has_no_bear_acceleration_or_turn(self):
        samples = calculate(trend_bars(300, step=0.20))

        ready = [sample for sample in samples if sample.ready]
        self.assertTrue(ready)

        forbidden = {
            Momentum.DOWN_ACCEL,
            Momentum.TURN_DOWN,
        }
        self.assertFalse(any(sample.state in forbidden for sample in ready))

        self.assertTrue(
            any(sample.state == Momentum.UP_ACCEL for sample in ready)
        )

    def test_constant_downtrend_has_no_bull_acceleration_or_turn(self):
        samples = calculate(
            trend_bars(300, start=300.0, step=-0.20)
        )

        ready = [sample for sample in samples if sample.ready]
        self.assertTrue(ready)

        forbidden = {
            Momentum.UP_ACCEL,
            Momentum.TURN_UP,
        }
        self.assertFalse(any(sample.state in forbidden for sample in ready))

        self.assertTrue(
            any(sample.state == Momentum.DOWN_ACCEL for sample in ready)
        )

    def test_up_to_down_reversal_turns_before_negative_core(self):
        split = 130
        samples = calculate(reversal_bars(up_count=split, down_count=130))

        turn_indexes = [
            i
            for i, sample in enumerate(samples)
            if i >= split and sample.state == Momentum.TURN_DOWN
        ]
        self.assertTrue(turn_indexes)

        first_turn = turn_indexes[0]
        self.assertGreater(samples[first_turn].core, 0.0)

        bearish_indexes = [
            i
            for i, sample in enumerate(samples)
            if i >= split and sample.state == Momentum.DOWN_ACCEL
        ]
        self.assertTrue(bearish_indexes)
        self.assertLess(first_turn, bearish_indexes[0])

    def test_down_to_up_reversal_turns_before_positive_core(self):
        split = 130
        samples = calculate(
            mirror_reversal_bars(down_count=split, up_count=130)
        )

        turn_indexes = [
            i
            for i, sample in enumerate(samples)
            if i >= split and sample.state == Momentum.TURN_UP
        ]
        self.assertTrue(turn_indexes)

        first_turn = turn_indexes[0]
        self.assertLess(samples[first_turn].core, 0.0)

        bullish_indexes = [
            i
            for i, sample in enumerate(samples)
            if i >= split and sample.state == Momentum.UP_ACCEL
        ]
        self.assertTrue(bullish_indexes)
        self.assertLess(first_turn, bullish_indexes[0])

    def test_small_sinusoidal_noise_does_not_break_scale_contract(self):
        bars: list[Bar] = []
        price = 100.0

        for i in range(320):
            open_ = price
            price += 0.18 + 0.015 * math.sin(i / 3.0)
            close = price
            high = max(open_, close) + 0.35 + 0.01 * math.sin(i)
            low = min(open_, close) - 0.35 - 0.01 * math.cos(i)
            bars.append(Bar(open_, high, low, close))

        base = calculate(bars)
        scaled = calculate(transform_scale(bars, 0.0137))

        self.assert_series_close(base, scaled, places=8)

    def test_invalid_ohlc_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate([Bar(open=10.0, high=9.0, low=8.0, close=8.5)])

        with self.assertRaises(ValueError):
            calculate([Bar(open=11.0, high=10.0, low=8.0, close=9.0)])


if __name__ == "__main__":
    unittest.main()

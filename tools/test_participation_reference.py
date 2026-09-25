#!/usr/bin/env python3
from __future__ import annotations

import unittest

from tools.execution_state_reference import Participation
from tools.participation_reference import (
    CONTRACTED_BELOW,
    EXPANDED_AT_OR_ABOVE,
    PRESSURE_MIN,
    STRONG_AT_OR_ABOVE,
    VOLUME_EMA_LEN,
    ParticipationBar,
    calculate,
    close_location_pressure,
    taker_imbalance,
)


def base_bars(count: int, *, volume: float = 100.0) -> list[ParticipationBar]:
    return [
        ParticipationBar(
            high=11.0,
            low=9.0,
            close=10.0,
            volume=volume,
        )
        for _ in range(count)
    ]


class ParticipationReferenceTests(unittest.TestCase):
    def test_constants_are_explicit(self):
        self.assertEqual(VOLUME_EMA_LEN, 20)
        self.assertAlmostEqual(CONTRACTED_BELOW, 0.80)
        self.assertAlmostEqual(EXPANDED_AT_OR_ABOVE, 1.20)
        self.assertAlmostEqual(STRONG_AT_OR_ABOVE, 1.50)
        self.assertAlmostEqual(PRESSURE_MIN, 0.20)

    def test_pressure_proxy_endpoints_and_midpoint(self):
        self.assertAlmostEqual(close_location_pressure(10.0, 0.0, 10.0), 1.0)
        self.assertAlmostEqual(close_location_pressure(10.0, 0.0, 0.0), -1.0)
        self.assertAlmostEqual(close_location_pressure(10.0, 0.0, 5.0), 0.0)

    def test_zero_range_pressure_is_neutral(self):
        self.assertEqual(close_location_pressure(10.0, 10.0, 10.0), 0.0)

    def test_pressure_is_price_scale_and_translation_invariant(self):
        base = close_location_pressure(110.0, 90.0, 106.0)
        scaled = close_location_pressure(11000.0, 9000.0, 10600.0)
        shifted = close_location_pressure(50110.0, 50090.0, 50106.0)

        self.assertAlmostEqual(base, scaled)
        self.assertAlmostEqual(base, shifted)

    def test_missing_baseline_is_not_ready(self):
        bars = base_bars(VOLUME_EMA_LEN)
        samples = calculate(bars, [1] * len(bars))

        self.assertTrue(all(not s.ready for s in samples))
        self.assertTrue(all(s.state == Participation.NEUTRAL for s in samples))

    def test_expanded_agreeing_volume_confirms_long(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=7.0,  # pressure +0.40
                volume=130.0,
            )
        )

        sample = calculate(bars, [1] * len(bars))[-1]

        self.assertTrue(sample.ready)
        self.assertGreaterEqual(sample.relative_volume, EXPANDED_AT_OR_ABOVE)
        self.assertGreaterEqual(sample.directional_pressure, PRESSURE_MIN)
        self.assertEqual(sample.state, Participation.CONFIRM)

    def test_expanded_opposing_volume_is_contrary_long(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=3.0,  # pressure -0.40
                volume=130.0,
            )
        )

        sample = calculate(bars, [1] * len(bars))[-1]

        self.assertEqual(sample.state, Participation.CONTRARY)

    def test_direction_mirrors_pressure_semantics(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=3.0,
                volume=130.0,
            )
        )

        short_sample = calculate(bars, [-1] * len(bars))[-1]
        self.assertEqual(short_sample.state, Participation.CONFIRM)

    def test_contracted_volume_is_weak(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=9.0,
                volume=70.0,
            )
        )

        sample = calculate(bars, [1] * len(bars))[-1]
        self.assertLess(sample.relative_volume, CONTRACTED_BELOW)
        self.assertEqual(sample.state, Participation.WEAK)

    def test_normal_volume_stays_neutral_despite_directional_close(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=10.0,
                volume=100.0,
            )
        )

        sample = calculate(bars, [1] * len(bars))[-1]
        self.assertEqual(sample.state, Participation.NEUTRAL)

    def test_strong_expansion_flag_is_separate_from_state_enum(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=7.0,
                volume=160.0,
            )
        )

        sample = calculate(bars, [1] * len(bars))[-1]
        self.assertTrue(sample.strong_expansion)
        self.assertEqual(sample.state, Participation.CONFIRM)

    def test_volume_scale_invariance(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=7.0,
                volume=130.0,
            )
        )

        scaled = [
            ParticipationBar(
                high=b.high,
                low=b.low,
                close=b.close,
                volume=None if b.volume is None else b.volume * 1000.0,
            )
            for b in bars
        ]

        a = calculate(bars, [1] * len(bars))[-1]
        b = calculate(scaled, [1] * len(scaled))[-1]

        self.assertEqual(a.state, b.state)
        self.assertAlmostEqual(a.relative_volume, b.relative_volume)

    def test_neutral_map_direction_is_not_ready(self):
        bars = base_bars(VOLUME_EMA_LEN + 2)
        samples = calculate(bars, [0] * len(bars))

        self.assertTrue(all(not sample.ready for sample in samples))
        self.assertTrue(all(sample.state == Participation.NEUTRAL for sample in samples))

    def test_zero_volume_after_ready_is_weak(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=5.0,
                volume=0.0,
            )
        )

        sample = calculate(bars, [1] * len(bars))[-1]
        self.assertTrue(sample.ready)
        self.assertEqual(sample.relative_volume, 0.0)
        self.assertEqual(sample.state, Participation.WEAK)

    def test_missing_current_volume_is_not_ready(self):
        bars = base_bars(VOLUME_EMA_LEN)
        bars.append(
            ParticipationBar(
                high=10.0,
                low=0.0,
                close=5.0,
                volume=None,
            )
        )

        sample = calculate(bars, [1] * len(bars))[-1]
        self.assertFalse(sample.ready)
        self.assertEqual(sample.state, Participation.NEUTRAL)

    def test_taker_imbalance_validation_helper(self):
        self.assertAlmostEqual(taker_imbalance(100.0, 100.0), 1.0)
        self.assertAlmostEqual(taker_imbalance(100.0, 50.0), 0.0)
        self.assertAlmostEqual(taker_imbalance(100.0, 0.0), -1.0)
        self.assertIsNone(taker_imbalance(0.0, 0.0))
        self.assertIsNone(taker_imbalance(None, None))

        with self.assertRaises(ValueError):
            taker_imbalance(100.0, 101.0)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            close_location_pressure(9.0, 10.0, 9.5)

        with self.assertRaises(ValueError):
            close_location_pressure(10.0, 0.0, 11.0)

        with self.assertRaises(ValueError):
            calculate(base_bars(2), [1])

        with self.assertRaises(ValueError):
            calculate(base_bars(2), [1, 2])


if __name__ == "__main__":
    unittest.main()

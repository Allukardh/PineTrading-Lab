#!/usr/bin/env python3
from __future__ import annotations

import unittest

from tools.execution_state_reference import RsiState
from tools.rsi_state_reference import (
    CENTER_HIGH,
    CENTER_LOW,
    EXTREME_OVERBOUGHT,
    EXTREME_OVERSOLD,
    MIN_STEP,
    OVERBOUGHT,
    OVERSOLD,
    RSI_LEN,
    ZONE_MEMORY_BARS,
    calculate,
    classify_rsi_values,
    context_allows,
    context_direction,
    context_opposes,
    local_opposes,
    local_supports,
    opposes,
    supports,
    wilder_rsi,
)


class RsiStateReferenceTests(unittest.TestCase):
    def test_constants_are_explicit(self):
        self.assertEqual(RSI_LEN, 14)
        self.assertEqual(CENTER_LOW, 48.0)
        self.assertEqual(CENTER_HIGH, 52.0)
        self.assertEqual(OVERBOUGHT, 70.0)
        self.assertEqual(OVERSOLD, 30.0)
        self.assertEqual(EXTREME_OVERBOUGHT, 80.0)
        self.assertEqual(EXTREME_OVERSOLD, 20.0)
        self.assertEqual(MIN_STEP, 0.25)
        self.assertEqual(ZONE_MEMORY_BARS, 2)

    def test_wilder_rsi_monotonic_bounds(self):
        up = [100.0 + i for i in range(80)]
        down = [200.0 - i for i in range(80)]

        up_rsi = wilder_rsi(up)
        down_rsi = wilder_rsi(down)

        self.assertEqual(up_rsi[RSI_LEN], 100.0)
        self.assertEqual(down_rsi[RSI_LEN], 0.0)

        for series in (up_rsi, down_rsi):
            for value in series:
                if value is not None:
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 100.0)

    def test_monotonic_series_reaches_extreme_states(self):
        up = calculate([100.0 + i for i in range(80)])
        down = calculate([200.0 - i for i in range(80)])

        self.assertEqual(up[-1].state, RsiState.EXTREME_OVERBOUGHT)
        self.assertEqual(down[-1].state, RsiState.EXTREME_OVERSOLD)

    def test_center_deadband(self):
        values = [None, 49.5, 50.0, 51.0]
        states = classify_rsi_values(values)

        self.assertEqual(states[2].state, RsiState.NEUTRAL)
        self.assertEqual(states[3].state, RsiState.NEUTRAL)

    def test_oversold_recovery_persists_after_zone_exit(self):
        values = [35.0, 29.0, 31.0, 34.0]
        states = classify_rsi_values(values)

        self.assertEqual(states[2].state, RsiState.RECOVERING_OVERSOLD)
        self.assertEqual(states[3].state, RsiState.RECOVERING_OVERSOLD)

    def test_oversold_recovery_expires_after_memory(self):
        values = [29.0, 31.0, 34.0, 37.0, 40.0]
        states = classify_rsi_values(values)

        self.assertEqual(states[1].state, RsiState.RECOVERING_OVERSOLD)
        self.assertEqual(states[2].state, RsiState.RECOVERING_OVERSOLD)
        self.assertEqual(states[3].state, RsiState.BEAR)
        self.assertEqual(states[4].state, RsiState.BEAR)

    def test_overbought_fade_persists_after_zone_exit(self):
        values = [65.0, 72.0, 69.0, 66.0]
        states = classify_rsi_values(values)

        self.assertEqual(states[2].state, RsiState.FADING_OVERBOUGHT)
        self.assertEqual(states[3].state, RsiState.FADING_OVERBOUGHT)

    def test_continuation_states_inside_standard_zones(self):
        overbought = classify_rsi_values([69.0, 71.0])
        oversold = classify_rsi_values([31.0, 29.0])

        self.assertEqual(
            overbought[-1].state,
            RsiState.RECOVERING_OVERBOUGHT,
        )
        self.assertEqual(
            oversold[-1].state,
            RsiState.FADING_OVERSOLD,
        )

    def test_extremes_override_directional_step(self):
        high = classify_rsi_values([79.0, 82.0])
        low = classify_rsi_values([21.0, 18.0])

        self.assertEqual(high[-1].state, RsiState.EXTREME_OVERBOUGHT)
        self.assertEqual(low[-1].state, RsiState.EXTREME_OVERSOLD)

    def test_context_direction_boundaries(self):
        self.assertEqual(context_direction(None), 0)
        self.assertEqual(context_direction(47.99), -1)
        self.assertEqual(context_direction(48.0), -1)
        self.assertEqual(context_direction(50.0), 0)
        self.assertEqual(context_direction(52.0), 1)
        self.assertEqual(context_direction(80.0), 1)

    def test_context_gate_blocks_opposing_htf(self):
        self.assertTrue(supports(1, RsiState.BULL, 1))
        self.assertTrue(supports(1, RsiState.BULL, 0))
        self.assertFalse(supports(1, RsiState.BULL, -1))

        self.assertTrue(supports(-1, RsiState.BEAR, -1))
        self.assertTrue(supports(-1, RsiState.BEAR, 0))
        self.assertFalse(supports(-1, RsiState.BEAR, 1))

    def test_context_opposition_is_explicit(self):
        self.assertTrue(context_opposes(1, -1))
        self.assertFalse(context_opposes(1, 0))
        self.assertFalse(context_opposes(1, 1))

        self.assertTrue(opposes(1, RsiState.BULL, -1))
        self.assertTrue(opposes(-1, RsiState.BEAR, 1))

    def test_supportive_and_opposing_local_contract_matches_suite(self):
        self.assertTrue(local_supports(1, RsiState.RECOVERING_OVERSOLD))
        self.assertTrue(local_supports(1, RsiState.RECOVERING_OVERBOUGHT))
        self.assertTrue(local_supports(-1, RsiState.FADING_OVERBOUGHT))
        self.assertTrue(local_supports(-1, RsiState.FADING_OVERSOLD))

        self.assertTrue(local_opposes(1, RsiState.EXTREME_OVERBOUGHT))
        self.assertTrue(local_opposes(-1, RsiState.EXTREME_OVERSOLD))

    def test_invalid_context_direction_rejected(self):
        with self.assertRaises(ValueError):
            context_allows(1, 2)

        with self.assertRaises(ValueError):
            context_opposes(-1, -2)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
from __future__ import annotations

import unittest

from tools.execution_candidate_reference import (
    ExecutionResearchBar,
    calculate,
)
from tools.execution_state_reference import Location, Readiness


def make_trend_then_reversal(
    *,
    first_step: float,
    reversal_step: float,
    first_count: int = 80,
    reversal_count: int = 12,
    start: float = 100.0,
    direction_after_reversal: int,
) -> list[ExecutionResearchBar]:
    bars: list[ExecutionResearchBar] = []
    price = start

    for _ in range(first_count):
        open_ = price
        close = price + first_step
        bars.append(
            ExecutionResearchBar(
                open=open_,
                high=max(open_, close) + 0.40,
                low=min(open_, close) - 0.40,
                close=close,
                volume=100.0,
                map_dir=0,
                location=Location.OUTSIDE,
            )
        )
        price = close

    for i in range(reversal_count):
        open_ = price
        close = price + reversal_step

        location = (
            Location.APPROACHING
            if i == 0
            else Location.IN_CORRECTION
            if i == 1
            else Location.RECLAIM
            if i == 2
            else Location.OUTSIDE
        )

        volume = 130.0 if i == 2 else 100.0

        bars.append(
            ExecutionResearchBar(
                open=open_,
                high=max(open_, close) + 0.40,
                low=min(open_, close) - 0.40,
                close=close,
                volume=volume,
                map_dir=direction_after_reversal,
                location=location,
                rsi_context_dir=0,
            )
        )
        price = close

    return bars


class ExecutionCandidateReferenceTests(unittest.TestCase):
    def test_long_end_to_end_candidate_path_is_reachable(self):
        bars = make_trend_then_reversal(
            first_step=-0.25,
            reversal_step=0.40,
            direction_after_reversal=1,
            start=120.0,
        )

        samples = calculate(bars)

        prep = samples[80]
        armed = samples[81]
        confirmed = samples[82]
        aligned = samples[83]

        self.assertEqual(prep.result.state.readiness, Readiness.PREP)
        self.assertTrue(prep.result.events.preparing_entered)
        self.assertEqual(prep.momentum_state_name, "TURN_UP")
        self.assertEqual(prep.rsi_state_name, "EXTREME_OVERSOLD")

        self.assertEqual(armed.result.state.readiness, Readiness.ARMED)
        self.assertTrue(armed.result.events.armed_entered)
        self.assertEqual(armed.momentum_state_name, "TURN_UP")
        self.assertEqual(armed.rsi_state_name, "RECOVERING_OVERSOLD")

        self.assertEqual(
            confirmed.result.state.readiness,
            Readiness.CONFIRMED,
        )
        self.assertTrue(confirmed.result.events.confirm)
        self.assertEqual(confirmed.participation_state_name, "CONFIRM")
        self.assertGreaterEqual(confirmed.relative_volume, 1.20)

        self.assertEqual(aligned.result.state.readiness, Readiness.ALIGNED)
        self.assertFalse(aligned.result.events.confirm)

    def test_short_end_to_end_candidate_path_is_reachable(self):
        bars = make_trend_then_reversal(
            first_step=0.25,
            reversal_step=-0.40,
            direction_after_reversal=-1,
            start=100.0,
        )

        samples = calculate(bars)

        prep = samples[80]
        armed = samples[81]
        confirmed = samples[82]
        aligned = samples[83]

        self.assertEqual(prep.result.state.readiness, Readiness.PREP)
        self.assertTrue(prep.result.events.preparing_entered)
        self.assertEqual(prep.momentum_state_name, "TURN_DOWN")
        self.assertEqual(prep.rsi_state_name, "EXTREME_OVERBOUGHT")

        self.assertEqual(armed.result.state.readiness, Readiness.ARMED)
        self.assertTrue(armed.result.events.armed_entered)
        self.assertEqual(armed.momentum_state_name, "TURN_DOWN")
        self.assertEqual(armed.rsi_state_name, "FADING_OVERBOUGHT")

        self.assertEqual(
            confirmed.result.state.readiness,
            Readiness.CONFIRMED,
        )
        self.assertTrue(confirmed.result.events.confirm)
        self.assertEqual(confirmed.participation_state_name, "CONFIRM")

        self.assertEqual(aligned.result.state.readiness, Readiness.ALIGNED)

    def test_opposing_rsi_context_prevents_end_to_end_confirm(self):
        bars = make_trend_then_reversal(
            first_step=-0.25,
            reversal_step=0.40,
            direction_after_reversal=1,
            start=120.0,
        )

        bars = [
            bar
            if i < 80
            else ExecutionResearchBar(
                **{
                    **bar.__dict__,
                    "rsi_context_dir": -1,
                }
            )
            for i, bar in enumerate(bars)
        ]

        samples = calculate(bars)

        self.assertEqual(samples[80].result.state.readiness, Readiness.PREP)
        self.assertNotEqual(samples[81].result.state.readiness, Readiness.ARMED)
        self.assertFalse(any(sample.result.events.confirm for sample in samples))

    def test_unconfirmed_confirmation_bar_remains_armed(self):
        bars = make_trend_then_reversal(
            first_step=-0.25,
            reversal_step=0.40,
            direction_after_reversal=1,
            start=120.0,
        )

        original = bars[82]
        bars[82] = ExecutionResearchBar(
            **{
                **original.__dict__,
                "bar_confirmed": False,
            }
        )

        samples = calculate(bars)

        self.assertEqual(samples[81].result.state.readiness, Readiness.ARMED)
        self.assertEqual(samples[82].result.state.readiness, Readiness.ARMED)
        self.assertFalse(samples[82].result.events.confirm)


if __name__ == "__main__":
    unittest.main()

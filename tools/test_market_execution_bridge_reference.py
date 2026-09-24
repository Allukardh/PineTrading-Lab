#!/usr/bin/env python3
from __future__ import annotations

import unittest

from tools.execution_state_reference import Location
from tools.market_execution_bridge_reference import (
    APPROACH_ATR,
    EVENT_HOLD_BARS,
    BridgeMemory,
    MapEvidence,
    classify,
)


class MarketExecutionBridgeTests(unittest.TestCase):
    def ev(self, **kw):
        base = dict(
            bar_index=100,
            map_dir=1,
            atr=10.0,
            close=115.0,
            correction_active=True,
            t1_top=110.0,
            t1_bottom=106.0,
            primary_top=105.0,
            primary_bottom=100.0,
            t3_top=99.0,
            t3_bottom=95.0,
        )
        base.update(kw)
        return MapEvidence(**base)

    def test_inside_full_correction_envelope(self):
        for close in (109.0, 103.0, 97.0):
            r = classify(BridgeMemory(), self.ev(close=close))
            self.assertEqual(r.location, Location.IN_CORRECTION)

    def test_bull_approaching_only_from_impulse_side(self):
        r = classify(BridgeMemory(), self.ev(close=114.9))
        self.assertEqual(r.location, Location.APPROACHING)

        r = classify(BridgeMemory(), self.ev(close=115.1))
        self.assertEqual(r.location, Location.OUTSIDE)

        # Price already below the full correction envelope is not "approaching".
        r = classify(BridgeMemory(), self.ev(close=94.0))
        self.assertEqual(r.location, Location.OUTSIDE)

    def test_bear_approaching_only_from_impulse_side(self):
        e = self.ev(
            map_dir=-1,
            close=90.1,
            t1_top=105.0,
            t1_bottom=100.0,
            primary_top=110.0,
            primary_bottom=106.0,
            t3_top=115.0,
            t3_bottom=111.0,
        )
        r = classify(BridgeMemory(), e)
        self.assertEqual(r.location, Location.APPROACHING)

        r = classify(BridgeMemory(), MapEvidence(**{**e.__dict__, "close": 89.9}))
        self.assertEqual(r.location, Location.OUTSIDE)

    def test_reclaim_priority_and_hold_window(self):
        first = classify(BridgeMemory(), self.ev(close=103.0, reclaim_event=True))
        self.assertEqual(first.location, Location.RECLAIM)

        mem = first.memory
        for offset in range(1, EVENT_HOLD_BARS + 1):
            r = classify(mem, self.ev(bar_index=100 + offset, close=120.0))
            self.assertEqual(r.location, Location.RECLAIM)
            mem = r.memory

        r = classify(mem, self.ev(bar_index=100 + EVENT_HOLD_BARS + 1, close=120.0))
        self.assertEqual(r.location, Location.OUTSIDE)

    def test_retest_priority_below_reclaim(self):
        r = classify(
            BridgeMemory(),
            self.ev(close=103.0, retest_event=True, reclaim_event=True),
        )
        self.assertEqual(r.location, Location.RECLAIM)

    def test_direction_change_clears_event_memory(self):
        first = classify(BridgeMemory(), self.ev(reclaim_event=True))
        self.assertEqual(first.location, Location.RECLAIM)

        flipped = self.ev(
            bar_index=101,
            map_dir=-1,
            close=80.0,
            correction_active=False,
            reclaim_event=False,
        )
        r = classify(first.memory, flipped)
        self.assertNotEqual(r.location, Location.RECLAIM)
        self.assertEqual(r.memory.direction, -1)
        self.assertIsNone(r.memory.last_reclaim_bar)

    def test_invalid_map_clears_memory(self):
        mem = BridgeMemory(direction=1, last_reclaim_bar=99, last_retest_bar=98)

        cases = [
            self.ev(map_dir=0),
            self.ev(thesis_invalidated=True),
            self.ev(structural_conflict=True),
            self.ev(atr=None),
            self.ev(atr=0.0),
            self.ev(close=None),
        ]

        for e in cases:
            r = classify(mem, e)
            self.assertEqual(r.location, Location.OUTSIDE)
            self.assertEqual(r.memory, BridgeMemory())

    def test_destination_near_is_not_entry_location(self):
        r = classify(
            BridgeMemory(),
            self.ev(
                close=130.0,
                correction_active=False,
                destination_near=True,
            ),
        )
        self.assertEqual(r.location, Location.DESTINATION_NEAR)

    def test_correction_priority_over_destination_near(self):
        r = classify(
            BridgeMemory(),
            self.ev(close=103.0, destination_near=True),
        )
        self.assertEqual(r.location, Location.IN_CORRECTION)

    def test_malformed_envelope_falls_through(self):
        r = classify(
            BridgeMemory(),
            self.ev(
                t1_top=None,
                destination_near=True,
            ),
        )
        self.assertEqual(r.location, Location.DESTINATION_NEAR)

    def test_constants_are_product_defaults(self):
        self.assertEqual(APPROACH_ATR, 0.50)
        self.assertEqual(EVENT_HOLD_BARS, 3)


if __name__ == "__main__":
    unittest.main()

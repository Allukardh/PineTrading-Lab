#!/usr/bin/env python3
import math, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import market_map_offline_core as mm

class T(unittest.TestCase):

    def test_ema_rma(self):
        self.assertEqual(mm.ema([1.0, 2.0, 3.0, 4.0], 3), [1.0, 1.5, 2.25, 3.125])
        r = mm.rma([1.0, 2.0, 3.0, 4.0], 3)
        self.assertEqual(r[:2], [None, None])
        self.assertAlmostEqual(r[2], 2)
        self.assertAlmostEqual(r[3], 8 / 3)

    def test_adaptive(self):
        self.assertEqual(mm.adaptive([0.4, 0.45, 0.5, 0.55])[:2], (False, 0.5))
        ok, s, d = mm.adaptive([0.4, 0.45, 0.5, 0.55, 0.6])
        self.assertTrue(ok)
        self.assertAlmostEqual(s, 0.455)
        self.assertAlmostEqual(d, 0.545)

    def test_pivot_ties(self):
        self.assertEqual(mm.phigh([12, 10, 11, 12, 11, 10, 9], 6), 12)
        self.assertIsNone(mm.phigh([9, 10, 11, 12, 12, 10, 9], 6))
        self.assertEqual(mm.plow([8, 10, 9, 8, 9, 10, 11], 6), 8)
        self.assertIsNone(mm.plow([11, 10, 9, 8, 8, 10, 11], 6))

    def test_bucket(self):
        self.assertEqual(mm.bucket([0, 60, 120], 0), (0, None))
        self.assertEqual(mm.bucket([0, 60, 120], 60), (1, 0))
        self.assertEqual(mm.bucket([0, 60, 120], 119), (1, 0))

    def test_context_index_matches_pine_f_sec_contract(self):
        times = [0, 60, 120]
        self.assertIsNone(mm.context_index(times, 0, self_context=False))
        self.assertEqual(mm.context_index(times, 60, self_context=False), 0)
        self.assertEqual(mm.context_index(times, 60, self_context=True), 1)
        self.assertEqual(mm.context_index(times, 119, self_context=True), 1)

    def test_high_timeframe_level_policy(self):
        self.assertIn('1d', mm.DAY_LEVEL_TFS)
        self.assertNotIn('3d', mm.DAY_LEVEL_TFS)
        self.assertNotIn('1w', mm.DAY_LEVEL_TFS)
        self.assertIn('3d', mm.WEEK_LEVEL_TFS)
        self.assertIn('1w', mm.WEEK_LEVEL_TFS)
        self.assertEqual(mm.CONTEXT_TF['3d'], '3d')
        self.assertEqual(mm.CONTEXT_TF['1w'], '1w')

    def test_ambiguous_touch(self):
        t = mm.Tracker()
        t.start(1, 1)
        t.touch(5, 110)
        self.assertEqual(t.resolve(5, 111, 99, False), (False, False, True))

    def test_same_bar_long_target_can_be_ordered_from_open_and_zone(self):
        t = mm.Tracker()
        t.start(1, 1)
        t.touch(5, 110, open_value=99, zone_top=100, zone_bottom=95)
        self.assertEqual(t.resolve(5, 111, 96, False), (True, False, False))

    def test_same_bar_short_target_can_be_ordered_from_open_and_zone(self):
        t = mm.Tracker()
        t.start(1, -1)
        t.touch(5, 90, open_value=101, zone_top=105, zone_bottom=100)
        self.assertEqual(t.resolve(5, 104, 89, False), (True, False, False))

    def test_same_bar_target_remains_ambiguous_when_open_is_between_zone_and_target(self):
        t = mm.Tracker()
        t.start(1, 1)
        t.touch(5, 110, open_value=105, zone_top=100, zone_bottom=95)
        self.assertEqual(t.resolve(5, 111, 96, False), (False, False, True))

    def test_target_must_remain_beyond_current_zone(self):
        self.assertTrue(mm.usable_target(1, 110, 100, 95))
        self.assertFalse(mm.usable_target(1, 98, 100, 95))
        self.assertFalse(mm.usable_target(1, 90, 100, 95))
        self.assertTrue(mm.usable_target(-1, 90, 105, 100))
        self.assertFalse(mm.usable_target(-1, 102, 105, 100))
        self.assertFalse(mm.usable_target(-1, 110, 105, 100))

    def test_later_dest(self):
        t = mm.Tracker()
        t.start(1, 1)
        t.touch(5, 110)
        self.assertEqual(t.resolve(5, 109, 99, False), (False, False, False))
        self.assertEqual(t.resolve(6, 111, 99, False), (True, False, False))

    def test_superseded(self):
        t = mm.Tracker()
        t.start(1, 1)
        t.touch(5, 110)
        t.start(2, -1)
        self.assertEqual(t.superseded, 1)

    def test_acceptance(self):
        xs = [mm.Candle(i, 100 + i, 101 + i, 99 + i, 100 + i, 10) for i in range(10)]
        v, n, c = mm.acceptance(xs, 9, 2, 6, 100, 110, 0.01)
        self.assertEqual(c, 5)
        self.assertIsNotNone(v)
        self.assertIsNotNone(n)

    def test_contract_smoke(self):
        x = []
        for i in range(360):
            c = 100 + 0.06 * i + 4 * math.sin(i / 8) + 0.3 * math.sin(i / 3)
            x.append(mm.Candle(i * 900000000, c - 0.1, c + 0.8, c - 0.8, c, 1000 + i))
        ctx = x[::4]
        d = x[::96]
        w = [x[0], x[-1]]
        integration = []
        rows = mm.Kernel(x, ctx, d, w, '15m').run(integration_rows=integration)
        self.assertEqual(len(rows), len(x))
        self.assertEqual(len(integration), len(x))
        self.assertEqual(set(rows[0]), set(mm.AUDIT_HEADER))
        self.assertTrue(any((r['MM Audit • Nova tese evt'] == 1 for r in rows)))
        self.assertTrue(all(
            r['MM Audit • MapDir'] in (-1, 0, 1)
            and r['MM Audit • Modelo'] in (0, 1, 2, 3, 4)
            and 0 <= r['MM Audit • Confluências'] <= 6
            for r in rows
        ))
        for row, snap in zip(rows, integration):
            self.assertEqual(row['MM Audit • MapDir'], snap.map_dir)
            self.assertEqual(row['MM Audit • Correção topo'], snap.primary_top)
            self.assertEqual(row['MM Audit • Correção fundo'], snap.primary_bottom)
        active = next(s for s in integration if s.correction_active)
        self.assertIsNotNone(active.t1_top)
        self.assertIsNotNone(active.t1_bottom)
        self.assertIsNotNone(active.t3_top)
        self.assertIsNotNone(active.t3_bottom)
        self.assertGreaterEqual(active.t1_top, active.t1_bottom)
        self.assertGreaterEqual(active.t3_top, active.t3_bottom)

        # Research telemetry must only expose state already implied by the
        # accepted audit/kernel path and must remain internally coherent.
        for snap in integration:
            self.assertIn(snap.regime_dir, (-1, 0, 1))
            self.assertIn(snap.structure_dir, (-1, 0, 1))
            self.assertIn(snap.structural_break_dir, (-1, 0, 1))
            if snap.new_thesis_event:
                self.assertIsNotNone(snap.thesis_key)
            if snap.thesis_invalidated:
                self.assertIsNone(snap.destination)

    def test_execution_integration_constants_match_promoted_pine(self):
        self.assertEqual(mm.RETEST_MAX_BARS, 24)
        self.assertAlmostEqual(mm.RETEST_TOL_ATR, 0.18)
        self.assertAlmostEqual(mm.TARGET_NEAR_ATR, 0.30)


if __name__ == '__main__':
    unittest.main()

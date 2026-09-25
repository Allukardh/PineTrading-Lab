import unittest

from tools.market_map_offline_core import IntegrationSnapshot
from tools.range_rotation_reference import (
    RANGE_BOUNDARY_DRIFT_MAX,
    RANGE_EDGE_FRACTION,
    RANGE_MIN_HEIGHT_ATR,
    RangeOutcome,
    RangeTrigger,
    RegimeRelation,
    box_from_snapshot,
    boxes_compatible,
    classify_range_rotation,
    detect_range_rotations,
)


def snap(
    i,
    close=100.0,
    *,
    atr=10.0,
    ph=110.0,
    lh=111.0,
    pl=90.0,
    ll=89.0,
    phb=1,
    lhb=5,
    plb=2,
    llb=6,
    regime=0,
    upper_reclaim=None,
    lower_reclaim=None,
):
    return IntegrationSnapshot(
        bar_index=i,
        time=i * 1_000_000,
        map_dir=regime,
        atr=atr,
        close=close,
        correction_active=False,
        thesis_invalidated=False,
        structural_conflict=False,
        t1_top=None,
        t1_bottom=None,
        primary_top=None,
        primary_bottom=None,
        t3_top=None,
        t3_bottom=None,
        retest_event=False,
        reclaim_event=False,
        destination_near=False,
        regime_dir=regime,
        structure_dir=0,
        last_swing_high=lh,
        last_swing_high_bar=lhb,
        prev_swing_high=ph,
        prev_swing_high_bar=phb,
        last_swing_low=ll,
        last_swing_low_bar=llb,
        prev_swing_low=pl,
        prev_swing_low_bar=plb,
        raw_upper_reclaim_level=upper_reclaim,
        raw_lower_reclaim_level=lower_reclaim,
    )


class RangeRotationTests(unittest.TestCase):
    def test_range_box_requires_two_stable_cycles(self):
        b = box_from_snapshot(snap(10))
        self.assertIsNotNone(b)
        self.assertGreaterEqual(b.height_atr, RANGE_MIN_HEIGHT_ATR)
        self.assertLessEqual(b.boundary_drift_ratio, RANGE_BOUNDARY_DRIFT_MAX)
        self.assertAlmostEqual(b.edge_band, b.height * RANGE_EDGE_FRACTION)

        # Same-side pivots clustered before the second opposite-side visit are
        # not two completed range cycles.
        bad_order = snap(10, phb=1, lhb=2, plb=3, llb=6)
        self.assertIsNone(box_from_snapshot(bad_order))

        # Excessive boundary drift is not a stable range.
        drift = snap(10, ph=110.0, lh=118.0, pl=90.0, ll=89.0)
        self.assertIsNone(box_from_snapshot(drift))

    def test_compatible_new_pivots_preserve_range_identity(self):
        a = box_from_snapshot(snap(10))
        b = box_from_snapshot(
            snap(
                11,
                ph=110.5,
                lh=111.5,
                pl=89.5,
                ll=89.0,
                phb=5,
                lhb=9,
                plb=6,
                llb=10,
            )
        )
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertTrue(boxes_compatible(a, b))

    def test_lower_edge_rejection_creates_long_rotation(self):
        xs = [snap(i) for i in range(3)]
        highs = [100.0, 98.0, 100.0]
        lows = [95.0, 89.0, 95.0]
        closes = [98.0, 96.0, 98.0]

        eps = detect_range_rotations(xs, highs, lows, closes)
        self.assertEqual(len(eps), 1)
        e = eps[0]
        self.assertEqual(e.direction, 1)
        self.assertEqual(e.trigger, RangeTrigger.EDGE_REJECTION)
        self.assertEqual(e.regime_relation, RegimeRelation.NEUTRAL)

    def test_raw_reclaim_is_preserved_as_stronger_trigger(self):
        xs = [
            snap(0),
            snap(1, lower_reclaim=90.0),
        ]
        highs = [100.0, 94.0]
        lows = [95.0, 88.5]
        closes = [98.0, 92.0]
        eps = detect_range_rotations(xs, highs, lows, closes)
        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0].trigger, RangeTrigger.SWEEP_RECLAIM)

    def test_rotation_outcome_reaches_opposite_edge(self):
        xs = [snap(i) for i in range(4)]
        highs = [98.0, 101.0, 105.0, 108.0]
        lows = [89.0, 95.0, 98.0, 100.0]
        closes = [96.0, 100.0, 103.0, 107.0]
        e = detect_range_rotations(xs[:1], highs[:1], lows[:1], closes[:1])[0]
        out = classify_range_rotation(e, xs, highs, lows, closes)
        self.assertEqual(out.outcome, RangeOutcome.OPPOSITE_REACHED)
        self.assertIsNotNone(out.midpoint_bar)
        self.assertIsNotNone(out.opposite_bar)

    def test_rotation_can_fail_before_mid(self):
        xs = [snap(i) for i in range(3)]
        highs = [98.0, 96.0, 95.0]
        lows = [89.0, 88.0, 87.0]
        closes = [96.0, 88.0, 87.5]
        e = detect_range_rotations(xs[:1], highs[:1], lows[:1], closes[:1])[0]
        out = classify_range_rotation(e, xs, highs, lows, closes)
        self.assertEqual(out.outcome, RangeOutcome.FAILED_BEFORE_MID)


if __name__ == "__main__":
    unittest.main()

import unittest

from tools.breakout_acceptance_reference import (
    BreakoutAcceptance,
    DECISIVE_BREAK_ATR,
    follow_through_bar,
    immediate_accepts,
)
from tools.execution_state_reference import Participation
from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_candidate_features import CandidateFeatures
from tools.opportunity_episode_reference import OpportunityEpisode, OpportunityType


def features(**kw):
    base = dict(
        episode_id="b",
        opportunity_type="BREAKOUT_CANDIDATE",
        direction=1,
        bar_index=0,
        prior_regime_bars=None,
        break_penetration_atr=0.60,
        candle_body_direction_atr=1.0,
        candle_range_atr=1.4,
        close_location_directional=0.7,
        momentum_state="UP_ACCEL",
        mte_core_directional=0.5,
        mte_acceleration_directional=0.1,
        rsi_state="BULL",
        rsi_center_directional=15.0,
        rsi_step_directional=3.0,
        htf_context_alignment=1,
        participation_state=Participation.CONFIRM.name,
        relative_volume=1.4,
        directional_pressure=0.5,
        strong_volume_expansion=False,
        destination_room_atr=2.0,
        invalidation_distance_atr=3.0,
    )
    base.update(kw)
    return CandidateFeatures(**base)


def snap(i, close, *, level=100.0, fakeout=False, invalid=False):
    return IntegrationSnapshot(
        bar_index=i,
        time=i * 1_000_000,
        map_dir=1,
        atr=10.0,
        close=close,
        correction_active=False,
        thesis_invalidated=invalid,
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
        regime_dir=1,
        structure_dir=1,
        structural_break_dir=1 if i == 0 else 0,
        destination=130.0,
        invalidation=90.0,
        structural_break_level=level,
        fakeout_event=fakeout,
    )


class BreakoutAcceptanceTests(unittest.TestCase):
    def test_decisive_penetration_and_existing_engine_semantics(self):
        f = features()
        self.assertEqual(DECISIVE_BREAK_ATR, 0.50)
        self.assertTrue(immediate_accepts(BreakoutAcceptance.PENETRATION, f))
        self.assertTrue(immediate_accepts(BreakoutAcceptance.PENETRATION_PSE, f))
        self.assertTrue(immediate_accepts(BreakoutAcceptance.PENETRATION_MTE, f))
        self.assertTrue(immediate_accepts(BreakoutAcceptance.PENETRATION_PSE_MTE, f))

        weak = features(participation_state=Participation.WEAK.name)
        self.assertFalse(immediate_accepts(BreakoutAcceptance.PENETRATION_PSE, weak))

        shallow = features(break_penetration_atr=0.49)
        self.assertFalse(immediate_accepts(BreakoutAcceptance.PENETRATION, shallow))

    def test_follow_through_never_backdates(self):
        e = OpportunityEpisode(
            episode_id="b",
            opportunity_type=OpportunityType.BREAKOUT_CANDIDATE,
            direction=1,
            onset_bar=0,
            confirmation_bar=0,
            thesis_key=1,
            reference_price=105.0,
            atr=10.0,
            destination=130.0,
            invalidation=90.0,
        )
        snaps = [snap(0, 105.0), snap(1, 106.0), snap(2, 107.0)]
        closes = [105.0, 106.0, 107.0]
        self.assertEqual(follow_through_bar(e, snaps, closes, 1), 1)
        self.assertEqual(follow_through_bar(e, snaps, closes, 2), 2)

    def test_follow_through_rejects_failed_hold_or_fakeout(self):
        e = OpportunityEpisode(
            episode_id="b",
            opportunity_type=OpportunityType.BREAKOUT_CANDIDATE,
            direction=1,
            onset_bar=0,
            confirmation_bar=0,
            thesis_key=1,
            reference_price=105.0,
            atr=10.0,
            destination=130.0,
            invalidation=90.0,
        )
        failed = [snap(0, 105.0), snap(1, 99.0), snap(2, 107.0)]
        self.assertIsNone(follow_through_bar(e, failed, [105.0, 99.0, 107.0], 1))

        fake = [snap(0, 105.0), snap(1, 106.0, fakeout=True), snap(2, 107.0)]
        self.assertIsNone(follow_through_bar(e, fake, [105.0, 106.0, 107.0], 1))


if __name__ == "__main__":
    unittest.main()

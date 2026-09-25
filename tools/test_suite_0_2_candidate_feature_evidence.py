import unittest

from tools.market_map_offline_core import IntegrationSnapshot
from tools.momentum_turn_reference import Momentum, MomentumSample
from tools.opportunity_candidate_features import extract_features
from tools.opportunity_episode_reference import OpportunityEpisode, OpportunityType
from tools.participation_reference import Participation, ParticipationSample
from tools.rsi_state_reference import RsiSample
from tools.execution_state_reference import RsiState
from tools.suite_0_2_candidate_feature_evidence import _auc


class CandidateFeatureEvidenceTests(unittest.TestCase):
    def test_auc_orientation_math(self):
        self.assertAlmostEqual(_auc([3, 4, 5], [0, 1, 2]), 1.0)
        self.assertAlmostEqual(_auc([0, 1, 2], [3, 4, 5]), 0.0)
        self.assertAlmostEqual(_auc([1, 1], [1, 1]), 0.5)
        self.assertIsNone(_auc([], [1]))

    def test_feature_extraction_is_direction_normalized(self):
        snap = IntegrationSnapshot(
            bar_index=0,
            time=0,
            map_dir=0,
            atr=10.0,
            close=90.0,
            correction_active=False,
            thesis_invalidated=False,
            structural_conflict=True,
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
            structure_dir=-1,
            structural_break_dir=-1,
            destination=80.0,
            invalidation=105.0,
            structural_break_level=95.0,
        )
        episode = OpportunityEpisode(
            episode_id="x",
            opportunity_type=OpportunityType.REGIME_TRANSITION_CANDIDATE,
            direction=-1,
            onset_bar=0,
            confirmation_bar=0,
            thesis_key=None,
            reference_price=90.0,
            atr=10.0,
            destination=80.0,
            invalidation=105.0,
            prior_regime_bars=20,
        )
        momentum = [
            MomentumSample(
                ready=True,
                core=-0.5,
                acceleration=-0.1,
                neutral_band=0.1,
                turn_band=0.05,
                state=Momentum.DOWN_ACCEL,
            )
        ]
        rsi = [
            RsiSample(
                ready=True,
                value=40.0,
                step=-2.0,
                state=RsiState.BEAR,
            )
        ]
        pse = [
            ParticipationSample(
                ready=True,
                relative_volume=1.4,
                pressure_proxy=-0.75,
                directional_pressure=0.75,
                strong_expansion=False,
                state=Participation.CONFIRM,
            )
        ]
        f = extract_features(
            episode,
            [snap],
            [100.0],
            [101.0],
            [89.0],
            [90.0],
            momentum,
            rsi,
            pse,
            [-1],
        )
        self.assertAlmostEqual(f.break_penetration_atr, 0.5)
        self.assertAlmostEqual(f.candle_body_direction_atr, 1.0)
        self.assertAlmostEqual(f.close_location_directional, 5.0 / 6.0)
        self.assertAlmostEqual(f.mte_core_directional, 0.5)
        self.assertAlmostEqual(f.mte_acceleration_directional, 0.1)
        self.assertAlmostEqual(f.rsi_center_directional, 10.0)
        self.assertAlmostEqual(f.rsi_step_directional, 2.0)
        self.assertEqual(f.htf_context_alignment, 1)
        self.assertAlmostEqual(f.directional_pressure, 0.75)
        self.assertEqual(f.prior_regime_bars, 20)


if __name__ == "__main__":
    unittest.main()

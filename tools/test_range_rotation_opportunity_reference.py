import unittest

from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_execution_counterfactual import OpportunityStage
from tools.range_rotation_opportunity_reference import (
    RangeIntegrationVariant,
    actionable,
    ambiguous_source_bars,
    build_range_opportunity_frames,
)
from tools.range_rotation_reference import (
    RangeRotationEpisode,
    RangeTrigger,
    RegimeRelation,
)


def snap(i, close=100.0, *, atr=10.0):
    return IntegrationSnapshot(
        bar_index=i,
        time=i * 1_000_000,
        map_dir=0,
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
        regime_dir=0,
        structure_dir=0,
        last_swing_high=111.0,
        last_swing_high_bar=5,
        prev_swing_high=110.5,
        prev_swing_high_bar=1,
        last_swing_low=89.0,
        last_swing_low_bar=6,
        prev_swing_low=89.5,
        prev_swing_low_bar=2,
    )


def episode(
    *,
    direction=1,
    bar=0,
    relation=RegimeRelation.NEUTRAL,
    trigger=RangeTrigger.EDGE_REJECTION,
):
    return RangeRotationEpisode(
        episode_id=f"rr:{direction}:{bar}:{relation.value}",
        direction=direction,
        confirmation_bar=bar,
        range_key=(1, 5, 2, 6),
        range_high=110.75,
        range_low=89.25,
        range_mid=100.0,
        edge_band=4.3,
        height_atr=2.15,
        boundary_drift_ratio=0.05,
        trigger=trigger,
        regime_relation=relation,
        reference_price=95.0 if direction == 1 else 105.0,
        atr=10.0,
    )


class RangeOpportunityFrameTests(unittest.TestCase):
    def test_edge_rejection_starts_strong_then_accepts_on_progress(self):
        eps = [episode(direction=1, bar=0)]
        xs = [snap(0, 95.0), snap(1, 97.0), snap(2, 99.0)]
        frames = build_range_opportunity_frames(
            eps,
            xs,
            highs=[98.0, 99.0, 101.0],
            lows=[91.0, 94.0, 96.0],
            closes=[95.0, 97.0, 99.0],
            variant=RangeIntegrationVariant.ALL_EDGE,
        )
        self.assertEqual(frames[0].stage, OpportunityStage.STRONG)
        self.assertEqual(frames[1].stage, OpportunityStage.ACCEPTED)
        self.assertEqual(frames[2].stage, OpportunityStage.ACCEPTED)

    def test_no_next_bar_progress_kills_frame(self):
        eps = [episode(direction=1, bar=0)]
        xs = [snap(0, 95.0), snap(1, 94.0), snap(2, 97.0)]
        frames = build_range_opportunity_frames(
            eps,
            xs,
            highs=[98.0, 97.0, 99.0],
            lows=[91.0, 92.0, 94.0],
            closes=[95.0, 94.0, 97.0],
            variant=RangeIntegrationVariant.ALL_EDGE,
        )
        self.assertEqual(frames[0].stage, OpportunityStage.STRONG)
        self.assertEqual(frames[1].stage, OpportunityStage.NONE)
        self.assertEqual(frames[2].stage, OpportunityStage.NONE)

    def test_opposite_edge_arrival_clears_before_late_confirmation(self):
        eps = [episode(direction=1, bar=0)]
        xs = [snap(0, 95.0), snap(1, 97.0), snap(2, 105.0)]
        frames = build_range_opportunity_frames(
            eps,
            xs,
            highs=[98.0, 99.0, 107.0],
            lows=[91.0, 94.0, 100.0],
            closes=[95.0, 97.0, 105.0],
            variant=RangeIntegrationVariant.ALL_EDGE,
        )
        self.assertEqual(frames[1].stage, OpportunityStage.ACCEPTED)
        self.assertEqual(frames[2].stage, OpportunityStage.NONE)

    def test_context_guarded_keeps_against_regime_awareness_only(self):
        against = episode(
            direction=1,
            relation=RegimeRelation.AGAINST_REGIME,
        )
        self.assertTrue(actionable(against, RangeIntegrationVariant.ALL_EDGE))
        self.assertFalse(
            actionable(against, RangeIntegrationVariant.CONTEXT_GUARDED)
        )

        xs = [snap(0, 95.0), snap(1, 97.0)]
        frames = build_range_opportunity_frames(
            [against],
            xs,
            highs=[98.0, 99.0],
            lows=[91.0, 94.0],
            closes=[95.0, 97.0],
            variant=RangeIntegrationVariant.CONTEXT_GUARDED,
        )
        self.assertTrue(all(f.stage == OpportunityStage.NONE for f in frames))

    def test_raw_sweep_reclaim_is_not_actionable(self):
        e = episode(trigger=RangeTrigger.SWEEP_RECLAIM)
        self.assertFalse(actionable(e, RangeIntegrationVariant.ALL_EDGE))

    def test_opposing_same_bar_sources_are_ambiguous(self):
        eps = [
            episode(direction=1, bar=0),
            episode(direction=-1, bar=0),
        ]
        self.assertEqual(
            ambiguous_source_bars(
                eps,
                variant=RangeIntegrationVariant.ALL_EDGE,
            ),
            1,
        )
        xs = [snap(0, 100.0)]
        frames = build_range_opportunity_frames(
            eps,
            xs,
            highs=[110.0],
            lows=[90.0],
            closes=[100.0],
            variant=RangeIntegrationVariant.ALL_EDGE,
        )
        self.assertEqual(frames[0].stage, OpportunityStage.NONE)


if __name__ == "__main__":
    unittest.main()

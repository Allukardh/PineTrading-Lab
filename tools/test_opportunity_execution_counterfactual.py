import unittest

from tools.execution_state_reference import Location, Participation
from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_episode_reference import (
    BreakContext,
    OpportunityEpisode,
    OpportunityType,
)
from tools.opportunity_execution_counterfactual import (
    OpportunityKind,
    OpportunityStage,
    build_opportunity_frames,
    project_for_state_machine,
)
from tools.participation_reference import ParticipationSample


def snap(i, close, *, break_level=None, map_dir=1, fakeout=False, dest_near=False):
    return IntegrationSnapshot(
        bar_index=i,
        time=i * 1_000_000,
        map_dir=map_dir,
        atr=10.0,
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
        destination_near=dest_near,
        regime_dir=map_dir,
        structure_dir=map_dir,
        structural_break_dir=1 if break_level is not None else 0,
        fakeout_event=fakeout,
        structural_break_level=break_level,
    )


def pse(state):
    return ParticipationSample(
        ready=True,
        relative_volume=1.4,
        pressure_proxy=0.5,
        directional_pressure=0.5,
        strong_expansion=False,
        state=state,
    )


def episode(kind, bar=0, context=None):
    return OpportunityEpisode(
        episode_id=f"{kind.value}:+1:{bar}",
        opportunity_type=kind,
        direction=1,
        onset_bar=bar,
        confirmation_bar=bar,
        thesis_key=1,
        reference_price=105.0,
        atr=10.0,
        destination=130.0,
        invalidation=90.0,
        break_context=context,
    )


class OpportunityCounterfactualTests(unittest.TestCase):
    def test_strong_breakout_progresses_candidate_strong_accepted(self):
        xs = [
            snap(0, 106.0, break_level=100.0),
            snap(1, 107.0),
            snap(2, 108.0),
            snap(3, 109.0),
        ]
        eps = [
            episode(
                OpportunityType.BREAKOUT_CANDIDATE,
                context=BreakContext.FRESH_EXPANSION.value,
            )
        ]
        frames = build_opportunity_frames(
            eps,
            xs,
            [x.close for x in xs],
            [Location.OUTSIDE] * len(xs),
            [pse(Participation.CONFIRM)] + [pse(Participation.NEUTRAL)] * 3,
        )
        self.assertEqual(frames[0].stage, OpportunityStage.CANDIDATE)
        self.assertEqual(frames[1].stage, OpportunityStage.STRONG)
        self.assertEqual(frames[2].stage, OpportunityStage.ACCEPTED)
        self.assertEqual(frames[3].stage, OpportunityStage.ACCEPTED)
        self.assertEqual(frames[0].kind, OpportunityKind.BREAKOUT_EXPANSION)

    def test_non_strong_breakout_waits_for_two_close_acceptance(self):
        xs = [
            snap(0, 106.0, break_level=100.0),
            snap(1, 107.0),
            snap(2, 108.0),
        ]
        eps = [
            episode(
                OpportunityType.BREAKOUT_CANDIDATE,
                context=BreakContext.OTHER.value,
            )
        ]
        frames = build_opportunity_frames(
            eps,
            xs,
            [x.close for x in xs],
            [Location.OUTSIDE] * len(xs),
            [pse(Participation.NEUTRAL)] * 3,
        )
        self.assertEqual(frames[0].stage, OpportunityStage.CANDIDATE)
        self.assertEqual(frames[1].stage, OpportunityStage.CANDIDATE)
        self.assertEqual(frames[2].stage, OpportunityStage.ACCEPTED)

    def test_failed_hold_kills_breakout_opportunity(self):
        xs = [
            snap(0, 106.0, break_level=100.0),
            snap(1, 99.0),
            snap(2, 108.0),
        ]
        eps = [
            episode(
                OpportunityType.BREAKOUT_CANDIDATE,
                context=BreakContext.OTHER.value,
            )
        ]
        frames = build_opportunity_frames(
            eps,
            xs,
            [x.close for x in xs],
            [Location.OUTSIDE] * len(xs),
            [pse(Participation.CONFIRM)] * 3,
        )
        self.assertEqual(frames[0].stage, OpportunityStage.CANDIDATE)
        self.assertEqual(frames[1].stage, OpportunityStage.NONE)
        self.assertEqual(frames[2].stage, OpportunityStage.NONE)

    def test_reacceleration_has_specific_kind(self):
        xs = [
            snap(0, 106.0, break_level=100.0),
            snap(1, 107.0),
            snap(2, 108.0),
        ]
        eps = [episode(OpportunityType.REACCELERATION)]
        frames = build_opportunity_frames(
            eps,
            xs,
            [x.close for x in xs],
            [Location.OUTSIDE] * 3,
            [pse(Participation.CONFIRM)] * 3,
        )
        self.assertEqual(frames[0].kind, OpportunityKind.REACCELERATION)
        self.assertEqual(frames[2].stage, OpportunityStage.ACCEPTED)

    def test_strict_regime_reversal_starts_accepted(self):
        xs = [snap(0, 106.0), snap(1, 107.0), snap(2, 108.0)]
        eps = [episode(OpportunityType.REGIME_REVERSAL)]
        frames = build_opportunity_frames(
            eps,
            xs,
            [x.close for x in xs],
            [Location.OUTSIDE] * 3,
            [pse(Participation.NEUTRAL)] * 3,
        )
        self.assertEqual(frames[0].kind, OpportunityKind.REGIME_REVERSAL)
        self.assertEqual(frames[0].stage, OpportunityStage.ACCEPTED)
        self.assertEqual(frames[2].stage, OpportunityStage.ACCEPTED)

    def test_baseline_relevant_location_terminates_overlay(self):
        xs = [snap(0, 106.0, break_level=100.0), snap(1, 107.0), snap(2, 108.0)]
        eps = [
            episode(
                OpportunityType.BREAKOUT_CANDIDATE,
                context=BreakContext.OTHER.value,
            )
        ]
        frames = build_opportunity_frames(
            eps,
            xs,
            [x.close for x in xs],
            [Location.OUTSIDE, Location.RETEST, Location.OUTSIDE],
            [pse(Participation.CONFIRM)] * 3,
        )
        self.assertEqual(frames[0].stage, OpportunityStage.CANDIDATE)
        self.assertEqual(frames[1].stage, OpportunityStage.NONE)

    def test_projection_blocks_premature_confirm_without_hiding_contrary(self):
        candidate = type("F", (), {})()
        # Use the real immutable frame for the actual calls.
        from tools.opportunity_execution_counterfactual import OpportunityFrame
        frame = OpportunityFrame(
            OpportunityKind.REACCELERATION,
            OpportunityStage.STRONG,
            1,
            10,
            100.0,
        )
        loc, part, overlay = project_for_state_machine(
            Location.OUTSIDE,
            frame,
            Participation.CONFIRM,
        )
        self.assertTrue(overlay)
        self.assertEqual(loc, Location.APPROACHING)
        self.assertEqual(part, Participation.NEUTRAL)

        _, part2, _ = project_for_state_machine(
            Location.OUTSIDE,
            frame,
            Participation.CONTRARY,
        )
        self.assertEqual(part2, Participation.CONTRARY)

        accepted = OpportunityFrame(
            OpportunityKind.REACCELERATION,
            OpportunityStage.ACCEPTED,
            1,
            10,
            100.0,
        )
        _, part3, _ = project_for_state_machine(
            Location.OUTSIDE,
            accepted,
            Participation.CONFIRM,
        )
        self.assertEqual(part3, Participation.CONFIRM)

    def test_existing_0_1_location_has_priority(self):
        from tools.opportunity_execution_counterfactual import OpportunityFrame
        frame = OpportunityFrame(
            OpportunityKind.BREAKOUT_EXPANSION,
            OpportunityStage.ACCEPTED,
            1,
            10,
            100.0,
        )
        loc, part, overlay = project_for_state_machine(
            Location.RECLAIM,
            frame,
            Participation.CONFIRM,
        )
        self.assertFalse(overlay)
        self.assertEqual(loc, Location.RECLAIM)
        self.assertEqual(part, Participation.CONFIRM)


if __name__ == "__main__":
    unittest.main()

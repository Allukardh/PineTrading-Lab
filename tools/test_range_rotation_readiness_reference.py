import unittest

from tools.execution_state_reference import Momentum, Participation, Readiness, RsiState, State
from tools.opportunity_execution_counterfactual import OpportunityFrame, OpportunityKind, OpportunityStage
from tools.range_rotation_readiness_reference import (
    RangeReadinessVariant,
    step_range_readiness,
)


def frame(stage, source=10, direction=1):
    return OpportunityFrame(
        kind=OpportunityKind.RANGE_ROTATION,
        stage=stage,
        direction=direction,
        source_bar=source,
    )


class RangeReadinessVariantTests(unittest.TestCase):
    def test_early_any1_arms_with_one_source_family(self):
        r=step_range_readiness(
            State(),frame(OpportunityStage.STRONG),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.NEUTRAL,
            rsi_context_dir=-1,
            participation=Participation.WEAK,
            variant=RangeReadinessVariant.EARLY_ANY1,
        )
        self.assertEqual(r.state.readiness,Readiness.ARMED)
        self.assertTrue(r.events.armed_entered)

    def test_selective_any2_prepares_with_one_and_arms_with_two(self):
        one=step_range_readiness(
            State(),frame(OpportunityStage.STRONG),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.NEUTRAL,
            rsi_context_dir=-1,
            participation=Participation.WEAK,
            variant=RangeReadinessVariant.SELECTIVE_ANY2,
        )
        self.assertEqual(one.state.readiness,Readiness.PREP)

        two=step_range_readiness(
            State(),frame(OpportunityStage.STRONG),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=-1,
            participation=Participation.WEAK,
            variant=RangeReadinessVariant.SELECTIVE_ANY2,
        )
        self.assertEqual(two.state.readiness,Readiness.ARMED)

    def test_dual_opposition_blocks_even_with_pse_confirm(self):
        r=step_range_readiness(
            State(),frame(OpportunityStage.STRONG),
            momentum=Momentum.DOWN_ACCEL,
            rsi=RsiState.BEAR,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
            variant=RangeReadinessVariant.EARLY_ANY1,
        )
        self.assertEqual(r.state.readiness,Readiness.WAIT)
        self.assertFalse(r.events.armed_entered)

    def test_accepted_confirms_already_armed_even_with_htf_opposition(self):
        r=step_range_readiness(
            State(Readiness.ARMED,1),frame(OpportunityStage.ACCEPTED),
            momentum=Momentum.NEUTRAL,
            rsi=RsiState.BEAR,
            rsi_context_dir=-1,
            participation=Participation.WEAK,
            variant=RangeReadinessVariant.EARLY_ANY1,
        )
        self.assertEqual(r.state.readiness,Readiness.CONFIRMED)
        self.assertTrue(r.events.confirm)

    def test_selective_prep_is_not_promoted_late_on_acceptance(self):
        r=step_range_readiness(
            State(Readiness.PREP,1),frame(OpportunityStage.ACCEPTED),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
            variant=RangeReadinessVariant.SELECTIVE_ANY2,
        )
        self.assertEqual(r.state.readiness,Readiness.PREP)
        self.assertFalse(r.events.confirm)
        self.assertFalse(r.events.armed_entered)

    def test_source_reset_cancels_old_and_arms_new(self):
        r=step_range_readiness(
            State(Readiness.ALIGNED,1),frame(OpportunityStage.STRONG,source=20),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.NEUTRAL,
            rsi_context_dir=0,
            participation=Participation.WEAK,
            variant=RangeReadinessVariant.EARLY_ANY1,
            source_reset=True,
        )
        self.assertEqual(r.state.readiness,Readiness.ARMED)
        self.assertTrue(r.events.canceled)
        self.assertTrue(r.events.armed_entered)


if __name__=="__main__":
    unittest.main()

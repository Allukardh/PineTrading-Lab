import unittest

from tools.execution_state_reference import (
    Momentum,
    Participation,
    Readiness,
    RsiState,
    State,
)
from tools.opportunity_execution_counterfactual import (
    OpportunityFrame,
    OpportunityKind,
    OpportunityStage,
)
from tools.opportunity_readiness_reference import step_opportunity


def frame(stage, direction=1):
    return OpportunityFrame(
        kind=OpportunityKind.BREAKOUT_EXPANSION,
        stage=stage,
        direction=direction,
        source_bar=10,
        break_level=100.0,
    )


class OpportunityReadinessTests(unittest.TestCase):
    def test_candidate_is_preparation_only(self):
        r1 = step_opportunity(
            State(),
            frame(OpportunityStage.CANDIDATE),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(r1.state.readiness, Readiness.PREP)
        self.assertTrue(r1.events.preparing_entered)

        r2 = step_opportunity(
            r1.state,
            frame(OpportunityStage.CANDIDATE),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(r2.state.readiness, Readiness.PREP)
        self.assertFalse(r2.events.armed_entered)
        self.assertFalse(r2.events.confirm)

    def test_strong_can_arm_but_not_confirm(self):
        prep = State(Readiness.PREP, 1)
        armed = step_opportunity(
            prep,
            frame(OpportunityStage.STRONG),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(armed.state.readiness, Readiness.ARMED)
        self.assertTrue(armed.events.armed_entered)

        still_armed = step_opportunity(
            armed.state,
            frame(OpportunityStage.STRONG),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(still_armed.state.readiness, Readiness.ARMED)
        self.assertFalse(still_armed.events.confirm)

    def test_accepted_is_required_for_confirm(self):
        armed = State(Readiness.ARMED, 1)
        r = step_opportunity(
            armed,
            frame(OpportunityStage.ACCEPTED),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(r.state.readiness, Readiness.CONFIRMED)
        self.assertTrue(r.events.confirm)

    def test_missing_frame_cancels_only_opportunity_state(self):
        armed = State(Readiness.ARMED, 1)
        r = step_opportunity(
            armed,
            OpportunityFrame(),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(r.state.readiness, Readiness.WAIT)
        self.assertTrue(r.events.canceled)

    def test_direction_change_resets_before_new_setup(self):
        armed = State(Readiness.ARMED, 1)
        r = step_opportunity(
            armed,
            frame(OpportunityStage.ACCEPTED, direction=-1),
            momentum=Momentum.DOWN_ACCEL,
            rsi=RsiState.BEAR,
            rsi_context_dir=-1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(r.state.readiness, Readiness.WAIT)
        self.assertEqual(r.state.direction, 0)
        self.assertTrue(r.events.canceled)


if __name__ == "__main__":
    unittest.main()

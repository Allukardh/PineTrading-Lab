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
    def test_candidate_is_awareness_only(self):
        r = step_opportunity(
            State(),
            frame(OpportunityStage.CANDIDATE),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(r.state.readiness, Readiness.WAIT)
        self.assertFalse(r.events.preparing_entered)
        self.assertFalse(r.events.armed_entered)
        self.assertFalse(r.events.confirm)

    def test_strong_prepares_then_can_arm_but_not_confirm(self):
        prep = step_opportunity(
            State(),
            frame(OpportunityStage.STRONG),
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(prep.state.readiness, Readiness.PREP)
        self.assertTrue(prep.events.preparing_entered)

        armed = step_opportunity(
            prep.state,
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

    def test_accepted_can_arm_directly_after_follow_through(self):
        r = step_opportunity(
            State(),
            frame(OpportunityStage.ACCEPTED),
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.NEUTRAL,
        )
        self.assertEqual(r.state.readiness, Readiness.ARMED)
        self.assertTrue(r.events.armed_entered)

    def test_accepted_can_confirm_from_remembered_strong_source(self):
        strong = OpportunityFrame(
            kind=OpportunityKind.BREAKOUT_EXPANSION,
            stage=OpportunityStage.ACCEPTED,
            direction=1,
            source_bar=10,
            break_level=100.0,
            source_strong=True,
        )
        r = step_opportunity(
            State(Readiness.ARMED, 1),
            strong,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.NEUTRAL,
        )
        self.assertEqual(r.state.readiness, Readiness.CONFIRMED)
        self.assertTrue(r.events.confirm)

    def test_non_strong_accepted_still_needs_current_participation(self):
        r = step_opportunity(
            State(Readiness.ARMED, 1),
            frame(OpportunityStage.ACCEPTED),
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.NEUTRAL,
        )
        self.assertEqual(r.state.readiness, Readiness.ARMED)
        self.assertFalse(r.events.confirm)

        r2 = step_opportunity(
            r.state,
            frame(OpportunityStage.ACCEPTED),
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.BULL,
            rsi_context_dir=1,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(r2.state.readiness, Readiness.CONFIRMED)
        self.assertTrue(r2.events.confirm)

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

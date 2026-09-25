import unittest

from tools.execution_state_reference import Momentum, Participation, RsiState
from tools.thesis_management_reference import (
    ManagementState,
    classify_management_v1_bar,
)


class ThesisManagementV1Tests(unittest.TestCase):
    def classify(self, **kw):
        args=dict(
            direction=1,
            high=105.0,
            low=99.0,
            close=103.0,
            atr=10.0,
            target=110.0,
            invalidation=90.0,
            path_progress=0.30,
            momentum=Momentum.UP_ACCEL,
            rsi=RsiState.BULL,
            participation=Participation.CONFIRM,
            structural_warning=False,
        )
        args.update(kw)
        return classify_management_v1_bar(**args)

    def test_structural_warning_alone_is_diagnostic_only(self):
        x=self.classify(
            structural_warning=True,
            momentum=Momentum.NEUTRAL,
            rsi=RsiState.NEUTRAL,
            participation=Participation.NEUTRAL,
        )
        self.assertEqual(x.state,ManagementState.CONTINUATION)
        self.assertTrue(x.structural_warning)

    def test_exhausted_before_midpoint_means_protect(self):
        x=self.classify(
            path_progress=0.30,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.FADING_OVERBOUGHT,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(x.state,ManagementState.PROTECT)

    def test_fading_after_midpoint_means_realization_risk(self):
        x=self.classify(
            path_progress=0.50,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.BULL,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(x.state,ManagementState.REALIZATION_RISK)

    def test_fading_before_midpoint_stays_continuation(self):
        x=self.classify(
            path_progress=0.49,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.BULL,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(x.state,ManagementState.CONTINUATION)

    def test_exhausted_after_midpoint_is_realization_not_protect(self):
        x=self.classify(
            path_progress=0.75,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.FADING_OVERBOUGHT,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(x.state,ManagementState.REALIZATION_RISK)

    def test_invalidation_near_has_precedence_over_favorable_maturity(self):
        x=self.classify(
            close=91.5,
            high=93.0,
            low=91.0,
            path_progress=0.75,
            target=110.0,
            invalidation=90.0,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.FADING_OVERBOUGHT,
            participation=Participation.CONFIRM,
        )
        self.assertTrue(x.invalidation_near)
        self.assertEqual(x.state,ManagementState.PROTECT)

    def test_existing_destination_near_reaction_risk_remains_realization(self):
        x=self.classify(
            close=107.5,
            high=108.0,
            path_progress=0.10,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.FADING_OVERBOUGHT,
            participation=Participation.CONFIRM,
        )
        self.assertTrue(x.target_near)
        self.assertEqual(x.state,ManagementState.REALIZATION_RISK)

    def test_terminal_states_keep_precedence(self):
        completed=self.classify(high=111.0,path_progress=0.9)
        self.assertEqual(completed.state,ManagementState.COMPLETED)

        invalid=self.classify(low=88.0,close=89.0,path_progress=-1.0)
        self.assertEqual(invalid.state,ManagementState.INVALIDATED)

        ambiguous=self.classify(high=111.0,low=88.0,close=89.0,path_progress=0.9)
        self.assertEqual(ambiguous.state,ManagementState.AMBIGUOUS)


if __name__=="__main__":
    unittest.main()

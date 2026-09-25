import unittest

from tools.execution_state_reference import Momentum, Participation, RsiState, Strength
from tools.thesis_management_reference import (
    INVALID_WARN_ATR,
    TARGET_NEAR_ATR,
    ManagementState,
    classify_management_bar,
)


class ThesisManagementV0Tests(unittest.TestCase):
    def classify(
        self,
        *,
        direction=1,
        high=105.0,
        low=99.0,
        close=103.0,
        atr=10.0,
        target=110.0,
        invalidation=90.0,
        momentum=Momentum.UP_ACCEL,
        rsi=RsiState.BULL,
        participation=Participation.CONFIRM,
        structural_warning=False,
    ):
        return classify_management_bar(
            direction=direction,
            high=high,
            low=low,
            close=close,
            atr=atr,
            target=target,
            invalidation=invalidation,
            momentum=momentum,
            rsi=rsi,
            participation=participation,
            structural_warning=structural_warning,
        )

    def test_clean_thesis_is_continuation(self):
        x=self.classify()
        self.assertEqual(x.state,ManagementState.CONTINUATION)
        self.assertEqual(x.strength,Strength.NORMAL)

    def test_destination_near_requires_multi_family_deterioration_for_realization(self):
        self.assertEqual(TARGET_NEAR_ATR,0.30)
        one=self.classify(
            close=107.5,
            high=108.0,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.BULL,
            participation=Participation.CONFIRM,
        )
        self.assertTrue(one.target_near)
        self.assertEqual(one.strength,Strength.FADING)
        self.assertEqual(one.state,ManagementState.CONTINUATION)

        two=self.classify(
            close=107.5,
            high=108.0,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.FADING_OVERBOUGHT,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(two.strength,Strength.REACTION_RISK)
        self.assertEqual(two.state,ManagementState.REALIZATION_RISK)

    def test_generic_exhaustion_means_protect(self):
        x=self.classify(
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.FADING_OVERBOUGHT,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(x.strength,Strength.EXHAUSTED)
        self.assertEqual(x.state,ManagementState.PROTECT)

    def test_fading_alone_remains_diagnostic(self):
        x=self.classify(momentum=Momentum.UP_DECEL)
        self.assertEqual(x.strength,Strength.FADING)
        self.assertEqual(x.state,ManagementState.CONTINUATION)

    def test_invalidation_near_means_protect(self):
        self.assertEqual(INVALID_WARN_ATR,0.20)
        x=self.classify(
            close=91.5,
            high=93.0,
            low=91.0,
            target=110.0,
            invalidation=90.0,
            momentum=Momentum.NEUTRAL,
            rsi=RsiState.NEUTRAL,
            participation=Participation.NEUTRAL,
        )
        self.assertTrue(x.invalidation_near)
        self.assertEqual(x.state,ManagementState.PROTECT)

    def test_structural_warning_means_protect(self):
        x=self.classify(
            momentum=Momentum.NEUTRAL,
            rsi=RsiState.NEUTRAL,
            participation=Participation.NEUTRAL,
            structural_warning=True,
        )
        self.assertEqual(x.state,ManagementState.PROTECT)

    def test_target_completion_has_terminal_precedence(self):
        x=self.classify(high=111.0,close=108.0)
        self.assertTrue(x.target_hit)
        self.assertEqual(x.state,ManagementState.COMPLETED)

    def test_invalidation_requires_confirmed_close(self):
        x=self.classify(low=88.0,close=91.0)
        self.assertFalse(x.invalidated)
        self.assertNotEqual(x.state,ManagementState.INVALIDATED)

        y=self.classify(low=88.0,close=89.0)
        self.assertTrue(y.invalidated)
        self.assertEqual(y.state,ManagementState.INVALIDATED)

    def test_same_bar_target_and_confirmed_invalidation_is_ambiguous(self):
        x=self.classify(high=111.0,low=88.0,close=89.0)
        self.assertTrue(x.target_hit)
        self.assertTrue(x.invalidated)
        self.assertEqual(x.state,ManagementState.AMBIGUOUS)

    def test_short_geometry_is_directionally_symmetric(self):
        x=self.classify(
            direction=-1,
            high=101.0,
            low=93.0,
            close=95.0,
            target=90.0,
            invalidation=110.0,
            momentum=Momentum.DOWN_ACCEL,
            rsi=RsiState.BEAR,
            participation=Participation.CONFIRM,
        )
        self.assertEqual(x.state,ManagementState.CONTINUATION)
        self.assertAlmostEqual(x.target_room_atr,0.5)
        self.assertAlmostEqual(x.invalidation_buffer_atr,1.5)


if __name__=="__main__":
    unittest.main()

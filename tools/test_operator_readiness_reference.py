import unittest

from types import SimpleNamespace

from tools.execution_state_reference import Events, Readiness, State
from tools.operator_readiness_reference import (
    OperatorReadiness,
    PathReadiness,
    from_sample,
    project,
)


class OperatorReadinessTests(unittest.TestCase):
    def test_all_wait(self):
        r=project([
            PathReadiness("a",Readiness.WAIT,0),
            PathReadiness("b",Readiness.WAIT,0),
        ])
        self.assertEqual(r.readiness,OperatorReadiness.WAIT)
        self.assertEqual(r.direction,0)
        self.assertFalse(r.conflict)

    def test_fresh_armed_surfaces_over_background_aligned(self):
        r=project([
            PathReadiness("frozen",Readiness.ALIGNED,1),
            PathReadiness("range",Readiness.ARMED,1),
        ])
        self.assertEqual(r.readiness,OperatorReadiness.ARMED)
        self.assertEqual(r.direction,1)
        self.assertEqual(r.selected_sources,("range",))
        self.assertEqual(r.background_aligned_sources,("frozen",))

    def test_confirmed_surfaces_over_prep_and_emits_confirm(self):
        r=project([
            PathReadiness("frozen",Readiness.PREP,-1),
            PathReadiness("range",Readiness.CONFIRMED,-1,True),
        ])
        self.assertEqual(r.readiness,OperatorReadiness.CONFIRMED)
        self.assertTrue(r.confirm)
        self.assertEqual(r.confirming_sources,("range",))

    def test_opposite_active_directions_become_non_actionable_conflict(self):
        r=project([
            PathReadiness("trend",Readiness.ARMED,1),
            PathReadiness("range",Readiness.CONFIRMED,-1,True),
        ])
        self.assertEqual(r.readiness,OperatorReadiness.CONFLICT)
        self.assertEqual(r.direction,0)
        self.assertTrue(r.conflict)
        self.assertFalse(r.confirm)
        self.assertEqual(r.suppressed_confirm_sources,("range",))

    def test_same_bar_same_direction_multi_confirm_collapses_to_one(self):
        r=project([
            PathReadiness("frozen",Readiness.CONFIRMED,1,True),
            PathReadiness("trend",Readiness.CONFIRMED,1,True),
        ])
        self.assertEqual(r.readiness,OperatorReadiness.CONFIRMED)
        self.assertTrue(r.confirm)
        self.assertEqual(set(r.confirming_sources),{"frozen","trend"})
        self.assertEqual(set(r.selected_sources),{"frozen","trend"})

    def test_equal_urgency_preserves_all_sources(self):
        r=project([
            PathReadiness("frozen",Readiness.ARMED,-1),
            PathReadiness("trend",Readiness.ARMED,-1),
        ])
        self.assertEqual(r.readiness,OperatorReadiness.ARMED)
        self.assertEqual(set(r.selected_sources),{"frozen","trend"})

    def test_from_sample(self):
        s=SimpleNamespace(
            result=SimpleNamespace(
                state=State(Readiness.PREP,1),
                events=Events(confirm=False),
            )
        )
        p=from_sample("x",s)
        self.assertEqual(p.path,"x")
        self.assertEqual(p.readiness,Readiness.PREP)
        self.assertEqual(p.direction,1)


if __name__=="__main__":
    unittest.main()

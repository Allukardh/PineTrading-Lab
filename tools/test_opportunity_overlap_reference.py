import unittest

from types import SimpleNamespace

from tools.execution_state_reference import Events, Readiness, State
from tools.opportunity_overlap_reference import (
    ConfirmEvent,
    confirm_events,
    match_near_confirms,
    match_near_opposite_confirms,
    pairwise_overlap,
    triple_overlap,
)


def sample(readiness=Readiness.WAIT,direction=0,confirm=False):
    return SimpleNamespace(
        result=SimpleNamespace(
            state=State(readiness,direction),
            events=Events(confirm=confirm),
        )
    )


class OpportunityOverlapTests(unittest.TestCase):
    def test_pairwise_same_and_opposite(self):
        a=[
            sample(Readiness.ARMED,1),
            sample(Readiness.PREP,1),
            sample(Readiness.CONFIRMED,-1,True),
        ]
        b=[
            sample(Readiness.PREP,1),
            sample(Readiness.ARMED,-1),
            sample(Readiness.CONFIRMED,-1,True),
        ]
        x=pairwise_overlap(a,b)
        self.assertEqual(x["both_active_bars"],3)
        self.assertEqual(x["same_direction_active_bars"],2)
        self.assertEqual(x["opposite_direction_active_bars"],1)
        self.assertEqual(x["simultaneous_same_direction_confirms"],1)

    def test_near_confirm_matching_is_one_to_one(self):
        a=[ConfirmEvent(10,1),ConfirmEvent(12,1),ConfirmEvent(30,-1)]
        b=[ConfirmEvent(11,1),ConfirmEvent(13,1),ConfirmEvent(28,-1)]
        m=match_near_confirms(a,b,window_bars=3)
        self.assertEqual(len(m),3)
        self.assertEqual(sorted(x.distance_bars for x in m),[1,1,2])

    def test_near_opposite_confirm_matching(self):
        a=[ConfirmEvent(10,1),ConfirmEvent(20,-1)]
        b=[ConfirmEvent(12,-1),ConfirmEvent(18,1)]
        m=match_near_opposite_confirms(a,b,window_bars=3)
        self.assertEqual(len(m),2)
        self.assertEqual(sorted(x.distance_bars for x in m),[2,2])

    def test_confirm_events(self):
        xs=[
            sample(),
            sample(Readiness.CONFIRMED,1,True),
            sample(Readiness.CONFIRMED,-1,True),
        ]
        self.assertEqual(confirm_events(xs),[ConfirmEvent(1,1),ConfirmEvent(2,-1)])

    def test_triple_conflict(self):
        a=[sample(Readiness.ARMED,1),sample(Readiness.ARMED,1)]
        b=[sample(Readiness.ARMED,1),sample(Readiness.ARMED,-1)]
        c=[sample(Readiness.ARMED,1),sample(Readiness.ARMED,1)]
        x=triple_overlap(a,b,c)
        self.assertEqual(x["all_active_bars"],2)
        self.assertEqual(x["all_same_direction_bars"],1)
        self.assertEqual(x["direction_conflict_bars"],1)


if __name__=="__main__":
    unittest.main()

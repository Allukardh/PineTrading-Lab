import unittest

from tools.execution_state_reference import Readiness
from tools.operator_readiness_reference import (
    OperatorProjection,
    OperatorReadiness,
    PathReadiness,
)
from tools.responsiveness_profile_reference import (
    ProfileMode,
    anticipated_events,
    resolve_anticipated,
    resolve_confirmed,
    standard_events,
)


def proj(readiness, direction=1, *, confirm=False, selected=("A",), confirming=()):
    return OperatorProjection(
        readiness=readiness,
        direction=direction,
        conflict=readiness==OperatorReadiness.CONFLICT,
        confirm=confirm,
        active_sources=selected if readiness!=OperatorReadiness.WAIT else (),
        selected_sources=selected if readiness!=OperatorReadiness.WAIT else (),
        confirming_sources=confirming,
        suppressed_confirm_sources=(),
        background_aligned_sources=(),
    )


def path(name, readiness, direction=1, confirm=False):
    return PathReadiness(name, readiness, direction if readiness!=Readiness.WAIT else 0, confirm)


class ResponsivenessProfileTests(unittest.TestCase):
    def test_anticipated_triggers_only_on_new_armed_entry(self):
        ps=[
            proj(OperatorReadiness.PREP),
            proj(OperatorReadiness.ARMED),
            proj(OperatorReadiness.ARMED),
            proj(OperatorReadiness.PREP),
            proj(OperatorReadiness.ARMED),
        ]
        ev=anticipated_events(ps)
        self.assertEqual([x.bar for x in ev],[1,4])
        self.assertTrue(all(x.mode==ProfileMode.ANTECIPADO for x in ev))

    def test_standard_is_literal_operator_confirm(self):
        ps=[
            proj(OperatorReadiness.ARMED),
            proj(OperatorReadiness.CONFIRMED,confirm=True,confirming=("A",)),
            proj(OperatorReadiness.ALIGNED),
        ]
        ev=standard_events(ps)
        self.assertEqual(len(ev),1)
        self.assertEqual(ev[0].bar,1)
        self.assertEqual(ev[0].sources,("A",))
        self.assertEqual(ev[0].mode,ProfileMode.PADRAO)

    def test_anticipated_converts_when_arming_source_confirms(self):
        ps=[
            {"A":path("A",Readiness.ARMED)},
            {"A":path("A",Readiness.ARMED)},
            {"A":path("A",Readiness.CONFIRMED,confirm=True)},
        ]
        event=type("E",(),{})()
        # use real event from detector
        ev=anticipated_events([
            proj(OperatorReadiness.ARMED),
            proj(OperatorReadiness.ARMED),
            proj(OperatorReadiness.CONFIRMED,confirm=True,confirming=("A",)),
        ])[0]
        r=resolve_anticipated(ev,ps)
        self.assertTrue(r.converted)
        self.assertEqual(r.confirm_bar,2)
        self.assertEqual(r.bars_to_confirm,2)

    def test_anticipated_false_start_when_source_dies(self):
        ev=anticipated_events([proj(OperatorReadiness.ARMED)])[0]
        rows=[
            {"A":path("A",Readiness.ARMED)},
            {"A":path("A",Readiness.PREP)},
            {"A":path("A",Readiness.WAIT)},
        ]
        r=resolve_anticipated(ev,rows)
        self.assertFalse(r.converted)
        self.assertEqual(r.end_bar,2)

    def test_confirmed_requires_same_source_persistence(self):
        std=standard_events([
            proj(OperatorReadiness.CONFIRMED,confirm=True,confirming=("A",)),
            proj(OperatorReadiness.ALIGNED,selected=("A",)),
        ])[0]
        rows=[
            {"A":path("A",Readiness.CONFIRMED,confirm=True)},
            {"A":path("A",Readiness.ALIGNED)},
        ]
        r=resolve_confirmed(std,[
            proj(OperatorReadiness.CONFIRMED,confirm=True,confirming=("A",)),
            proj(OperatorReadiness.ALIGNED,selected=("A",)),
        ],rows)
        self.assertTrue(r.survived)
        self.assertEqual(r.confirmed_event.bar,1)
        self.assertEqual(r.confirmed_event.reference_confirm_bar,0)

    def test_confirmed_rejects_if_source_dies_even_if_same_direction_elsewhere(self):
        std=standard_events([
            proj(OperatorReadiness.CONFIRMED,confirm=True,confirming=("A",)),
            proj(OperatorReadiness.ALIGNED,selected=("B",)),
        ])[0]
        rows=[
            {"A":path("A",Readiness.CONFIRMED,confirm=True),"B":path("B",Readiness.WAIT)},
            {"A":path("A",Readiness.WAIT),"B":path("B",Readiness.ALIGNED)},
        ]
        r=resolve_confirmed(std,[
            proj(OperatorReadiness.CONFIRMED,confirm=True,confirming=("A",)),
            proj(OperatorReadiness.ALIGNED,selected=("B",)),
        ],rows)
        self.assertFalse(r.survived)
        self.assertEqual(r.reason,"CONFIRMING_SOURCE_DIED")

    def test_confirmed_rejects_conflict(self):
        std=standard_events([
            proj(OperatorReadiness.CONFIRMED,confirm=True,confirming=("A",)),
            proj(OperatorReadiness.CONFLICT,direction=0,selected=("A","B")),
        ])[0]
        rows=[
            {"A":path("A",Readiness.CONFIRMED,confirm=True)},
            {"A":path("A",Readiness.ALIGNED),"B":path("B",Readiness.ARMED,-1)},
        ]
        r=resolve_confirmed(std,[
            proj(OperatorReadiness.CONFIRMED,confirm=True,confirming=("A",)),
            proj(OperatorReadiness.CONFLICT,direction=0,selected=("A","B")),
        ],rows)
        self.assertFalse(r.survived)
        self.assertEqual(r.reason,"OPERATOR_CONFLICT")


if __name__=="__main__":
    unittest.main()

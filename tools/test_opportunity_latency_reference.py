import unittest

from tools.execution_candidate_reference import ExecutionResearchSample
from tools.execution_state_reference import (
    Events,
    Location,
    Readiness,
    Result,
    State,
)
from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_episode_reference import OpportunityEpisode, OpportunityType
from tools.opportunity_latency_reference import measure_episode


def snap(
    i,
    *,
    map_dir=1,
    thesis_key=10,
    new_thesis_event=False,
    thesis_invalidated=False,
    structural_conflict=False,
    destination=120.0,
):
    return IntegrationSnapshot(
        bar_index=i,
        time=i * 1_000_000,
        map_dir=map_dir,
        atr=10.0,
        close=100.0 + i,
        correction_active=True,
        thesis_invalidated=thesis_invalidated,
        structural_conflict=structural_conflict,
        t1_top=102.0,
        t1_bottom=101.0,
        primary_top=101.0,
        primary_bottom=99.0,
        t3_top=99.0,
        t3_bottom=98.0,
        retest_event=False,
        reclaim_event=False,
        destination_near=False,
        regime_dir=map_dir if map_dir in (-1, 1) else 0,
        structure_dir=map_dir if map_dir in (-1, 1) else 0,
        thesis_key=thesis_key,
        new_thesis_event=new_thesis_event,
        destination=destination,
        invalidation=90.0,
    )


def sample(
    readiness,
    *,
    direction=1,
    prep=False,
    armed=False,
    confirm=False,
    momentum="UP_ACCEL",
    rsi="BULL",
    participation="CONFIRM",
):
    return ExecutionResearchSample(
        state_before=State(),
        result=Result(
            State(readiness, direction if readiness != Readiness.WAIT else 0),
            Events(
                preparing_entered=prep,
                armed_entered=armed,
                confirm=confirm,
            ),
        ),
        momentum_ready=True,
        momentum_core=0.5,
        momentum_state_name=momentum,
        rsi_ready=True,
        rsi_value=55.0,
        rsi_state_name=rsi,
        participation_ready=True,
        relative_volume=1.3,
        participation_state_name=participation,
    )


class OpportunityLatencyTests(unittest.TestCase):
    def episode(self):
        return OpportunityEpisode(
            episode_id="BREAKOUT_EXPANSION:+1:0",
            opportunity_type=OpportunityType.BREAKOUT_EXPANSION,
            direction=1,
            onset_bar=0,
            confirmation_bar=0,
            thesis_key=10,
            reference_price=100.0,
            atr=10.0,
            destination=120.0,
            invalidation=90.0,
        )

    def test_already_aligned_is_recorded_as_anticipated_not_new_confirm(self):
        xs = [snap(0), snap(1)]
        samples = [
            sample(Readiness.ALIGNED),
            sample(Readiness.ALIGNED),
        ]
        r = measure_episode(
            self.episode(),
            xs,
            [Location.RETEST, Location.RETEST],
            samples,
            [1, 1],
            [100.0, 101.0],
            response_window_bars=1,
        )
        self.assertTrue(r.already_preparing_or_better)
        self.assertTrue(r.already_armed_or_better)
        self.assertTrue(r.already_aligned)
        self.assertEqual(r.prep_latency_bars, 0)
        self.assertEqual(r.armed_latency_bars, 0)
        self.assertIsNone(r.confirm_bar)

    def test_forward_latency_and_atr_displacement(self):
        xs = [snap(i) for i in range(4)]
        samples = [
            sample(Readiness.WAIT, direction=0, momentum="UP_DECEL", participation="NEUTRAL"),
            sample(Readiness.PREP, prep=True, participation="NEUTRAL"),
            sample(Readiness.ARMED, armed=True, participation="NEUTRAL"),
            sample(Readiness.CONFIRMED, confirm=True),
        ]
        r = measure_episode(
            self.episode(),
            xs,
            [Location.RETEST] * 4,
            samples,
            [1] * 4,
            [100.0, 101.0, 103.0, 105.0],
            response_window_bars=3,
        )
        self.assertEqual(r.prep_latency_bars, 1)
        self.assertEqual(r.armed_latency_bars, 2)
        self.assertEqual(r.confirm_latency_bars, 3)
        self.assertAlmostEqual(r.confirm_displacement_atr, 0.5)
        self.assertAlmostEqual(r.confirm_room_to_destination_atr, 1.5)
        self.assertIsNone(r.missed_reason)
        self.assertEqual(r.terminated_by, "CONFIRMED")

    def test_location_not_relevant_is_exposed_as_miss_reason(self):
        xs = [snap(i) for i in range(3)]
        samples = [
            sample(Readiness.WAIT, direction=0, momentum="UP_DECEL", participation="NEUTRAL")
            for _ in xs
        ]
        r = measure_episode(
            self.episode(),
            xs,
            [Location.OUTSIDE] * 3,
            samples,
            [1] * 3,
            [100.0, 101.0, 102.0],
            response_window_bars=2,
        )
        self.assertEqual(r.deepest_state, "WAIT")
        self.assertEqual(r.missed_reason, "LOCATION_NOT_RELEVANT")
        self.assertIsNone(r.prep_bar)

    def test_thesis_replacement_terminates_episode(self):
        xs = [
            snap(0, thesis_key=10),
            snap(1, thesis_key=11, new_thesis_event=True),
            snap(2, thesis_key=11),
        ]
        samples = [
            sample(Readiness.PREP, prep=True, participation="NEUTRAL"),
            sample(Readiness.WAIT, direction=0, participation="NEUTRAL"),
            sample(Readiness.WAIT, direction=0, participation="NEUTRAL"),
        ]
        r = measure_episode(
            self.episode(),
            xs,
            [Location.RETEST, Location.RETEST, Location.RETEST],
            samples,
            [1, 1, 1],
            [100.0, 101.0, 102.0],
            response_window_bars=2,
        )
        self.assertEqual(r.terminated_by, "THESIS_REPLACED")
        self.assertEqual(r.missed_reason, "THESIS_REPLACED")
        self.assertEqual(r.window_end_bar, 1)


if __name__ == "__main__":
    unittest.main()

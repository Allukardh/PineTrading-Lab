#!/usr/bin/env python3
from __future__ import annotations

import itertools
import unittest

from tools.execution_state_reference import (
    Evidence,
    Events,
    Location,
    Momentum,
    Participation,
    Readiness,
    Result,
    RsiState,
    State,
    Strength,
    classify_strength,
    step,
)


class ExecutionStateReferenceTests(unittest.TestCase):
    def ev(
        self,
        direction=1,
        location=Location.IN_CORRECTION,
        momentum=Momentum.NEUTRAL,
        rsi=RsiState.NEUTRAL,
        rsi_context=0,
        participation=Participation.NEUTRAL,
        confirmed=True,
        invalidated=False,
        conflict=False,
    ):
        return Evidence(
            map_dir=direction,
            location=location,
            momentum=momentum,
            rsi=rsi,
            rsi_context_dir=rsi_context,
            participation=participation,
            bar_confirmed=confirmed,
            thesis_invalidated=invalidated,
            structural_conflict=conflict,
        )

    def test_long_canonical_path(self):
        s = State()

        r = step(s, self.ev(location=Location.APPROACHING))
        self.assertEqual(r.state.readiness, Readiness.PREP)
        self.assertTrue(r.events.preparing_entered)

        r = step(
            r.state,
            self.ev(
                momentum=Momentum.TURN_UP,
                rsi=RsiState.RECOVERING_OVERSOLD,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.ARMED)
        self.assertTrue(r.events.armed_entered)

        r2 = step(
            r.state,
            self.ev(
                momentum=Momentum.UP_ACCEL,
                rsi=RsiState.BULL,
                participation=Participation.CONFIRM,
                confirmed=False,
            ),
        )
        self.assertEqual(r2.state.readiness, Readiness.ARMED)
        self.assertFalse(r2.events.confirm)

        r = step(
            r2.state,
            self.ev(
                momentum=Momentum.UP_ACCEL,
                rsi=RsiState.BULL,
                participation=Participation.CONFIRM,
                confirmed=True,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.CONFIRMED)
        self.assertTrue(r.events.confirm)

        r = step(
            r.state,
            self.ev(
                location=Location.OUTSIDE,
                momentum=Momentum.UP_DECEL,
                rsi=RsiState.BULL,
                participation=Participation.NEUTRAL,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.ALIGNED)
        self.assertEqual(r.state.strength, Strength.FADING)

    def test_short_canonical_path(self):
        s = State()

        r = step(s, self.ev(direction=-1, location=Location.RETEST))
        self.assertEqual(r.state.readiness, Readiness.PREP)
        self.assertEqual(r.state.direction, -1)

        r = step(
            r.state,
            self.ev(
                direction=-1,
                location=Location.RETEST,
                momentum=Momentum.TURN_DOWN,
                rsi=RsiState.FADING_OVERBOUGHT,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.ARMED)

        r = step(
            r.state,
            self.ev(
                direction=-1,
                location=Location.RETEST,
                momentum=Momentum.DOWN_ACCEL,
                rsi=RsiState.BEAR,
                participation=Participation.CONFIRM,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.CONFIRMED)
        self.assertTrue(r.events.confirm)

        r = step(
            r.state,
            self.ev(
                direction=-1,
                location=Location.OUTSIDE,
                momentum=Momentum.DOWN_DECEL,
                rsi=RsiState.BEAR,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.ALIGNED)

    def test_opposing_confirmed_rsi_context_blocks_arming(self):
        prev = State(Readiness.PREP, 1, Strength.NORMAL)

        blocked = step(
            prev,
            self.ev(
                direction=1,
                momentum=Momentum.TURN_UP,
                rsi=RsiState.RECOVERING_OVERSOLD,
                rsi_context=-1,
            ),
        )
        self.assertEqual(blocked.state.readiness, Readiness.PREP)
        self.assertFalse(blocked.events.armed_entered)

        allowed = step(
            prev,
            self.ev(
                direction=1,
                momentum=Momentum.TURN_UP,
                rsi=RsiState.RECOVERING_OVERSOLD,
                rsi_context=0,
            ),
        )
        self.assertEqual(allowed.state.readiness, Readiness.ARMED)
        self.assertTrue(allowed.events.armed_entered)

    def test_opposing_confirmed_rsi_context_cancels_armed(self):
        prev = State(Readiness.ARMED, -1, Strength.NORMAL)

        r = step(
            prev,
            self.ev(
                direction=-1,
                location=Location.RETEST,
                momentum=Momentum.DOWN_ACCEL,
                rsi=RsiState.BEAR,
                rsi_context=1,
                participation=Participation.NEUTRAL,
            ),
        )

        self.assertEqual(r.state.readiness, Readiness.WAIT)
        self.assertTrue(r.events.canceled)

    def test_invalid_rsi_context_direction_rejected(self):
        with self.assertRaises(ValueError):
            step(
                State(),
                self.ev(
                    rsi_context=2,
                ),
            )

    def test_map_invalidation_wins(self):
        for stage in Readiness:
            direction = 0 if stage == Readiness.WAIT else 1
            prev = State(stage, direction, Strength.NORMAL)
            r = step(prev, self.ev(invalidated=True))
            self.assertEqual(r.state.readiness, Readiness.WAIT)
            self.assertEqual(r.state.direction, 0)
            self.assertEqual(r.state.strength, Strength.NORMAL)

    def test_structural_conflict_wins(self):
        prev = State(Readiness.ARMED, 1, Strength.NORMAL)
        r = step(prev, self.ev(conflict=True))
        self.assertEqual(r.state.readiness, Readiness.WAIT)
        self.assertTrue(r.events.canceled)

    def test_direction_flip_resets_before_new_setup(self):
        prev = State(Readiness.ALIGNED, 1, Strength.NORMAL)
        r = step(
            prev,
            self.ev(
                direction=-1,
                momentum=Momentum.TURN_DOWN,
                rsi=RsiState.BEAR,
                participation=Participation.CONFIRM,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.WAIT)
        self.assertEqual(r.state.direction, 0)
        self.assertTrue(r.events.canceled)

    def test_reaction_risk_requires_location_and_two_families(self):
        base = self.ev(
            location=Location.DESTINATION_NEAR,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.EXTREME_OVERBOUGHT,
            participation=Participation.NEUTRAL,
        )
        self.assertEqual(classify_strength(1, base), Strength.REACTION_RISK)

        not_near = self.ev(
            location=Location.OUTSIDE,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.EXTREME_OVERBOUGHT,
            participation=Participation.NEUTRAL,
        )
        self.assertEqual(classify_strength(1, not_near), Strength.EXHAUSTED)

        one_family = self.ev(
            location=Location.DESTINATION_NEAR,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.BULL,
            participation=Participation.NEUTRAL,
        )
        self.assertEqual(classify_strength(1, one_family), Strength.FADING)

    def test_aligned_does_not_cancel_on_one_weak_family(self):
        prev = State(Readiness.ALIGNED, 1, Strength.NORMAL)
        r = step(
            prev,
            self.ev(
                location=Location.OUTSIDE,
                momentum=Momentum.UP_DECEL,
                rsi=RsiState.BULL,
                participation=Participation.WEAK,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.ALIGNED)
        self.assertEqual(r.state.strength, Strength.EXHAUSTED)

    def test_aligned_cancels_on_two_opposing_directional_families(self):
        prev = State(Readiness.ALIGNED, 1, Strength.NORMAL)
        r = step(
            prev,
            self.ev(
                location=Location.OUTSIDE,
                momentum=Momentum.TURN_DOWN,
                rsi=RsiState.BEAR,
                participation=Participation.NEUTRAL,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.WAIT)
        self.assertTrue(r.events.canceled)

    def test_wait_can_never_jump_to_confirmed(self):
        for direction, location, momentum, rsi, participation, confirmed in itertools.product(
            (-1, 1),
            list(Location),
            list(Momentum),
            list(RsiState),
            list(Participation),
            (False, True),
        ):
            r = step(
                State(),
                self.ev(
                    direction=direction,
                    location=location,
                    momentum=momentum,
                    rsi=rsi,
                    participation=participation,
                    confirmed=confirmed,
                ),
            )
            self.assertNotIn(
                r.state.readiness,
                {Readiness.ARMED, Readiness.CONFIRMED, Readiness.ALIGNED},
            )
            self.assertFalse(r.events.confirm)

    def test_unconfirmed_bar_can_never_emit_confirm(self):
        for direction, location, momentum, rsi, participation in itertools.product(
            (-1, 1),
            list(Location),
            list(Momentum),
            list(RsiState),
            list(Participation),
        ):
            prev = State(Readiness.ARMED, direction, Strength.NORMAL)
            r = step(
                prev,
                self.ev(
                    direction=direction,
                    location=location,
                    momentum=momentum,
                    rsi=rsi,
                    participation=participation,
                    confirmed=False,
                ),
            )
            self.assertNotEqual(r.state.readiness, Readiness.CONFIRMED)
            self.assertFalse(r.events.confirm)

    def test_invalid_or_conflicted_context_never_arms(self):
        for direction, stage, invalidated, conflict in itertools.product(
            (-1, 0, 1),
            list(Readiness),
            (False, True),
            (False, True),
        ):
            if not invalidated and not conflict and direction != 0:
                continue
            prev_dir = direction if direction in (-1, 1) and stage != Readiness.WAIT else 0
            prev = State(stage, prev_dir, Strength.NORMAL)
            r = step(
                prev,
                Evidence(
                    map_dir=direction,
                    location=Location.IN_CORRECTION,
                    momentum=Momentum.UP_ACCEL,
                    rsi=RsiState.BULL,
                    participation=Participation.CONFIRM,
                    thesis_invalidated=invalidated,
                    structural_conflict=conflict,
                ),
            )
            self.assertEqual(r.state.readiness, Readiness.WAIT)
            self.assertFalse(r.events.confirm)

    def test_confirm_is_one_bar_then_aligned(self):
        prev = State(Readiness.CONFIRMED, 1, Strength.NORMAL)
        r = step(
            prev,
            self.ev(
                location=Location.OUTSIDE,
                momentum=Momentum.UP_ACCEL,
                rsi=RsiState.BULL,
                participation=Participation.CONFIRM,
            ),
        )
        self.assertEqual(r.state.readiness, Readiness.ALIGNED)
        self.assertFalse(r.events.confirm)

    def test_reaction_risk_edge_only_on_entry(self):
        prev = State(Readiness.ALIGNED, 1, Strength.NORMAL)
        evidence = self.ev(
            location=Location.DESTINATION_NEAR,
            momentum=Momentum.UP_DECEL,
            rsi=RsiState.EXTREME_OVERBOUGHT,
            participation=Participation.WEAK,
        )
        first = step(prev, evidence)
        self.assertEqual(first.state.strength, Strength.REACTION_RISK)
        self.assertTrue(first.events.reaction_risk_entered)

        second = step(first.state, evidence)
        self.assertEqual(second.state.strength, Strength.REACTION_RISK)
        self.assertFalse(second.events.reaction_risk_entered)


if __name__ == "__main__":
    unittest.main()

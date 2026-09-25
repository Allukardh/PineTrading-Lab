import unittest

from tools.market_map_offline_core import IntegrationSnapshot, FAIL_MAX_BARS
from tools.opportunity_episode_reference import OpportunityEpisode, OpportunityType
from tools.opportunity_outcome_reference import (
    CandidateOutcome,
    classify_all,
    classify_breakout,
    classify_regime_transitions,
)


def snap(i, *, map_dir=1, structure_dir=1, fakeout_event=False):
    return IntegrationSnapshot(
        bar_index=i,
        time=i * 1_000_000,
        map_dir=map_dir,
        atr=10.0,
        close=100.0 + i,
        correction_active=False,
        thesis_invalidated=False,
        structural_conflict=False,
        t1_top=None,
        t1_bottom=None,
        primary_top=None,
        primary_bottom=None,
        t3_top=None,
        t3_bottom=None,
        retest_event=False,
        reclaim_event=False,
        destination_near=False,
        regime_dir=map_dir if map_dir in (-1, 1) else 0,
        structure_dir=structure_dir,
        fakeout_event=fakeout_event,
    )


def ep(kind, direction, bar, name=None):
    return OpportunityEpisode(
        episode_id=name or f"{kind.value}:{direction:+d}:{bar}",
        opportunity_type=kind,
        direction=direction,
        onset_bar=bar,
        confirmation_bar=bar,
        thesis_key=None,
        reference_price=100.0,
        atr=10.0,
        destination=120.0,
        invalidation=90.0,
    )


class OpportunityOutcomeTests(unittest.TestCase):
    def test_breakout_fakeout_uses_accepted_fail_window(self):
        e = ep(OpportunityType.BREAKOUT_CANDIDATE, 1, 0)
        xs = [snap(i) for i in range(FAIL_MAX_BARS + 1)]
        xs[3] = snap(3, map_dir=0, structure_dir=-1, fakeout_event=True)
        out = classify_breakout(e, xs)
        self.assertEqual(out.outcome, CandidateOutcome.BREAKOUT_FAKEOUT)
        self.assertEqual(out.outcome_bar, 3)

    def test_breakout_held_requires_full_fail_window(self):
        e = ep(OpportunityType.BREAKOUT_CANDIDATE, 1, 0)
        xs = [snap(i) for i in range(FAIL_MAX_BARS + 1)]
        out = classify_breakout(e, xs)
        self.assertEqual(out.outcome, CandidateOutcome.BREAKOUT_HELD)
        self.assertEqual(out.outcome_bar, FAIL_MAX_BARS)

    def test_breakout_at_series_end_is_unresolved(self):
        e = ep(OpportunityType.BREAKOUT_CANDIDATE, 1, 0)
        xs = [snap(i) for i in range(FAIL_MAX_BARS)]
        out = classify_breakout(e, xs)
        self.assertEqual(out.outcome, CandidateOutcome.BREAKOUT_UNRESOLVED)

    def test_reacceleration_uses_same_structural_fakeout_contract(self):
        e = ep(OpportunityType.REACCELERATION, 1, 0)
        xs = [snap(i) for i in range(FAIL_MAX_BARS + 1)]
        xs[2] = snap(2, map_dir=0, structure_dir=-1, fakeout_event=True)
        out = classify_breakout(e, xs)
        self.assertEqual(out.outcome, CandidateOutcome.BREAKOUT_FAKEOUT)
        self.assertEqual(out.outcome_bar, 2)

    def test_regime_candidate_matures_before_opposite_candidate(self):
        a = ep(OpportunityType.REGIME_TRANSITION_CANDIDATE, 1, 10, "a")
        mature = ep(OpportunityType.REGIME_REVERSAL, 1, 15, "m")
        opposite = ep(OpportunityType.REGIME_TRANSITION_CANDIDATE, -1, 20, "b")
        out = classify_regime_transitions([a, mature, opposite])
        self.assertEqual(out["a"].outcome, CandidateOutcome.REGIME_MATURED)
        self.assertEqual(out["a"].outcome_bar, 15)

    def test_regime_candidate_fails_if_opposite_candidate_arrives_first(self):
        a = ep(OpportunityType.REGIME_TRANSITION_CANDIDATE, 1, 10, "a")
        opposite = ep(OpportunityType.REGIME_TRANSITION_CANDIDATE, -1, 12, "b")
        late = ep(OpportunityType.REGIME_REVERSAL, 1, 20, "m")
        out = classify_regime_transitions([a, opposite, late])
        self.assertEqual(out["a"].outcome, CandidateOutcome.REGIME_FAILED)
        self.assertEqual(out["a"].outcome_bar, 12)

    def test_non_candidate_is_not_applicable(self):
        p = ep(OpportunityType.PULLBACK_RETEST, 1, 0, "p")
        out = classify_all([p], [snap(0)])
        self.assertEqual(out["p"].outcome, CandidateOutcome.NOT_APPLICABLE)


if __name__ == "__main__":
    unittest.main()

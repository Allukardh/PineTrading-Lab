import unittest

from tools.market_map_offline_core import IntegrationSnapshot
from tools.opportunity_episode_reference import (
    OpportunityType,
    REVERSAL_PRIOR_REGIME_MIN_BARS,
    detect_episodes,
)


def snap(
    i,
    *,
    map_dir=1,
    regime_dir=1,
    structure_dir=1,
    structural_break_dir=0,
    thesis_key=10,
    correction_active=False,
    primary_top=None,
    primary_bottom=None,
    retest_event=False,
    reclaim_event=False,
    thesis_invalidated=False,
    structural_conflict=False,
):
    return IntegrationSnapshot(
        bar_index=i,
        time=i * 1_000_000,
        map_dir=map_dir,
        atr=10.0,
        close=100.0 + i,
        correction_active=correction_active,
        thesis_invalidated=thesis_invalidated,
        structural_conflict=structural_conflict,
        t1_top=None,
        t1_bottom=None,
        primary_top=primary_top,
        primary_bottom=primary_bottom,
        t3_top=None,
        t3_bottom=None,
        retest_event=retest_event,
        reclaim_event=reclaim_event,
        destination_near=False,
        regime_dir=regime_dir,
        structure_dir=structure_dir,
        structural_break_dir=structural_break_dir,
        thesis_key=thesis_key,
        destination=150.0,
        invalidation=80.0,
    )


class OpportunityEpisodeTests(unittest.TestCase):
    def test_breakout_is_known_on_break_bar(self):
        xs = [
            snap(0, structural_break_dir=0),
            snap(1, structural_break_dir=1),
            snap(2, structural_break_dir=0),
        ]
        eps = detect_episodes(xs, [101, 102, 103], [99, 100, 101])
        breaks = [e for e in eps if e.opportunity_type == OpportunityType.BREAKOUT_CANDIDATE]
        self.assertEqual(len(breaks), 1)
        self.assertEqual(breaks[0].onset_bar, 1)
        self.assertEqual(breaks[0].confirmation_bar, 1)
        self.assertEqual(breaks[0].direction, 1)

    def test_pullback_retest_is_deduplicated_per_thesis(self):
        xs = [
            snap(
                0,
                correction_active=True,
                primary_top=101.0,
                primary_bottom=99.0,
                thesis_key=7,
            ),
            snap(
                1,
                correction_active=True,
                primary_top=101.0,
                primary_bottom=99.0,
                retest_event=True,
                thesis_key=7,
            ),
            snap(
                2,
                correction_active=True,
                primary_top=104.0,
                primary_bottom=102.0,
                thesis_key=8,
            ),
        ]
        highs = [100.5, 101.0, 103.0]
        lows = [99.5, 99.0, 102.5]
        eps = detect_episodes(xs, highs, lows)
        pullbacks = [e for e in eps if e.opportunity_type == OpportunityType.PULLBACK_RETEST]
        self.assertEqual([e.thesis_key for e in pullbacks], [7, 8])
        self.assertEqual([e.confirmation_bar for e in pullbacks], [0, 2])

    def test_regime_transition_candidate_is_known_on_opposite_break(self):
        xs = [
            snap(
                i,
                map_dir=-1,
                regime_dir=-1,
                structure_dir=-1,
                thesis_key=100,
            )
            for i in range(REVERSAL_PRIOR_REGIME_MIN_BARS)
        ]
        break_bar = len(xs)
        xs.append(
            snap(
                break_bar,
                map_dir=0,
                regime_dir=0,
                structure_dir=1,
                structural_break_dir=1,
                thesis_key=None,
                structural_conflict=True,
            )
        )
        eps = detect_episodes(
            xs,
            [x.close + 1 for x in xs],
            [x.close - 1 for x in xs],
        )
        transitions = [
            e
            for e in eps
            if e.opportunity_type == OpportunityType.REGIME_TRANSITION_CANDIDATE
        ]
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].direction, 1)
        self.assertEqual(transitions[0].onset_bar, break_bar)
        self.assertEqual(transitions[0].confirmation_bar, break_bar)

    def test_regime_reversal_confirmation_is_not_backdated(self):
        xs = []
        for i in range(REVERSAL_PRIOR_REGIME_MIN_BARS):
            xs.append(
                snap(
                    i,
                    map_dir=-1,
                    regime_dir=-1,
                    structure_dir=-1,
                    thesis_key=100,
                )
            )
        # Neutral transition, then an opposite structural break before the
        # confirmed bull regime appears.
        xs.append(
            snap(
                len(xs),
                map_dir=0,
                regime_dir=0,
                structure_dir=1,
                structural_break_dir=1,
                thesis_key=None,
                structural_conflict=True,
            )
        )
        confirm_bar = len(xs)
        xs.append(
            snap(
                confirm_bar,
                map_dir=1,
                regime_dir=1,
                structure_dir=1,
                thesis_key=200,
            )
        )

        eps = detect_episodes(
            xs,
            [x.close + 1 for x in xs],
            [x.close - 1 for x in xs],
        )
        rev = [e for e in eps if e.opportunity_type == OpportunityType.REGIME_REVERSAL]
        self.assertEqual(len(rev), 1)
        self.assertEqual(rev[0].direction, 1)
        self.assertEqual(rev[0].onset_bar, REVERSAL_PRIOR_REGIME_MIN_BARS)
        self.assertEqual(rev[0].confirmation_bar, confirm_bar)
        self.assertLess(rev[0].onset_bar, rev[0].confirmation_bar)

    def test_short_prior_regime_does_not_create_reversal_label(self):
        xs = [
            snap(i, map_dir=-1, regime_dir=-1, structure_dir=-1)
            for i in range(REVERSAL_PRIOR_REGIME_MIN_BARS - 1)
        ]
        xs.append(
            snap(
                len(xs),
                map_dir=1,
                regime_dir=1,
                structure_dir=1,
                structural_break_dir=1,
                thesis_key=2,
            )
        )
        eps = detect_episodes(
            xs,
            [x.close + 1 for x in xs],
            [x.close - 1 for x in xs],
        )
        self.assertFalse(
            any(e.opportunity_type == OpportunityType.REGIME_REVERSAL for e in eps)
        )

    def test_length_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_episodes([snap(0)], [101.0], [])


if __name__ == "__main__":
    unittest.main()

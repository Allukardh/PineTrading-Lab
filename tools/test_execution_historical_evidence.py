#!/usr/bin/env python3
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from tools.execution_historical_evidence import (
    confirmed_context_indices,
    pearson,
    percentile,
    rankdata,
    sign_agreement,
    spearman,
)


class ExecutionHistoricalEvidenceTests(unittest.TestCase):
    def test_percentile_linear_interpolation(self):
        xs = [0.0, 10.0, 20.0, 30.0]
        self.assertEqual(percentile(xs, 0.0), 0.0)
        self.assertEqual(percentile(xs, 1.0), 30.0)
        self.assertAlmostEqual(percentile(xs, 0.5), 15.0)
        self.assertAlmostEqual(percentile(xs, 0.25), 7.5)

    def test_rankdata_uses_average_tie_rank(self):
        self.assertEqual(rankdata([10.0, 20.0, 20.0, 40.0]), [1.0, 2.5, 2.5, 4.0])

    def test_correlations(self):
        xs = [1.0, 2.0, 3.0, 4.0]
        self.assertAlmostEqual(pearson(xs, xs), 1.0)
        self.assertAlmostEqual(spearman(xs, xs), 1.0)
        self.assertAlmostEqual(pearson(xs, list(reversed(xs))), -1.0)
        self.assertAlmostEqual(spearman(xs, list(reversed(xs))), -1.0)

    def test_confirmed_context_uses_previous_htf_bar(self):
        utc = timezone.utc
        htf = [
            datetime(2026, 1, 1, 0, 0, tzinfo=utc),
            datetime(2026, 1, 1, 1, 0, tzinfo=utc),
            datetime(2026, 1, 1, 2, 0, tzinfo=utc),
        ]
        chart = [
            datetime(2026, 1, 1, 0, 0, tzinfo=utc),
            datetime(2026, 1, 1, 0, 45, tzinfo=utc),
            datetime(2026, 1, 1, 1, 0, tzinfo=utc),
            datetime(2026, 1, 1, 1, 45, tzinfo=utc),
            datetime(2026, 1, 1, 2, 0, tzinfo=utc),
        ]
        self.assertEqual(
            confirmed_context_indices(chart, htf),
            [None, None, 0, 0, 1],
        )

    def test_sign_agreement_excludes_near_zero(self):
        result = sign_agreement(
            [0.50, -0.50, 0.01, 0.50],
            [0.30, -0.20, 0.90, -0.30],
            eps=0.05,
        )
        self.assertEqual(result["agree"], 2)
        self.assertEqual(result["disagree"], 1)
        self.assertEqual(result["excluded_near_zero"], 1)
        self.assertAlmostEqual(result["agreement_pct"], 200.0 / 3.0)


if __name__ == "__main__":
    unittest.main()

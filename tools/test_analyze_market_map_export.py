#!/usr/bin/env python3
"""Deterministic unit tests for analyze_market_map_export.py."""
from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "mm_analyzer", HERE / "analyze_market_map_export.py"
)
assert SPEC and SPEC.loader
mm = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mm
SPEC.loader.exec_module(mm)

HEADER = [
    "Time", "Open", "High", "Low", "Close",
    "MM Audit • Schema",
    "MM Audit • Confirmado",
    "MM Audit • MapDir",
    "MM Audit • ATR",
    "MM Audit • Modelo",
    "MM Audit • Amostras adaptativas",
    "MM Audit • Correção topo",
    "MM Audit • Correção fundo",
    "MM Audit • Destino 1",
    "MM Audit • Invalidação",
    "MM Audit • Confluências",
    "MM Audit • Nova tese evt",
    "MM Audit • Toque zona evt",
    "MM Audit • Zona→Destino evt",
    "MM Audit • Zona→Invalidação evt",
    "MM Audit • Ambíguo evt",
    "MM Audit • Sweep reclaim evt",
]


def row(
    t: str, o: float, h: float, l: float, c: float,
    direction: int, atr: float, model: int, samples: int,
    top: float | None, bottom: float | None, dest: float | None,
    inv: float | None, conf: int,
    new: int = 0, touch: int = 0, dest_evt: int = 0,
    inv_evt: int = 0, amb_evt: int = 0, reclaim: int = 0,
):
    def v(x):
        return "" if x is None else x
    return [
        t, o, h, l, c, 2, 1, direction, atr, model, samples,
        v(top), v(bottom), v(dest), v(inv), conf,
        new, touch, dest_evt, inv_evt, amb_evt, reclaim,
    ]


ROWS = [
    row("2026-01-01 00:00", 100, 104, 99, 103, 1, 5, 4, 12, 100, 95, 110, 90, 4, new=1),
    row("2026-01-01 01:00", 103, 103, 97, 99, 1, 5, 4, 12, 100, 95, 110, 90, 4, touch=1, reclaim=1),
    row("2026-01-01 02:00", 99, 111, 98, 109, 1, 5, 4, 12, 100, 95, 111, 90, 4, dest_evt=1),
    row("2026-01-01 03:00", 120, 123, 118, 121, -1, 5, 2, 10, 125, 120, 100, 130, 3, new=1),
    row("2026-01-01 04:00", 121, 123, 119, 121, -1, 5, 2, 10, 125, 120, 100, 130, 3, touch=1, reclaim=-1),
    row("2026-01-01 05:00", 121, 131, 120, 130.5, -1, 5, 2, 10, 125, 120, 99, 130, 3, inv_evt=1),
    row("2026-01-01 06:00", 100, 103, 99, 102, 1, 4, 1, 2, 99, 96, 108, 92, 2, new=1),
    row("2026-01-01 07:00", 102, 109, 97, 104, 1, 4, 1, 2, 99, 96, 108, 92, 2, touch=1, amb_evt=1, reclaim=1),
    row("2026-01-01 08:00", 104, 105, 103, 104.5, 1, 4, 1, 2, 99, 96, 109, 92, 2),
]


class AnalyzerTests(unittest.TestCase):
    def write_csv(self, path: Path, rows=ROWS):
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(HEADER)
            w.writerows(rows)

    def test_analyze_expected_counts(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.csv"
            self.write_csv(p)
            report = mm.analyze(p)

            self.assertEqual(report["audit_schema"], 2)
            self.assertEqual(report["confirmed_rows"], len(ROWS))
            self.assertEqual(report["provisional_rows"], 0)
            self.assertEqual(report["counts"]["theses"], 3)
            self.assertEqual(report["counts"]["zone_touches"], 3)
            self.assertEqual(report["counts"]["destination_outcomes"], 1)
            self.assertEqual(report["counts"]["invalidation_outcomes"], 1)
            self.assertEqual(report["counts"]["resolved_non_ambiguous"], 2)
            self.assertEqual(report["counts"]["ambiguous"], 1)
            self.assertEqual(report["ambiguous_timing"], {"SAME_TOUCH": 1})
            self.assertEqual(report["ambiguous_timing_by_model"]["FIB"], {"SAME_TOUCH": 1})
            amb = report["lifecycle_examples"]["ambiguity"]["SAME_TOUCH|FIB|LONG"][0]
            self.assertEqual(amb["reason_from_visible_row"], "TARGET")
            self.assertEqual(amb["same_touch_order_class"], "UNORDERED_TARGET")
            self.assertEqual(amb["frozen_target"], 108)
            self.assertEqual(amb["bars_from_touch"], 0)
            self.assertEqual(report["ambiguous_reasons"], {"TARGET": 1})
            self.assertEqual(report["same_touch_order"], {"UNORDERED_TARGET": 1})
            self.assertAlmostEqual(report["rates"]["zone_to_destination_pct_resolved"], 50.0)
            self.assertAlmostEqual(report["rates"]["resolved_non_ambiguous_pct_of_touches"], 200.0 / 3.0)
            self.assertAlmostEqual(report["rates"]["destination_pct_of_touches"], 100.0 / 3.0)
            self.assertAlmostEqual(report["rates"]["invalidation_pct_of_touches"], 100.0 / 3.0)
            self.assertAlmostEqual(report["rates"]["ambiguous_pct_of_touches"], 100.0 / 3.0)
            self.assertAlmostEqual(report["rates"]["superseded_pct_of_touches"], 0.0)
            self.assertEqual(report["direction_theses"], {"LONG": 2, "SHORT": 1})
            self.assertEqual(report["touch_models"], {"LIVE/ADAPT": 1, "ADAPT": 1, "FIB": 1})
            self.assertEqual(report["reclaim_events"], {"BULL_RECLAIM": 2, "BEAR_RECLAIM": 1})
            self.assertEqual(report["counts"]["zone_touch_with_reclaim"], 3)
            self.assertEqual(report["pathologies"], {})

    def test_aggregate_reports(self):
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / "a.csv"
            b = Path(td) / "b.csv"
            self.write_csv(a)
            self.write_csv(b)
            ra = mm.analyze(a)
            rb = mm.analyze(b)
            agg = mm.aggregate_reports([ra, rb])

            self.assertEqual(agg["files"], 2)
            self.assertEqual(agg["counts"]["theses"], 6)
            self.assertEqual(agg["counts"]["zone_touches"], 6)
            self.assertAlmostEqual(agg["zone_to_destination_pct_resolved"], 50.0)
            self.assertAlmostEqual(agg["touch_outcome_accounting"]["destination_pct"], 100.0 / 3.0)
            self.assertAlmostEqual(agg["touch_outcome_accounting"]["invalidation_pct"], 100.0 / 3.0)
            self.assertAlmostEqual(agg["touch_outcome_accounting"]["ambiguous_pct"], 100.0 / 3.0)
            self.assertAlmostEqual(agg["touch_outcome_accounting"]["superseded_pct"], 0.0)
            self.assertAlmostEqual(agg["touch_outcome_accounting"]["accounted_pct"], 100.0)
            self.assertTrue(agg["hard_pass"])
            self.assertEqual(agg["pathologies"], {})

    def test_superseded_touch_is_accounted_as_censored(self):
        rows = [
            row("2026-01-01 00:00", 100, 104, 99, 103, 1, 5, 4, 12, 100, 95, 110, 90, 4, new=1),
            row("2026-01-01 01:00", 103, 103, 97, 99, 1, 5, 4, 12, 100, 95, 110, 90, 4, touch=1),
            row("2026-01-01 02:00", 99, 102, 98, 101, 1, 5, 4, 12, 100, 95, 111, 90, 4, new=1),
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "superseded.csv"
            self.write_csv(p, rows)
            report = mm.analyze(p)
            self.assertEqual(report["counts"]["zone_touches"], 1)
            self.assertEqual(report["counts"]["superseded_after_touch"], 1)
            self.assertAlmostEqual(report["rates"]["superseded_pct_of_touches"], 100.0)
            self.assertEqual(report["supersession_transitions"], {"LONG->LONG": 1})
            self.assertEqual(report["superseded_touch_models"], {"LIVE/ADAPT": 1})
            self.assertEqual(report["distributions"]["bars_touch_to_supersession"]["median"], 1.0)
            sup = report["lifecycle_examples"]["supersession"]["LONG->LONG|LIVE/ADAPT|LE3"][0]
            self.assertEqual(sup["transition"], "LONG->LONG")
            self.assertEqual(sup["prior_model"], "LIVE/ADAPT")
            self.assertEqual(sup["bars_touch_to_supersession"], 1)
            self.assertEqual(report["supersession_speed"], {"LE3": 1})
            self.assertEqual(report["supersession_transition_speed"], {"LONG->LONG": {"LE3": 1}})
            self.assertEqual(sup["touch"]["time"], "2026-01-01 01:00")
            self.assertEqual(sup["new_thesis"]["time"], "2026-01-01 02:00")
            self.assertEqual(report["pathologies"], {})

    def test_post_touch_ambiguity_is_classified_separately(self):
        rows = [
            row("2026-01-01 00:00", 100, 104, 99, 103, 1, 5, 4, 12, 100, 95, 110, 90, 4, new=1),
            row("2026-01-01 01:00", 103, 103, 97, 99, 1, 5, 4, 12, 100, 95, 110, 90, 4, touch=1),
            row("2026-01-01 02:00", 99, 112, 89, 101, 1, 5, 4, 12, 100, 95, 110, 90, 4, amb_evt=1),
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "post_touch_amb.csv"
            self.write_csv(p, rows)
            report = mm.analyze(p)
            self.assertEqual(report["ambiguous_timing"], {"POST_TOUCH_BOTH_BOUNDS": 1})
            self.assertEqual(
                report["ambiguous_timing_by_model"]["LIVE/ADAPT"],
                {"POST_TOUCH_BOTH_BOUNDS": 1},
            )
            amb = report["lifecycle_examples"]["ambiguity"]["POST_TOUCH_BOTH_BOUNDS|LIVE/ADAPT|LONG"][0]
            self.assertEqual(amb["bars_from_touch"], 1)
            self.assertEqual(amb["touch"]["time"], "2026-01-01 01:00")
            self.assertEqual(amb["event"]["time"], "2026-01-01 02:00")
            self.assertIsNone(amb["same_touch_order_class"])

    def test_reload_compare_pass_and_fail(self):
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / "before.csv"
            b = Path(td) / "after.csv"
            self.write_csv(a)
            self.write_csv(b)

            same = mm.compare_reload(a, b)
            self.assertTrue(same["pass"])
            self.assertEqual(same["mismatch_counts"], {})

            changed = [list(x) for x in ROWS]
            changed[2][7] = -1  # historical MapDir mutation
            self.write_csv(b, changed)

            diff = mm.compare_reload(a, b)
            self.assertFalse(diff["pass"])
            self.assertGreater(diff["mismatch_counts"].get("map_dir", 0), 0)


if __name__ == "__main__":
    unittest.main()

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
]


def row(
    t: str, o: float, h: float, l: float, c: float,
    direction: int, atr: float, model: int, samples: int,
    top: float | None, bottom: float | None, dest: float | None,
    inv: float | None, conf: int,
    new: int = 0, touch: int = 0, dest_evt: int = 0,
    inv_evt: int = 0, amb_evt: int = 0,
):
    def v(x):
        return "" if x is None else x
    return [
        t, o, h, l, c, 1, 1, direction, atr, model, samples,
        v(top), v(bottom), v(dest), v(inv), conf,
        new, touch, dest_evt, inv_evt, amb_evt,
    ]


ROWS = [
    row("2026-01-01 00:00", 100, 104, 99, 103, 1, 5, 4, 12, 100, 95, 110, 90, 4, new=1),
    row("2026-01-01 01:00", 103, 103, 97, 99, 1, 5, 4, 12, 100, 95, 110, 90, 4, touch=1),
    row("2026-01-01 02:00", 99, 111, 98, 109, 1, 5, 4, 12, 100, 95, 111, 90, 4, dest_evt=1),
    row("2026-01-01 03:00", 120, 123, 118, 121, -1, 5, 2, 10, 125, 120, 100, 130, 3, new=1),
    row("2026-01-01 04:00", 121, 123, 119, 121, -1, 5, 2, 10, 125, 120, 100, 130, 3, touch=1),
    row("2026-01-01 05:00", 121, 131, 120, 130.5, -1, 5, 2, 10, 125, 120, 99, 130, 3, inv_evt=1),
    row("2026-01-01 06:00", 100, 103, 99, 102, 1, 4, 1, 2, 99, 96, 108, 92, 2, new=1),
    row("2026-01-01 07:00", 102, 109, 97, 104, 1, 4, 1, 2, 99, 96, 108, 92, 2, touch=1, amb_evt=1),
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

            self.assertEqual(report["audit_schema"], 1)
            self.assertEqual(report["confirmed_rows"], len(ROWS))
            self.assertEqual(report["provisional_rows"], 0)
            self.assertEqual(report["counts"]["theses"], 3)
            self.assertEqual(report["counts"]["zone_touches"], 3)
            self.assertEqual(report["counts"]["destination_outcomes"], 1)
            self.assertEqual(report["counts"]["invalidation_outcomes"], 1)
            self.assertEqual(report["counts"]["resolved_non_ambiguous"], 2)
            self.assertEqual(report["counts"]["ambiguous"], 1)
            self.assertAlmostEqual(report["rates"]["zone_to_destination_pct_resolved"], 50.0)
            self.assertEqual(report["direction_theses"], {"LONG": 2, "SHORT": 1})
            self.assertEqual(report["touch_models"], {"LIVE/ADAPT": 1, "ADAPT": 1, "FIB": 1})
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
            self.assertTrue(agg["hard_pass"])
            self.assertEqual(agg["pathologies"], {})

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

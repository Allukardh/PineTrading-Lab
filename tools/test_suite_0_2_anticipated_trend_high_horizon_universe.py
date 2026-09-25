import unittest

from tools.suite_0_2_anticipated_trend_high_horizon_universe import aggregate_tf


def row(kind, *, direction=1, converted=False, outcome="NOT_APPLICABLE",
        bars_to_confirm=None, displacement=None, duration=None):
    return {
        "bar": 1,
        "direction": direction,
        "kind": kind,
        "source_bar": 0,
        "episode_id": f"{kind}:{direction}:{converted}:{outcome}",
        "outcome": outcome,
        "converted": converted,
        "confirm_bar": 2 if converted else None,
        "bars_to_confirm": bars_to_confirm,
        "directional_displacement_to_confirm_atr": displacement,
        "nonconverted_duration_bars": duration,
    }


def item(rows):
    return {
        "events": len(rows),
        "market_rows": 100,
        "direction_counts": {
            "LONG": sum(r["direction"] == 1 for r in rows),
            "SHORT": sum(r["direction"] == -1 for r in rows),
        },
        "rows": rows,
    }


class HighHorizonAggregateTests(unittest.TestCase):
    def test_event_rows_remain_iterable_and_aggregate(self):
        per = {
            "AAA": {
                "3d": item([
                    row(
                        "BREAKOUT_EXPANSION",
                        direction=1,
                        converted=True,
                        outcome="BREAKOUT_HELD",
                        bars_to_confirm=2,
                        displacement=0.4,
                    ),
                    row(
                        "REACCELERATION",
                        direction=-1,
                        converted=False,
                        outcome="NOT_APPLICABLE",
                        duration=2,
                    ),
                ])
            },
            "BBB": {
                "3d": item([
                    row(
                        "BREAKOUT_EXPANSION",
                        direction=-1,
                        converted=False,
                        outcome="BREAKOUT_FAKEOUT",
                        duration=4,
                    ),
                ])
            },
        }

        out = aggregate_tf(per, "3d")

        self.assertEqual(out["events"], 3)
        self.assertEqual(out["symbols_with_events"], 2)
        self.assertEqual(out["direction_counts"], {"LONG": 1, "SHORT": 2})

        b = out["by_kind"]["BREAKOUT_EXPANSION"]
        self.assertEqual(b["all"]["events"], 2)
        self.assertEqual(b["converted"]["held"], 1)
        self.assertEqual(b["nonconverted"]["fakeout"], 1)

    def test_market_rows_metadata_does_not_replace_event_rows(self):
        x = item([])
        self.assertIsInstance(x["rows"], list)
        self.assertIsInstance(x["market_rows"], int)


if __name__ == "__main__":
    unittest.main()

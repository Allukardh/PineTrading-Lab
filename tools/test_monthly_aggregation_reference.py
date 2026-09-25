import unittest
from datetime import datetime, timezone

from tools.monthly_aggregation_reference import (
    aggregate_calendar_month,
    logical_sha256,
)


def dt(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


class MonthlyAggregationTests(unittest.TestCase):
    def test_calendar_month_ohlcv(self):
        data = {
            "open_time": [
                dt(2026, 1, 30),
                dt(2026, 1, 31),
                dt(2026, 2, 1),
                dt(2026, 2, 2),
            ],
            "open": [10.0, 11.0, 20.0, 21.0],
            "high": [12.0, 13.0, 22.0, 24.0],
            "low": [9.0, 8.0, 19.0, 18.0],
            "close": [11.0, 12.0, 21.0, 23.0],
            "volume": [1.0, 2.0, 3.0, 4.0],
            "taker_buy_base_asset_volume": [0.4, 0.8, 1.5, 2.0],
        }
        out, prov = aggregate_calendar_month(data)

        self.assertEqual(out["open_time"], [dt(2026, 1, 30), dt(2026, 2, 1)])
        self.assertEqual(out["open"], [10.0, 20.0])
        self.assertEqual(out["high"], [13.0, 24.0])
        self.assertEqual(out["low"], [8.0, 18.0])
        self.assertEqual(out["close"], [12.0, 23.0])
        self.assertEqual(out["volume"], [3.0, 7.0])
        self.assertAlmostEqual(out["taker_buy_base_asset_volume"][0], 1.2)
        self.assertAlmostEqual(out["taker_buy_base_asset_volume"][1], 3.5)

        self.assertFalse(prov[0]["starts_on_calendar_day_1"])
        self.assertTrue(prov[0]["ends_on_calendar_month_end"])
        self.assertTrue(prov[1]["starts_on_calendar_day_1"])
        self.assertFalse(prov[1]["ends_on_calendar_month_end"])

    def test_deterministic_logical_hash(self):
        data = {
            "open_time": [dt(2026, 1, 1)],
            "open": [1.0],
            "high": [2.0],
            "low": [0.5],
            "close": [1.5],
            "volume": [10.0],
            "taker_buy_base_asset_volume": [6.0],
        }
        a, _ = aggregate_calendar_month(data)
        b, _ = aggregate_calendar_month(data)
        self.assertEqual(logical_sha256(a), logical_sha256(b))

    def test_rejects_non_monotonic_daily_input(self):
        data = {
            "open_time": [dt(2026, 1, 2), dt(2026, 1, 1)],
            "open": [1.0, 1.0],
            "high": [2.0, 2.0],
            "low": [0.5, 0.5],
            "close": [1.5, 1.5],
            "volume": [10.0, 10.0],
            "taker_buy_base_asset_volume": [6.0, 6.0],
        }
        with self.assertRaises(ValueError):
            aggregate_calendar_month(data)


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timedelta, timezone

from tools.market_map_offline_core import (
    Candle,
    Kernel,
    MID_LEN,
    SLOW_LEN,
    ema,
)


def candles(n=60):
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    out = []
    for i in range(n):
        p = 100.0 + i
        out.append(
            Candle(
                int((base + timedelta(days=30 * i)).timestamp() * 1_000_000),
                p - 0.5,
                p + 1.0,
                p - 1.0,
                p,
                1000.0 + i,
            )
        )
    return out


class MarketMapRegimeBasisTests(unittest.TestCase):
    def test_defaults_remain_50_200(self):
        xs = candles()
        k = Kernel(xs, xs, xs, xs, "1M")
        self.assertEqual(k.mid_len, MID_LEN)
        self.assertEqual(k.slow_len, SLOW_LEN)
        self.assertEqual(k.mid, ema([x.c for x in xs], MID_LEN))
        self.assertEqual(k.slow, ema([x.c for x in xs], SLOW_LEN))

    def test_monthly_candidate_can_use_12_46_without_changing_defaults(self):
        xs = candles()
        k = Kernel(xs, xs, xs, xs, "1M", mid_len=12, slow_len=46)
        self.assertEqual(k.mid_len, 12)
        self.assertEqual(k.slow_len, 46)
        self.assertEqual(k.mid, ema([x.c for x in xs], 12))
        self.assertEqual(k.slow, ema([x.c for x in xs], 46))

        default = Kernel(xs, xs, xs, xs, "1M")
        self.assertEqual(default.mid_len, 50)
        self.assertEqual(default.slow_len, 200)

    def test_rejects_invalid_basis(self):
        xs = candles()
        with self.assertRaises(ValueError):
            Kernel(xs, xs, xs, xs, "1M", mid_len=46, slow_len=12)
        with self.assertRaises(ValueError):
            Kernel(xs, xs, xs, xs, "1M", mid_len=0, slow_len=46)


if __name__ == "__main__":
    unittest.main()

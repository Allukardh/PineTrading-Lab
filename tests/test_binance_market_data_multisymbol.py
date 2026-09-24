from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.binance_market_data.core import DataValidationError
from tools.binance_market_data.downloader import BinanceArchiveClient
from tools.binance_market_data.pipeline import load_config, run_config


class MultiSymbolTests(unittest.TestCase):
    def test_first_available_month_discovery_uses_checksum_sidecars(self):
        client = BinanceArchiveClient("https://example.invalid")
        digest = "a" * 64

        def fake_get(url: str):
            if "-2020-09.zip.CHECKSUM" in url:
                return f"{digest}  ETHUSDT-1d-2020-09.zip\n", 200
            return None, 404

        client._get_text_optional = fake_get  # type: ignore[method-assign]
        self.assertEqual(
            client.find_first_available_month(
                market="spot", symbol="ETHUSDT", timeframe="1d",
                search_start="2020-07", search_end="2020-10",
            ),
            "2020-09",
        )

    def test_auto_start_requires_discovery_lower_bound(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cfg.json"
            p.write_text(json.dumps({
                "market": "spot",
                "symbols": [{
                    "symbol": "ETHUSDT",
                    "start_month": "auto",
                    "end_month": "auto",
                    "timeframes": ["1d"],
                }],
            }), encoding="utf-8")
            with self.assertRaises(DataValidationError):
                load_config(p)

    def test_symbol_filter_runs_only_requested_symbol(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "cfg.json"
            p.write_text(json.dumps({
                "market": "spot",
                "discovery_start_month": "2017-01",
                "symbols": [
                    {"symbol": "ETHUSDT", "start_month": "2017-08", "timeframes": ["1d"]},
                    {"symbol": "LTCUSDT", "start_month": "2017-12", "timeframes": ["1d"]},
                ],
            }), encoding="utf-8")

            called = []

            def fake_run_dataset(*, cfg, symbol_cfg, timeframe, data_root, client):
                called.append(symbol_cfg["symbol"])
                return {
                    "symbol": symbol_cfg["symbol"], "market": "spot", "timeframe": timeframe,
                    "resolved_start_month": symbol_cfg["start_month"],
                    "first_date": "2020-01-01T00:00:00Z", "last_date": "2020-01-01T00:00:00Z",
                    "candles": 1, "source_file_count": 1, "duplicates_found": 0, "gaps_found": 0,
                    "open_time_discontinuities_found": 0, "timestamp_units": {"ms": 1},
                    "timestamp_epoch_anomalies_found": 0, "close_time_conventions": {"boundary_minus_tick": 1},
                    "close_time_anomalies_found": 0, "files_missing": [],
                    "checksum_status": {"verified": 1, "missing": 0, "mismatch": 0},
                    "dataset_sha256": "a" * 64, "final_size_bytes": 1, "status": "ok",
                    "output_file": f"{symbol_cfg['symbol']}_{timeframe}.parquet",
                }

            with patch("tools.binance_market_data.pipeline.run_dataset", side_effect=fake_run_dataset):
                inv = run_config(p, root / "out", symbol_filter="ltcusdt")

            self.assertEqual(called, ["LTCUSDT"])
            self.assertEqual(list(inv["symbol_discovery"]), ["LTCUSDT"])
            self.assertTrue((root / "out/spot/LTCUSDT/manifests/LTCUSDT_inventory.json").is_file())

    def test_unknown_symbol_filter_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cfg.json"
            p.write_text(json.dumps({
                "market": "spot",
                "discovery_start_month": "2017-01",
                "symbols": [{"symbol": "ETHUSDT", "start_month": "2017-08", "timeframes": ["1d"]}],
            }), encoding="utf-8")
            with self.assertRaises(DataValidationError):
                run_config(p, Path(td) / "out", symbol_filter="NOPEUSDT")


if __name__ == "__main__":
    unittest.main()

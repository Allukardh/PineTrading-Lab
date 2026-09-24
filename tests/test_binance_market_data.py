from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
import zipfile
from decimal import Decimal
from pathlib import Path

from tools.binance_market_data import PIPELINE_VERSION, SCHEMA_VERSION
from tools.binance_market_data.core import (
    DataValidationError, expected_timestamp_unit_for_us, infer_timestamp_unit, iter_months, latest_publishable_month,
    parse_checksum_text, parse_kline_row, sha256_file, timestamp_to_us, validate_candle_duration, verify_checksum,
)
from tools.binance_market_data.storage import (
    build_manifest, manifest_is_current, source_fingerprint, write_json, write_parquet,
)
from tools.binance_market_data.validation import deduplicate, detect_gaps, read_zip_klines


ROW_MS = [
    "1609459200000", "29000.00000000", "29100.00000000", "28900.00000000", "29050.00000000",
    "10.00000000", "1609460099999", "290500.00000000", "100", "6.00000000", "174300.00000000", "0"
]
ROW_US = [
    "1735689600000000", "93000.00000000", "93100.00000000", "92900.00000000", "93050.00000000",
    "5.00000000", "1735690499999999", "465250.00000000", "80", "3.00000000", "279150.00000000", "0"
]


class CoreTests(unittest.TestCase):
    def test_month_iterator(self):
        self.assertEqual(list(iter_months("2024-11", "2025-02")), ["2024-11", "2024-12", "2025-01", "2025-02"])

    def test_latest_publishable_month_respects_first_monday(self):
        self.assertEqual(latest_publishable_month(datetime(2026, 9, 23, tzinfo=timezone.utc)), "2026-08")
        self.assertEqual(latest_publishable_month(datetime(2026, 10, 1, tzinfo=timezone.utc)), "2026-08")
        self.assertEqual(latest_publishable_month(datetime(2026, 10, 5, tzinfo=timezone.utc)), "2026-09")

    def test_timestamp_units(self):
        self.assertEqual(infer_timestamp_unit(1609459200000), "ms")
        self.assertEqual(infer_timestamp_unit(1735689600000000), "us")
        self.assertEqual(timestamp_to_us(1609459200000), (1609459200000000, "ms"))
        self.assertEqual(timestamp_to_us(1735689600000000), (1735689600000000, "us"))
        value_us, unit = timestamp_to_us(1735689600000)
        self.assertEqual(unit, "ms")
        self.assertEqual(expected_timestamp_unit_for_us(value_us), "us")
        value_us, unit = timestamp_to_us(1609459200000000)
        self.assertEqual(unit, "us")
        self.assertEqual(expected_timestamp_unit_for_us(value_us), "ms")
        with self.assertRaises(DataValidationError):
            timestamp_to_us(12345)

    def test_pre_transition_ms_candle_can_close_after_epoch_switch(self):
        row = parse_kline_row([
            "1735516800000", "93000", "93100", "92900", "93050", "5",
            "1735775999999", "465250", "80", "3", "279150", "0"
        ], source_file="BTCUSDT-3d-2024-12.zip")
        self.assertEqual(row["source_timestamp_unit"], "ms")
        self.assertLess(row["open_time_us"], 1_735_689_600_000_000)
        self.assertGreater(row["close_time_us"], 1_735_689_600_000_000)
        self.assertEqual(validate_candle_duration(row, "3d"), "boundary_minus_tick")

    def test_parse_preserves_taker_and_trade_fields(self):
        row = parse_kline_row(ROW_MS, source_file="x.zip")
        self.assertEqual(row["open_time_raw"], 1609459200000)
        self.assertEqual(row["close_time_raw"], 1609460099999)
        self.assertEqual(row["number_of_trades"], 100)
        self.assertEqual(row["taker_buy_base_asset_volume"], Decimal("6.00000000"))
        self.assertEqual(row["taker_buy_quote_asset_volume"], Decimal("174300.00000000"))
        self.assertEqual(row["source_timestamp_unit"], "ms")

    def test_schema_field_count_rejected(self):
        with self.assertRaises(DataValidationError):
            parse_kline_row(ROW_MS[:-1], source_file="bad.zip")

    def test_legacy_exact_boundary_close_time_is_classified(self):
        legacy = list(ROW_MS)
        legacy[0] = "1504712700000"
        legacy[6] = "1504713600000"
        row = parse_kline_row(legacy, source_file="BTCUSDT-15m-2017-09.zip")
        self.assertEqual(validate_candle_duration(row, "15m"), "exact_boundary")

    def test_legacy_early_close_is_preserved_and_classified(self):
        legacy = list(ROW_MS)
        legacy[0] = "1513599300000"
        legacy[6] = "1513600153419"
        row = parse_kline_row(legacy, source_file="BTCUSDT-15m-2017-12.zip")
        self.assertEqual(validate_candle_duration(row, "15m"), "early_close")

    def test_verified_pre_open_close_time_is_preserved_and_classified(self):
        legacy = list(ROW_MS)
        legacy[0] = "1608559200000"
        legacy[6] = "1608558440521"
        row = parse_kline_row(legacy, source_file="BTCUSDT-15m-2020-12.zip")
        self.assertEqual(row["close_time_raw"], 1608558440521)
        self.assertEqual(validate_candle_duration(row, "15m"), "pre_open")

    def test_checksum(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.zip"
            p.write_bytes(b"abc")
            digest = hashlib.sha256(b"abc").hexdigest()
            text = f"{digest}  x.zip\n"
            self.assertEqual(parse_checksum_text(text), (digest, "x.zip"))
            self.assertTrue(verify_checksum(p, text))

    def test_zip_parsing_and_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            good = Path(td) / "good.zip"
            with zipfile.ZipFile(good, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("good.csv", ",".join(ROW_MS) + "\n")
            rows = read_zip_klines(good, "15m")
            self.assertEqual(len(rows), 1)
            bad = Path(td) / "bad.zip"
            bad.write_bytes(b"not a zip")
            with self.assertRaises(DataValidationError):
                read_zip_klines(bad, "15m")

    def test_dedup_and_conflict(self):
        a = parse_kline_row(ROW_MS, source_file="a.zip")
        b = dict(a, source_file="b.zip")
        unique, dupes, conflicts = deduplicate([a, b])
        self.assertEqual(len(unique), 1)
        self.assertEqual(dupes, 1)
        self.assertEqual(conflicts, [])
        c = dict(a, close=Decimal("29060"), source_file="c.zip")
        _, dupes, conflicts = deduplicate([a, c])
        self.assertEqual(dupes, 1)
        self.assertEqual(len(conflicts), 1)

    def test_gap_detection(self):
        a = parse_kline_row(ROW_MS, source_file="a.zip")
        b = dict(a, open_time_us=a["open_time_us"] + 3 * 900_000_000, close_time_us=a["close_time_us"] + 3 * 900_000_000)
        gaps, discontinuities = detect_gaps([a, b], "15m")
        self.assertEqual(gaps[0]["missing_candles"], 2)
        self.assertEqual(discontinuities, [])

    def test_off_grid_restart_is_reported_as_finding(self):
        a = parse_kline_row(ROW_MS, source_file="a.zip")
        b = dict(
            a,
            open_time_us=a["open_time_us"] + 121_394_789_000,
            close_time_us=a["close_time_us"] + 121_394_789_000,
        )
        gaps, discontinuities = detect_gaps([a, b], "15m")
        self.assertEqual(gaps, [])
        self.assertEqual(len(discontinuities), 1)
        self.assertEqual(discontinuities[0]["delta_us"], 121_394_789_000)


    def test_fingerprint_and_manifest_idempotency(self):
        sources = [{"filename":"a.zip","zip_sha256":"a"*64,"checksum_expected":"a"*64,"checksum_status":"verified"}]
        fp = source_fingerprint(sources)
        missing = ["BTCUSDT-15m-2026-08.zip"]
        fp_missing = source_fingerprint(sources, missing_files=missing)
        self.assertNotEqual(fp, fp_missing)
        self.assertEqual(fp_missing, source_fingerprint(sources, missing_files=list(reversed(missing))))
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pq = td / "x.parquet"
            pq.write_bytes(b"parquet-placeholder")
            mf = td / "x.json"
            write_json(mf, {
                "pipeline_version": PIPELINE_VERSION,
                "schema_version": SCHEMA_VERSION,
                "source_fingerprint_sha256": fp,
                "dataset_sha256": sha256_file(pq),
            })
            self.assertTrue(manifest_is_current(mf, pq, fp))
            self.assertFalse(manifest_is_current(mf, pq, fp_missing))
            pq.write_bytes(b"changed")
            self.assertFalse(manifest_is_current(mf, pq, fp))

    def test_manifest_required_fields(self):
        row = parse_kline_row(ROW_US, source_file="x.zip")
        row["source_close_time_convention"] = validate_candle_duration(row, "15m")
        with tempfile.TemporaryDirectory() as td:
            pq = Path(td) / "BTCUSDT_15m.parquet"
            pq.write_bytes(b"x")
            src = [{"filename":"x.zip","zip_sha256":"f"*64,"size_bytes":1,"checksum_expected":"f"*64,"checksum_status":"verified"}]
            fp = source_fingerprint(src)
            m = build_manifest(
                symbol="BTCUSDT", market="spot", timeframe="15m", source_url="https://data.binance.vision/",
                rows=[row], source_files=src, missing_files=[], duplicate_count=0, conflicts=[], gaps=[],
                discontinuities=[], parquet_path=pq, fingerprint=fp,
            )
            for key in ("symbol","market","timeframe","data_source","first_date","last_date","candles",
                        "source_file_count","duplicates_found","gaps_found","open_time_discontinuities_found",
                        "timestamp_units","timestamp_epoch_anomalies_found",
                        "files_missing","checksum_status","dataset_sha256","final_size_bytes",
                        "pipeline_version","schema_version"):
                self.assertIn(key, m)

            finding = build_manifest(
                symbol="BTCUSDT", market="spot", timeframe="15m", source_url="https://data.binance.vision/",
                rows=[row], source_files=src, missing_files=[], duplicate_count=0, conflicts=[], gaps=[],
                discontinuities=[{"after_open_time":"2018-02-08T00:15:00Z","before_open_time":"2018-02-09T09:58:14.789000Z",
                                  "delta_us":121394789000,"expected_us":900000000}],
                parquet_path=pq, fingerprint=fp,
            )
            self.assertEqual(finding["status"], "ok_with_findings")
            self.assertEqual(finding["open_time_discontinuities_found"], 1)

            legacy_2025 = parse_kline_row([
                "1735689600000", "93000", "93100", "92900", "93050", "5",
                "1735948799999", "465250", "80", "3", "279150", "0"
            ], source_file="BTCUSDT-3d-2025-01.zip")
            legacy_2025["source_close_time_convention"] = validate_candle_duration(legacy_2025, "3d")
            unit_finding = build_manifest(
                symbol="BTCUSDT", market="spot", timeframe="3d", source_url="https://data.binance.vision/",
                rows=[legacy_2025], source_files=src, missing_files=[], duplicate_count=0, conflicts=[], gaps=[],
                discontinuities=[], parquet_path=pq, fingerprint=fp,
            )
            self.assertEqual(unit_finding["status"], "ok_with_findings")
            self.assertEqual(unit_finding["timestamp_epoch_anomalies_found"], 1)
            self.assertEqual(unit_finding["timestamp_units"], {"ms": 1})

    def test_parquet_consolidation_when_pyarrow_available(self):
        try:
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow not installed in local runtime")
        row = parse_kline_row(ROW_US, source_file="x.zip")
        row["source_close_time_convention"] = validate_candle_duration(row, "15m")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.parquet"
            write_parquet([row], p, symbol="BTCUSDT", market="spot", timeframe="15m")
            table = pq.read_table(p)
            self.assertEqual(table.num_rows, 1)
            self.assertIn("open_time_raw", table.column_names)
            self.assertIn("close_time_raw", table.column_names)
            self.assertIn("taker_buy_base_asset_volume", table.column_names)
            self.assertIn("source_timestamp_unit", table.column_names)
            self.assertIn("source_close_time_convention", table.column_names)


if __name__ == "__main__":
    unittest.main()

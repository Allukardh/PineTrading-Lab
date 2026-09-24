from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

from .core import DataValidationError, INTERVAL_US, iso_utc_from_us, parse_kline_row, validate_candle_duration


def read_zip_klines(path: Path, timeframe: str) -> list[dict]:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                raise DataValidationError(f"{path.name}: corrupt member {bad}")
            csv_members = [name for name in zf.namelist() if not name.endswith("/") and name.lower().endswith(".csv")]
            if len(csv_members) != 1:
                raise DataValidationError(f"{path.name}: expected exactly one CSV member, found {len(csv_members)}")
            with zf.open(csv_members[0], "r") as raw:
                reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
                rows: list[dict] = []
                for line_no, row in enumerate(reader, 1):
                    if not row:
                        continue
                    try:
                        item = parse_kline_row(row, source_file=path.name)
                        validate_candle_duration(item, timeframe)
                    except Exception as exc:
                        if isinstance(exc, DataValidationError):
                            raise DataValidationError(f"{path.name}:{line_no}: {exc}") from exc
                        raise
                    rows.append(item)
                return rows
    except zipfile.BadZipFile as exc:
        raise DataValidationError(f"{path.name}: invalid ZIP archive") from exc


def deduplicate(rows: Iterable[dict]) -> tuple[list[dict], int, list[dict]]:
    by_open: dict[int, dict] = {}
    duplicate_count = 0
    conflicts: list[dict] = []
    compare_fields = [
        "open_time_raw", "open_time_us", "open", "high", "low", "close", "volume", "close_time_raw", "close_time_us",
        "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume", "ignore",
    ]
    for row in rows:
        key = row["open_time_us"]
        existing = by_open.get(key)
        if existing is None:
            by_open[key] = row
            continue
        duplicate_count += 1
        if any(existing[name] != row[name] for name in compare_fields):
            conflicts.append({
                "open_time": iso_utc_from_us(key),
                "first_source": existing["source_file"],
                "second_source": row["source_file"],
            })
    return [by_open[k] for k in sorted(by_open)], duplicate_count, conflicts


def detect_gaps(rows: Sequence[dict], timeframe: str) -> tuple[list[dict], list[dict]]:
    expected = INTERVAL_US[timeframe]
    gaps: list[dict] = []
    discontinuities: list[dict] = []
    for prev, cur in zip(rows, rows[1:]):
        delta = cur["open_time_us"] - prev["open_time_us"]
        if delta == expected:
            continue
        base = {
            "after_open_time": iso_utc_from_us(prev["open_time_us"]),
            "before_open_time": iso_utc_from_us(cur["open_time_us"]),
            "delta_us": delta,
            "expected_us": expected,
        }
        if delta > expected and delta % expected == 0:
            gaps.append({**base, "missing_candles": delta // expected - 1})
        else:
            discontinuities.append(base)
    return gaps, discontinuities



from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from . import PIPELINE_VERSION, SCHEMA_VERSION

KLINE_COLUMNS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
)

DECIMAL_COLUMNS = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
)

INTERVAL_US = {
    "15m": 15 * 60 * 1_000_000,
    "1h": 60 * 60 * 1_000_000,
    "4h": 4 * 60 * 60 * 1_000_000,
    "1d": 24 * 60 * 60 * 1_000_000,
    "3d": 3 * 24 * 60 * 60 * 1_000_000,
    "1w": 7 * 24 * 60 * 60 * 1_000_000,
}


class DataValidationError(ValueError):
    pass


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_checksum_text(text: str) -> tuple[str, str | None]:
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    parts = line.split()
    if not parts or len(parts[0]) != 64 or any(c not in "0123456789abcdefABCDEF" for c in parts[0]):
        raise DataValidationError("invalid Binance CHECKSUM sidecar")
    filename = parts[-1].lstrip("*") if len(parts) >= 2 else None
    return parts[0].lower(), filename


def verify_checksum(path: Path, checksum_text: str) -> bool:
    expected, filename = parse_checksum_text(checksum_text)
    if filename and Path(filename).name != path.name:
        raise DataValidationError(f"checksum filename mismatch: expected {path.name}, sidecar names {filename}")
    return sha256_file(path) == expected


def infer_timestamp_unit(raw: int) -> str:
    # Contemporary Unix milliseconds are ~1e12; microseconds are ~1e15.
    if 100_000_000_000 <= raw < 100_000_000_000_000:
        return "ms"
    if 100_000_000_000_000 <= raw < 100_000_000_000_000_000:
        return "us"
    raise DataValidationError(f"unsupported/implausible timestamp magnitude: {raw}")


def timestamp_to_us(raw: int) -> tuple[int, str]:
    unit = infer_timestamp_unit(raw)
    value_us = raw * 1000 if unit == "ms" else raw
    switch_us = 1_735_689_600_000_000  # 2025-01-01T00:00:00Z
    expected = "us" if value_us >= switch_us else "ms"
    if unit != expected:
        raise DataValidationError(
            f"timestamp unit {unit} conflicts with Binance SPOT archive epoch rule; expected {expected}"
        )
    return value_us, unit


def iso_utc_from_us(value_us: int) -> str:
    return datetime.fromtimestamp(value_us / 1_000_000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def latest_publishable_month(now: datetime | None = None) -> str:
    """Latest month expected to have an official monthly archive.

    Binance documents monthly publication on the first Monday of the following month.
    Before that Monday, use the month before the immediately previous calendar month.
    """
    now = now or datetime.now(timezone.utc)
    first = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    days_to_monday = (7 - first.weekday()) % 7
    first_monday_day = 1 + days_to_monday
    y, m = previous_month(now.year, now.month)
    if now.day < first_monday_day:
        y, m = previous_month(y, m)
    return f"{y:04d}-{m:02d}"


def iter_months(start: str, end: str) -> Iterator[str]:
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    cur_y, cur_m = sy, sm
    while (cur_y, cur_m) <= (ey, em):
        yield f"{cur_y:04d}-{cur_m:02d}"
        cur_m += 1
        if cur_m == 13:
            cur_y += 1
            cur_m = 1


def _decimal(value: str, name: str) -> Decimal:
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise DataValidationError(f"invalid decimal in {name}: {value!r}") from exc
    if not d.is_finite():
        raise DataValidationError(f"non-finite decimal in {name}: {value!r}")
    return d


def parse_kline_row(row: Sequence[str], *, source_file: str) -> dict:
    if len(row) != 12:
        raise DataValidationError(f"{source_file}: expected 12 kline columns, got {len(row)}")

    open_raw = int(row[0])
    close_raw = int(row[6])
    open_us, open_unit = timestamp_to_us(open_raw)
    close_us, close_unit = timestamp_to_us(close_raw)
    if open_unit != close_unit:
        raise DataValidationError(f"{source_file}: mixed timestamp units inside one kline row")

    values = {name: _decimal(row[idx], name) for idx, name in enumerate(KLINE_COLUMNS) if name in DECIMAL_COLUMNS}
    try:
        trades = int(row[8])
    except ValueError as exc:
        raise DataValidationError(f"{source_file}: invalid number_of_trades {row[8]!r}") from exc

    if trades < 0:
        raise DataValidationError(f"{source_file}: negative number_of_trades")
    for name in ("volume", "quote_asset_volume", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume"):
        if values[name] < 0:
            raise DataValidationError(f"{source_file}: negative {name}")
    if min(values["open"], values["close"]) < values["low"] or max(values["open"], values["close"]) > values["high"]:
        raise DataValidationError(f"{source_file}: OHLC values outside [low, high]")
    if values["low"] > values["high"]:
        raise DataValidationError(f"{source_file}: low > high")
    if close_us < open_us:
        raise DataValidationError(f"{source_file}: close_time precedes open_time")

    return {
        "open_time_raw": open_raw,
        "open_time_us": open_us,
        "open": values["open"],
        "high": values["high"],
        "low": values["low"],
        "close": values["close"],
        "volume": values["volume"],
        "close_time_raw": close_raw,
        "close_time_us": close_us,
        "quote_asset_volume": values["quote_asset_volume"],
        "number_of_trades": trades,
        "taker_buy_base_asset_volume": values["taker_buy_base_asset_volume"],
        "taker_buy_quote_asset_volume": values["taker_buy_quote_asset_volume"],
        "ignore": values["ignore"],
        "source_file": source_file,
        "source_timestamp_unit": open_unit,
    }


def validate_candle_duration(record: dict, timeframe: str) -> None:
    expected = INTERVAL_US[timeframe]
    unit_tick = 1000 if record["source_timestamp_unit"] == "ms" else 1
    expected_close = record["open_time_us"] + expected - unit_tick
    if record["close_time_us"] != expected_close:
        raise DataValidationError(
            f"{record['source_file']}: unexpected close_time for {timeframe}: "
            f"open={record['open_time_us']} close={record['close_time_us']} expected={expected_close}"
        )



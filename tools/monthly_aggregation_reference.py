#!/usr/bin/env python3
"""Deterministic UTC calendar-month aggregation for Suite 0.2 research.

Input contract:
- accepted 1D Binance research dataset loaded through load_dataset()
- timestamps are preserved from actual accepted daily candles
- no missing day/month is synthesized

Monthly OHLCV:
- open_time = first available accepted daily candle timestamp in that UTC month
- open = first daily open
- high = max daily high
- low = min daily low
- close = last daily close
- volume = sum daily volume
- taker_buy_base_asset_volume = sum daily taker-buy base volume

The first listing month may therefore be partial by construction. That is
provenance, not an error.
"""
from __future__ import annotations

import hashlib
import json
from calendar import monthrange
from pathlib import Path
from typing import Sequence


FIELDS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "taker_buy_base_asset_volume",
)


def _validate_daily(data: dict) -> int:
    missing = [f for f in FIELDS if f not in data]
    if missing:
        raise ValueError(f"missing daily fields: {missing}")

    n = len(data["open_time"])
    if not n:
        return 0
    for f in FIELDS[1:]:
        if len(data[f]) != n:
            raise ValueError(f"length mismatch for {f}")

    times = data["open_time"]
    for i in range(1, n):
        if times[i] <= times[i - 1]:
            raise ValueError("daily open_time must be strictly increasing")
    return n


def aggregate_calendar_month(data: dict) -> tuple[dict, list[dict]]:
    n = _validate_daily(data)
    out = {f: [] for f in FIELDS}
    provenance: list[dict] = []
    if n == 0:
        return out, provenance

    groups: list[tuple[int, int, int, int]] = []
    start = 0
    times: Sequence = data["open_time"]

    for i in range(1, n + 1):
        boundary = (
            i == n
            or (times[i].year, times[i].month)
            != (times[start].year, times[start].month)
        )
        if not boundary:
            continue
        groups.append((start, i, times[start].year, times[start].month))
        start = i

    for start, end, year, month in groups:
        out["open_time"].append(times[start])
        out["open"].append(float(data["open"][start]))
        out["high"].append(max(float(x) for x in data["high"][start:end]))
        out["low"].append(min(float(x) for x in data["low"][start:end]))
        out["close"].append(float(data["close"][end - 1]))
        out["volume"].append(sum(float(x) for x in data["volume"][start:end]))
        out["taker_buy_base_asset_volume"].append(
            sum(float(x) for x in data["taker_buy_base_asset_volume"][start:end])
        )

        first_day = times[start].day
        last_day = times[end - 1].day
        expected_days = monthrange(year, month)[1]
        provenance.append(
            {
                "year": year,
                "month": month,
                "source_rows": end - start,
                "first_source_day": first_day,
                "last_source_day": last_day,
                "calendar_days": expected_days,
                "starts_on_calendar_day_1": first_day == 1,
                "ends_on_calendar_month_end": last_day == expected_days,
            }
        )

    return out, provenance


def logical_sha256(data: dict) -> str:
    """Stable content digest independent of Parquet writer metadata."""
    payload = []
    for i, t in enumerate(data["open_time"]):
        payload.append(
            [
                t.isoformat(),
                format(float(data["open"][i]), ".17g"),
                format(float(data["high"][i]), ".17g"),
                format(float(data["low"][i]), ".17g"),
                format(float(data["close"][i]), ".17g"),
                format(float(data["volume"][i]), ".17g"),
                format(float(data["taker_buy_base_asset_volume"][i]), ".17g"),
            ]
        )
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def write_monthly_parquet(data: dict, path: Path) -> str:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError(
            "pyarrow is required; install requirements-market-data.txt"
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "open_time": data["open_time"],
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data["volume"],
            "taker_buy_base_asset_volume": data[
                "taker_buy_base_asset_volume"
            ],
        }
    )
    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=False,
        write_statistics=True,
    )

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

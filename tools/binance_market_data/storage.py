from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Sequence

from . import PIPELINE_VERSION, SCHEMA_VERSION
from .core import INTERVAL_US, iso_utc_from_us, sha256_file, sha256_json


def source_fingerprint(source_files: Sequence[dict]) -> str:
    minimal = [
        {
            "filename": x["filename"],
            "zip_sha256": x["zip_sha256"],
            "checksum_expected": x.get("checksum_expected"),
            "checksum_status": x["checksum_status"],
        }
        for x in sorted(source_files, key=lambda y: y["filename"])
    ]
    return sha256_json(minimal)


def manifest_is_current(manifest_path: Path, parquet_path: Path, fingerprint: str) -> bool:
    if not manifest_path.is_file() or not parquet_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if manifest.get("pipeline_version") != PIPELINE_VERSION or manifest.get("schema_version") != SCHEMA_VERSION:
        return False
    if manifest.get("source_fingerprint_sha256") != fingerprint:
        return False
    expected_hash = manifest.get("dataset_sha256")
    return bool(expected_hash) and sha256_file(parquet_path) == expected_hash


def write_parquet(rows: Sequence[dict], path: Path, *, symbol: str, market: str, timeframe: str) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("pyarrow is required for Parquet consolidation; install requirements-market-data.txt") from exc

    dec = pa.decimal128(38, 18)
    data = {
        "symbol": pa.array([symbol] * len(rows), type=pa.string()),
        "market": pa.array([market] * len(rows), type=pa.string()),
        "timeframe": pa.array([timeframe] * len(rows), type=pa.string()),
        "open_time_raw": pa.array([r["open_time_raw"] for r in rows], type=pa.int64()),
        "open_time": pa.array([r["open_time_us"] for r in rows], type=pa.timestamp("us", tz="UTC")),
        "open": pa.array([r["open"] for r in rows], type=dec),
        "high": pa.array([r["high"] for r in rows], type=dec),
        "low": pa.array([r["low"] for r in rows], type=dec),
        "close": pa.array([r["close"] for r in rows], type=dec),
        "volume": pa.array([r["volume"] for r in rows], type=dec),
        "close_time_raw": pa.array([r["close_time_raw"] for r in rows], type=pa.int64()),
        "close_time": pa.array([r["close_time_us"] for r in rows], type=pa.timestamp("us", tz="UTC")),
        "quote_asset_volume": pa.array([r["quote_asset_volume"] for r in rows], type=dec),
        "number_of_trades": pa.array([r["number_of_trades"] for r in rows], type=pa.int64()),
        "taker_buy_base_asset_volume": pa.array([r["taker_buy_base_asset_volume"] for r in rows], type=dec),
        "taker_buy_quote_asset_volume": pa.array([r["taker_buy_quote_asset_volume"] for r in rows], type=dec),
        "ignore": pa.array([r["ignore"] for r in rows], type=dec),
        "source_file": pa.array([r["source_file"] for r in rows], type=pa.string()),
        "source_timestamp_unit": pa.array([r["source_timestamp_unit"] for r in rows], type=pa.string()),
        "source_close_time_convention": pa.array([r.get("source_close_time_convention", "unclassified") for r in rows], type=pa.string()),
    }
    table = pa.table(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(table, tmp, compression="zstd", use_dictionary=True, write_statistics=True)
    os.replace(tmp, path)


def build_manifest(
    *, symbol: str, market: str, timeframe: str, source_url: str, rows: Sequence[dict], source_files: Sequence[dict],
    missing_files: Sequence[str], duplicate_count: int, conflicts: Sequence[dict], gaps: Sequence[dict],
    discontinuities: Sequence[dict], parquet_path: Path, fingerprint: str,
) -> dict:
    checksum_counts = {"verified": 0, "missing": 0, "mismatch": 0}
    for item in source_files:
        status = item["checksum_status"]
        checksum_counts[status] = checksum_counts.get(status, 0) + 1
    first = iso_utc_from_us(rows[0]["open_time_us"]) if rows else None
    last = iso_utc_from_us(rows[-1]["open_time_us"]) if rows else None
    dataset_hash = sha256_file(parquet_path) if parquet_path.is_file() else None
    size = parquet_path.stat().st_size if parquet_path.is_file() else 0
    close_time_conventions = Counter(r.get("source_close_time_convention", "unclassified") for r in rows)
    anomalous_close_rows = [
        r for r in rows
        if r.get("source_close_time_convention") not in ("boundary_minus_tick", "exact_boundary")
    ]
    close_time_anomaly_samples = [
        {
            "open_time": iso_utc_from_us(r["open_time_us"]),
            "close_time": iso_utc_from_us(r["close_time_us"]),
            "source_file": r["source_file"],
            "convention": r.get("source_close_time_convention", "unclassified"),
            "delta_to_boundary_us": r["close_time_us"] - (r["open_time_us"] + INTERVAL_US[timeframe]),
        }
        for r in anomalous_close_rows[:100]
    ]
    status = "ok"
    if conflicts:
        status = "invalid"
    elif missing_files or gaps or discontinuities or anomalous_close_rows or checksum_counts.get("missing", 0):
        status = "ok_with_findings"
    return {
        "pipeline_version": PIPELINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "symbol": symbol,
        "market": market,
        "timeframe": timeframe,
        "data_source": source_url,
        "first_date": first,
        "last_date": last,
        "candles": len(rows),
        "source_file_count": len(source_files),
        "duplicates_found": duplicate_count,
        "conflicting_duplicates": list(conflicts),
        "gaps_found": len(gaps),
        "gaps": list(gaps),
        "open_time_discontinuities_found": len(discontinuities),
        "unexpected_discontinuities": list(discontinuities),
        "close_time_conventions": dict(sorted(close_time_conventions.items())),
        "close_time_anomalies_found": len(anomalous_close_rows),
        "close_time_anomaly_samples": close_time_anomaly_samples,
        "files_missing": list(missing_files),
        "checksum_status": checksum_counts,
        "source_fingerprint_sha256": fingerprint,
        "dataset_sha256": dataset_hash,
        "final_size_bytes": size,
        "output_file": parquet_path.name,
        "status": status,
        "source_files": list(source_files),
    }


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)

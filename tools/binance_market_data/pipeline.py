from __future__ import annotations

import json
from pathlib import Path

from . import PIPELINE_VERSION, SCHEMA_VERSION
from .core import DataValidationError, INTERVAL_US, iter_months, latest_publishable_month
from .storage import build_manifest, manifest_is_current, source_fingerprint, write_json, write_parquet
from .validation import deduplicate, detect_gaps, read_zip_klines
from .downloader import BinanceArchiveClient


def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("market") != "spot":
        raise DataValidationError("initial pipeline supports market=spot only")
    if not cfg.get("symbols"):
        raise DataValidationError("config has no symbols")
    for item in cfg["symbols"]:
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            raise DataValidationError("symbol entry is missing symbol")
        if not item.get("start_month"):
            raise DataValidationError(f"{symbol}: start_month is required")
        timeframes = item.get("timeframes") or []
        if not timeframes:
            raise DataValidationError(f"{symbol}: no timeframes configured")
        unknown = sorted(set(timeframes) - set(INTERVAL_US))
        if unknown:
            raise DataValidationError(f"{symbol}: unsupported timeframes: {', '.join(unknown)}")
    return cfg


def run_dataset(*, cfg: dict, symbol_cfg: dict, timeframe: str, data_root: Path, client: BinanceArchiveClient) -> dict:
    market = cfg["market"]
    symbol = symbol_cfg["symbol"].upper()
    start_month = symbol_cfg["start_month"]
    end_month = symbol_cfg.get("end_month") or latest_publishable_month()
    if end_month == "auto":
        end_month = latest_publishable_month()

    symbol_root = data_root / market / symbol
    raw_dir = symbol_root / "raw"
    consolidated_dir = symbol_root / "consolidated"
    manifest_dir = symbol_root / "manifests"
    report_dir = symbol_root / "reports"
    parquet_path = consolidated_dir / f"{symbol}_{timeframe}.parquet"
    manifest_path = manifest_dir / f"{symbol}_{timeframe}.manifest.json"
    report_path = report_dir / f"{symbol}_{timeframe}.report.json"

    source_files: list[dict] = []
    missing_files: list[str] = []
    zip_paths: list[Path] = []
    for month in iter_months(start_month, end_month):
        result = client.ensure_month(
            market=market, symbol=symbol, timeframe=timeframe, month=month, raw_dir=raw_dir
        )
        if result.missing:
            missing_files.append(result.filename)
            continue
        assert result.zip_path is not None and result.zip_sha256 is not None
        source_files.append({
            "filename": result.filename,
            "zip_sha256": result.zip_sha256,
            "size_bytes": result.size_bytes,
            "checksum_expected": result.checksum_expected,
            "checksum_status": result.checksum_status,
        })
        zip_paths.append(result.zip_path)

    fingerprint = source_fingerprint(source_files)
    if source_files and manifest_is_current(manifest_path, parquet_path, fingerprint):
        return json.loads(manifest_path.read_text(encoding="utf-8")) | {"idempotent_skip": True}

    all_rows = []
    for zip_path in zip_paths:
        all_rows.extend(read_zip_klines(zip_path, timeframe))
    rows, duplicate_count, conflicts = deduplicate(all_rows)
    gaps, discontinuities = detect_gaps(rows, timeframe)
    if conflicts:
        raise DataValidationError(f"{symbol} {timeframe}: conflicting duplicate candles detected")
    if not rows:
        raise DataValidationError(f"{symbol} {timeframe}: no source candles available")

    write_parquet(rows, parquet_path, symbol=symbol, market=market, timeframe=timeframe)
    source_url = f"{client.base_url}/data/{market}/monthly/klines/{symbol}/{timeframe}/"
    manifest = build_manifest(
        symbol=symbol,
        market=market,
        timeframe=timeframe,
        source_url=source_url,
        rows=rows,
        source_files=source_files,
        missing_files=missing_files,
        duplicate_count=duplicate_count,
        conflicts=conflicts,
        gaps=gaps,
        discontinuities=discontinuities,
        parquet_path=parquet_path,
        fingerprint=fingerprint,
    )
    write_json(manifest_path, manifest)
    write_json(report_path, {
        "dataset": f"{symbol}_{timeframe}",
        "status": manifest["status"],
        "candles": manifest["candles"],
        "first_date": manifest["first_date"],
        "last_date": manifest["last_date"],
        "duplicates_found": duplicate_count,
        "gaps_found": len(gaps),
        "open_time_discontinuities_found": len(discontinuities),
        "open_time_discontinuity_samples": list(discontinuities[:100]),
        "close_time_conventions": manifest["close_time_conventions"],
        "close_time_anomalies_found": manifest["close_time_anomalies_found"],
        "close_time_anomaly_samples": manifest["close_time_anomaly_samples"],
        "files_missing": missing_files,
        "checksum_status": manifest["checksum_status"],
        "dataset_sha256": manifest["dataset_sha256"],
        "final_size_bytes": manifest["final_size_bytes"],
        "pipeline_version": PIPELINE_VERSION,
        "schema_version": SCHEMA_VERSION,
    })
    return manifest


def run_config(config_path: Path, data_root: Path) -> dict:
    cfg = load_config(config_path)
    client = BinanceArchiveClient(cfg.get("source_base_url", "https://data.binance.vision"))
    inventory = {
        "pipeline_version": PIPELINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "market": cfg["market"],
        "datasets": [],
    }
    for symbol_cfg in cfg["symbols"]:
        for timeframe in symbol_cfg["timeframes"]:
            manifest = run_dataset(
                cfg=cfg,
                symbol_cfg=symbol_cfg,
                timeframe=timeframe,
                data_root=data_root,
                client=client,
            )
            inventory["datasets"].append({
                key: manifest.get(key)
                for key in (
                    "symbol", "market", "timeframe", "first_date", "last_date", "candles",
                    "source_file_count", "duplicates_found", "gaps_found", "open_time_discontinuities_found",
                    "close_time_conventions",
                    "close_time_anomalies_found", "files_missing", "checksum_status", "dataset_sha256",
                    "final_size_bytes", "status", "output_file",
                )
            })
    if len(cfg["symbols"]) == 1:
        symbol = cfg["symbols"][0]["symbol"].upper()
        inventory_path = data_root / cfg["market"] / symbol / "manifests" / f"{symbol}_inventory.json"
        write_json(inventory_path, inventory)
    return inventory

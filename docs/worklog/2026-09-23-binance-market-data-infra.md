# 2026-09-23 — Binance market-data infrastructure (Issue #14)

Branch: `infra/binance-market-data`

Base: current `main` commit `6fc2e1033d926f4d8bc47f9c0fd1763f97df6789`

## Scope boundary

Infrastructure only. No changes to Market Map or Execution semantics, indicators, signals, or parameter optimization.

## Engineering decisions

- Official Binance Public Data is the sole initial source.
- SPOT / BTCUSDT first; 15m, 1h, 4h, 1d, 3d, 1w.
- Monthly archives are preferred over daily files.
- Raw ZIPs are retained as the checksum-verified provenance layer.
- One consolidated Parquet per symbol/timeframe is preferred for deterministic offline analysis.
- Exact price/volume values use `decimal128(38,18)` rather than float64.
- Native timestamp integers are preserved while UTC microsecond-normalized timestamp columns are added.
- Missing/gapped history is reported, never synthetically filled.
- Exact duplicates are counted/deduplicated; conflicting duplicates are fatal.
- Checksum sidecars are refreshed on rerun; valid ZIP payloads are not redownloaded.
- Consolidation is fingerprinted and idempotent.

## Validation status

Local deterministic suite: 12 tests executed; 11 passed and the Parquet round-trip test was skipped only because `pyarrow` is absent from the delegated execution container. GitHub CI installs `pyarrow` and runs that test.

## Drive

The requested Google Drive hierarchy was created under root `PineTrading-Lab`; IDs are recorded in `docs/data/GOOGLE_DRIVE_LAYOUT.md`.

## Environment limitation

The delegated execution container could not resolve `data.binance.vision` by DNS. This blocks production dataset materialization in this runtime, not the downloader architecture. No synthetic dataset is presented as real Binance history.

The one-command network-capable run is documented in `docs/data/BINANCE_MARKET_DATA_PIPELINE.md`.

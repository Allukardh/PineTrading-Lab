# 2026-09-23 — Binance market-data infrastructure (Issue #14)

Branch: `infra/binance-market-data`

Base: current `main` commit `6fc2e1033d926f4d8bc47f9c0fd1763f97df6789`

## Scope boundary

Infrastructure only. No changes to Market Map or Execution semantics, indicators, signals, or parameter optimization.

## Engineering decisions

- Official Binance Public Data is the sole initial source.
- SPOT / BTCUSDT first; 15m, 1h, 4h, 1d, 3d, 1w.
- Monthly archives are preferred over daily files.
- Raw ZIPs are retained because their official checksum sidecars make them the strongest reproducible provenance layer and they remain modest relative to trade-level archives.
- One consolidated Parquet per symbol/timeframe is preferred for deterministic offline analysis and easy handoff to reference engines.
- Exact price/volume values use `decimal128(38,18)` in Parquet rather than float64.
- Timestamp normalization is unit-aware: milliseconds before the Binance SPOT archive switchover and microseconds from 2025-01-01 onward; all consolidated timestamps are UTC microseconds.
- Missing/gapped history is reported, never synthetically filled.
- Exact duplicates are counted/deduplicated; conflicting duplicates are fatal.
- Small checksum sidecars are refreshed on rerun to detect upstream Binance archive replacement; valid ZIP payloads are not redownloaded.
- Consolidation is fingerprinted and idempotent.

## Drive

Google Drive hierarchy was created under root `PineTrading-Lab`; IDs are recorded in `docs/data/GOOGLE_DRIVE_LAYOUT.md`.

## Environment limitation

The implementation runtime had GitHub and Google Drive connectivity but its execution container could not resolve `data.binance.vision`. This blocks production dataset materialization here, not the downloader architecture. No synthetic dataset is presented as real Binance history.

The local one-command run is documented in `docs/data/BINANCE_MARKET_DATA_PIPELINE.md`.

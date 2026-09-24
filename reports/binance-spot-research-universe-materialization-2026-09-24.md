# Binance SPOT research universe materialization — 2026-09-24

Pipeline: `0.2.0`  
Schema: `binance-spot-kline-v1`  
Production run: `36012752615`  
Reproducibility run: `36013237779`  
CI: `36013237831` — 20/20 tests PASS  
Static integrity: `36013237821` — PASS

## Result

All 14 requested symbols materialized successfully at 15m / 1h / 4h / 1d / 3d / 1w.

- 14 symbols / 84 datasets
- 4,429,685 candles
- 6,852 source archives
- 6,852/6,852 available Binance checksums verified
- 0 missing checksum sidecars
- 0 checksum mismatches
- 1 exact duplicate candle in AVAXUSDT, deterministically deduplicated and reported
- 373,013,524 Parquet bytes
- 218,849,280 raw provenance TAR bytes

Including the existing BTCUSDT baseline, the canonical store now contains 15 symbols / 90 datasets, 4,849,829 candles and 415,087,647 Parquet bytes.

## Symbol summary

| Symbol | First monthly archive | Candles | Source files | Parquet bytes | Exact dupes |
| --- | --- | ---: | ---: | ---: | ---: |
| AAVEUSDT | 2020-10 | 273,501 | 423 | 23,199,758 | 0 |
| ADAUSDT | 2018-04 | 389,389 | 603 | 31,563,480 | 0 |
| AVAXUSDT | 2020-09 | 276,413 | 429 | 22,781,891 | 1 |
| DOGEUSDT | 2019-07 | 332,977 | 513 | 28,460,273 | 0 |
| DOTUSDT | 2020-08 | 280,784 | 435 | 23,295,470 | 0 |
| ETHUSDT | 2017-08 | 420,144 | 651 | 39,767,643 | 0 |
| HBARUSDT | 2019-09 | 322,093 | 501 | 25,890,830 | 0 |
| LINKUSDT | 2019-01 | 354,578 | 549 | 29,682,060 | 0 |
| LTCUSDT | 2017-12 | 405,138 | 627 | 31,537,061 | 0 |
| NEARUSDT | 2020-10 | 273,614 | 423 | 22,524,973 | 0 |
| SOLUSDT | 2020-08 | 281,767 | 435 | 24,361,499 | 0 |
| SUIUSDT | 2023-05 | 155,024 | 237 | 14,277,759 | 0 |
| UNIUSDT | 2020-09 | 277,066 | 429 | 23,094,232 | 0 |
| XRPUSDT | 2018-05 | 387,197 | 597 | 32,576,595 | 0 |

The first month is discovered from the official Binance `1d` monthly checksum sidecars; it is not a hard-coded listing-date table.

## Missing public monthly archives

At materialization time every new symbol lacked the same three monthly objects in the Binance public store:

- `<SYMBOL>-3d-2026-08.zip`
- `<SYMBOL>-1w-2026-07.zip`
- `<SYMBOL>-1w-2026-08.zip`

They remain explicit `files_missing` findings. No candles were synthesized.

## Drive audit

Each new symbol has its own `raw / consolidated / manifests / reports` hierarchy under `Market Data/Binance/spot`.

The post-transfer audit confirmed exactly 6 Parquets + 1 raw TAR + 1 manifests TAR + 1 reports TAR for every symbol. Retry duplicates created during interrupted transfers for AVAXUSDT and UNIUSDT were removed before the audit passed.

## Reproducibility

The full 14-symbol matrix succeeded twice. Dataset validation remains checksum-first, source-preserving, gap-aware and idempotent. The second successful full run validates the same pipeline after the CI test-discovery correction.

## Scope guard

No Market Map or Execution semantics were changed.

# Binance historical market-data pipeline

Status: infrastructure-only implementation for Issue #14. It does not modify Market Map or Execution semantics.

## Source contract

Primary source: Binance Public Data (`https://data.binance.vision`). The implementation follows the official `binance/binance-public-data` contract:

- SPOT kline archives are published as daily or monthly ZIP files; this pipeline deliberately uses **monthly** archives.
- Monthly kline files use the native 12-field `/api/v3/klines` schema.
- Each archive normally has a sibling `.CHECKSUM` file containing the expected SHA-256.
- Binance SPOT archive timestamps are milliseconds before 2025-01-01 and microseconds from 2025-01-01 onward. The parser detects the unit from magnitude, normalizes to microseconds, and validates candle duration using the native source precision.
- Binance states that new monthly data becomes available on the first Monday of the following month. Therefore the default run ends at the latest month expected to be publishable: the previous calendar month after the first Monday has arrived, otherwise one month earlier.

Official references:

- `https://github.com/binance/binance-public-data`
- `https://data.binance.vision`
- `https://www.binance.com/en/support/announcement/detail/360000737572` (2018-02-09 system-upgrade completion notice)

## Initial scope

Market: `spot`

Symbol: `BTCUSDT`

Timeframes: `15m`, `1h`, `4h`, `1d`, `3d`, `1w`

Configured start month: `2017-08`. End month defaults to the latest officially publishable monthly archive window.

The core is symbol-agnostic. Adding ETHUSDT or AVAXUSDT later requires another config entry, not a rewrite.

## Local/Drive layout

The pipeline treats the supplied `--data-root` as the Binance root and writes:

```text
<data-root>/
  spot/
    BTCUSDT/
      raw/
        15m/
        1h/
        4h/
        1d/
        3d/
        1w/
      consolidated/
        BTCUSDT_15m.parquet
        BTCUSDT_1h.parquet
        BTCUSDT_4h.parquet
        BTCUSDT_1d.parquet
        BTCUSDT_3d.parquet
        BTCUSDT_1w.parquet
      manifests/
      reports/
```

Raw archives are retained by default because they are the official checksum-verified provenance layer and allow reprocessing without another full network transfer. The interval subdirectories under `raw/` avoid filename collisions and keep monthly sources auditable.

## One-command run

From repository root on Windows PowerShell/cmd with Python 3.12+:

```text
py -3.12 -m pip install -r requirements-market-data.txt && py -3.12 -m tools.binance_market_data run --config configs/binance-spot-btcusdt.json --data-root "data/market-data/Binance"
```

If Google Drive for desktop is mounted locally, point `--data-root` directly at the synced project folder, for example:

```text
py -3.12 -m pip install -r requirements-market-data.txt && py -3.12 -m tools.binance_market_data run --config configs/binance-spot-btcusdt.json --data-root "G:\My Drive\PineTrading-Lab\Market Data\Binance"
```

The exact drive letter/folder name is local-machine specific; the pipeline itself does not assume one.

## Idempotency and recovery

For each month/timeframe:

1. the tiny `.CHECKSUM` sidecar is refreshed so an upstream Binance archive replacement can be detected;
2. an already-present ZIP whose SHA-256 matches the sidecar is reused;
3. interrupted ZIP downloads use a `.part` file and HTTP `Range` resume when supported;
4. a checksum mismatch deletes the bad ZIP and fails the run rather than trusting corrupted data;
5. when a checksum sidecar is genuinely unavailable, the local ZIP is still SHA-256 hashed and the manifest records `checksum_status=missing`;
6. consolidation is skipped when source fingerprints, pipeline/schema versions, output existence, and final Parquet hash all match the prior manifest.

## Validation

Before consolidation the pipeline validates:

- ZIP structure/integrity (`ZipFile.testzip`);
- exactly one CSV payload per Binance monthly kline ZIP;
- exact 12-column native kline schema;
- timestamp magnitude/unit; the candle grid is validated from `open time`, while native `close time` conventions are classified and preserved. Verified legacy archives include exact-boundary closes, early closes, and at least one `pre_open` close timestamp (BTCUSDT 15m, 2020-12-21 14:00 UTC). These native metadata anomalies are reported rather than rewritten;
- numeric/finite OHLCV values;
- non-negative trade count and volume fields;
- OHLC ordering constraints;
- duplicate candle open times;
- conflicting duplicates;
- fixed-interval gaps;
- discontinuities that are not integer multiples of the requested timeframe. These are retained as provenance findings rather than silently normalized.

Exact duplicate candles are deduplicated deterministically and counted. Conflicting duplicates remain fatal. Integral gaps and non-integral open-time discontinuities are retained as findings; the pipeline **never fabricates or re-times candles**. This matters for verified historical Binance behavior: around the 2018-02-08/09 system-upgrade outage, the official BTCUSDT 15m archive contains an off-grid restart at `2018-02-09T09:58:14.789Z` and later re-aligns to the normal 15-minute grid.

## Parquet schema

Each `symbol + timeframe` becomes one Zstandard-compressed Parquet file. Columns:

- `symbol`, `market`, `timeframe`
- `open_time_raw` (exact native Binance integer)
- `open_time` (`timestamp[us, UTC]`, normalized)
- `open`, `high`, `low`, `close`
- `volume`
- `close_time_raw` (exact native Binance integer)
- `close_time` (`timestamp[us, UTC]`, normalized)
- `quote_asset_volume`
- `number_of_trades`
- `taker_buy_base_asset_volume`
- `taker_buy_quote_asset_volume`
- `ignore`
- `source_file`
- `source_timestamp_unit`
- `source_close_time_convention` (`boundary_minus_tick`, `exact_boundary`, `early_close`, `pre_open`, or `overrun`)

Price/volume-like numeric fields use Parquet `decimal128(38,18)` to avoid binary floating-point loss in the canonical dataset. Taker-buy fields are intentionally retained for future Execution research.

## Manifest contract

Each final dataset manifest includes at least:

- symbol, market, timeframe, data source;
- first and last candle timestamps;
- candle count and source-file count;
- duplicate count and conflict details;
- gap count/details plus `open_time_discontinuities_found` and exact unexpected open-time discontinuities;
- native close-time convention counts plus anomaly count/samples;
- missing monthly files;
- checksum verification summary;
- source archive hashes/fingerprints;
- consolidated Parquet SHA-256 and size;
- pipeline and schema versions.

## Runtime limitation recorded for the delegated ChatGPT environment

The delegated ChatGPT container itself could not resolve `data.binance.vision` by DNS. Production materialization is therefore validated through a network-capable GitHub Actions job and remains reproducible locally with the one-command run above.

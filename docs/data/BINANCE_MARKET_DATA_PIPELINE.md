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
- timestamp magnitude/unit and close-time duration;
- numeric/finite OHLCV values;
- non-negative trade count and volume fields;
- OHLC ordering constraints;
- duplicate candle open times;
- conflicting duplicates;
- fixed-interval gaps;
- discontinuities that are not integer multiples of the requested timeframe.

Exact duplicate candles are deduplicated deterministically and counted. Conflicting duplicates or non-integral interval discontinuities are fatal. Legitimate integral gaps are retained as gaps; the pipeline **never fabricates candles**.

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

Price/volume-like numeric fields use Parquet `decimal128(38,18)` to avoid binary floating-point loss in the canonical dataset. Taker-buy fields are intentionally retained for future Execution research.

## Manifest contract

Each final dataset manifest includes at least:

- symbol, market, timeframe, data source;
- first and last candle timestamps;
- candle count and source-file count;
- duplicate count and conflict details;
- gap count/details and unexpected discontinuities;
- missing monthly files;
- checksum verification summary;
- source archive hashes/fingerprints;
- consolidated Parquet SHA-256 and size;
- pipeline and schema versions.

## Runtime limitation recorded for the delegated ChatGPT environment

The delegated ChatGPT runtime used to implement Issue #14 could create the Google Drive hierarchy and modify GitHub, but its container could not resolve `data.binance.vision` by DNS. Consequently no BTCUSDT monthly ZIPs were downloaded and no production Parquet was fabricated in that runtime. The code/test/CI path is complete; materialization must occur in a network-capable local/CI environment using the one-command run above.

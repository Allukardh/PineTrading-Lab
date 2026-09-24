# Binance historical market-data pipeline

Status: infrastructure-only implementation for Issue #14, production-materialized on 2026-09-24. It does not modify Market Map or Execution semantics.

## Source contract

Primary source: Binance Public Data (`https://data.binance.vision`). The implementation follows the official `binance/binance-public-data` contract:

- SPOT kline archives are published as daily or monthly ZIP files; this pipeline deliberately uses **monthly** archives.
- Monthly kline files use the native 12-field `/api/v3/klines` schema.
- Each archive normally has a sibling `.CHECKSUM` file containing the expected SHA-256.
- Binance documents SPOT archive timestamps as milliseconds before 2025-01-01 and microseconds from 2025-01-01 onward. The parser detects the actual unit from magnitude and normalizes to microseconds. Because verified official archives can deviate from the documented epoch rule (for example BTCUSDT `3d` in `2025-01`), the documented rule is audited in manifests rather than used to rewrite or reject native timestamps.
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
- timestamp magnitude/unit; the actual unit is accepted from the native integer magnitude, while deviations from the documented 2025 microsecond epoch rule are counted and sampled in manifests. The candle grid is validated from `open time`, while native `close time` conventions are classified and preserved. Verified legacy archives include exact-boundary closes, early closes, and at least one `pre_open` close timestamp (BTCUSDT 15m, 2020-12-21 14:00 UTC). These native metadata anomalies are reported rather than rewritten;
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
- observed timestamp-unit counts plus documented-epoch anomaly count/samples;
- native close-time convention counts plus anomaly count/samples;
- missing monthly files;
- checksum verification summary;
- source archive hashes/fingerprints;
- consolidated Parquet SHA-256 and size;
- pipeline and schema versions.

## Production materialization — 2026-09-24

The delegated ChatGPT container itself could not resolve `data.binance.vision` by DNS, so the full production run was executed in the network-capable GitHub Actions environment instead of fabricating or substituting data.

Canonical production run:

- GitHub Actions run: `36006762328`
- source branch/head: `infra/binance-market-data` @ `eff420c7823e7e32e8317433ac61bd1e21d1914b`
- pipeline version: `0.1.2`
- schema version: `binance-spot-kline-v1`
- 6 consolidated Parquets produced
- 420,144 candles total
- 651 timeframe-month source archives consumed
- 651 Binance checksum sidecars verified; 0 missing and 0 mismatched
- 0 duplicate open times across all six consolidated datasets
- consolidated Parquet bytes: 42,074,123
- raw provenance bundle bytes: 25,077,760

The production run intentionally preserves source findings instead of normalizing them away. The 15m/1h/4h histories contain historical gaps and native close-time anomalies; 15m and 1h contain verified off-grid restart timestamps around the 2018 Binance outage; 3d/1w contain a small number of post-2025 archives that still use millisecond timestamps; and the public monthly store did not expose `BTCUSDT-3d-2026-08.zip`, `BTCUSDT-1w-2026-07.zip`, or `BTCUSDT-1w-2026-08.zip` at materialization time. These are recorded as findings, not silently filled.

The heavy materialization workflow is `workflow_dispatch` by design after this successful production validation. Pull requests continue to use the normal deterministic unit/integration CI without repeatedly downloading the entire historical corpus.

Small production inventory/report snapshots are versioned in Git. The large raw provenance bundle and six Parquets are stored in the Google Drive dataset hierarchy documented in `docs/data/GOOGLE_DRIVE_LAYOUT.md`.

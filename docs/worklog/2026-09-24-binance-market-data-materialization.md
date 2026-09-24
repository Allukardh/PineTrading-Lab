# 2026-09-24 — Binance BTCUSDT production materialization

Issue: #14  
Branch: `infra/binance-market-data`  
Base remains `main` at `6fc2e1033d926f4d8bc47f9c0fd1763f97df6789`.

## What completed

The historical market-data pipeline was exercised against the real Binance Public Data corpus in GitHub Actions because the delegated ChatGPT container could not resolve `data.binance.vision`.

After handling verified source quirks without rewriting native data, run `36006762328` completed successfully from source head `eff420c7823e7e32e8317433ac61bd1e21d1914b`.

Production outcome:

- 6 consolidated Parquets generated;
- 420,144 candles total;
- 651 timeframe-month source archives consumed;
- all 651 available SHA-256 sidecars verified;
- 0 checksum missing, 0 mismatch;
- 0 duplicate candle open times;
- 42,074,123 consolidated Parquet bytes;
- raw provenance retained as a 25,077,760-byte TAR transport bundle.

## Source findings preserved

The real corpus proved why the pipeline must preserve rather than "clean" Binance history:

- exact-boundary and early close timestamps exist in legacy archives;
- one verified 2020-12 BTCUSDT row has `close_time < open_time`; it is classified as `pre_open`, preserved, and surfaced;
- the 2018 Binance outage/restart contains off-grid open timestamps in 15m/1h;
- some 3d/1w rows after the documented 2025 timestamp transition still use milliseconds;
- the public monthly store was missing `BTCUSDT-3d-2026-08.zip`, `BTCUSDT-1w-2026-07.zip`, and `BTCUSDT-1w-2026-08.zip` at run time.

None of those findings are silently fabricated, shifted, or filled.

## Drive handoff

The requested Drive hierarchy now contains exactly six canonical Parquets in `consolidated`, plus the raw provenance, manifest, and report transport bundles in their respective folders. Connector-retry duplicates in `consolidated` were identified and deleted.

See `docs/data/GOOGLE_DRIVE_LAYOUT.md` and `manifests/binance-spot-btcusdt.production-2026-09-24.json` for IDs, hashes, and sizes.

## CI policy after production validation

The heavyweight full-history materialization workflow returns to manual `workflow_dispatch`. Normal PR CI continues to exercise parsing, validation, manifests, idempotency, and Parquet consolidation deterministically without redownloading the complete corpus on each source change.

## Scope guard

No Market Map or Execution semantics were changed. PR #15 remains open and unmerged.

# 2026-09-24 — Binance research universe production materialization

Expanded the proven BTCUSDT historical-data infrastructure to:

`ETHUSDT, AVAXUSDT, DOGEUSDT, DOTUSDT, ADAUSDT, XRPUSDT, SOLUSDT, UNIUSDT, NEARUSDT, AAVEUSDT, HBARUSDT, LINKUSDT, SUIUSDT, LTCUSDT`.

Engineering additions:

- pipeline version `0.2.0`;
- automatic first-month discovery from official Binance `.CHECKSUM` sidecars;
- `--symbol` filter for matrix execution;
- 14-symbol GitHub Actions matrix;
- four new deterministic tests for discovery/filter behavior;
- CI changed to discover the complete market-data test suite.

Production run `36012752615`: 14/14 jobs PASS.  
Reproducibility run `36013237779`: 14/14 jobs PASS.  
Normal CI `36013237831`: 20/20 tests PASS.  
Static integrity `36013237821`: PASS.

Drive transfer was audited per symbol. Connector retry duplicates for AVAXUSDT and UNIUSDT were deleted; every new symbol now has exactly six canonical Parquets and one bundle in each provenance/report folder.

Research-universe totals: 4,429,685 candles, 6,852 verified source archives/checksums, 373,013,524 Parquet bytes. One exact AVAXUSDT duplicate candle was deduplicated deterministically and retained as a manifest finding.

The heavy universe workflow returns to manual `workflow_dispatch` after production/reproducibility validation.

No Market Map or Execution semantics changed.

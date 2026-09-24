# BTCUSDT production materialization — 2026-09-24

Issue: #14  
Branch: `infra/binance-market-data`  
Materialization source head: `eff420c7823e7e32e8317433ac61bd1e21d1914b`  
GitHub Actions run: `36006762328`  
Pipeline: `0.1.2`  
Schema: `binance-spot-kline-v1`

## Result

The full Binance Public Data SPOT/BTCUSDT monthly-history materialization completed successfully for all configured timeframes. The run consumed 651 timeframe-month source archives and verified all 651 available Binance SHA-256 sidecars. No checksum was missing or mismatched, and no duplicate candle open time was found.

Across the six consolidated datasets there are 420,144 candles and 42,074,123 bytes of Parquet output.

| TF | Candles | First | Last | Source files | Gaps | Off-grid opens | Close-time findings | Epoch-unit findings | Missing monthly archives | SHA-256 |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 15m | 316,414 | 2017-08-17 04:00Z | 2026-08-31 23:45Z | 109 | 30 | 2 | 15 | 0 | none | `cac347638b577b2bcfcd671f66a68af96edb49c614c4dc203d7dc8ea3fb48411` |
| 1h | 79,117 | 2017-08-17 04:00Z | 2026-08-31 23:00Z | 109 | 27 | 2 | 14 | 0 | none | `86f2f12b66979d2e0659b44b95b584ec5140050770acce58e6c4643c9b409776` |
| 4h | 19,794 | 2017-08-17 04:00Z | 2026-08-31 20:00Z | 109 | 9 | 0 | 18 | 0 | none | `93226923a88861cc56d11d82900801db7f64fbe89920c710843dc26673265e06` |
| 1d | 3,302 | 2017-08-17 00:00Z | 2026-08-31 00:00Z | 109 | 0 | 0 | 0 | 0 | none | `1788d075ad21091e279cb68ccfac79935149ca9c444a74dbc971bba00e15fdae` |
| 3d | 1,061 | 2017-08-17 00:00Z | 2026-07-01 00:00Z | 108 | 12 | 0 | 0 | 10 | `BTCUSDT-3d-2026-08.zip` | `e4228da434e9131ae2353147181069d119bc0ef373ec4b93effc5c1dcf9a39d9` |
| 1w | 456 | 2017-08-14 00:00Z | 2026-06-29 00:00Z | 107 | 8 | 0 | 0 | 6 | `2026-07`, `2026-08` | `960de3600ea7ab8651ec2dbaa51d204e05fce19127eb53bb24fcd59dd010ac46` |

## Interpretation of findings

`ok_with_findings` is deliberate. The pipeline preserves native Binance history and reports anomalies instead of fabricating normalized candles.

- Historical integral gaps are recorded, not filled.
- The official 15m/1h history includes two non-integral open-time discontinuities around the 2018 system-upgrade outage/restart.
- Legacy source rows include exact-boundary, early-close, and one pre-open close timestamp; the raw timestamps are preserved.
- Some 3d/1w 2025 rows remain millisecond-based even though Binance documents the SPOT archive transition to microseconds from 2025-01-01; the observed unit is accepted and the deviation is surfaced.
- At run time the monthly public store did not expose one 3d archive and two 1w archives listed above. Their absence is explicit in the manifest.

## Google Drive materialization

Canonical consolidated objects:

- 15m: `1r78NY1v8VcppvJ04ughlNc0nOEmd4ukl`
- 1h: `1moilAqPlFo3791a7bTWQE00s-koQTCm2`
- 4h: `1UbSzypSTUAUfPI6LonMkbkHOi3la_lBo`
- 1d: `1Q0Zvmbn3x6MO3GGmB8zExXAqG9p1VnfL`
- 3d: `1u0cTA19g0s1ojxGyI3jkmW7Zlk_c-sUU`
- 1w: `1E1b8x1Imxprx_YyyHWN4Vin8mZgnntB_`

Transport/provenance bundles:

- raw monthly provenance TAR: `1QWuJ9_zWDNFSEhNUwmibTrZRIBzhgRcW`
- manifests TAR: `1DqXSH_TL05S3zCG6SNg6m9CwCr6lmWAZ`
- reports TAR: `1izcVMZHc8wFoL0O7PHZN2QG7SNUD0IIt`

The Drive `consolidated` folder was de-duplicated after connector retries and contains exactly one canonical Parquet per configured timeframe.

## Scope guard

No Market Map or Execution semantics were changed. This work remains infrastructure-only.

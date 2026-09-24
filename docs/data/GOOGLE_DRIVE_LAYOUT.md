# Google Drive dataset store

Created for PineTrading-Lab Issue #14.

Root folder: `PineTrading-Lab` (Drive ID `1iX6XQW9gjaYRfYN7PShMLx-ZqQQ-VttX`).

Current hierarchy:

```text
PineTrading-Lab/
  Market Data/
    Binance/
      spot/
        BTCUSDT/
          raw/
          consolidated/
          manifests/
          reports/
```

The repository stores code, schemas, tests, small manifests and small reports. Large raw ZIPs and final Parquets belong here, not in Git.

Folder IDs for handoff: Market Data `1PJdg3sxuyo9eCyNNYvPvt-hsH0qr9uQF`; Binance `120nd-nXTA8DpeFQDKXPqEWR1EJecDxes`; spot `1qEeg7z47mlKm4JkzoPaKdktL3VV-aYg2`; BTCUSDT `19RrYqQdsvpt09eIwAz3YMG1lkeIbe-hS`; raw `1A9bKRZypACqPp71Z3W1Rd2rmwgxjW90P`; consolidated `1fS9BD-OveKJbeIIbvGWrS0BCl1E5dSVx`; manifests `1jnaOxT7d_mAqNTNkIDlBLGTdgWMuvU8O`; reports `1I5qYBuSduGKY7W1iZAdR98tru31z0vHO`.

Inside `raw/`, the pipeline creates interval subdirectories (`15m/`, `1h/`, etc.) so monthly sources remain separated and auditable.

## Production snapshot — 2026-09-24

The successful GitHub Actions materialization run `36006762328` was bridged into this Drive hierarchy.

Canonical files currently retained:

| Folder | File | Drive ID | Bytes |
| --- | --- | --- | ---: |
| consolidated | `BTCUSDT_15m.parquet` | `1r78NY1v8VcppvJ04ughlNc0nOEmd4ukl` | 30,094,824 |
| consolidated | `BTCUSDT_1h.parquet` | `1moilAqPlFo3791a7bTWQE00s-koQTCm2` | 9,065,156 |
| consolidated | `BTCUSDT_4h.parquet` | `1UbSzypSTUAUfPI6LonMkbkHOi3la_lBo` | 2,314,969 |
| consolidated | `BTCUSDT_1d.parquet` | `1Q0Zvmbn3x6MO3GGmB8zExXAqG9p1VnfL` | 406,797 |
| consolidated | `BTCUSDT_3d.parquet` | `1u0cTA19g0s1ojxGyI3jkmW7Zlk_c-sUU` | 132,181 |
| consolidated | `BTCUSDT_1w.parquet` | `1E1b8x1Imxprx_YyyHWN4Vin8mZgnntB_` | 60,196 |
| raw | `BTCUSDT_raw_monthly.tar` | `1QWuJ9_zWDNFSEhNUwmibTrZRIBzhgRcW` | 25,077,760 |
| manifests | `BTCUSDT_manifests.tar` | `1DqXSH_TL05S3zCG6SNg6m9CwCr6lmWAZ` | 256,000 |
| reports | `BTCUSDT_reports.tar` | `1izcVMZHc8wFoL0O7PHZN2QG7SNUD0IIt` | 30,720 |

The six consolidated files are the actual Parquet bytes emitted by the production run. Their SHA-256 values are recorded in the production inventory in Git. The `raw`, `manifests`, and `reports` TAR files are transport bundles produced by the same run; extracting them recreates the pipeline's native subdirectory/file layout.

A direct local/Drive-mounted run still writes the interval subdirectories under `raw/` as documented above.

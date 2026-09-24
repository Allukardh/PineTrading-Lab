# Google Drive dataset store

Created for PineTrading-Lab Issue #14.

Root folder:

- `PineTrading-Lab`
- Drive folder ID: `1iX6XQW9gjaYRfYN7PShMLx-ZqQQ-VttX`

Current hierarchy:

```text
PineTrading-Lab/                         1iX6XQW9gjaYRfYN7PShMLx-ZqQQ-VttX
  Market Data/                           1PJdg3sxuyo9eCyNNYvPvt-hsH0qr9uQF
    Binance/                             120nd-nXTA8DpeFQDKXPqEWR1EJecDxes
      spot/                              1qEeg7z47mlKm4JkzoPaKdktL3VV-aYg2
        BTCUSDT/                         19RrYqQdsvpt09eIwAz3YMG1lkeIbe-hS
          raw/                           1A9bKRZypACqPp71Z3W1Rd2rmwgxjW90P
          consolidated/                  1fS9BD-OveKJbeIIbvGWrS0BCl1E5dSVx
          manifests/                     1jnaOxT7d_mAqNTNkIDlBLGTdgWMuvU8O
          reports/                       1I5qYBuSduGKY7W1iZAdR98tru31z0vHO
```

The repository stores code, schemas, tests, small manifests and small reports. Large raw ZIPs and final Parquets belong here, not in Git.

Inside `raw/`, the local pipeline creates interval subdirectories (`15m/`, `1h/`, etc.). This is intentional and documented: it keeps monthly sources separated while preserving the requested top-level `raw/` contract.

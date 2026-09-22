# TradingView Pine extraction — 2026-09-22

## Discovery

1. An old Tampermonkey Gist was rejected: it captures OHLC/Data Window information, not Pine sources.
2. `window.monaco` was probed and was not globally exposed.
3. DOM inspection confirmed Monaco-backed editor internals.
4. Current TradingView automation code revealed the authenticated internal `pine-facade` routes.
5. A read-only exporter was created.

## Observed routes

```text
GET https://pine-facade.tradingview.com/pine-facade/list/?filter=saved
GET https://pine-facade.tradingview.com/pine-facade/get/{scriptIdPart}/{version}
```

The browser uses its existing authenticated session via `credentials: "include"`. No cookie/token is copied.

## Successful result

- 53 discovered
- 53 exported
- 0 failed
- 6 core scripts recognized by `.[...]`

## Safety properties

The exporter:
- uses GET only
- does not call Monaco `setValue()`
- does not click Save
- does not POST/PUT/PATCH/DELETE
- does not inject source into the editor

## Future recovery

`pine-facade` is an internal interface and may change.

If this method stops working:
1. do not guess endpoints
2. verify the current TradingView network/automation implementation
3. rerun small Monaco/DOM probes
4. update the exporter only after validating read-only behavior
5. require `exported == discovered` and `failed == 0` before accepting a new snapshot

Never store TradingView session cookies, authorization headers, exchange credentials or webhook secrets in the repo.

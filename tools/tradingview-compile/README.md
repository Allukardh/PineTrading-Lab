# TradingView compile helper

`compile-current-editor.js` performs a **server-side Pine compilation check** using TradingView's own internal `translate_light` compiler endpoint.

It is intended for validation gates, not deployment.

## Safety properties

The helper:
- reads the source from the currently open Pine Monaco editor
- sends that source to TradingView's compiler endpoint
- does **not** call `setValue()`
- does **not** click Save
- does **not** create/update a TradingView script
- does **not** store session cookies or credentials

The endpoint is internal and may change without notice.

## Use

1. Open TradingView and the Pine Editor.
2. Load/paste the candidate source in the editor **without saving it over another script**.
3. Open DevTools → Console.
4. Paste/run `compile-current-editor.js`.
5. Acceptance for Gate 2:
   - `compiled: true`
   - `errors: 0`
   - every warning, if any, reviewed and documented
6. Copy the returned summary/error table into the validation evidence.

The full response is also exposed temporarily as:

```js
window.__PINE_TRADING_COMPILE_RESULT__
```

## Provenance

The Monaco discovery pattern and `translate_light` response shape were cross-checked against the current `tradesdontlie/tradingview-mcp` implementation on 2026-09-22.

Because both Monaco internals and `pine-facade` are internal TradingView implementation details, this helper is best-effort tooling rather than a stable API integration.

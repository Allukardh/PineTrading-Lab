# Validation and promotion gates

A script is not promoted merely because it compiles.

## Gate 0 — provenance / immutable baseline
- original source archived
- notices preserved
- import metadata recorded
- no secrets

## Gate 1 — static audit
- dead/unreachable logic
- contradictory conditions
- unsafe defaults
- input invariants
- MTF/LTF requests
- object/array limits
- duplicated logic
- semantic naming

## Gate 2 — TradingView compile
- Pine v6 compile PASS
- warnings explained/resolved

## Gate 3 — timing / repaint integrity
- confirmed vs live data is explicit
- HTF request policy is deterministic
- LTF access does not misuse `request.security()`
- reload parity checked
- pivot delay/back-plot semantics documented
- alerts fire on the intended confirmation boundary

Official references:
- https://www.tradingview.com/pine-script-docs/concepts/repainting/
- https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/

## Gate 4 — visual/state regression
Minimum matrix: BTCUSDT on 15m, 1h, 4h and 1D where applicable.

## Gate 5 — alert regression
One intended event must produce one intended alert; stale/repeated event behavior must be explicit.

## Gate 6 — market-behavior validation
Technical correctness is not evidence of trading edge. “Probability”, “quality”, GO/WATCH and similar labels are treated as heuristics until empirically calibrated.

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


## Gate 7 — defaults / operator UX
A technically correct script is not accepted if normal use requires low-level tuning.

Validate:
- default Profile is coherent without manual threshold editing
- Auto timeframe behavior is safe and understandable
- normal settings surface is minimal
- profile changes alter coherent behavior bundles
- engineering thresholds are hidden/internal unless a genuine operator preference exists
- chart answers the intended user questions without requiring interpretation of internal scores
- default visuals do not obscure price action

See `docs/DEFAULTS_AND_PROFILES.md`.

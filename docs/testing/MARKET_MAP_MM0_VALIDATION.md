# Market Map MM-0 — Historical Validation Guide

**Purpose:** validate the Correction/Destination Engine using TradingView's own chart history without adding trading-chart clutter.

## Why this exists

Compile/static gates prove implementation invariants, but they cannot prove that projected correction zones are useful on real market history.

MM-0 therefore computes hidden historical engineering counters inside Pine itself. This keeps validation on the same TradingView data and execution semantics as the production indicator.

## Data Window fields

- `MM Hist • Teses` — distinct structural impulse theses
- `MM Hist • Toques correção` — theses whose primary correction zone was touched
- `MM Hist • Destinos atingidos` — original directional destination reached
- `MM Hist • Invalidações` — confirmed thesis invalidations
- `MM Hist • Zona→Destino` — after zone touch, destination occurred before invalidation
- `MM Hist • Zona→Invalidação` — after zone touch, invalidation occurred before destination
- `MM Hist • Resultados ambíguos` — same-candle OHLC cases where event ordering cannot be known
- `MM Hist • Zona sem desfecho` — touched zones with no resolved destination/invalidation outcome yet
- `MM Hist • Zona→Destino % (engenharia)` — resolved, non-ambiguous post-zone destination share

## Interpretation rules

These are **engineering diagnostics**, not performance promises.

Do not call the final percentage:
- probability
- win rate for a trade
- expected return

The metric does not model:
- entries
- fees/slippage
- stop placement
- partial exits
- macro/news filters
- Execution confirmation

It only asks whether the map's primary correction zone is followed more often by the thesis destination or by structural invalidation among resolved historical cases.

## Acceptance philosophy

Do not optimize parameters to maximize one BTC/timeframe percentage.

A healthy foundation should instead show:
- non-trivial sample counts
- correction zones that are actually touched
- no obvious pathological invalidation rate
- broadly sensible behavior across 15m / 1H / 4H / 1D
- no dependence on one hand-picked period

Any later parameter change must improve semantic robustness, not merely historical curve fit.


## Intrabar-ordering rule

OHLC bars do not expose the event sequence inside the candle.

MM-0 therefore refuses to guess when:
- first zone touch and an outcome boundary happen in the same bar
- both destination and invalidation are crossed in the same bar

These cases are removed from the directional outcome denominator and reported separately.

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


## CSV export workflow

TradingView exports OHLC plus numeric plot results from active indicators. MM-0 therefore exposes a versioned `MM Audit • ...` schema using Data-Window-only plots so the chart stays clean while the historical state can be analyzed offline.

Current schema:

```text
MM Audit • Schema = 1
```

Important audit series include:
- confirmed/provisional bar state
- map direction
- correction model
- adaptive sample count
- correction zone top/bottom
- directional destination
- structural invalidation
- confluence count
- new-thesis event
- correction-zone touch event
- zone→destination event
- zone→invalidation event
- ambiguous-ordering event

### One-file analysis

Export chart data from TradingView and run:

```bash
python tools/analyze_market_map_export.py BTCUSDT_15m.csv
```

Multiple timeframes can be analyzed together:

```bash
python tools/analyze_market_map_export.py BTCUSDT_15m.csv BTCUSDT_1h.csv BTCUSDT_4h.csv BTCUSDT_1d.csv
```

Optional JSON:

```bash
python tools/analyze_market_map_export.py --json mm0-report.json BTCUSDT_15m.csv BTCUSDT_1h.csv BTCUSDT_4h.csv BTCUSDT_1d.csv
```

The analyzer reports:
- thesis and zone-touch counts
- resolved destination vs invalidation outcomes
- ambiguity/censoring
- behavior by direction
- behavior by FIB / ADAPT / LIVE model
- confluence distribution at first zone touch
- correction-zone width in ATR units
- destination and invalidation distance in ATR units
- bars from zone touch to outcome
- structural pathology checks

## Reload parity workflow

For the final deterministic-history gate:

1. export the chart once
2. reload the TradingView script/chart
3. export the same loaded history again
4. run:

```bash
python tools/analyze_market_map_export.py --compare before_reload.csv after_reload.csv
```

Only bars explicitly exported as confirmed are compared. The active provisional candle is excluded by state rather than by blindly dropping the last row.

**PASS:** zero differences in confirmed historical audit series.

## Historical-outcome semantics

The target used for zone-outcome validation is frozen at the **first correction-zone touch**, using the prior bar's destination when available.

This avoids a subtle look-ahead-like distortion where a same-bar liquidity sweep could advance the destination ladder before the validator records what the operator actually had available entering that candle.

Volume-acceptance confluence is also allowed to add a star only on a confirmed bar. LIVE price geometry may move intrabar, but confirmed confluence evidence is not granted by unfinished volume.

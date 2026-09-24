# Market Map MM-0 — Historical Validation Guide

**Purpose:** validate the Correction/Destination Engine using TradingView's own chart history without adding trading-chart clutter.

## Why this exists

Compile/static gates prove implementation invariants, but they cannot prove that projected correction zones are useful on real market history.

## Validation path after TradingView Essential limitation

The original workflow used TradingView CSV export because it contains the Pine-generated `MM Audit • ...` series.

The operator's TradingView Essential plan does not provide the required CSV export workflow. The project will **not** require a paid plan upgrade merely for engineering validation.

Therefore MM-0 now has two evidence paths:

### Primary historical path

Official Binance public BTCUSDT data, prepared by Issue #14, will feed a deterministic offline Market Map research/audit implementation.

Initial historical matrix:
- 15m
- 1H
- 4H
- 1D

Additional robustness:
- 3D
- 1W

The offline implementation must follow the same confirmed-state semantics as Pine and must be tested for equivalence on targeted representative cases before its historical statistics are treated as MM-0 evidence.

### Primary historical path — current status

The deterministic offline kernel now exists:

- `tools/market_map_offline_core.py`
- `tools/market_map_offline.py`
- `tools/test_market_map_offline.py`
- `.github/workflows/market-map-offline-evidence.yml`

Initial BTCUSDT matrix completed on the exact production artifacts from run `36006762328`.

Final accounting evidence run:

`36039228914`

Result:
- 45,562 theses
- 32,458 first correction-zone touches
- 5,408 non-ambiguous destination outcomes
- 1,039 non-ambiguous invalidation outcomes
- 4,560 ambiguous OHLC-order outcomes
- 21,448 superseded/censored touched theses
- 3 still open at export end
- outcome accounting: **100%**
- structural pathologies: **none**
- hard structural gate: **PASS**

Important denominator rule:

The conditional destination share among the 6,447 non-ambiguous resolved cases is 83.88%, but those resolved cases are only 19.86% of all touched theses.

Across all touches:
- destination: 16.66%
- invalidation: 3.20%
- ambiguous: 14.05%
- superseded/censored: 66.08%
- open: 0.01%

Therefore the conditional resolved percentage must never be presented as a trading win rate or unconditional map success rate.

A model-specific review also found that LIVE/ADAPT has much higher same-candle OHLC ambiguity than confirmed ADAPT. This is now a targeted parity/lifecycle question, not a parameter-tuning signal.

Full worklog:

`docs/worklog/2026-09-24-market-map-offline-evidence.md`

Robustness extension also completed for **3D / 1W** after reproducing Pine's self-context rule above 1D and disabling PDH/PDL there exactly as the Pine candidate does.

Robustness run:

`36039959727`

Result:
- six-timeframe structural pathology gate: **PASS**
- six-timeframe outcome accounting: **100%**
- 3D: 63 touches / 14 non-ambiguous resolved / no pathology
- 1W: 29 touches / only 8 non-ambiguous resolved / no pathology
- weekly result is explicitly flagged as a small sample and must not drive tuning

The six-timeframe aggregate leaves the core lifecycle finding essentially unchanged: roughly two-thirds of touched theses are superseded/censored before a non-ambiguous destination/invalidation resolution.

### TradingView parity path

TradingView remains the authority for:
- final rendering;
- real Pine behavior;
- selected confirmed-state/reload checks;
- visual usefulness.

The CSV audit tooling below remains supported if export access becomes available later, but it is no longer a blocker requiring TradingView Premium.

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

Because a newer structural thesis can supersede a touched thesis before either boundary resolves, the project must also report the full all-touch accounting. A large censored share is not a win or a loss and cannot be silently removed from interpretation.

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

OHLC bars do not normally expose the event sequence inside the candle, so MM-0 must not invent an order.

There is one safe topology exception for the historical audit:

- LONG: if the frozen destination is above the current correction zone and the candle opens at/below the zone top, a later high reaching that destination necessarily occurs after the zone was already touched;
- SHORT: if the frozen destination is below the current correction zone and the candle opens at/above the zone bottom, a later low reaching that destination necessarily occurs after the zone was already touched.

Those cases may resolve zone -> destination on the same bar because the order is mathematically implied by the bar open and level geometry.

MM-0 still reports ambiguity when:
- the open lies between the zone and destination, so target-vs-zone order is unknowable;
- destination and invalidation are both crossed on one candle;
- the exported row cannot establish a safe ordering.

The audit must remain conservative outside these provable cases.


## Optional TradingView CSV export workflow

TradingView exports OHLC plus numeric plot results from active indicators. MM-0 therefore exposes a versioned `MM Audit • ...` schema using Data-Window-only plots so the chart stays clean while the historical state can be analyzed offline.

Current schema:

```text
MM Audit • Schema = 2
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
- sweep/reclaim event direction

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

## Optional CSV reload-parity workflow

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

The target used for zone-outcome validation is frozen at the **first correction-zone touch**.

The prior bar's destination is preferred only when it remains a valid post-correction destination relative to the current zone:
- LONG target must be above the current correction-zone top;
- SHORT target must be below the current correction-zone bottom.

If the prior target has moved inside or behind the current LIVE/adaptive correction zone, it is stale for post-correction outcome measurement and must not be frozen. The current destination may be used only when it also lies beyond the zone; otherwise the audit target remains absent.

This preserves the original purpose — avoid a same-bar liquidity sweep silently advancing the ladder — without evaluating a stale liquidity level that is no longer a meaningful future destination.

Volume-acceptance confluence is also allowed to add a star only on a confirmed bar. LIVE price geometry may move intrabar, but confirmed confluence evidence is not granted by unfinished volume.


### Sweep/reclaim semantics

MM-0 now distinguishes a consumed liquidity level from a **confirmed sweep/reclaim**:

- bullish reclaim: price trades below intact lower liquidity and closes back above it
- bearish reclaim: price trades above intact upper liquidity and closes back below it

Only a previously unswept pool can create the event.

The relevant reclaim:
- can become the current `FASE = SWEEP / RECLAIM`
- preserves the just-consumed level as correction confluence even though it has disappeared from the unswept-liquidity list
- is exported as `MM Audit • Sweep reclaim evt`: +1 bullish, -1 bearish, 0 none

The offline analyzer reports reclaim events and how often a first correction-zone touch coincides with one.

### Volume-acceptance timing

For the live last bar, volume acceptance uses **confirmed data only**:
- on an open candle, the scan stops at the previous confirmed bar
- a LIVE impulse uses the previous confirmed extreme for the acceptance range
- at a confirmed zone-touch bar in history, acceptance is recomputed specifically for that event

This prevents volume confluence from flashing at candle close and disappearing on the next open, while avoiding an expensive 240-bar scan on every historical candle.


## Superseded outcomes

A touched correction thesis can be replaced by a newer structural thesis before either its frozen destination or invalidation resolves.

That case is **censored**, not open forever and not counted as a destination/invalidation result.

MM-0 therefore tracks:
- `Zona supersedida` — touched thesis replaced by a new thesis before resolution
- `Zona sem desfecho` — only the currently unresolved remainder after resolved, ambiguous and superseded cases are removed

The post-touch invalidation counter is labeled explicitly as `Invalidações pós-toque` so cumulative telemetry does not imply it counts every invalidation in the chart.

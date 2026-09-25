# Execution Evidence Engines — Historical Research Plan

**Status:** ready for Binance dataset handoff  
**Date:** 2026-09-23  
**Tracker:** #11  
**Data infrastructure:** Issue #14

## 1. Purpose

This plan defines what the main Execution research thread will measure once the delegated Binance dataset pipeline is available.

It intentionally exists **before seeing the historical results** so the project does not invent favorable metrics after the fact.

The goal is not to optimize PnL.

The goal is to challenge:
- MTE-A Momentum Turn
- RSE-A RSI State
- PSE-A Participation

for semantic usefulness, stability and independence.

## 2. Initial dataset scope

Primary:

```text
BTCUSDT spot
15m
1h
4h
1d
3d
1w
```

Use the maximum clean official Binance history produced by Issue #14.

Why all six:
- 15m / 1h / 4h are the initial Execution design matrix
- 1d / 3d / 1w are higher-timeframe robustness checks
- higher TFs are **not** an excuse to retune separate parameter sets

Later unchanged-default robustness:

```text
ETHUSDT
AVAXUSDT
```

## 3. General anti-overfit rules

Do not:
- choose defaults from one bull market
- choose defaults from one timeframe
- tune BTC then create separate ETH/AVAX values
- maximize a historical win rate
- optimize a strategy PnL that does not yet exist
- discard inconvenient years without a data-quality reason

Parameter change requires:
1. a named semantic pathology
2. evidence that the pathology is not isolated
3. a simple proposed fix
4. re-run across all available BTC timeframes
5. later unchanged-default ETH/AVAX check

## 4. Era slicing

Reports should include full history plus calendar/market-era slices where sample size permits.

At minimum report by year.

Useful broad interpretation:
- high-volatility bull periods
- high-volatility bear periods
- low-volatility/range periods

Do not hard-code regime labels from hindsight into the engine.

Era slicing is diagnostic only.

---

# MTE-A research

## 5. State occupancy

For every symbol/timeframe:

- ready bars
- NEUTRAL %
- TURN_UP %
- UP_ACCEL %
- UP_DECEL %
- TURN_DOWN %
- DOWN_ACCEL %
- DOWN_DECEL %

Pathology flags:
- any non-neutral state nearly absent
- TURN states dominate established-direction states
- NEUTRAL nearly always-on
- extreme LONG/SHORT asymmetry without corresponding price-regime explanation

## 6. State transition matrix

Count transitions:

```text
previous momentum state -> current momentum state
```

Questions:
- Does TURN normally bridge established states?
- Are there excessive direct UP_ACCEL ↔ DOWN_ACCEL flips?
- Is the neutral band useful or merely cosmetic?
- Do TURN states chatter back/forth?

## 7. Dwell time

Distribution in bars for each state:
- median
- p25
- p75
- p90

Particular focus:
- TURN_UP / TURN_DOWN
- NEUTRAL

A TURN state lasting one bar always may be too brittle.
A TURN state lasting dozens of bars may be too vague.

No target dwell time is predetermined.

## 8. Turn lead to signed zero-cross

For each MTE TURN episode:

- core sign when TURN begins
- bars until core crosses zero in the turn direction
- whether core instead resumes the original direction before zero-cross

This is not a trade success metric.

It answers whether TURN means:
> meaningful early counter-acceleration

rather than:
> random oscillator wobble.

## 9. Chatter

Report:
- state changes per 100 bars
- TURN direction reversals within 1/2/3 bars
- zero-cross reversals within 1/2/3 bars

Review by timeframe.

The goal is semantic stability without making the timing layer sluggish.

---

# RSE-A research

## 10. Local state occupancy

Report all RSE-A local states:
- EXTREME_OVERBOUGHT
- RECOVERING_OVERBOUGHT
- FADING_OVERBOUGHT
- BULL
- NEUTRAL
- BEAR
- RECOVERING_OVERSOLD
- FADING_OVERSOLD
- EXTREME_OVERSOLD

Check whether:
- recovery/fade states actually occur
- 2-bar memory creates useful persistence rather than noise
- extremes are rare enough to mean something but not unreachable

## 11. Recovery/fade lifecycle

For oversold recovery and overbought fade:

- number of raw zone touches
- number producing recovery/fade state
- bars spent in recovery/fade
- percent continuing through center dead-band
- percent expiring before center

Do not call this a win rate.

It tests whether the semantic memory behaves as intended.

## 12. Confirmed HTF context interaction

For each local supportive state:

- HTF agrees
- HTF neutral
- HTF opposes

Report how often HTF opposition would block ARMADO.

Pathology flags:
- HTF blocks almost everything
- HTF is almost never relevant
- large timeframe-specific asymmetry

Confirmed HTF construction must match the suite timing contract.

---

# PSE-A research

## 13. Relative-volume distribution

Report:
- p10 / p25 / median / p75 / p90 / p95
- % <0.80
- % >=1.20
- % >=1.50

Questions:
- Are candidate bands meaningful across timeframes?
- Does EMA20 prior-confirmed baseline adapt reasonably?
- Are states always WEAK on one TF or never expanded on another?

Do not normalize thresholds per timeframe unless evidence forces an architecture rethink.

## 14. Pressure-proxy distribution

Report close-location pressure:
- distribution
- sign balance
- abs pressure distribution
- % >=+0.20
- % <=-0.20

Check zero-range candle frequency.

## 15. Proxy vs Binance taker imbalance

Using validation-only Binance fields:

```text
takerImbalance = 2*takerBuyBase/volume - 1
```

Report:
- Pearson correlation
- Spearman/rank correlation if implementation dependency is acceptable
- sign agreement excluding near-zero values
- sign agreement when relative volume >=1.20
- sign agreement for abs(proxy) >=0.20
- quadrant counts:
  - proxy+ / taker+
  - proxy+ / taker-
  - proxy- / taker+
  - proxy- / taker-

Also report by timeframe.

This analysis decides whether the OHLC pressure proxy deserves to remain in production.

No minimum acceptable correlation is assumed in advance.

## 16. PSE-A semantic occupancy

For map direction +1 and -1 independently when available:

- CONFIRM %
- CONTRARY %
- WEAK %
- NEUTRAL %

Until the offline Market Map engine is available, a temporary research-only proxy may examine both directions symmetrically:

```text
classify the same bar once as hypothetical LONG and once as hypothetical SHORT
```

This is allowed only for PSE-A component analysis.

It must not be confused with actual Execution signals.

---

# Cross-engine research

## 17. Evidence redundancy

Once all three engines are computed on the same bars, report co-occurrence without declaring trades.

Examples:
- MTE aligned LONG + RSE long-supportive
- MTE aligned SHORT + RSE short-supportive
- MTE aligned + PSE CONFIRM
- RSE supportive + PSE CONFIRM
- all three aligned

Questions:
- Is one engine redundant?
- Does PSE-A merely delay conditions already identified by MTE/RSE?
- Does RSE-A contribute distinct recovery/exhaustion information?

Simple contingency tables are preferred over opaque composite scores.

## 18. Strength-family overlap

For candidate deterioration families:
- MTE deterioration
- RSE deterioration/exhaustion
- PSE weak/contrary

Report:
- zero families
- exactly one
- exactly two
- all three

This directly tests whether:
```text
0 -> NORMAL
1 -> PERDENDO FORÇA
2+ -> EXAUSTÃO
```
will be useful or constantly saturated.

## 19. Market Map integration — later stage

Once an offline-equivalent Market Map engine or trustworthy TradingView audit source exists, condition the same reports on:

- APPROACHING
- IN_CORRECTION
- RETEST
- RECLAIM
- DESTINATION_NEAR

Then measure Execution readiness frequency and reaction-risk clustering.

Do not block component research on Market Map offline implementation.

---

# Reporting

## 20. Required output per run

Machine-readable:
- JSON summary
- optional Parquet/CSV event table

Human-readable:
- Markdown report

Report metadata:
- data source
- symbol
- market
- timeframe
- start/end
- row count
- dataset hash/manifest identity
- research-default manifest version
- suite semantic-contract version
- code commit SHA

## 21. Reproducibility

Every report must identify:

```text
manifests/execution-research-defaults-v1.json
manifests/suite-semantics-v1.json
```

If a candidate default changes:
- increment/update the research manifest deliberately
- do not overwrite old report identity silently

## 22. Decision outcomes

For each engine, historical review ends in one of:

```text
KEEP
REFINE
REMOVE
INSUFFICIENT EVIDENCE
```

No numeric score or forced winner.

A more complicated engine must demonstrate incremental semantic value to survive.

## 23. Production gate

Historical component sanity is necessary but not sufficient.

Even if an evidence engine looks stable offline, production still requires:
- Pine equivalence
- reload parity
- real-chart UX
- integration with Market Map
- no user tuning burden

This plan does not authorize production `execution.pine`.

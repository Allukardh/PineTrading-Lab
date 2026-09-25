# Participation Engine — Clean-room Candidate PSE-A

**Status:** research candidate; not production Pine  
**Date:** 2026-09-23  
**Product:** Execution 0.1.x  
**Tracker:** #11

## 1. Objective

Replace the legacy Buying/Selling Volume presentation with an honest participation engine.

The engine must answer:

> Is current market participation meaningfully supporting, weakening or contradicting the active Market Map direction?

It must not claim access to historical aggressor order flow that OHLCV does not contain.

## 2. Legacy donor truth

The archived Buying/Selling Volume core estimates:

```text
buyVol  = volume * (close - low) / (high - low)
sellVol = volume * (high - close) / (high - low)
```

Therefore:

```text
buyVol - sellVol
---------------- = 2 * (close - low)/(high-low) - 1
     volume
```

This is simply the candle's **close location inside its high-low range**.

It can be useful as a pressure proxy, but it is not:
- aggressor buy volume
- aggressor sell volume
- order-flow delta
- exchange trade-side history

PSE-A keeps the useful proxy while naming it correctly.

## 3. Production-safe core evidence

### 3.1 Relative volume

```text
volumeBaseline = EMA(volume, 20)
relativeVolume = volume / volumeBaseline
```

Candidate bands:

```text
< 0.80x  contracted
0.80–1.20x normal
>= 1.20x expanded
>= 1.50x strong expansion
```

The 1.50x level is diagnostic/strength information. The semantic Participation state does not need a separate fifth enum solely for it.

### 3.2 Candle-location pressure proxy

For non-zero candle range:

```text
pressure = (2 * close - high - low) / (high - low)
```

Range:

```text
-1.0  close at low
 0.0  close at midpoint
+1.0  close at high
```

For a zero-range candle:

```text
pressure = 0
```

Direction-aware pressure:

```text
directionalPressure = pressure * mapDir
```

So positive means the close-location proxy agrees with the active thesis.

## 4. Pressure agreement threshold

Candidate:

```text
PRESSURE_MIN = 0.20
```

Interpretation:

A bullish candle-location proxy must close at least 60% up its high-low range to count as meaningful agreement:

```text
pressure >= +0.20
```

For bearish agreement:

```text
pressure <= -0.20
```

The value is provisional and must be tested historically.

It is not exposed as a normal operator setting.

## 5. PSE-A semantic states

The existing suite Participation enum remains:

- `CONFIRM`
- `NEUTRAL`
- `WEAK`
- `CONTRARY`

### CONFIRM

Requires:

```text
relativeVolume >= 1.20
directionalPressure >= +0.20
```

Meaning:
- participation is expanded
- candle-location pressure agrees with the thesis

This is the reload-safe participation evidence required by the current Execution `CONFIRMA` transition.

### CONTRARY

Requires:

```text
relativeVolume >= 1.20
directionalPressure <= -0.20
```

Meaning:
- participation is expanded
- pressure proxy closes meaningfully against the thesis

### WEAK

Requires:

```text
relativeVolume < 0.80
```

Low participation is considered weak regardless of candle-location direction.

One weak bar alone does not invalidate an already-aligned Execution state.

### NEUTRAL

Everything else:
- normal volume
- expanded volume without directional pressure
- directional pressure without enough volume expansion

This avoids pretending every candle contains meaningful participation evidence.

## 6. No map direction

When:

```text
mapDir == 0
```

PSE-A returns:
- semantic Participation = `NEUTRAL`
- directional pressure is not actionable

Participation does not create its own trade direction.

## 7. Missing/invalid volume

When volume is unavailable or the baseline is not ready:

- `ready = false`
- state = `NEUTRAL`
- Execution cannot reach a participation-confirmed `CONFIRMA` from this evidence

The first production scope is crypto, where volume data is normally available.

Do not silently replace missing volume with fake zero/one values.

## 8. Why not legacy VI formula

Legacy VI multiplied:
- normalized buy/sell proxy
- relative-volume index
- EMA-normalized proxy components

This creates a visually large number but makes its semantic meaning harder to explain.

PSE-A deliberately decomposes the evidence into:

```text
relative volume
+
directional close-location proxy
```

The state machine consumes the semantic result rather than a synthetic "force" magnitude.

## 9. Binance taker-buy data — validation truth, not Pine dependency

The delegated Binance pipeline preserves:

- volume
- taker buy base asset volume
- taker buy quote asset volume

For offline research, define a validation-only taker imbalance:

```text
takerImbalance = 2 * takerBuyBase / volume - 1
```

approximately ranging from:
- -1 seller-aggressor dominant
- 0 balanced
- +1 buyer-aggressor dominant

This is **not** automatically promoted into production Pine.

Purpose:

> test how often the OHLC close-location proxy agrees with the actual Binance taker-side imbalance available in the historical dataset.

Research questions:
- sign agreement rate
- correlation by timeframe
- behavior during expanded relative volume
- whether 0.20 is a meaningful pressure cutoff
- whether close-location pressure adds incremental value beyond relative volume

If the proxy performs poorly, simplify/remove it rather than preserve it for nostalgia.

## 10. Realtime incremental delta

The separate realtime `varip` donor remains optional enhancement research.

Hard invariant:
- realtime-only delta cannot create/cancel/alter a reload-reconstructible `CONFIRMA` event

PSE-A core remains historical/reload-safe.

## 11. Synthetic validation

Reference tests must cover:

- pressure range [-1, +1]
- close at high/low/midpoint
- zero-range candle
- price scale invariance
- price translation invariance
- volume scale invariance
- relative-volume readiness/warmup
- CONFIRM threshold
- CONTRARY threshold
- WEAK threshold
- neutral map direction
- missing/zero volume handling
- validation-only taker imbalance range

These tests validate mechanics, not market edge.

## 12. Audit plan

Execution audit should expose:

```text
EX Audit • Participação state
EX Audit • Vol relativo
EX Audit • Pressão proxy
EX Audit • Pressão direcional
EX Audit • Participação ready
```

Offline Binance reports may additionally contain:

```text
Research • Taker imbalance
Research • Proxy/taker sign agreement
```

Those research-only fields must not be confused with the production Pine data contract.

## 13. Promotion rule

PSE-A becomes production-canonical only if:

1. synthetic reference tests pass
2. relative-volume state frequency is sane
3. proxy/taker comparison justifies keeping close-location pressure
4. unchanged defaults are not pathological on BTC / ETH / AVAX
5. participation adds information beyond Momentum + RSI instead of merely delaying every signal
6. reload parity remains exact

Until then it remains a research candidate.

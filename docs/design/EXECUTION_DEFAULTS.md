# Execution 0.1.0 — Default Evidence Contract

**Status:** initial engineering defaults for implementation; subject to real-chart validation  
**Date:** 2026-09-23  
**Product policy:** defaults are owned by the engine, not delegated to the operator

## 1. Principle

Execution 0.1.0 must ship with one coherent default behavior.

The operator should not choose:
- MA type
- oscillator mode
- RSI timeframes
- RSI threshold sets
- volume normalization mode
- signal strictness
- arbitrary score weights

Those are engineering decisions.

If later validation demonstrates that materially different operating styles are useful, profiles can be introduced. No profile selector is justified yet.

## 2. Donor evidence

The initial contract is informed by the archived core/reference scripts:

### Moving Average Shift
Useful:
- normalized distance from a base moving average
- momentum turn / acceleration / deceleration
- compact histogram semantics

Discard:
- SMA/EMA/WMA/VWMA selector
- Original / Zero Cross / Signal Line modes
- arbitrary threshold-driven entry diamonds
- probability naming
- percentile warmup substitution

### RSI MTF Tactical
Useful defaults:
- RSI 14
- 50 centerline
- ±2 center dead-band concept
- 70/30 exhaustion
- 80/20 extended exhaustion
- recent directional step

Discard:
- four manual timeframes
- historical table
- live `lookahead_off` HTF state
- Stoch RSI and divergence as default blockers

### Buying/Selling Volume 2-in-1
Useful:
- 20-bar/period volume baseline
- relative volume
- candle-location pressure proxy as secondary evidence

Discard:
- RAW/VI user mode
- buy/sell percentage presented as real aggressor flow
- standalone table

### Realtime Volume Bars donor
Useful:
- `varip` incremental up/down volume observation

Hard limitation:
- realtime-only; cannot reconstruct equivalent history

Therefore it is enhancement-only and cannot alter confirmed reload-safe events.

## 3. RSI defaults

Internal defaults:

```text
RSI length              14
center                   50
center dead-band         48–52
overbought               70
oversold                 30
extended overbought      80
extended oversold        20
step lookback            2 bars
minimum directional step 0.25 RSI point
```

These inherit the useful parts of the existing RSI core while removing manual timeframe configuration.

### Automatic context timeframe

Use the same suite context policy as Market Map:

```text
chart <= 15m  -> context 1H
chart <= 1H   -> context 4H
chart <= 4H   -> context 1D
chart <= 1D   -> context 1W
above 1D      -> chart/self context unless a later rule is justified
```

HTF state is confirmed.

## 4. Participation defaults

Core reload-safe participation:

```text
volume baseline          EMA 20
normal participation     0.80x–1.20x baseline
expanded participation   >= 1.20x
strong expansion         >= 1.50x
contracted participation < 0.80x
pressure source          candle close location in H-L range
```

The pressure proxy is only directional supporting evidence.

It must never be labeled:
- buy volume
- sell volume
- order-flow delta
- aggressor flow

in final semantic output.

### Participation semantics

For the active thesis direction:

**CONFIRMA**
- volume >= 1.20x baseline
- pressure proxy agrees with direction

**NEUTRO**
- no strong contradiction
- volume roughly normal

**FRACO**
- volume < 0.80x baseline, or directional pressure is weak while continuation is expected

**CONTRARIA**
- expanded participation with pressure clearly opposite the thesis

A single low-volume bar should not invalidate an otherwise valid setup.

## 5. Momentum defaults

A first clean-room candidate is now selected for validation:

**MTE-A — volatility-normalized EMA spread**

```text
source            HLC3
fast EMA          8
slow EMA          21
ATR               14
core activity RMA 20
neutral factor    0.15
turn factor       0.50
turn floor        0.02
numeric accel eps 1e-9
```

Core:

```text
core = (EMA8(HLC3) - EMA21(HLC3)) / ATR14
```

Acceleration is the one-bar change in `core`.

The engine remains neutral until its volatility/activity context is valid. No synthetic normalization fallback is allowed.

The candidate preserves these invariants:

1. scale/translation stability
2. sign and acceleration are separate concepts
3. explicit TURN / ACCEL / DECEL semantics
4. no synthetic warmup values
5. no user-facing MA/signal-mode selector
6. confirmed actionable transitions happen later in the Execution state machine, not inside the oscillator

MTE-A is **not yet a frozen production default**. The exact formula/defaults must survive historical BTC/ETH/AVAX validation before canonization.

Detailed rationale and synthetic tests:

`docs/design/MOMENTUM_TURN_ENGINE.md`

Machine-readable candidate defaults:

`manifests/execution-research-defaults-v1.json`

## 6. Readiness evidence burden

No numeric score is exposed.

Semantic burden:

### PREPARANDO
Requires:
- coherent Market Map direction
- relevant location
- not invalidated
- momentum not strongly opposing

### ARMADO
Requires all three evidence families to be acceptable:
- momentum aligned
- RSI supportive
- participation not contrary

### CONFIRMA
Requires:
- prior ARMADO state
- confirmed chart close
- momentum still aligned
- RSI still supportive
- participation = CONFIRMA

This deliberately makes participation the final close-confirmation evidence rather than an always-required prerequisite for PREPARANDO.

## 7. Strength evidence burden

Strength uses independent evidence families:

1. momentum deterioration
2. RSI deterioration/exhaustion
3. participation deterioration

Default interpretation:

```text
0 families  -> NORMAL
1 family    -> PERDENDO FORÇA
2+ families -> EXAUSTÃO
```

`RISCO DE REAÇÃO` requires:
- a meaningful reaction location from Market Map, normally destination/opposing liquidity proximity
- **and** at least two deterioration families

No one oscillator can create the strongest warning by itself.

## 8. Destination proximity

Market Map currently marks the primary destination as near inside 0.30 ATR.

Execution should consume the same semantic concept rather than inventing a separate distance threshold.

If later evidence shows Execution needs a different warning distance, the change must be justified and documented rather than exposed as a user input.

## 9. Operator controls target

Execution 0.1.0 should expose at most:

- show/hide confirmed chart markers
- appearance controls that are genuinely personal

No normal threshold controls.

Advanced/Diagnostics can expose read-only/state information and, only if needed for engineering, hidden diagnostic inputs.

## 10. Validation rule

These defaults are **starting engineering defaults**, not claims of optimality.

They become production defaults only if:
- BTCUSDT 15m / 1H / 4H shows sensible state frequency and visual behavior
- ETHUSDT and AVAXUSDT do not show obvious pathology with unchanged values
- reload parity is exact for confirmed states
- no threshold needs per-asset hand tuning

If validation rejects a value, change the engine default in code and documentation. Do not make the operator tune around a weak default.

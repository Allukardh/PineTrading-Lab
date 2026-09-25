# Momentum Turn Engine — Clean-room Candidate MTE-A

**Status:** selected research candidate; not yet a production default  
**Date:** 2026-09-23  
**Product:** Execution 0.1.x  
**Tracker:** #11

## 1. Objective

Replace the useful idea behind legacy Moving Average Shift with a smaller, deterministic momentum engine that answers:

> Is short-horizon directional pressure accelerating, decelerating, or beginning to turn?

The engine must be:
- scale-independent enough for BTC / ETH / AVAX
- usable across 15m / 1H / 4H and later higher timeframes
- honest during warmup
- free from the legacy percentile-500 dependency
- free from user-facing MA/signal-mode configuration
- semantically compatible with the existing Execution state contract

This is **not** a standalone entry indicator.

## 2. What was preserved from legacy MA Shift

Useful concept:
- observe price displacement relative to a moving reference
- normalize before comparing behavior across markets
- distinguish current directional impulse from acceleration/deceleration
- detect counter-acceleration before a full directional zero-cross
- keep the lower-pane visualization compact

Preserved engineering findings from MAS-0:
- no synthetic warmup fallback
- close-confirmed actionable transitions
- no probability language
- acceleration must be orthogonal to direction rather than creating unreachable filters

## 3. What was rejected

### 3.1 Percentile-normalized distance as production core

Legacy shape:

```text
distance = price - MA
scale    = 97.5th percentile(abs(distance), 500)
normalized distance = distance / scale
oscillator = HMA(change(normalized distance, 15), 10)
```

Reasons not to carry it forward:
- 500-bar warmup is excessive for an execution engine
- percentile behavior changes with a single extreme regime
- 15-bar displacement-change is slow for a timing layer
- HMA + percentile + signal-mode selection adds complexity before proven value
- the legacy oscillator tends toward zero during a constant-velocity trend because it measures **change of displacement**, not persistent directional pressure

The last point matters: a timing engine should not interpret the natural normalization of a strong impulse as an opposite turn merely because the displacement-change magnitude is relaxing.

### 3.2 Pure displacement-velocity candidate

A clean-room candidate was considered:

```text
disp = (hlc3 - EMA21) / ATR14
impulse = smooth(disp - disp[3])
```

It is scale-invariant and simple, but synthetic reversal tests exposed an undesirable property:

- after a regime shock, the impulse can strongly counter-accelerate back toward zero while price is still moving steadily in the new direction

That makes the derivative useful as a secondary acceleration feature, but weaker as the **primary signed momentum state**.

### 3.3 Fast/slow spread without volatility normalization

```text
EMAfast - EMAslow
```

Rejected as the final core because raw magnitude is asset/price-scale dependent.

## 4. Selected candidate — MTE-A

The candidate uses a volatility-normalized fast/slow EMA spread.

### 4.1 Core

```text
source = HLC3

fast = EMA(source, 8)
slow = EMA(source, 21)
atr  = ATR(14)

core = (fast - slow) / atr
```

Interpretation:
- `core > 0`: fast execution momentum is above the slower reference
- `core < 0`: fast execution momentum is below the slower reference
- magnitude is expressed in ATR-normalized units rather than raw dollars

This is conceptually similar to a volatility-normalized MACD spread, but MTE-A does not expose MACD-style user controls or signal-line crossover modes.

## 5. Why EMA 8 / EMA 21

These values are **provisional engineering defaults**, not magic numbers.

Reasons:
- 21 is already a useful short structural/trend horizon in the suite
- 8 is meaningfully faster without becoming a one/two-bar noise tracker
- the ratio separates timing from Market Map's slower 21/50/200 regime layer
- warmup remains short enough for an execution engine

The Binance historical lab will decide whether this pair survives unchanged.

Do not expose 8/21 as normal user inputs.

## 6. Activity-adaptive neutral band

A fixed raw threshold would make behavior depend on market/timeframe.

MTE-A estimates recent core activity:

```text
coreActivity = RMA(abs(core), 20)
neutralBand  = 0.15 * coreActivity
```

State is `NEUTRAL` when:

```text
abs(core) <= neutralBand
```

This is a **relative dead-band**, not a probability threshold.

## 7. Acceleration

```text
accel = core - core[1]
accelActivity = RMA(abs(accel), 20)
turnBand = max(0.02, 0.50 * accelActivity)
accel semantic zero epsilon = 1e-9
```

The absolute 0.02 floor is in ATR-normalized core units. Its purpose is to prevent floating-point/minuscule changes in an otherwise steady trend from being labeled as a turn when recent acceleration activity decays toward zero.

Additionally, acceleration values with absolute magnitude <= `1e-9` are treated as exact zero for semantic classification. This is a numerical-stability epsilon, not a trading threshold. It prevents mathematically equivalent scale/translation transforms from flipping `UP_ACCEL` ↔ `UP_DECEL` solely because of floating-point sign noise.

The market-facing floor is provisional and must be challenged by real BTC/ETH/AVAX data.

## 8. Semantic state mapping

The existing suite momentum codes are retained.

### Neutral

```text
abs(core) <= neutralBand
→ NEUTRAL
```

### Positive core

```text
core > neutralBand

accel < -turnBand  → TURN_DOWN
accel < 0          → UP_DECEL
otherwise          → UP_ACCEL
```

### Negative core

```text
core < -neutralBand

accel > +turnBand  → TURN_UP
accel > 0          → DOWN_DECEL
otherwise          → DOWN_ACCEL
```

Important semantic distinction:

- `TURN_DOWN` means positive momentum is experiencing **meaningful counter-acceleration**
- it does **not** mean bearish momentum is already established
- `TURN_UP` is the mirror
- `UP_DECEL` / `DOWN_DECEL` are weaker deterioration states
- `UP_ACCEL` / `DOWN_ACCEL` are established directional states

This lets Execution react before the signed core crosses zero without pretending a reversal is complete.

## 9. Why TURN is a state, not an alert

MTE-A can remain in `TURN_DOWN` for several bars while positive core is collapsing.

That is intentional.

The actionable alert in the product is still:

`CONFIRMA LONG/SHORT`

Momentum TURN is evidence consumed by the Execution readiness machine.

This avoids adding another noisy crossover alert family.

## 10. Warmup policy

No value is fabricated.

MTE-A remains `ready = false` until all required components exist:

- slow EMA
- ATR
- core activity
- acceleration activity

While not ready:
- semantic state is neutral/unavailable for readiness purposes
- no Execution confirmation may be generated from the momentum family

No mintick/zero substitution is permitted for unavailable normalization.

## 11. Synthetic acceptance tests

Before historical market data, MTE-A must pass deterministic synthetic tests.

### Scale invariance
Multiplying all OHLC prices by a positive constant must preserve:
- core within numerical tolerance
- state sequence exactly

### Translation invariance
Adding a constant to all OHLC prices must preserve state sequence and approximately preserve core.

### Flat/no-volatility market
No division by zero, no synthetic spike, no actionable turn.

### Constant uptrend
After warmup:
- no DOWN_ACCEL state
- no meaningful TURN_DOWN caused only by floating-point drift

### Constant downtrend
Mirror requirement.

### Uptrend → downtrend reversal
Expected sequence:
- positive core
- TURN_DOWN while core is still positive
- neutral transition where appropriate
- DOWN_ACCEL after bearish momentum establishes

### Downtrend → uptrend reversal
Mirror requirement.

These tests validate mechanics, **not trading edge**.

## 12. Relationship to Execution state machine

Current reference semantics consume MTE-A like this:

For LONG:
- `TURN_UP` or `UP_ACCEL` can align/arm
- `TURN_DOWN` / `DOWN_ACCEL` strongly oppose
- `UP_DECEL` contributes deterioration
- `DOWN_DECEL` is not treated as bullish confirmation

For SHORT: mirrored.

After `CONFIRMA`, one-bar oscillator wiggles do not cancel ALINHADO by themselves.

## 13. Visual candidate

The lower pane should remain simple:

- zero line
- MTE core histogram or compact line
- color/state semantics from the canonical momentum state
- no signal line
- no percentile guides
- no separate trend diamonds
- no MA painting on the main chart from Execution

Possible visual interpretation:

```text
positive + accelerating  strong positive
positive + decelerating  softer positive
TURN_DOWN                transition warning
neutral                  muted
TURN_UP                  transition warning
negative + decelerating  softer negative
negative + accelerating  strong negative
```

Exact colors are a renderer decision, not part of the momentum contract.

## 14. What remains open

MTE-A is the **first candidate to validate**, not a frozen production formula.

Historical lab must test:
- event/state frequency
- dwell time in each state
- turn lead vs zero-cross
- excessive chatter
- behavior around Market Map correction/retest/reclaim locations
- consistency on BTC / ETH / AVAX
- 15m / 1H / 4H first, then higher TF sanity

Parameters that may change from evidence:
- fast EMA 8
- slow EMA 21
- activity 20
- neutral factor 0.15
- turn factor 0.50
- turn floor 0.02

The normal operator will not tune them.

## 15. Promotion rule

MTE-A becomes the canonical production Momentum Turn kernel only if:

1. synthetic invariants pass
2. historical event-frequency sanity passes
3. real-chart Execution UX is useful
4. unchanged defaults are not pathological across BTC/ETH/AVAX
5. confirmed state is deterministic after reload

Until then, documents must call it **candidate MTE-A**.

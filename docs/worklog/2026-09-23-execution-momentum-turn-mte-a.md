# Execution Research — Momentum Turn MTE-A

**Date:** 2026-09-23  
**Branch:** `research/execution-engine-design`  
**PR:** #12  
**Status:** research candidate; production Pine intentionally not started

## Objective

Resolve the last deliberately-open numeric kernel in the initial Execution architecture:

> replace legacy Moving Average Shift with a clean-room momentum-turn engine that is normalized, deterministic, small, and suitable for semantic state consumption.

## Legacy findings carried forward

The archived Moving Average Shift remains a donor, not the target product.

Useful:
- relative displacement / normalization
- turn vs acceleration/deceleration reading
- compact lower-pane presentation

Rejected from the final architecture:
- MA-type selector
- 40 / 15 / 500 / 97.5 / 10 defaults as inherited authority
- Original / Zero Cross / Signal Line modes
- percentile warmup
- probability wording
- standalone C/V entry diamonds
- chart candle/MA painting from the Execution product

MAS-0's earlier repairs remain valid evidence:
- unreachable default signal path fixed
- synthetic mintick warmup rejected
- actionable markers close-confirmed
- probability language removed

## Candidate comparison

### Legacy-style percentile displacement change

Not selected.

Main reasons:
- 500-bar warmup
- outlier/regime sensitivity
- complexity
- primary signal measures a change in displacement rather than persistent directional pressure

### ATR-normalized displacement velocity

Research form:

```text
disp = (HLC3 - EMA21) / ATR14
velocity = smooth(disp - disp[3])
```

Useful as acceleration research, but not selected as primary signed core.

Synthetic step/reversal reasoning exposed a problem:
- after a strong direction change, the velocity naturally relaxes back toward zero during a steady trend
- that relaxation can look like counter-acceleration even though the new directional trend continues

### MTE-A — selected first candidate

```text
core = (EMA8(HLC3) - EMA21(HLC3)) / ATR14
```

Then:
- RMA20 core activity -> adaptive neutral band
- one-bar core acceleration
- RMA20 acceleration activity
- meaningful counter-acceleration -> TURN
- ordinary same-direction acceleration/deceleration -> ACCEL / DECEL

This retains persistent signed direction while still detecting a turn before a zero-cross.

## Candidate constants

```text
FAST_EMA       8
SLOW_EMA       21
ATR_LEN        14
ACTIVITY_LEN   20
NEUTRAL_FACTOR 0.15
TURN_FACTOR    0.50
TURN_FLOOR     0.02
ACCEL_EPS      1e-9
```

These are candidate engineering defaults, not operator settings and not claimed optimal values.

## Numerical-invariance defect found by CI

The first synthetic scale/translation test exposed an important defect:

Mathematically equivalent transformed price series could produce:
- `UP_ACCEL` in one series
- `UP_DECEL` in the transformed series

The cause was floating-point sign noise in an acceleration value extremely close to zero.

This was not hidden.

Fix:
- acceleration magnitudes <= `1e-9` are classified as semantic zero

This epsilon is arithmetic stability, not a market threshold.

After the fix, scale/translation state parity passes.

## Executable research artifacts

- `docs/design/MOMENTUM_TURN_ENGINE.md`
- `tools/momentum_turn_reference.py`
- `tools/test_momentum_turn_reference.py`
- `manifests/execution-research-defaults-v1.json`
- `tools/check_execution_research_defaults.py`

The reference implementation uses explicit deterministic smoothing/warmup so the candidate can be validated independently of Pine syntax.

## Synthetic gates

Covered:

- explicit constant contract
- positive price-scale invariance
- price-translation invariance
- flat/zero-volatility behavior
- constant uptrend sanity
- constant downtrend sanity
- up -> down reversal:
  - TURN_DOWN before negative core
  - DOWN_ACCEL after bearish core establishes
- down -> up mirror
- small deterministic oscillatory noise + scale invariance
- malformed OHLC rejection

These are mechanical tests, not evidence of market edge.

## Semantics

MTE-A maps into the existing canonical momentum states:

```text
TURN_UP
UP_ACCEL
UP_DECEL
NEUTRAL
TURN_DOWN
DOWN_ACCEL
DOWN_DECEL
```

TURN is intentionally a state that may persist for multiple bars of meaningful counter-acceleration. It is not another alert family.

Execution's actionable transition remains `CONFIRMA LONG/SHORT`.

## Next evidence

MTE-A is ready for the historical data lab when Binance datasets arrive.

Required market checks:
- state frequency
- dwell time
- chatter
- lead from TURN to zero-cross
- behavior near Market Map correction/retest/reclaim locations
- BTC 15m / 1H / 4H first
- unchanged-default ETH / AVAX robustness later

Until that evidence exists, MTE-A remains a candidate and production `execution.pine` stays blocked.

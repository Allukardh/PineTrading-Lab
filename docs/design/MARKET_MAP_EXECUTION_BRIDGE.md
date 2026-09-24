# Market Map → Execution Bridge

**Status:** canonical integration design for Execution 0.1.x  
**Date:** 2026-09-23  
**Purpose:** convert Market Map geometry/events into one deterministic Execution location state

## 1. Why a bridge exists

Execution should not independently rediscover structure, correction geometry, retests or liquidity reclaims.

Those are Market Map responsibilities.

Execution receives the same canonical Market Map semantics and reduces them to a small location vocabulary:

```text
OUTSIDE
APPROACHING
IN_CORRECTION
RETEST
RECLAIM
DESTINATION_NEAR
```

This location state answers:

> Is price somewhere where execution timing matters?

It is not an entry signal.

## 2. Runtime implementation

Per `RUNTIME_TOPOLOGY.md`, there is no cross-indicator source wiring.

The bridge is a shared generated/recomputed kernel:

- Market Map uses it for the embedded Decision Panel.
- Execution uses the same bridge for the lower-pane state machine.

Repository validation must keep both consumers semantically identical.

## 3. Inputs from Market Map

Conceptual inputs:

- `mapDir`
- `correctionActive`
- `thesisInvalidated`
- `regimeStructureConflict`
- correction envelope geometry: T1 / primary / T3
- confirmed retest event
- confirmed aligned sweep/reclaim event
- `destinationNear`
- ATR

Execution does not create alternative correction levels.

## 4. Correction envelope

Although the normal Market Map panel shows only the **primary** correction zone, Execution may use the full already-computed T1/T2/T3 correction envelope internally.

This does not reintroduce three visible zones.

For a valid correction thesis:

```text
correctionEnvelopeTop    = highest(T1 top, primary top, T3 top)
correctionEnvelopeBottom = lowest(T1 bottom, primary bottom, T3 bottom)
```

`IN_CORRECTION` means current price is inside that valid envelope.

The primary zone remains the strongest visual/confluence area; Execution simply does not treat a valid shallow/deep correction as if price were structurally irrelevant.

## 5. APPROACHING

Initial internal default:

```text
APPROACH_DISTANCE = 0.50 ATR
```

For a bullish map:
- price is still above the correction envelope
- distance to envelope top <= 0.50 ATR

For a bearish map:
- price is still below the correction envelope
- distance to envelope bottom <= 0.50 ATR

Price that has already crossed through the entire envelope toward invalidation is **not** called APPROACHING.

The 0.50 ATR value is an engineering default to validate, not a user input.

## 6. RETEST / RECLAIM memory

A one-bar structural event can be useful for execution for more than one candle.

If Execution required momentum confirmation on the exact event candle, it would often miss a legitimate post-event setup.

Therefore:

```text
EVENT_HOLD_BARS = 3 confirmed chart bars
```

A confirmed aligned retest or sweep/reclaim remains the active location semantic for up to 3 bars, unless:

- thesis invalidates
- structural conflict suppresses the map
- map direction changes
- a newer event replaces it

This is event memory, not repainting.

## 7. Priority

When multiple location conditions are true, use:

```text
1. RECLAIM
2. RETEST
3. IN_CORRECTION
4. APPROACHING
5. DESTINATION_NEAR
6. OUTSIDE
```

Rationale:

- reclaim/retest are the most specific reaction semantics
- correction geometry is more useful for setup readiness than target proximity
- destination proximity primarily drives FORÇA / RISCO DE REAÇÃO, not a fresh entry setup

In normal geometry, correction and destination proximity should rarely overlap.

## 8. Invalid map

Return `OUTSIDE` immediately when:

- `mapDir == 0`
- thesis is invalidated
- regime/structure conflict suppresses the directional map
- ATR/required geometry is unavailable

Execution cannot become PREPARANDO/ARMADO from an invalid map.

## 9. Timing

Historical/confirmed bars:
- location is deterministic from confirmed Market Map state

Open realtime bar:
- geometry such as APPROACHING / IN_CORRECTION may update live
- retest/reclaim memory starts only from confirmed events
- `CONFIRMA LONG/SHORT` still requires chart-close confirmation

Thus the operator can see a setup forming without allowing provisional location to fabricate a confirmed signal.

## 10. Reference implementation

The architecture branch includes:

- `tools/market_execution_bridge_reference.py`
- `tools/test_market_execution_bridge_reference.py`

These validate the location contract independently of Pine syntax.

Production Pine must later match the same semantics.

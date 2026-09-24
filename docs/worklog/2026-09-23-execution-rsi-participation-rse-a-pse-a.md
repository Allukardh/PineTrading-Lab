# Execution Research — RSI RSE-A + Participation PSE-A

**Date:** 2026-09-23  
**Branch:** `research/execution-engine-design`  
**PR:** #12  
**Status:** research candidates; production Pine intentionally not started

## Objective

After MTE-A stabilized mechanically, define the two remaining reload-safe Execution evidence families:

1. RSI State Engine — recovery/exhaustion/context
2. Participation Engine — relative volume + honest OHLC pressure proxy

The goal is to replace the old RSI table + Buying/Selling Volume panel with semantic evidence, not to reproduce their UI.

---

## RSE-A — RSI State Engine

### Legacy evidence retained

From RSI MTF Tactical:
- RSI 14
- center 50
- center buffer ±2
- 70/30 standard extension
- 80/20 extreme extension
- 0.25 minimum directional step
- recent-direction concept

### Legacy surface retired

- four manual timeframe inputs
- current/previous/previous-2 table
- live `lookahead_off` HTF state
- RSI MA/cloud as a required decision input
- Stochastic RSI default
- divergence default

### Local semantic states

RSE-A uses the existing suite enum:

```text
EXTREME_OVERBOUGHT
RECOVERING_OVERBOUGHT
FADING_OVERBOUGHT
BULL
NEUTRAL
BEAR
RECOVERING_OVERSOLD
FADING_OVERSOLD
EXTREME_OVERSOLD
```

The exact priority/memory rules are canonical in:

`docs/design/RSI_STATE_ENGINE.md`

### Recovery/fade memory

A raw RSI zone should not lose all meaning at 30.1 or 69.9.

Candidate memory:

```text
2 confirmed bars
```

Examples:
- oversold touch + rising RSI can remain `RECOVERING_OVERSOLD` briefly after exiting 30
- overbought touch + falling RSI can remain `FADING_OVERBOUGHT` briefly after exiting 70

### HTF context separated from local state

A major architecture refinement:

RSE-A outputs:
- local RSI semantic state
- separate confirmed HTF RSI direction: -1 / 0 / +1

HTF mapping:

```text
RSI <= 48  BEAR
48–52      NEUTRAL
RSI >= 52  BULL
```

Execution readiness now applies:
- valid local state
- confirmed HTF must not oppose

Neutral HTF does not block a valid local recovery.

The executable Execution reference model was updated with `rsi_context_dir` and tests prove that opposing confirmed context:
- blocks ARMADO
- cancels an already-ARMED setup

The Strength axis still uses local exhaustion semantics rather than double-counting HTF opposition as a separate deterioration family.

### RSE-A executable artifacts

- `docs/design/RSI_STATE_ENGINE.md`
- `tools/rsi_state_reference.py`
- `tools/test_rsi_state_reference.py`

Tests cover:
- deterministic Wilder RSI bounds
- monotonic extremes
- center dead-band
- recovery/fade memory
- memory expiry
- continuation states
- extreme-state priority
- HTF 48/52 boundaries
- context support/opposition

---

## PSE-A — Participation Engine

### Legacy truth made explicit

The archived Buying/Selling Volume script computes:

```text
buy = volume * (close-low)/(high-low)
sell = volume * (high-close)/(high-low)
```

The directional difference is mathematically equivalent to:

```text
pressure = (2*close - high - low)/(high-low)
```

Therefore the historical "buy/sell volume" is a **close-location pressure proxy**, not aggressor flow.

PSE-A keeps the useful information and removes the false implication.

### Reload-safe production candidate

```text
baseline = prior confirmed EMA20(volume)
relativeVolume = current volume / baseline

pressure = candle close-location in [-1,+1]
directionalPressure = pressure * mapDir
```

Candidate pressure threshold:

```text
abs directional agreement threshold = 0.20
```

Interpretation:
- +0.20 corresponds to a bullish close at >=60% of the candle range
- -0.20 mirror

### Semantic mapping

```text
relativeVolume < 0.80
    -> WEAK

relativeVolume >= 1.20
and directionalPressure >= +0.20
    -> CONFIRM

relativeVolume >= 1.20
and directionalPressure <= -0.20
    -> CONTRARY

otherwise
    -> NEUTRAL
```

Strong expansion >=1.50 remains a diagnostic flag, not a new enum.

### Why prior confirmed EMA baseline

PSE-A uses the prior EMA20 baseline rather than including the current bar in its own denominator.

Benefits:
- cleaner interpretation of "current participation vs previous baseline"
- current spike does not damp itself
- open-bar relative volume can evolve against a fixed confirmed reference
- close-confirmed Execution still remains deterministic

This is a candidate design decision to validate historically.

### Binance taker data as validation truth

Issue #14's delegated market-data pipeline preserves taker-buy fields.

Offline only:

```text
takerImbalance = 2 * takerBuyBase / volume - 1
```

This is not a Pine dependency.

Its purpose is to test whether PSE-A's OHLC pressure proxy is useful enough to keep.

The historical lab should measure:
- proxy/taker sign agreement
- correlation
- behavior by timeframe
- behavior during expanded relative volume
- whether the 0.20 proxy threshold improves semantic quality

If the proxy adds little value, simplify/remove it.

### PSE-A executable artifacts

- `docs/design/PARTICIPATION_ENGINE.md`
- `tools/participation_reference.py`
- `tools/test_participation_reference.py`

Tests cover:
- proxy endpoint math
- zero-range safety
- price scale/translation invariance
- volume-scale invariance
- baseline warmup
- CONFIRM / CONTRARY / WEAK / NEUTRAL mapping
- map-direction mirroring
- missing/zero volume
- validation-only taker imbalance

---

## Machine-readable defaults

`manifests/execution-research-defaults-v1.json`

now covers:
- MTE-A
- RSE-A
- PSE-A
- Market Map -> Execution bridge

`tools/check_execution_research_defaults.py` prevents reference constants from drifting away from the manifest.

The suite semantic manifest also now includes:

```text
rsi_context_dir = -1 / 0 / +1
```

and CI validates it.

---

## Current Execution research stack

```text
Market Map location bridge
        ↓
MTE-A Momentum
+
RSE-A local RSI + confirmed HTF context
+
PSE-A reload-safe participation
        ↓
Execution semantic state machine
        ↓
EXECUÇÃO + FORÇA
```

No production Pine has been created.

This is deliberate: market-data validation should challenge the formulas before renderer/code-generation work makes them expensive to change.

## Latest automated gate

At this worklog point the integrated research CI passes:
- archive/reboot integrity
- Execution semantic reference tests
- Market Map -> Execution bridge tests
- MTE-A tests
- RSE-A tests
- PSE-A tests
- suite semantic manifest check
- Execution research-default manifest check

Run: `35948648459` — PASS

## Next independent work

While Issue #14 builds Binance datasets:
- prepare the historical research questions/report contract for the three evidence engines
- do not optimize numeric defaults without market data
- do not create production `execution.pine`

When the Binance dataset pipeline lands, use real data to challenge:
- MTE-A state frequency/chatter
- RSE-A state overlap/redundancy vs MTE-A
- PSE-A proxy vs taker imbalance
- whether all three evidence families add independent information

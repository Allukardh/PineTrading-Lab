# Market Map MM-0 — first integrated map prototype

**Date:** 2026-09-23  
**Candidate:** `src/core/market-map.pine`  
**Version:** 0.1.0  
**Status:** compile/static PASS; interactive visual validation pending

## Design freedom

The operator explicitly authorized the project to depart from legacy MA 6x/Fibonacci behavior and to use profiles only where they genuinely improve the product.

MM-0 therefore does **not** attempt to reproduce MA 6x visually.

## Minimal settings

MM-0 exposes only:
- Show moving averages
- Show panel
- Advanced: show BOS/CHoCH + secondary correction zones

The Clean/Standard/Detailed dropdown was removed. One well-designed default view is preferable to making the operator choose another presentation mode.

There is deliberately **one panel only**. Compact/Full panel variants are prohibited; diagnostic detail must not compete with the decision-facing panel.

No trading profile exists in MM-0 because the map itself does not yet need competing operating personalities.

Engineering thresholds are internal constants.

## Trend/regime model

MM-0 uses three visible EMA layers:
- EMA 21 — short response
- EMA 50 — intermediate structure
- EMA 200 — long regime

This is a deliberate simplification from the legacy six-MA overlay.

A confirmed higher-timeframe context is selected automatically:
- chart <= 15m → 1H
- chart <= 1H → 4H
- chart <= 4H → 1D
- chart <= 1D → 1W

HTF data uses the confirmed `[1] + lookahead_on` policy already validated in SignalGate.

## Structure engine

- confirmed pivots
- HH/LH and HL/LL classification
- BOS / CHoCH state
- breakout level memory
- confirmed retest state

## Liquidity engine

Clean-room structural-liquidity implementation:
- confirmed pivot highs/lows become candidate pools
- equal highs/lows receive stronger relevance
- pools are marked swept only on confirmed chart bars
- pivot confirmation delay is reconstructed: a newly confirmed pivot is immediately marked swept if price already crossed it during the right-side confirmation bars
- only the nearest unswept pool above and below price is shown by default
- no claim is made that these are actual leveraged-liquidation clusters

## Correction Engine

Uses the latest confirmed structural impulse and produces:
- T1: 0.382–0.500
- T2: 0.500–0.618
- T3: 0.618–0.786
- structural invalidation beyond the impulse origin with a small ATR buffer

T2 receives a **confluence count**, not a probability, from:
- Fibonacci zone itself
- EMA 50 proximity
- previous breakout/retest level
- nearest structural liquidity
- latest structural swing

## Phase classifier

Current semantic states:
- MAPEANDO
- TRANSIÇÃO
- IMPULSO
- ROMPIMENTO / IMPULSO
- PULLBACK
- CORREÇÃO
- CORREÇÃO PROFUNDA
- RETESTE

## Visual contract

Default Standard:
- EMA 21 / 50 / 200
- T1/T2/T3 current correction zones
- nearest structural liquidity above/below
- invalidation
- compact semantic panel

Clean:
- keeps T2 only for correction focus

Detailed:
- adds BOS / CHoCH / retest event markers

Only the **current map** is boxed. Historical box clutter is intentionally avoided.

## Deferred

MM-0 does not yet include:
- volume profile / POC confluence
- previous day/week highs/lows
- advanced multi-zone ranking
- Execution confirmation
- real derivatives liquidation data
- alerts

## Validation gates

1. Pine v6 server compile: 0 errors / 0 warnings
2. repository integrity
3. BTCUSDT 15m / 1H / 4H / 1D visual sanity
4. confirmed structure/liquidity reload parity
5. correction-zone sanity against historical impulses
6. default UX: useful without engineering-parameter tuning


## Automated validation evidence

- Pine compile run `35903976581`: **PASS**
- compiler errors: **0**
- compiler warnings: **0**
- static integrity run `35903976738`: **PASS**

The first compiler attempt correctly rejected dynamic `plotshape()` text. MM-0 was changed to separate constant-text BOS/CHoCH markers and then recompiled cleanly.


## MM-0.2 refinement — 2026-09-23

### Single-panel UX locked
The legacy Compact/Full split is explicitly retired. Market Map has one curated semantic panel. Visual mode changes chart-overlay density only.

### External structural liquidity
The Liquidity Engine now ranks the nearest unswept candidate from:
- confirmed swing pool
- equal-high/equal-low pool
- Previous Day High / Low
- Previous Week High / Low

The panel identifies the winning source as `SWING`, `EQH/EQL`, `PDH/PDL`, or `PWH/PWL`.

Daily/weekly candidates maintain session-scoped sweep state so a previously consumed level is not presented as untouched liquidity.

### Failed breakout
A confirmed breakout that closes back through its break level within the bounded failure window is classified as `FALSO ROMPIMENTO`.

If a CHoCH fails, structural direction is restored to the pre-break state instead of leaving a false reversal committed.

### Automated gates after refinement
- Pine compile PR run `35926083757`: **PASS**
- compiler errors: **0**
- compiler warnings: **0**
- static integrity run `35926099371`: **PASS**


## Adaptive correction + volume acceptance refinement

The Correction Engine now keeps up to 24 completed structural pullbacks separately for bullish HH→HL and bearish LL→LH sequences.

With at least 5 valid samples:
- the primary correction zone becomes adaptive around the recent median retracement depth
- IQR-derived spread controls zone width within bounded engineering limits
- the fallback remains 0.500–0.618 when sample history is insufficient

The current structural impulse is also scanned for volume acceptance:
- impulse VWAP: exact bar-volume weighted mean across the bounded impulse sample
- VNode: highest-volume hlc3 price bin inside the impulse
- VNode is **not** labeled POC because it is a bar-level approximation, not exchange volume-at-price

Correction confluence can now include:
- structural impulse
- overlap with the classic 0.500–0.618 core
- EMA 50
- BOS/retest level
- nearest structural liquidity
- impulse volume acceptance

The panel now says `CORREÇÃO`, not `T2`, and the context indicates `ADAPT n` or `FIB`.


## Volume-profile donor decision

The donor library contains full histogram/profile implementations, including ChartPrime POC logic and LuxAlgo clustered volume profiles. MM-0 intentionally does **not** transplant those implementations.

Reasons:
- they add substantial chart/object complexity
- clustered/K-means profile output is not necessary to answer the current Market Map questions
- third-party provenance/licensing remains separate
- a cleaner current-impulse acceptance model can supply useful confluence without pretending to be exchange volume-at-price

MM-0 therefore uses:
- exact bar-volume weighted mean price across the bounded structural impulse (`impulseVwap`)
- a clean-room 20-bin hlc3-volume node (`impulseVNode`)

`impulseVNode` is documented as an approximation and is never labeled `POC`.

An exact profile-style POC will only be added later if visual/market validation shows meaningful incremental information.

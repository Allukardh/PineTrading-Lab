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


## Regime vs structure conflict policy

Regime is intentionally slower than phase: a routine pullback should not erase a higher-timeframe trend.

However, when the slow regime and confirmed local structure point in opposite directions, MM-0 no longer forces a correction map in the old regime direction.

Policy:
- keep the slow `REGIME` label
- keep the confirmed `ESTRUTURA` label
- set `FASE = TRANSIÇÃO ESTRUTURAL`
- suppress directional correction-zone mapping until the conflict resolves

This prevents a local confirmed reversal from being mislabeled as an ordinary pullback merely because the slow MA/HTF regime has not flipped yet.


## First BTCUSDT visual matrix — operator screenshots

Received the first real TradingView screenshots at:
- BTCUSDT 15m
- BTCUSDT 1H
- BTCUSDT 4H
- BTCUSDT 1D

### What worked
- chart remained substantially cleaner than the legacy suite
- EMA 21/50/200 remained readable
- 4H and 1H correctly exposed regime/structure disagreement instead of inventing a clean continuation thesis
- 15m produced an adaptive correction zone and nearby liquidity without filling the chart with historical boxes
- liquidity-source labels were immediately interpretable

### Problems exposed
1. **Structure row ambiguity**
   - examples such as `HH/HL ↓` and `LH/LL ↑` mixed the last swing taxonomy with the last break direction
   - technically explainable, visually confusing

2. **Daily confirmation lag**
   - 1D showed `MAPEANDO` after an obvious developing breakout/impulse because the terminal pivot high was not yet confirmed
   - confirmed-only structure is correct for historical semantics, but too slow for a live correction map

3. **Status-line telemetry clutter**
   - structural plotshapes leaked repeated 0.00 values into the TradingView indicator status line

4. **Inactive correction model text**
   - context could show `FIB` / `ADAPT 24` even when no correction zone was active

### Changes from this visual gate
- added semantic last-event structure text, e.g. `CH↓ • HH/HL`, rather than an unexplained directional arrow after the swing pair
- added a **LIVE developing impulse** started by a confirmed breakout; its extreme expands until superseded/invalidated
- Correction Engine prefers the newer LIVE impulse when a terminal pivot is not yet confirmed
- LIVE zones are explicitly labeled `LIVE/FIB` or `LIVE/ADAPT n`
- fakeout invalidates the LIVE impulse
- structural plotshape telemetry is removed from the TradingView status line
- context only shows the correction model when an active correction map exists

### Gate status
The first matrix is **informative but not PASS** because it found real semantic/latency issues. A focused retest is required after the above fixes.


## Focused visual retest — 15m + 1D

Second operator screenshots received after LIVE-impulse and status-line cleanup.

### 1D — major improvement
Observed:
- Regime: ALTA
- Phase: PULLBACK
- Correction: approximately 78.8k–81.5k with five confluence stars
- Liquidity above: PDH around 86.7k
- Liquidity below: structural swing around 75.0k
- Invalidation: around 74.7k
- Context: W • HTF CONF • LIVE/ADAPT 24

This resolves the prior daily `MAPEANDO` failure. The developing impulse can now project a useful pullback zone before the terminal daily pivot is confirmed.

### 15m — useful map, remaining semantic issue found
Observed:
- status-line 0.00 clutter is gone
- adaptive correction zone rendered around 84.36k–84.44k
- nearest liquidity above/below rendered cleanly
- price was only a few dollars from the displayed bearish-thesis invalidation

The structure row still displayed a stale prior event (`CH↑ • HH/HL`) even though the active map/invalidation was bearish. This is a presentation bug caused by retaining the last structure-event label after a failed break/reversion.

The screenshot also showed a more important UX opportunity: when price is extremely close to invalidation, `CORREÇÃO PROFUNDA` is less useful than saying explicitly that the thesis is being tested.

### Fixes made from the retest
- structure row now reports **current active structural direction**:
  - `ALTA • HH/HL`
  - `BAIXA • LH/LL`
  - `ALTA • REVERSÃO`
  - `BAIXA • REVERSÃO`
  - mixed states where appropriate
- stale `lastStructureEvent` state removed
- added explicit thesis lifecycle:
  - `TESTE DE INVALIDAÇÃO` when price is within 0.20 ATR of invalidation or crosses it intrabar
  - `TESE INVALIDADA` only after a confirmed close beyond invalidation
- confirmed invalidation persists for the same impulse and suppresses the stale correction map until a new structural impulse is created
- panel shows `ROMPIDA • <price>` for a confirmed invalidation

### Automated validation after fixes
- Pine compile run `35931283445`: **PASS — 0 errors / 0 warnings**
- updated static-integrity run `35931316729`: **PASS**

The 1D LIVE correction map is now considered a strong visual result. The 15m screenshot was valuable because it exposed the last-event/active-structure ambiguity and the need for a real invalidation lifecycle.


## Destination Engine

Market Map now separates **where a correction can react** from **where the active directional thesis is trying to go**.

### Semantics
- `CORREÇÃO` = projected pullback/retest reaction zone
- `DESTINO` = intact structural liquidity in the active map direction
- `LIQ ↑ / LIQ ↓` = raw nearest liquidity on each side for context
- `INVALIDA` = level that breaks the current thesis

### Target ladder
`DESTINO` contains:
1. nearest intact directional liquidity
2. next distinct directional liquidity when available

Levels closer than `0.10 ATR` are treated as the same destination cluster rather than two fake independent targets.

Example:
```text
DESTINO  86.717 • PDH → 87.279 • EQH
```

When the first destination is within `0.30 ATR`, the panel marks it `PRÓX.`. This is deliberately a **reaction-risk / destination-proximity signal**, not an automatic sell/buy instruction.

This keeps the responsibility split clean:
- Market Map says where structurally relevant destinations are
- Execution will later decide whether momentum/participation supports entry, continuation or exit timing


### Stale-destination rule

A confirmed thesis invalidation now suppresses `DESTINO` for that impulse. Raw `LIQ ↑ / LIQ ↓` remain visible as market context, but the panel no longer presents a directional destination as if the invalidated thesis were still active.


## MM-0 POC scope decision

An exact profile-style POC is **not** being added to MM-0.

The current combination of:
- structural liquidity
- adaptive correction depth
- impulse VWAP
- approximate VNode
- BOS/retest level
- EMA context

already provides enough independent confluence for the foundation.

Adding a full volume-profile engine now would increase object/algorithm complexity and risk chart clutter without demonstrated incremental decision value. It remains available as a future research option, but is not a missing requirement for Market Map 0.1.0.


## Historical sanity instrumentation

MM-0 now contains chart-native engineering telemetry in the TradingView **Data Window only**. It does not add chart labels, a second panel, or normal operator settings.

Tracked counters:
- historical thesis instances
- first touch of the primary correction zone
- original directional destination hit
- confirmed invalidation
- zone → destination resolved outcomes
- zone → invalidation resolved outcomes
- engineering-only zone → destination percentage over resolved post-zone outcomes

Important interpretation:
- this percentage is **not** displayed in the trading panel
- it is **not** a predictive probability
- it exists only to test whether the Correction Engine behaves sensibly on the chart's loaded history

The thesis identity is based on **impulse origin + direction**, so the same thesis is not double-counted when a LIVE impulse later receives a confirmed terminal pivot.

## Destination-hit lifecycle

The panel now preserves one bar of event context when the previous directional target is reached:

```text
DESTINO  ATINGIDO 86.717 • PDH → 87.279 • EQH
```

After that, the normal destination ladder continues from the next intact liquidity pool.


### OHLC ambiguity policy

Historical candles do not reveal intrabar ordering.

The diagnostics therefore **exclude ambiguous outcome ordering** when:
- the first correction-zone touch and destination/invalidation occur on the same candle, or
- destination and invalidation boundaries are both crossed on the same candle after a prior zone touch

Those cases are counted separately as `Resultados ambíguos` and do not enter `Zona→Destino % (engenharia)`.

`Zona sem desfecho` also exposes censored/open historical cases instead of silently treating them as wins or losses.


## Offline CSV validation harness

MM-0 now exposes a versioned, Data-Window-only audit schema specifically for TradingView CSV export.

Added:
- `MM Audit • Schema = 1`
- explicit confirmed/provisional bar state
- per-bar geometry/state audit series
- per-bar semantic event series
- deterministic Python analyzer: `tools/analyze_market_map_export.py`
- analyzer unit tests wired into Static Integrity CI
- reload-parity comparison mode

Historical outcome tracking was tightened so the directional target is frozen when the primary correction zone is first touched, not when the thesis first exists. This makes the validation question match the actual decision-time map.

The current unconfirmed candle is excluded from deterministic pathology/reload checks through the exported confirmation state.

Volume-acceptance evidence can add correction confluence only after bar confirmation.

This converts the remaining historical-sanity gate from screenshot inspection into a reproducible CSV evidence workflow.


## Sweep/reclaim promotion

The liquidity engine previously knew whether pools had been consumed but did not surface the important distinction between:
- acceptance/break through liquidity
- wick-through + close-back reclaim

MM-0 now captures the nearest newly consumed structural/PDH/PDL/PWH/PWL level that is reclaimed on the same confirmed candle.

Effects:
- `FASE = SWEEP / RECLAIM` when the reclaim agrees with the active map direction
- reclaimed liquidity remains eligible as the liquidity confluence for the active correction zone on that event bar
- no extra operator setting or panel row
- schema-2 CSV audit exports the reclaim direction for offline analysis

## Stable volume-confluence timing

The current-bar volume acceptance layer now freezes to the previous confirmed bar while the new realtime candle is open. Historical zone-touch bars receive an event-local acceptance calculation.

This fixes a subtle lifecycle defect where a volume-confluence star could otherwise appear at close and disappear immediately at the next candle open.


## Superseded-outcome accounting

Historical telemetry previously left a touched-but-replaced thesis inside `Zona sem desfecho` forever.

MM-0 now classifies that lifecycle explicitly:
- when a new thesis starts while the prior thesis had touched its correction zone but had no resolved outcome, `diagSupersededAfterTouch` increments
- `Zona sem desfecho` subtracts resolved, ambiguous **and superseded** cases
- the invalidation cumulative label was clarified to `Invalidações pós-toque`

This makes censored historical cases explicit instead of silently contaminating the open-outcome count.


## Validation-route change — TradingView Essential

The operator confirmed the active TradingView plan is Essential and does not provide the CSV export capability assumed by the first MM-0 validation design.

Decision:
- do not require a Premium upgrade;
- preserve audit schema v2 and the CSV analyzer as optional/reusable tooling;
- make official Binance historical data the primary quantitative validation source;
- use Issue #14's delegated pipeline for BTCUSDT 15m/1H/4H/1D plus 3D/1W robustness;
- build a deterministic offline Market Map research/audit equivalent before using Binance history to judge Correction/Destination semantics;
- retain targeted TradingView visual/reload checks as the final Pine/runtime parity gate.

This changes the validation transport, not the MM-0 product semantics.

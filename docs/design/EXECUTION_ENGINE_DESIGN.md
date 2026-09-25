# Execution Engine — Design Research

**Status:** research only; implementation starts after Market Map MM-0 promotion  
**Date:** 2026-09-23  
**Product:** Execution

## 1. Product role

Execution answers one question:

> Given the current Market Map thesis, is price action confirming an entry/continuation/reaction **now**?

Execution does **not** own:
- structural regime
- correction-zone geometry
- liquidity destinations
- structural invalidation

Those belong to Market Map.

Execution owns:
- momentum turn / acceleration
- exhaustion / recovery
- participation / relative volume
- confirmed timing state
- minimal entry/continuation markers

The output must be semantic, not a collection of oscillator conditions.

Execution uses two orthogonal semantic outputs.

**Readiness**
- **AGUARDAR**
- **PREPARANDO LONG / SHORT**
- **ARMADO LONG / SHORT**
- **CONFIRMA LONG / SHORT** — one-bar transition event
- **ALINHADO LONG / SHORT** — persistent execution alignment, not position tracking

**Strength**
- **NORMAL**
- **PERDENDO FORÇA**
- **EXAUSTÃO**
- **RISCO DE REAÇÃO**

The detailed transition contract lives in `EXECUTION_STATE_MACHINE.md`.

No arbitrary probability percentage.

## 2. Legacy core findings

### 2.1 Moving Average Shift

Useful concepts:
- normalized distance from a base MA
- oscillator acceleration/deceleration
- reversal-style signal modes
- compact momentum visualization

Known legacy defects:
- default Original + Setup filter is logically unreachable
- Signal Line mode has the same sign/filter contradiction
- percentile warmup substitutes unavailable data with mintick, creating extreme normalization
- entry markers are not explicitly close-confirmed
- “probability” naming is not statistical probability
- too many MA/signal-mode choices for a production default

Preserved MAS-0 research already fixes:
- acceleration-based setup
- honest percentile warmup
- close-confirmed markers
- strength rather than probability semantics

Decision:
- reuse the **momentum-turn concept**, not the legacy configuration surface
- one engineered default oscillator path first; no three-mode selector unless later evidence justifies it

### 2.2 RSI MTF Tactical

Useful concepts:
- RSI 14 baseline
- centerline direction
- acceleration across recent bars
- overbought/oversold and extended exhaustion states
- regular/hidden divergence research
- MTF momentum agreement

Legacy problems:
- four manually configured timeframes
- large historical table
- HTF requests use live `lookahead_off` values, so current HTF states can change intrabar
- many disabled feature families remain in normal code
- repeated current/previous RSI table values are information-heavy but decision-light

Decision:
- Auto timeframe context only
- confirmed HTF RSI where it is used for state
- no multi-row RSI table
- current RSI value itself is secondary; semantic state is primary
- divergence remains optional research until it proves incremental value

### 2.3 Buying/Selling Volume 2-in-1

Useful concepts:
- relative-volume normalization
- volume participation vs its moving baseline
- directional pressure proxy
- separating historical and realtime evidence

Important limitation:
Historical `buyVol/sellVol` is derived from candle close location inside the high-low range. It is **not actual aggressor buy/sell volume**.

Decision:
- historical component is labeled **pressure proxy**, never true market delta
- use relative volume and expansion/contraction as the main historical participation evidence
- do not expose RAW/VI mode selection to the operator

## 3. Donor findings

### Realtime Volume Bars

High-value concept:
- `varip` incremental volume tracking during a realtime bar
- volume increments assigned to up/down/neutral tick movement

Hard limitation:
- accurate split exists only after the indicator starts observing realtime updates
- it resets on reload, symbol change or settings change
- it cannot reconstruct historical aggressor flow

Decision:
Execution may observe two participation evidence classes internally:
- **Historical/reload-safe:** relative volume + candle pressure proxy
- **Realtime-only:** incremental up/down volume delta when genuinely available

For 0.1.0, realtime-only delta may annotate the live view but **cannot create, cancel or alter a reload-reconstructible CONFIRMA event**.

The UI/diagnostics must disclose the distinction if realtime delta is used.

### MA MTF Momentum Histogram

Useful concept:
- simple fast-minus-slow MA momentum
- HTF state uses confirmed `[1] + lookahead_on`

Decision:
- confirmed HTF momentum implementation pattern is useful
- the large MA selector is not

### RSI research donors

Useful research directions:
- RSI centerline regime
- momentum acceleration
- exhaustion zones
- regular/hidden divergence

Decision:
- start simple
- divergence does not become a default blocker until validated

## 4. Proposed engine architecture

### 4.1 Momentum Turn Engine

Inputs under the hood:
- normalized MA distance
- oscillator acceleration
- zero/reversal context
- short smoothing

Semantic output:
- `TURN_UP`
- `UP_ACCEL`
- `UP_DECEL`
- `TURN_DOWN`
- `DOWN_ACCEL`
- `DOWN_DECEL`
- `NEUTRAL`

Markers are close-confirmed.

### 4.2 RSI State Engine

Base:
- RSI 14
- centerline 50 with small dead-band
- slope / recent-step direction
- 70/30 exhaustion
- 80/20 extended exhaustion

Confirmed HTF context is automatic.

Semantic output:
- bullish momentum
- bearish momentum
- recovering from oversold
- fading from overbought
- extended exhaustion
- neutral/conflict

### 4.3 Participation Engine

Historical evidence:
- relative volume vs EMA/SMA baseline
- volume expansion/contraction
- candle-location pressure proxy, explicitly approximate

Realtime enhancement:
- `varip` up/down incremental volume delta
- only active when genuine realtime accumulation exists
- never backfilled as historical truth

Semantic output:
- `CONFIRMA`
- `NEUTRO`
- `FRACO`
- `CONTRARIA`
- `RT+` / `RT-` only as optional live annotation
- `SEM DADO RT` only in diagnostics

## 5. Execution state machine

Execution should not fire simply because one oscillator crosses.

A candidate state is built from:

1. **Context direction**
   - supplied conceptually by Market Map
   - during standalone validation, use an internal simplified directional context

2. **Location**
   - correction/retest context belongs to Market Map
   - Execution should become more interested near a valid reaction zone, not everywhere

3. **Momentum**
   - turn / acceleration in thesis direction

4. **RSI**
   - recovery/continuation rather than blindly “oversold = buy”

5. **Participation**
   - volume evidence supports the move or at least does not contradict it

Canonical readiness path:

```text
AGUARDAR
  ↓ relevant location
PREPARANDO LONG
  ↓ momentum + RSI align
ARMADO LONG
  ↓ close confirmation + reload-safe participation
CONFIRMA LONG     (one-bar event)
  ↓
ALINHADO LONG
```

Mirrored for short.

Loss of setup quality before confirmation returns to `AGUARDAR`. After confirmation, ALINHADO persists until a canonical cancellation condition occurs; strength/reaction risk is reported separately.

See `EXECUTION_STATE_MACHINE.md` for transition/reset semantics.

## 6. Exit / correction-warning role

Execution must also help with the user's second need: recognizing when a move is losing quality **before/around a correction**.

Potential warning state uses:
- price approaching Market Map DESTINO
- momentum deceleration
- RSI exhaustion/failure to extend
- relative-volume fade or opposing realtime delta

Semantic output:

- `FORÇA NORMAL`
- `PERDENDO FORÇA`
- `EXAUSTÃO`
- `RISCO DE REAÇÃO`

The strongest reaction warning requires a meaningful Market Map location plus deterioration/exhaustion evidence. It is a risk warning, not an automatic exit command or calibrated probability.

## 7. UI policy

Execution is one lower pane.

Per `RUNTIME_TOPOLOGY.md`, the full suite Decision Panel is embedded in Market Map. Execution must not create a second full panel.

Default visible content:
- one momentum histogram/line
- minimal state color
- only confirmed LONG/SHORT markers on chart if useful

No:
- standalone RSI table
- buying/selling percentage table
- Compact/Full panel variants
- multiple signal-mode selector
- four manual MTF selectors
- dozens of thresholds

Normal settings target:
- show/hide chart markers
- optional appearance
- perhaps **no profile at all** for 0.1.0

## 8. Timing policy

- actionable state transitions commit on chart close
- HTF context uses confirmed values
- realtime volume delta may update intrabar as an annotation
- realtime-only evidence cannot create, cancel or alter a confirmed reload-safe signal
- realtime-only evidence must never rewrite historical bars as if equivalent data existed

## 9. Validation requirements

Before promotion:
- Pine compile: 0 errors / 0 warnings
- no unreachable default signal path
- no synthetic percentile warmup spikes
- no live HTF repaint in confirmed state
- markers survive close/reload
- historical vs realtime volume semantics clearly separated
- BTCUSDT 15m / 1H / 4H matrix
- enough historical engineering telemetry to detect always-on / never-on gates
- no optimization to one screenshot or one timeframe

## 10. Implementation order

After Market Map MM-0 promotion:

1. create Execution 0.1.0 clean-room shell
2. integrate repaired MA Shift momentum turn
3. add auto confirmed-HTF RSI state
4. add historical relative-volume participation
5. build semantic readiness + strength state machines
6. add correction/exhaustion warning
7. add optional realtime incremental delta annotation
8. add audit/reload validation
9. only then add alerts

## 11. Explicit non-goals for Execution 0.1.0

- no order-book claims
- no actual liquidation-flow claims
- no fake buy/sell volume history
- no arbitrary win probability
- no strategy auto-trading
- no optimization profiles unless validation proves they add real value

# Initial Audit — 53-script reboot

**Date:** 2026-09-22  
**Scope:** all 53 extracted sources; deep review of six core scripts plus donor/risk scan of 47 references.  
**Status:** static/source audit only. Reboot compile/runtime gates are not yet claimed PASS.

## Executive result

The extraction itself is healthy: 53/53 sources, zero exporter failures. The reboot is still justified because the core set contains timing, logic and semantic issues that matter when the indicators support real trading decisions.

## First destination — SignalGate Dashboard

SignalGate is first because it is the central GO/WATCH/NO-TRADE engine and multiple gates depend on timeframe requests.

Blockers:
1. Its helper requests current HTF expressions with `lookahead_off`. Historical future leak is avoided, but realtime HTF values remain unconfirmed and can differ after reload.
2. Auto trigger TF maps every intraday chart to 1H. On charts above 1H this becomes an LTF request through `request.security()`; TradingView documents that this returns only one intrabar and is generally limited for lower-timeframe analysis.
3. Break/retest events are not hard-gated to a new confirmed trigger-context bar, so event timing can drift from intended 1H-close semantics.
4. Those events feed score, EARLY/GO, IN_PLAY, fakeout and alerts.

**Milestone SG-0:** build a deterministic timeframe access layer before changing score weights or adding features.

## Core findings

### Buying Selling Volume 2-in-1
- Low structural complexity.
- “Buy/sell volume” is a candle-location allocation proxy, not aggressor volume, DOM or historical tick delta.
- Realtime donor script offers a `varip` incremental-volume model, but only realtime bars can support that behavior.
- Promotion blocker is mainly semantic clarity and architecture of proxy-vs-realtime modes.

### Liquidity Zones Tactical
- **Score defect:** an inactive side still gets 10 points from `eq*Mitigated ? 5 : 10`; the contribution is not guarded by `eq*Exists`.
- Pivot confirmation creates a blind interval: zones are timestamped at the pivot bar but only become known `pivotR` bars later; intervening touches/invalidation are not reconstructed.
- Only one active zone per side is retained.
- Sweep conditions can remain true across bars; static `alertcondition()` paths are not per-zone edge events.
- Volume dominance reuses the candle-location volume proxy.

### MA 6x
- MTF averages/slopes use current HTF values; chart `barstate.isconfirmed` does not confirm the HTF context.
- `continuationProb` is a weighted quality score, not a calibrated probability.
- `noiseProb` is rule-based, not probabilistic.
- With MTF disabled, `mtfAligned=true` still adds positive continuation/confidence points.
- Cross ETA is linear slope extrapolation; useful as an estimate, not a probability forecast.
- Strong donor: `.MA MTF Momentum Histogram` uses the confirmed-HTF `[1] + lookahead_on` pattern.

### Moving Average Shift
- **Critical default logic defect:** Original long requires oscillator below the negative threshold, while default Setup filter requires oscillator > 0; Original short requires oscillator above the positive threshold while Setup requires oscillator < 0. With defaults, Original-mode entry signals are mutually excluded.
- Percentile warmup replaces unavailable percentile with `syminfo.mintick`, which can create extreme normalized values instead of waiting for valid warmup.
- “probBull/probBear” are directional states, not probabilities.
- Realtime signal confirmation is not explicit.
- This is queued immediately after SignalGate because the defect is localized and easy to regression-test.

### RSI MTF Tactical OB/OS
- Four MTF RSI requests use current HTF values; these can change before the HTF candle closes.
- Chart-bar confirmation does not make those HTF values confirmed.
- Divergence uses negative plot offsets: confirmed pivots are drawn back on the pivot bar. That is retroactive visualization and must be made explicit.
- Inputs do not enforce extended OB > OB / extended OS < OS.
- `.RSI Trendlines with Breakouts` is quarantined because its optional HTF branch uses `lookahead_on` without an offset.

### SignalGate Dashboard — additional findings
- Mode C behaves like an event state, not a persistent reversal regime.
- MSS displacement is measured on chart timeframe even when structural logic is HTF; contract is implicit.
- Broken breakout levels can remain eligible for retest indefinitely.
- Trigger and IN_PLAY points partially double-count the same event family.
- Missing “next wall” yields a positive space point; this encodes “unknown = favorable”.
- Alert/event timing is not consistently bound to confirmed trigger-context bars.

## Reference library

Strong donor domains:
- BSV lineage: RAW v2 + VI v2
- SignalGate lineage: AVP Gate Test 1 + v3.5
- market structure: LuxAlgo Fractal, Minimal HH/HL/LH/LL, SMC CptRedd, JuanDeNogoya MTF
- break/retest: LuxAlgo Breakout Detector + Swing Breakouts Tests/Retests
- liquidity: High Volume Boxes + Volume-based S/R Zones + Volume-supported Fractal S/R + Cluster Volume Profile
- realtime volume: MarketWhisperer `varip` model
- confirmed HTF: MA MTF Momentum and the confirmed HTF block in Scalping PullBack

Quarantine — do not transplant as-is:
- Multi-Timeframe Trend Following with 200 EMA Filter: `lookahead_on` + current HTF EMA => historical future leak.
- RSI Trendlines with Breakouts: HTF RSI uses `lookahead_on` without historical offset => future leak.
- MacD Custom Multiple Time Frame: no version directive + legacy `security()`; requires complete timing rewrite.

## Statistics

- scripts: 53
- total lines: 12663
- core lines: 3989
- reference lines: 8674
- Pine v6: 20
- Pine v5: 16
- Pine v4: 12
- Pine v3: 2
- unspecified version: 3
- indicators: 33
- studies: 16
- strategies: 4

## Reboot sequence

1. SignalGate Dashboard — deterministic timeframe engine
2. Moving Average Shift — unreachable default signals + warmup/confirmation
3. Liquidity Zones Tactical — scoring/state model + multi-zone design
4. RSI MTF Tactical OB/OS — confirmed/live MTF policy
5. MA 6x — confirmed MTF + score/probability semantics
6. Buying Selling Volume 2-in-1 — proxy semantics + optional realtime mode

## Gate status

- Extraction integrity: PASS
- Archive/provenance capture: PASS
- Static inventory: PASS
- Initial static audit: PASS with blockers
- Pine v6 reboot compile: NOT STARTED
- Repaint/reload parity: NOT STARTED
- Alert regression: NOT STARTED
- Trading efficacy validation: NOT STARTED

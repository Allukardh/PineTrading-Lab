# SignalGate SG-0 — deterministic timeframe hardening

**Date:** 2026-09-22  
**Target:** `src/core/signalgate-dashboard.pine`  
**Candidate:** `0.1.0`  
**Status:** static candidate; TradingView compile/runtime gates pending

## Objective

Create the first reboot candidate without changing the scoring model itself. SG-0 is deliberately limited to data-timing correctness, lower-timeframe safety, state-commit boundaries, and alert determinism.

The archived v4.9.1 source remains untouched under `archive/sources/core/42-signalgate-dashboard.pine`.

## Root problem

The archived implementation used one generic request helper:

```pine
request.security(..., expression, gaps_off, lookahead_off)
```

For higher-timeframe requests, that can expose unconfirmed values on realtime bars and therefore produce different values after reload.

The archived auto-trigger mapping also selected 1H for every intraday chart. On a chart above 1H, that made `request.security()` a lower-timeframe request, where it returns only one intrabar per chart bar rather than a full lower-timeframe sequence.

Official TradingView references:
- https://www.tradingview.com/pine-script-docs/concepts/repainting/
- https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/
- https://www.tradingview.com/pine-script-docs/concepts/timeframes/

## SG-0 decisions

### 1. Confirmed HTF policy

For requested timeframes above the chart timeframe, SG-0 uses the canonical non-repainting pattern:

```pine
request.security(symbol, tf, expression[1], lookahead = barmerge.lookahead_on)
```

For equal timeframe, the local chart series is used directly.

This intentionally delays HTF information until it is confirmed. That is a correctness tradeoff, not a performance optimization.

### 2. No implicit LTF sampling

SG-0 does **not** use `request.security()` for a timeframe below the chart.

Auto mappings now behave as follows:

- Trigger: use 1H while chart <= 1H; above 1H, use the chart timeframe.
- Structure: use 4H while chart <= 4H; above 4H, use the chart timeframe.

Manual Bias/Structure/Trigger selections below the chart timeframe raise `runtime.error()`.

A true intrabar/LTF engine based on `request.security_lower_tf()` is a separate future milestone because it requires deterministic intrabar state processing, not a one-line substitution.

### 3. Confirmed state transitions

- Same-timeframe structure/BOS commits only on a confirmed chart bar.
- Same-timeframe breakout/retest/fakeout/invalidation commits only on a confirmed chart bar.
- Confirmed HTF trigger data can commit when the newly confirmed requested bar becomes available.

### 4. Alert policy

All `alertcondition()` paths are hard-gated by `barstate.isconfirmed`.

Fakeout uses a dedicated edge event (`fakeoutEvt = fakeout and not fakeout[1]`) so the optional fakeout alert/log fires once on transition instead of repeating on every confirmed chart bar while the condition remains active.

Dynamic `alert()` telemetry also executes only on confirmed chart bars and continues using `alert.freq_once_per_bar_close`.

Telemetry records:

```text
DATAPOLICY=CONFIRMED_HTF
```

### 5. Explicit realtime UI state

The compact panel labels the current chart bar as `FECHADA` or `PREVIEW`.

The normal panel identifies the HTF policy as `HTF: CONF`.

## Intentionally deferred

SG-0 does not yet change:
- score weights
- GO/WATCH thresholds
- trigger + IN_PLAY double-counting
- missing-wall space scoring
- Mode C persistence
- MSS chart-TF vs structure-TF semantics
- stale breakout-level expiry
- market-efficacy assumptions

Those are independent behavioral changes and require separate milestones.

## Static checks completed

- version lineage reset to `0.1.0`
- old live HTF helper removed from active candidate
- confirmed HTF wrapper present
- lower-timeframe guards present
- all `alertcondition()` calls close-gated
- telemetry close-gated
- archived source left untouched
- repository integrity workflow: **PASS**
  - push run: `35753309572`
  - PR run: `35753335019`

The CI checker also verifies that all 53 split archive sources still match the raw TradingView export after newline normalization.

## Validation gates still required

### Gate 2 — TradingView compile — PASS

The repository now has two compile paths:

- `tools/tradingview-compile/compile_pine.py` — CI/server compiler gate.
- `tools/tradingview-compile/compile-current-editor.js` — optional browser-side verification of the currently open editor.

The CI client submits the candidate to TradingView's internal `translate_light` compiler without saving or publishing anything.

Latest-head evidence:
- Pine compile baseline push run: `35753811279` — **PASS**
- Pine compile baseline PR run: `35753814597` — **PASS**
- Pine compile latest code-head run after fakeout edge fix: `35754001242` — **PASS**
- Static integrity latest code-head run: `35754001287` — **PASS**
- result: `compiled=true`
- compiler errors: **0**
- compiler warnings: **0**

The internal endpoint remains undocumented/unstable, so a future endpoint failure must be distinguished from an actual Pine compile failure.

### Gate 3 — timing/reload parity
Test at minimum:
- BTCUSDT 15m: trigger=1H, structure=4H, bias=4H/D
- BTCUSDT 1H: trigger=same TF, structure=4H, bias=4H/D
- BTCUSDT 4H: trigger=same TF, structure=same TF, bias=4H/D

For each:
1. observe state before chart-bar close
2. record state at close
3. reload chart
4. confirm closed-bar state/events remain identical
5. verify K/R, GO/EARLY and IN_PLAY alerts do not fire from transient intrabar states

### Guard test
On a 1D chart with default Bias TF #1 = 4H, the script should raise an explicit timeframe error rather than silently sample 4H intrabars.

## Promotion rule

Do not merge this candidate to `main` as an accepted SignalGate baseline until compile and timing/reload gates pass.

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

Bias timeframes below the chart are **safe-clamped to the chart timeframe**. This keeps the dashboard usable when the operator switches to a higher chart timeframe without falling back to invalid LTF sampling. The full panel reports the effective Bias TFs and appends `Bias clamp: SIM` when a clamp occurs.

Manual Structure/Trigger selections below the chart timeframe still raise `runtime.error()`, because silently changing those event-producing contexts would alter trigger/structure semantics.

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

## Independent archive-vs-candidate review

A line-level LCS diff was reviewed between the immutable archived SignalGate source and the active 0.1.0 candidate.

Result:
- 12 logical change hunks
- every hunk maps to SG-0 scope: version reset, timeframe policy/guards, confirmed structure/trigger commits, fakeout edge, panel disclosure, alert close-gating, telemetry policy
- no unrelated scoring/threshold/visual-market-logic rewrite was found

The fakeout path was tightened during this review so its optional alert/log uses a one-shot `fakeoutEvt` transition rather than the persistent state.

## Interactive evidence received

### BTCUSDT 15m
- candidate loaded successfully
- compact panel rendered
- current chart bar correctly displayed as `PREVIEW`
- effective Trigger TF displayed as `60`

### BTCUSDT 4H
- candidate loaded successfully
- full panel rendered, making all gates visible
- effective TF line displayed `Trigger 240 | Bias 240/D | Structure 240 | HTF: CONF`
- G1–G5, scores, conflict and mini-summary rendered without runtime error

### BTCUSDT 4H — reload parity evidence
Two screenshots were captured around a browser reload, approximately 22 seconds apart on the same open 4H bar.

Observed invariant state across reload:
- Profile: Agressivo
- Mode: B (BREAKOUT)
- Operação: Compra
- state: GO
- quality: BOM
- G1 Tendência: Alta
- G2 Estrutura: Alta
- G3 execution: LONG(1)
- G4 momentum state unchanged
- Força C/V: 8 / 1
- Pronto C/V: 100% / 14%
- Conflito: Não
- Trigger/Bias/Structure TF line unchanged: `240 | 240/D | 240 | HTF: CONF`
- visible historical BOS/CHoCH/retest markers and structure/range levels remained visually aligned

Expected live differences were observed because the current 4H candle continued trading between screenshots:
- BTC price changed from about 86,350 to 86,369
- G5 space changed slightly (about `1.02 / 5.45` to `1.00 / 5.47`)

Those small live-value changes are consistent with the still-open chart bar and are not, by themselves, evidence of repainting.

Conclusion: **4H reload visual/state parity PASS for closed-history/rendered state**. Alert-delivery parity at an actual bar close remains pending.

These observations validate rendering/timeframe selection, but **do not** close reload-parity or alert gates.

### BTCUSDT 1D — safe-clamp PASS
The original SG-0 guard correctly rejected the default 4H Bias #1 on a 1D chart instead of silently sampling LTF data. That protection is considered proven.

After the UX refinement, the revised candidate was retested interactively:
- script loaded without runtime error
- full panel rendered
- Trigger TF displayed `1D`
- Bias TF displayed `1D/D` (both are daily contexts; the difference is TradingView string formatting)
- Structure TF displayed `1D`
- `HTF: CONF` displayed
- `Bias clamp: SIM` displayed

Therefore the Bias safe-clamp behavior is **PASS** for the 1D default case.

## Validation gates still required

### Gate 2 — TradingView compile — PASS

The repository now has two compile paths:

- `tools/tradingview-compile/compile_pine.py` — CI/server compiler gate.
- `tools/tradingview-compile/compile-current-editor.js` — optional browser-side verification of the currently open editor.

The CI client submits the candidate to TradingView's internal `translate_light` compiler without saving or publishing anything.

Latest-head evidence:
- Pine compile baseline push run: `35753811279` — **PASS**
- Pine compile baseline PR run: `35753814597` — **PASS**
- Pine compile code-head run after fakeout edge fix: `35754001242` — **PASS**
- Static integrity code-head run: `35754001287` — **PASS**
- Latest PR compile run with strengthened invariants: `35754129004` — **PASS**
- Latest push static-integrity run with fakeout invariant: `35754121451` — **PASS**
- Bias safe-clamp source PR compile run: `35758036440` — **PASS**
- Bias safe-clamp invariant PR compile run: `35758056696` — **PASS**, errors 0, warnings 0
- Bias safe-clamp invariant PR integrity run: `35758056816` — **PASS**
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

### Safe-clamp test — 1D default PASS
On a 1D chart with default Bias TF #1 = 4H:
- [x] loads without a bias-timeframe runtime error
- [x] effective Bias contexts are daily (`1D/D`)
- [x] full panel shows `Bias clamp: SIM`
- [x] no lower-timeframe `request.security()` path is used (static/CI)

Still pending:
- manual Structure TF below chart must raise explicit runtime error
- manual Trigger TF below chart must raise explicit runtime error

## Promotion rule

Do not merge this candidate to `main` as an accepted SignalGate baseline until compile and timing/reload gates pass.

# Defaults and Profiles Policy

**Status:** Approved  
**Date:** 2026-09-23

## Principle

A user-facing default is a product decision, not an arbitrary Pine input default.

The operator should be able to add Market Map, Execution, and Decision Panel and obtain a coherent configuration immediately.

“Optimized default” in this project means:
- logically safe
- timing-safe
- internally consistent
- validated on the project test matrix
- suitable as the recommended general-purpose starting point

It does **not** mean a universal statistically optimal parameter for every asset/timeframe unless empirical testing demonstrates that.

## Normal user controls

Target normal configuration surface:

1. **Profile — only if that product genuinely needs one**
   - do not create profiles by default
   - if profiles add real value, keep the set small and coherent

2. **Visual presentation**
   - one curated default view
   - optional Advanced/Diagnostics detail toggle only when useful

3. **Appearance**
   - colors
   - line widths/styles
   - zone transparency
   - panel location/text size

4. **Alerts**
   - master enable
   - optional alert families

5. **Rare explicit preference**
   - only when Auto cannot safely infer the behavior

## Internal/profile-controlled settings

Normally hidden:
- ATR multipliers
- pivot left/right
- wick thresholds
- score weights
- volume thresholds
- cooldowns
- confirmation bars
- MTF mappings
- correction tolerances
- confluence weights
- structure sensitivity
- proximity thresholds

These are engineering parameters and should travel together through profile presets.

## Profile contract

Profiles are **optional**, not mandatory.

Suite 0.2 Phase E is now closed with a deliberately small evidence-backed set.

### PADRÃO — accepted default

- remains the recommended global default;
- preserves accepted confirmed OPERATOR_READINESS semantics;
- applies on every supported horizon;
- remains the effective behavior whenever no earlier-action contract has evidence.

### ANTECIPADO — scoped TREND posture

ANTECIPADO is **not** a global lowering of confirmation thresholds.

Evidence-backed actionable scope:
- horizons: **15m / 1H / 4H / 1D / 3D**;
- opportunity classes:
  - **BREAKOUT_EXPANSION**;
  - **REACCELERATION**.

It surfaces the already-accepted TREND path earlier, at an evidence-backed readiness point.

The following remain PADRÃO even when ANTECIPADO is selected:
- pullback / retest / reclaim;
- RANGE_ROTATION;
- strict REGIME_REVERSAL;
- **1W** execution;
- **1M** macro/cycle context.

ANTECIPADO means **earlier TREND opportunity/action posture**, not higher leverage, higher account risk, weaker timing safety or permission to repaint.

### CONFIRMADO — not shipped

The tested +1 persistence contract is **REMOVE / DO NOT SHIP**.

Evidence showed:
- added delay;
- weak/no useful quality discrimination;
- some rejected PADRÃO theses subsequently completed.

Do not invent +2/+3 variants merely to manufacture a third profile.

### Horizon result

- 15m — ANTECIPADO TREND supported
- 1H — ANTECIPADO TREND supported
- 4H — ANTECIPADO TREND supported
- 1D — ANTECIPADO TREND supported
- 3D — ANTECIPADO TREND supported
- 1W — PADRÃO only; early profile evidence too sparse
- 1M — macro/cycle awareness; not an execution-profile horizon

### Product rule

If a user selects ANTECIPADO on an unsupported opportunity class or horizon, the engine keeps PADRÃO semantics for that path.

The UI/guide must make this scoped behavior explicit enough that the operator does not interpret ANTECIPADO as a universal "faster everything" mode.

Profiles control coherent behavior. They must never expose a bag of ATR/pivot/RSI magic numbers.


## Auto-first policy

Where safe:
- derive effective timeframe from chart timeframe
- derive higher-timeframe context automatically
- derive correction/zone sensitivity from volatility/ATR
- derive display density from relevance

Manual overrides are exceptions.

## Validation requirement

Any change to a default/profile must document:
- what user-visible behavior changes;
- why the new default is preferred;
- compile/timing impact;
- visual regression evidence;
- market-behavior evidence when applicable;
- measured latency vs the frozen PADRÃO comparator;
- cancellation/churn cost;
- remaining structural room when the signal appears.

Suite 0.2 must first measure 0.1 latency. If ANTECIPADO / PADRÃO / CONFIRMADO do not create meaningful coherent tradeoffs, ship **no profile selector**.

Do not tune defaults only to make a single historical screenshot look better.


## Panel policy

The suite has **one semantic panel contract per product**.

Do not implement:
- Compact vs Full panel modes
- a “simple” panel that withholds decision-critical context
- a “complete” panel that exposes engineering diagnostics and internal scores

Normal controls may include **Show/Hide panel** and presentation preferences such as location/text size. Diagnostic data belongs in Advanced/Diagnostics or the Pine Data Window, not in a second panel mode.

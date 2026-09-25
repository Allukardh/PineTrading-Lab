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

A product should expose a profile selector only when materially different operating styles cannot be handled well by one robust automatic/default engine.

Suite 0.2 introduces an evidence-gated candidate contract:

### ANTECIPADO
- earlier opportunity recognition;
- lower confirmation burden where evidence supports it;
- especially relevant to regime reversals, breakouts and reacceleration;
- no lookahead or historical repaint;
- persistent actionable states remain timing-safe.

### PADRÃO
- the accepted 0.1 behavior is the anchor/reference;
- do not mutate this comparator while researching alternatives;
- remains the recommended default unless evidence proves another single default is better.

### CONFIRMADO
- later/more selective;
- stronger structural/HTF/participation burden;
- useful only if it materially improves false-start behavior without consuming too much of the move.

These names describe **timing/confirmation posture**, not risk appetite or leverage.

A profile must change coherent behavior bundles. It must not be a random collection of unrelated numbers.

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

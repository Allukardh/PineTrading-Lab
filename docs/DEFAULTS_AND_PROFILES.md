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

1. **Profile**
   - Sniper
   - Balanced — default
   - Aggressive

2. **Visual mode**
   - Clean
   - Standard — default
   - Detailed

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

### Sniper
- strongest confirmation requirement
- fewer signals
- later entries
- tighter noise rejection

### Balanced
- default
- general discretionary trading use
- compromise between timing and confirmation

### Aggressive
- earlier signals
- more opportunities
- accepts weaker confirmation
- still must obey structural invalidation and timing safety

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
- what user-visible behavior changes
- why the new default is preferred
- compile/timing impact
- visual regression evidence
- market-behavior evidence when applicable

Do not tune defaults only to make a single historical screenshot look better.

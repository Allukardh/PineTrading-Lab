# Moving Average Shift MAS-0 — signal reachability and deterministic markers

**Date:** 2026-09-22  
**Target:** `src/core/moving-average-shift.pine`  
**Candidate:** `0.1.0`  
**Status:** static candidate; compile/runtime validation pending

## Objective

Create the first reboot baseline without adding new trading features. MAS-0 addresses the initial audit blockers:

1. default signal path was logically unreachable in two of the three signal modes
2. percentile warmup substituted unavailable normalization data with `syminfo.mintick`, creating extreme oscillator values
3. entry markers could appear/disappear intrabar
4. “probability” labels described deterministic directional conditions, not calibrated probabilities

The archived v1.1 source remains untouched under `archive/sources/core/31-moving-average-shift.pine`.

## Root-cause analysis

### Default signal deadlock

Defaults:
- `signalMode = Original`
- `useDirectionalFilter = true`
- `useSetupFilter = true`

Legacy Original long:
- `osc < -threshold`

Legacy Setup long:
- `osc > 0`

Those cannot both be true. The short side had the mirrored contradiction.

The same contradiction existed in `Linha de sinal`, where long requires `osc < 0` and short requires `osc > 0`.

Only Zero Cross was naturally compatible with the legacy sign-based Setup filter.

### Warmup distortion

Legacy code:

```pine
absPercSafe = math.max(nz(absPercRaw, 0.0), syminfo.mintick)
```

Before the percentile window becomes valid, `absPercRaw` is unavailable. Replacing it with zero and then mintick divides the MA distance by an extremely small value, which can create meaningless normalized spikes.

## MAS-0 decisions

### 1. Orthogonal filters

Directional filter remains responsible for trend direction.

Setup filter now requires oscillator **acceleration in the intended signal direction**:
- long: `osc > osc[1]`
- short: `osc < osc[1]`

It no longer requires oscillator sign, so Original and Signal Line reversal-style entries remain reachable.

### 2. Honest percentile warmup

Until the requested percentile is available and positive:
- normalized distance is `na`
- oscillator is `na`
- signal paths remain unavailable

No synthetic mintick fallback is used.

### 3. Close-confirmed entry markers

Final C/V entry markers are gated by `barstate.isconfirmed`.

The oscillator and trend visualization remain live; only the actionable marker is close-confirmed.

### 4. Semantic cleanup

Legacy `probBull/probBear` variables were boolean directional strength conditions, not probabilities.

MAS-0 renames them to `strengthBull/strengthBear` and changes display titles from “Força provável” to “Força”.

### 5. Input invariant

Oscillator threshold now has `minval=0.0` because it is used as a symmetric magnitude around zero.

## Intentionally unchanged

- MA algorithms
- default MA type/length
- oscillator formula
- percentile lookback and percentile default
- Original / Zero Cross / Signal Line raw trigger definitions
- bar/candle painting
- visual colors
- no new alert system is added in MAS-0

## Static checks

- version reset to 0.1.0
- legacy contradictory Setup filter removed from entry path
- percentile mintick warmup substitution removed
- signal readiness tied to a valid oscillator
- entry markers close-confirmed
- probability terminology removed from active code
- source archive untouched

## Validation plan

### Gate 2 — Pine compile
- Pine v6 server compile
- 0 errors
- 0 unexplained warnings

### Gate 3 — signal reachability
On BTCUSDT, verify each mode can produce historical markers with defaults:
- Original
- Zero Cross
- Linha de sinal

Particular focus: Original and Linha de sinal must no longer be suppressed by the Setup filter.

### Gate 4 — warmup / visual sanity
- no giant oscillator spikes caused by unavailable percentile data
- oscillator begins only after normalization is valid
- MA/candle visuals remain sane

### Gate 5 — realtime marker confirmation
On an open bar, entry marker must not be committed until bar close.

## Promotion rule

Do not merge MAS-0 until compile and interactive signal/warmup checks pass.

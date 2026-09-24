# Execution historical evidence — locked analysis conventions

**Date:** 2026-09-24  
**Status:** locked before first BTC evidence result  
**Research plan:** `docs/testing/EXECUTION_EVIDENCE_RESEARCH_PLAN.md`  
**First evidence workflow:** `Execution offline evidence`  
**First evidence code head:** `74474ab3f8693c7b22e3677b178cbdc4245e5491`

This worklog records operational definitions that the pre-registered plan intentionally left descriptive.

They are fixed **before inspecting the first historical result** so the project does not choose convenient measurement semantics after seeing the data.

None of these conventions changes an Execution production candidate threshold.

## Dataset identity

The evidence runner rematerializes official Binance Public Data SPOT monthly klines through the accepted pipeline and requires each resulting Parquet SHA-256 to equal the corresponding promoted production-manifest SHA.

A mismatch aborts the evidence run before statistics are accepted.

## Confirmed HTF RSI alignment

Automatic context mapping remains the suite contract:

```text
15m -> 1h
1h  -> 4h
4h  -> 1d
1d  -> 1w
3d  -> self
1w  -> self
```

For a lower-timeframe bar, confirmed HTF context uses the **previous completed HTF bar**, matching the intended `[1] + lookahead_on` contract.

For 3d/1w self-context, the offline input consists only of completed bars, so the current completed local RSI is the self-context direction.

## MTE-A episode conventions

A TURN episode starts when the state enters `TURN_UP` or `TURN_DOWN` from another state.

A TURN episode is reviewed forward until the first of:
1. core crosses zero in the TURN direction;
2. acceleration resumes the original signed direction before zero-cross;
3. an opposite TURN begins before zero-cross;
4. dataset end.

Dwell is measured on contiguous ready bars.

Chatter:
- state changes per 100 ready-bar transitions;
- opposite TURN entries separated by <=1/2/3 chart bars;
- consecutive core zero-crosses separated by <=1/2/3 chart bars.

## RSE-A lifecycle conventions

A raw oversold/overbought **touch** is an entry into the raw zone from outside it, not every bar spent inside the zone.

A raw touch is considered to produce the corresponding recovery/fade state when that state occurs on the touch bar or within the following **2 confirmed bars**, matching the locked zone-memory length.

For a contiguous `RECOVERING_OVERSOLD` episode:
- continuation through center means the first bar after the episode is at/above RSI 52;
- otherwise the semantic recovery expired before completing the dead-band traversal.

For `FADING_OVERBOUGHT`, the mirror boundary is RSI 48.

This is a semantic lifecycle test, not price-outcome validation.

## PSE-A sign convention

General proxy-vs-taker sign-agreement statistics exclude values inside an analysis-only near-zero band:

```text
abs(value) < 0.05 -> near-zero / excluded from sign agreement
```

The same epsilon is applied symmetrically to proxy and taker imbalance.

This **0.05 is not an Execution engine threshold** and cannot be promoted into production merely because it appears in the research report.

The plan's explicit `abs(proxy) >= 0.20` view remains a separate reported slice.

Quadrant counts use the raw mathematical sign and exclude only exact zero.

## PSE-A direction during component research

Until full Market Map location-conditioned Execution research is run, PSE-A component occupancy is calculated twice on the same bar:
- hypothetical LONG;
- hypothetical SHORT.

This is explicitly allowed by the pre-registered plan and must never be described as an actual Execution signal.

## Cross-engine co-occurrence

Directional component alignment means:

LONG:
- MTE = `TURN_UP` or `UP_ACCEL`;
- RSE local state is LONG-supportive and confirmed HTF context does not oppose;
- PSE hypothetical LONG = `CONFIRM`.

SHORT mirrors those semantics.

Co-occurrence is descriptive only. No composite score is created.

## Year slicing

Candidate indicators are warmed on the **full continuous dataset first**.

Calendar-year reports then group already-computed samples by year.

Indicators are not reset at January 1, avoiding artificial annual warmup artifacts.

## Decision discipline

The analyzer emits `REVIEW_REQUIRED`; it does not automatically assign KEEP / REFINE / REMOVE / INSUFFICIENT EVIDENCE.

Those decisions are made only after comparing the historical output with the pathology questions written in the pre-registered plan.

No PnL or trade-win metric is calculated.

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


## Historical component evidence — BTC / ETH / AVAX

**Evidence matrix run:** `36077909903` — PASS  
**Static integrity:** `36077909923` — PASS  
**Branch head:** `fb833b25e90b2b2ca71e5c1c6680cbb79854e3d1`

Artifacts:
- BTC: `execution-btc-evidence` — artifact `10840702778`
- ETH: `execution-eth-evidence` — artifact `10841370010`
- AVAX: `execution-avax-evidence` — artifact `10841375463`

All three symbols use exact SHA-256-verified production Parquets and **unchanged** research defaults.

### MTE-A — KEEP

Across BTC / ETH / AVAX and 15m / 1h / 4h / 1d / 3d / 1w:

- TURN occupancy stays roughly **29–31%**;
- state changes stay roughly **32–38 per 100 ready bars**;
- TURN median dwell is normally **2 bars**, only drifting to ~2.5–3 on some higher-timeframe small samples;
- direct `UP_ACCEL <-> DOWN_ACCEL` flips remain negligible, at most about **0.3% of state changes**;
- opposite TURN reversals within 3 bars remain below about **0.2% of TURN episodes**;
- roughly **31–40%** of TURN episodes reach the signed zero-cross before original-direction acceleration resumes;
- roughly **60–68%** resume the original direction first.

Interpretation:
- MTE-A behaves as the intended early counter-acceleration / momentum-turn engine;
- TURN is not a reversal-probability claim;
- no numeric retuning is justified.

Decision: **KEEP MTE-A unchanged.**

### RSE-A — KEEP

Across the same matrix:

- extreme RSI states are rare but reachable (~**0.9–5.4%** depending on asset/timeframe);
- raw oversold/overbought touches consistently produce the intended recovery/fade semantics;
- on the primary lower timeframes, touch-to-recovery/fade conversion is broadly in the **mid-70% to low-80%** range;
- confirmed HTF opposition is material without making the engine nearly always blocked;
- the short 2-bar recovery/fade lifecycle behaves as designed.

The historical lifecycle report shows that most recovery/fade episodes do not themselves persist all the way through the center dead-band. This is **not treated as a defect** because RSE-A explicitly defines those states as brief recent-zone semantics, not as a promise that recovery survives until center.

Cross-engine evidence also does not show that RSE-A is merely MTE-A duplicated under different labels.

Decision: **KEEP RSE-A unchanged.**

Watch item:
- once actual Market Map direction/location drives the full state machine, verify that the deliberately short recovery/fade semantics do not create ARMADO churn.

### PSE-A — KEEP

Relative-volume bands remain meaningful without per-asset tuning:

- `<0.80x`: roughly **35–52%**;
- `>=1.20x`: roughly **23–29%**;
- `>=1.50x`: roughly **12–17%**.

The close-location pressure proxy shows a real but limited relationship to Binance taker imbalance:

- Pearson roughly **0.26–0.35**;
- Spearman roughly **0.27–0.41**;
- sign agreement on the large primary samples is generally around **66–75%**;
- sign agreement tends to improve when relative volume is expanded.

Interpretation:
- the proxy contains useful reload-safe directional evidence;
- it is not equivalent to real aggressor flow;
- Binance taker imbalance remains validation-only.

Decision: **KEEP PSE-A unchanged.**

Semantic lock:
- never label the proxy buy volume / sell volume / delta / aggressor flow.

### Cross-engine independence

With hypothetical LONG/SHORT component direction:

- all three evidence families align on only about **2.3–5.5%** of eligible bars across the full matrix;
- pairwise overlap is related, as expected, but no component subsumes the other two;
- no opaque score is justified.

### Strength mapping — INSUFFICIENT EVIDENCE

The unconditioned hypothetical-direction pass shows two-or-more deterioration families on roughly **24–44%** of bars depending on asset/timeframe/direction.

That is useful diagnostic evidence, but final:

```text
0 families  -> NORMAL
1 family    -> PERDENDO FORÇA
2+ families -> EXAUSTÃO
```

remains **INSUFFICIENT EVIDENCE** until it is conditioned on an actual coherent Market Map thesis/location.

Production readiness frequency is likewise not approved from hypothetical-direction component research alone.

### Component gate decision

```text
MTE-A  KEEP
RSE-A  KEEP
PSE-A  KEEP
```

No candidate defaults changed.

Production `execution.pine` remains blocked.

### Exact next evidence gate

Use the accepted/offline-equivalent Market Map to drive:

- actual `mapDir`;
- APPROACHING;
- IN_CORRECTION;
- RETEST;
- RECLAIM;
- DESTINATION_NEAR;
- invalidation/conflict.

Then simulate the canonical Execution state machine and determine whether:
- PREPARANDO is always-on / never-on;
- ARMADO occurs at useful frequency and precedes CONFIRMA;
- confirmations are not pathologically one-sided;
- one evidence family dominates every confirmation;
- Strength remains useful under real thesis/location;
- RISCO DE REAÇÃO clusters at meaningful Market Map locations;
- short RSE recovery/fade semantics cause integrated setup churn.

Only after that integrated gate may production `execution.pine` be created.

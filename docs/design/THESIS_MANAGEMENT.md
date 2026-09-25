# Thesis Management / Exit-Risk — Suite 0.2 Research Contract

**Status:** preregistered research contract  
**Tracking:** Issue #23 / draft PR #25  
**Scope:** management of a confirmed market thesis, never account-position inference

## 1. Product question

After an operator-facing CONFIRMA has occurred:

> Is the thesis still healthy, should the operator protect/not chase, is realization risk rising near the structural objective, or has the thesis structurally completed/invalidated?

This layer describes **market-thesis quality**.

It never assumes:
- that the operator entered;
- entry price;
- position size;
- leverage;
- exchange;
- stop placement;
- tax/account constraints.

## 2. Separation from entry readiness

Entry readiness remains:

`AGUARDAR -> PREPARANDO -> ARMADO -> CONFIRMA -> ALINHADO`

Management is a separate lifecycle output after a confirmed thesis:

`CONTINUATION / PROTECT / REALIZATION_RISK / COMPLETED / INVALIDATED / AMBIGUOUS`

A management state must not create a new entry signal by itself.

## 3. Thesis birth

A research management episode starts only on a unified
`OPERATOR_READINESS_V1` CONFIRMA bar.

The confirmation may originate from:
- frozen Execution 0.1;
- accepted trend Opportunity v2;
- RANGE_ROTATION EARLY_ANY1.

The episode freezes its structural anchors at confirmation time.

### Frozen 0.1 / trend Opportunity
- direction = confirmed operator direction;
- target = current Market Map destination;
- invalidation = current Market Map invalidation.

### RANGE_ROTATION
- target = opposite range edge objective;
- invalidation = source range edge;
- range geometry is taken from the source EDGE_REJECTION episode.

No target/invalidation is moved after the fact to improve retrospective results.

## 4. Existing accepted evidence reused

No new indicator family is introduced.

### MTE
Use existing momentum deterioration semantics.

### RSE
Use existing RSI deterioration semantics.

### PSE
Use existing participation semantics.

### Strength
Reuse accepted `classify_strength()`.

Generic deterioration families:
- MTE deterioration;
- RSE deterioration;
- PSE CONTRARY.

Near destination, PSE WEAK also counts in the accepted
`REACTION_RISK` semantic.

## 5. Existing structural distances reused

No new distance threshold is introduced.

- destination near = **<= 0.30 ATR**
- invalidation warning = **<= 0.20 ATR**

These are the accepted Market Map engineering defaults.

## 6. Preregistered management baseline V0

Precedence is evaluated in this order.

### AMBIGUOUS
On a bar where:
- the frozen target is reached intrabar; and
- the frozen invalidation is also confirmed broken on that same bar;

OHLC cannot establish whether target completion preceded thesis failure.

Do not force COMPLETED or INVALIDATED.

### COMPLETED
Frozen structural target reached, with no same-bar outcome ambiguity.

This means the objective was reached.
It is **not** an instruction that the operator must close a position.

### INVALIDATED
Frozen structural invalidation is confirmed broken, with no same-bar target ambiguity.

For directional thesis:
- LONG invalidation = confirmed close below frozen invalidation;
- SHORT invalidation = confirmed close above frozen invalidation.

### REALIZATION_RISK
Thesis is still valid and target is not yet completed, but:
- frozen target is within 0.30 ATR; and
- accepted Strength = REACTION_RISK.

This intentionally reuses the existing destination-near multi-family
deterioration contract.

Operator interpretation:
- if positioned: realization/protection deserves attention;
- if flat: avoid chasing simply because price is near objective;
- this is not a reversal/short signal.

### PROTECT
Thesis remains structurally valid and target not completed, but at least one
of these stronger risk conditions is present:

1. accepted Strength = EXHAUSTED; or
2. frozen invalidation is within 0.20 ATR; or
3. for Market-Map-driven theses only, the current map becomes structurally
   conflicting / loses the thesis direction.

Strength = FADING alone remains diagnostic in V0.
It does **not** promote PROTECT yet, specifically to test whether one-family
deterioration would otherwise saturate the operator output.

For RANGE_ROTATION, generic Market Map direction/conflict is not a hard
management warning because the accepted range opportunity may legitimately
oppose the larger map regime.

### CONTINUATION
None of the conditions above apply.

This does not mean guaranteed continuation.
It means no stronger management warning is currently evidenced by V0.

## 7. Research diagnostics kept beside V0

Even where they do not change the V0 state, report:
- first FADING bar;
- first EXHAUSTED bar;
- first destination-near bar;
- first invalidation-near bar;
- first Market Map structural warning where relevant;
- first REALIZATION_RISK;
- first PROTECT;
- target completion;
- invalidation;
- ambiguous outcome.

## 8. Timing / quality questions

On BTC 4H/1D measure:

- supported management episodes vs operator confirms;
- source-path contribution;
- target / invalidation / ambiguous / censored outcomes;
- bars from CONFIRMA to outcome;
- first PROTECT lead time before invalidation;
- first REALIZATION_RISK lead time before target;
- remaining ATR room at warning;
- warning saturation (% of live thesis bars);
- state transitions / flip-flop;
- warnings that disappear and reappear;
- whether FADING would materially improve timing or merely add churn;
- behavior by source path.

Do not convert these metrics into win probability.

## 9. Initial acceptance criteria

V0 is not accepted merely because it produces warnings.

A useful management state should:
- be reachable;
- not saturate most live-thesis bars;
- occur before the structural event often enough to be actionable;
- avoid rapid repeated CONTINUATION <-> warning flip-flop;
- preserve explicit terminal outcomes;
- remain source/venue/position agnostic.

If V0 is too sparse/late:
- diagnose the missing evidence family before relaxing thresholds.

If V0 saturates/churns:
- do not hide it behind smoothing without first identifying the cause.

## 10. Production status

Research only.

No production Pine/default/profile/panel change is authorized by this contract.

# Opportunity Engine — Suite 0.2 Research Contract

**Status:** candidate research contract  
**Tracking:** Issue #23

## 1. Purpose

The Opportunity Engine answers:

> **What kind of tradable market opportunity, if any, exists now?**

It sits between Market Map structural context and Execution timing.

It does not replace either engine.

```text
Market Map
    ↓
Opportunity Engine
    ↓
Execution
    ↓
Direct operator panel
```

## 2. Non-goals

The engine must not:
- predict guaranteed tops/bottoms;
- call every oscillation a trade;
- infer the operator's actual exchange position;
- confuse bearish analysis with mandatory shorting;
- optimize one asset/timeframe at the expense of general semantics;
- expose an opaque opportunity score as a fake probability.

## 3. Direction vs venue action

Canonical internal direction:

```text
+1 = bullish opportunity direction
 0 = no directional thesis
-1 = bearish opportunity direction
```

Operator translation:

| Direction | Spot interpretation | Bidirectional/Quantfury interpretation |
|---|---|---|
| +1 | buy / hold / add context | long context |
| -1 | protect / reduce / sell / avoid new buy | short context may also exist |
| 0 | wait / no directional action | wait |

The engine never needs exchange-specific price logic merely to support short.

## 4. Opportunity classes

Candidate enum:

```text
NONE
REGIME_REVERSAL
BREAKOUT_EXPANSION
PULLBACK_RETEST
REACCELERATION
RANGE_ROTATION
```

Exit/management evidence is a separate lifecycle output, not a new entry class.

## 5. REGIME_REVERSAL

A regime-reversal opportunity should require evidence that the prior regime is not merely experiencing a normal correction.

Candidate ingredients:
- mature opposite regime or prolonged neutral/base;
- structural transition;
- meaningful break/CHoCH;
- first aligned structural progression;
- HTF deterioration of the old regime and/or confirmation of the new one;
- momentum turn/acceleration;
- participation not materially contrary.

Research question:

> How early can the new regime be recognized without creating persistent false transitions?

## 6. BREAKOUT_EXPANSION

Candidate ingredients:
- range/structure boundary;
- confirmed close beyond boundary;
- destination room;
- participation expansion;
- directional pressure;
- HTF compatibility;
- fakeout/reclaim filter.

Research question:

> Can a breakout be surfaced before waiting for a full pullback without substantially increasing false expansion episodes?

## 7. PULLBACK_RETEST

Reference:
- preserve accepted Market Map 0.1 correction/retest/reclaim semantics.

Research question:

> Does the generalized Opportunity Engine preserve the useful behavior of 0.1 rather than degrading its strongest setup family?

## 8. REACCELERATION

Candidate ingredients:
- established coherent regime;
- no structural invalidation;
- momentum previously decelerated/compressed;
- aligned momentum re-expands;
- RSI returns supportive;
- participation recovers or confirms;
- meaningful room remains to destination.

Research question:

> Can continuation be recognized even when price never enters the primary correction envelope?

## 9. RANGE_ROTATION

Candidate ingredients:
- regime/trend is not strongly directional;
- stable range boundaries;
- price near a meaningful edge;
- rejection/sweep/reclaim;
- momentum turns away from the edge;
- opposite side offers adequate structural room.

Research question:

> Is the range state stable enough to justify rotation opportunities without creating blind mean-reversion signals?

## 10. Management / exit-risk state

Candidate management output:

```text
CONTINUATION
PROTECT
REALIZATION_RISK
INVALIDATED
```

This state describes **thesis quality**, not account position.

Examples:
- trader has spot long: `PROTECT` may support tightening discretion / considering reduction;
- trader has no position: the same state may mean "do not chase";
- trader uses Quantfury: a bearish opportunity may later become short context, but `REALIZATION_RISK` alone is not a short signal.

## 11. Opportunity/action separation

Possible combination:

```text
OPPORTUNITY = REGIME_REVERSAL
DIRECTION   = +1
ACTION       = PREPARING
```

Later:

```text
OPPORTUNITY = REGIME_REVERSAL
DIRECTION   = +1
ACTION       = CONFIRMED
```

And later still:

```text
MANAGEMENT = PROTECT
```

This avoids overloading one label with setup type, timing and lifecycle.

## 12. Candidate direct UI

Preferred operator concepts:

```text
CENÁRIO
OPORTUNIDADE
LADO
AÇÃO
ALVO
GESTÃO
INVALIDA
```

`CORREÇÃO` is conditional and appears only when relevant.

Internal technical semantics remain in Data Window/diagnostics.

## 13. Timing safety

0.2 may become earlier, but not by cheating.

Persistent actionable states must remain:
- deterministic;
- reload-safe;
- free of future lookahead;
- explicit about provisional vs confirmed evidence.

If an intrabar/developing annotation is later researched, it must be visibly distinguished from a confirmed historical state and must not rewrite history after reload.

## 14. Research outcome vocabulary

For each class:

```text
KEEP
REFINE
REMOVE
INSUFFICIENT EVIDENCE
```

No class becomes production simply because examples look attractive.

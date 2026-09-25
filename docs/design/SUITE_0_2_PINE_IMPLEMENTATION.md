# Suite 0.2 — Pine Implementation Contract

**Status:** Phase G implementation contract  
**Tracking:** Issue #26  
**Research baseline:** PR #25 merge `74d58a4376f004ec0548e2f9a3640f0d82119c35`

This document translates the accepted Suite 0.2 research contract into production-candidate Pine responsibilities.

It is not a new research surface.

If Pine behavior disagrees with the accepted Python/offline references, treat the discrepancy as an implementation/parity defect first.

## 1. Runtime topology

Suite 0.2 remains **two scripts**.

### Market Map
Overlay:
- regime / structure;
- liquidity;
- correction / retest / reclaim;
- destination / invalidation;
- opportunity classification;
- embedded operator-facing panel;
- embedded unified readiness / management rows for parity with Execution.

### Execution
Lower pane:
- MTE / RSE / PSE;
- frozen 0.1 readiness path;
- TREND_OPPORTUNITY_V2 readiness path;
- RANGE_EARLY_ANY1 readiness path;
- OPERATOR_READINESS_V1;
- profile posture;
- Thesis Management V1.1;
- compact standalone status cue.

There is no third runtime Decision Panel.

## 2. Independent internal paths

The following paths remain independent until operator projection.

### 2.1 FROZEN_0_1

Use the accepted 0.1 correction/retest/reclaim state machine unchanged.

Canonical conceptual source:
- `src/core/execution.pine` 0.1 lineage;
- `tools/execution_state_reference.py`.

Relevant locations:
- APPROACHING
- IN_CORRECTION
- RETEST
- RECLAIM

Do not reinterpret BREAKOUT / RANGE as fake correction locations.

### 2.2 TREND_OPPORTUNITY_V2

Opportunity kinds:
- BREAKOUT_EXPANSION
- REACCELERATION
- REGIME_REVERSAL

Canonical sources:
- `tools/opportunity_episode_reference.py`
- `tools/opportunity_execution_counterfactual.py`
- `tools/opportunity_readiness_reference.py`

### 2.3 RANGE_EARLY_ANY1

Canonical sources:
- `tools/range_rotation_reference.py`
- `tools/range_rotation_opportunity_reference.py`
- `tools/range_rotation_readiness_reference.py`

Only accepted primary trigger:
- EDGE_REJECTION

Raw SWEEP_RECLAIM remains auxiliary telemetry and never creates a standalone range entry path.

## 3. Trend opportunity classification

### 3.1 Structural break context

Maintain confirmed-bar bookkeeping:
- current regime direction + age;
- previous regime direction + age;
- last same-direction structural break;
- last accepted reaction bar by direction.

A reaction is:
- retest event; or
- reclaim event; or
- accepted correction-zone touch.

Classify each structural break from contemporaneous/past state only.

Priority:

1. EARLY_TRANSITION
   - break is opposite a mature prior regime;
   - mature prior regime minimum = **8 bars**.
   - awareness/reversal bookkeeping only; raw transition is not directly actionable.

2. PULLBACK_RESOLUTION
   - reaction occurred after previous same-direction structural break and before this break; or
   - reaction occurs on the break bar.

3. REACCELERATION
   - current regime already matches break direction;
   - regime age before break >= **8 bars**;
   - at least one prior same-direction structural break exists;
   - no qualifying reaction since that prior break.

4. FRESH_EXPANSION
   - coherent break not belonging to the above categories.

5. OTHER
   - fallback structural context.

### 3.2 BREAKOUT_EXPANSION source

Eligible BREAKOUT candidate:
- confirmed structural break;
- Market Map already coherent in break direction;
- no structural conflict;
- thesis not invalidated;
- break context is FRESH_EXPANSION or OTHER.

Source quality:
- break penetration >= **0.50 ATR**; and
- PSE == CONFIRM in opportunity direction.

This creates `source_strong = true`.

### 3.3 REACCELERATION source

Eligible when structural-break context == REACCELERATION.

It uses the same CANDIDATE / STRONG / ACCEPTED follow-through lifecycle as BREAKOUT_EXPANSION.

### 3.4 strict REGIME_REVERSAL

Raw EARLY_TRANSITION is not actionable.

REGIME_REVERSAL becomes an opportunity only after:
- the opposite confirmed regime is established;
- Market Map is coherent in that new direction;
- no structural conflict;
- thesis not invalidated.

The frame starts directly at ACCEPTED.

## 4. Trend OpportunityFrame lifecycle

Enums:

```text
OPP_NONE
OPP_BREAKOUT_EXPANSION
OPP_REACCELERATION
OPP_REGIME_REVERSAL
OPP_RANGE_ROTATION

STAGE_NONE
STAGE_CANDIDATE
STAGE_STRONG
STAGE_ACCEPTED
```

BREAKOUT_EXPANSION / REACCELERATION:

Source close:
- stage = CANDIDATE;
- freeze source bar;
- freeze structural break level;
- freeze `source_strong`.

+1 confirmed close:
- must hold beyond break level in opportunity direction;
- if not: clear;
- if held:
  - STRONG when `source_strong`;
  - otherwise remain CANDIDATE.

+2 confirmed close:
- +1 and +2 both hold break level;
- no fakeout / thesis invalidation during the two-bar hold;
- then ACCEPTED;
- otherwise clear.

After ACCEPTED, persist only while:
- Market Map direction still equals opportunity direction;
- thesis not invalidated;
- no structural conflict;
- no fakeout;
- destination not near;
- frozen 0.1 is not already in correction/retest/reclaim relevant location.

A new accepted trend opportunity supersedes the previous trend opportunity.

REGIME_REVERSAL starts ACCEPTED and follows the same coherence termination rules.

## 5. TREND_OPPORTUNITY_V2 readiness

MTE / RSE / PSE state definitions are unchanged.

PSE must be evaluated in the opportunity direction while the trend opportunity frame is active.

### CANDIDATE

Awareness only.

It must not create PREPARANDO / ARMADO / CONFIRMA.

If an old same-direction trend path is PREP or ARMED and a new CANDIDATE replaces its frame, reset/cancel that unconfirmed readiness.

### STRONG

From WAIT:
- MTE must not strongly oppose;
- PSE must not be CONTRARY;
- enter PREP.

From PREP:
- cancel on strong MTE opposition or PSE CONTRARY;
- ARM when:
  - MTE aligned; and
  - RSE supportive including confirmed HTF context.

STRONG can never CONFIRM.

### ACCEPTED

From WAIT:
- if RSE supportive and MTE not strongly opposing -> ARM directly;
- otherwise PREP.

From PREP:
- cancel on strong MTE opposition or PSE CONTRARY;
- ARM when RSE supportive and MTE not strongly opposing.

From ARMED:
- cancel on:
  - strong MTE opposition; or
  - RSE opposition including HTF; or
  - PSE CONTRARY.
- CONFIRM when:
  - chart bar confirmed;
  - frame ACCEPTED;
  - MTE not strongly opposing;
  - RSE supportive;
  - PSE CONFIRM **or** frozen `source_strong` participation memory.

CONFIRMED:
- next bar -> ALIGNED.

ALIGNED:
- remain aligned;
- cancel only when MTE strongly opposes **and** RSE opposes.

## 6. RANGE_ROTATION structural box

Canonical constants:
- minimum range height = **2.0 ATR**
- maximum boundary drift = **20% of range height**
- edge band = **20% of range height**

Require:
- two confirmed swing highs;
- two confirmed swing lows;
- prior swing high bar < last swing high bar;
- prior swing low bar < last swing low bar;
- the first high+low cycle must complete before the second cycle;
- both highs structurally above both lows.

Box:
- high = average(prev swing high, last swing high)
- low = average(prev swing low, last swing low)
- mid = midpoint(high, low)
- edge band = 20% of height.

Fresh compatible pivots may update the same range when:
- high boundary movement <= max(old edge, new edge);
- low boundary movement <= max(old edge, new edge);
- boxes still overlap structurally.

Same-edge source is re-enabled only after price traverses the midpoint back toward the opposite half.

## 7. RANGE_ROTATION source / frame

Primary source = EDGE_REJECTION only.

Long edge rejection:
- low <= range low + edge band;
- close >= range low + edge band;
- candle close-location pressure in long direction > 0;
- confirmed close is still inside the range;
- lower edge is ready.

Short mirror:
- high >= range high - edge band;
- close <= range high - edge band;
- directional close-location pressure in short direction > 0;
- close remains inside range;
- upper edge ready.

On source close:
- kind = RANGE_ROTATION;
- stage = STRONG;
- freeze source bar;
- freeze range high / low / mid / edge;
- freeze direction.

+1 confirmed bar:
- same compatible range;
- no close invalidation outside source range;
- opposite edge not already reached;
- close remains inside range;
- close progresses in source direction vs source close.

If all true -> ACCEPTED.
Otherwise clear.

After ACCEPTED:
- persist while same compatible range remains;
- clear on:
  - incompatible/new range;
  - confirmed close outside source range;
  - opposite edge reached.

## 8. RANGE_EARLY_ANY1 readiness

PSE is evaluated in range direction.
RSE uses **local** support/opposition for readiness.
HTF RSI remains context/strength information and does not veto range readiness.

Ignition families:
1. MTE aligned;
2. local RSE supportive;
3. PSE CONFIRM.

Hard source opposition:
- MTE strongly opposes **and**
- local RSE opposes.

### STRONG source

If hard opposition:
- WAIT / awareness only.

Otherwise:
- if any one ignition family is present -> ARM immediately;
- if none -> WAIT.

No PREP requirement for accepted EARLY_ANY1 production contract.

### ACCEPTED

If previous state was ARMED in same direction and bar is confirmed:
- CONFIRM.

If previous state was CONFIRMED:
- ALIGNED.

If previous state was ALIGNED:
- remain ALIGNED.

A setup that was not already ARMED at STRONG does not receive a late entry merely because +1 became ACCEPTED.

A new range source bar resets old range readiness before evaluating the new source.

## 9. OPERATOR_READINESS_V1

Paths:
- FROZEN_0_1
- TREND_OPPORTUNITY_V2
- RANGE_EARLY_ANY1

Active readiness urgency:

```text
CONFIRMED > ARMED > PREP > ALIGNED > WAIT
```

If no path active:
- WAIT;
- direction 0.

If active paths contain opposite directions:
- CONFLICT;
- direction 0;
- no unified actionable CONFIRMA;
- raw path events remain Data Window telemetry.

If all active paths agree on direction:
- select the highest urgency state;
- retain all selected source IDs for audit;
- unified confirm = any raw same-direction path CONFIRMA on that bar.

A fresh PREP / ARMED / CONFIRMED state must surface over a background same-direction ALIGNED state.

## 10. Responsiveness profiles

User-facing selector, if exposed:

```text
PADRÃO
ANTECIPADO
```

Default = **PADRÃO**.

Do not ship CONFIRMADO.

### PADRÃO

Action event = unified OPERATOR_READINESS CONFIRMA.

Thesis Management starts only from PADRÃO CONFIRMA.

### ANTECIPADO

This is an **early posture**, not a fake confirmation.

Allowed only when all are true:
- timeframe is 15m / 1H / 4H / 1D / 3D;
- selected opportunity source is TREND_OPPORTUNITY_V2;
- opportunity kind is BREAKOUT_EXPANSION or REACCELERATION;
- unified operator projection newly enters ARMED;
- no conflict.

Not allowed for:
- frozen pullback/retest/reclaim;
- RANGE_ROTATION;
- REGIME_REVERSAL;
- 1W;
- 1M.

ANTECIPADO must never:
- generate a PADRÃO CONFIRMA;
- start management;
- rewrite history.

## 11. Thesis Management V1.1

Starts only when unified PADRÃO emits directional CONFIRMA.

A new PADRÃO confirmation supersedes any still-open prior management thesis.

Freeze at confirmation:
- direction;
- confirm close;
- source path / opportunity kind;
- source bar;
- honestly available target;
- honestly available invalidation;
- anchor capability.

### 11.1 Anchor source

FROZEN_0_1:
- target = Market Map destination at confirm;
- invalidation = Market Map invalidation at confirm.

TREND_OPPORTUNITY_V2:
- target = current Market Map destination;
- invalidation = current Market Map invalidation.

RANGE_EARLY_ANY1:
- target = source range opposite edge minus edge band for LONG;
- target = source range opposite edge plus edge band for SHORT;
- invalidation = source range low for LONG;
- invalidation = source range high for SHORT.

### 11.2 Anchor usability

Target is usable only when it is still ahead of confirm close in thesis direction.

Invalidation is usable only when it is behind confirm close in thesis direction.

Capability:
- FULL
- INVALIDATION_ONLY
- TARGET_ONLY
- NONE

Never synthesize a missing/invalid target or invalidation.

For simultaneous same-direction confirming sources:
- merge only identical/equivalent usable target values;
- merge only identical/equivalent usable invalidation values;
- conflicting values become unavailable for that capability;
- preserve source telemetry.

### 11.3 Management calculations

Target hit:
- LONG: high >= frozen target;
- SHORT: low <= frozen target.

Invalidation:
- close-confirmed only;
- LONG: close < frozen invalidation;
- SHORT: close > frozen invalidation.

Target near:
- target room is nonnegative and <= **0.30 ATR**.

Invalidation near:
- invalidation buffer is nonnegative and <= **0.20 ATR**.

Path progress, only when target exists:
- initial directional distance = target - confirm close;
- progress = directional move from confirm close / initial target distance.

Strength uses existing accepted MTE/RSE/PSE semantics in management direction.

Management V1 rules:

1. terminal:
   - target and invalidation same bar -> AMBIGUOUS;
   - target hit -> COMPLETED;
   - invalidation -> INVALIDATED.

2. otherwise:
   - invalidation near -> PROTECT;
   - target near + REACTION_RISK -> REALIZATION_RISK;
   - path progress >= 0.50 and strength in FADING / EXHAUSTED / REACTION_RISK -> REALIZATION_RISK;
   - strength == EXHAUSTED -> PROTECT;
   - else CONTINUATION.

Structural warning remains diagnostics/telemetry only; it does not independently force management state.

### 11.4 Capability behavior

Missing target disables only:
- target progress;
- target-near;
- COMPLETED;
- target-driven REALIZATION_RISK.

Missing invalidation disables only:
- invalidation-near;
- INVALIDATED.

Strength-based CONTINUATION / PROTECT remains available for every directional thesis.

## 12. Horizon policy

### 15m / 1H
- short trades;
- precision execution;
- PADRÃO + supported TREND ANTECIPADO;
- Management V1.1 KEEP.

### 4H / 1D
- primary swing horizons;
- PADRÃO + supported TREND ANTECIPADO;
- Management V1.1 KEEP.

### 3D
- active medium/long opportunity;
- PADRÃO + supported TREND ANTECIPADO;
- Management V1.1 KEEP.

### 1W
- high-horizon opportunity/context;
- PADRÃO only;
- Management V1.1 KEEP but sparse;
- do not loosen weekly logic merely to create more events.

### 1M
- macro/cycle awareness only;
- no standalone Execution path;
- no ANTECIPADO;
- no Thesis Management start.

For 3D/1W macro context:
- only prior completed calendar month may be consumed;
- current incomplete month is never visible;
- UNAVAILABLE is different from NEUTRAL;
- monthly alignment never hard-blocks an accepted 3D/1W signal.

The fixed monthly 50/200 regime descriptor remains contextual only.
The 12/46 monthly candidate is not promoted.

## 13. Direct operator UX

Normal operator surface should not expose engine jargon by default.

Target embedded Market Map panel concepts:

```text
CENÁRIO
OPORTUNIDADE
LADO
AÇÃO
ALVO
GESTÃO
INVALIDA
CORREÇÃO   (only when relevant)
```

Candidate direct values:

CENÁRIO:
- ALTA
- BAIXA
- TRANSIÇÃO
- RANGE
- MISTO / CONFLITO only when needed

OPORTUNIDADE:
- CORREÇÃO / RETESTE
- BREAKOUT
- REACELERAÇÃO
- REVERSÃO
- ROTAÇÃO DE RANGE
- NENHUMA

LADO:
- COMPRA / LONG
- VENDA / SHORT
- —

AÇÃO:
- OBSERVAR
- PREPARAR
- ARMADO
- CONFIRMA
- ALINHADO
- CONFLITO

GESTÃO:
- CONTINUIDADE
- PROTEGER
- REALIZAÇÃO
- INVALIDADA
- CONCLUÍDA
- — when no active managed thesis

The script provides market/thesis context.
It never claims to know whether the operator actually holds a position.

## 14. Standalone Execution UX

Keep one compact cue, not a second panel.

It should expose:
- operator readiness;
- direction;
- profile posture when ANTECIPADO is active;
- management cue when a PADRÃO thesis exists.

MTE histogram remains useful as the lower-pane visual anchor.

## 15. Data Window / diagnostics

Keep or add hidden audit fields for:
- each independent path readiness / direction / confirm event;
- trend Opportunity kind / stage / source bar / source-strong;
- range validity / high / low / mid / edge / stage / source bar;
- operator readiness / direction / conflict / confirm;
- selected source path;
- active profile posture;
- management active / state / direction;
- anchor capability;
- frozen target / invalidation;
- path progress;
- monthly macro relation where available.

Normal operation must not require opening Data Window.

## 16. Implementation order

1. preserve current 0.1 path under explicit internal naming;
2. add opportunity/range state generation from existing Market Map semantics;
3. add independent trend/range readiness paths;
4. add OPERATOR_READINESS_V1;
5. add PADRÃO / scoped ANTECIPADO posture;
6. add Thesis Management V1.1;
7. update direct panel / standalone cue;
8. add audit plots;
9. mirror semantics in Market Map + Execution;
10. Static integrity;
11. Pine compile;
12. targeted TradingView evidence;
13. Portuguese operator guide;
14. promotion.

## 17. Translation invariants

Production candidate fails Phase G if any of these are violated:

- no lookahead;
- no historical backdating;
- actionable state changes commit only on chart close;
- HTF context remains confirmed;
- 0.1 correction/retest/reclaim behavior remains an independent path;
- trend/range path cannot mutate 0.1;
- OPERATOR_READINESS does not suppress a non-conflicting raw confirm;
- conflict never produces unified confirm;
- ANTECIPADO never starts management;
- 1W never emits ANTECIPADO;
- 1M never starts execution management;
- missing anchors remain missing;
- no synthetic target/invalidation;
- Market Map embedded rows and standalone Execution agree after reload.

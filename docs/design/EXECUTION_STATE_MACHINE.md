# Execution 0.1.0 — Semantic State Machine

**Status:** architecture candidate; no production Pine yet  
**Date:** 2026-09-23  
**Tracker:** #11  
**Depends on:** Market Map semantic contract

## 1. Design objective

Execution must answer a narrower question than Market Map:

> Given a valid directional map and a relevant price location, is the move becoming executable now?

It must not reproduce the old workflow where three oscillators, four RSI rows and a volume panel are mentally reconciled by the operator.

The engine can be complex internally. The visible result must remain small and semantic.

## 2. Two orthogonal outputs

Execution will not compress everything into one score.

It has two independent visible dimensions:

### 2.1 EXECUÇÃO — readiness

- `AGUARDAR`
- `PREPARANDO LONG`
- `PREPARANDO SHORT`
- `ARMADO LONG`
- `ARMADO SHORT`
- `CONFIRMA LONG`
- `CONFIRMA SHORT`
- `ALINHADO LONG`
- `ALINHADO SHORT`

`CONFIRMA ...` is a one-bar transition event suitable for alerts.

`ALINHADO ...` is the persistent post-confirmation state. It is **not** position tracking and does not mean “stay in a trade”.

### 2.2 FORÇA — continuation / reaction risk

- `NORMAL`
- `PERDENDO FORÇA`
- `EXAUSTÃO`
- `RISCO DE REAÇÃO`

This axis is deliberately independent from readiness.

Example:

```text
EXECUÇÃO  ALINHADO LONG
FORÇA     PERDENDO FORÇA
```

is meaningful: the directional evidence remains aligned, but continuation quality is deteriorating.

No percentage probability is attached to these labels.

## 3. Direction is separate from stage

Internally:

```text
executionDir   -1 / 0 / +1
readinessStage WAIT / PREP / ARMED / CONFIRMED
strengthState  NORMAL / FADING / EXHAUSTED / REACTION_RISK
```

This prevents a combinatorial enum such as `LONG_ARMED_EXHAUSTED_NEAR_TARGET`.

The renderer combines direction + stage into operator wording.

The initial engine-owned thresholds/defaults are documented in `EXECUTION_DEFAULTS.md`. The deterministic Market Map location reduction is documented in `MARKET_MAP_EXECUTION_BRIDGE.md`.

Machine-readable state codes are canonical in `manifests/suite-semantics-v1.json` and are validated against the reference model in CI.

## 4. Context and location contract

Execution is allowed to become interested only when the canonical Market Map logic provides a coherent thesis.

Required conceptual inputs:

- valid `mapDir`
- thesis not invalidated
- no regime/structure conflict that suppresses the map
- correction/retest/reclaim/location context
- destination proximity where relevant

Production scripts remain self-contained at runtime, per `SUITE_INTEGRATION_CONTRACT.md`. Execution will recompute the shared canonical kernels rather than require operator `input.source()` wiring.

### 4.1 Location states

Execution should internally distinguish at least:

- `OUTSIDE` — no useful execution location
- `APPROACHING` — approaching primary reaction area
- `IN_CORRECTION` — inside primary correction zone
- `RETEST` — confirmed structural retest
- `RECLAIM` — confirmed sweep/reclaim aligned with thesis
- `DESTINATION_NEAR` — continuation exists but reaction risk is elevated

Location is a **gate for attention**, not an entry signal by itself.

## 5. Momentum Turn Engine

Source concepts: repaired Moving Average Shift research.

The production engine should retain:

- normalized distance from a base moving average
- turn direction
- acceleration / deceleration
- smoothed momentum state
- close-confirmed state transitions

It should not retain:

- three user-selectable signal modes
- arbitrary “probability” wording
- synthetic percentile warmup
- user-facing MA-type zoo

### 5.1 Semantic momentum states

- `TURN_UP`
- `UP_ACCEL`
- `UP_DECEL`
- `TURN_DOWN`
- `DOWN_ACCEL`
- `DOWN_DECEL`
- `NEUTRAL`

The exact clean-room formula and defaults are implementation decisions to validate, not operator tuning work.

## 6. RSI State Engine

The first clean-room candidate is **RSE-A**, documented in `RSI_STATE_ENGINE.md`.

It separates local RSI semantics from confirmed HTF context rather than flattening both into a four-row table.

Base research:
- RSI 14
- centerline behavior
- recent slope/acceleration
- standard exhaustion regions
- optional divergence research

The visible product should not expose four manually configured RSI timeframes or a historical RSI table.

### 6.1 Automatic timing

- local RSI: current chart timeframe
- context RSI: same automatic confirmed HTF policy used by the suite
- actionable transitions: chart-close confirmed
- HTF contribution: confirmed only

### 6.2 Semantic RSI states

Directional:
- `BULL`
- `BEAR`
- `NEUTRAL`

Reaction-oriented:
- `RECOVERING_OVERSOLD`
- `FADING_OVERBOUGHT`
- `RECOVERING_OVERBOUGHT` where appropriate for continuation
- `FADING_OVERSOLD`
- `EXTREME_OVERBOUGHT`
- `EXTREME_OVERSOLD`

Raw RSI values can remain available in Data Window/diagnostics but are not the primary UX.

### 6.3 Divergence

Regular/hidden divergence remains research-only for the first implementation.

It becomes a default Execution input only if validation shows incremental information after momentum + RSI state + participation are already present.

## 7. Participation Engine

Participation has two evidence classes with different truth guarantees.

### 7.1 Historical / reload-safe evidence — core

Allowed to influence confirmed Execution states:

- relative volume against an internal baseline
- expansion / contraction of volume
- candle-location pressure proxy
- price/volume acceptance behavior where useful

The candle-location buy/sell split is explicitly a **pressure proxy**, not aggressor delta.

### 7.2 Realtime incremental delta — enhancement only

A `varip` incremental up/down volume engine can observe realtime updates while the chart is open.

It cannot reconstruct equivalent historical data after reload.

Therefore for Execution 0.1.0:

> Realtime-only delta may annotate or reinforce the live view, but it must **not** be required to create a persistent confirmed signal or a reload-reconstructible alert.

This is a hard timing invariant.

If later TradingView exposes a historical data source with equivalent semantics, this policy can be revisited.

### 7.3 Participation states

Core reload-safe state:

- `CONFIRMA`
- `NEUTRO`
- `FRACO`
- `CONTRARIA`

Optional realtime annotation:

- `RT+`
- `RT-`
- `RT SEM DADO` only in diagnostics

## 8. Readiness state machine

### 8.1 AGUARDAR

Default state.

Remain here when:
- no coherent Market Map thesis
- location is irrelevant
- thesis is invalidated
- direction is structurally conflicted
- evidence is contradictory enough that no execution setup exists

Do not invent a separate visible “NO TRADE score”.

### 8.2 PREPARANDO

Enter when all are true:

1. coherent directional map
2. relevant location: approaching correction/retest/reclaim
3. no invalidation
4. momentum is no longer strongly opposing the thesis

This is **attention**, not confirmation.

### 8.3 ARMADO

Enter from PREPARANDO when:

- momentum has turned/aligned in thesis direction
- local RSI state supports recovery/continuation
- confirmed RSI context is not opposite the thesis
- participation is not actively contradictory
- location remains valid

ARMADO means:

> the setup has the ingredients; wait for close confirmation.

### 8.4 CONFIRMA — event

One-bar event on the transition into confirmed readiness.

Requires:
- chart bar confirmed
- ARMADO was valid
- directional momentum remains aligned/accelerating
- local RSI remains compatible
- confirmed RSI context remains non-opposing
- reload-safe participation confirms or is sufficiently constructive
- Market Map thesis/location has not invalidated

This event is the primary alert edge.

### 8.5 ALINHADO — persistent state

After CONFIRMA, remain ALINHADO while:
- Market Map direction remains valid
- execution momentum remains directionally acceptable
- no explicit cancellation condition occurs

ALINHADO is **not a trade-management instruction**. FORÇA supplies deterioration/exhaustion warnings independently.

## 9. Reset / cancellation rules

PREPARANDO or ARMADO returns to AGUARDAR when:
- map thesis invalidates
- map direction disappears or reverses
- relevant location is lost before confirmation
- momentum makes a confirmed turn against the thesis
- RSI + momentum jointly contradict the intended direction

CONFIRMED/ALINHADO resets when:
- map thesis invalidates
- canonical map direction reverses
- a new opposing structural thesis supersedes the old one

Do not reset solely because one oscillator wiggles for one bar.

## 10. Strength / reaction-risk engine

This solves a different operator problem:

> The move is still directionally valid, but is continuation quality deteriorating near a place where reaction matters?

### 10.1 NORMAL

No meaningful deterioration cluster.

### 10.2 PERDENDO FORÇA

Exactly one independent deterioration family is enough to move Strength from NORMAL to PERDENDO FORÇA:

- momentum deterioration
- RSI deterioration/exhaustion
- reload-safe participation deterioration

This is deliberately a **soft warning**. It does not cancel an aligned Execution thesis by itself.

### 10.3 EXAUSTÃO

Two or more independent deterioration families are required.

Examples:
- momentum deceleration + RSI exhaustion
- momentum turn + weak/contrary participation
- RSI exhaustion + participation deterioration

This is stronger than PERDENDO FORÇA but still not “sell/buy now”.

### 10.4 RISCO DE REAÇÃO

Highest reaction warning.

Require:
- a meaningful Market Map location such as `DESTINATION_NEAR`, opposing liquidity, or a completed sweep/reclaim
- plus confirmed deterioration/exhaustion evidence

This wording is intentionally **risk**, not a calibrated probability.

## 11. Example operator outputs

### Setup forming

```text
EXECUÇÃO   PREPARANDO LONG
FORÇA      NORMAL
```

### Ready but waiting for close

```text
EXECUÇÃO   ARMADO LONG
FORÇA      NORMAL
```

### Confirmed transition

```text
EXECUÇÃO   CONFIRMA LONG
FORÇA      NORMAL
```

### Direction still aligned, continuation deteriorating

```text
EXECUÇÃO   ALINHADO LONG
FORÇA      PERDENDO FORÇA
```

### Near structural destination with exhaustion cluster

```text
EXECUÇÃO   ALINHADO LONG
FORÇA      RISCO DE REAÇÃO
```

The last example is a warning to inspect the market, not an automatic exit command.

## 12. Initial UI contract

Preferred default:
- one lower pane
- one compact momentum visualization
- one current Execution state
- one current Strength state
- optional confirmed LONG/SHORT chart marker
- no second panel

Normal controls target:
- show/hide chart markers
- optional appearance controls only

Advanced/Diagnostics may expose:
- raw momentum state
- raw RSI state
- participation state
- confirmed HTF context
- realtime-delta availability

No:
- Compact/Full variants
- four manual RSI timeframe selectors
- RAW/VI volume mode selector
- three MAS signal-mode selector
- arbitrary score
- percentage probability
- profile selector unless later evidence proves a real need

## 13. Alert contract

Alerts are transition events, not persistent conditions.

Candidate alert edges:

- `CONFIRMA LONG`
- `CONFIRMA SHORT`
- `RISCO DE REAÇÃO` entered
- optional `ARMADO LONG/SHORT` entered

Default production recommendation:
- confirmation alerts enabled
- armed/reaction alerts configurable
- no repeated alert every bar while a state persists

All actionable alerts are chart-close confirmed.

## 14. Historical validation telemetry

Execution should receive a hidden audit schema similar to Market Map.

Minimum audit fields:

- context/map direction
- location code
- momentum state code
- RSI state code
- participation state code
- readiness stage
- strength state
- PREPARANDO event
- ARMADO event
- CONFIRMA event
- cancellation/reset event

Validation questions:

- Is PREPARANDO always-on or never-on?
- Does ARMADO actually precede CONFIRMA?
- Are confirmation events close/reload stable?
- Does one evidence family dominate every signal?
- Is one direction/timeframe pathologically overrepresented?
- How often does RISCO DE REAÇÃO occur near a Market Map destination vs randomly elsewhere?
- Does realtime-only delta ever change a reload-safe confirmed event? It must not.

These metrics are engineering diagnostics, not strategy win rates.

## 15. Acceptance gates before production promotion

1. Pine v6 compile: 0 errors / 0 warnings
2. no unreachable default transition
3. no synthetic percentile warmup spike
4. confirmed HTF parity after reload
5. CONFIRMA events identical after reload
6. no confirmed signal depends on realtime-only `varip` data
7. BTCUSDT 15m / 1H / 4H visual matrix
8. historical event-frequency sanity
9. one-glance UX
10. no user tuning required for normal operation

## 16. Implementation hold

This document freezes the intended semantics, not the exact formula.

Production `execution.pine` starts only after Market Map MM-0 closes its remaining real-chart gates and the shared semantic contract is stable enough to generate/recompute the canonical context without drift.


## 17. Reference semantic model

Before Pine implementation, the transition contract is executable in pure Python:

- `tools/execution_state_reference.py`
- `tools/test_execution_state_reference.py`

The test suite exhaustively verifies key invariants including:
- WAIT cannot jump directly to ARMED/CONFIRMED/ALIGNED
- unconfirmed bars cannot emit CONFIRMA
- invalid/conflicted map context cannot arm
- direction reversal resets before the opposite setup starts
- CONFIRMA lasts one transition bar then becomes ALINHADO
- RISCO DE REAÇÃO requires meaningful location plus at least two deterioration families

The reference model validates semantics only; market formulas remain subject to TradingView validation.

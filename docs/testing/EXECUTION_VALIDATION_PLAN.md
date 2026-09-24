# Execution 0.1.0 — Validation Plan

**Status:** research / pre-implementation  
**Date:** 2026-09-23  
**Tracker:** #11  
**Depends on:** `EXECUTION_STATE_MACHINE.md`

## 1. Validation goal

Execution is not a strategy backtester.

Validation asks:

1. Are the semantics internally reachable and coherent?
2. Are confirmed events deterministic after reload?
3. Does the engine avoid always-on / never-on states?
4. Are the timing states visually useful around real Market Map locations?
5. Does one evidence family dominate the state machine unintentionally?
6. Do results survive different crypto assets/timeframes without retuning defaults?

No acceptance gate is based on maximizing historical profit.

## 2. Gate A — static / compile

Hard PASS requirements:

- Pine v6: 0 errors
- Pine v6: 0 warnings
- no `lookahead_off` HTF state where confirmed context is required
- no unreachable default readiness path
- no synthetic percentile warmup substitution
- no persistent-state alertcondition where an edge event is intended
- no confirmed signal depending on `varip`, `barstate.isrealtime` or equivalent realtime-only history
- no arbitrary probability percentage
- no user-facing multi-mode signal selector
- no four-manual-timeframe RSI configuration
- no Compact/Full panel split

## 3. Gate B — semantic transition invariants

The following transitions must be possible:

```text
AGUARDAR -> PREPARANDO -> ARMADO -> CONFIRMA -> ALINHADO
```

Mirrored for SHORT.

The following must be impossible:

- AGUARDAR -> CONFIRMA without the configured readiness path
- CONFIRMA on an unconfirmed chart bar
- ARMADO after the Market Map thesis is invalidated
- LONG readiness while the canonical context direction is SHORT
- SHORT readiness while the canonical context direction is LONG
- realtime-only delta changing a historical/reload-safe confirmed event

Cancellation must be explicit and deterministic.

## 4. Gate C — semantic-code integrity

Canonical integer/state mappings live in:

`manifests/suite-semantics-v1.json`

CI validates that the manifest and executable Python reference enums are identical using:

`tools/check_suite_semantics.py`

Any semantic code change is a contract change and must be intentional.

## 5. Gate D — hidden audit schema

Execution should expose Data-Window-only audit plots, versioned independently from the Market Map audit schema.

Candidate fields:

```text
EX Audit • Schema
EX Audit • Confirmado
EX Audit • ContextDir
EX Audit • Location
EX Audit • Momentum
EX Audit • RSI
EX Audit • Participation
EX Audit • Readiness
EX Audit • Strength
EX Audit • Preparando evt
EX Audit • Armado evt
EX Audit • Confirma evt
EX Audit • Cancelado evt
EX Audit • Risco reação evt
EX Audit • RT delta disponível
```

Codes must be documented and stable within an audit-schema version.

The audit schema exists for CSV/reload analysis, not normal chart UX.

## 6. Gate E — historical event-frequency sanity

The offline analyzer should report per asset/timeframe:

- bars loaded
- coherent-context bars
- relevant-location bars
- PREPARANDO count
- ARMADO count
- CONFIRMA count
- cancellation count
- ALINHADO duration distribution
- strength-state counts
- reaction-risk events
- LONG vs SHORT balance
- momentum-state distribution
- RSI-state distribution
- participation-state distribution

Review flags, not automatic optimization targets:

- PREPARANDO nearly always-on
- ARMADO never reached
- CONFIRMA nearly identical to every momentum cross
- one direction dominates despite mixed historical regimes
- reaction risk fires far from relevant Market Map locations
- participation is always neutral or always confirming
- one evidence family is effectively irrelevant
- excessive same-bar state jumps

The purpose is to discover broken logic, not tune for a preferred hit rate.

## 7. Gate F — reload parity

Workflow:

1. load a fixed chart/history
2. export Execution audit CSV
3. reload script/chart
4. export the same history again
5. compare only confirmed rows

Hard PASS:

- ContextDir identical
- Location identical
- Momentum/RSI/Participation confirmed states identical
- Readiness identical
- Strength identical
- CONFIRMA events identical
- cancellation events identical

Realtime-only annotation fields are excluded from parity.

## 8. Gate G — visual matrix

Initial matrix:

### BTCUSDT
- 15m
- 1H
- 4H

Questions:
- Can the operator understand current readiness in seconds?
- Does PREPARANDO occur near a meaningful reaction location rather than randomly?
- Is ARMADO visually distinct from CONFIRMA?
- Does ALINHADO linger sensibly without pretending to track a position?
- Does PERDENDO FORÇA precede some visible deterioration without firing constantly?
- Does RISCO DE REAÇÃO cluster near destination/liquidity/exhaustion contexts?

No manual threshold changes during the default matrix.

## 9. Gate H — cross-asset sanity

After BTC defaults are stable, test unchanged defaults on:

- ETHUSDT
- AVAXUSDT

At minimum:
- 15m
- 1H
- 4H

This is a robustness gate, not an optimization round.

If a default only works after per-asset tuning, it is not a good 0.1.0 default.

## 10. Gate I — realtime delta experiment

Only after reload-safe core is accepted.

Test the optional realtime incremental delta annotation separately.

Requirements:

- clearly marked realtime-only in diagnostics
- no change to CONFIRMA event identity
- no change to confirmed historical readiness after reload
- no fake historical backfill
- graceful `SEM DADO RT` state after load/reload

Evaluate whether it adds useful live context.

If not, omit it from the production default even if technically interesting.

## 11. Reaction-risk validation

`RISCO DE REAÇÃO` requires both:

1. meaningful Market Map location
2. independent deterioration/exhaustion cluster

Audit questions:
- percent of reaction-risk events near DESTINO / relevant opposing liquidity / reclaim
- whether the event is dominated by RSI alone
- whether it fires repeatedly during a single extended condition
- whether edge semantics prevent alert spam

Do **not** label any resulting historical percentage as future probability.

## 12. Alert validation

For every production alert:

- edge-driven
- chart-close confirmed unless explicitly documented otherwise
- one alert per transition
- reload does not fabricate historical notifications
- current-state persistence does not retrigger every bar

Initial alert candidates:
- CONFIRMA LONG
- CONFIRMA SHORT
- optional RISCO DE REAÇÃO entered

ARMADO alerts remain optional because excessive early warnings would undermine the objective UX.

## 13. Promotion rule

Execution 0.1.0 is promotable only when:

- all hard timing/static invariants PASS
- reload parity PASS
- BTC matrix is readable with defaults
- ETH/AVAX show no obvious default pathology
- no realtime-only evidence is required for confirmed signals
- visual output remains materially simpler than the three legacy scripts it replaces

A visually impressive oscillator that fails deterministic timing or requires constant user interpretation does not pass.

# ADR — Suite Runtime Topology

**Status:** accepted for 0.1.x architecture  
**Date:** 2026-09-23  
**Logical suite:** Market Map + Execution + Decision Panel  
**Runtime indicators:** 2

## Context

The suite has three logical responsibilities:

1. **Market Map** — structural overlay
2. **Execution** — timing/participation lower pane
3. **Decision Panel** — semantic synthesis

Treating those three names as three mandatory TradingView indicators creates avoidable problems:

- a standalone Decision Panel would need to recompute both Market Map and Execution state because required cross-script source wiring is rejected
- Market Map already has a semantic structural panel during MM-0
- a third indicator would create panel duplication and more chart setup
- the user explicitly wants fewer controls and less visual/code clutter
- a third runtime artifact adds another version/release surface without adding unique market information

## Decision

For the 0.1.x suite, keep **three logical product layers but only two runtime Pine indicators**.

### Runtime indicator 1 — Market Map

Overlay.

Owns:
- structural/regime/liquidity/correction rendering
- destinations/invalidation
- the **single suite Decision Panel**

For the final integrated suite, the Market Map panel gains the canonical Execution and Strength semantics:

```text
MARKET MAP

REGIME      ALTA
FASE        CORREÇÃO
ESTRUTURA   ALTA • HH/HL
CORREÇÃO    84.850–85.150 ★★★
DESTINO     87.400 PDH → 88.100 EQH
INVALIDA    84.050

EXECUÇÃO    ARMADO LONG
FORÇA       NORMAL
```

The Decision Panel remains a named logical layer in architecture/docs, but it is rendered by Market Map.

### Runtime indicator 2 — Execution

Lower pane.

Owns:
- momentum visualization
- RSI state visualization where useful
- participation visualization
- confirmed execution markers/events
- optional minimal current-state labels

It does **not** create another full Decision Panel.

## Shared Execution kernel

Because Pine cannot rely on local runtime imports between these two personal scripts, the canonical Execution kernel will be generated/validated into:

- `market-map.pine` — slim calculation only for the embedded Decision Panel
- `execution.pine` — same semantic kernel plus lower-pane renderer

Repository tooling must enforce that the semantic kernel is identical.

## Why not three runtime scripts

Rejected topology:

```text
Market Map overlay
Execution pane
Decision Panel overlay
```

Problems:
- duplicate Market Map calculations in Decision Panel
- duplicate Execution calculations in Decision Panel
- second overlay/panel lifecycle
- extra installation/configuration/version surface
- no unique information added by the third script

## Why not one runtime script

A single Pine indicator can force plots into different panes only within Pine's rendering constraints, but combining a structural overlay, lower-pane oscillator and all rendering into one artifact makes layout/control behavior harder to reason about and maintain.

Two indicators preserve a clean separation:
- chart geometry above
- timing evidence below

without forcing the operator to manage three scripts.

## Decision Panel lifecycle

MM-0's current structural panel is the **foundation** of the final Decision Panel.

Evolution:

```text
MM-0 structural panel
       ↓
Execution semantic contract stabilizes
       ↓
add EXECUÇÃO + FORÇA rows
       ↓
final suite Decision Panel
```

No separate Compact/Full version is created.

## User workflow

Final intended normal setup:

1. add **Market Map**
2. add **Execution**
3. done

No source wiring.
No third panel script.
No profile/configuration ceremony.

## Versioning

Logical versions remain independent in documentation:

- Market Map version
- Execution version
- Suite semantic-contract version

Decision Panel wording can have its own contract revision in docs/tests without requiring a third published Pine artifact.

## Revisit conditions

A standalone Decision Panel would only be reconsidered if TradingView later provides a low-friction, deterministic shared-state mechanism that removes duplicated calculation and user wiring, or if a concrete workflow demonstrates unique value from a separate panel artifact.

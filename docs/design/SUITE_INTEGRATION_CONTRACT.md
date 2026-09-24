# Suite Integration Contract — Market Map / Execution / Decision Panel

**Status:** architecture decision  
**Date:** 2026-09-23  
**Scope:** how the three Pine products share semantics without creating operator setup burden

## 1. Problem

Pine Script does not provide a normal module/import mechanism between arbitrary personal indicators.

TradingView supports two relevant cross-script mechanisms:

1. **Published Pine libraries**
   - reusable functions/types can be imported
   - the library must be published first
   - consumers pin an explicit library version

2. **Indicator-on-indicator source inputs**
   - an `input.source()` can select a plot from another indicator
   - this creates runtime wiring in chart settings
   - if the source script is removed/re-added, the external source selection must be configured again
   - only plotted series can cross this boundary

Neither mechanism should become a normal operator burden for PineTrading-Lab.

## 2. Product decision

The suite products will be **self-contained at runtime**.

Normal use must be:

1. add Market Map
2. add Execution
3. optionally add Decision Panel
4. use them immediately with production defaults

The operator must **not** wire ten source inputs between scripts.

Decision Panel must not require Market Map and Execution plots to be manually selected in Settings.

## 3. Shared logic strategy

Self-contained runtime does not mean copy/paste drift is acceptable.

Repository architecture will eventually separate:

- **semantic specification** — canonical definitions of states and contracts
- **shared calculation kernels** — deterministic logic reused by generation/build tooling
- **product renderers** — Market Map / Execution / Decision Panel UI
- **generated Pine candidates** — standalone scripts pasted into TradingView

Pine has no local include directive, so reuse will be enforced by repository tooling rather than manual duplication.

Possible implementation after MM-0 stabilizes:

```text
src/shared/
  regime.kernel
  structure.kernel
  correction.kernel
  execution.kernel
  contracts.kernel

tools/build_pine_suite.py

src/core/
  market-map.pine
  execution.pine
  decision-panel.pine
```

The exact fragment format remains an implementation detail. The invariant is more important:

> A semantic rule is authored once canonically and generated/validated into every product that needs it.

## 4. Why not use external `input.source()` as the production architecture

External source wiring is useful for research, but is rejected as the normal product contract because:

- it requires operator configuration
- it can break when scripts are removed/re-added
- it exposes transport plumbing in Settings
- it makes a clean default install impossible
- multiple semantic fields would require multiple source inputs unless packed into an opaque numeric bus

An encoded numeric bus would reduce the number of connections but would make debugging and long-term compatibility worse.

Therefore:

**External source inputs may be used only for lab experiments, never as required production setup.**

## 5. Why not require a published Pine library now

A Pine library is technically viable for reusable functions, but it introduces a separate TradingView publication/version lifecycle.

MM-0 and Execution are still evolving quickly. Publishing/pinning a library this early would add release friction before the stable semantic boundaries are known.

Decision:

- **do not require a Pine library for 0.1.x foundation work**
- revisit a private/published shared library only after semantic kernels stabilize
- repository generation remains the default architecture unless library publication clearly reduces maintenance without harming usability

## 6. Semantic contract

Products may compute the same canonical states internally, but the meanings must stay identical.

### 6.1 Market Map contract

Canonical concepts:

- `regimeDir`: -1 / 0 / +1
- `phase`: semantic state, e.g. impulse / pullback / correction / retest / transition / invalidated
- `structureDir`: -1 / 0 / +1
- `correctionTop`
- `correctionBottom`
- `correctionActive`
- `destination1`
- `destination2`
- `destinationNear`
- `invalidation`
- `thesisInvalidated`
- `contextTf`
- `confirmedHtfPolicy`

### 6.2 Execution contract

Canonical concepts:

- `momentumState`
- `rsiState`
- `participationState`
- `executionDir`: -1 / 0 / +1
- `executionState`: wait / preparing / armed / confirmed / conflict
- `exhaustionState`
- `confirmedSignalEvent`

### 6.3 Decision Panel contract

Decision Panel synthesizes the canonical engines but owns no unique hidden trading thesis.

It must be possible to explain every Decision Panel state as:

```text
Market Map semantic state
+
Execution semantic state
=
Decision Panel wording
```

No new opaque G1/G2/G3/G4/G5 scoring layer.

## 7. Versioning contract

Each product has its own visible version.

A shared semantic-contract version will also exist once Execution production begins:

```text
SUITE_CONTRACT = 1
```

A breaking meaning change requires incrementing the contract version.

Examples of breaking changes:
- changing the meaning of `regimeDir`
- changing invalidation from close-confirmed to intrabar
- changing destination semantics from intact liquidity to arbitrary target projection
- changing Execution CONFIRMA from close-confirmed to intrabar

Parameter tuning that preserves meaning does not necessarily require a contract bump.

## 8. Validation contract

Repository integrity tests must eventually verify:

- shared semantic tokens exist in all consumers
- generated product files match canonical kernels
- no product silently changes timing semantics
- Market Map and Decision Panel use the same regime/structure/invalidation rules
- Execution and Decision Panel use the same confirmation rules

## 9. Operator UX invariant

Normal operation must never require understanding the integration architecture.

If the user has to configure script A as the source of script B before the suite works, the production UX has failed.

The repository may be sophisticated. The TradingView workflow must remain simple.

# Execution 0.1.x — Lower-Pane Renderer Contract

**Status:** architecture candidate; no production Pine yet  
**Date:** 2026-09-23  
**Tracker:** #11  
**Depends on:** MTE-A / RSE-A / PSE-A + Execution semantic state machine

## 1. Goal

Execution's lower pane must make the timing engine readable without recreating the three legacy indicators it replaces.

The pane should answer visually:

1. Is momentum positive/negative?
2. Is it accelerating, decelerating or turning?
3. Did a confirmed Execution transition just occur?
4. Is continuation quality deteriorating?

The full semantic synthesis remains in Market Map's single Decision Panel.

Therefore Execution must **not** create a second full table/panel.

## 2. Default visual stack

Normal default pane contains only:

1. **MTE core histogram**
2. **zero line**
3. **confirmed readiness transition markers**
4. **subtle Strength background treatment**
5. optional confirmed chart-overlay LONG/SHORT marker

RSE-A and PSE-A remain internal evidence engines and Data-Window diagnostics by default.

No raw RSI line.
No raw volume histogram.
No three stacked mini-indicators.

## 3. MTE histogram

Primary plotted numeric series:

```text
MTE core = (EMA8(HLC3) - EMA21(HLC3)) / ATR14
```

The histogram carries continuous shape/magnitude.

Semantic state controls the renderer category:

```text
UP_ACCEL     positive / strong
UP_DECEL     positive / softened
TURN_DOWN    positive but warning transition
NEUTRAL      muted
TURN_UP      negative but warning transition
DOWN_DECEL   negative / softened
DOWN_ACCEL   negative / strong
```

Important:
- TURN_DOWN can remain above zero.
- TURN_UP can remain below zero.

The renderer must not force TURN bars to the opposite side of zero just to make them visually dramatic.

## 4. Zero line

One understated zero line.

No default:
- percentile guides
- ±threshold horizontal bands
- signal line
- MA line in the pane
- overbought/oversold RSI lines

The lower pane is a timing view, not a technical-study dashboard.

## 5. Readiness rendering

### PREPARANDO

No repeated chart marker.

The state can be visible through a subtle pane cue or last-bar semantic label if needed during UX validation.

Reason:
- PREPARANDO is attention, not an action edge.
- printing every PREPARANDO bar would recreate visual noise.

### ARMADO

One transition marker when ARMADO is entered.

Candidate visual:
- small neutral/outlined marker in the lower pane
- no main-chart marker by default

It should say:
> setup ingredients are present; confirmation is still pending.

### CONFIRMA LONG / SHORT

This is the main actionable visual event.

On the transition bar:
- clear lower-pane marker
- optional corresponding main-chart marker
- close-confirmed only

No repeated marker during ALINHADO.

### ALINHADO

Persistent state is represented through the semantic Decision Panel and the continuing momentum/strength visual.

Do not stamp `ALINHADO` on every bar.

## 6. Strength rendering

Strength is independent of readiness.

Default candidate uses **subtle pane background intensity**, not another numeric line:

```text
NORMAL              no background emphasis
PERDENDO FORÇA      very light warning tint
EXAUSTÃO            stronger warning tint
RISCO DE REAÇÃO     strongest but still translucent warning tint
```

Why background rather than another oscillator:
- Strength is categorical.
- A line would imply false numeric precision.
- It allows the operator to see deterioration while still reading MTE shape.

Exact colors/transparencies are renderer details to tune visually later.

## 7. RSE-A rendering

Default:
- no RSI line
- no 70/30/80/20 bands
- no MTF table

Data Window/diagnostics:
- local RSI value
- local RSE state code
- confirmed HTF RSI value/context direction

Optional future diagnostics may expose raw RSI visually, but not normal operation.

## 8. PSE-A rendering

Default:
- no raw volume histogram
- no buy/sell columns
- no pseudo-delta panel

Data Window/diagnostics:
- relative volume
- pressure proxy
- directional pressure
- participation state
- strong-expansion flag

A CONFIRM/CONTRARY participation event may eventually influence marker emphasis, but must not add a second visual scale.

## 9. Main-chart markers

Candidate normal control:

```text
Mostrar confirmações no gráfico   ON
```

Only:
- confirmed LONG transition
- confirmed SHORT transition

No chart markers for:
- PREPARANDO
- every ARMADO bar
- raw RSI zones
- every volume expansion
- MTE turns by themselves

This keeps the price chart focused on events that have passed the complete Execution state machine.

## 10. Last-bar semantic cue

During first visual prototypes, one small last-bar-only cue in the Execution pane is allowed:

```text
ARMADO LONG • NORMAL
```

or:

```text
ALINHADO LONG • RISCO DE REAÇÃO
```

It is not a table and does not carry raw metrics.

Promotion decision:
- keep it only if it materially improves standalone lower-pane readability;
- otherwise rely on Market Map's embedded Decision Panel and remove it.

No duplicate permanent table.

## 11. Normal settings budget

Target normal controls:

```text
Mostrar confirmações no gráfico   bool
Mostrar status no painel inferior bool   [only if last-bar cue survives UX test]
```

Appearance controls may remain in Style rather than Inputs where Pine permits.

No normal inputs for:
- EMA8/21
- ATR14
- MTE thresholds
- RSI thresholds
- volume thresholds
- pressure threshold
- HTF selection
- signal strictness

## 12. Advanced / Data Window

Engineering diagnostics may expose:
- MTE core
- MTE acceleration
- MTE state
- RSE local state
- RSI HTF context direction
- PSE state
- relative volume
- pressure proxy
- location
- readiness
- strength
- transition events

These should use Data Window/audit plots rather than normal visual clutter.

## 13. One-glance acceptance questions

A screenshot should answer within seconds:

- Is current momentum up or down?
- Is it strengthening or weakening?
- Is there a transition warning?
- Was there a confirmed LONG/SHORT event?
- Is reaction risk elevated?

If answering those requires reading raw RSI or volume values, the UX has failed.

## 14. Anti-clutter invariants

Do not add by default:
- RSI table
- volume table
- separate participation pane
- second semantic table
- raw MTF rows
- repeated PREPARANDO labels
- repeated ALINHADO labels
- standalone TURN alerts/diamonds
- four or more horizontal threshold lines

Every default visual object must justify a decision-support role.

## 15. First prototype acceptance

When production Pine work is eventually authorized, first visual prototype should use:

- BTCUSDT 15m
- BTCUSDT 1H
- BTCUSDT 4H

with defaults only.

The operator should not adjust thresholds or colors to rescue the prototype.

If the pane is visually confusing, change the renderer/semantics rather than adding configuration.

## 16. Production hold

This document defines rendering behavior only.

It does **not** authorize `execution.pine` before the historical evidence candidates have been challenged by the Binance lab.

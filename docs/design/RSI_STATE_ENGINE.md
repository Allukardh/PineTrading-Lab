# RSI State Engine — Clean-room Candidate RSE-A

**Status:** research candidate; not production Pine  
**Date:** 2026-09-23  
**Product:** Execution 0.1.x  
**Tracker:** #11

## 1. Objective

Replace the legacy four-timeframe RSI table with a small semantic engine answering two separate questions:

1. What is local RSI doing **now**?
2. Does the confirmed higher-timeframe RSI context support, oppose or stay neutral to that local behavior?

The operator should not reconcile raw values from four rows manually.

## 2. Preserved legacy evidence

Useful defaults from the archived RSI MTF Tactical script:

```text
RSI length             14
center                 50
center buffer          ±2
overbought             70
oversold               30
extended overbought    80
extended oversold      20
minimum bar step       0.25 RSI point
recent-direction idea  current / previous / previous-2
```

Useful concept:
- RSI state is not only zone membership; direction/recovery matters.

## 3. Rejected legacy surface

Do not carry into the normal Execution UI:

- four manual timeframe inputs
- 5-column historical table
- Stochastic RSI
- RSI moving-average selector/cloud
- divergence as a default blocker
- live HTF `lookahead_off` state
- separate OB/OS alert family as the main execution trigger

Those may remain research donors, not operator burden.

## 4. RSE-A local inputs

Candidate constants:

```text
source                  close
RSI length              14
center dead-band        48–52
overbought              70
oversold                30
extreme overbought      80
extreme oversold        20
minimum directional step 0.25
zone memory             2 confirmed bars
```

These values are already recorded in the Execution research-default manifest.

## 5. Local semantic states

The existing suite state codes are retained.

### EXTREME_OVERBOUGHT

```text
RSI >= 80
```

This is treated as reaction/exhaustion risk, not automatic short confirmation.

### EXTREME_OVERSOLD

```text
RSI <= 20
```

Mirror rule.

### RECOVERING_OVERSOLD

A bullish recovery state:

```text
recently touched RSI <= 30 within 2 confirmed bars
current RSI < 52
current step >= +0.25
```

This state may continue briefly after RSI exits the raw <=30 zone.

That is deliberate: a useful recovery should not disappear the instant RSI prints 30.1.

### FADING_OVERBOUGHT

A bearish reaction state:

```text
recently touched RSI >= 70 within 2 confirmed bars
current RSI > 48
current step <= -0.25
```

Mirror of oversold recovery.

### RECOVERING_OVERBOUGHT

Bullish continuation inside the overbought zone:

```text
70 <= RSI < 80
step >= +0.25
```

The name means overbought momentum is strengthening/holding in the bullish direction. It is not a claim that overbought conditions are safe.

### FADING_OVERSOLD

Bearish continuation inside the oversold zone:

```text
20 < RSI <= 30
step <= -0.25
```

Mirror rule.

### BULL

```text
RSI >= 52
```

when no more specific zone/recovery state above applies.

### BEAR

```text
RSI <= 48
```

when no more specific state applies.

### NEUTRAL

```text
48 < RSI < 52
```

when no recovery/fade state overrides it.

## 6. Priority

Classification priority:

```text
1. EXTREME_OVERBOUGHT / EXTREME_OVERSOLD
2. RECOVERING_OVERSOLD / FADING_OVERBOUGHT
3. RECOVERING_OVERBOUGHT / FADING_OVERSOLD
4. BULL / BEAR
5. NEUTRAL
```

Extremes win because the Execution Strength engine must see exhaustion risk even if the current one-bar slope points in the trend direction.

## 7. Confirmed HTF context

RSE-A produces a separate confirmed context direction:

```text
HTF RSI >= 52 -> +1 BULL
HTF RSI <= 48 -> -1 BEAR
otherwise     ->  0 NEUTRAL
```

The context direction is intentionally simpler than the local state.

It does not duplicate local recovery/exhaustion semantics.

Timing:
- automatic suite context timeframe
- confirmed HTF values only
- no live `lookahead_off` state used for persistent Execution confirmation

## 8. How local + HTF interact

The local state remains visible/auditable on its own.

For LONG readiness:
- local RSI must be a long-supportive state
- confirmed HTF context must **not** be bearish

For SHORT readiness:
- local RSI must be a short-supportive state
- confirmed HTF context must **not** be bullish

Neutral HTF does not block a valid local recovery.

### Long-supportive local states

- BULL
- RECOVERING_OVERSOLD
- RECOVERING_OVERBOUGHT

### Short-supportive local states

- BEAR
- FADING_OVERBOUGHT
- FADING_OVERSOLD

### Long-opposing local states

- BEAR
- FADING_OVERBOUGHT
- EXTREME_OVERBOUGHT

### Short-opposing local states

- BULL
- RECOVERING_OVERSOLD
- EXTREME_OVERSOLD

These mappings intentionally preserve the existing Execution semantic reference contract.

## 9. Why extremes do not simply follow direction

RSI 85 may occur in a very strong uptrend.

RSE-A still labels it `EXTREME_OVERBOUGHT` because the state is used by the independent **FORÇA** axis.

Market direction can remain:

```text
EXECUÇÃO  ALINHADO LONG
FORÇA     EXAUSTÃO / RISCO DE REAÇÃO
```

That is more informative than forcing RSI 85 into a generic BULL bucket.

Mirror for extreme oversold.

## 10. Divergence policy

Regular/hidden divergence is not part of RSE-A.

Reason:
- it requires pivot confirmation and adds another historical-lag layer
- Momentum Turn + RSI recovery + participation already provide independent evidence families
- adding divergence before those are validated risks redundant complexity

Revisit only if historical validation shows a concrete missing behavior.

## 11. Synthetic validation

Reference tests must cover:

- Wilder RSI bounds 0–100
- monotonic up -> extreme overbought
- monotonic down -> extreme oversold
- oversold recovery memory
- overbought fade memory
- center dead-band
- recovery state expires after memory window
- HTF direction 48/52 boundaries
- HTF opposition blocks readiness support
- extreme states override one-bar directional slope

These tests validate semantics, not trading edge.

## 12. Audit plan

Execution audit should expose separately:

```text
EX Audit • RSI local state
EX Audit • RSI context dir
EX Audit • RSI value
EX Audit • RSI context value
```

Raw values are diagnostics/Data Window evidence, not primary UI rows.

## 13. Promotion rule

RSE-A becomes production-canonical only after:

1. reference tests pass
2. confirmed HTF Pine parity is proven
3. BTC 15m / 1H / 4H state frequency is sane
4. unchanged defaults behave sensibly on ETH/AVAX
5. local recovery/fade states add information beyond Momentum Turn rather than duplicating it

Until then it remains a research candidate.

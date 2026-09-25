# Suite 0.2 Roadmap — Opportunity Expansion

**Status:** approved product direction / research not yet promoted  
**Tracking:** Issue #23  
**Baseline:** Market Map 0.1.0 + Execution 0.1.0 are frozen references

## 1. Why 0.2 exists

Suite 0.1 solved the foundation problem:

- two runtime indicators instead of six competing products;
- Market Map explains structural context;
- Execution confirms timing;
- the embedded Decision Panel keeps the operator-facing surface compact;
- historical/reload/parity infrastructure is trustworthy.

The next problem is different.

Execution 0.1 is strongest around **pullback / retest / reclaim** opportunities. The operator wants the suite to help recognize and exploit a broader set of recurring market opportunities while preserving final human discretion.

Suite 0.2 therefore optimizes for:

> **broader opportunity coverage + measured responsiveness + simpler operator language**

not for more indicators, more visible metrics or more settings.

## 2. Frozen 0.1 baseline

Do not mutate 0.1 in place merely to generate more signals.

- Market Map 0.1.0 promotion:
  `0eeb0d37b256a950cfb38f627fa3521bb213d380`
- Execution 0.1.0 promotion:
  `a7557df2d0142441ea782dba4b8c3f95ebc38371`

The current `main` implementations remain the recommended **PADRÃO** reference until 0.2 evidence proves a better contract.

Any changed behavior must belong to 0.2 and have a named evidence reason.

## 3. Operator / venue model

The market-analysis engine is **directional and exchange-agnostic**.

The same bearish thesis can mean different actions depending on venue:

- **MEXC / Bitget spot**
  - bullish thesis: candidate buy / hold / add context;
  - bearish thesis: avoid new buy, protect, reduce or sell;
  - no short position is assumed.

- **Quantfury**
  - the same bullish thesis may support long;
  - the same bearish thesis may support short;
  - short remains an operator choice, not a different analysis engine.

Therefore:

- no separate "spot engine" vs "short engine";
- internal state remains LONG/SHORT or +1/-1 when technically convenient;
- visible wording should be direct enough to map to both:
  - `COMPRA / LONG`
  - `VENDA / SHORT`

The final decision always belongs to the operator.

## 4. Opportunity families

0.2 researches six major recurring opportunity families.

### 4.1 Regime reversal

Purpose:

Detect when a mature bear/bull regime is plausibly transitioning into a new directional regime early enough to matter.

Candidate ingredients:
- base formation;
- structural transition;
- first meaningful HH/HL or LH/LL progression;
- CHoCH/MSS/BOS sequence;
- HTF regime change;
- participation expansion;
- momentum turn / acceleration.

This is the class intended to catch events such as a major bear-market transition without waiting for a later textbook pullback.

### 4.2 Breakout / expansion

Purpose:

Recognize a genuine directional expansion from range/structure before the opportunity is already mostly consumed.

Candidate ingredients:
- structural break;
- close acceptance beyond structure;
- relative-volume expansion;
- pressure agreement;
- HTF compatibility;
- fakeout/reclaim rejection.

### 4.3 Pullback / retest / reclaim

Purpose:

Preserve the accepted 0.1 specialty while integrating it into the broader opportunity taxonomy.

The 0.1 correction/retest engine remains the reference implementation.

### 4.4 Continuation / reacceleration

Purpose:

Recognize a trend resuming after compression or deceleration even when price never enters a textbook correction zone.

Candidate ingredients:
- coherent regime;
- momentum deceleration followed by aligned reacceleration;
- participation recovery;
- price holding structural support/resistance;
- destination still has room.

### 4.5 Range rotation

Purpose:

Recognize useful buy/sell directional opportunities at meaningful range extremes when the market is not trending.

This must not become blind mean-reversion.

Candidate ingredients:
- confirmed range;
- meaningful upper/lower boundary;
- rejection/sweep;
- momentum turn;
- asymmetric room to opposite range liquidity.

### 4.6 Exhaustion / exit-risk

Purpose:

Provide thesis-management evidence after a move has already matured.

This is **not** an automatic sell/short command.

Candidate ingredients:
- destination proximity/achievement;
- momentum deterioration;
- RSI exhaustion;
- participation deterioration;
- adverse sweep/reclaim;
- structural failure/invalidation.

Expected operator interpretation:
- continuation still healthy;
- protect;
- realization risk;
- thesis invalidated.

## 5. Trade/thesis lifecycle

Opportunity class and execution state are separate.

Candidate internal lifecycle:

```text
NO_THESIS
  -> DISCOVERED
  -> FORMING
  -> ARMED
  -> CONFIRMED
  -> ACTIVE
  -> MATURE
  -> EXIT_RISK
  -> INVALIDATED / COMPLETED
```

The visible panel does not need to expose these exact internal names.

Important distinctions:

- **Opportunity** = what kind of market setup exists.
- **Action** = how ready the setup is now.
- **Management** = whether an already-developed thesis still has healthy continuation or increasing protection/realization risk.

The script does not know the operator's actual account position. It describes the **market/thesis condition**, never pretends to know that a position is open.

## 6. Horizon architecture

### 6.1 Tactical / precision

- **15m**
- **1H**

Use cases:
- short-duration trades;
- precision entry inside a larger 4H/1D thesis;
- early momentum/participation detail.

### 6.2 Swing

- **4H**
- **1D**

This is the primary discretionary swing-trading horizon.

The 0.2 design should make these timeframes first-class rather than merely scaled copies of 15m logic.

### 6.3 Medium / long horizon

- **3D**
- **1W**
- **1M**

Historical-lab note:
- the accepted consolidated dataset currently ends at 1W;
- 1M research must therefore use a deterministic calendar-month aggregation from the accepted 1D candles, or add an explicit 1M dataset to the historical pipeline if Pine/offline parity requires a native timeframe;
- never silently substitute 1W self-context for a monthly study.

Use cases:
- regime transition;
- cycle expansion/contraction;
- larger structural opportunity;
- medium/long position timing.

The current >1D HTF mapping must not simply be inherited.

Candidate research should compare context hierarchies such as:

```text
15m -> 1H
1H  -> 4H
4H  -> 1D
1D  -> 1W
3D  -> 1W and/or 1M
1W  -> 1M
1M  -> slower monthly / multi-month regime context
```

A second internal macro-context layer may be tested if it improves regime-transition detection without cluttering the visible panel.

## 7. Responsiveness objective

0.1 deliberately favors confirmed, reload-safe semantics.

0.2 must **measure** whether that confirmation is arriving too late before changing it.

For each opportunity family and horizon measure where possible:

- opportunity-onset bar/time;
- bars to PREPARANDO;
- bars to ARMADO;
- bars to CONFIRMA;
- ATR-normalized displacement already traveled at each state;
- structural room remaining to destination;
- opportunity episodes never recognized;
- cancellation / false-start rate;
- direction balance;
- cross-asset stability.

No profile or threshold change is justified solely because a screenshot "looks late".

## 8. Candidate profiles

Profiles are not yet accepted.

They may be introduced only if responsiveness evidence demonstrates a useful timing/confirmation tradeoff.

### ANTECIPADO

Goal:
- detect a valid opportunity earlier;
- reduce missed early-stage reversals/breakouts/reaccelerations.

Rules:
- still no lookahead;
- no historical repaint;
- actionable persistent states still commit on confirmed data;
- may allow broader opportunity locations / lighter confirmation burden.

### PADRÃO

Goal:
- preserve the accepted 0.1 behavior as the anchor/reference.

PADRÃO must remain available unchanged while profile research occurs.

### CONFIRMADO

Goal:
- fewer, later, higher-burden confirmations;
- useful where the operator prefers stronger structural/HTF evidence.

Profiles, if promoted, control coherent behavior bundles. They never expose a bag of ATR/pivot/RSI magic numbers.

## 9. Direct operator language

0.2 should increase internal semantics while **reducing translation burden**.

Candidate operator panel:

```text
CENÁRIO       ALTA
OPORTUNIDADE  REACELERAÇÃO
LADO          COMPRA / LONG
AÇÃO          PREPARAR

ALVO          87.400 -> 88.100
GESTÃO        CONTINUIDADE
INVALIDA      84.050
```

When correction information matters:

```text
CORREÇÃO      84.850–85.150
```

When a developed move deteriorates:

```text
GESTÃO        PROTEGER
```

or, only when evidence is stronger:

```text
GESTÃO        REALIZAÇÃO
```

Technical REGIME/FASE/structure/MTE/RSE/PSE codes may remain in Data Window/diagnostics. The operator should not have to mentally translate them during live use.

The visible panel must remain compact. No second full panel and no return of Compact/Full modes.

## 10. Research order

### Phase A — Opportunity taxonomy / labels
1. define deterministic opportunity-event contracts;
2. build historical episode extractor;
3. quantify how 0.1 behaves around those episodes.

### Phase B — 0.1 latency baseline
1. measure PREPARANDO / ARMADO / CONFIRMA latency;
2. quantify missed opportunities and move already traveled;
3. separate latency caused by honest confirmation from latency caused by overly narrow opportunity location.

### Phase C — Opportunity Engine candidates
1. regime reversal;
2. breakout / expansion;
3. continuation / reacceleration;
4. range rotation;
5. integrate accepted pullback/retest;
6. exit-risk / management state.

### Phase D — Horizon study
1. 4H/1D primary swing;
2. 3D/1W/1M medium/long;
3. 15m/1H precision;
4. compare HTF mappings.

### Phase E — Profile counterfactuals
Only if latency evidence warrants:
- ANTECIPADO;
- PADRÃO;
- CONFIRMADO.

### Phase F — integrated evidence
- Market Map + Execution;
- BTC primary;
- ETH/AVAX unchanged-default robustness first;
- broader universe only where useful;
- no per-asset retuning by default.

### Phase G — TradingView gate
- targeted live/reload parity;
- direct-panel usability;
- no trivial operator QA loops.

## 11. Mandatory operator guide

Before 0.2 promotion create:

`docs/GUIA_DO_OPERADOR.md`

Language: **Portuguese (Brazil)**.

It must explain:
- how to read both panels;
- every visible field/state;
- opportunity classes;
- action states;
- management/exit-risk states;
- spot buy/sell interpretation;
- optional Quantfury long/short interpretation;
- horizon/timeframe usage;
- profiles if they survive research;
- targets/corrections/invalidation;
- what 0 / ∅ / no-event means;
- practical examples;
- what the scripts cannot know;
- what remains the operator's decision.

Write it after the 0.2 semantics stabilize so the guide cannot become stale during research.

## 12. 0.2 acceptance criterion

Suite 0.2 must show:

- materially broader opportunity coverage than 0.1;
- useful regime-reversal / breakout / continuation behavior;
- preserved quality of pullback/retest handling;
- measured latency improvement where claimed;
- no hidden repaint/lookahead;
- no pathological setup churn;
- robust 4H/1D behavior;
- coherent 3D/1W/1M behavior;
- useful 15m/1H precision behavior;
- direct operator UX no more cluttered than 0.1;
- stable Market Map / Execution parity;
- Portuguese operator guide complete.

Compilation alone is not promotion evidence.

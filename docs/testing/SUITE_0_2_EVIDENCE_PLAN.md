# Suite 0.2 Evidence Plan — Opportunity Coverage and Responsiveness

**Status:** pre-registered research plan  
**Tracking:** Issue #23  
**Rule:** define the questions before tuning candidate behavior

## 1. Objective

Determine whether Suite 0.1:
- misses important recurring opportunity classes;
- recognizes valid opportunities too late;
- needs distinct responsiveness profiles;
- needs stronger high-timeframe context for medium/long trades.

This is not initially a profitability optimization study.

## 2. Frozen comparator

The exact 0.1 production baseline is the comparator.

Market Map:
`0eeb0d37b256a950cfb38f627fa3521bb213d380`

Execution:
`a7557df2d0142441ea782dba4b8c3f95ebc38371`

Do not change the comparator after seeing 0.2 results.

## 3. Primary horizons

### Precision / short
- 15m
- 1H

### Swing
- 4H
- 1D

### Medium / long
- 3D
- 1W
- 1M

The accepted Binance lab currently stores through 1W. For 1M evidence:
- first preference is deterministic calendar-month OHLCV aggregation from the accepted 1D Parquet;
- add a native 1M pipeline artifact only if parity/reproducibility evidence shows aggregation is insufficient;
- record the provenance explicitly in every 1M report.

4H / 1D are primary product-development horizons.

3D / 1W / 1M are mandatory robustness/horizon-design evidence, not optional afterthoughts.

## 4. Primary assets

Initial:
- BTCUSDT
- ETHUSDT
- AVAXUSDT

Use accepted Binance production datasets.

Expand to the wider stored universe only after the episode extractor / metrics are stable.

## 5. Opportunity episode contracts

Before testing profiles, implement deterministic episode labels for:

- regime reversal;
- breakout/expansion;
- pullback/retest/reclaim;
- reacceleration;
- range rotation;
- destination/exhaustion/exit-risk context.

The labels must be defined from data available at or after the event, with explicit separation between:
- event onset;
- confirmation point;
- later outcome.

Do not backdate a confirmed label to a point that could not have been known live.

## 6. 0.1 latency baseline

For each episode:

- did 0.1 create PREPARANDO?
- did it reach ARMADO?
- did it reach CONFIRMA?
- bars from episode onset to each state;
- price displacement in ATR from onset to each state;
- percent of structural path to destination already traveled;
- whether confirmation happened after destination was already too near;
- whether the episode completed without any actionable state.

Report distributions, not only averages:
- median;
- p75;
- p90.

## 7. Missed-opportunity taxonomy

Classify why 0.1 missed an episode where possible:

```text
NO_COHERENT_MAP
LOCATION_NOT_RELEVANT
MOMENTUM_OPPOSED
RSI_OPPOSED
PARTICIPATION_NOT_CONFIRMING
HTF_BLOCKED
THESIS_REPLACED
DESTINATION_TOO_NEAR
OTHER
```

The purpose is to distinguish:
- honest confirmation delay;
- narrow 0.1 opportunity-location policy;
- actual engine pathology.

## 8. Candidate 0.2 metrics

For each candidate opportunity class/profile:

- recognized episode count;
- missed episode count;
- PREPARANDO/ARMADO/CONFIRMA latency;
- cancellation rate;
- <=1/2/3-bar churn;
- direction balance;
- opportunity-class balance;
- timeframe balance;
- structural room remaining at signal;
- invalidation-before-target diagnostic;
- target-before-invalidation diagnostic where OHLC order is knowable;
- ambiguous/censored accounting.

Outcome metrics remain diagnostics, not "win probability".

## 9. Profile test

Profiles are tested only after the 0.1 latency report exists.

Candidate comparison:

```text
ANTECIPADO
PADRÃO
CONFIRMADO
```

Questions:
- Does ANTECIPADO materially reduce useful latency?
- What cancellation/churn cost does it introduce?
- Does CONFIRMADO materially reduce false starts or merely arrive after too much of the move?
- Does PADRÃO remain the best single automatic default?

If the profiles do not create meaningful coherent tradeoffs, **do not ship profiles**.

## 10. HTF/horizon study

Test candidate context mappings for:
- 4H;
- 1D;
- 3D;
- 1W;
- 1M.

Questions:
- Does a true higher timeframe improve regime-reversal stability?
- Does monthly context make weekly signals unusably late?
- Is a two-layer context (structural + macro) more useful than one HTF?
- Can 15m/1H act as precision execution while preserving a 4H/1D thesis?

Do not force one mapping across every horizon if evidence supports a deterministic horizon-aware mapping.

## 11. Cross-asset robustness

After candidate logic stabilizes on BTC:

Run ETH and AVAX with **identical defaults**.

A candidate that requires immediate per-asset retuning fails the first robustness screen unless there is a strong structural reason.

## 12. UI evidence

The direct panel must be tested for:
- decision comprehension in seconds;
- no duplicated internal semantics;
- no visible metric that requires memorizing engine codes;
- no more clutter than 0.1;
- Market Map / Execution semantic parity;
- before/after reload stability.

## 13. Promotion gate

0.2 may promote only if:

- at least one new opportunity family adds material coverage without pathological churn;
- pullback/retest quality is preserved;
- latency claims are measured;
- profile claims, if any, are supported by explicit tradeoffs;
- 4H/1D behavior is strong enough for primary use;
- 3D/1W/1M behavior is coherent;
- 15m/1H remains useful for short/precision execution;
- Pine compile/static parity are green;
- TradingView reload parity is green;
- `docs/GUIA_DO_OPERADOR.md` is complete in Portuguese.

## 14. Anti-overfitting rule

Do not:
- tune to one screenshot;
- maximize one aggregate hit rate;
- optimize one coin and copy thresholds blindly;
- choose a profile because it "looks faster";
- turn outcome diagnostics into a fake probability.

Every accepted refinement must name the semantic problem it solves.

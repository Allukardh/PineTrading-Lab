# Execution historical evidence — component + Market Map integration gate

**Date:** 2026-09-24  
**Issue:** #11  
**PR:** #12  
**Status:** evidence gate complete; production Pine not yet created

## Evidence identity

Primary run: 36080621108

Research head: 90a46c209bd3f2aeeae969a6b00490a7687d08de

Static integrity: 36080620994 — **PASS**

BTC artifact: execution-btc-evidence (artifact id 10841947391)

BTC evidence hashes:
- JSON SHA-256: 5c33b66b2be75d492044b705e11634c6c830eda43758018303d5500a7f032e0d
- Markdown SHA-256: 882b2165dfc19668c456844f42af62dac895373e795618b67bb73f09447682cf

Cross-asset artifacts:
- ETHUSDT: artifact id 10841503174
- AVAXUSDT: artifact id 10841148565

All datasets were canonical SHA-256-verified Binance SPOT Parquets from the accepted market-data lab.

Research defaults remained unchanged at manifests/execution-research-defaults-v1.json.
Suite semantic contract remained manifests/suite-semantics-v1.json.

No threshold was tuned from the evidence.

---

## MTE-A — decision: KEEP

Observed across BTC/ETH/AVAX and 15m/1h/4h/1d/3d/1w:
- TURN occupancy is consistently about **29–31%**;
- NEUTRAL is roughly **5–8%**;
- state changes are about **32–38 per 100 ready bars**;
- TURN median dwell is typically **2 bars**, occasionally 3 on higher TF;
- TURN direction reversals inside 1–3 bars are extremely rare;
- median TURN-to-zero-cross lead is about **4 bars** on primary TFs;
- only roughly 31–40% of TURN episodes reach a signed zero-cross before the original direction resumes.

Interpretation:

TURN means early counter-acceleration / preparation evidence. It must not be presented as a guaranteed reversal or directional confirmation by itself.

No occupancy, chatter or cross-asset instability justifies changing EMA8/EMA21, ATR14, activity RMA20, neutral factor 0.15, turn factor 0.50 or turn floor 0.02.

**Decision: KEEP MTE-A unchanged.**

---

## RSE-A — decision: KEEP, with semantic lock

Component evidence:
- all semantic states are reachable;
- extreme states remain uncommon rather than unreachable;
- oversold recovery / overbought fade states occur consistently;
- confirmed HTF opposition blocks a meaningful minority of supportive local states, not almost everything and not almost nothing.

The pre-registered lifecycle diagnostic showed that recovery/fade states usually last only **1–2 bars** and more than 95% do not remain in that same semantic state until the center dead-band is crossed.

This initially looked like a possible pathology.

Accepted Market Map integration resolves the question.

On real MM-0 relevant locations, RSI is supportive about:
- **59.58%** on 15m;
- **59.59%** on 1h;
- **60.13%** on 4h;
- **54.98%** on 1d.

Recovery/fade states themselves represent roughly **7–10%** of relevant-location bars.

Therefore the 2-bar memory behaves as a **short transition tag**, while subsequent BULL/BEAR/NEUTRAL semantics carry the continuing oscillator state. It does not make ARMADO/CONFIRMA unreachable and is not evidence for extending memory merely to increase persistence.

No evidence justifies changing RSI14, 48–52 dead-band, 70/30, 80/20, minimum step 0.25 or the 2-bar memory.

**Decision: KEEP RSE-A unchanged.**

Semantic lock: RECOVERING/FADING is a short recent-zone transition semantic, not a promise that the label persists until RSI reaches the center band.

---

## PSE-A — decision: KEEP

Relative-volume occupancy is stable across BTC/ETH/AVAX and timeframes:
- contracted (<0.80) is common but not always-on;
- expanded (>=1.20) is consistently reachable;
- strong expansion (>=1.50) is meaningful but not rare to the point of uselessness.

The OHLC close-location pressure proxy was challenged against Binance validation-only taker-buy imbalance.

Primary BTC examples:
- Pearson correlation roughly **0.27–0.34** on 15m–1d;
- Spearman roughly **0.32–0.36**;
- sign agreement roughly **67–72%** on 15m–1d;
- agreement generally improves when relative volume or pressure magnitude is stronger.

ETH and AVAX show the same positive relationship rather than a BTC-only artifact.

This is not strong enough to relabel the proxy as true aggressor flow, but it is sufficiently related to real taker imbalance to retain incremental semantic value.

The production meaning remains strictly: candle-location directional pressure proxy — not real buy/sell volume and not market delta.

No evidence justifies changing EMA20 prior-confirmed volume baseline, 0.80 / 1.20 / 1.50 bands or pressure threshold 0.20.

**Decision: KEEP PSE-A unchanged.**

---

## Cross-engine redundancy — KEEP all three families

Unconditioned all-three alignment is only about **2–5%** depending on asset/timeframe.

Pairwise overlap shows:
- MTE + RSE co-occurs materially more often than all three;
- PSE removes a distinct subset rather than simply duplicating MTE/RSE;
- RSE contributes distinct recovery/exhaustion + HTF-context information.

No engine is redundant enough to remove at this gate.

---

## Accepted Market Map -> Execution integration

The accepted MM-0 offline kernel was wired through the canonical location bridge into the integrated Execution reference state machine.

BTC was used for the primary integration gate with tick=0.01.

### Location relevance

Relevant locations (APPROACHING / IN_CORRECTION / RETEST / RECLAIM) occupy approximately:
- 15m: **49.14%**
- 1h: **49.87%**
- 4h: **50.08%**
- 1d: **48.30%**
- 3d: **32.33%**
- 1w: **36.62%**

### Readiness reachability

BTC:
- 15m: PREP 17.58%, ARMED 8.76%, CONFIRMED 1,649 events, ALIGNED 5.41%
- 1h: PREP 17.88%, ARMED 8.96%, CONFIRMED 380 events, ALIGNED 5.32%
- 4h: PREP 18.04%, ARMED 8.76%, CONFIRMED 107 events, ALIGNED 5.48%
- 1d: PREP 22.41%, ARMED 5.21%, CONFIRMED 6 events, ALIGNED 1.36%
- 3d: 1 confirmation
- 1w: 0 confirmations in the small robustness sample

The primary 15m/1h/4h design matrix is clearly reachable.

### Confirmation location

Most intraday confirmations occur at RETEST:
- 15m: 1,427 / 1,649
- 1h: 319 / 380
- 4h: 85 / 107

This is not a target to optimize. It is a semantic observation consistent with Execution acting as a timing layer after structural interaction rather than firing everywhere inside a correction.

### Era spread

Confirm events are present across essentially every complete BTC calendar year in the primary intraday matrix.

Examples:
- 15m confirmations by year span 2017–2026 with 149–205 in each full year 2018–2025;
- 1h similarly spans every year;
- 4h similarly spans every year.

The candidate is not reachable only in one favored historical era.

---

## Strength semantics — KEEP

Integrated BTC primary TFs show approximately:
- NORMAL: **54–58%**
- FADING: **37–39%**
- EXHAUSTED: **5–7%**
- REACTION_RISK: rare globally, by design.

At DESTINATION_NEAR, REACTION_RISK becomes materially more relevant:
- 15m: **4.89%**
- 1h: **4.38%**
- 4h: **7.17%**
- 1d: **14.29%** (smaller sample)

This supports the intended distinction: generic deterioration is not automatically reaction risk; destination proximity + multiple deterioration families creates the stronger warning.

No strength-family threshold change is justified.

---

## Evidence decisions

| Candidate | Decision | Reason |
| --- | --- | --- |
| MTE-A | **KEEP** | stable occupancy/chatter/dwell across assets and TFs; TURN semantics validated as early counter-acceleration |
| RSE-A | **KEEP** | all states reachable; HTF context useful; short recovery/fade memory remains useful in real MM locations without blocking readiness |
| PSE-A | **KEEP** | stable relative-volume semantics and consistent positive relationship to validation-only Binance taker imbalance |
| Readiness state machine | **KEEP** | PREP/ARMED/CONFIRM/ALIGNED all reachable on primary TFs and across eras |
| Strength state machine | **KEEP** | not saturated; reaction risk concentrates appropriately near destination |

No candidate receives REFINE / REMOVE / INSUFFICIENT EVIDENCE at this gate.

---

## Production gate decision

The pre-registered historical evidence gate is **CLOSED**.

This authorizes the next engineering phase:
1. create production execution.pine as a clean-room implementation of the accepted semantic contract;
2. preserve the validated defaults unchanged initially;
3. generate/validate the same Execution semantic kernel into Market Map's embedded Decision Panel;
4. then run Pine compile/static and TradingView reload/UX parity.

This evidence does **not** establish profitability, expected return, win rate or an automated trading strategy.

# Market Map MM-0 — offline BTC historical evidence

**Date:** 2026-09-24  
**Candidate branch:** `feat/market-map-0.1.0-mm0`  
**Evidence kernel:** `tools/market_map_offline_core.py` + `tools/market_map_offline.py`  
**Audit contract:** Market Map Audit Schema v2  
**Status:** offline structural sanity PASS; market-usefulness/parity review remains open

## Purpose

Replace the blocked TradingView CSV transport with a deterministic research path over the accepted Binance historical-data lab, without changing MM-0 trading semantics or tuning parameters from the result.

The offline kernel emits the same Audit Schema v2 consumed by `tools/analyze_market_map_export.py`.

## Canonical data provenance

Source materialization run:

`36006762328`

Exact BTCUSDT production artifacts were downloaded from that run and SHA-256 verified before use.

| TF | rows | canonical SHA-256 |
| --- | ---: | --- |
| 15m | 316,414 | `cac347638b577b2bcfcd671f66a68af96edb49c614c4dc203d7dc8ea3fb48411` |
| 1h | 79,117 | `86f2f12b66979d2e0659b44b95b584ec5140050770acce58e6c4643c9b409776` |
| 4h | 19,794 | `93226923a88861cc56d11d82900801db7f64fbe89920c710843dc26673265e06` |
| 1d | 3,302 | `1788d075ad21091e279cb68ccfac79935149ca9c444a74dbc971bba00e15fdae` |
| 1w | 456 | `960de3600ea7ab8651ec2dbaa51d204e05fce19127eb53bb24fcd59dd010ac46` |

1W is used as confirmed HTF context for the 1D audit. The initial outcome matrix remains 15m / 1h / 4h / 1d.

## Reproducible evidence run

Workflow:

`.github/workflows/market-map-offline-evidence.yml`

Final accounting run:

`36039228914`

Evidence head:

`8f30bdb5618d2da3d5751e3de6402924f1321296`

Machine-readable artifact:

`mm0-evidence.json` — SHA-256 `70c0692d1a6fe8dfc01b02a0b2b844060e9aecfd619f094eaf4d98c72b34d08d`

Provenance artifact is deterministic across reruns:

`mm0-materialization.json` — SHA-256 `014accf26675eafb4ad733b87196a321a8de7a2129c21fa212cbb0ce0580cbd2`

Subsequent commit `74fe0ea7d15fbcdaf211c0b541c5fc66976b6f0d` adds only analyzer regression coverage; Pine compile and Static integrity both PASS there.

## Structural result

The offline matrix processed:

- 316,414 confirmed 15m rows
- 79,117 confirmed 1h rows
- 19,794 confirmed 4h rows
- 3,302 confirmed 1d rows

Across the four audits:

- theses: **45,562**
- first correction-zone touches: **32,458**
- destination outcomes: **5,408**
- invalidation outcomes: **1,039**
- ambiguous outcomes: **4,560**
- superseded/censored after touch: **21,448**
- still open at export end: **3**
- touches coincident with reclaim: **1,356**

Structural pathology checks:

**PASS — no pathology detected.**

The full touch accounting closes at exactly **100%**.

## Correct denominator — do not call 83.9% a win rate

Among only the **6,447 non-ambiguous resolved** cases, destination occurred first in **83.88%**.

That statistic is conditional on a small selected subset and is not a trading win rate.

Across **all 32,458 touched theses**, the honest accounting is:

- destination: **16.66%**
- invalidation: **3.20%**
- ambiguous OHLC ordering: **14.05%**
- superseded/censored by a newer thesis: **66.08%**
- open at export end: **0.01%**

Only **19.86%** of touched theses reached a non-ambiguous destination/invalidation resolution before replacement.

This is currently the most important historical finding.

## Timeframe pattern

| TF | touched | destination / all touches | invalidation / all touches | ambiguous | superseded/censored |
| --- | ---: | ---: | ---: | ---: | ---: |
| 15m | 24,258 | 16.05% | 3.38% | 13.38% | 67.19% |
| 1h | 6,306 | 17.70% | 2.81% | 15.30% | 64.18% |
| 4h | 1,626 | 19.93% | 2.46% | 17.65% | 59.90% |
| 1d | 268 | 27.99% | 0.75% | 23.51% | 47.76% |

The direction is descriptive only. No parameter should be changed to improve these percentages without a semantic reason.

## Model composition and ambiguity

Zone-touch models:

- ADAPT: 21,226
- LIVE/ADAPT: 11,174
- FIB: 34
- LIVE/FIB: 24

Adaptive models therefore dominate the mature historical sample.

A more important distinction appears in ambiguous outcome ordering:

- ADAPT: 215 ambiguous / 21,226 touches ≈ **1.0%**
- LIVE/ADAPT: 4,335 ambiguous / 11,174 touches ≈ **38.8%**
- FIB: 1 / 34
- LIVE/FIB: 9 / 24

This does **not** justify removing or retuning LIVE mapping yet.

It pre-registers the next discriminant:

> Inspect representative LIVE/ADAPT first-touch ambiguous cases and determine whether the high ambiguity is an honest consequence of developing-impulse timing + OHLC granularity or a semantic/identity defect in the LIVE thesis lifecycle.

## Invalidation-distance note

The analyzer can observe a negative signed close-to-invalidation distance on the confirmed invalidation bar.

That is compatible with Pine semantics:
- `invalidationBrokenNow` becomes true when the confirmed close crosses the invalidation;
- the current thesis becomes invalidated;
- destination/active correction geometry is suppressed;
- the audit invalidation series remains present while `correctionReady` is true.

The zone/invalidation geometry checks themselves reported zero pathologies.

## Known parity obligations

The offline engine is research evidence, not a replacement for Pine runtime authority.

Before promotion, targeted parity still must cover:
- pivot tie behavior;
- representative confirmed HTF `[1]` transitions;
- LIVE -> confirmed impulse identity continuity;
- representative LIVE/ADAPT ambiguous touch candles;
- confirmed invalidation lifecycle;
- final TradingView rendering/reload sanity.

TradingView CSV export is optional if account capability changes later; no plan upgrade is required.

## Decision

Do not tune correction ratios, ATR tolerances, pivot length, LIVE rules or target rules from this aggregate result.

The next gate is **lifecycle/parity diagnosis**, led by the high supersession share and model-specific LIVE ambiguity.

Only after that gate should the project decide whether MM-0 semantics need adjustment or whether these are honest censoring/observability characteristics of the map.


## 3D / 1W robustness extension

The Pine timeframe contract was verified before extending the offline matrix.

For chart timeframes above 1D, MM-0 uses:

`contextTf = timeframe.period`

Therefore:
- 3D uses current 3D state as its context rather than inventing a higher timeframe;
- 1W uses current 1W state as its context;
- PDH/PDL are disabled above 1D, matching `dayLevelsAllowed = chartSec <= tfDSec`;
- PWH/PWL remain available through 1W.

The offline kernel was extended to reproduce those rules explicitly and regression-test them.

Robustness workflow run:

`36039959727`

Evidence head:

`8b4390462d36e2219249b86f11813df0d77b3fcd`

Artifacts:
- `mm0-evidence.json` — SHA-256 `86591c85cf6b6a09d93a221ae7d3000ac1db1069a48af76ec76fe4ead9a90146`
- `mm0-materialization.json` — SHA-256 `edde04d3b3b99e444c07f9a14908dbe2058cb3db9f282cf875b93a50a741be5b`

Additional canonical source:
- 3D Parquet: 1,061 rows, SHA-256 `e4228da434e9131ae2353147181069d119bc0ef373ec4b93effc5c1dcf9a39d9`

Generated robustness audits:
- 3D audit SHA-256 `701b7a84ef69447eb8d004919d45d1cf589773a969ce2d11bec1c14cc48873f4`
- 1W audit SHA-256 `8adb84fb9e1676cf2014d43ce3fb5a2ca43709f884f06c9ed6fe1778fe7bbfef`

### 3D

- theses: 96
- touches: 63
- destination: 12
- invalidation: 2
- ambiguous: 7
- superseded/censored: 42
- open: 0
- structural pathologies: none

All-touch accounting:
- destination: 19.05%
- invalidation: 3.17%
- ambiguous: 11.11%
- superseded/censored: 66.67%
- resolved non-ambiguous: 22.22%

### 1W

- theses: 36
- touches: 29
- destination: 8
- invalidation: 0
- ambiguous: 7
- superseded/censored: 14
- open: 0
- structural pathologies: none

All-touch accounting:
- destination: 27.59%
- invalidation: 0.00%
- ambiguous: 24.14%
- superseded/censored: 48.28%
- resolved non-ambiguous: 27.59%

The 1W result has only **8 non-ambiguous resolved outcomes**. The analyzer correctly raises:

`small resolved sample (8)`

No statistical conclusion or parameter tuning is allowed from that weekly sample.

### Six-timeframe aggregate

Across 15m / 1h / 4h / 1d / 3d / 1w:

- theses: **45,694**
- touches: **32,550**
- destination outcomes: **5,428**
- invalidation outcomes: **1,041**
- non-ambiguous resolved: **6,469**
- ambiguous: **4,574**
- superseded/censored: **21,504**
- open: **3**
- outcome accounting: **100%**
- structural pathologies: **none**

All-touch accounting:
- destination: **16.68%**
- invalidation: **3.20%**
- ambiguous: **14.05%**
- superseded/censored: **66.06%**
- open: **0.01%**

The robustness extension therefore does not materially change the initial interpretation. It strengthens the structural sanity result while preserving the same lifecycle concern: most touched theses are replaced before a non-ambiguous destination/invalidation outcome.

## Next discriminant after robustness

No correction ratio, pivot length, ATR tolerance, LIVE rule or target rule is changed from these aggregates.

The next evidence gate remains:

1. isolate representative LIVE/ADAPT ambiguous first-touch candles;
2. isolate representative touched theses superseded before outcome;
3. determine whether those cases are honest consequences of developing-impulse timing / OHLC observability or a thesis-identity/lifecycle defect;
4. only if a semantic defect is demonstrated should MM-0 logic change;
5. then request a small, targeted TradingView parity set for the specific states that cannot be proven offline.



## Lifecycle diagnosis — ambiguity decomposition and audit correction

The lifecycle gate was expanded before any MM-0 parameter tuning.

Diagnostic tooling first decomposed the previous 4,574 ambiguous outcomes by timing and geometry.

Before the correction:
- same-touch ambiguity: **4,571 / 4,574**
- post-touch both-bounds ambiguity: **3 / 4,574**
- same-touch cases whose open/geometry proved zone-before-target: **2,553**
- frozen targets already inside the current correction zone: **769**
- frozen targets already behind the current correction zone: **108**
- genuinely unordered same-touch target cases: **1,108**

The inside/behind cases exposed a real **audit-semantic defect** rather than a Market Map target/display defect.

At first correction-zone touch, the historical telemetry froze the prior bar's destination whenever direction was unchanged. Under LIVE/adaptive geometry, that prior liquidity target can become stale relative to the current correction zone. The UI/current destination may already be valid while the audit still evaluates an obsolete prior target.

The audit contract was corrected in Pine and the offline kernel:

1. a previous target is frozen only if it remains directionally **beyond the current correction zone**;
2. otherwise the current destination is used only if it is beyond the zone;
3. if neither is valid, the audit target is left absent rather than fabricating a post-correction destination;
4. a same-touch destination is no longer automatically ambiguous when candle open + level topology prove that the correction zone had to be touched before the destination;
5. genuinely unordered same-touch cases remain ambiguous;
6. destination + invalidation on the same candle remains ambiguous.

No correction ratio, pivot length, ATR tolerance, LIVE impulse rule, destination ladder rule or user-facing trading semantic was tuned.

### Corrected six-timeframe evidence

Offline evidence run:

`36068967348`

Evidence commit:

`151518a5965fd07cd1051917a355e1df1f29164c`

Machine-readable evidence artifact:

`mm0-evidence.json` — SHA-256 `5c51309699a39dd864f971794296c0a65baa2d093f94c2e735f859a308d95f13`

Pine audit-semantic parity fix:

`26e7e821706ecdb687d9b6d23e53b70632ace8b2`

Pine compile:

`36068992937` — **PASS**

Final repository/static gate after updating regression invariants:

`36069062578` — **PASS**

Corrected aggregate:

- theses: **45,694** unchanged
- first correction-zone touches: **32,550** unchanged
- destination outcomes: **8,208**
- invalidation outcomes: **1,055**
- non-ambiguous resolved: **9,263**
- ambiguous: **1,121**
- superseded/censored: **22,163**
- open: **3**
- touch accounting: **100%**
- structural pathologies: **none**

All-touch accounting now becomes:

- destination: **25.22%**
- invalidation: **3.24%**
- ambiguous: **3.44%**
- superseded/censored: **68.09%**
- open: **0.01%**

The ambiguity reduction from **4,574 -> 1,121** is not performance tuning. It removes:
- audit targets that were no longer valid post-correction destinations; and
- cases whose event order is logically inferable from the candle open + zone/target topology.

The remaining same-touch ambiguity consists primarily of **1,108 genuinely unordered target cases**, plus three target-first-at-open cases and a handful of rows where the visible exported fields cannot independently reconstruct the original reason. Only **3** post-touch both-boundary ambiguity cases remain.

### Supersession diagnosis

After removing the audit ambiguity defect, supersession remains the dominant lifecycle outcome (**68.09% of touched theses**), but representative cases do not support a thesis-identity bug.

Same-direction supersessions remain common because a new thesis uses a **new impulse origin**. The thesis key is already stable across LIVE -> confirmed-terminal-pivot evolution, so terminal confirmation does not create a new thesis by itself.

Corrected transition counts:

- LONG -> LONG: **8,533**
- SHORT -> SHORT: **7,096**
- LONG -> SHORT: **3,233**
- SHORT -> LONG: **3,301**

Supersession speed:

- <=3 bars after touch: **5,998**
- 4–10 bars: **10,402**
- >10 bars: **5,763**

Representative same-direction cases show either:
- a genuinely new structural impulse origin; or
- a period in which map/correction geometry becomes inactive before a later same-direction thesis appears.

Therefore no thesis-identity or lifecycle rule is changed from aggregate supersession percentages.

### Lifecycle-gate decision

The proven defect was in **historical audit target freezing / ambiguity classification**, and it is corrected.

The available evidence does **not** justify changing MM-0 trading semantics or tuning the engine.

The next gate can move from aggregate lifecycle diagnosis to a **small targeted Pine/TradingView parity check** focused on the audit states that cannot be proven from the offline kernel alone.

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

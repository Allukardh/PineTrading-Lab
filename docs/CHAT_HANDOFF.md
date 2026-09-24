# PineTrading-Lab — Chat Continuation Checkpoint

**Status:** CANONICAL CHAT HANDOFF  
**Date:** 2026-09-24 — continuity protocol v2  
**Repository:** `Allukardh/PineTrading-Lab`  
**Accepted main baseline:** SignalGate Dashboard 0.1.0  
**Primary active candidate:** Market Map MM-0  
**Parallel research:** Execution architecture  
**Rule:** do not reconstruct the project from old chat transcripts first.

## 0. Durable write-ahead checkpoint — schema v2

**Checkpoint state:** STABLE  
**Product work currently in flight:** none  
**Continuity protocol:** WRITE-AHEAD + COMMIT-RESULT  
**Continuity hardening promoted:** PR #16 → `3f9e5a73d3aa94c9bfae6d984f1c25a83e60bf42`  
**Reusable continuity standard:** `docs/PROJECT_CONTINUITY_STANDARD.md`  
**Operator evidence required right now:** none

### Last verified active refs

```text
PR #10  feat/market-map-0.1.0-mm0
head    7d77fa09f9309c5b419d2723553d1b8537300352

PR #12  research/execution-engine-design
head    bfd4cad9c35eddf5acdd4df2bf52ba47bddba2f0
```

### Durable result of the completed MM-0 lifecycle block

The lifecycle investigation found a real defect in **historical audit semantics**, not evidence that the visible Market Map destination/correction engine should be retuned.

The audit had two problems:

1. on first correction-zone touch it could freeze the previous bar's destination even after LIVE/adaptive geometry moved that level inside or behind the current correction zone;
2. it treated every same-touch destination as ambiguous even when candle open + zone/target topology proved the zone had to be touched before the target.

Pine telemetry and the offline kernel were corrected in parity.

Key evidence:
- corrected six-timeframe offline run: `36068967348` — PASS;
- evidence commit: `151518a5965fd07cd1051917a355e1df1f29164c`;
- Pine audit-parity fix: `26e7e821706ecdb687d9b6d23e53b70632ace8b2`;
- Pine compile: `36068992937` — PASS;
- final branch Static integrity: `36069246767` — PASS;
- structural pathologies: none;
- touch accounting: 100%.

Corrected six-timeframe accounting:
- theses: 45,694;
- touches: 32,550;
- destination outcomes: 8,208;
- invalidation outcomes: 1,055;
- non-ambiguous resolved: 9,263;
- ambiguous: 1,121;
- superseded/censored: 22,163;
- open: 3.

All-touch shares:
- destination: 25.22%;
- invalidation: 3.24%;
- ambiguous: 3.44%;
- superseded/censored: 68.09%;
- open: 0.01%.

The old 4,574 ambiguity count was materially overstated:
- 2,553 same-touch cases were safely zone-first-target by open/topology;
- 769 used a frozen target inside the current zone;
- 108 used a frozen target behind the current zone;
- after correction, 1,108 genuinely unordered same-touch target cases remain, plus only 3 post-touch both-boundary cases and a small unreconstructible remainder.

Representative supersession cases do **not** demonstrate a LIVE→confirmed identity bug. Thesis identity remains anchored to impulse origin + direction; same-direction replacement generally reflects a new structural origin or a later reactivation after map geometry became inactive.

Decision:
- do not tune correction ratios, pivot length, ATR tolerances, LIVE rules or destination rules from these lifecycle percentages;
- no product/trading semantic change is justified from supersession aggregates;
- the proven audit defect is fixed.

### Exact next atomic product action

Before asking the operator for any new TradingView evidence:

1. reconcile PR #10 with the current `main` so the candidate contains the promoted data/continuity state without losing its unmerged Market Map work;
2. verify merge/static/compile integrity after reconciliation;
3. define the **smallest targeted TradingView visual/reload parity set** still needed for MM-0 promotion;
4. only then ask the operator for that batched evidence.

Do not reopen historical-data plumbing and do not start production `execution.pine`.

### Recovery algorithm

If interruption occurs after the next PREPARED checkpoint:

1. compare actual PR #10 / PR #12 heads with the refs recorded here;
2. inspect only commits/runs/artifacts newer than the checkpoint;
3. if refs did not move, execute the recorded atomic action;
4. if refs moved, reconstruct completed work from the GitHub delta and continue;
5. old chat transcripts are fallback only for an unresolved contradiction that canonical project evidence cannot explain.

---

## 1. Resume in this exact order

```text
README.md
docs/CANONICAL_STATE.md
docs/CONTINUITY_LOG.md
docs/CHAT_HANDOFF.md
PR #10 / feat/market-map-0.1.0-mm0
PR #12 / research/execution-engine-design
```

Then read only the detailed worklogs/design files relevant to the active task.

GitHub is canonical.

`main` describes accepted/promoted truth. PR #10 and PR #12 contain unmerged candidate/research truth.

---

## 2. Operator interaction / focus

The operator is satisfied with the current methodology and explicitly wants it preserved across chats.

Maintain:

- broad assistant engineering freedom;
- professional GitHub-first workflow;
- durable but proportionate documentation of rationale/decisions, without narrating every micro-step;
- minimal user-facing settings;
- no legacy UI preservation merely from habit;
- no repeated trivial TradingView tests;
- batch operator validation into meaningful gates;
- distinguish compile/static PASS from market/TradingView PASS;
- keep moving while user evidence is not yet needed;
- when the operator says “continue”, advance autonomously to the next meaningful evidence boundary;
- keep product/trading usefulness ahead of process ceremony;
- do not lose project focus by over-discussing continuity itself.

If a future chat begins with a request to continue this project, resume engineering from the checkpoint below rather than re-planning the suite.

---

## 3. Accepted state on main

`main` at continuity creation:

```text
9d47521f9c225272606a1357f6f209dfe1389bec
```

Accepted product baseline:
- SignalGate Dashboard 0.1.0

Accepted high-level suite direction:
- Market Map
- Execution
- Decision Panel

Do not treat unmerged MM-0/Execution research as already promoted to main.

---

## 4. Market Map MM-0 — ACTIVE PRODUCT GATE

**Branch:** `feat/market-map-0.1.0-mm0`  
**PR:** #10 — Market Map 0.1.0 MM-0: integrated structure, liquidity and correction map  
**Head at this checkpoint:** `c8912c14a99cf10650886891425b5776a3924178`  
**PR state:** Draft / mergeable

Latest automated evidence at this checkpoint:

```text
Pine compile                 PASS  run 36040517753
Static integrity             PASS  run 36040517726
BTC 6-timeframe offline gate PASS  run 36039959727
```

The offline gate uses exact SHA-256-verified BTCUSDT production Parquets promoted by PR #15.

After the prior handoff checkpoint, PR #10 added lifecycle-diagnostic tooling and tests at `7909d3a...` and `c8912c1...`. These commits diagnose ambiguity/supersession behavior; they do not change Market Map Pine trading semantics.

### Current MM-0 candidate semantics

- EMA 21/50/200 trend layer
- automatic confirmed HTF context
- semantic regime vs local structure conflict handling
- confirmed pivots / HH-HL / LH-LL
- BOS / CHoCH / retest / fakeout
- structural liquidity pools
- PDH/PDL/PWH/PWL
- confirmed sweep/reclaim phase
- adaptive correction depth from recent completed pullbacks
- Fibonacci fallback/core reference
- one primary visible correction zone
- LIVE developing impulse
- impulse VWAP + clean-room VNode acceptance
- directional DESTINO = nearest + next distinct intact liquidity
- ATINGIDO event
- structural invalidation lifecycle
- invalidated thesis suppresses stale correction/destination
- one semantic panel
- no Compact/Full variants
- no mandatory profile
- Data-Window-only audit schema v2
- offline CSV analyzer
- reload-parity comparator

### MM-0 promotion blockers

The primary offline historical gate is now complete.

Completed:
1. deterministic Audit Schema v2 offline kernel;
2. exact-production BTCUSDT historical matrix on 15m / 1H / 4H / 1D;
3. 3D / 1W robustness using Pine's self-context rule above 1D;
4. full touch-outcome accounting with no structural pathology.

Six-timeframe result:
- 45,694 theses;
- 32,550 first correction-zone touches;
- 5,428 destination outcomes;
- 1,041 invalidation outcomes;
- 4,574 ambiguous OHLC-order outcomes;
- 21,504 superseded/censored touched theses;
- 3 open at export end;
- touch accounting = 100%;
- structural pathology gate = PASS.

Interpretation lock:
- the ~83.9% destination share among non-ambiguous resolved cases is **not** a win rate;
- only ~19.87% of touched theses resolve destination/invalidation non-ambiguously before replacement;
- ~66.06% of touched theses are superseded/censored;
- LIVE/ADAPT has much higher same-candle OHLC ambiguity than confirmed ADAPT and must be diagnosed before any tuning.

Remaining promotion work:
1. isolate representative LIVE/ADAPT ambiguous first-touch cases;
2. isolate representative touched theses superseded before outcome;
3. determine whether those are honest developing-impulse/OHLC observability effects or a thesis-lifecycle/identity defect;
4. only if a semantic defect is proven, change MM-0 logic;
5. then perform a small targeted TradingView visual/reload parity set for the representative states that cannot be proven offline.

Do not tune correction ratios, pivot length, ATR tolerances, LIVE rules or target rules from the aggregate percentages.

### Next operator evidence request

**None right now.**

The assistant should first finish the offline lifecycle/parity diagnosis using the already accepted datasets and the MM-0 candidate.

Only after representative cases are isolated should the operator be asked for a small number of targeted TradingView screenshots/reload checks.

Do not ask for historical CSV export, a TradingView plan upgrade, or manual Binance downloads.

### Important MM-0 files on PR #10

```text
src/core/market-map.pine
docs/CANONICAL_STATE.md
docs/TRADING_SYSTEM_DESIGN.md
docs/testing/MARKET_MAP_MM0_VALIDATION.md
docs/worklog/2026-09-23-market-map-mm0.md
docs/worklog/2026-09-24-market-map-offline-evidence.md
tools/analyze_market_map_export.py
tools/test_analyze_market_map_export.py
tools/market_map_offline_core.py
tools/market_map_offline.py
tools/test_market_map_offline.py
.github/workflows/market-map-offline-evidence.yml
```

---

## 5. Execution — PARALLEL RESEARCH ONLY

**Branch:** `research/execution-engine-design`  
**PR:** #12 — Research: Execution Engine architecture  
**Head at this checkpoint:** `bfd4cad9c35eddf5acdd4df2bf52ba47bddba2f0`  
**PR state:** Draft / mergeable  
**Production `execution.pine`: NOT CREATED intentionally**

Latest automated evidence at the current Execution research head:

```text
Static integrity PASS  run 35949566301
```

### Candidate runtime topology

Three logical layers, two TradingView indicators:

```text
Market Map
  overlay + single suite Decision Panel

Execution
  lower pane
```

A standalone third Decision Panel indicator is not part of the current candidate topology.

### Candidate Execution semantics

Readiness:

```text
AGUARDAR
 -> PREPARANDO LONG/SHORT
 -> ARMADO LONG/SHORT
 -> CONFIRMA LONG/SHORT   [one-bar confirmed event]
 -> ALINHADO LONG/SHORT
```

Strength:

```text
NORMAL
PERDENDO FORÇA
EXAUSTÃO
RISCO DE REAÇÃO
```

Readiness and strength are separate axes.

### Candidate evidence engines

**MTE-A — Momentum Turn**
- core = (EMA8(HLC3) - EMA21(HLC3)) / ATR14
- activity RMA20
- neutral factor 0.15
- turn factor 0.50
- turn floor 0.02
- numeric accel epsilon 1e-9
- synthetic scale/translation/trend/reversal tests PASS

**RSE-A — RSI State**
- RSI 14
- center dead-band 48–52
- 70/30 standard zones
- 80/20 extremes
- minimum step 0.25
- 2 confirmed-bar recovery/fade memory
- separate confirmed HTF RSI context direction -1/0/+1

**PSE-A — Participation**
- prior confirmed EMA20 volume baseline
- <0.80 WEAK
- >=1.20 expanded
- >=1.50 strong diagnostic
- close-location pressure proxy
- pressure threshold 0.20
- Binance taker-buy imbalance reserved for offline validation only

All numeric values are research candidates, not operator settings and not yet production-canonical.

### Market Map -> Execution bridge candidate

Location vocabulary:

```text
OUTSIDE
APPROACHING
IN_CORRECTION
RETEST
RECLAIM
DESTINATION_NEAR
```

Initial internal defaults:
- APPROACHING <= 0.50 ATR from valid correction envelope
- RETEST/RECLAIM memory = 3 confirmed chart bars

Priority:

```text
RECLAIM
> RETEST
> IN_CORRECTION
> APPROACHING
> DESTINATION_NEAR
> OUTSIDE
```

### Truth/timing invariants

- HTF state confirmed
- actionable CONFIRMA is chart-close confirmed
- historical buy/sell split is only a candle-pressure proxy
- realtime `varip` delta is optional live annotation
- realtime-only delta cannot create/cancel/alter reload-safe CONFIRMA
- no fabricated probability percentage

### Executable design artifacts

```text
docs/design/EXECUTION_ENGINE_DESIGN.md
docs/design/EXECUTION_STATE_MACHINE.md
docs/design/EXECUTION_DEFAULTS.md
docs/design/MOMENTUM_TURN_ENGINE.md
docs/design/RSI_STATE_ENGINE.md
docs/design/PARTICIPATION_ENGINE.md
docs/design/MARKET_MAP_EXECUTION_BRIDGE.md
docs/design/SUITE_INTEGRATION_CONTRACT.md
docs/design/RUNTIME_TOPOLOGY.md
docs/testing/EXECUTION_VALIDATION_PLAN.md
docs/testing/EXECUTION_EVIDENCE_RESEARCH_PLAN.md

tools/execution_state_reference.py
tools/test_execution_state_reference.py
tools/market_execution_bridge_reference.py
tools/test_market_execution_bridge_reference.py
tools/momentum_turn_reference.py
tools/test_momentum_turn_reference.py
tools/rsi_state_reference.py
tools/test_rsi_state_reference.py
tools/participation_reference.py
tools/test_participation_reference.py
tools/check_suite_semantics.py
tools/check_execution_research_defaults.py

manifests/suite-semantics-v1.json
manifests/execution-research-defaults-v1.json
```

### Exact next independent Execution task

The three reload-safe evidence-engine candidates now exist and pass reference tests.

Issue #14 has landed, so the evidence gate is now active:

> Keep production `execution.pine` blocked. Run the pre-registered historical tests for MTE-A / RSE-A / PSE-A against the accepted Binance datasets before numerically retuning or promoting any candidate formula.

The historical research questions are pre-registered in:

`docs/testing/EXECUTION_EVIDENCE_RESEARCH_PLAN.md`

Historical evidence now takes priority over further formula invention. Non-numeric UX/shared-kernel work remains secondary and must not bypass the evidence gate.

---

## 6. Historical market-data infrastructure — PROMOTED

Issue #14 and PR #15 are complete.

**Issue:** #14 — closed  
**PR:** #15 — merged  
**Branch head promoted:** `64a9fc0a4ea05299b78253563b3b20874e8a7256`  
**Merge commit:** `bf132cf715aade528aa89b1b327566a964015609`

Accepted scope:
- official Binance Public Data SPOT monthly klines;
- 15 symbols;
- 15m / 1h / 4h / 1d / 3d / 1w;
- checksum-first/resumable source acquisition;
- native timestamp provenance + deterministic normalization;
- duplicate/gap/off-grid/close-time findings without fabricated candles;
- consolidated Zstd Parquet datasets;
- deterministic manifests/reports/hashes/idempotency;
- Google Drive as the large dataset store;
- GitHub for code/config/schema/tests/docs/small reports.

Production inventory:
- 15 symbols / 90 datasets;
- 4,849,829 candles;
- 7,503 available official checksums verified;
- 0 checksum mismatches;
- 1 exact AVAXUSDT duplicate deterministically deduplicated and reported.

Final promotion gate:
- Market data pipeline: PASS — 21/21 tests;
- Static integrity: PASS;
- P1 timestamp-transition review addressed and regression-tested;
- P2 missing-archive idempotency review addressed and regression-tested.

Primary consumer paths:
- `configs/binance-spot-research-universe.json`
- `docs/data/BINANCE_MARKET_DATA_PIPELINE.md`
- `docs/data/GOOGLE_DRIVE_LAYOUT.md`
- `manifests/binance-spot-btcusdt.production-2026-09-24.json`
- `manifests/binance-spot-research-universe.production-2026-09-24.json`
- `reports/binance-spot-btcusdt-materialization-2026-09-24.md`
- `reports/binance-spot-research-universe-materialization-2026-09-24.md`

Do not reopen downloader/infrastructure design unless a concrete validation requirement exposes a real defect. The next use of this work is historical evidence for Market Map and Execution.

---

## 7. Do not resurrect

Without new evidence, do not return to:

- six final independent indicators;
- legacy MA 6x reproduction as a requirement;
- Compact/Full panels;
- Clean/Standard/Detailed ceremony as a requirement;
- four manual RSI timeframe rows;
- RAW/VI production selector;
- dozens of thresholds;
- arbitrary probability/score;
- POC/profile engine in MM-0 without demonstrated incremental value;
- `input.source()` integration plumbing as required user setup;
- realtime delta as historical truth;
- third mandatory Decision Panel indicator.

---

## 8. If this chat dies during the MM-0 lifecycle/parity gate

Resume like this:

1. verify PR #10 and PR #12 heads/status;
2. read any commits newer than the SHAs recorded above;
3. treat PR #15 / Issue #14 infrastructure as accepted `main` state;
4. treat the six-timeframe MM-0 structural historical gate as completed candidate evidence, not promoted product truth;
5. continue the LIVE/ADAPT ambiguity + superseded-thesis lifecycle diagnosis before any numeric tuning;
6. only after representative cases are isolated, request a small targeted TradingView parity set if still needed;
7. run the pre-registered Execution evidence tests before retuning MTE-A / RSE-A / PSE-A;
8. do not create production Execution Pine until MM-0 and the evidence candidates have enough historical validation;
9. update this handoff whenever the exact next discriminant changes.

The project should continue from here without requiring the operator to re-explain the methodology, product goal or prior decisions.

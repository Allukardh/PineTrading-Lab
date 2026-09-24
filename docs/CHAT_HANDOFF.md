# PineTrading-Lab — Chat Continuation Checkpoint

**Status:** CANONICAL CHAT HANDOFF  
**Date:** 2026-09-24 14:39 BRT  
**Repository:** `Allukardh/PineTrading-Lab`  
**Accepted main baseline:** SignalGate Dashboard 0.1.0  
**Primary active candidate:** Market Map MM-0  
**Parallel research:** Execution architecture  
**Rule:** do not reconstruct the project from old chat transcripts first.

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
- aggressive documentation of rationale/decisions;
- minimal user-facing settings;
- no legacy UI preservation merely from habit;
- no repeated trivial TradingView tests;
- batch operator validation into meaningful gates;
- distinguish compile/static PASS from market/TradingView PASS;
- keep moving while user evidence is not yet needed;
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
**Head at this checkpoint:** `317e8c6c5a0a2afbe1f8efa2e20eb3bd377d9359`  
**PR state:** Draft / mergeable

Latest automated evidence at this checkpoint:

```text
Pine compile     PASS  run 35938558117
Static integrity PASS  run 35938558111
```

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

The operator uses TradingView Essential, which does **not** allow the required CSV export workflow without upgrading. Do not ask the operator to buy Premium merely for validation.

Revised evidence path:

1. final TradingView visual sanity with current DESTINO / invalidation / sweep-reclaim semantics;
2. historical offline sanity using official Binance BTCUSDT data from delegated Issue #14:
   - 15m
   - 1H
   - 4H
   - 1D
   - 3D / 1W as higher-timeframe robustness where useful
3. implement/validate a deterministic offline Market Map equivalent or audit kernel against the Pine semantics;
4. targeted TradingView reload/visual parity on representative confirmed states instead of full-history CSV parity.

The existing TradingView CSV audit/analyzer remains useful infrastructure if export access becomes available later, but it is no longer the primary promotion path.

### Next operator evidence request

None right now.

The Binance historical-data infrastructure is now promoted on `main` via PR #15 / Issue #14.

Next:
- consume the canonical production manifests/reports and Drive datasets;
- build/validate the deterministic offline Market Map audit kernel against MM-0 semantics;
- run historical sanity on BTCUSDT 15m / 1H / 4H / 1D first, then use 3D / 1W for higher-timeframe robustness where useful;
- only after offline evidence identifies representative states, ask for a small number of targeted TradingView screenshots/reload checks if Pine/runtime parity still needs confirmation.

Do not ask the operator for thousands of Binance files or a TradingView plan upgrade.

### Important MM-0 files on PR #10

```text
src/core/market-map.pine
docs/CANONICAL_STATE.md
docs/TRADING_SYSTEM_DESIGN.md
docs/testing/MARKET_MAP_MM0_VALIDATION.md
docs/worklog/2026-09-23-market-map-mm0.md
tools/analyze_market_map_export.py
tools/test_analyze_market_map_export.py
```

---

## 5. Execution — PARALLEL RESEARCH ONLY

**Branch:** `research/execution-engine-design`  
**PR:** #12 — Research: Execution Engine architecture  
**Head at this checkpoint:** `cb7beeedab3ce59451c788af9c61c77d86ac276e`  
**PR state:** Draft / mergeable  
**Production `execution.pine`: NOT CREATED intentionally**

Latest automated evidence:

```text
Integrated Execution research CI
PASS  run 35948868686
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

## 8. If this chat dies during the offline evidence gate

Resume like this:

1. verify PR #10 and PR #12 heads/status;
2. read any commits newer than the SHAs recorded above;
3. treat PR #15 / Issue #14 infrastructure as accepted `main` state;
4. prioritize offline MM-0 historical validation using the accepted Binance production datasets;
5. run the pre-registered Execution evidence tests before retuning MTE-A / RSE-A / PSE-A;
6. do not create production Execution Pine until MM-0 and the evidence candidates have enough historical validation;
7. update this handoff whenever the exact next discriminant changes.

The project should continue from here without requiring the operator to re-explain the methodology, product goal or prior decisions.

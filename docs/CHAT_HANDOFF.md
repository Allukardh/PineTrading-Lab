# PineTrading-Lab — Chat Continuation Checkpoint

**Status:** CANONICAL CHAT HANDOFF  
**Date:** 2026-09-23 21:47 BRT  
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

These are real TradingView gates, not code chores:

1. final visual sanity with current DESTINO / invalidation / sweep-reclaim semantics;
2. historical CSV sanity on BTCUSDT:
   - 15m
   - 1H
   - 4H
   - 1D
3. confirmed-history reload parity.

### Next operator evidence request

When the operator is ready, obtain **five CSV exports** from the current MM-0 candidate:

```text
BTCUSDT 15m
BTCUSDT 1H
BTCUSDT 4H
BTCUSDT 1D
one second export of any one timeframe after reload
```

The exact same candidate/version should be used for all five.

The assistant then runs the repository analyzer and decides whether MM-0:
- passes;
- needs semantic adjustment;
- needs correction-engine/default adjustment.

Do not ask for screenshots/CSV again before there is a meaningful reason.

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
**Head at this checkpoint:** `663277d35cddefcfb02e1e4fa289d9359a394cbb`  
**PR state:** Draft / mergeable  
**Production `execution.pine`: NOT CREATED intentionally**

Latest automated evidence:

```text
Static integrity + semantic/reference tests
PASS  run 35940853153
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

### Candidate engine-owned defaults

- RSI 14
- center dead-band 48–52
- exhaustion 70/30
- extended exhaustion 80/20
- volume baseline EMA 20
- contracted participation < 0.80x
- expanded participation >= 1.20x
- strong expansion >= 1.50x
- no normal user threshold tuning

The exact clean-room Momentum Turn numeric formula is intentionally not frozen yet.

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
docs/design/MARKET_MAP_EXECUTION_BRIDGE.md
docs/design/SUITE_INTEGRATION_CONTRACT.md
docs/design/RUNTIME_TOPOLOGY.md
docs/testing/EXECUTION_VALIDATION_PLAN.md

tools/execution_state_reference.py
tools/test_execution_state_reference.py
tools/market_execution_bridge_reference.py
tools/test_market_execution_bridge_reference.py
tools/check_suite_semantics.py
manifests/suite-semantics-v1.json
```

### Exact next independent Execution task

Until MM-0 real-chart evidence arrives:

> Research and define the clean-room **Momentum Turn Engine** candidate without creating production `execution.pine`.

Use legacy Moving Average Shift and relevant donor scripts as evidence, not authority.

Do not freeze old SMA40 / osc15 / percentile500 / 97.5 / smooth10 values merely because they existed.

The goal is a normalized momentum-turn formula that:
- behaves comparably across BTC/ETH/AVAX;
- exposes turn / acceleration / deceleration;
- has honest warmup;
- has minimal/no operator tuning;
- can later be validated on BTC 15m/1H/4H.

---

## 6. Delegated market-data infrastructure

A separate chat/thread may own the historical data plumbing so the main Pine engineering thread remains focused.

**Tracker:** Issue #14 — `Infra: Binance historical market-data pipeline + Google Drive dataset store`

Expected branch:

`infra/binance-market-data`

Scope:
- official Binance public spot klines
- BTCUSDT first
- 15m / 1h / 4h / 1d / 3d / 1w
- monthly archives preferred
- automated download/checksum/normalization/gap detection
- consolidated Parquet outputs
- Google Drive for large/raw/consolidated data
- GitHub only for code/manifests/tests/docs/reports

The delegated thread must not modify Market Map/Execution semantics.

If this main chat is active while Issue #14 is being handled elsewhere:
- continue Momentum Turn / Execution research here
- consume the data-pipeline PR/artifacts only when they are ready
- do not duplicate the downloader work in this thread

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

## 8. If this chat dies before the CSV gate

Resume like this:

1. verify PR #10 and PR #12 heads/status;
2. read any commits newer than the SHAs recorded above;
3. if the operator has brought the requested CSVs, prioritize MM-0 historical/reload validation;
4. otherwise continue Momentum Turn research on PR #12;
5. do not create production Execution Pine until the MM-0 interface/contract is stable enough;
6. update this handoff whenever the exact next discriminant changes.

The project should continue from here without requiring the operator to re-explain the methodology, product goal or prior decisions.

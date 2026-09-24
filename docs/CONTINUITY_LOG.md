# PineTrading-Lab — Continuous Engineering Context

> Permanent, incremental continuity log for the PineTrading-Lab project.
>
> This file exists so a future ChatGPT instance can reconstruct **why the project is in its current state and how the operator expects the work to be conducted**, not merely read the latest code.

## 1. Resume order after a chat interruption

Do **not** start by rereading old chat transcripts.

Read in this order:

1. `README.md` — project identity and repository rules.
2. `docs/CANONICAL_STATE.md` — accepted/promoted truth on `main`.
3. `docs/CONTINUITY_LOG.md` — causal history, product rationale and locked interaction methodology.
4. `docs/CHAT_HANDOFF.md` — exact active continuation point, including unmerged branches/PRs and write-ahead recovery state.
5. The active PR/branch documents named in `CHAT_HANDOFF.md`.
6. Detailed worklogs/audits only when they are relevant to the active gate.

### Authority rule

- `main` is authoritative for **accepted/promoted** product state.
- An active feature/research branch is authoritative only for its **unmerged candidate**.
- `CHAT_HANDOFF.md` is allowed to reference both and must keep that distinction explicit.
- A compile/CI PASS is not equivalent to TradingView visual/history validation.
- A design decision is not equivalent to implemented production Pine.

If documents disagree, never silently average them. Identify which evidence level each document represents.

---

## 2. Continuity durability protocol — WRITE-AHEAD + COMMIT-RESULT

The old rule of updating continuity only **after** something materially changed left a dangerous window: the chat could die while analysis, tooling, commits or workflow evidence were in progress, after the previous handoff but before the next one.

The project therefore uses a two-phase durability protocol.

### What counts as a substantial block

Use the protocol before work that meets any of these conditions:

- more than one meaningful repository/workflow/tool action is likely;
- commits, workflow runs or artifacts may be created;
- analysis is long enough that losing it would force meaningful reconstruction;
- the active discriminant may change;
- a product/engine semantic decision may be made.

Do **not** create checkpoint noise for a trivial read, a one-line factual lookup or a purely conversational response.

### Phase A — WRITE-AHEAD / PREPARED

Before substantial work begins, update `docs/CHAT_HANDOFF.md` on `main` as the **first durable engineering action**.

Record:

- checkpoint state = `PREPARED`;
- current active PR/branch heads;
- last verified durable result;
- exact next atomic action;
- working hypothesis/discriminant when one exists;
- expected commit/workflow/artifact/evidence;
- whether operator evidence is required;
- recovery algorithm if interruption happens before completion.

This write-ahead update is not a request for permission and should not interrupt the engineering rhythm. It exists so a new chat can recover the *intent* of the work even if the original chat dies before producing a result.

### Phase B — COMMIT-RESULT / STABLE

After each meaningful milestone:

1. commit or otherwise persist the actual engineering result first;
2. update `docs/CHAT_HANDOFF.md` with the new refs/runs/artifacts and the new exact next discriminant;
3. mark the checkpoint `STABLE` when no product work remains in flight;
4. update this `CONTINUITY_LOG.md` only if causal history, product direction, methodology or a retired route changed.

### Recovery if the chat dies between A and B

A future chat must:

1. read the canonical resume sequence;
2. compare the recorded PR/branch heads with the actual GitHub heads;
3. inspect only commits newer than the recorded checkpoint;
4. inspect workflow runs/artifacts newer than the checkpoint when relevant;
5. if refs did not move, resume the recorded next atomic action;
6. if refs moved, infer what actually completed from GitHub evidence and continue from there;
7. never redo a completed analysis merely because the prior conversational explanation was lost.

This makes the GitHub delta itself the recovery mechanism for work that completed after the write-ahead checkpoint.

### File responsibilities

- `CHAT_HANDOFF.md` is intentionally volatile and may be updated frequently.
- `CONTINUITY_LOG.md` is intentionally slow and should stay readable as causal memory.
- `CANONICAL_STATE.md` remains accepted/promoted truth on `main`, not a scratchpad for unmerged work.

---

## 3. Interaction methodology — LOCKED unless the operator changes it

The operator has explicitly granted broad engineering freedom.

The expected working style is:

- the assistant may redesign legacy scripts instead of reproducing them;
- preserve useful concepts, not legacy clutter;
- engine defaults should be engineered and validated rather than delegated back to the operator;
- profiles exist only when they add genuine value;
- chart UX should be objective and minimal;
- no Compact/Full dual-panel pattern;
- do not ask the operator to test trivial changes that can be proven by code/CI;
- batch TradingView/user validation into meaningful gates;
- use GitHub as the canonical engineering record;
- distinguish implementation correctness from actual market usefulness;
- do not promote something because it merely looks good in one screenshot;
- document decisions, rejected routes and evidence before moving on.

### Product-first interaction contract — essence of Chat 01

The project exists to help the operator **read the market more objectively and reduce mechanical chart interpretation**, not to preserve six legacy scripts or maximize engineering ceremony.

Preserve this interaction model across chats:

- product usefulness to real trading decisions comes before preserving legacy code, UI, terminology or roadmap order;
- the assistant is an autonomous engineering partner, not a project manager waiting for permission at every micro-step;
- when the operator says “continue”, advance autonomously to the next meaningful evidence boundary unless unique operator input is actually required;
- prefer doing the repeatable engineering silently and returning with a substantive result, decision or discovered defect;
- communicate the important outcome, why it matters and what changed — do not turn the conversation into a running report of every commit/tool call;
- ask the operator primarily for evidence the assistant cannot obtain itself: TradingView visual/realtime behavior, operator usefulness, or an actual product choice;
- reduce operator cognitive load: hidden engine complexity is acceptable only when the visible output becomes clearer and more useful;
- “surprise me” means freedom to depart from familiar scripts/periods/visuals when a better evidenced design exists, not freedom to add novelty for its own sake;
- if professional process starts to dominate the product conversation, pull the focus back to the question: **does this make the chart more useful for the operator's decision?**

The GitHub discipline exists to support this rhythm, not replace it.

The operator contributes the evidence the assistant cannot obtain directly:
- TradingView visual behavior;
- TradingView CSV exports;
- reload behavior;
- market-usefulness feedback.

The assistant should carry the repeatable engineering, documentation, CI and analysis work.

---

## 4. Locked product direction

The project rebooted the extracted legacy collection rather than preserving six end-user indicators.

Logical suite:

1. **Market Map**
   - regime/trend
   - structure
   - structural liquidity
   - correction/retest/reclaim location
   - destination
   - invalidation

2. **Execution**
   - momentum turn/acceleration
   - RSI recovery/exhaustion
   - participation/relative volume
   - execution timing
   - continuation/reaction-risk state

3. **Decision Panel**
   - semantic synthesis of Market Map + Execution
   - no opaque gate score

The current Execution research candidate further proposes **two runtime indicators for three logical layers**:
- Market Map overlay + embedded Decision Panel
- Execution lower pane

That topology is not promoted on `main` until its research PR is accepted.

---

## 5. UX/default invariants

Current direction:

- Auto-first.
- Minimal user settings.
- Engineering thresholds live in the engine.
- No mandatory profile selector.
- One useful default presentation is preferable to visual-density ceremony.
- Avoid raw technical tables when a semantic state communicates the same information.
- No fabricated probability percentage.
- No claim that OHLCV-only structural liquidity equals leveraged-liquidation data.
- Realtime-only information must never be presented as if it were reconstructible historical truth.

---

## 6. Timing/evidence invariants

These distinctions must remain explicit:

### Compile/static proof
Proves:
- Pine syntax/compiler acceptance;
- repository invariants;
- deterministic reference-model tests.

Does **not** prove:
- useful correction zones;
- sensible event frequency;
- reload parity on TradingView;
- profitable trades.

### TradingView proof
Used for:
- real chart rendering;
- real TradingView data semantics;
- historical CSV audit;
- confirmed-history reload parity;
- visual usefulness.

### Trading usefulness
Separate again from technical correctness.

The scripts are decision-support. The operator decides the trade using chart context plus external market/macroeconomic/political information.

---

## 7. Routes intentionally retired/deferred

Do not resurrect these without new evidence:

- treating the six legacy core scripts as six mandatory final indicators;
- recreating the old MA 6x UI merely for familiarity;
- Compact/Full panel variants;
- large multi-row RSI tables;
- four manually configured RSI timeframes;
- RAW/VI participation selector as a production choice;
- exposing dozens of engine thresholds;
- labeling candle-location pressure as real buy/sell aggressor volume;
- allowing realtime-only `varip` delta to determine reload-safe confirmed signals;
- full profile-style POC inside Market Map merely because donor code exists;
- requiring `input.source()` plumbing between final suite indicators;
- a third mandatory Decision Panel indicator unless later evidence demonstrates unique value;
- arbitrary “probability” or opaque composite scores.

---

## 8. Historical engineering narrative

### 2026-09-22 — TradingView extraction and repository reboot

All accessible TradingView scripts were extracted and archived immutably.

The repository established:
- immutable raw/source archive;
- core vs donor/reference classification;
- version reboot policy;
- professional changelog/audit/testing structure.

The operator explicitly requested that existing legacy version numbers not be preserved as product lineage. Reboot products begin at 0.1.0 when accepted.

### 2026-09-22/23 — SignalGate timing hardening

SignalGate Dashboard 0.1.0 became the first accepted engineering baseline.

Its value is timing/reload discipline, not its old final UX.

Important inheritance:
- confirmed HTF policy;
- close-confirmed transitions;
- reload-safe event thinking.

### 2026-09-23 — Suite architecture replaces six-script end state

The project moved from “repair six indicators” to a three-layer decision-support suite:

```text
Market Map
+
Execution
+
Decision Panel
```

The operator explicitly approved:
- departing from legacy visuals/periods where a better design exists;
- engine-owned defaults;
- minimal settings;
- profiles only where justified.

### 2026-09-23 — Market Map MM-0

Active candidate: PR #10 / `feat/market-map-0.1.0-mm0`.

Major candidate architecture:
- EMA 21/50/200;
- automatic confirmed HTF;
- HH/HL/LH/LL + BOS/CHoCH;
- structural liquidity + PDH/PDL/PWH/PWL;
- confirmed sweep/reclaim;
- adaptive Correction Engine with Fibonacci fallback;
- directional destination ladder;
- structural invalidation;
- stable confirmed volume-acceptance confluence;
- one semantic panel;
- versioned Data-Window/CSV audit schema;
- offline historical analyzer + reload comparator.

Compile/static gates are green. Promotion is deliberately blocked on real TradingView historical/visual evidence.

### 2026-09-23 — TradingView Essential changes the historical-validation path

The operator confirmed the account is TradingView Essential and cannot export the historical CSVs required by the original MM-0 audit workflow without upgrading.

Decision:
- do **not** require a TradingView Premium upgrade for engineering validation;
- preserve the Pine CSV audit schema/analyzer because it remains useful when export access exists;
- move primary historical validation to official Binance public market data;
- delegate data plumbing to a separate infrastructure thread tracked by Issue #14;
- keep the main indicator-engineering thread focused on Market Map / Execution;
- use targeted TradingView visual/reload checks later for Pine/runtime parity rather than as the only source of historical evidence.

Issue #14 owns:
- official Binance spot klines;
- BTCUSDT first;
- 15m / 1h / 4h / 1d / 3d / 1w;
- automated monthly download/checksum/gap validation;
- large Parquet datasets stored outside Git, preferably in the connected Google Drive.

This change improves independence from TradingView plan limitations and creates a reproducible offline research lab.

### 2026-09-23 — Execution architecture research

Active research: PR #12 / `research/execution-engine-design`.

The legacy Moving Average Shift, RSI MTF Tactical and Buying/Selling Volume scripts are donors, not final products.

Candidate Execution semantics:

```text
EXECUÇÃO:
AGUARDAR -> PREPARANDO -> ARMADO -> CONFIRMA -> ALINHADO

FORÇA:
NORMAL / PERDENDO FORÇA / EXAUSTÃO / RISCO DE REAÇÃO
```

Research added executable Python reference models and CI for semantic transitions before production Pine exists.

This is intentional: Pine implementation must conform to an explicit contract instead of inventing behavior during coding.

The research subsequently produced three first-pass evidence-engine candidates:

- **MTE-A — Momentum Turn**
  - ATR-normalized EMA8/EMA21 spread;
  - adaptive neutral/counter-acceleration semantics;
  - scale/translation/reversal synthetic tests.

- **RSE-A — RSI State**
  - local RSI14 semantic state;
  - 48–52 center dead-band;
  - 70/30 and 80/20 zones;
  - 2-bar recovery/fade memory;
  - separate confirmed HTF RSI context direction.

- **PSE-A — Participation**
  - current volume vs prior confirmed EMA20 baseline;
  - honest candle close-location pressure proxy;
  - validation-only comparison against Binance taker-buy imbalance.

All three remain research candidates. Numeric defaults must not be optimized before the Binance historical lab supplies evidence.

---

### 2026-09-24 — Binance historical lab completed and promoted

Issue #14 / PR #15 completed the delegated historical-data infrastructure and was promoted to `main`.

Promotion merge:

`bf132cf715aade528aa89b1b327566a964015609`

Accepted production evidence:
- 15 Binance SPOT symbols;
- 6 timeframes per symbol: 15m / 1h / 4h / 1d / 3d / 1w;
- 90 consolidated Parquet datasets;
- 4,849,829 candles;
- 7,503 available official Binance checksums verified;
- 0 checksum mismatches;
- one exact AVAXUSDT duplicate deterministically deduplicated and reported;
- unavailable expected monthly objects retained explicitly as findings; no candle synthesis.

The final independent review also closed two correctness issues before promotion:
- timestamp precision around the 2024/2025 transition now preserves valid native millisecond rows and reports epoch inconsistencies as findings instead of rejecting verified candles;
- expected-but-missing monthly archives participate in the idempotency fingerprint, preventing an old manifest from silently masking a newly expected 404.

Final PR gate:
- Market data pipeline: 21/21 PASS;
- Static integrity: PASS.

Causal consequence for the product work:
- historical data plumbing is no longer the blocker;
- offline Market Map validation becomes the primary next evidence gate;
- pre-registered MTE-A / RSE-A / PSE-A historical tests may now run against real market data;
- production `execution.pine` remains blocked until those evidence results are reviewed;
- downloader redesign should not resume unless a concrete evidence task exposes an actual infrastructure defect.

---

### 2026-09-24 — MM-0 offline historical structural gate completed on PR #10

This is **unmerged candidate evidence** on PR #10 / `feat/market-map-0.1.0-mm0`; it does not promote Market Map semantics to `main`.

The project implemented a deterministic offline Market Map audit kernel that emits the same Audit Schema v2 consumed by the existing analyzer.

Evidence source:
- exact SHA-256-verified BTCUSDT production Parquets from the accepted PR #15 historical-data lab;
- primary matrix: 15m / 1h / 4h / 1d;
- robustness extension: 3d / 1w;
- 3d/1w context semantics explicitly match Pine: self-context above 1D, PDH/PDL disabled above 1D, PWH/PWL retained through 1W.

Final six-timeframe robustness run:

`36039959727`

Candidate head after documentation/gates:

`31b9096179a2b5b3173a6ab8a03452636536fae0`

Automated gates:
- Pine compile: PASS — run `36040202039`;
- Static integrity: PASS — run `36040202044`;
- six-timeframe offline pathology gate: PASS.

Six-timeframe historical accounting:
- 45,694 theses;
- 32,550 first correction-zone touches;
- 5,428 destination outcomes;
- 1,041 invalidation outcomes;
- 4,574 ambiguous OHLC-order outcomes;
- 21,504 superseded/censored touched theses;
- 3 open at export end;
- outcome accounting = 100%;
- structural pathologies = none.

Interpretation decision:
- the ~83.9% destination share among non-ambiguous resolved cases is conditional and must **not** be called a trade win rate or unconditional map success rate;
- only ~19.87% of touched theses resolve destination/invalidation non-ambiguously before replacement;
- ~66.06% are superseded/censored before that resolution;
- LIVE/ADAPT produces far more same-candle OHLC ambiguity than confirmed ADAPT.

The 1W extension has only 8 non-ambiguous resolved cases and is explicitly a small sample. It is robustness evidence only and cannot drive tuning.

Causal consequence:
- historical structural sanity is no longer the active MM-0 blocker;
- do not tune correction ratios, pivot length, ATR tolerances, LIVE rules or target rules from aggregate percentages;
- the next discriminant is lifecycle/parity diagnosis of representative LIVE/ADAPT ambiguous first-touch cases and superseded touched theses;
- only after those representative cases are understood should targeted TradingView screenshots/reload checks be requested.

---

### 2026-09-24 — Continuity protocol v2 closes the mid-task interruption gap

Audit of the continuity mechanism found that it was functioning but not interruption-safe enough:

- `CONTINUITY_LOG.md` had been updated through the MM-0 offline structural gate;
- `CHAT_HANDOFF.md` had correctly advanced to the lifecycle/parity gate;
- PR #10 then advanced beyond the handoff to lifecycle diagnostic commits before the next handoff update;
- the previous protocol therefore preserved the last completed milestone but could lose the intent/results of work performed in the interval before the next checkpoint;
- resume-order wording also disagreed between documents.

Decision:

- unify the resume order as `README -> CANONICAL_STATE -> CONTINUITY_LOG -> CHAT_HANDOFF -> active PR/branch`;
- preserve the Chat-01 product-first/autonomous interaction contract explicitly;
- use the two-phase WRITE-AHEAD + COMMIT-RESULT protocol in `CHAT_HANDOFF.md`;
- keep `CONTINUITY_LOG.md` slow and causal rather than turning it into a per-commit diary.

This protocol is now part of the locked working methodology.

---

## 9. Current continuation checkpoint

The exact volatile checkpoint belongs in:

`docs/CHAT_HANDOFF.md`

At the time this continuity system was introduced:
- accepted `main` baseline remained SignalGate Dashboard 0.1.0;
- Market Map MM-0 was compile/static green; the original TradingView CSV path was later replaced as the primary historical route by the delegated Binance offline lab because Essential cannot export those CSVs;
- Execution remained design/research only;
- MTE-A / RSE-A / PSE-A candidates and their executable reference tests were added after the initial continuity checkpoint;
- Issue #14 / PR #15 historical-data infrastructure is accepted on `main`;
- the initial MM-0 offline historical structural gate is complete on unmerged PR #10; its active blocker is LIVE/supersession lifecycle parity diagnosis;
- production `execution.pine` remains intentionally blocked until historical evidence challenges the candidate formulas.

Future chats must read `CHAT_HANDOFF.md` rather than relying on this paragraph to stay current.

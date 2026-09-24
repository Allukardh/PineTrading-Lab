# PineTrading-Lab — Continuous Engineering Context

> Permanent, incremental continuity log for the PineTrading-Lab project.
>
> This file exists so a future ChatGPT instance can reconstruct **why the project is in its current state and how the operator expects the work to be conducted**, not merely read the latest code.

## 1. Resume order after a chat interruption

Do **not** start by rereading old chat transcripts.

Read in this order:

1. `README.md` — project identity and repository rules.
2. `docs/CANONICAL_STATE.md` — accepted/promoted truth on `main`.
3. `docs/CHAT_HANDOFF.md` — exact active continuation point, including unmerged branches/PRs.
4. `docs/CONTINUITY_LOG.md` — causal history and locked interaction methodology.
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

## 2. Continuity update rule

Whenever one of these changes materially, continuity must be updated in the same engineering step:

- suite architecture or runtime topology;
- a product/engine semantic contract;
- a meaningful implementation becomes compile/static green;
- a TradingView visual/history/reload gate passes or fails;
- an old route/design is retired or deliberately deferred;
- the active PR, branch, gate or exact next discriminant changes;
- operator interaction methodology changes.

Update sequence:

1. update the authoritative implementation/design/worklog first;
2. update `docs/CHAT_HANDOFF.md` if the exact resume point changed;
3. append/update this continuity log when the causal project history changed;
4. do not create a new continuity file merely because the chat changed.

The project may create detailed dated worklogs for engineering evidence, but continuity itself remains stable.

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

---

## 9. Current continuation checkpoint

The exact volatile checkpoint belongs in:

`docs/CHAT_HANDOFF.md`

At the time this continuity system was introduced:
- accepted `main` baseline remained SignalGate Dashboard 0.1.0;
- Market Map MM-0 was compile/static green but awaiting TradingView CSV/visual/reload evidence;
- Execution remained design/research only, with reference-state and bridge semantics green in CI;
- the next independent research task was the clean-room Momentum Turn Engine;
- production `execution.pine` remained intentionally blocked.

Future chats must read `CHAT_HANDOFF.md` rather than relying on this paragraph to stay current.

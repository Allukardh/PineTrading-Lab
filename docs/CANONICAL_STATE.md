# Canonical State

**Date:** 2026-09-24  
**Phase:** Trading Suite Architecture v1 — Execution 0.1.0 production implementation  
**Primary accepted product baseline:** Market Map 0.1.0 on `main`  
**Preserved engineering baseline:** SignalGate Dashboard 0.1.0  
**Active architecture:** two runtime indicators — Market Map (with embedded Decision Panel) + Execution

## Continuity navigation

For resuming the project after a chat interruption:
- `docs/CONTINUITY_LOG.md` — permanent causal history and interaction methodology
- `docs/CHAT_HANDOFF.md` — exact current continuation point, including unmerged active branches/PRs

This document remains authoritative for **accepted/promoted main state**. The handoff may reference newer unmerged candidates and must keep that distinction explicit.

## Evidence baseline

The immutable TradingView extraction remains under `archive/`:
- discovered: 53
- exported: 53
- failed: 0
- principal/core: 6
- reference/donor: 47
- mode: `pine-facade / read-only`

Never edit archived Pine files to represent new behavior.

## Accepted historical market-data lab

PR #15 / Issue #14 is **PROMOTED TO `main`** as the canonical offline historical-data infrastructure.

Promotion merge:

`bf132cf715aade528aa89b1b327566a964015609`

Scope:
- official Binance Public Data SPOT monthly klines only;
- 15 symbols:
  - BTCUSDT
  - ETHUSDT
  - AVAXUSDT
  - DOGEUSDT
  - DOTUSDT
  - ADAUSDT
  - XRPUSDT
  - SOLUSDT
  - UNIUSDT
  - NEARUSDT
  - AAVEUSDT
  - HBARUSDT
  - LINKUSDT
  - SUIUSDT
  - LTCUSDT
- timeframes: 15m / 1h / 4h / 1d / 3d / 1w;
- 90 consolidated Parquet datasets;
- 4,849,829 candles;
- 7,503 available official checksums verified;
- 0 checksum mismatches;
- one exact AVAXUSDT duplicate deterministically deduplicated and reported;
- expected-but-missing Binance monthly objects remain explicit findings; no candles are synthesized.

Final PR gate:
- Market data pipeline: PASS — 21/21 tests;
- Static integrity: PASS;
- timestamp precision transition regression: PASS;
- missing-archive idempotency regression: PASS.

Canonical repository artifacts:
- `configs/binance-spot-research-universe.json`
- `docs/data/BINANCE_MARKET_DATA_PIPELINE.md`
- `docs/data/GOOGLE_DRIVE_LAYOUT.md`
- `manifests/binance-spot-btcusdt.production-2026-09-24.json`
- `manifests/binance-spot-research-universe.production-2026-09-24.json`
- `reports/binance-spot-btcusdt-materialization-2026-09-24.md`
- `reports/binance-spot-research-universe-materialization-2026-09-24.md`

The historical lab is evidence infrastructure only. It does not promote or alter Market Map / Execution trading semantics by itself.

## Accepted product direction

The project no longer assumes that the six legacy core scripts remain six independent end-user indicators.

Approved logical architecture, delivered through **two runtime indicators**:

1. **Market Map**
   - trend/regime
   - market structure
   - structural liquidity
   - correction/retest zones
   - targets and invalidation
   - embedded semantic Decision Panel

2. **Execution**
   - momentum
   - RSI/exhaustion/divergence
   - volume participation
   - entry confirmation

The **Decision Panel** remains a logical synthesis layer, not a third mandatory script. It is embedded in Market Map and may incorporate validated Execution state without resurrecting SignalGate as a separate final product.

Canonical design:
- `docs/TRADING_SYSTEM_DESIGN.md`
- `docs/DEFAULTS_AND_PROFILES.md`

## Accepted reboot baselines

### SignalGate Dashboard 0.1.0

Path: `src/core/signalgate-dashboard.pine`

Status: **ACCEPTED ENGINEERING BASELINE**

Validation summary:
- static transformation invariants: PASS
- archive/source integrity: PASS
- Pine v6 TradingView server compile: PASS (0 errors / 0 warnings)
- Bias safe-clamp 1D default case: PASS
- manual Structure/Trigger lower-TF guards: PASS
- 15m/1H/4H reload visual/state matrix: PASS for closed-history/rendered state
- 15m bar-close HEARTBEAT transport: PASS and repeatable on consecutive closes
- alert edge invariants: PASS

Scope note:
- SignalGate 0.1.0 remains valuable as the timing-safe synthesis foundation.
- its G1/G2/G3/G4/G5 UX and score semantics are not the final Decision Panel contract.

## Operator workflow evidence

The most relied-upon legacy workflow was:
- **MA 6x** for moving-average/trend reading
- **Fibonacci retracement** for pullback/correction context

This is evidence about what helped the operator, **not a compatibility contract**.

Therefore:
- moving-average context remains valuable, but the project may change the count, periods and presentation;
- retracement/correction context remains valuable, but Fibonacci may be combined with or subordinated to adaptive/statistical correction logic;
- legacy scripts are donors/research material, not product specifications;
- low-level configuration is not delegated back to the operator;
- the assistant may replace familiar mechanics when a clearer or better-evidenced design exists.

## Liquidity decision

Liquidity Zones Tactical is **not** treated as a leveraged-liquidation map.

Its useful concepts are retained as an internal **Market Map Liquidity Engine**:
- equal highs/lows
- structural liquidity pools
- sweeps/reclaims
- mitigation/invalidation
- nearest relevant pools

Actual leveraged liquidation clusters require external derivatives/order-book/open-interest/liquidation data and are outside what chart-only OHLCV can honestly infer.

## Defaults policy

Normal operation is **Auto-first with engineered defaults**.

- No profile selector is mandatory.
- Profiles exist only when they represent genuinely useful operating behaviors.
- Timeframe behavior should be automatic where safe.
- The normal user-facing surface should remain minimal.
- Colors/styles, alert families and rare true operator preferences may remain configurable.
- Engineering thresholds belong inside the engine or Advanced/Diagnostics, not in the normal workflow.
- “Optimized default” means a project-recommended, validated default; it must not be presented as universally optimal without evidence.

## Development state

### SignalGate
Accepted timing-safe engineering baseline/donor. It is not a final third runtime product.

### Moving Average Shift MAS-0
Closed standalone reboot research is preserved as donor material for Execution.

### Market Map 0.1.0
**ACCEPTED PRODUCT BASELINE** on `main`.

Promotion:
`0eeb0d37b256a950cfb38f627fa3521bb213d380`

Promotion evidence:
- corrected six-timeframe BTCUSDT offline lifecycle/pathology gate: PASS;
- 100% touch accounting;
- zero structural pathologies;
- Pine v6 compile: PASS;
- Static integrity: PASS;
- BTCUSDT 4H before/after reload visual/state parity: PASS;
- BTCUSDT 1D correction/destination/invalidation/HTF presentation: PASS.

### Execution research contract
**ACCEPTED ON `main`.**

Promotion:
`1df7adaf3d39047fd400e4d81a4b30415a2934bd`

Accepted evidence decisions:
- MTE-A — KEEP;
- RSE-A — KEEP;
- PSE-A — KEEP;
- readiness state machine — KEEP;
- strength state machine — KEEP;
- no research defaults retuned.

Integrated evidence:
- workflow `36080621108` — PASS;
- Static integrity `36080620994` — PASS;
- accepted MM-0 offline semantics drove actual direction/location;
- BTC 15m/1h/4h readiness path reached PREP / ARMED / CONFIRMED / ALIGNED across multiple market eras;
- reaction-risk semantics remained unsaturated and concentrated appropriately near destination.

### Execution 0.1.0
**Primary active production focus.**

Issue: #20 — production implementation + Market Map semantic parity.

Production `execution.pine` may now be created, but must initially preserve the accepted research defaults/semantics exactly. Parameter tuning remains blocked unless production parity exposes a named semantic defect.

### Current product sequence
1. implement production `execution.pine` from the accepted research contract;
2. enforce semantic-kernel parity between the Execution lower pane and Market Map embedded Decision Panel;
3. run Pine compile/static parity;
4. run targeted TradingView 15m/1h/4h reload/UX validation;
5. only then promote Execution 0.1.0 and advance the integrated suite.

## Version lineage

Legacy application versions remain historical evidence only.

For suite products:
- `0.1.0` = first accepted reboot baseline
- `0.x` = controlled engineering/UX evolution
- `1.0.0` = only after timing, visual, alert and market-behavior validation close

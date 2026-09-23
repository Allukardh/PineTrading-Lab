# Canonical State

**Date:** 2026-09-23  
**Phase:** Trading Suite Architecture v1 — Market Map foundation  
**Main baseline:** SignalGate Dashboard 0.1.0 accepted on `main`  
**Active architecture:** Market Map + Execution + Decision Panel  
**Active development branch:** `feat/market-map-0.1.0-mm0`

## Evidence baseline

The immutable TradingView extraction remains under `archive/`:
- discovered: 53
- exported: 53
- failed: 0
- principal/core: 6
- reference/donor: 47
- mode: `pine-facade / read-only`

Never edit archived Pine files to represent new behavior.

## Accepted product direction

The project no longer assumes that the six legacy core scripts remain six independent end-user indicators.

Approved final suite:

1. **Market Map**
   - trend/regime
   - market structure
   - structural liquidity
   - correction/retest zones
   - targets and invalidation

2. **Execution**
   - momentum
   - RSI/exhaustion/divergence
   - volume participation
   - entry confirmation

3. **Decision Panel**
   - concise semantic synthesis
   - no requirement for the operator to interpret opaque internal gate scores

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

This is treated as evidence of useful concepts, **not a constraint on the new product**.

Therefore:
- MA 6x is a Market Map donor, not a mandatory six-line UI
- the new Market Map may change MA count/periods/type when a cleaner or stronger design is preferable
- Fibonacci is available to the Correction Engine, but its implementation may differ from the prior manual workflow
- final defaults are selected by engineering judgment and validation
- low-level configuration is not delegated back to the operator

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

A profile selector is used only where it adds genuine value; it is not mandatory across the suite.

Normal user-facing settings should be limited primarily to:
- visual density
- colors/styles
- alert families
- rare true operator preferences
- profile only when materially justified

Engineering thresholds belong under profiles or Advanced/Diagnostics, not in the normal workflow.

## Development state

### SignalGate
Accepted timing-safe baseline.

### Moving Average Shift MAS-0
Existing draft work is preserved but **paused as a standalone-product reboot**. Its useful logic will be integrated under Execution after Market Map foundations are established.

### Market Map MM-0

Path: `src/core/market-map.pine`

Status: **COMPILE/STATIC PASS; visual validation pending**

Current prototype:
- minimal 3-control UI
- one semantic panel; no Compact/Full variants
- EMA 21/50/200 trend layer
- automatic confirmed HTF context
- HH/HL/LH/LL + BOS/CHoCH
- structural-liquidity pools + PDH/PDL/PWH/PWL ranking
- directional destination ladder: nearest + next distinct intact liquidity
- target proximity disclosure without automatic trade instruction
- failed-breakout/fakeout state
- adaptive Correction Engine: empirical pullback depth with Fib fallback
- impulse volume-acceptance confluence (VWAP + VNode, not labeled POC)
- current-map-only primary correction zone; T1/T3 are Advanced detail

### Next implementation target
**Market Map foundation**

Order:
1. MA 6x trend/regime layer
2. deterministic structure engine
3. structural-liquidity engine
4. breakout/retest state
5. Correction Engine + Fibonacci
6. volume/POC confluence
7. target/invalidation rendering

## Version lineage

Legacy application versions remain historical evidence only.

For suite products:
- `0.1.0` = first accepted reboot baseline
- `0.x` = controlled engineering/UX evolution
- `1.0.0` = only after timing, visual, alert and market-behavior validation close

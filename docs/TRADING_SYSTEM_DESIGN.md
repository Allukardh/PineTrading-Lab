# Trading System Design — Suite Architecture v1

**Status:** Approved architecture  
**Date:** 2026-09-23  
**Primary use:** graphical decision-support for discretionary cryptocurrency trading

## 1. Product goal

PineTrading-Lab is not intended to become a collection of six independent indicators that the operator must mentally reconcile.

The product goal is a **three-part trading suite** that reduces mechanical chart interpretation while preserving final human discretion:

1. **Market Map** — where price is, what regime/phase it is in, where structure/liquidity lives, and where a correction/retest is likely to react.
2. **Execution** — whether momentum/participation currently supports acting on the map.
3. **Decision Panel** — concise synthesis of Market Map + Execution into a small number of actionable states.

The suite supports a decision. It does not replace macro/news/political/context analysis and does not place trades.

## 2. Core operator questions

Every visible output must help answer one of these questions:

1. **Direction:** Is the market structurally bullish, bearish, or neutral/ranging?
2. **Phase:** Is price in impulse, correction, retest, breakout, exhaustion, or transition?
3. **Destination:** What are the nearest technically relevant liquidity/structure targets above and below?
4. **Correction:** If price retraces, where are the most plausible reaction zones and where is the structural invalidation?
5. **Execution:** Is there enough confirmation to act now, or should the operator wait?

Any metric that does not materially improve one of these answers belongs under the hood or should be removed.

## 3. Final suite

### 3.1 Market Map

**Role:** price-chart overlay and structural context engine.

Market Map owns:

- moving-average trend/regime layer
- swing structure: HH/HL/LH/LL
- BOS / CHoCH / MSS semantics
- support/resistance zones
- probable structural liquidity pools
- sweeps and reclaims
- breakout vs retest state
- correction zones
- Fibonacci retracement/confluence
- volume-derived support/resistance / POC / high-volume nodes where useful
- nearest upside/downside technical targets
- structural invalidation

### 3.2 Execution

**Role:** timing/confirmation engine, preferably in a lower pane with minimal overlay markers.

Execution owns:

- momentum acceleration/deceleration
- Moving Average Shift concepts
- MTF RSI / exhaustion / divergence
- volume participation
- historical volume-pressure proxy where unavoidable
- realtime incremental volume logic where TradingView data permits it
- confirmation state for long/short execution

Execution must not create its own independent market map. It answers:

> “Given the current map, is the move confirming now?”

### 3.3 Decision Panel

**Role:** small, human-readable synthesis layer.

The accepted SignalGate Dashboard 0.1.0 is a timing-safe engineering baseline, **not** the final UX contract.

The final panel should prefer semantic outputs over internal gate names and arbitrary scores.

Target format:

```text
BTCUSDT • 15m

REGIME       ↑ ALTA
FASE         ↘ CORREÇÃO
ESTRUTURA    HH/HL • intacta

LIQUIDEZ ↑   87.400–87.650
LIQUIDEZ ↓   85.050–84.850

PULLBACK
T1           85.950–85.700
T2           85.150–84.850  ★ confluência
T3           84.300–84.050

EXECUÇÃO     AGUARDAR
CONFIRMAÇÃO  Reteste + momentum
INVALIDA     < 84.050
```

When confirmation arrives:

```text
FASE         RETESTE
EXECUÇÃO     LONG ✓
ALVO 1       87.400
ALVO 2       88.100
```

Internal engines may remain complex. The visible answer should not be.

## 4. Existing six core scripts — new roles

The six extracted core scripts remain valuable source material, but they are no longer assumed to remain six end-user products.

| Legacy core | New role | Product destination |
|---|---|---|
| MA 6x | Primary trend/regime + familiar moving-average visual layer | Market Map |
| Liquidity Zones Tactical | Structural-liquidity/sweep engine | Market Map |
| RSI MTF Tactical OB/OS | Momentum/exhaustion/divergence evidence | Execution |
| Moving Average Shift | Momentum turn/acceleration and trigger evidence | Execution |
| Buying Selling Volume 2-in-1 | Participation/pressure evidence; historical proxy + possible realtime mode | Execution |
| SignalGate Dashboard | Timing-safe synthesis baseline; semantics to be simplified | Decision Panel |

## 5. MA 6x is the operator anchor

The operator's historical workflow relied primarily on **MA 6x plus Fibonacci retracement**. This is important product evidence.

Therefore:

- the MA visual layer must not be discarded
- Market Map should preserve the ability to display the familiar MA structure clearly
- current MA 6x periods (7/20/50/100/200/350 EMA defaults) are treated as a compatibility baseline, not automatically as statistically optimal
- final defaults are product decisions to be validated, not tuning work delegated to the operator
- MA 6x “probability”/quality concepts must not be presented as calibrated probabilities unless backed by empirical calibration
- Fibonacci becomes a first-class input to the Correction Engine instead of a manual afterthought

## 6. Correction Engine

The current suite lacks a sufficiently explicit answer to:

> “Is this a correction/retest, and where can it plausibly end?”

Market Map will contain a dedicated **Correction Engine**.

### 6.1 Inputs

A correction zone may receive confluence from:

- last valid structural impulse
- BOS/retest level
- last meaningful HL/LH
- Fibonacci retracement of the structural impulse
- support/resistance zone
- volume-supported level
- POC / high-volume node where appropriate
- VWAP/anchored VWAP where appropriate
- nearby structural-liquidity pool
- ATR / recent pullback depth context

### 6.2 Output

Do not claim an exact future price.

Prefer zones:

- **T1 — shallow correction / retest**
- **T2 — primary confluence zone**
- **T3 — deep correction**
- **Invalidation — structural condition that breaks the thesis**

Example:

```text
T1  85.950–85.700
T2  85.150–84.850  ★★★
T3  84.300–84.050
INV < 83.950
```

The star/confluence label represents independent evidence count/quality, not a fabricated win probability.

## 7. Liquidity semantics

### 7.1 What Pine can reasonably infer

Market Map may identify **probable structural liquidity** using:

- equal highs / equal lows
- un-swept swing highs/lows
- previous day/week highs/lows
- breakout/retest levels
- pivots and clustered support/resistance
- volume-supported zones
- stop-prone structural areas
- sweep/reclaim behavior

### 7.2 What Pine OHLCV cannot honestly claim

A chart-only Pine script must not label those zones as actual leveraged-position liquidation clusters.

Actual liquidation maps require external derivatives/order-book/open-interest/liquidation data or another explicit data feed.

Therefore the project will use terminology such as:

- `Liquidity Pool`
- `Structural Liquidity`
- `Sweep`
- `Likely Stops`

and will **not** label OHLCV-inferred zones as `Liquidation Map`.

## 8. Liquidity Zones Tactical decision

**Decision: KEEP the logic, RETIRE the standalone product concept.**

Liquidity Zones Tactical is useful because it contributes:
- equal-high/equal-low detection
- probable liquidity zones
- sweep/reclaim logic
- wick rejection
- mitigation/invalidation state
- proximity to nearest liquidity

It becomes harmful only when:
- it is interpreted as real leveraged-liquidation data
- too many zones/labels clutter the chart
- its score is treated as a calibrated probability
- a single “liquidity” script competes visually with structure, fib and volume layers

Therefore it will be refactored into the **Market Map Liquidity Engine**, with default output limited to the nearest/highest-relevance pools above and below price.

Known legacy defects from the initial audit remain blockers before reuse:
- inactive-side score contribution
- pivot-confirmation blind interval
- only one active zone per side
- persistent sweep conditions
- candle-location volume proxy

## 9. Donor library — what will actually be reused

Third-party/reference scripts are research donors, not end-user indicators.

High-value concepts:

| Donor family | Intended use |
|---|---|
| Market Structure CHoCH/BOS / HH-HL-LH-LL / SMC | structural state engine |
| Breakouts Tests & Retests / Breakout Detector MTF | breakout/retest state machine |
| Fibo Levels + Volume Profile + Targets | correction/target confluence |
| Volume-based S/R Zones | multi-zone structural map |
| High Volume Boxes | volume-confirmed support/resistance |
| Clusters Volume Profile | POC/HVN-style concentration evidence |
| Realtime Volume Bars | realtime participation mode |
| MA MTF Momentum | confirmed-HTF implementation patterns |
| Ultimate RSI / RSI Trend | momentum/exhaustion research |
| Supertrend Fakeout | fakeout state research |

Quarantined timing/lookahead code must never be transplanted as-is.

Licensing/provenance rules in `NOTICE.md` remain mandatory.

## 10. Default-settings product policy

The operator should **not** be responsible for engineering the indicator through dozens of thresholds.

Defaults are part of the product.

### 10.1 Exposed settings should be minimal

Normal settings should be limited to:

- **Profile:** Sniper / Balanced / Aggressive
- optional trading horizon only if Auto cannot reliably infer it
- visual mode: Clean / Standard / Detailed
- color/theme controls
- line/zone visibility where genuinely personal
- alert enable/disable

Everything else should be:
- automatically derived from chart timeframe/market context, or
- controlled internally by the selected profile, or
- hidden under an explicit Advanced/Diagnostics section.

### 10.2 Default profile

**Balanced** is the default unless evidence later supports a better universal default.

Profiles control coherent bundles, not isolated magic numbers:

- **Sniper:** fewer, later, stronger confirmations
- **Balanced:** general-purpose default
- **Aggressive:** earlier/more frequent signals with lower confirmation burden

### 10.3 No configuration dumping

An input is not exposed merely because Pine can expose it.

Before adding a user-facing setting, ask:

1. Is this a genuine operator preference?
2. Can Auto infer it safely?
3. Is it already represented by Profile?
4. Would changing it without understanding the engine be likely to degrade behavior?

If (2) or (3) is yes, or (4) is yes, keep it internal.

### 10.4 Advanced settings

Advanced/diagnostic inputs may exist for engineering and validation, but:
- they default to hidden/off
- they are not required for normal trading
- they must not be part of the normal operator workflow

## 11. Timeframe policy

Default operation is automatic and deterministic.

- higher-timeframe data: confirmed where required
- lower-timeframe requests: only through a deliberately designed LTF engine
- no silent misuse of `request.security()`
- manual timeframe selection is exceptional, not normal workflow
- effective timeframes are visible in diagnostics, not demanded from the operator

## 12. Visual-density policy

The chart must answer questions, not display every internal observation.

Default Market Map should show only:
- selected MA layer
- current structural regime
- nearest relevant support/resistance/liquidity zones
- active correction/retest zones
- next upside/downside target
- structural invalidation
- only the most relevant event labels

Historical/debug labels are optional.

## 13. Probability terminology

Do not use percentage probability unless there is a defined, measured calibration dataset and methodology.

Allowed:
- High/Medium/Low confluence
- 3/4 confirmations
- Strong/Moderate/Weak setup
- empirically measured hit-rate with documented sample

Not allowed:
- arbitrary score renamed “78% probability”
- rule-based state presented as statistical confidence

## 14. Development order

Architecture replaces the previous “repair six independent scripts in sequence” plan.

### Phase A — Market Map foundation

1. MA/regime layer from MA 6x
2. deterministic structure engine
3. structural-liquidity engine
4. breakout/retest state
5. Correction Engine + Fibonacci
6. volume/POC confluence
7. clean target/invalidation rendering

### Phase B — Execution

1. Moving Average Shift concepts
2. RSI MTF/exhaustion
3. volume participation
4. confirmation state machine
5. close/reload/alert validation

### Phase C — Decision Panel

1. consume semantic outputs from Market Map + Execution
2. retire opaque G1/G2/G3/G4/G5 presentation
3. show regime/phase/zones/execution/invalidation
4. optional compact/full modes
5. alerts tied to semantic state transitions

## 15. Current development consequences

- SignalGate Dashboard 0.1.0 remains an accepted engineering baseline.
- MAS-0 work is preserved but **paused as a standalone-product reboot**.
- No more core script will be “fixed for its own sake” before mapping its logic into the three-product architecture.
- The next implementation milestone is **Market Map foundation**, beginning with the MA 6x trend/regime layer and Correction Engine design.

## 16. Acceptance criterion for the suite

A normal chart should be understandable in seconds.

The target operator experience is:

```text
REGIME      Alta
FASE        Correção
T2          84.850–85.150
LIQ ↑       87.400
LIQ ↓       84.700
EXECUÇÃO    Aguardar
TRIGGER     Reteste + momentum
INVALIDA    < 84.050
```

If the operator must study ten internal scores before understanding what the system is saying, the UX has failed.

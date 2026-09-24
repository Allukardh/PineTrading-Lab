# Trading System Design — Suite Architecture v1

**Status:** Approved architecture  
**Date:** 2026-09-23  
**Primary use:** graphical decision-support for discretionary cryptocurrency trading

## 1. Product goal

PineTrading-Lab is not intended to become a collection of six independent indicators that the operator must mentally reconcile.

The product goal is **three logical layers delivered through two runtime indicators**, reducing mechanical chart interpretation while preserving final human discretion:

1. **Market Map** — where price is, what regime/phase it is in, where structure/liquidity lives, and where a correction/retest is likely to react.
2. **Execution** — whether momentum/participation currently supports acting on the map.
3. **Decision Panel** — concise synthesis of Market Map + Execution into a small number of actionable states, embedded in Market Map rather than deployed as a third indicator.

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

### Runtime topology

The final operator surface is intentionally limited to **two TradingView indicators**:

1. **Market Map overlay + embedded Decision Panel**
2. **Execution lower pane**

The three-layer vocabulary remains useful architecturally, but it must never be interpreted as a requirement for three separate Pine scripts. SignalGate Dashboard remains an engineering/timing donor and accepted historical baseline, not a third final runtime product.


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
- volume-acceptance / volume-supported confluence where it demonstrates incremental value
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

**Role:** one small, human-readable synthesis layer **embedded in Market Map**. It is not a standalone mandatory runtime indicator.

There are **no Compact/Full panel variants**. That legacy split created two bad outcomes: one panel omitted useful context and the other exposed internal clutter. The suite uses one semantic panel whose contents are curated by the engine. The operator may show or hide it, but does not choose between competing information architectures.

The accepted SignalGate Dashboard 0.1.0 is a timing-safe engineering baseline, **not** the final UX contract.

The final panel should prefer semantic outputs over internal gate names and arbitrary scores.

Target format:

```text
BTCUSDT • 15m

REGIME       ALTA
FASE         CORREÇÃO
ESTRUTURA    ALTA • HH/HL

CORREÇÃO     85.150–84.850  ★★★
DESTINO      87.400 • PDH → 88.100 • EQH
LIQ ↑        87.400 • PDH
LIQ ↓        84.700 • EQL
INVALIDA     84.050

EXECUÇÃO     AGUARDAR
CONFIRMAÇÃO  Reteste + momentum
```

When confirmation arrives, Decision Panel may simplify to:

```text
FASE         RETESTE
EXECUÇÃO     CONFIRMA LONG
DESTINO      87.400 → 88.100
INVALIDA     84.050
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

## 5. MA 6x + Fibonacci are operator evidence, not product constraints

The operator's historical workflow relied primarily on **MA 6x plus Fibonacci retracement**. This tells us that moving-average structure and retracement context are genuinely useful to the operator, but it does **not** require the new suite to preserve the old layout, number of averages, periods, algorithms, or Fibonacci presentation.

Therefore:

- Market Map should retain a useful moving-average layer because it materially helps visual trend reading
- MA 6x is a donor/research baseline, not a UI contract
- the new engine may reduce, replace, or change the old 7/20/50/100/200/350 set when a cleaner design is better
- Fibonacci is a useful Correction Engine input, not a mandatory standalone drawing model
- final defaults are engineering/product decisions and may differ materially from the legacy scripts
- no legacy habit should block a demonstrably clearer or more robust design
- MA 6x “probability”/quality concepts must not be presented as calibrated probabilities unless backed by empirical calibration

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
- volume-acceptance / high-volume evidence where justified
- VWAP/anchored VWAP where appropriate
- nearby structural-liquidity pool
- ATR / recent pullback depth context

### 6.2 Output

Do not claim an exact future price.

The normal operator view exposes **one primary correction zone** plus structural invalidation.

Shallow/deep Fibonacci satellites may exist internally or under Advanced/Diagnostics, but they are not separate default panel rows.

Example:

```text
CORREÇÃO  85.150–84.850  ★★★
INVALIDA  83.950
```

The primary zone may adapt to recent completed pullback depth when enough samples exist, with Fibonacci retained as a fallback/reference input.

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

- **Profile only when it materially improves a product.** A product may intentionally have no profile selector.
- optional trading horizon only if Auto cannot reliably infer it
- a single curated default visual
- optional Advanced structural-detail toggle
- color/theme controls
- line/zone visibility where genuinely personal
- alert enable/disable

Everything else should be:
- automatically derived from chart timeframe/market context, or
- controlled internally by the selected profile, or
- hidden under an explicit Advanced/Diagnostics section.

### 10.2 Profiles are optional product tools

Do not add Sniper/Balanced/Aggressive merely for consistency across the suite.

Use profiles only when one product genuinely needs distinct coherent operating styles. If one robust automatic/default behavior is preferable, expose no profile at all.

When profiles are justified, they must control coherent bundles rather than isolated magic numbers. A likely contract is:

- **Sniper:** fewer, later, stronger confirmations
- **Balanced:** general-purpose behavior
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

Historical/debug labels are optional and belong behind an Advanced/Diagnostics toggle. Do not create multiple visual-mode presets merely to hide/show the same information.

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
6. validated volume-acceptance confluence
7. directional destination + invalidation rendering
8. historical CSV sanity + reload-parity validation

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
4. one curated semantic panel; no Compact/Full variants
5. alerts tied to semantic state transitions

## 15. Current development consequences

- SignalGate Dashboard 0.1.0 remains an accepted engineering baseline.
- MAS-0 work is preserved but **paused as a standalone-product reboot**.
- No more core script will be “fixed for its own sake” before mapping its logic into the three-product architecture.
- Market Map MM-0 is the active foundation candidate; implementation is substantially complete and promotion is blocked on historical CSV sanity, reload parity, and the final visual pass.
- Execution architecture research may proceed in parallel, but production implementation waits for the Market Map semantic contract to stabilize.

## 16. Acceptance criterion for the suite

A normal chart should be understandable in seconds.

The target operator experience is:

```text
REGIME      Alta
FASE        Correção
ESTRUTURA   Alta • HH/HL
CORREÇÃO    84.850–85.150  ★★★
DESTINO     87.400 PDH → 88.100 EQH
LIQ ↑       87.400
LIQ ↓       84.700
EXECUÇÃO    Aguardar
INVALIDA    84.050
```

If the operator must study ten internal scores before understanding what the system is saying, the UX has failed.

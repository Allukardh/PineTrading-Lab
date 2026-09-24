# Changelog

All notable project changes are documented here.

## [Unreleased]

### Next
- Run the pre-registered Execution evidence research plan against accepted Binance datasets.
- Keep production `execution.pine` blocked until MTE-A / RSE-A / PSE-A evidence is reviewed.
- Integrate validated Execution semantics into the embedded Market Map Decision Panel without creating a third runtime indicator.

## [Market Map 0.1.0] - 2026-09-24

### Added
- First accepted Market Map baseline: EMA 21/50/200 regime layer, confirmed structure, structural liquidity, correction engine, destination ladder and structural invalidation.
- Adaptive correction depth with Fibonacci fallback/core reference.
- Confirmed sweep/reclaim semantics and external PDH/PDL/PWH/PWL liquidity.
- Impulse VWAP + clean-room VNode acceptance confluence.
- One semantic Decision Panel embedded in Market Map; no Compact/Full variants and no third mandatory panel script.
- Audit Schema v2, offline Market Map kernel, lifecycle analyzer and reload-parity tooling.

### Changed
- Final runtime topology is **two TradingView indicators for three logical layers**: Market Map + embedded Decision Panel, and Execution lower pane.
- Historical audit target freezing now rejects stale targets that moved inside/behind the current correction zone.
- Same-bar zone→destination outcomes are resolved only when candle open + level topology prove the event order; genuinely unordered cases remain ambiguous.
- SignalGate remains a timing/reload/alert engineering donor rather than a final runtime product.

### Validation
- Corrected BTCUSDT six-timeframe offline lifecycle/pathology gate: PASS.
- 45,694 theses / 32,550 first correction-zone touches / 100% outcome accounting.
- 8,208 destination outcomes, 1,055 invalidation outcomes, 1,121 ambiguous, 22,163 superseded/censored, 3 open.
- Structural pathologies: 0.
- Pine v6 compile: PASS — run `36073131137`.
- Static integrity: PASS — runs `36073131121`, `36073128209`.
- Final TradingView BTCUSDT 4H before/after reload parity: PASS.
- Final BTCUSDT 1D correction/destination/invalidation visual sanity: PASS.

### Promotion
- PR #10 merged to `main`.
- Merge commit: `0eeb0d37b256a950cfb38f627fa3521bb213d380`.
- Issue #9 closed as completed.

## [SignalGate Dashboard 0.1.0] - 2026-09-22

### Added
- First accepted reboot baseline for SignalGate Dashboard.
- Confirmed-HTF request policy using `[1] + lookahead_on`.
- Bias timeframe safe-clamp when configured below the chart timeframe.
- Runtime guards for manual Structure/Trigger timeframes below the chart.
- Explicit PREVIEW/FECHADA chart-bar state and HTF confirmation disclosure.
- Repository integrity CI and TradingView server compile CI.
- Read-only current-editor compile helper.
- Bar-close KV telemetry with confirmed data-policy metadata.

### Changed
- Auto Trigger/Structure mappings no longer silently select a timeframe below the chart.
- Same-timeframe structure/trigger state transitions commit only on confirmed chart bars.
- Alert conditions and dynamic telemetry are chart-close gated.
- Full panel displays effective bias timeframes and clamp state.

### Fixed
- Removed implicit lower-timeframe `request.security()` sampling path.
- Fakeout alert/log now uses a one-shot edge event instead of a persistent condition.

### Validation
- Pine v6 server compile: PASS, 0 errors, 0 warnings.
- 15m/1H/4H closed-history/rendered reload matrix: PASS.
- 1D bias safe-clamp: PASS.
- Manual Structure/Trigger lower-TF guards: PASS.
- Two consecutive 15m HEARTBEAT closes: exactly one alert per close.
- Event-edge definitions locked by CI invariants.
- Natural GO/EARLY/K-R/IN_PLAY/Fakeout field samples moved to non-blocking issue #4.

### Integrity
- Archived v4.9.1 source remains untouched.
- No TradingView cookies/session tokens, API keys, exchange keys, webhook secrets, or other credentials are stored.

## [Project Reboot Foundation] - 2026-09-22

### Added
- Professional repository structure.
- Immutable TradingView snapshot.
- Exact archival split of all 53 Pine sources.
- Script catalog and initial static audit.
- Extraction/recovery tooling.
- Provenance safeguards and validation gates.

### Changed
- Active version lineage reset: core scripts restart at `0.1.0` on first accepted reboot baseline.

# Changelog

All notable project changes are documented here.

## [Unreleased]

### Added
- Approved three-product suite architecture: **Market Map**, **Execution**, and **Decision Panel**.
- Market Map 0.1.0 / MM-0 prototype with integrated regime, structure, structural liquidity and Correction Engine.
- Market Map liquidity ranking now includes confirmed PDH/PDL/PWH/PWL candidates and source labels.
- Market Map adds a confirmed sweep/reclaim phase and preserves reclaimed liquidity as correction confluence.
- Market Map CSV audit schema v2 exports confirmation state and reclaim direction.
- Market Map failed-breakout state restores pre-break structure when a CHoCH fails.
- Market Map adds a directional destination ladder using the nearest and next distinct intact liquidity pools, with proximity disclosure.
- Market Map Correction Engine now adapts its primary zone from recent completed pullback depths, with Fibonacci fallback when sample history is insufficient.
- Market Map adds clean-room current-impulse volume acceptance via VWAP + approximate VNode; no false POC labeling.
- Single semantic panel policy; Compact/Full variants are retired.
- Dedicated Correction Engine design for pullback/retest zones, confluence targets and invalidation.
- Minimal-settings / profile-driven defaults policy.

### Changed
- Development roadmap no longer repairs six legacy core indicators as six independent end-user products.
- MA 6x becomes the operator-familiar trend/regime foundation for Market Map.
- Fibonacci retracement becomes a first-class Correction Engine input.
- Liquidity Zones Tactical is reclassified as an internal structural-liquidity engine, not a leveraged-liquidation map.
- Moving Average Shift standalone reboot work is paused until the Execution product phase.

### Next
- Market Map foundation: MA/regime layer + structure + liquidity + correction engine.
- SignalGate live event-specific field observations continue in issue #4.

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

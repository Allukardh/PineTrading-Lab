# SignalGate Dashboard 0.1.0

**Date:** 2026-09-22  
**Status:** Accepted reboot baseline  
**Promotion commit:** `7990c7a6e0288fe85fc29a71f08b4ae0c5ae297b`

## Purpose

SignalGate 0.1.0 is not a score-model redesign. It is the first professional reboot baseline and focuses on deterministic timeframe semantics, confirmed data handling, lower-timeframe safety, alert timing, and reproducible validation.

## Accepted changes

- confirmed HTF values via `[1] + lookahead_on`
- equal-TF direct series path
- no implicit LTF sampling through `request.security()`
- Bias safe-clamp to chart TF
- manual Structure/Trigger lower-TF runtime guards
- confirmed structure/trigger state commits
- chart-close alert conditions
- chart-close KV telemetry
- fakeout edge-event fix
- explicit effective timeframe disclosure in the full panel

## Validation evidence

- TradingView server compile: 0 errors / 0 warnings
- repository/archive integrity: PASS
- BTCUSDT 15m reload: PASS for closed-history/rendered state
- BTCUSDT 1H reload: PASS for closed-history/rendered state
- BTCUSDT 4H reload: PASS for closed-history/rendered state
- BTCUSDT 1D Bias safe-clamp: PASS
- manual Structure 60 on 4H: expected runtime guard PASS
- manual Trigger 60 on 4H: expected runtime guard PASS
- HEARTBEAT at 17:15:01: one entry
- HEARTBEAT at 17:30:01: one entry
- no duplicate heartbeat observed

## Deferred by design

The following were deliberately not changed in 0.1.0:
- score weights
- GO/WATCH thresholds
- Mode C persistence
- MSS timeframe semantics
- stale breakout-level expiry
- trigger/IN_PLAY score overlap
- space-scoring assumptions
- market-efficacy calibration

Live event-specific alert observations continue in issue #4 and do not alter the accepted baseline.

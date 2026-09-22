# Canonical State

**Date:** 2026-09-22  
**Phase:** Moving Average Shift MAS-0 — signal reachability and deterministic markers  
**Main baseline:** SignalGate Dashboard 0.1.0 promoted at `7990c7a6e0288fe85fc29a71f08b4ae0c5ae297b`  
**Active development branch:** `fix/moving-average-shift-0.1.0-mas0`

## Evidence baseline

The immutable TradingView extraction remains under `archive/`:
- discovered: 53
- exported: 53
- failed: 0
- principal/core: 6
- mode: `pine-facade / read-only`

Never edit archived Pine files to represent new behavior.

## Accepted reboot baselines

### SignalGate Dashboard 0.1.0

Path: `src/core/signalgate-dashboard.pine`

Status: **ACCEPTED**

Validation summary:
- static transformation invariants: PASS
- archive/source integrity: PASS
- Pine v6 TradingView server compile: PASS (0 errors / 0 warnings)
- Bias safe-clamp 1D default case: PASS
- manual Structure/Trigger lower-TF guards: PASS
- 15m/1H/4H reload visual/state matrix: PASS for closed-history/rendered state
- 15m bar-close HEARTBEAT transport: PASS and repeatable on two consecutive closes
- alert edge invariants: PASS
- live event-specific samples: tracked non-blocking in issue #4

Scope note:
- SignalGate 0.1.0 closes SG-0 timeframe/confirmation hardening only.
- score weights, GO/WATCH thresholds, Mode C persistence, MSS semantics, stale breakout expiry, score overlap and market-efficacy calibration remain future work.

Reference:
- `docs/worklog/2026-09-22-signalgate-sg0-timeframe-hardening.md`

## Active candidate

### Moving Average Shift 0.1.0 / MAS-0

Path: `src/core/moving-average-shift.pine`

Scope:
- restore reachable default signal path
- make Setup filter acceleration-based instead of sign-based
- remove invalid percentile warmup fallback
- close-confirm C/V entry markers
- remove probability terminology from deterministic strength conditions

The raw signal algorithms themselves are intentionally unchanged.

See `docs/worklog/2026-09-22-moving-average-shift-mas0.md`.

## Version lineage

Pre-reboot TradingView metadata and in-script version labels are historical evidence only.

For each core script:
- `0.1.0` = first accepted reboot baseline
- `0.x` = stabilization and controlled evolution
- `1.0.0` = only after compile, timing/repaint, visual, alert and acceptance gates close

# Canonical State

**Date:** 2026-09-22  
**Phase:** Initial reboot audit  
**Working branch:** `audit/initial-reboot`

## Evidence baseline

The TradingView extraction is preserved under `archive/`:
- discovered: 53
- exported: 53
- failed: 0
- principal/core: 6
- mode: `pine-facade / read-only`

The archive is immutable. Development happens only after a source is promoted into `src/core/`.

## Version reset

Pre-reboot TradingView metadata and in-script labels remain historical evidence only.

For every core script:
- `0.1.0` = first promoted reboot candidate/baseline
- `0.x` = stabilization and controlled evolution
- `1.0.0` = only after compile, timing/repaint, visual, alert and acceptance gates close

No active Pine source is promoted in this foundation commit because the audit found blockers.

## First destination

**SignalGate Dashboard**.

Before changing weights or features, its first milestone is a deterministic timeframe/request layer:
- explicit confirmed-vs-live HTF policy
- runtime timeframe validation
- correct LTF handling
- trigger events tied to the intended trigger-bar boundary

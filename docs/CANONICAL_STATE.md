# Canonical State

**Date:** 2026-09-22  
**Phase:** SignalGate SG-0 — deterministic timeframe hardening  
**Main baseline:** foundation/audit merged at `2f9029b1bfe5f9a17617253fd43201554042e2a8`  
**Working branch:** `feat/signalgate-0.1.0-sg0`

## Evidence baseline

The immutable TradingView extraction remains under `archive/`:
- discovered: 53
- exported: 53
- failed: 0
- principal/core: 6
- mode: `pine-facade / read-only`

Never edit archived Pine files to represent new behavior.

## Version lineage

Pre-reboot TradingView metadata and in-script version labels are historical evidence only.

For every rebooted core script:
- `0.1.0` = first reboot candidate
- `0.x` = stabilization and controlled evolution
- `1.0.0` = only after compile, timing/repaint, visual, alert and acceptance gates close

## Active candidate

### SignalGate Dashboard 0.1.0 / SG-0

Path: `src/core/signalgate-dashboard.pine`

Scope is intentionally narrow:
- confirmed HTF request policy
- no implicit lower-timeframe `request.security()`
- safe Auto Trigger / Auto Structure mappings
- Bias TF safe-clamp to chart TF when configured below chart
- runtime guards for invalid manual Structure/Trigger timeframe combinations
- confirmed structure/trigger state commits
- chart-close alert and telemetry gates
- explicit PREVIEW/FECHADA bar state in panel

The scoring model, thresholds and market-logic weights have **not** been redesigned yet.

## Gate status

- Foundation archive/provenance: **PASS**
- Initial 53-script static audit: **PASS with blockers documented**
- SignalGate SG-0 transformation invariants: **PASS (static)**
- Bias safe-clamp 1D default case: **PASS (interactive)**
- Manual Structure/Trigger lower-TF guards: **PASS (interactive)**
- Repository integrity automation: **PASS** (latest push + PR runs)
- Pine v6 TradingView server compile: **PASS** — errors 0, warnings 0 (GitHub Actions)
- Realtime vs reload parity: **PASS for SG-0 scope** — 15m/1H/4H closed-history/rendered state stable; 15m bar-close telemetry repeatable
- Alert regression: **PASS for SG-0 release scope** — transport, close gating, edge invariants and repeatability verified; natural event samples tracked post-merge in #4
- Visual/state regression: **PASS for SG-0 scope** — 15m/1H/4H reload matrix stable; 1D safe-clamp and manual lower-TF guards validated
- Market efficacy validation: **NOT STARTED**

## Merge rule

All SG-0 release-blocking gates are closed. PR #2 is eligible for promotion to `main`. Event-specific live-alert observations continue in #4 without blocking the accepted 0.1.0 baseline.

See `docs/worklog/2026-09-22-signalgate-sg0-timeframe-hardening.md`.

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
- runtime guards for invalid manual timeframe combinations
- confirmed structure/trigger state commits
- chart-close alert and telemetry gates
- explicit PREVIEW/FECHADA bar state in panel

The scoring model, thresholds and market-logic weights have **not** been redesigned yet.

## Gate status

- Foundation archive/provenance: **PASS**
- Initial 53-script static audit: **PASS with blockers documented**
- SignalGate SG-0 transformation invariants: **PASS (static)**
- Repository integrity automation: **PASS** (latest push + PR runs)
- Pine v6 TradingView server compile: **PASS** — errors 0, warnings 0 (GitHub Actions)
- Realtime vs reload parity: **PENDING — interactive chart gate**
- Alert regression: **PENDING**
- Visual/state regression: **PENDING**
- Market efficacy validation: **NOT STARTED**

## Merge rule

The SG-0 feature PR remains draft until compile and timing/reload gates pass. No SG-0 code is considered accepted merely because static checks pass.

See `docs/worklog/2026-09-22-signalgate-sg0-timeframe-hardening.md`.

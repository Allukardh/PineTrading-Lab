# PineTrading-Lab

Private engineering lab for TradingView/Pine Script indicators used as decision-support in cryptocurrency trading.

## Principles

- **GitHub is canonical.**
- **No silent edits:** behavioral changes are reviewable and documented.
- **Archive is immutable:** the 2026-09-22 TradingView extraction is the pre-reboot evidence baseline.
- **Version reboot:** legacy script versions are historical only. Active core scripts restart at **0.1.0** when promoted into `src/core/`.
- **Determinism before features:** timeframe semantics, repaint behavior, alert timing and state transitions are validated before strategy refinement.
- **Code quality != trading edge:** technical correctness and market efficacy are tested separately.
- **Third-party provenance is preserved:** archived donor/reference scripts retain original notices and are not automatically relicensed.

## Snapshot

- 53 scripts
- 12663 source lines
- 657404 source characters
- 6 core reboot targets
- 47 reference/donor scripts
- export: 53/53 successful, 0 failures

## Product architecture

The reboot now targets a three-part suite instead of six independent end-user indicators:

- **Market Map** — trend/regime, structure, structural liquidity, correction/retest zones, targets and invalidation.
- **Execution** — momentum, RSI/exhaustion, volume participation and entry confirmation.
- **Decision Panel** — concise semantic synthesis of Market Map + Execution.

SignalGate Dashboard 0.1.0 is the accepted timing-safe synthesis baseline. The next implementation focus is **Market Map**, using MA 6x as the operator-familiar trend layer and Fibonacci as a first-class Correction Engine input.

See:
- `docs/TRADING_SYSTEM_DESIGN.md`
- `docs/DEFAULTS_AND_PROFILES.md`
- `docs/audit/2026-09-22-initial-audit.md`.

## Repository layout

- `archive/raw/` — immutable TradingView JSON export
- `archive/sources/core/` — exact pre-reboot core Pine sources
- `archive/sources/reference/` — exact pre-reboot donor/reference sources
- `src/core/` — active reboot sources; intentionally empty until promotion
- `docs/` — canonical state, suite architecture, defaults/profiles, extraction, versioning, testing, catalog, audits
- `tools/tradingview-export/` — read-only extractor and local splitter
- `manifests/` — machine-readable import inventory

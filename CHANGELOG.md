# Changelog

All notable project changes are documented here.

## [Unreleased]

### Added
- Professional reboot repository structure.
- Immutable 2026-09-22 TradingView snapshot.
- Exact archival split of all 53 Pine sources.
- Full script catalog and initial static audit.
- Extraction/recovery tooling.
- Provenance safeguards and validation gates.
- SignalGate Dashboard reboot candidate `0.1.0` (SG-0).
- Repository integrity checker and GitHub Actions static-integrity workflow.
- Read-only-current-editor / non-saving TradingView server compile helper for Gate 2 validation.

### Changed
- Active version lineage reset. Every core script begins at `0.1.0` when first promoted from archive into `src/core/`.
- SignalGate HTF data policy now uses confirmed higher-timeframe values (`[1] + lookahead_on`) instead of unconfirmed realtime HTF values.
- SignalGate auto Trigger/Structure mappings no longer silently select timeframes below the chart.
- SignalGate state-changing trigger/structure events commit on confirmed context boundaries.
- SignalGate `alertcondition()` and telemetry paths are explicitly chart-close gated.

### Fixed
- SignalGate no longer uses `request.security()` as an implicit lower-timeframe sampler when Auto Trigger is enabled on charts above 1H.

### Integrity
- No TradingView cookies/session tokens, API keys, exchange keys, webhook secrets, or other credentials are stored.

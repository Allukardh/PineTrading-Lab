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

### Changed
- Active version lineage reset. Every core script begins at `0.1.0` when first promoted from archive into `src/core/`.

### Integrity
- No TradingView cookies/session tokens, API keys, exchange keys, webhook secrets, or other credentials are stored.

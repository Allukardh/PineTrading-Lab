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

The reboot now reduces the six legacy end-user indicators to **two runtime indicators carrying three logical layers**:

- **Market Map** — chart overlay for trend/regime, structure, structural liquidity, correction/retest zones, targets and invalidation; it also owns the embedded semantic Decision Panel.
- **Execution** — lower-pane timing engine for momentum, RSI/exhaustion, volume participation and entry confirmation.
- **Decision Panel** — a logical synthesis layer embedded in Market Map, **not a third mandatory indicator/script**.

SignalGate Dashboard 0.1.0 is the accepted timing-safe synthesis baseline. The active product focus is **Market Map**. Legacy MA 6x, Fibonacci and the other archived scripts are research evidence/donors, not compatibility requirements; the project is free to change periods, visual language and correction logic when evidence supports a better design. The exact unmerged candidate checkpoint lives in `docs/CHAT_HANDOFF.md`.

See:
- `docs/TRADING_SYSTEM_DESIGN.md`
- `docs/DEFAULTS_AND_PROFILES.md`
- `docs/audit/2026-09-22-initial-audit.md`.



## Continuity after a chat interruption

The repository contains an explicit continuation system so a future chat does not need old transcripts to reconstruct either the engineering state **or the working method**.

Resume in this exact order:

1. `README.md`
2. `docs/CANONICAL_STATE.md`
3. `docs/CONTINUITY_LOG.md`
4. `docs/CHAT_HANDOFF.md`
5. the active PR/branch documents named by the handoff

Roles:

- `docs/CONTINUITY_LOG.md` is **slow memory**: causal history, product rationale, rejected routes and the operator/assistant working contract.
- `docs/CHAT_HANDOFF.md` is **fast memory**: current refs, last durable result, in-flight work and the exact next atomic discriminant.

### Write-ahead durability rule

For any substantial engineering block whose interruption would force meaningful reconstruction, the **first durable action** is to update `docs/CHAT_HANDOFF.md` on `main` with a PREPARED checkpoint before the block starts.

That checkpoint records:
- current active branch/PR heads;
- the last verified durable result;
- the next atomic action;
- expected workflow/artifact/evidence;
- whether operator evidence is required;
- recovery instructions if the chat dies mid-block.

After a meaningful milestone, update the handoff again with the actual result and new next discriminant.

If interruption occurs between those two checkpoints, the next chat compares the recorded refs with GitHub's actual refs/runs/artifacts and continues from the delta instead of repeating the previous analysis.

`CONTINUITY_LOG.md` is updated only when causal history, methodology or product decisions change; it must not become a noisy per-commit journal.

## Repository layout

- `archive/raw/` — immutable TradingView JSON export
- `archive/sources/core/` — exact pre-reboot core Pine sources
- `archive/sources/reference/` — exact pre-reboot donor/reference sources
- `src/core/` — active reboot sources; intentionally empty until promotion
- `docs/` — canonical state, suite architecture, defaults/profiles, extraction, versioning, testing, catalog, audits
- `tools/tradingview-export/` — read-only extractor and local splitter
- `manifests/` — machine-readable import inventory

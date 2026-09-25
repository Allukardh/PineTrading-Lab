# Suite 0.2 Phase G — TradingView Validation Gate

**Status:** manual parity/reload gate  
**Tracking:** Issue #26 / PR #27  
**Candidate head:** `88efeb6e92ec186d46ad2b4b0315cf84dea40970`

## 1. Automated prerequisite — CLOSED

At the candidate head:

- Pine compile — **PASS** run `36199944975`
- Static integrity — **PASS** run `36199944904`
- Market Map v0.2.0 compiles
- Execution v0.2.0 compiles
- cross-script static/default/semantic contract checker passes

No manual validation is allowed to become a tuning session.

## 2. Purpose of the manual gate

This gate does **not** ask whether a particular historical trade would have made money.

It checks only what TradingView itself is uniquely positioned to prove:

1. Market Map embedded operator state and standalone Execution agree on the live chart;
2. reload does not change confirmed semantic state;
3. direct panel is readable with defaults;
4. high-horizon context does not create obvious UI/parity defects;
5. PADRÃO / ANTECIPADO posture does not create cross-script contradiction.

## 3. Scripts

Use both scripts from the same Phase G candidate branch:

- `src/core/market-map.pine`
- `src/core/execution.pine`

Do not mix 0.1 and 0.2 versions.

## 4. Defaults

For the primary matrix:

- Market Map: defaults;
- Execution: defaults;
- response profile: **PADRÃO** in both scripts;
- no style/threshold changes.

BOS/CHoCH secondary details may remain at their default visibility.

## 5. Minimal BTCUSDT matrix

Capture one current-chart screenshot for each:

- **4H**
- **1D**
- **3D**
- **1W**

Each screenshot should show, where practical:
- Market Map panel;
- standalone Execution cue/lower pane;
- current price area;
- Data Window if it can remain readable without obscuring the chart.

Do not search history for a prettier signal. Current state is sufficient for parity.

## 6. What must agree

User-facing semantic parity:

- direction / side;
- ACTION/readiness;
- opportunity class when one exists;
- management state when one exists;
- no contradictory unified CONFIRMA;
- no Execution cue claiming an opposite direction from Market Map.

Audit parity, when visible:
- operator readiness code;
- operator direction;
- conflict state;
- raw confirm event;
- selected source path;
- management active/state/direction;
- anchor capability;
- target/invalidation when available;
- monthly macro context on 3D/1W where available.

The standalone Execution may remain visually more compact. Text layout does not need to match Market Map; **semantic state does**.

## 7. Reload check

After recording the PADRÃO 4H state:

1. keep BTCUSDT 4H;
2. reload TradingView/browser/chart so scripts are recalculated from history;
3. do not change inputs;
4. capture the same view again.

Hard PASS:
- confirmed Market Map operator state unchanged;
- standalone Execution confirmed state unchanged;
- management state/anchors unchanged where active;
- both scripts still agree.

Realtime-only transient chart behavior is not allowed to rewrite confirmed history.

## 8. ANTECIPADO sanity check

On BTCUSDT 4H:

1. set **both scripts** to `ANTECIPADO`;
2. capture one screenshot;
3. do not tune any other input.

Expected semantics:
- ANTECIPADO may surface an earlier posture only for accepted TREND scope;
- it may not create a fake PADRÃO CONFIRMA;
- it may not start Thesis Management;
- RANGE_ROTATION / REGIME_REVERSAL / frozen pullback path are not made aggressive merely because the profile changed.

If the current 4H chart has no qualifying trend opportunity, no visible difference from PADRÃO is itself valid.

## 9. 1W scope sanity

Even if the selector is later switched to ANTECIPADO for a diagnostic:
- 1W must remain PADRÃO behavior;
- no anticipated posture is valid on 1W.

The primary screenshot remains PADRÃO; no extra 1W profile screenshot is required unless an anomaly appears.

## 10. Evidence interpretation

PASS if:
- 4H/1D/3D/1W show no cross-script semantic contradiction;
- 4H reload parity is stable;
- 4H ANTECIPADO behavior is either coherently scoped or inactive;
- no obvious direct-panel defect appears.

REFINE if:
- one script disagrees with the other on the same confirmed bar;
- reload changes a confirmed state/anchor;
- ANTECIPADO creates management or a fake CONFIRMA;
- high-horizon UI exposes contradictory state.

Do not change thresholds based on these screenshots.

## 11. After PASS

Then:
1. record manual evidence;
2. create/update `docs/GUIA_DO_OPERADOR.md` in Portuguese;
3. reconcile PR #27 with current main if required;
4. rerun final Static integrity + Pine compile;
5. promote only after the operator guide and final gate are complete.

# Suite 0.2 Phase G — TradingView Validation Gate

**Status:** manual parity/reload gate  
**Tracking:** Issue #26 / PR #27  
**Initial compiled candidate head:** `88efeb6e92ec186d46ad2b4b0315cf84dea40970`  
**Runtime-repaired candidate head:** `42b8ebb3812395cf17520626368456e003930ab2`

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


## 12. Runtime plot-count blocker and repair

The first TradingView load exposed a runtime-only implementation defect that Pine compile did not reject:

- Market Map: **RE10140**, 94 plot counts > TradingView limit 64;
- Execution: **RE10140**, 82 plot counts > TradingView limit 64.

Classification:
- instrumentation / translation defect;
- not a research-semantic defect;
- no threshold, opportunity, readiness, profile or management retuning authorized.

Repair:
- reduced redundant Data Window plot telemetry while preserving operator/cross-script parity fields;
- Market Map source-level plot-producing calls: **53**;
- Execution source-level plot-producing calls: **43**;
- added conservative static budget guard: **<=55** source-level plot-producing calls per script.

Post-repair automated evidence:
- Pine compile `36202404753` — **PASS**;
- Static integrity `36202404767` — **PASS**.

BTCUSDT 4H PADRÃO runtime smoke after repair:
- both scripts rendered;
- RE10140 did not recur;
- screenshot was retained as the official 4H PADRÃO matrix capture.

## 13. Final TradingView matrix — PASS

Operator evidence used both Suite 0.2 scripts from the same repaired Phase G branch, defaults unchanged unless explicitly noted.

### BTCUSDT 4H — PADRÃO

Market Map:
- CENÁRIO: **MISTO / CONFLITO**
- OPORTUNIDADE: **NENHUMA**
- LADO: **—**
- AÇÃO: **AGUARDAR**
- GESTÃO: **—**

Execution:
- **AGUARDAR**

Result:
- cross-script semantic parity **PASS**.

### BTCUSDT 1D — PADRÃO

Market Map:
- CENÁRIO: **ALTA**
- OPORTUNIDADE: **NENHUMA**
- LADO: **COMPRA / LONG**
- AÇÃO: **PREPARANDO LONG**
- GESTÃO: **—**

Execution:
- **PREPARANDO LONG**

Result:
- direction/readiness parity **PASS**.

### BTCUSDT 3D — PADRÃO

Market Map:
- CENÁRIO: **TRANSIÇÃO ↑ • MACRO NEUTRO**
- OPORTUNIDADE: **NENHUMA**
- LADO: **COMPRA / LONG**
- AÇÃO: **PREPARANDO LONG**
- GESTÃO: **—**

Execution:
- **PREPARANDO LONG • MACRO NEUTRO**

Result:
- direction/readiness and monthly-macro presentation parity **PASS**.

### BTCUSDT 1W — PADRÃO

Market Map:
- CENÁRIO: **ALTA**
- OPORTUNIDADE: **NENHUMA**
- LADO: **COMPRA / LONG**
- AÇÃO: **ARMADO LONG**
- GESTÃO: **—**

Execution:
- **ARMADO LONG**

Result:
- high-horizon PADRÃO parity **PASS**.
- no unsupported anticipated posture is present.

### BTCUSDT 4H — reload, PADRÃO unchanged

After TradingView/browser reload with inputs unchanged:

Market Map:
- **MISTO / CONFLITO**
- **NENHUMA**
- **AGUARDAR**
- **GESTÃO —**

Execution:
- **AGUARDAR**

The current realtime candle/price had progressed between captures, but the confirmed semantic state remained the same.

Result:
- confirmed reload parity **PASS**.

### BTCUSDT 4H — ANTECIPADO

Both scripts switched to ANTECIPADO; no other input changed.

Market Map:
- CENÁRIO: **MISTO / CONFLITO**
- OPORTUNIDADE: **NENHUMA**
- AÇÃO: **AGUARDAR**
- GESTÃO: **—**

Execution:
- **AGUARDAR**

Interpretation:
- current 4H chart had no qualifying TREND opportunity for scoped early posture;
- therefore no visible change from PADRÃO is valid;
- no fake PADRÃO CONFIRMA;
- no management started;
- no cross-script contradiction.

Result:
- ANTECIPADO scope sanity **PASS**.

## 14. Supplemental cross-asset 4H sanity

Additional current-chart PADRÃO screenshots were supplied for ETH, AVAX, XRP, SUI, DOT, DOGE, NEAR, SOL and HBAR.

Observed combinations exercised:
- WAIT / AGUARDAR;
- PREP / PREPARANDO;
- ARMED / ARMADO;
- active CONTINUIDADE management;
- MISTO / CONFLITO;
- TRANSIÇÃO;
- ALTA;
- CORREÇÃO;
- RETESTE / RECLAIM.

No obvious Market Map ↔ Execution semantic contradiction was observed.

These screenshots are supplemental robustness evidence only. They did not authorize retuning and do not replace the BTCUSDT matrix.

## 15. Phase G manual decision

**TradingView manual parity/reload/profile gate: PASS.**

Closed conditions:
- runtime plot-count defect repaired;
- 4H / 1D / 3D / 1W no visible cross-script contradiction;
- 4H reload preserves confirmed semantic state;
- ANTECIPADO remains correctly scoped/inactive when unsupported by current opportunity context;
- direct Market Map panel remains readable;
- Execution remains a compact cue rather than a duplicate full panel.

Next:
1. create `docs/GUIA_DO_OPERADOR.md` in Portuguese;
2. reconcile PR #27 with current `main`;
3. rerun final Static integrity + Pine compile;
4. promote Suite 0.2 only if final gates remain green.

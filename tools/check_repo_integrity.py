#!/usr/bin/env python3
"""Repository-level deterministic checks for PineTrading-Lab.

No external packages required.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def norm(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def main() -> None:
    raw_path = ROOT / "archive/raw/TradingView_Pine_Backup_2026-09-22.json"
    manifest_path = ROOT / "manifests/import-2026-09-22.json"

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    totals = raw.get("totals", {})
    if totals.get("discovered") != 53 or totals.get("exported") != 53 or totals.get("failed") != 0:
        fail(f"unexpected archive totals: {totals}")

    raw_scripts = raw.get("scripts", [])
    manifest_scripts = manifest.get("scripts", [])
    if len(raw_scripts) != 53 or len(manifest_scripts) != 53:
        fail("archive/manifest script count mismatch")

    by_index = {item["index"]: item for item in manifest_scripts}
    for index, script in enumerate(raw_scripts, 1):
        item = by_index.get(index)
        if item is None:
            fail(f"manifest missing index {index}")
        path = ROOT / item["path"]
        if not path.is_file():
            fail(f"missing archived source: {item['path']}")
        archived = norm(path.read_text(encoding="utf-8"))
        exported = norm(script.get("source") or "")
        if archived != exported:
            fail(f"archive source differs from raw export at index {index}: {item['name']}")

    sg_path = ROOT / "src/core/signalgate-dashboard.pine"
    if sg_path.exists():
        sg = norm(sg_path.read_text(encoding="utf-8"))
        required = [
            'indicator("SignalGate Dashboard v0.1.0"',
            'sgDashVer = "0.1.0"',
            '_expr[1], barmerge.gaps_off, barmerge.lookahead_on',
            'Trigger TF must be equal to or higher than the chart TF in SG-0',
            'DATAPOLICY=CONFIRMED_HTF',
            'if logOn and barstate.isconfirmed',
            'fakeoutEvt = fakeout and not fakeout[1]',
            'alFake and fakeoutEvt',
            'string tf_bias1_eff = bias1CfgSec < chartTfSec ? timeframe.period : tf_bias1',
            'string tf_bias2_eff = bias2CfgSec < chartTfSec ? timeframe.period : tf_bias2',
            'ema200_bias1 = f_sec(tf_bias1_eff',
            'ema200_bias2 = f_sec(tf_bias2_eff',
            'Bias clamp: SIM',
        ]
        for token in required:
            if token not in sg:
                fail(f"SignalGate SG-0 invariant missing: {token}")

        forbidden = [
            'request.security(syminfo.tickerid, _tf, _expr, barmerge.gaps_off, barmerge.lookahead_off)',
            'SignalGate Dashboard v4.9.1',
            'alFake and fakeout,',
            'Bias TF #1 must be equal to or higher than the chart TF',
            'Bias TF #2 must be equal to or higher than the chart TF',
        ]
        for token in forbidden:
            if token in sg:
                fail(f"SignalGate SG-0 forbidden legacy pattern present: {token}")

        alert_lines = [line.strip() for line in sg.splitlines() if "alertcondition(" in line]
        if not alert_lines:
            fail("SignalGate contains no alertcondition() calls")
        for line in alert_lines:
            if "alertcondition(alertBarOk and " not in line:
                fail(f"ungated alertcondition: {line}")

        # Event alerts must be transition/edge driven rather than persistent-state driven.
        event_edge_invariants = [
            'goLongEvt   = (verdict == "LONG")  and (verdict[1] != "LONG")',
            'goShortEvt  = (verdict == "SHORT") and (verdict[1] != "SHORT")',
            'earlyLongEvt  = (state == "🟡 EARLY LONG")  and (state[1] != "🟡 EARLY LONG")',
            'earlyShortEvt = (state == "🟡 EARLY SHORT") and (state[1] != "🟡 EARLY SHORT")',
            'watchEvt    = (state == "⚠️ WATCH") and (state[1] != "⚠️ WATCH")',
            'noTradeEvt  = (state == "⛔ NO-TRADE") and (state[1] != "⛔ NO-TRADE")',
            'breakUpEvt    = breakUp and not breakUp[1]',
            'breakDownEvt  = breakDown and not breakDown[1]',
            'retestUpEvt   = retestUp and not retestUp[1]',
            'retestDownEvt = retestDown and not retestDown[1]',
            'fakeoutEvt = fakeout and not fakeout[1]',
            'ipStartEvt  = (inDir != 0) and (inDir[1] == 0)',
            'ipEndEvt    = (inDir == 0) and (inDir[1] != 0)',
        ]
        for token in event_edge_invariants:
            if token not in sg:
                fail(f"SignalGate event-edge invariant missing: {token}")

    mm_path = ROOT / "src/core/market-map.pine"
    if mm_path.exists():
        mm = norm(mm_path.read_text(encoding="utf-8"))
        required_mm = [
            'indicator("Market Map v0.1.0"',
            '_expr[1], barmerge.gaps_off, barmerge.lookahead_on',
            'int FAST_LEN = 21',
            'int MID_LEN = 50',
            'int SLOW_LEN = 200',
            'string contextTf = chartSec <= tf15Sec ? "60"',
            'bool alreadySwept = postPivotHigh > ph + syminfo.mintick',
            'bool alreadySwept = postPivotLow < pl - syminfo.mintick',
            'float fibT2Top = correctionReady ? math.max(fib500, fib618) : na',
            'float fibT2Bottom = correctionReady ? math.min(fib500, fib618) : na',
            'string correctionBaseModel = empiricalReady ? "ADAPT "',
            'string correctionModel = correctionReady ? (useLiveImpulse ? "LIVE/" : "")',
            'f_impulse_acceptance(_startBar, _endBar, _low, _high)',
            'correctionConfluence += f_in_zone(emaMid, primaryTop, primaryBottom, zoneTol) ? 1 : 0',
            'phaseTxt := close > impulseHigh ? "ROMPIMENTO / IMPULSO"',
            'table.cell(panel, 0, 1, "REGIME"',
            'table.cell(panel, 0, 4, "CORREÇÃO"',
            'table.cell(panel, 0, 5, "DESTINO"',
            'table.cell(panel, 0, 6, "LIQ ↑"',
            'table.cell(panel, 0, 8, "INVALIDA"',
            'liqAboveSource := "PDH"',
            'liqAboveSource := "PWH"',
            'liqBelowSource := "PDL"',
            'liqBelowSource := "PWL"',
            'float liqAbove2 = na',
            'float liqBelow2 = na',
            'float destination1 = mapDir == 1 ? liqAbove : mapDir == -1 ? liqBelow : na',
            'bool destinationNear = not na(destinationDistanceAtr) and destinationDistanceAtr <= TARGET_NEAR_ATR',
            'string activeDestinationTxt = thesisInvalidated ? "—" : destinationTxt',
            'bool acceptanceEvidenceReady = acceptanceReady and barstate.isconfirmed',
            'bool destinationHitEvt = destinationHitUp or destinationHitDown',
            '"ATINGIDO " + f_price(destinationHitLevel)',
            'int impulseKey = correctionReady and not na(impulseStartBar) ? impulseStartBar * 3 + (mapDir + 1) : na',
            'var int diagTheses = 0',
            'var int diagAmbiguousOutcomes = 0',
            'diagTrackedDestination := prevTargetUsable ? destination1[1] : destination1',
            'bool diagAmbiguousNow = not diagOutcomeResolved',
            'float diagOpenAfterZone = math.max(0, diagZoneTouches - diagResolvedAfterZone - diagAmbiguousOutcomes)',
            'float diagZoneTouchPct = diagTheses > 0 ? 100.0 * diagZoneTouches / diagTheses : na',
            'float diagAvgBarsToOutcome = diagOutcomeBarsCount > 0 ? 1.0 * diagOutcomeBarsSum / diagOutcomeBarsCount : na',
            'float diagZoneReactionPct = diagResolvedAfterZone > 0 ? 100.0 * diagZoneToDestination / diagResolvedAfterZone : na',
            'plot(mapDir, "MM Audit • MapDir"',
            'plot(diagZoneTouchNow ? 1 : 0, "MM Audit • Toque zona evt"',
            'plot(diagDestinationResolvedNow ? 1 : 0, "MM Audit • Zona→Destino evt"',
            'plot(diagAmbiguousOutcomes, "MM Hist • Resultados ambíguos"',
            'plot(diagZoneReactionPct, "MM Hist • Zona→Destino % (engenharia)"',
            'table.cell(panel, 0, 5, "DESTINO"',
            'phaseTxt := "FALSO ROMPIMENTO"',
            'bool bullSwingSequence = lastHighType == "HH" and lastLowType == "HL"',
            '"ALTA • REVERSÃO"',
            '"BAIXA • REVERSÃO"',
            'bool regimeStructureConflict = regimeDir != 0 and structureDir != 0 and regimeDir != structureDir',
            'phaseTxt := regimeStructureConflict ? "TRANSIÇÃO ESTRUTURAL" : "TRANSIÇÃO"',
            'var int invalidatedImpulseKey = na',
            'phaseTxt := "TESTE DE INVALIDAÇÃO"',
            'phaseTxt := "TESE INVALIDADA"',
            'string contextTxt = contextTf + " • HTF CONF" + (correctionActive ? " • " + correctionModel : "")',
            '// Single semantic panel — no Compact/Full variants',
        ]
        for token in required_mm:
            if token not in mm:
                fail(f"Market Map MM-0 invariant missing: {token}")

        forbidden_mm = [
            'lookahead_off)',
            'Liquidation Map',
            'probability',
            'probabilidade',
            'compactPanel',
            'fullPanel',
            'Painel compacto',
            'Painel completo',
            'lastStructureEvent',
            'varip ',
            'barstate.isrealtime',
            'timenow',
        ]
        for token in forbidden_mm:
            if token in mm:
                fail(f"Market Map MM-0 forbidden pattern present: {token}")

        operator_inputs = [
            line.strip() for line in mm.splitlines()
            if line.strip().startswith(("showMAs = input.", "showPanel = input.", "showStructureDetails = input."))
        ]
        if len(operator_inputs) != 3:
            fail(f"Market Map should expose exactly 3 operator controls in MM-0, found {len(operator_inputs)}")
        if 'visualMode = input.' in mm:
            fail("Market Map visual-mode dropdown should not exist in MM-0")

    print("PASS: archive integrity + reboot invariants")


if __name__ == "__main__":
    main()

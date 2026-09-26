#!/usr/bin/env python3
"""Validate production Execution Pine against accepted v2/default + suite contracts.

This is a static parity guard. It does not replace Pine compile or TradingView
reload validation; it prevents silent drift in the duplicated self-contained
runtime kernels before those gates.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXEC = ROOT / "src" / "core" / "execution.pine"
MM = ROOT / "src" / "core" / "market-map.pine"
DEFAULTS = ROOT / "manifests" / "execution-research-defaults-v2.json"
SEMANTICS = ROOT / "manifests" / "suite-semantics-v1.json"


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def number(text: str, name: str) -> float:
    pattern = rf"^(?:int|float)\s+{re.escape(name)}\s*=\s*([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)\s*$"
    m = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    if not m:
        fail(f"numeric Pine constant not found: {name}")
    return float(m.group(1))


def expect_num(text: str, name: str, expected: float) -> None:
    actual = number(text, name)
    if actual != float(expected):
        fail(f"{name}: Pine={actual} expected={expected}")


def require(text: str, tokens: list[str], label: str) -> None:
    for token in tokens:
        if token not in text:
            fail(f"{label} token missing: {token}")


PLOT_PRODUCING_CALL_RE = re.compile(
    r"\b(?:plot|plotshape|plotchar|plotbar|plotcandle|bgcolor|fill|alertcondition)\s*\("
)
PLOT_PRODUCING_CALL_BUDGET = 55


def plot_producing_call_count(text: str) -> int:
    """Conservative source-level guard for TradingView's 64 plot-count ceiling.

    Some Pine calls can consume more than one runtime plot count, so the source
    call budget deliberately leaves headroom instead of trying to equal 64.
    """
    total = 0
    for raw_line in text.splitlines():
        code = raw_line.split("//", 1)[0]
        total += len(PLOT_PRODUCING_CALL_RE.findall(code))
    return total


def main() -> int:
    ex = EXEC.read_text(encoding="utf-8").replace("\r\n", "\n")
    mm = MM.read_text(encoding="utf-8").replace("\r\n", "\n")
    defaults = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    semantics = json.loads(SEMANTICS.read_text(encoding="utf-8"))

    ex_plot_calls = plot_producing_call_count(ex)
    mm_plot_calls = plot_producing_call_count(mm)
    if ex_plot_calls > PLOT_PRODUCING_CALL_BUDGET:
        fail(
            f"Execution plot-producing calls={ex_plot_calls} exceed conservative "
            f"budget={PLOT_PRODUCING_CALL_BUDGET}"
        )
    if mm_plot_calls > PLOT_PRODUCING_CALL_BUDGET:
        fail(
            f"Market Map plot-producing calls={mm_plot_calls} exceed conservative "
            f"budget={PLOT_PRODUCING_CALL_BUDGET}"
        )

    if defaults["execution_research_defaults_version"] != 2:
        fail("accepted defaults manifest is not v2")

    require(
        ex,
        [
            'indicator("Execution v0.2.0"',
            "int EXECUTION_CONTRACT = 2",
            "int EXECUTION_DEFAULTS_VERSION = 2",
            'string responseProfile = input.string("PADRÃO", "Perfil de resposta", options=["PADRÃO", "ANTECIPADO"]',
            "_expr[1], barmerge.gaps_off, barmerge.lookahead_on",
            "if barstate.isconfirmed",
            "bool confirmLong = operatorConfirmEvent and operatorDir == 1",
            "bool confirmShort = operatorConfirmEvent and operatorDir == -1",
            "var int trendOppKind = OPP_NONE",
            "var int rangeOppStage = OPP_STAGE_NONE",
            "var int trendReadiness = READY_WAIT",
            "var int rangeReadiness = READY_WAIT",
            "int operatorReadiness = OP_READY_WAIT",
            "bool operatorConflict = false",
            "bool anticipatedPosture = responseProfile == \"ANTECIPADO\"",
            "var bool managementActive = false",
            "var int managementState = MGMT_NONE",
            "managementCapability := not na(mergedTarget) and not na(mergedInvalidation) ? CAP_FULL",
            "rangeIgnitionCount >= 1",
            "trendOppStage >= OPP_STAGE_ACCEPTED",
            "plot(operatorReadiness, \"EX 0.2 • Operator readiness\"",
            "plot(managementState, \"EX 0.2 • Gestão estado\"",
            "plot(mteReady ? mteCore : na, \"Momentum\"",
            'var table statusCue = table.new(position.top_right, 1, 1',
            "f_operator_txt(operatorReadiness, operatorDir)",
        ],
        "Execution",
    )

    forbidden = [
        "lookahead_off)",
        "input.source(",
        "varip ",
        "timenow",
        "probability",
        "probabilidade",
        "Compact",
        "Full panel",
    ]
    for token in forbidden:
        if token in ex:
            fail(f"forbidden Execution production pattern present: {token}")

    # Threshold/configuration inputs must not leak into normal operator UX.
    # Suite 0.2 intentionally exposes exactly one semantic posture selector.
    threshold_inputs = [
        line.strip()
        for line in ex.splitlines()
        if re.search(r"\binput\.(?:int|float|string|source)\(", line)
        and "Perfil de resposta" not in line
    ]
    if threshold_inputs:
        fail(f"Execution exposes forbidden normal threshold/source inputs: {threshold_inputs}")

    profile_inputs = [
        line.strip()
        for line in ex.splitlines()
        if "input.string(" in line and "Perfil de resposta" in line
    ]
    if len(profile_inputs) != 1:
        fail(f"Execution must expose exactly one response-profile selector: {profile_inputs}")

    # Exact accepted component defaults.
    mte = defaults["momentum_turn"]
    for pine_name, key in [
        ("MTE_FAST_EMA", "fast_ema"),
        ("MTE_SLOW_EMA", "slow_ema"),
        ("MTE_ATR_LEN", "atr_length"),
        ("MTE_ACTIVITY_LEN", "activity_rma"),
        ("MTE_NEUTRAL_FACTOR", "neutral_factor"),
        ("MTE_TURN_FACTOR", "turn_factor"),
        ("MTE_TURN_FLOOR", "turn_floor"),
        ("MTE_ACCEL_EPS", "accel_epsilon"),
    ]:
        expect_num(ex, pine_name, mte[key])

    rsi = defaults["rsi"]
    for pine_name, key in [
        ("RSI_LEN", "length"),
        ("RSI_CENTER_LOW", "center_deadband_low"),
        ("RSI_CENTER_HIGH", "center_deadband_high"),
        ("RSI_OVERBOUGHT", "overbought"),
        ("RSI_OVERSOLD", "oversold"),
        ("RSI_EXTREME_OVERBOUGHT_LEVEL", "extended_overbought"),
        ("RSI_EXTREME_OVERSOLD_LEVEL", "extended_oversold"),
        ("RSI_MIN_STEP", "minimum_directional_step"),
        ("RSI_ZONE_MEMORY_BARS", "zone_memory_bars"),
    ]:
        expect_num(ex, pine_name, rsi[key])

    pse = defaults["participation"]
    for pine_name, key in [
        ("PSE_VOLUME_EMA_LEN", "baseline_length"),
        ("PSE_CONTRACTED_BELOW", "contracted_below"),
        ("PSE_EXPANDED_AT_OR_ABOVE", "expanded_at_or_above"),
        ("PSE_STRONG_AT_OR_ABOVE", "strong_at_or_above"),
        ("PSE_PRESSURE_MIN", "pressure_min"),
    ]:
        expect_num(ex, pine_name, pse[key])

    bridge = defaults["market_map_execution_bridge"]
    expect_num(ex, "EX_APPROACH_ATR", bridge["approach_distance_atr"])
    expect_num(ex, "EX_EVENT_HOLD_BARS", bridge["event_hold_bars"])

    # Market Map constants that the self-contained Execution context must mirror.
    parity = [
        ("MID_LEN", "MM_MID_LEN"),
        ("SLOW_LEN", "MM_SLOW_LEN"),
        ("ATR_LEN", "MM_ATR_LEN"),
        ("PIVOT_LEN", "MM_PIVOT_LEN"),
        ("POOL_MAX", "MM_POOL_MAX"),
        ("RETEST_MAX_BARS", "MM_RETEST_MAX_BARS"),
        ("FAIL_MAX_BARS", "MM_FAIL_MAX_BARS"),
        ("PULLBACK_SAMPLE_MAX", "MM_PULLBACK_SAMPLE_MAX"),
        ("PULLBACK_MIN_SAMPLES", "MM_PULLBACK_MIN_SAMPLES"),
        ("EQ_TOL_ATR", "MM_EQ_TOL_ATR"),
        ("RETEST_TOL_ATR", "MM_RETEST_TOL_ATR"),
        ("FAIL_TOL_ATR", "MM_FAIL_TOL_ATR"),
        ("INVALID_TOL_ATR", "MM_INVALID_TOL_ATR"),
        ("TARGET_NEAR_ATR", "MM_TARGET_NEAR_ATR"),
        ("PULLBACK_MIN_DEPTH", "MM_PULLBACK_MIN_DEPTH"),
        ("PULLBACK_MAX_DEPTH", "MM_PULLBACK_MAX_DEPTH"),
    ]
    for mm_name, ex_name in parity:
        a = number(mm, mm_name)
        b = number(ex, ex_name)
        if a != b:
            fail(f"Market Map/Execution context drift: {mm_name}={a} {ex_name}={b}")

    require(
        ex,
        [
            "bool mmRegimeStructureConflict = mmRegimeDir != 0 and mmStructureDir != 0 and mmRegimeDir != mmStructureDir",
            "int mapDir = mmRegimeStructureConflict ? 0 : mmRegimeDir != 0 ? mmRegimeDir : mmStructureDir",
            "int mmImpulseKey = mmCorrectionReady and not na(mmImpulseStartBar) ? mmImpulseStartBar * 3 + (mapDir + 1) : na",
            "bool thesisInvalidated = mmCorrectionReady and not na(mmImpulseKey) and mmInvalidatedImpulseKey == mmImpulseKey",
            "bool mmDestinationNear = not na(mmDestinationDistanceAtr) and mmDestinationDistanceAtr <= MM_TARGET_NEAR_ATR",
        ],
        "Market Map slim context",
    )

    # Embedded Decision Panel consumer must use the same accepted defaults.
    embedded_pairs = [
        ("MTE_FAST_EMA", "EX_MTE_FAST_EMA"),
        ("MTE_SLOW_EMA", "EX_MTE_SLOW_EMA"),
        ("MTE_ATR_LEN", "EX_MTE_ATR_LEN"),
        ("MTE_ACTIVITY_LEN", "EX_MTE_ACTIVITY_LEN"),
        ("MTE_NEUTRAL_FACTOR", "EX_MTE_NEUTRAL_FACTOR"),
        ("MTE_TURN_FACTOR", "EX_MTE_TURN_FACTOR"),
        ("MTE_TURN_FLOOR", "EX_MTE_TURN_FLOOR"),
        ("MTE_ACCEL_EPS", "EX_MTE_ACCEL_EPS"),
        ("RSI_LEN", "EX_RSI_LEN"),
        ("RSI_CENTER_LOW", "EX_RSI_CENTER_LOW"),
        ("RSI_CENTER_HIGH", "EX_RSI_CENTER_HIGH"),
        ("RSI_OVERBOUGHT", "EX_RSI_OVERBOUGHT"),
        ("RSI_OVERSOLD", "EX_RSI_OVERSOLD"),
        ("RSI_EXTREME_OVERBOUGHT_LEVEL", "EX_RSI_EXTREME_OVERBOUGHT_LEVEL"),
        ("RSI_EXTREME_OVERSOLD_LEVEL", "EX_RSI_EXTREME_OVERSOLD_LEVEL"),
        ("RSI_MIN_STEP", "EX_RSI_MIN_STEP"),
        ("RSI_ZONE_MEMORY_BARS", "EX_RSI_ZONE_MEMORY_BARS"),
        ("PSE_VOLUME_EMA_LEN", "EX_PSE_VOLUME_EMA_LEN"),
        ("PSE_CONTRACTED_BELOW", "EX_PSE_CONTRACTED_BELOW"),
        ("PSE_EXPANDED_AT_OR_ABOVE", "EX_PSE_EXPANDED_AT_OR_ABOVE"),
        ("PSE_PRESSURE_MIN", "EX_PSE_PRESSURE_MIN"),
        ("EX_APPROACH_ATR", "EX_APPROACH_ATR"),
        ("EX_EVENT_HOLD_BARS", "EX_EVENT_HOLD_BARS"),
    ]
    for execution_name, market_name in embedded_pairs:
        a = number(ex, execution_name)
        b = number(mm, market_name)
        if a != b:
            fail(
                f"Execution/embedded Decision Panel default drift: "
                f"{execution_name}={a} {market_name}={b}"
            )

    expect_num(mm, "EX_DEFAULTS_VERSION", 2)

    embedded_semantic_pairs = [
        ("MTE_NEUTRAL", "EX_MTE_NEUTRAL"),
        ("MTE_TURN_UP", "EX_MTE_TURN_UP"),
        ("MTE_UP_ACCEL", "EX_MTE_UP_ACCEL"),
        ("MTE_UP_DECEL", "EX_MTE_UP_DECEL"),
        ("MTE_TURN_DOWN", "EX_MTE_TURN_DOWN"),
        ("MTE_DOWN_ACCEL", "EX_MTE_DOWN_ACCEL"),
        ("MTE_DOWN_DECEL", "EX_MTE_DOWN_DECEL"),
        ("RSI_NEUTRAL", "EX_RSI_NEUTRAL"),
        ("RSI_BULL", "EX_RSI_BULL"),
        ("RSI_RECOVERING_OVERSOLD", "EX_RSI_RECOVERING_OVERSOLD"),
        ("RSI_RECOVERING_OVERBOUGHT", "EX_RSI_RECOVERING_OVERBOUGHT"),
        ("RSI_EXTREME_OVERBOUGHT", "EX_RSI_EXTREME_OVERBOUGHT"),
        ("RSI_EXTREME_OVERSOLD", "EX_RSI_EXTREME_OVERSOLD"),
        ("RSI_FADING_OVERSOLD", "EX_RSI_FADING_OVERSOLD"),
        ("RSI_FADING_OVERBOUGHT", "EX_RSI_FADING_OVERBOUGHT"),
        ("RSI_BEAR", "EX_RSI_BEAR"),
        ("PSE_NEUTRAL", "EX_PSE_NEUTRAL"),
        ("PSE_CONFIRM", "EX_PSE_CONFIRM"),
        ("PSE_WEAK", "EX_PSE_WEAK"),
        ("PSE_CONTRARY", "EX_PSE_CONTRARY"),
        ("READY_WAIT", "EX_READY_WAIT"),
        ("READY_PREP", "EX_READY_PREP"),
        ("READY_ARMED", "EX_READY_ARMED"),
        ("READY_CONFIRMED", "EX_READY_CONFIRMED"),
        ("READY_ALIGNED", "EX_READY_ALIGNED"),
        ("STRENGTH_NORMAL", "EX_STRENGTH_NORMAL"),
        ("STRENGTH_FADING", "EX_STRENGTH_FADING"),
        ("STRENGTH_EXHAUSTED", "EX_STRENGTH_EXHAUSTED"),
        ("STRENGTH_REACTION_RISK", "EX_STRENGTH_REACTION_RISK"),
    ]
    for execution_name, market_name in embedded_semantic_pairs:
        a = number(ex, execution_name)
        b = number(mm, market_name)
        if a != b:
            fail(
                f"Execution/embedded semantic-code drift: "
                f"{execution_name}={a} {market_name}={b}"
            )

    suite_02_pairs = [
        ("OPP_NONE", "EX_OPP_NONE"),
        ("OPP_BREAKOUT_EXPANSION", "EX_OPP_BREAKOUT_EXPANSION"),
        ("OPP_REACCELERATION", "EX_OPP_REACCELERATION"),
        ("OPP_REGIME_REVERSAL", "EX_OPP_REGIME_REVERSAL"),
        ("OPP_RANGE_ROTATION", "EX_OPP_RANGE_ROTATION"),
        ("OPP_STAGE_NONE", "EX_OPP_STAGE_NONE"),
        ("OPP_STAGE_CANDIDATE", "EX_OPP_STAGE_CANDIDATE"),
        ("OPP_STAGE_STRONG", "EX_OPP_STAGE_STRONG"),
        ("OPP_STAGE_ACCEPTED", "EX_OPP_STAGE_ACCEPTED"),
        ("OP_READY_WAIT", "EX_OP_READY_WAIT"),
        ("OP_READY_PREP", "EX_OP_READY_PREP"),
        ("OP_READY_ARMED", "EX_OP_READY_ARMED"),
        ("OP_READY_CONFIRMED", "EX_OP_READY_CONFIRMED"),
        ("OP_READY_ALIGNED", "EX_OP_READY_ALIGNED"),
        ("OP_READY_CONFLICT", "EX_OP_READY_CONFLICT"),
        ("PATH_NONE", "EX_PATH_NONE"),
        ("PATH_FROZEN_0_1", "EX_PATH_FROZEN_0_1"),
        ("PATH_TREND_V2", "EX_PATH_TREND_V2"),
        ("PATH_RANGE_ANY1", "EX_PATH_RANGE_ANY1"),
        ("PATH_MULTI", "EX_PATH_MULTI"),
        ("REVERSAL_PRIOR_REGIME_MIN_BARS", "EX_REVERSAL_PRIOR_REGIME_MIN_BARS"),
        ("REACCELERATION_REGIME_MIN_BARS", "EX_REACCELERATION_REGIME_MIN_BARS"),
        ("BREAK_DECISIVE_ATR", "EX_BREAK_DECISIVE_ATR"),
        ("RANGE_BOUNDARY_DRIFT_MAX", "EX_RANGE_BOUNDARY_DRIFT_MAX"),
        ("RANGE_MIN_HEIGHT_ATR", "EX_RANGE_MIN_HEIGHT_ATR"),
        ("RANGE_EDGE_FRACTION", "EX_RANGE_EDGE_FRACTION"),
        ("MGMT_TARGET_NEAR_ATR", "EX_MGMT_TARGET_NEAR_ATR"),
        ("MGMT_INVALID_WARN_ATR", "EX_MGMT_INVALID_WARN_ATR"),
        ("CAP_NONE", "EX_CAP_NONE"),
        ("CAP_TARGET_ONLY", "EX_CAP_TARGET_ONLY"),
        ("CAP_INVALIDATION_ONLY", "EX_CAP_INVALIDATION_ONLY"),
        ("CAP_FULL", "EX_CAP_FULL"),
    ]
    for execution_name, market_name in suite_02_pairs:
        a = number(ex, execution_name)
        b = number(mm, market_name)
        if a != b:
            fail(
                f"Suite 0.2 Execution/Market Map drift: "
                f"{execution_name}={a} {market_name}={b}"
            )

    require(
        mm,
        [
            'indicator("Market Map v0.2.0"',
            'string responseProfile = input.string("PADRÃO", "Perfil de resposta", options=["PADRÃO", "ANTECIPADO"]',
            "float exMteCore = not na(exMteFast) and not na(exMteSlow)",
            "float exRsiLocal = f_ex_rsi(close)",
            "var int exTrendOppKind = EX_OPP_NONE",
            "var int exRangeOppStage = EX_OPP_STAGE_NONE",
            "var int exTrendReadiness = EX_READY_WAIT",
            "var int exRangeReadiness = EX_READY_WAIT",
            "int exOperatorReadiness = EX_OP_READY_WAIT",
            "bool exOperatorConflict = false",
            "bool exAnticipatedPosture = responseProfile == \"ANTECIPADO\"",
            "var bool exManagementActive = false",
            "var int exManagementState = EX_MGMT_NONE",
            "exManagementCapability := not na(mergedTarget) and not na(mergedInvalidation) ? EX_CAP_FULL",
            "exRangeIgnitionCount >= 1",
            "exTrendOppStage >= EX_OPP_STAGE_ACCEPTED",
            'table.cell(panel, 0, 1, "CENÁRIO"',
            'table.cell(panel, 0, 2, "OPORTUNIDADE"',
            'table.cell(panel, 0, 3, "LADO"',
            'table.cell(panel, 0, 4, "AÇÃO"',
            'table.cell(panel, 0, 5, "ALVO"',
            'table.cell(panel, 0, 6, "GESTÃO"',
            'table.cell(panel, 0, 7, "INVALIDA"',
            'table.cell(panel, 0, 8, correctionActive ? "CORREÇÃO" : ""',
            "table.clear(panel, 0, 0, 1, 8)",
            'plot(exOperatorReadiness, "MM EX 0.2 • Operator readiness"',
            'plot(exManagementState, "MM EX 0.2 • Gestão estado"',
        ],
        "Market Map embedded Execution consumer",
    )

    # Semantic codes must match the machine-readable suite contract.
    sem = semantics["semantics"]
    code_maps = {
        "momentum": {
            "NEUTRAL": "MTE_NEUTRAL",
            "TURN_UP": "MTE_TURN_UP",
            "UP_ACCEL": "MTE_UP_ACCEL",
            "UP_DECEL": "MTE_UP_DECEL",
            "TURN_DOWN": "MTE_TURN_DOWN",
            "DOWN_ACCEL": "MTE_DOWN_ACCEL",
            "DOWN_DECEL": "MTE_DOWN_DECEL",
        },
        "rsi_state": {
            "NEUTRAL": "RSI_NEUTRAL",
            "BULL": "RSI_BULL",
            "RECOVERING_OVERSOLD": "RSI_RECOVERING_OVERSOLD",
            "RECOVERING_OVERBOUGHT": "RSI_RECOVERING_OVERBOUGHT",
            "EXTREME_OVERBOUGHT": "RSI_EXTREME_OVERBOUGHT",
            "EXTREME_OVERSOLD": "RSI_EXTREME_OVERSOLD",
            "FADING_OVERSOLD": "RSI_FADING_OVERSOLD",
            "FADING_OVERBOUGHT": "RSI_FADING_OVERBOUGHT",
            "BEAR": "RSI_BEAR",
        },
        "participation": {
            "NEUTRAL": "PSE_NEUTRAL",
            "CONFIRM": "PSE_CONFIRM",
            "WEAK": "PSE_WEAK",
            "CONTRARY": "PSE_CONTRARY",
        },
        "location": {
            "OUTSIDE": "LOC_OUTSIDE",
            "APPROACHING": "LOC_APPROACHING",
            "IN_CORRECTION": "LOC_IN_CORRECTION",
            "RETEST": "LOC_RETEST",
            "RECLAIM": "LOC_RECLAIM",
            "DESTINATION_NEAR": "LOC_DESTINATION_NEAR",
        },
        "readiness": {
            "WAIT": "READY_WAIT",
            "PREP": "READY_PREP",
            "ARMED": "READY_ARMED",
            "CONFIRMED": "READY_CONFIRMED",
            "ALIGNED": "READY_ALIGNED",
        },
        "strength": {
            "NORMAL": "STRENGTH_NORMAL",
            "FADING": "STRENGTH_FADING",
            "EXHAUSTED": "STRENGTH_EXHAUSTED",
            "REACTION_RISK": "STRENGTH_REACTION_RISK",
        },
    }

    for family, mapping in code_maps.items():
        expected_by_name = {name: int(code) for code, name in sem[family].items()}
        for semantic_name, pine_name in mapping.items():
            expect_num(ex, pine_name, expected_by_name[semantic_name])

    print(
        "PASS: Suite 0.2 Pine contract/default/cross-script parity; "
        f"plot-producing calls EX={ex_plot_calls}, MM={mm_plot_calls} "
        f"(budget<={PLOT_PRODUCING_CALL_BUDGET})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

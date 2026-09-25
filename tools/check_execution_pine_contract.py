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


def main() -> int:
    ex = EXEC.read_text(encoding="utf-8").replace("\r\n", "\n")
    mm = MM.read_text(encoding="utf-8").replace("\r\n", "\n")
    defaults = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    semantics = json.loads(SEMANTICS.read_text(encoding="utf-8"))

    if defaults["execution_research_defaults_version"] != 2:
        fail("accepted defaults manifest is not v2")

    require(
        ex,
        [
            'indicator("Execution v0.1.0"',
            "int EXECUTION_CONTRACT = 1",
            "int EXECUTION_DEFAULTS_VERSION = 2",
            "_expr[1], barmerge.gaps_off, barmerge.lookahead_on",
            "if barstate.isconfirmed",
            "bool confirmLong = confirmEvent and executionDir == 1",
            "bool confirmShort = confirmEvent and executionDir == -1",
            "executionLocation == LOC_DESTINATION_NEAR and destinationDeterioration >= 2",
            "participationState == PSE_CONTRARY ? 1 : 0",
            "participationState == PSE_WEAK or participationState == PSE_CONTRARY",
            "int EX_EVENT_HOLD_MAX_MS = 12 * 60 * 60 * 1000",
            "int EX_EVENT_HOLD_BARS = 3",
            "plot(mteReady ? mteCore : na, \"Momentum\"",
            'plot(executionReadiness, "EX • Readiness"',
            'plot(executionStrength, "EX • Força"',
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
    threshold_inputs = [
        line.strip()
        for line in ex.splitlines()
        if re.search(r"\binput\.(?:int|float|string|source)\(", line)
    ]
    if threshold_inputs:
        fail(f"Execution exposes forbidden normal threshold/source inputs: {threshold_inputs}")

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

    require(
        mm,
        [
            "float exMteCore = not na(exMteFast) and not na(exMteSlow)",
            "float exRsiLocal = f_ex_rsi(close)",
            "float exDirectionalPressure = exPseReady and mapDir != 0 ? exPressureProxy * mapDir : na",
            "int exGenericDeterioration = (exMomentumDeteriorates ? 1 : 0) + (exRsiDeteriorates ? 1 : 0) + (exParticipationState == EX_PSE_CONTRARY ? 1 : 0)",
            "exLocation == EX_LOC_DESTINATION_NEAR and exDestinationDeterioration >= 2",
            "if barstate.isconfirmed",
            "else if prevReadiness == EX_READY_ARMED",
            "exParticipationState == EX_PSE_CONFIRM",
            'table.cell(panel, 0, 10, "EXECUÇÃO"',
            'table.cell(panel, 0, 11, "FORÇA"',
            "table.clear(panel, 0, 0, 1, 11)",
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

    print("PASS: Execution Pine v0.1.0 contract/default/context parity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

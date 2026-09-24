#!/usr/bin/env python3
"""Validate Execution research defaults against executable reference constants."""
from __future__ import annotations

import json
from pathlib import Path

from tools.market_execution_bridge_reference import APPROACH_ATR, EVENT_HOLD_BARS
from tools.momentum_turn_reference import (
    ACCEL_EPS,
    ACTIVITY_LEN,
    ATR_LEN,
    FAST_EMA,
    NEUTRAL_FACTOR,
    SLOW_EMA,
    TURN_FACTOR,
    TURN_FLOOR,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "execution-research-defaults-v1.json"


def _expect(actual, expected, label: str) -> None:
    if actual != expected:
        raise SystemExit(f"FAIL: {label}: manifest={actual!r} reference={expected!r}")


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    _expect(data.get("execution_research_defaults_version"), 1, "defaults version")
    _expect(data.get("status"), "candidate", "status")

    m = data["momentum_turn"]
    _expect(m["candidate"], "MTE-A", "momentum candidate")
    _expect(m["source"], "hlc3", "momentum source")
    _expect(m["fast_ema"], FAST_EMA, "fast EMA")
    _expect(m["slow_ema"], SLOW_EMA, "slow EMA")
    _expect(m["atr_length"], ATR_LEN, "ATR length")
    _expect(m["activity_rma"], ACTIVITY_LEN, "activity RMA")
    _expect(m["neutral_factor"], NEUTRAL_FACTOR, "neutral factor")
    _expect(m["turn_factor"], TURN_FACTOR, "turn factor")
    _expect(m["turn_floor"], TURN_FLOOR, "turn floor")
    _expect(m["accel_epsilon"], ACCEL_EPS, "acceleration epsilon")

    b = data["market_map_execution_bridge"]
    _expect(b["approach_distance_atr"], APPROACH_ATR, "approach ATR")
    _expect(b["event_hold_bars"], EVENT_HOLD_BARS, "event hold bars")

    rsi = data["rsi"]
    expected_rsi = {
        "length": 14,
        "center": 50,
        "center_deadband_low": 48,
        "center_deadband_high": 52,
        "overbought": 70,
        "oversold": 30,
        "extended_overbought": 80,
        "extended_oversold": 20,
        "zone_memory_bars": 2,
        "minimum_directional_step": 0.25,
    }
    _expect(rsi, expected_rsi, "RSI defaults")

    participation = data["participation"]
    expected_participation = {
        "baseline": "ema",
        "baseline_length": 20,
        "contracted_below": 0.8,
        "expanded_at_or_above": 1.2,
        "strong_at_or_above": 1.5,
    }
    _expect(participation, expected_participation, "participation defaults")

    print("PASS: Execution research defaults v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

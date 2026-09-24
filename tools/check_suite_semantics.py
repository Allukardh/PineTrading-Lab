#!/usr/bin/env python3
"""Validate machine-readable suite semantic codes against reference enums."""
from __future__ import annotations

import json
from pathlib import Path

from execution_state_reference import (
    Location,
    Momentum,
    Participation,
    Readiness,
    RsiState,
    Strength,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "suite-semantics-v1.json"


def _enum_map(enum_cls):
    return {str(int(member.value)): member.name for member in enum_cls}


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if data.get("suite_contract_version") != 1:
        raise SystemExit("FAIL: suite_contract_version must be 1")

    semantics = data.get("semantics", {})
    expected = {
        "location": _enum_map(Location),
        "momentum": _enum_map(Momentum),
        "rsi_state": _enum_map(RsiState),
        "participation": _enum_map(Participation),
        "readiness": _enum_map(Readiness),
        "strength": _enum_map(Strength),
    }

    for name, enum_values in expected.items():
        manifest_values = semantics.get(name)
        if manifest_values != enum_values:
            raise SystemExit(
                f"FAIL: semantic drift in {name}: "
                f"manifest={manifest_values!r} reference={enum_values!r}"
            )

    map_dir = semantics.get("map_dir")
    if map_dir != {"-1": "BAIXA", "0": "NEUTRO_TRANSICAO", "1": "ALTA"}:
        raise SystemExit(f"FAIL: invalid map_dir contract: {map_dir!r}")

    labels = data.get("operator_labels_pt_br", {})
    readiness_labels = labels.get("readiness", {})
    strength_labels = labels.get("strength", {})

    if set(readiness_labels) != {m.name for m in Readiness}:
        raise SystemExit("FAIL: readiness operator labels do not cover every state")
    if set(strength_labels) != {m.name for m in Strength}:
        raise SystemExit("FAIL: strength operator labels do not cover every state")

    all_label_values = list(readiness_labels.values()) + list(strength_labels.values())
    if any(not isinstance(v, str) or not v.strip() for v in all_label_values):
        raise SystemExit("FAIL: blank/non-string operator label")

    print("PASS: suite semantic contract v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

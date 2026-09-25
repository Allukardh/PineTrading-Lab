#!/usr/bin/env python3
"""Integrated historical evidence for Market Map -> Execution.

This runner composes only already-accepted/reviewed research pieces:
- accepted MM-0 offline-equivalent Market Map kernel
- canonical Market Map -> Execution location bridge
- MTE-A / RSE-A / PSE-A candidate engines
- canonical Execution semantic state machine

It is not a strategy backtest:
- no PnL
- no trade win rate
- no threshold optimization
- no production Pine generation
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Sequence

from tools.execution_candidate_reference import ExecutionResearchBar, calculate as calculate_execution
from tools.execution_historical_evidence import (
    TIMEFRAMES,
    build_context_dirs,
    distribution,
    load_dataset,
    pct,
    sha256_file,
)
from tools.execution_state_reference import (
    Location,
    Momentum,
    Participation,
    Readiness,
    RsiState,
    Strength,
    RELEVANT_LOCATIONS,
)
from tools.market_execution_bridge_reference import (
    BridgeMemory,
    MapEvidence,
    classify as classify_location,
)
from tools.market_map_offline_core import (
    CONTEXT_TF as MM_CONTEXT_TF,
    Candle,
    IntegrationSnapshot,
    Kernel,
)
from tools.rsi_state_reference import calculate as calculate_rsi


def to_mm_candles(data: dict) -> list[Candle]:
    return [
        Candle(
            int(round(t.timestamp() * 1_000_000.0)),
            float(o),
            float(h),
            float(l),
            float(c),
            float(v),
        )
        for t, o, h, l, c, v in zip(
            data["open_time"],
            data["open"],
            data["high"],
            data["low"],
            data["close"],
            data["volume"],
        )
    ]


def _dwell_states(samples: Sequence) -> dict[str, dict]:
    runs: dict[str, list[float]] = defaultdict(list)
    active = None
    length = 0

    def flush() -> None:
        nonlocal active, length
        if active is not None and length:
            runs[active].append(float(length))
        active = None
        length = 0

    for sample in samples:
        name = sample.result.state.readiness.name
        if name == active:
            length += 1
        else:
            flush()
            active = name
            length = 1
    flush()

    out = {}
    for name, values in sorted(runs.items()):
        d = distribution(values)
        out[name] = {
            "episodes": len(values),
            "median": d["median"],
            "p75": d["p75"],
            "p90": d["p90"],
        }
    return out


def _momentum_strongly_opposes(direction: int, state: Momentum) -> bool:
    if direction == 1:
        return state in {Momentum.TURN_DOWN, Momentum.DOWN_ACCEL}
    if direction == -1:
        return state in {Momentum.TURN_UP, Momentum.UP_ACCEL}
    return True


def _rsi_opposes(direction: int, state: RsiState, context_dir: int) -> bool:
    if direction == 1:
        return (
            state in {RsiState.BEAR, RsiState.FADING_OVERBOUGHT, RsiState.EXTREME_OVERBOUGHT}
            or context_dir == -1
        )
    if direction == -1:
        return (
            state in {RsiState.BULL, RsiState.RECOVERING_OVERSOLD, RsiState.EXTREME_OVERSOLD}
            or context_dir == 1
        )
    return True


def _momentum_deteriorates(direction: int, state: Momentum) -> bool:
    if direction == 1:
        return state in {Momentum.UP_DECEL, Momentum.TURN_DOWN, Momentum.DOWN_ACCEL, Momentum.DOWN_DECEL}
    if direction == -1:
        return state in {Momentum.DOWN_DECEL, Momentum.TURN_UP, Momentum.UP_ACCEL, Momentum.UP_DECEL}
    return False


def _rsi_deteriorates(direction: int, state: RsiState) -> bool:
    if direction == 1:
        return state in {RsiState.FADING_OVERBOUGHT, RsiState.EXTREME_OVERBOUGHT}
    if direction == -1:
        return state in {RsiState.RECOVERING_OVERSOLD, RsiState.EXTREME_OVERSOLD}
    return False


def _participation_enum(name: str) -> Participation:
    return Participation[name]


def build_market_locations(
    snapshots: Sequence[IntegrationSnapshot],
) -> list[Location]:
    memory = BridgeMemory()
    locations: list[Location] = []

    for snap in snapshots:
        result = classify_location(
            memory,
            MapEvidence(
                bar_index=snap.bar_index,
                map_dir=snap.map_dir,
                atr=snap.atr,
                close=snap.close,
                correction_active=snap.correction_active,
                thesis_invalidated=snap.thesis_invalidated,
                structural_conflict=snap.structural_conflict,
                t1_top=snap.t1_top,
                t1_bottom=snap.t1_bottom,
                primary_top=snap.primary_top,
                primary_bottom=snap.primary_bottom,
                t3_top=snap.t3_top,
                t3_bottom=snap.t3_bottom,
                retest_event=snap.retest_event,
                reclaim_event=snap.reclaim_event,
                destination_near=snap.destination_near,
            ),
        )
        memory = result.memory
        locations.append(result.location)

    return locations


def summarize_integrated(
    snapshots: Sequence[IntegrationSnapshot],
    locations: Sequence[Location],
    samples: Sequence,
    context_dirs: Sequence[int],
) -> dict:
    if not (len(snapshots) == len(locations) == len(samples) == len(context_dirs)):
        raise ValueError("integrated series length mismatch")

    rows = len(samples)
    coherent = [
        i
        for i, snap in enumerate(snapshots)
        if snap.map_dir in (-1, 1)
        and not snap.thesis_invalidated
        and not snap.structural_conflict
        and snap.atr is not None
        and snap.atr > 0
    ]
    relevant = [i for i in coherent if locations[i] in RELEVANT_LOCATIONS]
    destination_near = [i for i in coherent if locations[i] == Location.DESTINATION_NEAR]

    location_counts = Counter(locations[i].name for i in coherent)
    raw_map_events = {
        "RETEST": sum(int(snap.retest_event) for snap in snapshots),
        "RECLAIM": sum(int(snap.reclaim_event) for snap in snapshots),
    }
    readiness_counts = Counter(samples[i].result.state.readiness.name for i in range(rows))
    readiness_coherent = Counter(samples[i].result.state.readiness.name for i in coherent)
    strength_coherent = Counter(samples[i].result.state.strength.name for i in coherent)

    active_exec = [
        i
        for i in coherent
        if samples[i].result.state.readiness in {Readiness.CONFIRMED, Readiness.ALIGNED}
    ]
    active_exec_set = set(active_exec)
    strength_active = Counter(samples[i].result.state.strength.name for i in active_exec)

    transitions = Counter(
        f"{sample.state_before.readiness.name}->{sample.result.state.readiness.name}"
        for sample in samples
    )

    event_counts = Counter()
    event_dir: dict[str, Counter[str]] = defaultdict(Counter)
    confirm_location = Counter()
    cancel_from = Counter()
    cancel_reasons = Counter()

    def cancel_reason(i: int) -> str:
        sample = samples[i]
        snap = snapshots[i]
        direction = snap.map_dir
        reasons = []

        if (
            direction not in (-1, 1)
            or snap.thesis_invalidated
            or snap.structural_conflict
        ):
            reasons.append("MAP_INVALID")
        elif (
            sample.state_before.direction in (-1, 1)
            and sample.state_before.direction != direction
        ):
            reasons.append("MAP_DIRECTION_CHANGE")
        else:
            stage = sample.state_before.readiness
            momentum = Momentum[sample.momentum_state_name]
            rsi = RsiState[sample.rsi_state_name]
            participation = _participation_enum(sample.participation_state_name)

            if stage in {Readiness.PREP, Readiness.ARMED} and locations[i] not in RELEVANT_LOCATIONS:
                reasons.append("LOCATION_LOST")
            if _momentum_strongly_opposes(direction, momentum):
                reasons.append("MOMENTUM_OPPOSES")
            if stage in {Readiness.ARMED, Readiness.ALIGNED} and _rsi_opposes(
                direction, rsi, context_dirs[i]
            ):
                reasons.append("RSI_OPPOSES")
            if stage in {Readiness.PREP, Readiness.ARMED} and participation == Participation.CONTRARY:
                reasons.append("PSE_CONTRARY")

        return "+".join(reasons) if reasons else "OTHER"

    for i, sample in enumerate(samples):
        ev = sample.result.events
        direction = snapshots[i].map_dir
        dname = "LONG" if direction == 1 else "SHORT" if direction == -1 else "NONE"

        if ev.preparing_entered:
            event_counts["PREPARING_ENTERED"] += 1
            event_dir["PREPARING_ENTERED"][dname] += 1
        if ev.armed_entered:
            event_counts["ARMED_ENTERED"] += 1
            event_dir["ARMED_ENTERED"][dname] += 1
        if ev.confirm:
            event_counts["CONFIRM"] += 1
            event_dir["CONFIRM"][dname] += 1
            confirm_location[locations[i].name] += 1
        if ev.canceled:
            event_counts["CANCELED"] += 1
            event_dir["CANCELED"][dname] += 1
            cancel_from[sample.state_before.readiness.name] += 1
            cancel_reasons[cancel_reason(i)] += 1
        if ev.reaction_risk_entered:
            event_counts["REACTION_RISK_ENTERED"] += 1
            event_dir["REACTION_RISK_ENTERED"][dname] += 1

    prep = event_counts["PREPARING_ENTERED"]
    armed = event_counts["ARMED_ENTERED"]
    confirms = event_counts["CONFIRM"]

    # Quick setup churn.
    quick_prep_cancel = {str(n): 0 for n in (1, 2, 3)}
    quick_armed_cancel = {str(n): 0 for n in (1, 2, 3)}
    quick_armed_cancel_reasons_3 = Counter()
    prep_entries = [i for i, s in enumerate(samples) if s.result.events.preparing_entered]
    armed_entries = [i for i, s in enumerate(samples) if s.result.events.armed_entered]

    for start in prep_entries:
        for j in range(start + 1, min(rows, start + 4)):
            if samples[j].result.events.armed_entered or samples[j].result.events.confirm:
                break
            if samples[j].result.events.canceled:
                gap = j - start
                for n in (1, 2, 3):
                    if gap <= n:
                        quick_prep_cancel[str(n)] += 1
                break

    for start in armed_entries:
        for j in range(start + 1, min(rows, start + 4)):
            if samples[j].result.events.confirm:
                break
            if samples[j].result.events.canceled:
                gap = j - start
                for n in (1, 2, 3):
                    if gap <= n:
                        quick_armed_cancel[str(n)] += 1
                if gap <= 3:
                    quick_armed_cancel_reasons_3[cancel_reason(j)] += 1
                break

    # RSE memory watch: ARMADO entered specifically from the short-lived
    # recovery/fade states; determine whether a quick cancel is attributable
    # to RSI while location/momentum/participation remain otherwise valid.
    rse_memory_armed = 0
    rse_memory_quick_cancel = {str(n): 0 for n in (1, 2, 3)}
    rse_only_quick_cancel = {str(n): 0 for n in (1, 2, 3)}

    for start in armed_entries:
        direction = snapshots[start].map_dir
        rsi_name = samples[start].rsi_state_name
        is_memory_arm = (
            direction == 1 and rsi_name == "RECOVERING_OVERSOLD"
        ) or (
            direction == -1 and rsi_name == "FADING_OVERBOUGHT"
        )
        if not is_memory_arm:
            continue
        rse_memory_armed += 1

        for j in range(start + 1, min(rows, start + 4)):
            if samples[j].result.events.confirm:
                break
            if not samples[j].result.events.canceled:
                continue

            gap = j - start
            for n in (1, 2, 3):
                if gap <= n:
                    rse_memory_quick_cancel[str(n)] += 1

            d = snapshots[j].map_dir
            m = Momentum[samples[j].momentum_state_name]
            r = RsiState[samples[j].rsi_state_name]
            p = _participation_enum(samples[j].participation_state_name)
            rsi_only = (
                d in (-1, 1)
                and locations[j] in RELEVANT_LOCATIONS
                and not snapshots[j].thesis_invalidated
                and not snapshots[j].structural_conflict
                and not _momentum_strongly_opposes(d, m)
                and p != Participation.CONTRARY
                and _rsi_opposes(d, r, context_dirs[j])
            )
            if rsi_only:
                for n in (1, 2, 3):
                    if gap <= n:
                        rse_only_quick_cancel[str(n)] += 1
            break

    strength_family_combo_coherent = Counter()
    strength_family_combo_active = Counter()
    for i in coherent:
        direction = snapshots[i].map_dir
        m = Momentum[samples[i].momentum_state_name]
        r = RsiState[samples[i].rsi_state_name]
        p = _participation_enum(samples[i].participation_state_name)
        families = []
        if _momentum_deteriorates(direction, m):
            families.append("MTE")
        if _rsi_deteriorates(direction, r):
            families.append("RSI")
        if p in {Participation.WEAK, Participation.CONTRARY}:
            families.append("PSE")
        combo = "+".join(families) if families else "NONE"
        strength_family_combo_coherent[combo] += 1
        if i in active_exec_set:
            strength_family_combo_active[combo] += 1

    reaction_risk = [
        i for i in coherent if samples[i].result.state.strength == Strength.REACTION_RISK
    ]
    reaction_outside_dest = [
        i for i in reaction_risk if locations[i] != Location.DESTINATION_NEAR
    ]

    return {
        "rows": rows,
        "map": {
            "coherent_bars": len(coherent),
            "coherent_pct": pct(len(coherent), rows),
            "relevant_location_bars": len(relevant),
            "relevant_location_pct_of_coherent": pct(len(relevant), len(coherent)),
            "destination_near_bars": len(destination_near),
            "raw_event_counts": raw_map_events,
            "event_hold_amplification": {
                "RETEST": (
                    None if not raw_map_events["RETEST"]
                    else location_counts["RETEST"] / raw_map_events["RETEST"]
                ),
                "RECLAIM": (
                    None if not raw_map_events["RECLAIM"]
                    else location_counts["RECLAIM"] / raw_map_events["RECLAIM"]
                ),
            },
            "location_counts": dict(sorted(location_counts.items())),
            "location_pct_of_coherent": {
                k: pct(v, len(coherent)) for k, v in sorted(location_counts.items())
            },
        },
        "readiness": {
            "counts_all": dict(sorted(readiness_counts.items())),
            "pct_all": {k: pct(v, rows) for k, v in sorted(readiness_counts.items())},
            "counts_coherent": dict(sorted(readiness_coherent.items())),
            "pct_coherent": {
                k: pct(v, len(coherent)) for k, v in sorted(readiness_coherent.items())
            },
            "dwell_bars": _dwell_states(samples),
            "transitions": dict(sorted(transitions.items())),
            "events": dict(event_counts),
            "events_by_direction": {
                k: dict(v) for k, v in sorted(event_dir.items())
            },
            "confirm_location_counts": dict(sorted(confirm_location.items())),
            "cancel_from": dict(sorted(cancel_from.items())),
            "cancel_reason_counts": dict(sorted(cancel_reasons.items())),
            "prep_to_armed_pct": pct(armed, prep),
            "armed_to_confirm_pct": pct(confirms, armed),
            "confirm_per_1000_relevant_bars": (
                None if not relevant else 1000.0 * confirms / len(relevant)
            ),
            "quick_prep_cancel_within_bars": quick_prep_cancel,
            "quick_armed_cancel_within_bars": quick_armed_cancel,
            "quick_armed_cancel_reason_counts_3bar": dict(
                sorted(quick_armed_cancel_reasons_3.items())
            ),
        },
        "strength": {
            "coherent_counts": dict(sorted(strength_coherent.items())),
            "coherent_pct": {
                k: pct(v, len(coherent)) for k, v in sorted(strength_coherent.items())
            },
            "confirmed_aligned_bars": len(active_exec),
            "confirmed_aligned_counts": dict(sorted(strength_active.items())),
            "confirmed_aligned_pct": {
                k: pct(v, len(active_exec)) for k, v in sorted(strength_active.items())
            },
            "family_combo_counts_coherent": dict(sorted(strength_family_combo_coherent.items())),
            "family_combo_pct_coherent": {
                k: pct(v, len(coherent))
                for k, v in sorted(strength_family_combo_coherent.items())
            },
            "family_combo_counts_confirmed_aligned": dict(sorted(strength_family_combo_active.items())),
            "family_combo_pct_confirmed_aligned": {
                k: pct(v, len(active_exec))
                for k, v in sorted(strength_family_combo_active.items())
            },
            "reaction_risk_bars": len(reaction_risk),
            "reaction_risk_pct_of_destination_near": pct(
                len(reaction_risk), len(destination_near)
            ),
            "reaction_risk_outside_destination_near": len(reaction_outside_dest),
        },
        "rse_memory_watch": {
            "armed_from_recovery_fade": rse_memory_armed,
            "quick_cancel_within_bars": rse_memory_quick_cancel,
            "rsi_only_quick_cancel_within_bars": rse_only_quick_cancel,
            "rsi_only_quick_cancel_3bar_pct": pct(
                rse_only_quick_cancel["3"], rse_memory_armed
            ),
        },
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Integrated Market Map → Execution historical evidence — BTC",
        "",
        "This is semantic/state-machine evidence, not a strategy backtest or profitability claim.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        f"- Market Map source: accepted MM-0 offline-equivalent kernel",
        f"- Execution defaults manifest: v{report['metadata']['research_defaults_version']}",
        f"- suite semantics: v{report['metadata']['suite_contract_version']}",
        "",
        "## Cross-timeframe summary",
        "",
        "| TF | coherent % | relevant % | PREP | ARMED | CONFIRM | A/P % | C/A % | confirm/1000 relevant | quick armed cancel <=3 | RSE-only churn <=3 | reaction risk / dest-near % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for tf in TIMEFRAMES:
        e = report["timeframes"][tf]["evidence"]
        rd = e["readiness"]
        mp = e["map"]
        rw = e["rse_memory_watch"]
        st = e["strength"]
        events = rd["events"]
        lines.append(
            "| {tf} | {coh} | {rel} | {prep} | {armed} | {conf} | {ap} | {ca} | {rate} | {qac} | {rchurn} | {rr} |".format(
                tf=tf,
                coh=_fmt(mp["coherent_pct"]),
                rel=_fmt(mp["relevant_location_pct_of_coherent"]),
                prep=events.get("PREPARING_ENTERED", 0),
                armed=events.get("ARMED_ENTERED", 0),
                conf=events.get("CONFIRM", 0),
                ap=_fmt(rd["prep_to_armed_pct"]),
                ca=_fmt(rd["armed_to_confirm_pct"]),
                rate=_fmt(rd["confirm_per_1000_relevant_bars"]),
                qac=rd["quick_armed_cancel_within_bars"]["3"],
                rchurn=_fmt(rw["rsi_only_quick_cancel_3bar_pct"]),
                rr=_fmt(st["reaction_risk_pct_of_destination_near"]),
            )
        )

    lines += [
        "",
        "## Guardrails",
        "",
        "- No row above is a trade win rate.",
        "- Candidate defaults are not tuned by this runner.",
        "- Production `execution.pine` remains blocked until these integrated semantics are reviewed.",
        "- Any REFINE decision must name a semantic pathology rather than optimize frequency.",
        "",
    ]
    return "\n".join(lines)


def _fmt(value, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--canonical-manifest", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    ap.add_argument("--code-sha", default="unknown")
    ap.add_argument("--tick-size", type=float, default=0.01)
    args = ap.parse_args()

    symbol = args.symbol.upper()
    canonical = json.loads(args.canonical_manifest.read_text(encoding="utf-8"))
    expected = {d["timeframe"]: d for d in canonical["datasets"]}
    market = canonical.get("market", "spot")

    datasets: dict[str, dict] = {}
    meta = {}
    for tf in TIMEFRAMES:
        path = args.data_root / market / symbol / "consolidated" / f"{symbol}_{tf}.parquet"
        if not path.is_file():
            raise SystemExit(f"missing dataset: {path}")
        actual_hash = sha256_file(path)
        exp = expected[tf]
        if actual_hash != exp["dataset_sha256"]:
            raise SystemExit(
                f"{symbol} {tf}: SHA mismatch {actual_hash} != {exp['dataset_sha256']}"
            )
        data = load_dataset(path)
        if len(data["close"]) != exp["candles"]:
            raise SystemExit(
                f"{symbol} {tf}: row mismatch {len(data['close'])} != {exp['candles']}"
            )
        datasets[tf] = data
        meta[tf] = {
            "rows": len(data["close"]),
            "dataset_sha256": actual_hash,
            "first_date": exp["first_date"],
            "last_date": exp["last_date"],
            "status": exp["status"],
        }

    mm_candles = {tf: to_mm_candles(datasets[tf]) for tf in TIMEFRAMES}
    rsi_cache = {tf: calculate_rsi(datasets[tf]["close"]) for tf in TIMEFRAMES}

    defaults_path = Path("manifests/execution-research-defaults-v1.json")
    semantics_path = Path("manifests/suite-semantics-v1.json")
    defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))

    report = {
        "metadata": {
            "symbol": symbol,
            "market": market,
            "data_source": "official Binance Public Data SPOT monthly klines",
            "canonical_manifest": str(args.canonical_manifest),
            "canonical_materialization_run": canonical["materialization"]["github_actions_run_id"],
            "research_defaults_version": defaults["execution_research_defaults_version"],
            "research_defaults_sha256": sha256_file(defaults_path),
            "suite_contract_version": semantics["suite_contract_version"],
            "suite_semantics_sha256": sha256_file(semantics_path),
            "code_sha": args.code_sha,
            "tick_size": args.tick_size,
            "integration_contract": {
                "market_map": "accepted MM-0 offline-equivalent kernel",
                "bridge": "market_execution_bridge_reference.py",
                "execution": "execution_candidate_reference.py + execution_state_reference.py",
            },
        },
        "timeframes": {},
        "decision": "REVIEW_REQUIRED",
    }

    daily = mm_candles["1d"]
    weekly = mm_candles["1w"]

    for tf in TIMEFRAMES:
        ctx_tf = MM_CONTEXT_TF[tf]
        snapshots: list[IntegrationSnapshot] = []
        Kernel(
            mm_candles[tf],
            mm_candles[ctx_tf],
            daily,
            weekly,
            tf,
            args.tick_size,
        ).run(integration_rows=snapshots, emit_audit=False)

        if len(snapshots) != len(datasets[tf]["close"]):
            raise SystemExit(
                f"{tf}: Market Map integration length mismatch "
                f"{len(snapshots)} != {len(datasets[tf]['close'])}"
            )

        locations = build_market_locations(snapshots)
        context_dirs = build_context_dirs(tf, datasets, rsi_cache)

        bars = [
            ExecutionResearchBar(
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
                map_dir=snap.map_dir,
                location=loc,
                rsi_context_dir=context_dirs[i],
                thesis_invalidated=snap.thesis_invalidated,
                structural_conflict=snap.structural_conflict,
                bar_confirmed=True,
            )
            for i, (o, h, l, c, v, snap, loc) in enumerate(
                zip(
                    datasets[tf]["open"],
                    datasets[tf]["high"],
                    datasets[tf]["low"],
                    datasets[tf]["close"],
                    datasets[tf]["volume"],
                    snapshots,
                    locations,
                )
            )
        ]
        samples = calculate_execution(bars)

        evidence = summarize_integrated(
            snapshots,
            locations,
            samples,
            context_dirs,
        )
        report["timeframes"][tf] = {
            "metadata": meta[tf] | {"context_timeframe": ctx_tf},
            "evidence": evidence,
        }

    # Hard semantic invariants. Frequency itself is review evidence, not a pass/fail target.
    for tf, item in report["timeframes"].items():
        ev = item["evidence"]
        if ev["strength"]["reaction_risk_outside_destination_near"] != 0:
            raise SystemExit(f"{tf}: REACTION_RISK escaped DESTINATION_NEAR contract")
        confirms = ev["readiness"]["events"].get("CONFIRM", 0)
        by_dir = ev["readiness"]["events_by_direction"].get("CONFIRM", {})
        if confirms != by_dir.get("LONG", 0) + by_dir.get("SHORT", 0):
            raise SystemExit(f"{tf}: confirmation direction accounting mismatch")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md = markdown_report(report)
    args.output_md.write_text(md + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

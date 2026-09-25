#!/usr/bin/env python3
"""Historical evidence runner for Execution research candidates.

Implements the pre-registered questions in
docs/testing/EXECUTION_EVIDENCE_RESEARCH_PLAN.md.

This is component research, not a strategy backtest:
- no PnL
- no trade win rate
- no threshold optimization
- no production Execution signals

The runner validates dataset SHA-256 identities against the canonical
production manifest before computing evidence.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from tools.execution_candidate_reference import (
    ExecutionResearchBar,
    calculate as calculate_execution_candidate,
)
from tools.execution_state_reference import (
    Location,
    Momentum,
    Participation,
    Readiness,
    RELEVANT_LOCATIONS,
    RsiState,
    Strength,
)
from tools.market_execution_bridge_reference import (
    BridgeMemory,
    MapEvidence,
    classify as classify_map_location,
)
from tools.market_map_offline_core import Candle as MarketMapCandle
from tools.market_map_offline_core import Kernel as MarketMapKernel
from tools.momentum_turn_reference import Bar as MomentumBar
from tools.momentum_turn_reference import calculate as calculate_momentum
from tools.participation_reference import (
    CONTRACTED_BELOW,
    EXPANDED_AT_OR_ABOVE,
    PRESSURE_MIN,
    ParticipationBar,
    calculate as calculate_participation,
    taker_imbalance,
)
from tools.rsi_state_reference import (
    CENTER_HIGH,
    CENTER_LOW,
    OVERBOUGHT,
    OVERSOLD,
    ZONE_MEMORY_BARS,
    calculate as calculate_rsi,
    context_direction,
    local_supports,
    supports,
)

TIMEFRAMES = ("15m", "1h", "4h", "1d", "3d", "1w")
CONTEXT_TF = {
    "15m": "1h",
    "1h": "4h",
    "4h": "1d",
    "1d": "1w",
    "3d": "3d",
    "1w": "1w",
}
SIGN_NEAR_ZERO = 0.05


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pct(part: int | float, total: int | float) -> float | None:
    if not total:
        return None
    return 100.0 * float(part) / float(total)


def percentile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be inside [0, 1]")
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    pos = q * (len(xs) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def distribution(values: Sequence[float]) -> dict:
    return {
        "count": len(values),
        "p10": percentile(values, 0.10),
        "p25": percentile(values, 0.25),
        "median": percentile(values, 0.50),
        "p75": percentile(values, 0.75),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
    }


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys):
        raise ValueError("series length mismatch")
    if len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    if den == 0.0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / den


def rankdata(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = avg_rank
        i = j
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys):
        raise ValueError("series length mismatch")
    if len(xs) < 2:
        return None
    return pearson(rankdata(xs), rankdata(ys))


def _state_pct(counter: Counter[str], total: int) -> dict[str, float | None]:
    return {key: pct(value, total) for key, value in sorted(counter.items())}


def _dwell(samples: Sequence, *, state_attr: str = "state") -> dict[str, dict]:
    episodes: dict[str, list[float]] = defaultdict(list)
    active_name: str | None = None
    length = 0

    def flush() -> None:
        nonlocal active_name, length
        if active_name is not None and length:
            episodes[active_name].append(float(length))
        active_name = None
        length = 0

    for sample in samples:
        if not getattr(sample, "ready", False):
            flush()
            continue
        name = getattr(sample, state_attr).name
        if name == active_name:
            length += 1
        else:
            flush()
            active_name = name
            length = 1
    flush()

    return {
        name: {
            "episodes": len(values),
            "p25": percentile(values, 0.25),
            "median": percentile(values, 0.50),
            "p75": percentile(values, 0.75),
            "p90": percentile(values, 0.90),
        }
        for name, values in sorted(episodes.items())
    }


def _sign(value: float, eps: float = 0.0) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def sign_agreement(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    eps: float = SIGN_NEAR_ZERO,
    mask: Sequence[bool] | None = None,
) -> dict:
    agree = disagree = excluded = 0
    for i, (x, y) in enumerate(zip(xs, ys)):
        if mask is not None and not mask[i]:
            continue
        sx = _sign(x, eps)
        sy = _sign(y, eps)
        if sx == 0 or sy == 0:
            excluded += 1
        elif sx == sy:
            agree += 1
        else:
            disagree += 1
    used = agree + disagree
    return {
        "agree": agree,
        "disagree": disagree,
        "excluded_near_zero": excluded,
        "agreement_pct": pct(agree, used),
        "near_zero_epsilon": eps,
    }


def confirmed_context_indices(
    chart_times: Sequence[datetime],
    htf_times: Sequence[datetime],
) -> list[int | None]:
    """Previous completed HTF bar for [1] + lookahead_on semantics."""
    out: list[int | None] = []
    for t in chart_times:
        current = bisect.bisect_right(htf_times, t) - 1
        previous = current - 1
        out.append(previous if previous >= 0 else None)
    return out


def load_dataset(path: Path) -> dict:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("pyarrow is required; install requirements-market-data.txt") from exc

    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "taker_buy_base_asset_volume",
    ]
    table = pq.read_table(path, columns=cols)
    d = table.to_pydict()

    def fs(name: str) -> list[float]:
        return [float(v) for v in d[name]]

    return {
        "open_time": list(d["open_time"]),
        "open": fs("open"),
        "high": fs("high"),
        "low": fs("low"),
        "close": fs("close"),
        "volume": fs("volume"),
        "taker_buy_base_asset_volume": fs("taker_buy_base_asset_volume"),
    }


def mte_report(samples: Sequence) -> dict:
    ready = [s for s in samples if s.ready]
    occupancy = Counter(s.state.name for s in ready)

    transitions: Counter[str] = Counter()
    prev = None
    state_changes = 0
    for s in ready:
        if prev is not None:
            transitions[f"{prev.name}->{s.state.name}"] += 1
            if prev != s.state:
                state_changes += 1
        prev = s.state

    turn_starts: list[tuple[int, Momentum]] = []
    prev_state: Momentum | None = None
    for i, s in enumerate(samples):
        if not s.ready:
            prev_state = None
            continue
        if s.state in (Momentum.TURN_UP, Momentum.TURN_DOWN) and s.state != prev_state:
            turn_starts.append((i, s.state))
        prev_state = s.state

    turn_sign = Counter()
    zero_lead: list[float] = []
    resumed_before_zero = 0
    opposite_turn_before_zero = 0
    unresolved = 0

    for i, state in turn_starts:
        core = samples[i].core
        if core is None:
            continue
        turn_sign["positive" if core > 0 else "negative" if core < 0 else "zero"] += 1
        resolved = False
        for j in range(i + 1, len(samples)):
            sj = samples[j]
            if not sj.ready or sj.core is None:
                continue
            crossed = (
                state == Momentum.TURN_DOWN and sj.core <= 0.0
            ) or (
                state == Momentum.TURN_UP and sj.core >= 0.0
            )
            if crossed:
                zero_lead.append(float(j - i))
                resolved = True
                break
            resumed = (
                state == Momentum.TURN_DOWN and sj.state == Momentum.UP_ACCEL
            ) or (
                state == Momentum.TURN_UP and sj.state == Momentum.DOWN_ACCEL
            )
            if resumed:
                resumed_before_zero += 1
                resolved = True
                break
            if sj.state in (Momentum.TURN_UP, Momentum.TURN_DOWN) and sj.state != state:
                opposite_turn_before_zero += 1
                resolved = True
                break
        if not resolved:
            unresolved += 1

    turn_reversals = {str(n): 0 for n in (1, 2, 3)}
    for (i, a), (j, b) in zip(turn_starts, turn_starts[1:]):
        if a != b:
            gap = j - i
            for n in (1, 2, 3):
                if gap <= n:
                    turn_reversals[str(n)] += 1

    crosses: list[int] = []
    prev_core: float | None = None
    for i, s in enumerate(samples):
        if not s.ready or s.core is None:
            continue
        if prev_core is not None and (
            (prev_core > 0.0 and s.core <= 0.0)
            or (prev_core < 0.0 and s.core >= 0.0)
        ):
            crosses.append(i)
        prev_core = s.core

    zero_reversals = {str(n): 0 for n in (1, 2, 3)}
    for a, b in zip(crosses, crosses[1:]):
        gap = b - a
        for n in (1, 2, 3):
            if gap <= n:
                zero_reversals[str(n)] += 1

    return {
        "ready_bars": len(ready),
        "occupancy_counts": dict(sorted(occupancy.items())),
        "occupancy_pct": _state_pct(occupancy, len(ready)),
        "transition_matrix": dict(sorted(transitions.items())),
        "dwell_bars": _dwell(samples),
        "turn_lead": {
            "episodes": len(turn_starts),
            "core_sign_at_start": dict(turn_sign),
            "bars_to_zero_cross": distribution(zero_lead),
            "resumed_original_direction_before_zero": resumed_before_zero,
            "opposite_turn_before_zero": opposite_turn_before_zero,
            "unresolved_to_end": unresolved,
        },
        "chatter": {
            "state_changes": state_changes,
            "state_changes_per_100_ready_bars": (
                None if len(ready) < 2 else 100.0 * state_changes / (len(ready) - 1)
            ),
            "turn_direction_reversals_within_bars": turn_reversals,
            "zero_cross_reversals_within_bars": zero_reversals,
        },
    }


def _zone_touch_indices(values: Sequence[float | None], *, oversold: bool) -> list[int]:
    out = []
    previous_inside = False
    for i, value in enumerate(values):
        inside = bool(value is not None and (value <= OVERSOLD if oversold else value >= OVERBOUGHT))
        if inside and not previous_inside:
            out.append(i)
        previous_inside = inside
    return out


def _recovery_lifecycle(
    values: Sequence[float | None],
    samples: Sequence,
    *,
    recovery_state: RsiState,
    center_boundary: float,
    rising: bool,
) -> dict:
    starts = []
    prev = None
    for i, sample in enumerate(samples):
        if not sample.ready:
            prev = None
            continue
        if sample.state == recovery_state and prev != recovery_state:
            starts.append(i)
        prev = sample.state

    dwells = []
    through_center = 0
    expired_before_center = 0
    for start in starts:
        end = start
        while end + 1 < len(samples) and samples[end + 1].ready and samples[end + 1].state == recovery_state:
            end += 1
        dwells.append(float(end - start + 1))
        nxt = end + 1
        value = values[nxt] if nxt < len(values) else None
        crossed = bool(
            value is not None
            and (value >= center_boundary if rising else value <= center_boundary)
        )
        if crossed:
            through_center += 1
        else:
            expired_before_center += 1

    return {
        "episodes": len(starts),
        "dwell_bars": distribution(dwells),
        "continued_through_center": through_center,
        "continued_through_center_pct": pct(through_center, len(starts)),
        "expired_before_center": expired_before_center,
        "expired_before_center_pct": pct(expired_before_center, len(starts)),
    }


def rse_report(samples: Sequence, context_dirs: Sequence[int]) -> dict:
    ready = [s for s in samples if s.ready]
    occupancy = Counter(s.state.name for s in ready)
    values = [s.value for s in samples]

    oversold_touches = _zone_touch_indices(values, oversold=True)
    overbought_touches = _zone_touch_indices(values, oversold=False)

    def produces(touches: Sequence[int], state: RsiState) -> int:
        count = 0
        for i in touches:
            stop = min(len(samples), i + ZONE_MEMORY_BARS + 1)
            if any(samples[j].ready and samples[j].state == state for j in range(i, stop)):
                count += 1
        return count

    context_by_state: dict[str, Counter[str]] = defaultdict(Counter)
    direction_totals = {1: Counter(), -1: Counter()}
    for sample, ctx in zip(samples, context_dirs):
        if not sample.ready:
            continue
        for direction in (1, -1):
            if local_supports(direction, sample.state):
                relation = "agree" if ctx == direction else "neutral" if ctx == 0 else "oppose"
                context_by_state[f"{direction:+d}:{sample.state.name}"][relation] += 1
                direction_totals[direction][relation] += 1

    return {
        "ready_bars": len(ready),
        "occupancy_counts": dict(sorted(occupancy.items())),
        "occupancy_pct": _state_pct(occupancy, len(ready)),
        "dwell_bars": _dwell(samples),
        "raw_zone_touches": {
            "oversold": len(oversold_touches),
            "overbought": len(overbought_touches),
        },
        "zone_touch_to_semantic_state": {
            "oversold_touches_producing_recovery": produces(
                oversold_touches, RsiState.RECOVERING_OVERSOLD
            ),
            "overbought_touches_producing_fade": produces(
                overbought_touches, RsiState.FADING_OVERBOUGHT
            ),
        },
        "recovery_fade_lifecycle": {
            "oversold_recovery": _recovery_lifecycle(
                values,
                samples,
                recovery_state=RsiState.RECOVERING_OVERSOLD,
                center_boundary=CENTER_HIGH,
                rising=True,
            ),
            "overbought_fade": _recovery_lifecycle(
                values,
                samples,
                recovery_state=RsiState.FADING_OVERBOUGHT,
                center_boundary=CENTER_LOW,
                rising=False,
            ),
        },
        "htf_context_interaction": {
            "by_supportive_state": {
                key: dict(value) for key, value in sorted(context_by_state.items())
            },
            "long": dict(direction_totals[1])
            | {"opposition_block_pct": pct(direction_totals[1]["oppose"], sum(direction_totals[1].values()))},
            "short": dict(direction_totals[-1])
            | {"opposition_block_pct": pct(direction_totals[-1]["oppose"], sum(direction_totals[-1].values()))},
        },
    }


def pse_report(
    bars: Sequence[ParticipationBar],
    long_samples: Sequence,
    short_samples: Sequence,
    taker_values: Sequence[float | None],
) -> dict:
    ready_idx = [i for i, s in enumerate(long_samples) if s.ready]
    rv = [float(long_samples[i].relative_volume) for i in ready_idx if long_samples[i].relative_volume is not None]
    pressure = [float(long_samples[i].pressure_proxy) for i in ready_idx]
    taker = [taker_values[i] for i in ready_idx]

    pairs = [(p, float(t)) for p, t in zip(pressure, taker) if t is not None]
    px = [x for x, _ in pairs]
    tx = [y for _, y in pairs]

    expanded_mask = [
        long_samples[i].relative_volume is not None
        and long_samples[i].relative_volume >= EXPANDED_AT_OR_ABOVE
        for i in ready_idx
    ]
    pressure_mask = [abs(p) >= PRESSURE_MIN for p in pressure]

    pair_ready_positions = [k for k, t in enumerate(taker) if t is not None]
    expanded_pair_mask = [expanded_mask[k] for k in pair_ready_positions]
    pressure_pair_mask = [pressure_mask[k] for k in pair_ready_positions]

    quadrants = Counter()
    excluded_zero = 0
    for p, t in pairs:
        sp = _sign(p, 0.0)
        st = _sign(t, 0.0)
        if sp == 0 or st == 0:
            excluded_zero += 1
            continue
        quadrants[f"proxy{'+' if sp > 0 else '-'}_taker{'+' if st > 0 else '-'}"] += 1

    abs_pressure = [abs(x) for x in pressure]
    zero_range = sum(1 for bar in bars if bar.high == bar.low)
    long_occ = Counter(s.state.name for s in long_samples if s.ready)
    short_occ = Counter(s.state.name for s in short_samples if s.ready)

    return {
        "ready_bars": len(ready_idx),
        "relative_volume": {
            "distribution": distribution(rv),
            "below_0_80": sum(x < CONTRACTED_BELOW for x in rv),
            "below_0_80_pct": pct(sum(x < CONTRACTED_BELOW for x in rv), len(rv)),
            "at_or_above_1_20": sum(x >= EXPANDED_AT_OR_ABOVE for x in rv),
            "at_or_above_1_20_pct": pct(sum(x >= EXPANDED_AT_OR_ABOVE for x in rv), len(rv)),
            "at_or_above_1_50": sum(x >= 1.50 for x in rv),
            "at_or_above_1_50_pct": pct(sum(x >= 1.50 for x in rv), len(rv)),
        },
        "pressure_proxy": {
            "distribution": distribution(pressure),
            "abs_distribution": distribution(abs_pressure),
            "positive": sum(x > 0 for x in pressure),
            "negative": sum(x < 0 for x in pressure),
            "zero": sum(x == 0 for x in pressure),
            "at_or_above_pos_0_20": sum(x >= PRESSURE_MIN for x in pressure),
            "at_or_above_pos_0_20_pct": pct(sum(x >= PRESSURE_MIN for x in pressure), len(pressure)),
            "at_or_below_neg_0_20": sum(x <= -PRESSURE_MIN for x in pressure),
            "at_or_below_neg_0_20_pct": pct(sum(x <= -PRESSURE_MIN for x in pressure), len(pressure)),
            "zero_range_candles": zero_range,
            "zero_range_pct_all_rows": pct(zero_range, len(bars)),
        },
        "proxy_vs_taker_imbalance": {
            "pairs": len(pairs),
            "pearson": pearson(px, tx),
            "spearman": spearman(px, tx),
            "sign_agreement": sign_agreement(px, tx),
            "sign_agreement_relvol_ge_1_20": sign_agreement(
                px, tx, mask=expanded_pair_mask
            ),
            "sign_agreement_abs_proxy_ge_0_20": sign_agreement(
                px, tx, mask=pressure_pair_mask
            ),
            "quadrants": dict(sorted(quadrants.items())),
            "quadrant_excluded_exact_zero": excluded_zero,
        },
        "semantic_occupancy_hypothetical": {
            "long_counts": dict(sorted(long_occ.items())),
            "long_pct": _state_pct(long_occ, sum(long_occ.values())),
            "short_counts": dict(sorted(short_occ.items())),
            "short_pct": _state_pct(short_occ, sum(short_occ.values())),
        },
    }


def _mte_aligned(direction: int, state: Momentum) -> bool:
    return state in (
        {Momentum.TURN_UP, Momentum.UP_ACCEL}
        if direction == 1
        else {Momentum.TURN_DOWN, Momentum.DOWN_ACCEL}
    )


def _mte_deteriorates(direction: int, state: Momentum) -> bool:
    if direction == 1:
        return state in {Momentum.UP_DECEL, Momentum.TURN_DOWN, Momentum.DOWN_ACCEL, Momentum.DOWN_DECEL}
    return state in {Momentum.DOWN_DECEL, Momentum.TURN_UP, Momentum.UP_ACCEL, Momentum.UP_DECEL}


def _rsi_deteriorates(direction: int, state: RsiState) -> bool:
    if direction == 1:
        return state in {RsiState.FADING_OVERBOUGHT, RsiState.EXTREME_OVERBOUGHT}
    return state in {RsiState.RECOVERING_OVERSOLD, RsiState.EXTREME_OVERSOLD}


def cross_engine_report(
    momentum_samples: Sequence,
    rsi_samples: Sequence,
    context_dirs: Sequence[int],
    pse_long: Sequence,
    pse_short: Sequence,
) -> dict:
    out = {}
    for direction, pse in ((1, pse_long), (-1, pse_short)):
        eligible = 0
        co = Counter()
        strength = Counter()
        for m, r, ctx, p in zip(momentum_samples, rsi_samples, context_dirs, pse):
            if not (m.ready and r.ready and p.ready):
                continue
            eligible += 1
            ma = _mte_aligned(direction, m.state)
            rs = supports(direction, r.state, ctx)
            pc = p.state == Participation.CONFIRM
            co["mte_rsi"] += int(ma and rs)
            co["mte_pse"] += int(ma and pc)
            co["rsi_pse"] += int(rs and pc)
            co["all_three"] += int(ma and rs and pc)

            families = sum(
                (
                    _mte_deteriorates(direction, m.state),
                    _rsi_deteriorates(direction, r.state),
                    p.state in {Participation.WEAK, Participation.CONTRARY},
                )
            )
            strength[str(families)] += 1

        out["long" if direction == 1 else "short"] = {
            "eligible_bars": eligible,
            "cooccurrence_counts": dict(co),
            "cooccurrence_pct": {k: pct(v, eligible) for k, v in co.items()},
            "deterioration_family_counts": dict(sorted(strength.items())),
            "deterioration_family_pct": {
                k: pct(v, eligible) for k, v in sorted(strength.items())
            },
        }
    return out


def yearly_basic(
    times: Sequence[datetime],
    momentum_samples: Sequence,
    rsi_samples: Sequence,
    context_dirs: Sequence[int],
    pse_long: Sequence,
    taker_values: Sequence[float | None],
) -> dict:
    years: dict[int, list[int]] = defaultdict(list)
    for i, t in enumerate(times):
        years[t.year].append(i)

    result = {}
    for year, idxs in sorted(years.items()):
        m_ready = [momentum_samples[i] for i in idxs if momentum_samples[i].ready]
        r_ready = [rsi_samples[i] for i in idxs if rsi_samples[i].ready]
        p_idxs = [i for i in idxs if pse_long[i].ready]

        mo = Counter(s.state.name for s in m_ready)
        ro = Counter(s.state.name for s in r_ready)
        rv = [
            float(pse_long[i].relative_volume)
            for i in p_idxs
            if pse_long[i].relative_volume is not None
        ]
        pairs = []
        for i in p_idxs:
            ti = taker_values[i]
            if ti is not None:
                pairs.append((float(pse_long[i].pressure_proxy), float(ti)))
        px = [a for a, _ in pairs]
        tx = [b for _, b in pairs]

        long_support = long_oppose = short_support = short_oppose = 0
        for i in idxs:
            r = rsi_samples[i]
            if not r.ready:
                continue
            ctx = context_dirs[i]
            if local_supports(1, r.state):
                long_support += 1
                long_oppose += int(ctx == -1)
            if local_supports(-1, r.state):
                short_support += 1
                short_oppose += int(ctx == 1)

        result[str(year)] = {
            "bars": len(idxs),
            "mte_ready": len(m_ready),
            "mte_occupancy_pct": _state_pct(mo, len(m_ready)),
            "rse_ready": len(r_ready),
            "rse_occupancy_pct": _state_pct(ro, len(r_ready)),
            "rse_htf_opposition_block_pct": {
                "long": pct(long_oppose, long_support),
                "short": pct(short_oppose, short_support),
            },
            "pse_ready": len(p_idxs),
            "pse_relative_volume": {
                "median": percentile(rv, 0.5),
                "below_0_80_pct": pct(sum(x < CONTRACTED_BELOW for x in rv), len(rv)),
                "at_or_above_1_20_pct": pct(sum(x >= EXPANDED_AT_OR_ABOVE for x in rv), len(rv)),
                "at_or_above_1_50_pct": pct(sum(x >= 1.50 for x in rv), len(rv)),
            },
            "proxy_vs_taker": {
                "pairs": len(pairs),
                "pearson": pearson(px, tx),
                "spearman": spearman(px, tx),
                "sign_agreement": sign_agreement(px, tx),
            },
        }
    return result


def build_context_dirs(
    timeframe: str,
    datasets: dict[str, dict],
    rsi_cache: dict[str, Sequence],
) -> list[int]:
    local = datasets[timeframe]
    context_tf = CONTEXT_TF[timeframe]
    if context_tf == timeframe:
        return [context_direction(s.value) if s.ready else 0 for s in rsi_cache[timeframe]]

    htf = datasets[context_tf]
    indices = confirmed_context_indices(local["open_time"], htf["open_time"])
    htf_samples = rsi_cache[context_tf]
    out = []
    for idx in indices:
        if idx is None:
            out.append(0)
        else:
            sample = htf_samples[idx]
            out.append(context_direction(sample.value) if sample.ready else 0)
    return out


def analyze_timeframe(
    timeframe: str,
    data: dict,
    context_dirs: Sequence[int],
) -> dict:
    momentum_bars = [
        MomentumBar(o, h, l, c)
        for o, h, l, c in zip(data["open"], data["high"], data["low"], data["close"])
    ]
    participation_bars = [
        ParticipationBar(h, l, c, v)
        for h, l, c, v in zip(data["high"], data["low"], data["close"], data["volume"])
    ]
    momentum = calculate_momentum(momentum_bars)
    rsi = calculate_rsi(data["close"])
    pse_long = calculate_participation(participation_bars, [1] * len(participation_bars))
    pse_short = calculate_participation(participation_bars, [-1] * len(participation_bars))
    taker = [
        taker_imbalance(v, b)
        for v, b in zip(data["volume"], data["taker_buy_base_asset_volume"])
    ]

    return {
        "mte_a": mte_report(momentum),
        "rse_a": rse_report(rsi, context_dirs),
        "pse_a": pse_report(participation_bars, pse_long, pse_short, taker),
        "cross_engine": cross_engine_report(momentum, rsi, context_dirs, pse_long, pse_short),
        "yearly": yearly_basic(
            data["open_time"], momentum, rsi, context_dirs, pse_long, taker
        ),
    }


def _to_market_map_candles(data: dict) -> list[MarketMapCandle]:
    return [
        MarketMapCandle(
            t=int(t.timestamp() * 1_000_000),
            o=o,
            h=h,
            l=l,
            c=c,
            v=v,
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


def market_map_integration_report(
    timeframe: str,
    datasets: dict[str, dict],
    context_dirs: Sequence[int],
    *,
    tick_size: float,
) -> dict:
    """Run accepted MM-0 semantics into the candidate Execution state machine."""

    chart = _to_market_map_candles(datasets[timeframe])
    context = _to_market_map_candles(datasets[CONTEXT_TF[timeframe]])
    daily = _to_market_map_candles(datasets["1d"])
    weekly = _to_market_map_candles(datasets["1w"])

    snapshots = []
    MarketMapKernel(
        chart,
        context,
        daily,
        weekly,
        timeframe,
        tick=tick_size,
    ).run(snapshots, emit_audit=False)

    if len(snapshots) != len(chart):
        raise AssertionError(
            f"{timeframe}: Market Map integration rows {len(snapshots)} != chart rows {len(chart)}"
        )
    if len(context_dirs) != len(chart):
        raise AssertionError(
            f"{timeframe}: RSI context rows {len(context_dirs)} != chart rows {len(chart)}"
        )

    memory = BridgeMemory()
    locations: list[Location] = []
    research_bars: list[ExecutionResearchBar] = []

    for candle, snapshot, rsi_context in zip(chart, snapshots, context_dirs):
        bridge = classify_map_location(
            memory,
            MapEvidence(
                bar_index=snapshot.bar_index,
                map_dir=snapshot.map_dir,
                atr=snapshot.atr,
                close=snapshot.close,
                correction_active=snapshot.correction_active,
                bar_time_ms=snapshot.time // 1000,
                thesis_invalidated=snapshot.thesis_invalidated,
                structural_conflict=snapshot.structural_conflict,
                t1_top=snapshot.t1_top,
                t1_bottom=snapshot.t1_bottom,
                primary_top=snapshot.primary_top,
                primary_bottom=snapshot.primary_bottom,
                t3_top=snapshot.t3_top,
                t3_bottom=snapshot.t3_bottom,
                retest_event=snapshot.retest_event,
                reclaim_event=snapshot.reclaim_event,
                destination_near=snapshot.destination_near,
            ),
        )
        memory = bridge.memory
        locations.append(bridge.location)
        research_bars.append(
            ExecutionResearchBar(
                open=candle.o,
                high=candle.h,
                low=candle.l,
                close=candle.c,
                volume=candle.v,
                map_dir=snapshot.map_dir,
                location=bridge.location,
                rsi_context_dir=rsi_context,
                thesis_invalidated=snapshot.thesis_invalidated,
                structural_conflict=snapshot.structural_conflict,
                bar_confirmed=True,
            )
        )

    samples = calculate_execution_candidate(research_bars)

    location_counts = Counter(loc.name for loc in locations)
    readiness_counts = Counter(sample.result.state.readiness.name for sample in samples)
    strength_counts = Counter(sample.result.state.strength.name for sample in samples)
    transition_counts = Counter()
    readiness_by_location: dict[str, Counter[str]] = defaultdict(Counter)
    strength_by_location: dict[str, Counter[str]] = defaultdict(Counter)
    gate_by_location: dict[str, Counter[str]] = defaultdict(Counter)
    event_counts = Counter()
    confirm_by_location = Counter()
    confirm_by_direction = Counter()
    yearly_confirm = Counter()

    previous_readiness: Readiness | None = None
    rsi_supportive_relevant = 0
    rsi_relevant = 0
    rsi_recovery_fade_relevant = 0

    for i, (bar, loc, sample) in enumerate(zip(research_bars, locations, samples)):
        result = sample.result
        readiness = result.state.readiness
        strength = result.state.strength
        readiness_by_location[loc.name][readiness.name] += 1
        strength_by_location[loc.name][strength.name] += 1

        if previous_readiness is not None:
            transition_counts[f"{previous_readiness.name}->{readiness.name}"] += 1
        previous_readiness = readiness

        if loc in RELEVANT_LOCATIONS and bar.map_dir in (-1, 1):
            gate_by_location[loc.name]["bars"] += 1
            momentum_aligned = _mte_aligned(
                bar.map_dir,
                Momentum[sample.momentum_state_name],
            )
            rsi_supportive = supports(
                bar.map_dir,
                RsiState[sample.rsi_state_name],
                bar.rsi_context_dir,
            )
            participation_confirm = (
                Participation[sample.participation_state_name] == Participation.CONFIRM
            )
            gate_by_location[loc.name]["momentum_aligned"] += int(momentum_aligned)
            gate_by_location[loc.name]["rsi_supportive"] += int(rsi_supportive)
            gate_by_location[loc.name]["participation_confirm"] += int(participation_confirm)
            gate_by_location[loc.name]["all_three"] += int(
                momentum_aligned and rsi_supportive and participation_confirm
            )

            rsi_relevant += 1
            rsi_supportive_relevant += int(rsi_supportive)
            rsi_recovery_fade_relevant += int(
                sample.rsi_state_name
                in {
                    "RECOVERING_OVERSOLD",
                    "RECOVERING_OVERBOUGHT",
                    "FADING_OVERBOUGHT",
                    "FADING_OVERSOLD",
                }
            )

        events = result.events
        for name in (
            "preparing_entered",
            "armed_entered",
            "confirm",
            "canceled",
            "reaction_risk_entered",
        ):
            if getattr(events, name):
                event_counts[name] += 1

        if events.confirm:
            confirm_by_location[loc.name] += 1
            confirm_by_direction["LONG" if result.state.direction == 1 else "SHORT"] += 1
            yearly_confirm[datasets[timeframe]["open_time"][i].year] += 1

    by_location = {}
    for loc_name, total in sorted(location_counts.items()):
        by_location[loc_name] = {
            "bars": total,
            "bar_pct": pct(total, len(locations)),
            "readiness_counts": dict(readiness_by_location[loc_name]),
            "readiness_pct": _state_pct(readiness_by_location[loc_name], total),
            "strength_counts": dict(strength_by_location[loc_name]),
            "strength_pct": _state_pct(strength_by_location[loc_name], total),
        }

    gate_summary = {}
    for loc_name, counts in sorted(gate_by_location.items()):
        total = counts["bars"]
        gate_summary[loc_name] = {
            "bars": total,
            "momentum_aligned_pct": pct(counts["momentum_aligned"], total),
            "rsi_supportive_pct": pct(counts["rsi_supportive"], total),
            "participation_confirm_pct": pct(counts["participation_confirm"], total),
            "all_three_pct": pct(counts["all_three"], total),
        }

    return {
        "tick_size": tick_size,
        "bars": len(samples),
        "location_counts": dict(sorted(location_counts.items())),
        "location_pct": _state_pct(location_counts, len(samples)),
        "readiness_counts": dict(sorted(readiness_counts.items())),
        "readiness_pct": _state_pct(readiness_counts, len(samples)),
        "strength_counts": dict(sorted(strength_counts.items())),
        "strength_pct": _state_pct(strength_counts, len(samples)),
        "readiness_transitions": dict(sorted(transition_counts.items())),
        "by_location": by_location,
        "relevant_location_gate_rates": gate_summary,
        "events": dict(sorted(event_counts.items())),
        "confirm_by_location": dict(sorted(confirm_by_location.items())),
        "confirm_by_direction": dict(sorted(confirm_by_direction.items())),
        "confirm_by_year": {str(k): v for k, v in sorted(yearly_confirm.items())},
        "rsi_at_relevant_locations": {
            "bars": rsi_relevant,
            "supportive_pct": pct(rsi_supportive_relevant, rsi_relevant),
            "recovery_fade_state_pct": pct(rsi_recovery_fade_relevant, rsi_relevant),
        },
    }


def _fmt(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown_report(report: dict) -> str:
    lines = [
        f"# Execution historical evidence — {report['metadata']['symbol']}",
        "",
        "This is semantic/component evidence, not a strategy backtest or profitability claim.",
        "",
        f"- symbol: **{report['metadata']['symbol']}**",
        f"- market: **{report['metadata']['market']}**",
        f"- code SHA: `{report['metadata']['code_sha']}`",
        f"- research defaults: v{report['metadata']['research_defaults_version']}",
        f"- suite semantics: v{report['metadata']['suite_contract_version']}",
        f"- sign near-zero convention: ±{SIGN_NEAR_ZERO}",
        "",
        "## Cross-timeframe summary",
        "",
        "| TF | Rows | MTE changes/100 | TURN % | RSE extremes % | HTF block L/S % | RV <0.8 / >=1.2 / >=1.5 % | Proxy↔taker Pearson / Spearman | Sign agree % | All-3 L/S % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tf in TIMEFRAMES:
        item = report["timeframes"][tf]
        m = item["evidence"]["mte_a"]
        r = item["evidence"]["rse_a"]
        p = item["evidence"]["pse_a"]
        x = item["evidence"]["cross_engine"]
        turn_pct = sum(
            (m["occupancy_pct"].get("TURN_UP") or 0.0, m["occupancy_pct"].get("TURN_DOWN") or 0.0)
        )
        extreme_pct = sum(
            (r["occupancy_pct"].get("EXTREME_OVERBOUGHT") or 0.0, r["occupancy_pct"].get("EXTREME_OVERSOLD") or 0.0)
        )
        rv = p["relative_volume"]
        corr = p["proxy_vs_taker_imbalance"]
        lines.append(
            "| {tf} | {rows} | {chg} | {turn} | {ext} | {bl}/{bs} | {weak}/{exp}/{strong} | {pear}/{spear} | {agree} | {al}/{as_} |".format(
                tf=tf,
                rows=item["metadata"]["rows"],
                chg=_fmt(m["chatter"]["state_changes_per_100_ready_bars"]),
                turn=_fmt(turn_pct),
                ext=_fmt(extreme_pct),
                bl=_fmt(r["htf_context_interaction"]["long"].get("opposition_block_pct")),
                bs=_fmt(r["htf_context_interaction"]["short"].get("opposition_block_pct")),
                weak=_fmt(rv["below_0_80_pct"]),
                exp=_fmt(rv["at_or_above_1_20_pct"]),
                strong=_fmt(rv["at_or_above_1_50_pct"]),
                pear=_fmt(corr["pearson"], 3),
                spear=_fmt(corr["spearman"], 3),
                agree=_fmt(corr["sign_agreement"]["agreement_pct"]),
                al=_fmt(x["long"]["cooccurrence_pct"].get("all_three")),
                as_=_fmt(x["short"]["cooccurrence_pct"].get("all_three")),
            )
        )
    integration_tfs = [
        tf for tf in TIMEFRAMES
        if "market_map_integration" in report["timeframes"][tf]["evidence"]
    ]
    if integration_tfs:
        lines += [
            "",
            "## Accepted Market Map -> Execution integration",
            "",
            "| TF | Relevant location % | PREP % | ARMED % | CONFIRM events | ALIGNED % | RSI supportive @ relevant % | RSI recovery/fade @ relevant % |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for tf in integration_tfs:
            integ = report["timeframes"][tf]["evidence"]["market_map_integration"]
            relevant_pct = sum(
                integ["location_pct"].get(name) or 0.0
                for name in ("APPROACHING", "IN_CORRECTION", "RETEST", "RECLAIM")
            )
            lines.append(
                "| {tf} | {rel} | {prep} | {armed} | {confirm} | {aligned} | {rsi} | {rf} |".format(
                    tf=tf,
                    rel=_fmt(relevant_pct),
                    prep=_fmt(integ["readiness_pct"].get("PREP")),
                    armed=_fmt(integ["readiness_pct"].get("ARMED")),
                    confirm=integ["events"].get("confirm", 0),
                    aligned=_fmt(integ["readiness_pct"].get("ALIGNED")),
                    rsi=_fmt(integ["rsi_at_relevant_locations"].get("supportive_pct")),
                    rf=_fmt(integ["rsi_at_relevant_locations"].get("recovery_fade_state_pct")),
                )
            )

    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- No metric above is a trade win rate.",
        "- No thresholds were tuned from these results.",
        "- Higher-timeframe small samples are robustness evidence, not optimization targets.",
        "- Engine decisions remain KEEP / REFINE / REMOVE / INSUFFICIENT EVIDENCE after human review of the pre-registered questions.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--canonical-manifest", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--code-sha", default="unknown")
    parser.add_argument(
        "--market-map-integration",
        action="store_true",
        help="Condition Execution evidence on accepted MM-0 offline semantics.",
    )
    parser.add_argument(
        "--tick-size",
        type=float,
        default=None,
        help="Instrument minimum tick for MM-0 integration; required with --market-map-integration.",
    )
    args = parser.parse_args()

    if args.market_map_integration and (args.tick_size is None or args.tick_size <= 0):
        parser.error("--tick-size > 0 is required with --market-map-integration")

    canonical = json.loads(args.canonical_manifest.read_text(encoding="utf-8"))
    expected = {d["timeframe"]: d for d in canonical["datasets"]}
    symbol = args.symbol.upper()
    market = canonical.get("market", "spot")

    datasets: dict[str, dict] = {}
    dataset_meta: dict[str, dict] = {}
    for tf in TIMEFRAMES:
        path = args.data_root / market / symbol / "consolidated" / f"{symbol}_{tf}.parquet"
        if not path.is_file():
            raise SystemExit(f"missing dataset: {path}")
        actual_hash = sha256_file(path)
        exp = expected[tf]
        if actual_hash != exp["dataset_sha256"]:
            raise SystemExit(
                f"{symbol} {tf}: dataset SHA mismatch: {actual_hash} != {exp['dataset_sha256']}"
            )
        data = load_dataset(path)
        datasets[tf] = data
        dataset_meta[tf] = {
            "path": str(path),
            "dataset_sha256": actual_hash,
            "canonical_dataset_sha256": exp["dataset_sha256"],
            "first_date": exp["first_date"],
            "last_date": exp["last_date"],
            "rows": len(data["close"]),
            "canonical_candles": exp["candles"],
            "status": exp["status"],
        }
        if len(data["close"]) != exp["candles"]:
            raise SystemExit(
                f"{symbol} {tf}: row mismatch: {len(data['close'])} != {exp['candles']}"
            )

    rsi_cache = {tf: calculate_rsi(datasets[tf]["close"]) for tf in TIMEFRAMES}

    defaults_path = Path("manifests/execution-research-defaults-v2.json")
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
            "research_defaults_manifest": str(defaults_path),
            "research_defaults_manifest_sha256": sha256_file(defaults_path),
            "research_defaults_version": defaults["execution_research_defaults_version"],
            "suite_semantics_manifest": str(semantics_path),
            "suite_semantics_manifest_sha256": sha256_file(semantics_path),
            "suite_contract_version": semantics["suite_contract_version"],
            "code_sha": args.code_sha,
            "analysis_conventions": {
                "sign_near_zero_epsilon": SIGN_NEAR_ZERO,
                "confirmed_htf": "previous completed HTF bar ([1] + lookahead_on equivalent)",
                "above_1d_context": "self confirmed RSI context",
                "pse_component_direction": "hypothetical LONG and SHORT classifications; not Execution signals",
                "market_map_integration": bool(args.market_map_integration),
                "market_map_tick_size": args.tick_size,
            },
        },
        "timeframes": {},
        "decision": {
            "mte_a": "REVIEW_REQUIRED",
            "rse_a": "REVIEW_REQUIRED",
            "pse_a": "REVIEW_REQUIRED",
            "note": "KEEP/REFINE/REMOVE/INSUFFICIENT EVIDENCE is assigned only after reviewing the pre-registered questions.",
        },
    }

    for tf in TIMEFRAMES:
        context_dirs = build_context_dirs(tf, datasets, rsi_cache)
        evidence = analyze_timeframe(tf, datasets[tf], context_dirs)
        if args.market_map_integration:
            assert args.tick_size is not None
            evidence["market_map_integration"] = market_map_integration_report(
                tf,
                datasets,
                context_dirs,
                tick_size=args.tick_size,
            )
        report["timeframes"][tf] = {
            "metadata": dataset_meta[tf]
            | {
                "context_timeframe": CONTEXT_TF[tf],
                "start": datasets[tf]["open_time"][0].isoformat(),
                "end": datasets[tf]["open_time"][-1].isoformat(),
            },
            "evidence": evidence,
        }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(markdown_report(report) + "\n", encoding="utf-8")
    print(markdown_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations
import bisect, math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence
AUDIT_SCHEMA = 2
MID_LEN = 50
SLOW_LEN = 200
ATR_LEN = 14
PIVOT_LEN = 3
POOL_MAX = 24
RETEST_MAX_BARS = 24
FAIL_MAX_BARS = 6
PULLBACK_SAMPLE_MAX = 24
PULLBACK_MIN_SAMPLES = 5
ACCEPTANCE_BINS = 20
ACCEPTANCE_MAX_BARS = 240
EQ_TOL_ATR = 0.12
RETEST_TOL_ATR = 0.18
FAIL_TOL_ATR = 0.08
INVALID_TOL_ATR = 0.12
TARGET_MERGE_ATR = 0.1
TARGET_NEAR_ATR = 0.30
PULLBACK_MIN_DEPTH = 0.12
PULLBACK_MAX_DEPTH = 0.9
AUDIT_HEADER = ['Time', 'Open', 'High', 'Low', 'Close', 'MM Audit • Schema', 'MM Audit • Confirmado', 'MM Audit • MapDir', 'MM Audit • ATR', 'MM Audit • Modelo', 'MM Audit • Amostras adaptativas', 'MM Audit • Correção topo', 'MM Audit • Correção fundo', 'MM Audit • Destino 1', 'MM Audit • Invalidação', 'MM Audit • Confluências', 'MM Audit • Nova tese evt', 'MM Audit • Toque zona evt', 'MM Audit • Zona→Destino evt', 'MM Audit • Zona→Invalidação evt', 'MM Audit • Ambíguo evt', 'MM Audit • Sweep reclaim evt']
CONTEXT_TF = {'15m': '1h', '1h': '4h', '4h': '1d', '1d': '1w', '3d': '3d', '1w': '1w', '1M': '1M'}
DAY_LEVEL_TFS = {'15m', '1h', '4h', '1d'}
WEEK_LEVEL_TFS = set(CONTEXT_TF) - {'1M'}

@dataclass(frozen=True)
class Candle:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float

    @property
    def hlc3(self):
        return (self.h + self.l + self.c) / 3

@dataclass(frozen=True)
class IntegrationSnapshot:
    bar_index: int
    time: int
    map_dir: int
    atr: float | None
    close: float
    correction_active: bool
    thesis_invalidated: bool
    structural_conflict: bool
    t1_top: float | None
    t1_bottom: float | None
    primary_top: float | None
    primary_bottom: float | None
    t3_top: float | None
    t3_bottom: float | None
    retest_event: bool
    reclaim_event: bool
    destination_near: bool

    # 0.2 research telemetry only. These fields expose state already calculated
    # by the accepted MM-0 kernel; they do not alter Market Map semantics.
    regime_dir: int = 0
    structure_dir: int = 0
    structural_break_dir: int = 0
    fakeout_event: bool = False
    new_thesis_event: bool = False
    thesis_key: int | None = None
    destination: float | None = None
    invalidation: float | None = None
    structural_break_level: float | None = None

    # Range-rotation research telemetry. Values are confirmed swing/reclaim
    # state already known by MM-0 on this bar; exposing them does not change
    # any production Market Map decision.
    last_swing_high: float | None = None
    last_swing_high_bar: int | None = None
    prev_swing_high: float | None = None
    prev_swing_high_bar: int | None = None
    last_swing_low: float | None = None
    last_swing_low_bar: int | None = None
    prev_swing_low: float | None = None
    prev_swing_low_bar: int | None = None
    raw_upper_reclaim_level: float | None = None
    raw_lower_reclaim_level: float | None = None


@dataclass
class Pool:
    level: float
    swept: bool
    bar: int

@dataclass
class Tracker:
    key: int | None = None
    direction: int = 0
    target: float | None = None
    touch_bar: int | None = None
    touched: bool = False
    target_hit: bool = False
    invalidated: bool = False
    resolved: bool = False
    same_bar_target_ordered: bool = False
    superseded: int = 0

    def start(self, key: int, direction: int):
        if self.touched and (not self.resolved):
            self.superseded += 1
        self.key = key
        self.direction = direction
        self.target = None
        self.touch_bar = None
        self.same_bar_target_ordered = False
        self.touched = self.target_hit = self.invalidated = self.resolved = False

    def touch(
        self,
        bar: int,
        target: float | None,
        *,
        open_value: float | None = None,
        zone_top: float | None = None,
        zone_bottom: float | None = None,
    ):
        self.touched = True
        self.touch_bar = bar
        self.target = target
        self.same_bar_target_ordered = bool(
            target is not None
            and open_value is not None
            and zone_top is not None
            and zone_bottom is not None
            and (
                (self.direction == 1 and target > zone_top and open_value <= zone_top)
                or (self.direction == -1 and target < zone_bottom and open_value >= zone_bottom)
            )
        )

    def resolve(self, bar: int, hi: float, lo: float, thesis_invalidated: bool):
        d = self.touched and (not self.target_hit) and (self.target is not None) and (self.direction == 1 and hi >= self.target or (self.direction == -1 and lo <= self.target))
        inv = self.touched and thesis_invalidated and (not self.invalidated)
        same_bar = self.touch_bar == bar
        ordered_dest_only = same_bar and d and (not inv) and self.same_bar_target_ordered
        amb = not self.resolved and ((same_bar and (d or inv) and not ordered_dest_only) or (d and inv))
        de = d and (not amb) and (not self.resolved)
        ie = inv and (not amb) and (not self.resolved)
        if amb:
            self.resolved = True
        if d:
            self.target_hit = True
        if inv:
            self.invalidated = True
        if de or ie:
            self.resolved = True
        return (bool(de), bool(ie), bool(amb))

def ema(xs: Sequence[float], n: int):
    a = 2 / (n + 1)
    out = []
    p = None
    for x in xs:
        p = x if p is None else a * x + (1 - a) * p
        out.append(p)
    return out

def rma(xs: Sequence[float], n: int):
    out = [None] * len(xs)
    if len(xs) < n:
        return out
    p = sum(xs[:n]) / n
    out[n - 1] = p
    for i in range(n, len(xs)):
        p = (p * (n - 1) + xs[i]) / n
        out[i] = p
    return out

def atr(cs: Sequence[Candle], n: int=ATR_LEN):
    tr = []
    for i, x in enumerate(cs):
        tr.append(x.h - x.l if i == 0 else max(x.h - x.l, abs(x.h - cs[i - 1].c), abs(x.l - cs[i - 1].c)))
    return rma(tr, n)

def quantile(xs: Sequence[float], q: float):
    if not xs:
        return None
    a = sorted(xs)
    p = (len(a) - 1) * q
    lo = math.floor(p)
    hi = math.ceil(p)
    return a[lo] if lo == hi else a[lo] + (a[hi] - a[lo]) * (p - lo)

def adaptive(xs: Sequence[float]):
    if len(xs) < PULLBACK_MIN_SAMPLES:
        return (False, 0.5, 0.618)
    q1, m, q3 = (quantile(xs, 0.25), quantile(xs, 0.5), quantile(xs, 0.75))
    half = max(0.045, min(0.11, (q3 - q1) * 0.45))
    shallow = max(0.236, min(0.786, m - half))
    deep = max(shallow + 0.04, min(0.886, m + half))
    return (True, shallow, deep)

def phigh(xs: Sequence[float], i: int, n: int=PIVOT_LEN):
    c = i - n
    left = c - n
    if left < 0:
        return None
    v = xs[c]
    return v if all((v >= xs[j] for j in range(left, c))) and all((v > xs[j] for j in range(c + 1, i + 1))) else None

def plow(xs: Sequence[float], i: int, n: int=PIVOT_LEN):
    c = i - n
    left = c - n
    if left < 0:
        return None
    v = xs[c]
    return v if all((v <= xs[j] for j in range(left, c))) and all((v < xs[j] for j in range(c + 1, i + 1))) else None

def bucket(times: Sequence[int], t: int):
    cur = bisect.bisect_right(times, t) - 1
    return (None, None) if cur < 0 else (cur, cur - 1 if cur else None)


def context_index(times: Sequence[int], t: int, *, self_context: bool) -> int | None:
    """Match Pine f_sec(): current value on self-TF, prior confirmed value on HTF."""
    cur, prev = bucket(times, t)
    return cur if self_context else prev

def push_sample(a: list[float], x: float | None):
    if x is not None and PULLBACK_MIN_DEPTH <= x <= PULLBACK_MAX_DEPTH:
        a.append(x)
        if len(a) > PULLBACK_SAMPLE_MAX:
            a.pop(0)

def in_zone(x, top, bottom, tol):
    return x is not None and top is not None and (bottom is not None) and (bottom - tol <= x <= top + tol)

def usable_target(direction: int, target: float | None, top: float | None, bottom: float | None) -> bool:
    if target is None or top is None or bottom is None:
        return False
    return (direction == 1 and target > top) or (direction == -1 and target < bottom)

def acceptance(cs: Sequence[Candle], cur: int, start: int | None, end: int | None, lo, hi, tick):
    if start is None or end is None or lo is None or (hi is None) or (hi - lo <= tick):
        return (None, None, 0)
    bins = [0.0] * ACCEPTANCE_BINS
    pv = vol = 0.0
    count = 0
    for j in range(min(cur, end), max(0, cur - ACCEPTANCE_MAX_BARS + 1, start) - 1, -1):
        x = cs[j]
        if x.v <= 0:
            continue
        p = x.hlc3
        pv += p * x.v
        vol += x.v
        count += 1
        k = int(math.floor(max(0, min(0.999999, (p - lo) / (hi - lo))) * ACCEPTANCE_BINS))
        bins[k] += x.v
    if vol <= 0:
        return (None, None, count)
    k = max(range(ACCEPTANCE_BINS), key=bins.__getitem__)
    return (pv / vol, lo + (k + 0.5) * (hi - lo) / ACCEPTANCE_BINS, count)

class Kernel:

    def __init__(self, chart, context, daily, weekly, timeframe, tick=0.01):
        if timeframe not in CONTEXT_TF:
            raise ValueError(timeframe)
        self.x = list(chart)
        self.ctx = list(context)
        self.d = list(daily)
        self.w = list(weekly)
        self.tf = timeframe
        self.tick = tick
        self.self_context = CONTEXT_TF[timeframe] == timeframe
        self.day_levels_allowed = timeframe in DAY_LEVEL_TFS
        self.week_levels_allowed = timeframe in WEEK_LEVEL_TFS
        closes = [x.c for x in self.x]
        highs = [x.h for x in self.x]
        lows = [x.l for x in self.x]
        self.mid = ema(closes, MID_LEN)
        self.slow = ema(closes, SLOW_LEN)
        self.a = atr(self.x)
        self.ph = [phigh(highs, i) for i in range(len(self.x))]
        self.pl = [plow(lows, i) for i in range(len(self.x))]
        cc = [x.c for x in self.ctx]
        self.cm = ema(cc, MID_LEN)
        self.cs = ema(cc, SLOW_LEN)
        self.ct = [x.t for x in self.ctx]
        self.dt = [x.t for x in self.d]
        self.wt = [x.t for x in self.w]

    def run(
        self,
        integration_rows: list[IntegrationSnapshot] | None = None,
        *,
        emit_audit: bool = True,
    ):
        rows = []
        hp = []
        lp = []
        bulls = []
        bears = []
        tr = Tracker()
        lsh = psh = None
        lshb = pshb = None
        lht = '—'
        lsl = psl = None
        lslb = pslb = None
        llt = '—'
        sdir = 0
        break_level = None
        break_dir = 0
        break_bar = None
        pre_sdir = 0
        live_dir = 0
        live_lo = live_hi = None
        live_start = live_break = None
        pdhs = pdls = pwhs = pwls = False
        prev_db = prev_wb = None
        invalid_key = None
        prev_close = prev_lsh = prev_lsl = None
        prev_map = 0
        prev_dest = None
        highs = [x.h for x in self.x]
        lows = [x.l for x in self.x]
        for i, x in enumerate(self.x):
            a = self.a[i]
            mid = self.mid[i]
            slow = self.slow[i]
            cp = context_index(self.ct, x.t, self_context=self.self_context)
            cclose = self.ctx[cp].c if cp is not None else None
            cm = self.cm[cp] if cp is not None else None
            cs = self.cs[cp] if cp is not None else None
            s3 = self.slow[i - 3] if i >= 3 else None
            lb = mid is not None and slow is not None and (s3 is not None) and (mid > slow) and (slow >= s3)
            lr = mid is not None and slow is not None and (s3 is not None) and (mid < slow) and (slow <= s3)
            cb = cm is not None and cs is not None and (cclose is not None) and (cm > cs) and (cclose > cs)
            cr = cm is not None and cs is not None and (cclose is not None) and (cm < cs) and (cclose < cs)
            regime = 1 if lb and cb else -1 if lr and cr else 0
            ph = self.ph[i]
            pl = self.pl[i]
            pbar = i - PIVOT_LEN
            if pl is not None and lht == 'HH' and (lslb is not None) and (lshb is not None) and (lslb < lshb < pbar):
                r = lsh - lsl
                push_sample(bulls, (lsh - pl) / r if r > self.tick else None)
            if ph is not None and llt == 'LL' and (lshb is not None) and (lslb is not None) and (lshb < lslb < pbar):
                r = lsh - lsl
                push_sample(bears, (ph - lsl) / r if r > self.tick else None)
            if ph is not None:
                psh, pshb = (lsh, lshb)
                lsh, lshb = (ph, pbar)
                lht = 'H' if psh is None else 'HH' if ph > psh else 'LH'
                hp.append(Pool(ph, max(highs[max(0, i - 2):i + 1]) > ph + self.tick, pbar))
                hp = hp[-POOL_MAX:]
            if pl is not None:
                psl, pslb = (lsl, lslb)
                lsl, lslb = (pl, pbar)
                llt = 'L' if psl is None else 'HL' if pl > psl else 'LL'
                lp.append(Pool(pl, min(lows[max(0, i - 2):i + 1]) < pl - self.tick, pbar))
                lp = lp[-POOL_MAX:]
            rec_a = rec_b = None
            for p in hp:
                if not p.swept and x.h > p.level + self.tick:
                    if x.c < p.level and (rec_a is None or p.level < rec_a):
                        rec_a = p.level
                    p.swept = True
            for p in lp:
                if not p.swept and x.l < p.level - self.tick:
                    if x.c > p.level and (rec_b is None or p.level > rec_b):
                        rec_b = p.level
                    p.swept = True
            bu = lsh is not None and prev_close is not None and (prev_lsh is not None) and (x.c > lsh) and (prev_close <= prev_lsh)
            bd = lsl is not None and prev_close is not None and (prev_lsl is not None) and (x.c < lsl) and (prev_close >= prev_lsl)
            if bu:
                pre_sdir = sdir
                sdir = 1
                break_level = lsh
                break_dir = 1
                break_bar = i
                live_dir = 1
                live_lo = lsl
                live_hi = x.h
                live_start = lslb
                live_break = i
            if bd:
                pre_sdir = sdir
                sdir = -1
                break_level = lsl
                break_dir = -1
                break_bar = i
                live_dir = -1
                live_hi = lsh
                live_lo = x.l
                live_start = lshb
                live_break = i
            if live_dir == 1 and live_hi is not None:
                live_hi = max(live_hi, x.h)
            if live_dir == -1 and live_lo is not None:
                live_lo = min(live_lo, x.l)
            retest_up = break_dir == 1 and break_bar is not None and (a is not None) and (i > break_bar) and (i - break_bar <= RETEST_MAX_BARS) and (x.l <= break_level + a * RETEST_TOL_ATR) and (x.c >= break_level)
            retest_down = break_dir == -1 and break_bar is not None and (a is not None) and (i > break_bar) and (i - break_bar <= RETEST_MAX_BARS) and (x.h >= break_level - a * RETEST_TOL_ATR) and (x.c <= break_level)
            fu = break_dir == 1 and break_bar is not None and (a is not None) and (i > break_bar) and (i - break_bar <= FAIL_MAX_BARS) and (x.c < break_level - a * FAIL_TOL_ATR)
            fd = break_dir == -1 and break_bar is not None and (a is not None) and (i > break_bar) and (i - break_bar <= FAIL_MAX_BARS) and (x.c > break_level + a * FAIL_TOL_ATR)
            if fu or fd:
                sdir = pre_sdir
                break_dir = 0
                live_dir = 0
            db, dp = bucket(self.dt, x.t)
            wb, wp = bucket(self.wt, x.t)
            if prev_db is not None and db != prev_db:
                pdhs = pdls = False
            if prev_wb is not None and wb != prev_wb:
                pwhs = pwls = False
            prev_db, prev_wb = (db, wb)
            pdh = self.d[dp].h if self.day_levels_allowed and dp is not None else None
            pdl = self.d[dp].l if self.day_levels_allowed and dp is not None else None
            pwh = self.w[wp].h if self.week_levels_allowed and wp is not None else None
            pwl = self.w[wp].l if self.week_levels_allowed and wp is not None else None
            if pdh is not None and (not pdhs) and (x.h > pdh + self.tick):
                if x.c < pdh and (rec_a is None or pdh < rec_a):
                    rec_a = pdh
                pdhs = True
            if pdl is not None and (not pdls) and (x.l < pdl - self.tick):
                if x.c > pdl and (rec_b is None or pdl > rec_b):
                    rec_b = pdl
                pdls = True
            if pwh is not None and (not pwhs) and (x.h > pwh + self.tick):
                if x.c < pwh and (rec_a is None or pwh < rec_a):
                    rec_a = pwh
                pwhs = True
            if pwl is not None and (not pwls) and (x.l < pwl - self.tick):
                if x.c > pwl and (rec_b is None or pwl > rec_b):
                    rec_b = pwl
                pwls = True
            above = [p.level for p in hp if not p.swept and p.level > x.c]
            below = [p.level for p in lp if not p.swept and p.level < x.c]
            if pdh is not None and (not pdhs) and (pdh > x.c):
                above.append(pdh)
            if pwh is not None and (not pwhs) and (pwh > x.c):
                above.append(pwh)
            if pdl is not None and (not pdls) and (pdl < x.c):
                below.append(pdl)
            if pwl is not None and (not pwls) and (pwl < x.c):
                below.append(pwl)
            la = min(above) if above else None
            lbv = max(below) if below else None
            conflict = regime and sdir and (regime != sdir)
            mdir = 0 if conflict else regime if regime else sdir
            rel_rec = rec_b if mdir == 1 else rec_a if mdir == -1 else None
            reclaim_evt = mdir if rel_rec is not None else 0
            dest = la if mdir == 1 else lbv if mdir == -1 else None
            ilo = ihi = None
            istart = iend = None
            if mdir == 1 and lsh is not None and (lshb is not None):
                if lslb is not None and lslb < lshb:
                    ilo, istart = (lsl, lslb)
                elif pslb is not None and pslb < lshb:
                    ilo, istart = (psl, pslb)
                ihi, iend = (lsh, lshb)
            if mdir == -1 and lsl is not None and (lslb is not None):
                if lshb is not None and lshb < lslb:
                    ihi, istart = (lsh, lshb)
                elif pshb is not None and pshb < lslb:
                    ihi, istart = (psh, pshb)
                ilo, iend = (lsl, lslb)
            use_live = False
            newer = iend is None or (live_break is not None and live_break > iend)
            if mdir == 1 and live_dir == 1 and (live_start is not None) and (live_lo is not None) and (live_hi is not None) and newer:
                ilo, ihi, istart, iend, use_live = (live_lo, live_hi, live_start, i, True)
            if mdir == -1 and live_dir == -1 and (live_start is not None) and (live_lo is not None) and (live_hi is not None) and newer:
                ilo, ihi, istart, iend, use_live = (live_lo, live_hi, live_start, i, True)
            rng = ihi - ilo if ihi is not None and ilo is not None else None
            ready = rng is not None and rng > self.tick * 20 and (iend is not None)
            samples = len(bulls) if mdir == 1 else len(bears) if mdir == -1 else 0
            emp, shallow, deep = adaptive(bulls if mdir == 1 else bears if mdir == -1 else [])
            top = bot = fibt = fibb = None
            t1_top = t1_bottom = t3_top = t3_bottom = None
            model = 0
            if ready:
                if mdir == 1:
                    fib382 = ihi - rng * 0.382
                    fib500 = ihi - rng * 0.500
                    fib618 = ihi - rng * 0.618
                    fib786 = ihi - rng * 0.786
                    a1 = ihi - rng * shallow
                    a2 = ihi - rng * deep
                else:
                    fib382 = ilo + rng * 0.382
                    fib500 = ilo + rng * 0.500
                    fib618 = ilo + rng * 0.618
                    fib786 = ilo + rng * 0.786
                    a1 = ilo + rng * shallow
                    a2 = ilo + rng * deep
                f1 = fib500
                f2 = fib618
                t1_top, t1_bottom = (max(fib382, fib500), min(fib382, fib500))
                t3_top, t3_bottom = (max(fib618, fib786), min(fib618, fib786))
                top, bot = (max(a1, a2), min(a1, a2))
                fibt, fibb = (max(f1, f2), min(f1, f2))
                model = 4 if use_live and emp else 3 if use_live else 2 if emp else 1
            inval = key = None
            if ready and a is not None:
                inval = ilo - a * INVALID_TOL_ATR if mdir == 1 else ihi + a * INVALID_TOL_ATR
                key = istart * 3 + (mdir + 1)
                broken = x.c < inval if mdir == 1 else x.c > inval
                if broken:
                    invalid_key = key
            thesis_inv = ready and key is not None and (invalid_key == key)
            active = ready and (not thesis_inv)
            destination_near = bool(dest is not None and a is not None and a > 0 and abs(dest - x.c) / a <= TARGET_NEAR_ATR and not thesis_inv)
            retest_evt = bool((mdir == 1 and retest_up) or (mdir == -1 and retest_down))
            reclaim_aligned_evt = bool(reclaim_evt == mdir and mdir in (-1, 1))
            new = ready and key is not None and (key != tr.key)
            if new:
                tr.start(key, mdir)
            touch = bool(active and (not tr.touched) and (top is not None) and (x.h >= bot) and (x.l <= top))
            tv = tn = None
            tb = 0
            if touch:
                tv, tn, tb = acceptance(self.x, i, istart, iend, ilo, ihi, self.tick)
                prev_target_usable = prev_map == mdir and usable_target(mdir, prev_dest, top, bot)
                current_target_usable = usable_target(mdir, dest, top, bot)
                tracked_target = prev_dest if prev_target_usable else dest if current_target_usable else None
                tr.touch(i, tracked_target, open_value=x.o, zone_top=top, zone_bottom=bot)
            de, ie, amb = tr.resolve(i, x.h, x.l, thesis_inv)
            tol = (a or 0) * 0.15
            fib = ready and top is not None and (top >= fibb) and (bot <= fibt)
            conf = (1 if active else 0) + int(fib) + int(in_zone(mid, top, bot, tol)) + int(in_zone(break_level, top, bot, tol))
            reaction = rel_rec if rel_rec is not None else lbv if mdir == 1 else la if mdir == -1 else None
            conf += int(in_zone(reaction, top, bot, tol))
            conf += int(tb >= 8 and tv is not None and (in_zone(tv, top, bot, tol) or in_zone(tn, top, bot, tol)))
            if integration_rows is not None:
                integration_rows.append(IntegrationSnapshot(
                    bar_index=i,
                    time=x.t,
                    map_dir=mdir,
                    atr=a,
                    close=x.c,
                    correction_active=bool(active),
                    thesis_invalidated=bool(thesis_inv),
                    structural_conflict=bool(conflict),
                    t1_top=t1_top if active else None,
                    t1_bottom=t1_bottom if active else None,
                    primary_top=top if active else None,
                    primary_bottom=bot if active else None,
                    t3_top=t3_top if active else None,
                    t3_bottom=t3_bottom if active else None,
                    retest_event=retest_evt,
                    reclaim_event=reclaim_aligned_evt,
                    destination_near=destination_near,
                    regime_dir=regime,
                    structure_dir=sdir,
                    structural_break_dir=1 if bu else -1 if bd else 0,
                    fakeout_event=bool(fu or fd),
                    new_thesis_event=bool(new),
                    thesis_key=key,
                    destination=None if thesis_inv else dest,
                    invalidation=inval if ready else None,
                    structural_break_level=break_level if (bu or bd) else None,
                    last_swing_high=lsh,
                    last_swing_high_bar=lshb,
                    prev_swing_high=psh,
                    prev_swing_high_bar=pshb,
                    last_swing_low=lsl,
                    last_swing_low_bar=lslb,
                    prev_swing_low=psl,
                    prev_swing_low_bar=pslb,
                    raw_upper_reclaim_level=rec_a,
                    raw_lower_reclaim_level=rec_b,
                ))
            ts = datetime.fromtimestamp(x.t / 1000000.0, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
            if emit_audit:
                rows.append(dict(zip(AUDIT_HEADER, [ts, x.o, x.h, x.l, x.c, AUDIT_SCHEMA, 1, mdir, a, model, samples, top if active else None, bot if active else None, None if thesis_inv else dest, inval if ready else None, conf, int(new), int(touch),int(de),int(ie),int(amb), reclaim_evt])))
            prev_close = x.c
            prev_lsh = lsh
            prev_lsl = lsl
            prev_map = mdir
            prev_dest = dest
        return rows

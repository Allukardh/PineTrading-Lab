#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path
from market_map_offline_core import AUDIT_HEADER, Candle, Kernel

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def load(p):
    try:
        import pyarrow.parquet as pq
    except ImportError as e:
        raise RuntimeError('pyarrow is required') from e
    t = pq.read_table(p, columns=['open_time', 'open', 'high', 'low', 'close', 'volume'])
    cols = [t[n].to_pylist() for n in ['open_time', 'open', 'high', 'low', 'close', 'volume']]
    out = []
    for dt, o, h, l, c, v in zip(*cols):
        out.append(Candle(int(round(dt.timestamp() * 1000000.0)), float(o), float(h), float(l), float(c), float(v)))
    return out

def write(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_HEADER)
        w.writeheader()
        w.writerows(({k: '' if r[k] is None else r[k] for k in AUDIT_HEADER} for r in rows))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-root', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--json', type=Path)
    ap.add_argument('--tick-size', type=float, default=0.01)
    a = ap.parse_args()
    specs = [('15m', '1h'), ('1h', '4h'), ('4h', '1d'), ('1d', '1w')]
    d = load(a.data_root / 'BTCUSDT_1d.parquet')
    w = load(a.data_root / 'BTCUSDT_1w.parquet')
    rep = []
    for tf, ctx in specs:
        cp = a.data_root / f'BTCUSDT_{tf}.parquet'
        hp = a.data_root / f'BTCUSDT_{ctx}.parquet'
        rows = Kernel(load(cp), load(hp), d, w, tf, a.tick_size).run()
        out = a.output_dir / f'BTCUSDT_{tf}_mm0_audit.csv'
        write(out, rows)
        rep.append({'timeframe': tf, 'rows': len(rows), 'audit_csv': str(out), 'audit_sha256': sha(out), 'source_sha256': sha(cp), 'context_sha256': sha(hp)})
    payload = {'audit_schema': 2, 'tick_size': a.tick_size, 'datasets': rep}
    txt = json.dumps(payload, indent=2, sort_keys=True)
    print(txt)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(txt + '\n', encoding='utf-8')
if __name__ == '__main__':
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Official Binance monthly kline -> validated Parquet pipeline")
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="download, verify, validate, consolidate, and report")
    run.add_argument("--config", type=Path, default=Path("configs/binance-spot-btcusdt.json"))
    run.add_argument("--data-root", type=Path, default=Path("data/market-data/Binance"))
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "run":
        result = run_config(args.config, args.data_root)
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

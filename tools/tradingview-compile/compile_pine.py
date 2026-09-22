#!/usr/bin/env python3
"""Compile Pine sources against TradingView's translate_light endpoint.

This performs a compiler check only. It does not create, update, publish, or save
TradingView scripts. The endpoint is internal and may change without notice.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = (
    "https://pine-facade.tradingview.com/pine-facade/translate_light"
    "?user_name=Guest&pine_id=00000000-0000-0000-0000-000000000000"
)


def pos(obj: dict | None) -> str:
    if not obj:
        return "?:?"
    line = obj.get("line")
    column = obj.get("column")
    return f"{line if line is not None else '?'}:{column if column is not None else '?'}"


def compile_source(path: Path, timeout: int) -> tuple[bool, list[dict], list[dict]]:
    source = path.read_text(encoding="utf-8")
    body = urllib.parse.urlencode({"source": source}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.tradingview.com/",
            "User-Agent": "PineTrading-Lab-CI/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"network/compiler request failed: {exc}") from exc

    errors: list[dict] = []
    warnings: list[dict] = []
    inner = payload.get("result") if isinstance(payload, dict) else None

    if isinstance(inner, dict):
        for item in inner.get("errors2") or []:
            errors.append(
                {
                    "line": (item.get("start") or {}).get("line"),
                    "column": (item.get("start") or {}).get("column"),
                    "end_line": (item.get("end") or {}).get("line"),
                    "end_column": (item.get("end") or {}).get("column"),
                    "message": item.get("message") or str(item),
                }
            )
        for item in inner.get("warnings2") or []:
            warnings.append(
                {
                    "line": (item.get("start") or {}).get("line"),
                    "column": (item.get("start") or {}).get("column"),
                    "message": item.get("message") or str(item),
                }
            )

    top_error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(top_error, str) and top_error:
        errors.append({"line": None, "column": None, "message": top_error})

    return len(errors) == 0, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()

    failed = False

    for path in args.paths:
        if not path.is_file():
            print(f"ERROR {path}: file not found", file=sys.stderr)
            failed = True
            continue

        print(f"::group::Compile {path}")
        try:
            compiled, errors, warnings = compile_source(path, args.timeout)
        except RuntimeError as exc:
            print(f"COMPILER REQUEST ERROR: {exc}", file=sys.stderr)
            print("::endgroup::")
            failed = True
            continue

        for error in errors:
            print(
                f"ERROR {pos(error)} {error.get('message', '')}",
                file=sys.stderr,
            )
        for warning in warnings:
            print(
                f"WARNING {pos(warning)} {warning.get('message', '')}",
                file=sys.stderr,
            )

        print(
            json.dumps(
                {
                    "file": str(path),
                    "compiled": compiled,
                    "errors": len(errors),
                    "warnings": len(warnings),
                },
                ensure_ascii=False,
            )
        )
        print("::endgroup::")

        if not compiled or (args.fail_on_warning and warnings):
            failed = True

    if failed:
        print("PINE COMPILE GATE: FAIL", file=sys.stderr)
        return 1

    print("PINE COMPILE GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

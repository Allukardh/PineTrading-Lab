from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from .core import DataValidationError, parse_checksum_text, sha256_file, verify_checksum


@dataclass(frozen=True)
class DownloadResult:
    filename: str
    zip_path: Path | None
    checksum_path: Path | None
    checksum_status: str
    checksum_expected: str | None
    zip_sha256: str | None
    size_bytes: int
    missing: bool = False


class BinanceArchiveClient:
    def __init__(self, base_url: str = "https://data.binance.vision", *, timeout: int = 30, retries: int = 4):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PineTrading-Lab-market-data/0.1.0"})

    @staticmethod
    def archive_relpath(market: str, symbol: str, timeframe: str, month: str) -> str:
        filename = f"{symbol}-{timeframe}-{month}.zip"
        return f"data/{market}/monthly/klines/{symbol}/{timeframe}/{filename}"

    def _get_text_optional(self, url: str) -> tuple[str | None, int]:
        for attempt in range(self.retries):
            try:
                r = self.session.get(url, timeout=self.timeout)
                if r.status_code == 404:
                    return None, 404
                r.raise_for_status()
                return r.text, r.status_code
            except requests.RequestException:
                if attempt + 1 == self.retries:
                    raise
                time.sleep(min(2 ** attempt, 8))
        raise AssertionError("unreachable")

    def _download_resumable(self, url: str, dest: Path) -> int:
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(dest.suffix + ".part")
        for attempt in range(self.retries):
            offset = part.stat().st_size if part.exists() else 0
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            try:
                with self.session.get(url, headers=headers, stream=True, timeout=self.timeout) as r:
                    if r.status_code == 404:
                        return 404
                    if offset and r.status_code == 206:
                        mode = "ab"
                    else:
                        mode = "wb"
                        offset = 0
                    r.raise_for_status()
                    with part.open(mode) as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                os.replace(part, dest)
                return 200
            except requests.RequestException:
                if attempt + 1 == self.retries:
                    raise
                time.sleep(min(2 ** attempt, 8))
        raise AssertionError("unreachable")

    def ensure_month(self, *, market: str, symbol: str, timeframe: str, month: str, raw_dir: Path) -> DownloadResult:
        rel = self.archive_relpath(market, symbol, timeframe, month)
        filename = Path(rel).name
        zip_url = f"{self.base_url}/{rel}"
        checksum_url = zip_url + ".CHECKSUM"
        zip_path = raw_dir / timeframe / filename
        checksum_path = raw_dir / timeframe / (filename + ".CHECKSUM")

        # Refresh tiny checksum sidecars each run so upstream archive replacements are detected.
        checksum_text, checksum_http = self._get_text_optional(checksum_url)
        expected = None
        if checksum_text is not None:
            expected, checksum_name = parse_checksum_text(checksum_text)
            if checksum_name and Path(checksum_name).name != filename:
                raise DataValidationError(f"{filename}: checksum sidecar names {checksum_name}")
            checksum_path.parent.mkdir(parents=True, exist_ok=True)
            checksum_path.write_text(checksum_text, encoding="utf-8")

        if zip_path.exists() and checksum_text is not None and verify_checksum(zip_path, checksum_text):
            return DownloadResult(filename, zip_path, checksum_path, "verified", expected, expected, zip_path.stat().st_size)

        # Existing file with absent checksum is retained unless corrupt processing later rejects it.
        if zip_path.exists() and checksum_text is None:
            digest = sha256_file(zip_path)
            return DownloadResult(filename, zip_path, None, "missing", None, digest, zip_path.stat().st_size)

        if zip_path.exists():
            zip_path.unlink()
        status = self._download_resumable(zip_url, zip_path)
        if status == 404:
            return DownloadResult(filename, None, checksum_path if checksum_http != 404 else None, "missing", expected, None, 0, True)

        digest = sha256_file(zip_path)
        if checksum_text is not None:
            if digest != expected:
                zip_path.unlink(missing_ok=True)
                raise DataValidationError(f"{filename}: SHA-256 mismatch after download")
            checksum_status = "verified"
        else:
            checksum_status = "missing"
        return DownloadResult(filename, zip_path, checksum_path if checksum_text is not None else None, checksum_status, expected, digest, zip_path.stat().st_size)

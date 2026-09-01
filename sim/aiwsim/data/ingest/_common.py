"""Shared helpers for the ingest scripts: root discovery, URL checks, downloads, argparse."""

from __future__ import annotations

import argparse
import io
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import polars as pl

from aiwsim.data.provenance import sha256_file, write_provenance  # noqa: F401  (re-exported)

USER_AGENT = "aiwsim-data-ingest/0.1 (+https://github.com/; research use)"
NOT_IN_INVENTORY = "file URL not recorded in docs/data-inventory.md; follows the publisher's naming convention"


def find_root(start: Path | None = None) -> Path:
    """Walk up from ``start`` (cwd) to the workspace root (has ``data/`` and ``pyproject.toml``)."""
    p = (start or Path.cwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / "pyproject.toml").exists() and (cand / "data").is_dir():
            return cand
    raise FileNotFoundError("workspace root not found; pass --root")


def _request(url: str, method: str = "GET", timeout: int = 60, headers: dict | None = None):
    h = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        h.update(headers)
    return urllib.request.urlopen(urllib.request.Request(url, method=method, headers=h), timeout=timeout)


def check_url(url: str, timeout: int = 30) -> tuple[bool, str]:
    """HEAD the URL (falling back to a ranged GET); returns (ok, 'status or error')."""
    try:
        with _request(url, "HEAD", timeout) as r:
            return 200 <= r.status < 400, str(r.status)
    except urllib.error.HTTPError as e:
        if e.code in (403, 405):  # some hosts reject HEAD; try a tiny GET
            try:
                with _request(url, "GET", timeout, {"Range": "bytes=0-0"}) as r:
                    return 200 <= r.status < 400, str(r.status)
            except urllib.error.HTTPError as e2:
                return False, f"HTTP {e2.code}"
            except Exception as e2:  # noqa: BLE001
                return False, f"{type(e2).__name__}: {e2}"
        return False, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def run_checks(urls: dict[str, str]) -> int:
    """Print a check line per URL; return 0 if all reachable else 1."""
    bad = 0
    for name, url in urls.items():
        ok, st = check_url(url)
        print(f"[{'ok' if ok else 'FAIL'}] {name:28s} {st:22s} {url}")
        bad += not ok
    return 1 if bad else 0


def download(url: str, dest: Path, *, force: bool = False, timeout: int = 300) -> Path:
    """Download ``url`` to ``dest`` (atomic via .part); skip if it exists unless ``force``."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"  cached  {dest}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    print(f"  GET     {url}")
    with _request(url, "GET", timeout) as r, open(part, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    part.replace(dest)
    print(f"  saved   {dest} ({dest.stat().st_size:,} bytes)")
    return dest


def zip_members(zip_path: Path, pattern: str) -> list[str]:
    rx = re.compile(pattern, re.IGNORECASE)
    with zipfile.ZipFile(zip_path) as z:
        return [n for n in z.namelist() if rx.search(n)]


def read_zip_member(zip_path: Path, name: str) -> bytes:
    with zipfile.ZipFile(zip_path) as z:
        return z.read(name)


def read_excel_bytes(data: bytes, sheet_name: str | None = None, **kw) -> pl.DataFrame:
    """Read an xlsx from bytes with polars (needs `fastexcel` or `openpyxl`); clear error otherwise."""
    try:
        return pl.read_excel(io.BytesIO(data), sheet_name=sheet_name, infer_schema_length=0, **kw)
    except (ImportError, ModuleNotFoundError) as e:  # pragma: no cover - depends on the host env
        raise SystemExit(
            "reading .xlsx needs an Excel engine: run `uv add --package aiwsim fastexcel` "
            "(or openpyxl) on the ingest machine"
        ) from e


def read_tsv_bytes(data: bytes, **kw) -> pl.DataFrame:
    return pl.read_csv(io.BytesIO(data), separator="\t", infer_schema_length=0, quote_char=None,
                       encoding="utf8-lossy", **kw)


def base_parser(description: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--root", type=Path, default=None, help="workspace root (default: auto-detect)")
    ap.add_argument("--check", action="store_true", help="only verify that the source URLs respond")
    ap.add_argument("--dry-run", action="store_true", help="download/parse but write nothing")
    ap.add_argument("--force", action="store_true", help="re-download cached raw files")
    return ap


def resolve_root(args) -> Path:
    return Path(args.root).resolve() if args.root else find_root()


def write_csv(df: pl.DataFrame, path: Path, dry_run: bool) -> Path:
    if dry_run:
        print(f"  [dry-run] would write {path} ({df.height} rows, {len(df.columns)} cols)")
        print(df.head(5))
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(path)
    print(f"  wrote   {path} ({df.height} rows)")
    return path


def fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2

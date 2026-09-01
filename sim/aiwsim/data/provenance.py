"""Provenance records for every processed table (contracts §4).

One JSON file per table at ``data/provenance/<table>.json``; ``<table>`` may contain a
sub-directory (``series/btos`` -> ``data/provenance/series/btos.json``).  ``status`` is one of
``real``, ``partial``, ``FIXTURE``; a qualifier in parentheses may follow, e.g.
``real (transcribed; secondary confirmation)``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATUS_VALUES = ("real", "partial", "FIXTURE")


@dataclass
class Provenance:
    table: str
    source: str
    source_url: str
    license: str
    pulled_at: str
    commit: str
    sha256: str
    transformations: list[str]
    status: str
    notes: str = ""
    built_at: str = ""
    output: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_status(self.status)


def validate_status(status: str) -> None:
    head = status.split(" ")[0].split("(")[0]
    if head not in STATUS_VALUES:
        raise ValueError(f"provenance status {status!r} must start with one of {STATUS_VALUES}")


def status_kind(status: str) -> str:
    """Return the bare status word (``real`` / ``partial`` / ``FIXTURE``) of a status string."""
    return status.split(" ")[0].split("(")[0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance_dir(root: Path) -> Path:
    return Path(root) / "data" / "provenance"


def provenance_path(root: Path, table: str) -> Path:
    return provenance_dir(root) / f"{table}.json"


def today() -> str:
    return dt.datetime.now(dt.UTC).date().isoformat()


def write_provenance(
    root: Path,
    table: str,
    output_path: Path,
    *,
    source: str,
    source_url: str,
    license: str,
    transformations: list[str],
    status: str,
    notes: str = "",
    commit: str = "",
    pulled_at: str | None = None,
    extra: dict | None = None,
) -> Path:
    """Write ``data/provenance/<table>.json`` describing ``output_path``; returns the path."""
    output_path = Path(output_path)
    rec = Provenance(
        table=table,
        source=source,
        source_url=source_url,
        license=license,
        pulled_at=pulled_at or today(),
        commit=commit,
        sha256=sha256_file(output_path),
        transformations=list(transformations),
        status=status,
        notes=notes,
        built_at=dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        output=str(output_path.relative_to(Path(root))) if output_path.is_absolute() else str(output_path),
        extra=extra or {},
    )
    path = provenance_path(root, table)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(rec), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def read_provenance(root: Path, table: str) -> Provenance:
    data = json.loads(provenance_path(root, table).read_text(encoding="utf-8"))
    return Provenance(**data)


def list_provenance(root: Path) -> dict[str, Provenance]:
    """All provenance records keyed by table name (``series/btos`` style for sub-directories)."""
    base = provenance_dir(root)
    out: dict[str, Provenance] = {}
    if not base.exists():
        return out
    for path in sorted(base.rglob("*.json")):
        table = str(path.relative_to(base).with_suffix("")).replace("\\", "/")
        data = json.loads(path.read_text(encoding="utf-8"))
        out[table] = Provenance(**data)
    return out

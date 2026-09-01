"""Anthropic Economic Index ingest -> task-level usage shares by release (theta anchoring, spec
§2.2 / P.24; sigma by task family, P.16).

Inventory row 6: https://huggingface.co/datasets/Anthropic/EconomicIndex (data CC BY; folders
through ``release_2026_03_24``).  Files are listed through the Hugging Face tree API and fetched
via ``resolve/main/<path>``; ``huggingface_hub`` is used instead when importable.  The per-release
file layout is NOT recorded in the inventory (the taxonomy changed V1 -> V3), so the parser scans
each release's CSVs for a task column (``onet_task`` / ``task_name``) and a share/percent column and
writes whatever it finds, one row per (release, task), to ``series/aei_task_usage.csv``.  Inspect
the ``columns_used`` field of the provenance record after the first run.
"""

from __future__ import annotations

import json
import sys

import polars as pl

from aiwsim.data.ingest._common import (
    _request,
    base_parser,
    download,
    resolve_root,
    run_checks,
    write_csv,
    write_provenance,
)
from aiwsim.data.sources import SOURCES

REPO = "Anthropic/EconomicIndex"
LANDING = f"https://huggingface.co/datasets/{REPO}"
TREE_API = f"https://huggingface.co/api/datasets/{REPO}/tree/main"
RESOLVE = f"https://huggingface.co/datasets/{REPO}/resolve/main/"
KNOWN_RELEASES = ["release_2026_03_24"]  # from the inventory; others discovered from the tree API


def list_tree(path: str = "") -> list[dict]:
    url = TREE_API + (f"/{path}" if path else "")
    with _request(url) as r:
        return json.loads(r.read().decode("utf-8"))


def walk_release(release: str) -> list[str]:
    """All file paths under a release folder (recursive)."""
    out, stack = [], [release]
    while stack:
        d = stack.pop()
        for item in list_tree(d):
            if item.get("type") == "directory":
                stack.append(item["path"])
            else:
                out.append(item["path"])
    return out


def find_task_share(df: pl.DataFrame) -> tuple[str, str, str | None] | None:
    lc = {c.lower(): c for c in df.columns}
    task = next((lc[c] for c in lc if "onet_task" in c or c in ("task_name", "task", "onet task")), None)
    share = next((lc[c] for c in lc if any(k in c for k in ("pct", "percent", "share", "proportion"))), None)
    auto = next((lc[c] for c in lc if "automation" in c or "directive" in c), None)
    if task and share:
        return task, share, auto
    return None


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    ap.add_argument("--releases", nargs="*", help="release folders to ingest (default: all release_* folders)")
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, "tree_api": TREE_API})
    root = resolve_root(args)
    src = SOURCES["aei"]
    raw_dir = root / "data" / "raw" / "aei"
    releases = args.releases or [i["path"] for i in list_tree() if i.get("type") == "directory" and i["path"].startswith("release_")]
    releases = sorted(set(releases) | (set(KNOWN_RELEASES) if not args.releases else set()))
    print(f"  releases: {releases}")
    frames, used = [], {}
    for rel in releases:
        for path in walk_release(rel):
            if not path.lower().endswith(".csv"):
                continue
            local = download(RESOLVE + path, raw_dir / path, force=args.force)
            try:
                df = pl.read_csv(local, infer_schema_length=0, encoding="utf8-lossy")
            except Exception as e:  # noqa: BLE001
                print(f"  skip {path}: {e}")
                continue
            hit = find_task_share(df)
            if not hit:
                continue
            task, share, auto = hit
            used[path] = {"task": task, "share": share, "automation": auto}
            sel = df.select(pl.lit(rel).alias("release"), pl.lit(path).alias("file"), pl.col(task).alias("onet_task"),
                            pl.col(share).cast(pl.Float64, strict=False).alias("usage_share"),
                            (pl.col(auto).cast(pl.Float64, strict=False) if auto else pl.lit(None, dtype=pl.Float64)).alias("automation_share"))
            frames.append(sel)
    if not frames:
        print("  no task-level usage tables recognized; inspect data/raw/aei and adjust find_task_share()")
        return 1
    out = pl.concat(frames).with_columns(pl.lit("real:AEI").alias("source_tag"))
    p = write_csv(out, root / "data" / "processed" / "series" / "aei_task_usage.csv", args.dry_run)
    if not args.dry_run:
        write_provenance(root, "series/aei_task_usage", p, source=f"{src.name} ({', '.join(releases)})", source_url=LANDING,
                         license=src.license, status="real",
                         transformations=["task-level usage share columns detected heuristically per file (see extra.columns_used)"],
                         notes="Taxonomy V1->V3 across releases: shares are not strictly comparable between releases.",
                         extra={"ingested": True, "columns_used": used, "releases": releases})
    return 0


if __name__ == "__main__":
    sys.exit(main())

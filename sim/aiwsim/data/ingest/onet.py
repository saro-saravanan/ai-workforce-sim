"""O*NET 31.0 text database ingest -> task weights (importance x relevance x frequency) and the
Work Context presence items (spec §2.2).

Inventory row 1 records https://www.onetcenter.org/database.html .  The zip name below follows the
O*NET Center convention ``dl_files/database/db_<major>_<minor>_text.zip``; verify with ``--check``.

Outputs (both real, tagged D):
* ``data/processed/onet_task_weights.csv``: task_id, onet_soc_code, importance, relevance,
  frequency_score, weight (normalized within onet_soc_code)
* ``data/processed/onet_presence.csv``: onet_soc_code, the four Work Context items rescaled to
  [0, 1], and ``presence`` = their mean

``build.py`` does not yet consume these files; wiring them into ``tasks.csv`` (replacing the
Core/Supplemental weights and the keyword presence rule) is the next step once real data exist.
"""

from __future__ import annotations

import sys

import polars as pl

from aiwsim.data.ingest._common import (
    NOT_IN_INVENTORY,
    base_parser,
    download,
    read_tsv_bytes,
    read_zip_member,
    resolve_root,
    run_checks,
    write_csv,
    write_provenance,
    zip_members,
)
from aiwsim.data.sources import SOURCES

VERSION = "31.0"
LANDING = "https://www.onetcenter.org/database.html"
URLS = {"db_text_zip": "https://www.onetcenter.org/dl_files/database/db_31_0_text.zip"}  # NOT IN INVENTORY

PRESENCE_ITEMS = [  # Work Context element names (spec §2.2); matched on name, not element id
    "Face-to-Face Discussions",
    "Physical Proximity",
    "Deal With External Customers",
    "Performing for or Working Directly with the Public",
]


def _member(zip_path, name_regex: str) -> bytes:
    hits = zip_members(zip_path, name_regex)
    if not hits:
        raise SystemExit(f"member matching {name_regex!r} not found in {zip_path}")
    return read_zip_member(zip_path, hits[0])


def task_weights(ratings: pl.DataFrame) -> pl.DataFrame:
    r = ratings.rename({c: c.strip() for c in ratings.columns})
    r = r.select(pl.col("O*NET-SOC Code").alias("onet_soc_code"), pl.col("Task ID").alias("task_id"),
                 pl.col("Scale ID").alias("scale"), pl.col("Category").alias("category"),
                 pl.col("Data Value").cast(pl.Float64, strict=False).alias("value"))
    im = r.filter(pl.col("scale") == "IM").select("onet_soc_code", "task_id", pl.col("value").alias("importance"))
    rt = r.filter(pl.col("scale") == "RT").select("onet_soc_code", "task_id", pl.col("value").alias("relevance"))
    # FT: percent of respondents per frequency category 1..7 -> expected category, rescaled to [0, 1]
    ft = (r.filter(pl.col("scale") == "FT")
          .with_columns(pl.col("category").cast(pl.Float64, strict=False))
          .group_by(["onet_soc_code", "task_id"])
          .agg(((pl.col("category") * pl.col("value")).sum() / pl.col("value").sum()).alias("f_cat"))
          .with_columns(((pl.col("f_cat") - 1) / 6).clip(0, 1).alias("frequency_score")).drop("f_cat"))
    w = im.join(rt, on=["onet_soc_code", "task_id"], how="left").join(ft, on=["onet_soc_code", "task_id"], how="left")
    w = w.with_columns(
        (pl.col("importance").fill_null(3.0) / 5.0) * (pl.col("relevance").fill_null(100.0) / 100.0)
        * pl.col("frequency_score").fill_null(0.5)).alias("w_raw")
    return w.with_columns((pl.col("w_raw") / pl.col("w_raw").sum().over("onet_soc_code")).alias("weight")).drop("w_raw")


def presence_items(wc: pl.DataFrame) -> pl.DataFrame:
    w = wc.rename({c: c.strip() for c in wc.columns})
    w = w.filter(pl.col("Element Name").is_in(PRESENCE_ITEMS) & (pl.col("Scale ID") == "CX"))
    w = w.select(pl.col("O*NET-SOC Code").alias("onet_soc_code"), pl.col("Element Name").alias("item"),
                 ((pl.col("Data Value").cast(pl.Float64, strict=False) - 1) / 4).clip(0, 1).alias("v"))
    wide = w.pivot(on="item", index="onet_soc_code", values="v")
    cols = [c for c in PRESENCE_ITEMS if c in wide.columns]
    return wide.with_columns(pl.mean_horizontal([pl.col(c) for c in cols]).alias("presence")).sort("onet_soc_code")


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, **URLS})
    root = resolve_root(args)
    src = SOURCES["onet"]
    z = download(URLS["db_text_zip"], root / "data" / "raw" / "onet" / f"db_{VERSION.replace('.', '_')}_text.zip", force=args.force)
    ratings = read_tsv_bytes(_member(z, r"Task Ratings\.txt$"))
    wc = read_tsv_bytes(_member(z, r"Work Context\.txt$"))
    tw = task_weights(ratings)
    pr = presence_items(wc)
    print(f"  task weights: {tw.height} rows, {tw['onet_soc_code'].n_unique()} occupations; presence: {pr.height} occupations")
    p1 = write_csv(tw, root / "data" / "processed" / "onet_task_weights.csv", args.dry_run)
    p2 = write_csv(pr, root / "data" / "processed" / "onet_presence.csv", args.dry_run)
    if not args.dry_run:
        write_provenance(root, "onet_task_weights", p1, source=f"O*NET {VERSION} Task Ratings.txt", source_url=LANDING,
                         license=src.license, status="real",
                         transformations=["weight ∝ (IM/5) x (RT/100) x frequency_score, normalized within O*NET-SOC",
                                          "frequency_score = (expected FT category - 1) / 6"],
                         notes=NOT_IN_INVENTORY, extra={"ingested": True, "version": VERSION})
        write_provenance(root, "onet_presence", p2, source=f"O*NET {VERSION} Work Context.txt", source_url=LANDING,
                         license=src.license, status="real",
                         transformations=[f"items {PRESENCE_ITEMS} (CX scale 1-5) rescaled (x-1)/4; presence = mean"],
                         notes=NOT_IN_INVENTORY, extra={"ingested": True, "version": VERSION})
    return 0


if __name__ == "__main__":
    sys.exit(main())

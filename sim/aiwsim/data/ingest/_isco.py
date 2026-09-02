"""ISCO-08 2-digit -> SOC 2018 6-digit distribution used by ``ilostat.py`` and ``eurostat_lfs.py``.

Inventory row 14: there is **no official ISCO-08 x SOC 2018 crosswalk**; the chain used here is
ISCO-08 -> SOC 2010 (BLS ``ISCO_SOC_Crosswalk.xls``, public domain, inventory row 14) ->
SOC 2018 (BLS ``soc_2010_to_2018_crosswalk.xlsx``, public domain; file URL follows the BLS SOC
site's naming convention and is not in the inventory).  An ISCO 2-digit group maps to the set of
SOC 2018 codes reached through the chain; a country's employment in the group is distributed over
those codes in proportion to the U.S. employment mix within the group (``occupations.csv``), so
the within-group mix is a U.S. proxy while the between-group mix is the country's own.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from aiwsim.data.ingest._common import download, read_excel_bytes

ISCO_SOC_2010_XLS = "https://www.bls.gov/soc/ISCO_SOC_Crosswalk.xls"  # inventory row 14
SOC_2010_2018_XLSX = "https://www.bls.gov/soc/2018/soc_2010_to_2018_crosswalk.xlsx"  # NOT IN INVENTORY
CROSSWALK_SOURCE_TAG = "crosswalk:BLS_ISCO08->SOC2010->SOC2018;within-group mix = U.S. proxy"


def _find_col(df: pl.DataFrame, *needles: str) -> str:
    for c in df.columns:
        lc = c.lower()
        if all(n in lc for n in needles):
            return c
    raise SystemExit(f"column with {needles} not found in {df.columns}")


def _header_frame(data: bytes, must_contain: tuple[str, ...]) -> pl.DataFrame:
    """Read an Excel sheet whose header row is not the first row (BLS puts a title above)."""
    raw = read_excel_bytes(data, has_header=False)
    for i, row in enumerate(raw.head(12).iter_rows()):
        cells = [str(c or "").lower() for c in row]
        if all(any(n in c for c in cells) for n in must_contain):
            body = raw.slice(i + 1)
            body.columns = [str(c or f"col{j}").strip() for j, c in enumerate(raw.row(i))]
            return body
    raise SystemExit(f"header row containing {must_contain} not found")


def load_isco08_to_soc2018(root: Path, force: bool = False) -> pl.DataFrame:
    """Frame (isco08_4, isco08_2, soc2010, soc2018) with one row per chain link."""
    raw_dir = root / "data" / "raw" / "crosswalks"
    a = download(ISCO_SOC_2010_XLS, raw_dir / "ISCO_SOC_Crosswalk.xls", force=force)
    b = download(SOC_2010_2018_XLSX, raw_dir / "soc_2010_to_2018_crosswalk.xlsx", force=force)
    x1 = _header_frame(a.read_bytes(), ("isco", "soc"))
    isco_col, soc10_col = _find_col(x1, "isco", "code"), _find_col(x1, "soc", "code")
    x1 = x1.select(pl.col(isco_col).cast(pl.Utf8).str.strip_chars().alias("isco08_4"),
                   pl.col(soc10_col).cast(pl.Utf8).str.strip_chars().alias("soc2010"))
    x1 = x1.filter(pl.col("isco08_4").str.contains(r"^\d{4}$") & pl.col("soc2010").str.contains(r"^\d{2}-\d{4}$"))
    x2 = _header_frame(b.read_bytes(), ("2010", "2018"))
    c10, c18 = _find_col(x2, "2010", "code"), _find_col(x2, "2018", "code")
    x2 = x2.select(pl.col(c10).cast(pl.Utf8).str.strip_chars().alias("soc2010"),
                   pl.col(c18).cast(pl.Utf8).str.strip_chars().alias("soc2018"))
    x2 = x2.filter(pl.col("soc2018").str.contains(r"^\d{2}-\d{4}$"))
    chain = x1.join(x2, on="soc2010", how="inner").with_columns(
        pl.col("isco08_4").str.slice(0, 2).alias("isco08_2")).unique()
    if chain.height == 0:
        raise SystemExit("crosswalk chain is empty; inspect the two BLS workbooks")
    return chain


def distribute_isco2_to_occ(isco2: pl.DataFrame, chain: pl.DataFrame, occ: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """``isco2``: (region_id, isco08_2, emp).  Returns (region_id, occ_code, emp) over every
    occupation in ``occ`` (occ_code, emp_national) and notes on unmapped mass.

    SOC 2018 codes are matched to OEWS codes at the detailed level, else the broad code (xx-xxx0)
    as in the Phase 1 task mapping.  Employment in ISCO groups with no SOC target is spread over
    all occupations by the U.S. mix and reported in the notes."""
    oews_codes = set(occ["occ_code"])
    link = chain.select("isco08_2", "soc2018").unique().with_columns(
        pl.when(pl.col("soc2018").is_in(list(oews_codes))).then(pl.col("soc2018"))
        .otherwise(pl.col("soc2018").str.slice(0, 6) + "0").alias("occ_code"))
    link = link.filter(pl.col("occ_code").is_in(list(oews_codes))).select("isco08_2", "occ_code").unique()
    us = occ.select("occ_code", pl.col("emp_national").cast(pl.Float64))
    link = link.join(us, on="occ_code", how="left").with_columns(
        (pl.col("emp_national") / pl.col("emp_national").sum().over("isco08_2")).alias("w"))
    out = isco2.join(link, on="isco08_2", how="left")
    unmapped = out.filter(pl.col("occ_code").is_null())
    notes = {"unmapped_isco2_groups": sorted(set(unmapped["isco08_2"])),
             "unmapped_emp_by_region": {r: float(v) for r, v in
                                        unmapped.group_by("region_id").agg(pl.col("emp").sum()).iter_rows()}}
    mapped = out.filter(pl.col("occ_code").is_not_null()).with_columns((pl.col("emp") * pl.col("w")).alias("e"))
    mapped = mapped.group_by("region_id", "occ_code").agg(pl.col("e").sum().alias("emp"))
    if unmapped.height:
        spread = unmapped.group_by("region_id").agg(pl.col("emp").sum().alias("u")).join(
            us.with_columns((pl.col("emp_national") / pl.col("emp_national").sum()).alias("s")), how="cross")
        spread = spread.select("region_id", "occ_code", (pl.col("u") * pl.col("s")).alias("emp"))
        mapped = pl.concat([mapped, spread]).group_by("region_id", "occ_code").agg(pl.col("emp").sum())
    # every occupation gets a row (zero where the chain reaches nothing)
    grid = mapped.select("region_id").unique().join(us.select("occ_code"), how="cross")
    return grid.join(mapped, on=["region_id", "occ_code"], how="left").fill_null(0.0).sort(["region_id", "occ_code"]), notes


def apply_to_occ_region(root: Path, new: pl.DataFrame, wage_level: dict[str, float], occ: pl.DataFrame,
                        tag: str) -> pl.DataFrame:
    """Replace the FIXTURE rows of ``regions/occ_region.csv`` for the regions in ``new``; keep the
    others.  ``emp`` rounded to integer heads; wages stay U.S. wage x wage_level_rel_us."""
    path = root / "data" / "processed" / "regions" / "occ_region.csv"
    cur = pl.read_csv(path, infer_schema_length=0) if path.exists() else pl.DataFrame(
        schema={"occ_code": pl.Utf8, "region_id": pl.Utf8, "emp": pl.Utf8, "wage_mean_annual_usd": pl.Utf8,
                "source_tag": pl.Utf8})
    keep = cur.filter(~pl.col("region_id").is_in(list(set(new["region_id"]))))
    wage = occ.select("occ_code", pl.col("wage_mean_annual").cast(pl.Float64))
    rows = new.join(wage, on="occ_code", how="left").with_columns(
        pl.col("emp").round(0).cast(pl.Int64),
        (pl.col("wage_mean_annual") * pl.col("region_id").replace_strict(wage_level, default=1.0)).round(2)
        .alias("wage_mean_annual_usd"),
        pl.lit(tag).alias("source_tag"),
    ).select("occ_code", "region_id", "emp", "wage_mean_annual_usd", "source_tag")
    return pl.concat([keep.select(rows.columns).cast(rows.schema), rows]).sort(["region_id", "occ_code"])

"""ILOSTAT employment by ISCO-08 2-digit occupation and country -> ``regions/occ_region.csv``.

Inventory row 15 records the landing page https://ilostat.ilo.org/ only.  The bulk file below is
the ILOSTAT data API (``rplumber.ilo.org``) export of indicator ``EMP_TEMP_SEX_OC2_NB_A``
(employment by sex and occupation, ISCO-08 2-digit, annual, thousands); the URL follows the API's
naming convention and is NOT IN INVENTORY; verify with ``--check``.

Countries are mapped to regions through ``regions/region_members.csv`` (Natural Earth ISO3 =
ILOSTAT ``ref_area``), the latest year per country is kept, and the ISCO 2-digit employment is
distributed over SOC 2018 occupations through the crosswalk chain in ``_isco.py`` (source tag
records it).  EU-27 members are left to ``eurostat_lfs.py``; the U.S. keeps ``occupations.csv``.
Regions with fewer than ``--min-coverage`` of their population covered by ILOSTAT keep the
FIXTURE rows (China's two-digit coverage is limited, inventory row 15).
"""

from __future__ import annotations

import sys

import polars as pl

from aiwsim.data.ingest._common import (
    NOT_IN_INVENTORY,
    base_parser,
    download,
    resolve_root,
    run_checks,
    write_csv,
    write_provenance,
)
from aiwsim.data.ingest._isco import (
    CROSSWALK_SOURCE_TAG,
    ISCO_SOC_2010_XLS,
    SOC_2010_2018_XLSX,
    apply_to_occ_region,
    distribute_isco2_to_occ,
    load_isco08_to_soc2018,
)
from aiwsim.data.sources import SOURCES

LANDING = "https://ilostat.ilo.org/"
INDICATOR = "EMP_TEMP_SEX_OC2_NB_A"
URLS = {
    "ilostat_csv": f"https://rplumber.ilo.org/data/indicator/?id={INDICATOR}&format=.csv",  # NOT IN INVENTORY
    "isco_soc_2010": ISCO_SOC_2010_XLS,
    "soc_2010_2018": SOC_2010_2018_XLSX,
}
SKIP_REGIONS = {"US", "EU"}  # U.S.: occupations.csv; EU: eurostat_lfs.py


def parse_ilostat(path, members: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """(region_id, isco08_2, emp) in heads from the latest year per country, plus coverage notes."""
    df = pl.read_csv(path, infer_schema_length=0)
    cols = {c.lower(): c for c in df.columns}
    need = ["ref_area", "sex", "classif1", "time", "obs_value"]
    if any(n not in cols for n in need):
        raise SystemExit(f"unexpected ILOSTAT columns {df.columns}; expected {need}")
    df = df.select(pl.col(cols["ref_area"]).alias("iso3"), pl.col(cols["sex"]).alias("sex"),
                   pl.col(cols["classif1"]).alias("occ"), pl.col(cols["time"]).cast(pl.Int64, strict=False).alias("year"),
                   pl.col(cols["obs_value"]).cast(pl.Float64, strict=False).alias("v"))
    df = df.filter((pl.col("sex") == "SEX_T") & pl.col("occ").str.contains(r"^OCU_ISCO08_\d{2}$") & pl.col("v").is_not_null())
    df = df.with_columns(pl.col("occ").str.slice(-2).alias("isco08_2"))
    latest = df.group_by("iso3").agg(pl.col("year").max().alias("year"))
    df = df.join(latest, on=["iso3", "year"], how="inner")
    m = members.select("iso3", "region_id", pl.col("population").cast(pl.Float64))
    df = df.join(m, on="iso3", how="inner").filter((pl.col("region_id") != "") & ~pl.col("region_id").is_in(list(SKIP_REGIONS)))
    covered = df.select("iso3", "region_id", "population", "year").unique()
    pop = m.filter(pl.col("region_id") != "").group_by("region_id").agg(pl.col("population").sum().alias("pop"))
    cov = covered.group_by("region_id").agg(pl.col("population").sum().alias("cov"), pl.col("year").min().alias("year_min"),
                                            pl.col("year").max().alias("year_max")).join(pop, on="region_id")
    cov = cov.with_columns((pl.col("cov") / pl.col("pop")).alias("coverage"))
    out = df.group_by("region_id", "isco08_2").agg((pl.col("v") * 1000.0).sum().alias("emp"))
    return out, {r["region_id"]: r for r in cov.to_dicts()}


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    ap.add_argument("--min-coverage", type=float, default=0.6, help="min population share covered per region")
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, **URLS})
    root = resolve_root(args)
    src = SOURCES["ilostat"]
    proc = root / "data" / "processed"
    members = pl.read_csv(proc / "regions" / "region_members.csv", infer_schema_length=0)
    regions = pl.read_csv(proc / "regions" / "regions.csv", infer_schema_length=0)
    occ = pl.read_csv(proc / "occupations.csv", infer_schema_length=0)
    raw = download(URLS["ilostat_csv"], root / "data" / "raw" / "ilostat" / f"{INDICATOR}.csv", force=args.force)
    isco2, coverage = parse_ilostat(raw, members)
    ok = [r for r, c in coverage.items() if c["coverage"] >= args.min_coverage]
    print("  coverage:", {r: round(c["coverage"], 2) for r, c in coverage.items()}, "-> using", ok)
    if not ok:
        print("  no region reaches the coverage threshold; nothing written")
        return 0
    isco2 = isco2.filter(pl.col("region_id").is_in(ok))
    chain = load_isco08_to_soc2018(root, force=args.force)
    dist, notes = distribute_isco2_to_occ(isco2, chain, occ)
    # scale each region to employment_total so the model's totals do not jump with ILOSTAT coverage
    tot = regions.select("region_id", pl.col("employment_total").cast(pl.Float64))
    dist = dist.join(dist.group_by("region_id").agg(pl.col("emp").sum().alias("s")), on="region_id").join(tot, on="region_id")
    dist = dist.select("region_id", "occ_code", (pl.col("emp") * pl.col("employment_total") / pl.col("s")).alias("emp"))
    wage_level = {r["region_id"]: float(r["wage_level_rel_us"]) for r in regions.to_dicts()}
    tag = f"real:ILOSTAT_{INDICATOR};{CROSSWALK_SOURCE_TAG}"
    table = apply_to_occ_region(root, dist, wage_level, occ, tag)
    p = write_csv(table, proc / "regions" / "occ_region.csv", args.dry_run)
    if not args.dry_run:
        write_provenance(
            root, "regions/occ_region", p, source=f"ILOSTAT {INDICATOR} (annual, ISCO-08 2-digit) for regions {ok}; "
            "other regions keep their previous rows", source_url=LANDING, license=src.license,
            status="partial (ILOSTAT via ISCO->SOC crosswalk; remaining regions FIXTURE)",
            transformations=["latest year per country, SEX_T, ISCO-08 2-digit; thousands -> heads",
                             "countries -> regions via regions/region_members.csv; U.S. and EU-27 skipped",
                             ("ISCO-08 2-digit -> SOC 2018 through BLS ISCO->SOC2010 and SOC2010->SOC2018 crosswalks; "
                              "within-group split by the U.S. employment mix (occupations.csv)"),
                             "scaled to regions.csv employment_total; wages = U.S. wage x wage_level_rel_us"],
            notes=f"{NOT_IN_INVENTORY}. Coverage by region: {coverage}. Unmapped ISCO groups: {notes}.",
            extra={"ingested": True, "coverage": coverage, "crosswalk_notes": notes, "regions_replaced": ok})
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Eurostat LFS ``lfsa_egai2d`` (employment by sex, age and ISCO-08 2-digit) -> EU rows of
``regions/occ_region.csv``.

Inventory row 14 records the LFS database page and the table code.  The SDMX-CSV export URL
below follows the Eurostat dissemination API convention and is NOT IN INVENTORY; verify with
``--check``.  Totals (sex T, age 15-74) for the EU-27 members are summed per ISCO 2-digit group
in the latest year and distributed over SOC 2018 occupations through the crosswalk chain in
``_isco.py``.  Values are thousands of persons.
"""

from __future__ import annotations

import gzip
import io
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
from aiwsim.data.regions import EU27
from aiwsim.data.sources import SOURCES

TABLE = "lfsa_egai2d"
LANDING = "https://ec.europa.eu/eurostat/web/lfs/database"
URLS = {
    "sdmx_csv": ("https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
                 f"{TABLE}?format=SDMX-CSV&compressed=true"),  # NOT IN INVENTORY
    "isco_soc_2010": ISCO_SOC_2010_XLS,
    "soc_2010_2018": SOC_2010_2018_XLSX,
}
# Eurostat geo codes are ISO alpha-2 except Greece (EL); map to Natural Earth alpha-3.
GEO_TO_ISO3 = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "HR": "HRV", "CY": "CYP", "CZ": "CZE", "DK": "DNK", "EE": "EST",
    "FI": "FIN", "FR": "FRA", "DE": "DEU", "EL": "GRC", "HU": "HUN", "IE": "IRL", "IT": "ITA", "LV": "LVA",
    "LT": "LTU", "LU": "LUX", "MT": "MLT", "NL": "NLD", "PL": "POL", "PT": "PRT", "RO": "ROU", "SK": "SVK",
    "SI": "SVN", "ES": "ESP", "SE": "SWE",
}
assert set(GEO_TO_ISO3.values()) == set(EU27)


def parse_sdmx_csv(path) -> tuple[pl.DataFrame, dict]:
    data = path.read_bytes()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    df = pl.read_csv(io.BytesIO(data), infer_schema_length=0)
    cols = {c.lower(): c for c in df.columns}
    need = ["geo", "sex", "age", "isco08", "time_period", "obs_value"]
    if any(n not in cols for n in need):
        raise SystemExit(f"unexpected {TABLE} columns {df.columns}; expected {need}")
    df = df.select(pl.col(cols["geo"]).alias("geo"), pl.col(cols["sex"]).alias("sex"), pl.col(cols["age"]).alias("age"),
                   pl.col(cols["isco08"]).alias("isco"), pl.col(cols["time_period"]).cast(pl.Int64, strict=False).alias("year"),
                   pl.col(cols["obs_value"]).cast(pl.Float64, strict=False).alias("v"))
    df = df.filter((pl.col("sex") == "T") & (pl.col("age") == "Y15-74") & pl.col("isco").str.contains(r"^OC\d{2}$")
                   & pl.col("geo").is_in(list(GEO_TO_ISO3)) & pl.col("v").is_not_null())
    year = int(df["year"].max())
    df = df.filter(pl.col("year") == year)
    have = sorted(set(df["geo"]))
    out = df.with_columns(pl.col("isco").str.slice(2, 2).alias("isco08_2")).group_by("isco08_2").agg(
        (pl.col("v") * 1000.0).sum().alias("emp")).with_columns(pl.lit("EU").alias("region_id"))
    return out.select("region_id", "isco08_2", "emp"), {"year": year, "members_present": have,
                                                          "members_missing": sorted(set(GEO_TO_ISO3) - set(have))}


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, **URLS})
    root = resolve_root(args)
    src = SOURCES["eurostat_lfs"]
    proc = root / "data" / "processed"
    regions = pl.read_csv(proc / "regions" / "regions.csv", infer_schema_length=0)
    occ = pl.read_csv(proc / "occupations.csv", infer_schema_length=0)
    raw = download(URLS["sdmx_csv"], root / "data" / "raw" / "eurostat" / f"{TABLE}.csv.gz", force=args.force)
    isco2, info = parse_sdmx_csv(raw)
    print(f"  {TABLE}: year {info['year']}, {len(info['members_present'])} members, "
          f"{isco2.height} ISCO groups, {isco2['emp'].sum():,.0f} employed")
    chain = load_isco08_to_soc2018(root, force=args.force)
    dist, notes = distribute_isco2_to_occ(isco2, chain, occ)
    tot = float(regions.filter(pl.col("region_id") == "EU")["employment_total"][0])
    dist = dist.with_columns((pl.col("emp") * tot / pl.col("emp").sum()).alias("emp"))
    wage_level = {r["region_id"]: float(r["wage_level_rel_us"]) for r in regions.to_dicts()}
    tag = f"real:Eurostat_{TABLE}_{info['year']};{CROSSWALK_SOURCE_TAG}"
    table = apply_to_occ_region(root, dist, wage_level, occ, tag)
    p = write_csv(table, proc / "regions" / "occ_region.csv", args.dry_run)
    if not args.dry_run:
        write_provenance(
            root, "regions/occ_region", p, source=f"Eurostat LFS {TABLE} (EU-27 sum, sex T, age 15-74, "
            f"{info['year']}) for EU; other regions keep their previous rows", source_url=LANDING,
            license=src.license, status="partial (EU from Eurostat LFS via ISCO->SOC crosswalk)",
            transformations=["EU-27 members summed per ISCO-08 2-digit group, latest year; thousands -> heads",
                             ("ISCO-08 2-digit -> SOC 2018 through BLS ISCO->SOC2010 and SOC2010->SOC2018 crosswalks; "
                              "within-group split by the U.S. employment mix (occupations.csv)"),
                             "scaled to regions.csv employment_total; wages = U.S. wage x wage_level_rel_us"],
            notes=f"{NOT_IN_INVENTORY}. {info}. Crosswalk notes: {notes}.",
            extra={"ingested": True, "lfs": info, "crosswalk_notes": notes})
    return 0


if __name__ == "__main__":
    sys.exit(main())

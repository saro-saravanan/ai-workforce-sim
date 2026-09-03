"""OEWS May 2025 ingest: occupation x industry (-> ``occ_sector.csv``) and occupation x state
(-> ``occ_state.csv``, ``states.csv``); refreshes employment and wages in ``occupations.csv``.

Inventory row 7 records only the landing page https://www.bls.gov/oes/ .  The zip names below follow
the BLS "special requests" convention (oesm<yy>nat / oesm<yy>st / oesm<yy>in4); run ``--check``
first and fix the constants if BLS has renamed them.  BLS blocks requests without a User-Agent.

Sector mapping: the national industry file's ``I_GROUP == "sector"`` rows carry NAICS sector codes
(``11`` ... ``31-33`` ... ``92``); OEWS government aggregates (NAICS ``999xxx``) map to ``92``.
Shares are renormalized per occupation because suppressed cells make the sector sum < TOT_EMP.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

from aiwsim.data.fixtures import naics_to_sector
from aiwsim.data.ingest._common import (
    NOT_IN_INVENTORY,
    base_parser,
    download,
    read_excel_bytes,
    read_zip_member,
    resolve_root,
    run_checks,
    write_csv,
    write_provenance,
    zip_members,
)
from aiwsim.data.sources import SOURCES

VINTAGE = "May 2025"
LANDING = "https://www.bls.gov/oes/"
BASE = "https://www.bls.gov/oes/special-requests/"
URLS = {
    "national_cross_industry": BASE + "oesm25nat.zip",  # NOT IN INVENTORY (naming convention)
    "national_by_industry": BASE + "oesm25in4.zip",     # NOT IN INVENTORY (naming convention)
    "state": BASE + "oesm25st.zip",                     # NOT IN INVENTORY (naming convention)
}
MISSING = {"#", "*", "**", ""}


def _num(col: str) -> pl.Expr:
    return (pl.when(pl.col(col).is_in(list(MISSING)) | pl.col(col).is_null()).then(None)
            .otherwise(pl.col(col).cast(pl.Utf8).str.replace_all(",", "")).cast(pl.Float64, strict=False))


def _load_zip_table(zip_path: Path) -> pl.DataFrame:
    members = zip_members(zip_path, r"\.(xlsx|csv)$")
    members = [m for m in members if "field_desc" not in m.lower() and "readme" not in m.lower()]
    if not members:
        raise SystemExit(f"no data member in {zip_path}: {zip_members(zip_path, '.')}")
    frames = []
    for m in members:
        raw = read_zip_member(zip_path, m)
        df = read_excel_bytes(raw) if m.lower().endswith(".xlsx") else pl.read_csv(raw, infer_schema_length=0)
        df.columns = [c.strip().upper().lstrip("﻿") for c in df.columns]
        frames.append(df)
    return pl.concat(frames, how="diagonal_relaxed") if len(frames) > 1 else frames[0]


def build_occ_sector(ind: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    det = ind.filter(pl.col("O_GROUP") == "detailed")
    sector_rows = det.filter((pl.col("I_GROUP") == "sector") | pl.col("NAICS").cast(pl.Utf8).str.starts_with("99"))
    sector_rows = sector_rows.with_columns(
        pl.col("NAICS").cast(pl.Utf8).map_elements(naics_to_sector, return_dtype=pl.Utf8).alias("sector_code"),
        _num("TOT_EMP").alias("emp"),
    ).filter(pl.col("sector_code").is_not_null() & pl.col("emp").is_not_null())
    g = sector_rows.group_by(["OCC_CODE", "sector_code"]).agg(pl.col("emp").sum())
    g = g.with_columns((pl.col("emp") / pl.col("emp").sum().over("OCC_CODE")).alias("emp_share"))
    out = g.select(pl.col("OCC_CODE").alias("occ_code"), "sector_code", "emp_share").with_columns(
        pl.lit(f"real:OEWS_{VINTAGE.replace(' ', '')}_industry").alias("source_tag")).sort(["occ_code", "sector_code"])
    info = {"sectors_present": sorted(out["sector_code"].unique().to_list()), "occupations": out["occ_code"].n_unique()}
    return out, info


def build_occ_state(st: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    det = st.filter((pl.col("O_GROUP") == "detailed") & (pl.col("AREA_TYPE").cast(pl.Utf8) == "2"))
    fips = (pl.when(pl.col("AREA").cast(pl.Utf8).str.len_chars() <= 2).then(pl.col("AREA").cast(pl.Utf8).str.zfill(2))
            .otherwise(pl.col("AREA").cast(pl.Utf8).str.zfill(7).str.slice(0, 2)))            # state files carry the 2-digit FIPS ("1".."56"); older files 7 digits
    det = det.with_columns(fips.alias("fips"), _num("TOT_EMP").alias("emp"))
    det = det.filter(pl.col("emp").is_not_null())
    occ_state = det.select(pl.col("OCC_CODE").alias("occ_code"), "fips", pl.col("emp").cast(pl.Int64)).with_columns(
        pl.lit(f"real:OEWS_{VINTAGE.replace(' ', '')}_state").alias("source_tag")).sort(["occ_code", "fips"])
    tot = st.filter((pl.col("O_GROUP") == "total") & (pl.col("AREA_TYPE").cast(pl.Utf8) == "2")).select(
        fips.alias("fips"),
        pl.col("AREA_TITLE").alias("name"), pl.col("PRIM_STATE").alias("abbrev"),
        _num("TOT_EMP").cast(pl.Int64).alias("emp_total"),
    ).with_columns(pl.lit(f"real:OEWS_{VINTAGE.replace(' ', '')}_state").alias("source_tag")).sort("fips")
    return occ_state, tot


def refresh_occupations(root: Path, nat: pl.DataFrame, dry_run: bool) -> None:
    path = root / "data" / "processed" / "occupations.csv"
    if not path.exists():
        print("  occupations.csv not present; run `aiwsim data build` first (skipping refresh)")
        return
    occ = pl.read_csv(path, infer_schema_length=0)
    det = nat.filter(pl.col("O_GROUP") == "detailed").select(
        pl.col("OCC_CODE").alias("occ_code"), _num("TOT_EMP").cast(pl.Int64).alias("emp_national"),
        _num("A_MEAN").alias("wage_mean_annual"), _num("A_PCT10").alias("wage_p10_annual"),
        _num("A_MEDIAN").alias("wage_median_annual"))
    merged = occ.drop(["emp_national", "wage_mean_annual", "wage_p10_annual", "wage_median_annual"]).join(
        det, on="occ_code", how="left")
    n_missing = merged.filter(pl.col("emp_national").is_null()).height
    print(f"  occupations.csv refresh: {occ.height - n_missing} matched, {n_missing} occupations not in {VINTAGE}")
    merged = merged.with_columns(pl.col("source_tag").str.replace("OEWS_May2021", f"OEWS_{VINTAGE.replace(' ', '')}"))
    write_csv(merged.select(occ.columns), path, dry_run)


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, **URLS})
    root = resolve_root(args)
    raw_dir = root / "data" / "raw" / "oews"
    src = SOURCES["bls_oews"]
    ext = root / "data" / "external" / "bls"
    ext_files = {"national_by_industry": "natsector", "state": "state", "national_cross_industry": "national"}
    tables: dict[str, pl.DataFrame] = {}
    if ext.exists() and all(list(ext.glob(f"{v}_M20*_dl.xlsx")) for v in ext_files.values()):
        # the external-data workflow fetched the extracted spreadsheets on a runner (BLS is unreachable from the build environment)
        for k, v in ext_files.items():
            f = max(ext.glob(f"{v}_M20*_dl.xlsx"))
            print(f"  external {f}")
            df = read_excel_bytes(f.read_bytes()); df.columns = [c.strip().upper().lstrip("\ufeff") for c in df.columns]; tables[k] = df
        zips = {}
    else:
        zips = {k: download(u, raw_dir / Path(u).name, force=args.force) for k, u in URLS.items()}

    ind = tables.get("national_by_industry") if tables else _load_zip_table(zips["national_by_industry"])
    occ_sector, info = build_occ_sector(ind)
    print(f"  occ_sector: {info}")
    p = write_csv(occ_sector, root / "data" / "processed" / "occ_sector.csv", args.dry_run)
    if not args.dry_run:
        write_provenance(root, "occ_sector", p, source=f"OEWS {VINTAGE} national occupation x industry ({URLS['national_by_industry']})",
                         source_url=LANDING, license=src.license, status="real",
                         transformations=[("I_GROUP == 'sector' rows (+ NAICS 999xxx government -> 92) mapped to the "
                                          "20 sectors of spec §1.2 (data/fixtures/sectors_20.csv)"),
                                          "emp_share renormalized within occupation over published cells"],
                         notes=f"{NOT_IN_INVENTORY}. Sectors present: {info['sectors_present']}",
                         extra={"ingested": True, "vintage": VINTAGE})

    st = tables.get("state") if tables else _load_zip_table(zips["state"])
    occ_state, states = build_occ_state(st)
    p1 = write_csv(occ_state, root / "data" / "processed" / "occ_state.csv", args.dry_run)
    p2 = write_csv(states, root / "data" / "processed" / "states.csv", args.dry_run)
    if not args.dry_run:
        for table, p in (("occ_state", p1), ("states", p2)):
            write_provenance(root, table, p, source=f"OEWS {VINTAGE} state file ({URLS['state']})", source_url=LANDING,
                             license=src.license, status="real",
                             transformations=["AREA_TYPE == 2 (states + DC); fips = first two digits of AREA",
                                              "suppressed cells dropped (state sums < national)"],
                             notes=NOT_IN_INVENTORY, extra={"ingested": True, "vintage": VINTAGE})

    nat = tables.get("national_cross_industry") if tables else _load_zip_table(zips["national_cross_industry"])
    refresh_occupations(root, nat, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

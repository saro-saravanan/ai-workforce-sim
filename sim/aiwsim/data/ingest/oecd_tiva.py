"""OECD TiVA (Trade in Value Added) -> ``import_share`` in ``regions/regions.csv`` and
``regions/trade_weights.csv``.

Inventory row 16 records the TiVA topic page only.  The SDMX query below targets the TiVA 2025
main-indicators dataflow on ``sdmx.oecd.org`` and is NOT IN INVENTORY; the dataflow id and the
dimension codes must be confirmed with ``--check`` and a first ``--dry-run`` (the parser reads
the CSV header, so column names are matched case-insensitively).

Indicators used (TiVA 2025 measure codes, verify at ingest):
  ``FFD_DVA``  origin of value added in final demand: the share of ``REF_AREA``'s final demand
               met by value added originating in ``PARTNER`` (WLD for total, own code for domestic).
The domestic share is the region's own-origin share; ``import_share`` = 1 - domestic share; the
weights over the other nine regions are the partner shares, renormalised to the import share
(rest-of-world origin is dropped, as in the FIXTURE).  EU-27 is aggregated from its members with
intra-EU origin counted as domestic; RoA aggregates the TiVA economies that fall in the region
(TiVA ends 2022; the latest year is extrapolated flat, inventory row 16).
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
from aiwsim.data.regions import EU27, REGION_IDS
from aiwsim.data.sources import SOURCES

LANDING = "https://www.oecd.org/en/topics/sub-issues/trade-in-value-added.html"
MEASURE = "FFD_DVA"
URLS = {
    "tiva_sdmx_csv": ("https://sdmx.oecd.org/public/rest/data/OECD.STI.PIE,DSD_TIVA_MAIN@DF_TIVA_MAIN,1.0/"
                      f"..{MEASURE}...?format=csvfilewithlabels"),  # NOT IN INVENTORY
}
SOURCE_TAG = "real:OECD_TiVA_2025_FFD_DVA;rest-of-world origin dropped"


def region_of(members: pl.DataFrame) -> dict[str, str]:
    return {r["iso3"]: r["region_id"] for r in members.to_dicts() if r["region_id"]}


def parse_tiva(path, members: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """(region_to, region_from, value) with value = value added in region_to's final demand that
    originates in region_from (levels; shares are formed by the caller)."""
    df = pl.read_csv(path, infer_schema_length=0)
    lc = {c.lower(): c for c in df.columns}
    ref = lc.get("ref_area") or lc.get("cou")
    par = lc.get("partner") or lc.get("par")
    meas, time_c, val = lc.get("measure") or lc.get("ind"), lc.get("time_period"), lc.get("obs_value")
    if not all([ref, par, time_c, val]):
        raise SystemExit(f"unexpected TiVA columns {df.columns}")
    df = df.select(pl.col(ref).alias("to"), pl.col(par).alias("frm"), pl.col(time_c).cast(pl.Int64, strict=False).alias("year"),
                   pl.col(val).cast(pl.Float64, strict=False).alias("v"),
                   *([pl.col(meas).alias("measure")] if meas else []))
    if "measure" in df.columns:
        df = df.filter(pl.col("measure") == MEASURE)
    df = df.filter(pl.col("v").is_not_null())
    year = int(df["year"].max())
    df = df.filter(pl.col("year") == year)
    rmap = region_of(members)
    df = df.with_columns(pl.col("to").replace_strict(rmap, default=None).alias("region_to"),
                         pl.col("frm").replace_strict(rmap, default=None).alias("region_from"))
    cov = {r: sorted(set(df.filter(pl.col("region_to") == r)["to"])) for r in REGION_IDS}
    # EU-27 members inside the EU count as domestic; RoA likewise across its members
    agg = df.filter(pl.col("region_to").is_not_null() & pl.col("region_from").is_not_null()) \
            .group_by("region_to", "region_from").agg(pl.col("v").sum().alias("v"))
    return agg, {"year": year, "economies_by_region": cov, "eu27": sorted(EU27)}


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, **URLS})
    root = resolve_root(args)
    src = SOURCES["oecd"]
    proc = root / "data" / "processed" / "regions"
    members = pl.read_csv(proc / "region_members.csv", infer_schema_length=0)
    regions = pl.read_csv(proc / "regions.csv", infer_schema_length=0)
    raw = download(URLS["tiva_sdmx_csv"], root / "data" / "raw" / "oecd" / f"tiva_{MEASURE}.csv", force=args.force)
    agg, info = parse_tiva(raw, members)
    covered = [r for r in REGION_IDS if info["economies_by_region"].get(r)]
    print(f"  TiVA {info['year']}: regions with data {covered}")
    rows, import_share = [], {}
    for to in REGION_IDS:
        sub = {r["region_from"]: float(r["v"]) for r in agg.filter(pl.col("region_to") == to).to_dicts()}
        if to not in covered or not sub or to not in sub:
            # keep the FIXTURE row for this region
            old = pl.read_csv(proc / "trade_weights.csv", infer_schema_length=0).filter(pl.col("region_to") == to)
            rows.extend((r["region_from"], to, float(r["weight"]), r["source_tag"]) for r in old.to_dicts())
            continue
        total = sum(sub.values())
        dom = sub[to] / total
        import_share[to] = round(1.0 - dom, 4)
        foreign = {f: v for f, v in sub.items() if f != to}
        fsum = sum(foreign.values())
        for frm in REGION_IDS:
            w = dom if frm == to else (1.0 - dom) * foreign.get(frm, 0.0) / fsum if fsum else 0.0
            rows.append((frm, to, round(w, 6), SOURCE_TAG))
    tw = pl.DataFrame(rows, schema=["region_from", "region_to", "weight", "source_tag"], orient="row")
    p = write_csv(tw, proc / "trade_weights.csv", args.dry_run)
    reg = regions.with_columns(pl.col("import_share").cast(pl.Float64)).with_columns(
        pl.col("region_id").replace_strict(import_share, default=None).fill_null(pl.col("import_share")).alias("import_share"))
    p2 = write_csv(reg, proc / "regions.csv", args.dry_run)
    if not args.dry_run:
        write_provenance(
            root, "regions/trade_weights", p, source=f"OECD TiVA 2025 {MEASURE}, {info['year']} (flat extrapolation)",
            source_url=LANDING, license=src.license,
            status="partial (TiVA for covered regions; FIXTURE rows kept elsewhere)",
            transformations=["economies -> regions via regions/region_members.csv; intra-region origin counted as domestic",
                             ("weight(from, to) = origin share of value added in to's final demand; rest-of-world origin "
                              "dropped and foreign shares renormalised to the import share")],
            notes=f"{NOT_IN_INVENTORY}. {info}. import_share written back to regions.csv for {sorted(import_share)}.",
            extra={"ingested": True, "import_share": import_share, "coverage": info["economies_by_region"]})
        write_provenance(
            root, "regions/regions", p2, source="regions.csv with import_share from OECD TiVA (other columns unchanged)",
            source_url=LANDING, license=src.license, status="partial (Natural Earth pop/GDP real; TiVA import_share; other columns E)",
            transformations=[f"import_share = 1 - domestic origin share of final demand ({MEASURE})"],
            notes=f"{NOT_IN_INVENTORY}. Regions updated: {sorted(import_share)}.", extra={"ingested": True})
    return 0


if __name__ == "__main__":
    sys.exit(main())

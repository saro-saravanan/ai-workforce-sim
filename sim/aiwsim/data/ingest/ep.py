"""BLS Employment Projections 2024-34 ingest -> ``baseline_growth_10y`` in ``occupations.csv``.

Inventory row 7 records the landing page https://www.bls.gov/emp/ only.  The occupation matrix
workbook URL below follows the EP site's convention (``ind-occ-matrix/occupation.xlsx``; Table 1.2
"Employment by detailed occupation" is the HTML equivalent); verify with ``--check``.

Writes ``data/processed/baseline_growth.csv`` (occ_code, baseline_growth_10y, vintage) and, if
``occupations.csv`` exists, updates its ``baseline_growth_10y`` column in place (matched on 6-digit
SOC; unmatched occupations fall back to their broad/minor/major aggregate as in the Phase 1 build).
"""

from __future__ import annotations

import sys

import polars as pl

from aiwsim.data.ingest._common import (
    NOT_IN_INVENTORY,
    base_parser,
    download,
    read_excel_bytes,
    resolve_root,
    run_checks,
    write_csv,
    write_provenance,
)
from aiwsim.data.sources import SOURCES

VINTAGE = "2024-34"
LANDING = "https://www.bls.gov/emp/"
URLS = {
    "occupation_matrix_xlsx": "https://www.bls.gov/emp/ind-occ-matrix/occupation.xlsx",  # NOT IN INVENTORY
    "table_1_2_html": "https://www.bls.gov/emp/tables/emp-by-detailed-occupation.htm",   # NOT IN INVENTORY
}


def parse_matrix(data: bytes) -> pl.DataFrame:
    """Find the code column and the 'Employment change, percent, 2024-34' column, whatever the header rows."""
    df = read_excel_bytes(data, has_header=False)
    # locate the header row: first row containing a cell that mentions 'code'
    header_idx = None
    for i, row in enumerate(df.head(10).iter_rows()):
        cells = [str(c or "").lower() for c in row]
        if any("code" in c for c in cells) and any("percent" in c for c in cells):
            header_idx = i
            break
    if header_idx is None:
        raise SystemExit("could not locate header row in occupation.xlsx; inspect the workbook")
    header = [str(c or "").strip() for c in df.row(header_idx)]
    body = df.slice(header_idx + 1)
    body.columns = [h or f"col{i}" for i, h in enumerate(header)]
    code_col = next(c for c in body.columns if "code" in c.lower())
    pct_col = next(c for c in body.columns if "percent" in c.lower() and "change" in c.lower())
    type_col = next((c for c in body.columns if "type" in c.lower()), None)
    out = body.select(pl.col(code_col).alias("occ_code"), pl.col(pct_col).cast(pl.Float64, strict=False).alias("pct"),
                      *( [pl.col(type_col).alias("occ_type")] if type_col else []))
    out = out.filter(pl.col("occ_code").str.contains(r"^\d{2}-\d{4}$") & pl.col("pct").is_not_null())
    if type_col:
        out = out.filter(pl.col("occ_type").str.to_lowercase().str.contains("line item|detailed|summary").fill_null(True))
    return out.select("occ_code", (pl.col("pct") / 100).alias("baseline_growth_10y")).unique(subset="occ_code")


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    ap.add_argument("--no-update", action="store_true", help="do not touch occupations.csv")
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, **URLS})
    root = resolve_root(args)
    src = SOURCES["bls_ep"]
    xlsx = download(URLS["occupation_matrix_xlsx"], root / "data" / "raw" / "ep" / "occupation_2024_34.xlsx", force=args.force)
    growth = parse_matrix(xlsx.read_bytes()).with_columns(pl.lit(VINTAGE).alias("vintage"))
    print(f"  parsed {growth.height} occupations with {VINTAGE} percent change")
    p = write_csv(growth, root / "data" / "processed" / "baseline_growth.csv", args.dry_run)
    if not args.dry_run:
        write_provenance(root, "baseline_growth", p, source=f"BLS EP {VINTAGE} occupation matrix", source_url=LANDING,
                         license=src.license, status="real",
                         transformations=["percent change 2024-34 / 100 by 6-digit SOC"], notes=NOT_IN_INVENTORY,
                         extra={"ingested": True, "vintage": VINTAGE})
    occ_path = root / "data" / "processed" / "occupations.csv"
    if args.no_update or not occ_path.exists():
        return 0
    occ = pl.read_csv(occ_path, infer_schema_length=0)
    # detailed match; fall back to broad (xx-xxx0), minor (xx-xx00), major (xx-0000) codes present in the matrix
    g = dict(zip(growth["occ_code"], growth["baseline_growth_10y"]))
    vals, lvls = [], []
    for code in occ["occ_code"]:
        for lvl, key in (("detailed", code), ("broad", code[:-1] + "0"), ("minor", code[:4] + "000"), ("major", code[:2] + "-0000")):
            if key in g:
                vals.append(g[key]); lvls.append(lvl); break
        else:
            vals.append(None); lvls.append("unmatched")
    occ = occ.with_columns(pl.Series("baseline_growth_10y", vals, dtype=pl.Float64), pl.Series("growth_match_level", lvls),
                           pl.col("source_tag").str.replace("EP_2020-30", f"EP_{VINTAGE}"))
    print("  match levels:", occ["growth_match_level"].value_counts().sort("growth_match_level").rows())
    write_csv(occ, occ_path, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

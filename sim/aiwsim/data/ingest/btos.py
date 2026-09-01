"""Census BTOS AI-use series ingest -> ``series/btos.csv`` (+ sector and size cuts).

Inventory row 8 records the landing page https://www.census.gov/programs-surveys/btos.html ; the
biweekly response-estimate downloads (national, state, sector, employment size) are linked from
the BTOS "Data" page.  No file URL is recorded in the inventory: ``DOWNLOAD_PAGE`` below is the
data page and ``--file`` accepts a manually downloaded workbook/CSV.  The parser looks for the AI
question by text ("artificial intelligence" and "last two weeks") rather than by question id, and
splits the series at the 17 Nov 2025 wording change (``wording`` column).
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import polars as pl

from aiwsim.data.ingest._common import (
    base_parser,
    download,
    read_excel_bytes,
    resolve_root,
    run_checks,
    write_csv,
    write_provenance,
)
from aiwsim.data.sources import SOURCES

LANDING = "https://www.census.gov/programs-surveys/btos.html"
DOWNLOAD_PAGE = "https://www.census.gov/programs-surveys/btos/data.html"  # NOT IN INVENTORY (data page)
WORDING_CHANGE = dt.date(2025, 11, 17)
TAG = "real:BTOS"


def _load(path: Path) -> pl.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        return read_excel_bytes(path.read_bytes())
    return pl.read_csv(path, infer_schema_length=0, encoding="utf8-lossy")


def _col(df: pl.DataFrame, *needles: str) -> str | None:
    for c in df.columns:
        lc = c.lower()
        if all(n in lc for n in needles):
            return c
    return None


def extract_ai_series(df: pl.DataFrame) -> pl.DataFrame:
    """Rows of the 'currently using AI' question with answer Yes -> period_end, share (fraction)."""
    qtext = _col(df, "question") or _col(df, "item")
    atext = _col(df, "answer")
    est = _col(df, "estimate") or _col(df, "percent") or _col(df, "value")
    period = _col(df, "period") or _col(df, "date") or _col(df, "week")
    if not all([qtext, atext, est, period]):
        raise SystemExit(f"unrecognized BTOS layout; columns: {df.columns}")
    ai = df.filter(pl.col(qtext).str.to_lowercase().str.contains("artificial intelligence")
                   & pl.col(qtext).str.to_lowercase().str.contains("two weeks")
                   & pl.col(atext).str.to_lowercase().str.starts_with("yes"))
    ai = ai.select(pl.col(period).alias("period_raw"), pl.col(est).cast(pl.Float64, strict=False).alias("share"))
    # period strings vary ("2025-11-17 to 2025-11-30", "Nov 17 - Nov 30, 2025"); keep the last date found
    ai = ai.with_columns(pl.col("period_raw").str.extract_all(r"\d{4}-\d{2}-\d{2}").list.last().alias("period_end"))
    ai = ai.filter(pl.col("period_end").is_not_null()).with_columns(
        (pl.col("share") / 100).alias("share_using_ai"),
        pl.when(pl.col("period_end").str.to_date() >= WORDING_CHANGE).then(pl.lit("business_functions"))
        .otherwise(pl.lit("original")).alias("wording"),
        pl.lit("firm").alias("weighting"), pl.lit(TAG).alias("source_tag"))
    return ai.select("period_end", "share_using_ai", "wording", "weighting", "source_tag").sort("period_end")


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    ap.add_argument("--file", type=Path, help="manually downloaded BTOS national response-estimates file")
    ap.add_argument("--sector-file", type=Path, help="sector cut (optional)")
    ap.add_argument("--size-file", type=Path, help="employment-size cut (optional)")
    ap.add_argument("--url", help="direct file URL if known (overrides --file)")
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, "data_page": DOWNLOAD_PAGE, **({"file": args.url} if args.url else {})})
    root = resolve_root(args)
    src = SOURCES["btos"]
    if args.url:
        path = download(args.url, root / "data" / "raw" / "btos" / Path(args.url).name, force=args.force)
    elif args.file:
        path = args.file
    else:
        print(f"no --url/--file given; download the national response estimates from {DOWNLOAD_PAGE} and re-run")
        return 2
    nat = extract_ai_series(_load(path))
    print(f"  national series: {nat.height} periods, {nat['period_end'].min()} .. {nat['period_end'].max()}")
    p = write_csv(nat, root / "data" / "processed" / "series" / "btos.csv", args.dry_run)
    if not args.dry_run:
        write_provenance(root, "series/btos", p, source=f"Census BTOS response estimates ({path.name})",
                         source_url=args.url or LANDING, license=src.license, status="real",
                         transformations=["AI question located by text; answer 'Yes'; percent -> fraction",
                                          f"wording = business_functions from {WORDING_CHANGE} else original"],
                         notes="Sector/size cuts in series/btos_sector.csv and series/btos_size.csv when supplied.",
                         extra={"ingested": True})
    for label, f in (("sector", args.sector_file), ("size", args.size_file)):
        if f:
            cut = _load(f)
            key = _col(cut, "sector") or _col(cut, "naics") or _col(cut, "size") or _col(cut, "employment")
            if key is None:
                print(f"  {label} file: no cut column recognized; skipped")
                continue
            parts = [extract_ai_series(g).with_columns(pl.lit(str(k)).alias(label))
                     for k, g in cut.group_by(key, maintain_order=True)]
            out = pl.concat(parts)
            write_csv(out, root / "data" / "processed" / "series" / f"btos_{label}.csv", args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

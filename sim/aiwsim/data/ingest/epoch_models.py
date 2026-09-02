"""Epoch AI Notable AI Models -> ``regions/actor_releases.csv`` (dates, open-weights flag, ECI).

Inventory row 10 records the landing pages (https://epoch.ai/data/notable-ai-models,
https://epoch.ai/eci).  The CSV URLs below follow Epoch's ``epochdb`` download convention and are
NOT IN INVENTORY; verify with ``--check``.  Data CC BY 4.0.

Rows are kept for organisations mapped to our actors (``ORG_TO_ACTOR``) with a publication date
from 2023-03-01 on.  ``open_weights`` comes from Epoch's ``Accessibility`` column (any value
starting with "Open weights"); ``capability_index`` is log2 of the METR 50% horizon (minutes) where
the model name matches ``series/metr_horizons.csv``; ``eci`` is Epoch's Capabilities Index score
where the ECI file has the model.  The transcribed table in ``aiwsim.data.actors`` is replaced
wholesale, so a model missing from Epoch disappears (the dry run lists the difference).
"""

from __future__ import annotations

import math
import sys

import polars as pl

from aiwsim.data.actors import ACTORS, RELEASES_TAG
from aiwsim.data.ingest._common import (
    NOT_IN_INVENTORY,
    base_parser,
    download,
    resolve_root,
    run_checks,
    write_csv,
    write_provenance,
)
from aiwsim.data.sources import SOURCES

LANDING = "https://epoch.ai/data/notable-ai-models"
URLS = {
    "notable_models_csv": "https://epoch.ai/data/epochdb/notable_ai_models.csv",  # NOT IN INVENTORY
    "eci_csv": "https://epoch.ai/data/epochdb/eci.csv",  # NOT IN INVENTORY
}
START_DATE = "2023-03-01"
# Epoch "Organization" strings (lower-cased substring match, first hit wins) -> actor_id.
ORG_TO_ACTOR: list[tuple[str, str]] = [
    ("openai", "openai"), ("anthropic", "anthropic"), ("google deepmind", "google_deepmind"),
    ("google", "google_deepmind"), ("deepmind", "google_deepmind"), ("meta", "meta"), ("xai", "xai"),
    ("microsoft", "microsoft"), ("amazon", "amazon"), ("nvidia", "nvidia"), ("mistral", "mistral"),
    ("aleph alpha", "aleph_alpha"), ("deepseek", "deepseek"), ("alibaba", "alibaba"), ("qwen", "alibaba"),
    ("bytedance", "bytedance"), ("moonshot", "moonshot"), ("zhipu", "zhipu"), ("z.ai", "zhipu"),
    ("baidu", "baidu"), ("tencent", "tencent"), ("samsung", "samsung"), ("softbank", "softbank"),
    ("sb intuitions", "softbank"), ("naver", "naver"), ("sakana", "sakana"),
]
SOURCE_TAG = "real:Epoch_notable_models;ECI where published"


def actor_for(org: str | None) -> str | None:
    s = (org or "").lower()
    for needle, actor in ORG_TO_ACTOR:
        if needle in s:
            return actor
    return None


def _col(df: pl.DataFrame, *cands: str) -> str | None:
    lc = {c.lower(): c for c in df.columns}
    for c in cands:
        if c.lower() in lc:
            return lc[c.lower()]
    return None


def parse_models(path, metr: pl.DataFrame, eci: pl.DataFrame | None) -> pl.DataFrame:
    df = pl.read_csv(path, infer_schema_length=0)
    model_c, org_c = _col(df, "Model", "System"), _col(df, "Organization", "Organization(s)")
    date_c, acc_c = _col(df, "Publication date"), _col(df, "Accessibility", "Model accessibility")
    if not (model_c and org_c and date_c):
        raise SystemExit(f"unexpected Notable Models columns {df.columns}")
    out = df.select(pl.col(model_c).alias("model"), pl.col(org_c).alias("org"), pl.col(date_c).alias("date"),
                    (pl.col(acc_c) if acc_c else pl.lit(None, dtype=pl.Utf8)).alias("accessibility"))
    out = out.with_columns(pl.col("org").map_elements(actor_for, return_dtype=pl.Utf8).alias("actor_id"))
    out = out.filter(pl.col("actor_id").is_not_null() & pl.col("date").str.contains(r"^\d{4}-\d{2}-\d{2}$")
                     & (pl.col("date") >= START_DATE))
    out = out.with_columns(
        pl.col("accessibility").fill_null("").str.to_lowercase().str.starts_with("open weights").cast(pl.Int64)
        .alias("open_weights"))
    horizon = {m: float(h) for m, h in zip(metr["model"], metr["horizon_minutes_p50"].cast(pl.Float64)) if h}
    out = out.with_columns(pl.col("model").map_elements(
        lambda m: round(math.log2(horizon[m]), 3) if m in horizon else None, return_dtype=pl.Float64)
        .alias("capability_index"))
    if eci is not None:
        m_c, s_c = _col(eci, "Model", "model"), _col(eci, "ECI", "eci", "score", "ECI score")
        if m_c and s_c:
            e = eci.select(pl.col(m_c).alias("model"), pl.col(s_c).cast(pl.Float64, strict=False).alias("eci"))
            e = e.group_by("model").agg(pl.col("eci").max())
            out = out.join(e, on="model", how="left")
    if "eci" not in out.columns:
        out = out.with_columns(pl.lit(None, dtype=pl.Float64).alias("eci"))
    out = out.with_columns(pl.col("accessibility").alias("note"), pl.lit(SOURCE_TAG).alias("source_tag"))
    return out.select("actor_id", "model", "date", "capability_index", "open_weights", "note", "source_tag", "eci") \
        .unique(subset=["actor_id", "model"], keep="first").sort(["date", "actor_id", "model"])


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    ap.add_argument("--no-eci", action="store_true", help="skip the ECI file")
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"landing": LANDING, **URLS})
    root = resolve_root(args)
    src = SOURCES["epoch"]
    proc = root / "data" / "processed"
    metr = pl.read_csv(proc / "series" / "metr_horizons.csv", infer_schema_length=0)
    raw_dir = root / "data" / "raw" / "epoch"
    models = download(URLS["notable_models_csv"], raw_dir / "notable_ai_models.csv", force=args.force)
    eci = None
    if not args.no_eci:
        try:
            eci = pl.read_csv(download(URLS["eci_csv"], raw_dir / "eci.csv", force=args.force), infer_schema_length=0)
        except Exception as e:  # noqa: BLE001 - the ECI file is optional
            print(f"  ECI file unavailable ({type(e).__name__}: {e}); eci column left null")
    rel = parse_models(models, metr, eci)
    known = {a["actor_id"] for a in ACTORS}
    print(f"  {rel.height} releases for {rel['actor_id'].n_unique()} actors; actors without rows: "
          f"{sorted(known - set(rel['actor_id']))}")
    old_p = proc / "regions" / "actor_releases.csv"
    if old_p.exists():
        old = pl.read_csv(old_p, infer_schema_length=0)
        gone = old.join(rel.select("actor_id", "model"), on=["actor_id", "model"], how="anti")
        if gone.height:
            print(f"  transcribed rows not matched in Epoch by (actor_id, model): {gone.select('actor_id', 'model').rows()}")
    p = write_csv(rel, old_p, args.dry_run)
    if not args.dry_run:
        write_provenance(
            root, "regions/actor_releases", p, source="Epoch AI Notable AI Models (+ ECI where published)",
            source_url=LANDING, license=src.license, status="real",
            transformations=[f"Organization -> actor_id via ORG_TO_ACTOR; publication date >= {START_DATE}",
                             "open_weights = Accessibility starts with 'Open weights'",
                             "capability_index = log2(METR 50% horizon minutes) where the model is in series/metr_horizons.csv",
                             "eci = Epoch Capabilities Index score by model name (max over evaluations)"],
            notes=f"{NOT_IN_INVENTORY}. Replaces the transcribed table ({RELEASES_TAG}).",
            extra={"ingested": True, "extra_urls": list(src.extra_urls)})
    return 0


if __name__ == "__main__":
    sys.exit(main())

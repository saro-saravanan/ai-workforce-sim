"""Build every table of contracts §1 into ``data/processed/`` from the staged raw inputs.

    from aiwsim.data.build import build_all, status
    build_all(root)   # -> {table: provenance status}
    status(root)      # prints provenance status per table

Phase 1 inputs (staged, gitignored) are the files mirrored in openai/GPTs-are-GPTs (MIT):
``full_labelset.tsv`` (O*NET tasks with Eloundou labels), ``occ_level.csv`` (occupation betas),
``national_May2021_dl.csv`` (OEWS May 2021 national) and ``occupations_projections_processed.csv``
(BLS EP 2020-30); plus Natural Earth 1:110m admin-1.  Tables that need network sources are
fixtures here and are replaced by ``aiwsim.data.ingest``.

Phase 2 cohort tables (contracts §7, ``data/processed/cohorts/``) additionally need the repo's
``occupations_onet_basic_skills.csv`` (O*NET Job Zone by title) and
``occupations_onet_bls_matched.csv`` (O*NET title <-> OEWS code); see ``aiwsim.data.cohorts``.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from aiwsim.data import actors as ac
from aiwsim.data import classify, series
from aiwsim.data import clusters as cl
from aiwsim.data import cohorts as co
from aiwsim.data import fixtures as fx
from aiwsim.data import regions as rg
from aiwsim.data.geo import build_us_states, build_world
from aiwsim.data.provenance import list_provenance, status_kind, write_provenance
from aiwsim.data.registry import write_registry
from aiwsim.data.sources import SOURCES

TABLES = [
    "occupations", "tasks", "sectors", "occ_sector", "states", "occ_state",
    "series/btos", "series/metr_horizons", "series/capex", "series/regulatory_events",
    "params/registry", "geo/us_states",
    "cohorts/occ_decile", "cohorts/national_deciles", "cohorts/occ_education", "cohorts/occ_age",
    # Phase 3 (contracts §11)
    "regions/region_members", "regions/regions", "regions/occ_region", "regions/trade_weights",
    "regions/actors", "regions/actor_releases", "regions/value_chain", "geo/world",
    "applications/embodiment_classes", "applications/applications", "applications/approval_paths", "applications/self_employed",
]
NE_WORLD_50M = "ne_50m_admin_0_countries.geojson"

RAW_GPTS = Path("data/raw/gpts_are_gpts")
RAW_NE = Path("data/raw/natural_earth")
PROCESSED = Path("data/processed")

MISSING_WAGE_TOKENS = {"#", "*", "**", ""}


# ------------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------------
def _num(col: str) -> pl.Expr:
    """OEWS numeric column: strip thousands separators; '#', '*' and blanks -> null."""
    return (
        pl.when(pl.col(col).is_in(list(MISSING_WAGE_TOKENS)) | pl.col(col).is_null())
        .then(None)
        .otherwise(pl.col(col).str.replace_all(",", ""))
        .cast(pl.Float64, strict=False)
    )


def _gpts_commit(root: Path) -> str:
    p = root / RAW_GPTS / "COMMIT"
    return p.read_text().strip() if p.exists() else ""


def _write_csv(df: pl.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(path)
    return path


# ------------------------------------------------------------------------------------------------
# raw loaders
# ------------------------------------------------------------------------------------------------
def load_raw(root: Path) -> dict[str, pl.DataFrame]:
    g = root / RAW_GPTS
    labels = pl.read_csv(g / "full_labelset.tsv", separator="\t", infer_schema_length=0)
    oews = pl.read_csv(g / "national_May2021_dl.csv", infer_schema_length=0, encoding="utf8-lossy")
    oews = oews.rename({oews.columns[0]: "AREA"})  # BOM-prefixed first header
    proj = pl.read_csv(g / "occupations_projections_processed.csv", infer_schema_length=0)
    occ_level = pl.read_csv(g / "occ_level.csv", infer_schema_length=0)
    skills_path = g / "occupations_onet_basic_skills.csv"
    if not skills_path.exists():
        raise FileNotFoundError(
            f"{skills_path} missing: stage data/occupations_onet_basic_skills.csv from openai/GPTs-are-GPTs "
            "(the O*NET Job Zone source for the Phase 2 cohort tables)")
    basic_skills = pl.read_csv(skills_path, infer_schema_length=0)
    matched = pl.read_csv(g / "occupations_onet_bls_matched.csv", infer_schema_length=0)
    return {"labels": labels, "oews": oews, "proj": proj, "occ_level": occ_level,
            "basic_skills": basic_skills, "matched": matched}


# ------------------------------------------------------------------------------------------------
# occupations + tasks + clusters
# ------------------------------------------------------------------------------------------------
def build_occupations_and_tasks(raw: dict[str, pl.DataFrame], params: cl.ClusterParams | None = None):
    params = params or cl.ClusterParams()
    notes: dict[str, object] = {}
    oews = raw["oews"]
    det = oews.filter(pl.col("O_GROUP") == "detailed").select(
        pl.col("OCC_CODE").alias("occ_code"), pl.col("OCC_TITLE").alias("title"),
        _num("TOT_EMP").cast(pl.Int64).alias("emp_national"),
        _num("A_MEAN").alias("wage_mean_annual"), _num("A_PCT10").alias("wage_p10_annual"),
        _num("A_MEDIAN").alias("wage_median_annual"),
    ).with_columns(pl.col("occ_code").str.slice(0, 2).alias("major_group"))
    oews_codes = set(det["occ_code"])

    # -- wages: '#' (>= $208,000) and '*' are missing.  Fill order (documented in provenance):
    #    (1) the occupation's other reported wage (median <- mean, mean <- median),
    #    (2) the 2-digit major-group value from the OEWS 'major' rows.
    maj = oews.filter(pl.col("O_GROUP") == "major").select(
        pl.col("OCC_CODE").str.slice(0, 2).alias("major_group"),
        _num("A_MEAN").alias("mg_mean"), _num("A_PCT10").alias("mg_p10"), _num("A_MEDIAN").alias("mg_median"),
    )
    det = det.join(maj, on="major_group", how="left")
    n_missing = {c: int(det[c].null_count()) for c in ("wage_mean_annual", "wage_p10_annual", "wage_median_annual")}
    det = det.with_columns(
        (pl.col("wage_mean_annual").is_null() | pl.col("wage_p10_annual").is_null()
         | pl.col("wage_median_annual").is_null()).cast(pl.Int64).alias("wage_imputed"),
        pl.coalesce([pl.col("wage_median_annual"), pl.col("wage_mean_annual"), pl.col("mg_median")]).alias("wage_median_annual"),
        pl.coalesce([pl.col("wage_mean_annual"), pl.col("wage_median_annual"), pl.col("mg_mean")]).alias("wage_mean_annual"),
        pl.coalesce([pl.col("wage_p10_annual"), pl.col("mg_p10")]).alias("wage_p10_annual"),
    ).drop("mg_mean", "mg_p10", "mg_median")
    notes["wages_missing_raw"] = n_missing
    notes["wages_imputed_occupations"] = int(det["wage_imputed"].sum())

    # -- tasks: O*NET-SOC -> 6-digit SOC -> OEWS code; weights Core 2 / Supplemental 1 (missing -> 1)
    lab = raw["labels"].select(
        pl.col("Task ID").cast(pl.Float64).cast(pl.Int64).cast(pl.Utf8).alias("task_id"),
        pl.col("O*NET-SOC Code").alias("onet_soc_code"),
        pl.col("Task").alias("task_text"),
        pl.col("Task Type").alias("task_type"),
        pl.col("human_labels"), pl.col("gpt4_exposure"),
        pl.col("beta").cast(pl.Float64),
    ).with_columns(pl.col("onet_soc_code").str.slice(0, 7).alias("soc6"))
    soc6_codes = sorted(set(lab["soc6"]))
    mapping = {c: cl.map_to_oews(c, oews_codes) for c in soc6_codes}
    unmapped = sorted(c for c, v in mapping.items() if v is None)
    notes["onet_soc6_unmapped_dropped"] = unmapped
    notes["onet_soc6_via_broad"] = sorted(c for c, v in mapping.items() if v and v != c and c not in cl.ONET_TO_OEWS_2021)
    notes["onet_soc6_via_crosswalk"] = {c: v for c, v in cl.ONET_TO_OEWS_2021.items() if v}
    map_df = pl.DataFrame({"soc6": list(mapping), "occ_code": list(mapping.values())})
    lab = lab.join(map_df, on="soc6", how="left")
    n_dropped = lab.filter(pl.col("occ_code").is_null()).height
    lab = lab.filter(pl.col("occ_code").is_not_null())
    notes["tasks_dropped_unmapped"] = n_dropped
    n_type_missing = int(lab["task_type"].null_count())
    notes["tasks_task_type_missing_weight1"] = n_type_missing
    lab = lab.with_columns(
        pl.when(pl.col("task_type") == "Core").then(2.0).otherwise(1.0).alias("w_raw"),
        pl.when(pl.col("human_labels").is_not_null()).then(pl.col("human_labels")).otherwise(pl.col("gpt4_exposure")).alias("exposure_label"),
        pl.when(pl.col("human_labels").is_not_null()).then(pl.lit("human_labels")).otherwise(pl.lit("gpt4_exposure")).alias("label_source"),
    ).with_columns((pl.col("w_raw") / pl.col("w_raw").sum().over("occ_code")).alias("weight"))
    notes["label_source_counts"] = {k: int(v) for k, v in
                                    zip(*lab["label_source"].value_counts().sort("label_source").to_dict().values())}

    tasks = classify.classify_frame(lab, "task_text")
    tasks = tasks.with_columns(pl.lit("real:eloundou_labels+onet_tasks;classifiers:E").alias("source_tag")).select(
        "task_id", "occ_code", "task_text", "weight", "exposure_label", "beta",
        "modality", "presence", "use_case", "consequence_high", "channel", "source_tag",
        "onet_soc_code", "task_type", "label_source",
    ).sort(["occ_code", "task_id"])
    notes["classifier_distribution"] = classify.distribution(tasks)
    notes["classifier_distribution_weighted"] = classify.distribution(tasks, weight_col="weight")

    # -- occupation beta (Eloundou): mean of human & GPT-4 betas per O*NET code, averaged to OEWS code
    ob = cl.occupation_beta(raw["occ_level"]).with_columns(pl.col("onet_code").str.slice(0, 7).alias("soc6"))
    ob = ob.join(map_df, on="soc6", how="left").filter(pl.col("occ_code").is_not_null())
    ob = ob.group_by("occ_code").agg(pl.col("beta").mean().alias("eloundou_beta"))
    det = det.join(ob, on="occ_code", how="left")
    n_tasks = tasks.group_by("occ_code").len().rename({"len": "n_tasks"})
    det = det.join(n_tasks, on="occ_code", how="left").with_columns(pl.col("n_tasks").fill_null(0))
    no_beta = det.filter(pl.col("eloundou_beta").is_null())
    notes["occupations_without_onet_tasks"] = {
        "count": no_beta.height, "employment": int(no_beta["emp_national"].sum()),
        "codes": no_beta["occ_code"].to_list(),
    }
    # impute beta for occupations with no O*NET tasks: employment-weighted mean of the minor group,
    # else of the major group.  Flagged in beta_imputed.
    det = det.with_columns(pl.col("occ_code").str.slice(0, 5).alias("minor_group"))
    imp_minor = det.filter(pl.col("eloundou_beta").is_not_null()).group_by("minor_group").agg(
        ((pl.col("eloundou_beta") * pl.col("emp_national")).sum() / pl.col("emp_national").sum()).alias("b_minor"))
    imp_major = det.filter(pl.col("eloundou_beta").is_not_null()).group_by("major_group").agg(
        ((pl.col("eloundou_beta") * pl.col("emp_national")).sum() / pl.col("emp_national").sum()).alias("b_major"))
    det = det.join(imp_minor, on="minor_group", how="left").join(imp_major, on="major_group", how="left")
    det = det.with_columns(
        pl.col("eloundou_beta").is_null().cast(pl.Int64).alias("beta_imputed"),
        pl.coalesce([pl.col("eloundou_beta"), pl.col("b_minor"), pl.col("b_major")]).alias("eloundou_beta"),
    ).drop("b_minor", "b_major", "minor_group")

    # -- baseline growth: BLS EP 2020-30 percent change, matched by title at detailed / broad / minor / major level
    proj = raw["proj"].select(
        pl.col("occupation").str.to_lowercase().str.strip_chars().alias("k"),
        pl.col("pct_emp_change_2020_2030").cast(pl.Float64, strict=False).alias("pct"),
    ).filter(pl.col("pct").is_not_null()).unique(subset="k", keep="first")
    ptab = dict(zip(proj["k"], proj["pct"]))
    titles = {r["OCC_CODE"]: r["OCC_TITLE"].lower().strip() for r in oews.select("OCC_CODE", "OCC_TITLE").to_dicts()}
    growth, level = [], []
    for code, title in zip(det["occ_code"], det["title"]):
        cand = [("detailed", title.lower().strip()), ("broad", titles.get(code[:-1] + "0")),
                ("minor", titles.get(code[:4] + "000")), ("major", titles.get(code[:2] + "-0000"))]
        g, lv = None, None
        for name, key in cand:
            if key is not None and key in ptab:
                g, lv = ptab[key] / 100.0, name
                break
        growth.append(g)
        level.append(lv or "unmatched")
    det = det.with_columns(pl.Series("baseline_growth_10y", growth, dtype=pl.Float64),
                           pl.Series("growth_match_level", level))
    notes["growth_match_levels"] = {k: int(v) for k, v in
                                    zip(*det["growth_match_level"].value_counts().sort("growth_match_level").to_dict().values())}

    # -- clusters (spec §1.1)
    cdf = cl.build_clusters(det.select("occ_code", "title", "emp_national", "wage_median_annual",
                                       pl.col("eloundou_beta").alias("beta")), params)
    det = det.join(cdf, on="occ_code", how="left")
    notes["clusters"] = cl.summarize(cdf)
    notes["cluster_params"] = params.__dict__

    occ = det.with_columns(pl.lit("partial:OEWS_May2021;EP_2020-30").alias("source_tag")).select(
        "occ_code", "title", "major_group", "cluster_id", "cluster_title", "emp_national",
        "wage_mean_annual", "wage_p10_annual", "wage_median_annual", "baseline_growth_10y", "source_tag",
        "eloundou_beta", "n_tasks", "growth_match_level", "wage_imputed", "beta_imputed", "cluster_size", "cluster_rule",
    ).sort("occ_code")
    return occ, tasks, notes


# ------------------------------------------------------------------------------------------------
# build_all
# ------------------------------------------------------------------------------------------------
def build_all(root: Path | str, verbose: bool = True, cluster_params: cl.ClusterParams | None = None) -> dict[str, str]:
    root = Path(root).resolve()
    out = root / PROCESSED
    out.mkdir(parents=True, exist_ok=True)
    (root / "data" / "fixtures").mkdir(parents=True, exist_ok=True)
    commit = _gpts_commit(root)
    el, oews_src, ep_src, ne = SOURCES["eloundou"], SOURCES["bls_oews"], SOURCES["bls_ep"], SOURCES["natural_earth"]
    statuses: dict[str, str] = {}

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    raw = load_raw(root)
    occ, tasks, notes = build_occupations_and_tasks(raw, cluster_params)

    # ---- occupations.csv ---------------------------------------------------------------------
    p = _write_csv(occ, out / "occupations.csv")
    statuses["occupations"] = "partial"
    write_provenance(
        root, "occupations", p,
        source="OEWS May 2021 national cross-industry (national_May2021_dl.csv) + BLS EP 2020-30 "
               "(occupations_projections_processed.csv), both mirrored in openai/GPTs-are-GPTs; "
               "Eloundou occ_level.csv for clustering betas",
        source_url=el.url, license=f"MIT (repo mirror); underlying BLS data public domain ({oews_src.url}; {ep_src.url})",
        commit=commit, status="partial",
        transformations=[
            "OEWS detailed rows only (831 occupations, SOC 2018 hybrid); TOT_EMP -> emp_national",
            ("wages A_MEAN/A_PCT10/A_MEDIAN; '#' and '*' treated as missing; fill order: occupation's other "
            "reported wage (median<-mean, mean<-median), then major-group value; flagged in wage_imputed"),
            ("baseline_growth_10y = EP 2020-30 percent change / 100, matched by title at detailed, else broad, "
            "minor or major group (growth_match_level)"),
            ("eloundou_beta = mean(human_rating_beta, dv_rating_beta) per O*NET code, averaged to the OEWS code; "
            "imputed (employment-weighted minor-group mean) for occupations without O*NET tasks (beta_imputed)"),
            ("clusters per spec §1.1 (aiwsim.data.clusters): anchors >= 300k, merge within minor group when "
            "|Δbeta| < 0.1 and |Δmedian wage| < 20%, never across major groups"),
        ],
        notes="VINTAGE: employment and wages are OEWS May 2021 and growth is EP 2020-30, not the May 2025 / "
              "2024-34 vintages required by the spec; replace via aiwsim.data.ingest.oews and ingest.ep. "
              f"Wages missing in raw: {notes['wages_missing_raw']}; occupations with any imputed wage: "
              f"{notes['wages_imputed_occupations']}. Growth match levels: {notes['growth_match_levels']}. "
              f"Occupations without O*NET tasks: {notes['occupations_without_onet_tasks']['count']} "
              f"({notes['occupations_without_onet_tasks']['employment']:,} heads), beta imputed. "
              f"Clusters: {notes['clusters']} with params {notes['cluster_params']}.",
        extra={"occupations_without_onet_tasks": notes["occupations_without_onet_tasks"],
               "clusters": notes["clusters"], "cluster_params": notes["cluster_params"],
               "growth_match_levels": notes["growth_match_levels"]},
    )
    log(f"occupations.csv: {occ.height} occupations, {notes['clusters']['n_clusters']} clusters")

    # ---- tasks.csv ---------------------------------------------------------------------------
    p = _write_csv(tasks, out / "tasks.csv")
    statuses["tasks"] = "real"
    write_provenance(
        root, "tasks", p,
        source="openai/GPTs-are-GPTs full_labelset.tsv (O*NET task statements, Eloundou et al. labels)",
        source_url=el.url, license="MIT", commit=commit, status="real",
        transformations=[
            ("O*NET-SOC code -> 6-digit SOC -> OEWS May 2021 code (broad code where OEWS publishes the broad "
            "occupation; explicit crosswalk ONET_TO_OEWS_2021 for SOC-2010-era codes)"),
            "weight = Core 2 / Supplemental 1 (Eloundou coreweight; missing Task Type -> 1), normalized within occ_code",
            "exposure_label = human_labels where present else gpt4_exposure (label_source column records which)",
            "beta from the row's beta column",
            f"modality {classify.CLASSIFIER_VERSION}", f"presence {classify.CLASSIFIER_VERSION}",
            f"use_case (EU AI Act Annex III / Art. 50) {classify.CLASSIFIER_VERSION}",
            f"consequence_high {classify.CLASSIFIER_VERSION}",
            f"channel {classify.CHANNEL_VERSION}",
        ],
        notes="Labels and weights are real (status real); modality, presence, use_case and consequence_high are "
              "E-tagged keyword rules (aiwsim.data.classify) to be replaced by O*NET Work Context / GWA on ingest. "
              f"Label source counts: {notes['label_source_counts']}. Tasks dropped because the SOC is not "
              f"published in OEWS: {notes['tasks_dropped_unmapped']} ({notes['onet_soc6_unmapped_dropped']}). "
              f"Rows with missing Task Type given weight 1: {notes['tasks_task_type_missing_weight1']}. "
              f"Classifier distribution (row shares): {notes['classifier_distribution']}",
        extra={"classifier_distribution": notes["classifier_distribution"],
               "classifier_distribution_weighted": notes["classifier_distribution_weighted"],
               "onet_soc6_via_broad": notes["onet_soc6_via_broad"],
               "onet_soc6_via_crosswalk": notes["onet_soc6_via_crosswalk"]},
    )
    log(f"tasks.csv: {tasks.height} tasks")
    if verbose:
        classify.print_distribution(tasks)

    # ---- sectors.csv (+ fixtures/sectors_20.csv) --------------------------------------------
    sec = pl.DataFrame([fx.SECTOR_ALL])
    p = _write_csv(sec, out / "sectors.csv")
    statuses["sectors"] = "FIXTURE"
    write_provenance(
        root, "sectors", p, source="contracts §1 Phase 1 sector fixture", source_url="docs/contracts.md",
        license="n/a (fixture)", status="FIXTURE",
        transformations=[("single sector ALL: labor_cost_share 0.58, demand_elasticity 0.8, tradable 0, friction 1.0, "
                         "consumption_share 1.0")],
        notes="Replaced by the OEWS occupation x industry matrix (ingest/oews.py) mapped to the 20 sectors of spec "
              "§1.2 listed in data/fixtures/sectors_20.csv; labor_cost_share from BEA I-O, consumption_share from "
              "CPI relative importance.",
    )
    _write_csv(fx.sectors_20_frame(), root / "data" / "fixtures" / "sectors_20.csv")

    # ---- occ_sector.csv ----------------------------------------------------------------------
    occ_sector = occ.select("occ_code").with_columns(pl.lit("ALL").alias("sector_code"), pl.lit(1.0).alias("emp_share"),
                                                     pl.lit(fx.FIXTURE_TAG).alias("source_tag"))
    p = _write_csv(occ_sector, out / "occ_sector.csv")
    statuses["occ_sector"] = "FIXTURE"
    write_provenance(root, "occ_sector", p, source="contracts §1 Phase 1 sector fixture", source_url="docs/contracts.md",
                     license="n/a (fixture)", status="FIXTURE",
                     transformations=["every occupation -> sector ALL with emp_share 1.0"],
                     notes="Replaced by ingest/oews.py (OEWS national occupation x industry).")

    # ---- states.csv / occ_state.csv ----------------------------------------------------------
    st = fx.state_shares()
    shares = st["state_share"].to_list()
    rows = []
    for code, emp in zip(occ["occ_code"], occ["emp_national"]):
        alloc = fx.allocate_integer(int(emp), shares)
        rows.extend((code, f, e) for f, e in zip(st["fips"], alloc))
    occ_state = pl.DataFrame(rows, schema=["occ_code", "fips", "emp"], orient="row").with_columns(
        pl.lit(fx.FIXTURE_TAG).alias("source_tag"))
    emp_tot = occ_state.group_by("fips").agg(pl.col("emp").sum().alias("emp_total"))
    states = st.join(emp_tot, on="fips", how="left").with_columns(pl.lit(fx.FIXTURE_TAG).alias("source_tag")).select(
        "fips", "name", "abbrev", "emp_total", "source_tag", "pop_2020", "state_share").sort("fips")
    p = _write_csv(states, out / "states.csv")
    statuses["states"] = "FIXTURE"
    cap = SOURCES["census_apportionment_2020"]
    state_notes = ("POPULATION SHARE PROXY FOR EMPLOYMENT SHARE; replace with OEWS state ingest (ingest/oews.py). "
                   "state_share = 2020 Census apportionment resident population / 331,449,281 (50 states + DC). "
                   "Populations were transcribed from memory, not fetched: the total matches the published U.S. "
                   "resident population exactly and each state is believed accurate to well within 5%, but the "
                   "table has not been checked against the Census page in this sandbox. Same occupational mix "
                   "in every state.")
    write_provenance(root, "states", p, source=cap.name, source_url=cap.url, license=cap.license, status="FIXTURE",
                     transformations=["state_share = pop_2020 / total", "emp_total = sum of occ_state.emp per state"],
                     notes=state_notes)
    p = _write_csv(occ_state, out / "occ_state.csv")
    statuses["occ_state"] = "FIXTURE"
    write_provenance(root, "occ_state", p, source=cap.name + " x OEWS May 2021 national employment", source_url=cap.url,
                     license=cap.license, status="FIXTURE",
                     transformations=[("emp = largest-remainder integer allocation of emp_national by state_share "
                                      "(sums exactly to emp_national)")],
                     notes=state_notes)
    log(f"states.csv: {states.height} states; occ_state.csv: {occ_state.height} rows")

    # ---- series ------------------------------------------------------------------------------
    series_specs = [
        ("series/btos", series.btos(), SOURCES["btos"], "Census BTOS AI question, inventory §3 table",
         ["transcribed from docs/data-inventory.md §3; shares as fractions; month-only periods dated to month end"],
         ("Sector cuts for the period ending 3 May 2026 (Information 39.7%, Finance and Insurance 33.9%) are in the "
         "row note, not separate rows. Wording change 17 Nov 2025 -> two series (wording column). Full biweekly "
         "series to be pulled by ingest/btos.py.")),
        ("series/metr_horizons", series.metr_horizons(), SOURCES["metr"], "METR time horizons, inventory §3",
         ["transcribed from docs/data-inventory.md §3; hours -> minutes; '>= 16 h' stored as its lower bound"],
         series.METR_DOUBLING_NOTES),
        ("series/capex", series.capex(), SOURCES["sec_capex"], "Hyperscaler capex table, inventory §4",
         ["transcribed from docs/data-inventory.md §4; guidance ranges stored as midpoint with low/high columns"],
         "Key is (company, year, basis): Microsoft is given on both June-fiscal and calendar bases, so (company, "
         "year) alone is not unique — a documented deviation from contracts §1. " + series.CAPEX_SUM_NOTES),
        ("series/regulatory_events", series.regulatory_events(), SOURCES["regulatory"],
         "Regulatory timeline, inventory §5",
         ["transcribed from docs/data-inventory.md §5; month-precision dates set to the 1st (date_precision)"],
         ("Sources: EU Official Journal (Reg. 2024/1689, Reg. 2026/1744), Colorado and California legislatures, "
         "China CAC, BIS press releases.")),
    ]
    for table, df, src, source, transf, note in series_specs:
        p = _write_csv(df, out / f"{table}.csv")
        statuses[table] = series.TAG
        write_provenance(root, table, p, source=source, source_url=src.url, license=src.license, status=series.TAG,
                         transformations=transf, notes=note,
                         extra={"extra_urls": list(src.extra_urls)} if src.extra_urls else None)
    log("series: btos, metr_horizons, capex, regulatory_events")

    # ---- params/registry.yaml ----------------------------------------------------------------
    p = out / "params" / "registry.yaml"
    write_registry(p)
    statuses["params/registry"] = "real (transcribed)"
    from aiwsim.data.registry import COUNT_NOTE, PARAMETERS
    write_provenance(root, "params/registry", p, source="docs/model-spec.md §10 parameter registry (v0.2)",
                     source_url="docs/model-spec.md", license="project", status="real (transcribed)",
                     transformations=[("transcribed row by row; class/modality/size/stage centrals as `by` mappings "
                                      "with top-level central null; textual centrals kept in `note`")],
                     notes=COUNT_NOTE + f" Transcribed rows: {len(PARAMETERS)}.")
    log(f"params/registry.yaml: {len(PARAMETERS)} parameters")

    # ---- geo/us_states.geojson ---------------------------------------------------------------
    raw_ne = root / RAW_NE / "ne_admin1_110m.geojson"
    gj = build_us_states(raw_ne)
    p = out / "geo" / "us_states.geojson"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
    statuses["geo/us_states"] = "real"
    write_provenance(root, "geo/us_states", p, source=f"{ne.name} ({raw_ne.name})", source_url=ne.url,
                     license=ne.license, status="real",
                     transformations=["filter iso_a2 == 'US' (51 features)",
                                      "properties reduced to {fips (from 'fips' = 'USxx'), name, abbrev (= postal)}",
                                      "features sorted by fips"],
                     notes="Geometry unchanged (1:110m).", extra={"extra_urls": list(ne.extra_urls)})
    log("geo/us_states.geojson: 51 features")

    # ---- cohorts/ (contracts §7) -------------------------------------------------------------
    statuses.update(build_cohorts(root, raw, occ, commit, log))
    # ---- regions/ + geo/world (contracts §11) -------------------------------------------------
    statuses.update(build_regions(root, occ, log))
    # ---- applications/ (spec v0.3 §A.3–A.5, §A.8) --------------------------------------------
    statuses.update(build_applications(root, occ, log))
    return statuses


def build_applications(root: Path, occ: pl.DataFrame, log) -> dict[str, str]:
    """Write the four ``data/processed/applications/`` tables and provenance (spec v0.3)."""
    from aiwsim.data import applications as ap
    out = root / PROCESSED / "applications"
    out.mkdir(parents=True, exist_ok=True)
    statuses: dict[str, str] = {}
    spec_url = "docs/model-spec-v0.3-applications.md"
    p = _write_csv(ap.embodiment_classes_frame(), out / "embodiment_classes.csv")
    statuses["applications/embodiment_classes"] = "FIXTURE (E)"
    write_provenance(root, "applications/embodiment_classes", p, source="spec v0.3 §A.3 class parameters (authors' estimates, V? pending §A.10)",
                     source_url=spec_url, license="n/a (estimates)", status="FIXTURE (E: authors' estimates, spec v0.3)",
                     transformations=[("one row per embodiment class: a_emb, theta range, clock, unit price 2025, lifetime, opex ratio, utilization, task units per hour, "
                                      "production ramp cap, cumulative production 2025, adjacent jobs per unit, initial stock and production shares by region")],
                     notes="Every value is an estimate written before the data plan ran; unit prices, utilization, ramps and 2025 production are V? (spec §A.10). "
                           "Replace through the verification items; the registry rows P.108–P.120 carry the ranges.")
    p = _write_csv(ap.applications_frame(), out / "applications.csv")
    statuses["applications/applications"] = "FIXTURE (E)"
    write_provenance(root, "applications/applications", p, source="spec v0.3 §A.8 application catalogue", source_url=spec_url, license="n/a (catalogue)", status="FIXTURE (E: authors' estimates, spec v0.3)",
                     transformations=["one row per application: family, embodiment class(es), target occupation codes, platform flag, regions first, anchor series, constraints, provisional timings"],
                     notes="Phase 6 implements the embodied rows; output-substitution and traded-services rows arrive in Phase 7. Timings are provisional ranges for the reviewer, not results.")
    p = _write_csv(ap.approval_paths_frame(), out / "approval_paths.csv")
    statuses["applications/approval_paths"] = "FIXTURE (E)"
    write_provenance(root, "applications/approval_paths", p, source="spec v0.3 §A.3.4 approval baseline paths (E, V?)", source_url=spec_url, license="n/a (estimates)", status="FIXTURE (E: authors' estimates, spec v0.3)",
                     transformations=["J rises linearly from j0 at start_year to j_full at full_year per class and region; lever states frozen/baseline/accelerated/moratorium"],
                     notes="No dataset of future permits exists; the baseline path is a dated judgement to be replaced by transcribed regulatory timetables (verification item).")
    regions_dir = root / PROCESSED / "regions"
    occ_region = pl.read_csv(regions_dir / "occ_region.csv", schema_overrides={"occ_code": pl.Utf8, "region_id": pl.Utf8}) if (regions_dir / "occ_region.csv").exists() else None
    se, notes = ap.self_employed_frame(occ, None, occ_region)
    p = _write_csv(se, out / "self_employed.csv")
    statuses["applications/self_employed"] = "FIXTURE"
    write_provenance(root, "applications/self_employed", p, source="FIXTURE: CPS-based self-employment shares by SOC major group (E) with platform add-ons (E, V?)",
                     source_url="https://cps.ipums.org/cps/", license="n/a (fixture)", status="FIXTURE",
                     transformations=["heads = regional occupation employment × major-group self-employed share × regional multiplier (cap 0.6)",
                                      "platform add-on heads attached to 53-3054, 43-5021, 53-3033 (U.S.) scaled to other regions by employment ratio and a platform scale",
                                      "fte = heads × mean weekly hours / 40"],
                     notes=f"Replaced by ingest/cps_selfemp.py (IPUMS CPS class of worker, hours, multiple job holding) and Census Nonemployer Statistics. FTE by region: {notes['fte_by_region']}.",
                     extra=notes)
    log(f"applications/: {len(ap.EMBODIMENT_CLASSES)} classes, {len(ap.APPLICATIONS)} applications, self-employed FTE {notes['fte_by_region']}")
    return statuses


def build_regions(root: Path, occ: pl.DataFrame, log) -> dict[str, str]:
    """Write the seven ``data/processed/regions/`` tables, ``geo/world.geojson`` and provenance."""
    out = root / PROCESSED / "regions"
    ne = SOURCES["natural_earth_50m"]
    raw_ne = root / RAW_NE / NE_WORLD_50M
    if not raw_ne.exists():
        raise FileNotFoundError(f"{raw_ne} missing: fetch {ne.url.replace('/blob/', '/raw/')} (public domain)")
    src = json.loads(raw_ne.read_text(encoding="utf-8"))
    feats = [f for f in src["features"] if f["properties"]["ADM0_A3"] != "ATA"]
    statuses: dict[str, str] = {}
    vintage = "Natural Earth POP_EST / GDP_MD are mostly 2019 estimates (pop_year / gdp_year columns)."

    # region_members.csv
    members = rg.region_members(feats)
    p = _write_csv(members, out / "region_members.csv")
    statuses["regions/region_members"] = "real"
    by_region = {k: int(v) for k, v in members.group_by("region_id").len().sort("region_id").iter_rows()}
    write_provenance(
        root, "regions/region_members", p, source=f"{ne.name} ({NE_WORLD_50M})", source_url=ne.url,
        license=ne.license, status="real",
        transformations=[
            "one row per admin-0 feature (ADM0_A3 = iso3), Antarctica dropped",
            "population = POP_EST; gdp_bn_usd = GDP_MD / 1000",
            ("region_id: USA->US; EU-27 members->EU; GBR->UK; CHN, HKG, MAC->CN; JPN->JP; KOR->KR; IND->IN; "
             "TWN->TW; SGP->SG; CONTINENT 'Asia' minus SUBREGION 'Western Asia'/'Central Asia' and Iran->RoA; "
             "else '' (aiwsim.data.regions.assign_region)"),
        ],
        notes=f"{vintage} Members per region: {by_region}.",
        extra={"members_per_region": by_region, "extra_urls": list(ne.extra_urls)},
    )
    log(f"regions/region_members.csv: {members.height} countries; per region {by_region}")

    # regions.csv
    o = occ.select(pl.col("emp_national").cast(pl.Float64), pl.col("baseline_growth_10y").cast(pl.Float64))
    us_growth = float((o["emp_national"] * o["baseline_growth_10y"]).sum() / o["emp_national"].sum())
    regions = rg.regions_frame(members, us_growth)
    p = _write_csv(regions, out / "regions.csv")
    statuses["regions/regions"] = "partial (Natural Earth pop/GDP real; other columns E)"
    write_provenance(
        root, "regions/regions", p,
        source="Natural Earth admin-0 (population, GDP) aggregated over region_members.csv; other columns are the "
               "constant tables in aiwsim.data.regions",
        source_url=ne.url, license=f"{ne.license} (Natural Earth); n/a (estimates)",
        status="partial (Natural Earth pop/GDP real; other columns E)",
        transformations=[
            "population, gdp_bn_usd = sums over members",
            "employment_total = round(population x EMP_TO_POP_RATIO) (employment / total population, ~2024, E)",
            "emp_growth_10y US = employment-weighted mean of occupations.csv baseline_growth_10y (EP 2020-30)",
            "remaining columns transcribed from the constant tables; per-column tags in extra.column_tags",
        ],
        notes=f"{vintage} EMP_TO_POP_RATIO is employment over TOTAL population, not the 15+/16+ headline ratio. "
              "import_share is replaced by ingest/oecd_tiva.py; epl_multiplier is an approximate reading of OECD EPL "
              "strictness ratios (D); regime and avail_delay_quarters follow spec §8.2 / P.30.",
        extra={"column_tags": rg.REGION_COLUMN_TAGS, "emp_to_pop_ratio": rg.EMP_TO_POP_RATIO,
               "us_emp_growth_10y": round(us_growth, 4)},
    )
    log(f"regions/regions.csv: {regions.height} regions; employment_total "
        + ", ".join(f"{r} {e/1e6:.0f}M" for r, e in zip(regions["region_id"], regions["employment_total"])))

    # occ_region.csv (FIXTURE)
    occ_region, tilt_notes = rg.occ_region_frame(occ, regions)
    p = _write_csv(occ_region, out / "occ_region.csv")
    statuses["regions/occ_region"] = "FIXTURE"
    write_provenance(
        root, "regions/occ_region", p,
        source="U.S. occupational mix (occupations.csv, OEWS May 2021) tilted by GDP per capita; regions.csv",
        source_url="docs/contracts.md", license="n/a (fixture); underlying OEWS public domain", status="FIXTURE",
        transformations=[
            (f"U.S. employment shares x (gdp_pc/gdp_pc_US)^(+{rg.TILT_EXPONENT}) for major groups "
             f"{sorted(rg.TILT_UP_GROUPS)} and ^(-{rg.TILT_EXPONENT}) for {sorted(rg.TILT_DOWN_GROUPS)}, "
             "unchanged elsewhere; renormalised"),
            "emp = largest-remainder integer allocation of employment_total (sums exactly)",
            "wage_mean_annual_usd = U.S. wage_mean_annual x wage_level_rel_us",
        ],
        notes="STRUCTURAL PROXY, not observed: every region carries the U.S. within-group mix. The U.S. rows equal "
              "the OEWS mix scaled to employment_total (which exceeds the OEWS wage-and-salary total); the U.S. "
              "model keeps occupations.csv / occ_state.csv. Replaced by ingest/ilostat.py and ingest/eurostat_lfs.py "
              f"through the ISCO->SOC crosswalk chain. Tilt by region (gdp_pc ratio, high-skill share): {tilt_notes}.",
        extra={"tilt_exponent": rg.TILT_EXPONENT, "tilt": tilt_notes},
    )
    log(f"regions/occ_region.csv: {occ_region.height} rows (FIXTURE)")

    # trade_weights.csv (FIXTURE)
    tw = rg.trade_weights_frame(regions)
    p = _write_csv(tw, out / "trade_weights.csv")
    statuses["regions/trade_weights"] = "FIXTURE"
    write_provenance(
        root, "regions/trade_weights", p, source="regions.csv import_share and GDP", source_url="docs/contracts.md",
        license="n/a (fixture)", status="FIXTURE",
        transformations=["weight(to, to) = 1 - import_share",
                         "weight(from, to) = import_share x gdp_from / sum of GDP over the other nine regions"],
        notes="Rest of the world is not a source region, so the import share is fully attributed to the nine "
              "modelled partners. Replaced by ingest/oecd_tiva.py.",
    )

    # actors.csv
    actors = ac.actors_frame()
    p = _write_csv(actors, out / "actors.csv")
    statuses["regions/actors"] = "partial (public facts; E lags/availability; prices S verify at ingest)"
    vp, rh = SOURCES["vendor_pricing"], SOURCES["release_history"]
    null_price = actors.filter(pl.col("price_frontier_usd_per_mtok").is_null())["actor_id"].to_list()
    write_provenance(
        root, "regions/actors", p, source="spec §3.1 actor list; public facts (region, role, weights posture); "
        f"{vp.name}", source_url=vp.url, license=vp.license,
        status="partial (public facts; E lags/availability; prices S verify at ingest)",
        transformations=[
            "frontier_lag_quarters, releases_per_year: E per contracts §11 build notes",
            "price_frontier_usd_per_mtok = (3 x input + output) / 4 of the vendor list price named in price_note",
            "avail_<region>: rule per actor (availability_rule column) in aiwsim.data.actors.availability",
        ],
        notes="Prices were transcribed from memory (no web access); each carries its date and 'verify at ingest'. "
              f"Actors with null price: {null_price}. Microsoft and Amazon are labs with a cloud note; NVIDIA is "
              "compute; TSMC and ASML are chokepoints with export-control availability in CN (E). "
              f"Replaced by ingest/epoch_models.py ({rh.url}).",
        extra={"null_price_actors": null_price, "extra_urls": list(vp.extra_urls)},
    )
    log(f"regions/actors.csv: {actors.height} actors ({len(null_price)} without a list price)")

    # actor_releases.csv
    rel = ac.releases_frame(series.metr_horizons())
    p = _write_csv(rel, out / "actor_releases.csv")
    statuses["regions/actor_releases"] = "real (transcribed; verify at ingest)"
    write_provenance(
        root, "regions/actor_releases", p, source=rh.name, source_url=rh.url, license=rh.license,
        status="real (transcribed; verify at ingest)",
        transformations=["release dates transcribed from public announcements (day precision unless noted)",
                         "capability_index = log2(METR 50% horizon minutes) for models in series/metr_horizons.csv",
                         "open_weights = 1 where weights were published at release"],
        notes="Only releases whose dates the author is confident of; fewer, correct rows over coverage. "
              "Replaced by ingest/epoch_models.py (Epoch Notable AI Models, with ECI).",
        extra={"n_with_capability_index": int(rel["capability_index"].is_not_null().sum())},
    )
    log(f"regions/actor_releases.csv: {rel.height} releases")

    # value_chain.csv
    vc = rg.value_chain_frame()
    p = _write_csv(vc, out / "value_chain.csv")
    statuses["regions/value_chain"] = "partial (D, public gross margins, approximate)"
    sm = SOURCES["sec_margins"]
    write_provenance(
        root, "regions/value_chain", p, source=f"spec §6.3 table (P.85) from {sm.name}", source_url=sm.url,
        license=sm.license, status="partial (D, public gross margins, approximate)",
        transformations=["stage shares model 0.25 / compute 0.35 / chips 0.25 / integration 0.15 as in spec §6.3",
                         "chips fixed split US 0.55 (design), TW 0.35 (fab), EU 0.10 (ASML), KR 0 (memory not split out)"],
        notes="Shares are the spec's central values derived from public gross margins (D); not fitted here.",
    )

    # geo/world.geojson
    region_of = {iso3: rid for iso3, rid in zip(members["iso3"], members["region_id"])}
    gj = build_world(raw_ne, region_of)
    p = root / PROCESSED / "geo" / "world.geojson"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
    size_mb = p.stat().st_size / 1e6
    if size_mb > 3.0:
        raise ValueError(f"geo/world.geojson is {size_mb:.2f} MB (> 3 MB); simplify (drop small islands or use 110m)")
    statuses["geo/world"] = "real"
    write_provenance(
        root, "geo/world", p, source=f"{ne.name} ({NE_WORLD_50M})", source_url=ne.url, license=ne.license, status="real",
        transformations=["Antarctica (ATA) dropped", "properties reduced to {iso3 (= ADM0_A3), name, region_id}",
                         "features sorted by iso3; geometry unchanged (1:50m)"],
        notes=f"{len(gj['features'])} features, {size_mb:.2f} MB. 1:50m used because Singapore is absent at 1:110m "
              "(contracts §13 says 110m; deviation recorded here).",
        extra={"extra_urls": list(ne.extra_urls)},
    )
    log(f"geo/world.geojson: {len(gj['features'])} features, {size_mb:.2f} MB")
    return statuses


def build_cohorts(root: Path, raw: dict[str, pl.DataFrame], occ: pl.DataFrame, commit: str, log) -> dict[str, str]:
    """Write the four ``data/processed/cohorts/`` tables and their provenance; returns statuses."""
    out = root / PROCESSED / "cohorts"
    el, oews_src, onet_src, cps = SOURCES["eloundou"], SOURCES["bls_oews"], SOURCES["onet"], SOURCES["cps_ipums"]
    decile_tag = "partial:OEWS_May2021_lognormal;D"
    education_tag = "partial:ONET_JobZone_mapping;E"
    tabs = co.build_cohort_tables(raw["oews"], raw["basic_skills"], raw["matched"], occ, decile_tag=decile_tag,
                                  education_tag=education_tag, age_tag=fx.FIXTURE_TAG)
    n = tabs["notes"]
    statuses: dict[str, str] = {}
    vintage = ("VINTAGE: OEWS May 2021 (GPTs-are-GPTs mirror), not May 2025; refreshed when ingest/oews.py "
               "replaces the raw file.")
    replaced = "Replaced by aiwsim.data.ingest.cps_asec (IPUMS CPS ASEC, five pooled years) with status real."

    p = _write_csv(tabs["national_deciles"], out / "national_deciles.csv")
    statuses["cohorts/national_deciles"] = "partial (derived D)"
    write_provenance(
        root, "cohorts/national_deciles", p,
        source="OEWS May 2021 national 'All Occupations' row 00-0000 (national_May2021_dl.csv, GPTs-are-GPTs mirror)",
        source_url=el.url, license=f"MIT (repo mirror); underlying BLS data public domain ({oews_src.url})",
        commit=commit, status="partial (derived D)",
        transformations=[
            ("lognormal fitted by least squares of ln(annual wage) on the normal quantiles of 0.10/0.25/0.50/0.75/"
             "0.90 through A_PCT10, A_PCT25, A_MEDIAN, A_PCT75, A_PCT90"),
            "lower_bound_annual(decile k) = exp(mu + sigma * z_{(k-1)/10}) for k = 2..10; decile 1 lower bound 0",
        ],
        notes=f"{vintage} Fit: mu={n['national_fit']['mu']:.4f}, sigma={n['national_fit']['sigma']:.4f}. OEWS "
              "covers wage and salary workers only (no self-employed); the cutpoints are a lognormal "
              "approximation of the OEWS wage distribution, not CPS individual-earnings deciles.",
        extra={"fit": n["national_fit"]},
    )

    p = _write_csv(tabs["occ_decile"], out / "occ_decile.csv")
    statuses["cohorts/occ_decile"] = "partial (derived D)"
    write_provenance(
        root, "cohorts/occ_decile", p,
        source="OEWS May 2021 national detailed occupation percentiles (national_May2021_dl.csv, GPTs-are-GPTs mirror)",
        source_url=el.url, license=f"MIT (repo mirror); underlying BLS data public domain ({oews_src.url})",
        commit=commit, status="partial (derived D)",
        transformations=[
            ("per occupation, lognormal (mu, sigma) by least squares of ln(annual wage) on normal quantiles through "
             "the usable A_PCT10/A_PCT25/A_MEDIAN/A_PCT75/A_PCT90; '#' (>= $208,000 top code) and '*' treated as "
             "missing as in occupations.csv"),
            (f"fewer than {co.MIN_POINTS_OWN_FIT} usable percentiles: own mu with the major group's sigma "
             "(fit_level major_sigma); none: major group's mu and sigma (fit_level major); the major-group "
             "parameters are fitted the same way through the OEWS 'major' rows"),
            "share(decile k) = lognormal mass between the national cutpoints of cohorts/national_deciles.csv",
        ],
        notes=f"{vintage} Fit levels: {n['decile_fit_levels']}. Treating '#' as missing understates dispersion "
              "for top-coded occupations. Employment-weighted share per decile (should be ~0.1 each; OEWS excludes "
              f"the self-employed and the lognormal is an approximation): {n['decile_employment_weighted_check']}.",
        extra={"fit_levels": n["decile_fit_levels"],
               "employment_weighted_decile_shares": n["decile_employment_weighted_check"]},
    )
    log(f"cohorts/occ_decile.csv: {tabs['occ_decile'].height} rows; emp-weighted decile shares "
        f"{n['decile_employment_weighted_check']}")

    jz_note = (f"O*NET titles matched to OEWS codes through occupations_onet_bls_matched.csv; unmatched "
               f"occupations ({n['job_zone_unmatched']['count']}) take the employment-weighted major-group Job Zone "
               f"mix (jz_imputed). Job Zone mix over occupations (unweighted): {n['job_zone_distribution_unweighted']}.")
    p = _write_csv(tabs["occ_education"], out / "occ_education.csv")
    statuses["cohorts/occ_education"] = "partial (estimated E)"
    write_provenance(
        root, "cohorts/occ_education", p,
        source="O*NET Job Zone per occupation (occupations_onet_basic_skills.csv, GPTs-are-GPTs mirror) through the "
               "JOB_ZONE_EDUCATION mapping of aiwsim.data.cohorts",
        source_url=el.url, license=f"MIT (repo mirror); underlying O*NET data CC BY 4.0 ({onet_src.url})",
        commit=commit, status="partial (estimated E)",
        transformations=[
            "Job Zone -> education mix rows (lt_hs, hs, some_college, ba_plus): " + "; ".join(
                f"JZ{z}: {'/'.join(f'{x:.2f}' for x in row)}" for z, row in co.JOB_ZONE_EDUCATION.items()),
            "an OEWS code carrying several O*NET titles takes the equal-weight mixture of their Job Zone rows",
        ],
        notes=f"MAPPING MATRIX IS AN ESTIMATE (E), not fitted to microdata. {jz_note} Employment-weighted "
              f"education shares: {n['education_employment_weighted']}. {replaced}",
        extra={"job_zone_unmatched": n["job_zone_unmatched"],
               "education_employment_weighted": n["education_employment_weighted"],
               "job_zone_education": {str(k): list(v) for k, v in co.JOB_ZONE_EDUCATION.items()}},
    )
    log(f"cohorts/occ_education.csv: {tabs['occ_education'].height} rows; emp-weighted "
        f"{n['education_employment_weighted']}")

    p = _write_csv(tabs["occ_age"], out / "occ_age.csv")
    statuses["cohorts/occ_age"] = "FIXTURE"
    write_provenance(
        root, "cohorts/occ_age", p,
        source="national employed age distribution (approximate CPS 2024, E) tilted by O*NET Job Zone "
               "(occupations_onet_basic_skills.csv, GPTs-are-GPTs mirror)",
        source_url=cps.url, license=f"n/a (fixture); O*NET data CC BY 4.0 ({onet_src.url})",
        commit=commit, status="FIXTURE",
        transformations=[
            "national bands " + ", ".join(f"{b} {s:.3f}" for b, s in co.AGE_NATIONAL.items()),
            "16-24 share multiplied by the Job Zone tilt " + ", ".join(
                f"JZ{z} {t}" for z, t in co.JZ_TILT_16_24.items()) + ", then renormalised",
            "an OEWS code carrying several O*NET titles takes the equal-weight mixture of their Job Zone rows",
        ],
        notes=f"FIXTURE: the national vector is approximate (transcribed, not fetched) and the tilt is a guess. "
              f"{replaced} {jz_note} Employment-weighted age shares: {n['age_employment_weighted']}.",
        extra={"job_zone_unmatched": n["job_zone_unmatched"],
               "age_employment_weighted": n["age_employment_weighted"]},
    )
    log(f"cohorts/occ_age.csv: {tabs['occ_age'].height} rows (FIXTURE)")
    return statuses


def status(root: Path | str) -> dict[str, str]:
    """Print provenance status per table; returns {table: status}."""
    root = Path(root).resolve()
    recs = list_provenance(root)
    out: dict[str, str] = {}
    print(f"{'table':28s} {'status':44s} {'pulled_at':11s} sha256")
    for table in TABLES:
        rec = recs.get(table)
        if rec is None:
            print(f"{table:28s} {'MISSING':44s}")
            out[table] = "MISSING"
            continue
        out[table] = rec.status
        print(f"{table:28s} {rec.status:44s} {rec.pulled_at:11s} {rec.sha256[:12]}")
    extra = sorted(set(recs) - set(TABLES))
    for table in extra:
        rec = recs[table]
        out[table] = rec.status
        print(f"{table:28s} {rec.status:44s} {rec.pulled_at:11s} {rec.sha256[:12]}  (extra)")
    kinds = {}
    for s in out.values():
        kinds[status_kind(s) if s != "MISSING" else "MISSING"] = kinds.get(status_kind(s) if s != "MISSING" else "MISSING", 0) + 1
    print("summary:", ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    return out


if __name__ == "__main__":
    import sys

    r = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    build_all(r)
    status(r)

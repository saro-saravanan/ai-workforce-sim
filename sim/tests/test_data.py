"""Data-layer contract tests (contracts §1, §4).  Runs ``build_all`` once, then checks the outputs."""

from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path

import polars as pl
import pytest
from aiwsim.data.build import TABLES, build_all
from aiwsim.data.classify import MODALITIES, USE_CASES
from aiwsim.data.provenance import STATUS_VALUES, list_provenance, status_kind
from aiwsim.data.registry import load_registry

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

# (table, file, key columns)
KEYS = {
    "occupations": ("occupations.csv", ["occ_code"]),
    "tasks": ("tasks.csv", ["task_id"]),
    "sectors": ("sectors.csv", ["sector_code"]),
    "occ_sector": ("occ_sector.csv", ["occ_code", "sector_code"]),
    "states": ("states.csv", ["fips"]),
    "occ_state": ("occ_state.csv", ["occ_code", "fips"]),
    # period_end alone is not unique: the Nov 2025-Jan 2026 pooled reading is given firm- and employment-weighted
    "series/btos": ("series/btos.csv", ["period_end", "wording", "weighting"]),
    "series/metr_horizons": ("series/metr_horizons.csv", ["model"]),
    # Microsoft appears on fiscal and calendar bases (documented deviation from contracts §1)
    "series/capex": ("series/capex.csv", ["company", "year", "basis"]),
    "series/regulatory_events": ("series/regulatory_events.csv", ["event_id"]),
}


@pytest.fixture(scope="module")
def built() -> dict[str, str]:
    return build_all(ROOT, verbose=False)


def _read(name: str) -> pl.DataFrame:
    return pl.read_csv(PROCESSED / name, infer_schema_length=0)


def test_every_table_exists(built):
    for table in TABLES:
        ext = ".yaml" if table.startswith("params/") else ".geojson" if table.startswith("geo/") else ".csv"
        assert (PROCESSED / f"{table}{ext}").exists(), table
        assert table in built


def test_keys_unique(built):
    for table, (fname, keys) in KEYS.items():
        df = _read(fname)
        assert set(keys) <= set(df.columns), (table, keys)
        assert df.select(keys).n_unique() == df.height, f"{table}: duplicate keys {keys}"
        assert df.select(pl.col(keys).is_null().any()).to_numpy().sum() == 0, f"{table}: null keys"


def test_task_weights_sum_to_one(built):
    t = _read("tasks.csv").with_columns(pl.col("weight").cast(pl.Float64))
    s = t.group_by("occ_code").agg(pl.col("weight").sum())
    assert ((s["weight"] - 1.0).abs() < 1e-6).all()
    assert t["weight"].min() > 0


def test_tasks_reference_occupations(built):
    t, o = _read("tasks.csv"), _read("occupations.csv")
    assert set(t["occ_code"]) <= set(o["occ_code"])
    assert set(t["exposure_label"]) <= {"E0", "E1", "E2"}
    b = t["beta"].cast(pl.Float64)
    assert b.min() >= 0 and b.max() <= 1


def test_occ_sector_shares_sum_to_one(built):
    s = _read("occ_sector.csv").with_columns(pl.col("emp_share").cast(pl.Float64))
    o = _read("occupations.csv")
    g = s.group_by("occ_code").agg(pl.col("emp_share").sum())
    assert ((g["emp_share"] - 1.0).abs() < 1e-6).all()
    assert set(g["occ_code"]) == set(o["occ_code"])
    assert set(s["sector_code"]) <= set(_read("sectors.csv")["sector_code"])


def test_occ_state_sums_to_national(built):
    st = _read("occ_state.csv").with_columns(pl.col("emp").cast(pl.Int64))
    o = _read("occupations.csv").with_columns(pl.col("emp_national").cast(pl.Int64))
    g = st.group_by("occ_code").agg(pl.col("emp").sum().alias("emp"))
    j = o.join(g, on="occ_code", how="left")
    assert j["emp"].null_count() == 0
    assert ((j["emp"] - j["emp_national"]).abs() <= 51).all()  # within rounding (one head per state)
    states = _read("states.csv").with_columns(pl.col("emp_total").cast(pl.Int64))
    assert set(st["fips"]) == set(states["fips"]) and states.height == 51
    tot = st.group_by("fips").agg(pl.col("emp").sum().alias("t")).join(states, on="fips")
    assert (tot["t"] == tot["emp_total"]).all()
    assert all(len(f) == 2 for f in states["fips"])


def test_occupations_columns_and_clusters(built):
    o = _read("occupations.csv")
    need = ["occ_code", "title", "major_group", "cluster_id", "cluster_title", "emp_national", "wage_mean_annual",
            "wage_p10_annual", "wage_median_annual", "baseline_growth_10y", "source_tag"]
    assert set(need) <= set(o.columns)
    for c in ["emp_national", "wage_mean_annual", "wage_p10_annual", "wage_median_annual", "baseline_growth_10y",
              "cluster_id"]:
        assert o[c].null_count() == 0, c
    assert (o["major_group"] == o["occ_code"].str.slice(0, 2)).all()
    # clusters never cross major groups; ids are dense c001..cNNN
    k = o.group_by("cluster_id").agg(pl.col("major_group").n_unique().alias("k"))
    assert k["k"].max() == 1
    n = o["cluster_id"].n_unique()
    assert set(o["cluster_id"]) == {f"c{i:03d}" for i in range(1, n + 1)}
    big = o.with_columns(pl.col("emp_national").cast(pl.Int64)).filter(pl.col("emp_national") >= 300_000)
    sizes = o.group_by("cluster_id").len()
    assert big.join(sizes, on="cluster_id")["len"].max() == 1  # anchors stay singletons


def test_registry_loads_with_unique_ids_and_ordered_ranges(built):
    doc = load_registry(PROCESSED / "params" / "registry.yaml")
    ids = [p["id"] for p in doc["parameters"]]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("P.") for i in ids)
    for p in doc["parameters"]:
        assert {"id", "name", "central", "min", "max", "unit", "tag", "source"} <= set(p)
        assert p["tag_primary"] in ("S", "D", "E")
        rows = [p] + list(p.get("by", {}).values())
        for r in rows:
            c, lo, hi = r.get("central"), r.get("min"), r.get("max")
            if all(isinstance(x, (int, float)) for x in (c, lo, hi)):
                assert lo <= c <= hi, (p["id"], r)


def test_every_processed_table_has_provenance(built):
    recs = list_provenance(ROOT)
    for table in set(TABLES) | set(built):
        assert table in recs, f"no provenance for {table}"
        rec = recs[table]
        assert status_kind(rec.status) in STATUS_VALUES
        assert rec.sha256 and rec.source_url and rec.license and rec.transformations
        ext = ".yaml" if table.startswith("params/") else ".geojson" if table.startswith("geo/") else ".csv"
        assert rec.output.endswith(f"{table}{ext}"), (table, rec.output)


def test_classifier_columns_take_allowed_values(built):
    t = _read("tasks.csv")
    assert set(t["modality"]) <= set(MODALITIES)
    assert set(t["use_case"]) <= set(USE_CASES)
    assert set(t["consequence_high"]) <= {"0", "1"}
    p = t["presence"].cast(pl.Float64)
    assert p.min() >= 0 and p.max() <= 1 and p.null_count() == 0
    # each class actually occurs
    assert set(t["modality"]) == set(MODALITIES) and set(t["use_case"]) == set(USE_CASES)


def test_sectors_fixture(built):
    s = _read("sectors.csv")
    assert s.height == 1 and s["sector_code"][0] == "ALL"
    assert float(s["labor_cost_share"][0]) == 0.58 and float(s["demand_elasticity"][0]) == 0.8
    s20 = pl.read_csv(ROOT / "data" / "fixtures" / "sectors_20.csv", infer_schema_length=0)
    assert s20.height == 20 and s20["sector_code"].n_unique() == 20


def test_geo_us_states(built):
    gj = json.loads((PROCESSED / "geo" / "us_states.geojson").read_text())
    assert len(gj["features"]) == 51
    fips = {f["properties"]["fips"] for f in gj["features"]}
    assert fips == set(_read("states.csv")["fips"])
    for f in gj["features"]:
        assert set(f["properties"]) == {"fips", "name", "abbrev"}


def test_series_columns(built):
    assert {"period_end", "share_using_ai", "wording", "weighting", "source_tag"} <= set(_read("series/btos.csv").columns)
    assert {"model", "date", "horizon_minutes_p50", "ci_low_minutes", "ci_high_minutes", "source_tag"} <= set(
        _read("series/metr_horizons.csv").columns)
    assert {"company", "year", "capex_bn_usd", "basis", "source_tag"} <= set(_read("series/capex.csv").columns)
    assert {"event_id", "region", "date", "kind", "description", "source_tag"} <= set(
        _read("series/regulatory_events.csv").columns)


# ---- Phase 2 cohort tables (contracts §7) ---------------------------------------------------------
COHORT_TABLES = {
    "cohorts/occ_decile": ("decile", [str(k) for k in range(1, 11)]),
    "cohorts/occ_education": ("education", ["lt_hs", "hs", "some_college", "ba_plus"]),
    "cohorts/occ_age": ("age_band", ["16-24", "25-44", "45-54", "55+"]),
}


def _cohort(table: str) -> pl.DataFrame:
    return _read(f"{table}.csv").with_columns(pl.col("share").cast(pl.Float64))


def test_cohort_tables_registered_and_have_provenance(built):
    recs = list_provenance(ROOT)
    for table in [*COHORT_TABLES, "cohorts/national_deciles"]:
        assert table in TABLES and table in built
        assert (PROCESSED / f"{table}.csv").exists()
        assert table in recs and status_kind(recs[table].status) in STATUS_VALUES
    assert status_kind(recs["cohorts/occ_age"].status) == "FIXTURE"
    assert "cps_asec" in recs["cohorts/occ_age"].notes


def test_cohort_shares_sum_to_one_and_cover_every_occupation(built):
    occ_codes = set(_read("occupations.csv")["occ_code"])
    for table, (col, levels) in COHORT_TABLES.items():
        df = _cohort(table)
        assert {"occ_code", col, "share", "source_tag"} <= set(df.columns), table
        assert set(df[col]) == set(levels), table
        assert df.select(["occ_code", col]).n_unique() == df.height, f"{table}: duplicate keys"
        assert df["share"].min() >= 0 and df["share"].max() <= 1, table
        g = df.group_by("occ_code").agg(pl.col("share").sum().alias("s"), pl.len().alias("n"))
        assert ((g["s"] - 1.0).abs() < 1e-6).all(), table
        assert (g["n"] == len(levels)).all(), table
        assert set(g["occ_code"]) == occ_codes, table


def test_national_decile_cutpoints_strictly_increasing(built):
    nd = _read("cohorts/national_deciles.csv").with_columns(
        pl.col("decile").cast(pl.Int64), pl.col("lower_bound_annual").cast(pl.Float64)).sort("decile")
    assert nd["decile"].to_list() == list(range(1, 11))
    lb = nd["lower_bound_annual"].to_list()
    assert lb[0] == 0.0
    assert all(b > a for a, b in pairwise(lb))
    # the OEWS all-occupations median ($45,760) lies in decile 5 or 6
    assert lb[4] < 45_760 < lb[6]


def test_occ_decile_employment_weighted_shares_near_ten_percent(built):
    d = _cohort("cohorts/occ_decile").join(
        _read("occupations.csv").select("occ_code", pl.col("emp_national").cast(pl.Float64)), on="occ_code")
    g = d.group_by("decile").agg((pl.col("share") * pl.col("emp_national")).sum() / pl.col("emp_national").sum())
    assert ((g["share"] - 0.1).abs() < 0.05).all(), g.sort("decile")["share"].to_list()
    assert abs(g["share"].sum() - 1.0) < 1e-6

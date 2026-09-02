"""Data-layer contract tests (contracts §1, §4).  Runs ``build_all`` once, then checks the outputs."""

from __future__ import annotations

import datetime as dt
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


# ---- Phase 3 regional tables (contracts §11) ------------------------------------------------------
REGION_IDS = ["US", "EU", "UK", "CN", "JP", "KR", "IN", "TW", "SG", "RoA"]
REGION_TABLES = ["regions/region_members", "regions/regions", "regions/occ_region", "regions/trade_weights",
                 "regions/actors", "regions/actor_releases", "regions/value_chain"]
EU27 = {"AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL", "ITA",
        "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE"}


def test_region_tables_registered_with_provenance(built):
    recs = list_provenance(ROOT)
    for table in [*REGION_TABLES, "geo/world"]:
        assert table in TABLES and table in built, table
        assert table in recs and status_kind(recs[table].status) in STATUS_VALUES, table
    assert status_kind(recs["regions/occ_region"].status) == "FIXTURE"
    assert status_kind(recs["regions/trade_weights"].status) == "FIXTURE"
    assert status_kind(recs["regions/region_members"].status) == "real"


def test_region_members_cover_the_world(built):
    m = _read("regions/region_members.csv")
    assert m.height >= 170 and m["iso3"].n_unique() == m.height
    reg = dict(zip(m["iso3"], m["region_id"]))
    assert all(reg[c] == "EU" for c in EU27)
    for iso3, rid in [("USA", "US"), ("GBR", "UK"), ("CHN", "CN"), ("JPN", "JP"), ("KOR", "KR"), ("IND", "IN"),
                      ("TWN", "TW"), ("SGP", "SG"), ("IDN", "RoA"), ("VNM", "RoA")]:
        assert reg[iso3] == rid, iso3
    assert reg["SAU"] == "" and reg["KAZ"] == "" and reg["BRA"] == "" and "ATA" not in reg
    assert set(m["region_id"]) == set(REGION_IDS) | {""}
    assert m["population"].cast(pl.Int64).min() >= 0 and m["gdp_bn_usd"].cast(pl.Float64).min() >= 0


def test_regions_table(built):
    r = _read("regions/regions.csv")
    assert r["region_id"].to_list() == REGION_IDS
    need = {"name", "population", "gdp_bn_usd", "employment_total", "wage_level_rel_us", "emp_growth_10y",
            "import_share", "epl_multiplier", "avail_delay_quarters", "frontier_lag_quarters",
            "compliance_premium_high_risk", "regime", "data_center_share", "spillover_weight_us", "source_tag"}
    assert need <= set(r.columns)
    assert set(r["regime"]) <= {"state_patchwork", "eu_ai_act", "licensing", "light"}
    m = _read("regions/region_members.csv").with_columns(pl.col("population").cast(pl.Int64))
    us_pop = m.filter(pl.col("iso3") == "USA")["population"][0]
    assert r.filter(pl.col("region_id") == "US")["population"].cast(pl.Int64)[0] == us_pop
    eu_pop = m.filter(pl.col("region_id") == "EU")["population"].sum()
    assert r.filter(pl.col("region_id") == "EU")["population"].cast(pl.Int64)[0] == eu_pop
    dc = r["data_center_share"].cast(pl.Float64).sum()
    assert abs(dc - 1.0) < 1e-6
    for c in ("import_share", "epl_multiplier", "spillover_weight_us", "compliance_premium_high_risk"):
        v = r[c].cast(pl.Float64)
        assert v.min() >= 0 and v.max() <= 1, c


def test_occ_region_covers_every_occupation_and_sums_to_employment_total(built):
    occ_codes = set(_read("occupations.csv")["occ_code"])
    o = _read("regions/occ_region.csv").with_columns(pl.col("emp").cast(pl.Int64),
                                                     pl.col("wage_mean_annual_usd").cast(pl.Float64))
    assert o.select(["occ_code", "region_id"]).n_unique() == o.height
    for rid in REGION_IDS:
        sub = o.filter(pl.col("region_id") == rid)
        assert set(sub["occ_code"]) == occ_codes and sub.height == 831, rid
    r = _read("regions/regions.csv").with_columns(pl.col("employment_total").cast(pl.Int64))
    tot = o.group_by("region_id").agg(pl.col("emp").sum().alias("s")).join(r, on="region_id")
    assert ((tot["s"] - tot["employment_total"]).abs() <= 1).all()
    assert o["emp"].min() >= 0 and o["wage_mean_annual_usd"].min() > 0
    # the tilt: India's professional share is below the U.S. share, its farm/production share above
    occ = _read("occupations.csv").select("occ_code", "major_group")
    j = o.join(occ, on="occ_code").with_columns(pl.col("major_group").is_in(["11", "13", "15", "17", "19", "21", "23",
                                                                              "25", "27", "29"]).alias("hi"))
    share = j.group_by("region_id").agg((pl.col("emp").filter(pl.col("hi")).sum() / pl.col("emp").sum()).alias("hi"))
    s = dict(zip(share["region_id"], share["hi"]))
    assert s["IN"] < s["US"] < s["SG"] or s["IN"] < s["US"]


def test_trade_weights_rows_sum_to_one(built):
    t = _read("regions/trade_weights.csv").with_columns(pl.col("weight").cast(pl.Float64))
    assert t.height == 100 and t.select(["region_from", "region_to"]).n_unique() == 100
    g = t.group_by("region_to").agg(pl.col("weight").sum())
    assert ((g["weight"] - 1.0).abs() < 1e-5).all()
    assert t["weight"].min() >= 0
    r = _read("regions/regions.csv").with_columns(pl.col("import_share").cast(pl.Float64))
    dom = t.filter(pl.col("region_from") == pl.col("region_to")).join(r, left_on="region_to", right_on="region_id")
    assert ((dom["weight"] - (1 - dom["import_share"])).abs() < 1e-5).all()


def test_actors_and_availability(built):
    a = _read("regions/actors.csv")
    assert a["actor_id"].n_unique() == a.height == 23
    assert set(a["role"]) == {"lab", "compute", "chokepoint"}
    assert set(a["weights_posture"]) <= {"closed", "open-lagged", "open-frontier"}
    assert set(a["region_id"]) <= set(REGION_IDS)
    for rid in REGION_IDS:
        v = a[f"avail_{rid}"].cast(pl.Float64)
        assert v.null_count() == 0 and v.min() >= 0 and v.max() <= 1, rid
    row = {r["actor_id"]: r for r in a.to_dicts()}
    assert float(row["openai"]["avail_CN"]) == 0.0 and float(row["openai"]["avail_EU"]) == 1.0
    assert float(row["deepseek"]["avail_US"]) == 0.5 and float(row["baidu"]["avail_EU"]) == 0.2
    assert row["nvidia"]["role"] == "compute" and row["tsmc"]["role"] == "chokepoint" and row["asml"]["role"] == "chokepoint"
    assert row["deepseek"]["weights_posture"] == "open-frontier" and row["meta"]["weights_posture"] == "open-lagged"
    prices = a["price_frontier_usd_per_mtok"].cast(pl.Float64, strict=False)
    assert prices.drop_nulls().min() > 0
    assert a["frontier_lag_quarters"].cast(pl.Int64).min() >= 0 and a["releases_per_year"].cast(pl.Int64).min() >= 1


def test_actor_releases_dates_parse_and_are_sorted(built):
    rel = _read("regions/actor_releases.csv")
    assert rel.select(["actor_id", "model"]).n_unique() == rel.height
    d = rel["date"].str.to_date("%Y-%m-%d")
    assert d.null_count() == 0
    assert d.to_list() == sorted(d.to_list())
    assert d.min() >= dt.date(2023, 3, 1) and d.max() <= dt.date(2026, 6, 30)
    assert set(rel["actor_id"]) <= set(_read("regions/actors.csv")["actor_id"])
    assert set(rel["open_weights"]) <= {"0", "1"}
    ci = rel["capability_index"].cast(pl.Float64, strict=False)
    metr = _read("series/metr_horizons.csv")
    assert ci.drop_nulls().len() == metr.height
    gpt5 = rel.filter(pl.col("model") == "GPT-5")["capability_index"].cast(pl.Float64)[0]
    assert abs(gpt5 - 7.1) < 0.05


def test_value_chain_shares(built):
    v = _read("regions/value_chain.csv").with_columns(pl.col("share_of_spend").cast(pl.Float64))
    assert v["stage"].to_list() == ["model", "compute", "chips", "integration"]
    assert abs(v["share_of_spend"].sum() - 1.0) < 1e-9
    assert set(v["allocation"]) == {"market_share", "data_center", "fixed", "domestic"}
    chips = v.filter(pl.col("stage") == "chips")
    fixed = sum(float(chips[c][0]) for c in ("fixed_US", "fixed_TW", "fixed_EU", "fixed_KR"))
    assert abs(fixed - 1.0) < 1e-9


def test_geo_world_matches_members(built):
    p = PROCESSED / "geo" / "world.geojson"
    assert p.stat().st_size <= 3_000_000
    gj = json.loads(p.read_text())
    m = _read("regions/region_members.csv")
    assert len(gj["features"]) == m.height
    reg = dict(zip(m["iso3"], m["region_id"]))
    for f in gj["features"]:
        pr = f["properties"]
        assert set(pr) == {"iso3", "name", "region_id"}
        assert reg[pr["iso3"]] == pr["region_id"]
    assert "ATA" not in reg

"""Phase 3 regional tables (contracts §11): ``regions.csv``, ``region_members.csv``,
``occ_region.csv``, ``trade_weights.csv`` and ``value_chain.csv``.

Population and GDP come from Natural Earth admin-0 (real, POP_EST / GDP_MD with their vintage
columns).  Everything else in ``regions.csv`` is a documented constant below, tagged per column in
``REGION_COLUMN_TAGS`` (E = estimate, D = derived from a public statistic, S = from the spec).
``occ_region.csv`` and ``trade_weights.csv`` are FIXTURE structural proxies replaced by the
ILOSTAT / Eurostat LFS and OECD TiVA ingests (``aiwsim.data.ingest``).
"""

from __future__ import annotations

import math

import polars as pl

from aiwsim.data.fixtures import FIXTURE_TAG, allocate_integer

REGION_IDS = ["US", "EU", "UK", "CN", "JP", "KR", "IN", "TW", "SG", "RoA"]
REGION_NAMES = {
    "US": "United States", "EU": "European Union (EU-27)", "UK": "United Kingdom", "CN": "China",
    "JP": "Japan", "KR": "South Korea", "IN": "India", "TW": "Taiwan", "SG": "Singapore",
    "RoA": "Rest of Asia",
}

# EU-27 member states (ISO 3166-1 alpha-3 = Natural Earth ADM0_A3).
EU27 = frozenset({
    "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL",
    "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE",
})
# Single-country regions.  Hong Kong and Macao are separate Natural Earth features; they are
# mapped to CN (PRC regulatory perimeter for AI services and U.S. export controls treat them as
# China) rather than falling through to RoA.
COUNTRY_TO_REGION = {
    "USA": "US", "GBR": "UK", "CHN": "CN", "HKG": "CN", "MAC": "CN", "JPN": "JP", "KOR": "KR",
    "IND": "IN", "TWN": "TW", "SGP": "SG",
}
# Rest of Asia = CONTINENT "Asia" minus the Middle East (Natural Earth SUBREGION "Western Asia")
# and Central Asia (and the "Seven seas" subregion, i.e. the Australian Indian Ocean Territories).
# Natural Earth files Iran under "Southern Asia"; it is excluded explicitly as Middle East
# (sanctioned; no frontier-lab availability), which is what the region is meant to capture.
ROA_EXCLUDED_SUBREGIONS = frozenset({"Western Asia", "Central Asia", "Seven seas (open ocean)"})
ROA_EXCLUDED_ISO3 = frozenset({"IRN"})


def assign_region(iso3: str, continent: str, subregion: str) -> str:
    """Region id for a Natural Earth admin-0 feature, or ``""`` when outside the ten regions."""
    if iso3 in COUNTRY_TO_REGION:
        return COUNTRY_TO_REGION[iso3]
    if iso3 in EU27:  # takes precedence over the Asia rule (Cyprus is 'Western Asia' in Natural Earth)
        return "EU"
    if continent == "Asia" and subregion not in ROA_EXCLUDED_SUBREGIONS and iso3 not in ROA_EXCLUDED_ISO3:
        return "RoA"
    return ""


MEMBERS_TAG = "real:natural_earth_admin0_50m"


def region_members(features: list[dict]) -> pl.DataFrame:
    """``region_members.csv`` from Natural Earth admin-0 features (Antarctica dropped by the caller)."""
    rows = []
    for f in features:
        p = f["properties"]
        iso3 = p["ADM0_A3"]
        rows.append({
            "iso3": iso3,
            "region_id": assign_region(iso3, p.get("CONTINENT", ""), p.get("SUBREGION", "")),
            "name": p["NAME"],
            # Natural Earth uses -99 for "unknown"; clamp to 0 (only uninhabited / unmodelled features)
            "population": max(int(p["POP_EST"] or 0), 0),
            "gdp_bn_usd": max(float(p["GDP_MD"] or 0), 0.0) / 1000.0,
            "source_tag": MEMBERS_TAG,
            "continent": p.get("CONTINENT", ""),
            "subregion": p.get("SUBREGION", ""),
            "pop_year": int(p["POP_YEAR"] or 0),
            "gdp_year": int(p["GDP_YEAR"] or 0),
        })
    return pl.DataFrame(rows).sort("iso3")


# ------------------------------------------------------------------------------------------------
# regions.csv constants (all E unless stated; see REGION_COLUMN_TAGS)
# ------------------------------------------------------------------------------------------------
# employment_total = population x EMP_TO_POP_RATIO.  Natural Earth POP_EST is TOTAL population,
# so the ratio is employment / total population (approximate 2024: ILO modelled estimates and
# national LFS), NOT the headline employment-to-population ratio of the 15+/16+ population
# (U.S. ~0.60, Japan ~0.62, ...) which would overstate employment by 20-30%.  Singapore's total
# employment includes non-resident work-permit holders.  E, believed within ~10%.
EMP_TO_POP_RATIO = {
    "US": 0.48, "EU": 0.44, "UK": 0.49, "CN": 0.52, "JP": 0.55, "KR": 0.55, "IN": 0.41, "TW": 0.50,
    "SG": 0.65, "RoA": 0.45,
}
# Mean wage relative to the U.S. at market exchange rates (E).
WAGE_LEVEL_REL_US = {
    "US": 1.0, "EU": 0.75, "UK": 0.8, "CN": 0.25, "JP": 0.65, "KR": 0.6, "IN": 0.08, "TW": 0.5,
    "SG": 0.9, "RoA": 0.15,
}
# Baseline 10-year employment growth (E); US is derived from occupations.csv (employment-weighted
# mean of baseline_growth_10y) at build time.
EMP_GROWTH_10Y = {
    "EU": 0.02, "UK": 0.03, "CN": -0.03, "JP": -0.05, "KR": -0.02, "IN": 0.12, "TW": -0.02, "SG": 0.05,
    "RoA": 0.10,
}
# Share of tradable demand met by imports (E; EU is extra-EU).  Replaced by OECD TiVA.
IMPORT_SHARE = {
    "US": 0.15, "EU": 0.20, "UK": 0.30, "CN": 0.15, "JP": 0.18, "KR": 0.35, "IN": 0.20, "TW": 0.45,
    "SG": 0.60, "RoA": 0.30,
}
# Layoff-friction multiplier (D from OECD EPL strictness ratios, approximate; U.S. = 1).
EPL_MULTIPLIER = {
    "US": 1.0, "EU": 0.5, "UK": 0.8, "CN": 0.7, "JP": 0.6, "KR": 0.7, "IN": 0.6, "TW": 0.8, "SG": 0.9,
    "RoA": 0.8,
}
# delta^reg (spec §3.3, P.30): availability delay for closed frontier models, quarters (S/E).
AVAIL_DELAY_QUARTERS = {
    "US": 0, "EU": 1, "UK": 0, "CN": 4, "JP": 0, "KR": 0, "IN": 0, "TW": 0, "SG": 0, "RoA": 1,
}
# Domestic-actor lag when the foreign frontier is unavailable (CN: DeepSeek/Qwen behind the U.S.
# frontier by ~4 quarters under export controls; 0 elsewhere because the U.S. frontier is available).
FRONTIER_LAG_QUARTERS = {
    "US": 0, "EU": 0, "UK": 0, "CN": 4, "JP": 0, "KR": 0, "IN": 0, "TW": 0, "SG": 0, "RoA": 0,
}
# Compliance premium on high-risk use cases as a share of task cost (spec P.31, E).
COMPLIANCE_PREMIUM_HIGH_RISK = {
    "US": 0.03, "EU": 0.10, "UK": 0.03, "CN": 0.05, "JP": 0.02, "KR": 0.02, "IN": 0.02, "TW": 0.02,
    "SG": 0.02, "RoA": 0.02,
}
REGIME = {
    "US": "state_patchwork", "EU": "eu_ai_act", "UK": "light", "CN": "licensing", "JP": "light",
    "KR": "light", "IN": "light", "TW": "light", "SG": "light", "RoA": "light",
}
# Share of global inference capacity located in the region (E; sums to 1).
DATA_CENTER_SHARE = {
    "US": 0.55, "EU": 0.12, "UK": 0.04, "CN": 0.15, "JP": 0.05, "KR": 0.02, "IN": 0.03, "TW": 0.01,
    "SG": 0.02, "RoA": 0.01,
}
# Adoption spillover weight from the U.S. (E).
SPILLOVER_WEIGHT_US = {
    "US": 0.0, "EU": 0.5, "UK": 0.7, "CN": 0.2, "JP": 0.4, "KR": 0.5, "IN": 0.4, "TW": 0.5, "SG": 0.6,
    "RoA": 0.3,
}
REGION_COLUMN_TAGS = {
    "population": "real (Natural Earth POP_EST, summed over members)",
    "gdp_bn_usd": "real (Natural Earth GDP_MD / 1000, summed over members)",
    "employment_total": "E (population x EMP_TO_POP_RATIO, employment / total population, ~2024)",
    "wage_level_rel_us": "E",
    "emp_growth_10y": "E (US: D, employment-weighted mean of occupations.csv baseline_growth_10y)",
    "import_share": "E (replaced by OECD TiVA, ingest/oecd_tiva.py)",
    "epl_multiplier": "D (OECD EPL strictness ratios, approximate)",
    "avail_delay_quarters": "S/E (spec P.30)",
    "frontier_lag_quarters": "E",
    "compliance_premium_high_risk": "E (spec P.31)",
    "regime": "S (spec §8.2 baselines)",
    "data_center_share": "E",
    "spillover_weight_us": "E",
}
REGIONS_TAG = "partial:natural_earth_pop_gdp;E(other columns, aiwsim.data.regions)"


def regions_frame(members: pl.DataFrame, us_emp_growth_10y: float) -> pl.DataFrame:
    """``regions.csv``: population and GDP aggregated from ``members``; constants for the rest."""
    agg = members.filter(pl.col("region_id") != "").group_by("region_id").agg(
        pl.col("population").sum().alias("population"), pl.col("gdp_bn_usd").sum().alias("gdp_bn_usd"),
        pl.len().alias("n_members"))
    a = {r["region_id"]: r for r in agg.to_dicts()}
    missing = [r for r in REGION_IDS if r not in a]
    if missing:
        raise ValueError(f"regions without Natural Earth members: {missing}")
    growth = {**EMP_GROWTH_10Y, "US": float(us_emp_growth_10y)}
    rows = []
    for r in REGION_IDS:
        pop, gdp = int(a[r]["population"]), float(a[r]["gdp_bn_usd"])
        rows.append({
            "region_id": r, "name": REGION_NAMES[r], "population": pop, "gdp_bn_usd": round(gdp, 3),
            "employment_total": round(pop * EMP_TO_POP_RATIO[r]),
            "wage_level_rel_us": WAGE_LEVEL_REL_US[r], "emp_growth_10y": round(growth[r], 4),
            "import_share": IMPORT_SHARE[r], "epl_multiplier": EPL_MULTIPLIER[r],
            "avail_delay_quarters": AVAIL_DELAY_QUARTERS[r], "frontier_lag_quarters": FRONTIER_LAG_QUARTERS[r],
            "compliance_premium_high_risk": COMPLIANCE_PREMIUM_HIGH_RISK[r], "regime": REGIME[r],
            "data_center_share": DATA_CENTER_SHARE[r], "spillover_weight_us": SPILLOVER_WEIGHT_US[r],
            "source_tag": REGIONS_TAG, "n_members": int(a[r]["n_members"]),
            "emp_to_pop_ratio": EMP_TO_POP_RATIO[r],
        })
    return pl.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# occ_region.csv: U.S. mix tilted by GDP per capita (FIXTURE)
# ------------------------------------------------------------------------------------------------
# Structural proxy (contracts §11): the employment share of each U.S. occupation is multiplied by
# (gdp_pc_region / gdp_pc_US) ** (+TILT_EXPONENT) for the high-skill major groups and
# ** (-TILT_EXPONENT) for the physical / agricultural / food-and-cleaning groups, then renormalised.
# The exponent is an E guess: at India's GDP per capita (~3% of the U.S.) it moves professional
# groups down by ~70% and physical groups up ~3.4x relative to the U.S. mix.
TILT_EXPONENT = 0.35
TILT_UP_GROUPS = frozenset({"11", "13", "15", "17", "19", "21", "23", "25", "27", "29"})
TILT_DOWN_GROUPS = frozenset({"35", "37", "45", "47", "51", "53"})
OCC_REGION_TAG = f"{FIXTURE_TAG}:us_mix_gdp_pc_tilt"


def tilt_factor(major_group: str, gdp_pc_ratio: float) -> float:
    if major_group in TILT_UP_GROUPS:
        return gdp_pc_ratio ** TILT_EXPONENT
    if major_group in TILT_DOWN_GROUPS:
        return gdp_pc_ratio ** (-TILT_EXPONENT)
    return 1.0


def occ_region_frame(occ: pl.DataFrame, regions: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """(occ_code, region_id) -> emp (largest-remainder integers summing to employment_total),
    wage_mean_annual_usd = U.S. wage x wage_level_rel_us.  Returns (frame, notes)."""
    o = occ.select("occ_code", "major_group", pl.col("emp_national").cast(pl.Float64),
                   pl.col("wage_mean_annual").cast(pl.Float64)).sort("occ_code")
    us_share = (o["emp_national"] / o["emp_national"].sum()).to_list()
    reg = {r["region_id"]: r for r in regions.to_dicts()}
    us_pc = reg["US"]["gdp_bn_usd"] / reg["US"]["population"]
    rows, notes = [], {}
    for rid in REGION_IDS:
        r = reg[rid]
        ratio = (r["gdp_bn_usd"] / r["population"]) / us_pc
        fac = [tilt_factor(g, ratio) for g in o["major_group"]]
        w = [s * f for s, f in zip(us_share, fac)]
        tot = sum(w)
        shares = [x / tot for x in w]
        emp = allocate_integer(int(r["employment_total"]), shares)
        wl = r["wage_level_rel_us"]
        rows.extend((code, rid, e, round(wage * wl, 2)) for code, e, wage in zip(o["occ_code"], emp, o["wage_mean_annual"]))
        up = sum(s for s, g in zip(shares, o["major_group"]) if g in TILT_UP_GROUPS)
        notes[rid] = {"gdp_pc_ratio": round(ratio, 4), "high_skill_share": round(up, 4)}
    df = pl.DataFrame(rows, schema=["occ_code", "region_id", "emp", "wage_mean_annual_usd"], orient="row")
    return df.with_columns(pl.lit(OCC_REGION_TAG).alias("source_tag")).sort(["region_id", "occ_code"]), notes


# ------------------------------------------------------------------------------------------------
# trade_weights.csv (FIXTURE)
# ------------------------------------------------------------------------------------------------
TRADE_TAG = f"{FIXTURE_TAG}:import_share_x_gdp_weights"


def trade_weights_frame(regions: pl.DataFrame) -> pl.DataFrame:
    """For each region_to: domestic weight 1 - import_share; the import share split across the
    other nine regions in proportion to their GDP (the rest of the world is not a source)."""
    reg = {r["region_id"]: r for r in regions.to_dicts()}
    rows = []
    for to in REGION_IDS:
        imp = float(reg[to]["import_share"])
        others = [s for s in REGION_IDS if s != to]
        gdp_sum = sum(float(reg[s]["gdp_bn_usd"]) for s in others)
        for frm in REGION_IDS:
            w = 1.0 - imp if frm == to else imp * float(reg[frm]["gdp_bn_usd"]) / gdp_sum
            rows.append((frm, to, w))
    df = pl.DataFrame(rows, schema=["region_from", "region_to", "weight"], orient="row")
    return df.with_columns(pl.col("weight").round(6), pl.lit(TRADE_TAG).alias("source_tag"))


# ------------------------------------------------------------------------------------------------
# value_chain.csv (spec §6.3, P.85; D from public gross margins, approximate)
# ------------------------------------------------------------------------------------------------
VALUE_CHAIN_TAG = "partial:public_gross_margins;D"
VALUE_CHAIN_ROWS = [
    # stage, share_of_spend, allocation, fixed_US, fixed_TW, fixed_EU, fixed_KR
    ("model", 0.25, "market_share", None, None, None, None),
    ("compute", 0.35, "data_center", None, None, None, None),
    ("chips", 0.25, "fixed", 0.55, 0.35, 0.10, 0.0),
    ("integration", 0.15, "domestic", None, None, None, None),
]


def value_chain_frame() -> pl.DataFrame:
    df = pl.DataFrame(
        VALUE_CHAIN_ROWS,
        schema={"stage": pl.Utf8, "share_of_spend": pl.Float64, "allocation": pl.Utf8, "fixed_US": pl.Float64,
                "fixed_TW": pl.Float64, "fixed_EU": pl.Float64, "fixed_KR": pl.Float64},
        orient="row",
    )
    if not math.isclose(df["share_of_spend"].sum(), 1.0):
        raise AssertionError("value chain shares must sum to 1")
    return df.with_columns(pl.lit(VALUE_CHAIN_TAG).alias("source_tag"))

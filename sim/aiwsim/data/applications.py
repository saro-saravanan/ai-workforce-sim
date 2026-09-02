"""Application-layer tables (spec v0.3 §A.3–A.5, §A.8): embodiment classes, applications catalogue,
approval paths, production shares, and the self-employed / platform workforce stock.

Every value here is an authors' estimate (`E`) written before the data plan of §A.10 ran; values marked
V? in the spec are provisional and the provenance records say so. The builders return polars frames and
the notes the provenance writer needs.
"""
from __future__ import annotations

import polars as pl

CLASSES = ["driving", "manip", "fixed", "aerial"]
REGIONS = ["US", "EU", "UK", "CN", "JP", "KR", "IN", "TW", "SG", "RoA"]

# ---- embodiment classes (spec §A.3.1–A.3.3; registry P.100–P.120) -------------------------------------------------
EMBODIMENT_CLASSES: list[dict] = [
    # class, a_emb, theta_lo, theta_hi (doublings on the class clock), tau_months, saturation, unit_price_2025_usd, lifetime_y,
    # opex_ratio, utilization, task_units_per_hour, g_max_per_year, cum_production_2025_units, adjacent_jobs_per_unit, note
    {"cls": "driving", "a_emb": 0.85, "theta_lo": 0.5, "theta_hi": 4.0, "tau_months": 18, "saturation": 8, "unit_price_2025_usd": 150_000,
     "lifetime_years": 5, "opex_ratio": 0.8, "utilization": 0.45, "task_units_per_hour": 1.0, "g_max_per_year": 0.5, "cum_production_2025": 3_000,
     "adjacent_jobs_per_unit": 0.10, "note": "V?: unit price = vehicle + sensing + amortized autonomy stack; utilization = paid hours / 8760; 2025 cumulative production from public fleet counts"},
    {"cls": "manip", "a_emb": 0.60, "theta_lo": 2.0, "theta_hi": 7.0, "tau_months": 15, "saturation": 10, "unit_price_2025_usd": 80_000,
     "lifetime_years": 8, "opex_ratio": 0.4, "utilization": 0.60, "task_units_per_hour": 0.7, "g_max_per_year": 0.5, "cum_production_2025": 20_000,
     "adjacent_jobs_per_unit": 0.05, "note": "V?: mobile manipulators and humanoids on one class clock; theta spread covers warehouse picking (low) to construction (high)"},
    {"cls": "fixed", "a_emb": 0.30, "theta_lo": 1.0, "theta_hi": 5.0, "tau_months": 24, "saturation": 8, "unit_price_2025_usd": 60_000,
     "lifetime_years": 10, "opex_ratio": 0.3, "utilization": 0.80, "task_units_per_hour": 1.5, "g_max_per_year": 0.5, "cum_production_2025": 5_000,
     "adjacent_jobs_per_unit": 0.03, "note": "AI-enabled increment over the baseline automation trend only (spec §A.1 attack 2); a_emb is the increment"},
    {"cls": "aerial", "a_emb": 0.50, "theta_lo": 2.0, "theta_hi": 5.0, "tau_months": 18, "saturation": 8, "unit_price_2025_usd": 15_000,
     "lifetime_years": 4, "opex_ratio": 0.6, "utilization": 0.30, "task_units_per_hour": 1.0, "g_max_per_year": 0.5, "cum_production_2025": 5_000,
     "adjacent_jobs_per_unit": 0.05, "note": "V?: delivery and inspection drones"},
]

# initial deployed stock 2024Q1 by class and region (units; E, V?)
INITIAL_STOCK: dict[str, dict[str, float]] = {
    "driving": {"US": 500, "CN": 500},
    "manip": {"US": 5_000, "CN": 5_000, "JP": 2_000, "KR": 1_000, "EU": 3_000},
    "fixed": {},
    "aerial": {"US": 300, "CN": 1_000},
}

# production location shares by class (spec §A.3.3, registry P.118; E)
PRODUCTION_SHARES: dict[str, dict[str, float]] = {
    "driving": {"US": 0.40, "CN": 0.45, "EU": 0.05, "JP": 0.05, "KR": 0.05},
    "manip": {"CN": 0.45, "JP": 0.15, "KR": 0.10, "EU": 0.10, "US": 0.20},
    "fixed": {"CN": 0.40, "JP": 0.25, "EU": 0.20, "KR": 0.10, "US": 0.05},
    "aerial": {"CN": 0.60, "US": 0.30, "EU": 0.10},
}

# approval baseline paths (spec §A.3.4, registry P.119; E, V?): J rises linearly from j0 at start_year to j_full at full_year
APPROVAL_PATHS: dict[str, dict[str, tuple[int, int, float, float]]] = {
    "driving": {"US": (2024, 2036, 0.03, 0.70), "CN": (2024, 2034, 0.03, 0.80), "EU": (2027, 2040, 0.00, 0.50), "UK": (2026, 2037, 0.00, 0.60),
                "JP": (2025, 2037, 0.01, 0.50), "KR": (2025, 2036, 0.01, 0.60), "IN": (2032, 2040, 0.00, 0.15), "TW": (2027, 2038, 0.00, 0.50),
                "SG": (2025, 2033, 0.02, 0.80), "RoA": (2025, 2038, 0.01, 0.35)},
    "aerial": {"US": (2025, 2036, 0.02, 0.50), "CN": (2024, 2034, 0.05, 0.70), "EU": (2027, 2040, 0.00, 0.40), "UK": (2026, 2038, 0.00, 0.50),
               "JP": (2025, 2036, 0.02, 0.50), "KR": (2025, 2035, 0.02, 0.60), "IN": (2028, 2040, 0.00, 0.30), "TW": (2027, 2038, 0.00, 0.50),
               "SG": (2025, 2032, 0.05, 0.80), "RoA": (2026, 2038, 0.01, 0.40)},
    "manip": {r: (2024, 2030, 0.90, 1.00) for r in REGIONS},
    "fixed": {r: (2024, 2030, 0.95, 1.00) for r in REGIONS},
}

# ---- applications catalogue (spec §A.8; Phase 6 = embodied rows; software/output/traded rows are labels until Phase 7) ----
APPLICATIONS: list[dict] = [
    {"app_id": "robotaxi", "name": "Robotaxis", "family": "embodied", "cls": "driving", "platform": 1,
     "occ_codes": "53-3054;53-3053", "sectors": "", "regions_first": "US;CN;SG;RoA",
     "anchor": "paid autonomous rides per week and fleet size (public company posts); state and city permits",
     "constraints": "approval by city and state; production ramp; utilization",
     "provisional_profitable": "2026-28", "provisional_deployed50": "2031-35"},
    {"app_id": "autonomous_trucking", "name": "Autonomous trucking", "family": "embodied", "cls": "driving", "platform": 0,
     "occ_codes": "53-3032", "sectors": "", "regions_first": "US;CN", "anchor": "driverless corridor launches; permits",
     "constraints": "approval by state and corridor; depot network", "provisional_profitable": "2027-29", "provisional_deployed50": "2033-37"},
    {"app_id": "last_mile_delivery", "name": "Last-mile delivery", "family": "embodied", "cls": "driving;aerial", "platform": 1,
     "occ_codes": "53-3033;43-5021;53-3031", "sectors": "", "regions_first": "US;CN;KR;SG", "anchor": "permitted operations counts",
     "constraints": "sidewalk and BVLOS approval; density", "provisional_profitable": "2027-30", "provisional_deployed50": "2033-38"},
    {"app_id": "warehouse_robotics", "name": "Warehouse robotics", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "53-7062;53-7064;53-7065;53-7051", "sectors": "", "regions_first": "US;CN;JP;KR;EU",
     "anchor": "robot installations (IFR aggregates); retailer disclosures", "constraints": "ramp; integration; site conversion",
     "provisional_profitable": "2025-27", "provisional_deployed50": "2030-34"},
    {"app_id": "manufacturing_flexible", "name": "Flexible manufacturing robots", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "51-2098;51-2092;51-2028;51-9061;51-9111;51-4121", "sectors": "", "regions_first": "CN;KR;JP;US;EU",
     "anchor": "IFR installations by application; humanoid pilot counts", "constraints": "learning rate; integration",
     "provisional_profitable": "2028-31", "provisional_deployed50": "2034-40"},
    {"app_id": "humanoid_general", "name": "General-purpose humanoids", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "*manip", "sectors": "", "regions_first": "CN;US", "anchor": "unit price disclosures; pilot deployments",
     "constraints": "unit cost; dexterity; safety certification", "provisional_profitable": "2030-34", "provisional_deployed50": "beyond 2040"},
    {"app_id": "food_service_automation", "name": "Food-service automation", "family": "embodied", "cls": "manip;fixed", "platform": 0,
     "occ_codes": "35-2014;35-2011;35-2021;35-3023;35-2012", "sectors": "", "regions_first": "US;JP;KR", "anchor": "vendor deployments",
     "constraints": "unit cost vs low wages; site conversion", "provisional_profitable": "2028-32", "provisional_deployed50": "2035-40"},
    {"app_id": "agricultural_robotics", "name": "Agricultural robotics", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "45-2092;45-2091;45-2093", "sectors": "", "regions_first": "US;EU;JP", "anchor": "deployment counts by crop",
     "constraints": "seasonality; crop specificity", "provisional_profitable": "2027-31", "provisional_deployed50": "2035-40"},
    {"app_id": "construction_robotics", "name": "Construction robotics", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "47-2061;47-2021;47-2081;47-2171;47-2031", "sectors": "", "regions_first": "JP;US", "anchor": "pilot counts",
     "constraints": "site variability; codes", "provisional_profitable": "2030-35", "provisional_deployed50": "beyond 2040"},
    {"app_id": "retail_checkout_shelf", "name": "Retail checkout and shelf automation", "family": "embodied", "cls": "fixed;manip", "platform": 0,
     "occ_codes": "41-2011;53-7065;41-2031", "sectors": "", "regions_first": "US;UK;EU;JP", "anchor": "retailer disclosures",
     "constraints": "shrink and customer acceptance", "provisional_profitable": "2025-27", "provisional_deployed50": "2030-34"},
]

# ---- self-employed and platform workforce (spec §A.5.1; FIXTURE until the CPS / Nonemployer ingest runs) ------------------
# share of an occupation's workers who are self-employed (incorporated + unincorporated), by SOC major group; E, V? (CPS-based recollection)
SELF_EMPLOYED_SHARE_BY_MG: dict[str, float] = {
    "11": 0.12, "13": 0.08, "15": 0.05, "17": 0.04, "19": 0.03, "21": 0.04, "23": 0.15, "25": 0.03, "27": 0.30, "29": 0.05, "31": 0.06,
    "33": 0.01, "35": 0.03, "37": 0.20, "39": 0.25, "41": 0.10, "43": 0.03, "45": 0.25, "47": 0.20, "49": 0.10, "51": 0.04, "53": 0.08, "55": 0.0,
}
# platform-mediated workers who are NOT in OEWS at all (heads, mean weekly hours), attached to an occupation; U.S.; E, V?
PLATFORM_ADDON_US: dict[str, tuple[float, float]] = {
    "53-3054": (1_500_000, 15.0),   # rideshare drivers (taxi drivers and chauffeurs code)
    "43-5021": (600_000, 12.0),     # app-based couriers
    "53-3033": (200_000, 20.0),     # app-based delivery in light trucks and vans
}
# regional multipliers on the self-employed share (E): informal and own-account work is more common outside the U.S.
SELF_EMPLOYED_REGION_MULT: dict[str, float] = {"US": 1.0, "EU": 1.2, "UK": 1.3, "CN": 1.5, "JP": 0.8, "KR": 1.8, "IN": 3.0, "TW": 1.2, "SG": 0.9, "RoA": 2.5}
PLATFORM_REGION_SCALE: dict[str, float] = {"US": 1.0, "EU": 0.9, "UK": 0.25, "CN": 3.0, "JP": 0.15, "KR": 0.25, "IN": 2.5, "TW": 0.1, "SG": 0.08, "RoA": 2.0}
SELF_EMPLOYED_HOURS = 35.0
FTE_HOURS = 40.0


def embodiment_classes_frame() -> pl.DataFrame:
    rows = []
    for c in EMBODIMENT_CLASSES:
        row = dict(c)
        for r in REGIONS:
            row[f"stock_2024_{r}"] = float(INITIAL_STOCK[c["cls"]].get(r, 0.0))
            row[f"prod_share_{r}"] = float(PRODUCTION_SHARES[c["cls"]].get(r, 0.0))
        row["source_tag"] = "E (spec v0.3 §A.3, V? values pending §A.10 verification)"
        rows.append(row)
    return pl.DataFrame(rows)


def approval_paths_frame() -> pl.DataFrame:
    rows = []
    for cls, by_r in APPROVAL_PATHS.items():
        for r in REGIONS:
            s, f, j0, jf = by_r[r]
            rows.append({"cls": cls, "region_id": r, "start_year": s, "full_year": f, "j0": j0, "j_full": jf,
                         "source_tag": "E (spec v0.3 §A.3.4 baseline path, V?)"})
    return pl.DataFrame(rows)


def applications_frame() -> pl.DataFrame:
    return pl.DataFrame([{**a, "source_tag": "spec v0.3 §A.8 catalogue (provisional timings are E, V?)"} for a in APPLICATIONS])


def self_employed_frame(occ: pl.DataFrame, regions: pl.DataFrame | None, occ_region: pl.DataFrame | None) -> tuple[pl.DataFrame, dict]:
    """occupation × region: self-employed heads, mean hours, FTE, platform share. FIXTURE."""
    codes = occ["occ_code"].to_list(); mg = occ["major_group"].to_list(); emp_us = occ["emp_national"].cast(pl.Float64).to_list()
    emp_by_region: dict[str, dict[str, float]] = {"US": dict(zip(codes, emp_us, strict=True))}
    if occ_region is not None:
        for r in occ_region.iter_rows(named=True):
            emp_by_region.setdefault(r["region_id"], {})[r["occ_code"]] = float(r["emp"])
    region_ids = [r for r in REGIONS if r in emp_by_region]
    rows = []; totals: dict[str, float] = {}
    for rid in region_ids:
        mult = SELF_EMPLOYED_REGION_MULT.get(rid, 1.0); psc = PLATFORM_REGION_SCALE.get(rid, 0.5)
        for code, group in zip(codes, mg, strict=True):
            e = emp_by_region[rid].get(code, 0.0)
            share = min(0.6, SELF_EMPLOYED_SHARE_BY_MG.get(group, 0.05) * mult)
            heads = e * share; hours = SELF_EMPLOYED_HOURS; platform_heads = 0.0
            if code in PLATFORM_ADDON_US:
                ph, phrs = PLATFORM_ADDON_US[code]
                platform_heads = ph * psc * (emp_by_region[rid].get(code, 0.0) / max(emp_by_region["US"].get(code, 1.0), 1.0) if rid != "US" else 1.0)
                hours = (heads * hours + platform_heads * phrs) / max(heads + platform_heads, 1.0)
                heads += platform_heads
            fte = heads * hours / FTE_HOURS
            if heads > 0:
                rows.append({"occ_code": code, "region_id": rid, "heads": round(heads, 1), "mean_weekly_hours": round(hours, 2), "fte": round(fte, 1),
                             "platform_share": round(platform_heads / max(heads, 1.0), 4),
                             "source_tag": "FIXTURE: CPS major-group self-employment shares (E) × regional multiplier; platform add-on E, V?"})
                totals[rid] = totals.get(rid, 0.0) + fte
    return pl.DataFrame(rows), {"fte_by_region": {k: round(v) for k, v in totals.items()}, "platform_addon_us": PLATFORM_ADDON_US}

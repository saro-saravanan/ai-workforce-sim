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
    # opex_ratio, utilization, task_units_per_hour, g_max_per_year, cum_production_2025_units, adjacent_jobs_per_unit, cost_floor_usd_per_hour, note
    # cost_floor_usd_per_hour (E; review §2.8, Phase 9): the hardware cost per worker-hour equivalent cannot fall below the running cost that
    # Wright's law does not learn away. Driving 3.0: energy, insurance, cleaning, remote assistance and depot per vehicle-hour at scale (E, from
    # disclosed robotaxi operating budgets read per paid hour); mobile manipulation 1.5, fixed automation 1.0, aerial 0.8: energy, maintenance and
    # a capital charge at scale (E). Applied in mc.py as a floor on kappa; lever applications.hardware.cost_floor_scale scales it (0 = Phase 8 curves).
    {"cls": "driving", "a_emb": 0.85, "theta_lo": 0.5, "theta_hi": 4.0, "tau_months": 18, "saturation": 8, "unit_price_2025_usd": 150_000,
     "lifetime_years": 5, "opex_ratio": 0.8, "utilization": 0.45, "task_units_per_hour": 1.0, "g_max_per_year": 0.5, "cum_production_2025": 3_000,
     "adjacent_jobs_per_unit": 0.10, "cost_floor_usd_per_hour": 3.0,
     "note": "V?: unit price = vehicle + sensing + amortized autonomy stack; utilization = paid hours / 8760; 2025 cumulative production from public fleet counts"},
    {"cls": "manip", "a_emb": 0.60, "theta_lo": 2.0, "theta_hi": 7.0, "tau_months": 15, "saturation": 10, "unit_price_2025_usd": 80_000,
     "lifetime_years": 8, "opex_ratio": 0.4, "utilization": 0.60, "task_units_per_hour": 0.7, "g_max_per_year": 0.5, "cum_production_2025": 20_000,
     "adjacent_jobs_per_unit": 0.05, "cost_floor_usd_per_hour": 1.5,
     "note": "V?: mobile manipulators and humanoids on one class clock; theta spread covers warehouse picking (low) to construction (high)"},
    {"cls": "fixed", "a_emb": 0.30, "theta_lo": 1.0, "theta_hi": 5.0, "tau_months": 24, "saturation": 8, "unit_price_2025_usd": 60_000,
     "lifetime_years": 10, "opex_ratio": 0.3, "utilization": 0.80, "task_units_per_hour": 1.5, "g_max_per_year": 0.5, "cum_production_2025": 5_000,
     "adjacent_jobs_per_unit": 0.03, "cost_floor_usd_per_hour": 1.0,
     "note": "AI-enabled increment over the baseline automation trend only (spec §A.1 attack 2); a_emb is the increment"},
    {"cls": "aerial", "a_emb": 0.50, "theta_lo": 2.0, "theta_hi": 5.0, "tau_months": 18, "saturation": 8, "unit_price_2025_usd": 15_000,
     "lifetime_years": 4, "opex_ratio": 0.6, "utilization": 0.30, "task_units_per_hour": 1.0, "g_max_per_year": 0.5, "cum_production_2025": 5_000,
     "adjacent_jobs_per_unit": 0.05, "cost_floor_usd_per_hour": 0.8, "note": "V?: delivery and inspection drones"},
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
    {"app_id": "robotaxi", "whole_job": 1, "eta_app": 1.5, "name": "Robotaxis", "family": "embodied", "cls": "driving", "platform": 1,
     "occ_codes": "53-3054;53-3053", "sectors": "", "regions_first": "US;CN;SG;RoA",
     "anchor": "paid autonomous rides per week and fleet size (public company posts); state and city permits",
     "constraints": "approval by city and state; production ramp; utilization",
     "provisional_profitable": "2026-28", "provisional_deployed50": "2031-35"},
    {"app_id": "autonomous_trucking", "whole_job": 1, "eta_app": 0.8, "name": "Autonomous trucking", "family": "embodied", "cls": "driving", "platform": 0,
     "occ_codes": "53-3032", "sectors": "", "regions_first": "US;CN", "anchor": "driverless corridor launches; permits",
     "constraints": "approval by state and corridor; depot network", "provisional_profitable": "2027-29", "provisional_deployed50": "2033-37"},
    {"app_id": "last_mile_delivery", "whole_job": 1, "eta_app": 1.2, "name": "Last-mile delivery", "family": "embodied", "cls": "driving;aerial", "platform": 1,
     "occ_codes": "53-3033;43-5021;53-3031", "sectors": "", "regions_first": "US;CN;KR;SG", "anchor": "permitted operations counts",
     "constraints": "sidewalk and BVLOS approval; density", "provisional_profitable": "2027-30", "provisional_deployed50": "2033-38"},
    {"app_id": "warehouse_robotics", "eta_app": 0.5, "name": "Warehouse robotics", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "53-7062;53-7064;53-7065;53-7051", "sectors": "", "regions_first": "US;CN;JP;KR;EU",
     "anchor": "robot installations (IFR aggregates); retailer disclosures", "constraints": "ramp; integration; site conversion",
     "provisional_profitable": "2025-27", "provisional_deployed50": "2030-34"},
    {"app_id": "manufacturing_flexible", "eta_app": 0.6, "name": "Flexible manufacturing robots", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "51-2098;51-2092;51-2028;51-9061;51-9111;51-4121", "sectors": "", "regions_first": "CN;KR;JP;US;EU",
     "anchor": "IFR installations by application; humanoid pilot counts", "constraints": "learning rate; integration",
     "provisional_profitable": "2028-31", "provisional_deployed50": "2034-40"},
    {"app_id": "humanoid_general", "eta_app": 0.8, "name": "General-purpose humanoids", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "*manip", "sectors": "", "regions_first": "CN;US", "anchor": "unit price disclosures; pilot deployments",
     "constraints": "unit cost; dexterity; safety certification", "provisional_profitable": "2030-34", "provisional_deployed50": "beyond 2040"},
    {"app_id": "food_service_automation", "eta_app": 0.8, "name": "Food-service automation", "family": "embodied", "cls": "manip;fixed", "platform": 0,
     "occ_codes": "35-2014;35-2011;35-2021;35-3023;35-2012", "sectors": "", "regions_first": "US;JP;KR", "anchor": "vendor deployments",
     "constraints": "unit cost vs low wages; site conversion", "provisional_profitable": "2028-32", "provisional_deployed50": "2035-40"},
    {"app_id": "agricultural_robotics", "eta_app": 0.5, "name": "Agricultural robotics", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "45-2092;45-2091;45-2093", "sectors": "", "regions_first": "US;EU;JP", "anchor": "deployment counts by crop",
     "constraints": "seasonality; crop specificity", "provisional_profitable": "2027-31", "provisional_deployed50": "2035-40"},
    {"app_id": "construction_robotics", "eta_app": 0.7, "name": "Construction robotics", "family": "embodied", "cls": "manip", "platform": 0,
     "occ_codes": "47-2061;47-2021;47-2081;47-2171;47-2031", "sectors": "", "regions_first": "JP;US", "anchor": "pilot counts",
     "constraints": "site variability; codes", "provisional_profitable": "2030-35", "provisional_deployed50": "beyond 2040"},
    # ---- output substitution (Phase 7, spec §A.4) ----
    {"app_id": "generative_video", "name": "Generative video", "family": "output", "cls": "video", "platform": 0, "occ_codes": "*cat", "sectors": "",
     "regions_first": "global", "anchor": "AI-generated share of new uploads and releases; guild agreements", "constraints": "quality gap; authenticity premium; licensing regime",
     "provisional_profitable": "2027-30", "provisional_deployed50": "2032-38"},
    {"app_id": "generative_music", "name": "Generative music", "family": "output", "cls": "music", "platform": 0, "occ_codes": "*cat", "sectors": "",
     "regions_first": "global", "anchor": "AI-generated share of streams and uploads", "constraints": "authenticity premium; licensing",
     "provisional_profitable": "2026-28", "provisional_deployed50": "2030-36"},
    {"app_id": "generative_text", "name": "Generative text", "family": "output", "cls": "text", "platform": 0, "occ_codes": "*cat", "sectors": "",
     "regions_first": "US;UK;EU", "anchor": "AI-generated share of new titles and articles", "constraints": "authenticity premium; discoverability",
     "provisional_profitable": "2025-27", "provisional_deployed50": "2029-34"},
    {"app_id": "generative_image_design", "name": "Generative image and design", "family": "output", "cls": "image_design", "platform": 0, "occ_codes": "*cat", "sectors": "",
     "regions_first": "global", "anchor": "stock-image revenue and AI share", "constraints": "quality gap", "provisional_profitable": "2024-26", "provisional_deployed50": "2028-32"},
    {"app_id": "machine_translation_voice", "name": "Machine translation and voice", "family": "output", "cls": "translation_voice", "platform": 0, "occ_codes": "*cat", "sectors": "",
     "regions_first": "global", "anchor": "translation industry revenue mix", "constraints": "quality gap in high-stakes domains",
     "provisional_profitable": "2024-26", "provisional_deployed50": "2027-31"},
    {"app_id": "generative_advertising", "name": "Generative advertising creative", "family": "output", "cls": "advertising", "platform": 0, "occ_codes": "*cat", "sectors": "",
     "regions_first": "global", "anchor": "agency disclosures", "constraints": "quality gap; brand risk", "provisional_profitable": "2025-27", "provisional_deployed50": "2029-33"},
    # ---- traded services and software applications (Phase 7, spec §A.5.3 and §A.8) ----
    {"app_id": "ai_customer_service", "name": "AI customer service and back office", "family": "traded", "cls": "bpo", "platform": 0,
     "occ_codes": "43-4051;43-9061;43-3021;43-4171;43-3031", "sectors": "", "regions_first": "IN;RoA;US", "anchor": "BPO revenue growth and headcount; deflection disclosures",
     "constraints": "deflection rates; regulation of automated decisions", "provisional_profitable": "2025-27", "provisional_deployed50": "2029-33"},
    {"app_id": "ai_it_services", "name": "AI coding agents in IT services", "family": "traded", "cls": "it_services", "platform": 0,
     "occ_codes": "15-1252;15-1232;15-1244;15-1211;15-1299", "sectors": "", "regions_first": "IN;US", "anchor": "IT services export growth and headcount",
     "constraints": "client acceptance; contract structures", "provisional_profitable": "2025-27", "provisional_deployed50": "2029-33"},
    {"app_id": "ai_tutoring_education", "name": "AI tutoring", "family": "software", "cls": "", "platform": 0, "occ_codes": "25-3041;25-9042;25-9045;25-3021", "sectors": "",
     "regions_first": "US;IN;CN", "anchor": "adoption in districts and platforms", "constraints": "procurement; evidence of efficacy",
     "provisional_profitable": "2026-29", "provisional_deployed50": "2032-38"},
    {"app_id": "ai_diagnostics", "name": "AI diagnostics", "family": "software", "cls": "", "platform": 0, "occ_codes": "29-2034;29-2035;31-9094;29-1224", "sectors": "",
     "regions_first": "US;EU;CN", "anchor": "cleared devices counts; deployment", "constraints": "regulatory clearance; liability",
     "provisional_profitable": "2026-29", "provisional_deployed50": "2032-38"},
    {"app_id": "ai_legal_research", "name": "AI legal research", "family": "software", "cls": "", "platform": 0, "occ_codes": "23-2011;23-1011;23-2093", "sectors": "",
     "regions_first": "US;UK", "anchor": "firm adoption surveys", "constraints": "professional rules", "provisional_profitable": "2025-27", "provisional_deployed50": "2029-33"},
    {"app_id": "retail_checkout_shelf", "eta_app": 0.5, "name": "Retail checkout and shelf automation", "family": "embodied", "cls": "fixed;manip", "platform": 0,
     "occ_codes": "41-2011;53-7065;41-2031", "sectors": "", "regions_first": "US;UK;EU;JP", "anchor": "retailer disclosures",
     "constraints": "shrink and customer acceptance", "provisional_profitable": "2025-27", "provisional_deployed50": "2030-34"},
]

# ---- output-substitution categories (spec §A.4; registry P.125–P.129); all E, V? ----------------------------------------------
# share0: AI-produced share of category spending in 2024Q1 (anchor, E V?); us_consumption_bn: 2024 U.S. spending at baseline prices; eta: own-price elasticity; ratio0: AI/human price 2024;
# alpha0: authenticity premium 2025 level (logit units); intermediate: category is an input to other sectors' costs
CONTENT_CATEGORIES: list[dict] = [
    {"cat_id": "video", "share0": 0.005, "name": "Motion picture and video", "occ_codes": "27-2011;27-2012;27-4011;27-4031;27-4032;27-1014;27-4012",
     "us_consumption_bn": 150.0, "eta": 0.8, "ratio0": 0.2, "alpha0": 1.5, "intermediate": 0, "anchor": "AI-generated share of new uploads and releases; guild agreements"},
    {"cat_id": "music", "share0": 0.01, "name": "Sound recording and music", "occ_codes": "27-2042;27-2041;27-4014", "us_consumption_bn": 20.0, "eta": 0.8, "ratio0": 0.15,
     "alpha0": 1.8, "intermediate": 0, "anchor": "AI-generated share of streams and uploads"},
    {"cat_id": "text", "share0": 0.02, "name": "Book, periodical and news publishing", "occ_codes": "27-3043;27-3041;27-3023;27-3042", "us_consumption_bn": 40.0, "eta": 0.6,
     "ratio0": 0.1, "alpha0": 1.2, "intermediate": 0, "anchor": "AI-generated share of new titles and articles"},
    {"cat_id": "image_design", "share0": 0.05, "name": "Graphic design, illustration and photography", "occ_codes": "27-1024;27-1013;27-4021;27-1021;27-1012",
     "us_consumption_bn": 30.0, "eta": 1.0, "ratio0": 0.1, "alpha0": 0.8, "intermediate": 1, "anchor": "stock-image marketplace revenue and AI share"},
    {"cat_id": "translation_voice", "share0": 0.15, "name": "Translation, interpretation and voice", "occ_codes": "27-3091;27-3011;27-3012", "us_consumption_bn": 10.0, "eta": 1.2,
     "ratio0": 0.05, "alpha0": 0.5, "intermediate": 1, "anchor": "translation industry revenue mix"},
    {"cat_id": "advertising", "share0": 0.03, "name": "Advertising creative", "occ_codes": "27-1011;11-2011", "us_consumption_bn": 40.0, "eta": 1.0, "ratio0": 0.15,
     "alpha0": 0.6, "intermediate": 1, "anchor": "agency disclosures; creative production spend"},
]

# ---- traded services (spec §A.5.3; registry P.124); E, V? ---------------------------------------------------------------------
# exporter region, category, 2024 exports $bn, FTE per $m of exports, export-serving occupations, importer weights (renormalized over modelled regions)
SERVICES_TRADE: list[dict] = [
    {"exporter": "IN", "category": "bpo", "export_bn": 45.0, "fte_per_musd": 25.0, "occ_codes": "43-4051;43-9061;43-3021;43-4171;43-3031",
     "importers": "US:0.6;EU:0.2;UK:0.15;RoA:0.05", "anchor": "NASSCOM BPM revenue and headcount"},
    {"exporter": "IN", "category": "it_services", "export_bn": 200.0, "fte_per_musd": 15.0, "occ_codes": "15-1252;15-1232;15-1244;15-1211;15-1299",
     "importers": "US:0.62;EU:0.2;UK:0.15;JP:0.03", "anchor": "NASSCOM IT services exports"},
    {"exporter": "RoA", "category": "bpo", "export_bn": 40.0, "fte_per_musd": 28.0, "occ_codes": "43-4051;43-9061;43-3021;43-4171",
     "importers": "US:0.7;EU:0.1;UK:0.1;SG:0.1", "anchor": "IBPAP (Philippines) revenue and headcount"},
    {"exporter": "RoA", "category": "it_services", "export_bn": 15.0, "fte_per_musd": 15.0, "occ_codes": "15-1252;15-1232;15-1211",
     "importers": "US:0.6;EU:0.2;JP:0.1;SG:0.1", "anchor": "Philippines and Vietnam IT exports"},
    {"exporter": "EU", "category": "bpo", "export_bn": 15.0, "fte_per_musd": 12.0, "occ_codes": "43-4051;43-9061;43-3021",
     "importers": "US:0.4;UK:0.4;CN:0.05;JP:0.05;RoA:0.1", "anchor": "Eurostat ITS other business services (Poland, Romania, Portugal)"},
]


# ---- named forecasts (forecaster scoreboard; spec v0.3 §A.16); every value transcribed from recollection, V? until the source is fetched ----
# metric ids map to model quantities in aiwsim.results2.forecasts_section
FORECASTS: list[dict] = [
    {"source": "RethinkX / Tony Seba, Rethinking Transportation 2020–2030 (2017)", "short": "Seba 2017, passenger miles", "region": "US", "year": 2030,
     "metric": "autonomous_share_of_ride_hail", "proxy": 1, "preset_id": "preset-seba-rethinkx", "claimed": 95.0, "unit": "% of passenger miles served by autonomous fleets",
     "note": "the report's headline: 95% of U.S. passenger miles by on-demand autonomous EV fleets within ten years of approval; the model's nearest quantity is robotaxi deployment coverage of profitable ride-hail hours"},
    {"source": "RethinkX / Tony Seba, Rethinking Transportation (2017)", "short": "Seba 2017, drivers (implied)", "region": "US", "year": 2030,
     "metric": "ride_hail_driver_displacement", "proxy": 0, "preset_id": "preset-seba-rethinkx", "claimed": 90.0, "unit": "% of ride-hail driver task-hours",
     "note": "implied by the passenger-mile claim; compared with the model's robotaxi displacement share"},
    {"source": "RethinkX, Rethinking Humanity (2020)", "short": "RethinkX 2020", "region": "US", "year": 2035,
     "metric": "embodied_displacement_share", "proxy": 1, "preset_id": "preset-seba-rethinkx", "claimed": 20.0, "unit": "% of task-hours",
     "note": "the report argues that labour, transport, food, energy and materials are disrupted in the 2020s–2030s; 20% of physical task-hours by 2035 is our reading of its labour chapter (V?, low confidence transcription)"},
    {"source": "Acemoglu (2024), 'The Simple Macroeconomics of AI'", "short": "Acemoglu 2024", "region": "US", "year": 2034,
     "metric": "tfp_pct", "proxy": 0, "preset_id": "preset-acemoglu-2024", "claimed": 0.66, "unit": "% TFP over ten years (upper bound)", "note": "replication preset exists"},
    {"source": "Goldman Sachs (2023), 'The Potentially Large Effects of AI on Economic Growth'", "short": "Goldman 2023", "region": "US", "year": 2033,
     "metric": "gdp_pct", "proxy": 0, "preset_id": "preset-goldman-2023", "claimed": 7.0, "unit": "% GDP over ten years", "note": "replication preset exists"},
    {"source": "IMF (2024), 'Gen-AI: Artificial Intelligence and the Future of Work'", "short": "IMF 2024", "region": "US", "year": 2034,
     "metric": "exposed_share", "proxy": 1, "claimed": 60.0, "unit": "% of jobs exposed (advanced economies)", "note": "compared with the model's ever-automatable mass share of employment"},
    {"source": "Brynjolfsson, Chandar, Chen (2025), 'Canaries in the Coal Mine'", "short": "Canaries 2025", "region": "US", "year": 2025,
     "metric": "young_exposed_employment_pct", "proxy": 1, "claimed": -13.0, "unit": "% employment of 22–25-year-olds in the most exposed occupations vs late 2022",
     "note": "compared with the model's 16–24 employment effect in the most exposed occupations at 2025Q4"},
    # ---- investment versus returns: observed capex and AI revenue ----
    {"source": "Company reports and guidance (Alphabet, Amazon, Meta, Microsoft), calendar 2025", "short": "Hyperscaler capex 2025", "region": "US", "year": 2025,
     "metric": "hyperscaler_capex_bn", "proxy": 0, "claimed": 413.0, "unit": "$bn capital expenditure, four hyperscalers",
     "note": "calendar-2025 capex of the four largest hyperscalers (data/processed/series/capex.csv); the model's capex path is a parameter (P.80), so agreement here is by construction",
     "source_tag": "company 10-K/10-Q figures transcribed in capex.csv (real; secondary confirmation)"},
    {"source": "Company guidance (Jul 2026 earnings calls), calendar 2026", "short": "Hyperscaler capex 2026 guidance", "region": "US", "year": 2026,
     "metric": "hyperscaler_capex_bn", "proxy": 0, "claimed": 725.0, "unit": "$bn capital expenditure, four hyperscalers",
     "note": "Amazon ~200, Microsoft ~190, Alphabet 175-205, Meta 125-145; the model's 2026 capex is P.80 x (1 + P.81)",
     "source_tag": "Jul 2026 guidance via press summaries (V: page summaries 2026-09-03)"},
    {"source": "Generative-AI industry revenue 2025: OpenAI $13.1bn (FT-verified statements), Anthropic about $5bn, Microsoft and Google AI lines, Menlo Ventures' enterprise estimate; consumer plus enterprise",
     "short": "AI industry revenue 2025", "region": "US", "year": 2025, "metric": "ai_producer_revenue_bn", "proxy": 0, "claimed": 60.0, "claimed_low": 45.0, "claimed_high": 80.0,
     "unit": "$bn of AI producers' revenue worldwide", "note": "the model's producers' revenue is calibrated to this and the 2026 row (P.140, P.143); world total, all regions",
     "source_tag": "press summaries and Menlo Ventures 2025 (V: secondary; scope varies by source, hence the range)"},
    {"source": "Generative-AI industry revenue 2026 (estimate): OpenAI about $40bn annualized (Jul 2026), Anthropic about $47bn gross run rate (Aug 2026), Microsoft, Google and others; estimates in circulation run from about $90bn to about $200bn",
     "short": "AI industry revenue 2026 (est.)", "region": "US", "year": 2026, "metric": "ai_producer_revenue_bn", "proxy": 0, "claimed": 140.0, "claimed_low": 90.0, "claimed_high": 200.0,
     "unit": "$bn of AI producers' revenue worldwide", "note": "calibration target for the revenue layer; the model's 2026Q4 rate against full-year estimates",
     "source_tag": "press summaries (V: secondary; run rates are not calendar revenue, hence the range)"},
    # ---- observed AI-cited layoffs (Challenger, Gray & Christmas job-cut announcement reports) ----
    {"source": "Challenger, Gray & Christmas, job cut announcement reports (2025 annual; monthly through June 2026)", "short": "Challenger 2025, AI-cited job cuts", "region": "US", "year": 2025,
     "metric": "ai_layoffs_in_year", "proxy": 1, "claimed": 54836.0, "unit": "announced U.S. job cuts citing AI in the calendar year",
     "note": "employers cited AI for 54,836 announced cuts in 2025; compared with the model's layoffs attributed to AI during 2025 (announced cuts include positions closed by attrition and redeployment, so the like-for-like model figure lies between its layoffs and its unfilled positions)",
     "source_tag": "challengergray.com monthly reports (V: page summaries 2026-09-03; report PDFs not fetched)"},
    {"source": "Challenger, Gray & Christmas, job cut announcement reports (cumulative since AI was first tracked in 2023)", "short": "Challenger 2026, AI-cited cuts since 2023", "region": "US", "year": 2026, "quarter": "2026Q2",
     "metric": "ai_layoffs_cum", "proxy": 1, "claimed": 173568.0, "unit": "announced U.S. job cuts citing AI, 2023 to June 2026",
     "note": "101,743 of these were announced in the first half of 2026, when AI led all stated reasons for cuts five months running; compared with the model's cumulative AI layoffs at 2026Q2",
     "source_tag": "challengergray.com June 2026 report and coverage (V: page summaries 2026-09-03; report PDFs not fetched)"},
    # ---- RethinkX labour series (2024–2026) and the 2026 convergence report; the preset-seba-2026 scenario carries their assumptions ----
    {"source": "RethinkX, 'Near-zero cost labor: the disruptive economics of humanoid robots' (2025) and 'This time, we are the horses' (2024, updated Dec 2025)",
     "short": "RethinkX 2025, robot cost at entry", "region": "US", "year": 2025, "metric": "humanoid_cost_per_hour_usd", "proxy": 1, "preset_id": "preset-seba-2026", "claimed": 10.0,
     "unit": "$ per robot labour-hour at market entry", "note": "humanoid robots enter the market at a cost-capability under $10/hour; compared with the model's mobile-manipulation hardware cost per worker-hour equivalent (integration excluded); for a cost, 'model lower' means the model is the more aggressive of the two",
     "source_tag": "rethinkx.com/blog/rethinkx/disruptive-economics-of-humanoid-robots and /the-disruption-of-labour-by-humanoid-robots (V: page summaries 2026-09-02; full text not fetched)"},
    {"source": "RethinkX, 'Near-zero cost labor' (2025); '15 RethinkX Robotics Insights' (2026)", "short": "RethinkX 2025, robot cost by 2035", "region": "US", "year": 2034,
     "metric": "humanoid_cost_per_hour_usd", "proxy": 1, "preset_id": "preset-seba-2026", "claimed": 1.0, "unit": "$ per robot labour-hour",
     "note": "under $1/hour before 2035 (and under $0.10 before 2045, outside the horizon); compared with the model's mobile-manipulation hardware cost per worker-hour equivalent at 2034Q4; for a cost, 'model lower' means the model is the more aggressive of the two",
     "source_tag": "rethinkx.com/labor/in-depth/insights-into-humanoid-robotics (V: page summary 2026-09-02; full text not fetched)"},
    {"source": "RethinkX, 'This time, we are the horses' (updated Dec 2025); 'The Painful Truth about AI & Robotics' (2026)", "short": "RethinkX 2026, robots do half of physical work", "region": "US", "year": 2039,
     "metric": "physical_work_share", "proxy": 1, "preset_id": "preset-seba-2026", "claimed": 50.0, "unit": "% of physical task-hours",
     "note": "'by the end of the 2030s robots are likely to be performing as much total labor as human beings'; read as half of physical task-hours done by robots and vehicles at 2039Q4 (office and analytical work is the software channel, not this claim)",
     "source_tag": "rethinkx.com/blog/rethinkx/the-painful-truth-about-ai-and-robotics (V: page summary 2026-09-02; full text not fetched)"},
    {"source": "Seba / RethinkX, 'Rethinking Energy, Mobility, and Materials' (2026), decadal roadmap", "short": "Seba 2026, TaaS by 2035", "region": "US", "year": 2035,
     "metric": "autonomous_share_of_ride_hail", "proxy": 1, "preset_id": "preset-seba-2026", "claimed": 80.0, "unit": "% of urban passenger miles by autonomous TaaS",
     "note": "roadmap phase 3 (~2035): 'TaaS provides over 80% of urban passenger miles'; compared with robotaxi deployment coverage of profitable ride-hail hours",
     "source_tag": "user-supplied summary of the 2026 report (V: summary only; report not fetched)"},
    {"source": "Seba / RethinkX, 'Rethinking Energy, Mobility, and Materials' (2026), decadal roadmap", "short": "Seba 2026, TaaS by 2032", "region": "US", "year": 2032,
     "metric": "autonomous_share_of_ride_hail", "proxy": 1, "preset_id": "preset-seba-2026", "claimed": 50.0, "unit": "% of urban passenger miles by autonomous TaaS",
     "note": "roadmap phase 2 (2029–2032): 'autonomous TaaS networks gain widespread regulatory approval'; read as half of urban passenger miles by 2032 on the way to 80% in 2035",
     "source_tag": "user-supplied summary of the 2026 report (V: summary only; the 50% midpoint is our interpolation)"},
]


def forecasts_frame() -> pl.DataFrame:
    targets = {"Challenger 2025, AI-cited job cuts", "Challenger 2026, AI-cited cuts since 2023", "AI industry revenue 2025", "AI industry revenue 2026 (est.)"}
    return pl.DataFrame([{"source_tag": "transcribed from recollection (V?); fetch and cite before use", "role": ("target" if f["short"] in targets else "comparison"), **f} for f in FORECASTS])


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


def content_categories_frame() -> pl.DataFrame:
    return pl.DataFrame([{**c, "source_tag": "E (spec v0.3 §A.4, V? pending §A.10 verification)"} for c in CONTENT_CATEGORIES])


def services_trade_frame() -> pl.DataFrame:
    return pl.DataFrame([{**r, "source_tag": "E (spec v0.3 §A.5.3, V?: BPM6 and industry statistics pending)"} for r in SERVICES_TRADE])


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

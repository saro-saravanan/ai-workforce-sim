"""Parameter registry transcribed from ``docs/model-spec.md`` §10 (v0.2).

Every row of the seven §10 tables is transcribed with ``id, name, central, min, max, unit, tag,
source``.  Where the spec gives the central by class/modality/size/stage the row carries a ``by``
mapping (per-key ``central``/``min``/``max``) and a top-level ``central`` of ``null``.  ``tag`` is
the spec's literal tag (``S``, ``D``, ``E``, ``S/E``, ``S→fit``, ``E→fit``); ``tag_primary`` is the
first letter, one of S/D/E.  Rows whose central is textual in the spec ("from BTOS", "fitted",
"CPS") keep the text in ``note`` with ``central: null``.

The spec's summary line says 77 parameters; the tables contain 81 rows (P.32a/P.32b are separate
rows).  All 81 are transcribed; the discrepancy is recorded in ``COUNT_NOTE``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

COUNT_NOTE = (
    "Spec §10 says 'Counts: 77 parameters; 18 S, 21 D, 38 E'. The tables as written contain 81 rows "
    "(including P.32a and P.32b); all rows are transcribed verbatim. v0.3 adds P.100–P.128 (application layer)."
)


def _p(id_, name, central, lo, hi, unit, tag, source, **kw):
    row = {"id": id_, "name": name, "central": central, "min": lo, "max": hi, "unit": unit, "tag": tag,
           "tag_primary": tag[0] if tag[0] in "SDE" else None, "source": source}
    row.update(kw)
    return row


def _by(**entries):
    return {k: {"central": c, "min": lo, "max": hi} for k, (c, lo, hi) in entries.items()}


def _mpc_deciles():
    # "0.9 -> 0.4" across deciles, ±0.1: linear interpolation between the endpoints is our reading (E).
    out = {}
    for d in range(1, 11):
        c = round(0.9 - (0.9 - 0.4) * (d - 1) / 9, 4)
        out[f"d{d:02d}"] = {"central": c, "min": round(c - 0.1, 4), "max": round(c + 0.1, 4)}
    return out


PARAMETERS: list[dict] = [
    # ---- Capability clock and cost --------------------------------------------------------------
    _p("P.01", "Clock doubling time τ₀", 5, 3, 12, "months", "S",
       "METR 2025: ~7 mo 2019-25, ~4 mo 2024-25; Time Horizon 1.1: 6.3 mo all-time, 4.3 since 2023, ~3 since 2024",
       group="capability_clock_and_cost"),
    _p("P.02", "Drift in doubling time γ", 0, -0.2, 0.3, "per year", "E", "", group="capability_clock_and_cost"),
    _p("P.03", "Clock noise sd", 0.15, 0.05, 0.3, "doublings/q", "E", "", group="capability_clock_and_cost"),
    _p("P.04", "Price decline at fixed capability ρ", 10, 3, 50, "×/year", "S",
       "Epoch AI Mar 2025: 9×-900×/yr across milestones, 40×/yr for GPT-4-level science QA",
       group="capability_clock_and_cost"),
    _p("P.05", "Open-frontier lag threshold", 2, 1, 4, "quarters", "D", "DeepSeek-R1 / Llama-3 episodes",
       group="capability_clock_and_cost"),
    _p("P.06", "Open-weights price multiplier", 0.25, 0.1, 0.5, "ratio", "D", "same", group="capability_clock_and_cost"),
    _p("P.07", "Tokens per capex dollar improvement e", 2, 1.3, 3, "×/year", "E", "hardware price-performance (Epoch)",
       group="capability_clock_and_cost"),
    _p("P.08", "Base tokens per task-unit n₀ by modality", None, None, None, "tokens", "E", "AEI conversation lengths",
       group="capability_clock_and_cost", range_note="±50%",
       by=_by(software=(None, None, None), other_cognitive=(None, None, None),
              interpersonal=(None, None, None), physical=(None, None, None)),
       note="Spec gives no numeric centrals by modality; to be set from AEI conversation lengths, range ±50%."),
    _p("P.09", "Integration cost I_s", 15, 5, 40, "% annual wage", "E", "sector-scaled; zero for entrants",
       group="capability_clock_and_cost"),
    _p("P.10", "Amortization H", 12, 8, 20, "quarters", "E", "", group="capability_clock_and_cost"),
    _p("P.15", "Threshold softness s", 1.0, 0.5, 2, "doublings", "E", "", group="capability_clock_and_cost"),
    _p("P.16", "Substitution share σ (initial)", 0.45, 0.25, 0.7, "share", "S",
       "AEI automation share 43% (Feb 2025), 49% (Sep 2025), 45% (Jan 2026); by task family",
       group="capability_clock_and_cost"),
    _p("P.17", "σ drift per doubling", 0.01, -0.02, 0.06, "share", "D", "not monotone in AEI; range includes zero",
       group="capability_clock_and_cost"),
    _p("P.19", "Robotics doubling time", 24, 12, 48, "months", "E", "", group="capability_clock_and_cost"),
    _p("P.36", "Clock saturation C_max", 20, 14, 24, "doublings", "E", "beyond this only a_k binds",
       group="capability_clock_and_cost"),
    # ---- Task feasibility ---------------------------------------------------------------------
    _p("P.20", "Ever-automatable a_base(E1)", 0.9, 0.7, 1.0, "probability", "E", "", group="task_feasibility"),
    _p("P.21", "a_base(E2)", 0.7, 0.4, 0.9, "probability", "E", "", group="task_feasibility"),
    _p("P.22", "a_base(E0)", 0.25, 0.05, 0.5, "probability", "E", "non-zero because labels are GPT-4-era",
       group="task_feasibility"),
    _p("P.23", "Presence exponent λ_π", 1.5, 0.5, 3, "—", "E", "O*NET Work Context presence items",
       group="task_feasibility"),
    _p("P.24", "AEI usage threshold for anchoring θ", 0.5, 0.25, 1.0, "× employment share", "E",
       "usage is a lower bound on feasibility", group="task_feasibility"),
    _p("P.25", "Δ(E1) beyond 2026Q2 clock", 1, 0, 3, "doublings", "E", "", group="task_feasibility"),
    _p("P.26", "Δ(E2)", 3, 1, 5, "doublings", "E", "", group="task_feasibility"),
    _p("P.27", "Δ(E0)", 6, 3, 10, "doublings", "E", "", group="task_feasibility"),
    _p("P.28", "Reliability shift, high-consequence tasks", 1, 0.5, 2, "doublings", "D",
       "METR 80% vs 50% horizon ratio", group="task_feasibility"),
    _p("P.29", "Token growth per doubling γ_n", 0.7, 0.4, 1.0, "log₂ tokens / doubling", "E",
       "agentic token use grows with task length", group="task_feasibility"),
    _p("P.34", "Domain transfer g_m", None, None, None, "—", "E", "METR measures software tasks only",
       group="task_feasibility",
       by=_by(software=(1.0, 1.0, 1.0), other_cognitive=(0.7, 0.4, 1.0), interpersonal=(0.5, 0.2, 0.8)),
       note="Spec ranges '0.4-1.0; 0.2-0.8' read as other cognitive and interpersonal; software is the reference (1.0)."),
    _p("P.35", "Profitability softness b_κ", 0.5, 0.25, 1, "log units", "E", "", group="task_feasibility"),
    _p("P.59", "a_phys (robotics track)", 0.3, 0.1, 0.6, "probability", "E", "", group="task_feasibility"),
    # ---- Regulation and access ----------------------------------------------------------------
    _p("P.30", "Availability delay δ^reg", None, None, None, "quarters", "S/E",
       "EU launch delays; CN frontier gap (Epoch)", group="regulation_and_access",
       by=_by(EU=(1, 0, 4), CN=(4, 2, 8))),
    _p("P.31", "Compliance premium χ by use-case class", None, None, None, "% of κ", "E",
       "no measured value; Annex III scope", group="regulation_and_access",
       by=_by(high_risk=(10, 2, 30), transparency=(1, 0, 3), unregulated=(0, 0, 0)),
       note="high-risk central refers to the EU"),
    _p("P.32a", "High-risk use-case friction φ^HR", 0.6, 0.3, 0.9, "multiplier", "E",
       "applies to Annex III task share only", group="regulation_and_access"),
    _p("P.32b", "Transparency-class friction φ^T", 0.9, 0.7, 1.0, "multiplier", "E", "", group="regulation_and_access"),
    _p("P.33", "EU employment-protection multiplier on layoffs", 0.5, 0.3, 0.8, "multiplier", "D", "OECD EPL ratio",
       group="regulation_and_access"),
    _p("P.37", "Availability gate v_min", 0.5, 0.25, 0.75, "—", "E", "", group="regulation_and_access"),
    # ---- Compute and supply -------------------------------------------------------------------
    _p("P.38", "Compute depreciation", 20, 12, 28, "quarters", "S",
       "hyperscaler useful-life disclosures (5-6 years)", group="compute_and_supply"),
    _p("P.39", "Capacity price exponent ξ", 1.0, 0.5, 2, "—", "E", "", group="compute_and_supply"),
    _p("P.57", "Market-share capability sensitivity β_m", 1.0, 0.5, 2, "per doubling", "E", "", group="compute_and_supply"),
    _p("P.58", "Market-share price sensitivity ψ_p", 0.5, 0.2, 1, "—", "E", "Ramp vendor shares as loose check",
       group="compute_and_supply"),
    # ---- Adoption -----------------------------------------------------------------------------
    _p("P.40", "Augmentation gain ψ", 0.25, 0.10, 0.50, "share", "S",
       "Brynjolfsson-Li-Raymond 14/15%, 34% novices; Noy-Zhang -40% time; Peng 55.8%; "
       "Dell'Acqua 12.2% tasks, 25.1% faster", group="adoption"),
    _p("P.41", "Bass p (fixed, not fitted)", 0.03, 0.01, 0.06, "per year", "S", "Sultan et al. 1990", group="adoption"),
    _p("P.42", "Bass q (fitted)", 0.38, 0.2, 0.6, "per year", "S→fit", "", group="adoption", fitted=True,
       note="0.38 is the prior"),
    _p("P.43", "Spillover q^× (fixed prior)", 0.1, 0, 0.3, "per year", "E", "not identifiable from shared clock",
       group="adoption"),
    _p("P.44", "Spillover lag L", 4, 2, 8, "quarters", "E", "", group="adoption"),
    _p("P.45", "Spillover weights", None, None, None, "—", "D", "", group="adoption", note="TiVA-based"),
    _p("P.46", "Hurdle B*_f by size (fitted)", None, None, None, "$/worker-q", "E→fit", "", group="adoption",
       fitted=True, note="no central given; fitted"),
    _p("P.47", "Hurdle dispersion b (fixed)", None, None, None, "$/worker-q", "E", "", group="adoption",
       note="no central given"),
    _p("P.48", "Sector friction φ_s", None, 0.5, 2, "multiplier", "D", "", group="adoption",
       note="central 'from BTOS' (derived); range ×0.5-2 around the derived value"),
    _p("P.49", "Size friction φ_f", None, None, None, "multiplier", "D",
       "BTOS 32% employment- vs 18% firm-weighted", group="adoption",
       by=_by(small=(0.6, 0.4, 0.8), mid=(0.8, 0.6, 1.0), large=(1.0, 0.8, 1.2)), range_note="±0.2"),
    _p("P.50", "Intensity ceiling ι^max", 0.7, 0.4, 0.9, "share", "E", "", group="adoption"),
    _p("P.51", "Intensity ramp", 0.08, 0.04, 0.15, "per quarter", "E", "", group="adoption"),
    _p("P.52", "Entrant adoption A^ent and entry rate ε", None, None, None, "share; per year", "D", "",
       group="adoption", range_note="±50%",
       by={"entrant_adoption": {"central": None, "min": None, "max": None, "note": "BTOS young firms"},
           "entry_rate": {"central": 0.08, "min": 0.04, "max": 0.12, "note": "BDS ~8%/yr, ±50%"}}),
    # ---- Labor --------------------------------------------------------------------------------
    _p("P.53", "Pass-through to prices π_p", 0.7, 0.3, 1.0, "share", "E",
       "the disputed step from productivity to living standards", group="labor"),
    _p("P.54", "Data-center jobs per $bn capex", None, None, None, "jobs/$bn", "D",
       "construction temporary, operations persistent", group="labor", range_note="±50%",
       note="central 'from BLS/QCEW'"),
    _p("P.55", "AI-development jobs per $bn AI spend", None, None, None, "jobs/$bn", "D", "", group="labor",
       range_note="±50%", note="central 'from BLS OEWS 5415/5182'"),
    _p("P.60", "Output demand elasticity η_s", None, None, None, "elasticity", "S", "Bessen 2019", group="labor",
       by=_by(tradables=(1.0, 0.5, 1.5), local_services=(0.6, 0.3, 1.0))),
    _p("P.61", "Reinstatement ρ_new", 0.4, 0.1, 0.8, "share", "E", "ensemble axis", group="labor"),
    _p("P.62", "New-task lag", 8, 4, 16, "quarters", "E", "", group="labor"),
    _p("P.63", "Net occupational attrition ς^occ", 2.5, 1.5, 3.5, "%/quarter", "D",
       "CPS matched files: retirement + occupation change + LF exit; within-occupation quits excluded "
       "(JOLTS total separations 3.3%/mo is the wrong quantity)", group="labor"),
    _p("P.64", "Layoff friction", 0.25, 0.1, 0.5, "share of gap/q", "E", "", group="labor"),
    _p("P.65", "Seniority protection", 0.5, 0, 1, "index", "E", "", group="labor"),
    _p("P.66", "Skill-distance decay", None, None, None, "—", "D", "", group="labor", note="fitted"),
    _p("P.67", "Occupation transition matrix", None, None, None, "—", "D", "CPS matched monthly", group="labor"),
    _p("P.68", "Retraining entry base rate", None, None, None, "per quarter", "D", "", group="labor",
       range_note="±50%", note="by cohort"),
    _p("P.69", "Scarring ℓ", 0.12, 0.05, 0.25, "share", "S", "Jacobson et al. 1993; Davis-von Wachter 2011",
       group="labor"),
    _p("P.70", "Retraining success", 0.55, 0.35, 0.75, "probability", "E", "WIOA", group="labor"),
    _p("P.71", "Retraining duration", 4, 2, 8, "quarters", "D", "", group="labor"),
    _p("P.72", "Hours conversion, shorter week", 0.8, 0.5, 1, "share", "E", "", group="labor"),
    _p("P.73", "Wage adjustment ε_w", 0.3, 0.15, 0.6, "per quarter", "S",
       "partial adjustment toward Lichter et al. 2015 (mean -0.51, median -0.39)", group="labor"),
    _p("P.74", "Productivity pass-through to wages β", 0.3, 0.1, 0.6, "share", "E", "ensemble axis", group="labor"),
    # ---- Macro --------------------------------------------------------------------------------
    _p("P.56", "Crowding-out of incremental AI investment", 0.3, 0, 0.7, "share", "E", "", group="macro"),
    _p("P.80", "U.S. AI capex 2025", 400, 380, 415, "$bn", "S",
       "Alphabet 91.4, Amazon 131.8, Meta 72.2, Microsoft ≈88-118", group="macro"),
    _p("P.81", "Capex growth 2026", 80, 60, 100, "%", "S", "Jul 2026 guidance ≈ $720-760bn", group="macro"),
    _p("P.82", "Capex path after 2026", None, None, None, "—", "E", "", group="macro",
       by={"growth_per_year_2027_2029": {"central": 10, "min": -10, "max": 30, "unit": "%/yr"},
           "plateau_start_year": {"central": 2030, "min": 2027, "max": 2033, "unit": "year"}},
       note="'+10%/yr to 2029, then flat'; range '-10-+30%/yr; plateau 2027-2033'"),
    _p("P.83", "Domestic value-added share of capex", 0.5, 0.3, 0.7, "share", "E", "", group="macro"),
    _p("P.84", "Productivity J-curve lag", 4, 0, 8, "quarters", "S", "Brynjolfsson-Rock-Syverson", group="macro"),
    _p("P.85", "Value-chain split of AI spend", None, None, None, "share", "D",
       "public gross margins (model providers, cloud, NVIDIA, TSMC, ASML)", group="macro",
       by=_by(model=(0.25, 0.15, 0.35), compute=(0.35, 0.25, 0.45), chips=(0.25, 0.15, 0.35),
              integration=(0.15, 0.05, 0.25)), range_note="±0.1 each"),
    _p("P.86", "MPC by decile", None, None, None, "share", "S", "Fagereng et al.; CBO", group="macro",
       by=_mpc_deciles(), range_note="±0.1",
       note="'0.9 → 0.4' across deciles; linear interpolation between the endpoints is our reading (E)."),
    _p("P.87", "Demand multiplier m", 0.6, 0.3, 0.9, "—", "S/E", "", group="macro"),
    _p("P.88", "Import shares", None, None, None, "—", "S", "", group="macro", note="TiVA"),
    _p("P.89", "Within-decile spread", None, None, None, "—", "D", "", group="macro", note="CPS"),
    _p("P.90", "Copula block correlations", None, None, None, "—", "E", "§7.1 table", group="macro",
       range_note="±0.2",
       by=_by(feasibility_level=(0.7, 0.5, 0.9), speed=(0.5, 0.3, 0.7), friction=(0.6, 0.4, 0.8),
              labor_institutions=(0.4, 0.2, 0.6), regions=(0.8, 0.6, 1.0)),
       note="Speed block: τ₀, ρ (negative), γ_n — magnitude ±0.5 with ρ entering negatively."),
    # ---- v0.3 application layer (docs/model-spec-v0.3-applications.md §A.9); all E unless noted; V? = provisional ----
    _p("P.100", "a_emb(driving)", 0.85, 0.5, 0.95, "share", "E", "spec v0.3 §A.3.1", group="applications"),
    _p("P.101", "a_emb(mobile manipulation)", 0.6, 0.3, 0.85, "share", "E", "spec v0.3 §A.3.1", group="applications"),
    _p("P.102", "a_emb(fixed automation) increment", 0.3, 0.1, 0.5, "share", "E", "over the baseline automation trend", group="applications"),
    _p("P.103", "a_emb(aerial)", 0.5, 0.2, 0.8, "share", "E", "spec v0.3 §A.3.1", group="applications"),
    _p("P.104", "Baseline automation trend scale", 1.0, 0.5, 1.5, "×", "E", "lever baseline.automation_trend", group="applications"),
    _p("P.105", "a_phys,none", 0.0, 0.0, 0.1, "share", "E", "care, dexterity, safety-critical bodily work", group="applications"),
    _p("P.106", "Presence exponent, embodied λ^emb_π", 0.5, 0.0, 1.5, "—", "E", "weaker than software (P.23): a robot can be present", group="applications"),
    _p("P.107", "Coupling of embodiment clocks to the software clock g^emb", 0.3, 0.0, 0.7, "—", "E", "range includes zero", group="applications"),
    _p("P.108", "Embodiment clock doubling time τ_c", None, None, None, "months", "E", "V?: driving from paid-ride and disengagement series once ingested",
       group="applications", by=_by(driving=(18, 9, 36), manip=(15, 8, 36), fixed=(24, 12, 48), aerial=(18, 9, 36))),
    _p("P.109", "Embodiment clock saturation", None, None, None, "doublings", "E", "", group="applications",
       by=_by(driving=(8, 5, 12), manip=(10, 6, 14), fixed=(8, 5, 12), aerial=(8, 5, 12))),
    _p("P.110", "Unit price 2025 p_c,0", None, None, None, "USD", "E", "V?: vendor disclosures pending", group="applications",
       by=_by(driving=(150_000, 80_000, 300_000), manip=(80_000, 30_000, 200_000), fixed=(60_000, 30_000, 120_000), aerial=(15_000, 5_000, 40_000))),
    _p("P.111", "Lifetime L_c", None, None, None, "years", "S", "V?", group="applications",
       by=_by(driving=(5, 3, 7), manip=(8, 5, 11), fixed=(10, 6, 14), aerial=(4, 2, 6))),
    _p("P.112", "Real rate i", 0.06, 0.03, 0.10, "per year", "S", "", group="applications"),
    _p("P.113", "Hardware learning rate LR_c", 0.12, 0.05, 0.25, "per doubling of cumulative production", "S", "V?: EV battery and industrial-robot histories; ensemble axis {0.08, 0.20}", group="applications"),
    _p("P.114", "Operating cost ratio o_c", None, None, None, "× annual capital cost", "E", "", group="applications",
       by=_by(driving=(0.8, 0.4, 1.5), manip=(0.4, 0.2, 0.8), fixed=(0.3, 0.15, 0.6), aerial=(0.6, 0.3, 1.2))),
    _p("P.115", "Utilization u_c", None, None, None, "share of hours", "E", "V?: lever for robotaxis", group="applications",
       by=_by(driving=(0.45, 0.2, 0.7), manip=(0.6, 0.3, 0.85), fixed=(0.8, 0.5, 0.95), aerial=(0.3, 0.1, 0.6))),
    _p("P.116", "Task-units per hour relative to a worker TU_c", None, None, None, "×", "E", "", group="applications",
       by=_by(driving=(1.0, 0.5, 2.0), manip=(0.7, 0.3, 1.5), fixed=(1.5, 0.8, 3.0), aerial=(1.0, 0.5, 2.0))),
    _p("P.117", "Maximum production growth g^max_c", 0.5, 0.3, 1.5, "per year", "S", "V?: EV production grew ~50%/yr 2015–2023 from a small base; industrial robots ~10%/yr; 0.7 in the first draft gave tens of millions of manipulators by 2040", group="applications"),
    _p("P.118", "Production location shares", None, None, None, "share", "D", "vehicle and robot manufacturing locations (embodiment_classes.csv)", group="applications"),
    _p("P.119", "Approval path J_c,r,t", None, None, None, "share", "E", "V?: approval_paths.csv baseline; lever states frozen/baseline/accelerated/moratorium", group="applications"),
    _p("P.120", "Adjacent jobs per deployed unit β_c", None, None, None, "FTE per unit", "E", "V?: remote assistance, depot, fleet maintenance", group="applications",
       by=_by(driving=(0.10, 0.0, 0.3), manip=(0.05, 0.0, 0.2), fixed=(0.03, 0.0, 0.1), aerial=(0.05, 0.0, 0.2))),
    _p("P.121", "Self-employed exit hazard per unit earnings loss", 0.3, 0.1, 0.6, "per year per 100% loss", "E", "hours fall first, exits follow (spec §A.3.6)", group="applications"),
    _p("P.122", "Layoff share for site conversions", 0.6, 0.3, 0.9, "share", "E", "embodied substitution inside an employer", group="applications"),
    _p("P.123", "Employee ↔ self-employed transition rates", None, None, None, "per quarter", "D", "CPS flows (pending ingest)", group="applications"),
    _p("P.124", "Export-serving employment per revenue", None, None, None, "FTE per USD m", "D", "services trade (Phase 7)", group="applications"),
    _p("P.125", "Price sensitivity γ_s (output substitution)", 2.0, 1.0, 4.0, "—", "S", "V?: Armington-type; Phase 7", group="applications"),
    _p("P.126", "Quality gap q_0, q_1", None, None, None, "logit units", "E", "Phase 7", group="applications", by=_by(q0=(-2.0, -4.0, 0.0), q1=(3.0, 1.0, 6.0))),
    _p("P.127", "Authenticity premium α_s (2025 level; half-life if eroding)", None, None, None, "logit units; years", "E", "V?: ensemble axis {persistent, eroding}; Phase 7",
       group="applications", by=_by(level=(1.5, 0.5, 3.0), half_life_years=(8, 4, 20))),
    _p("P.128", "AI content platform margin", 0.4, 0.2, 0.7, "share of price", "E", "Phase 7", group="applications"),
    # ---- Phase 8 revenue layer (spec v0.3 §A.16): what firms pay over token cost, and consumer AI spending ----
    _p("P.140", "Consumer AI revenue 2025", 15.0, 10.0, 22.0, "$bn/yr", "S",
       "OpenAI FY2025 revenue $13.1bn (FT-verified statements), consumer subscriptions the larger part in 2025; Google, xAI, Perplexity and others; Phase 8", group="revenue"),
    _p("P.141", "Consumer AI revenue ceiling", 150.0, 80.0, 300.0, "$bn/yr", "E",
       "about 1.5bn paying-equivalent users at $100/yr (subscriptions plus advertising); Phase 8", group="revenue"),
    _p("P.142", "Consumer AI revenue midpoint year", 2030.0, 2028.0, 2034.0, "year", "E", "logistic path anchored at P.140 in 2025; Phase 8", group="revenue"),
    _p("P.143", "Market price over cost, 2025", 5.0, 3.0, 8.0, "multiple", "E",
       "what employers pay per unit of AI work delivered over the model's cost of that work (tokens at the fixed-capability price plus integration): "
       "usage intensity per unit of work delivered (agentic loops, retries, pilots and seats that displace nothing yet: about 2x), frontier pricing over the "
       "fixed-capability path (about 2x), provider margin (about 1.3x); fitted so producers' revenue matches reported industry revenue in 2025 ($45-80bn) and 2026 ($90-200bn); Phase 8", group="revenue"),
    _p("P.144", "Market price over token cost, long run", 1.5, 1.1, 2.5, "multiple", "E", "competition compresses margins and frontier premia; Phase 8", group="revenue"),
    _p("P.145", "Price multiple half-life", 5.0, 3.0, 10.0, "years", "E", "Phase 8", group="revenue"),
    # ---- Phase 9 labour market (review §2.7): entrant supply responds to relative wages with a lag ----
    _p("P.146", "Entrant supply elasticity to relative wages", 0.5, 0.0, 1.5, "elasticity", "E",
       "field-of-study response literature (enrolment and major choice respond to expected relative earnings with elasticities of order 0.5, "
       "with a lag of a few years); scales the share of an occupation's attrition cut that lands on its entrant cohort; 0 reproduces the Phase 8 rule; Phase 9", group="labor"),
    _p("P.147", "Entrant response lag", 8, 4, 16, "quarters", "E", "time from a relative-wage change to a change in the entering cohort (course length); Phase 9", group="labor"),
]


def registry_document() -> dict:
    ids = [p["id"] for p in PARAMETERS]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate parameter ids")
    tags = {}
    for p in PARAMETERS:
        tags[p["tag_primary"]] = tags.get(p["tag_primary"], 0) + 1
    return {
        "spec_version": "0.3",
        "source": "docs/model-spec.md §10 (v0.2) + docs/model-spec-v0.3-applications.md §A.9 (P.100–P.128)",
        "count": len(PARAMETERS),
        "count_by_tag_primary": tags,
        "count_note": COUNT_NOTE,
        "tag_legend": {"S": "sourced", "D": "derived", "E": "estimated by us"},
        "parameters": PARAMETERS,
    }


def write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(registry_document(), sort_keys=False, allow_unicode=True, width=110)
    path.write_text(text, encoding="utf-8")
    load_registry(path)  # round-trip check


def load_registry(path: Path) -> dict:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    ids = [p["id"] for p in doc["parameters"]]
    if len(ids) != len(set(ids)):
        raise ValueError("registry.yaml: duplicate ids")
    return doc

"""Lever catalogue: schema walk with labels, units, registry parameter, and mechanism (contracts §9)."""
from __future__ import annotations

import json
from typing import Any

from . import service

LEVER_LABELS: dict[str, tuple[str, str, str, str]] = {
    # path: (label, unit, registry param, mechanism)
    "levers.capability.doubling_months": ("Capability doubling time", "months", "P.01", "capability clock (spec §3.2)"),
    "levers.capability.doubling_drift_per_year": ("Change in doubling time per year", "fraction/yr", "P.02", "capability clock (spec §3.2)"),
    "levers.capability.ever_automatable_scale": ("Ever-automatable task mass (scale)", "×", "P.20–P.22", "task feasibility ceiling (spec §2.2)"),
    "levers.capability.domain_transfer.other_cognitive": ("Domain transfer: other cognitive work", "fraction", "P.34", "feasibility clock per modality (spec §2.3)"),
    "levers.capability.domain_transfer.interpersonal": ("Domain transfer: interpersonal work", "fraction", "P.34", "feasibility clock per modality (spec §2.3)"),
    "levers.capability.clock_saturation_doublings": ("Clock saturation", "doublings", "P.36", "capability clock (spec §3.2)"),
    "levers.capability.robotics_doubling_months": ("Robotics doubling time", "months", "P.19", "physical tasks (spec §3.5)"),
    "levers.capability.feedback_from_revenue": ("Capability feedback from AI revenue", "", "", "optional feedback (spec §3.2)"),
    "levers.cost.price_decline_per_year": ("Inference price decline at fixed capability", "×/yr", "P.04", "price path (spec §3.3)"),
    "levers.cost.open_weights_multiplier": ("Open-weights price multiplier", "×", "P.06", "price compression (spec §3.3)"),
    "levers.cost.cost_floor_decline_per_year": ("Cost floor decline", "×/yr", "P.07", "compute cost floor (spec §3.4)"),
    "levers.cost.compute_capacity_constraint": ("Compute capacity constraint", "", "P.38–P.39", "capacity price multiplier (spec §3.4)"),
    "levers.cost.capacity_price_exponent": ("Capacity price exponent", "", "P.39", "capacity price multiplier (spec §3.4)"),
    "levers.cost.token_growth_per_doubling": ("Token growth per capability doubling", "log₂ tokens", "P.29", "tokens per task (spec §2.2)"),
    "levers.regulation.EU.ai_act": ("EU AI Act timetable", "", "P.30–P.32", "availability delay and use-case friction (spec §3.3, §4.2)"),
    "levers.regulation.EU.data_localization": ("EU data localization", "", "", "cloud rent allocation (spec §6.3)"),
    "levers.regulation.US.regime": ("U.S. regulatory regime", "", "P.31–P.32", "use-case compliance premium and friction (spec §4.2)"),
    "levers.regulation.CN.licensing": ("China licensing regime", "", "P.30", "availability (spec §3.3)"),
    "levers.regulation.export_controls": ("Chip export controls", "", "", "frontier lag and compute for China (spec §3.5)"),
    "levers.adoption.sector_friction_scale": ("Sector friction (scale)", "×", "P.48", "adoption speed (spec §4.2)"),
    "levers.adoption.small_firm_friction_scale": ("Small-firm friction (scale)", "×", "P.49", "adoption speed by size (spec §4.2)"),
    "levers.adoption.intensity_ceiling": ("Intensity ceiling within adopters", "share", "P.50", "realized task share (spec §4.2)"),
    "levers.adoption.spillover_lag_quarters": ("Cross-region spillover lag", "quarters", "P.44", "adoption spillover (spec §4.2)"),
    "levers.adoption.entrant_scale": ("AI-native entrant adoption (scale)", "×", "P.52", "entry term (spec §4.2)"),
    "levers.labor.reinstatement_ratio": ("Reinstatement (new-task) ratio", "share", "P.61", "new-task creation (spec §5.2)"),
    "levers.labor.demand_elasticity_scale": ("Output demand elasticity (scale)", "×", "P.60", "demand response to lower costs (spec §5.2)"),
    "levers.labor.layoff_friction": ("Layoff friction", "share/quarter", "P.64", "hiring channel vs layoffs (spec §5.3)"),
    "levers.labor.price_pass_through": ("Pass-through of cost savings to prices", "share", "P.53", "prices and real wages (spec §6.2)"),
    "levers.labor.occupational_attrition_pct_per_quarter": ("Net occupational attrition", "%/quarter", "P.63", "hiring channel (spec §5.3)"),
    "levers.labor.wage_pass_through": ("Productivity pass-through to wages", "share", "P.74", "wages (spec §5.5)"),
    "levers.baseline.bls_ai_adjustment": ("Baseline: BLS AI adjustment", "", "", "frozen-AI baseline (spec §7.6)"),
    "levers.baseline.automation_trend": ("Baseline: pre-AI automation trend (scale)", "×", "P.104", "AI-enabled increment over the trend (spec v0.3 §A.6.2)"),
    "levers.applications.embodiment.driving_doubling_months": ("Driving autonomy doubling time", "months", "P.108", "embodiment clock (spec v0.3 §A.3.1)"),
    "levers.applications.embodiment.manipulation_doubling_months": ("Mobile manipulation doubling time", "months", "P.108", "embodiment clock (spec v0.3 §A.3.1)"),
    "levers.applications.embodiment.fixed_doubling_months": ("Fixed automation doubling time", "months", "P.108", "embodiment clock (spec v0.3 §A.3.1)"),
    "levers.applications.embodiment.aerial_doubling_months": ("Aerial autonomy doubling time", "months", "P.108", "embodiment clock (spec v0.3 §A.3.1)"),
    "levers.applications.embodiment.coupling_to_software": ("Coupling of embodiment clocks to the software clock", "", "P.107", "embodiment clock (spec v0.3 §A.3.1)"),
    "levers.applications.hardware.learning_rate": ("Hardware learning rate", "per doubling", "P.113", "Wright's law unit cost (spec v0.3 §A.3.2)"),
    "levers.applications.hardware.utilization_scale": ("Hardware utilization (scale)", "×", "P.115", "cost per task-unit (spec v0.3 §A.3.2)"),
    "levers.applications.hardware.unit_price_scale": ("Hardware unit price 2025 (scale)", "×", "P.110", "cost per task-unit (spec v0.3 §A.3.2)"),
    "levers.applications.hardware.ramp_max_growth_per_year": ("Production ramp cap", "/yr", "P.117", "deployment speed (spec v0.3 §A.3.3)"),
    "levers.applications.enabled": ("Application layer (v0.3) on", "", "", "embodied, output-substitution and traded-services channels (spec v0.3)"),
    "levers.applications.content.authenticity": ("Authenticity premium", "", "P.127", "output substitution (spec v0.3 §A.4)"),
    "levers.applications.content.authenticity_level_scale": ("Authenticity premium level (scale)", "×", "P.127", "output substitution (spec v0.3 §A.4)"),
    "levers.applications.content.licensing_regime": ("Content licensing regime", "", "P.128", "AI content price and quality growth (spec v0.3 §A.4)"),
    "levers.applications.content.price_sensitivity": ("Content price sensitivity γ", "", "P.125", "output substitution (spec v0.3 §A.4)"),
    "levers.applications.trade.services_exposure_scale": ("Services-trade exposure (scale)", "×", "P.124", "traded services (spec v0.3 §A.5.3)"),
    "levers.applications.induced_demand_scale": ("Induced demand from cheaper applications", "×", "", "output demand for robotaxis and drones (spec v0.3 §A.16)"),
    "levers.applications.platform_labor": ("Platform labor classification", "", "P.123", "self-employed margin (spec v0.3 §A.3.6)"),
}
POLICY_LABELS = {
    "retraining_subsidy_pct_wage": ("Retraining subsidy", "% of wage"), "wage_insurance_replacement": ("Wage insurance replacement", "share"),
    "wage_insurance_years": ("Wage insurance duration", "years"), "ubi_monthly_usd": ("Universal basic income", "$/month"),
    "ai_tax_pct_of_ai_spend": ("AI tax", "% of AI spend"), "work_week_hours": ("Standard work week", "hours"), "immigration_scale": ("Immigration (scale)", "×"),
}


def _walk_schema(node: dict[str, Any], path: str, base: dict[str, Any], out: list[dict[str, Any]]) -> None:
    props = node.get("properties", {})
    for k, v in props.items():
        p = f"{path}.{k}"
        default = base.get(k) if isinstance(base, dict) else None
        if "enum" in v:
            lab = LEVER_LABELS.get(p, (k.replace("_", " ").capitalize(), "", "", ""))
            out.append({"path": p, "label": lab[0], "group": p.split(".")[1], "type": "enum", "options": v["enum"], "default": default,
                        "unit": lab[1], "param": lab[2], "mechanism": lab[3]})
        elif v.get("type") == "number" or v.get("type") == "integer":
            lab = LEVER_LABELS.get(p, (k.replace("_", " ").capitalize(), "", "", ""))
            lo, hi = v.get("minimum", 0), v.get("maximum", 1)
            step = (hi - lo) / 100 if v.get("type") == "number" else 1
            out.append({"path": p, "label": lab[0], "group": p.split(".")[1], "type": "number", "min": lo, "max": hi, "step": round(step, 6),
                        "default": default, "unit": lab[1], "param": lab[2], "mechanism": lab[3]})
        elif v.get("type") == "boolean":
            lab = LEVER_LABELS.get(p, (k.replace("_", " ").capitalize(), "", "", ""))
            out.append({"path": p, "label": lab[0], "group": p.split(".")[1], "type": "boolean", "default": default, "unit": "", "param": lab[2], "mechanism": lab[3]})
        elif v.get("type") == "object" and "properties" in v:
            _walk_schema(v, p, default if isinstance(default, dict) else {}, out)
        elif v.get("type") == "object" and "additionalProperties" in v and k == "policy":
            us = (default or {}).get("US", {}) if isinstance(default, dict) else {}
            for pk, pv in v["additionalProperties"].get("properties", {}).items():
                if pv.get("type") == "number":
                    lab = POLICY_LABELS.get(pk, (pk, ""))
                    out.append({"path": f"{p}.US.{pk}", "label": lab[0], "group": "policy", "type": "number", "min": pv.get("minimum", 0),
                                "max": pv.get("maximum", 1), "step": round((pv.get("maximum", 1) - pv.get("minimum", 0)) / 100, 6),
                                "default": us.get(pk), "unit": lab[1], "param": "", "mechanism": "transfers, hours and financing (spec v0.3 §A.16)"})
                elif pv.get("type") == "object" and pk == "financing":
                    for fk, fv in pv.get("properties", {}).items():
                        out.append({"path": f"{p}.US.financing.{fk}", "label": f"Financing: {fk.replace('_', ' ')}", "group": "policy", "type": "enum",
                                    "options": fv["enum"], "default": (us.get("financing") or {}).get(fk), "unit": "", "param": "", "mechanism": "financing rule (spec §6.5)"})



for _r in ("US", "EU", "UK", "CN", "JP", "KR", "IN", "TW", "SG", "RoA"):
    LEVER_LABELS[f"levers.applications.approval.{_r}"] = (f"Approval regime: {_r}", "", "P.119", "deployment share J (spec v0.3 §A.3.4)")


def lever_definitions() -> list[dict[str, Any]]:
    schema = json.loads((service.ROOT / "scenarios" / "schema.json").read_text())
    base = service.resolve(service.find_scenario("baseline"))
    out: list[dict[str, Any]] = []
    _walk_schema(schema["properties"]["levers"], "levers", base.get("levers", {}), out)
    return out

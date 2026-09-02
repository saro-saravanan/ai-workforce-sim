"""Parameter registry access and scenario lever resolution.

The registry (data/processed/params/registry.yaml) is the single source of truth for
central values, ranges, provenance tags, and sources (spec §10). Scenario levers and
overrides (spec §8) are applied here to produce a resolved, immutable parameter set.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Defaults for parameters that the run needs but that carry no registry row yet, or
# whose registry central is `null` because it is given `by` class. Every entry here
# is tagged E in the spec unless noted; the registry row, when present, wins.
_CODE_DEFAULTS: dict[str, Any] = {
    "P.11": 10.0,      # frontier blended price, $ per million tokens at release (S: public price lists)
    "P.12": 0.5,       # cost floor 2024, $ per million tokens (E)
    "P.13": 1.0e15,    # tokens per year of capacity per $bn of capex, 2024 hardware (E)
    "P.14": 150.0,     # trend AI capex 2023, $bn/yr, grows 5%/yr in the baseline (E)
    "P.08": {"software": 50_000, "other_cognitive": 40_000, "interpersonal": 30_000, "physical": 20_000},
    "P.34": {"software": 1.0, "other_cognitive": 0.7, "interpersonal": 0.5, "physical": 1.0},
    "P.30": {"EU": 1, "CN": 4, "US": 0},
    "P.31": {"high_risk": 0.10, "transparency": 0.01, "unregulated": 0.0},
    "P.49": {"small": 0.6, "mid": 0.8, "large": 1.0},
    "P.60": {"tradable": 1.0, "local": 0.6},
    "P.85": {"model": 0.25, "compute": 0.35, "chips": 0.25, "integration": 0.15},
    "P.86": [0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.4],
}

SIZE_CLASSES = ("small", "mid", "large")
# Employment shares by firm-size class, U.S. private sector (D, approximate from SUSB:
# <50 employees ~27%, 50–499 ~20%, 500+ ~53%).
SIZE_EMP_SHARES = {"small": 0.27, "mid": 0.20, "large": 0.53}


@dataclass(frozen=True)
class ParamSpec:
    id: str
    name: str
    central: Any
    min: Any
    max: Any
    unit: str
    tag: str
    source: str
    by: dict[str, Any] | None = None


@dataclass
class Params:
    """Resolved parameter values for one run. Access with p["P.01"] or p.by("P.34", key)."""

    values: dict[str, Any] = field(default_factory=dict)
    specs: dict[str, ParamSpec] = field(default_factory=dict)
    flags: dict[str, str] = field(default_factory=dict)

    def __getitem__(self, pid: str) -> Any:
        if pid in self.values and self.values[pid] is not None:
            return self.values[pid]
        if pid in _CODE_DEFAULTS:
            return _CODE_DEFAULTS[pid]
        raise KeyError(f"parameter {pid} has no value")

    def get(self, pid: str, default: Any = None) -> Any:
        try:
            return self[pid]
        except KeyError:
            return default

    def by(self, pid: str, key: str) -> float:
        v = self.get(pid)
        if isinstance(v, dict):
            if key in v:
                inner = v[key]
                val = inner.get("central") if isinstance(inner, dict) else inner
                if val is not None:
                    return float(val)
            fallback = _CODE_DEFAULTS.get(pid)
            if isinstance(fallback, dict) and key in fallback:
                return float(fallback[key])
            raise KeyError(f"{pid} has no entry for {key!r}")
        return float(v)

    def set(self, pid: str, value: Any) -> None:
        self.values[pid] = value

    def copy(self) -> Params:
        return Params(dict(self.values), dict(self.specs), dict(self.flags))


def load_registry(path: Path) -> dict[str, ParamSpec]:
    raw = yaml.safe_load(path.read_text())
    items = raw["parameters"] if isinstance(raw, dict) and "parameters" in raw else raw
    specs: dict[str, ParamSpec] = {}
    for it in items:
        if isinstance(items, dict):
            pid, body = it, items[it]
        else:
            pid, body = it["id"], it
        specs[pid] = ParamSpec(
            id=pid,
            name=str(body.get("name", "")),
            central=body.get("central"),
            min=body.get("min"),
            max=body.get("max"),
            unit=str(body.get("unit", "")),
            tag=str(body.get("tag", "E")),
            source=str(body.get("source", "")),
            by=body.get("by"),
        )
    return specs


def central_params(registry_path: Path) -> Params:
    specs = load_registry(registry_path)
    values: dict[str, Any] = {}
    for pid, s in specs.items():
        if s.by:
            values[pid] = {k: (v["central"] if isinstance(v, dict) and "central" in v else v) for k, v in s.by.items()}
        else:
            values[pid] = s.central
    p = Params(values=values, specs=specs)
    p.flags["registry"] = str(registry_path)
    return p


def _scale_by(p: Params, pid: str, scale: float) -> None:
    v = p.get(pid)
    if isinstance(v, dict):
        p.set(pid, {k: float(x) * scale for k, x in v.items()})
    elif v is not None:
        p.set(pid, float(v) * scale)


def apply_levers(p: Params, levers: dict[str, Any]) -> Params:
    """Map scenario levers (spec §8.2) onto registry parameters. Returns a new Params."""
    q = p.copy()
    cap = levers.get("capability", {})
    if "doubling_months" in cap:
        q.set("P.01", float(cap["doubling_months"]))
    if "doubling_drift_per_year" in cap:
        q.set("P.02", float(cap["doubling_drift_per_year"]))
    if "ever_automatable_scale" in cap:
        s = float(cap["ever_automatable_scale"])
        for pid in ("P.20", "P.21", "P.22"):
            q.set(pid, min(1.0, float(p[pid]) * s))
    if "domain_transfer" in cap:
        dt = dict(q["P.34"])
        dt.update({k: float(v) for k, v in cap["domain_transfer"].items()})
        q.set("P.34", dt)
    if "clock_saturation_doublings" in cap:
        q.set("P.36", float(cap["clock_saturation_doublings"]))
    if "robotics_doubling_months" in cap:
        q.set("P.19", float(cap["robotics_doubling_months"]))
    q.flags["capability_feedback"] = "on" if cap.get("feedback_from_revenue") else "off"

    cost = levers.get("cost", {})
    if "price_decline_per_year" in cost:
        q.set("P.04", float(cost["price_decline_per_year"]))
    if "open_weights_multiplier" in cost:
        q.set("P.06", float(cost["open_weights_multiplier"]))
    if "cost_floor_decline_per_year" in cost:
        q.set("P.07", float(cost["cost_floor_decline_per_year"]))
    if "capacity_price_exponent" in cost:
        q.set("P.39", float(cost["capacity_price_exponent"]))
    if "token_growth_per_doubling" in cost:
        q.set("P.29", float(cost["token_growth_per_doubling"]))
    q.flags["compute_capacity"] = "on" if cost.get("compute_capacity_constraint", True) else "off"

    reg = levers.get("regulation", {})
    us = reg.get("US", {}).get("regime", "state_patchwork")
    # U.S. regimes scale the high-risk compliance premium and friction (E).
    us_scale = {"none": 0.0, "state_patchwork": 0.3, "federal_light": 0.6, "federal_strict": 1.0}[us]
    chi = dict(q["P.31"])
    q.set("P.31_US", {k: float(v) * us_scale for k, v in chi.items()})
    q.flags["us_regime"] = us
    q.flags["eu_ai_act"] = reg.get("EU", {}).get("ai_act", "baseline")
    q.flags["export_controls"] = reg.get("export_controls", "2026_status_quo")

    ad = levers.get("adoption", {})
    if "sector_friction_scale" in ad:
        q.set("P.48_scale", float(ad["sector_friction_scale"]))
    if "small_firm_friction_scale" in ad:
        f = dict(q["P.49"])
        f["small"] = min(1.0, f["small"] * float(ad["small_firm_friction_scale"]))
        q.set("P.49", f)
    if "intensity_ceiling" in ad:
        q.set("P.50", float(ad["intensity_ceiling"]))
    if "spillover_lag_quarters" in ad:
        q.set("P.44", float(ad["spillover_lag_quarters"]))
    if "entrant_scale" in ad:
        q.set("P.52_scale", float(ad["entrant_scale"]))

    lab = levers.get("labor", {})
    if "reinstatement_ratio" in lab:
        q.set("P.61", float(lab["reinstatement_ratio"]))
    if "demand_elasticity_scale" in lab:
        q.set("P.60_scale", float(lab["demand_elasticity_scale"]))
    if "layoff_friction" in lab:
        q.set("P.64", float(lab["layoff_friction"]))
    if "price_pass_through" in lab:
        q.set("P.53", float(lab["price_pass_through"]))
    if "occupational_attrition_pct_per_quarter" in lab:
        q.set("P.63", float(lab["occupational_attrition_pct_per_quarter"]))
    if "wage_pass_through" in lab:
        q.set("P.74", float(lab["wage_pass_through"]))

    pol = levers.get("policy", {}).get("US", {})
    q.set("policy", dict(pol))
    base = levers.get("baseline", {})
    q.flags["bls_ai_adjustment"] = base.get("bls_ai_adjustment", "restore_trend")
    if "automation_trend" in base:
        q.set("P.104", float(base["automation_trend"]))

    # ---- v0.3 application layer (spec §A.9) ----
    app = levers.get("applications", {})
    q.flags["applications_enabled"] = bool(app.get("enabled", True))
    emb = app.get("embodiment", {})
    tau = dict(q.get("P.108") or {})
    for cls, key in (("driving", "driving_doubling_months"), ("manip", "manipulation_doubling_months"), ("fixed", "fixed_doubling_months"), ("aerial", "aerial_doubling_months")):
        if key in emb:
            tau[cls] = float(emb[key])
    if tau:
        q.set("P.108", tau)
    if "coupling_to_software" in emb:
        q.set("P.107", float(emb["coupling_to_software"]))
    if "manipulation_automatable_share" in emb:
        q.set("P.101", float(emb["manipulation_automatable_share"]))
    hw = app.get("hardware", {})
    if "learning_rate" in hw:
        q.set("P.113", float(hw["learning_rate"]))
    if "ramp_max_growth_per_year" in hw:
        q.set("P.117", float(hw["ramp_max_growth_per_year"]))
    q.flags["utilization_scale"] = float(hw.get("utilization_scale", 1.0))
    q.flags["unit_price_scale"] = float(hw.get("unit_price_scale", 1.0))
    q.flags["approval"] = {k: str(v) for k, v in app.get("approval", {}).items()}
    q.flags["platform_labor"] = app.get("platform_labor", "status_quo")
    q.flags["induced_demand_scale"] = float(app.get("induced_demand_scale", 1.0))
    content = app.get("content", {})
    q.flags["authenticity"] = content.get("authenticity", "eroding")
    q.flags["authenticity_level_scale"] = float(content.get("authenticity_level_scale", 1.0))
    q.flags["licensing_regime"] = content.get("licensing_regime", "permissive")
    if "price_sensitivity" in content:
        q.set("P.125", float(content["price_sensitivity"]))
    trade = app.get("trade", {})
    q.flags["services_exposure_scale"] = float(trade.get("services_exposure_scale", 1.0))
    return q


def apply_overrides(p: Params, overrides: dict[str, Any]) -> Params:
    q = p.copy()
    for pid, spec in overrides.items():
        if "central" in spec:
            q.set(pid, spec["central"])
        if "by" in spec:
            cur = q.get(pid)
            merged = dict(cur) if isinstance(cur, dict) else {}
            merged.update(spec["by"])
            q.set(pid, merged)
    return q

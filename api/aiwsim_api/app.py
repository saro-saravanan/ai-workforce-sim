"""FastAPI service over aiwsim (docs/contracts.md §3 and §9)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from aiwsim import SPEC_VERSION
from aiwsim.pipeline import Context, paired_compare, run_scenario
from aiwsim.scenario import load_scenario_file
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware


def find_root() -> Path:
    p = Path(__file__).resolve()
    for cand in (p, *p.parents):
        if (cand / "scenarios" / "schema.json").exists():
            return cand
    raise RuntimeError("repository root not found")


ROOT = find_root()
CACHE = ROOT / "data" / "cache"
USER_DIR = ROOT / "scenarios" / "user"
app = FastAPI(title="AI Workforce Sim API", version=SPEC_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=2048)
_state: dict[str, Any] = {}


def ctx() -> Context:
    if "ctx" not in _state:
        _state["ctx"] = Context(ROOT)
    return _state["ctx"]


def _scenario_files() -> list[Path]:
    files = [f for f in sorted((ROOT / "scenarios").glob("*.json")) if f.name != "schema.json"]
    if USER_DIR.exists():
        files += sorted(USER_DIR.glob("*.json"))
    return files


def list_scenarios() -> list[dict[str, Any]]:
    out = []
    for f in _scenario_files():
        d = load_scenario_file(f)
        out.append({"id": d.get("id"), "name": d.get("name"), "parent": d.get("parent"), "description": d.get("description", ""),
                    "preset": bool(d.get("preset", False)), "user": f.parent == USER_DIR})
    return out


def _find(sid: str) -> dict[str, Any]:
    for f in _scenario_files():
        d = load_scenario_file(f)
        if d.get("id") == sid:
            return d
    raise HTTPException(404, f"scenario {sid} not found")


@app.get("/api/health")
def health():
    c = ctx()
    return {"status": "ok", "spec_version": SPEC_VERSION, "data_version": c.inputs.data_version, "data_flags": c.inputs.data_flags,
            "cohorts": c.cohort_flag}


@app.get("/api/scenarios")
def scenarios():
    return list_scenarios()


@app.get("/api/scenarios/{sid}")
def scenario(sid: str):
    try:
        return ctx().resolve(_find(sid))
    except Exception as e:  # validation
        raise HTTPException(422, str(e)) from e


@app.post("/api/scenarios")
def save_scenario(body: dict[str, Any]):
    sid = str(body.get("id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", sid):
        raise HTTPException(422, "id must match ^[a-z0-9][a-z0-9-]{1,63}$")
    body = dict(body); body["user"] = True; body.setdefault("schema_version", "0.2")
    try:
        canon = ctx().resolve(body)
    except Exception as e:
        raise HTTPException(422, f"scenario invalid: {e}") from e
    USER_DIR.mkdir(parents=True, exist_ok=True)
    (USER_DIR / f"{sid}.json").write_text(json.dumps(body, indent=2))
    return canon


@app.get("/api/params")
def params():
    return yaml.safe_load(ctx().registry.read_text())


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
                                "default": us.get(pk), "unit": lab[1], "param": "", "mechanism": "transfers and financing (spec §6.5); Phase 3 wiring"})
                elif pv.get("type") == "object" and pk == "financing":
                    for fk, fv in pv.get("properties", {}).items():
                        out.append({"path": f"{p}.US.financing.{fk}", "label": f"Financing: {fk.replace('_', ' ')}", "group": "policy", "type": "enum",
                                    "options": fv["enum"], "default": (us.get("financing") or {}).get(fk), "unit": "", "param": "", "mechanism": "financing rule (spec §6.5)"})


@app.get("/api/levers")
def levers():
    schema = json.loads((ROOT / "scenarios" / "schema.json").read_text())
    base = ctx().resolve(_find("baseline"))
    out: list[dict[str, Any]] = []
    _walk_schema(schema["properties"]["levers"], "levers", base.get("levers", {}), out)
    return out


@app.get("/api/geo/us-states")
def geo_us_states():
    f = ROOT / "data" / "processed" / "geo" / "us_states.geojson"
    if not f.exists():
        raise HTTPException(404, "us_states.geojson not built; run `aiwsim data build`")
    return json.loads(f.read_text())


def _paths(shash: str) -> tuple[Path, Path]:
    stem = shash.replace(":", "_")
    return CACHE / f"{stem}.json", CACHE / f"{stem}.npz"


@app.post("/api/run")
def run(body: dict[str, Any]):
    c = ctx()
    draws = body.pop("draws", None); ensemble = body.pop("ensemble", None)
    if "id" in body and len(body) == 1:
        raw = _find(body["id"])
    else:
        raw = body
    try:
        scen = c.resolve(raw)
    except Exception as e:
        raise HTTPException(422, f"scenario invalid: {e}") from e
    if draws is not None:
        draws = max(1, min(int(draws), 400)); scen = dict(scen); scen["draws"] = draws
    if ensemble is not None:
        scen = dict(scen); scen["ensemble"] = {**scen.get("ensemble", {}), "mechanisms": ensemble}
    shash = c.hash(scen)
    jpath, npath = _paths(shash)
    if not jpath.exists():
        doc, rawarr = run_scenario(c, scen)
        CACHE.mkdir(parents=True, exist_ok=True)
        jpath.write_text(json.dumps(doc, separators=(",", ":")))
        np.savez_compressed(npath, **rawarr)
    else:
        doc = json.loads(jpath.read_text())
    return {"scenario_hash": shash, "meta": doc["meta"]}


def _load(shash: str) -> dict[str, Any]:
    jpath, _ = _paths(shash)
    if not jpath.exists():
        raise HTTPException(404, "results not found; POST /api/run first")
    return json.loads(jpath.read_text())


@app.get("/api/results/{shash}")
def results(shash: str):
    return _load(shash)


@app.get("/api/results/{shash}/{section}")
def results_section(shash: str, section: str):
    doc = _load(shash)
    if section not in doc:
        raise HTTPException(404, f"unknown section {section}")
    return doc[section]


@app.get("/api/sensitivity/{shash}")
def sensitivity(shash: str):
    return _load(shash).get("tornado", {})


@app.get("/api/explain/{shash}")
def explain(shash: str, metric: str = "employment_pct_vs_baseline", quarter: str = "2040Q4"):
    doc = _load(shash)
    q = doc["meta"]["quarters"]
    if quarter not in q:
        raise HTTPException(422, f"quarter must be one of {q[0]}..{q[-1]}")
    t = q.index(quarter)
    s = doc["series"]["US"].get(metric)
    if s is None:
        raise HTTPException(404, f"unknown metric {metric}")
    ch = doc.get("channels", {}).get(metric, {})
    contrib = {k: v[t] for k, v in ch.get("contributions", {}).items()} if ch else {}
    conf = doc.get("confidence", {}).get(metric, {})
    conf_q = conf.get(quarter) or conf.get("2040Q4") or {}
    trace = doc.get("explain", {}).get("trace", {})
    return {"metric": metric, "quarter": quarter, "value": {k: v[t] for k, v in s.items()}, "channels": contrib,
            "trace": trace.get(quarter) or trace.get("2040Q4") or {}, "confidence": conf_q,
            "top_params": doc.get("tornado", {}).get(metric, [])[:5], "notes": doc.get("explain", {}).get("notes", []),
            "diff": doc.get("explain", {}).get("diff", [])}


@app.get("/api/compare")
def compare(a: str, b: str):
    c = ctx()
    da, db = _load(a), _load(b)
    _, na = _paths(a); _, nb = _paths(b)
    if not (na.exists() and nb.exists()):
        raise HTTPException(404, "per-draw arrays missing for one of the runs; re-run it")
    ra = dict(np.load(na)); rb = dict(np.load(nb))
    delta = paired_compare(ra, rb, da["meta"]["quarters"], c.inputs.state_fips, c.inputs.occ_codes)
    sa = c.resolve(_find(da["meta"]["scenario_id"])) if da["meta"].get("scenario_id") else {}
    sb = c.resolve(_find(db["meta"]["scenario_id"])) if db["meta"].get("scenario_id") else {}
    from aiwsim.results2 import annotate_diff
    from aiwsim.scenario import diff as sdiff
    return {"a": {"hash": a, "id": da["meta"].get("scenario_id"), "name": da["meta"].get("scenario_name")},
            "b": {"hash": b, "id": db["meta"].get("scenario_id"), "name": db["meta"].get("scenario_name")},
            "diff": annotate_diff(sdiff(sa, sb)) if sa and sb else [], "delta": delta,
            "confidence": {"a": da.get("confidence", {}), "b": db.get("confidence", {})},
            "trace": {"a": da.get("explain", {}).get("trace", {}), "b": db.get("explain", {}).get("trace", {})}}

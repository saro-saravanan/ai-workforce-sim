"""FastAPI service over aiwsim (docs/contracts.md §3)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aiwsim import SPEC_VERSION
from aiwsim.engine import channel_decomposition, run_central
from aiwsim.inputs import load_inputs
from aiwsim.params import apply_levers, apply_overrides, central_params
from aiwsim.results import build_results
from aiwsim.scenario import load_scenario_file, resolve, scenario_hash, validate
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


def find_root() -> Path:
    p = Path(__file__).resolve()
    for cand in (p, *p.parents):
        if (cand / "scenarios" / "schema.json").exists():
            return cand
    raise RuntimeError("repository root not found")


ROOT = find_root()
CACHE = ROOT / "data" / "cache"
app = FastAPI(title="AI Workforce Sim API", version=SPEC_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_state: dict[str, Any] = {}


def inputs():
    if "inputs" not in _state:
        _state["inputs"] = load_inputs(ROOT)
    return _state["inputs"]


def registry_path() -> Path:
    return ROOT / "data" / "processed" / "params" / "registry.yaml"


def list_scenarios() -> list[dict[str, Any]]:
    out = []
    for f in sorted((ROOT / "scenarios").glob("*.json")):
        if f.name == "schema.json":
            continue
        d = load_scenario_file(f)
        out.append({"id": d.get("id"), "name": d.get("name"), "parent": d.get("parent"), "description": d.get("description", "")})
    return out


@app.get("/api/health")
def health():
    inp = inputs()
    return {"status": "ok", "spec_version": SPEC_VERSION, "data_version": inp.data_version, "data_flags": inp.data_flags}


@app.get("/api/scenarios")
def scenarios():
    return list_scenarios()


@app.get("/api/scenarios/{sid}")
def scenario(sid: str):
    for f in (ROOT / "scenarios").glob("*.json"):
        if f.name != "schema.json" and load_scenario_file(f).get("id") == sid:
            return resolve(load_scenario_file(f), ROOT / "scenarios")
    raise HTTPException(404, f"scenario {sid} not found")


@app.get("/api/params")
def params():
    import yaml
    return yaml.safe_load(registry_path().read_text())


@app.get("/api/geo/us-states")
def geo_us_states():
    f = ROOT / "data" / "processed" / "geo" / "us_states.geojson"
    if not f.exists():
        raise HTTPException(404, "us_states.geojson not built; run `aiwsim data build`")
    return json.loads(f.read_text())


@app.post("/api/run")
def run(body: dict[str, Any]):
    inp = inputs()
    if "id" in body and len(body) == 1:
        scen = scenario(body["id"])
    else:
        scen = resolve(body, ROOT / "scenarios")
    try:
        validate(scen, ROOT / "scenarios" / "schema.json")
    except Exception as e:  # jsonschema.ValidationError
        raise HTTPException(422, f"scenario invalid: {e}") from e
    shash = scenario_hash(scen, SPEC_VERSION, inp.data_version)
    path = CACHE / f"{shash.replace(':', '_')}.json"
    if not path.exists():
        p = apply_overrides(apply_levers(central_params(registry_path()), scen.get("levers", {})), scen.get("overrides", {}))
        r = run_central(inp, p, scen)
        doc = build_results(inp, r, scen, shash, channel_decomposition(inp, p, scen, r))
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, separators=(",", ":")))
    else:
        doc = json.loads(path.read_text())
    return {"scenario_hash": shash, "meta": doc["meta"]}


def _load(shash: str) -> dict[str, Any]:
    path = CACHE / f"{shash.replace(':', '_')}.json"
    if not path.exists():
        raise HTTPException(404, "results not found; POST /api/run first")
    return json.loads(path.read_text())


@app.get("/api/results/{shash}")
def results(shash: str):
    return _load(shash)


@app.get("/api/results/{shash}/{section}")
def results_section(shash: str, section: str):
    doc = _load(shash)
    if section not in doc:
        raise HTTPException(404, f"unknown section {section}")
    return doc[section]

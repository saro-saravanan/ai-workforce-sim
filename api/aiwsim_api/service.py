"""Shared service layer: repository root, simulation context, scenario lookup, run cache.

Used by the HTTP app (app.py), the chat tools (chat.py), and the brief/insight builders so the
chat layer calls the same code paths as the UI and never computes numbers of its own.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
from aiwsim.pipeline import Context, paired_compare, run_scenario
from aiwsim.results2 import annotate_diff
from aiwsim.scenario import diff as sdiff
from aiwsim.scenario import load_scenario_file


class NotFound(Exception):
    pass


class Invalid(Exception):
    pass


def find_root() -> Path:
    p = Path(__file__).resolve()
    for cand in (p, *p.parents):
        if (cand / "scenarios" / "schema.json").exists():
            return cand
    raise RuntimeError("repository root not found")


ROOT = find_root()
CACHE = ROOT / "data" / "cache"
USER_DIR = ROOT / "scenarios" / "user"
SCENARIO_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{1,63}")
_state: dict[str, Any] = {}


def ctx() -> Context:
    if "ctx" not in _state:
        _state["ctx"] = Context(ROOT)
    return _state["ctx"]


def scenario_files() -> list[Path]:
    files = [f for f in sorted((ROOT / "scenarios").glob("*.json")) if f.name != "schema.json"]
    if USER_DIR.exists():
        files += sorted(USER_DIR.glob("*.json"))
    return files


def list_scenarios() -> list[dict[str, Any]]:
    out = []
    for f in scenario_files():
        d = load_scenario_file(f)
        out.append({"id": d.get("id"), "name": d.get("name"), "parent": d.get("parent"), "description": d.get("description", ""),
                    "preset": bool(d.get("preset", False)), "user": f.parent == USER_DIR})
    return out


def find_scenario(sid: str) -> dict[str, Any]:
    for f in scenario_files():
        d = load_scenario_file(f)
        if d.get("id") == sid:
            return d
    raise NotFound(f"scenario {sid} not found")


def resolve(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        return ctx().resolve(raw)
    except Exception as e:  # jsonschema / inheritance errors
        raise Invalid(str(e)) from e


def save_scenario(body: dict[str, Any]) -> dict[str, Any]:
    sid = str(body.get("id", ""))
    if not SCENARIO_ID_RE.fullmatch(sid):
        raise Invalid("id must match ^[a-z0-9][a-z0-9-]{1,63}$")
    body = dict(body); body["user"] = True; body.setdefault("schema_version", "0.2")
    canon = resolve(body)
    USER_DIR.mkdir(parents=True, exist_ok=True)
    (USER_DIR / f"{sid}.json").write_text(json.dumps(body, indent=2))
    return canon


def paths(shash: str) -> tuple[Path, Path]:
    stem = shash.replace(":", "_")
    return CACHE / f"{stem}.json", CACHE / f"{stem}.npz"


def run_or_load(raw: dict[str, Any], draws: int | None = None, ensemble: str | None = None,
                regions: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    """Resolve, hash, and run a scenario (or return the cached document). Returns (hash, results doc)."""
    c = ctx()
    scen = resolve(raw)
    if draws is not None:
        scen = dict(scen); scen["draws"] = max(1, min(int(draws), 400))
    if ensemble is not None:
        scen = dict(scen); scen["ensemble"] = {**scen.get("ensemble", {}), "mechanisms": ensemble}
    shash = c.hash(scen)
    jpath, npath = paths(shash)
    if jpath.exists():
        return shash, json.loads(jpath.read_text())
    doc, rawarr = run_scenario(c, scen, regions=regions)
    CACHE.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(doc, separators=(",", ":")))
    np.savez_compressed(npath, **rawarr)
    return shash, doc


def load_results(shash: str) -> dict[str, Any]:
    jpath, _ = paths(shash)
    if not jpath.exists():
        raise NotFound("results not found; POST /api/run first")
    return json.loads(jpath.read_text())


def scenario_of(doc: dict[str, Any]) -> dict[str, Any]:
    """The canonical scenario a results document was run from (empty when the id is unknown)."""
    sid = doc["meta"].get("scenario_id")
    if not sid:
        return {}
    try:
        return resolve(find_scenario(sid))
    except NotFound:
        return {}


def explain(doc: dict[str, Any], metric: str, quarter: str, region: str = "US") -> dict[str, Any]:
    q = doc["meta"]["quarters"]
    if quarter not in q:
        raise Invalid(f"quarter must be one of {q[0]}..{q[-1]}")
    t = q.index(quarter)
    block = doc["series"].get(region) or doc["series"]["US"]
    s = block.get(metric)
    if s is None:
        raise NotFound(f"unknown metric {metric}")
    ch = doc.get("channels", {}).get(metric, {}) if region == "US" else {}
    contrib = {k: v[t] for k, v in ch.get("contributions", {}).items()} if ch else {}
    conf = doc.get("confidence", {}).get(metric, {})
    conf_q = conf.get(quarter) or conf.get("2040Q4") or {}
    trace = doc.get("explain", {}).get("trace", {})
    return {"metric": metric, "quarter": quarter, "region": region, "value": {k: v[t] for k, v in s.items()}, "channels": contrib,
            "trace": trace.get(quarter) or trace.get("2040Q4") or {}, "confidence": conf_q,
            "top_params": doc.get("tornado", {}).get(metric, [])[:5], "notes": doc.get("explain", {}).get("notes", []),
            "diff": doc.get("explain", {}).get("diff", [])}


def compare(a: str, b: str) -> dict[str, Any]:
    c = ctx()
    da, db = load_results(a), load_results(b)
    _, na = paths(a); _, nb = paths(b)
    if not (na.exists() and nb.exists()):
        raise NotFound("per-draw arrays missing for one of the runs; re-run it")
    ra = dict(np.load(na)); rb = dict(np.load(nb))
    delta = paired_compare(ra, rb, da["meta"]["quarters"], c.inputs.state_fips, c.inputs.occ_codes)
    sa, sb = scenario_of(da), scenario_of(db)
    return {"a": {"hash": a, "id": da["meta"].get("scenario_id"), "name": da["meta"].get("scenario_name")},
            "b": {"hash": b, "id": db["meta"].get("scenario_id"), "name": db["meta"].get("scenario_name")},
            "diff": annotate_diff(sdiff(sa, sb)) if sa and sb else [], "delta": delta,
            "confidence": {"a": da.get("confidence", {}), "b": db.get("confidence", {})},
            "trace": {"a": da.get("explain", {}).get("trace", {}), "b": db.get("explain", {}).get("trace", {})}}

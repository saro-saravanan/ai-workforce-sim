"""FastAPI service over aiwsim (docs/contracts.md §3, §9, §13, §15–16, §26–28)."""
from __future__ import annotations

import json
from typing import Any

import yaml
from aiwsim import SPEC_VERSION
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import chat as chat_mod
from . import service
from . import story as story_mod
from .brief import build_brief_html, build_brief_md
from .insights import top_insights
from .levers import lever_definitions
from .service import ROOT, ctx

app = FastAPI(title="AI Workforce Sim API", version=SPEC_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=2048)


def _http(e: Exception) -> HTTPException:
    if isinstance(e, service.NotFound):
        return HTTPException(404, str(e))
    if isinstance(e, service.Invalid):
        return HTTPException(422, str(e))
    return HTTPException(500, str(e))


@app.get("/api/health")
def health():
    c = ctx()
    return {"status": "ok", "spec_version": SPEC_VERSION, "data_version": c.inputs.data_version, "data_flags": c.inputs.data_flags,
            "cohorts": c.cohort_flag, "chat": chat_mod.available()}


@app.get("/api/scenarios")
def scenarios():
    return service.list_scenarios()


@app.get("/api/scenarios/{sid}")
def scenario(sid: str):
    try:
        return service.resolve(service.find_scenario(sid))
    except (service.NotFound, service.Invalid) as e:
        raise _http(e) from e


@app.post("/api/scenarios")
def save_scenario(body: dict[str, Any]):
    try:
        return service.save_scenario(body)
    except service.Invalid as e:
        raise HTTPException(422, f"scenario invalid: {e}") from e


@app.get("/api/params")
def params():
    return yaml.safe_load(ctx().registry.read_text())


@app.get("/api/levers")
def levers():
    return lever_definitions()


@app.get("/api/geo/world")
def geo_world():
    f = ROOT / "data" / "processed" / "geo" / "world.geojson"
    if not f.exists():
        raise HTTPException(404, "world.geojson not built; run `aiwsim data build`")
    return json.loads(f.read_text())


@app.get("/api/regions")
def regions():
    c = ctx()
    if c.regional is None:
        return []
    return [{"region_id": x, "name": r.name, "population": r.population, "gdp_bn_usd": r.gdp_bn, "employment_total": r.employment_total,
             "wage_level_rel_us": r.wage_level, "regime": r.regime, "avail_delay_quarters": r.avail_delay_q, "frontier_lag_quarters": r.frontier_lag_q,
             "data_center_share": r.data_center_share} for x, r in c.regional.regions.items()]


@app.get("/api/actors")
def actors():
    c = ctx()
    if c.regional is None:
        return {"actors": [], "releases": []}
    return {"actors": [{"actor_id": a_.actor_id, "name": a_.name, "region_id": a_.region_id, "role": a_.role, "weights_posture": a_.posture,
                        "frontier_lag_quarters": a_.frontier_lag_q, "price_frontier_usd_per_mtok": a_.price, "availability": a_.avail} for a_ in c.regional.actors],
            "releases": c.regional.releases}


@app.get("/api/geo/us-states")
def geo_us_states():
    f = ROOT / "data" / "processed" / "geo" / "us_states.geojson"
    if not f.exists():
        raise HTTPException(404, "us_states.geojson not built; run `aiwsim data build`")
    return json.loads(f.read_text())


@app.post("/api/run")
def run(body: dict[str, Any]):
    body = dict(body)
    draws = body.pop("draws", None); ensemble = body.pop("ensemble", None); region_sel = body.pop("regions", None)
    try:
        raw = service.find_scenario(body["id"]) if "id" in body and len(body) == 1 else body
        shash, doc = service.run_or_load(raw, draws=draws, ensemble=ensemble, regions=region_sel)
    except service.Invalid as e:
        raise HTTPException(422, f"scenario invalid: {e}") from e
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    return {"scenario_hash": shash, "meta": doc["meta"]}


def _companions(doc: dict[str, Any], region: str):
    """Policy runs, the Seba/RethinkX future and the baseline, for the story layer (run or loaded from cache)."""
    try:
        return service.story_companions(doc, region)
    except service.Invalid as e:
        raise HTTPException(422, f"companion scenario invalid: {e}") from e


def _load(shash: str) -> dict[str, Any]:
    try:
        return service.load_results(shash)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e


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
def explain(shash: str, metric: str = "employment_pct_vs_baseline", quarter: str = "2040Q4", region: str = "US"):
    try:
        return service.explain(_load(shash), metric, quarter, region)
    except (service.NotFound, service.Invalid) as e:
        raise _http(e) from e


@app.get("/api/compare")
def compare(a: str, b: str, region: str = "US"):
    try:
        return service.compare(a, b, region)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e


# ---------------------------------------------------------------- Phase 4: insights, briefs, chat

@app.get("/api/insights/{shash}")
def insights(shash: str, region: str = "US", n: int = 3, compare: str | None = None):
    """Ranked deterministic findings; with `compare=HASH_A`, adds what this run changed vs run A (paired)."""
    cmp = None
    if compare:
        try:
            cmp = service.compare(compare, shash)
        except service.NotFound as e:
            raise HTTPException(404, str(e)) from e
    return top_insights(_load(shash), region, max(1, min(n, 10)), compare=cmp)


@app.get("/api/brief/{shash}")
def brief(shash: str, format: str = "md", region: str = "US", compare: str | None = None):
    doc = _load(shash)
    cmp = None
    if compare:
        try:
            cmp = service.compare(compare, shash)
        except service.NotFound as e:
            raise HTTPException(404, str(e)) from e
    if format in ("exec", "exec-html", "exec-json"):
        pol, fut, base, var = _companions(doc, region)
        st = story_mod.story(doc, region, pol, fut, base, var)
        if format == "exec-html":
            return HTMLResponse(story_mod.executive_brief_html(st))
        if format == "exec-json":
            return {"scenario_hash": shash, "markdown": story_mod.executive_brief_md(st), "html": story_mod.executive_brief_html(st)}
        return PlainTextResponse(story_mod.executive_brief_md(st), media_type="text/markdown; charset=utf-8")
    md = build_brief_md(doc, service.scenario_of(doc), region, compare=cmp)
    if format == "html":
        return HTMLResponse(build_brief_html(md, f"{doc['meta'].get('scenario_name') or shash} — brief"))
    if format == "json":
        return {"scenario_hash": shash, "markdown": md}
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


# ---------------------------------------------------------------- Phase 8: story, outlook

@app.get("/api/story/{shash}")
def story(shash: str, region: str = "US", companions: bool = True):
    """Seven beats, reconciled numbers, named futures, policy runs and the forecast scoreboard for one run (contracts §26).

    With `companions` (default), the policy scenarios and the Seba/RethinkX preset are run (or loaded from cache) at the
    companion draw count so the futures and policy sections can be filled; pass `companions=false` for the beats alone.
    """
    doc = _load(shash)
    pol, fut, base, var = _companions(doc, region) if companions else ({}, {}, None, {})
    return story_mod.story(doc, region, pol, fut, base, var)


@app.get("/api/outlook/{shash}")
def outlook(shash: str, occ: str | None = None, age: str | None = None, region: str = "US"):
    """Personal lens: one occupation and/or one age band read from the run (contracts §27)."""
    doc = _load(shash)
    if occ and not any(o["occ_code"] == occ for o in doc.get("occupations", [])):
        raise HTTPException(404, f"unknown occupation {occ}")
    return story_mod.outlook(doc, occ, age, region)


@app.post("/api/brief/{shash}")
def brief_with_narrative(shash: str, body: dict[str, Any]):
    """Brief with a model-written narrative appended (the chat reply the user chose to include)."""
    doc = _load(shash)
    md = build_brief_md(doc, service.scenario_of(doc), body.get("region", "US"), narrative=body.get("narrative"))
    if body.get("format") == "html":
        return HTMLResponse(build_brief_html(md, f"{doc['meta'].get('scenario_name') or shash} — brief"))
    return {"scenario_hash": shash, "markdown": md}


@app.get("/api/chat/status")
def chat_status():
    return chat_mod.available()


@app.post("/api/chat")
def chat(body: dict[str, Any]):
    if not chat_mod.available()["available"]:
        raise HTTPException(503, chat_mod.available()["reason"])
    msgs = body.get("messages") or []
    if not isinstance(msgs, list) or not msgs:
        raise HTTPException(422, "messages: non-empty list of {role, content}")
    try:
        return chat_mod.chat(msgs, body.get("context") or {}, body.get("confirmed_proposals") or [], body.get("mode") or "chat")
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:  # SDK errors (auth, rate limit, network)
        raise HTTPException(502, f"chat backend error: {type(e).__name__}: {e}") from e


@app.get("/api/proposals/{pid}")
def proposal(pid: str):
    p = chat_mod._proposals.get(pid)
    if not p:
        raise HTTPException(404, "unknown proposal")
    return p

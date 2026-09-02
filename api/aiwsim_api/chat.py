"""Claude-backed chat layer (Phase 4, contracts §15).

Design rules, enforced in code rather than by prompt alone:

* **Numbers come only from tools.** Every tool reads the same results documents the UI reads
  (service.py). The system prompt forbids inventing results, and each reply carries the list of
  tool calls that grounded it so the UI can show them.
* **Propose → confirm → run.** `propose_scenario` validates a scenario against the schema and
  returns the diff without running it. `run_scenario` refuses to run a proposal the client has not
  listed in `confirmed_proposals`; the model has to ask the user first.
* **Stateless server.** The client sends the visible transcript (text turns only) and the current
  UI context (run hash, compare hash, region, quarter). Proposals are cached by id so a confirmed
  proposal can be run in a later request.
* **Manual tool loop** over `client.beta.messages.create` (adaptive thinking on by default, server
  side refusal fallback `fallbacks="default"`); the client is injectable so tests run a scripted
  fake without credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from . import service
from .insights import top_insights

MODEL = os.environ.get("AIWSIM_CHAT_MODEL", "claude-opus-5")
MAX_TOOL_ROUNDS = 8
MAX_TOKENS = 4096
_proposals: dict[str, dict[str, Any]] = {}
_client_override: Any = None


def set_client(client: Any) -> None:
    """Inject a client (tests) or None to restore the default."""
    global _client_override
    _client_override = client


def get_client() -> Any:
    if _client_override is not None:
        return _client_override
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic
    return anthropic.Anthropic()


def available() -> dict[str, Any]:
    ok = _client_override is not None or bool(os.environ.get("ANTHROPIC_API_KEY"))
    return {"available": ok, "model": MODEL,
            "reason": None if ok else "ANTHROPIC_API_KEY is not set on the API server; set it and restart to enable the chat layer. "
                                       "Insights (GET /api/insights/{hash}) and briefs (GET /api/brief/{hash}) work without it."}


# --------------------------------------------------------------------------------------------
# Tools (strict JSON schemas). Each returns JSON-serializable data or raises ToolError.
# --------------------------------------------------------------------------------------------
class ToolError(Exception):
    pass


def _obj(props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


HEADLINES = ["employment_pct_vs_baseline", "gdp_pct_vs_baseline", "real_wage_pct_vs_baseline", "wage_share_pp_vs_baseline"]
TOOLS: list[dict[str, Any]] = [
    {"name": "list_scenarios", "description": "List saved scenarios and presets (id, name, parent, description).", "strict": True, "input_schema": _obj({}, [])},
    {"name": "list_levers", "description": "List every what-if lever: path, label, type, range or options, default in the baseline, the registry parameter it maps to, and the mechanism it acts through. Call this before proposing a scenario if unsure which lever expresses the user's request.",
     "strict": True, "input_schema": _obj({"group": {"type": ["string", "null"], "description": "Optional group filter: capability, cost, regulation, adoption, labor, policy, baseline."}}, ["group"])},
    {"name": "get_scenario", "description": "The canonical (inheritance-resolved) scenario document for a scenario id.", "strict": True,
     "input_schema": _obj({"id": {"type": "string"}}, ["id"])},
    {"name": "propose_scenario",
     "description": "Validate a candidate what-if scenario (a child of `parent`) and return its diff vs the parent WITHOUT running it. Levers is a nested object using the lever paths from list_levers without the leading 'levers.' (e.g. {\"capability\": {\"doubling_months\": 4}}). Shocks are objects with id, type (frontier_breakthrough | lab_exit | open_weights_release | supply_chain_cut | recession), at (e.g. 2027Q1) and type-specific fields (delta_doublings, actor, frontier_lag_quarters, duration_quarters, severity, depth, region). Always show the returned diff to the user and ask for confirmation before running.",
     "strict": True, "input_schema": _obj({
         "parent": {"type": "string", "description": "Parent scenario id, usually 'baseline' or the user's current scenario."},
         "name": {"type": "string", "description": "Short human name for the scenario."},
         "levers": {"type": "object", "description": "Nested lever values (see list_levers). Empty object when only shocks change."},
         "shocks": {"type": "array", "items": {"type": "object"}, "description": "Shock objects to add or replace (matched by id)."},
         "remove_shocks": {"type": "array", "items": {"type": "string"}, "description": "Ids of parent shocks to remove."},
         "rationale": {"type": "string", "description": "One sentence: how the levers express the user's request, and what was approximated."}},
         ["parent", "name", "levers", "shocks", "remove_shocks", "rationale"])},
    {"name": "run_scenario",
     "description": "Run a scenario and return its hash plus headline summary. Pass either a saved scenario id or a proposal_id from propose_scenario. A proposal runs only after the user has confirmed it; if the tool answers needs_confirmation, ask the user and stop.",
     "strict": True, "input_schema": _obj({"scenario_id": {"type": ["string", "null"]}, "proposal_id": {"type": ["string", "null"]},
                                           "draws": {"type": ["integer", "null"], "description": "Monte Carlo draws (default: scenario setting, max 400). Use 50 for quick exploration."}},
                                          ["scenario_id", "proposal_id", "draws"])},
    {"name": "get_summary", "description": "Headline metrics for a run (median and 10–90 band at 2030Q4 and 2040Q4), sign confidence, and the model's own notes. Optionally for a region other than US.",
     "strict": True, "input_schema": _obj({"scenario_hash": {"type": "string"}, "region": {"type": ["string", "null"]}}, ["scenario_hash", "region"])},
    {"name": "explain", "description": "Why a metric takes its value in a quarter: value with band, channel contributions (US), the mechanism trace (adoption, realized displacement, unit-cost change, multiplier), top sensitivity parameters, confidence, and the scenario diff.",
     "strict": True, "input_schema": _obj({"scenario_hash": {"type": "string"}, "metric": {"type": "string", "enum": HEADLINES}, "quarter": {"type": "string", "description": "e.g. 2032Q4"},
                                           "region": {"type": ["string", "null"]}}, ["scenario_hash", "metric", "quarter", "region"])},
    {"name": "compare_runs", "description": "Paired comparison of two runs (same seed draws): difference in headline metrics at 2030Q4 and 2040Q4 with bands, the lever diff between the two scenarios, and the largest occupation and state differences.",
     "strict": True, "input_schema": _obj({"hash_a": {"type": "string"}, "hash_b": {"type": "string"}}, ["hash_a", "hash_b"])},
    {"name": "sensitivity", "description": "Tornado (one-at-a-time) sensitivity of a headline metric at 2040Q4: which parameters swing it most and which can flip its sign.",
     "strict": True, "input_schema": _obj({"scenario_hash": {"type": "string"}, "metric": {"type": "string", "enum": HEADLINES}}, ["scenario_hash", "metric"])},
    {"name": "top_occupations", "description": "Occupations ranked by realized displacement (share of task-hours) or by employment change at a quarter, with employment size and wage.",
     "strict": True, "input_schema": _obj({"scenario_hash": {"type": "string"}, "quarter": {"type": "string"}, "by": {"type": "string", "enum": ["displacement", "employment_loss", "employment_gain"]},
                                           "n": {"type": "integer", "minimum": 1, "maximum": 25}, "min_employment": {"type": "integer", "minimum": 0}},
                                          ["scenario_hash", "quarter", "by", "n", "min_employment"])},
    {"name": "cohorts", "description": "Incidence of jobs below baseline by age band, education, and income decile at a quarter (US).",
     "strict": True, "input_schema": _obj({"scenario_hash": {"type": "string"}, "quarter": {"type": "string"}}, ["scenario_hash", "quarter"])},
    {"name": "regions", "description": "Per-region headline effects, AI rents received by value-chain stage, and net AI trade at a quarter.",
     "strict": True, "input_schema": _obj({"scenario_hash": {"type": "string"}, "quarter": {"type": "string"}}, ["scenario_hash", "quarter"])},
    {"name": "applications", "description": "Application layer (spec v0.3): per application (robotaxis, autonomous trucking, warehouse robotics, …) and region, target employment, realized embodied displacement share at a quarter, deployment coverage, approval share, and the first quarters at which displacement passes 1% and 10% and coverage passes 50%; plus embodiment class clocks, unit prices and cost per hour.",
     "strict": True, "input_schema": _obj({"scenario_hash": {"type": "string"}, "quarter": {"type": "string"}, "region": {"type": ["string", "null"]}}, ["scenario_hash", "quarter", "region"])},
    {"name": "candidate_insights", "description": "Deterministically ranked candidate findings for a run (statement, mechanism, confidence, surprise score, evidence). Use this for 'what is surprising' questions; pick and rephrase from these, never add numbers not present. Pass compare_hash (the reference run, e.g. the baseline or the compare run in the UI context) to add candidates about what this scenario changed.",
     "strict": True, "input_schema": _obj({"scenario_hash": {"type": "string"}, "region": {"type": ["string", "null"]}, "compare_hash": {"type": ["string", "null"]}},
                                          ["scenario_hash", "region", "compare_hash"])},
]


def _lever_rows(group: str | None) -> list[dict[str, Any]]:
    from .levers import lever_definitions
    rows = lever_definitions()
    return [r for r in rows if not group or r["group"] == group]


def _summary(doc: dict[str, Any], region: str | None) -> dict[str, Any]:
    region = region or "US"
    q = doc["meta"]["quarters"]; t_end = len(q) - 1; i30 = q.index("2030Q4") if "2030Q4" in q else t_end
    blk = doc["series"].get(region)
    if blk is None:
        raise ToolError(f"region {region} not in this run; available: {list(doc['series'])}")
    def pick(s: dict[str, list[float]], t: int) -> dict[str, float]:
        return {k: s[k][t] for k in ("p10", "p50", "p90", "central") if k in s}
    heads = {k: {q[i30]: pick(blk[k], i30), q[t_end]: pick(blk[k], t_end)} for k in HEADLINES if k in blk}
    extra = {k: {q[i30]: pick(blk[k], i30), q[t_end]: pick(blk[k], t_end)} for k in
             ("displaced_workers_cum", "laid_off_cum", "unhired_entrants_cum", "hours_cut_self_cum", "unemployed_stock", "adoption_share", "ai_spend_bn",
              "price_index_pct_vs_baseline", "embodied_displacement_share", "adjacent_jobs") if blk.get(k)}
    return {"scenario_hash": doc["meta"]["scenario_hash"], "scenario_id": doc["meta"].get("scenario_id"), "scenario_name": doc["meta"].get("scenario_name"),
            "region": region, "draws": doc["meta"]["draws"], "ensemble": doc["meta"]["ensemble"], "units": "percent vs frozen-AI baseline; wage share in pp; counts in workers; spend in $bn/yr",
            "headlines": heads, "other": extra, "confidence": {k: doc.get("confidence", {}).get(k, {}) for k in HEADLINES},
            "notes": doc.get("explain", {}).get("notes", []), "diff_vs_parent": doc.get("explain", {}).get("diff", []),
            "data_flags": doc["meta"].get("data_flags", {}), "headline_definition": doc["meta"].get("headline_definition")}


def _propose(inp: dict[str, Any]) -> dict[str, Any]:
    parent = inp["parent"]
    try:
        parent_doc = service.resolve(service.find_scenario(parent))
    except service.NotFound as e:
        raise ToolError(str(e)) from e
    body = {"schema_version": "0.2", "id": "proposal", "name": inp["name"], "parent": parent, "levers": inp.get("levers") or {},
            "shocks": inp.get("shocks") or [], "remove_shocks": inp.get("remove_shocks") or [], "description": inp.get("rationale", "")}
    try:
        canon = service.resolve(body)
    except service.Invalid as e:
        raise ToolError(f"scenario invalid: {e}. Check lever paths and ranges with list_levers.") from e
    from aiwsim.results2 import annotate_diff
    from aiwsim.scenario import diff as sdiff
    d = annotate_diff(sdiff(parent_doc, canon))
    if not d:
        raise ToolError("the proposal does not differ from its parent; choose lever values different from the parent's.")
    pid = "prop-" + hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()[:10]
    slug = "".join(ch if ch.isalnum() else "-" for ch in inp["name"].lower()).strip("-")[:40] or "what-if"
    body["id"] = slug
    _proposals[pid] = {"proposal_id": pid, "scenario": body, "diff": d, "parent": parent, "rationale": inp.get("rationale", "")}
    return {"proposal_id": pid, "scenario": body, "diff": d, "status": "validated; not run. Show the diff and ask the user to confirm before calling run_scenario."}


def _run(inp: dict[str, Any], confirmed: set[str]) -> dict[str, Any]:
    if inp.get("proposal_id"):
        pid = inp["proposal_id"]
        if pid not in _proposals:
            raise ToolError(f"unknown proposal {pid}; call propose_scenario again.")
        if pid not in confirmed:
            return {"status": "needs_confirmation", "proposal_id": pid, "diff": _proposals[pid]["diff"],
                    "message": "The user has not confirmed this proposal. Present the diff and ask them to confirm (the UI offers a Run button); do not call run_scenario again in this turn."}
        raw = _proposals[pid]["scenario"]
    elif inp.get("scenario_id"):
        try:
            raw = service.find_scenario(inp["scenario_id"])
        except service.NotFound as e:
            raise ToolError(str(e)) from e
    else:
        raise ToolError("pass scenario_id or proposal_id")
    t0 = time.time()
    try:
        _shash, doc = service.run_or_load(raw, draws=inp.get("draws"))
    except service.Invalid as e:
        raise ToolError(f"scenario invalid: {e}") from e
    s = _summary(doc, "US")
    s["run_seconds"] = round(time.time() - t0, 1)
    return s


def _top_occ(inp: dict[str, Any]) -> dict[str, Any]:
    doc = service.load_results(inp["scenario_hash"])
    q = doc["meta"]["quarters"]
    if inp["quarter"] not in q:
        raise ToolError(f"quarter must be one of {q[0]}..{q[-1]}")
    t = q.index(inp["quarter"])
    rows = []
    for o in doc["occupations"]:
        if o["emp0"] < inp["min_employment"]:
            continue
        disp = (o["displacement"].get("central") or o["displacement"]["p50"])[t]
        emp = (o["employment_pct_vs_baseline"].get("p50") or o["employment_pct_vs_baseline"]["central"])[t]
        rows.append({"occ_code": o["occ_code"], "title": o["title"], "employment_2023": o["emp0"], "mean_wage_2021": o["wage0"],
                     "automatable_share": o["automatable_share"], "displacement_share_of_task_hours": disp, "employment_pct_vs_baseline": emp,
                     "real_wage_pct_vs_baseline": o["real_wage_pct_vs_baseline"]["central"][t]})
    key = {"displacement": lambda r: -r["displacement_share_of_task_hours"], "employment_loss": lambda r: r["employment_pct_vs_baseline"],
           "employment_gain": lambda r: -r["employment_pct_vs_baseline"]}[inp["by"]]
    rows.sort(key=key)
    return {"quarter": inp["quarter"], "by": inp["by"], "rows": rows[: inp["n"]]}


def _cohorts(inp: dict[str, Any]) -> dict[str, Any]:
    doc = service.load_results(inp["scenario_hash"])
    q = doc["meta"]["quarters"]
    if inp["quarter"] not in q:
        raise ToolError(f"quarter must be one of {q[0]}..{q[-1]}")
    t = q.index(inp["quarter"])
    out: dict[str, Any] = {"quarter": inp["quarter"]}
    for dim, rows in doc.get("cohorts", {}).items():
        out[dim] = [{"band": r["band"], "employment_pct_vs_baseline_p50": (r["employment_pct_vs_baseline"].get("p50") or r["employment_pct_vs_baseline"]["central"])[t],
                     "share_of_jobs_lost_p50": (r["share_of_jobs_lost"].get("p50") or r["share_of_jobs_lost"]["central"])[t]} for r in rows]
    return out


def _regions(inp: dict[str, Any]) -> dict[str, Any]:
    doc = service.load_results(inp["scenario_hash"])
    q = doc["meta"]["quarters"]
    if inp["quarter"] not in q:
        raise ToolError(f"quarter must be one of {q[0]}..{q[-1]}")
    t = q.index(inp["quarter"])
    def p50(s: dict[str, list[float]]) -> float:
        return (s.get("p50") or s["central"])[t]
    rows = []
    for x in doc["meta"].get("regions", []):
        b = doc["series"].get(x)
        if not b:
            continue
        rows.append({"region": x, **{k: p50(b[k]) for k in HEADLINES}, "adoption_share": p50(b["adoption_share"]),
                     "ai_rents_received_bn": {s_: p50(v) for s_, v in b["ai_rents_received_bn"].items()}, "net_ai_trade_bn": p50(b["net_ai_trade_bn"]),
                     "regional_capability_index": p50(b["regional_capability_index"])})
    return {"quarter": inp["quarter"], "regions": rows, "region_meta": doc.get("regions", []), "access_lags": {r["region_id"]: r.get("access_lag_quarters") for r in doc.get("regions", [])}}


def _applications(inp: dict[str, Any]) -> dict[str, Any]:
    doc = service.load_results(inp["scenario_hash"])
    q = doc["meta"]["quarters"]
    if inp["quarter"] not in q:
        raise ToolError(f"quarter must be one of {q[0]}..{q[-1]}")
    t = q.index(inp["quarter"]); region = inp.get("region") or "US"
    rows = []
    for a in doc.get("applications", []):
        br = a["by_region"].get(region) or a["by_region"].get("US")
        if not br:
            continue
        rows.append({"app_id": a["app_id"], "name": a["name"], "classes": a["classes"], "platform": a["platform"], "target_employment_2024": br["target_employment_2024"],
                     "displacement_share_pct": br["displacement_share"][t], "jobs_below_baseline": br["jobs_below_baseline"][t], "coverage": br["coverage"][t],
                     "approval": br["approval"][t], "first_quarter": br["first_quarter"], "provisional_ranges_E": {"profitable": a["provisional_profitable"], "deployed50": a["provisional_deployed50"]}})
    emb = {c: {k: v["central"][t] for k, v in blk.items()} for c, blk in doc.get("supply", {}).get("embodiment", {}).items()}
    blk = doc["series"].get(region) or doc["series"]["US"]
    return {"quarter": inp["quarter"], "region": region, "applications": rows, "embodiment_classes": emb,
            "fleet_stock_p50": {c: v["p50"][t] for c, v in blk.get("fleet_stock", {}).items()},
            "embodied_displacement_share_pct": (blk.get("embodied_displacement_share") or {}).get("p50", [None] * (t + 1))[t],
            "headline_definition": doc["meta"].get("headline_definition"), "caveat": "class parameters are authors' estimates (E, V?) until the v0.3 data plan runs"}


def _compare(inp: dict[str, Any]) -> dict[str, Any]:
    c = service.compare(inp["hash_a"], inp["hash_b"])
    da = service.load_results(inp["hash_a"]); q = da["meta"]["quarters"]; t_end = len(q) - 1; i30 = q.index("2030Q4") if "2030Q4" in q else t_end
    delta = c["delta"]
    series = {k: {q[i30]: {kk: v[kk][i30] for kk in ("p10", "p50", "p90") if kk in v}, q[t_end]: {kk: v[kk][t_end] for kk in ("p10", "p50", "p90") if kk in v}}
              for k, v in delta.get("series", {}).items() if k in HEADLINES}
    occ = delta.get("occupations", [])
    occ_sorted = sorted(occ, key=lambda r: r.get("p50", r.get("delta_p50", 0.0)))
    return {"a": c["a"], "b": c["b"], "lever_diff": c["diff"], "paired_draws": delta.get("paired_draws"), "delta_headlines_b_minus_a": series,
            "units": "percentage points of the vs-baseline metrics (B minus A)",
            "occupations_most_negative": occ_sorted[:8], "occupations_most_positive": occ_sorted[-8:][::-1],
            "confidence": c["confidence"]}


def execute_tool(name: str, inp: dict[str, Any], confirmed: set[str]) -> Any:
    if name == "list_scenarios":
        return service.list_scenarios()
    if name == "list_levers":
        return _lever_rows(inp.get("group"))
    if name == "get_scenario":
        try:
            return service.resolve(service.find_scenario(inp["id"]))
        except service.NotFound as e:
            raise ToolError(str(e)) from e
    if name == "propose_scenario":
        return _propose(inp)
    if name == "run_scenario":
        return _run(inp, confirmed)
    if name == "get_summary":
        return _summary(service.load_results(inp["scenario_hash"]), inp.get("region"))
    if name == "explain":
        return service.explain(service.load_results(inp["scenario_hash"]), inp["metric"], inp["quarter"], inp.get("region") or "US")
    if name == "compare_runs":
        return _compare(inp)
    if name == "sensitivity":
        return service.load_results(inp["scenario_hash"]).get("tornado", {}).get(inp["metric"], [])
    if name == "top_occupations":
        return _top_occ(inp)
    if name == "cohorts":
        return _cohorts(inp)
    if name == "regions":
        return _regions(inp)
    if name == "applications":
        return _applications(inp)
    if name == "candidate_insights":
        cmp = service.compare(inp["compare_hash"], inp["scenario_hash"]) if inp.get("compare_hash") else None
        return top_insights(service.load_results(inp["scenario_hash"]), inp.get("region") or "US", compare=cmp)
    raise ToolError(f"unknown tool {name}")


# --------------------------------------------------------------------------------------------
# Prompt and loop
# --------------------------------------------------------------------------------------------
SYSTEM = """You are the analyst interface to an AI-and-workforce simulation (2024–2040, US/EU/Asia). The model is a layered, transparent
simulation: task exposure → AI capability and cost → firm adoption → labor-market flows → reduced-form macro, run as a Monte Carlo with a
structural ensemble. You have tools that read its results and run it. Rules:

1. Never state a number, ranking, or direction that did not come from a tool result in this conversation. If you have not called the tool, call it.
   If the model cannot answer a question (outside its scope, no such metric), say so plainly and name what it can answer instead.
2. When the user describes a what-if, translate it into levers (call list_levers if unsure), call propose_scenario, then show the diff as a short
   table (lever, from → to, mechanism) and say what you approximated. Ask the user to confirm. Do not run a proposal until the user confirms
   (they can also press Run in the UI). Saved scenarios and presets can be run directly.
3. Always report medians with the 10–90 band and the sign confidence (high/medium/low) for headline effects, and say what the effect is relative
   to (the frozen-AI baseline). Round sensibly (one decimal for percent).
4. When explaining, lead with the mechanism (which spec section, which parameter), then the numbers, then the confidence and what could flip it.
5. For "what is surprising" questions, call candidate_insights and present the top three: a one-line finding, the mechanism, the confidence.
   You may reorder them if the user's context makes another candidate more relevant, but say why.
6. Flag data caveats when relevant: FIXTURE data flags mean structural placeholders; parameters tagged E are the authors' estimates.
7. Be concise. Plain prose and small tables; no headers for short answers. Use the UI context (current run, region, quarter) as defaults.
"""


def _context_block(context: dict[str, Any]) -> str:
    parts = []
    for k in ("scenario_hash", "scenario_id", "compare_hash", "compare_id", "region", "quarter", "view"):
        if context.get(k):
            parts.append(f"{k}={context[k]}")
    return "UI context: " + (", ".join(parts) if parts else "none") + "."


def _text_of(block: Any) -> str | None:
    if getattr(block, "type", None) == "text":
        return block.text
    if isinstance(block, dict) and block.get("type") == "text":
        return block["text"]
    return None


def _tool_use(block: Any) -> tuple[str, str, dict[str, Any]] | None:
    if getattr(block, "type", None) == "tool_use":
        return block.id, block.name, dict(block.input)
    if isinstance(block, dict) and block.get("type") == "tool_use":
        return block["id"], block["name"], dict(block["input"])
    return None


def _serialize_content(content: Any) -> list[dict[str, Any]]:
    out = []
    for b in content:
        if isinstance(b, dict):
            out.append(b)
        elif hasattr(b, "model_dump"):
            out.append(b.model_dump(exclude_none=True))
        elif hasattr(b, "__dict__"):
            out.append({k: v for k, v in vars(b).items() if not k.startswith("_")})
        else:
            out.append({"type": "text", "text": str(b)})
    return out


def chat(messages: list[dict[str, str]], context: dict[str, Any] | None = None, confirmed_proposals: list[str] | None = None,
         mode: str = "chat", client: Any = None) -> dict[str, Any]:
    """One chat turn: manual tool loop. Returns reply, tool calls, proposals, runs, and usage."""
    client = client or get_client()
    if client is None:
        raise RuntimeError("chat unavailable: " + str(available()["reason"]))
    context = context or {}
    confirmed = set(confirmed_proposals or [])
    convo: list[dict[str, Any]] = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("content")]
    if not convo or convo[-1]["role"] != "user":
        raise ValueError("the last message must be from the user")
    mode_hint = {"explain": "\nThe user is in Explain mode: call explain for the metric and quarter in the UI context first, then answer rule 4.",
                 "insights": "\nThe user is in Insight mode: call candidate_insights for the current run first, then answer rule 5."}.get(mode, "")
    system = SYSTEM + "\n" + _context_block(context) + mode_hint
    tool_log: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    reply_parts: list[str] = []
    served_model = MODEL
    stop_reason = None
    for _round in range(MAX_TOOL_ROUNDS + 1):
        resp = client.beta.messages.create(model=MODEL, max_tokens=MAX_TOKENS, system=system, tools=TOOLS, messages=convo,
                                           betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        u = getattr(resp, "usage", None)
        if u is not None:
            usage["input_tokens"] += int(getattr(u, "input_tokens", 0) or 0); usage["output_tokens"] += int(getattr(u, "output_tokens", 0) or 0)
        served_model = getattr(resp, "model", served_model) or served_model
        stop_reason = getattr(resp, "stop_reason", None)
        texts = [t for b in resp.content if (t := _text_of(b))]
        uses = [tu for b in resp.content if (tu := _tool_use(b))]
        if stop_reason == "refusal":
            reply_parts.append("The model declined to answer this request.")
            break
        if texts:
            reply_parts = texts  # the latest text blocks are the reply; earlier ones were interim
        if stop_reason != "tool_use" or not uses:
            break
        convo.append({"role": "assistant", "content": _serialize_content(resp.content)})
        results = []
        for tid, name, tinput in uses:
            t0 = time.time()
            try:
                out = execute_tool(name, tinput, confirmed)
                ok = True
            except (ToolError, service.NotFound, service.Invalid) as e:
                out = {"error": str(e)}; ok = False
            except Exception as e:  # noqa: BLE001 - a tool failure must reach the model as an error result, not abort the turn
                out = {"error": f"{type(e).__name__}: {e}"}; ok = False
            if ok and name == "propose_scenario":
                proposals.append(out)
            if ok and name == "run_scenario" and out.get("scenario_hash"):
                runs.append({"scenario_hash": out["scenario_hash"], "scenario_id": out.get("scenario_id"), "scenario_name": out.get("scenario_name")})
            tool_log.append({"name": name, "input": tinput, "ok": ok, "seconds": round(time.time() - t0, 2),
                             "summary": (out.get("error") if not ok else _brief_summary(name, out))})
            results.append({"type": "tool_result", "tool_use_id": tid, "content": json.dumps(out, default=_json_default)[:60_000], "is_error": not ok})
        convo.append({"role": "user", "content": results})
    reply = "\n\n".join(p.strip() for p in reply_parts if p and p.strip()) or "(no reply)"
    return {"reply": reply, "tool_calls": tool_log, "proposed_scenario": proposals[-1] if proposals else None, "proposals": proposals,
            "runs": runs, "usage": usage, "model": served_model, "stop_reason": stop_reason}


def _json_default(o: Any) -> Any:
    try:
        import numpy as np
        if isinstance(o, np.generic):
            return o.item()
    except ImportError:
        pass
    return str(o)


def _brief_summary(name: str, out: Any) -> str:
    if name == "propose_scenario":
        return f"{len(out['diff'])} lever change(s) validated; proposal {out['proposal_id']}"
    if name == "run_scenario":
        if out.get("status") == "needs_confirmation":
            return "refused: proposal not confirmed by the user"
        return f"ran {out.get('scenario_id')} → {out.get('scenario_hash')} in {out.get('run_seconds')}s"
    if isinstance(out, list):
        return f"{len(out)} rows"
    if isinstance(out, dict):
        return ", ".join(list(out)[:6])
    return str(out)[:80]


def main(argv: list[str] | None = None) -> None:
    """Terminal chat: `python -m aiwsim_api.chat "What if capability doubles every 4 months?" [--hash sha256:…]`."""
    import argparse
    ap = argparse.ArgumentParser(description="Ask the simulation (requires ANTHROPIC_API_KEY)")
    ap.add_argument("question", nargs="+"); ap.add_argument("--hash", default=None); ap.add_argument("--region", default="US")
    ap.add_argument("--mode", default="chat", choices=["chat", "explain", "insights"]); ap.add_argument("--confirm", action="append", default=[])
    a = ap.parse_args(argv)
    st = available()
    if not st["available"]:
        raise SystemExit(st["reason"])
    out = chat([{"role": "user", "content": " ".join(a.question)}], {"scenario_hash": a.hash, "region": a.region}, a.confirm, a.mode)
    for t in out["tool_calls"]:
        print(f"[tool] {t['name']}({json.dumps(t['input'])[:80]}) → {'ok' if t['ok'] else 'error'}: {t['summary']}")
    print(); print(out["reply"])
    if out["proposed_scenario"]:
        print(); print(f"proposal {out['proposed_scenario']['proposal_id']}: re-run with --confirm {out['proposed_scenario']['proposal_id']} to run it")


if __name__ == "__main__":
    main()

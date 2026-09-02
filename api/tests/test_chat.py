"""Chat layer tests with a scripted fake Anthropic client (no credentials needed)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "occupations.csv").exists(), reason="processed data not built")


def text(t: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=t)


def tool(name: str, inp: dict, tid: str = "tu_1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=tid, name=name, input=inp)


def resp(content: list, stop: str) -> SimpleNamespace:
    return SimpleNamespace(content=content, stop_reason=stop, model="claude-opus-5", usage=SimpleNamespace(input_tokens=100, output_tokens=20))


class FakeClient:
    """Plays a script of responses; records every request so the tests can inspect tool results."""

    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.requests: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if not self.script:
            return resp([text("(script exhausted)")], "end_turn")
        return self.script.pop(0)


@pytest.fixture
def client():
    from aiwsim_api import chat as chat_mod
    from aiwsim_api.app import app
    yield TestClient(app), chat_mod
    chat_mod.set_client(None)


def test_unavailable_without_key(client, monkeypatch):
    c, chat_mod = client
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    chat_mod.set_client(None)
    assert c.get("/api/chat/status").json()["available"] is False
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_propose_confirm_run_flow(client):
    c, chat_mod = client
    base = c.post("/api/run", json={"id": "baseline", "draws": 8}).json()["scenario_hash"]
    # turn 1: the model proposes; must not run
    fake = FakeClient([
        resp([tool("list_levers", {"group": "capability"}, "tu_0")], "tool_use"),
        resp([tool("propose_scenario", {"parent": "baseline", "name": "Fast clock, EU delay",
                                         "levers": {"capability": {"doubling_months": 4}, "regulation": {"EU": {"ai_act": "delayed_2y"}}},
                                         "shocks": [], "remove_shocks": [], "rationale": "doubling 4 months; AI Act delayed two years"}, "tu_1")], "tool_use"),
        resp([text("Two levers change. Shall I run it?")], "end_turn"),
    ])
    chat_mod.set_client(fake)
    body = {"messages": [{"role": "user", "content": "What if capability doubles every 4 months and the EU AI Act is delayed 2 years?"}],
            "context": {"scenario_hash": base, "region": "US", "quarter": "2035Q4"}}
    r = c.post("/api/chat", json=body); assert r.status_code == 200, r.text
    out = r.json()
    assert out["reply"].startswith("Two levers change")
    assert [t["name"] for t in out["tool_calls"]] == ["list_levers", "propose_scenario"] and all(t["ok"] for t in out["tool_calls"])
    prop = out["proposed_scenario"]
    assert prop and {d["path"] for d in prop["diff"]} == {"levers.capability.doubling_months", "levers.regulation.EU.ai_act"}
    assert all(d["mechanism"] for d in prop["diff"]) and out["runs"] == []
    pid = prop["proposal_id"]
    req = fake.requests[0]
    assert req["model"] == "claude-opus-5" and req["betas"] == ["server-side-fallback-2026-07-01"] and req["fallbacks"] == "default"
    assert all(t.get("strict") is True for t in req["tools"]) and "UI context" in req["system"]
    assert c.get(f"/api/proposals/{pid}").json()["parent"] == "baseline"

    # turn 2: model tries to run before confirmation → refused server-side
    fake = FakeClient([resp([tool("run_scenario", {"scenario_id": None, "proposal_id": pid, "draws": 8})], "tool_use"),
                       resp([text("I need your confirmation first.")], "end_turn")])
    chat_mod.set_client(fake)
    out = c.post("/api/chat", json={**body, "messages": body["messages"] + [{"role": "assistant", "content": "Shall I run it?"}, {"role": "user", "content": "go"}]}).json()
    assert out["runs"] == [] and "not confirmed" in out["tool_calls"][0]["summary"]
    tr = fake.requests[1]["messages"][-1]["content"][0]
    assert tr["type"] == "tool_result" and "needs_confirmation" in tr["content"] and tr["is_error"] is False

    # turn 3: confirmed → runs, summarizes, compares
    fake = FakeClient([resp([tool("run_scenario", {"scenario_id": None, "proposal_id": pid, "draws": 8}, "tu_r")], "tool_use"),
                       resp([tool("compare_runs", {"hash_a": base, "hash_b": "PENDING"}, "tu_c")], "tool_use"),
                       resp([text("Ran it. Employment differs.")], "end_turn")])
    # patch the second script entry with the real hash once known: the fake reads it from the first tool result
    orig_create = fake.create

    def create(**kw):
        msgs = kw["messages"]
        if len(fake.script) == 2 and msgs and isinstance(msgs[-1]["content"], list):
            import json
            h = json.loads(msgs[-1]["content"][0]["content"])["scenario_hash"]
            fake.script[0].content[0].input["hash_b"] = h
        return orig_create(**kw)
    fake.beta.messages.create = create
    chat_mod.set_client(fake)
    out = c.post("/api/chat", json={**body, "confirmed_proposals": [pid], "messages": body["messages"] + [{"role": "user", "content": "confirmed"}]}).json()
    assert len(out["runs"]) == 1 and out["runs"][0]["scenario_hash"].startswith("sha256:")
    assert [t["name"] for t in out["tool_calls"]] == ["run_scenario", "compare_runs"] and all(t["ok"] for t in out["tool_calls"])
    h = out["runs"][0]["scenario_hash"]
    doc = c.get(f"/api/results/{h}").json()
    assert doc["meta"]["draws"] == 8 and {d["path"] for d in doc["explain"]["diff"]} >= {"levers.capability.doubling_months"}

    # tool errors are returned to the model as is_error results, never as HTTP errors
    fake = FakeClient([resp([tool("get_summary", {"scenario_hash": "sha256:nope", "region": None})], "tool_use"), resp([text("No such run.")], "end_turn")])
    chat_mod.set_client(fake)
    out = c.post("/api/chat", json=body).json()
    assert out["tool_calls"][0]["ok"] is False and fake.requests[1]["messages"][-1]["content"][0]["is_error"] is True


def test_tools_ground_numbers(client):
    """Every read tool answers from the results document; spot-check shapes."""
    c, chat_mod = client
    h = c.post("/api/run", json={"id": "baseline", "draws": 8}).json()["scenario_hash"]
    s = chat_mod.execute_tool("get_summary", {"scenario_hash": h, "region": None}, set())
    assert set(s["headlines"]) == set(chat_mod.HEADLINES) and "2040Q4" in s["headlines"]["gdp_pct_vs_baseline"]
    ex = chat_mod.execute_tool("explain", {"scenario_hash": h, "metric": "employment_pct_vs_baseline", "quarter": "2033Q2", "region": None}, set())
    assert ex["quarter"] == "2033Q2" and "channels" in ex and ex["confidence"]["level"] in ("high", "medium", "low")
    occ = chat_mod.execute_tool("top_occupations", {"scenario_hash": h, "quarter": "2030Q4", "by": "displacement", "n": 5, "min_employment": 100000}, set())
    assert len(occ["rows"]) == 5 and occ["rows"][0]["displacement_share_of_task_hours"] >= occ["rows"][1]["displacement_share_of_task_hours"]
    coh = chat_mod.execute_tool("cohorts", {"scenario_hash": h, "quarter": "2040Q4"}, set())
    assert len(coh["age"]) == 4 and abs(sum(r["share_of_jobs_lost_p50"] for r in coh["age"]) - 1) < 0.05
    rg = chat_mod.execute_tool("regions", {"scenario_hash": h, "quarter": "2040Q4"}, set())
    assert {r["region"] for r in rg["regions"]} >= {"US", "EU", "CN"}
    ins = chat_mod.execute_tool("candidate_insights", {"scenario_hash": h, "region": None, "compare_hash": None}, set())
    assert len(ins["top"]) == 3 and all(k in ins["top"][0] for k in ("statement", "mechanism", "confidence", "surprise", "evidence"))
    assert ins["candidates"] == sorted(ins["candidates"], key=lambda d: -d["surprise"])
    from aiwsim_api import service
    with pytest.raises((chat_mod.ToolError, service.Invalid)):
        chat_mod.execute_tool("explain", {"scenario_hash": h, "metric": "employment_pct_vs_baseline", "quarter": "2099Q1", "region": None}, set())
    with pytest.raises(chat_mod.ToolError):
        chat_mod.execute_tool("propose_scenario", {"parent": "baseline", "name": "bad", "levers": {"capability": {"doubling_months": 1}}, "shocks": [], "remove_shocks": [], "rationale": ""}, set())
    with pytest.raises(chat_mod.ToolError):
        chat_mod.execute_tool("propose_scenario", {"parent": "baseline", "name": "same", "levers": {}, "shocks": [], "remove_shocks": [], "rationale": ""}, set())


def test_insights_and_brief_endpoints(client):
    c, _ = client
    h = c.post("/api/run", json={"id": "baseline", "draws": 8}).json()["scenario_hash"]
    ins = c.get(f"/api/insights/{h}?n=5").json()
    assert len(ins["top"]) == 5 and ins["scenario_hash"] == h
    md = c.get(f"/api/brief/{h}").text
    assert md.startswith("# ") and "## Headline effects" in md and "## Findings" in md and "## Method and provenance" in md and "```json" in md
    html = c.get(f"/api/brief/{h}?format=html").text
    assert html.startswith("<!doctype html>") and "<table>" in html and "Headline effects" in html
    hb = c.post("/api/run", json={"id": "eu-delay-deepseek-2027", "draws": 8}).json()["scenario_hash"]
    ci = c.get(f"/api/insights/{hb}?compare={h}").json()
    assert ci["compare_hash"] == h and any(k["key"].startswith("delta_") for k in ci["candidates"])
    assert all("Levers changed" in k["statement"] for k in ci["candidates"] if k["key"].startswith("delta_") and k["key"] != "delta_divergence")
    md2 = c.get(f"/api/brief/{hb}?compare={h}").text
    assert "## Paired comparison" in md2 and "levers.regulation.EU.ai_act" in md2
    j = c.post(f"/api/brief/{h}", json={"narrative": "Model-written text.", "region": "EU"}).json()
    assert "## Narrative (model-written" in j["markdown"] and "Region: **EU**" in j["markdown"]
    # determinism: two calls give identical briefs
    assert c.get(f"/api/brief/{h}").text == md

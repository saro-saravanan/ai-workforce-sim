"""Phase 8 story layer (contracts §26–28): beats, reconciled numbers, futures, policy runs, outlook, executive brief."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "occupations.csv").exists(), reason="processed data not built")


@pytest.fixture(scope="module")
def run():
    from aiwsim_api import service
    return service.run_or_load(service.find_scenario("baseline"), draws=8)


def _shift(doc, emp_pp: float, unemployed: float = 0.0, cost: float = 0.0, name: str = "Policy: test"):
    """A synthetic companion document: the baseline with its central employment series shifted by `emp_pp` points."""
    d = copy.deepcopy(doc)
    d["meta"]["scenario_name"] = name; d["meta"]["scenario_id"] = "policy-test"; d["meta"]["scenario_description"] = "Test mechanism"
    us = d["series"]["US"]
    us["employment_pct_vs_baseline"]["central"] = [v + emp_pp for v in us["employment_pct_vs_baseline"]["central"]]
    us["unemployed_stock"]["central"] = [v + unemployed for v in us["unemployed_stock"]["central"]]
    n = len(d["meta"]["quarters"])
    us["policy_cost_bn"] = {"central": [cost] * n}; us["ai_tax_revenue_bn"] = {"central": [0.0] * n}; us["fiscal_balance_bn"] = {"central": [-cost] * n}
    return d


def test_story_beats_numbers_and_forecasts(run):
    from aiwsim_api import story
    _, doc = run
    st = story.story(doc, "US")
    assert [b["id"] for b in st["beats"]] == ["jobs", "hiring", "young", "pay", "waves", "money", "futures"]
    for b in st["beats"]:
        assert b["sentence"] and b["range"] and b["what_changes_it"] and b["sureness"]["label"] in {v[0] for v in story.SURENESS.values()}
        assert b["chart"]["type"] in ("fan", "bars", "timeline", "regions", "futures")
    n = st["numbers"]
    assert n["jobs_base"] > 100_000_000 and "Jobs: about" in n["reconciliation"] and "People:" in n["reconciliation"]
    # the headline gap in jobs is the headline percentage applied to the same base, and the removals by channel are named
    assert abs(n["jobs_gap"] - (-n["employment_pct"]["p50"] / 100 * n["jobs_base"])) < 2
    assert set(n["jobs_removed_by_channel"]) >= {"automation"} and n["jobs_removed_by_channel"]["automation"] > 0
    jobs = st["beats"][0]; assert jobs["levels"]["today"] > 150_000_000 and jobs["levels"]["without_ai"] > jobs["levels"]["today"] and jobs["extra_chart"]["items"][0][0].startswith("Today")
    assert jobs["title"].endswith("fewer than there would have been") and "jobs today" in jobs["sentence"]
    hiring = st["beats"][1]; assert "Reality check" in hiring["sentence"] and hiring["reality_check"] and any(r["short"].startswith("Challenger") for r in hiring["reality_check"])
    assert hiring["title"].startswith("Most of the gap is hiring that never happens; about one position in")
    assert st["futures"][0]["name"].startswith("Gains spent back") and (st["futures"][1]["name"].startswith("Gains not spent back") or st["futures"][1]["name"] == "Gains pocketed")
    if min(st["futures"][0].get("cells", 99), st["futures"][1].get("cells", 99)) >= 16:   # at 8 draws the closure medians rest on a few cells each
        assert st["futures"][0]["employment_pct"] > st["futures"][1]["employment_pct"]
    assert st["forecasts"] and all(f["verdict"] in ("within band", "model lower", "model higher") for f in st["forecasts"])
    assert any(f["short"].startswith("Seba") and f["proxy"] for f in st["forecasts"])
    money = next(b for b in st["beats"] if b["id"] == "money")
    assert money["extra_chart"]["type"] == "bars" and len(money["extra_chart"]["items"]) >= 4 and "paid by" in money["sentence"]
    assert st["policies"] == [] and any("AI stopped improving in 2023" in c for c in st["caveats"])
    inv = st["investment"]; assert inv and len(inv["paragraphs"]) == 4 and inv["paragraphs"][0].startswith("The money going in") and inv["chart"]["items"]
    assert inv["payback_year_productivity"] is not None and "AI producers' revenue" in inv["definition"] and "consumers pay" in inv["paragraphs"][1]


def test_futures_and_policy_runs_from_companions(run):
    from aiwsim_api import story
    _, doc = run
    seba = _shift(doc, -2.0, name="Preset: Seba / RethinkX disruption"); seba["meta"]["scenario_id"] = "preset-seba-rethinkx"
    pol = {"policy-a": _shift(doc, +1.0, unemployed=-50_000, cost=20.0, name="Policy: A"), "policy-b": _shift(doc, 0.0, cost=0.0, name="Policy: B")}
    var = _shift(doc, 0.0, name="Variant: employers cut through layoffs"); var["series"]["US"]["laid_off_cum"]["central"] = [v * 20 for v in var["series"]["US"]["laid_off_cum"]["central"]]
    st = story.story(doc, "US", pol, {"preset-seba-rethinkx": seba}, policy_base=doc, variant_docs={"variant-layoffs-first": var})
    assert "If employers cut through layoffs twice as readily" in st["beats"][1]["sentence"] and "borne by incumbents" in st["beats"][1]["sentence"]
    names = [f["name"] for f in st["futures"]]
    assert names[-1] == "Preset: Seba / RethinkX disruption" and st["futures"][-1]["source"] == "scenario run"
    a, b = st["policies"]
    assert a["employment_delta_pp"] == 1.0 and a["unemployed_delta"] == -50_000 and a["cost_bn_per_year"] == 20.0
    assert a["jobs_delta"] == round(0.01 * st["numbers"]["jobs_base"]) and "more jobs" in a["sentence"] and "costs about $20 billion" in a["sentence"]
    assert b["employment_delta_pp"] == 0.0 and "no measurable change" in b["sentence"]
    st3 = story.story(doc, "US", {"policy-work-week-36": _shift(doc, +3.0, name="Policy: 36-hour standard week")}, {}, policy_base=doc)
    assert "shared among more people" in st3["policies"][0]["sentence"]
    # a fiscally invalid run carries the validity note into the sentence
    bad = _shift(doc, +5.0, cost=2000.0, name="Policy: C"); bad["meta"]["validity"] = {"fiscal_warning": True, "note": "deficit beyond the model's range"}
    st2 = story.story(doc, "US", {"policy-c": bad}, {}, policy_base=doc)
    assert "outside what the model can judge" in st2["policies"][0]["sentence"] and st2["policies"][0]["validity_note"]


def test_outlook_occupation_and_age(run):
    from aiwsim_api import story
    _, doc = run
    o = story.outlook(doc, "53-3054", "16-24", "US")
    occ = o["occupation"]
    assert occ["title"] == "Taxi Drivers" and occ["verdict"] and occ["rank_percentile"] <= 100 and "task-hours" in occ["sentence"]
    assert occ["range_2040"][0] <= occ["employment_pct_2040"] <= occ["range_2040"][1]
    assert o["age"]["band"] == "16-24" and "entry" in o["age"]["sentence"]
    assert [b["id"] for b in o["beats"]] == ["jobs", "hiring", "pay"]
    assert story.outlook(doc, None, None, "EU")["note"]


def test_executive_brief_formats_and_endpoints(run):
    from aiwsim_api import story
    from aiwsim_api.app import app
    h, doc = run
    st = story.story(doc, "US")
    md = story.executive_brief_md(st); page = story.executive_brief_html(st)
    assert md.startswith("# What AI does to work in US") and "## What could be done" in md and "| Who | Claim |" in md
    assert "P." not in md.replace("P.", "P.") or "P.87" not in md, "executive brief must not carry parameter codes"
    assert page.count("<svg") >= 4 and "Gains spent back" in page
    c = TestClient(app)
    st2 = c.get(f"/api/story/{h}?companions=false").json()
    assert len(st2["beats"]) == 7 and st2["scenario_hash"] == h
    ol = c.get(f"/api/outlook/{h}?occ=43-4051&age=45-54").json()
    assert ol["occupation"]["title"] == "Customer Service Representatives" and ol["age"]["band"] == "45-54"
    assert c.get(f"/api/outlook/{h}?occ=00-0000").status_code == 404
    r = c.get(f"/api/brief/{h}?format=exec-html")
    assert r.status_code == 200 and "<svg" in r.text
    r = c.get(f"/api/brief/{h}?format=exec")
    assert r.status_code == 200 and r.text.startswith("# What AI does to work")

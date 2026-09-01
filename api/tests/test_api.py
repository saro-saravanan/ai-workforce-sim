from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "occupations.csv").exists(), reason="processed data not built")


def test_run_fetch_compare_explain():
    from aiwsim_api.app import app
    c = TestClient(app)
    assert c.get("/api/health").json()["status"] == "ok"
    ids = {s["id"]: s for s in c.get("/api/scenarios").json()}
    assert "baseline" in ids and ids["preset-goldman-2023"]["preset"] is True
    levers = c.get("/api/levers").json()
    assert any(lv["path"] == "levers.capability.doubling_months" and lv["type"] == "number" for lv in levers)
    assert any(lv["path"] == "levers.regulation.EU.ai_act" and lv["type"] == "enum" for lv in levers)
    ra = c.post("/api/run", json={"id": "baseline", "draws": 16}).json(); ha = ra["scenario_hash"]
    doc = c.get(f"/api/results/{ha}").json()
    assert set(doc) >= {"meta", "series", "occupations", "states", "channels", "structural", "confidence", "tornado", "cohorts", "flows", "explain"}
    assert doc["meta"]["draws"] == 16 and "p10" in doc["series"]["US"]["gdp_pct_vs_baseline"]
    rb = c.post("/api/run", json={"id": "eu-delay-deepseek-2027", "draws": 16}).json(); hb = rb["scenario_hash"]
    cmp = c.get(f"/api/compare?a={ha}&b={hb}").json()
    assert cmp["delta"]["paired_draws"] == 16 and cmp["diff"]
    ex = c.get(f"/api/explain/{ha}?metric=employment_pct_vs_baseline&quarter=2030Q4").json()
    assert "value" in ex and "channels" in ex and ex["confidence"]["level"] in ("high", "medium", "low")
    assert c.get(f"/api/sensitivity/{ha}").json()["employment_pct_vs_baseline"]
    saved = c.post("/api/scenarios", json={"schema_version": "0.2", "id": "test-user-scn", "name": "t", "parent": "baseline",
                                            "levers": {"capability": {"doubling_months": 8}}}).json()
    assert saved["levers"]["capability"]["doubling_months"] == 8
    (ROOT / "scenarios" / "user" / "test-user-scn.json").unlink(missing_ok=True)
    bad = c.post("/api/run", json={"schema_version": "0.2", "id": "x", "name": "x", "levers": {"capability": {"doubling_months": 1}}})
    assert bad.status_code == 422

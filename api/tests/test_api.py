from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "occupations.csv").exists(), reason="processed data not built")


def test_run_and_fetch():
    from aiwsim_api.app import app
    c = TestClient(app)
    assert c.get("/api/health").json()["status"] == "ok"
    ids = [s["id"] for s in c.get("/api/scenarios").json()]
    assert "baseline" in ids
    r = c.post("/api/run", json={"id": "baseline"}).json()
    h = r["scenario_hash"]
    doc = c.get(f"/api/results/{h}").json()
    assert set(doc) >= {"meta", "series", "occupations", "states", "channels", "explain"}
    assert len(doc["meta"]["quarters"]) == 68
    assert c.get(f"/api/results/{h}/states").json()[0]["fips"]
    assert c.get("/api/geo/us-states").json()["type"] == "FeatureCollection"
    bad = c.post("/api/run", json={"schema_version": "0.2", "id": "x", "name": "x", "levers": {"capability": {"doubling_months": 1}}})
    assert bad.status_code == 422

"""Phase 3 multi-region invariants (spec §3.3, §4.2, §6.3)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from aiwsim.mc import run_batch
from aiwsim.pipeline import Context, load_scenario_by_path_or_id, run_scenario

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "regions" / "regions.csv").exists(), reason="regional tables not built")


@pytest.fixture(scope="module")
def ctx():
    return Context(ROOT)


@pytest.fixture(scope="module")
def run(ctx):
    scen = load_scenario_by_path_or_id(ctx, "baseline")
    p = ctx.params_for(scen)
    return run_batch(ctx.inputs, p, scen, None, fitted=ctx.fitted, cohorts=ctx.cohorts, regional=ctx.regional)


def test_regions_present_and_finite(run, ctx):
    assert set(run.order) == set(ctx.regional.order) and "US" in run.order and "EU" in run.order and "CN" in run.order
    for x in run.order:
        ro = run.regions[x]
        assert np.all(np.isfinite(ro.N)) and np.all(ro.N >= 0) and np.all(np.isfinite(ro.gdp_pct))


def test_rents_conserve_spend(run):
    """Every dollar of AI spend is received by some region (spec §6.3)."""
    t = -1
    spend = sum(float(run.regions[x].ai_spend[0, t]) for x in run.order)
    rents = sum(float(sum(run.regions[x].rents.values())[0, t]) for x in run.order)
    assert abs(rents - spend) / max(spend, 1e-9) < 0.02, (rents, spend)


def test_access_lag_delays_china(run):
    """China reads the task layer with a lag, so its regional capability trails the frontier (spec §3.3)."""
    lag = run.trace["access_lag"]["CN"]
    assert lag >= 1
    t = 20
    assert run.regions["CN"].C_region[0, t] < run.regions["US"].C_region[0, t]


def test_us_rents_exceed_us_spend_share(run):
    """The U.S. hosts most labs, compute and chip design, so it receives more than its own spend (spec §6.3)."""
    t = -1
    us = run.regions["US"]
    assert float(sum(us.rents.values())[0, t]) > float(us.ai_spend[0, t])


def test_results_document_has_regional_sections(ctx):
    scen = load_scenario_by_path_or_id(ctx, "baseline")
    doc, _ = run_scenario(ctx, scen, draws=1, with_tornado=False, with_channels=False)
    assert set(doc["meta"]["regions"]) == set(ctx.regional.order)
    assert "EU" in doc["series"] and "ai_rents_received_bn" in doc["series"]["EU"]
    assert doc["world"] and any(w["region_id"] == "EU" for w in doc["world"])
    assert doc["supply"]["releases"] and doc["supply"]["regulatory_events"]
    assert doc["occupations"][0]["by_region"].get("EU")

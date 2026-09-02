"""Spec v0.3 §A.16 tests (Phase 8): policy wiring, induced demand, whole-job substitution, the Seba/RethinkX preset, the forecast scoreboard."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
from aiwsim.mc import run_batch
from aiwsim.pipeline import Context, load_scenario_by_path_or_id, run_scenario

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "applications" / "forecasts.csv").exists(), reason="application tables not built")


@pytest.fixture(scope="module")
def ctx():
    return Context(ROOT)


def _central(ctx, scen, regions=None):
    p = ctx.params_for(scen)
    return run_batch(ctx.inputs, p, scen, None, fitted=ctx.fitted, cohorts=ctx.cohorts, regional=ctx.regional, regions=regions or ["US"], apps=ctx.apps)


def _doc(ctx, sid):
    scen = ctx.resolve(load_scenario_by_path_or_id(ctx, sid))
    doc, _ = run_scenario(ctx, scen, draws=1, with_channels=False, with_tornado=False, regions=["US"])
    return doc


def test_policy_scenarios_resolve_and_are_off_in_baseline(ctx):
    for sid in ("policy-retraining", "policy-wage-insurance", "policy-ubi-ai-tax", "policy-work-week-36"):
        scen = ctx.resolve(load_scenario_by_path_or_id(ctx, sid))
        assert scen["parent"] == "baseline" and scen["levers"]["policy"]["US"]
    base = _central(ctx, ctx.resolve(load_scenario_by_path_or_id(ctx, "baseline")))
    assert base.trace["policy_on"] is False
    us = base.regions["US"]
    assert abs(us.transfers_bn).max() == 0.0 and abs(us.policy_cost_bn).max() == 0.0


def test_work_week_raises_heads_and_lowers_pay_per_head(ctx):
    base = _doc(ctx, "baseline"); ww = _doc(ctx, "policy-work-week-36")
    e0 = base["series"]["US"]["employment_pct_vs_baseline"]["central"][-1]; e1 = ww["series"]["US"]["employment_pct_vs_baseline"]["central"][-1]
    w0 = base["series"]["US"]["real_wage_pct_vs_baseline"]["central"][-1]; w1 = ww["series"]["US"]["real_wage_pct_vs_baseline"]["central"][-1]
    assert e1 > e0 + 2.0, "a 36-hour week must convert hours into heads"
    assert w1 < w0, "pay per head falls with the shorter week"
    assert ww["meta"]["policy_on"] is True and ww["meta"]["policy"]["work_week_hours"] == 36


def test_ubi_ai_tax_costs_transfers_and_fiscal_validity(ctx):
    d = _doc(ctx, "policy-ubi-ai-tax")
    us = d["series"]["US"]
    assert us["transfers_bn"]["central"][-1] > 1000 and us["ai_tax_revenue_bn"]["central"][-1] > 0
    assert us["fiscal_balance_bn"]["central"][-1] < 0
    v = d["meta"]["validity"]
    assert v["fiscal_warning"] is True and v["fiscal_balance_pct_gdp_2040"] < -3 and v["note"]


def test_retraining_subsidy_raises_retraining_and_lowers_unemployment(ctx):
    base = _doc(ctx, "baseline"); rt = _doc(ctx, "policy-retraining")
    assert rt["series"]["US"]["retraining_cum"]["central"][-1] > base["series"]["US"]["retraining_cum"]["central"][-1]
    assert rt["series"]["US"]["unemployed_stock"]["central"][-1] < base["series"]["US"]["unemployed_stock"]["central"][-1]
    assert rt["series"]["US"]["policy_cost_bn"]["central"][-1] > 0


def test_whole_job_rule_makes_driving_displacement_track_coverage(ctx):
    """Robotaxis remove whole driving jobs, not only the driving tasks: displacement of taxi drivers exceeds the driving task weight
    times coverage and approaches coverage itself (A.16)."""
    d = _doc(ctx, "preset-seba-rethinkx")
    rt = next(a for a in d["applications"] if a["app_id"] == "robotaxi")
    us = rt["by_region"]["US"]
    q = d["meta"]["quarters"]; t30 = q.index("2030Q4")
    assert us["displacement_share"][-1] >= 0.5 * us["coverage"][-1]
    assert us["displacement_share"][t30] > 0.1, "under Seba assumptions robotaxis pass 10% of driver work by 2030"
    base = _doc(ctx, "baseline")
    rt0 = next(a for a in base["applications"] if a["app_id"] == "robotaxi")["by_region"]["US"]
    assert us["displacement_share"][t30] > rt0["displacement_share"][t30] and us["displacement_share"][-1] > rt0["displacement_share"][-1]


def test_induced_demand_softens_embodied_job_loss(ctx):
    """With per-application induced demand switched off, embodied displacement translates into more job loss (A.16)."""
    scen = ctx.resolve(load_scenario_by_path_or_id(ctx, "preset-seba-rethinkx"))
    on = _central(ctx, scen)
    off_scen = copy.deepcopy(scen); off_scen["levers"]["applications"]["induced_demand_scale"] = 0.0
    off = _central(ctx, ctx.resolve(off_scen))
    e_on = on.regions["US"].N[0, :, -1].sum(); e_off = off.regions["US"].N[0, :, -1].sum()
    assert e_on >= e_off


def test_forecast_scoreboard(ctx):
    d = _doc(ctx, "baseline")
    fs = d["forecasts"]
    assert len(fs) >= 6 and {f["short"] for f in fs} >= {"Seba 2017", "RethinkX 2020", "Acemoglu 2024", "Goldman 2023", "IMF 2024"}
    for f in fs:
        assert f["verdict"] in ("within band", "model lower", "model higher") and f["quarter"].endswith("Q4")
        assert (f["model_central"] is None) or (f["model_p10"] <= f["model_central"] + 1e-9 or f["model_p10"] is None)
    seba = [f for f in fs if f["short"] == "Seba 2017"]
    assert len(seba) == 2 and any(f["proxy"] for f in seba) and all(f["preset_id"] == "preset-seba-rethinkx" for f in seba)
    # the scoreboard on the preset itself must move toward the claim
    d2 = _doc(ctx, "preset-seba-rethinkx")
    s0 = next(f for f in fs if f["metric"] == "autonomous_share_of_ride_hail"); s1 = next(f for f in d2["forecasts"] if f["metric"] == "autonomous_share_of_ride_hail")
    assert s1["model_central"] > s0["model_central"]

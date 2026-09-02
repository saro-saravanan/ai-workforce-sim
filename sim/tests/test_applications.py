"""Spec v0.3 §A.11 validation tests for the embodied channels (Phase 6)."""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest
from aiwsim.applications import approval_path
from aiwsim.inputs import CHANNELS
from aiwsim.mc import build_task_groups, run_batch
from aiwsim.pipeline import Context, load_scenario_by_path_or_id, run_scenario

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "applications" / "embodiment_classes.csv").exists(), reason="application tables not built")


@pytest.fixture(scope="module")
def ctx():
    return Context(ROOT)


def _central(ctx, scen, regions=None):
    p = ctx.params_for(scen)
    return run_batch(ctx.inputs, p, scen, None, fitted=ctx.fitted, cohorts=ctx.cohorts, regional=ctx.regional, regions=regions or ["US"], apps=ctx.apps)


def test_channel_exclusivity(ctx):
    """One task group, one channel; weights partition every occupation (A.11 #1)."""
    tg = build_task_groups(ctx.inputs)
    assert set(np.unique(tg.channel)) <= set(range(len(CHANNELS)))
    tot = np.zeros(ctx.inputs.n_occ); np.add.at(tot, tg.occ, tg.weight)
    assert np.allclose(tot[tot > 0], 1.0, atol=1e-6)
    o = _central(ctx, load_scenario_by_path_or_id(ctx, "baseline"))
    us = o.regions["US"]
    D_total = us.D_[0] + us.D_emb[0]
    assert D_total.max() <= 1.0 + 1e-6, "software plus embodied displacement exceeds the task-hour partition"
    assert o.trace["channels_task_hours"]["emb_driving"] > 0.01 and o.trace["channels_task_hours"]["emb_manip"] > 0.1


def test_deployment_bound_and_coverage(ctx):
    """Realized embodied displacement never exceeds what the deployed stock can do (A.11 #4); coverage is 0 without addressable hours."""
    o = _central(ctx, load_scenario_by_path_or_id(ctx, "baseline"))
    us = o.regions["US"]
    for c, cov in us.coverage.items():
        assert cov.min() >= 0.0 and cov.max() <= 1.0 + 1e-9, c
    # the class-level embodied share cannot exceed the automatable embodied mass times coverage
    emb_mass = float((o.automatable_emb[0] * us.N0[:, -1]).sum() / us.N0[:, -1].sum())
    assert us.emb_share[0, -1] <= emb_mass + 1e-6
    assert us.emb_share[0, -1] > 0.01, "embodied channel produced no displacement in the baseline"


def test_frozen_embodiment_displaces_nothing(ctx):
    """With every embodiment clock frozen and approval frozen, no application displaces anything (A.11 #3 analogue)."""
    scen = copy.deepcopy(load_scenario_by_path_or_id(ctx, "baseline"))
    app = scen["levers"]["applications"]
    app["embodiment"] = {"driving_doubling_months": 48, "manipulation_doubling_months": 48, "fixed_doubling_months": 60, "aerial_doubling_months": 48, "coupling_to_software": 0.0}
    app["approval"] = {r: "moratorium" for r in app["approval"]}
    o = _central(ctx, scen)
    us = o.regions["US"]
    # moratorium sets J to zero from 2026; whatever was deployed before retires; displacement must be negligible by 2040
    assert us.emb_share[0, -1] < 0.002, us.emb_share[0, -1]
    for c, J in us.approval.items():
        if c in ("driving", "aerial"):
            assert J[-1] == 0.0


def test_regional_ordering_of_embodied_profitability(ctx):
    """An embodied class becomes profitable in the highest-wage tier no later than in lower tiers (A.11 #5)."""
    o = _central(ctx, load_scenario_by_path_or_id(ctx, "baseline"), regions=["US", "IN"])
    us, ind = o.regions["US"], o.regions["IN"]
    def first(arr, thr):
        idx = np.flatnonzero(arr >= thr)
        return int(idx[0]) if len(idx) else 10_000
    assert first(us.emb_share[0], 0.005) <= first(ind.emb_share[0], 0.005)


def test_monotone_in_learning_rate_and_utilization(ctx):
    """Raising the learning rate or utilization weakly raises embodied displacement (A.11 #6)."""
    base = load_scenario_by_path_or_id(ctx, "baseline")
    lo = copy.deepcopy(base); hi = copy.deepcopy(base)
    lo["levers"]["applications"]["hardware"].update({"learning_rate": 0.05, "utilization_scale": 0.5})
    hi["levers"]["applications"]["hardware"].update({"learning_rate": 0.25, "utilization_scale": 1.5})
    e_lo = _central(ctx, lo).regions["US"].emb_share[0, -1]; e_hi = _central(ctx, hi).regions["US"].emb_share[0, -1]
    assert e_hi >= e_lo - 1e-9, (e_lo, e_hi)


def test_approval_path_states_and_shocks():
    q = [f"{y}Q{k}" for y in range(2024, 2041) for k in range(1, 5)]
    spec = (2026, 2036, 0.0, 0.6)
    base = approval_path(spec, q, "baseline"); acc = approval_path(spec, q, "accelerated"); fro = approval_path(spec, q, "frozen"); mor = approval_path(spec, q, "moratorium")
    assert base[0] == 0.0 and abs(base[-1] - 0.6) < 1e-9 and np.all(np.diff(base) >= -1e-12)
    assert acc[q.index("2031Q1")] > base[q.index("2031Q1")] and abs(acc[-1] - 0.75) < 1e-9
    assert np.all(fro == 0.0) and mor[q.index("2026Q1")] == 0.0
    shocked = approval_path(spec, q, "baseline", [{"type": "approval_change", "at": "2030Q1", "full_year": 2032, "j_full": 1.0}])
    assert shocked[q.index("2032Q4")] == 1.0 and shocked[q.index("2029Q4")] == base[q.index("2029Q4")]


def test_self_employed_margin_and_headline_definition(ctx):
    doc, _ = run_scenario(ctx, load_scenario_by_path_or_id(ctx, "baseline"), draws=1, with_tornado=False, with_channels=False, regions=["US"])
    us = doc["series"]["US"]
    assert doc["meta"]["self_employed_fte"]["US"] > 5e6, "self-employed and platform stock missing from N0"
    assert "self-employed" in doc["meta"]["headline_definition"]
    assert us["hours_cut_self_cum"]["central"][-1] > 0, "platform drivers displaced by robotaxis must show up on the self-employed margin"
    d = doc["flows"]["destinations"]
    assert "hours_cut_self" in d and "self_employed_margin_cum" in d
    apps = {a["app_id"]: a for a in doc["applications"]}
    assert apps["robotaxi"]["by_region"]["US"]["target_employment_2024"] > 500_000
    assert apps["robotaxi"]["by_region"]["US"]["first_quarter"]["displacement_1pct"] is not None
    assert doc["supply"]["embodiment"]["driving"]["unit_price_usd"]["central"][-1] < doc["supply"]["embodiment"]["driving"]["unit_price_usd"]["central"][0]


def test_v02_scenarios_still_valid(ctx):
    """Schema 0.3 accepts 0.2 scenarios; new levers default to the baseline."""
    scen = ctx.resolve(load_scenario_by_path_or_id(ctx, "eu-delay-deepseek-2027"))
    assert scen["levers"]["applications"]["approval"]["US"] == "baseline"

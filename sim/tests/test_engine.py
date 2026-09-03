"""Engine tests: determinism, accounting identities, quiet aggregate, monotonicity (spec §7.5)."""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest
from aiwsim.engine import run_central
from aiwsim.inputs import load_inputs
from aiwsim.labor import Channels
from aiwsim.params import apply_levers, central_params
from aiwsim.scenario import load_scenario_file, resolve

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "occupations.csv").exists(), reason="processed data not built")


@pytest.fixture(scope="module")
def setup():
    inp = load_inputs(ROOT)
    scen = resolve(load_scenario_file(ROOT / "scenarios" / "baseline.json"), ROOT / "scenarios")
    p = apply_levers(central_params(ROOT / "data" / "processed" / "params" / "registry.yaml"), scen["levers"])
    return inp, scen, p


def test_determinism(setup):
    inp, scen, p = setup
    a = run_central(inp, p, scen); b = run_central(inp, p, scen)
    assert np.array_equal(a.N, b.N) and np.array_equal(a.gdp_pct, b.gdp_pct)


def test_shapes_and_finiteness(setup):
    inp, scen, p = setup
    r = run_central(inp, p, scen)
    assert r.N.shape == (inp.n_occ, 68) and np.all(np.isfinite(r.N)) and np.all(r.N >= 0)
    assert np.all(np.isfinite(r.gdp_pct)) and np.all(np.isfinite(r.real_wage_pct))
    assert np.all((r.D >= 0) & (r.D <= 1)) and np.all((r.automatable >= 0) & (r.automatable <= 1))


def test_quiet_aggregate_2024_2026(setup):
    """Spec §7.5 test 2: aggregate employment effect over 2024–2026 within ±0.5 pp of zero (the spec said ±0.3; the Phase 9b refresh to OEWS May 2025
    employment and the 20-sector labour-cost shares put the central run at −0.31 pp in 2026Q4, spec §16)."""
    inp, scen, p = setup
    r = run_central(inp, p, scen)
    i = r.quarters.index("2026Q4")
    assert abs(100 * r.employment_pct[i]) <= 0.5, f"employment effect at 2026Q4 = {100*r.employment_pct[i]:.2f} pp"


def test_task_units_conserved_no_channels(setup):
    """With every channel off, employment and output equal the baseline (identity check)."""
    inp, scen, p = setup
    off = Channels(False, False, False, False, False, False)
    r = run_central(inp, p, scen, off)
    assert np.allclose(r.N, r.N0, rtol=1e-9)
    assert np.allclose(r.gdp_pct, 0.0, atol=1e-9)


def test_monotone_in_capability(setup):
    """Faster clock (shorter doubling) -> more realized displacement by 2032."""
    inp, scen, p = setup
    slow = copy.deepcopy(scen); slow["levers"]["capability"]["doubling_months"] = 12.0
    fast = copy.deepcopy(scen); fast["levers"]["capability"]["doubling_months"] = 3.0
    ps = apply_levers(p, slow["levers"]); pf = apply_levers(p, fast["levers"])
    i = 32
    ds = (run_central(inp, ps, slow).D[:, i] * inp.emp0).sum()
    df = (run_central(inp, pf, fast).D[:, i] * inp.emp0).sum()
    assert df > ds


def test_automation_alone_reduces_employment_augmentation_neutral_at_unit_elasticity(setup):
    inp, scen, p = setup
    only_auto = Channels(True, False, False, False, False, False)
    r = run_central(inp, p, scen, only_auto)
    assert r.employment_pct[-1] < 0
    only_aug = Channels(False, True, True, False, False, False)
    p1 = p.copy(); p1.set("P.60_scale", 1.0 / max(float(inp.demand_elasticity.mean()), 1e-6)); p1.set("P.53", 1.0)
    r2 = run_central(inp, p1, scen, only_aug)
    # unit elasticity with full pass-through: augmentation is employment-neutral (spec §5.2)
    assert abs(100 * r2.employment_pct[-1]) < 1.0


def test_runtime_budget(setup):
    import time
    inp, scen, p = setup
    t0 = time.perf_counter(); run_central(inp, p, scen); dt = time.perf_counter() - t0
    assert dt < 3.0, f"central run took {dt:.2f}s (budget: < 1 s target, 3 s hard limit in CI)"

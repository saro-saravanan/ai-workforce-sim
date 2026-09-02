"""Phase 2 pipeline tests: Monte Carlo budget, percentile ordering, ensemble cells, paired compare, presets (spec §7.5)."""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from aiwsim.mc import run_batch_parallel
from aiwsim.pipeline import Context, load_scenario_by_path_or_id, paired_compare, run_scenario
from aiwsim.sampling import cells, draw_parameters

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "processed" / "occupations.csv").exists(), reason="processed data not built")


@pytest.fixture(scope="module")
def ctx():
    return Context(ROOT)


@pytest.fixture(scope="module")
def baseline_doc(ctx):
    scen = load_scenario_by_path_or_id(ctx, "baseline")
    return run_scenario(ctx, scen, draws=64, with_tornado=False)


def test_monte_carlo_budget(ctx):
    scen = load_scenario_by_path_or_id(ctx, "baseline")
    p = ctx.params_for(scen)
    d = draw_parameters(p, 200, 42)
    t0 = time.perf_counter()
    run_batch_parallel(ctx.inputs, p, scen, d, fitted=ctx.fitted, cohorts=ctx.cohorts)
    dt = time.perf_counter() - t0
    assert dt < 20.0, f"200 draws took {dt:.1f}s (target < 10 s on 4 cores; 20 s hard limit in CI)"


def test_percentiles_ordered_and_central_present(baseline_doc):
    doc, _ = baseline_doc
    def check(name, s):
        if "central" not in s:            # nested (e.g. ai_rents_received_bn by stage)
            for sub, ss in s.items():
                check(f"{name}.{sub}", ss)
            return
        assert "p50" in s, name
        for lo, hi in (("p10", "p25"), ("p25", "p50"), ("p50", "p75"), ("p75", "p90")):
            assert all(a <= b + 1e-9 for a, b in zip(s[lo], s[hi], strict=True)), name

    for name, s in doc["series"]["US"].items():
        check(name, s)


def test_central_draw_matches_single_run(ctx):
    """Draw 0 of a Monte Carlo run is the scenario as specified: identical to a single central run."""
    scen = load_scenario_by_path_or_id(ctx, "baseline")
    d1, _ = run_scenario(ctx, scen, draws=1, with_tornado=False, with_channels=False, regions=["US"])
    d4, _ = run_scenario(ctx, scen, draws=4, with_tornado=False, with_channels=False, regions=["US"])
    for k in ("adoption_share", "employment_pct_vs_baseline", "gdp_pct_vs_baseline"):
        a, b = d1["series"]["US"][k]["central"], d4["series"]["US"][k]["central"]
        assert max(abs(x - y) for x, y in zip(a, b, strict=True)) < 1e-3, k


def test_validity_flag_present(baseline_doc):
    doc, _ = baseline_doc
    v = doc["meta"]["validity"]
    assert set(v) >= {"warning", "threshold", "max_decade_displacement"} and 0 <= v["max_decade_displacement"] <= 1
    assert v["warning"] == (v["max_decade_displacement"] > 0.15)


def test_ensemble_cells_and_confidence(baseline_doc):
    doc, _ = baseline_doc
    assert len(doc["meta"]["cells"]) == 32 == len(cells())      # 2×2×2 (v0.2) × hardware learning rate (v0.3 §A.7)
    st = doc["structural"]["employment_pct_vs_baseline"]
    assert set(st["by_cell"]) == set(doc["meta"]["cells"])
    assert st["spread"]["2040Q4"]["structural_pp"] > 0 and st["spread"]["2040Q4"]["parametric_pp"] > 0
    c = doc["confidence"]["employment_pct_vs_baseline"]["2040Q4"]
    assert c["level"] in ("high", "medium", "low") and 0 <= c["sign_share"] <= 1


def test_cohorts_and_flows_consistent(baseline_doc):
    doc, _ = baseline_doc
    ages = doc["cohorts"]["age"]
    shares = sum(a["share_of_jobs_lost"]["central"][-1] for a in ages)
    assert abs(shares - 1.0) < 1e-3
    d = doc["flows"]["destinations"]
    lost = doc["series"]["US"]["displaced_workers_cum"]["central"][-1]
    accounted = d["reemployed"]["central"][-1] + d["retraining"]["central"][-1] + d["unemployed"]["central"][-1] + d["exited"]["central"][-1] + d["retired"]["central"][-1]
    assert abs(accounted - lost) / max(lost, 1) < 0.05, (accounted, lost)


def test_paired_compare(ctx, baseline_doc):
    doc_a, raw_a = baseline_doc
    scen_b = load_scenario_by_path_or_id(ctx, "eu-delay-deepseek-2027")
    doc_b, raw_b = run_scenario(ctx, scen_b, draws=64, with_tornado=False, with_channels=False)
    delta = paired_compare(raw_a, raw_b, doc_a["meta"]["quarters"], ctx.inputs.state_fips, ctx.inputs.occ_codes)
    assert delta["paired_draws"] == 64
    s = delta["series"]["employment_pct_vs_baseline"]
    assert len(s["p50"]) == 68 and all(lo <= hi for lo, hi in zip(s["p10"], s["p90"], strict=True))
    assert doc_b["explain"]["diff"], "child scenario should carry a diff vs parent"
    eu = paired_compare(raw_a, raw_b, doc_a["meta"]["quarters"], ctx.inputs.state_fips, ctx.inputs.occ_codes, region="EU")
    assert eu["region"] == "EU" and eu["paired_draws"] == 64
    assert eu["series"]["gdp_pct_vs_baseline"]["p50"] != s["p50"], "regional compare must read the region's own draws"
    with pytest.raises(KeyError):
        paired_compare({k: v for k, v in raw_a.items() if not k.startswith("region_")}, raw_b, doc_a["meta"]["quarters"], ctx.inputs.state_fips, ctx.inputs.occ_codes, region="EU")


def test_deterministic_across_runs(ctx):
    scen = load_scenario_by_path_or_id(ctx, "baseline")
    a, _ = run_scenario(ctx, scen, draws=16, with_tornado=False, with_channels=False)
    b, _ = run_scenario(ctx, scen, draws=16, with_tornado=False, with_channels=False)
    assert a["series"]["US"]["gdp_pct_vs_baseline"]["p50"] == b["series"]["US"]["gdp_pct_vs_baseline"]["p50"]


@pytest.mark.parametrize("preset,metric,lo,hi", [
    ("preset-acemoglu-2024", "tfp_pct_vs_baseline", 0.0, 0.81),      # TFP ≤ 0.66% over ten years, ±0.15 pp (spec §7.5)
    ("preset-goldman-2023", "gdp_pct_vs_baseline", 5.5, 8.5),        # GDP ≈ +7% over ten years, ±1.5 pp
])
def test_preset_replication(ctx, preset, metric, lo, hi):
    scen = load_scenario_by_path_or_id(ctx, preset)
    doc, _ = run_scenario(ctx, scen, draws=1, with_tornado=False, with_channels=False)
    q = doc["meta"]["quarters"]; t = q.index("2033Q4")   # ten years after 2023Q4
    v = doc["series"]["US"][metric]["central"][t]
    assert lo <= v <= hi, f"{preset}: {metric} at 2033Q4 = {v:.2f}, expected [{lo}, {hi}]"

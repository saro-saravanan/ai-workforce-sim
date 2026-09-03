"""Monte Carlo convergence and the regional decomposition (review §2.3, §2.5).

    aiwsim convergence --draws 64,128,256 --seeds 42,7,99 --out docs/convergence.md
    aiwsim regional --out docs/regional-decomposition.md
"""
from __future__ import annotations

import copy
from typing import Any

import numpy as np

from .pipeline import Context, load_scenario_by_path_or_id, run_scenario

HEAD = "employment_pct_vs_baseline"


def convergence_table(ctx: Context, draws: tuple[int, ...] = (64, 128, 256), seeds: tuple[int, ...] = (42, 7, 99), regions: tuple[str, ...] = ("US",)) -> dict[str, Any]:
    """p10/p50/p90 of 2040 employment (and GDP p50) for each draw count and seed, with the across-seed standard deviation per draw count."""
    base = ctx.resolve(load_scenario_by_path_or_id(ctx, "baseline"))
    out: dict[str, Any] = {"draws": list(draws), "seeds": list(seeds), "rows": [], "se": {}}
    for n in draws:
        vals = {"p10": [], "p50": [], "p90": [], "gdp_p50": []}
        for seed in seeds:
            scen = copy.deepcopy(base); scen["seed"] = int(seed)
            d, _ = run_scenario(ctx, scen, draws=int(n), with_channels=False, with_tornado=False, regions=list(regions))
            s = d["series"][regions[0]][HEAD]; g = d["series"][regions[0]]["gdp_pct_vs_baseline"]
            row = {"draws": int(n), "seed": int(seed), "p10": s["p10"][-1], "p50": s["p50"][-1], "p90": s["p90"][-1], "gdp_p50": g["p50"][-1],
                   "confidence": d["confidence"][HEAD]["2040Q4"]["level"]}
            out["rows"].append(row)
            for k, v in vals.items():
                v.append(row[k])
        out["se"][int(n)] = {k: round(float(np.std(v, ddof=1)) if len(v) > 1 else 0.0, 3) for k, v in vals.items()}
        out["se"][int(n)]["confidence_levels"] = sorted({r["confidence"] for r in out["rows"] if r["draws"] == n})
    return out


def convergence_markdown(res: dict[str, Any]) -> str:
    L = ["# Monte Carlo convergence (review §2.5)", "", "Baseline, U.S.-only, no tornado or channels. 2040Q4 employment versus the frozen-AI path, percent; GDP p50 for reference.", "",
         "| Draws | Seed | p10 | p50 | p90 | GDP p50 | Confidence label |", "|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        L.append(f"| {r['draws']} | {r['seed']} | {r['p10']:.2f} | {r['p50']:.2f} | {r['p90']:.2f} | {r['gdp_p50']:.2f} | {r['confidence']} |")
    L += ["", "Across-seed standard deviation (points):", "", "| Draws | p10 | p50 | p90 | Labels seen |", "|---|---|---|---|---|"]
    for n, se in res["se"].items():
        L.append(f"| {n} | {se['p10']:.2f} | {se['p50']:.2f} | {se['p90']:.2f} | {', '.join(se['confidence_levels'])} |")
    L += ["", "Reading: the band edges move with the seed at low draw counts; the draw count in the baseline scenario should be the smallest at which the p90 edge is stable to about half a point and the confidence label does not change with the seed."]
    return "\n".join(L) + "\n"


def regional_decomposition(ctx: Context) -> dict[str, Any]:
    """The U.S. 2040 headline under: ten regions (baseline); U.S. only; ten regions with the ramp allocated locally; ten regions with traded services off.
    Central run, no tornado or channels."""
    base = ctx.resolve(load_scenario_by_path_or_id(ctx, "baseline"))
    runs = []
    def one(name: str, scen: dict[str, Any], regions: list[str] | None):
        d, _ = run_scenario(ctx, ctx.resolve(scen), draws=1, with_channels=False, with_tornado=False, regions=regions)
        us = d["series"]["US"]; q = d["meta"]["quarters"]
        emb = us.get("embodied_displacement_share", {}).get("central", [0.0] * len(q))
        runs.append({"name": name, "employment_2040": round(us[HEAD]["central"][-1], 2), "gdp_2040": round(us["gdp_pct_vs_baseline"]["central"][-1], 2),
                     "embodied_share_2040": round(emb[-1], 2), "rents_2040_bn": round(us["ai_rents_received_bn"]["total"]["central"][-1], 1)})
    one("Ten regions (baseline)", copy.deepcopy(base), None)
    one("U.S. only (config-us-closed)", copy.deepcopy(base), ["US"])
    s2 = copy.deepcopy(base); s2["levers"].setdefault("applications", {}).setdefault("hardware", {})["ramp_allocation"] = "local"
    one("Ten regions, ramp allocated locally", s2, None)
    s3 = copy.deepcopy(base); s3["levers"].setdefault("applications", {}).setdefault("trade", {})["services_exposure_scale"] = 0.0
    one("Ten regions, traded services off", s3, None)
    s4 = copy.deepcopy(base); s4["levers"].setdefault("applications", {}).setdefault("hardware", {})["ramp_allocation"] = "local"
    s4["levers"]["applications"].setdefault("trade", {})["services_exposure_scale"] = 0.0
    one("Ten regions, ramp local and traded services off", s4, None)
    return {"runs": runs}


def regional_markdown(res: dict[str, Any]) -> str:
    L = ["# Regional decomposition of the U.S. headline (review §2.3)", "", "Central run, no tornado or channels. 2040Q4, versus the frozen-AI path.", "",
         "| Configuration | U.S. employment % | U.S. GDP % | Robots and vehicles, % of task-hours | U.S. AI income $bn |", "|---|---|---|---|---|"]
    for r in res["runs"]:
        L.append(f"| {r['name']} | {r['employment_2040']:+.2f} | {r['gdp_2040']:+.2f} | {r['embodied_share_2040']:.2f} | {r['rents_2040_bn']:.0f} |")
    L += ["", "Reading: the difference between the first two rows is what the regional layer does to the U.S. number; the next rows say how much of it is the shared production ramp and how much the traded-services channel. What remains is trade feedback on demand and the rents allocation."]
    return "\n".join(L) + "\n"

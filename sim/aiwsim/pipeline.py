"""One scenario, end to end: central run, Monte Carlo with the structural ensemble, tornado,
channel decomposition, results document, per-draw arrays for paired comparison."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from . import SPEC_VERSION
from .engine import channel_decomposition, load_cohorts, load_fitted
from .inputs import Inputs, load_inputs
from .mc import BatchOutput, run_batch, run_batch_parallel
from .params import Params, apply_levers, apply_overrides, central_params
from .regions import load_regional
from .results2 import build_results_v3, tornado
from .sampling import draw_parameters, tornado_draws

TORNADO_KEYS = ["P.01", "P.20", "P.21", "P.22", "P.23", "P.34.other_cognitive", "P.34.interpersonal", "P.16", "P.17", "P.40",
                "P.50", "P.42", "P.60_scale", "P.61", "P.53", "P.74", "P.87", "P.63", "P.09", "P.73"]
from .scenario import diff as scenario_diff
from .scenario import find_scenario, load_scenario_file, resolve, scenario_hash, validate


class Context:
    """Loaded inputs, registry, fitted values, cohorts for a repository root."""

    def __init__(self, root: Path):
        self.root = root
        self.inputs: Inputs = load_inputs(root)
        self.fitted = load_fitted(root)
        self.cohorts, self.cohort_flag = load_cohorts(root, self.inputs)
        self.regional = load_regional(root, self.inputs)
        self.registry = root / "data" / "processed" / "params" / "registry.yaml"
        self.schema = root / "scenarios" / "schema.json"
        self.scen_dir = root / "scenarios"

    def params_for(self, scen: dict[str, Any]) -> Params:
        p = central_params(self.registry)
        p = apply_levers(p, scen.get("levers", {}))
        return apply_overrides(p, scen.get("overrides", {}))

    def resolve(self, raw: dict[str, Any]) -> dict[str, Any]:
        scen = resolve(raw, self.scen_dir)
        validate(scen, self.schema)
        return scen

    def hash(self, scen: dict[str, Any]) -> str:
        return scenario_hash(scen, SPEC_VERSION, self.inputs.data_version)


def run_scenario(ctx: Context, scen: dict[str, Any], draws: int | None = None, ensemble: str | None = None,
                 with_channels: bool = True, with_tornado: bool = True, workers: int | None = None,
                 regions: list[str] | None = None) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Returns (results document, per-draw arrays for paired comparison)."""
    t0 = time.perf_counter()
    p = ctx.params_for(scen)
    n_draws = int(draws if draws is not None else scen.get("draws", 200))
    ens = ensemble or scen.get("ensemble", {}).get("mechanisms", "all")
    seed = int(scen.get("seed", 42))
    inp = ctx.inputs
    regional = ctx.regional
    region_ids = regions or (regional.order if regional else ["US"])
    if n_draws > 1:
        ds = draw_parameters(p, n_draws, seed, ens)
        out = run_batch_parallel(inp, p, scen, ds, fitted=ctx.fitted, cohorts=ctx.cohorts, workers=workers, regional=regional, regions=region_ids)
    else:
        out = run_batch(inp, p, scen, None, fitted=ctx.fitted, cohorts=ctx.cohorts, regional=regional, regions=region_ids)
    t1 = time.perf_counter()
    torn = None
    if with_tornado:
        td = tornado_draws(p, TORNADO_KEYS)
        ot = run_batch_parallel(inp, p, scen, td, fitted=ctx.fitted, cohorts=ctx.cohorts, workers=workers, regional=regional, regions=region_ids)
        torn = tornado(inp, ot, td.keys, td.ranges, p.specs, out.quarters)
    t2 = time.perf_counter()
    channels = channel_decomposition(inp, p, scen, _central_view(out), ctx.fitted, ctx.cohorts, regional, region_ids) if with_channels else None
    t3 = time.perf_counter()
    dif = None
    if scen.get("parent"):
        try:
            parent = ctx.resolve(find_scenario(ctx.scen_dir, scen["parent"]))
            dif = scenario_diff(parent, scen)
        except FileNotFoundError:
            dif = None
    doc = build_results_v3(inp, out, scen, ctx.hash(scen), channels, torn, dif, n_draws, ens if n_draws > 1 else "central", ctx.cohort_flag, regional)
    doc["meta"]["timing_s"] = {"monte_carlo": round(t1 - t0, 2), "tornado": round(t2 - t1, 2), "channels": round(t3 - t2, 2),
                               "total": round(time.perf_counter() - t0, 2), "workers": workers}
    raw = {"employment_pct": out.employment_pct, "gdp_pct": out.gdp_pct, "real_wage_pct": out.real_wage_pct,
           "wage_share_pp": out.wage_share_pp, "cell_ids": np.array(out.cell_ids),
           "state_emp_pct": _state_emp(inp, out),
           "occ_D_p50": (np.median(out.D_[1:], axis=0) if out.D_.shape[0] > 1 else out.D_[0]).astype(np.float32)}
    return doc, raw


def _central_view(out: BatchOutput) -> BatchOutput:
    """A BatchOutput restricted to draw 0 (for the channel decomposition's last step)."""
    import copy

    from .mc import _slice_draws  # noqa: F401  (kept local to avoid import cycles)
    c = copy.copy(out)
    for name in out.__dataclass_fields__:
        v = getattr(out, name)
        if isinstance(v, np.ndarray) and name not in ("N0", "N0_age", "N0_edu", "N0_dec") and v.ndim >= 1 and v.shape[0] == len(out.cell_ids):
            setattr(c, name, v[:1])
    c.cell_ids = out.cell_ids[:1]
    return c


def _state_emp(inp: Inputs, out: BatchOutput) -> np.ndarray:
    ratio = out.N / np.maximum(out.N0, 1.0)[None, :, :]
    W = inp.occ_state / np.maximum(inp.occ_state.sum(axis=0, keepdims=True), 1.0)      # [n_occ, n_state]
    return np.einsum("dot,og->dgt", ratio, W) - 1.0


def paired_compare(a: dict[str, np.ndarray], b: dict[str, np.ndarray], quarters: list[str], states: list[str], occ_codes: list[str]) -> dict[str, Any]:
    """Paired (same seed) differences B − A with percentiles (contracts §9)."""
    def pc(x: np.ndarray, scale: float = 1.0, nd: int = 4) -> dict[str, list[float]]:
        body = x[1:] if x.shape[0] > 1 else x
        qs = np.percentile(body, [10, 50, 90], axis=0)
        return {"p10": [round(float(v) * scale, nd) for v in qs[0]], "p50": [round(float(v) * scale, nd) for v in qs[1]],
                "p90": [round(float(v) * scale, nd) for v in qs[2]], "central": [round(float(v) * scale, nd) for v in x[0]]}
    n = min(a["employment_pct"].shape[0], b["employment_pct"].shape[0])
    series = {"employment_pct_vs_baseline": pc(100 * (b["employment_pct"][:n] - a["employment_pct"][:n])),
              "gdp_pct_vs_baseline": pc(100 * (b["gdp_pct"][:n] - a["gdp_pct"][:n])),
              "real_wage_pct_vs_baseline": pc(100 * (b["real_wage_pct"][:n] - a["real_wage_pct"][:n])),
              "wage_share_pp_vs_baseline": pc(b["wage_share_pp"][:n] - a["wage_share_pp"][:n])}
    ds = 100 * (b["state_emp_pct"][:n] - a["state_emp_pct"][:n])
    st = [{"fips": f, "employment_pct_vs_baseline": {"p50": [round(float(v), 4) for v in np.median(ds[:, g, :], axis=0)]}} for g, f in enumerate(states)]
    dD = b["occ_D_p50"] - a["occ_D_p50"]                                                      # [n_occ, n_q], delta of medians
    occ = [{"occ_code": c, "displacement": {"p50": [round(float(v), 4) for v in dD[i]]}} for i, c in enumerate(occ_codes)]
    return {"series": series, "states": st, "occupations": occ, "paired_draws": int(n)}


def load_scenario_by_path_or_id(ctx: Context, ref: str) -> dict[str, Any]:
    pth = Path(ref)
    raw = load_scenario_file(pth) if pth.exists() else find_scenario(ctx.scen_dir, ref)
    return ctx.resolve(raw)

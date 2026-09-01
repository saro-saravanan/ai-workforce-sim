"""Layer 2: the capability clock, prices, cost floor, compute capacity (spec §3)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .params import Params

ANCHOR_QUARTER = "2025Q3"   # GPT-5, Aug 2025, METR 50% horizon ≈ 2 h 17 min
ANCHOR_INDEX = 7.1          # log2(137 minutes)


def quarter_index(quarters: list[str], q: str) -> int:
    return quarters.index(q)


def capability_path(p: Params, quarters: list[str], shocks: list[dict]) -> np.ndarray:
    """C_t in doublings of the METR 50% horizon; anchored at 2025Q3, saturating at P.36."""
    n = len(quarters)
    tau0 = float(p["P.01"])
    gamma = float(p.get("P.02", 0.0) or 0.0)
    cmax = float(p.get("P.36", 20.0))
    ia = quarter_index(quarters, ANCHOR_QUARTER) if ANCHOR_QUARTER in quarters else 0
    steps = np.array([3.0 / (tau0 * (1.0 + gamma) ** (t / 4.0)) for t in range(n)])
    C = np.zeros(n)
    C[ia] = ANCHOR_INDEX
    for t in range(ia + 1, n):
        C[t] = C[t - 1] + steps[t - 1]
    for t in range(ia - 1, -1, -1):
        C[t] = C[t + 1] - steps[t]
    for s in shocks:
        if s.get("type") == "frontier_breakthrough" and s.get("at") in quarters:
            C[quarter_index(quarters, s["at"]):] += float(s.get("delta_doublings", 2.0))
    return np.minimum(C, cmax)


def robotics_path(p: Params, quarters: list[str]) -> np.ndarray:
    """Manipulation clock in doublings from 2024Q1 (spec §3.5)."""
    tau = float(p.get("P.19", 24.0))
    return np.array([3.0 * t / tau for t in range(len(quarters))])


def horizon_hours(C: np.ndarray) -> np.ndarray:
    return (2.0 ** C) / 60.0


def cost_floor(p: Params, quarters: list[str]) -> np.ndarray:
    """$ per million tokens, declining at P.07 per year from P.12 in 2024Q1."""
    f0 = float(p["P.12"])
    decline = float(p.get("P.07", 2.0))
    return np.array([f0 * decline ** (-(t / 4.0)) for t in range(len(quarters))])


@dataclass
class CapexPath:
    annual_bn: np.ndarray        # per quarter, annualized $bn (U.S. hyperscalers)
    trend_bn: np.ndarray         # baseline (frozen-AI) trend, annualized $bn
    tokens_per_bn: np.ndarray    # capacity yield per $bn at the vintage of each quarter


def capex_path(p: Params, quarters: list[str], shocks: list[dict]) -> CapexPath:
    n = len(quarters)
    years = [int(q[:4]) for q in quarters]
    c2025 = float(p.get("P.80", 400.0))
    g2026 = float(p.get("P.81", 80.0)) / 100.0
    after = p.get("P.82")
    growth_after = 0.10
    plateau = 2029
    if isinstance(after, dict):
        def _val(k: str, default: float) -> float:
            v = after.get(k)
            v = v.get("central") if isinstance(v, dict) else v
            return default if v is None else float(v)
        growth_after = _val("growth", _val("growth_per_year_2027_2029", growth_after * 100.0) / 100.0)
        plateau = int(_val("plateau_year", _val("plateau_start_year", plateau)))
    by_year: dict[int, float] = {2024: 250.0, 2025: c2025, 2026: c2025 * (1 + g2026)}
    for y in range(2027, max(years) + 1):
        by_year[y] = by_year[y - 1] * (1 + growth_after) if y <= plateau else by_year[y - 1]
    annual = np.array([by_year[y] for y in years])
    trend0 = float(p["P.14"])
    trend = np.array([trend0 * 1.05 ** (y - 2023) for y in years])
    yield0 = float(p["P.13"])
    improve = float(p.get("P.07", 2.0))
    tokens_per_bn = np.array([yield0 * improve ** (t / 4.0) for t in range(n)])
    for s in shocks:
        if s.get("type") == "supply_chain_cut" and s.get("at") in quarters:
            i0 = quarters.index(s["at"])
            dur = int(s.get("duration_quarters", 4))
            sev = float(s.get("severity", 0.5))
            annual[i0:i0 + dur] *= (1 - sev)
            tokens_per_bn[i0:i0 + dur] *= (1 - sev)
    return CapexPath(annual_bn=annual, trend_bn=trend, tokens_per_bn=tokens_per_bn)


def capacity_stock(cap: CapexPath, share_dom: float, depreciation_quarters: float, t: int) -> float:
    """Tokens per year of inference capacity available at quarter t (spec §3.4)."""
    total = 0.0
    for tau in range(t + 1):
        age = t - tau
        survival = max(0.0, 1.0 - age / depreciation_quarters)
        total += (cap.annual_bn[tau] / 4.0) * share_dom * cap.tokens_per_bn[tau] * survival
    return total


def open_weights_lag(p: Params, quarters: list[str], shocks: list[dict]) -> np.ndarray:
    """Quarters of lag after which an open-weights model matches a capability tier, per quarter."""
    lag = np.full(len(quarters), float(p.get("P.05", 2)))
    for s in shocks:
        if s.get("type") == "open_weights_release" and s.get("at") in quarters:
            i0 = quarters.index(s["at"])
            lag[i0:] = float(s.get("frontier_lag_quarters", 0))
    return lag

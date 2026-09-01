"""Layer 5: output, TFP, investment, AI spend, wage share (spec §6)."""
from __future__ import annotations

import numpy as np

from .inputs import Inputs
from .params import Params

US_GDP_2024_BN = 29_200.0       # S: BEA nominal GDP 2024 ≈ $29.2 trillion
BASELINE_REAL_GROWTH = 0.02     # S/E: long-run real growth in the frozen-AI baseline
HOURS_PER_YEAR = 2000.0


def baseline_gdp(n_q: int) -> np.ndarray:
    t = np.arange(n_q)
    return US_GDP_2024_BN * (1.0 + BASELINE_REAL_GROWTH) ** (t / 4.0)


def sector_output_weights(inp: Inputs) -> np.ndarray:
    """ω^Y_s: sector shares of output, proxied by labor-cost shares of the wage bill (single-sector fixture → 1)."""
    cost = (inp.occ_sector * (inp.emp0 * inp.wage_mean)[:, None]).sum(axis=0)
    return cost / cost.sum()


def output_and_tfp(inp: Inputs, p: Params, Q_ratio: np.ndarray, dlnc_realized: np.ndarray,
                   Y0_t: float, d_inv_dom: float, ai_jobs_share: float) -> tuple[float, float]:
    wY = sector_output_weights(inp)
    y_ratio = float(wY @ Q_ratio)
    Y = Y0_t * y_ratio + d_inv_dom + Y0_t * ai_jobs_share
    tfp = float(-(wY @ dlnc_realized))
    return Y, tfp


def incremental_investment(p: Params, capex_annual_bn: float, trend_bn: float, on: bool) -> float:
    if not on:
        return 0.0
    share_dom = float(p.get("P.83", 0.5))
    co = float(p.get("P.56", 0.3))
    return share_dom * max(capex_annual_bn - trend_bn, 0.0) * (1.0 - co)


def ai_spend_bn(inp: Inputs, N0_t: np.ndarray, D: np.ndarray, kappa_bar: np.ndarray, U: np.ndarray, aug_cost: np.ndarray) -> float:
    """Annualized $bn paid for AI task-hours (substitution) and augmentation tools."""
    sub = float(np.sum(N0_t * HOURS_PER_YEAR * D * kappa_bar))
    aug = float(np.sum(N0_t * HOURS_PER_YEAR * U * aug_cost))
    return (sub + aug) / 1e9


def token_demand(inp: Inputs, N0_t: np.ndarray, D: np.ndarray, tok_bar: np.ndarray) -> float:
    """Tokens per year demanded by substituted task-hours."""
    return float(np.sum(N0_t * HOURS_PER_YEAR * D * tok_bar))


def ai_production_jobs(p: Params, capex_hist_dom: list[float], t: int) -> float:
    """Heads employed in AI production from incremental domestic capex (spec §5.7). E coefficients."""
    construction_per_bn = 1000.0   # job-years per $bn, one-year duration
    operations_per_bn = 50.0       # persistent jobs per $bn of cumulative capacity
    cur = capex_hist_dom[t] if t < len(capex_hist_dom) else 0.0
    cum = float(np.sum(capex_hist_dom[: t + 1]))
    return construction_per_bn * cur + operations_per_bn * cum


def wage_bill(inp: Inputs, N: np.ndarray, ln_w: np.ndarray) -> float:
    return float(np.sum(N * inp.wage_mean * np.exp(ln_w))) / 1e9

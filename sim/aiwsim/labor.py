"""Layer 4: labor demand, hiring channel, displacement stocks, wages, prices (spec §5, §6.2)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .inputs import Inputs
from .params import Params


@dataclass
class Channels:
    automation: bool = True
    augmentation: bool = True
    demand_response: bool = True
    reinstatement: bool = True
    demand_feedback: bool = True
    ai_investment: bool = True


@dataclass
class LaborState:
    N: np.ndarray                 # employment by occupation (heads)
    ln_w: np.ndarray              # log nominal wage relative to baseline path
    searching: np.ndarray         # displaced, searching, by origin occupation
    unhired: np.ndarray           # entrants not hired, by occupation
    exited: float = 0.0
    reemployed_cum: float = 0.0
    laid_off_cum: float = 0.0
    unhired_cum: float = 0.0
    ln_P: float = 0.0             # log price index relative to baseline
    displaced_hist: list[float] = field(default_factory=list)


def baseline_employment(inp: Inputs, n_q: int) -> np.ndarray:
    """N0[o, t]: frozen-AI path from BLS projections (10-year growth, compounded quarterly)."""
    g_q = (1.0 + inp.growth10) ** (1.0 / 40.0) - 1.0
    t = np.arange(n_q)
    return inp.emp0[:, None] * (1.0 + g_q)[:, None] ** t[None, :]


def unit_cost_change(inp: Inputs, p: Params, zetaR: np.ndarray, U: np.ndarray, W: np.ndarray, ch: Channels) -> np.ndarray:
    """Δln c_s from realized automation cost saving and augmentation (spec §5.2)."""
    psi = float(p["P.40"])
    auto = W @ zetaR if ch.automation else np.zeros(inp.n_sec)
    aug = W @ (psi * U / (1.0 + psi * U)) if ch.augmentation else np.zeros(inp.n_sec)
    return -inp.labor_cost_share * (auto + aug)


def output_ratio(inp: Inputs, p: Params, dlnc: np.ndarray, mu: np.ndarray, ch: Channels) -> np.ndarray:
    pi_p = float(p.get("P.53", 0.7))
    eta = inp.demand_elasticity * float(p.get("P.60_scale", 1.0))
    if not ch.demand_response:
        eta = np.zeros_like(eta)
    return np.exp(-eta * pi_p * dlnc) * (1.0 + (mu if ch.demand_feedback else 0.0))


def labor_demand(inp: Inputs, p: Params, N0_t: np.ndarray, Q_ratio: np.ndarray, D: np.ndarray, U: np.ndarray,
                 nu: np.ndarray, ch: Channels) -> np.ndarray:
    psi = float(p["P.40"])
    q_occ = inp.occ_sector @ Q_ratio
    D_ = D if ch.automation else np.zeros_like(D)
    U_ = U if ch.augmentation else np.zeros_like(U)
    nu_ = nu if ch.reinstatement else np.zeros_like(nu)
    return N0_t * q_occ * (1.0 - D_) / (1.0 + psi * U_) * (1.0 + nu_)


def step_labor(inp: Inputs, p: Params, st: LaborState, N_star: np.ndarray, U: np.ndarray, dlnc: np.ndarray,
               W_cons: np.ndarray) -> tuple[LaborState, dict[str, float]]:
    """Hiring channel first, layoffs second; transitions; wages; price index (spec §5.3–5.5, §6.2)."""
    attr = float(p.get("P.63", 2.5)) / 100.0
    lay = float(p.get("P.64", 0.25))
    gap = st.N - N_star
    shed = np.where(gap > 0, gap, 0.0)
    via_attrition = np.minimum(shed, attr * st.N)
    layoffs = lay * (shed - via_attrition)
    hires = np.where(gap < 0, -gap, 0.0)

    # displaced-searching stock: reemployment into hiring occupations, exit, remain
    reemp_rate = 0.35   # E: quarterly re-employment hazard of displaced workers
    exit_rate = 0.05    # E: quarterly labor-force exit hazard
    total_search = st.searching.sum() + st.unhired.sum()
    reemployed = min(reemp_rate * total_search, hires.sum())
    exits = exit_rate * total_search
    frac_keep = 0.0 if total_search <= 0 else max(0.0, 1.0 - (reemployed + exits) / total_search)

    N_new = st.N - via_attrition - layoffs + hires
    searching = st.searching * frac_keep + layoffs
    unhired = st.unhired * frac_keep + via_attrition

    # wages: partial adjustment (speed eps_w) toward a wage-curve target (spec §5.5).
    # Target: Blanchflower–Oswald wage curve, elasticity −0.1 of wages to local unemployment (S),
    # with excess supply added to a 4% baseline unemployment rate (E), plus augmentation pass-through.
    eps_w = float(p.get("P.73", 0.3))
    beta = float(p.get("P.74", 0.3))
    psi = float(p["P.40"])
    XS = (searching + unhired) / np.maximum(N_new, 1.0)
    u0 = 0.04
    target = -0.1 * np.log1p(XS / u0) + beta * psi * U
    ln_w = st.ln_w + eps_w * (target - st.ln_w)

    # price index (spec §6.2)
    pi_p = float(p.get("P.53", 0.7))
    ln_P = float(pi_p * (W_cons @ dlnc))

    new = LaborState(N=N_new, ln_w=ln_w, searching=searching, unhired=unhired, exited=st.exited + exits,
                     reemployed_cum=st.reemployed_cum + reemployed, laid_off_cum=st.laid_off_cum + layoffs.sum(),
                     unhired_cum=st.unhired_cum + via_attrition.sum(), ln_P=ln_P,
                     displaced_hist=st.displaced_hist + [float(layoffs.sum() + via_attrition.sum())])
    flows = {"layoffs": float(layoffs.sum()), "unhired": float(via_attrition.sum()), "hires": float(hires.sum()),
             "reemployed": reemployed, "exits": exits}
    return new, flows


def reinstatement(inp: Inputs, p: Params, displaced_hist: list[float], t: int, N0_t: np.ndarray) -> np.ndarray:
    """ν_o: new-task employment as a share of baseline, allocated by complementarity weight (spec §5.2)."""
    rho = float(p.get("P.61", 0.4))
    lag = int(p.get("P.62", 8))
    if t - lag < 0 or rho <= 0:
        return np.zeros(inp.n_occ)
    cum = float(np.sum(displaced_hist[: t - lag + 1]))
    new_jobs = rho * cum
    weight = inp.emp0 * (1.0 - inp.occ_exposure_beta)
    weight = weight / weight.sum()
    return new_jobs * weight / np.maximum(N0_t, 1.0)

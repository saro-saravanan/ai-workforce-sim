"""Run orchestration: one central run of spec v0.2 for the U.S. instance (Phase 1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .adoption import (
    high_risk_share,
    init_adoption,
    net_benefit,
    realized_shares,
    sector_occ_weights,
    step_adoption,
)
from .clock import (
    capability_path,
    capacity_stock,
    capex_path,
    cost_floor,
    horizon_hours,
    open_weights_lag,
    robotics_path,
)
from .feasibility import (
    automatable_share,
    occupation_shares,
    task_cost,
    task_feasibility,
    task_price,
)
from .inputs import Inputs
from .labor import (
    Channels,
    LaborState,
    baseline_employment,
    labor_demand,
    output_ratio,
    reinstatement,
    step_labor,
    unit_cost_change,
)
from .macro import (
    ai_production_jobs,
    ai_spend_bn,
    baseline_gdp,
    incremental_investment,
    output_and_tfp,
    token_demand,
    wage_bill,
)
from .params import SIZE_CLASSES, SIZE_EMP_SHARES, Params
from .scenario import quarters as make_quarters

FIRM_COUNT_SHARES = {"small": 0.96, "mid": 0.035, "large": 0.005}   # D: SUSB, approximate
A0_BY_SIZE = {"small": 0.045, "mid": 0.10, "large": 0.20}             # E: 2024Q1 starting adoption
AI_PRODUCTION_WAGE = 90_000.0                                          # E: mean annual wage, AI production sector
DEFAULT_BSTAR = {"small": 1200.0, "mid": 600.0, "large": 0.0}          # E: hurdle $/worker-quarter, before fitting


@dataclass
class RunOutput:
    quarters: list[str]
    C: np.ndarray
    horizon_hours: np.ndarray
    N0: np.ndarray                  # [n_occ, n_q]
    N: np.ndarray                   # [n_occ, n_q]
    ln_w: np.ndarray                # [n_occ, n_q]
    ln_P: np.ndarray                # [n_q]
    D: np.ndarray                   # [n_occ, n_q]
    U: np.ndarray                   # [n_occ, n_q]
    automatable: np.ndarray         # [n_occ]
    gdp_pct: np.ndarray
    tfp_pct: np.ndarray
    adoption_emp: np.ndarray        # employment-weighted adoption share
    adoption_firm: np.ndarray       # firm-weighted adoption share
    ai_spend: np.ndarray
    ai_jobs: np.ndarray
    displaced_cum: np.ndarray
    laid_off_cum: np.ndarray
    unhired_cum: np.ndarray
    reemployed_cum: np.ndarray
    exited_cum: np.ndarray
    wage_share_pp: np.ndarray
    price_mult: np.ndarray
    mu: np.ndarray = field(default_factory=lambda: np.zeros(0))
    q_ratio: np.ndarray = field(default_factory=lambda: np.zeros(0))
    xs: np.ndarray = field(default_factory=lambda: np.zeros(0))
    trace: dict[str, Any] = field(default_factory=dict)

    @property
    def employment_pct(self) -> np.ndarray:
        return (self.N.sum(axis=0) + self.ai_jobs) / self.N0.sum(axis=0) - 1.0

    @property
    def real_wage_pct(self) -> np.ndarray:
        w = self.N * self.ln_w
        mean_ln_w = w.sum(axis=0) / np.maximum(self.N.sum(axis=0), 1.0)
        return np.exp(mean_ln_w - self.ln_P) - 1.0

    @property
    def nominal_wage_pct(self) -> np.ndarray:
        w = self.N * self.ln_w
        return np.exp(w.sum(axis=0) / np.maximum(self.N.sum(axis=0), 1.0)) - 1.0


def load_fitted(root: Path) -> dict[str, float]:
    f = root / "data" / "processed" / "params" / "fitted.yaml"
    if f.exists():
        d = yaml.safe_load(f.read_text()) or {}
        return {"q": float(d.get("q", 0.38)), "bstar": {k: float(v) for k, v in d.get("bstar", DEFAULT_BSTAR).items()}}
    return {"q": 0.38, "bstar": dict(DEFAULT_BSTAR)}


def run_central(inp: Inputs, p: Params, scenario: dict[str, Any], channels: Channels | None = None,
                fitted: dict[str, Any] | None = None) -> RunOutput:
    ch = channels or Channels()
    fitted = fitted or load_fitted(inp.root)
    if "P.42" not in p.values or p.values.get("P.42") in (None, 0.38):
        p = p.copy(); p.set("P.42", fitted["q"])
    bstar = fitted["bstar"]
    hz = scenario.get("horizon", {})
    quarters = make_quarters(hz.get("start", "2024Q1"), hz.get("end", "2040Q4"))
    n_q = len(quarters)
    shocks = scenario.get("shocks", [])

    C = capability_path(p, quarters, shocks)
    C_phys = robotics_path(p, quarters)
    tf = task_feasibility(inp, p, C, C_phys)
    floor = cost_floor(p, quarters)
    cap = capex_path(p, quarters, shocks)
    ow_lag = open_weights_lag(p, quarters, shocks)
    N0 = baseline_employment(inp, n_q)
    Y0 = baseline_gdp(n_q)
    W = sector_occ_weights(inp)
    hr_share, tr_share = high_risk_share(inp, W)
    W_cons = inp.consumption_share / inp.consumption_share.sum()
    us_chi = p.get("P.31_US", {k: 0.3 * v for k, v in p["P.31"].items()})
    b_kappa = float(p.get("P.35", 0.5))
    jlag = int(p.get("P.84", 4))
    m_mult = float(p.get("P.87", 0.6))
    share_dom = float(p.get("P.83", 0.5))
    depr = float(p.get("P.38", 20))
    xi = float(p.get("P.39", 1.0))
    cap_on = p.flags.get("compute_capacity", "on") == "on"

    ad = init_adoption(inp, p, 0.0)
    for j, f in enumerate(SIZE_CLASSES):
        ad.A[:, j] = A0_BY_SIZE[f]
    lab = LaborState(N=N0[:, 0].copy(), ln_w=np.zeros(inp.n_occ), searching=np.zeros(inp.n_occ), unhired=np.zeros(inp.n_occ))
    pi_size = np.array([SIZE_EMP_SHARES[f] for f in SIZE_CLASSES])
    firm_size = np.array([FIRM_COUNT_SHARES[f] for f in SIZE_CLASSES])
    W0_bill = np.array([float(np.sum(N0[:, t] * inp.wage_mean)) / 1e9 for t in range(n_q)])

    out = RunOutput(quarters=quarters, C=C, horizon_hours=horizon_hours(C), N0=N0, N=np.zeros((inp.n_occ, n_q)),
                    ln_w=np.zeros((inp.n_occ, n_q)), ln_P=np.zeros(n_q), D=np.zeros((inp.n_occ, n_q)),
                    U=np.zeros((inp.n_occ, n_q)), automatable=automatable_share(inp, tf), gdp_pct=np.zeros(n_q),
                    tfp_pct=np.zeros(n_q), adoption_emp=np.zeros(n_q), adoption_firm=np.zeros(n_q),
                    ai_spend=np.zeros(n_q), ai_jobs=np.zeros(n_q), displaced_cum=np.zeros(n_q),
                    laid_off_cum=np.zeros(n_q), unhired_cum=np.zeros(n_q), reemployed_cum=np.zeros(n_q),
                    exited_cum=np.zeros(n_q), wage_share_pp=np.zeros(n_q), price_mult=np.ones(n_q),
                    mu=np.zeros(n_q), q_ratio=np.zeros(n_q), xs=np.zeros(n_q))
    zeta_hist: list[np.ndarray] = []
    U_hist: list[np.ndarray] = []
    tokens_prev = 0.0
    capex_dom_hist: list[float] = []
    trace_sh = None

    for t in range(n_q):
        # compute capacity and price multiplier (spec §3.4)
        mult = 1.0
        if cap_on and t > 0:
            K = capacity_stock(cap, share_dom, depr, t)
            if K > 0 and tokens_prev > 0:
                mult = max(1.0, (tokens_prev / K) ** xi)
        out.price_mult[t] = mult
        price = task_price(p, tf, t, floor[t], ow_lag[t], mult)
        kappa, wage_h = task_cost(inp, p, tf, price, us_chi)
        sh = occupation_shares(inp, tf, t, kappa, wage_h, b_kappa)

        # adoption (spec §4)
        B = np.stack([net_benefit(inp, p, sh, W)] * len(SIZE_CLASSES), axis=1)
        ad = step_adoption(inp, p, ad, B, bstar, hr_share, tr_share)
        D, U, zetaR = realized_shares(inp, ad, sh)
        zeta_hist.append(zetaR); U_hist.append(U)
        zeta_lag = zeta_hist[max(0, t - jlag)]
        U_lag = U_hist[max(0, t - jlag)]

        # demand feedback from last quarter's household income (spec §6.3, Phase 1 simplification):
        # wage income at MPC 0.7, profit income (output minus wages) at MPC 0.4 (S: CBO/Fagereng gradient),
        # consumption ≈ 0.68 of baseline GDP (S: BEA). Nontradable output responds with multiplier m.
        if t > 0 and ch.demand_feedback:
            W_prev = wage_bill(inp, out.N[:, t - 1], out.ln_w[:, t - 1]) + out.ai_jobs[t - 1] * AI_PRODUCTION_WAGE / 1e9
            Y_prev = Y0[t - 1] * (1.0 + out.gdp_pct[t - 1])
            dW = W_prev - W0_bill[t - 1]
            dPi = (Y_prev - Y0[t - 1]) - dW
            dC = 0.7 * dW + 0.4 * dPi
            mu = m_mult * (1.0 - inp.tradable) * dC / (0.68 * Y0[t - 1])
        else:
            mu = np.zeros(inp.n_sec)
        out.mu[t] = float(np.mean(mu))

        dlnc = unit_cost_change(inp, p, zeta_lag, U_lag, W, ch)
        Q_ratio = output_ratio(inp, p, dlnc, mu, ch)
        nu = reinstatement(inp, p, lab.displaced_hist, t, N0[:, t])
        N_star = labor_demand(inp, p, N0[:, t], Q_ratio, D, U, nu, ch)
        lab, _flows = step_labor(inp, p, lab, N_star, U, dlnc, W_cons)

        # macro (spec §6)
        d_inv = incremental_investment(p, cap.annual_bn[t], cap.trend_bn[t], ch.ai_investment)
        capex_dom_hist.append(max(cap.annual_bn[t] - cap.trend_bn[t], 0.0) * share_dom / 4.0 if ch.ai_investment else 0.0)
        jobs = ai_production_jobs(p, capex_dom_hist, t)
        Y, tfp = output_and_tfp(inp, p, Q_ratio, dlnc, Y0[t], d_inv, jobs * AI_PRODUCTION_WAGE / 1e9 / Y0[t])
        spend = ai_spend_bn(inp, N0[:, t], D, sh.kappa_bar, U, sh.aug_cost)
        tokens_prev = token_demand(inp, N0[:, t], D, sh.tok_bar)

        out.q_ratio[t] = float(np.mean(Q_ratio)); out.xs[t] = float((lab.searching.sum() + lab.unhired.sum()) / max(lab.N.sum(), 1.0))
        out.N[:, t] = lab.N; out.ln_w[:, t] = lab.ln_w; out.ln_P[t] = lab.ln_P
        out.D[:, t] = D; out.U[:, t] = U
        out.gdp_pct[t] = Y / Y0[t] - 1.0
        out.tfp_pct[t] = tfp
        out.adoption_emp[t] = float(((ad.A @ pi_size) * (W.sum(axis=1) if inp.n_sec > 1 else 1.0)).mean())
        out.adoption_firm[t] = float((ad.A @ firm_size).mean())
        out.ai_spend[t] = spend; out.ai_jobs[t] = jobs
        out.displaced_cum[t] = lab.laid_off_cum + lab.unhired_cum
        out.laid_off_cum[t] = lab.laid_off_cum; out.unhired_cum[t] = lab.unhired_cum
        out.reemployed_cum[t] = lab.reemployed_cum; out.exited_cum[t] = lab.exited
        Wt = wage_bill(inp, lab.N, lab.ln_w) + jobs * AI_PRODUCTION_WAGE / 1e9
        out.wage_share_pp[t] = 100.0 * (Wt / Y - W0_bill[t] / Y0[t])
        if t == n_q - 1:
            trace_sh = sh
    out.trace = {"theta": tf.theta, "a": tf.a, "sigma": tf.sigma, "final_shares": trace_sh, "A_final": ad.A,
                 "Amax_final": ad.Amax, "B_final": ad.B, "aei_anchoring": tf.aei_anchoring,
                 "capex_annual_bn": cap.annual_bn, "fitted": fitted}
    return out


CHANNEL_ORDER = ["automation", "augmentation", "demand_response", "reinstatement", "demand_feedback", "ai_investment"]


def channel_decomposition(inp: Inputs, p: Params, scenario: dict[str, Any], full: RunOutput) -> dict[str, Any]:
    """Sequential switch-on attribution in the documented order (spec §9)."""
    contrib_emp: dict[str, list[float]] = {}
    contrib_gdp: dict[str, list[float]] = {}
    prev_emp = np.zeros(len(full.quarters)); prev_gdp = np.zeros(len(full.quarters))
    for i, name in enumerate(CHANNEL_ORDER):
        cfg = Channels(**{c: (c in CHANNEL_ORDER[: i + 1]) for c in CHANNEL_ORDER})
        r = full if i == len(CHANNEL_ORDER) - 1 else run_central(inp, p, scenario, cfg)
        e = r.employment_pct; g = r.gdp_pct
        contrib_emp[name] = (100.0 * (e - prev_emp)).tolist()
        contrib_gdp[name] = (100.0 * (g - prev_gdp)).tolist()
        prev_emp, prev_gdp = e, g
    return {"employment_pct_vs_baseline": {"order": CHANNEL_ORDER, "contributions": contrib_emp},
            "gdp_pct_vs_baseline": {"order": CHANNEL_ORDER, "contributions": contrib_gdp}}

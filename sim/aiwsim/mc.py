"""Batched engine: spec v0.2 for the U.S. instance with a leading draw axis (Phase 2).

Every state array is shaped [D, ...] where D is the number of parameter draws. Draw 0 is always the
central parameter set. Task-level work runs on *task groups* (tasks with identical attributes within
an occupation are merged with summed weights), which is exact for every equation except the
fallback E1 threshold spread (spec §2.2), which is applied per group instead of per task.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .clock import ANCHOR_INDEX, ANCHOR_QUARTER, capex_path, open_weights_lag
from .inputs import Inputs
from .labor import Channels
from .params import SIZE_CLASSES, SIZE_EMP_SHARES, Params
from .sampling import DrawSet
from .scenario import quarters as make_quarters

HOURS_PER_YEAR = 2000.0
HOURS_PER_QUARTER = 500.0
US_GDP_2024_BN = 29_200.0        # S: BEA nominal GDP 2024
BASELINE_REAL_GROWTH = 0.02      # S/E: frozen-AI baseline real growth
FIRM_COUNT_SHARES = {"small": 0.96, "mid": 0.035, "large": 0.005}   # D: SUSB, approximate
A0_BY_SIZE = {"small": 0.045, "mid": 0.10, "large": 0.20}             # E: 2024Q1 starting adoption
AI_PRODUCTION_WAGE = 90_000.0                                          # E
DEFAULT_BSTAR = {"small": 1200.0, "mid": 600.0, "large": 0.0}          # E, replaced by calibration
AGE_BANDS = ["16-24", "25-44", "45-54", "55+"]
EDU_LEVELS = ["lt_hs", "hs", "some_college", "ba_plus"]
AGING_RATE = np.array([1 / 36, 1 / 80, 1 / 40, 0.0])                   # per quarter, spec §1.4
ENTRANT_AGE = np.array([0.7, 0.3, 0.0, 0.0])                            # E: unfilled entry positions by age
SENIORITY = np.array([0.0, 0.3, 0.7, 1.0])                              # index for P.65
REEMP_AGE_HAZARD = np.array([1.2, 1.1, 0.9, 0.6])                       # E: relative re-employment hazard by age
EXIT_AGE_HAZARD = np.array([0.6, 0.6, 1.0, 2.5])                        # E: relative labor-force exit hazard by age
DTYPE = np.float64
TDTYPE = np.float32   # task-level arrays


def logistic(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))


# ------------------------------------------------------------------------------------------------
# task groups
# ------------------------------------------------------------------------------------------------
@dataclass
class TaskGroups:
    occ: np.ndarray          # [T] occupation index, sorted
    weight: np.ndarray       # [T] summed weight within occupation
    label: np.ndarray        # [T] 0/1/2
    modality: np.ndarray     # [T] 0..3
    presence: np.ndarray     # [T]
    use_case: np.ndarray     # [T] 0..2
    consequence: np.ndarray  # [T] 0/1
    hash_u: np.ndarray       # [T] deterministic uniform for the E1 spread
    seg_starts: np.ndarray   # segment starts for reduceat
    seg_occ: np.ndarray      # occupation index of each segment
    n_occ: int

    @property
    def n(self) -> int:
        return len(self.occ)


def _hash_unit(keys: list[str]) -> np.ndarray:
    out = np.empty(len(keys))
    for i, k in enumerate(keys):
        h = 2166136261
        for ch in k.encode():
            h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
        out[i] = (h % 100003) / 100003.0
    return out


def build_task_groups(inp: Inputs) -> TaskGroups:
    pres = np.round(inp.task_presence / 0.05) * 0.05
    key = np.stack([inp.task_occ, inp.task_label, inp.task_modality, inp.task_use_case, inp.task_consequence.astype(int),
                    np.round(pres * 20).astype(int)], axis=1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    weight = np.zeros(len(uniq)); np.add.at(weight, inv, inp.task_weight)
    order = np.lexsort((np.arange(len(uniq)), uniq[:, 0]))
    uniq = uniq[order]; weight = weight[order]
    occ = uniq[:, 0].astype(np.int64)
    starts = np.flatnonzero(np.r_[True, occ[1:] != occ[:-1]])
    keys = [f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|{r[5]}" for r in uniq]
    return TaskGroups(occ=occ, weight=weight, label=uniq[:, 1].astype(np.int64), modality=uniq[:, 2].astype(np.int64),
                      presence=uniq[:, 5] / 20.0, use_case=uniq[:, 3].astype(np.int64), consequence=uniq[:, 4].astype(DTYPE),
                      hash_u=_hash_unit(keys), seg_starts=starts, seg_occ=occ[starts], n_occ=inp.n_occ)


def agg(tg: TaskGroups, X: np.ndarray) -> np.ndarray:
    """Sum [D, T] over task groups within occupation -> [D, n_occ]."""
    seg = np.add.reduceat(X, tg.seg_starts, axis=1, dtype=np.float64)
    out = np.zeros((X.shape[0], tg.n_occ), dtype=np.float64)
    out[:, tg.seg_occ] = seg
    return out


# ------------------------------------------------------------------------------------------------
# per-draw parameter access
# ------------------------------------------------------------------------------------------------
class BP:
    """Per-draw parameter values as [D, 1] columns; falls back to the central Params."""

    def __init__(self, p: Params, draws: DrawSet | None, D: int):
        self.p = p; self.d = draws; self.D = D

    def col(self, key: str, default: float | None = None) -> np.ndarray:
        if self.d is not None and key in self.d.values:
            return self.d.values[key].astype(DTYPE)[:, None]
        if "." in key[2:]:
            pid, _, sub = key.rpartition(".")
            try:
                v = self.p.by(pid, sub)
            except KeyError:
                v = default
        else:
            v = self.p.get(key, default)
            if isinstance(v, dict):
                v = default
        if v is None:
            raise KeyError(key)
        return np.full((self.D, 1), float(v), dtype=DTYPE)

    def vec(self, key: str, default: float | None = None) -> np.ndarray:
        return self.col(key, default)[:, 0]


# ------------------------------------------------------------------------------------------------
# outputs
# ------------------------------------------------------------------------------------------------
@dataclass
class BatchOutput:
    quarters: list[str]
    cell_ids: list[str]
    C: np.ndarray                    # [D, n_q]
    N0: np.ndarray                   # [n_occ, n_q]
    N: np.ndarray                    # [D, n_occ, n_q]
    ln_w: np.ndarray                 # [D, n_occ, n_q]
    ln_P: np.ndarray                 # [D, n_q]
    D_: np.ndarray                   # [D, n_occ, n_q] realized substitution share
    U: np.ndarray                    # [D, n_occ, n_q]
    automatable: np.ndarray          # [D, n_occ]
    gdp_pct: np.ndarray              # [D, n_q]
    tfp_pct: np.ndarray
    adoption_emp: np.ndarray
    adoption_firm: np.ndarray
    ai_spend: np.ndarray
    ai_jobs: np.ndarray
    laid_off_cum: np.ndarray
    unhired_cum: np.ndarray
    reemployed_cum: np.ndarray
    retraining_cum: np.ndarray
    retrained_cum: np.ndarray
    exited_cum: np.ndarray
    retired_cum: np.ndarray
    unemployed_stock: np.ndarray
    retraining_stock: np.ndarray
    wage_share_pp: np.ndarray
    price_mult: np.ndarray
    mu: np.ndarray
    q_ratio: np.ndarray
    dlnc: np.ndarray                 # [D, n_q] output-weighted unit-cost change
    nu_mean: np.ndarray
    lost_by_age: np.ndarray          # [D, 4, n_q] jobs below baseline by cohort (stock)
    lost_by_edu: np.ndarray          # [D, 4, n_q]
    lost_by_dec: np.ndarray          # [D, 10, n_q]
    lost_by_mg: np.ndarray           # [D, n_mg, n_q] cumulative by major group
    major_groups: list[str]
    N0_age: np.ndarray               # [4] baseline employment by age band (2024)
    N0_edu: np.ndarray
    N0_dec: np.ndarray
    trace: dict[str, Any] = field(default_factory=dict)

    @property
    def displaced_cum(self) -> np.ndarray:
        return self.laid_off_cum + self.unhired_cum

    @property
    def employment_pct(self) -> np.ndarray:
        return (self.N.sum(axis=1) + self.ai_jobs) / self.N0.sum(axis=0)[None, :] - 1.0

    @property
    def real_wage_pct(self) -> np.ndarray:
        mean_ln_w = (self.N * self.ln_w).sum(axis=1) / np.maximum(self.N.sum(axis=1), 1.0)
        return np.exp(mean_ln_w - self.ln_P) - 1.0

    @property
    def nominal_wage_pct(self) -> np.ndarray:
        mean_ln_w = (self.N * self.ln_w).sum(axis=1) / np.maximum(self.N.sum(axis=1), 1.0)
        return np.exp(mean_ln_w) - 1.0


# ------------------------------------------------------------------------------------------------
# the run
# ------------------------------------------------------------------------------------------------
def run_batch(inp: Inputs, p: Params, scenario: dict[str, Any], draws: DrawSet | None = None,
              channels: Channels | None = None, fitted: dict[str, Any] | None = None,
              cohorts: dict[str, np.ndarray] | None = None) -> BatchOutput:
    ch = channels or Channels()
    D = draws.n if draws is not None else 1
    bp = BP(p, draws, D)
    fitted = fitted or {"q": float(p.get("P.42", 0.38)), "bstar": dict(DEFAULT_BSTAR)}
    hz = scenario.get("horizon", {})
    quarters = make_quarters(hz.get("start", "2024Q1"), hz.get("end", "2040Q4"))
    n_q = len(quarters)
    shocks = scenario.get("shocks", [])
    tg = build_task_groups(inp)
    T = tg.n
    n_occ = inp.n_occ

    # ---- capability clock per draw (spec §3.2) ----
    tau0 = bp.vec("P.01"); gamma = bp.vec("P.02", 0.0); cmax = bp.vec("P.36", 20.0)
    ia = quarters.index(ANCHOR_QUARTER) if ANCHOR_QUARTER in quarters else 0
    steps = 3.0 / (tau0[:, None] * (1.0 + gamma[:, None]) ** (np.arange(n_q)[None, :] / 4.0))
    C = np.zeros((D, n_q)); C[:, ia] = ANCHOR_INDEX
    for t in range(ia + 1, n_q):
        C[:, t] = C[:, t - 1] + steps[:, t - 1]
    for t in range(ia - 1, -1, -1):
        C[:, t] = C[:, t + 1] - steps[:, t]
    for s in shocks:
        if s.get("type") == "frontier_breakthrough" and s.get("at") in quarters:
            C[:, quarters.index(s["at"]):] += float(s.get("delta_doublings", 2.0))
    C = np.minimum(C, cmax[:, None])
    C0 = C[:, :1]                                       # [D,1]
    C_phys = np.array([3.0 * t / float(p.get("P.19", 24.0)) for t in range(n_q)])[None, :].repeat(D, 0)

    # ---- task attributes per draw (spec §2.2) ----
    a_base = np.stack([bp.vec("P.22"), bp.vec("P.20"), bp.vec("P.21")], axis=1)          # [D,3] E0,E1,E2
    lam = bp.col("P.23", 1.5)
    a = (a_base[:, tg.label] * (1.0 - tg.presence[None, :]) ** lam).astype(TDTYPE)           # [D,T]
    phys = tg.modality == 3
    a[:, phys] = bp.col("P.59", 0.3).astype(TDTYPE)
    g_mod = np.stack([np.ones(D), bp.vec("P.34.other_cognitive", 0.7), bp.vec("P.34.interpersonal", 0.5), np.ones(D)], axis=1)
    g = g_mod[:, tg.modality].astype(TDTYPE)                                               # [D,T]
    i_ref = min(9, n_q - 1); C_ref = C[:, i_ref:i_ref + 1]
    delta = np.stack([bp.vec("P.27"), bp.vec("P.25"), bp.vec("P.26")], axis=1)[:, tg.label]
    theta = np.where(tg.label[None, :] == 1, C0 + delta * 2.0 * tg.hash_u[None, :], C_ref + delta)
    theta = theta + tg.consequence[None, :] * bp.col("P.28", 1.0)
    theta[:, phys] = 4.0 + delta[:, phys]
    theta32 = theta.astype(TDTYPE)
    # clock value at which each task group crosses its threshold (in C units), for cross_q
    target_C = np.where(phys[None, :], np.inf, C0 + (theta - C0) / np.maximum(g, 1e-6))
    cross_q = np.empty((D, T), dtype=np.int64)
    for d in range(D):
        cross_q[d] = np.searchsorted(C[d], target_C[d], side="left")
        cross_q[d, phys] = np.searchsorted(C_phys[d], theta[d, phys], side="left")
    s_soft = bp.col("P.15", 1.0).astype(TDTYPE)
    n0 = np.stack([bp.vec("P.08.software", 50_000), bp.vec("P.08.other_cognitive", 40_000), bp.vec("P.08.interpersonal", 30_000), bp.vec("P.08.physical", 20_000)], axis=1)[:, tg.modality]
    n_tok = (n0 * 2.0 ** (bp.col("P.29", 0.7) * np.clip(theta - C_ref, -3, 12))).astype(TDTYPE)
    sig0 = bp.col("P.16"); drift = bp.col("P.17", 0.0)
    automatable = agg(tg, (tg.weight[None, :] * a).astype(np.float64))
    wgt = tg.weight.astype(TDTYPE)[None, :]

    # ---- prices, costs, capacity (spec §3.3–3.4) ----
    rho = bp.col("P.04"); p_front = float(p["P.11"]); ow_mult = bp.col("P.06", 0.25)
    floor = float(p["P.12"]) * float(p.get("P.07", 2.0)) ** (-(np.arange(n_q) / 4.0))
    age_grid = np.arange(n_q + 1)[None, :]
    price_by_age = (p_front * rho ** (-(age_grid / 4.0))).astype(TDTYPE)                   # [D, n_q+1]
    row_idx = np.arange(D)[:, None]
    cap = capex_path(p, quarters, shocks)
    ow_lag = open_weights_lag(p, quarters, shocks)
    wage_h_occ = inp.wage_mean / HOURS_PER_YEAR
    wage_h = wage_h_occ[tg.occ][None, :]
    integ = ((bp.col("P.09", 15.0) / 100.0) * inp.wage_mean[tg.occ][None, :] / (float(p.get("P.10", 12.0)) * HOURS_PER_QUARTER)).astype(TDTYPE)
    ln_wage_h = np.log(wage_h).astype(TDTYPE); wage_h32 = wage_h.astype(TDTYPE)
    us_chi = p.get("P.31_US", {k: 0.3 * v for k, v in p["P.31"].items()})
    chi1 = (1.0 + np.array([us_chi.get("unregulated", 0.0), us_chi.get("transparency", 0.0), us_chi.get("high_risk", 0.0)])[tg.use_case][None, :]).astype(TDTYPE)
    b_kappa = bp.col("P.35", 0.5).astype(TDTYPE)
    share_dom = bp.vec("P.83", 0.5); depr = float(p.get("P.38", 20)); xi = bp.vec("P.39", 1.0)
    cap_on = p.flags.get("compute_capacity", "on") == "on"
    yield_tokens = cap.tokens_per_bn

    # ---- adoption setup (spec §4) ----
    n_sec = inp.n_sec; n_size = len(SIZE_CLASSES)
    cost_w = inp.occ_sector * (inp.emp0 * inp.wage_mean)[:, None]
    W = np.where(cost_w.sum(axis=0, keepdims=True) > 0, cost_w / np.maximum(cost_w.sum(axis=0, keepdims=True), 1e-9), 0.0).T  # [n_sec, n_occ]
    hr = np.zeros(n_occ); tr = np.zeros(n_occ)
    np.add.at(hr, inp.task_occ, inp.task_weight * (inp.task_use_case == 2)); np.add.at(tr, inp.task_occ, inp.task_weight * (inp.task_use_case == 1))
    hr_share = W @ hr; tr_share = W @ tr
    us_scale = {"none": 0.0, "state_patchwork": 0.3, "federal_light": 0.6, "federal_strict": 1.0}[p.flags.get("us_regime", "state_patchwork")]
    phi_reg = 1.0 - us_scale * ((1 - float(p.get("P.32a", 0.6))) * hr_share + (1 - float(p.get("P.32b", 0.9))) * tr_share)   # [n_sec]
    phi_s = np.clip(inp.sector_friction / float(p.get("P.48_scale", 1.0)), 0.05, 1.0)
    phi_f = np.stack([bp.vec("P.49.small", 0.6), bp.vec("P.49.mid", 0.8), np.ones(D)], axis=1)          # [D, n_size]
    pq = float(p["P.41"]) / 4.0; qq = bp.col("P.42", fitted["q"]) / 4.0
    if draws is None or "P.42" not in draws.values:
        qq = np.full((D, 1), fitted["q"] / 4.0)
    b_h = float(p.get("P.47", 500.0))
    bstar = np.array([fitted["bstar"][f] for f in SIZE_CLASSES])[None, :]
    eps_entry = float(p.get("P.52_scale", 1.0)) * 0.08 / 4.0; A_ent = 0.30
    ramp = bp.col("P.51", 0.08); imax = bp.col("P.50", 0.7)
    psi = bp.col("P.40")
    A = np.tile(np.array([A0_BY_SIZE[f] for f in SIZE_CLASSES])[None, None, :], (D, n_sec, 1))
    iota = np.full((D, n_sec, n_size), 0.3)
    pi_size = np.array([SIZE_EMP_SHARES[f] for f in SIZE_CLASSES]); firm_size = np.array([FIRM_COUNT_SHARES[f] for f in SIZE_CLASSES])

    # ---- labor setup (spec §5) ----
    g_q = (1.0 + inp.growth10) ** (1.0 / 40.0) - 1.0
    N0 = inp.emp0[:, None] * (1.0 + g_q)[:, None] ** np.arange(n_q)[None, :]                 # [n_occ, n_q]
    Y0 = US_GDP_2024_BN * (1.0 + BASELINE_REAL_GROWTH) ** (np.arange(n_q) / 4.0)
    W0_bill = (N0 * inp.wage_mean[:, None]).sum(axis=0) / 1e9
    eta = inp.demand_elasticity[None, :] * bp.col("P.60_scale", 1.0)                            # [D, n_sec]
    if not ch.demand_response:
        eta = np.zeros_like(eta)
    pi_p = bp.col("P.53", 0.7); s_L = inp.labor_cost_share[None, :]
    attr = bp.col("P.63", 2.5) / 100.0; lay = bp.col("P.64", 0.25)
    eps_w = bp.col("P.73", 0.3); beta_w = bp.col("P.74", 0.3)
    rho_new = bp.vec("P.61", 0.4); lag_new = int(p.get("P.62", 8))
    m_mult = bp.vec("P.87", 0.6); co = bp.vec("P.56", 0.3); jlag = int(p.get("P.84", 4))
    W_cons = inp.consumption_share / inp.consumption_share.sum()
    wY = cost_w.sum(axis=0) / cost_w.sum()
    compl = inp.emp0 * (1.0 - inp.occ_exposure_beta); compl = compl / compl.sum()
    retr_entry = float(p.get("P.68", 0.06)); retr_success = float(p.get("P.70", 0.55)); retr_dur = int(p.get("P.71", 4))
    reemp_rate = 0.35; exit_rate = 0.05
    scar = bp.col("P.69", 0.12)

    # cohorts (spec §1.4, §5.3–5.4): marginal shares per occupation, product-of-marginals joint
    age_sh = cohorts["age"] if cohorts else np.tile(np.array([0.125, 0.44, 0.20, 0.235]), (n_occ, 1))     # [n_occ,4]
    edu_sh = cohorts["education"] if cohorts else np.full((n_occ, 4), 0.25)
    dec_sh = cohorts["decile"] if cohorts else np.full((n_occ, 10), 0.1)
    N0_age = inp.emp0 @ age_sh; N0_edu = inp.emp0 @ edu_sh; N0_dec = inp.emp0 @ dec_sh
    dec_rank = np.arange(10)[::-1] + 1.0
    entry_dec = dec_sh * dec_rank[None, :]; entry_dec /= entry_dec.sum(axis=1, keepdims=True)          # entrants sit in the lower deciles
    sen_prot = float(p.get("P.65", 0.5))
    lay_age_w = (1.0 - sen_prot * SENIORITY)[None, :] * age_sh; lay_age_w /= lay_age_w.sum(axis=1, keepdims=True)
    mg = sorted(set(inp.major_group)); mg_idx = np.array([mg.index(m) for m in inp.major_group])

    N = np.tile(N0[:, 0][None, :], (D, 1)); ln_w = np.zeros((D, n_occ))
    searching = np.zeros((D, n_occ)); unhired = np.zeros((D, n_occ))
    retraining = np.zeros((D, retr_dur))          # cohorts of retrainees by quarters-to-completion
    lost_age = np.zeros((D, 4)); lost_edu = np.zeros((D, 4)); lost_dec = np.zeros((D, 10))
    disp_hist = np.zeros((D, n_q)); zeta_hist: list[np.ndarray] = []; U_hist: list[np.ndarray] = []
    tokens_prev = np.zeros(D); capex_dom = np.zeros((D, n_q))
    z = lambda *s: np.zeros((D, *s))
    out = BatchOutput(quarters=quarters, cell_ids=list(draws.cell_ids) if draws else ["central"], C=C, N0=N0,
                      N=z(n_occ, n_q), ln_w=z(n_occ, n_q), ln_P=z(n_q), D_=z(n_occ, n_q), U=z(n_occ, n_q),
                      automatable=automatable, gdp_pct=z(n_q), tfp_pct=z(n_q), adoption_emp=z(n_q), adoption_firm=z(n_q),
                      ai_spend=z(n_q), ai_jobs=z(n_q), laid_off_cum=z(n_q), unhired_cum=z(n_q), reemployed_cum=z(n_q),
                      retraining_cum=z(n_q), retrained_cum=z(n_q), exited_cum=z(n_q), retired_cum=z(n_q), unemployed_stock=z(n_q), retraining_stock=z(n_q),
                      wage_share_pp=z(n_q), price_mult=np.ones((D, n_q)), mu=z(n_q), q_ratio=z(n_q), dlnc=z(n_q), nu_mean=z(n_q),
                      lost_by_age=z(4, n_q), lost_by_edu=z(4, n_q), lost_by_dec=z(10, n_q), lost_by_mg=z(len(mg), n_q), major_groups=mg,
                      N0_age=N0_age, N0_edu=N0_edu, N0_dec=N0_dec)
    cum = {k: np.zeros(D) for k in ("laid", "unhired", "reemp", "retr_in", "retr_done", "exit", "retired", "aijobs_prev")}
    lost_mg = np.zeros((D, len(mg)))
    pi_row = pi_size[None, :]

    for t in range(n_q):
        # ---- capacity multiplier (spec §3.4) ----
        mult = np.ones(D)
        if cap_on and t > 0:
            ages = t - np.arange(t + 1)
            surv = np.maximum(0.0, 1.0 - ages / depr)
            K = share_dom * float(np.sum((cap.annual_bn[: t + 1] / 4.0) * yield_tokens[: t + 1] * surv))
            with np.errstate(divide="ignore", invalid="ignore"):
                mult = np.where((K > 0) & (tokens_prev > 0), np.maximum(1.0, (tokens_prev / np.maximum(K, 1e-9)) ** xi), 1.0)
        out.price_mult[:, t] = mult

        # ---- feasibility, price, profitability (spec §2.3–2.4, §3.3) ----
        C_eff = (C0 + g * (C[:, t:t + 1] - C0)).astype(TDTYPE)
        C_eff[:, phys] = C_phys[:, t:t + 1].astype(TDTYPE)
        F = a * logistic((C_eff - theta32) / s_soft)
        age_q = np.maximum(0, t - cross_q)
        price = price_by_age[row_idx, age_q]
        price = np.where(age_q >= ow_lag[t], price * ow_mult.astype(TDTYPE), price)
        price = np.maximum(price, TDTYPE(floor[t])) * mult.astype(TDTYPE)[:, None]
        kappa = np.maximum((price * n_tok * TDTYPE(1e-6) + integ) * chi1, TDTYPE(1e-6))
        prof = logistic((ln_wage_h - np.log(kappa)) / b_kappa)
        sig = np.clip(sig0 + drift * (C[:, t:t + 1] - C0), 0.0, 1.0).astype(TDTYPE)
        wPi = wgt * sig * F * prof
        wF_aug = wgt * (1 - sig) * F
        S = agg(tg, wPi).astype(np.float64); G = agg(tg, wF_aug).astype(np.float64)
        Z = agg(tg, wPi * np.clip(1 - kappa / wage_h32, 0, 1)).astype(np.float64)
        Kc = agg(tg, wPi * kappa).astype(np.float64); Tk = agg(tg, wPi * n_tok).astype(np.float64)
        Aug = agg(tg, wF_aug * kappa).astype(np.float64) * 0.3
        with np.errstate(divide="ignore", invalid="ignore"):
            kappa_bar = np.where(S > 0, Kc / np.maximum(S, 1e-12), 0.0); tok_bar = np.where(S > 0, Tk / np.maximum(S, 1e-12), 0.0)

        # ---- adoption (spec §4.2) ----
        wage_q = inp.wage_mean[None, :] / 4.0
        B = (Z + psi * G) * wage_q @ W.T - (HOURS_PER_QUARTER * Aug) @ W.T                  # [D, n_sec]
        Amax = logistic((B[:, :, None] - bstar[None, :, :]) / b_h)                           # [D, n_sec, n_size]
        room = np.maximum(Amax - A, 0.0)
        ratio = np.where(Amax > 1e-6, A / np.maximum(Amax, 1e-6), 0.0)
        dA = (pq + qq[:, :, None] * ratio) * room * phi_s[None, :, None] * phi_f[:, None, :] * phi_reg[None, :, None]
        A_new = np.clip(A + dA + eps_entry * np.maximum(A_ent - A, 0.0), 0.0, 1.0)
        i_inc = iota + ramp[:, :, None] * (imax[:, :, None] - iota)
        iota = np.clip(np.where(A_new > 1e-9, (A * i_inc) / np.maximum(A_new, 1e-9), iota), 0.0, imax[:, :, None])
        A = A_new
        eff = (A * iota) @ pi_size                                                            # [D, n_sec]
        occ_eff = eff @ inp.occ_sector.T                                                     # [D, n_occ]
        Dr = occ_eff * S; Ur = occ_eff * G; zetaR = occ_eff * Z
        zeta_hist.append(zetaR); U_hist.append(Ur)
        zeta_lag = zeta_hist[max(0, t - jlag)]; U_lag = U_hist[max(0, t - jlag)]

        # ---- demand feedback from last quarter's household income (spec §6.3) ----
        if t > 0 and ch.demand_feedback:
            W_prev = (out.N[:, :, t - 1] * inp.wage_mean[None, :] * np.exp(out.ln_w[:, :, t - 1])).sum(axis=1) / 1e9 + out.ai_jobs[:, t - 1] * AI_PRODUCTION_WAGE / 1e9
            Y_prev = Y0[t - 1] * (1.0 + out.gdp_pct[:, t - 1])
            dW = W_prev - W0_bill[t - 1]; dPi = (Y_prev - Y0[t - 1]) - dW
            dC = 0.7 * dW + 0.4 * dPi
            mu = (m_mult * dC / (0.68 * Y0[t - 1]))[:, None] * (1.0 - inp.tradable)[None, :]
        else:
            mu = np.zeros((D, n_sec))
        out.mu[:, t] = mu.mean(axis=1)

        # ---- unit cost, output demand, labor demand (spec §5.2) ----
        auto = (zeta_lag @ W.T) if ch.automation else 0.0
        aug = ((psi * U_lag / (1.0 + psi * U_lag)) @ W.T) if ch.augmentation else 0.0
        dlnc = -s_L * (auto + aug)                                                           # [D, n_sec]
        Q_ratio = np.exp(-eta * pi_p * dlnc) * (1.0 + (mu if ch.demand_feedback else 0.0))
        out.q_ratio[:, t] = Q_ratio.mean(axis=1); out.dlnc[:, t] = dlnc @ wY
        q_occ = Q_ratio @ inp.occ_sector.T
        if ch.reinstatement and t - lag_new >= 0:
            new_jobs = rho_new * disp_hist[:, : t - lag_new + 1].sum(axis=1)
            nu = new_jobs[:, None] * compl[None, :] / np.maximum(N0[:, t][None, :], 1.0)
        else:
            nu = np.zeros((D, n_occ))
        out.nu_mean[:, t] = (nu * N0[:, t][None, :]).sum(axis=1) / N0[:, t].sum()
        D_use = Dr if ch.automation else 0.0; U_use = Ur if ch.augmentation else 0.0
        N_star = N0[:, t][None, :] * q_occ * (1.0 - D_use) / (1.0 + psi * U_use) * (1.0 + nu)

        # ---- hiring channel first, layoffs second (spec §5.3) ----
        gap = N - N_star
        shed = np.maximum(gap, 0.0)
        via_attr = np.minimum(shed, attr * N)
        layoffs = lay * (shed - via_attr)
        hires = np.maximum(-gap, 0.0)
        # ---- transitions (spec §5.4): searching -> re-employed / retraining / exit / remain ----
        total_search = searching.sum(axis=1) + unhired.sum(axis=1)
        reemployed = np.minimum(reemp_rate * total_search, hires.sum(axis=1))
        exits = exit_rate * total_search
        to_retrain = retr_entry * total_search
        completed = retraining[:, 0].copy()
        retraining = np.roll(retraining, -1, axis=1); retraining[:, -1] = to_retrain
        retrained_ok = retr_success * completed
        retrained_fail = completed - retrained_ok
        with np.errstate(divide="ignore", invalid="ignore"):
            keep = np.where(total_search > 0, np.maximum(0.0, 1.0 - (reemployed + exits + to_retrain) / np.maximum(total_search, 1e-9)), 0.0)
        N = N - via_attr - layoffs + hires
        searching = searching * keep[:, None] + layoffs + (retrained_fail[:, None] * compl[None, :])
        unhired = unhired * keep[:, None] + via_attr
        # wages (spec §5.5): partial adjustment toward a wage-curve target
        XS = (searching + unhired) / np.maximum(N, 1.0)
        target = -0.1 * np.log1p(XS / 0.04) + beta_w * psi * Ur
        ln_w = ln_w + eps_w * (target - ln_w)
        ln_P = pi_p[:, 0] * (dlnc @ W_cons)

        # ---- cohort incidence and aging (spec §1.4, §5.3) ----
        lost_age += via_attr.sum(axis=1)[:, None] * ENTRANT_AGE[None, :] + layoffs @ lay_age_w
        lost_edu += (via_attr + layoffs) @ edu_sh
        lost_dec += via_attr @ entry_dec + layoffs @ dec_sh
        back = reemployed + retrained_ok
        age_w = lost_age * REEMP_AGE_HAZARD[None, :]; age_w = age_w / np.maximum(age_w.sum(axis=1, keepdims=True), 1e-9)
        lost_age -= back[:, None] * age_w
        edu_w = lost_edu / np.maximum(lost_edu.sum(axis=1, keepdims=True), 1e-9); lost_edu -= back[:, None] * edu_w
        dec_w = lost_dec / np.maximum(lost_dec.sum(axis=1, keepdims=True), 1e-9); lost_dec -= back[:, None] * dec_w
        lost_age = np.maximum(lost_age, 0.0); lost_edu = np.maximum(lost_edu, 0.0); lost_dec = np.maximum(lost_dec, 0.0)
        moved = lost_age * AGING_RATE[None, :]; lost_age = lost_age - moved; lost_age[:, 1:] += moved[:, :-1]
        ex_w = lost_age * EXIT_AGE_HAZARD[None, :]; ex_w = ex_w / np.maximum(ex_w.sum(axis=1, keepdims=True), 1e-9)
        retired = exits * ex_w[:, 3]
        lost_mg += np.stack([(via_attr + layoffs)[:, mg_idx == k].sum(axis=1) for k in range(len(mg))], axis=1)

        # ---- macro (spec §6) ----
        inc = max(cap.annual_bn[t] - cap.trend_bn[t], 0.0)
        d_inv = share_dom * inc * (1.0 - co) if ch.ai_investment else np.zeros(D)
        capex_dom[:, t] = (inc * share_dom / 4.0) if ch.ai_investment else 0.0
        jobs = 1000.0 * capex_dom[:, t] + 50.0 * capex_dom[:, : t + 1].sum(axis=1)
        y_ratio = Q_ratio @ wY
        Y = Y0[t] * y_ratio + d_inv + jobs * AI_PRODUCTION_WAGE / 1e9
        tfp = -(dlnc @ wY)
        spend = ((N0[:, t][None, :] * HOURS_PER_YEAR * Dr * kappa_bar).sum(axis=1)
                 + (N0[:, t][None, :] * HOURS_PER_YEAR * Ur * (Aug / np.maximum(G, 1e-9))).sum(axis=1)) / 1e9
        tokens_prev = (N0[:, t][None, :] * HOURS_PER_YEAR * Dr * tok_bar).sum(axis=1)

        # ---- record ----
        cum["laid"] += layoffs.sum(axis=1); cum["unhired"] += via_attr.sum(axis=1); cum["reemp"] += reemployed
        cum["retr_in"] += to_retrain; cum["retr_done"] += retrained_ok; cum["exit"] += exits; cum["retired"] += retired
        disp_hist[:, t] = layoffs.sum(axis=1) + via_attr.sum(axis=1)
        out.N[:, :, t] = N; out.ln_w[:, :, t] = ln_w; out.ln_P[:, t] = ln_P
        out.D_[:, :, t] = Dr; out.U[:, :, t] = Ur
        out.gdp_pct[:, t] = Y / Y0[t] - 1.0; out.tfp_pct[:, t] = tfp
        out.adoption_emp[:, t] = ((A @ pi_size) * wY[None, :]).sum(axis=1); out.adoption_firm[:, t] = ((A @ firm_size) * wY[None, :]).sum(axis=1)
        out.ai_spend[:, t] = spend; out.ai_jobs[:, t] = jobs
        out.laid_off_cum[:, t] = cum["laid"]; out.unhired_cum[:, t] = cum["unhired"]; out.reemployed_cum[:, t] = cum["reemp"]
        out.retraining_cum[:, t] = cum["retr_in"]; out.retrained_cum[:, t] = cum["retr_done"]; out.exited_cum[:, t] = cum["exit"]; out.retired_cum[:, t] = cum["retired"]
        out.unemployed_stock[:, t] = searching.sum(axis=1) + unhired.sum(axis=1)
        out.retraining_stock[:, t] = retraining.sum(axis=1)
        Wt = (N * inp.wage_mean[None, :] * np.exp(ln_w)).sum(axis=1) / 1e9 + jobs * AI_PRODUCTION_WAGE / 1e9
        out.wage_share_pp[:, t] = 100.0 * (Wt / Y - W0_bill[t] / Y0[t])
        out.lost_by_age[:, :, t] = lost_age; out.lost_by_edu[:, :, t] = lost_edu; out.lost_by_dec[:, :, t] = lost_dec; out.lost_by_mg[:, :, t] = lost_mg
        _ = pi_row, scar
    out.trace = {"fitted": fitted, "theta_central": theta[0], "a_central": a[0], "task_groups": T,
                 "aei_anchoring": "unavailable: class offsets with E1 spread (spec §2.2 fallback)", "capex_annual_bn": cap.annual_bn}
    return out


# ------------------------------------------------------------------------------------------------
# parallel chunks over draws (numpy releases the GIL inside ufuncs)
# ------------------------------------------------------------------------------------------------
def _slice_draws(d: DrawSet, lo: int, hi: int) -> DrawSet:
    return DrawSet(n=hi - lo, keys=d.keys, values={k: v[lo:hi] for k, v in d.values.items()}, cell_ids=d.cell_ids[lo:hi], ranges=d.ranges)


def _concat(outs: list[BatchOutput]) -> BatchOutput:
    first = outs[0]
    merged: dict[str, Any] = {}
    for name in first.__dataclass_fields__:
        v = getattr(first, name)
        if name in ("quarters", "N0", "N0_age", "N0_edu", "N0_dec", "major_groups", "trace"):
            merged[name] = v
        elif name == "cell_ids":
            merged[name] = [c for o in outs for c in o.cell_ids]
        elif isinstance(v, np.ndarray):
            merged[name] = np.concatenate([getattr(o, name) for o in outs], axis=0)
        else:
            merged[name] = v
    return BatchOutput(**merged)


def run_batch_parallel(inp: Inputs, p: Params, scenario: dict[str, Any], draws: DrawSet, channels: Channels | None = None,
                       fitted: dict[str, Any] | None = None, cohorts: dict[str, np.ndarray] | None = None,
                       workers: int | None = None) -> BatchOutput:
    import os
    from concurrent.futures import ThreadPoolExecutor

    workers = workers or max(1, min(8, os.cpu_count() or 1))
    if draws.n < 2 * workers:
        return run_batch(inp, p, scenario, draws, channels, fitted, cohorts)
    bounds = np.linspace(0, draws.n, workers + 1).astype(int)
    chunks = [_slice_draws(draws, int(bounds[i]), int(bounds[i + 1])) for i in range(workers)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        outs = list(ex.map(lambda c: run_batch(inp, p, scenario, c, channels, fitted, cohorts), chunks))
    return _concat(outs)

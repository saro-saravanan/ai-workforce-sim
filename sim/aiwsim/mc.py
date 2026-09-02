"""Batched multi-region engine: spec v0.2 with a leading draw axis (Phase 2) and regions (Phase 3).

Every state array is shaped [D, ...]. Draw 0 is the central parameter set. Task-level work runs on task
groups (identical attributes within an occupation), once per quarter per wage tier; regions read the
task layer at their access lag (spec §3.3). Regions are coupled through the shared clock and prices,
adoption spillover from the U.S. (spec §4.2), trade-linked demand feedback (spec §6.3), global compute
capacity (spec §3.4), and AI rents by value-chain stage (spec §6.3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .clock import ANCHOR_INDEX, ANCHOR_QUARTER, capex_path, open_weights_lag
from .inputs import Inputs
from .labor import Channels
from .params import SIZE_CLASSES, SIZE_EMP_SHARES, Params
from .regions import BASELINE_GDP_GROWTH, Region, RegionalInputs, wage_tier
from .sampling import DrawSet
from .scenario import quarters as make_quarters

HOURS_PER_YEAR = 2000.0
HOURS_PER_QUARTER = 500.0
US_GDP_2024_BN = 29_200.0        # S: BEA nominal GDP 2024
BASELINE_REAL_GROWTH = 0.02      # S/E: frozen-AI baseline real growth (U.S.)
FIRM_COUNT_SHARES = {"small": 0.96, "mid": 0.035, "large": 0.005}   # D: SUSB, approximate
A0_BY_SIZE = {"small": 0.045, "mid": 0.10, "large": 0.20}             # E: 2024Q1 starting adoption (U.S.)
A0_REGION_SCALE = {"US": 1.0, "EU": 0.7, "UK": 0.9, "CN": 0.8, "JP": 0.6, "KR": 0.8, "IN": 0.6, "TW": 0.8, "SG": 1.0, "RoA": 0.4}  # E
AI_PRODUCTION_WAGE = 90_000.0                                          # E
DEFAULT_BSTAR = {"small": 1200.0, "mid": 600.0, "large": 0.0}          # E, replaced by calibration
AGE_BANDS = ["16-24", "25-44", "45-54", "55+"]
EDU_LEVELS = ["lt_hs", "hs", "some_college", "ba_plus"]
AGING_RATE = np.array([1 / 36, 1 / 80, 1 / 40, 0.0])
ENTRANT_AGE = np.array([0.7, 0.3, 0.0, 0.0])
SENIORITY = np.array([0.0, 0.3, 0.7, 1.0])
REEMP_AGE_HAZARD = np.array([1.2, 1.1, 0.9, 0.6])
EXIT_AGE_HAZARD = np.array([0.6, 0.6, 1.0, 2.5])
DTYPE = np.float64
TDTYPE = np.float32
# regime → (use-case friction scale on the high-risk share, general licensing friction) (E)
REGIME = {"state_patchwork": (0.3, 1.0), "eu_ai_act": (1.0, 1.0), "licensing": (0.5, 0.9), "light": (0.1, 1.0), "federal_strict": (1.0, 1.0), "none": (0.0, 1.0)}
HARDWARE_SHARE_OF_CAPEX = 0.5   # E: accelerators and equipment (imported), rest domestic construction and fit-out
CAPEX_HARDWARE_VA = {"US": 0.55, "TW": 0.20, "KR": 0.15, "EU": 0.10}   # E: value-added split of the hardware half (design, fabrication, memory, equipment)


def logistic(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))


# ------------------------------------------------------------------------------------------------
# task groups
# ------------------------------------------------------------------------------------------------
@dataclass
class TaskGroups:
    occ: np.ndarray; weight: np.ndarray; label: np.ndarray; modality: np.ndarray; presence: np.ndarray
    use_case: np.ndarray; consequence: np.ndarray; hash_u: np.ndarray; seg_starts: np.ndarray; seg_occ: np.ndarray; n_occ: int

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
    key = np.stack([inp.task_occ, inp.task_label, inp.task_modality, inp.task_use_case, inp.task_consequence.astype(int), np.round(pres * 20).astype(int)], axis=1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    weight = np.zeros(len(uniq)); np.add.at(weight, inv, inp.task_weight)
    order = np.lexsort((np.arange(len(uniq)), uniq[:, 0]))
    uniq = uniq[order]; weight = weight[order]
    occ = uniq[:, 0].astype(np.int64)
    starts = np.flatnonzero(np.r_[True, occ[1:] != occ[:-1]])
    keys = [f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|{r[5]}" for r in uniq]
    return TaskGroups(occ=occ, weight=weight, label=uniq[:, 1].astype(np.int64), modality=uniq[:, 2].astype(np.int64), presence=uniq[:, 5] / 20.0,
                      use_case=uniq[:, 3].astype(np.int64), consequence=uniq[:, 4].astype(DTYPE), hash_u=_hash_unit(keys), seg_starts=starts,
                      seg_occ=occ[starts], n_occ=inp.n_occ)


def agg(tg: TaskGroups, X: np.ndarray) -> np.ndarray:
    seg = np.add.reduceat(X, tg.seg_starts, axis=1, dtype=np.float64)
    out = np.zeros((X.shape[0], tg.n_occ), dtype=np.float64)
    out[:, tg.seg_occ] = seg
    return out


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


@dataclass
class OccLayer:
    S: np.ndarray; G: np.ndarray; Z: np.ndarray; kappa_bar: np.ndarray; tok_bar: np.ndarray; aug: np.ndarray


# ------------------------------------------------------------------------------------------------
# outputs
# ------------------------------------------------------------------------------------------------
def _z(D: int, *s: int) -> np.ndarray:
    return np.zeros((D, *s))


@dataclass
class RegionOut:
    region_id: str
    N0: np.ndarray; N: np.ndarray; ln_w: np.ndarray; ln_P: np.ndarray; D_: np.ndarray; U: np.ndarray
    gdp_pct: np.ndarray; tfp_pct: np.ndarray; adoption_emp: np.ndarray; adoption_firm: np.ndarray; ai_spend: np.ndarray; ai_jobs: np.ndarray
    laid_off_cum: np.ndarray; unhired_cum: np.ndarray; reemployed_cum: np.ndarray; retraining_cum: np.ndarray; retrained_cum: np.ndarray
    exited_cum: np.ndarray; retired_cum: np.ndarray; unemployed_stock: np.ndarray; retraining_stock: np.ndarray; wage_share_pp: np.ndarray
    mu: np.ndarray; q_ratio: np.ndarray; dlnc: np.ndarray; nu_mean: np.ndarray
    lost_by_age: np.ndarray; lost_by_edu: np.ndarray; lost_by_dec: np.ndarray; lost_by_mg: np.ndarray
    rents: dict[str, np.ndarray]            # stage -> [D, n_q] $bn/yr received
    net_ai_trade: np.ndarray                # [D, n_q]
    C_region: np.ndarray                    # [D, n_q] regional capability
    N0_age: np.ndarray; N0_edu: np.ndarray; N0_dec: np.ndarray
    wage_mean: np.ndarray
    emp_total: np.ndarray = field(default_factory=lambda: np.zeros(0))     # [D, n_q] heads (all draws)
    mean_ln_w: np.ndarray = field(default_factory=lambda: np.zeros(0))     # [D, n_q] employment-weighted log wage (all draws)

    @property
    def displaced_cum(self) -> np.ndarray:
        return self.laid_off_cum + self.unhired_cum

    @property
    def employment_pct(self) -> np.ndarray:
        return (self.emp_total + self.ai_jobs) / np.maximum(self.N0.sum(axis=0)[None, :], 1.0) - 1.0

    @property
    def real_wage_pct(self) -> np.ndarray:
        return np.exp(self.mean_ln_w - self.ln_P) - 1.0

    @property
    def nominal_wage_pct(self) -> np.ndarray:
        return np.exp(self.mean_ln_w) - 1.0


@dataclass
class BatchOutput:
    quarters: list[str]
    cell_ids: list[str]
    C: np.ndarray                         # [D, n_q] frontier clock
    regions: dict[str, RegionOut]
    order: list[str]
    automatable: np.ndarray               # [D, n_occ] (U.S. wage tier)
    price_mult: np.ndarray                # [D, n_q]
    price_frontier: np.ndarray            # [n_q]
    price_fixed: np.ndarray               # [n_q]
    market_share: dict[str, dict[str, np.ndarray]]   # region -> actor -> [n_q]
    availability: dict[str, dict[str, np.ndarray]]   # region -> actor -> [n_q] 0/1
    major_groups: list[str]
    trace: dict[str, Any] = field(default_factory=dict)

    # U.S. views kept for Phase 1–2 consumers
    @property
    def us(self) -> RegionOut:
        return self.regions["US"]

    def __getattr__(self, name: str):
        if name in ("N0", "N", "ln_w", "ln_P", "D_", "U", "gdp_pct", "tfp_pct", "adoption_emp", "adoption_firm", "ai_spend", "ai_jobs",
                    "laid_off_cum", "unhired_cum", "reemployed_cum", "retraining_cum", "retrained_cum", "exited_cum", "retired_cum",
                    "unemployed_stock", "retraining_stock", "wage_share_pp", "mu", "q_ratio", "dlnc", "nu_mean", "lost_by_age", "lost_by_edu",
                    "lost_by_dec", "lost_by_mg", "N0_age", "N0_edu", "N0_dec", "displaced_cum", "employment_pct", "real_wage_pct", "nominal_wage_pct"):
            return getattr(self.regions["US"], name)
        raise AttributeError(name)


# ------------------------------------------------------------------------------------------------
# region state
# ------------------------------------------------------------------------------------------------
def _us_region(inp: Inputs) -> Region:
    return Region("US", "United States", 335e6, US_GDP_2024_BN, float(inp.emp0.sum()), 1.0, float((inp.growth10 * inp.emp0).sum() / inp.emp0.sum()),
                  0.15, 1.0, 0, 0, 0.03, "state_patchwork", 0.55, 0.0, inp.emp0.copy(), inp.wage_mean.copy(), inp.growth10.copy(), "US national")


def run_batch(inp: Inputs, p: Params, scenario: dict[str, Any], draws: DrawSet | None = None, channels: Channels | None = None,
              fitted: dict[str, Any] | None = None, cohorts: dict[str, np.ndarray] | None = None,
              regional: RegionalInputs | None = None, regions: list[str] | None = None) -> BatchOutput:
    ch = channels or Channels()
    D = draws.n if draws is not None else 1
    bp = BP(p, draws, D)
    fitted = fitted or {"q": float(p.get("P.42", 0.38)), "bstar": dict(DEFAULT_BSTAR)}
    hz = scenario.get("horizon", {})
    quarters = make_quarters(hz.get("start", "2024Q1"), hz.get("end", "2040Q4"))
    n_q = len(quarters)
    shocks = scenario.get("shocks", [])
    tg = build_task_groups(inp)
    n_occ = inp.n_occ
    levers = scenario.get("levers", {})

    # ---- regions in this run ----
    if regional is None:
        reg_list = [_us_region(inp)]
    else:
        wanted = regions or regional.order
        reg_list = [regional.regions[x] for x in regional.order if x in wanted]
        if "US" in wanted and "US" not in regional.regions:
            reg_list.insert(0, _us_region(inp))
    order = [r.region_id for r in reg_list]
    eu_act = levers.get("regulation", {}).get("EU", {}).get("ai_act", "baseline")
    exp_ctl = levers.get("regulation", {}).get("export_controls", "2026_status_quo")
    localization = levers.get("regulation", {}).get("EU", {}).get("data_localization", "none")

    def access_lag(r: Region) -> int:
        lag = max(r.avail_delay_q, r.frontier_lag_q)
        if r.region_id == "EU":
            lag = {"repealed": 0, "delayed_2y": 0, "baseline": r.avail_delay_q, "strict_original_2026": r.avail_delay_q + 1}.get(eu_act, lag)
        if r.region_id == "CN":
            lag = max(1, lag + {"rescinded": -2, "2026_status_quo": 0, "tightened": 4}.get(exp_ctl, 0))
        return int(lag)

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
    C0 = C[:, :1]
    C_phys = np.array([3.0 * t / float(p.get("P.19", 24.0)) for t in range(n_q)])[None, :].repeat(D, 0)

    # ---- task attributes (spec §2.2) ----
    a_base = np.stack([bp.vec("P.22"), bp.vec("P.20"), bp.vec("P.21")], axis=1)
    lam = bp.col("P.23", 1.5)
    a = (a_base[:, tg.label] * (1.0 - tg.presence[None, :]) ** lam).astype(TDTYPE)
    phys = tg.modality == 3
    a[:, phys] = bp.col("P.59", 0.3).astype(TDTYPE)
    g_mod = np.stack([np.ones(D), bp.vec("P.34.other_cognitive", 0.7), bp.vec("P.34.interpersonal", 0.5), np.ones(D)], axis=1)
    g = g_mod[:, tg.modality].astype(TDTYPE)
    i_ref = min(9, n_q - 1); C_ref = C[:, i_ref:i_ref + 1]
    delta = np.stack([bp.vec("P.27"), bp.vec("P.25"), bp.vec("P.26")], axis=1)[:, tg.label]
    theta = np.where(tg.label[None, :] == 1, C0 + delta * 2.0 * tg.hash_u[None, :], C_ref + delta)
    theta = theta + tg.consequence[None, :] * bp.col("P.28", 1.0)
    theta[:, phys] = 4.0 + delta[:, phys]
    theta32 = theta.astype(TDTYPE)
    target_C = np.where(phys[None, :], np.inf, C0 + (theta - C0) / np.maximum(g, 1e-6))
    cross_q = np.empty((D, tg.n), dtype=np.int64)
    for d in range(D):
        cross_q[d] = np.searchsorted(C[d], target_C[d], side="left")
        cross_q[d, phys] = np.searchsorted(C_phys[d], theta[d, phys], side="left")
    s_soft = bp.col("P.15", 1.0).astype(TDTYPE)
    n0 = np.stack([bp.vec("P.08.software", 50_000), bp.vec("P.08.other_cognitive", 40_000), bp.vec("P.08.interpersonal", 30_000), bp.vec("P.08.physical", 20_000)], axis=1)[:, tg.modality]
    n_tok = (n0 * 2.0 ** (bp.col("P.29", 0.7) * np.clip(theta - C_ref, -3, 12))).astype(TDTYPE)
    sig0 = bp.col("P.16"); drift = bp.col("P.17", 0.0)
    wgt = tg.weight.astype(TDTYPE)[None, :]
    automatable = agg(tg, (tg.weight[None, :] * a).astype(np.float64))

    # ---- prices and costs (spec §3.3–3.4) ----
    rho = bp.col("P.04"); p_front = float(p["P.11"]); ow_mult = bp.col("P.06", 0.25)
    floor = float(p["P.12"]) * float(p.get("P.07", 2.0)) ** (-(np.arange(n_q) / 4.0))
    price_by_age = (p_front * rho ** (-(np.arange(n_q + 1)[None, :] / 4.0))).astype(TDTYPE)
    row_idx = np.arange(D)[:, None]
    cap = capex_path(p, quarters, shocks)
    ow_lag = open_weights_lag(p, quarters, shocks)
    wage_h_us = (inp.wage_mean / HOURS_PER_YEAR)[tg.occ][None, :]
    integ_us = ((bp.col("P.09", 15.0) / 100.0) * inp.wage_mean[tg.occ][None, :] / (float(p.get("P.10", 12.0)) * HOURS_PER_QUARTER)).astype(TDTYPE)
    b_kappa = bp.col("P.35", 0.5).astype(TDTYPE)
    depr = float(p.get("P.38", 20)); xi = bp.vec("P.39", 1.0)
    cap_on = p.flags.get("compute_capacity", "on") == "on"
    tiers = sorted({wage_tier(r.wage_level) for r in reg_list}, reverse=True)
    ln_wage_tier = {m: np.log(wage_h_us * m).astype(TDTYPE) for m in tiers}
    wage_h_tier = {m: (wage_h_us * m).astype(TDTYPE) for m in tiers}
    price_frontier = np.full(n_q, p_front)
    price_fixed = np.maximum(p_front * float(p["P.04"]) ** (-(np.arange(n_q) / 4.0)), floor)

    # ---- adoption setup (spec §4) ----
    n_sec = inp.n_sec; n_size = len(SIZE_CLASSES)
    cost_w = inp.occ_sector * (inp.emp0 * inp.wage_mean)[:, None]
    W = np.where(cost_w.sum(axis=0, keepdims=True) > 0, cost_w / np.maximum(cost_w.sum(axis=0, keepdims=True), 1e-9), 0.0).T
    hr = np.zeros(n_occ); tr = np.zeros(n_occ)
    np.add.at(hr, inp.task_occ, inp.task_weight * (inp.task_use_case == 2)); np.add.at(tr, inp.task_occ, inp.task_weight * (inp.task_use_case == 1))
    hr_share = W @ hr; tr_share = W @ tr
    phi_hr = float(p.get("P.32a", 0.6)); phi_tr = float(p.get("P.32b", 0.9))
    phi_s = np.clip(inp.sector_friction / float(p.get("P.48_scale", 1.0)), 0.05, 1.0)
    phi_f = np.stack([bp.vec("P.49.small", 0.6), bp.vec("P.49.mid", 0.8), np.ones(D)], axis=1)
    pq = float(p["P.41"]) / 4.0
    qq = bp.col("P.42", fitted["q"]) / 4.0
    if draws is None or "P.42" not in draws.values:
        qq = np.full((D, 1), fitted["q"] / 4.0)
    qx = float(p.get("P.43", 0.1)) / 4.0; L_spill = int(p.get("P.44", 4))
    b_h = float(p.get("P.47", 500.0))
    bstar = np.array([fitted["bstar"][f] for f in SIZE_CLASSES])[None, :]
    eps_entry = float(p.get("P.52_scale", 1.0)) * 0.08 / 4.0; A_ent = 0.30
    ramp = bp.col("P.51", 0.08); imax = bp.col("P.50", 0.7)
    psi = bp.col("P.40")
    pi_size = np.array([SIZE_EMP_SHARES[f] for f in SIZE_CLASSES]); firm_size = np.array([FIRM_COUNT_SHARES[f] for f in SIZE_CLASSES])
    wY = cost_w.sum(axis=0) / cost_w.sum()

    # ---- labor / macro setup (spec §5–6) ----
    eta = inp.demand_elasticity[None, :] * bp.col("P.60_scale", 1.0)
    if not ch.demand_response:
        eta = np.zeros_like(eta)
    pi_p = bp.col("P.53", 0.7); s_L = inp.labor_cost_share[None, :]
    attr = bp.col("P.63", 2.5) / 100.0; lay = bp.col("P.64", 0.25)
    eps_w = bp.col("P.73", 0.3); beta_w = bp.col("P.74", 0.3)
    rho_new = bp.vec("P.61", 0.4); lag_new = int(p.get("P.62", 8))
    m_mult = bp.vec("P.87", 0.6); co = bp.vec("P.56", 0.3); jlag = int(p.get("P.84", 4))
    W_cons = inp.consumption_share / inp.consumption_share.sum()
    compl = inp.emp0 * (1.0 - inp.occ_exposure_beta); compl = compl / compl.sum()
    retr_entry = float(p.get("P.68", 0.06)); retr_success = float(p.get("P.70", 0.55)); retr_dur = int(p.get("P.71", 4))
    reemp_rate = 0.35; exit_rate = 0.05
    age_sh = cohorts["age"] if cohorts else np.tile(np.array([0.125, 0.44, 0.20, 0.235]), (n_occ, 1))
    edu_sh = cohorts["education"] if cohorts else np.full((n_occ, 4), 0.25)
    dec_sh = cohorts["decile"] if cohorts else np.full((n_occ, 10), 0.1)
    dec_rank = np.arange(10)[::-1] + 1.0
    entry_dec = dec_sh * dec_rank[None, :]; entry_dec /= entry_dec.sum(axis=1, keepdims=True)
    sen_prot = float(p.get("P.65", 0.5))
    lay_age_w = (1.0 - sen_prot * SENIORITY)[None, :] * age_sh; lay_age_w /= lay_age_w.sum(axis=1, keepdims=True)
    mg = sorted(set(inp.major_group)); mg_idx = np.array([mg.index(m) for m in inp.major_group])
    MG = np.zeros((n_occ, len(mg))); MG[np.arange(n_occ), mg_idx] = 1.0
    ridx = {x: i for i, x in enumerate(order)}
    n_r = len(order)
    # trade: share of r's tradable output sold to r' ∝ weight[r→r'] × GDP_{r'}
    if regional is not None and n_r > 1:
        full_idx = [regional.order.index(x) for x in order]
        Tw = regional.trade[np.ix_(full_idx, full_idx)]
        gdp = np.array([r.gdp_bn for r in reg_list])
        sales = Tw * gdp[None, :]; sales = sales / np.maximum(sales.sum(axis=1, keepdims=True), 1e-9)
    else:
        sales = np.eye(n_r)
    vc = regional.value_chain if regional is not None and regional.value_chain else {
        "model": {"share": 0.25, "allocation": "market_share", "fixed": {}}, "compute": {"share": 0.35, "allocation": "data_center", "fixed": {}},
        "chips": {"share": 0.25, "allocation": "fixed", "fixed": {"US": 0.55, "TW": 0.35, "EU": 0.10}}, "integration": {"share": 0.15, "allocation": "domestic", "fixed": {}}}
    labs = [a_ for a_ in (regional.actors if regional else []) if a_.role == "lab"]
    beta_m = float(p.get("P.57", 1.0)); psi_p = float(p.get("P.58", 0.5))
    prices_known = [a_.price for a_ in labs if a_.price]
    p_med = float(np.median(prices_known)) if prices_known else p_front

    # ---- market shares and availability per region (deterministic, central params; spec §3.6) ----
    market_share: dict[str, dict[str, np.ndarray]] = {x: {} for x in order}
    availability: dict[str, dict[str, np.ndarray]] = {x: {} for x in order}
    for x in order:
        for a_ in labs:
            av = a_.avail.get(x, 1.0)
            if x == "CN" and a_.region_id == "US":
                av = {"rescinded": 0.5, "2026_status_quo": av, "tightened": 0.0}.get(exp_ctl, av)
            availability[x][a_.actor_id] = np.full(n_q, 1.0 if av >= 0.5 else 0.0)
        if labs:
            score = np.array([(beta_m * (-a_.frontier_lag_q * 0.6) - psi_p * np.log((a_.price or p_med) / p_med)) for a_ in labs])
            avv = np.array([a_.avail.get(x, 1.0) for a_ in labs])
            w_ = np.exp(score - score.max()) * avv; w_ = w_ / max(w_.sum(), 1e-9)
            for a_, sh in zip(labs, w_, strict=True):
                market_share[x][a_.actor_id] = np.full(n_q, float(sh))

    # ---- regions stacked on a second batch axis: arrays are [D, R, ...] (Phase 3 vectorization) ----
    R = len(reg_list)
    lags = np.array([access_lag(r) for r in reg_list]); tiers_r = [wage_tier(r.wage_level) for r in reg_list]
    g10_r = np.stack([r.growth10 if r.growth10 is not None else np.full(n_occ, r.emp_growth10) for r in reg_list])           # [R, n_occ]
    N0 = np.stack([r.emp0 for r in reg_list])[:, :, None] * (1.0 + ((1.0 + g10_r) ** (1.0 / 40.0) - 1.0))[:, :, None] ** np.arange(n_q)[None, None, :]  # [R, n_occ, n_q]
    Y0 = np.stack([r.gdp_bn * (1.0 + BASELINE_GDP_GROWTH.get(r.region_id, BASELINE_REAL_GROWTH)) ** (np.arange(n_q) / 4.0) for r in reg_list])    # [R, n_q]
    wage_r = np.stack([r.wage_mean for r in reg_list])                                                                          # [R, n_occ]
    W0_bill = (N0 * wage_r[:, :, None]).sum(axis=1) / 1e9                                                                       # [R, n_q]
    epl = np.array([r.epl_multiplier for r in reg_list])[None, :, None]
    spill_w = np.array([r.spillover_weight_us for r in reg_list])
    dc_share = np.array([r.data_center_share for r in reg_list]); dc_norm = dc_share / max(dc_share.sum(), 1e-9)
    wl = np.array([r.wage_level if r.wage_level > 0 else 1.0 for r in reg_list])
    phi_reg = np.zeros((R, n_sec))
    for k, r in enumerate(reg_list):
        us_scale, lic = REGIME.get(r.regime, (0.1, 1.0))
        if r.region_id == "EU":
            us_scale = {"repealed": 0.0, "delayed_2y": 0.3, "baseline": 1.0, "strict_original_2026": 1.2}.get(eu_act, 1.0)
        phi_reg[k] = (1.0 - us_scale * ((1 - phi_hr) * hr_share + (1 - phi_tr) * tr_share)) * lic
    A = np.stack([np.tile(np.array([A0_BY_SIZE[f] * A0_REGION_SCALE.get(r.region_id, 0.6) for f in SIZE_CLASSES])[None, :], (n_sec, 1)) for r in reg_list])[None]
    A = np.repeat(A, D, axis=0)                                                                                                  # [D, R, n_sec, n_size]
    iota = np.full((D, R, n_sec, n_size), 0.3)
    N = np.repeat(N0[None, :, :, 0], D, axis=0)                                                                                  # [D, R, n_occ]
    ln_w = np.zeros((D, R, n_occ)); searching = np.zeros((D, R, n_occ)); unhired = np.zeros((D, R, n_occ)); retraining = np.zeros((D, R, retr_dur))
    lost_age = np.zeros((D, R, 4)); lost_edu = np.zeros((D, R, 4)); lost_dec = np.zeros((D, R, 10)); lost_mg = np.zeros((D, R, len(mg)))
    disp_hist = np.zeros((D, R, n_q)); zeta_hist: list[np.ndarray] = []; U_hist: list[np.ndarray] = []
    cum = {k: np.zeros((D, R)) for k in ("laid", "unhired", "reemp", "retr_in", "retr_done", "exit", "retired")}
    dC_prev = np.zeros((D, R)); capex_dom = np.zeros((D, R, n_q))
    us_k = order.index("US") if "US" in order else 0
    # rent allocation matrices [R_spender, R_receiver]
    stages = list(vc)
    alloc_m: dict[str, np.ndarray] = {}
    for stage, cfg in vc.items():
        M = np.zeros((R, R))
        kind = cfg["allocation"] if regional is not None else "domestic"
        if kind == "market_share" and labs:
            for i_s, x in enumerate(order):
                for a_ in labs:
                    if a_.region_id in ridx and x in market_share and a_.actor_id in market_share[x]:
                        M[i_s, ridx[a_.region_id]] += float(market_share[x][a_.actor_id][0])
                if M[i_s].sum() < 1e-9:
                    M[i_s, i_s] = 1.0
        elif kind == "data_center":
            for i_s, x in enumerate(order):
                row = dc_norm.copy()
                if x == "EU" and localization != "none" and "EU" in ridx:
                    keep = {"partial": 0.5, "full": 1.0}[localization]
                    others = row.copy(); others[ridx["EU"]] = 0.0; others = others / max(others.sum(), 1e-9)
                    row = (1 - keep) * others; row[ridx["EU"]] += keep
                M[i_s] = row
        elif kind == "fixed":
            row = np.zeros(R)
            for y, share in cfg["fixed"].items():
                if y in ridx:
                    row[ridx[y]] = share
            if row.sum() < 1e-9:
                row[us_k] = 1.0
            M[:] = row[None, :] / row.sum()
        else:
            M = np.eye(R)
        alloc_m[stage] = M
    hw_va = np.array([CAPEX_HARDWARE_VA.get(x, 0.0) for x in order]) if regional is not None else np.eye(1)[0]
    stage_share = np.array([vc[s]["share"] for s in stages])
    rents_out = {s: np.zeros((D, R, n_q)) for s in stages}
    outs = {x: RegionOut(region_id=x, N0=N0[k], N=_z(D, n_occ, n_q), ln_w=_z(D, n_occ, n_q), ln_P=_z(D, n_q), D_=_z(D, n_occ, n_q), U=_z(D, n_occ, n_q),
                         gdp_pct=_z(D, n_q), tfp_pct=_z(D, n_q), adoption_emp=_z(D, n_q), adoption_firm=_z(D, n_q), ai_spend=_z(D, n_q), ai_jobs=_z(D, n_q),
                         laid_off_cum=_z(D, n_q), unhired_cum=_z(D, n_q), reemployed_cum=_z(D, n_q), retraining_cum=_z(D, n_q), retrained_cum=_z(D, n_q),
                         exited_cum=_z(D, n_q), retired_cum=_z(D, n_q), unemployed_stock=_z(D, n_q), retraining_stock=_z(D, n_q), wage_share_pp=_z(D, n_q),
                         mu=_z(D, n_q), q_ratio=_z(D, n_q), dlnc=_z(D, n_q), nu_mean=_z(D, n_q), lost_by_age=_z(D, 4, n_q), lost_by_edu=_z(D, 4, n_q),
                         lost_by_dec=_z(D, 10, n_q), lost_by_mg=_z(D, len(mg), n_q), rents={}, net_ai_trade=_z(D, n_q), C_region=_z(D, n_q),
                         N0_age=reg_list[k].emp0 @ age_sh, N0_edu=reg_list[k].emp0 @ edu_sh, N0_dec=reg_list[k].emp0 @ dec_sh, wage_mean=reg_list[k].wage_mean)
            for k, x in enumerate(order)}
    # per-occupation histories: all draws for the U.S. (states, occupation bands), central draw only elsewhere (memory)
    Dk = [D if x == "US" else 1 for x in order]
    dt_k = [np.float64 if x == "US" else np.float32 for x in order]
    Nt = [np.zeros((Dk[k], n_occ, n_q), dtype=dt_k[k]) for k in range(R)]; LNW = [np.zeros((Dk[k], n_occ, n_q), dtype=dt_k[k]) for k in range(R)]
    DD = [np.zeros((Dk[k], n_occ, n_q), dtype=dt_k[k]) for k in range(R)]; UU = [np.zeros((Dk[k], n_occ, n_q), dtype=dt_k[k]) for k in range(R)]
    LNP = np.zeros((D, R, n_q))
    rec = {k: np.zeros((D, R, n_q)) for k in ("gdp", "tfp", "adopt_e", "adopt_f", "spend", "jobs", "unemp", "retr_stock", "wshare", "mu", "q", "dlnc", "nu", "net", "C", "emp", "mlnw")}
    rec_cum = {k: np.zeros((D, R, n_q)) for k in cum}
    LA = np.zeros((D, R, 4, n_q)); LE = np.zeros((D, R, 4, n_q)); LD = np.zeros((D, R, 10, n_q)); LM = np.zeros((D, R, len(mg), n_q))

    layer_cache: dict[tuple[int, float], OccLayer] = {}
    base_cache: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    price_mult = np.ones((D, n_q)); tokens_prev = np.zeros(D)

    def base_layer(t: int, mult: np.ndarray):
        if t in base_cache:
            return base_cache[t]
        C_eff = (C0 + g * (C[:, t:t + 1] - C0)).astype(TDTYPE)
        C_eff[:, phys] = C_phys[:, t:t + 1].astype(TDTYPE)
        F = a * logistic((C_eff - theta32) / s_soft)
        age_q = np.maximum(0, t - cross_q)
        price = price_by_age[row_idx, age_q]
        price = np.where(age_q >= ow_lag[t], price * ow_mult.astype(TDTYPE), price)
        price = np.maximum(price, TDTYPE(floor[t])) * mult.astype(TDTYPE)[:, None]
        sig = np.clip(sig0 + drift * (C[:, t:t + 1] - C0), 0.0, 1.0).astype(TDTYPE)
        base_cache[t] = (price * n_tok * TDTYPE(1e-6), wgt * sig * F, wgt * (1 - sig) * F, sig)
        return base_cache[t]

    def task_layer(t: int, mult: np.ndarray, tier: float) -> OccLayer:
        key = (t, tier)
        if key in layer_cache:
            return layer_cache[key]
        inference, wF_sig, wF_aug, _sig = base_layer(t, mult)
        kappa = np.maximum(inference + integ_us * TDTYPE(tier), TDTYPE(1e-6))
        prof = logistic((ln_wage_tier[tier] - np.log(kappa)) / b_kappa)
        wPi = wF_sig * prof
        S = agg(tg, wPi); G = agg(tg, wF_aug)
        Z = agg(tg, wPi * np.clip(1 - kappa / wage_h_tier[tier], 0, 1))
        Kc = agg(tg, wPi * kappa); Tk = agg(tg, wPi * n_tok); Aug = agg(tg, wF_aug * kappa) * 0.3
        with np.errstate(divide="ignore", invalid="ignore"):
            kb = np.where(S > 0, Kc / np.maximum(S, 1e-12), 0.0); tb = np.where(S > 0, Tk / np.maximum(S, 1e-12), 0.0)
        lay_ = OccLayer(S=S, G=G, Z=Z, kappa_bar=kb, tok_bar=tb, aug=Aug)
        layer_cache[key] = lay_
        return lay_

    tradable = inp.tradable[None, None, :]
    for t in range(n_q):
        mult = np.ones(D)
        if cap_on and t > 0:
            ages = t - np.arange(t + 1)
            surv = np.maximum(0.0, 1.0 - ages / depr)
            K = float(np.sum((cap.annual_bn[: t + 1] / 4.0) * cap.tokens_per_bn[: t + 1] * surv))
            with np.errstate(divide="ignore", invalid="ignore"):
                mult = np.where((K > 0) & (tokens_prev > 0), np.maximum(1.0, (tokens_prev / max(K, 1e-9)) ** xi), 1.0)
        price_mult[:, t] = mult
        # task layer per region at its access lag and wage tier -> [D, R, n_occ]
        lays = [task_layer(max(0, t - int(lags[k])), price_mult[:, max(0, t - int(lags[k]))], tiers_r[k]) for k in range(R)]
        S = np.stack([l_.S for l_ in lays], axis=1); G = np.stack([l_.G for l_ in lays], axis=1); Z = np.stack([l_.Z for l_ in lays], axis=1)
        kb = np.stack([l_.kappa_bar for l_ in lays], axis=1); tb = np.stack([l_.tok_bar for l_ in lays], axis=1); Aug = np.stack([l_.aug for l_ in lays], axis=1)
        rec["C"][:, :, t] = np.stack([C[:, max(0, t - int(lags[k]))] for k in range(R)], axis=1)

        # ---- adoption (spec §4.2), [D, R, n_sec, n_size] ----
        wage_q = wage_r[None, :, :] / 4.0
        B = np.einsum("dro,so->drs", (Z + psi[:, None, :] * G) * wage_q, W) - HOURS_PER_QUARTER * np.einsum("dro,so->drs", Aug, W)
        Amax = logistic((B[:, :, :, None] - (bstar[None, None, :, :] * wl[None, :, None, None])) / b_h)
        room = np.maximum(Amax - A, 0.0)
        ratio = np.where(Amax > 1e-6, A / np.maximum(Amax, 1e-6), 0.0)
        spill = np.zeros((D, R, 1, 1))
        if t - L_spill >= 0:
            spill[:, :, 0, 0] = qx * spill_w[None, :] * rec["adopt_e"][:, us_k, t - L_spill][:, None]
            spill[:, us_k] = 0.0
        dA = (pq + qq[:, :, None, None] * ratio + spill) * room * phi_s[None, None, :, None] * phi_f[:, None, None, :] * phi_reg[None, :, :, None]
        A_new = np.clip(A + dA + eps_entry * np.maximum(A_ent - A, 0.0), 0.0, 1.0)
        i_inc = iota + ramp[:, :, None, None] * (imax[:, :, None, None] - iota)
        iota = np.clip(np.where(A_new > 1e-9, (A * i_inc) / np.maximum(A_new, 1e-9), iota), 0.0, imax[:, :, None, None])
        A = A_new
        eff = (A * iota) @ pi_size                                                   # [D, R, n_sec]
        occ_eff = eff @ inp.occ_sector.T                                             # [D, R, n_occ]
        Dr = occ_eff * S; Ur = occ_eff * G; zetaR = occ_eff * Z
        zeta_hist.append(zetaR); U_hist.append(Ur)
        if len(zeta_hist) > jlag + 1:
            zeta_hist.pop(0); U_hist.pop(0)
        zeta_lag = zeta_hist[0]; U_lag = U_hist[0]

        # ---- demand feedback: domestic + trade-linked foreign income (spec §6.3) ----
        if t > 0 and ch.demand_feedback:
            foreign = dC_prev @ sales.T                                              # [D, R]
            mu = (m_mult[:, None] * dC_prev)[:, :, None] * (1.0 - tradable) + (m_mult[:, None] * foreign)[:, :, None] * tradable
            mu = np.clip(mu, -0.5, 0.5)
        else:
            mu = np.zeros((D, R, n_sec))
        rec["mu"][:, :, t] = mu.mean(axis=2)
        auto = np.einsum("dro,so->drs", zeta_lag, W) if ch.automation else 0.0
        aug = np.einsum("dro,so->drs", psi[:, None, :] * U_lag / (1.0 + psi[:, None, :] * U_lag), W) if ch.augmentation else 0.0
        dlnc = -s_L[None] * (auto + aug)                                             # [D, R, n_sec]
        Q_ratio = np.exp(-eta[:, None, :] * pi_p[:, None, :] * dlnc) * (1.0 + (mu if ch.demand_feedback else 0.0))
        rec["q"][:, :, t] = Q_ratio.mean(axis=2); rec["dlnc"][:, :, t] = dlnc @ wY
        q_occ = Q_ratio @ inp.occ_sector.T
        N0t = N0[:, :, t][None]                                                      # [1, R, n_occ]
        if ch.reinstatement and t - lag_new >= 0:
            new_jobs = rho_new[:, None] * disp_hist[:, :, : t - lag_new + 1].sum(axis=2)
            nu = new_jobs[:, :, None] * compl[None, None, :] / np.maximum(N0t, 1.0)
        else:
            nu = np.zeros((D, R, n_occ))
        rec["nu"][:, :, t] = (nu * N0t).sum(axis=2) / np.maximum(N0t.sum(axis=2), 1.0)
        D_use = Dr if ch.automation else 0.0; U_use = Ur if ch.augmentation else 0.0
        N_star = N0t * q_occ * (1.0 - D_use) / (1.0 + psi[:, None, :] * U_use) * (1.0 + nu)

        # ---- hiring channel, layoffs, transitions (spec §5.3–5.4) ----
        gap = N - N_star
        shed = np.maximum(gap, 0.0)
        via_attr = np.minimum(shed, attr[:, None, :] * N)
        layoffs = lay[:, None, :] * epl * (shed - via_attr)
        hires = np.maximum(-gap, 0.0)
        total_search = searching.sum(axis=2) + unhired.sum(axis=2)                   # [D, R]
        reemployed = np.minimum(reemp_rate * total_search, hires.sum(axis=2))
        exits = exit_rate * total_search
        to_retrain = retr_entry * total_search
        completed = retraining[:, :, 0].copy()
        retraining = np.roll(retraining, -1, axis=2); retraining[:, :, -1] = to_retrain
        retrained_ok = retr_success * completed; retrained_fail = completed - retrained_ok
        with np.errstate(divide="ignore", invalid="ignore"):
            keep = np.where(total_search > 0, np.maximum(0.0, 1.0 - (reemployed + exits + to_retrain) / np.maximum(total_search, 1e-9)), 0.0)
        N = N - via_attr - layoffs + hires
        searching = searching * keep[:, :, None] + layoffs + retrained_fail[:, :, None] * compl[None, None, :]
        unhired = unhired * keep[:, :, None] + via_attr
        XS = (searching + unhired) / np.maximum(N, 1.0)
        target = -0.1 * np.log1p(XS / 0.04) + beta_w[:, None, :] * psi[:, None, :] * Ur
        ln_w = np.clip(ln_w + eps_w[:, None, :] * (target - ln_w), -2.0, 2.0)
        ln_P = pi_p[:, 0][:, None] * (dlnc @ W_cons)                                 # [D, R]

        # ---- cohorts (U.S. occupation-cohort structure applied to every region; flagged) ----
        lost_age += via_attr.sum(axis=2)[:, :, None] * ENTRANT_AGE[None, None, :] + layoffs @ lay_age_w
        lost_edu += (via_attr + layoffs) @ edu_sh
        lost_dec += via_attr @ entry_dec + layoffs @ dec_sh
        back = reemployed + retrained_ok
        age_w = lost_age * REEMP_AGE_HAZARD[None, None, :]; age_w = age_w / np.maximum(age_w.sum(axis=2, keepdims=True), 1e-9)
        lost_age -= back[:, :, None] * age_w
        edu_w = lost_edu / np.maximum(lost_edu.sum(axis=2, keepdims=True), 1e-9); lost_edu -= back[:, :, None] * edu_w
        dec_w = lost_dec / np.maximum(lost_dec.sum(axis=2, keepdims=True), 1e-9); lost_dec -= back[:, :, None] * dec_w
        lost_age = np.maximum(lost_age, 0.0); lost_edu = np.maximum(lost_edu, 0.0); lost_dec = np.maximum(lost_dec, 0.0)
        moved = lost_age * AGING_RATE[None, None, :]; lost_age = lost_age - moved; lost_age[:, :, 1:] += moved[:, :, :-1]
        ex_w = lost_age * EXIT_AGE_HAZARD[None, None, :]; ex_w = ex_w / np.maximum(ex_w.sum(axis=2, keepdims=True), 1e-9)
        retired = exits * ex_w[:, :, 3]
        lost_mg += (via_attr + layoffs) @ MG

        # ---- macro (spec §6): investment by data-center location, spend, rents, net AI trade ----
        inc = max(cap.annual_bn[t] - cap.trend_bn[t], 0.0)
        dc_inc = inc * dc_share[None, :]                                             # [1, R]
        d_inv = dc_inc * (1.0 - HARDWARE_SHARE_OF_CAPEX) * (1.0 - co[:, None]) if ch.ai_investment else np.zeros((D, R))
        capex_dom[:, :, t] = (dc_inc * (1.0 - HARDWARE_SHARE_OF_CAPEX) / 4.0) if ch.ai_investment else 0.0
        jobs = 1000.0 * capex_dom[:, :, t] + 50.0 * capex_dom[:, :, : t + 1].sum(axis=2)
        y_ratio = Q_ratio @ wY
        Y_task = Y0[None, :, t] * y_ratio + d_inv + jobs * AI_PRODUCTION_WAGE / 1e9
        tfp = -(dlnc @ wY)
        D_sp = Dr if ch.automation else np.zeros_like(Dr); U_sp = Ur if ch.augmentation else np.zeros_like(Ur)
        spend = ((N0t * HOURS_PER_YEAR * D_sp * kb).sum(axis=2) + (N0t * HOURS_PER_YEAR * U_sp * (Aug / np.maximum(G, 1e-9))).sum(axis=2)) / 1e9   # [D, R]
        tokens_prev = (N0t * HOURS_PER_YEAR * D_sp * tb).sum(axis=(1, 2))
        received_total = np.zeros((D, R))
        for i_s, stage in enumerate(stages):
            recv = (spend * stage_share[i_s]) @ alloc_m[stage]
            rents_out[stage][:, :, t] = recv; received_total += recv
        hw_export = (inc * HARDWARE_SHARE_OF_CAPEX * hw_va[None, :]) if (ch.ai_investment and regional is not None) else 0.0
        net = received_total - spend + hw_export
        Y = Y_task + net
        Wt = (N * wage_r[None] * np.exp(ln_w)).sum(axis=2) / 1e9 + jobs * AI_PRODUCTION_WAGE / 1e9
        dW = Wt - W0_bill[None, :, t]; dPi = (Y - Y0[None, :, t]) - dW
        dC_prev = (0.7 * dW + 0.4 * dPi) / (0.68 * Y0[None, :, t])

        # ---- record ----
        for k_, v_ in (("laid", layoffs.sum(axis=2)), ("unhired", via_attr.sum(axis=2)), ("reemp", reemployed), ("retr_in", to_retrain), ("retr_done", retrained_ok), ("exit", exits), ("retired", retired)):
            cum[k_] += v_; rec_cum[k_][:, :, t] = cum[k_]
        disp_hist[:, :, t] = layoffs.sum(axis=2) + via_attr.sum(axis=2)
        LNP[:, :, t] = ln_P
        rec["emp"][:, :, t] = N.sum(axis=2); rec["mlnw"][:, :, t] = (N * ln_w).sum(axis=2) / np.maximum(N.sum(axis=2), 1.0)
        for k in range(R):
            Nt[k][:, :, t] = N[: Dk[k], k]; LNW[k][:, :, t] = ln_w[: Dk[k], k]; DD[k][:, :, t] = Dr[: Dk[k], k]; UU[k][:, :, t] = Ur[: Dk[k], k]
        rec["gdp"][:, :, t] = Y / Y0[None, :, t] - 1.0; rec["tfp"][:, :, t] = tfp
        rec["adopt_e"][:, :, t] = ((A @ pi_size) * wY[None, None, :]).sum(axis=2); rec["adopt_f"][:, :, t] = ((A @ firm_size) * wY[None, None, :]).sum(axis=2)
        rec["spend"][:, :, t] = spend; rec["jobs"][:, :, t] = jobs; rec["net"][:, :, t] = net
        rec["unemp"][:, :, t] = searching.sum(axis=2) + unhired.sum(axis=2); rec["retr_stock"][:, :, t] = retraining.sum(axis=2)
        rec["wshare"][:, :, t] = 100.0 * (Wt / Y - W0_bill[None, :, t] / Y0[None, :, t])
        LA[:, :, :, t] = lost_age; LE[:, :, :, t] = lost_edu; LD[:, :, :, t] = lost_dec; LM[:, :, :, t] = lost_mg
        min_needed = t - int(lags.max())
        for key in [k for k in layer_cache if k[0] < min_needed]:
            del layer_cache[key]
        for k_ in [k for k in base_cache if k < min_needed]:
            del base_cache[k_]

    for k, x in enumerate(order):
        o = outs[x]
        o.N = Nt[k].astype(np.float64); o.ln_w = LNW[k].astype(np.float64); o.ln_P = LNP[:, k]; o.D_ = DD[k].astype(np.float64); o.U = UU[k].astype(np.float64)
        o.gdp_pct = rec["gdp"][:, k]; o.tfp_pct = rec["tfp"][:, k]; o.adoption_emp = rec["adopt_e"][:, k]; o.adoption_firm = rec["adopt_f"][:, k]
        o.ai_spend = rec["spend"][:, k]; o.ai_jobs = rec["jobs"][:, k]; o.net_ai_trade = rec["net"][:, k]; o.C_region = rec["C"][:, k]
        o.emp_total = rec["emp"][:, k]; o.mean_ln_w = rec["mlnw"][:, k]
        o.laid_off_cum = rec_cum["laid"][:, k]; o.unhired_cum = rec_cum["unhired"][:, k]; o.reemployed_cum = rec_cum["reemp"][:, k]
        o.retraining_cum = rec_cum["retr_in"][:, k]; o.retrained_cum = rec_cum["retr_done"][:, k]; o.exited_cum = rec_cum["exit"][:, k]; o.retired_cum = rec_cum["retired"][:, k]
        o.unemployed_stock = rec["unemp"][:, k]; o.retraining_stock = rec["retr_stock"][:, k]; o.wage_share_pp = rec["wshare"][:, k]
        o.mu = rec["mu"][:, k]; o.q_ratio = rec["q"][:, k]; o.dlnc = rec["dlnc"][:, k]; o.nu_mean = rec["nu"][:, k]
        o.lost_by_age = LA[:, k]; o.lost_by_edu = LE[:, k]; o.lost_by_dec = LD[:, k]; o.lost_by_mg = LM[:, k]
        o.rents = {s: rents_out[s][:, k] for s in stages}
    return BatchOutput(quarters=quarters, cell_ids=list(draws.cell_ids) if draws else ["central"], C=C, regions=outs, order=order,
                       automatable=automatable, price_mult=price_mult, price_frontier=price_frontier, price_fixed=price_fixed,
                       market_share=market_share, availability=availability, major_groups=mg,
                       trace={"fitted": fitted, "task_groups": tg.n, "aei_anchoring": "unavailable: class offsets with E1 spread (spec §2.2 fallback)",
                              "capex_annual_bn": cap.annual_bn, "access_lag": {x: int(lags[k]) for k, x in enumerate(order)},
                              "wage_tier": {x: tiers_r[k] for k, x in enumerate(order)}})


# ------------------------------------------------------------------------------------------------
# parallel chunks over draws
# ------------------------------------------------------------------------------------------------
def _slice_draws(d: DrawSet, lo: int, hi: int) -> DrawSet:
    return DrawSet(n=hi - lo, keys=d.keys, values={k: v[lo:hi] for k, v in d.values.items()}, cell_ids=d.cell_ids[lo:hi], ranges=d.ranges)


def _concat_region(outs: list[RegionOut]) -> RegionOut:
    first = outs[0]
    merged: dict[str, Any] = {}
    for name in first.__dataclass_fields__:
        v = getattr(first, name)
        if name in ("region_id", "N0", "N0_age", "N0_edu", "N0_dec", "wage_mean"):
            merged[name] = v
        elif name in ("N", "ln_w", "D_", "U") and v.shape[0] == 1 and first.region_id != "US":
            merged[name] = v                      # central draw only outside the U.S.; chunk 0 holds it
        elif name == "rents":
            merged[name] = {s: np.concatenate([o.rents[s] for o in outs], axis=0) for s in v}
        elif isinstance(v, np.ndarray):
            merged[name] = np.concatenate([getattr(o, name) for o in outs], axis=0)
        else:
            merged[name] = v
    return RegionOut(**merged)


def _concat(outs: list[BatchOutput]) -> BatchOutput:
    first = outs[0]
    return BatchOutput(quarters=first.quarters, cell_ids=[c for o in outs for c in o.cell_ids], C=np.concatenate([o.C for o in outs], axis=0),
                       regions={x: _concat_region([o.regions[x] for o in outs]) for x in first.order}, order=first.order,
                       automatable=np.concatenate([o.automatable for o in outs], axis=0), price_mult=np.concatenate([o.price_mult for o in outs], axis=0),
                       price_frontier=first.price_frontier, price_fixed=first.price_fixed, market_share=first.market_share,
                       availability=first.availability, major_groups=first.major_groups, trace=first.trace)


def run_batch_parallel(inp: Inputs, p: Params, scenario: dict[str, Any], draws: DrawSet, channels: Channels | None = None,
                       fitted: dict[str, Any] | None = None, cohorts: dict[str, np.ndarray] | None = None, workers: int | None = None,
                       regional: RegionalInputs | None = None, regions: list[str] | None = None) -> BatchOutput:
    import os
    from concurrent.futures import ThreadPoolExecutor

    workers = workers or max(1, min(8, os.cpu_count() or 1))
    if draws.n < 2 * workers:
        return run_batch(inp, p, scenario, draws, channels, fitted, cohorts, regional, regions)
    bounds = np.linspace(0, draws.n, workers + 1).astype(int)
    chunks = [_slice_draws(draws, int(bounds[i]), int(bounds[i + 1])) for i in range(workers)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        outs = list(ex.map(lambda c: run_batch(inp, p, scenario, c, channels, fitted, cohorts, regional, regions), chunks))
    return _concat(outs)

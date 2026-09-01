"""Layer 1: task feasibility, thresholds, tokens, and profitability (spec §2)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .inputs import Inputs
from .params import Params

HOURS_PER_YEAR = 2000.0
HOURS_PER_QUARTER = 500.0


def logistic(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))


def _task_hash_unit(task_ids: np.ndarray) -> np.ndarray:
    """Deterministic pseudo-uniform in [0,1) per task id, for spreading fallback thresholds."""
    out = np.empty(len(task_ids))
    for i, tid in enumerate(task_ids):
        h = 2166136261
        for ch in str(tid).encode():
            h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
        out[i] = (h % 100003) / 100003.0
    return out


@dataclass
class TaskFeasibility:
    a: np.ndarray               # ever-automatable mass per task
    theta: np.ndarray           # feasibility point on the (task-effective) clock
    F: np.ndarray               # [n_tasks, n_q] feasibility
    cross_q: np.ndarray         # first quarter index where C_eff >= theta, or n_q if never
    n_tok: np.ndarray           # tokens per task-hour
    sigma: np.ndarray           # [n_q] substitution share
    aei_anchoring: str


def task_feasibility(inp: Inputs, p: Params, C: np.ndarray, C_phys: np.ndarray) -> TaskFeasibility:
    n_q = len(C)
    lbl = inp.task_label
    a_base = np.array([float(p["P.22"]), float(p["P.20"]), float(p["P.21"])])[lbl]  # E0,E1,E2
    lam = float(p.get("P.23", 1.5))
    a = a_base * (1.0 - inp.task_presence) ** lam
    phys = inp.task_modality == 3
    a = np.where(phys, float(p.get("P.59", 0.3)), a)

    C0 = C[0]
    # domain transfer: effective clock per modality (spec §2.3)
    g = np.array([p.by("P.34", m) for m in ("software", "other_cognitive", "interpersonal", "physical")])
    gk = g[inp.task_modality]
    C_eff = C0 + gk[:, None] * (C[None, :] - C0)          # [n_tasks, n_q]
    C_eff[phys] = C_phys[None, :]

    # feasibility point theta: AEI anchoring unavailable in this build -> class offsets (spec §2.2)
    i_ref = min(9, n_q - 1)   # 2026Q2
    C_ref = C[i_ref]
    delta = np.array([float(p["P.27"]), float(p["P.25"]), float(p["P.26"])])[lbl]  # E0,E1,E2
    u = _task_hash_unit(inp.task_ids)
    theta = np.where(lbl == 1, C0 + delta * 2.0 * u, C_ref + delta)  # E1 spread over 2024–2025 (fallback)
    theta = theta + inp.task_consequence * float(p.get("P.28", 1.0))
    theta = np.where(phys, 4.0 + delta, theta)

    s = float(p.get("P.15", 1.0))
    F = a[:, None] * logistic((C_eff - theta[:, None]) / s)

    crossed = C_eff >= theta[:, None]
    cross_q = np.where(crossed.any(axis=1), crossed.argmax(axis=1), n_q)

    n0 = np.array([p.by("P.08", m) for m in ("software", "other_cognitive", "interpersonal", "physical")])
    gamma_n = float(p.get("P.29", 0.7))
    n_tok = n0[inp.task_modality] * 2.0 ** (gamma_n * np.clip(theta - C_ref, -3, 12))

    sig0 = float(p["P.16"])
    drift = float(p.get("P.17", 0.0) or 0.0)
    sigma = np.clip(sig0 + drift * (C - C0), 0.0, 1.0)
    return TaskFeasibility(a=a, theta=theta, F=F, cross_q=cross_q, n_tok=n_tok, sigma=sigma,
                           aei_anchoring="unavailable: class offsets with E1 spread (spec §2.2 fallback)")


def task_price(p: Params, tf: TaskFeasibility, t: int, floor_t: float, ow_lag: float, mult: float) -> np.ndarray:
    """$ per million tokens for each task's capability tier at quarter t (spec §3.3–3.4)."""
    rho = float(p["P.04"])
    p_front = float(p["P.11"])
    age = np.maximum(0.0, t - tf.cross_q)                # quarters since the tier was reached
    price = p_front * rho ** (-(age / 4.0))
    open_mult = np.where(age >= ow_lag, float(p.get("P.06", 0.25)), 1.0)
    price = np.maximum(price * open_mult, floor_t) * mult
    return price


def task_cost(inp: Inputs, p: Params, tf: TaskFeasibility, price: np.ndarray, us_chi: dict[str, float]) -> np.ndarray:
    """κ: $ per task-hour performed by AI (inference + integration + compliance)."""
    inference = price * tf.n_tok / 1e6
    wage_h = inp.wage_mean[inp.task_occ] / HOURS_PER_YEAR
    integ_share = float(p.get("P.09", 15.0)) / 100.0
    H = float(p.get("P.10", 12.0))
    integration = integ_share * inp.wage_mean[inp.task_occ] / (H * HOURS_PER_QUARTER)
    chi = np.array([us_chi.get("unregulated", 0.0), us_chi.get("transparency", 0.0), us_chi.get("high_risk", 0.0)])[inp.task_use_case]
    kappa = (inference + integration) * (1.0 + chi)
    return np.maximum(kappa, 1e-6), wage_h


@dataclass
class OccupationShares:
    S: np.ndarray        # substitutable, profitable-feasible share of occupation labor
    G: np.ndarray        # augmentable feasible share
    zeta: np.ndarray     # cost-saving share of labor cost if fully adopted
    kappa_bar: np.ndarray  # mean $ per AI task-hour on substituted tasks
    tok_bar: np.ndarray    # mean tokens per AI task-hour on substituted tasks
    aug_cost: np.ndarray   # $ per worker-hour of augmentation tool use (E: 0.3 × tokens)


def occupation_shares(inp: Inputs, tf: TaskFeasibility, t: int, kappa: np.ndarray, wage_h: np.ndarray,
                      b_kappa: float) -> OccupationShares:
    F = tf.F[:, t]
    prof = logistic((np.log(wage_h) - np.log(kappa)) / b_kappa)
    Pi = F * prof
    sig = tf.sigma[t]
    w = inp.task_weight
    n = inp.n_occ
    S = np.zeros(n); G = np.zeros(n); Z = np.zeros(n); K = np.zeros(n); T = np.zeros(n); A = np.zeros(n)
    np.add.at(S, inp.task_occ, w * sig * Pi)
    np.add.at(G, inp.task_occ, w * (1 - sig) * F)
    np.add.at(Z, inp.task_occ, w * sig * Pi * np.clip(1.0 - kappa / wage_h, 0.0, 1.0))
    np.add.at(K, inp.task_occ, w * sig * Pi * kappa)
    np.add.at(T, inp.task_occ, w * sig * Pi * tf.n_tok)
    np.add.at(A, inp.task_occ, w * (1 - sig) * F * kappa * 0.3)
    with np.errstate(divide="ignore", invalid="ignore"):
        kappa_bar = np.where(S > 0, K / S, 0.0)
        tok_bar = np.where(S > 0, T / S, 0.0)
    return OccupationShares(S=S, G=G, zeta=Z, kappa_bar=kappa_bar, tok_bar=tok_bar, aug_cost=A)


def automatable_share(inp: Inputs, tf: TaskFeasibility) -> np.ndarray:
    out = np.zeros(inp.n_occ)
    np.add.at(out, inp.task_occ, inp.task_weight * tf.a)
    return out

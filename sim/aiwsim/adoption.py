"""Layer 3: adoption ceiling, speed, intensity, entrants (spec §4)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .feasibility import HOURS_PER_QUARTER, OccupationShares
from .inputs import Inputs
from .params import SIZE_CLASSES, SIZE_EMP_SHARES, Params


@dataclass
class AdoptionState:
    A: np.ndarray        # [n_sec, n_size] share of firms adopting
    iota: np.ndarray     # [n_sec, n_size] mean intensity among adopters
    Amax: np.ndarray     # [n_sec, n_size] ceiling this quarter
    B: np.ndarray        # [n_sec, n_size] net benefit, $ per worker-quarter


def init_adoption(inp: Inputs, p: Params, A0: float) -> AdoptionState:
    n_s = inp.n_sec
    shape = (n_s, len(SIZE_CLASSES))
    return AdoptionState(A=np.full(shape, A0), iota=np.full(shape, 0.3), Amax=np.ones(shape), B=np.zeros(shape))


def sector_occ_weights(inp: Inputs) -> np.ndarray:
    """[n_sec, n_occ] labor-cost weights of occupations within each sector."""
    cost = inp.occ_sector * (inp.emp0 * inp.wage_mean)[:, None]      # [n_occ, n_sec]
    tot = cost.sum(axis=0, keepdims=True)
    return np.where(tot > 0, cost / np.maximum(tot, 1e-9), 0.0).T


def net_benefit(inp: Inputs, p: Params, sh: OccupationShares, W: np.ndarray, entrant: bool = False) -> np.ndarray:
    """$ per worker-quarter for the marginal firm in each sector (spec §4.2)."""
    psi = float(p["P.40"])
    wage_q = inp.wage_mean / 4.0
    gain = W @ (wage_q * (sh.zeta + psi * sh.G))
    tool = W @ (HOURS_PER_QUARTER * sh.aug_cost)
    return gain - tool


def high_risk_share(inp: Inputs, W: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Share of sector task-hours in high-risk and transparency use-case classes."""
    hr = np.zeros(inp.n_occ); tr = np.zeros(inp.n_occ)
    np.add.at(hr, inp.task_occ, inp.task_weight * (inp.task_use_case == 2))
    np.add.at(tr, inp.task_occ, inp.task_weight * (inp.task_use_case == 1))
    return W @ hr, W @ tr


def step_adoption(inp: Inputs, p: Params, st: AdoptionState, B: np.ndarray, Bstar: dict[str, float],
                  hr_share: np.ndarray, tr_share: np.ndarray, avail: float = 1.0) -> AdoptionState:
    b = float(p.get("P.47", 500.0))
    pq = float(p["P.41"]) / 4.0
    qq = float(p["P.42"]) / 4.0
    fs = float(p.get("P.48_scale", 1.0))
    phi_s = np.clip(inp.sector_friction / fs, 0.05, 1.0)
    phi_hr = float(p.get("P.32a", 0.6)); phi_tr = float(p.get("P.32b", 0.9))
    us_scale = {"none": 0.0, "state_patchwork": 0.3, "federal_light": 0.6, "federal_strict": 1.0}[p.flags.get("us_regime", "state_patchwork")]
    phi_reg = 1.0 - us_scale * ((1 - phi_hr) * hr_share + (1 - phi_tr) * tr_share)
    eps = float(p.get("P.52_scale", 1.0)) * 0.08 / 4.0     # BDS firm entry ~8%/yr
    A_ent = 0.30                                           # E: entrant adoption share (BTOS young firms)
    ramp = float(p.get("P.51", 0.08)); imax = float(p.get("P.50", 0.7))
    A_new = st.A.copy(); i_new = st.iota.copy(); Amax = np.zeros_like(st.A)
    for j, f in enumerate(SIZE_CLASSES):
        phi_f = p.by("P.49", f)
        Bs = Bstar.get(f, 0.0)
        Amax[:, j] = 1.0 / (1.0 + np.exp(-np.clip((B[:, j] - Bs) / b, -60, 60)))
        room = np.maximum(Amax[:, j] - st.A[:, j], 0.0)
        ratio = np.where(Amax[:, j] > 1e-6, st.A[:, j] / np.maximum(Amax[:, j], 1e-6), 0.0)
        dA = (pq + qq * ratio) * room * phi_s * phi_f * phi_reg * avail
        entry = eps * np.maximum(A_ent - st.A[:, j], 0.0)
        A_new[:, j] = np.clip(st.A[:, j] + dA + entry, 0.0, 1.0)
        # intensity: incumbents ramp toward the ceiling; new adopters enter at zero
        incumbents = st.A[:, j]
        i_inc = st.iota[:, j] + ramp * (imax - st.iota[:, j])
        i_new[:, j] = np.where(A_new[:, j] > 1e-9, (incumbents * i_inc) / np.maximum(A_new[:, j], 1e-9), st.iota[:, j])
        i_new[:, j] = np.clip(i_new[:, j], 0.0, imax)
    return AdoptionState(A=A_new, iota=i_new, Amax=Amax, B=B)


def realized_shares(inp: Inputs, st: AdoptionState, sh: OccupationShares) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """D, U, zetaR per occupation: adoption-weighted substitution, augmentation, cost saving."""
    pi = np.array([SIZE_EMP_SHARES[f] for f in SIZE_CLASSES])
    eff = (st.A * st.iota) @ pi                     # [n_sec] effective AI penetration
    occ_eff = inp.occ_sector @ eff                  # [n_occ]
    return occ_eff * sh.S, occ_eff * sh.G, occ_eff * sh.zeta

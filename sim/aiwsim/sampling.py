"""Correlated parameter draws: Latin-hypercube marginals through a Gaussian copula with block
correlations (spec §7.1), plus the 2×2×2 structural ensemble (spec §7.2)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .params import Params

# Copula blocks (spec §7.1). Members are registry ids; the correlation is applied within a block.
BLOCKS: dict[str, tuple[list[str], float]] = {
    "feasibility_level": (["P.20", "P.21", "P.22", "P.25", "P.26", "P.27", "P.34.other_cognitive", "P.34.interpersonal", "P.23"], 0.7),
    "speed": (["P.01", "P.29"], 0.5),
    "friction": (["P.09", "P.49.small", "P.49.mid", "P.50", "P.51"], 0.6),
    "labor_institutions": (["P.73", "P.74", "P.69", "P.63", "P.64"], 0.4),
    "hardware_economics": (["P.113", "P.115.driving", "P.117", "P.108.driving", "P.108.manip"], 0.6),   # spec v0.3 §A.7
    "product_preferences": (["P.125", "P.127.level", "P.126.q1"], 0.6),                                 # spec v0.3 §A.7
}
NEGATIVE_PAIRS = [("P.01", "P.04")]   # faster capability, faster price decline (spec §7.1)

# Parameters sampled in the Monte Carlo (id -> (min, central, max)); keyed ids use "P.xx.key".
SAMPLED: list[str] = [
    "P.01", "P.04", "P.06", "P.09", "P.15", "P.16", "P.17", "P.20", "P.21", "P.22", "P.23", "P.25", "P.26", "P.27",
    "P.29", "P.34.other_cognitive", "P.34.interpersonal", "P.35", "P.40", "P.42", "P.49.small", "P.49.mid",
    "P.50", "P.51", "P.53", "P.60_scale", "P.61", "P.62", "P.63", "P.64", "P.69", "P.73", "P.74", "P.83", "P.87", "P.56",
    "P.100", "P.101", "P.107", "P.108.driving", "P.108.manip", "P.113", "P.115.driving", "P.117", "P.121",
    "P.125", "P.126.q1", "P.127.level", "P.128",
]

ENSEMBLE_AXES: dict[str, dict[str, dict[str, float]]] = {
    "demand": {"bessen": {"P.60_scale": 1.0}, "unit_elastic": {"P.60_scale": 1.25}},
    "reinstatement": {"acemoglu_low": {"P.61": 0.15}, "historical": {"P.61": 0.6}},
    "passthrough": {"low": {"P.74": 0.15, "P.53": 0.4}, "mid": {"P.74": 0.4, "P.53": 0.8}},
    "hardware": {"automotive": {"P.113": 0.08}, "electronics": {"P.113": 0.20}},     # spec v0.3 §A.7 learning-rate axis
    "authenticity": {"persistent": {"P.127.half_life_years": 1e6}, "eroding": {"P.127.half_life_years": 8.0}},   # spec v0.3 §A.4, §A.7
}


def cells() -> list[dict[str, Any]]:
    out = []
    for d, dv in ENSEMBLE_AXES["demand"].items():
        for r, rv in ENSEMBLE_AXES["reinstatement"].items():
            for pth, pv in ENSEMBLE_AXES["passthrough"].items():
                for hw, hv in ENSEMBLE_AXES["hardware"].items():
                    for au, av in ENSEMBLE_AXES["authenticity"].items():
                        out.append({"id": f"{d}|{r}|{pth}|{hw}|{au}", "values": {**dv, **rv, **pv, **hv, **av}})
    return out


def _norm_cdf(z: np.ndarray) -> np.ndarray:
    erf = np.vectorize(math.erf)
    return 0.5 * (1.0 + erf(z / math.sqrt(2.0)))


def _current(p: Params, key: str) -> float | None:
    """The scenario's current value for a sampled key (levers and overrides applied)."""
    if key.endswith("_scale"):
        v = p.get(key)
        return None if v is None or isinstance(v, dict) else float(v)
    if key.count(".") == 2:
        pid, _, sub = key.rpartition(".")
        try:
            return p.by(pid, sub)
        except KeyError:
            return None
    v = p.get(key)
    return None if v is None or isinstance(v, dict) else float(v)


def _range_of(p: Params, key: str) -> tuple[float, float, float] | None:
    """(min, current, max): the registry range re-centred on the scenario's current value (spec §7.1).
    A lever that moves a parameter moves the mode of its distribution; the range widens to include it."""
    r = _registry_range(p, key)
    if r is None:
        return None
    lo, _mode, hi = r
    cur = _current(p, key)
    if cur is None:
        return r
    return (min(lo, cur), cur, max(hi, cur))


def _registry_range(p: Params, key: str) -> tuple[float, float, float] | None:
    """(min, central, max) for a registry id or keyed id; None when the registry has no range."""
    base, _, sub = key.partition(".") if key.count(".") == 2 else (key, "", "")
    if key.endswith("_scale"):
        pid = key.replace("_scale", "")
        spec = p.specs.get(pid)
        if pid == "P.60":
            return (0.5, 1.0, 1.5)   # scale on sector elasticities (spec §8.2)
        return None
    if sub:
        pid = base
        spec = p.specs.get(pid)
        if spec is None or not spec.by or sub not in spec.by:
            return None
        e = spec.by[sub]
        if isinstance(e, dict) and all(k in e for k in ("min", "central", "max")) and e["central"] is not None:
            return (float(e["min"]), float(e["central"]), float(e["max"]))
        return None
    spec = p.specs.get(key)
    if spec is None or spec.central is None or spec.min is None or spec.max is None:
        return None
    try:
        return (float(spec.min), float(spec.central), float(spec.max))
    except (TypeError, ValueError):
        return None


def triangular_ppf(u: np.ndarray, lo: float, mode: float, hi: float) -> np.ndarray:
    if hi <= lo:
        return np.full_like(u, mode)
    fc = (mode - lo) / (hi - lo)
    return np.where(u < fc, lo + np.sqrt(u * (hi - lo) * (mode - lo)), hi - np.sqrt((1 - u) * (hi - lo) * (hi - mode)))


@dataclass
class DrawSet:
    n: int
    keys: list[str]
    values: dict[str, np.ndarray]      # key -> [n] sampled values (central at index 0)
    cell_ids: list[str]                # per draw
    ranges: dict[str, tuple[float, float, float]]


def draw_parameters(p: Params, n: int, seed: int, ensemble: str = "all", correlation_scale: float = 1.0) -> DrawSet:
    """Draw n parameter sets. Draw 0 is always the central set (in the first cell)."""
    rng = np.random.default_rng(seed)
    keys = [k for k in SAMPLED if _range_of(p, k) is not None]
    ranges = {k: _range_of(p, k) for k in keys}
    m = len(keys)
    # correlation matrix from blocks
    R = np.eye(m)
    idx = {k: i for i, k in enumerate(keys)}
    for members, rho in BLOCKS.values():
        ids = [idx[k] for k in members if k in idx]
        for a in ids:
            for b in ids:
                if a != b:
                    R[a, b] = rho * correlation_scale
    for a, b in NEGATIVE_PAIRS:
        if a in idx and b in idx:
            R[idx[a], idx[b]] = R[idx[b], idx[a]] = -0.5 * correlation_scale
    # ensure positive definite
    w, V = np.linalg.eigh(R)
    R = (V * np.maximum(w, 1e-6)) @ V.T
    d = np.sqrt(np.diag(R)); R = R / np.outer(d, d)
    L = np.linalg.cholesky(R)
    z = rng.standard_normal((n, m)) @ L.T
    # rank-based Latin hypercube stratification preserving the copula's rank correlation
    u = np.empty_like(z)
    for j in range(m):
        ranks = np.argsort(np.argsort(z[:, j]))
        u[:, j] = (ranks + rng.uniform(size=n)) / n
    values: dict[str, np.ndarray] = {}
    for j, k in enumerate(keys):
        lo, mode, hi = ranges[k]
        v = triangular_ppf(u[:, j], lo, mode, hi)
        v[0] = mode
        values[k] = v
    cs = cells()
    if ensemble == "all":
        cell_ids = ["central"] + [cs[(i - 1) % len(cs)]["id"] for i in range(1, n)]
        for i in range(1, n):
            for k, val in cs[(i - 1) % len(cs)]["values"].items():
                if k not in values:
                    base = _current(p, k)
                    if base is None:
                        b0 = p.get(k, 1.0); base = float(b0) if not isinstance(b0, dict) else 1.0
                    values[k] = np.full(n, float(base))
                values[k][i] = val
    else:
        cell_ids = ["central"] * n
    return DrawSet(n=n, keys=list(values), values=values, cell_ids=cell_ids, ranges=ranges)


def tornado_draws(p: Params, keys: list[str] | None = None) -> DrawSet:
    """One-at-a-time low/high draws for the tornado: draw 0 central, then (low, high) per parameter."""
    keys = [k for k in (keys or SAMPLED) if _range_of(p, k) is not None]
    n = 1 + 2 * len(keys)
    values: dict[str, np.ndarray] = {}
    ranges = {k: _range_of(p, k) for k in keys}
    for k in keys:
        lo, mode, hi = ranges[k]
        values[k] = np.full(n, mode)
    for j, k in enumerate(keys):
        lo, mode, hi = ranges[k]
        values[k][1 + 2 * j] = lo
        values[k][2 + 2 * j] = hi
    return DrawSet(n=n, keys=keys, values=values, cell_ids=["central"] * n, ranges=ranges)

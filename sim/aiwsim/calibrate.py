"""Fit Bass q and the small/mid hurdle to the BTOS series (spec §4.3, §7.4). Deterministic grid search."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .engine import run_central
from .inputs import Inputs
from .params import Params

# Targets (docs/data-inventory.md §3): firm-weighted, original wording, Sep 2025 ≈ 0.10 (t=6);
# new wording growth Nov 2025 → May 2026 ≈ +2.5 pp (t=7 → t=9); employment-weighted Nov 2025–Jan 2026 ≈ 0.32 (t≈7).
TARGETS = {"firm_t6": 0.10, "firm_growth_t7_t9": 0.025, "emp_t7": 0.32}


def loss(r) -> float:
    f = r.adoption_firm; e = r.adoption_emp
    return ((f[6] - TARGETS["firm_t6"]) / 0.02) ** 2 + ((f[9] - f[7] - TARGETS["firm_growth_t7_t9"]) / 0.01) ** 2 \
        + 0.5 * ((e[7] - TARGETS["emp_t7"]) / 0.05) ** 2


def fit(inp: Inputs, p: Params, scenario: dict[str, Any]) -> dict[str, Any]:
    best = None
    for q in (0.25, 0.35, 0.45, 0.55, 0.7, 0.9):
        for bs in (200.0, 600.0, 1200.0, 2000.0, 3000.0, 4500.0):
            fitted = {"q": q, "bstar": {"small": bs, "mid": bs * 0.5, "large": 0.0}}
            r = run_central(inp, p, scenario, fitted=fitted)
            L = loss(r)
            if best is None or L < best[0]:
                best = (L, fitted, r)
    L, fitted, r = best
    fitted["loss"] = float(L)
    fitted["fit_points"] = {"firm_t6": float(r.adoption_firm[6]), "firm_t7": float(r.adoption_firm[7]),
                            "firm_t9": float(r.adoption_firm[9]), "emp_t7": float(r.adoption_emp[7])}
    fitted["targets"] = TARGETS
    fitted["note"] = "p, b, q_x fixed at priors; q and B* fitted; BTOS wording break treated as a level shift (spec §7.4)."
    return fitted


def write_fitted(root: Path, fitted: dict[str, Any]) -> Path:
    out = root / "data" / "processed" / "params" / "fitted.yaml"
    out.write_text(yaml.safe_dump(fitted, sort_keys=False))
    return out

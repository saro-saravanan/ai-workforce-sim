"""Run orchestration on top of the batched engine (mc.py): central run, channel decomposition,
fitted-parameter loading. `run_central` returns a RunOutput view of draw 0 for tests and the CLI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .inputs import Inputs
from .labor import Channels
from .mc import DEFAULT_BSTAR, BatchOutput, run_batch
from .params import Params

CHANNEL_ORDER = ["automation", "augmentation", "embodied", "output_substitution", "traded_services", "demand_response", "reinstatement", "demand_feedback",
                 "ai_investment", "adjacent"]


@dataclass
class RunOutput:
    """Draw-0 view of a BatchOutput (kept for the Phase 1 CLI printout and tests)."""
    b: BatchOutput

    @property
    def quarters(self) -> list[str]:
        return self.b.quarters

    @property
    def N(self) -> np.ndarray:
        return self.b.N[0]

    @property
    def N0(self) -> np.ndarray:
        return self.b.N0

    @property
    def D(self) -> np.ndarray:
        return self.b.D_[0]

    @property
    def automatable(self) -> np.ndarray:
        return self.b.automatable[0]

    @property
    def gdp_pct(self) -> np.ndarray:
        return self.b.gdp_pct[0]

    @property
    def tfp_pct(self) -> np.ndarray:
        return self.b.tfp_pct[0]

    @property
    def employment_pct(self) -> np.ndarray:
        return self.b.employment_pct[0]

    @property
    def real_wage_pct(self) -> np.ndarray:
        return self.b.real_wage_pct[0]

    @property
    def adoption_emp(self) -> np.ndarray:
        return self.b.adoption_emp[0]

    @property
    def adoption_firm(self) -> np.ndarray:
        return self.b.adoption_firm[0]

    @property
    def wage_share_pp(self) -> np.ndarray:
        return self.b.wage_share_pp[0]

    @property
    def displaced_cum(self) -> np.ndarray:
        return self.b.displaced_cum[0]

    @property
    def horizon_hours(self) -> np.ndarray:
        return 2.0 ** self.b.C[0] / 60.0

    @property
    def C(self) -> np.ndarray:
        return self.b.C[0]


def load_fitted(root: Path) -> dict[str, Any]:
    f = root / "data" / "processed" / "params" / "fitted.yaml"
    if f.exists():
        d = yaml.safe_load(f.read_text()) or {}
        return {"q": float(d.get("q", 0.38)), "bstar": {k: float(v) for k, v in d.get("bstar", DEFAULT_BSTAR).items()}}
    return {"q": 0.38, "bstar": dict(DEFAULT_BSTAR)}


def load_cohorts(root: Path, inp: Inputs) -> tuple[dict[str, np.ndarray] | None, str]:
    """Cohort marginal shares per occupation from data/processed/cohorts (contracts §7)."""
    import polars as pl
    d = root / "data" / "processed" / "cohorts"
    if not (d / "occ_age.csv").exists():
        return None, "unavailable: uniform national shares"
    idx = {c: i for i, c in enumerate(inp.occ_codes)}

    def table(name: str, col: str, levels: list[str]) -> np.ndarray:
        df = pl.read_csv(d / f"{name}.csv", schema_overrides={"occ_code": pl.Utf8, col: pl.Utf8})
        out = np.zeros((inp.n_occ, len(levels)))
        for r in df.iter_rows(named=True):
            if r["occ_code"] in idx and str(r[col]) in levels:
                out[idx[r["occ_code"]], levels.index(str(r[col]))] = float(r["share"])
        rs = out.sum(axis=1, keepdims=True)
        return np.where(rs > 0, out / np.maximum(rs, 1e-12), 1.0 / len(levels))

    age = table("occ_age", "age_band", ["16-24", "25-44", "45-54", "55+"])
    edu = table("occ_education", "education", ["lt_hs", "hs", "some_college", "ba_plus"])
    dec = table("occ_decile", "decile", [str(i) for i in range(1, 11)])
    flag = inp.data_flags.get("cohorts/occ_age", "FIXTURE")
    return {"age": age, "education": edu, "decile": dec}, f"age {flag}; education E (Job Zone); decile D (OEWS percentiles); joint = product of marginals"


def run_central(inp: Inputs, p: Params, scenario: dict[str, Any], channels: Channels | None = None,
                fitted: dict[str, Any] | None = None, cohorts: dict[str, np.ndarray] | None = None) -> RunOutput:
    fitted = fitted or load_fitted(inp.root)
    return RunOutput(run_batch(inp, p, scenario, None, channels, fitted, cohorts))


def channel_decomposition(inp: Inputs, p: Params, scenario: dict[str, Any], full: BatchOutput,
                          fitted: dict[str, Any] | None = None, cohorts: dict[str, np.ndarray] | None = None,
                          regional: Any = None, regions: list[str] | None = None, apps: Any = None) -> dict[str, Any]:
    """Sequential switch-on attribution in the documented order (spec §9), on the central draw."""
    n_q = len(full.quarters)
    prev_emp = np.zeros(n_q); prev_gdp = np.zeros(n_q)
    contrib_emp: dict[str, list[float]] = {}; contrib_gdp: dict[str, list[float]] = {}
    for i, name in enumerate(CHANNEL_ORDER):          # sequential: single-draw runs are GIL-bound, threads made this slower
        cfg = Channels(**{c: (c in CHANNEL_ORDER[: i + 1]) for c in CHANNEL_ORDER})
        r = full if i == len(CHANNEL_ORDER) - 1 else run_batch(inp, p, scenario, None, cfg, fitted, cohorts, regional, regions, apps)
        e = r.regions["US"].employment_pct[0]; g = r.regions["US"].gdp_pct[0]
        contrib_emp[name] = [round(float(v), 4) for v in 100.0 * (e - prev_emp)]
        contrib_gdp[name] = [round(float(v), 4) for v in 100.0 * (g - prev_gdp)]
        prev_emp, prev_gdp = e, g
    return {"employment_pct_vs_baseline": {"order": CHANNEL_ORDER, "contributions": contrib_emp},
            "gdp_pct_vs_baseline": {"order": CHANNEL_ORDER, "contributions": contrib_gdp}}

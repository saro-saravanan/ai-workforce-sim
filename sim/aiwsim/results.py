"""Assemble the results document (docs/contracts.md §2)."""
from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np

from . import SPEC_VERSION
from .engine import RunOutput
from .inputs import Inputs


def _p50(x: np.ndarray, scale: float = 1.0, nd: int = 4) -> dict[str, list[float]]:
    return {"p50": [round(float(v) * scale, nd) for v in x]}


def explain_notes(inp: Inputs, r: RunOutput) -> list[str]:
    q = r.quarters
    t_end = len(q) - 1
    i2030 = q.index("2030Q4") if "2030Q4" in q else t_end
    notes = []
    notes.append(
        f"By {q[i2030]}, the capability clock reaches {r.horizon_hours[i2030]:.0f}-hour tasks at 50% reliability "
        f"(index {r.C[i2030]:.1f}); employment-weighted adoption is {100*r.adoption_emp[i2030]:.0f}% of firms."
    )
    big = inp.emp0 >= 100_000
    order = np.argsort(-np.where(big, r.D[:, i2030], -1.0))[:3]
    parts = [f"{inp.occ_titles[i]} ({100*r.D[i, i2030]:.0f}% of task-hours, {inp.emp0[i]/1e6:.1f}M jobs)" for i in order]
    notes.append(f"Highest realized displacement by {q[i2030]} among occupations with 100k+ jobs: " + "; ".join(parts) + ".")
    lay = r.laid_off_cum[t_end]; unh = r.unhired_cum[t_end]
    notes.append(
        f"Of {(lay+unh)/1e6:.1f}M jobs below baseline by {q[t_end]}, {100*unh/max(lay+unh,1):.0f}% come through reduced hiring "
        f"(positions not refilled after natural attrition) and {100*lay/max(lay+unh,1):.0f}% through layoffs; "
        f"{r.reemployed_cum[t_end]/1e6:.1f}M displaced workers were re-employed in growing occupations."
    )
    notes.append(
        f"Aggregate employment is {100*r.employment_pct[i2030]:+.1f}% vs the no-AI baseline in {q[i2030]} and "
        f"{100*r.employment_pct[t_end]:+.1f}% in {q[t_end]}; real wages {100*r.real_wage_pct[t_end]:+.1f}%, "
        f"GDP {100*r.gdp_pct[t_end]:+.1f}%, wage share {r.wage_share_pp[t_end]:+.1f} pp."
    )
    hidden = np.argsort(-(r.automatable - r.D[:, i2030]) * inp.emp0)[:3]
    notes.append("Exposed but not yet hit (largest gap × employment): " + "; ".join(
        f"{inp.occ_titles[i]} (automatable {100*r.automatable[i]:.0f}%, realized {100*r.D[i, i2030]:.0f}%)" for i in hidden) + ".")
    notes.append("Numbers are a single central run; Monte Carlo bands and the structural ensemble arrive in Phase 2. "
                 "Occupation × state and occupation × sector splits are fixtures until the OEWS ingest runs.")
    return notes


def build_results(inp: Inputs, r: RunOutput, scenario: dict[str, Any], shash: str, channels: dict[str, Any] | None) -> dict[str, Any]:
    emp_pct = r.employment_pct
    flags = dict(inp.data_flags)
    flags["aei_anchoring"] = "unavailable"
    meta = {
        "spec_version": SPEC_VERSION, "schema_version": "0.2", "scenario_id": scenario.get("id"), "scenario_name": scenario.get("name"),
        "scenario_hash": shash, "seed": scenario.get("seed", 42), "run_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "draws": 1, "ensemble": "central", "quarters": r.quarters, "regions": ["US"],
        "baseline": "no_frontier_ai_after_2023", "data_flags": flags, "data_version": inp.data_version,
        "capability_units": "doublings of METR 50% task horizon (minutes = 2^index)",
        "fitted": r.trace.get("fitted"),
    }
    series = {"US": {
        "gdp_pct_vs_baseline": _p50(r.gdp_pct, 100.0),
        "employment_pct_vs_baseline": _p50(emp_pct, 100.0),
        "real_wage_pct_vs_baseline": _p50(r.real_wage_pct, 100.0),
        "nominal_wage_pct_vs_baseline": _p50(r.nominal_wage_pct, 100.0),
        "wage_share_pp_vs_baseline": _p50(r.wage_share_pp, 1.0),
        "tfp_pct_vs_baseline": _p50(r.tfp_pct, 100.0),
        "price_index_pct_vs_baseline": _p50(np.exp(r.ln_P) - 1.0, 100.0),
        "displaced_workers_cum": _p50(r.displaced_cum, 1.0, 0),
        "laid_off_cum": _p50(r.laid_off_cum, 1.0, 0),
        "unhired_entrants_cum": _p50(r.unhired_cum, 1.0, 0),
        "reemployed_cum": _p50(r.reemployed_cum, 1.0, 0),
        "exited_cum": _p50(r.exited_cum, 1.0, 0),
        "adoption_share": _p50(r.adoption_emp, 100.0),
        "adoption_share_firm_weighted": _p50(r.adoption_firm, 100.0),
        "ai_spend_bn": _p50(r.ai_spend, 1.0, 1),
        "ai_production_jobs": _p50(r.ai_jobs, 1.0, 0),
        "capability_index": _p50(r.C, 1.0, 2),
        "capability_horizon_hours": _p50(r.horizon_hours, 1.0, 1),
        "compute_price_multiplier": _p50(r.price_mult, 1.0, 3),
    }}
    occs = []
    beta = inp.occ_exposure_beta
    for i in range(inp.n_occ):
        occs.append({
            "occ_code": inp.occ_codes[i], "title": inp.occ_titles[i], "cluster_id": inp.cluster_id[i],
            "major_group": inp.major_group[i], "emp0": int(inp.emp0[i]), "wage0": int(inp.wage_mean[i]),
            "automatable_share": round(float(r.automatable[i]), 4), "exposure_beta": round(float(beta[i]), 4),
            "displacement": _p50(r.D[i]), "augmentation": _p50(r.U[i]),
            "employment_pct_vs_baseline": _p50(r.N[i] / np.maximum(r.N0[i], 1.0) - 1.0, 100.0),
            "real_wage_pct_vs_baseline": _p50(np.exp(r.ln_w[i] - r.ln_P) - 1.0, 100.0),
        })
    states = []
    ratio = r.N / np.maximum(r.N0, 1.0)                  # [n_occ, n_q]
    state_share = inp.occ_state.sum(axis=0) / max(inp.occ_state.sum(), 1.0)
    for g in range(len(inp.state_fips)):
        w = inp.occ_state[:, g]
        tot = max(w.sum(), 1.0)
        emp_g = (ratio * w[:, None]).sum(axis=0) + r.ai_jobs * state_share[g]
        lnw_g = ((r.ln_w * w[:, None]).sum(axis=0) / tot) - r.ln_P
        states.append({
            "fips": inp.state_fips[g], "name": inp.state_names[g], "abbrev": inp.state_abbrev[g],
            "employment_pct_vs_baseline": _p50(emp_g / tot - 1.0, 100.0),
            "real_wage_pct_vs_baseline": _p50(np.exp(lnw_g) - 1.0, 100.0),
            "displaced_workers_cum": _p50(r.displaced_cum * state_share[g], 1.0, 0),
        })
    doc = {"meta": meta, "series": series, "occupations": occs, "states": states,
           "channels": channels or {}, "explain": {"notes": explain_notes(inp, r)}}
    return doc

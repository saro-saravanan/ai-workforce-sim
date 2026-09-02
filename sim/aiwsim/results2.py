"""Results document v0.3 (docs/contracts.md §2 and §8) from a BatchOutput."""
from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np

from . import SPEC_VERSION
from .inputs import Inputs
from .mc import AGE_BANDS, EDU_LEVELS, BatchOutput

PCTS = [10, 25, 50, 75, 90]
HEADLINES = ["employment_pct_vs_baseline", "gdp_pct_vs_baseline", "real_wage_pct_vs_baseline", "wage_share_pp_vs_baseline"]
MECHANISM_OF = {
    "levers.capability": "capability clock and feasibility (spec §2–3)", "levers.cost": "price and compute cost (spec §3.3–3.4)",
    "levers.regulation": "availability and use-case friction (spec §3.3, §4.2)", "levers.adoption": "adoption ceiling and speed (spec §4.2)",
    "levers.labor": "labor demand, reinstatement, wages, prices (spec §5, §6.2)", "levers.policy": "transfers and financing (spec §6.5)",
    "levers.baseline": "frozen-AI baseline construction (spec §7.6)", "shocks": "event shocks (spec §8.3)", "overrides": "direct parameter override (spec §10)",
}


def pct(x: np.ndarray, scale: float = 1.0, nd: int = 4) -> dict[str, list[float]]:
    """x: [D, n_q]. Percentiles over draws excluding the central draw when D > 1; central = draw 0."""
    out: dict[str, list[float]] = {}
    body = x[1:] if x.shape[0] > 1 else x
    if x.shape[0] > 1:
        qs = np.percentile(body, PCTS, axis=0)
        for i, q in enumerate(PCTS):
            out[f"p{q}"] = [round(float(v) * scale, nd) for v in qs[i]]
    else:
        out["p50"] = [round(float(v) * scale, nd) for v in x[0]]
    out["central"] = [round(float(v) * scale, nd) for v in x[0]]
    return out


def rl(x: np.ndarray, scale: float = 1.0, nd: int = 3) -> list[float]:
    return [round(float(v) * scale, nd) for v in x]


def slim(x: np.ndarray, scale: float = 1.0, nd: int = 3) -> dict[str, list[float]]:
    """p10/p50/p90 + central, 3 decimals: for the per-occupation and per-state series (document size)."""
    body = x[1:] if x.shape[0] > 1 else x
    out = {"central": rl(x[0], scale, nd)}
    if x.shape[0] > 1:
        qs = np.percentile(body, [10, 50, 90], axis=0)
        out.update({"p10": rl(qs[0], scale, nd), "p50": rl(qs[1], scale, nd), "p90": rl(qs[2], scale, nd)})
    else:
        out["p50"] = out["central"]
    return out


def headline_series(o: BatchOutput) -> dict[str, np.ndarray]:
    return {
        "employment_pct_vs_baseline": 100.0 * o.employment_pct, "gdp_pct_vs_baseline": 100.0 * o.gdp_pct,
        "real_wage_pct_vs_baseline": 100.0 * o.real_wage_pct, "wage_share_pp_vs_baseline": o.wage_share_pp,
    }


def structural(o: BatchOutput, quarters: list[str]) -> dict[str, Any]:
    hs = headline_series(o)
    cells = sorted({c for c in o.cell_ids if c != "central"})
    idx = {c: [i for i, cid in enumerate(o.cell_ids) if cid == c] for c in cells}
    out: dict[str, Any] = {}
    for m, x in hs.items():
        by_cell = {c: {"p50": [round(float(v), 4) for v in np.median(x[idx[c]], axis=0)]} for c in cells if idx[c]}
        spread = {}
        for q in ("2030Q4", "2040Q4"):
            if q in quarters and cells:
                t = quarters.index(q)
                within = float(np.mean([np.percentile(x[idx[c], t], 90) - np.percentile(x[idx[c], t], 10) for c in cells if idx[c]]))
                meds = [float(np.median(x[idx[c], t])) for c in cells if idx[c]]
                spread[q] = {"parametric_pp": round(within, 3), "structural_pp": round(max(meds) - min(meds), 3)}
        out[m] = {"by_cell": by_cell, "spread": spread}
    return out


def tornado(inp: Inputs, o_t: BatchOutput, keys: list[str], ranges: dict[str, tuple[float, float, float]],
            specs: dict[str, Any], quarters: list[str], at: str = "2040Q4") -> dict[str, list[dict[str, Any]]]:
    t = quarters.index(at) if at in quarters else len(quarters) - 1
    hs = headline_series(o_t)
    out: dict[str, list[dict[str, Any]]] = {}
    for m, x in hs.items():
        rows = []
        base = float(x[0, t])
        for j, k in enumerate(keys):
            lo, _mode, hi = ranges[k]
            e_lo = float(x[1 + 2 * j, t]); e_hi = float(x[2 + 2 * j, t])
            pid = k.split(".")[0] + "." + k.split(".")[1] if k.count(".") >= 1 else k
            pid = pid.replace("_scale", "")
            spec = specs.get(pid)
            rows.append({"param": k, "name": (spec.name if spec else k), "tag": (spec.tag if spec else "E"), "low": lo, "high": hi,
                         "effect_at_low": round(e_lo, 4), "effect_at_high": round(e_hi, 4), "swing": round(abs(e_hi - e_lo), 4),
                         "flips_sign": bool(np.sign(e_lo) != np.sign(base) or np.sign(e_hi) != np.sign(base)) and abs(base) > 1e-9})
        rows.sort(key=lambda r: -r["swing"])
        out[m] = rows[:15]
    return out


def confidence(o: BatchOutput, torn: dict[str, list[dict[str, Any]]] | None, quarters: list[str]) -> dict[str, Any]:
    hs = headline_series(o)
    cells = sorted({c for c in o.cell_ids if c != "central"})
    idx = {c: [i for i, cid in enumerate(o.cell_ids) if cid == c] for c in cells}
    out: dict[str, Any] = {}
    for m, x in hs.items():
        out[m] = {}
        for q in ("2030Q4", "2040Q4"):
            if q not in quarters:
                continue
            t = quarters.index(q)
            ref = np.sign(x[0, t]) if abs(x[0, t]) > 1e-9 else np.sign(np.median(x[1:, t]) if x.shape[0] > 1 else 0)
            body = x[1:, t] if x.shape[0] > 1 else x[:, t]
            share = float(np.mean(np.sign(body) == ref)) if len(body) else 1.0
            agree = all(np.sign(np.median(x[idx[c], t])) == ref for c in cells if idx[c]) if cells else True
            flips = [r["param"] for r in (torn or {}).get(m, []) if r.get("flips_sign")]
            level = "high" if agree and share >= 0.9 and not flips else ("medium" if agree and share >= 0.7 else "low")
            out[m][q] = {"level": level, "sign_share": round(share, 3), "cells_agree": bool(agree), "flip_params": flips[:5]}
    return out


def cohorts_section(o: BatchOutput) -> dict[str, Any]:
    def block(lost: np.ndarray, base: np.ndarray, labels: list[str]) -> list[dict[str, Any]]:
        tot = np.maximum(lost.sum(axis=1, keepdims=True), 1.0)
        return [{"band": labels[k], "employment_pct_vs_baseline": pct(-100.0 * lost[:, k, :] / max(base[k], 1.0)),
                 "share_of_jobs_lost": pct(lost[:, k, :] / tot[:, 0, :])} for k in range(len(labels))]
    return {"age": block(o.lost_by_age, o.N0_age, AGE_BANDS), "education": block(o.lost_by_edu, o.N0_edu, EDU_LEVELS),
            "income_decile": block(o.lost_by_dec, o.N0_dec, [str(i) for i in range(1, 11)])}


MG_TITLES = {"11": "Management", "13": "Business & financial", "15": "Computer & mathematical", "17": "Architecture & engineering",
             "19": "Science", "21": "Community & social service", "23": "Legal", "25": "Education", "27": "Arts, media & design",
             "29": "Healthcare practitioners", "31": "Healthcare support", "33": "Protective service", "35": "Food preparation",
             "37": "Building & grounds", "39": "Personal care", "41": "Sales", "43": "Office & admin support", "45": "Farming",
             "47": "Construction", "49": "Installation & repair", "51": "Production", "53": "Transportation", "55": "Military"}


def flows_section(o: BatchOutput) -> dict[str, Any]:
    tot = o.lost_by_mg[:, :, -1]
    order = np.argsort(-np.median(tot, axis=0))
    origins = []
    other = np.zeros_like(o.lost_by_mg[:, 0, :])
    for r, k in enumerate(order):
        if r < 6:
            origins.append({"major_group": o.major_groups[k], "title": MG_TITLES.get(o.major_groups[k], o.major_groups[k]),
                            "jobs_lost_cum": pct(o.lost_by_mg[:, k, :], 1.0, 0)})
        else:
            other = other + o.lost_by_mg[:, k, :]
    origins.append({"major_group": "other", "title": "Other groups", "jobs_lost_cum": pct(other, 1.0, 0)})
    return {"origins": origins, "destinations": {
        "reemployed": pct(o.reemployed_cum + o.retrained_cum, 1.0, 0), "retraining": pct(o.retraining_stock, 1.0, 0),
        "unemployed": pct(o.unemployed_stock, 1.0, 0), "exited": pct(o.exited_cum - o.retired_cum, 1.0, 0), "retired": pct(o.retired_cum, 1.0, 0),
        "unfilled_entry": pct(o.unhired_cum, 1.0, 0), "laid_off": pct(o.laid_off_cum, 1.0, 0)}}


def explain_notes(inp: Inputs, o: BatchOutput, conf: dict[str, Any]) -> list[str]:
    q = o.quarters; t_end = len(q) - 1; i30 = q.index("2030Q4") if "2030Q4" in q else t_end
    e = 100 * o.employment_pct; g = 100 * o.gdp_pct; rw = 100 * o.real_wage_pct
    def band(x: np.ndarray, t: int) -> str:
        if x.shape[0] > 1:
            return f"{x[0, t]:+.1f}% (10–90: {np.percentile(x[1:, t], 10):+.1f} to {np.percentile(x[1:, t], 90):+.1f})"
        return f"{x[0, t]:+.1f}%"
    notes = [
        f"By {q[i30]}, the capability clock reaches {2**o.C[0, i30]/60:.0f}-hour tasks at 50% reliability; employment-weighted adoption is {100*o.adoption_emp[0, i30]:.0f}% of firms.",
        f"Employment vs the no-AI baseline: {band(e, i30)} in {q[i30]}, {band(e, t_end)} in {q[t_end]}; GDP {band(g, t_end)}; real wages {band(rw, t_end)}.",
    ]
    big = inp.emp0 >= 100_000
    order = np.argsort(-np.where(big, o.D_[0, :, i30], -1.0))[:3]
    notes.append(f"Highest realized displacement by {q[i30]} among occupations with 100k+ jobs: " + "; ".join(
        f"{inp.occ_titles[i]} ({100*o.D_[0, i, i30]:.0f}% of task-hours)" for i in order) + ".")
    lay = o.laid_off_cum[0, t_end]; unh = o.unhired_cum[0, t_end]
    notes.append(f"Of {(lay+unh)/1e6:.1f}M jobs below baseline by {q[t_end]}, {100*unh/max(lay+unh,1):.0f}% come through positions not refilled after attrition and {100*lay/max(lay+unh,1):.0f}% through layoffs.")
    c = conf.get("employment_pct_vs_baseline", {}).get(q[t_end], {})
    if c:
        notes.append(f"Confidence in the sign of the {q[t_end]} employment effect: {c['level']} (sign holds in {100*c['sign_share']:.0f}% of draws; mechanism cells {'agree' if c['cells_agree'] else 'disagree'}"
                     + (f"; parameters that can flip it: {', '.join(c['flip_params'])}" if c['flip_params'] else "") + ").")
    if len(o.order) > 1:
        emps = {x: 100 * o.regions[x].employment_pct[0, t_end] for x in o.order}
        first_hit = sorted(o.order, key=lambda x: emps[x])[:3]
        rents = {x: float(sum(o.regions[x].rents.values())[0, t_end]) for x in o.order}
        tot = max(sum(rents.values()), 1e-9)
        top_rent = sorted(o.order, key=lambda x: -rents[x])[:3]
        notes.append(f"Regions with the largest {q[t_end]} employment effect: " + "; ".join(f"{x} {emps[x]:+.1f}%" for x in first_hit)
                     + f". AI rents by {q[t_end]} accrue " + ", ".join(f"{100*rents[x]/tot:.0f}% to {x}" for x in top_rent) + ".")
        lags = o.trace.get("access_lag", {})
        late = [x for x in o.order if lags.get(x, 0) >= 2]
        if late:
            notes.append("Frontier access lags of two or more quarters: " + ", ".join(f"{x} ({lags[x]}q)" for x in late)
                         + ", which delays adoption and shifts model-stage rents toward domestic labs.")
    la = o.lost_by_age[0, :, t_end]
    if la.sum() > 0:
        notes.append(f"Jobs below baseline by age in {q[t_end]}: 16–24 {100*la[0]/la.sum():.0f}%, 25–44 {100*la[1]/la.sum():.0f}%, 45–54 {100*la[2]/la.sum():.0f}%, 55+ {100*la[3]/la.sum():.0f}%, against employment shares of {100*o.N0_age[0]/o.N0_age.sum():.0f}/{100*o.N0_age[1]/o.N0_age.sum():.0f}/{100*o.N0_age[2]/o.N0_age.sum():.0f}/{100*o.N0_age[3]/o.N0_age.sum():.0f}%.")
    return notes


def trace(o: BatchOutput, quarters: list[str]) -> dict[str, Any]:
    out = {}
    for q in ("2030Q4", "2040Q4"):
        if q in quarters:
            t = quarters.index(q)
            N0t = o.N0[:, t]
            out[q] = {"automatable_share": round(float((o.automatable[0] * o.N0[:, 0]).sum() / o.N0[:, 0].sum()), 4),
                      "realized_D": round(float((o.D_[0, :, t] * N0t).sum() / N0t.sum()), 4), "realized_U": round(float((o.U[0, :, t] * N0t).sum() / N0t.sum()), 4),
                      "adoption_emp": round(float(o.adoption_emp[0, t]), 4), "dln_unit_cost": round(float(o.dlnc[0, t]), 4), "q_ratio": round(float(o.q_ratio[0, t]), 4),
                      "mu": round(float(o.mu[0, t]), 4), "nu": round(float(o.nu_mean[0, t]), 4), "price_index": round(float(np.exp(o.ln_P[0, t]) - 1), 4),
                      "capability_index": round(float(o.C[0, t]), 2), "compute_price_multiplier": round(float(o.price_mult[0, t]), 3)}
    return out


META_PATHS = {"id", "name", "description", "parent", "created", "author", "preset", "user", "schema_version", "seed", "draws"}


def annotate_diff(d: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for e in d:
        if e["path"].split(".")[0] in META_PATHS:
            continue
        mech = next((v for k, v in MECHANISM_OF.items() if e["path"].startswith(k)), "")
        out.append({**e, "mechanism": mech})
    return out


def region_series(ro) -> dict[str, Any]:
    return {
        "gdp_pct_vs_baseline": pct(ro.gdp_pct, 100.0), "employment_pct_vs_baseline": pct(ro.employment_pct, 100.0),
        "real_wage_pct_vs_baseline": pct(ro.real_wage_pct, 100.0), "nominal_wage_pct_vs_baseline": pct(ro.nominal_wage_pct, 100.0),
        "wage_share_pp_vs_baseline": pct(ro.wage_share_pp), "tfp_pct_vs_baseline": pct(ro.tfp_pct, 100.0),
        "price_index_pct_vs_baseline": pct(np.exp(ro.ln_P) - 1.0, 100.0), "displaced_workers_cum": pct(ro.displaced_cum, 1.0, 0),
        "laid_off_cum": pct(ro.laid_off_cum, 1.0, 0), "unhired_entrants_cum": pct(ro.unhired_cum, 1.0, 0), "reemployed_cum": pct(ro.reemployed_cum, 1.0, 0),
        "retraining_cum": pct(ro.retraining_cum, 1.0, 0), "exited_cum": pct(ro.exited_cum, 1.0, 0), "unemployed_stock": pct(ro.unemployed_stock, 1.0, 0),
        "adoption_share": pct(ro.adoption_emp, 100.0), "adoption_share_firm_weighted": pct(ro.adoption_firm, 100.0),
        "ai_spend_bn": pct(ro.ai_spend, 1.0, 1), "ai_production_jobs": pct(ro.ai_jobs, 1.0, 0),
        "ai_rents_received_bn": {**{s_: pct(a, 1.0, 1) for s_, a in ro.rents.items()}, "total": pct(sum(ro.rents.values()), 1.0, 1)},
        "net_ai_trade_bn": pct(ro.net_ai_trade, 1.0, 1), "regional_capability_index": pct(ro.C_region, 1.0, 2),
    }


def _quarter_of(date: str, quarters: list[str]) -> str | None:
    try:
        y, m = int(date[:4]), int(date[5:7])
    except (ValueError, TypeError):
        return None
    qn = f"{y}Q{(m - 1) // 3 + 1}"
    return qn if qn in quarters else None


def _releases(regional: Any, quarters: list[str]) -> list[dict[str, Any]]:
    if regional is None:
        return []
    names = {a_.actor_id: (a_.name, a_.region_id) for a_ in regional.actors}
    out = []
    for r in regional.releases:
        nm, rid = names.get(r.get("actor_id"), (r.get("actor_id"), ""))
        out.append({"actor_id": r.get("actor_id"), "name": nm, "region_id": rid, "model": r.get("model"), "date": r.get("date"),
                    "quarter": _quarter_of(str(r.get("date")), quarters), "capability_index": r.get("capability_index"),
                    "open_weights": int(r.get("open_weights") or 0)})
    return out


def _reg_events(inp: Inputs, quarters: list[str]) -> list[dict[str, Any]]:
    f = inp.root / "data" / "processed" / "series" / "regulatory_events.csv"
    if not f.exists():
        return []
    import polars as pl
    out = []
    for r in pl.read_csv(f).fill_null("").to_dicts():
        out.append({"event_id": r.get("event_id"), "region": r.get("region"), "date": r.get("date"), "quarter": _quarter_of(str(r.get("date")), quarters),
                    "kind": r.get("kind"), "description": r.get("description")})
    return out


def build_results_v3(inp: Inputs, o: BatchOutput, scenario: dict[str, Any], shash: str, channels: dict[str, Any] | None,
                     torn: dict[str, Any] | None, diff: list[dict[str, Any]] | None, draws: int, ensemble: str,
                     cohort_flag: str, regional: Any = None) -> dict[str, Any]:
    q = o.quarters
    flags = dict(inp.data_flags); flags["aei_anchoring"] = "unavailable"; flags["cohorts"] = cohort_flag
    conf = confidence(o, torn, q)
    cells = sorted({c for c in o.cell_ids if c != "central"})
    meta = {"spec_version": SPEC_VERSION, "schema_version": "0.3", "scenario_id": scenario.get("id"), "scenario_name": scenario.get("name"),
            "scenario_parent": scenario.get("parent"), "scenario_hash": shash, "seed": scenario.get("seed", 42),
            "run_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "draws": draws, "ensemble": ensemble, "cells": cells,
            "percentiles": PCTS, "quarters": q, "regions": ["US"], "baseline": "no_frontier_ai_after_2023", "data_flags": flags,
            "data_version": inp.data_version, "capability_units": "doublings of METR 50% task horizon (minutes = 2^index)",
            "fitted": o.trace.get("fitted"), "task_groups": o.trace.get("task_groups")}
    series = {x: region_series(o.regions[x]) for x in o.order}
    series["US"].update({"capability_index": pct(o.C, 1.0, 2), "capability_horizon_hours": pct(2.0 ** o.C / 60.0, 1.0, 1),
                         "compute_price_multiplier": pct(o.price_mult, 1.0, 3)})
    regions_meta: list[dict[str, Any]] = []
    world: list[dict[str, Any]] = []
    if regional is not None:
        for x in o.order:
            rg = regional.regions.get(x)
            if rg:
                regions_meta.append({"region_id": x, "name": rg.name, "employment_total": rg.employment_total, "gdp_bn_usd": rg.gdp_bn,
                                     "population": rg.population, "wage_level_rel_us": rg.wage_level,
                                     "access_lag_quarters": o.trace.get("access_lag", {}).get(x),
                                     "data_flags": {"occ_region": "US national" if x == "US" else regional.data_flags.get("regions/occ_region", "FIXTURE")}})
        for m in regional.members:
            rid = m.get("region_id") or ""
            if rid in o.regions:
                ro = o.regions[rid]
                world.append({"iso3": m["iso3"], "name": m["name"], "region_id": rid, "employment_pct_vs_baseline": slim(ro.employment_pct, 100.0),
                              "real_wage_pct_vs_baseline": slim(ro.real_wage_pct, 100.0)})
            else:
                world.append({"iso3": m["iso3"], "name": m["name"], "region_id": ""})
        flags["members"] = "member countries carry their region's series (composition only)"
    supply = {
        "clock": pct(o.C, 1.0, 2), "horizon_hours": pct(2.0 ** o.C / 60.0, 1.0, 1),
        "regional_capability": {x: {"central": rl(o.regions[x].C_region[0], 1.0, 2)} for x in o.order},
        "price_frontier_usd_per_mtok": {"central": rl(o.price_frontier, 1.0, 3)},
        "price_fixed_capability_usd_per_mtok": {"central": rl(o.price_fixed, 1.0, 4)},
        "releases": _releases(regional, q), "regulatory_events": _reg_events(inp, q),
        "availability": {x: {a_: [int(v) for v in arr] for a_, arr in o.availability.get(x, {}).items()} for x in o.order},
        "market_share": {x: {a_: {"central": rl(arr, 1.0, 3)} for a_, arr in o.market_share.get(x, {}).items()} for x in o.order},
    }
    beta = inp.occ_exposure_beta
    occs = []
    for i in range(inp.n_occ):
        occs.append({"occ_code": inp.occ_codes[i], "title": inp.occ_titles[i], "cluster_id": inp.cluster_id[i], "major_group": inp.major_group[i],
                     "emp0": int(inp.emp0[i]), "wage0": int(inp.wage_mean[i]), "automatable_share": round(float(o.automatable[0, i]), 4),
                     "exposure_beta": round(float(beta[i]), 4), "displacement": slim(o.D_[:, i, :]), "augmentation": {"central": rl(o.U[0, i, :])},
                     "employment_pct_vs_baseline": slim(o.N[:, i, :] / np.maximum(o.N0[i], 1.0)[None, :] - 1.0, 100.0),
                     "real_wage_pct_vs_baseline": {"central": rl(np.exp(o.ln_w[0, i, :] - o.ln_P[0]) - 1.0, 100.0)},
                     "by_region": {x: {"displacement": {"central": rl(o.regions[x].D_[0, i, :])}} for x in o.order if x != "US"}})
    ratio = o.N / np.maximum(o.N0, 1.0)[None, :, :]
    state_share = inp.occ_state.sum(axis=0) / max(inp.occ_state.sum(), 1.0)
    states = []
    for g in range(len(inp.state_fips)):
        w = inp.occ_state[:, g]; tot = max(w.sum(), 1.0)
        emp_g = np.einsum("dot,o->dt", ratio, w) + o.ai_jobs * state_share[g]
        lnw_g = np.einsum("dot,o->dt", o.ln_w, w) / tot - o.ln_P
        states.append({"fips": inp.state_fips[g], "name": inp.state_names[g], "abbrev": inp.state_abbrev[g],
                       "employment_pct_vs_baseline": slim(emp_g / tot - 1.0, 100.0), "real_wage_pct_vs_baseline": slim(np.exp(lnw_g) - 1.0, 100.0),
                       "displaced_workers_cum": slim(o.displaced_cum * state_share[g], 1.0, 0)})
    meta["regions"] = list(o.order)
    return {"meta": meta, "series": series, "occupations": occs, "states": states, "regions": regions_meta, "world": world, "supply": supply,
            "channels": channels or {},
            "structural": structural(o, q) if cells else {}, "confidence": conf, "tornado": torn or {},
            "cohorts": cohorts_section(o), "flows": flows_section(o),
            "explain": {"notes": explain_notes(inp, o, conf), "trace": trace(o, q), "diff": annotate_diff(diff or [])}}

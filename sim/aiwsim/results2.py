"""Results document v0.3 (docs/contracts.md §2 and §8) from a BatchOutput."""
from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np

from . import SPEC_VERSION
from .inputs import Inputs
from .mc import AGE_BANDS, EDU_LEVELS, US_GDP_2024_BN, BatchOutput

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
        "unfilled_entry": pct(o.unhired_cum, 1.0, 0), "laid_off": pct(o.laid_off_cum, 1.0, 0),
        "hours_cut_self": pct(o.underemp_self, 1.0, 0) if o.underemp_self.size else pct(np.zeros_like(o.laid_off_cum), 1.0, 0),
        "self_employed_margin_cum": pct(o.cut_cum, 1.0, 0) if o.cut_cum.size else pct(np.zeros_like(o.laid_off_cum), 1.0, 0)}}


def _horizon_words(c: float) -> str:
    """METR horizon in words; beyond a work-month the clock is past the benchmark's range and the number stops being meaningful."""
    h = 2.0 ** c / 60.0
    if h < 1:
        return f"{60*h:.0f}-minute tasks at 50% reliability"
    if h < 40:
        return f"{h:.0f}-hour tasks at 50% reliability"
    if h < 160:
        return f"{h/40:.0f}-work-week tasks at 50% reliability"
    return "tasks longer than a work-month, beyond the measured range of the horizon benchmark"


def validity(o: BatchOutput) -> dict[str, Any]:
    """Spec §12: flag runs where realized displacement exceeds 15% of task-hours within any ten-year window (central draw, U.S.)."""
    q = o.quarters
    N0 = np.maximum(o.N0, 1.0)
    share = (o.D_[0] * N0).sum(axis=0) / N0.sum(axis=0)                                         # [n_q] realized D share of task-hours
    best, i_from, i_to = 0.0, 0, 0
    for t in range(len(q)):
        s = min(t + 40, len(q) - 1)
        d = float(share[s] - share[t])
        if d > best:
            best, i_from, i_to = d, t, s
    fiscal = o.us.fiscal_balance_bn[0, -1] if o.us.fiscal_balance_bn.size else 0.0
    gdp_end = US_GDP_2024_BN * (1.0 + o.us.gdp_pct[0, -1])
    fiscal_pct = 100.0 * fiscal / max(gdp_end, 1.0)
    return {"warning": bool(best > 0.15) or bool(fiscal_pct < -3.0), "threshold": 0.15, "max_decade_displacement": round(best, 4), "from": q[i_from], "to": q[i_to],
            "fiscal_balance_pct_gdp_2040": round(fiscal_pct, 2),
            "fiscal_warning": bool(fiscal_pct < -3.0),
            "note": ("deficit-financed transfers above 3% of GDP are outside the model's validity: it has no inflation or interest-rate response, so their demand effect is overstated"
                     if fiscal_pct < -3.0 else "")}


def explain_notes(inp: Inputs, o: BatchOutput, conf: dict[str, Any]) -> list[str]:
    q = o.quarters; t_end = len(q) - 1; i30 = q.index("2030Q4") if "2030Q4" in q else t_end
    e = 100 * o.employment_pct; g = 100 * o.gdp_pct; rw = 100 * o.real_wage_pct
    def band(x: np.ndarray, t: int) -> str:
        if x.shape[0] > 1:
            return f"{x[0, t]:+.1f}% (10–90: {np.percentile(x[1:, t], 10):+.1f} to {np.percentile(x[1:, t], 90):+.1f})"
        return f"{x[0, t]:+.1f}%"
    notes = [
        f"By {q[i30]}, frontier AI systems can complete {_horizon_words(o.C[0, i30])} (capability index {o.C[0, i30]:.1f}); firms employing {100*o.adoption_emp[0, i30]:.0f}% of workers use AI in some tasks.",
        f"Employment vs the no-AI baseline: {band(e, i30)} in {q[i30]}, {band(e, t_end)} in {q[t_end]}; GDP {band(g, t_end)}; real wages {band(rw, t_end)}.",
    ]
    big = inp.emp0 >= 100_000
    order = np.argsort(-np.where(big, o.D_[0, :, i30], -1.0))[:3]
    notes.append(f"Highest realized displacement by {q[i30]} among occupations with 100k+ jobs: " + "; ".join(
        f"{inp.occ_titles[i]} ({100*o.D_[0, i, i30]:.0f}% of task-hours)" for i in order) + ".")
    lay = o.laid_off_cum[0, t_end]; unh = o.unhired_cum[0, t_end]; cut = float(o.cut_cum[0, t_end]) if o.cut_cum.size else 0.0
    tot_lost = max(lay + unh + cut, 1.0)
    notes.append(f"Of {tot_lost/1e6:.1f}M FTE jobs below baseline by {q[t_end]}, {100*unh/tot_lost:.0f}% come through positions not refilled after attrition, "
                 f"{100*lay/tot_lost:.0f}% through layoffs, and {100*cut/tot_lost:.0f}% through hours cut for self-employed and platform workers.")
    if o.content_share:
        shares = {c: 100 * v[0, t_end] for c, v in o.content_share.items()}
        top = sorted(shares.items(), key=lambda kv: -kv[1])[:3]
        notes.append("Output substitution (spec v0.3): AI-produced content takes " + ", ".join(f"{100*v/100:.0f}% of {c}" for c, v in top)
                     + f" spending by {q[t_end]} at the central authenticity premium; consumer-surplus proxy ${o.consumer_surplus[0, t_end]:.0f}bn/yr, AI-content revenue ${o.ai_content_revenue[0, t_end]:.0f}bn/yr.")
    if o.trace.get("export_serving_fte"):
        ex = {x: v for x, v in o.trace["export_serving_fte"].items() if v > 0}
        if ex and len(o.order) > 1:
            hit = {x: 100 * o.regions[x].trade_share[0, t_end] for x in ex if x in o.regions}
            notes.append("Traded services (spec v0.3): export-serving employment " + ", ".join(f"{x} {v/1e6:.1f}M" for x, v in ex.items())
                         + "; displacement through importers' automation by " + q[t_end] + ": " + ", ".join(f"{x} {v:.2f}% of employment" for x, v in hit.items()) + ".")
    if o.emb_share.size and o.emb_share[0, t_end] > 1e-4:
        fl = {c: float(v[0, t_end]) for c, v in o.fleet.items()}
        notes.append(f"Embodied AI (spec v0.3) displaces {100*o.emb_share[0, t_end]:.1f}% of U.S. task-hours by {q[t_end]} ({100*o.emb_share[0, i30]:.1f}% by {q[i30]}); "
                     + "deployed units: " + ", ".join(f"{c} {v/1e3:.0f}k" for c, v in fl.items()) + f"; adjacent and hardware-production jobs {o.adjacent_jobs[0, t_end]/1e3:.0f}k.")
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
    v = validity(o)
    if v["warning"]:
        notes.append(f"Validity warning: {100*v['max_decade_displacement']:.0f}% of task-hours displaced within a decade (from {v['from']} to {v['to']}) exceeds the 15% range in which the "
                     "reduced-form labor and price rules were checked; without market clearing, unemployment persistence and wage effects in this range are overstated (spec §12).")
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


def region_series(ro, mg: list[str] | None = None) -> dict[str, Any]:
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
        "ai_spend_by_source_bn": _spend_sources(ro),
        "ai_spend_by_occupation_group_bn": _spend_groups(ro, mg or []),
        "net_ai_trade_bn": pct(ro.net_ai_trade, 1.0, 1), "regional_capability_index": pct(ro.C_region, 1.0, 2),
        # ---- v0.3 application layer (spec §A.6.3) ----
        "embodied_displacement_share": pct(ro.emb_share, 100.0) if ro.emb_share.size else {},
        "adjacent_jobs": pct(ro.adjacent_jobs, 1.0, 0) if ro.adjacent_jobs.size else {},
        "hardware_capex_bn": pct(ro.hw_capex_bn, 1.0, 2) if ro.hw_capex_bn.size else {},
        "underemployed_self_fte": pct(ro.underemp_self, 1.0, 0) if ro.underemp_self.size else {},
        "hours_cut_self_cum": pct(ro.cut_cum, 1.0, 0) if ro.cut_cum.size else {},
        "fleet_stock": {c: pct(v, 1.0, 0) for c, v in ro.fleet.items()},
        "coverage": {c: pct(v, 1.0, 3) for c, v in ro.coverage.items()},
        "approval_share": {c: pct(np.repeat(v[None, :], 2, axis=0), 1.0, 3) for c, v in ro.approval.items()},   # draw-independent: all percentiles equal
        # ---- Phase 7: output substitution and traded services (spec §A.4, §A.5.3) ----
        "ai_content_share": {c: pct(v, 100.0, 2) for c, v in ro.content_share.items()},
        "content_consumption_ratio": {c: pct(v, 1.0, 3) for c, v in ro.content_q.items()},
        "ai_content_revenue_bn": pct(ro.ai_content_revenue, 1.0, 2) if ro.ai_content_revenue.size else {},
        "consumer_surplus_proxy_bn": pct(ro.consumer_surplus, 1.0, 2) if ro.consumer_surplus.size else {},
        "traded_services_displacement_share": pct(ro.trade_share, 100.0, 3) if ro.trade_share.size else {},
        # ---- Phase 8: policy layer (spec §6.5 minimal, §A.16) ----
        "transfers_bn": pct(ro.transfers_bn, 1.0, 2) if ro.transfers_bn.size else {},
        "policy_cost_bn": pct(ro.policy_cost_bn, 1.0, 2) if ro.policy_cost_bn.size else {},
        "ai_tax_revenue_bn": pct(ro.ai_tax_revenue_bn, 1.0, 2) if ro.ai_tax_revenue_bn.size else {},
        "fiscal_balance_bn": pct(ro.fiscal_balance_bn, 1.0, 2) if ro.fiscal_balance_bn.size else {},
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


def applications_section(inp: Inputs, o: BatchOutput, apps: Any) -> list[dict[str, Any]]:
    """Per application and region (central draw): target employment, realized embodied displacement, coverage, approval, gate quarters (spec §A.6.3)."""
    if apps is None:
        return []
    q = o.quarters
    out = []
    for app in apps.apps:
        mask = apps.occ_mask(app, inp)
        codes = [inp.occ_codes[i] for i in np.flatnonzero(mask)]
        by_region: dict[str, Any] = {}
        for x in o.order:
            ro = o.regions[x]
            if not ro.D_emb.size:
                continue
            N0m = ro.N0[mask]                                                             # [n_m, n_q]
            if app.family == "embodied":
                De = ro.D_emb[0][mask]
            elif app.family == "traded":
                De = ro.D_trade[0][mask] if ro.D_trade.size else np.zeros_like(N0m)
            elif app.family == "output":
                cid = app.classes[0]
                sh = ro.content_share.get(cid); qq = ro.content_q.get(cid)
                De = np.repeat((1.0 - (1.0 - sh[0]) * qq[0])[None, :], N0m.shape[0], axis=0) if sh is not None else np.zeros_like(N0m)   # human output lost vs baseline
            else:
                De = ro.D_[0][mask]                                                       # software channel (central)
            tot = np.maximum(N0m.sum(axis=0), 1.0)
            disp = (De * N0m).sum(axis=0) / tot
            primary = next((c for c in app.classes if c in ro.coverage), None)          # gates of the primary (first-listed) class
            cov = ro.coverage[primary][0] if primary else (ro.content_share[app.classes[0]][0] if app.family == "output" and app.classes[0] in ro.content_share else np.zeros(len(q)))
            appr = ro.approval[primary] if primary and primary in ro.approval else np.zeros(len(q))
            def first(arr: np.ndarray, thr: float) -> str | None:
                idx = np.flatnonzero(arr >= thr)
                return q[int(idx[0])] if len(idx) else None
            by_region[x] = {"target_employment_2024": int(N0m[:, 0].sum()), "displacement_share": rl(disp, 100.0, 2),
                            "jobs_below_baseline": rl((De * N0m).sum(axis=0), 1.0, 0), "coverage": rl(cov, 1.0, 3), "approval": rl(appr, 1.0, 3),
                            "first_quarter": {"displacement_1pct": first(disp, 0.01), "displacement_10pct": first(disp, 0.10), "coverage_50pct": first(cov, 0.5)}}
        out.append({"app_id": app.app_id, "name": app.name, "family": app.family, "classes": app.classes, "platform": app.platform,
                    "occ_codes": codes, "regions_first": app.regions_first, "anchor": app.anchor, "constraints": app.constraints,
                    "provisional_profitable": app.provisional_profitable, "provisional_deployed50": app.provisional_deployed50, "by_region": by_region})
    return out


def _spend_sources(ro: Any) -> dict[str, Any]:
    """Who pays for AI (spec §A.16): employers replacing tasks (automation), employers buying tools (augmentation), consumers paying for AI-made content.
    AI income received by a region (`ai_rents_received_bn`) is the value-chain split of this spending across all regions."""
    if not ro.spend_aug.size:
        return {}
    content = ro.ai_content_revenue if ro.ai_content_revenue.size else np.zeros_like(ro.ai_spend)
    auto = np.maximum(ro.ai_spend - ro.spend_aug - content, 0.0)
    return {"automation": pct(auto, 1.0, 2), "augmentation": pct(ro.spend_aug, 1.0, 2), "content": pct(content, 1.0, 2), "total": pct(ro.ai_spend, 1.0, 2)}


def _spend_groups(ro: Any, mg: list[str], top: int = 8) -> dict[str, Any]:
    """Software AI spend by the occupation group whose work it replaces or speeds up, $bn/yr, keyed by group title:
    the largest groups at the horizon plus 'Other groups' (percentile dicts like every other series)."""
    if not ro.spend_by_mg.size:
        return {}
    tot = ro.spend_by_mg[0, :, -1]
    order = np.argsort(-tot)
    out: dict[str, Any] = {}; other = np.zeros_like(ro.spend_by_mg[:, 0, :])
    for rank, k in enumerate(order):
        if rank < top and tot[k] > 0.05:
            out[MG_TITLES.get(mg[k], mg[k])] = pct(ro.spend_by_mg[:, k, :], 1.0, 2)
        else:
            other = other + ro.spend_by_mg[:, k, :]
    out["Other groups"] = pct(other, 1.0, 2)
    return out


def forecasts_section(inp: Inputs, o: BatchOutput, apps: Any) -> list[dict[str, Any]]:
    """Forecaster scoreboard: each named claim against the model's central value and 10–90 band for the same quantity (spec v0.3 §A.16)."""
    if apps is None or not getattr(apps, "forecasts", None):
        return []
    q = o.quarters
    out = []
    for f in apps.forecasts:
        rid = f.get("region") or "US"; ro = o.regions.get(rid) or o.regions["US"]
        yq = f"{int(f['year'])}Q4"
        if yq not in q:
            out.append({**f, "model_central": None, "model_p10": None, "model_p90": None, "verdict": "outside horizon"}); continue
        t = q.index(yq); m = f["metric"]; arr = None; note = ""
        if m == "gdp_pct":
            arr = 100 * ro.gdp_pct[:, t]
        elif m == "tfp_pct":
            arr = 100 * ro.tfp_pct[:, t]
        elif m == "embodied_displacement_share":
            arr = 100 * ro.emb_share[:, t] if ro.emb_share.size else None
        elif m == "autonomous_share_of_ride_hail":
            arr = 100 * ro.coverage["driving"][:, t] if "driving" in ro.coverage else None; note = "model quantity: robotaxi deployment coverage of profitable ride-hail hours"
        elif m == "ride_hail_driver_displacement":
            idx = [i for i, c in enumerate(inp.occ_codes) if c in ("53-3054", "53-3053")]
            arr = 100 * (ro.D_emb[0][idx, t] * ro.N0[idx, t]).sum() / max(ro.N0[idx, t].sum(), 1.0) * np.ones(1) if ro.D_emb.size and idx else None; note = "central draw only"
        elif m == "physical_work_share":
            phys = sum(v for k, v in (o.trace.get("channels_task_hours") or {}).items() if k.startswith("emb_"))
            arr = 100 * ro.emb_share[:, t] / max(phys, 1e-6) if ro.emb_share.size and phys > 0 else None
            note = f"model quantity: robots' and vehicles' share of physical task-hours (embodied channels are {100*phys:.0f}% of all task-hours; the rest is office and analytical work done by software)"
        elif m == "humanoid_cost_per_hour_usd":
            arr = o.kappa_emb["manip"][:, t] if getattr(o, "kappa_emb", None) and "manip" in o.kappa_emb else None
            note = "model quantity: mobile-manipulation hardware cost per worker-hour equivalent (annualized unit price over utilized hours; integration excluded)"
        elif m == "exposed_share":
            arr = 100 * (o.automatable[:, :] * ro.N0[None, :, 0]).sum(axis=1) / max(ro.N0[:, 0].sum(), 1.0); note = "model quantity: ever-automatable task-hour share of employment (software + embodied)"
        elif m == "young_exposed_employment_pct":
            top = np.argsort(-inp.occ_exposure_beta)[: max(1, inp.n_occ // 10)]
            la = ro.lost_by_age[:, 0, t]; base = float(ro.N0_age[0]); arr = -100 * la / max(base, 1.0) * (ro.N0[top, 0].sum() / ro.N0[:, 0].sum()) ** 0 if la.size else None
            note = "model quantity: 16–24 employment effect (all occupations); the model does not split young workers by occupation exposure"
        if arr is None:
            out.append({**f, "model_central": None, "model_p10": None, "model_p90": None, "verdict": "not comparable", "note": (f.get("note", "") + "; " + note).strip("; ")}); continue
        arr = np.asarray(arr, dtype=float); central = float(arr[0]); lo = float(np.percentile(arr[1:], 10)) if arr.size > 1 else central; hi = float(np.percentile(arr[1:], 90)) if arr.size > 1 else central
        claimed = float(f["claimed"])
        verdict = "within band" if lo - 1e-9 <= claimed <= hi + 1e-9 else ("model lower" if claimed > hi else "model higher")
        out.append({**f, "quarter": yq, "model_central": round(central, 2), "model_p10": round(lo, 2), "model_p90": round(hi, 2), "verdict": verdict,
                    "note": (f.get("note", "") + ("; " + note if note else "")).strip("; ")})
    return out


def build_results_v3(inp: Inputs, o: BatchOutput, scenario: dict[str, Any], shash: str, channels: dict[str, Any] | None,
                     torn: dict[str, Any] | None, diff: list[dict[str, Any]] | None, draws: int, ensemble: str,
                     cohort_flag: str, regional: Any = None, apps: Any = None) -> dict[str, Any]:
    q = o.quarters
    flags = dict(inp.data_flags); flags["aei_anchoring"] = "unavailable"; flags["cohorts"] = cohort_flag
    conf = confidence(o, torn, q)
    cells = sorted({c for c in o.cell_ids if c != "central"})
    meta = {"spec_version": SPEC_VERSION, "schema_version": "0.4", "scenario_id": scenario.get("id"), "scenario_name": scenario.get("name"),
            "scenario_parent": scenario.get("parent"), "scenario_hash": shash, "seed": scenario.get("seed", 42),
            "run_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "draws": draws, "ensemble": ensemble, "cells": cells,
            "percentiles": PCTS, "quarters": q, "regions": ["US"], "baseline": "no_frontier_ai_after_2023", "data_flags": flags,
            "data_version": inp.data_version, "capability_units": "doublings of METR 50% task horizon (minutes = 2^index)",
            "fitted": o.trace.get("fitted"), "task_groups": o.trace.get("task_groups"), "validity": validity(o),
            "headline_definition": "FTE jobs including self-employed and platform workers (spec v0.3 §A.5.1); payroll-only employment is not separately tracked",
            "channels_task_hours": o.trace.get("channels_task_hours"), "self_employed_fte": o.trace.get("self_employed_fte"),
            "embodied_on": o.trace.get("embodied_on"), "content_categories": o.trace.get("content_categories"), "export_serving_fte": o.trace.get("export_serving_fte"),
            "policy_on": o.trace.get("policy_on"), "policy": o.trace.get("policy")}
    series = {x: region_series(o.regions[x], o.major_groups) for x in o.order}
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
        "embodiment": {c: {"clock": pct(o.C_emb[c], 1.0, 2), "unit_price_usd": pct(o.price_emb[c], 1.0, 0), "cost_per_hour_usd": pct(o.kappa_emb[c], 1.0, 2)}
                       for c in o.C_emb},
    }
    beta = inp.occ_exposure_beta
    occs = []
    for i in range(inp.n_occ):
        occs.append({"occ_code": inp.occ_codes[i], "title": inp.occ_titles[i], "cluster_id": inp.cluster_id[i], "major_group": inp.major_group[i],
                     "emp0": int(inp.emp0[i]), "wage0": int(inp.wage_mean[i]), "automatable_share": round(float(o.automatable[0, i]), 4),
                     "exposure_beta": round(float(beta[i]), 4), "displacement": slim(o.D_[:, i, :]), "augmentation": {"central": rl(o.U[0, i, :])},
                     "automatable_share_embodied": round(float(o.automatable_emb[0, i]), 4) if o.automatable_emb.size else 0.0,
                     "displacement_embodied": {"central": rl(o.us.D_emb[0, i, :])} if o.us.D_emb.size else {"central": []},
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
            "cohorts": cohorts_section(o), "flows": flows_section(o), "applications": applications_section(inp, o, apps), "forecasts": forecasts_section(inp, o, apps),
            "explain": {"notes": explain_notes(inp, o, conf), "trace": trace(o, q), "diff": annotate_diff(diff or [])}}

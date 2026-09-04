"""The story layer (Phase 8): one reconciled set of numbers, seven beats in plain language, named futures, what could be done,
a personal outlook, and an executive brief with inline charts.

Everything here reads the results document; nothing is computed by a model call. The executive brief deliberately carries no
parameter codes, percentiles, or section references: those stay in the technical brief (brief.py).
"""
from __future__ import annotations

import html
import json
import math
from typing import Any

import numpy as np
from aiwsim.data.regions import REGION_NAMES

HEAD = "employment_pct_vs_baseline"
WORLD = "WORLD"
WORLD_NAME = "the world (ten modelled regions)"
AGE_LABELS = {"16-24": "under 25", "25-44": "25 to 44", "45-54": "45 to 54", "55+": "55 and over"}
SURENESS = {"high": ("we would bet on it", 3), "medium": ("leaning this way", 2), "low": ("a coin flip", 1)}
FAMILY_WORDS = {"embodied": "robots and vehicles", "output": "AI-made content", "software": "software doing office tasks", "traded": "automation abroad"}
POLICY_HOW = {
    "policy-retraining": "Pays half the wage of workers who enrol in retraining, so more of the displaced retrain and more complete it; paid from the deficit.",
    "policy-wage-insurance": "Tops up the pay of displaced workers who take a lower-paid job, half the gap for two years; paid from a tax on AI spending.",
    "policy-ubi-ai-tax": "Pays every adult $500 a month, financed by an income-tax surcharge (balanced budget) with a 30% tax on AI spending on top.",
    "policy-work-week-36": "Shortens the standard week to 36 hours, so the same work is shared among more people; pay per head falls in step and total pay does not.",
}
CHANNEL_WORDS = {"automation": "software doing tasks", "augmentation": "faster work needing fewer people", "embodied": "robots and vehicles", "output_substitution": "AI-made content",
                 "traded_services": "automation abroad", "demand_response": "cheaper output selling more", "reinstatement": "new kinds of work", "demand_feedback": "workers' spending",
                 "ai_investment": "building AI itself", "adjacent": "jobs around AI"}


# ---------------------------------------------------------------- helpers
def region_name(region: str) -> str:
    return WORLD_NAME if region == WORLD else REGION_NAMES.get(region, region)


_MAX_KEYS = ("capability_index", "capability_horizon_hours", "regional_capability_index")
_WEIGHTED_TOKENS = ("_pct", "_pp_", "share", "ratio", "index", "multiplier", "coverage", "approval")
_PCTL = ("p10", "p25", "p50", "p75", "p90", "central")


def _world_rule(key: str) -> str:
    """How a series aggregates over regions: the capability clock is the frontier (max), rates and shares are
    employment-weighted means of each percentile, counts and dollars are sums (the same rules as the web app's World)."""
    if key in _MAX_KEYS:
        return "max"
    if any(t in key for t in _WEIGHTED_TOKENS):
        return "weighted"
    return "sum"


def _aggregate(parts: list[tuple[float, dict[str, list[float]] | None]], rule: str) -> dict[str, list[float]]:
    usable = [(w, s) for w, s in parts if isinstance(s, dict) and (s.get("p50") or s.get("central"))]
    out: dict[str, list[float]] = {}
    if not usable:
        return out
    for k in _PCTL:
        if not all(s.get(k) for _, s in usable):
            continue
        arrs = [np.asarray(s[k], dtype=float) for _, s in usable]; n = max(len(a) for a in arrs)
        stack = np.vstack([np.pad(a, (0, n - len(a)), constant_values=np.nan) for a in arrs])
        ws = np.asarray([w for w, _ in usable], dtype=float); ok = np.isfinite(stack)
        if rule == "max":
            v = np.max(np.where(ok, stack, -np.inf), axis=0)
        elif rule == "weighted":
            wsum = (ok * ws[:, None]).sum(axis=0)
            v = np.where(wsum > 0, (np.where(ok, stack, 0.0) * ws[:, None]).sum(axis=0) / np.where(wsum > 0, wsum, 1.0), 0.0)
        else:
            v = np.where(ok, stack, 0.0).sum(axis=0)
        out[k] = [float(x) if np.isfinite(x) else 0.0 for x in v]
    return out


def world_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """The document with a `WORLD` series block: every regional series combined under `_world_rule`, the self-employed
    stock summed and a regions row for the aggregate, so the story reads World like any other region."""
    series = doc.get("series") or {}
    ids = [r for r in doc["meta"].get("regions", []) if r in series] or list(series)
    if WORLD in series or len(ids) < 2:
        return doc
    weights = {r["region_id"]: float(r.get("employment_total") or 0.0) for r in doc.get("regions", [])}
    blk: dict[str, Any] = {}
    for key, val in series[ids[0]].items():
        rule = _world_rule(key)
        if isinstance(val, dict) and (val.get("p50") or val.get("central")):
            blk[key] = _aggregate([(weights.get(r, 0.0), series[r].get(key)) for r in ids], rule)
        elif isinstance(val, dict):
            blk[key] = {sub: _aggregate([(weights.get(r, 0.0), (series[r].get(key) or {}).get(sub)) for r in ids], rule) for sub in val}
    out = dict(doc); out["series"] = dict(series); out["series"][WORLD] = blk
    meta = dict(doc["meta"]); se = dict(meta.get("self_employed_fte") or {}); se[WORLD] = float(sum(se.get(r, 0.0) for r in ids)); meta["self_employed_fte"] = se
    out["meta"] = meta
    out["regions"] = [*doc.get("regions", []), {"region_id": WORLD, "name": WORLD_NAME, "employment_total": sum(weights.get(r, 0.0) for r in ids)}]
    return out


def _worldify(docs: dict[str, dict[str, Any]] | None) -> dict[str, dict[str, Any]] | None:
    return {k: world_doc(v) for k, v in docs.items()} if docs else docs


def _p(s: dict[str, list[float]], t: int, k: str = "p50") -> float:
    arr = s.get(k) or s.get("p50") or s.get("central")
    return float(arr[t]) if arr else 0.0


def _band(s: dict[str, list[float]], t: int) -> tuple[float, float, float]:
    return _p(s, t, "p10"), _p(s, t, "p50"), _p(s, t, "p90")


def _millions(x: float) -> str:
    x = abs(x)
    if x >= 1e9:
        return f"{x/1e9:.2f} billion"
    if x >= 1e6:
        return f"{x/1e6:.1f} million"
    if x >= 1e3:
        return f"{x/1e3:.0f},000"
    return f"{x:.0f}"


def _sure(level: str) -> dict[str, Any]:
    label, n = SURENESS.get(level, SURENESS["low"])
    return {"level": level, "label": label, "dots": n}


def _jobs_base(doc: dict[str, Any], region: str) -> float:
    """The denominator for turning a percentage into jobs: the frozen-AI employment level at the horizon (heads, modelled
    occupations plus self-employed and platform workers), so 'x% fewer' and the levels chart agree; older documents fall back
    to 2024 employment plus the self-employed stock."""
    blk = (doc.get("series") or {}).get(region) or (doc.get("series") or {}).get("US") or {}
    lvl0 = blk.get("baseline_employment_level") or {}
    if lvl0.get("central") or lvl0.get("p50"):
        return _p(lvl0, len(doc["meta"]["quarters"]) - 1)
    rg = next((r for r in doc.get("regions", []) if r["region_id"] == region), None)
    base = float(rg["employment_total"]) if rg else 0.0
    return base + float((doc["meta"].get("self_employed_fte") or {}).get(region, 0.0))


def _quarter_year(q: str | None) -> str | None:
    return q[:4] if q else None


def _row_when(f: dict[str, Any]) -> str:
    return str(f["year"]) if f.get("metric") == "ai_layoffs_in_year" else f"2023 to {_quarter_words(str(f.get('quarter') or ''))}"


def _quarter_words(q: str) -> str:
    months = {"1": "March", "2": "June", "3": "September", "4": "December"}
    return f"{months.get(q[-1], '')} {q[:4]}".strip() if len(q) == 6 else q


# ---------------------------------------------------------------- beats
def story(doc: dict[str, Any], region: str = "US", policy_docs: dict[str, dict[str, Any]] | None = None,
          futures_docs: dict[str, dict[str, Any]] | None = None, policy_base: dict[str, Any] | None = None,
          variant_docs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """The whole story for one run. `policy_docs` are the policy scenarios, read as differences from `policy_base`
    (the baseline they modify; defaults to `doc`); `futures_docs` are scenario runs shown as named futures;
    `variant_docs` are behavioural variants (the layoffs-first run feeds the hiring beat)."""
    if region == WORLD:
        doc = world_doc(doc); policy_docs = _worldify(policy_docs); futures_docs = _worldify(futures_docs); variant_docs = _worldify(variant_docs)
        policy_base = world_doc(policy_base) if policy_base else policy_base
    q = doc["meta"]["quarters"]; t40 = len(q) - 1; t30 = q.index("2030Q4") if "2030Q4" in q else t40
    blk = doc["series"].get(region) or doc["series"]["US"]
    yr = q[t40][:4]
    base = _jobs_base(doc, region)
    conf = lambda m, qq=q[t40]: (doc.get("confidence", {}).get(m, {}).get(qq) or {}).get("level", "low")

    # ---- reconciled numbers (one convention: medians; jobs in heads) ----
    e10, e50, e90 = _band(blk[HEAD], t40)
    jobs_gap = -e50 / 100 * base; jobs_lo = -e10 / 100 * base; jobs_hi = -e90 / 100 * base
    us_detail = region == "US"
    rname = region_name(region)
    # the people ledger: the U.S. reads the flows section (destinations of the displaced); every other region reads its own series
    flows = doc.get("flows", {}).get("destinations", {}) if us_detail else {}
    def _people(flow_key: str, series_key: str) -> float:
        return _p(flows[flow_key], t40) if flow_key in flows else _p(blk.get(series_key, {}), t40)
    displaced = _p(blk["displaced_workers_cum"], t40); reemp = _people("reemployed", "reemployed_cum")
    unemployed = _p(blk["unemployed_stock"], t40); exited = _people("exited", "exited_cum")
    unfilled = _people("unfilled_entry", "unhired_entrants_cum"); laid = _people("laid_off", "laid_off_cum")
    peak_t = int(max(range(len(q)), key=lambda i: _p(blk["unemployed_stock"], i))); peak_unemp = _p(blk["unemployed_stock"], peak_t)
    g50 = _p(blk["gdp_pct_vs_baseline"], t40); rw10, rw50, rw90 = _band(blk["real_wage_pct_vs_baseline"], t40)
    price = _p(blk["price_index_pct_vs_baseline"], t40); wshare = _p(blk["wage_share_pp_vs_baseline"], t40)
    hours_cut = _people("self_employed_margin_cum", "hours_cut_self_cum")
    removed, added = _channel_split(doc, region, t40, base)
    recon = _reconciliation(yr, base, jobs_gap, displaced, reemp, unemployed, exited, unfilled, laid, hours_cut, removed, added)
    numbers = {"jobs_base": round(base), "jobs_gap": round(jobs_gap), "jobs_gap_low": round(jobs_lo), "jobs_gap_high": round(jobs_hi),
               "employment_pct": {"p10": e10, "p50": e50, "p90": e90}, "displaced_cum": round(displaced), "reemployed": round(reemp),
               "unemployed_extra": round(unemployed), "exited": round(exited), "unfilled": round(unfilled), "laid_off": round(laid), "hours_cut_self": round(hours_cut),
               "jobs_removed_by_channel": removed, "jobs_added_by_channel": added,
               "unemployment_peak": {"quarter": q[peak_t], "extra": round(peak_unemp)}, "gdp_pct": g50, "real_wage_pct": {"p10": rw10, "p50": rw50, "p90": rw90},
               "price_index_pct": price, "wage_share_pp": wshare, "reconciliation": recon}

    sp = structural_spread(doc)
    beats: list[dict[str, Any]] = []
    # 1. The jobs ledger in levels: today, 2040 without AI, 2040 with AI
    lvl = blk.get("employment_level") or {}; lvl0 = blk.get("baseline_employment_level") or {}
    today = _p(lvl0, 0) if lvl0 else base; without = _p(lvl0, t40) if lvl0 else base
    numbers["jobs_today"] = round(today); numbers["jobs_2040_no_ai"] = round(without)
    with50 = _p(lvl, t40) if lvl else without * (1 + e50 / 100); with10 = _p(lvl, t40, "p10") if lvl else without * (1 + e10 / 100); with90 = _p(lvl, t40, "p90") if lvl else without * (1 + e90 / 100)
    vs_today = with50 / max(today, 1.0) - 1.0
    if vs_today >= 0.01:
        title1 = "More jobs than today, fewer than there would have been"; today_words = f"about {100*vs_today:.0f}% more than today"
    elif vs_today <= -0.01:
        title1 = "Fewer jobs than today, and fewer still than there would have been"; today_words = f"about {abs(100*vs_today):.0f}% fewer than today"
    else:
        title1 = "About as many jobs as today, fewer than there would have been"; today_words = "about the same as today"
    beats.append({"id": "jobs", "title": title1,
                  "sentence": f"There are about {_millions(today)} jobs today. Without further AI progress, population and normal growth would take that to about {_millions(without)} by {yr}. "
                              f"With AI the model's median is about {_millions(with50)} ({today_words}; likely between {_millions(with10)} and {_millions(with90)}): "
                              f"about {_millions(jobs_gap)} fewer than there would have been, one job in {round(base / max(jobs_gap, 1.0))} " + ("never created rather than destroyed." if unfilled > 3 * max(laid, 1.0) else "removed.")
                              + (f" The biggest remover is {CHANNEL_WORDS[max(removed, key=removed.get)]}; the biggest offset is {CHANNEL_WORDS[max(added, key=added.get)]}." if removed and added else ""),
                  "range": f"Across the model's assumptions, between {_millions(jobs_lo)} fewer and {'no loss at all' if jobs_hi <= 0 else _millions(jobs_hi) + ' fewer'} than there would have been; "
                           f"against today, between {abs(100*(with10/max(today,1.0)-1)):.0f}% {'fewer' if with10 < today else 'more'} and {abs(100*(with90/max(today,1.0)-1)):.0f}% {'fewer' if with90 < today else 'more'}."
                           + (f" The model's mechanism cells alone span {sp['min']:+.1f}% to {sp['max']:+.1f}%." if sp else ""),
                  "sureness": _sure("low" if (sp and not sp["agree_on_sign"]) else conf(HEAD)), "what_changes_it": "Whether households' spending of the gains feeds back into hiring (the macro closure) and how strongly (the demand multiplier); with the feedback off the gap is about a third larger.",
                  "chart": {"type": "fan", "series": {"employment": {k: blk[HEAD][k] for k in ("p10", "p50", "p90") if k in blk[HEAD]},
                                                      "gdp": {k: blk["gdp_pct_vs_baseline"][k] for k in ("p10", "p50", "p90") if k in blk["gdp_pct_vs_baseline"]}}, "quarters": q},
                  "extra_chart": {"type": "bars", "title": f"Jobs in millions: today, {yr} without AI, {yr} with AI",
                                  "items": [["Today (2024)", round(today / 1e6, 1)], [f"{yr} without AI", round(without / 1e6, 1)], [f"{yr} with AI, median", round(with50 / 1e6, 1)],
                                            [f"{yr} with AI, low", round(with10 / 1e6, 1)], [f"{yr} with AI, high", round(with90 / 1e6, 1)]], "unit": "M jobs"},
                  "levels": {"today": round(today), "without_ai": round(without), "with_ai": {"p10": round(with10), "p50": round(with50), "p90": round(with90)}}})
    # 2. Most of the gap is hiring that never happens; and a reality check against announced AI layoffs
    tot_lost = max(unfilled + laid + hours_cut, 1.0)
    obs = [f for f in doc.get("forecasts", []) if str(f.get("short", "")).startswith("Challenger") and f.get("model_central") is not None] if us_detail else []
    reality = ""
    if obs:
        parts = []
        for f in obs:
            when = f"in {f['year']}" if f.get("metric") == "ai_layoffs_in_year" else f"since 2023 through {_quarter_words(f.get('quarter') or '')}"
            parts.append(f"{f['claimed']:,.0f} AI-cited job cuts {when} (model: {f['model_central']:,.0f})")
        reality = (" Reality check: employers announced " + " and ".join(parts) + ", by Challenger, Gray & Christmas's count. The baseline's layoff pace is fitted to these counts: a quarter of each required cut "
                   "is taken as layoffs at once rather than waiting for attrition. The counts are announcements, which include positions closed by attrition and redeployment, so the fit is deliberately loose; "
                   "without it the model's attrition-first rule produced a tenth of the announced layoffs.")
    var_words = ""
    vdoc = (variant_docs or {}).get("variant-layoffs-first") or next(iter(v for k, v in (variant_docs or {}).items() if "layoff" in k), None)
    if vdoc:
        vb = vdoc["series"].get(region) or vdoc["series"]["US"]; vq = vdoc["meta"]["quarters"]; vt = len(vq) - 1; vt30 = vq.index("2030Q4") if "2030Q4" in vq else vt
        v_laid30 = _p(vb["laid_off_cum"], vt30, "central"); v_laid = _p(vb["laid_off_cum"], vt, "central")
        v_peak = max(_p(vb["unemployed_stock"], i, "central") for i in range(len(vq))); v_e = _p(vb[HEAD], vt, "central"); e_c = _p(blk[HEAD], t40, "central")
        var_words = (" If employers cut through layoffs twice as readily (the layoffs-first variant): "
                     f"{_millions(v_laid30)} layoffs by 2030 and {_millions(v_laid)} by {yr} instead of {_millions(laid)}, unemployment peaking {_millions(v_peak)} above the no-AI path, "
                     f"and total jobs {'about the same' if abs(v_e - e_c) < 0.5 else f'{v_e - e_c:+.1f} points different'}: the same gap, borne by incumbents instead of entrants.")
    lay_share = laid / max(unfilled + laid, 1.0)
    beats.append({"id": "hiring", "title": f"Most of the gap is hiring that never happens; about one position in {max(round(1 / max(lay_share, 1e-6)), 2)} removed is a layoff",
                  "sentence": f"Of the {_millions(tot_lost)} positions AI takes out of the economy by {yr} in the central run, {_millions(unfilled)} are jobs never offered to new entrants and {_millions(laid)} are layoffs. "
                              f"Unemployment rises by at most {_millions(peak_unemp)} at its {q[peak_t][:4]} peak. Of the people affected, {_millions(reemp)} find other work and {_millions(exited)} leave the workforce."
                              + reality + var_words,
                  "range": "Hiring-first holds in every scenario the model ships; the layoff share is fitted to 2025–2026 announcements and is the least certain number here.",
                  "sureness": _sure("medium" if obs else ("high" if unfilled / tot_lost > 0.85 else "medium")),
                  "what_changes_it": "How fast employers cut ahead of attrition: the attrition rate and the layoff pace, both levers in the technical brief. Faster cuts do not change the total; they move it from entrants to incumbents and raise the unemployment peak.",
                  "chart": {"type": "bars", "items": [["Positions never refilled", unfilled], ["Layoffs", laid], ["Found other work", reemp], ["Left the workforce", exited], ["Still unemployed", unemployed]]}})
    if obs:
        beats[-1]["extra_chart"] = {"type": "bars", "title": "AI-cited job cuts: announced versus the model's layoffs",
                                    "items": [[f"Announced, {_row_when(f)}", float(f["claimed"])] for f in obs] + [[f"Model, {_row_when(f)}", float(f["model_central"])] for f in obs]}
        beats[-1]["reality_check"] = [{"short": f["short"], "claimed": f["claimed"], "model_central": f["model_central"], "verdict": f["verdict"], "unit": f["unit"]} for f in obs]
    # 3. The young pay first
    ages = doc.get("cohorts", {}).get("age", []); edu = doc.get("cohorts", {}).get("education", []); dec = doc.get("cohorts", {}).get("income_decile", [])
    if ages:
        share = {a["band"]: _p(a["share_of_jobs_lost"], t40) for a in ages}; own = {a["band"]: _p(a["employment_pct_vs_baseline"], t40) for a in ages}
        young = share.get("16-24", 0.0); young_own = own.get("16-24", 0.0); mid_own = own.get("25-44", 0.0); old_own = own.get("55+", 0.0)
        e_lo = _p(edu[0]["employment_pct_vs_baseline"], t40) if edu else 0.0; e_hi = _p(edu[-1]["employment_pct_vs_baseline"], t40) if edu else 0.0
        d_lo = sum(_p(x["employment_pct_vs_baseline"], t40) for x in dec[:5]) / 5 if dec else 0.0; d_hi = _p(dec[-1]["employment_pct_vs_baseline"], t40) if dec else 0.0
        beats.append({"id": "young", "title": "The young pay first" + ("" if us_detail else " (U.S. detail)"),
                      "sentence": ("" if us_detail else "Age, education and income splits are modelled for the United States only; there, w") + f"{'W' if us_detail else ''}orkers under 25 carry {100*young:.0f}% of the shortfall, about {abs(young_own):.0f}% of their group's jobs, against {abs(mid_own):.0f}% for 25 to 44 and "
                                  f"{'almost nothing' if abs(old_own) < 0.5 else f'{abs(old_own):.0f}%'} for those over 55. Workers without a degree lose "
                                  f"{_ratio_words(e_lo, e_hi, 'graduates')}, and the bottom half of earners lose {_ratio_words(d_lo, d_hi, 'the top tenth')}.",
                      "range": "Incumbents are mostly safe; entrants are not. That is the practical advice hidden in the numbers.",
                      "sureness": _sure("medium" if conf(HEAD) != "high" else "high"),
                      "what_changes_it": "Whether employers cut through attrition (which lands on entrants) or through layoffs (which lands on incumbents).",
                      "chart": {"type": "bars", "items": [[AGE_LABELS.get(a["band"], a["band"]), 100 * _p(a["share_of_jobs_lost"], t40)] for a in ages],
                                "reference": [[AGE_LABELS.get(b, b), 100 * v] for b, v in zip([a["band"] for a in ages], _age_employment_shares(doc), strict=False)], "unit": "% of jobs lost"}})
    # 4. Pay up, worker share down
    wage_usd = 2500 * (rw50 / 4.1) if rw50 else 0.0
    beats.append({"id": "pay", "title": "Pay goes up, the worker's share goes down",
                  "sentence": f"Real pay is about {rw50:.0f}% higher by {yr} (roughly ${wage_usd:,.0f} a year for a $60,000 earner) because prices fall about {abs(price):.0f}%. "
                              f"The economy is about {g50:.0f}% larger. But workers' share of national income falls by {abs(wshare):.1f} points: the gains are real and they go disproportionately to owners.",
                  "range": f"Real pay likely between {rw10:+.0f}% and {rw90:+.0f}%.", "sureness": _sure(conf("real_wage_pct_vs_baseline")),
                  "what_changes_it": "How much of the cost saving reaches prices; if firms keep it as margin, pay rises less and the owner share rises more.",
                  "chart": {"type": "bars", "items": [["Economy (GDP)", g50], ["Real pay", rw50], ["Prices", price], ["Workers' share of income (points)", wshare]], "unit": "% by " + yr}})
    wdoc = (variant_docs or {}).get("variant-market-clearing-wages")
    if wdoc:
        wb = wdoc["series"].get(region) or wdoc["series"]["US"]; wq = wdoc["meta"]["quarters"]; wt = len(wq) - 1
        w_rw = _p(wb["real_wage_pct_vs_baseline"], wt, "central"); w_e = _p(wb[HEAD], wt, "central"); e_c = _p(blk[HEAD], t40, "central")
        w_ages = wdoc.get("cohorts", {}).get("age", []); w_young = next((_p(a["share_of_jobs_lost"], wt, "central") for a in w_ages if a["band"] == "16-24"), None)
        young_c = next((_p(a["share_of_jobs_lost"], t40, "central") for a in doc.get("cohorts", {}).get("age", []) if a["band"] == "16-24"), None)
        rw_c = _p(blk["real_wage_pct_vs_baseline"], t40, "central")
        def _cmp(v: float, c: float, unit: str, nd: int = 0) -> str:
            return "about the same" if abs(v - c) < 0.5 else f"{v:+.{nd}f}{unit} instead of {c:+.{nd}f}{unit}"
        beats[-1]["sentence"] += (" If wages absorb more of the excess supply (the market-clearing wage variant: wage adjustment, pass-through and reinstatement at the top of their ranges): "
                                  f"real pay {_cmp(w_rw, rw_c, '%')}, total jobs {'about the same' if abs(w_e - e_c) < 0.5 else f'{w_e - e_c:+.1f} points different'}"
                                  + (f", and the under-25 share of the shortfall {'about the same' if abs(100*w_young - 100*young_c) < 0.5 else f'{100*w_young:.0f}% instead of {100*young_c:.0f}%'}" if w_young is not None and young_c is not None else "") + ".")
    # 5. Three waves
    apps = doc.get("applications", [])
    waves = []
    for a in apps:
        br = a["by_region"].get(region) or a["by_region"].get("US")
        if not br:
            continue
        gate = br["first_quarter"].get("displacement_1pct")
        waves.append({"app": a["name"], "family": a["family"], "family_words": FAMILY_WORDS.get(a["family"], a["family"]), "first_year": _quarter_year(gate),
                      "share_2030": br["displacement_share"][t30], "share_2040": br["displacement_share"][t40], "target_jobs": br["target_employment_2024"]})
    occs = doc.get("occupations", [])
    big = [o for o in occs if o["emp0"] >= 200_000]
    emb = blk.get("embodied_displacement_share", {}); content = blk.get("ai_content_share", {})
    content_sorted = sorted(((k, _p(v, t40)) for k, v in content.items()), key=lambda kv: -kv[1])
    if us_detail:
        worst30 = sorted(big, key=lambda o: _p(o["employment_pct_vs_baseline"], t30))[:4]
        worst40 = sorted(big, key=lambda o: _p(o["employment_pct_vs_baseline"], t40))[:4]
        best40 = sorted(big, key=lambda o: -_p(o["employment_pct_vs_baseline"], t40))[:4]
        first_words = "Office and analytical work is being reshaped now: " + ", ".join(f"{o['title'].lower()} ({_p(o['employment_pct_vs_baseline'], t30):+.0f}%)" for o in worst30) + " by 2030. "
        growing_words = "Growing: " + ", ".join(f"{o['title'].lower()} ({_p(o['employment_pct_vs_baseline'], t40):+.0f}%)" for o in best40) + "."
        occ_lists: dict[str, Any] | None = {"hit_first": [[o["title"], _p(o["employment_pct_vs_baseline"], t30)] for o in worst30], "hit_most": [[o["title"], _p(o["employment_pct_vs_baseline"], t40)] for o in worst40],
                                            "growing": [[o["title"], _p(o["employment_pct_vs_baseline"], t40)] for o in best40]}
    else:
        # employment by occupation is U.S. detail; the region has its own automated task share per occupation (the U.S. task mix tilted by income)
        def _auto(o: dict[str, Any], t: int) -> float:
            return 100 * _p((o.get("by_region") or {}).get(region, {}).get("displacement", {}), t, "central")
        ranked = [o for o in big if _auto(o, t30) > 0]
        first = sorted(ranked, key=lambda o: -_auto(o, t30))[:4]
        first_words = ((f"Office and analytical work is being reshaped now; the occupations whose work is most automated in {rname} by 2030: "
                        + ", ".join(f"{o['title'].lower()} ({_auto(o, t30):.0f}% of task-hours)" for o in first) + ". ")
                       if first else "Office and analytical work is being reshaped now. ")
        growing_words = "Job counts by occupation are U.S. detail (the Occupations view); the region's totals are in the first finding."
        occ_lists = None
    beats.append({"id": "waves", "title": "Three waves, not one",
                  "sentence": (first_words
                               + f"Robots and vehicles arrive later: {_p(emb, t30):.1f}% of task-hours in 2030, {_p(emb, t40):.1f}% by {yr}. "
                               + (f"AI-made content takes {content_sorted[0][0].replace('_', ' and ')} first ({content_sorted[0][1]:.0f}% of spending by {yr}) and {content_sorted[-1][0]} last ({content_sorted[-1][1]:.0f}%). " if content_sorted else "")
                               + growing_words),
                  "range": "Timing of the robot wave depends on how fast fleets can be built and approved, not on the software.",
                  "sureness": _sure("medium"), "what_changes_it": "Production ramps, permits, and hardware costs for the robot wave; how much people keep paying for human-made work for the content wave.",
                  "chart": {"type": "timeline", "items": [w for w in waves if w["first_year"]], "start": int(q[0][:4]), "end": int(q[-1][:4])},
                  **({"occupations": occ_lists} if occ_lists else {})})
    # 6. Where the money goes
    regions = [x for x in doc["meta"].get("regions", []) if x in doc["series"]]
    rents = {x: _p(doc["series"][x]["ai_rents_received_bn"]["total"], t40) for x in regions}
    remp = {x: _p(doc["series"][x][HEAD], t40) for x in regions}; rgdp = {x: _p(doc["series"][x]["gdp_pct_vs_baseline"], t40) for x in regions}
    top = sorted(rents.items(), key=lambda kv: -kv[1])[:4]
    src, groups, stages = _income_sources(doc, region, regions, t40)
    beats.append({"id": "money", "title": "The money flows to the U.S. and the chip makers",
                  "sentence": f"By {yr} " + ", ".join(f"{x} collects about ${v:.0f} billion a year in AI income" for x, v in top[:1]) + "; " + ", ".join(f"{x} ${v:.0f} billion" for x, v in top[1:]) + ". "
                              + f"The largest GDP gains are in {', '.join(x for x, _ in sorted(rgdp.items(), key=lambda kv: -kv[1])[:2])} (chip exports); "
                              + f"the largest job losses in {', '.join(x for x, _ in sorted(remp.items(), key=lambda kv: kv[1])[:2])}. "
                              + _sources_sentence(src, groups, stages, yr),
                  "range": "Regional splits rest on where models, data centres and chips are made; the country-level job numbers outside the U.S. use placeholder occupation mixes.",
                  "sureness": _sure("medium"), "what_changes_it": "Data-localization rules, export controls, and where the next fabs and data centres are built.",
                  "chart": {"type": "regions", "items": [[x, remp[x], rgdp[x], rents[x]] for x in regions]},
                  "extra_chart": {"type": "bars", "title": f"Where the money comes from, {yr} ($bn a year, all regions)",
                                  "items": [["Software replacing tasks", src.get("automation", 0.0)], ["Tools that speed up workers", src.get("augmentation", 0.0)],
                                            ["AI subscriptions and services (consumers)", src.get("consumer", 0.0)], ["AI-made content (consumers)", src.get("content", 0.0)]] + [[f"Work bought: {t}", v] for t, v in groups[:6]], "unit": "$bn"},
                  "income": {"sources_world_bn": src, "paying_groups_world_bn": groups, "received_by_stage_bn": stages}})
    # 7. Two futures, and the difference is a choice
    futures = named_futures(doc, region, futures_docs)
    beats.append({"id": "futures", "title": "Two futures, and the difference is partly a choice",
                  "sentence": " ".join(f"{f['name']}: {f['description']}" for f in futures),
                  "range": "The model's biggest uncertainty is whether the gains are spent back into the economy or pocketed; that is partly policy, partly corporate behaviour, and partly what people choose to pay for.",
                  "sureness": _sure("low"), "what_changes_it": "See the futures and the policy runs below.", "chart": {"type": "futures", "items": futures}})

    policies = policy_runs(policy_base or doc, policy_docs or {}, region)
    investment = investment_story(doc)
    caveats = _caveats(doc)
    return {"scenario_hash": doc["meta"]["scenario_hash"], "scenario_id": doc["meta"].get("scenario_id"), "scenario_name": doc["meta"].get("scenario_name"),
            "region": region, "region_name": rname, "horizon": [q[0], q[-1]], "numbers": numbers, "beats": beats, "futures": futures, "policies": policies,
            "policies_against": (policy_base or doc)["meta"].get("scenario_name"), "investment": investment, "backtest": backtest_story(doc), "structural_spread": sp, "caveats": caveats,
            "forecasts": doc.get("forecasts", []), "glossary": glossary(numbers, rname)}


def _ratio_words(lo: float, hi: float, other: str) -> str:
    """'3 times as much as X', or a plain comparison when the other group is barely touched."""
    if abs(hi) < 0.5:
        return f"about {abs(lo):.0f}% of their jobs while {other} {'are' if other.endswith('s') else 'is'} barely affected"
    r = abs(lo) / abs(hi)
    if r < 1.15:
        return f"about as much as {other}"
    return f"{r:.0f} times as much as {other}" if r >= 1.5 else f"{r:.1f} times as much as {other}"


def _channel_split(doc: dict[str, Any], region: str, t: int, base: float) -> tuple[dict[str, float], dict[str, float]]:
    """Jobs removed and added by channel (from the central-run decomposition, U.S. only; empty elsewhere)."""
    if region != "US":
        return {}, {}
    ch = doc.get("channels", {}).get(HEAD, {}).get("contributions", {})
    removed = {k: round(-v[t] / 100 * base) for k, v in ch.items() if v[t] < -0.005}
    added = {k: round(v[t] / 100 * base) for k, v in ch.items() if v[t] > 0.005}
    return removed, added


def _reconciliation(yr: str, base: float, net: float, displaced: float, reemp: float, unemployed: float, exited: float, unfilled: float, laid: float,
                    hours_cut: float, removed: dict[str, float], added: dict[str, float]) -> str:
    """One paragraph that keeps the jobs ledger (positions) and the people ledger (who was affected, where they went) apart and says why they differ."""
    s = f"Jobs: about {_millions(net)} fewer exist in {yr} than there would have been"
    if removed and added:
        top_r = max(removed.items(), key=lambda kv: kv[1]); top_a = max(added.items(), key=lambda kv: kv[1])
        s += f"; the biggest remover is {CHANNEL_WORDS.get(top_r[0], top_r[0])}, the biggest offset {CHANNEL_WORDS.get(top_a[0], top_a[0])}"
    s += (f". People: over the period about {_millions(displaced)} found the job they had, or would have had, gone: {_millions(unfilled)} positions never offered to new entrants, "
          f"{_millions(laid)} layoffs" + (f", {_millions(hours_cut)} full-time equivalents of gig and freelance hours cut" if hours_cut >= 50_000 else "") + ". ")
    s += (f"Of them, {_millions(reemp)} found other work, {_millions(exited)} left the workforce and {_millions(unemployed)} are unemployed in {yr}. "
          "The two ledgers differ because someone who finds other work fills a position that would otherwise have gone to someone else: the jobs ledger counts positions, the people ledger counts people.")
    return s


def _income_sources(doc: dict[str, Any], region: str, regions: list[str], t: int) -> tuple[dict[str, float], list[tuple[str, float]], dict[str, float]]:
    """World AI spending by who pays (automation, augmentation, content) and by the occupation group whose work is bought, plus the region's receipts by value-chain stage."""
    src: dict[str, float] = {}; groups: dict[str, float] = {}
    for x in regions:
        blk = doc["series"][x]
        for k, v in (blk.get("ai_spend_by_source_bn") or {}).items():
            if k != "total":
                src[k] = src.get(k, 0.0) + _p(v, t)
        for title, v in (blk.get("ai_spend_by_occupation_group_bn") or {}).items():
            if title != "Other groups":
                groups[title] = groups.get(title, 0.0) + _p(v, t)
    rb = doc["series"].get(region) or doc["series"]["US"]
    stages = {k: _p(v, t) for k, v in (rb.get("ai_rents_received_bn") or {}).items() if k != "total"}
    src = {k: round(v, 1) for k, v in src.items()}; stages = {k: round(v, 1) for k, v in stages.items()}
    return src, sorted(((t, round(v, 1)) for t, v in groups.items()), key=lambda kv: -kv[1]), stages


def _sources_sentence(src: dict[str, float], groups: list[tuple[str, float]], stages: dict[str, float], yr: str) -> str:
    tot = sum(src.values())
    if tot <= 0:
        return ""
    share = lambda k: 100 * src.get(k, 0.0) / tot
    s = (f"That income is paid by employers replacing tasks with software ({share('automation'):.0f}% of the ${tot:.0f} billion spent on AI worldwide in {yr}), "
         f"employers buying tools that speed up workers ({share('augmentation'):.0f}%), consumers paying for AI subscriptions and services ({share('consumer'):.0f}%), and consumers paying for AI-made content ({share('content'):.0f}%)")
    if groups:
        s += "; the work being bought is mostly " + ", ".join(f"{t.lower()} (${v:.0f} billion)" for t, v in groups[:3])
    if stages:
        top = sorted(stages.items(), key=lambda kv: -kv[1])[:3]
        s += ". It lands with " + ", ".join(f"{STAGE_WORDS.get(k, k)} (${v:.0f} billion)" for k, v in top) + "."
    else:
        s += "."
    return s


STAGE_WORDS = {"model": "the model makers", "compute": "the cloud and data-centre operators", "chips": "the chip makers", "integration": "local integrators and platforms", "fabs": "the fabs", "energy": "energy suppliers"}


def backtest_story(doc: dict[str, Any]) -> dict[str, Any] | None:
    """The model scored against 2024-2026 observations, with a plain sentence per series (contracts §29)."""
    bt = doc.get("backtest")
    if not bt or not bt.get("rows"):
        return None
    sentences = []
    for sm in bt["summary"].values():
        if sm.get("n"):
            fit = " (a calibration target, so not evidence)" if sm.get("used_in_fit") else ""
            sentences.append(f"{sm['label']}: the model is off by {sm['mape_pct']:.0f}% on average over {sm['n']} observations, "
                             f"{'above' if sm['bias_pct'] > 0 else 'below'} the observed values{fit}.")
        else:
            sentences.append(f"{sm['label']}: the model does not track this quantity; shown for context.")
    return {"horizon": bt["horizon"], "rows": bt["rows"], "summary": bt["summary"], "sentences": sentences, "notes": bt.get("notes", [])}


def investment_story(doc: dict[str, Any]) -> dict[str, Any] | None:
    """Investment versus returns: the capex being poured into data centres and power against what the model says AI earns and
    what it adds to the economy. World totals, central run, from the results document's `investment` section."""
    inv = doc.get("investment")
    if not inv or not inv.get("rows"):
        return None
    rows = {r["year"]: r for r in inv["rows"]}; years = inv["years"]; y0, yN = years[0], years[-1]
    pm = doc["meta"].get("price_multiple_path") or []
    if pm:
        qs = doc["meta"]["quarters"]
        for y, r in rows.items():
            t = max(i for i, x in enumerate(qs) if int(x[:4]) == y); r["price_multiple"] = pm[t]
    r26 = rows.get(2026) or rows[y0]; r30 = rows.get(2030) or r26; rN = rows[yN]
    obs = [(y, r["capex_observed_bn"]) for y, r in rows.items() if r.get("capex_observed_bn")]
    cum = inv["cumulative_2024_to_horizon"]
    payback = next((y for y in years if sum(rows[k]["producer_revenue_bn"] for k in years if k <= y) >= sum(rows[k]["capex_model_bn"] for k in years if k <= y)), None)
    econ_payback = next((y for y in years if sum(rows[k]["productivity_gain_bn"] for k in years if k <= y) >= sum(rows[k]["capex_model_bn"] for k in years if k <= y)), None)
    ratio_rev = cum["producer_revenue_bn"] / max(cum["capex_model_bn"], 1.0); ratio_prod = cum["productivity_gain_bn"] / max(cum["capex_model_bn"], 1.0)
    def money(v: float) -> str:
        return f"${v/1000:,.1f} trillion" if abs(v) >= 1000 else f"${v:,.0f} billion"
    para = [
        (f"The money going in. The four largest cloud companies spent about {money(obs[-2][1] if len(obs) > 1 else r26['capex_model_bn'])} on data centres, chips and power in {obs[-2][0] if len(obs) > 1 else y0} and have guided to about "
        f"{money(obs[-1][1])} for {obs[-1][0]}. The model takes that path as given: {money(r26['capex_model_bn'])} in 2026, rising to {money(r30['capex_model_bn'])} a year by 2030 and flat after, "
        f"about {money(cum['capex_model_bn'])} over {y0}–{yN}."),
        (f"The money coming back to AI producers. In the model, employers and consumers spend {money(r26['producer_revenue_bn'])} a year on AI in 2026, {money(r30['producer_revenue_bn'])} by 2030 and "
        f"{money(rN['producer_revenue_bn'])} by {yN}: {money(cum['producer_revenue_bn'])} over the period, {100*ratio_rev:.0f}% of the capital spent. "
        + (f"Producers' cumulative revenue passes cumulative capex in {payback}." if payback else f"Producers' cumulative revenue never catches up with cumulative capex by {yN}.")
        + f" It has three parts: what employers pay to replace and speed up work at market prices (token cost times a price multiple that starts near {rows[y0].get('price_multiple', 4.0):.0f}x and compresses with competition), "
          f"what consumers pay for AI subscriptions and services ({money(r26.get('consumer_revenue_bn', 0.0))} in 2026, {money(rN.get('consumer_revenue_bn', 0.0))} by {yN}), and AI-made content. "
          "The path is fitted to the industry's reported 2025 revenue and its 2026 run rates, which sit on the scoreboard below."),
        (f"The return to the economy. The same AI adds about {money(r30['productivity_gain_bn'])} a year of productivity gain by 2030 and {money(rN['productivity_gain_bn'])} by {yN} across the modelled regions "
        f"({money(cum['productivity_gain_bn'])} cumulative, {ratio_prod:.1f} times the capital spent" + (f"; the productivity gain alone repays the capex by {econ_payback}" if econ_payback else "") + "). "
        f"Counting the data-centre build itself as output, the GDP effect is {money(rN['gdp_gain_bn'])} a year by {yN}. Most of that gain goes to the firms that adopt AI and, through lower prices, to their customers, not to the companies that built the capacity."),
        ("How the two fit together. The investment is a bet that revenue will grow into the capacity: the capex path is front-loaded and the model's revenue follows adoption, so by construction the first years look like a bubble on a revenue-to-capex basis. "
        "Three things can close the gap: AI revenue far above what labour substitution alone justifies (consumer and advertising businesses, or prices held well above token cost); adoption faster than the model's central pace (the Seba presets are that case); "
        "or investors accepting that, as with railways, electricity and fibre, society earns most of the return and the builders earn a normal or poor one. The model cannot say which; it can say that the productivity return is real and large, that it lands with adopters, and that it arrives a decade after the capital."),
    ]
    chart_years = [y for y in (2025, 2026, 2028, 2030, 2035, 2040) if y in rows]
    items = []
    for y in chart_years:
        r = rows[y]
        items.append([f"{y} capex", r["capex_observed_bn"] if r.get("capex_observed_bn") else r["capex_model_bn"]])
        items.append([f"{y} AI producers' revenue", r["producer_revenue_bn"]])
        items.append([f"{y} productivity gain", r["productivity_gain_bn"]])
    return {"paragraphs": para, "rows": [rows[y] for y in chart_years], "cumulative": cum, "payback_year_revenue": payback, "payback_year_productivity": econ_payback,
            "chart": {"type": "bars", "title": "Per year, $bn: capital spent (observed where reported, else the model's path), AI producers' revenue, productivity gain", "items": items, "unit": "$bn"},
            "definition": "AI producers' revenue (called AI rents by value-chain stage in the technical documents) is what the makers of models, the cloud and data-centre operators, the chip makers and the integrators receive: employers' spending on AI at market prices, consumers' spending on AI subscriptions and services, and payments for AI-made content, split across the four stages and allocated to the regions whose companies hold the market share. It is gross revenue, not profit and not economic rent in the textbook sense."}


def _age_employment_shares(doc: dict[str, Any]) -> list[float]:
    ages = doc.get("cohorts", {}).get("age", [])
    if not ages:
        return []
    # employment share by band is not carried explicitly; approximate from the U.S. structure used in the engine (documented E values)
    return [0.13, 0.44, 0.20, 0.23][: len(ages)]


def named_futures(doc: dict[str, Any], region: str, futures_docs: dict[str, dict[str, Any]] | None) -> list[dict[str, Any]]:
    q = doc["meta"]["quarters"]; t40 = len(q) - 1; yr = q[t40][:4]
    blk = doc["series"].get(region) or doc["series"]["US"]
    base = _jobs_base(doc, region)
    torn = {r["param"]: r for r in doc.get("tornado", {}).get(HEAD, [])}
    torn_g = {r["param"]: r for r in doc.get("tornado", {}).get("gdp_pct_vs_baseline", [])}
    out = []
    m = torn.get("P.87")
    closure = _closure_medians(doc, region)
    if region != "US":
        # the cell medians are the U.S. headline's; scale them by the region's own median so the future's jobs count fits its ledger
        us50 = _p(doc["series"]["US"][HEAD], t40); r50 = _p(blk[HEAD], t40)
        if us50:
            closure = {c: {**v, "employment_pct": v["employment_pct"] * r50 / us50} for c, v in closure.items()}
    for key, name, words in (("demand", "Gains spent back (demand closure)", "households spend the productivity gains and firms hire against that demand; the model's default closure"),
                             ("no_demand_feedback", "Gains not spent back (no demand feedback)", "the spending feedback is switched off, so only cheaper output and new tasks offset the displacement")):
        c = closure.get(key)
        if c:
            out.append({"name": name, "employment_pct": c["employment_pct"], "gdp_pct": c.get("gdp_pct"), "jobs": round(-c["employment_pct"] / 100 * base), "source": f"structural ensemble: median of the {c['cells']} cells with this closure", "cells": c["cells"],
                        "description": f"{words.capitalize()}. Employment in {yr} is {c['employment_pct']:+.0f}% versus no AI (about {_millions(-c['employment_pct']/100*base)} {'fewer' if c['employment_pct'] < 0 else 'more'} jobs)."})
    if m and not closure:
        lo_e = m["effect_at_low"]; gm = torn_g.get("P.87", {})
        out.append({"name": "Gains pocketed", "employment_pct": lo_e, "gdp_pct": gm.get("effect_at_low"), "jobs": round(-lo_e / 100 * base), "source": "sensitivity: demand multiplier at the bottom of its range",
                    "description": f"If the gains are saved or paid out as rents, employment is {lo_e:+.0f}% (about {_millions(-lo_e/100*base)} fewer jobs)."})
    if not out:
        out.append({"name": "Central", "employment_pct": _p(blk[HEAD], t40), "gdp_pct": _p(blk["gdp_pct_vs_baseline"], t40), "jobs": round(-_p(blk[HEAD], t40) / 100 * base), "source": "median", "description": ""})
    for sid, fd in (futures_docs or {}).items():
        fb = fd["series"].get(region) or fd["series"]["US"]; fq = fd["meta"]["quarters"]; ft = len(fq) - 1
        e = _p(fb[HEAD], ft, "central"); g = _p(fb["gdp_pct_vs_baseline"], ft, "central"); emb = _p(fb.get("embodied_displacement_share", {}), ft, "central")
        rt = next((a for a in fd.get("applications", []) if a["app_id"] == "robotaxi"), None)
        gate = (rt["by_region"].get(region) or rt["by_region"].get("US", {})).get("first_quarter", {}).get("displacement_10pct") if rt else None
        out.append({"name": fd["meta"].get("scenario_name", sid), "scenario_id": sid, "employment_pct": e, "gdp_pct": g, "jobs": round(-e / 100 * base), "source": "scenario run",
                    "description": f"With {fd['meta'].get('scenario_name', sid).replace('Preset: ', '')} assumptions, employment in {yr} is {e:+.0f}% and robots and vehicles do {emb:.0f}% of task-hours"
                                   + (f"; robotaxis pass 10% of driver work in {gate[:4]}" if gate else "") + "."})
    return out


def _closure_medians(doc: dict[str, Any], region: str) -> dict[str, dict[str, float]]:
    """Median 2040 employment (and GDP) across the structural cells of each macro closure (the sixth cell axis)."""
    st = doc.get("structural") or {}
    emp = (st.get(HEAD) or {}).get("by_cell") or {}; gdp = (st.get("gdp_pct_vs_baseline") or {}).get("by_cell") or {}
    out: dict[str, dict[str, float]] = {}
    for key in ("demand", "no_demand_feedback"):
        es = [v["p50"][-1] for c, v in emp.items() if c.split("|")[-1] == key and v.get("p50")]
        gs = [v["p50"][-1] for c, v in gdp.items() if c.split("|")[-1] == key and v.get("p50")]
        if es:
            out[key] = {"employment_pct": float(np.median(es)), "gdp_pct": float(np.median(gs)) if gs else None, "cells": len(es)}
    return out


def structural_spread(doc: dict[str, Any], metric: str = HEAD) -> dict[str, Any] | None:
    """Range of the cell medians at the horizon: the disagreement between the model's mechanism cells, separate from the parameter draws."""
    by = ((doc.get("structural") or {}).get(metric) or {}).get("by_cell") or {}
    vals = [v["p50"][-1] for v in by.values() if v.get("p50")]
    if not vals:
        return None
    return {"min": float(min(vals)), "max": float(max(vals)), "cells": len(vals), "agree_on_sign": (min(vals) > 0) == (max(vals) > 0)}


def policy_runs(doc: dict[str, Any], policy_docs: dict[str, dict[str, Any]], region: str) -> list[dict[str, Any]]:
    q = doc["meta"]["quarters"]; t40 = len(q) - 1
    blk = doc["series"].get(region) or doc["series"]["US"]; base = _jobs_base(doc, region)
    e0 = _p(blk[HEAD], t40, "central"); u0 = _p(blk["unemployed_stock"], t40, "central"); rw0 = _p(blk["real_wage_pct_vs_baseline"], t40, "central")
    out = []
    for sid, pd in policy_docs.items():
        pb = pd["series"].get(region) or pd["series"]["US"]; pq = pd["meta"]["quarters"]; pt = len(pq) - 1
        e1 = _p(pb[HEAD], pt, "central"); u1 = _p(pb["unemployed_stock"], pt, "central"); rw1 = _p(pb["real_wage_pct_vs_baseline"], pt, "central")
        cost = _p(pb.get("policy_cost_bn", {}), pt, "central"); tax = _p(pb.get("ai_tax_revenue_bn", {}), pt, "central"); fiscal = _p(pb.get("fiscal_balance_bn", {}), pt, "central")
        val = pd["meta"].get("validity", {})
        out.append({"scenario_id": sid, "name": pd["meta"].get("scenario_name", sid).replace("Policy: ", ""), "description": (pd["meta"].get("scenario_description") or ""),
                    "jobs_delta": round((e1 - e0) / 100 * base), "employment_delta_pp": round(e1 - e0, 2), "unemployed_delta": round(u1 - u0), "real_wage_delta_pp": round(rw1 - rw0, 2),
                    "cost_bn_per_year": round(cost, 1), "ai_tax_revenue_bn": round(tax, 1), "fiscal_balance_bn": round(fiscal, 1),
                    "validity_note": val.get("note", "") if val.get("fiscal_warning") else "",
                    "sentence": _policy_sentence(pd["meta"].get("scenario_name", sid), e1 - e0, base, u1 - u0, rw1 - rw0, cost, fiscal, val, POLICY_HOW.get(sid, ""))})
    return out


def _policy_sentence(name: str, de: float, base: float, du: float, drw: float, cost: float, fiscal: float, val: dict[str, Any], how: str = "") -> str:
    name = name.replace("Policy: ", "")
    parts = [f"{name}: "]
    if abs(de) >= 0.05:
        parts.append(f"{_millions(abs(de)/100*base)} {'more' if de > 0 else 'fewer'} jobs than the baseline by 2040")
    else:
        parts.append("no measurable change in total jobs")
    if abs(du) >= 5000:
        parts.append(f", {_millions(abs(du))} {'fewer' if du < 0 else 'more'} unemployed")
    if abs(drw) >= 0.3:
        parts.append(f", real pay per head {drw:+.1f} points")
    if cost > 0.5:
        parts.append(f"; costs about ${cost:.0f} billion a year" + (f", of which the deficit carries ${abs(fiscal):.0f} billion" if fiscal < -0.5 else ""))
    s = "".join(parts) + "."
    if how:
        s += " " + how.rstrip(".") + "."
    if val.get("fiscal_warning"):
        s += " A deficit this large is outside what the model can judge: it has no inflation or interest-rate response, so the jobs effect is overstated."
    return s


def _caveats(doc: dict[str, Any]) -> list[str]:
    flags = doc["meta"].get("data_flags", {})
    fixtures = [k for k, v in flags.items() if isinstance(v, str) and "FIXTURE" in v.upper()]
    out = [
        "This is a structured scenario model, not an estimated forecasting model: its ranges are ranges over its own assumptions and exclude model error.",
        "Every number is a difference from a world in which AI stopped improving in 2023, not a forecast of the level of jobs or output.",
        "The headline counts jobs as full-time equivalents and includes gig and freelance work.",
    ]
    if fixtures:
        out.append("Placeholder inputs, to be replaced with measured data: " + ", ".join(sorted(fixtures)) + ". Robot, content and trade parameters are the authors' estimates.")
    out.append("The occupation classifier works from task wording; a few occupations are placed oddly (electricians count as robot targets), which is visible in the occupation view.")
    v = doc["meta"].get("validity", {})
    if v.get("warning"):
        out.append(v.get("note") or "This run is outside the range in which the model's labour rules were checked.")
    return out


GLOSSARY = {
    "versus no AI": "compared with a world in which AI stopped improving in 2023; population and normal growth are the same in both",
    "range of the model's assumptions": "the middle 80% of the model's runs across its parameter draws and mechanism cells; one run in ten falls above it and one in ten below. It is not a forecast interval: it excludes model error, data error and events outside the model",
    "we would bet on it / leaning / a coin flip": "how sure the model is of the direction: sure across all its versions, mostly, or split",
    "AI income (AI producers' revenue)": "what the makers of models, the cloud and data-centre operators, the chip makers and the integrators receive; in the model this equals what employers and consumers spend on AI, split by stage and allocated to the regions whose companies hold the market share; gross revenue, not profit and not economic rent in the textbook sense",
    "jobs today": "employment in the modelled occupations plus self-employed and platform workers, in full-time equivalents, not the official headline count",
    "jobs ledger / people ledger": "positions that exist versus people whose job was affected; a person who finds other work takes a position someone else would have had, so the two do not add up to each other",
}


def glossary(numbers: dict[str, Any], rname: str) -> dict[str, str]:
    """The glossary with the region's own 2024 count in the 'jobs today' entry."""
    g = dict(GLOSSARY)
    today = numbers.get("jobs_today") or numbers.get("jobs_base")
    if today:
        g["jobs today"] = f"{GLOSSARY['jobs today']}; about {_millions(float(today))} in 2024 in {rname}"
    return g


# ---------------------------------------------------------------- personal outlook
def outlook(doc: dict[str, Any], occ_code: str | None, age_band: str | None, region: str = "US") -> dict[str, Any]:
    q = doc["meta"]["quarters"]; t40 = len(q) - 1; t30 = q.index("2030Q4") if "2030Q4" in q else t40; yr = q[t40][:4]
    st = story(doc, region)
    occs = doc.get("occupations", [])
    o = next((x for x in occs if x["occ_code"] == occ_code), None) if occ_code else None
    out: dict[str, Any] = {"region": region, "region_name": st["region_name"], "beats": [b for b in st["beats"] if b["id"] in ("jobs", "hiring", "pay")], "sureness_legend": SURENESS,
                           "note": "" if region == "US" else "Occupation and age figures are U.S. detail; the region's totals are in the beats above."}
    if o:
        e30 = _p(o["employment_pct_vs_baseline"], t30); e40 = _p(o["employment_pct_vs_baseline"], t40); lo = _p(o["employment_pct_vs_baseline"], t40, "p10"); hi = _p(o["employment_pct_vs_baseline"], t40, "p90")
        d_sw = _p(o["displacement"], t40, "central"); d_emb = _p(o.get("displacement_embodied", {}), t40, "central") if o.get("displacement_embodied", {}).get("central") else 0.0
        rw = _p(o["real_wage_pct_vs_baseline"], t40, "central")
        ranks = sorted(occs, key=lambda x: _p(x["employment_pct_vs_baseline"], t40))
        pos = next(i for i, x in enumerate(ranks) if x["occ_code"] == occ_code); pct_rank = 100 * pos / max(len(ranks) - 1, 1)
        same = [x for x in occs if x["major_group"] == o["major_group"] and x["occ_code"] != occ_code and x["emp0"] >= 50_000]
        growing = sorted(same, key=lambda x: -_p(x["employment_pct_vs_baseline"], t40))[:3]
        how = "mostly software doing parts of the job" if d_sw >= 2 * max(d_emb, 1e-9) else ("mostly machines and vehicles" if d_emb > d_sw else "a mix of software and machines")
        verdict = ("among the hardest hit" if pct_rank < 10 else "harder hit than most" if pct_rank < 30 else "about average" if pct_rank < 70 else "less affected than most" if pct_rank < 90 else "among the most protected")
        out["occupation"] = {"occ_code": occ_code, "title": o["title"], "employment_2024": o["emp0"], "employment_pct_2030": e30, "employment_pct_2040": e40, "range_2040": [lo, hi],
                             "task_hours_automated_2040": {"software": d_sw * 100, "machines": d_emb * 100}, "real_wage_pct_2040": rw, "rank_percentile": round(pct_rank),
                             "verdict": verdict, "how": how, "growing_nearby": [[x["title"], _p(x["employment_pct_vs_baseline"], t40)] for x in growing],
                             "sentence": (f"{o['title']}: {verdict}. About {abs(e40):.0f}% {'fewer' if e40 < 0 else 'more'} jobs than there would have been by {yr} "
                                          f"({abs(e30):.0f}% by 2030); likely between {lo:+.0f}% and {hi:+.0f}%. {how.capitalize()}: {100*(d_sw+d_emb):.0f}% of the work's task-hours are done by AI by {yr}. "
                                          f"Pay for those who stay is {rw:+.0f}% in real terms.")}
    if age_band and doc.get("cohorts", {}).get("age"):
        a = next((x for x in doc["cohorts"]["age"] if x["band"] == age_band), None)
        if a:
            share = _p(a["share_of_jobs_lost"], t40); own = _p(a["employment_pct_vs_baseline"], t40)
            out["age"] = {"band": age_band, "share_of_jobs_lost": share, "employment_pct_2040": own,
                          "sentence": (f"People {AGE_LABELS.get(age_band, age_band)} carry {100*share:.0f}% of the jobs that go missing by {yr}, about {abs(own):.1f}% of the group's jobs. "
                                       + ("Most of the loss is jobs never offered rather than jobs taken away, so the practical risk is at entry: first jobs, changing jobs, returning to work."
                                          if age_band == "16-24" else "Incumbents are mostly protected because employers cut through attrition rather than layoffs; the risk rises if you change occupations."))}
    return out


# ---------------------------------------------------------------- executive brief (markdown + html with inline SVG)
def _lede(st: dict[str, Any]) -> str:
    """The five-sentence summary at the top of the executive brief."""
    n = st["numbers"]; yr = st["horizon"][1][:4]
    without = n.get("jobs_2040_no_ai") or n["jobs_base"]
    who = "the young pay first" if st.get("region", "US") == "US" else "new entrants pay first"
    return (f"By {yr} there are about {_millions(n['jobs_gap'])} fewer jobs than there would have been, out of the {_millions(without)} there would have been in {yr}; most of them are jobs never created rather than jobs destroyed. "
            f"Most of that is hiring that never happens rather than layoffs (about one position in {max(round((n['unfilled'] + n['laid_off']) / max(n['laid_off'], 1)), 2)} removed is a layoff), so {who}. "
            f"Real pay rises about {n['real_wage_pct']['p50']:.0f}% and the economy is about {n['gdp_pct']:.0f}% larger, but workers' share of income falls {abs(n['wage_share_pp']):.1f} points. "
            f"Office work is reshaped now, robots come in the mid-2030s, AI-made content spreads category by category. "
            f"Whether jobs end up down {abs(n['employment_pct']['p10']):.0f}% or flat depends mostly on whether the gains are spent back into the economy.")


def executive_brief_md(st: dict[str, Any]) -> str:
    L = [f"# What AI does to work in {st.get('region_name') or st['region']}, in seven findings", "",
         f"Scenario: {st['scenario_name']}. Everything below is a difference from a world in which AI stopped improving in 2023. Run `{st['scenario_hash']}`.", ""]
    L.append("## In five sentences"); L.append("")
    L.append(_lede(st))
    L.append("")
    L.append("")
    for i, b in enumerate(st["beats"], 1):
        L.append(f"## {i}. {b['title']}"); L.append(""); L.append(b["sentence"]); L.append("")
        if b.get("extra_chart"):
            L.append(f"*{b['extra_chart'].get('title', '')}*"); L.append("")
            for label, v in b["extra_chart"]["items"]:
                L.append(f"- {label.strip()}: {float(v):,.0f}")
            L.append("")
        L.append(f"*Range of the model's assumptions:* {b['range']}  ")
        L.append(f"*How sure:* {b['sureness']['label']}.  ")
        L.append(f"*What changes it:* {b['what_changes_it']}"); L.append("")
    L.append("## What could be done"); L.append("")
    if st["policies"]:
        for pr in st["policies"]:
            L.append(f"- {pr['sentence']}")
    else:
        L.append("- Policy runs are not available for this document; the technical brief lists the levers.")
    L.append("")
    if st.get("investment"):
        L.append("## Investment versus returns"); L.append("")
        for para in st["investment"]["paragraphs"]:
            L.append(para); L.append("")
        L.append("| Year | Capex ($bn) | AI producers' revenue ($bn) | Productivity gain ($bn) | GDP effect ($bn) |"); L.append("|---|---|---|---|---|")
        for r in st["investment"]["rows"]:
            L.append(f"| {r['year']} | {r['capex_observed_bn'] if r.get('capex_observed_bn') else r['capex_model_bn']:,.0f}{' (reported)' if r.get('capex_observed_bn') else ''} | {r['producer_revenue_bn']:,.0f} | {r['productivity_gain_bn']:,.0f} | {r['gdp_gain_bn']:,.0f} |")
        L.append(""); L.append(f"*{st['investment']['definition']}*"); L.append("")
    if st.get("forecasts"):
        L.append("## How the model compares with named forecasts"); L.append("")
        L.append("| Who | Claim | Model (this run) | Verdict |"); L.append("|---|---|---|---|")
        for f in st["forecasts"]:
            mc = f.get("model_central")
            L.append(f"| {f['short']}{' (calibration target)' if f.get('role') == 'target' else ''} | {f['claimed']} {f['unit']} by {f['year']} ({f['region']}) | {(f'{mc:.1f}') if mc is not None else 'n/a'} | {f['verdict']}{' (nearest model quantity)' if f.get('proxy') else ''} |")
        L.append(""); L.append("A claim marked *nearest model quantity* is compared with the closest thing the model tracks, named in the technical brief; the verdict is about direction and size, not a one-to-one test.")
        L.append("")
    if st.get("backtest"):
        L.append("## How the model has done so far (2024 to mid-2026)"); L.append("")
        for x in st["backtest"]["sentences"]:
            L.append(f"- {x}")
        L.append(""); L.append("| Series | Quarter | Observed | Model | Error |"); L.append("|---|---|---|---|---|")
        for r in st["backtest"]["rows"]:
            if r.get("model_central") is not None:
                L.append(f"| {r['label']} | {r['quarter']} | {r['value']:,.1f} | {r['model_central']:,.1f} | {r['error_pct']:+.0f}% |")
        L.append("")
    L.append("## Read this with care"); L.append("")
    for c in st["caveats"]:
        L.append(f"- {c}")
    L.append(""); L.append("## Words used"); L.append("")
    for k, v in st["glossary"].items():
        L.append(f"- **{k}**: {v}")
    L.append("")
    return "\n".join(L)


def _svg_fan(chart: dict[str, Any], w: int = 640, h: int = 220) -> str:
    q = chart["quarters"]; n = len(q); pad = 36
    series = chart["series"]
    allv = [v for s in series.values() for k in s for v in s[k]]
    lo, hi = min(allv + [0]), max(allv + [0]); span = (hi - lo) or 1.0
    x = lambda i: pad + (w - 2 * pad) * i / max(n - 1, 1)
    y = lambda v: h - pad - (h - 2 * pad) * (v - lo) / span
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Employment and GDP versus no AI, with likely ranges">']
    parts.append(f'<line x1="{pad}" y1="{y(0):.1f}" x2="{w-pad}" y2="{y(0):.1f}" stroke="currentColor" stroke-opacity="0.35"/>')
    colors = {"employment": "#2f6db3", "gdp": "#c46b1e"}
    for name, s in series.items():
        c = colors.get(name, "#888")
        if "p10" in s and "p90" in s:
            pts = " ".join(f"{x(i):.1f},{y(s['p10'][i]):.1f}" for i in range(n)) + " " + " ".join(f"{x(i):.1f},{y(s['p90'][i]):.1f}" for i in range(n - 1, -1, -1))
            parts.append(f'<polygon points="{pts}" fill="{c}" fill-opacity="0.15"/>')
        pts = " ".join(f"{x(i):.1f},{y(s['p50'][i]):.1f}" for i in range(n))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2"/>')
        parts.append(f'<text x="{w-pad-4}" y="{y(s["p50"][-1])-6:.1f}" font-size="11" text-anchor="end" fill="{c}">{ {"employment": "jobs", "gdp": "GDP"}.get(name, name)}</text>')
    for i in range(0, n, 16):
        parts.append(f'<text x="{x(i):.1f}" y="{h-8}" font-size="11" text-anchor="middle" fill="currentColor">{q[i][:4]}</text>')
    for v in (lo, 0, hi):
        parts.append(f'<text x="{pad-6}" y="{y(v)+4:.1f}" font-size="11" text-anchor="end" fill="currentColor">{v:+.0f}%</text>')
    parts.append("</svg>")
    return "".join(parts)


def _svg_bars(chart: dict[str, Any], w: int = 640, h: int | None = None) -> str:
    items = chart["items"]; unit = chart.get("unit", ""); ref = {k: v for k, v in chart.get("reference", [])}
    h = h or (26 * len(items) + 30); label_w = 220
    vals = [float(v) for _, v in items] + list(ref.values()); m = max(abs(v) for v in vals) or 1.0
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img">']
    for i, (label, v) in enumerate(items):
        yy = 8 + i * 26; bw = (w - label_w - 150) * abs(float(v)) / m
        parts.append(f'<text x="{label_w-8}" y="{yy+14}" font-size="12" text-anchor="end" fill="currentColor">{html.escape(str(label))}</text>')
        parts.append(f'<rect x="{label_w}" y="{yy+2}" width="{bw:.1f}" height="16" fill="{"#2f6db3" if float(v) >= 0 else "#b3402f"}" rx="2"/>')
        if label in ref:
            rw_ = (w - label_w - 150) * abs(ref[label]) / m
            parts.append(f'<rect x="{label_w}" y="{yy+19}" width="{rw_:.1f}" height="3" fill="currentColor" fill-opacity="0.4"/>')
        txt = f"{float(v):,.0f}" if abs(float(v)) >= 1000 else f"{float(v):+.1f}{unit if unit.startswith('%') else ''}"
        parts.append(f'<text x="{label_w+bw+6:.1f}" y="{yy+14}" font-size="12" fill="currentColor">{txt}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _svg_timeline(chart: dict[str, Any], w: int = 640) -> str:
    items = sorted(chart["items"], key=lambda it: it["first_year"]); start, end = chart["start"], chart["end"]; label_w = 230
    h = 22 * len(items) + 30
    x = lambda yr_: label_w + (w - label_w - 30) * (int(yr_) - start) / max(end - start, 1)
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="When each application passes 1% of its target work">']
    for yr_ in range(start, end + 1, 4):
        parts.append(f'<line x1="{x(yr_):.1f}" y1="6" x2="{x(yr_):.1f}" y2="{h-16}" stroke="currentColor" stroke-opacity="0.15"/>')
        parts.append(f'<text x="{x(yr_):.1f}" y="{h-4}" font-size="11" text-anchor="middle" fill="currentColor">{yr_}</text>')
    col = {"embodied": "#7a4fb3", "output": "#2f9e8f", "software": "#2f6db3", "traded": "#c46b1e"}
    for i, it in enumerate(items):
        yy = 8 + i * 22
        parts.append(f'<text x="{label_w-8}" y="{yy+12}" font-size="12" text-anchor="end" fill="currentColor">{html.escape(it["app"])}</text>')
        parts.append(f'<circle cx="{x(it["first_year"]):.1f}" cy="{yy+8}" r="6" fill="{col.get(it["family"], "#888")}"/>')
    parts.append("</svg>")
    return "".join(parts)


def _svg_regions(chart: dict[str, Any], w: int = 640) -> str:
    items = chart["items"]; h = 24 * len(items) + 30; label_w = 60
    m_e = max(abs(r[1]) for r in items) or 1.0; m_r = max(abs(r[3]) for r in items) or 1.0
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Jobs and AI income by region">']
    parts.append(f'<text x="{label_w+10}" y="12" font-size="11" fill="currentColor">Jobs versus no AI, 2040</text><text x="{w/2+20}" y="12" font-size="11" fill="currentColor">AI income received, $bn/yr</text>')
    for i, (x_, e, g, r) in enumerate(items):
        yy = 20 + i * 24
        parts.append(f'<text x="{label_w-6}" y="{yy+13}" font-size="12" text-anchor="end" fill="currentColor">{x_}</text>')
        bw = (w / 2 - label_w - 60) * abs(e) / m_e
        parts.append(f'<rect x="{label_w}" y="{yy+3}" width="{bw:.1f}" height="14" fill="{"#2f6db3" if e >= 0 else "#b3402f"}" rx="2"/><text x="{label_w+bw+4:.1f}" y="{yy+14}" font-size="11" fill="currentColor">{e:+.1f}%</text>')
        rw_ = (w / 2 - 80) * abs(r) / m_r
        parts.append(f'<rect x="{w/2+20}" y="{yy+3}" width="{rw_:.1f}" height="14" fill="#7a4fb3" rx="2"/><text x="{w/2+24+rw_:.1f}" y="{yy+14}" font-size="11" fill="currentColor">{r:.0f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def chart_svg(chart: dict[str, Any]) -> str:
    kind = chart.get("type")
    try:
        if kind == "fan":
            return _svg_fan(chart)
        if kind == "bars":
            return _svg_bars(chart)
        if kind == "timeline":
            return _svg_timeline(chart) if chart.get("items") else ""
        if kind == "regions":
            return _svg_regions(chart)
    except (KeyError, ValueError, ZeroDivisionError):
        return ""
    return ""


_CSS = """
:root{color-scheme:light dark}body{font:16px/1.55 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:820px;margin:32px auto;padding:0 20px;color:#1c1c1c;background:#fff}
h1{font-size:28px;line-height:1.2;margin:0 0 6px}h2{font-size:19px;margin:30px 0 8px}.lede{font-size:17px;border-left:4px solid #2f6db3;padding:8px 14px;background:#f4f7fb;border-radius:4px}
.beat{margin:18px 0 26px}.meta{display:flex;gap:18px;flex-wrap:wrap;font-size:13.5px;color:#555;margin-top:6px}.dots{letter-spacing:2px}
.futures{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.card{border:1px solid #ddd;border-radius:8px;padding:10px 12px}.card b{display:block;margin-bottom:4px}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{border:1px solid #e3e3e3;padding:5px 8px;text-align:left;vertical-align:top}th{background:#f5f5f5}
.caveat{background:#fff7e6;border:1px solid #f0d9a8;border-radius:6px;padding:10px 14px;font-size:14px}code{font:12.5px ui-monospace,Menlo,monospace;background:#f3f3f3;padding:1px 4px;border-radius:3px}
svg text{font-family:inherit}@media (prefers-color-scheme: dark){body{background:#151618;color:#e6e6e6}.lede{background:#1c2430}.card{border-color:#333}th{background:#222}td,th{border-color:#333}.caveat{background:#2a2410;border-color:#5a4a1a}.meta{color:#aaa}code{background:#202225}}
@media print{body{margin:0;max-width:none}.beat{break-inside:avoid}}
"""


def executive_brief_html(st: dict[str, Any]) -> str:
    e = html.escape
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{e(st['scenario_name'] or 'Scenario')} — what AI does to work</title><style>{_CSS}</style></head><body>"]
    parts.append(f"<h1>What AI does to work in {e(st.get('region_name') or st['region'])}, in seven findings</h1><p style='color:#666;font-size:14px'>Scenario: {e(st['scenario_name'] or '')}. Everything below is a difference from a world in which AI stopped improving in 2023.</p>")
    parts.append("<div class='lede'>" + e(_lede(st)) + "</div>")
    for i, b in enumerate(st["beats"], 1):
        parts.append(f"<div class='beat'><h2>{i}. {e(b['title'])}</h2><p>{e(b['sentence'])}</p>")
        if b["id"] == "futures":
            parts.append("<div class='futures'>" + "".join(f"<div class='card'><b>{e(f['name'])}</b>{e(f['description'])}</div>" for f in b["chart"]["items"]) + "</div>")
        else:
            parts.append(chart_svg(b["chart"]))
        if b.get("extra_chart"):
            parts.append(f"<p style='font-size:13.5px;color:#666;margin:10px 0 2px'>{e(b['extra_chart'].get('title', ''))}</p>" + chart_svg(b["extra_chart"]))
        parts.append(f"<div class='meta'><span><b>Range of the model's assumptions:</b> {e(b['range'])}</span><span><b>How sure:</b> <span class='dots'>{'●' * b['sureness']['dots']}{'○' * (3 - b['sureness']['dots'])}</span> {e(b['sureness']['label'])}</span><span><b>What changes it:</b> {e(b['what_changes_it'])}</span></div></div>")
    parts.append("<h2>What could be done</h2>")
    if st["policies"]:
        parts.append("<ul>" + "".join(f"<li>{e(p['sentence'])}</li>" for p in st["policies"]) + "</ul>")
    else:
        parts.append("<p>Policy runs are not available for this document.</p>")
    if st.get("investment"):
        inv = st["investment"]
        parts.append("<h2>Investment versus returns</h2>" + "".join(f"<p>{e(x)}</p>" for x in inv["paragraphs"]) + chart_svg(inv["chart"]))
        parts.append("<table><tr><th>Year</th><th>Capex ($bn)</th><th>AI producers' revenue ($bn)</th><th>Productivity gain ($bn)</th><th>GDP effect ($bn)</th></tr>"
                     + "".join(f"<tr><td>{r['year']}</td><td>{(r['capex_observed_bn'] if r.get('capex_observed_bn') else r['capex_model_bn']):,.0f}{' (reported)' if r.get('capex_observed_bn') else ''}</td><td>{r['producer_revenue_bn']:,.0f}</td><td>{r['productivity_gain_bn']:,.0f}</td><td>{r['gdp_gain_bn']:,.0f}</td></tr>" for r in inv["rows"])
                     + f"</table><p style='font-size:13px;color:#666'>{e(inv['definition'])}</p>")
    if st.get("forecasts"):
        parts.append("<h2>How the model compares with named forecasts</h2><table><tr><th>Who</th><th>Claim</th><th>Model (this run)</th><th>Verdict</th></tr>")
        for f in st["forecasts"]:
            mc = f.get("model_central")
            parts.append(f"<tr><td>{e(f['short'])}{' <i>(calibration target)</i>' if f.get('role') == 'target' else ''}</td><td>{e(str(f['claimed']))} {e(f['unit'])} by {f['year']} ({e(f['region'])})</td><td>{(f'{mc:.1f}') if mc is not None else 'n/a'}</td><td>{e(f['verdict'])}{' (nearest model quantity)' if f.get('proxy') else ''}</td></tr>")
        parts.append("</table><p style='font-size:13px;color:#666'>A claim marked <i>nearest model quantity</i> is compared with the closest thing the model tracks; the verdict is about direction and size, not a one-to-one test.</p>")
    if st.get("backtest"):
        parts.append("<h2>How the model has done so far (2024 to mid-2026)</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in st["backtest"]["sentences"]) + "</ul>")
        parts.append("<table><tr><th>Series</th><th>Quarter</th><th>Observed</th><th>Model</th><th>Error</th></tr>"
                     + "".join(f"<tr><td>{e(r['label'])}</td><td>{r['quarter']}</td><td>{r['value']:,.1f}</td><td>{r['model_central']:,.1f}</td><td>{r['error_pct']:+.0f}%</td></tr>" for r in st["backtest"]["rows"] if r.get("model_central") is not None)
                     + "</table>")
    parts.append("<h2>Read this with care</h2><div class='caveat'><ul>" + "".join(f"<li>{e(c)}</li>" for c in st["caveats"]) + "</ul></div>")
    parts.append("<h2>Words used</h2><ul>" + "".join(f"<li><b>{e(k)}</b>: {e(v)}</li>" for k, v in st["glossary"].items()) + "</ul>")
    parts.append(f"<p style='color:#888;font-size:12px'>Run <code>{e(st['scenario_hash'])}</code>. Technical brief and methodology in the repository.</p></body></html>")
    return "".join(parts)


def dumps(obj: Any) -> str:
    return json.dumps(obj, default=lambda o: float(o) if isinstance(o, (int, float)) or hasattr(o, "item") else str(o))


def _isfinite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)

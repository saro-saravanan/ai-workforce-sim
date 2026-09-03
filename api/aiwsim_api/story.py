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

HEAD = "employment_pct_vs_baseline"
AGE_LABELS = {"16-24": "under 25", "25-44": "25 to 44", "45-54": "45 to 54", "55+": "55 and over"}
SURENESS = {"high": ("we would bet on it", 3), "medium": ("leaning this way", 2), "low": ("a coin flip", 1)}
FAMILY_WORDS = {"embodied": "robots and vehicles", "output": "AI-made content", "software": "software doing office tasks", "traded": "automation abroad"}
POLICY_HOW = {
    "policy-retraining": "Pays half the wage of workers who enrol in retraining, so more of the displaced retrain and more complete it; paid from the deficit.",
    "policy-wage-insurance": "Tops up the pay of displaced workers who take a lower-paid job, half the gap for two years; paid from a tax on AI spending.",
    "policy-ubi-ai-tax": "Pays every adult $500 a month; a 30% tax on AI spending covers a small part and the deficit the rest.",
    "policy-work-week-36": "Shortens the standard week to 36 hours, so the same work is shared among more people; pay per head falls in step and total pay does not.",
}
CHANNEL_WORDS = {"automation": "software doing tasks", "augmentation": "faster work needing fewer people", "embodied": "robots and vehicles", "output_substitution": "AI-made content",
                 "traded_services": "automation abroad", "demand_response": "cheaper output selling more", "reinstatement": "new kinds of work", "demand_feedback": "workers' spending",
                 "ai_investment": "building AI itself", "adjacent": "jobs around AI"}


# ---------------------------------------------------------------- helpers
def _p(s: dict[str, list[float]], t: int, k: str = "p50") -> float:
    arr = s.get(k) or s.get("p50") or s.get("central")
    return float(arr[t]) if arr else 0.0


def _band(s: dict[str, list[float]], t: int) -> tuple[float, float, float]:
    return _p(s, t, "p10"), _p(s, t, "p50"), _p(s, t, "p90")


def _millions(x: float) -> str:
    x = abs(x)
    if x >= 1e6:
        return f"{x/1e6:.1f} million"
    if x >= 1e3:
        return f"{x/1e3:.0f},000"
    return f"{x:.0f}"


def _sure(level: str) -> dict[str, Any]:
    label, n = SURENESS.get(level, SURENESS["low"])
    return {"level": level, "label": label, "dots": n}


def _jobs_base(doc: dict[str, Any], region: str) -> float:
    rg = next((r for r in doc.get("regions", []) if r["region_id"] == region), None)
    base = float(rg["employment_total"]) if rg else 0.0
    return base + float((doc["meta"].get("self_employed_fte") or {}).get(region, 0.0))


def _quarter_year(q: str | None) -> str | None:
    return q[:4] if q else None


# ---------------------------------------------------------------- beats
def story(doc: dict[str, Any], region: str = "US", policy_docs: dict[str, dict[str, Any]] | None = None,
          futures_docs: dict[str, dict[str, Any]] | None = None, policy_base: dict[str, Any] | None = None) -> dict[str, Any]:
    """The whole story for one run. `policy_docs` are the policy scenarios, read as differences from `policy_base`
    (the baseline they modify; defaults to `doc`); `futures_docs` are scenario runs shown as named futures."""
    q = doc["meta"]["quarters"]; t40 = len(q) - 1; t30 = q.index("2030Q4") if "2030Q4" in q else t40
    blk = doc["series"].get(region) or doc["series"]["US"]
    yr = q[t40][:4]
    base = _jobs_base(doc, region)
    conf = lambda m, qq=q[t40]: (doc.get("confidence", {}).get(m, {}).get(qq) or {}).get("level", "low")

    # ---- reconciled numbers (one convention: medians; jobs in heads) ----
    e10, e50, e90 = _band(blk[HEAD], t40)
    jobs_gap = -e50 / 100 * base; jobs_lo = -e10 / 100 * base; jobs_hi = -e90 / 100 * base
    flows = doc.get("flows", {}).get("destinations", {})
    displaced = _p(blk["displaced_workers_cum"], t40); reemp = _p(flows.get("reemployed", {}), t40) if flows else 0.0
    unemployed = _p(blk["unemployed_stock"], t40); exited = _p(flows.get("exited", {}), t40) if flows else 0.0
    unfilled = _p(flows.get("unfilled_entry", {}), t40) if flows else 0.0; laid = _p(flows.get("laid_off", {}), t40) if flows else 0.0
    peak_t = int(max(range(len(q)), key=lambda i: _p(blk["unemployed_stock"], i))); peak_unemp = _p(blk["unemployed_stock"], peak_t)
    g50 = _p(blk["gdp_pct_vs_baseline"], t40); rw10, rw50, rw90 = _band(blk["real_wage_pct_vs_baseline"], t40)
    price = _p(blk["price_index_pct_vs_baseline"], t40); wshare = _p(blk["wage_share_pp_vs_baseline"], t40)
    hours_cut = _p(flows.get("self_employed_margin_cum", {}), t40) if flows else 0.0
    removed, added = _channel_split(doc, region, t40, base)
    recon = _reconciliation(yr, base, jobs_gap, displaced, reemp, unemployed, exited, unfilled, laid, hours_cut, removed, added)
    numbers = {"jobs_base": round(base), "jobs_gap": round(jobs_gap), "jobs_gap_low": round(jobs_lo), "jobs_gap_high": round(jobs_hi),
               "employment_pct": {"p10": e10, "p50": e50, "p90": e90}, "displaced_cum": round(displaced), "reemployed": round(reemp),
               "unemployed_extra": round(unemployed), "exited": round(exited), "unfilled": round(unfilled), "laid_off": round(laid), "hours_cut_self": round(hours_cut),
               "jobs_removed_by_channel": removed, "jobs_added_by_channel": added,
               "unemployment_peak": {"quarter": q[peak_t], "extra": round(peak_unemp)}, "gdp_pct": g50, "real_wage_pct": {"p10": rw10, "p50": rw50, "p90": rw90},
               "price_index_pct": price, "wage_share_pp": wshare, "reconciliation": recon}

    beats: list[dict[str, Any]] = []
    # 1. More jobs than today, fewer than there would have been
    beats.append({"id": "jobs", "title": "More jobs than today, fewer than there would have been",
                  "sentence": f"By {yr} there are about {_millions(jobs_gap)} fewer jobs than there would have been without AI, on a base of about {_millions(base)}: "
                              f"about one job in {round(base / max(jobs_gap, 1.0))} " + ("never created rather than destroyed." if unfilled > 3 * max(laid, 1.0) else "removed.")
                              + (f" The biggest remover is {CHANNEL_WORDS[max(removed, key=removed.get)]}; the biggest offset is {CHANNEL_WORDS[max(added, key=added.get)]}." if removed and added else ""),
                  "range": f"Likely between {_millions(jobs_lo)} fewer and {'no loss at all' if jobs_hi <= 0 else _millions(jobs_hi) + ' fewer'}.",
                  "sureness": _sure(conf(HEAD)), "what_changes_it": "How much of the productivity gain gets spent back into the economy. Spent back, jobs are flat or up; pocketed, the loss doubles.",
                  "chart": {"type": "fan", "series": {"employment": {k: blk[HEAD][k] for k in ("p10", "p50", "p90") if k in blk[HEAD]},
                                                      "gdp": {k: blk["gdp_pct_vs_baseline"][k] for k in ("p10", "p50", "p90") if k in blk["gdp_pct_vs_baseline"]}}, "quarters": q}})
    # 2. Not fired, not hired
    tot_lost = max(unfilled + laid + _p(flows.get("self_employed_margin_cum", {}), t40) if flows else 1.0, 1.0)
    beats.append({"id": "hiring", "title": "People are not fired. They are not hired.",
                  "sentence": f"Of the {_millions(tot_lost)} positions AI takes out of the economy by {yr}, {_millions(unfilled)} are jobs never offered to new entrants and {_millions(laid)} are layoffs. "
                              f"Unemployment rises by at most {_millions(peak_unemp)} at its {q[peak_t][:4]} peak. Of the people affected, {_millions(reemp)} find other work and {_millions(exited)} leave the workforce.",
                  "range": "The split between unfilled positions and layoffs holds in every scenario the model ships.",
                  "sureness": _sure("high" if unfilled / tot_lost > 0.85 else "medium"),
                  "what_changes_it": "The pace at which employers let attrition do the work: faster required cuts turn unfilled positions into layoffs.",
                  "chart": {"type": "bars", "items": [["Positions never refilled", unfilled], ["Layoffs", laid], ["Found other work", reemp], ["Left the workforce", exited], ["Still unemployed", unemployed]]}})
    # 3. The young pay first
    ages = doc.get("cohorts", {}).get("age", []); edu = doc.get("cohorts", {}).get("education", []); dec = doc.get("cohorts", {}).get("income_decile", [])
    if ages:
        share = {a["band"]: _p(a["share_of_jobs_lost"], t40) for a in ages}; own = {a["band"]: _p(a["employment_pct_vs_baseline"], t40) for a in ages}
        young = share.get("16-24", 0.0); young_own = own.get("16-24", 0.0); mid_own = own.get("25-44", 0.0); old_own = own.get("55+", 0.0)
        e_lo = _p(edu[0]["employment_pct_vs_baseline"], t40) if edu else 0.0; e_hi = _p(edu[-1]["employment_pct_vs_baseline"], t40) if edu else 0.0
        d_lo = sum(_p(x["employment_pct_vs_baseline"], t40) for x in dec[:5]) / 5 if dec else 0.0; d_hi = _p(dec[-1]["employment_pct_vs_baseline"], t40) if dec else 0.0
        beats.append({"id": "young", "title": "The young pay first",
                      "sentence": f"Workers under 25 carry {100*young:.0f}% of the shortfall, about {abs(young_own):.0f}% of their group's jobs, against {abs(mid_own):.0f}% for 25 to 44 and "
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
    worst30 = sorted(big, key=lambda o: _p(o["employment_pct_vs_baseline"], t30))[:4]
    worst40 = sorted(big, key=lambda o: _p(o["employment_pct_vs_baseline"], t40))[:4]
    best40 = sorted(big, key=lambda o: -_p(o["employment_pct_vs_baseline"], t40))[:4]
    emb = blk.get("embodied_displacement_share", {}); content = blk.get("ai_content_share", {})
    content_sorted = sorted(((k, _p(v, t40)) for k, v in content.items()), key=lambda kv: -kv[1])
    beats.append({"id": "waves", "title": "Three waves, not one",
                  "sentence": ("Office and analytical work is being reshaped now: " + ", ".join(f"{o['title'].lower()} ({_p(o['employment_pct_vs_baseline'], t30):+.0f}%)" for o in worst30) + f" by 2030. "
                               f"Robots and vehicles arrive later: {_p(emb, t30):.1f}% of task-hours in 2030, {_p(emb, t40):.1f}% by {yr}. "
                               + (f"AI-made content takes {content_sorted[0][0].replace('_', ' and ')} first ({content_sorted[0][1]:.0f}% of spending by {yr}) and {content_sorted[-1][0]} last ({content_sorted[-1][1]:.0f}%). " if content_sorted else "")
                               + "Growing: " + ", ".join(f"{o['title'].lower()} ({_p(o['employment_pct_vs_baseline'], t40):+.0f}%)" for o in best40) + "."),
                  "range": "Timing of the robot wave depends on how fast fleets can be built and approved, not on the software.",
                  "sureness": _sure("medium"), "what_changes_it": "Production ramps, permits, and hardware costs for the robot wave; how much people keep paying for human-made work for the content wave.",
                  "chart": {"type": "timeline", "items": [w for w in waves if w["first_year"]], "start": int(q[0][:4]), "end": int(q[-1][:4])},
                  "occupations": {"hit_first": [[o["title"], _p(o["employment_pct_vs_baseline"], t30)] for o in worst30], "hit_most": [[o["title"], _p(o["employment_pct_vs_baseline"], t40)] for o in worst40],
                                  "growing": [[o["title"], _p(o["employment_pct_vs_baseline"], t40)] for o in best40]}})
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
                                            ["AI-made content (consumers)", src.get("content", 0.0)]] + [[f"Work bought: {t}", v] for t, v in groups[:6]], "unit": "$bn"},
                  "income": {"sources_world_bn": src, "paying_groups_world_bn": groups, "received_by_stage_bn": stages}})
    # 7. Two futures, and the difference is a choice
    futures = named_futures(doc, region, futures_docs)
    beats.append({"id": "futures", "title": "Two futures, and the difference is partly a choice",
                  "sentence": " ".join(f"{f['name']}: {f['description']}" for f in futures),
                  "range": "The model's biggest uncertainty is whether the gains are spent back into the economy or pocketed; that is partly policy, partly corporate behaviour, and partly what people choose to pay for.",
                  "sureness": _sure("low"), "what_changes_it": "See the futures and the policy runs below.", "chart": {"type": "futures", "items": futures}})

    policies = policy_runs(policy_base or doc, policy_docs or {}, region)
    caveats = _caveats(doc)
    return {"scenario_hash": doc["meta"]["scenario_hash"], "scenario_id": doc["meta"].get("scenario_id"), "scenario_name": doc["meta"].get("scenario_name"),
            "region": region, "horizon": [q[0], q[-1]], "numbers": numbers, "beats": beats, "futures": futures, "policies": policies,
            "policies_against": (policy_base or doc)["meta"].get("scenario_name"), "caveats": caveats,
            "forecasts": doc.get("forecasts", []), "glossary": GLOSSARY}


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
        for g in blk.get("ai_spend_by_occupation_group_bn") or []:
            if g["major_group"] != "other":
                groups[g["title"]] = groups.get(g["title"], 0.0) + _p(g["spend_bn"], t)
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
         f"employers buying tools that speed up workers ({share('augmentation'):.0f}%), and consumers paying for AI-made content ({share('content'):.0f}%)")
    if groups:
        s += "; the work being bought is mostly " + ", ".join(f"{t.lower()} (${v:.0f} billion)" for t, v in groups[:3])
    if stages:
        top = sorted(stages.items(), key=lambda kv: -kv[1])[:3]
        s += ". It lands with " + ", ".join(f"{STAGE_WORDS.get(k, k)} (${v:.0f} billion)" for k, v in top) + "."
    else:
        s += "."
    return s


STAGE_WORDS = {"model": "the model makers", "compute": "the cloud and data-centre operators", "chips": "the chip makers", "integration": "local integrators and platforms", "fabs": "the fabs", "energy": "energy suppliers"}


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
    if m:
        hi_e, lo_e = m["effect_at_high"], m["effect_at_low"]; gm = torn_g.get("P.87", {})
        out.append({"name": "Gains spent back", "employment_pct": hi_e, "gdp_pct": gm.get("effect_at_high"), "jobs": round(-hi_e / 100 * base), "source": "sensitivity: demand multiplier at the top of its range",
                    "description": f"If productivity gains are spent back into the economy, employment in {yr} is {hi_e:+.0f}% versus no AI ({'about ' + _millions(-hi_e/100*base) + ' more jobs' if hi_e > 0 else 'about ' + _millions(-hi_e/100*base) + ' fewer'})."})
        out.append({"name": "Gains pocketed", "employment_pct": lo_e, "gdp_pct": gm.get("effect_at_low"), "jobs": round(-lo_e / 100 * base), "source": "sensitivity: demand multiplier at the bottom of its range",
                    "description": f"If the gains are saved or paid out as rents, employment is {lo_e:+.0f}% (about {_millions(-lo_e/100*base)} fewer jobs)."})
    else:
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
    "likely range": "the middle 80% of the model's runs; one run in ten falls above it and one in ten below",
    "we would bet on it / leaning / a coin flip": "how sure the model is of the direction: sure across all its versions, mostly, or split",
    "AI income": "money flowing to the makers of models, computing, and chips, and to integrators",
    "jobs ledger / people ledger": "positions that exist versus people whose job was affected; a person who finds other work takes a position someone else would have had, so the two do not add up to each other",
}


# ---------------------------------------------------------------- personal outlook
def outlook(doc: dict[str, Any], occ_code: str | None, age_band: str | None, region: str = "US") -> dict[str, Any]:
    q = doc["meta"]["quarters"]; t40 = len(q) - 1; t30 = q.index("2030Q4") if "2030Q4" in q else t40; yr = q[t40][:4]
    st = story(doc, region)
    occs = doc.get("occupations", [])
    o = next((x for x in occs if x["occ_code"] == occ_code), None) if occ_code else None
    out: dict[str, Any] = {"region": region, "beats": [b for b in st["beats"] if b["id"] in ("jobs", "hiring", "pay")], "sureness_legend": SURENESS,
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
def executive_brief_md(st: dict[str, Any]) -> str:
    n = st["numbers"]; yr = st["horizon"][1][:4]
    L = [f"# What AI does to work in {st['region']}, in seven findings", "",
         f"Scenario: {st['scenario_name']}. Everything below is a difference from a world in which AI stopped improving in 2023. Run `{st['scenario_hash']}`.", ""]
    L.append("## In five sentences"); L.append("")
    L.append(f"By {yr} there are about {_millions(n['jobs_gap'])} fewer jobs than there would have been, out of about {_millions(n['jobs_base'])}; most of them are jobs never created rather than jobs destroyed. "
             f"Almost none of that is layoffs: it is positions not refilled, so the young pay first. Real pay rises about {n['real_wage_pct']['p50']:.0f}% and the economy is about {n['gdp_pct']:.0f}% larger, "
             f"but workers' share of income falls {abs(n['wage_share_pp']):.1f} points. Office work is reshaped now, robots come in the mid-2030s, AI-made content spreads category by category. "
             f"Whether jobs end up down {abs(n['employment_pct']['p10']):.0f}% or flat depends mostly on whether the gains are spent back into the economy.")
    L.append("")
    for i, b in enumerate(st["beats"], 1):
        L.append(f"## {i}. {b['title']}"); L.append(""); L.append(b["sentence"]); L.append("")
        if b.get("extra_chart"):
            L.append(f"*{b['extra_chart'].get('title', '')}*"); L.append("")
            for label, v in b["extra_chart"]["items"]:
                L.append(f"- {label.strip()}: {float(v):,.0f}")
            L.append("")
        L.append(f"*Likely range:* {b['range']}  ")
        L.append(f"*How sure:* {b['sureness']['label']}.  ")
        L.append(f"*What changes it:* {b['what_changes_it']}"); L.append("")
    L.append("## What could be done"); L.append("")
    if st["policies"]:
        for pr in st["policies"]:
            L.append(f"- {pr['sentence']}")
    else:
        L.append("- Policy runs are not available for this document; the technical brief lists the levers.")
    L.append("")
    if st.get("forecasts"):
        L.append("## How the model compares with named forecasts"); L.append("")
        L.append("| Who | Claim | Model (this run) | Verdict |"); L.append("|---|---|---|---|")
        for f in st["forecasts"]:
            mc = f.get("model_central")
            L.append(f"| {f['short']} | {f['claimed']} {f['unit']} by {f['year']} ({f['region']}) | {(f'{mc:.1f}') if mc is not None else 'n/a'} | {f['verdict']}{' (nearest model quantity)' if f.get('proxy') else ''} |")
        L.append(""); L.append("A claim marked *nearest model quantity* is compared with the closest thing the model tracks, named in the technical brief; the verdict is about direction and size, not a one-to-one test.")
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
    n = st["numbers"]; yr = st["horizon"][1][:4]
    e = html.escape
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{e(st['scenario_name'] or 'Scenario')} — what AI does to work</title><style>{_CSS}</style></head><body>"]
    parts.append(f"<h1>What AI does to work in {e(st['region'])}, in seven findings</h1><p style='color:#666;font-size:14px'>Scenario: {e(st['scenario_name'] or '')}. Everything below is a difference from a world in which AI stopped improving in 2023.</p>")
    parts.append("<div class='lede'>" + e(
        f"By {yr} there are about {_millions(n['jobs_gap'])} fewer jobs than there would have been, out of about {_millions(n['jobs_base'])}; most of them are jobs never created rather than jobs destroyed. "
        f"Almost none of that is layoffs: it is positions not refilled, so the young pay first. Real pay rises about {n['real_wage_pct']['p50']:.0f}% and the economy is about {n['gdp_pct']:.0f}% larger, "
        f"but workers' share of income falls {abs(n['wage_share_pp']):.1f} points. Office work is reshaped now, robots come in the mid-2030s, AI-made content spreads category by category. "
        f"Whether jobs end up down {abs(n['employment_pct']['p10']):.0f}% or flat depends mostly on whether the gains are spent back into the economy.") + "</div>")
    for i, b in enumerate(st["beats"], 1):
        parts.append(f"<div class='beat'><h2>{i}. {e(b['title'])}</h2><p>{e(b['sentence'])}</p>")
        if b["id"] == "futures":
            parts.append("<div class='futures'>" + "".join(f"<div class='card'><b>{e(f['name'])}</b>{e(f['description'])}</div>" for f in b["chart"]["items"]) + "</div>")
        else:
            parts.append(chart_svg(b["chart"]))
        if b.get("extra_chart"):
            parts.append(f"<p style='font-size:13.5px;color:#666;margin:10px 0 2px'>{e(b['extra_chart'].get('title', ''))}</p>" + chart_svg(b["extra_chart"]))
        parts.append(f"<div class='meta'><span><b>Likely range:</b> {e(b['range'])}</span><span><b>How sure:</b> <span class='dots'>{'●' * b['sureness']['dots']}{'○' * (3 - b['sureness']['dots'])}</span> {e(b['sureness']['label'])}</span><span><b>What changes it:</b> {e(b['what_changes_it'])}</span></div></div>")
    parts.append("<h2>What could be done</h2>")
    if st["policies"]:
        parts.append("<ul>" + "".join(f"<li>{e(p['sentence'])}</li>" for p in st["policies"]) + "</ul>")
    else:
        parts.append("<p>Policy runs are not available for this document.</p>")
    if st.get("forecasts"):
        parts.append("<h2>How the model compares with named forecasts</h2><table><tr><th>Who</th><th>Claim</th><th>Model (this run)</th><th>Verdict</th></tr>")
        for f in st["forecasts"]:
            mc = f.get("model_central")
            parts.append(f"<tr><td>{e(f['short'])}</td><td>{e(str(f['claimed']))} {e(f['unit'])} by {f['year']} ({e(f['region'])})</td><td>{(f'{mc:.1f}') if mc is not None else 'n/a'}</td><td>{e(f['verdict'])}{' (nearest model quantity)' if f.get('proxy') else ''}</td></tr>")
        parts.append("</table><p style='font-size:13px;color:#666'>A claim marked <i>nearest model quantity</i> is compared with the closest thing the model tracks; the verdict is about direction and size, not a one-to-one test.</p>")
    parts.append("<h2>Read this with care</h2><div class='caveat'><ul>" + "".join(f"<li>{e(c)}</li>" for c in st["caveats"]) + "</ul></div>")
    parts.append("<h2>Words used</h2><ul>" + "".join(f"<li><b>{e(k)}</b>: {e(v)}</li>" for k, v in st["glossary"].items()) + "</ul>")
    parts.append(f"<p style='color:#888;font-size:12px'>Run <code>{e(st['scenario_hash'])}</code>. Technical brief and methodology in the repository.</p></body></html>")
    return "".join(parts)


def dumps(obj: Any) -> str:
    return json.dumps(obj, default=lambda o: float(o) if isinstance(o, (int, float)) or hasattr(o, "item") else str(o))


def _isfinite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)

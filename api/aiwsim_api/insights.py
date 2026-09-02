"""Deterministic candidate insights from a results document (Phase 4, contracts §15).

Each candidate is computed from the results document alone: statement with the numbers it rests on,
the mechanism in the spec that produces it, the model's own confidence in it, and a *surprise*
score (0–1) that ranks how far the finding sits from a naive prior. The chat layer can only pick
from and rephrase these candidates; it never produces numbers of its own.
"""
from __future__ import annotations

from typing import Any

HEADLINE_LABELS = {"employment_pct_vs_baseline": "employment", "gdp_pct_vs_baseline": "GDP",
                   "real_wage_pct_vs_baseline": "real wages", "wage_share_pp_vs_baseline": "wage share"}
AGE_LABELS = ["16–24", "25–44", "45–54", "55+"]


def _at(series: dict[str, list[float]], t: int, key: str = "p50") -> float:
    s = series.get(key) or series.get("central") or series.get("p50")
    return float(s[t]) if s else 0.0


def _band(series: dict[str, list[float]], t: int, unit: str = "%", nd: int = 1) -> str:
    p50 = _at(series, t)
    if "p10" in series and "p90" in series:
        return f"{p50:+.{nd}f}{unit} (10–90: {_at(series, t, 'p10'):+.{nd}f} to {_at(series, t, 'p90'):+.{nd}f}{unit})"
    return f"{p50:+.{nd}f}{unit}"


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _conf(doc: dict[str, Any], metric: str, q: str) -> str:
    return (doc.get("confidence", {}).get(metric, {}).get(q) or {}).get("level", "n/a")


def candidate_insights(doc: dict[str, Any], region: str = "US") -> list[dict[str, Any]]:
    quarters: list[str] = doc["meta"]["quarters"]
    t_end = len(quarters) - 1
    q_end = quarters[t_end]
    i30 = quarters.index("2030Q4") if "2030Q4" in quarters else t_end
    us = doc["series"].get("US", {})
    blk = doc["series"].get(region) or us
    out: list[dict[str, Any]] = []

    def add(key: str, title: str, statement: str, mechanism: str, confidence: str, surprise: float,
            evidence: dict[str, Any], metric: str | None = None, quarter: str = q_end) -> None:
        out.append({"key": key, "title": title, "statement": statement, "mechanism": mechanism, "confidence": confidence,
                    "surprise": round(_clip(surprise), 3), "evidence": evidence, "metric": metric, "quarter": quarter, "region": region})

    # 1. GDP up while employment down (or the reverse): the level/composition split.
    e, g, rw = blk.get("employment_pct_vs_baseline", {}), blk.get("gdp_pct_vs_baseline", {}), blk.get("real_wage_pct_vs_baseline", {})
    if e and g:
        e50, g50 = _at(e, t_end), _at(g, t_end)
        if g50 > 0 and e50 < 0:
            add("gdp_vs_employment", "Output rises while employment falls",
                f"In {region}, GDP is {_band(g, t_end)} above the no-AI baseline by {q_end} while employment is {_band(e, t_end)}; real wages are {_band(rw, t_end) if rw else 'n/a'}.",
                "Task automation lowers unit costs (spec §5.2); demand responds with elasticity η_s and the demand multiplier m (P.87), "
                "but below unit elasticity the output gain does not refill the displaced task-hours (spec §5.2–5.3).",
                _conf(doc, "employment_pct_vs_baseline", q_end), 0.35 + min(0.4, abs(e50) / 10) + min(0.25, g50 / 20),
                {"gdp_pct_vs_baseline": _at(g, t_end), "employment_pct_vs_baseline": e50, "real_wage_pct_vs_baseline": _at(rw, t_end) if rw else None},
                "employment_pct_vs_baseline")

    # 2. Hiring channel: jobs lost through unfilled attrition vs layoffs.
    lay, unh = blk.get("laid_off_cum", {}), blk.get("unhired_entrants_cum", {})
    if lay and unh:
        l50, u50 = _at(lay, t_end), _at(unh, t_end)
        tot = l50 + u50
        if tot > 0:
            share = u50 / tot
            add("hiring_channel", "Displacement runs through hiring, not layoffs",
                f"Of {tot/1e6:.1f}M jobs below baseline in {region} by {q_end}, {100*share:.0f}% are positions not refilled after normal attrition and {100*(1-share):.0f}% are layoffs.",
                "Employers first absorb the fall in labor demand through net occupational attrition (P.63, 2.5%/quarter); layoffs occur only when the required "
                "contraction outruns attrition and layoff friction (P.64) (spec §5.3).",
                _conf(doc, "employment_pct_vs_baseline", q_end), 0.3 + 0.6 * abs(share - 0.5) * 2 * (0.5 if share < 0.5 else 1.0),
                {"laid_off_cum": l50, "unhired_entrants_cum": u50, "unfilled_share": round(share, 3)}, "employment_pct_vs_baseline")

    # 3. Sensitivity: one parameter dominates, or flips the sign.
    torn = doc.get("tornado", {}).get("employment_pct_vs_baseline", [])
    if len(torn) >= 2:
        top, second = torn[0], torn[1]
        ratio = top["swing"] / max(second["swing"], 1e-9)
        flips = [r for r in torn if r.get("flips_sign")]
        add("dominant_parameter", f"{top['name']} dominates the employment uncertainty",
            f"Across its literature range ({top['low']}–{top['high']}), {top['name']} ({top['param']}) moves {q_end} employment from {top['effect_at_low']:+.1f}% to {top['effect_at_high']:+.1f}%, "
            f"a swing {ratio:.1f}× the next parameter ({second['name']}, {second['swing']:.1f} pp)."
            + (f" It is one of {len(flips)} parameter(s) that can flip the sign of the effect." if top.get("flips_sign") else ""),
            "One-at-a-time sensitivity at the central draw (spec §9.3); the demand feedback (spec §6.2) enters through the multiplier m (P.87) and elasticity η_s (P.60).",
            "high" if ratio > 2 else "medium", 0.25 + min(0.5, (ratio - 1) / 4) + (0.2 if top.get("flips_sign") else 0.0),
            {"param": top["param"], "swing_pp": top["swing"], "next_param": second["param"], "next_swing_pp": second["swing"], "flip_params": [r["param"] for r in flips]},
            "employment_pct_vs_baseline")

    # 4. Structural vs parametric uncertainty.
    st = doc.get("structural", {}).get("employment_pct_vs_baseline", {}).get("spread", {}).get(q_end)
    if st:
        s_pp, p_pp = st.get("structural_pp", 0.0), st.get("parametric_pp", 0.0)
        if p_pp > 0:
            r = s_pp / p_pp
            add("structural_uncertainty", "Which theory is right matters as much as which numbers",
                f"The spread between mechanism cells (demand form × reinstatement × pass-through) at {q_end} is {s_pp:.1f} pp of employment, against a {p_pp:.1f} pp 10–90 parametric band within a cell.",
                "The 2×2×2 structural ensemble (spec §9.2) encodes literature disagreements as discrete alternatives rather than parameter ranges.",
                "high" if len(doc["meta"].get("cells", [])) >= 4 else "low", 0.3 + min(0.6, r * 0.4),
                {"structural_pp": s_pp, "parametric_pp": p_pp, "ratio": round(r, 2)}, "employment_pct_vs_baseline")

    # 5. Cohort incidence: young workers and low deciles.
    coh = doc.get("cohorts", {})
    if coh.get("age") and region == "US":
        shares = [_at(b["share_of_jobs_lost"], t_end) for b in coh["age"]]
        young = shares[0] if shares else 0.0
        add("age_incidence", "Young entrants carry the adjustment",
            f"Workers aged 16–24 absorb {100*young:.0f}% of jobs below baseline by {q_end}" + (f", and 25–44 a further {100*shares[1]:.0f}%" if len(shares) > 1 else "")
            + f"; the 55+ group carries {100*shares[3]:.0f}%." if len(shares) > 3 else "",
            "Because contraction runs through unfilled vacancies (spec §5.3), the incidence falls on entrants and job changers rather than incumbents; "
            "cohort attribution follows the hiring-share matrix (spec §5.6).",
            _conf(doc, "employment_pct_vs_baseline", q_end), 0.3 + min(0.6, max(0.0, young - 0.13) * 2.5),
            {"share_by_age": dict(zip(AGE_LABELS, [round(s, 3) for s in shares]))}, "employment_pct_vs_baseline")
    if coh.get("income_decile") and region == "US":
        dec = [_at(b["share_of_jobs_lost"], t_end) for b in coh["income_decile"]]
        if len(dec) == 10:
            low, high = sum(dec[:3]), sum(dec[7:])
            add("decile_incidence", "Incidence by income decile",
                f"Deciles 1–3 carry {100*low:.0f}% of jobs below baseline by {q_end} and deciles 8–10 carry {100*high:.0f}%.",
                "Displacement is task-based (spec §2): clerical and entry-level cognitive tasks sit in the lower-middle deciles, "
                "while high-decile occupations are augmented (U) more than displaced (D) (spec §5.2).",
                _conf(doc, "employment_pct_vs_baseline", q_end), 0.25 + min(0.5, abs(low - high)),
                {"deciles_1_3": round(low, 3), "deciles_8_10": round(high, 3)}, "employment_pct_vs_baseline")

    # 6. Real wages vs nominal: the price channel.
    nw, pi = blk.get("nominal_wage_pct_vs_baseline", {}), blk.get("price_index_pct_vs_baseline", {})
    if rw and nw and pi:
        n50, r50, p50 = _at(nw, t_end), _at(rw, t_end), _at(pi, t_end)
        if abs(r50 - n50) > 0.5:
            add("price_channel", "Real wage gains come through prices",
                f"Nominal wages in {region} are {n50:+.1f}% vs baseline by {q_end}, but the price index is {p50:+.1f}%, so real wages are {r50:+.1f}%.",
                "Pass-through of cost savings to prices π_p (P.53) lowers the consumer price index; real wages rise even where the wage curve holds nominal wages down (spec §6.2).",
                _conf(doc, "real_wage_pct_vs_baseline", q_end), 0.3 + min(0.5, abs(r50 - n50) / 6),
                {"nominal_wage_pct": n50, "real_wage_pct": r50, "price_index_pct": p50}, "real_wage_pct_vs_baseline")

    # 7. Occupation concentration.
    occs = doc.get("occupations", [])
    if occs and region == "US":
        big = [o for o in occs if o["emp0"] >= 100_000]
        ranked = sorted(big, key=lambda o: -(o["displacement"].get("central") or o["displacement"]["p50"])[i30])[:3]
        if ranked:
            add("occupation_leaders", "Where displacement lands first",
                f"By {quarters[i30]}, the highest realized displacement among occupations with 100k+ jobs: " + "; ".join(
                    f"{o['title']} ({100*(o['displacement'].get('central') or o['displacement']['p50'])[i30]:.0f}% of task-hours, {o['emp0']/1e3:.0f}k jobs)" for o in ranked) + ".",
                "Task-level feasibility (spec §2.2) and the profitability test (spec §3.3) reach exposure-class E1 tasks first; realized displacement D is scaled by adoption and intensity (spec §4.2).",
                "medium", 0.35, {"occupations": [{"occ_code": o["occ_code"], "title": o["title"], "displacement": (o["displacement"].get("central") or o["displacement"]["p50"])[i30]} for o in ranked]},
                "employment_pct_vs_baseline", quarters[i30])

    # 8. Regional rents concentration and regional divergence.
    regions = doc["meta"].get("regions", [])
    if len(regions) > 1:
        rents = {x: _at(doc["series"][x]["ai_rents_received_bn"]["total"], t_end) for x in regions if x in doc["series"]}
        tot = sum(rents.values())
        if tot > 0:
            top = sorted(rents.items(), key=lambda kv: -kv[1])[:3]
            add("rents_concentration", "AI rents concentrate in the chip and model producers",
                f"By {q_end}, AI rents accrue " + ", ".join(f"{100*v/tot:.0f}% to {x}" for x, v in top) + f" of a ${tot/1e3:.1f}T annual total.",
                "Rents are allocated per value-chain stage: model rents to the labs' home regions, compute to data-center location, chips to a fixed fab split (spec §6.3).",
                "medium", 0.3 + min(0.5, top[0][1] / tot - 0.3),
                {"rents_bn": {x: round(v, 1) for x, v in top}, "total_bn": round(tot, 1)}, None)
        emps = {x: _at(doc["series"][x]["employment_pct_vs_baseline"], t_end) for x in regions if x in doc["series"]}
        if emps:
            lo, hi = min(emps.items(), key=lambda kv: kv[1]), max(emps.items(), key=lambda kv: kv[1])
            add("regional_divergence", "Regions diverge on employment",
                f"The {q_end} employment effect ranges from {lo[1]:+.1f}% ({lo[0]}) to {hi[1]:+.1f}% ({hi[0]}).",
                "Wage tiers change the profitability test (spec §3.3): lower-wage regions automate later at a given price; access lags and spillover shift timing (spec §4.2, §6.3).",
                "medium", 0.25 + min(0.5, (hi[1] - lo[1]) / 8), {"employment_pct_by_region": {k: round(v, 2) for k, v in emps.items()}}, "employment_pct_vs_baseline")

    # 9. Sign confidence.
    conf = doc.get("confidence", {}).get("employment_pct_vs_baseline", {}).get(q_end)
    if conf:
        add("sign_confidence", f"Sign of the employment effect is {conf['level']} confidence",
            f"The {q_end} employment sign holds in {100*conf['sign_share']:.0f}% of draws; mechanism cells {'agree' if conf['cells_agree'] else 'disagree'}"
            + (f"; parameters able to flip it: {', '.join(conf['flip_params'])}." if conf.get("flip_params") else "."),
            "Confidence classification combines the draw sign share, cell agreement, and tornado sign flips (spec §9.4).",
            conf["level"], 0.2 + (0.5 if conf["level"] == "low" else 0.2 if conf["level"] == "medium" else 0.0),
            {"sign_share": conf["sign_share"], "cells_agree": conf["cells_agree"], "flip_params": conf.get("flip_params", [])}, "employment_pct_vs_baseline")

    # 10. Adoption outruns displacement.
    ad = blk.get("adoption_share", {})
    if ad and e:
        a30, e30 = _at(ad, i30), _at(e, i30)
        if a30 > 30:
            add("adoption_vs_effect", "Adoption is broad before the labor effect is",
                f"By {quarters[i30]}, {a30:.0f}% of {region} employment sits in adopting firms, yet employment is only {e30:+.1f}% vs baseline.",
                "The adoption S-curve (spec §4.2) counts firms using AI at any intensity; the realized task share is capped by the intensity ceiling (P.50) and the feasibility clock (spec §2.3).",
                "medium", 0.25 + min(0.5, (a30 / 100) - abs(e30) / 10), {"adoption_share": a30, "employment_pct_vs_baseline": e30}, "employment_pct_vs_baseline", quarters[i30])

    out.sort(key=lambda d: -d["surprise"])
    return out


def compare_insights(cmp: dict[str, Any], quarters: list[str], region: str = "US") -> list[dict[str, Any]]:
    """Candidates about what a scenario changed vs a reference run (paired draws, contracts §10)."""
    t_end = len(quarters) - 1; q_end = quarters[t_end]
    a_name = cmp["a"].get("name") or cmp["a"]["hash"]; b_name = cmp["b"].get("name") or cmp["b"]["hash"]
    lever_diff = [d for d in cmp.get("diff", []) if d["path"].split(".")[0] in ("levers", "shocks", "overrides")]
    levers = ", ".join(f"{d['path'].split('.', 1)[-1]} {d.get('from')}→{d.get('to')}" for d in lever_diff[:4]) or "no lever differs (ensemble or draw settings only)"
    out: list[dict[str, Any]] = []
    series = cmp.get("delta", {}).get("series", {})
    for k, label in HEADLINE_LABELS.items():
        s = series.get(k)
        if not s or not s.get("p50"):
            continue
        d50 = float(s["p50"][t_end]); lo = float(s.get("p10", s["p50"])[t_end]); hi = float(s.get("p90", s["p50"])[t_end])
        excludes_zero = lo > 0 or hi < 0
        unit = "pp"
        out.append({"key": f"delta_{k}", "title": f"{b_name} moves {label} by {d50:+.1f} {unit} vs {a_name}",
                    "statement": f"Paired over the same draws, {label} in {q_end} is {d50:+.1f} {unit} in '{b_name}' relative to '{a_name}' (10–90: {lo:+.1f} to {hi:+.1f}); "
                                 f"the band {'excludes' if excludes_zero else 'includes'} zero. Levers changed: {levers}.",
                    "mechanism": "Paired comparison on common draws removes shared parameter noise, so the band reflects the lever change alone (spec §9.5); "
                                 "the lever's mechanism is listed in the diff.",
                    "confidence": "high" if excludes_zero and abs(d50) > 0.5 else ("medium" if excludes_zero else "low"),
                    "surprise": round(_clip(0.4 + min(0.5, abs(d50) / 4) + (0.1 if excludes_zero else -0.2)), 3),
                    "evidence": {"delta_p10": lo, "delta_p50": d50, "delta_p90": hi, "paired_draws": cmp.get("delta", {}).get("paired_draws"), "diff": cmp.get("diff", [])},
                    "metric": k, "quarter": q_end, "region": region})
    if len(out) >= 2:
        e = next((c for c in out if c["metric"] == "employment_pct_vs_baseline"), None)
        g = next((c for c in out if c["metric"] == "gdp_pct_vs_baseline"), None)
        if e and g and e["evidence"]["delta_p50"] * g["evidence"]["delta_p50"] < 0 and min(abs(e["evidence"]["delta_p50"]), abs(g["evidence"]["delta_p50"])) > 0.5:
            out.append({"key": "delta_divergence", "title": "The change moves GDP and employment in opposite directions",
                        "statement": f"Relative to '{a_name}', '{b_name}' changes {q_end} GDP by {g['evidence']['delta_p50']:+.1f} pp and employment by {e['evidence']['delta_p50']:+.1f} pp.",
                        "mechanism": "Faster or cheaper capability raises output through the cost channel while the hiring channel absorbs the task-hours (spec §5.2–5.3, §6.2).",
                        "confidence": "medium", "surprise": 0.85, "evidence": {"gdp": g["evidence"], "employment": e["evidence"]},
                        "metric": "employment_pct_vs_baseline", "quarter": q_end, "region": region})
    if out and all(abs(c["evidence"]["delta_p50"]) < 0.3 for c in out if c["key"] != "delta_divergence"):
        out.append({"key": "delta_null", "title": f"'{b_name}' barely moves {region} headline outcomes",
                    "statement": f"Relative to '{a_name}', every {q_end} headline delta in {region} is within ±0.3 pp: "
                                 + "; ".join(f"{HEADLINE_LABELS[c['metric']]} {c['evidence']['delta_p50']:+.1f} pp" for c in out if c["key"] != "delta_divergence")
                                 + f". Levers changed: {levers}.",
                    "mechanism": "Levers acting on another region's availability or regulation reach this region only through spillover and trade (spec §4.2, §6.3), "
                                 "which are second-order at this horizon; check the affected region's series and the regional comparison instead.",
                    "confidence": "high", "surprise": 0.96, "evidence": {"deltas": {c["metric"]: c["evidence"]["delta_p50"] for c in out if c["key"] != "delta_divergence"}, "diff": lever_diff},
                    "metric": "employment_pct_vs_baseline", "quarter": q_end, "region": region})
    return out


def top_insights(doc: dict[str, Any], region: str = "US", n: int = 3, compare: dict[str, Any] | None = None) -> dict[str, Any]:
    cands = candidate_insights(doc, region)
    if compare:
        cands = compare_insights(compare, doc["meta"]["quarters"], region) + cands
        cands.sort(key=lambda d: -d["surprise"])
    return {"scenario_hash": doc["meta"]["scenario_hash"], "scenario_id": doc["meta"].get("scenario_id"), "region": region,
            "compare_hash": compare["a"]["hash"] if compare else None,
            "top": cands[:n], "candidates": cands, "method": "deterministic ranking by surprise score; statements are computed from the results document"
            + ("; delta candidates from the paired comparison against compare_hash" if compare else "")}

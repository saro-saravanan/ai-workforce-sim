"""Phase 9 diagnostics for the task engine (docs/adversarial-review-phase8.md §2.4): the threshold-seed sensitivity and the
classifier audit sample. Both are reproducible from the command line (``aiwsim diag threshold-seeds``, ``aiwsim diag classifier-sample``)."""
from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from .mc import run_batch
from .pipeline import Context, load_scenario_by_path_or_id

CHANNELS = ("software", "emb_driving", "emb_manip", "emb_fixed", "emb_aerial", "none")


def _ranks(x: np.ndarray) -> np.ndarray:
    """Average ranks (ties share the mean rank), 1-based."""
    order = np.argsort(x, kind="mergesort"); sx = x[order]; ranks = np.empty(len(x)); i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and sx[j + 1] == sx[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rank correlation; scipy when available, else the rank Pearson correlation in numpy."""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    try:
        from scipy.stats import spearmanr
        return float(spearmanr(a, b).correlation)
    except ImportError:
        ra = _ranks(a); rb = _ranks(b); ra -= ra.mean(); rb -= rb.mean()
        d = float(np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))
        return float((ra * rb).sum() / d) if d > 0 else float("nan")


def threshold_seed_sensitivity(ctx: Context, seeds: tuple[int, ...] = (0, 1, 2), regions: tuple[str, ...] = ("US",),
                               scenario: str = "baseline") -> list[dict[str, Any]]:
    """Central run of ``scenario`` per threshold seed (lever capability.threshold_seed): the 2030 and 2040 U.S. employment headline, the
    Spearman rank correlation of occupation-level 2040 employment effects with seed 0, and the share of the ten most affected major groups
    that seed 0 and the seed agree on."""
    base = load_scenario_by_path_or_id(ctx, scenario)
    inp = ctx.inputs; rows: list[dict[str, Any]] = []; occ0 = None; top0: set[int] = set()
    for s in seeds:
        scen = copy.deepcopy(base); scen.setdefault("levers", {}).setdefault("capability", {})["threshold_seed"] = int(s)
        scen = ctx.resolve(scen); p = ctx.params_for(scen)
        o = run_batch(inp, p, scen, None, fitted=ctx.fitted, cohorts=ctx.cohorts, regional=ctx.regional, regions=list(regions), apps=ctx.apps)
        us = o.regions["US"]; q = o.quarters; t30 = q.index("2030Q4") if "2030Q4" in q else len(q) - 1
        occ = us.N[0, :, -1] / np.maximum(us.N0[:, -1], 1.0) - 1.0                                   # occupation-level 2040 employment effect
        top = set(np.argsort(occ)[: max(1, inp.n_occ // 10)].tolist())                                  # most affected decile of occupations
        if occ0 is None:
            occ0 = occ; top0 = top
        rows.append({"seed": int(s), "employment_pct_2030": round(100 * float(us.employment_pct[0, t30]), 2),
                     "employment_pct_2040": round(100 * float(us.employment_pct[0, -1]), 2),
                     "gdp_pct_2040": round(100 * float(us.gdp_pct[0, -1]), 2),
                     "spearman_occupations_vs_seed0": round(spearman(occ0, occ), 4),
                     "top_decile_overlap_vs_seed0": round(len(top0 & top) / max(len(top0), 1), 3),
                     "max_abs_occupation_change_pp": round(100 * float(np.abs(occ - occ0).max()), 2)})
    return rows


def seed_table(rows: list[dict[str, Any]]) -> str:
    head = ["Seed", "Employment 2030 (%)", "Employment 2040 (%)", "Δ vs seed 0 (pp)", "GDP 2040 (%)", "Spearman ρ, occupation effects 2040",
            "Top-decile overlap", "Max occupation change (pp)"]
    e0 = rows[0]["employment_pct_2040"] if rows else 0.0
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        lines.append(f"| {r['seed']} | {r['employment_pct_2030']:+.2f} | {r['employment_pct_2040']:+.2f} | {r['employment_pct_2040'] - e0:+.2f} | "
                     f"{r['gdp_pct_2040']:+.2f} | {r['spearman_occupations_vs_seed0']:.4f} | {r['top_decile_overlap_vs_seed0']:.2f} | {r['max_abs_occupation_change_pp']:.2f} |")
    return "\n".join(lines)


def _cell(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def classifier_sample(root: Path, n: int = 120, seed: int = 20260903, out: Path | None = None) -> pl.DataFrame:
    """Sample ``n`` task statements stratified by channel (n // 6 per channel; strata that are too small hand their quota to the others in
    round-robin) with a fixed seed, and write them as a markdown audit table with a blank column for the human label."""
    proc = root / "data" / "processed"
    tasks = pl.read_csv(proc / "tasks.csv", schema_overrides={"occ_code": pl.Utf8, "task_id": pl.Utf8})
    occ = pl.read_csv(proc / "occupations.csv", schema_overrides={"occ_code": pl.Utf8}).select("occ_code", "title")
    tasks = tasks.join(occ, on="occ_code", how="left").sort(["occ_code", "task_id"])
    rng = np.random.default_rng(seed)
    avail = {c: tasks.filter(pl.col("channel") == c) for c in CHANNELS}
    quota = {c: min(n // len(CHANNELS), avail[c].height) for c in CHANNELS}
    while sum(quota.values()) < n and any(quota[c] < avail[c].height for c in CHANNELS):
        for c in CHANNELS:
            if sum(quota.values()) >= n:
                break
            if quota[c] < avail[c].height:
                quota[c] += 1
    parts = []
    for c in CHANNELS:
        df = avail[c]
        if quota[c] == 0 or df.height == 0:
            continue
        idx = np.sort(rng.choice(df.height, size=quota[c], replace=False))
        parts.append(df[idx.tolist()])
    sample = pl.concat(parts).select("occ_code", "title", "task_id", "task_text", "modality", "channel")
    if out is not None:
        counts = {c: int(quota[c]) for c in CHANNELS}
        lines = ["# Classifier audit sample", "",
                 f"{sample.height} O*NET task statements sampled from `data/processed/tasks.csv` with seed {seed}, stratified by the channel the keyword rules "
                 f"assigned (`aiwsim diag classifier-sample --n {n} --seed {seed}`; review §2.4 item 3). Counts by assigned channel: "
                 + ", ".join(f"{c} {v}" for c, v in counts.items()) + ".", "",
                 ("Fill the last column by hand with one of: `software` (screen work an AI system can do), `emb_driving` (a vehicle drives), `emb_manip` "
                  "(a mobile manipulator or humanoid handles objects in a semi-structured setting), `emb_fixed` (fixed automation in a structured line or "
                  "cell), `emb_aerial` (a drone), `none` (care, dexterity, safety-critical or unstructured bodily work outside the embodied horizon at "
                  "central). Precision and recall per channel follow from the two columns; the sample is not labelled by the model's authors."), "",
                 "| # | Occupation | Task statement | Assigned channel | Human label |", "|---|---|---|---|---|"]
        for i, r in enumerate(sample.iter_rows(named=True), start=1):
            lines.append(f"| {i} | {_cell(r['occ_code'])} {_cell(r['title'] or '')} | {_cell(r['task_text'])} | {_cell(r['channel'])} |  |")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sample


# ----------------------------------------------------------------------------------------------
# Phase 9b: 2026 hold-out and the exposure-source swap
# ----------------------------------------------------------------------------------------------
def _backtest_rows(ctx: Context, scen: dict[str, Any], regions: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Backtest rows of a central run; all ten regions by default because the revenue row is a world total."""
    from .pipeline import run_scenario
    d, _ = run_scenario(ctx, ctx.resolve(scen), draws=1, with_channels=False, with_tornado=False, regions=list(regions) if regions else None)
    return d.get("backtest", {}).get("rows", [])


def _row(rows: list[dict[str, Any]], sid: str, q: str) -> dict[str, Any] | None:
    return next((r for r in rows if r["series_id"] == sid and r["quarter"] == q), None)


def holdout_2026(ctx: Context, scenario: str = "baseline", multiples: tuple[float, ...] = (3.0, 4.0, 5.0, 6.0, 7.0, 8.0),
                 layoff_shares: tuple[float, ...] = (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)) -> dict[str, Any]:
    """Refit the two fitted parameters to 2025 only and score the 2026 rows (review §2.2 item 2). The market-price multiple P.143 is refit to
    the 2025 revenue row, then the layoff-first share to the 2025 Challenger row (a one-dimensional grid each, central ten-region runs); the
    2026 rows (Challenger 2026Q2, revenue 2026, BTOS 2026Q1) are then reported under the refit and under the shipped fit."""
    base = load_scenario_by_path_or_id(ctx, scenario)
    shipped = _backtest_rows(ctx, copy.deepcopy(base))
    def with_(m: float | None, phi: float | None) -> dict[str, Any]:
        s = copy.deepcopy(base)
        if m is not None:
            s.setdefault("overrides", {})["P.143"] = {"central": float(m)}
        if phi is not None:
            s.setdefault("levers", {}).setdefault("labor", {})["layoff_first_share"] = float(phi)
        return s
    def logerr(rows: list[dict[str, Any]], sid: str, q: str) -> float:
        r = _row(rows, sid, q)
        return abs(math.log(max(r["model_central"], 1e-9) / max(r["value"], 1e-9))) if r and r["model_central"] else 9.0
    fit_m = []
    for m in multiples:
        rows = _backtest_rows(ctx, with_(m, None)); fit_m.append((logerr(rows, "ai_revenue", "2025Q4"), m, rows))
    best_m = min(fit_m, key=lambda x: x[0])[1]
    fit_phi = []
    for phi in layoff_shares:
        rows = _backtest_rows(ctx, with_(best_m, phi)); fit_phi.append((logerr(rows, "challenger_ai_cum", "2025Q4"), phi, rows))
    _err_phi, best_phi, refit_rows = min(fit_phi, key=lambda x: x[0])
    score = [("challenger_ai_cum", "2026Q2"), ("ai_revenue", "2026Q4"), ("btos_firm", "2026Q1"), ("btos_firm", "2025Q4")]
    table = []
    for sid, q in score:
        a = _row(shipped, sid, q); b = _row(refit_rows, sid, q)
        if a and b:
            table.append({"series_id": sid, "label": a["label"], "quarter": q, "observed": a["value"], "shipped_model": a["model_central"], "shipped_error_pct": a["error_pct"],
                          "refit_model": b["model_central"], "refit_error_pct": b["error_pct"]})
    shipped_m = float(ctx.params_for(ctx.resolve(copy.deepcopy(base))).get("P.143", 5.0))
    shipped_phi = float(base.get("levers", {}).get("labor", {}).get("layoff_first_share", 0.25))
    return {"refit": {"P.143": best_m, "layoff_first_share": best_phi, "fit_rows": ["ai_revenue 2025Q4", "challenger_ai_cum 2025Q4"]},
            "shipped": {"P.143": shipped_m, "layoff_first_share": shipped_phi, "fit_rows": ["ai_revenue 2025Q4, 2026Q4", "challenger_ai_cum 2025Q4, 2026Q2"]},
            "grid": {"P.143": [(m, round(e, 3)) for e, m, _ in fit_m], "layoff_first_share": [(phi, round(e, 3)) for e, phi, _ in fit_phi]},
            "holdout_rows": table}


def holdout_markdown(res: dict[str, Any]) -> str:
    intro = (f"Refit to 2025 only: market-price multiple P.143 = {res['refit']['P.143']:.1f} (shipped {res['shipped']['P.143']:.1f}), layoff-first share = "
             f"{res['refit']['layoff_first_share']:.2f} (shipped {res['shipped']['layoff_first_share']:.2f}). Central ten-region runs; the shipped fit used the 2026 rows too.")
    L = ["# 2026 hold-out (review §2.2, item 2)", "", intro, "",
         "| Series | Quarter | Observed | Shipped model | Shipped error | Refit-to-2025 model | Refit error |", "|---|---|---|---|---|---|---|"]
    for r in res["holdout_rows"]:
        L.append(f"| {r['label']} | {r['quarter']} | {r['observed']:,.1f} | {r['shipped_model']:,.1f} | {r['shipped_error_pct']:+.0f}% | {r['refit_model']:,.1f} | {r['refit_error_pct']:+.0f}% |")
    L += ["", "Grid searched (absolute log error against the 2025 row): P.143 " + ", ".join(f"{m}: {e}" for m, e in res["grid"]["P.143"]) +
          "; layoff share " + ", ".join(f"{p}: {e}" for p, e in res["grid"]["layoff_first_share"]) + ".", ""]
    return "\n".join(L) + "\n"


def exposure_source_sensitivity(ctx: Context, regions: tuple[str, ...] = ("US",), scenario: str = "baseline") -> list[dict[str, Any]]:
    """Central run under the two exposure sources (lever capability.exposure_source): headline, Spearman rank correlation of occupation effects,
    top-decile overlap; the AIOE source needs data/processed/exposure_aioe.csv (built from the fetched appendix, never committed)."""
    base = load_scenario_by_path_or_id(ctx, scenario)
    inp = ctx.inputs; rows: list[dict[str, Any]] = []; occ0 = None; top0: set[int] = set()
    for src in ("gpts", "aioe"):
        scen = copy.deepcopy(base); scen.setdefault("levers", {}).setdefault("capability", {})["exposure_source"] = src
        scen = ctx.resolve(scen); p = ctx.params_for(scen)
        o = run_batch(inp, p, scen, None, fitted=ctx.fitted, cohorts=ctx.cohorts, regional=ctx.regional, regions=list(regions), apps=ctx.apps)
        us = o.regions["US"]; q = o.quarters; t30 = q.index("2030Q4") if "2030Q4" in q else len(q) - 1
        occ = us.N[0, :, -1] / np.maximum(us.N0[:, -1], 1.0) - 1.0
        top = set(np.argsort(occ)[: max(1, inp.n_occ // 10)].tolist())
        if occ0 is None:
            occ0 = occ; top0 = top
        rows.append({"source": src, "available": bool(inp.occ_beta_alt is not None) if src == "aioe" else True,
                     "employment_pct_2030": round(100 * float(us.employment_pct[0, t30]), 2), "employment_pct_2040": round(100 * float(us.employment_pct[0, -1]), 2),
                     "gdp_pct_2040": round(100 * float(us.gdp_pct[0, -1]), 2), "spearman_occupations_vs_gpts": round(spearman(occ0, occ), 4),
                     "top_decile_overlap_vs_gpts": round(len(top0 & top) / max(len(top0), 1), 3), "max_abs_occupation_change_pp": round(100 * float(np.abs(occ - occ0).max()), 2)})
    return rows


def exposure_table(rows: list[dict[str, Any]]) -> str:
    head = ["Exposure source", "Employment 2030 (%)", "Employment 2040 (%)", "GDP 2040 (%)", "Spearman ρ, occupation effects vs GPTs", "Top-decile overlap", "Max occupation change (pp)"]
    L = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        L.append(f"| {r['source']}{'' if r['available'] else ' (table absent: identical to gpts)'} | {r['employment_pct_2030']:+.2f} | {r['employment_pct_2040']:+.2f} | {r['gdp_pct_2040']:+.2f} | "
                 f"{r['spearman_occupations_vs_gpts']:.3f} | {r['top_decile_overlap_vs_gpts']:.2f} | {r['max_abs_occupation_change_pp']:.2f} |")
    return "\n".join(L)

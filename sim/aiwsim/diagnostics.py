"""Phase 9 diagnostics for the task engine (docs/adversarial-review-phase8.md §2.4): the threshold-seed sensitivity and the
classifier audit sample. Both are reproducible from the command line (``aiwsim diag threshold-seeds``, ``aiwsim diag classifier-sample``)."""
from __future__ import annotations

import copy
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

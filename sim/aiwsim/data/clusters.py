"""Occupation clustering (spec §1.1) and the O*NET-SOC -> OEWS code mapping.

Rule, as specified:

1. Collapse O*NET-SOC codes (``xx-xxxx.00`` / ``.01`` ...) to 6-digit SOC.  Task weights are
   aggregated across the O*NET sub-occupations and renormalized within the 6-digit code.
2. Every 6-digit SOC with national employment >= ``emp_threshold`` (300,000) is its own cluster.
3. The remaining occupations are merged within the same SOC family (minor group, ``xx-xx00``;
   see ``family_key``) when their Eloundou beta differs by < ``beta_tol`` (0.1) and their median
   annual wages differ by < ``wage_tol`` (20%).  Merging never crosses 2-digit major groups
   (implied by the family rule, asserted anyway).
4. Beta for an occupation = mean of ``human_rating_beta`` and ``dv_rating_beta`` from
   ``occ_level.csv`` where both exist, else whichever exists; averaged over the O*NET
   sub-occupations that map to the same OEWS code.

Merging is greedy and deterministic: within a family, un-anchored occupations are visited in
descending employment order and attached to the first existing merged cluster (in creation order)
whose employment-weighted beta and median wage are within tolerance, else they start a new
cluster.  Thresholds are parameters (``ClusterParams``) so the spec's targets (~100-150 clusters)
can be revisited without touching code.

OEWS May 2021 publishes some SOC 2018 occupations at the broad (``xx-xxx0``) level and merges a
few SOC-2010-era codes still present in the O*NET-SOC 2019 label set; ``ONET_TO_OEWS_2021`` is the
explicit, hand-checked crosswalk for the latter.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class ClusterParams:
    emp_threshold: int = 300_000
    beta_tol: float = 0.10
    wage_tol: float = 0.20
    family: str = "minor"  # "minor" (xx-xx00) or "broad" (xx-xxx0)
    # Opt-in second pass (NOT in the spec): merge the non-anchor clusters left after the family pass
    # within the 2-digit major group under the same tolerances.  Off by default; the spec rule alone
    # yields ~450 clusters on OEWS May 2021, far above the ~120 target (see build provenance).
    stage2_major: bool = False


# O*NET-SOC 2019 codes (SOC 2010 lineage) that OEWS May 2021 reports under a merged SOC 2018 code.
ONET_TO_OEWS_2021: dict[str, str | None] = {
    "21-1011": "21-1018",  # Substance Abuse and Behavioral Disorder Counselors
    "21-1014": "21-1018",  # Mental Health Counselors
    "25-2055": "25-2052",  # Special Education Teachers, Kindergarten
    "25-2056": "25-2052",  # Special Education Teachers, Elementary School
    "25-9042": "25-9045",  # Teaching Assistants, Preschool... Except Special Education
    "25-9043": "25-9045",  # Teaching Assistants, Special Education
    "51-2022": "51-2028",  # Electrical and Electronic Equipment Assemblers
    "51-2023": "51-2028",  # Electromechanical Equipment Assemblers
    "53-1042": "53-1047",  # First-Line Supervisors of Helpers, Laborers, and Material Movers, Hand
    "53-1043": "53-1047",  # First-Line Supervisors of Material-Moving Machine and Vehicle Operators
    "53-1044": "53-1047",  # First-Line Supervisors of Passenger Attendants
    "45-3031": None,       # Fishing and Hunting Workers: not published in OEWS (self-employed)
}


def soc6(onet_code: str) -> str:
    """``11-1011.00`` -> ``11-1011``."""
    return onet_code.strip()[:7]


def major_group(occ_code: str) -> str:
    return occ_code[:2]


def family_key(occ_code: str, family: str = "minor") -> str:
    if family == "minor":
        return occ_code[:5] + "00"
    if family == "broad":
        return occ_code[:6] + "0"
    raise ValueError(family)


def map_to_oews(code6: str, oews_codes: set[str]) -> str | None:
    """Map a 6-digit SOC to the OEWS detailed code that carries it, or None if unpublished."""
    if code6 in oews_codes:
        return code6
    if code6 in ONET_TO_OEWS_2021:
        return ONET_TO_OEWS_2021[code6]
    broad = code6[:-1] + "0"
    if broad in oews_codes:
        return broad
    return None


def occupation_beta(occ_level: pl.DataFrame) -> pl.DataFrame:
    """Per O*NET code beta: mean of human and GPT-4 (dv) betas where both exist, else the one present."""
    df = occ_level.select(
        pl.col("O*NET-SOC Code").alias("onet_code"),
        pl.col("human_rating_beta").cast(pl.Float64, strict=False).alias("hb"),
        pl.col("dv_rating_beta").cast(pl.Float64, strict=False).alias("db"),
    )
    return df.with_columns(
        pl.when(pl.col("hb").is_not_null() & pl.col("db").is_not_null())
        .then((pl.col("hb") + pl.col("db")) / 2)
        .otherwise(pl.coalesce([pl.col("hb"), pl.col("db")]))
        .alias("beta")
    ).select("onet_code", "beta")


def build_clusters(occ: pl.DataFrame, params: ClusterParams | None = None) -> pl.DataFrame:
    """Assign ``cluster_id`` / ``cluster_title`` to every occupation.

    ``occ`` needs ``occ_code``, ``title``, ``emp_national``, ``wage_median_annual``, ``beta``
    (no nulls in the last three).  Returns a frame with ``occ_code``, ``cluster_id``,
    ``cluster_title``, ``cluster_size``, ``cluster_rule`` (``anchor`` / ``merged`` / ``single``).
    """
    params = params or ClusterParams()
    need = {"occ_code", "title", "emp_national", "wage_median_annual", "beta"}
    missing = need - set(occ.columns)
    if missing:
        raise ValueError(f"build_clusters: missing columns {sorted(missing)}")
    if occ.select(pl.col(["emp_national", "wage_median_annual", "beta"]).is_null().any()).to_numpy().any():
        raise ValueError("build_clusters: nulls in emp_national / wage_median_annual / beta")

    rows = occ.sort(["emp_national", "occ_code"], descending=[True, False]).to_dicts()
    clusters: list[dict] = []  # each: members(list of rows), emp, beta_w, wage_w, family, rule

    def add_cluster(row: dict, rule: str) -> dict:
        c = {"members": [row], "emp": row["emp_national"], "beta": row["beta"],
             "wage": row["wage_median_annual"], "family": family_key(row["occ_code"], params.family),
             "rule": rule}
        clusters.append(c)
        return c

    def attach(c: dict, row: dict) -> None:
        e0, e1 = c["emp"], row["emp_national"]
        tot = e0 + e1
        c["beta"] = (c["beta"] * e0 + row["beta"] * e1) / tot
        c["wage"] = (c["wage"] * e0 + row["wage_median_annual"] * e1) / tot
        c["emp"] = tot
        c["members"].append(row)

    for row in rows:
        if row["emp_national"] >= params.emp_threshold:
            add_cluster(row, "anchor")
            continue
        fam = family_key(row["occ_code"], params.family)
        target = None
        for c in clusters:
            if c["rule"] == "anchor" or c["family"] != fam:
                continue
            if major_group(c["members"][0]["occ_code"]) != major_group(row["occ_code"]):
                continue  # never across major groups (implied by family, asserted here)
            if abs(c["beta"] - row["beta"]) < params.beta_tol and \
                    abs(row["wage_median_annual"] / c["wage"] - 1.0) < params.wage_tol:
                target = c
                break
        if target is None:
            add_cluster(row, "merged")
        else:
            attach(target, row)

    if params.stage2_major:
        # Second pass: greedily merge non-anchor clusters within the major group (largest first).
        pool = sorted([c for c in clusters if c["rule"] != "anchor"], key=lambda c: -c["emp"])
        kept: list[dict] = [c for c in clusters if c["rule"] == "anchor"]
        merged2: list[dict] = []
        for c in pool:
            mg = major_group(c["members"][0]["occ_code"])
            target = None
            for k in merged2:
                if major_group(k["members"][0]["occ_code"]) != mg:
                    continue
                if abs(k["beta"] - c["beta"]) < params.beta_tol and abs(c["wage"] / k["wage"] - 1.0) < params.wage_tol:
                    target = k
                    break
            if target is None:
                c["rule"] = "merged"
                merged2.append(c)
            else:
                e0, e1 = target["emp"], c["emp"]
                target["beta"] = (target["beta"] * e0 + c["beta"] * e1) / (e0 + e1)
                target["wage"] = (target["wage"] * e0 + c["wage"] * e1) / (e0 + e1)
                target["emp"] = e0 + e1
                target["members"].extend(c["members"])
        clusters = kept + merged2

    # Deterministic ids: order clusters by the occ_code of their largest member.
    for c in clusters:
        c["members"].sort(key=lambda r: (-r["emp_national"], r["occ_code"]))
        c["lead"] = c["members"][0]["occ_code"]
    clusters.sort(key=lambda c: c["lead"])
    out = []
    for i, c in enumerate(clusters, start=1):
        cid = f"c{i:03d}"
        n = len(c["members"])
        lead_title = c["members"][0]["title"]
        title = lead_title if n == 1 else f"{lead_title} (+{n - 1})"
        rule = c["rule"] if n > 1 or c["rule"] == "anchor" else "single"
        for r in c["members"]:
            out.append({"occ_code": r["occ_code"], "cluster_id": cid, "cluster_title": title,
                        "cluster_size": n, "cluster_rule": rule})
    return pl.DataFrame(out).sort("occ_code")


def summarize(clusters: pl.DataFrame) -> dict:
    by = clusters.group_by("cluster_id").agg(pl.col("cluster_rule").first(), pl.col("cluster_size").first())
    return {
        "n_clusters": by.height,
        "anchors": by.filter(pl.col("cluster_rule") == "anchor").height,
        "merged": by.filter(pl.col("cluster_rule") == "merged").height,
        "singles_below_threshold": by.filter(pl.col("cluster_rule") == "single").height,
        "max_size": int(by["cluster_size"].max()),
    }

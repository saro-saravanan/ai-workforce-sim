"""Phase 2 cohort input tables (contracts §7): earnings deciles, education and age per occupation.

Built offline from the staged Phase 1 inputs; ``aiwsim.data.ingest.cps_asec`` replaces the
education and age tables (and adds the joint table) on a machine with an IPUMS API key.

* **Deciles (status D, derived).**  A lognormal is fitted per occupation through its OEWS annual
  wage percentiles (least squares of log wage on the normal quantiles of 0.10 / 0.25 / 0.50 / 0.75
  / 0.90).  ``#`` (top-coded, >= $208,000) and ``*`` are treated as missing exactly as in
  ``build.py``; an occupation with fewer than three usable percentiles keeps its own location but
  borrows the major group's dispersion (``fit_level = major_sigma``), and one with none takes the
  major group's parameters outright (``fit_level = major``).  National decile cutpoints come from
  the same fit through the OEWS "All Occupations" row; the share of an occupation's workers in
  each decile is the lognormal mass between consecutive cutpoints.
* **Education (tag E, estimate).**  O*NET Job Zone -> education mix through ``JOB_ZONE_EDUCATION``
  below.  Each OEWS occupation is matched to its O*NET titles through the GPTs-are-GPTs
  ``occupations_onet_bls_matched.csv`` file (the same title <-> SOC matching used for the Phase 1
  build); an OEWS code that carries several O*NET titles takes the equal-weight mixture of their
  Job Zone rows.  Unmatched occupations take the employment-weighted mean Job Zone mix of their
  major group (``jz_imputed = 1``).
* **Age (FIXTURE).**  The national employed age distribution (``AGE_NATIONAL``, approximate CPS
  2024, E) with the 16-24 share tilted multiplicatively by Job Zone (``JZ_TILT_16_24``) and the
  vector renormalised.  Replaced by the CPS ASEC ingest.
"""

from __future__ import annotations

import math

import numpy as np
import polars as pl

MISSING_WAGE_TOKENS = {"#", "*", "**", ""}

# OEWS percentile columns -> the cumulative probability they report.
PCT_COLS: dict[str, float] = {"A_PCT10": 0.10, "A_PCT25": 0.25, "A_MEDIAN": 0.50, "A_PCT75": 0.75, "A_PCT90": 0.90}

# Fewer usable percentiles than this -> borrow the major group's sigma (then its mu as well at 0).
MIN_POINTS_OWN_FIT = 3
SIGMA_FLOOR = 0.05

DECILES = list(range(1, 11))
EDUCATION_LEVELS = ["lt_hs", "hs", "some_college", "ba_plus"]
AGE_BANDS = ["16-24", "25-44", "45-54", "55+"]
JOB_ZONES = [1, 2, 3, 4, 5]

# ------------------------------------------------------------------------------------------------
# JOB_ZONE_EDUCATION: O*NET Job Zone -> share of workers by highest education (tag E).
#
# Rows are Job Zones 1..5 (1 = little or no preparation, 5 = extensive preparation); columns are
# EDUCATION_LEVELS = [lt_hs, hs, some_college, ba_plus] and each row sums to 1.  The rows are
# estimates chosen to be consistent with the O*NET Job Zone definitions (JZ1 "may require a high
# school diploma or GED"; JZ2 "usually require a high school diploma"; JZ3 "vocational training,
# related on-the-job experience, or an associate's degree"; JZ4 "usually a four-year bachelor's
# degree"; JZ5 "graduate school") and with the broad shape of the BLS educational-attainment-by-
# occupation tables; they are NOT fitted to microdata.  Replaced by the CPS ASEC ingest
# (aiwsim.data.ingest.cps_asec), which measures education per occupation directly.
# ------------------------------------------------------------------------------------------------
JOB_ZONE_EDUCATION: dict[int, tuple[float, float, float, float]] = {
    1: (0.25, 0.55, 0.15, 0.05),
    2: (0.10, 0.55, 0.25, 0.10),
    3: (0.03, 0.35, 0.42, 0.20),
    4: (0.01, 0.10, 0.24, 0.65),
    5: (0.00, 0.02, 0.08, 0.90),
}

# National employed age distribution, bands of contracts §7.  Approximate CPS 2024 (E): 16-24 about
# 12.5%, 25-44 about 44%, 45-54 about 20%, 55+ about 23.5%.  FIXTURE until the CPS ASEC ingest.
AGE_NATIONAL: dict[str, float] = {"16-24": 0.125, "25-44": 0.44, "45-54": 0.20, "55+": 0.235}

# Multiplicative tilt applied to the 16-24 share by Job Zone before renormalising (E): entry-level
# Job Zones employ more young workers, professional Job Zones fewer.
JZ_TILT_16_24: dict[int, float] = {1: 1.6, 2: 1.3, 3: 1.0, 4: 0.6, 5: 0.4}


# ------------------------------------------------------------------------------------------------
# normal helpers (no scipy in the sandbox)
# ------------------------------------------------------------------------------------------------
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Inverse standard normal CDF by bisection (accurate to ~1e-12; only called a few times)."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"p must be in (0, 1): {p}")
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


Z_PCT: dict[float, float] = {p: norm_ppf(p) for p in PCT_COLS.values()}
Z_DECILE: list[float] = [norm_ppf(k / 10.0) for k in range(1, 10)]


# ------------------------------------------------------------------------------------------------
# lognormal fit
# ------------------------------------------------------------------------------------------------
def fit_lognormal(points: list[tuple[float, float]], sigma: float | None = None) -> tuple[float, float]:
    """Least-squares fit of ``ln w = mu + sigma * z_p`` through ``(p, w)`` pairs.

    With ``sigma`` given, only ``mu`` is estimated (mean residual).  Returns ``(mu, sigma)``.
    """
    if not points:
        raise ValueError("no points")
    z = np.array([Z_PCT[p] if p in Z_PCT else norm_ppf(p) for p, _ in points])
    y = np.log(np.array([w for _, w in points], dtype=float))
    if sigma is not None:
        return float(np.mean(y - sigma * z)), float(sigma)
    if len(points) < 2:
        raise ValueError("need at least two points to fit sigma")
    zc, yc = z - z.mean(), y - y.mean()
    s = float((zc * yc).sum() / (zc * zc).sum())
    s = max(s, SIGMA_FLOOR)
    return float(y.mean() - s * z.mean()), s


def _usable_points(row: dict) -> list[tuple[float, float]]:
    pts = []
    for col, p in PCT_COLS.items():
        v = row.get(col)
        if v is None or str(v).strip() in MISSING_WAGE_TOKENS:
            continue
        pts.append((p, float(str(v).replace(",", ""))))
    return pts


def national_cutpoints(oews: pl.DataFrame) -> tuple[float, float, list[float]]:
    """(mu, sigma, nine decile cutpoints) from the OEWS ``00-0000`` All Occupations row."""
    tot = oews.filter(pl.col("OCC_CODE") == "00-0000").to_dicts()
    if len(tot) != 1:
        raise ValueError("OEWS All Occupations row (00-0000) not found exactly once")
    pts = _usable_points(tot[0])
    if len(pts) < MIN_POINTS_OWN_FIT:
        raise ValueError("All Occupations row has too few usable percentiles")
    mu, sigma = fit_lognormal(pts)
    return mu, sigma, [math.exp(mu + sigma * z) for z in Z_DECILE]


def fit_wage_params(oews: pl.DataFrame) -> pl.DataFrame:
    """Per detailed OEWS occupation: ``occ_code, mu, sigma, n_points, fit_level``."""
    maj: dict[str, tuple[float, float]] = {}
    for row in oews.filter(pl.col("O_GROUP") == "major").to_dicts():
        pts = _usable_points(row)
        if len(pts) >= 2:
            maj[row["OCC_CODE"][:2]] = fit_lognormal(pts)
    out = []
    for row in oews.filter(pl.col("O_GROUP") == "detailed").to_dicts():
        code = row["OCC_CODE"]
        pts = _usable_points(row)
        mg = maj.get(code[:2])
        if len(pts) >= MIN_POINTS_OWN_FIT:
            mu, sigma, level = *fit_lognormal(pts), "own"
        elif pts and mg is not None:
            mu, sigma, level = *fit_lognormal(pts, sigma=mg[1]), "major_sigma"
        elif mg is not None:
            mu, sigma, level = mg[0], mg[1], "major"
        else:  # pragma: no cover - every OEWS major group publishes percentiles
            raise ValueError(f"no wage percentiles for {code} and none for its major group")
        out.append({"occ_code": code, "mu": mu, "sigma": sigma, "n_points": len(pts), "fit_level": level})
    return pl.DataFrame(out)


def decile_shares(mu: float, sigma: float, cutpoints: list[float]) -> list[float]:
    """Lognormal(mu, sigma) mass in each of the ten bins delimited by the nine ``cutpoints``."""
    cdf = [norm_cdf((math.log(c) - mu) / sigma) for c in cutpoints]
    edges = [0.0, *cdf, 1.0]
    return [edges[i + 1] - edges[i] for i in range(10)]


# ------------------------------------------------------------------------------------------------
# Job Zone per occupation
# ------------------------------------------------------------------------------------------------
def _norm_title(col: str) -> pl.Expr:
    return pl.col(col).str.strip_chars().str.to_lowercase()


def job_zone_weights(basic_skills: pl.DataFrame, matched: pl.DataFrame, occ: pl.DataFrame) -> pl.DataFrame:
    """Per occupation the fraction of matched O*NET titles in each Job Zone (``jz1``..``jz5``).

    ``occ`` needs ``occ_code``, ``major_group`` and ``emp_national``.  Unmatched occupations get the
    employment-weighted mean of their major group and ``jz_imputed = 1``.  Also returns ``job_zone``
    (mean Job Zone) and ``n_onet`` (matched O*NET titles).
    """
    jz = basic_skills.select(_norm_title("Occupation").alias("k"),
                             pl.col("Job Zone").cast(pl.Int64, strict=False).alias("jz")).filter(
        pl.col("jz").is_in(JOB_ZONES)).unique(subset="k", keep="first")
    m = matched.filter(pl.col("OCC_CODE").is_not_null()).select(
        _norm_title("occupation").alias("k"), pl.col("OCC_CODE").alias("occ_code")).unique()
    j = m.join(jz, on="k", how="inner")
    per = j.group_by("occ_code").agg(
        *[(pl.col("jz") == z).mean().alias(f"jz{z}") for z in JOB_ZONES],
        pl.len().alias("n_onet"),
    )
    cols = [f"jz{z}" for z in JOB_ZONES]
    base = occ.select("occ_code", "major_group", pl.col("emp_national").cast(pl.Float64))
    df = base.join(per, on="occ_code", how="left")
    known = df.filter(pl.col("n_onet").is_not_null())
    mg = known.group_by("major_group").agg(
        *[((pl.col(c) * pl.col("emp_national")).sum() / pl.col("emp_national").sum()).alias(f"mg_{c}") for c in cols])
    df = df.join(mg, on="major_group", how="left")
    df = df.with_columns(pl.col("n_onet").is_null().cast(pl.Int64).alias("jz_imputed"))
    df = df.with_columns(*[pl.coalesce([pl.col(c), pl.col(f"mg_{c}")]).alias(c) for c in cols])
    if df.select(pl.any_horizontal(pl.col(cols).is_null().any())).item():  # pragma: no cover
        bad = df.filter(pl.any_horizontal(pl.col(cols).is_null()))["occ_code"].to_list()
        raise ValueError(f"no Job Zone information for major groups of {bad}")
    df = df.with_columns(
        pl.sum_horizontal([pl.col(f"jz{z}") * z for z in JOB_ZONES]).alias("job_zone"),
        pl.col("n_onet").fill_null(0),
    )
    return df.select("occ_code", *cols, "job_zone", "n_onet", "jz_imputed").sort("occ_code")


def age_rows_by_job_zone() -> dict[int, tuple[float, ...]]:
    """Age band shares per Job Zone: national vector with the 16-24 share tilted, renormalised."""
    out = {}
    for z, tilt in JZ_TILT_16_24.items():
        v = [AGE_NATIONAL[b] * (tilt if b == "16-24" else 1.0) for b in AGE_BANDS]
        s = sum(v)
        out[z] = tuple(x / s for x in v)
    return out


def _mix_rows(jzw: pl.DataFrame, rows: dict[int, tuple[float, ...]], names: list[str], value_col: str,
              tag: str) -> pl.DataFrame:
    w = jzw.select([f"jz{z}" for z in JOB_ZONES]).to_numpy()
    r = np.array([rows[z] for z in JOB_ZONES])
    shares = w @ r
    shares = shares / shares.sum(axis=1, keepdims=True)
    codes = jzw["occ_code"].to_list()
    recs = [{"occ_code": c, value_col: n, "share": float(shares[i, k])}
            for i, c in enumerate(codes) for k, n in enumerate(names)]
    return pl.DataFrame(recs).with_columns(pl.lit(tag).alias("source_tag")).join(
        jzw.select("occ_code", "job_zone", "jz_imputed"), on="occ_code", how="left")


# ------------------------------------------------------------------------------------------------
# build
# ------------------------------------------------------------------------------------------------
def build_cohort_tables(oews: pl.DataFrame, basic_skills: pl.DataFrame, matched: pl.DataFrame,
                        occ: pl.DataFrame, *, decile_tag: str, education_tag: str, age_tag: str) -> dict:
    """Return ``{"occ_decile", "national_deciles", "occ_education", "occ_age", "notes"}``.

    ``occ`` is the built ``occupations.csv`` frame (``occ_code``, ``major_group``, ``emp_national``);
    every output table covers exactly its ``occ_code`` set.
    """
    notes: dict[str, object] = {}
    codes = occ["occ_code"].to_list()

    # -- deciles
    mu_n, sigma_n, cuts = national_cutpoints(oews)
    nat = pl.DataFrame({"decile": DECILES, "lower_bound_annual": [0.0, *cuts]}).with_columns(
        pl.lit(decile_tag).alias("source_tag"))
    params = fit_wage_params(oews).filter(pl.col("occ_code").is_in(codes))
    missing = sorted(set(codes) - set(params["occ_code"]))
    if missing:
        raise ValueError(f"occupations without OEWS wage rows: {missing}")
    recs = []
    for r in params.to_dicts():
        for k, s in zip(DECILES, decile_shares(r["mu"], r["sigma"], cuts)):
            recs.append({"occ_code": r["occ_code"], "decile": k, "share": s})
    occ_decile = pl.DataFrame(recs).with_columns(pl.lit(decile_tag).alias("source_tag")).join(
        params.select("occ_code", "mu", "sigma", "n_points", "fit_level"), on="occ_code", how="left"
    ).sort(["occ_code", "decile"])
    emp = occ.select("occ_code", pl.col("emp_national").cast(pl.Float64))
    chk = occ_decile.join(emp, on="occ_code").group_by("decile").agg(
        ((pl.col("share") * pl.col("emp_national")).sum() / pl.col("emp_national").sum()).alias("s")).sort("decile")
    notes["national_fit"] = {"mu": mu_n, "sigma": sigma_n, "cutpoints": cuts}
    notes["decile_fit_levels"] = {k: int(v) for k, v in zip(*params["fit_level"].value_counts().sort("fit_level")
                                                             .to_dict().values())}
    notes["decile_employment_weighted_check"] = [round(float(x), 4) for x in chk["s"]]

    # -- Job Zone -> education, age
    jzw = job_zone_weights(basic_skills, matched, occ)
    occ_edu = _mix_rows(jzw, JOB_ZONE_EDUCATION, EDUCATION_LEVELS, "education", education_tag).sort(
        ["occ_code", "education"])
    occ_age = _mix_rows(jzw, age_rows_by_job_zone(), AGE_BANDS, "age_band", age_tag).sort(["occ_code", "age_band"])
    notes["job_zone_unmatched"] = {"count": int(jzw["jz_imputed"].sum()),
                                   "codes": jzw.filter(pl.col("jz_imputed") == 1)["occ_code"].to_list()}
    notes["job_zone_distribution_unweighted"] = {
        f"jz{z}": round(float(jzw[f"jz{z}"].mean()), 4) for z in JOB_ZONES}

    def weighted(df: pl.DataFrame, col: str) -> dict[str, float]:
        g = df.join(emp, on="occ_code").group_by(col).agg(
            ((pl.col("share") * pl.col("emp_national")).sum() / pl.col("emp_national").sum()).alias("s"))
        return {k: round(float(v), 4) for k, v in zip(g[col], g["s"])}

    notes["education_employment_weighted"] = {k: weighted(occ_edu, "education")[k] for k in EDUCATION_LEVELS}
    notes["age_employment_weighted"] = {k: weighted(occ_age, "age_band")[k] for k in AGE_BANDS}
    return {"occ_decile": occ_decile, "national_deciles": nat, "occ_education": occ_edu, "occ_age": occ_age,
            "notes": notes}

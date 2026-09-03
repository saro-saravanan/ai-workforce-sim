"""Tables built from files under ``data/external/`` (fetched by the external-data workflow on a GitHub runner because the
build environment cannot reach bls.gov or bea.gov). Each function returns ``None`` when its files are absent, and the
build falls back to the Phase 1 fixtures, so a clean clone still builds.

* BLS OEWS May 2025: ``natsector_M2025_dl.xlsx`` (occupation x NAICS sector), ``state_M2025_dl.xlsx`` (occupation x state),
  ``national_M2025_dl.xlsx`` (national employment and wages).
* BEA input-output use table (summary level, Supply-Use framework): ``USE_TABLE_FILE`` names the spreadsheet; the ingest
  ``bea_use_table`` derives labour-cost shares, consumption shares and the direct-requirements matrix by 20 NAICS sectors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from .fixtures import SECTORS_20, naics_to_sector
from .ingest._common import read_excel_bytes
from .ingest.oews import (
    _num,
    build_occ_sector,
    build_occ_state,
)

OEWS_VINTAGE_DEFAULT = "May 2025"

# Sector parameters that the BEA use table supplies when present; until then authors' estimates (tag E), by NAICS sector.
# labor_cost_share: compensation of employees / gross output (BEA GDP-by-industry orders of magnitude); consumption_share:
# personal consumption expenditure by producing sector (BEA PCE bridge, rough); demand_elasticity: price elasticity of sector
# demand (E, literature ranges 0.2-1.2, the single-sector fixture used 0.8); friction: Bass adoption friction phi_s (1.0 = the
# calibrated single-sector speed; the BTOS sector cuts are not yet used to differentiate it, so 1.0 everywhere).
SECTOR_E: dict[str, dict[str, float]] = {
    "11": {"labor_cost_share": 0.20, "consumption_share": 0.010, "demand_elasticity": 0.5},
    "21": {"labor_cost_share": 0.15, "consumption_share": 0.010, "demand_elasticity": 0.5},
    "22": {"labor_cost_share": 0.15, "consumption_share": 0.030, "demand_elasticity": 0.3},
    "23": {"labor_cost_share": 0.35, "consumption_share": 0.010, "demand_elasticity": 0.8},
    "31-33": {"labor_cost_share": 0.20, "consumption_share": 0.220, "demand_elasticity": 1.0},
    "42": {"labor_cost_share": 0.40, "consumption_share": 0.050, "demand_elasticity": 0.8},
    "44-45": {"labor_cost_share": 0.45, "consumption_share": 0.100, "demand_elasticity": 0.8},
    "48-49": {"labor_cost_share": 0.35, "consumption_share": 0.040, "demand_elasticity": 0.8},
    "51": {"labor_cost_share": 0.25, "consumption_share": 0.050, "demand_elasticity": 1.2},
    "52": {"labor_cost_share": 0.30, "consumption_share": 0.090, "demand_elasticity": 0.8},
    "53": {"labor_cost_share": 0.10, "consumption_share": 0.160, "demand_elasticity": 0.5},
    "54": {"labor_cost_share": 0.50, "consumption_share": 0.030, "demand_elasticity": 1.0},
    "55": {"labor_cost_share": 0.60, "consumption_share": 0.000, "demand_elasticity": 0.6},
    "56": {"labor_cost_share": 0.55, "consumption_share": 0.020, "demand_elasticity": 0.9},
    "61": {"labor_cost_share": 0.65, "consumption_share": 0.020, "demand_elasticity": 0.4},
    "62": {"labor_cost_share": 0.55, "consumption_share": 0.160, "demand_elasticity": 0.4},
    "71": {"labor_cost_share": 0.40, "consumption_share": 0.020, "demand_elasticity": 1.0},
    "72": {"labor_cost_share": 0.35, "consumption_share": 0.060, "demand_elasticity": 0.9},
    "81": {"labor_cost_share": 0.45, "consumption_share": 0.040, "demand_elasticity": 0.8},
    "92": {"labor_cost_share": 0.60, "consumption_share": 0.020, "demand_elasticity": 0.2},
}


def _ext(root: Path) -> Path:
    return Path(root) / "data" / "external"


def _read_xlsx(path: Path) -> pl.DataFrame:
    df = read_excel_bytes(path.read_bytes())
    df.columns = [c.strip().upper().lstrip("﻿") for c in df.columns]
    return df


def oews_external(root: Path) -> dict[str, Any] | None:
    """The OEWS-derived tables when the three spreadsheets are present under data/external/bls."""
    d = _ext(root) / "bls"
    files = {k: sorted(d.glob(f"{v}_M20*_dl.xlsx")) for k, v in (("sector", "natsector"), ("state", "state"), ("national", "national"))}
    if not all(files.values()):
        return None
    vintage = OEWS_VINTAGE_DEFAULT
    m = files["national"][-1].name
    if "_M20" in m:
        vintage = f"May {m.split('_M')[1][:4]}"
    ind = _read_xlsx(files["sector"][-1]); st = _read_xlsx(files["state"][-1]); nat = _read_xlsx(files["national"][-1])
    occ_sector, info = build_occ_sector(ind)
    occ_state, states = build_occ_state(st)
    tag = f"real:OEWS_{vintage.replace(' ', '')}"
    occ_sector = occ_sector.with_columns(pl.lit(tag + "_industry").alias("source_tag"))
    occ_state = occ_state.with_columns(pl.lit(tag + "_state").alias("source_tag"))
    states = states.with_columns(pl.lit(tag + "_state").alias("source_tag"))
    det = nat.filter(pl.col("O_GROUP") == "detailed").select(
        pl.col("OCC_CODE").alias("occ_code"), _num("TOT_EMP").cast(pl.Int64).alias("emp_national"),
        _num("A_MEAN").alias("wage_mean_annual"), _num("A_PCT10").alias("wage_p10_annual"), _num("A_MEDIAN").alias("wage_median_annual"))
    return {"occ_sector": occ_sector, "occ_state": occ_state, "states": states, "national": det, "vintage": vintage, "info": info,
            "files": {k: str(v[-1].relative_to(root)) for k, v in files.items()}}


def refresh_occupations_frame(occ: pl.DataFrame, det: pl.DataFrame, vintage: str) -> tuple[pl.DataFrame, int]:
    """Replace employment and wages in the occupations frame with the OEWS vintage's; occupations missing there keep their values."""
    cols = ["emp_national", "wage_mean_annual", "wage_p10_annual", "wage_median_annual"]
    new = occ.join(det.rename({c: c + "_new" for c in cols}), on="occ_code", how="left")
    n_missing = new.filter(pl.col("emp_national_new").is_null()).height
    exprs = [pl.when(pl.col(c + "_new").is_not_null()).then(pl.col(c + "_new")).otherwise(pl.col(c)).alias(c) for c in cols]
    out = new.with_columns(exprs).drop([c + "_new" for c in cols])
    out = out.with_columns(pl.col("source_tag").cast(pl.Utf8).str.replace("OEWS_May2021", f"OEWS_{vintage.replace(' ', '')}"))
    return out.select(occ.columns), n_missing


def bea_use_table(root: Path) -> dict[str, Any] | None:
    """Sector parameters and the direct-requirements matrix from the BEA summary use table, when the file is present."""
    d = _ext(root) / "bea"
    marker = d / "USE_TABLE_FILE"
    if not marker.exists():
        return None
    f = d / marker.read_text().strip()
    if not f.exists():
        return None
    from .ingest.bea_io import (  # local import: only needed when the file exists
        parse_use_table,
        parse_use_table_api,
    )
    if f.suffix.lower() == ".json":
        return parse_use_table_api(f)
    if f.suffix.lower() in (".xlsx", ".xls"):
        return parse_use_table(f)
    return None


def sectors_table(bea: dict[str, Any] | None) -> tuple[pl.DataFrame, str]:
    """The 20-sector table: tradable from the fixture list, the rest from BEA when present, else the E estimates."""
    rows = []
    for s in SECTORS_20:
        code = s["sector_code"]; e = SECTOR_E[code]
        lcs = e["labor_cost_share"]; cs = e["consumption_share"]; tag = "E (authors' estimate; BEA use table pending)"
        if bea and code in bea.get("labor_cost_share", {}):
            lcs = float(bea["labor_cost_share"][code]); cs = float(bea["consumption_share"].get(code, cs)); tag = f"real:BEA_use_{bea.get('year', '')} (labor_cost_share, consumption_share); E (elasticity, friction)"
        rows.append({"sector_code": code, "title": s["title"], "labor_cost_share": round(lcs, 4), "demand_elasticity": e["demand_elasticity"],
                     "tradable": int(s["tradable"]), "friction": 1.0, "consumption_share": cs, "source_tag": tag})
    df = pl.DataFrame(rows)
    tot = float(df["consumption_share"].sum())
    df = df.with_columns((pl.col("consumption_share") / tot).round(5).alias("consumption_share"))
    return df, ("real (BEA)" if bea else "partial (20 sectors; E estimates until the BEA use table is fetched)")


def io_direct_requirements(bea: dict[str, Any] | None) -> pl.DataFrame | None:
    """Direct requirements a_ij (intermediate use of sector i's output per dollar of sector j's output), 20 x 20, when BEA is present."""
    if not bea or "direct_requirements" not in bea:
        return None
    codes = [s["sector_code"] for s in SECTORS_20]
    A = bea["direct_requirements"]
    rows = [{"from_sector": i, **{j: float(A.get(i, {}).get(j, 0.0)) for j in codes}} for i in codes]
    return pl.DataFrame(rows)


def complete_occ_sector(occ_sector: pl.DataFrame, occ: pl.DataFrame) -> pl.DataFrame:
    """Occupations the OEWS industry file does not publish (legislators, a few small ones) take the employment-weighted sector shares of their
    major group, tagged as derived; every occupation then has shares that sum to one."""
    have = set(occ_sector["occ_code"].to_list())
    missing = [c for c in occ["occ_code"].to_list() if c not in have]
    if not missing:
        return occ_sector
    emp = occ.select("occ_code", pl.col("emp_national").cast(pl.Float64).alias("emp"), pl.col("occ_code").str.slice(0, 2).alias("mg"))
    w = occ_sector.join(emp, on="occ_code", how="inner").with_columns((pl.col("emp_share").cast(pl.Float64) * pl.col("emp")).alias("h"))
    mg_sh = w.group_by(["mg", "sector_code"]).agg(pl.col("h").sum()).with_columns((pl.col("h") / pl.col("h").sum().over("mg")).alias("emp_share"))
    rows = []
    for c in missing:
        mg = c[:2]; part = mg_sh.filter(pl.col("mg") == mg)
        if part.height == 0:
            part = w.group_by("sector_code").agg(pl.col("h").sum()).with_columns((pl.col("h") / pl.col("h").sum()).alias("emp_share"))
        rows += [{"occ_code": c, "sector_code": r["sector_code"], "emp_share": float(r["emp_share"]), "source_tag": "derived: major-group average (not published by OEWS by industry)"} for r in part.iter_rows(named=True)]
    return pl.concat([occ_sector, pl.DataFrame(rows).select(occ_sector.columns)], how="vertical_relaxed").sort(["occ_code", "sector_code"])


def complete_occ_state(occ_state: pl.DataFrame, states: pl.DataFrame, occ: pl.DataFrame) -> pl.DataFrame:
    """State rows renormalized so each occupation's states sum to its national employment (suppressed cells are missing from the file), and
    occupations without any state row allocated by the states' shares of total employment (largest-remainder rounding)."""
    from .fixtures import allocate_integer
    nat = {r["occ_code"]: int(r["emp_national"]) for r in occ.select("occ_code", pl.col("emp_national").cast(pl.Int64)).iter_rows(named=True)}
    fips = states["fips"].to_list(); tot = [float(x) for x in states["emp_total"].cast(pl.Float64).to_list()]; st_share = [x / max(sum(tot), 1.0) for x in tot]
    out_rows: list[dict[str, Any]] = []
    by_occ: dict[str, list[tuple[str, float]]] = {}
    for r in occ_state.iter_rows(named=True):
        by_occ.setdefault(r["occ_code"], []).append((r["fips"], float(r["emp"] or 0.0)))
    tag = occ_state["source_tag"][0] if occ_state.height else "real"
    for code, n in nat.items():
        rows = by_occ.get(code)
        if rows and sum(e for _, e in rows) > 0:
            s = sum(e for _, e in rows); alloc = allocate_integer(n, [e / s for _, e in rows])
            out_rows += [{"occ_code": code, "fips": f, "emp": a, "source_tag": tag + "; renormalized to national"} for (f, _), a in zip(rows, alloc, strict=True)]
        else:
            alloc = allocate_integer(n, st_share)
            out_rows += [{"occ_code": code, "fips": f, "emp": a, "source_tag": "derived: national employment by state employment share (no state rows published)"} for f, a in zip(fips, alloc, strict=True)]
    return pl.DataFrame(out_rows).sort(["occ_code", "fips"])


__all__ = ["SECTOR_E", "bea_use_table", "io_direct_requirements", "naics_to_sector", "oews_external", "refresh_occupations_frame", "sectors_table"]

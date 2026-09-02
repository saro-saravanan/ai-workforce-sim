"""Regional inputs (contracts §11): regions, members, occupation × region, trade weights, actors, releases, value chain."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

from .inputs import Inputs

REGION_ORDER = ["US", "EU", "UK", "CN", "JP", "KR", "IN", "TW", "SG", "RoA"]
# E: baseline real GDP growth per year in the frozen-AI counterfactual (IMF WEO long-run, approximate)
BASELINE_GDP_GROWTH = {"US": 0.02, "EU": 0.013, "UK": 0.015, "CN": 0.04, "JP": 0.007, "KR": 0.02, "IN": 0.06, "TW": 0.025, "SG": 0.025, "RoA": 0.045}


@dataclass
class Region:
    region_id: str
    name: str
    population: float
    gdp_bn: float
    employment_total: float
    wage_level: float
    emp_growth10: float
    import_share: float
    epl_multiplier: float
    avail_delay_q: int
    frontier_lag_q: int
    chi_high_risk: float
    regime: str
    data_center_share: float
    spillover_weight_us: float
    emp0: np.ndarray            # [n_occ] heads
    wage_mean: np.ndarray       # [n_occ] annual USD
    growth10: np.ndarray | None = None   # [n_occ] baseline 10-year growth by occupation (U.S. pattern shifted to the region mean)
    source_tag: str = ""


@dataclass
class Actor:
    actor_id: str
    name: str
    region_id: str
    role: str
    posture: str
    frontier_lag_q: float
    releases_per_year: float
    price: float | None
    avail: dict[str, float]


@dataclass
class RegionalInputs:
    regions: dict[str, Region]
    order: list[str]
    members: list[dict]                 # region_members rows
    trade: np.ndarray                   # [n_r, n_r] weight[from, to]
    actors: list[Actor]
    releases: list[dict]
    value_chain: dict[str, dict]        # stage -> {share, allocation, fixed: {region: share}}
    data_flags: dict[str, str] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.order)


def load_regional(root: Path, inp: Inputs) -> RegionalInputs | None:
    d = root / "data" / "processed" / "regions"
    if not (d / "regions.csv").exists():
        return None
    occ_idx = {c: i for i, c in enumerate(inp.occ_codes)}
    rg = pl.read_csv(d / "regions.csv", schema_overrides={"region_id": pl.Utf8, "regime": pl.Utf8})
    orow = pl.read_csv(d / "occ_region.csv", schema_overrides={"occ_code": pl.Utf8, "region_id": pl.Utf8})
    emp: dict[str, np.ndarray] = {}; wage: dict[str, np.ndarray] = {}
    for r in orow.iter_rows(named=True):
        rid = r["region_id"]
        if rid not in emp:
            emp[rid] = np.zeros(inp.n_occ); wage[rid] = inp.wage_mean.copy()
        i = occ_idx.get(r["occ_code"])
        if i is not None:
            emp[rid][i] = float(r["emp"]); wage[rid][i] = float(r["wage_mean_annual_usd"])
    regions: dict[str, Region] = {}
    for r in rg.iter_rows(named=True):
        rid = r["region_id"]
        if rid == "US":
            e, w = inp.emp0.copy(), inp.wage_mean.copy()
        else:
            e, w = emp.get(rid, np.zeros(inp.n_occ)), wage.get(rid, inp.wage_mean.copy())
        us_mean = float((inp.growth10 * inp.emp0).sum() / inp.emp0.sum())
        g10 = inp.growth10.copy() if rid == "US" else inp.growth10 + (float(r["emp_growth_10y"]) - us_mean)
        regions[rid] = Region(
            region_id=rid, name=r["name"], population=float(r["population"]), gdp_bn=float(r["gdp_bn_usd"]),
            employment_total=float(r["employment_total"]), wage_level=float(r["wage_level_rel_us"]), emp_growth10=float(r["emp_growth_10y"]),
            import_share=float(r["import_share"]), epl_multiplier=float(r["epl_multiplier"]), avail_delay_q=int(r["avail_delay_quarters"]),
            frontier_lag_q=int(r["frontier_lag_quarters"]), chi_high_risk=float(r["compliance_premium_high_risk"]), regime=str(r["regime"]),
            data_center_share=float(r["data_center_share"]), spillover_weight_us=float(r["spillover_weight_us"]), emp0=e, wage_mean=w,
            growth10=g10, source_tag=str(r.get("source_tag", "")))
    # consistency guard for fixture wages (spec §16): the wage bill cannot exceed ~55% of GDP; scale wages down when it does
    for rid, rg in regions.items():
        bill_bn = float((rg.emp0 * rg.wage_mean).sum()) / 1e9
        cap_bn = 0.55 * rg.gdp_bn
        if bill_bn > cap_bn > 0:
            rg.wage_mean = rg.wage_mean * (cap_bn / bill_bn)
            rg.wage_level = rg.wage_level * (cap_bn / bill_bn)
            rg.source_tag = (rg.source_tag + "; wages scaled to 55% of GDP for consistency").strip("; ")
    order = [x for x in REGION_ORDER if x in regions] + [x for x in regions if x not in REGION_ORDER]
    ridx = {x: i for i, x in enumerate(order)}
    trade = np.eye(len(order))
    tw = d / "trade_weights.csv"
    if tw.exists():
        trade = np.zeros((len(order), len(order)))
        for r in pl.read_csv(tw, schema_overrides={"region_from": pl.Utf8, "region_to": pl.Utf8}).iter_rows(named=True):
            if r["region_from"] in ridx and r["region_to"] in ridx:
                trade[ridx[r["region_from"]], ridx[r["region_to"]]] = float(r["weight"])
    actors: list[Actor] = []
    af = d / "actors.csv"
    if af.exists():
        for r in pl.read_csv(af, schema_overrides={"actor_id": pl.Utf8, "region_id": pl.Utf8, "role": pl.Utf8, "weights_posture": pl.Utf8}, null_values=["", "null", "NA"]).iter_rows(named=True):
            actors.append(Actor(actor_id=r["actor_id"], name=r["name"], region_id=r["region_id"], role=r["role"], posture=r["weights_posture"],
                                frontier_lag_q=float(r["frontier_lag_quarters"] or 0), releases_per_year=float(r["releases_per_year"] or 2),
                                price=(None if r.get("price_frontier_usd_per_mtok") in (None, "") else float(r["price_frontier_usd_per_mtok"])),
                                avail={x: float(r.get(f"avail_{x}", 1.0) or 0.0) for x in order}))
    releases: list[dict] = []
    rf = d / "actor_releases.csv"
    if rf.exists():
        releases = pl.read_csv(rf, schema_overrides={"actor_id": pl.Utf8, "model": pl.Utf8, "date": pl.Utf8}, null_values=["", "null", "NA"]).to_dicts()
    vc: dict[str, dict] = {}
    vf = d / "value_chain.csv"
    if vf.exists():
        for r in pl.read_csv(vf, schema_overrides={"stage": pl.Utf8, "allocation": pl.Utf8}).iter_rows(named=True):
            vc[r["stage"]] = {"share": float(r["share_of_spend"]), "allocation": r["allocation"],
                              "fixed": {k[6:]: float(r[k] or 0) for k in r if k.startswith("fixed_") and r[k] not in (None, "")}}
    members: list[dict] = []
    mf = d / "region_members.csv"
    if mf.exists():
        members = pl.read_csv(mf, schema_overrides={"iso3": pl.Utf8, "region_id": pl.Utf8, "name": pl.Utf8}).fill_null("").to_dicts()
    flags = {k: v for k, v in inp.data_flags.items() if k.startswith("regions/")}
    return RegionalInputs(regions=regions, order=order, members=members, trade=trade, actors=actors, releases=releases, value_chain=vc, data_flags=flags)


def wage_tier(wage_level: float) -> float:
    """Task-layer wage tier used for the profitability test (spec §2.4): 1.0, 0.25, or 0.1 of U.S. wages."""
    if wage_level >= 0.5:
        return 1.0
    if wage_level >= 0.2:
        return 0.25
    return 0.1

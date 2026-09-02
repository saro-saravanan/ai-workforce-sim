"""Runtime inputs for the application layer (spec v0.3 §A.3–A.5): embodiment classes, approval paths,
production shares, catalogue, and the self-employed / platform stock by region and occupation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

from .inputs import CHANNELS, Inputs

CLASSES = ["driving", "manip", "fixed", "aerial"]
CHANNEL_OF_CLASS = {c: CHANNELS.index(f"emb_{c}") for c in CLASSES}     # class -> task channel index
APPROVAL_STATES = ("frozen", "baseline", "accelerated", "moratorium")


@dataclass
class EmbodimentClass:
    cls: str
    a_emb: float; theta_lo: float; theta_hi: float; tau_months: float; saturation: float
    unit_price_2025: float; lifetime_years: float; opex_ratio: float; utilization: float; task_units_per_hour: float
    g_max_per_year: float; cum_production_2025: float; adjacent_jobs_per_unit: float
    stock_2024: dict[str, float] = field(default_factory=dict)
    prod_share: dict[str, float] = field(default_factory=dict)


@dataclass
class Application:
    app_id: str; name: str; family: str; classes: list[str]; platform: bool; occ_codes: list[str]; regions_first: list[str]
    anchor: str = ""; constraints: str = ""; provisional_profitable: str = ""; provisional_deployed50: str = ""


@dataclass
class ContentCategory:
    cat_id: str; name: str; occ_idx: np.ndarray; us_consumption_bn: float; eta: float; ratio0: float; alpha0: float; intermediate: bool; anchor: str = ""
    share0: float = 0.02


@dataclass
class ServicesTrade:
    exporter: str; category: str; export_bn: float; fte_per_musd: float; occ_idx: np.ndarray; importers: dict[str, float]; anchor: str = ""


@dataclass
class AppInputs:
    classes: dict[str, EmbodimentClass]
    apps: list[Application]
    approval: dict[tuple[str, str], tuple[int, int, float, float]]      # (cls, region) -> (start_year, full_year, j0, j_full)
    self_fte: dict[str, np.ndarray]                                      # region -> [n_occ] self-employed FTE
    platform_share: dict[str, np.ndarray]                                # region -> [n_occ] share of that FTE that is platform-mediated
    categories: list[ContentCategory] = field(default_factory=list)      # spec §A.4
    trade: list[ServicesTrade] = field(default_factory=list)             # spec §A.5.3
    data_flags: dict[str, str] = field(default_factory=dict)

    def occ_mask(self, app: Application, inp: Inputs) -> np.ndarray:
        """Boolean [n_occ] mask of an application's target occupations ('*manip' = every occupation with manipulation task-hours; '*cat' = its category's)."""
        if app.occ_codes == ["*manip"]:
            m = np.zeros(inp.n_occ, dtype=bool)
            np.add.at(m, inp.task_occ[inp.task_channel == CHANNEL_OF_CLASS["manip"]], True)
            return m
        if app.occ_codes == ["*cat"]:
            m = np.zeros(inp.n_occ, dtype=bool)
            for c in self.categories:
                if c.cat_id in app.classes:
                    m[c.occ_idx] = True
            return m
        codes = set(app.occ_codes)
        return np.array([c in codes for c in inp.occ_codes])


def approval_path(spec: tuple[int, int, float, float], quarters: list[str], state: str = "baseline",
                  shocks: list[dict] | None = None, cls: str = "", region: str = "") -> np.ndarray:
    """J_{c,r,t} for the quarters (spec §A.3.4): linear ramp under the lever state, then dated shocks."""
    start, full, j0, jf = spec
    if state == "accelerated":
        full = full - 5; jf = min(1.0, jf + 0.15)
    yrs = np.array([int(q[:4]) + (int(q[-1]) - 1) / 4.0 for q in quarters])
    if state == "frozen":
        J = np.full(len(quarters), j0)
    else:
        J = np.where(yrs < start, j0, np.where(yrs >= full, jf, j0 + (jf - j0) * (yrs - start) / max(full - start, 0.25)))
    if state == "moratorium":
        J = np.where(yrs >= 2026.0, 0.0, J)
    for s in shocks or []:
        if s.get("type") != "approval_change" or s.get("at") not in quarters:
            continue
        if s.get("cls", cls) != cls or (s.get("region") not in (None, "", region)):
            continue
        t0 = quarters.index(s["at"]); new_full = int(s.get("full_year", full)); new_jf = float(s.get("j_full", jf))
        tail = yrs[t0:]
        J[t0:] = np.where(tail >= new_full, new_jf, J[t0] + (new_jf - J[t0]) * (tail - tail[0]) / max(new_full - tail[0], 0.25))
    return np.clip(J, 0.0, 1.0)


def load_applications(root: Path, inp: Inputs, region_ids: list[str] | None = None) -> AppInputs | None:
    d = root / "data" / "processed" / "applications"
    if not (d / "embodiment_classes.csv").exists():
        return None
    ec = pl.read_csv(d / "embodiment_classes.csv", schema_overrides={"cls": pl.Utf8})
    classes: dict[str, EmbodimentClass] = {}
    for r in ec.iter_rows(named=True):
        regs = sorted({k[len("stock_2024_"):] for k in r if k.startswith("stock_2024_")})
        classes[r["cls"]] = EmbodimentClass(
            cls=r["cls"], a_emb=float(r["a_emb"]), theta_lo=float(r["theta_lo"]), theta_hi=float(r["theta_hi"]), tau_months=float(r["tau_months"]),
            saturation=float(r["saturation"]), unit_price_2025=float(r["unit_price_2025_usd"]), lifetime_years=float(r["lifetime_years"]),
            opex_ratio=float(r["opex_ratio"]), utilization=float(r["utilization"]), task_units_per_hour=float(r["task_units_per_hour"]),
            g_max_per_year=float(r["g_max_per_year"]), cum_production_2025=float(r["cum_production_2025"]), adjacent_jobs_per_unit=float(r["adjacent_jobs_per_unit"]),
            stock_2024={x: float(r[f"stock_2024_{x}"] or 0.0) for x in regs}, prod_share={x: float(r[f"prod_share_{x}"] or 0.0) for x in regs})
    apps: list[Application] = []
    for r in pl.read_csv(d / "applications.csv", schema_overrides={"app_id": pl.Utf8, "occ_codes": pl.Utf8, "cls": pl.Utf8}).fill_null("").iter_rows(named=True):
        apps.append(Application(app_id=r["app_id"], name=r["name"], family=r["family"], classes=[c for c in str(r["cls"]).split(";") if c],
                                platform=bool(int(r["platform"] or 0)), occ_codes=[c for c in str(r["occ_codes"]).split(";") if c],
                                regions_first=[c for c in str(r["regions_first"]).split(";") if c], anchor=str(r.get("anchor", "")),
                                constraints=str(r.get("constraints", "")), provisional_profitable=str(r.get("provisional_profitable", "")),
                                provisional_deployed50=str(r.get("provisional_deployed50", ""))))
    approval: dict[tuple[str, str], tuple[int, int, float, float]] = {}
    for r in pl.read_csv(d / "approval_paths.csv", schema_overrides={"cls": pl.Utf8, "region_id": pl.Utf8}).iter_rows(named=True):
        approval[(r["cls"], r["region_id"])] = (int(r["start_year"]), int(r["full_year"]), float(r["j0"]), float(r["j_full"]))
    occ_idx = {c: i for i, c in enumerate(inp.occ_codes)}
    self_fte: dict[str, np.ndarray] = {}; plat: dict[str, np.ndarray] = {}
    for r in pl.read_csv(d / "self_employed.csv", schema_overrides={"occ_code": pl.Utf8, "region_id": pl.Utf8}).iter_rows(named=True):
        rid = r["region_id"]
        if region_ids is not None and rid not in region_ids:
            continue
        i = occ_idx.get(r["occ_code"])
        if i is None:
            continue
        self_fte.setdefault(rid, np.zeros(inp.n_occ)); plat.setdefault(rid, np.zeros(inp.n_occ))
        self_fte[rid][i] = float(r["fte"]); plat[rid][i] = float(r["platform_share"])
    cats: list[ContentCategory] = []
    cf = d / "content_categories.csv"
    if cf.exists():
        for r in pl.read_csv(cf, schema_overrides={"cat_id": pl.Utf8, "occ_codes": pl.Utf8}).fill_null("").iter_rows(named=True):
            idx = np.array([occ_idx[c] for c in str(r["occ_codes"]).split(";") if c in occ_idx], dtype=np.int64)
            cats.append(ContentCategory(cat_id=r["cat_id"], name=r["name"], occ_idx=idx, us_consumption_bn=float(r["us_consumption_bn"]), eta=float(r["eta"]),
                                        ratio0=float(r["ratio0"]), alpha0=float(r["alpha0"]), intermediate=bool(int(r["intermediate"] or 0)), anchor=str(r.get("anchor", "")),
                                        share0=float(r.get("share0", 0.02) or 0.02)))
    trade: list[ServicesTrade] = []
    tf = d / "services_trade.csv"
    if tf.exists():
        for r in pl.read_csv(tf, schema_overrides={"exporter": pl.Utf8, "category": pl.Utf8, "occ_codes": pl.Utf8, "importers": pl.Utf8}).fill_null("").iter_rows(named=True):
            idx = np.array([occ_idx[c] for c in str(r["occ_codes"]).split(";") if c in occ_idx], dtype=np.int64)
            imp = {kv.split(":")[0]: float(kv.split(":")[1]) for kv in str(r["importers"]).split(";") if ":" in kv}
            trade.append(ServicesTrade(exporter=r["exporter"], category=r["category"], export_bn=float(r["export_bn"]), fte_per_musd=float(r["fte_per_musd"]),
                                       occ_idx=idx, importers=imp, anchor=str(r.get("anchor", ""))))
    flags = {k: v for k, v in inp.data_flags.items() if k.startswith("applications/")}
    return AppInputs(classes=classes, apps=apps, approval=approval, self_fte=self_fte, platform_share=plat, categories=cats, trade=trade, data_flags=flags)

"""Load the canonical input tables (docs/contracts.md §1) into arrays."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

LABELS = {"E0": 0, "E1": 1, "E2": 2}
MODALITIES = ["software", "other_cognitive", "interpersonal", "physical"]
USE_CASES = ["unregulated", "transparency", "high_risk"]


@dataclass
class Inputs:
    root: Path
    # occupations
    occ_codes: list[str]
    occ_titles: list[str]
    major_group: list[str]
    cluster_id: list[str]
    emp0: np.ndarray            # heads, national
    wage_mean: np.ndarray       # annual $
    wage_p10: np.ndarray        # annual $
    growth10: np.ndarray        # fraction over 10 years (baseline)
    # tasks
    task_ids: np.ndarray
    task_occ: np.ndarray        # int index into occupations
    task_weight: np.ndarray     # sums to 1 within occupation
    task_label: np.ndarray      # 0/1/2
    task_beta: np.ndarray
    task_modality: np.ndarray   # int index into MODALITIES
    task_presence: np.ndarray
    task_use_case: np.ndarray   # int index into USE_CASES
    task_consequence: np.ndarray
    # sectors
    sector_codes: list[str]
    labor_cost_share: np.ndarray
    demand_elasticity: np.ndarray
    tradable: np.ndarray
    sector_friction: np.ndarray
    consumption_share: np.ndarray
    occ_sector: np.ndarray      # [n_occ, n_sec] share of occupation employment
    # states
    state_fips: list[str]
    state_names: list[str]
    state_abbrev: list[str]
    occ_state: np.ndarray       # [n_occ, n_state] heads
    # series
    btos: pl.DataFrame | None
    metr: pl.DataFrame | None
    capex: pl.DataFrame | None
    data_flags: dict[str, str] = field(default_factory=dict)
    data_version: str = ""

    @property
    def n_occ(self) -> int:
        return len(self.occ_codes)

    @property
    def n_tasks(self) -> int:
        return len(self.task_ids)

    @property
    def n_sec(self) -> int:
        return len(self.sector_codes)

    @property
    def occ_exposure_beta(self) -> np.ndarray:
        out = np.zeros(self.n_occ)
        np.add.at(out, self.task_occ, self.task_weight * self.task_beta)
        return out


def _hash_dir(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(d.rglob("*")):
        if f.is_file() and f.suffix in (".csv", ".yaml", ".yml", ".json", ".geojson"):
            h.update(f.relative_to(d).as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:12]


def _flags(prov_dir: Path) -> dict[str, str]:
    flags: dict[str, str] = {}
    if prov_dir.exists():
        for f in sorted(prov_dir.glob("*.json")):
            try:
                d = json.loads(f.read_text())
                flags[d.get("table", f.stem)] = d.get("status", "unknown")
            except json.JSONDecodeError:
                flags[f.stem] = "unreadable"
    return flags


def load_inputs(root: Path) -> Inputs:
    proc = root / "data" / "processed"
    occ = pl.read_csv(proc / "occupations.csv", schema_overrides={"occ_code": pl.Utf8, "major_group": pl.Utf8, "cluster_id": pl.Utf8})
    occ = occ.sort("occ_code")
    occ_codes = occ["occ_code"].to_list()
    occ_index = {c: i for i, c in enumerate(occ_codes)}

    tasks = pl.read_csv(proc / "tasks.csv", schema_overrides={"occ_code": pl.Utf8, "task_id": pl.Utf8})
    tasks = tasks.filter(pl.col("occ_code").is_in(occ_codes)).sort(["occ_code", "task_id"])

    sectors = pl.read_csv(proc / "sectors.csv", schema_overrides={"sector_code": pl.Utf8}).sort("sector_code")
    sec_index = {c: i for i, c in enumerate(sectors["sector_code"].to_list())}
    os_ = pl.read_csv(proc / "occ_sector.csv", schema_overrides={"occ_code": pl.Utf8, "sector_code": pl.Utf8})
    occ_sector = np.zeros((len(occ_codes), len(sec_index)))
    for r in os_.iter_rows(named=True):
        if r["occ_code"] in occ_index and r["sector_code"] in sec_index:
            occ_sector[occ_index[r["occ_code"]], sec_index[r["sector_code"]]] = float(r["emp_share"])

    states = pl.read_csv(proc / "states.csv", schema_overrides={"fips": pl.Utf8}).sort("fips")
    st_index = {c: i for i, c in enumerate(states["fips"].to_list())}
    ost = pl.read_csv(proc / "occ_state.csv", schema_overrides={"occ_code": pl.Utf8, "fips": pl.Utf8})
    occ_state = np.zeros((len(occ_codes), len(st_index)))
    for r in ost.iter_rows(named=True):
        if r["occ_code"] in occ_index and r["fips"] in st_index:
            occ_state[occ_index[r["occ_code"]], st_index[r["fips"]]] = float(r["emp"])

    def series(name: str) -> pl.DataFrame | None:
        f = proc / "series" / f"{name}.csv"
        return pl.read_csv(f) if f.exists() else None

    flags = _flags(root / "data" / "provenance")
    return Inputs(
        root=root,
        occ_codes=occ_codes,
        occ_titles=occ["title"].to_list(),
        major_group=occ["major_group"].to_list(),
        cluster_id=occ["cluster_id"].to_list(),
        emp0=occ["emp_national"].cast(pl.Float64).to_numpy(),
        wage_mean=occ["wage_mean_annual"].cast(pl.Float64).to_numpy(),
        wage_p10=occ["wage_p10_annual"].cast(pl.Float64).to_numpy(),
        growth10=occ["baseline_growth_10y"].cast(pl.Float64).fill_null(0.0).to_numpy(),
        task_ids=tasks["task_id"].to_numpy(),
        task_occ=np.array([occ_index[c] for c in tasks["occ_code"].to_list()], dtype=np.int64),
        task_weight=tasks["weight"].cast(pl.Float64).to_numpy(),
        task_label=np.array([LABELS[x] for x in tasks["exposure_label"].to_list()], dtype=np.int64),
        task_beta=tasks["beta"].cast(pl.Float64).to_numpy(),
        task_modality=np.array([MODALITIES.index(x) for x in tasks["modality"].to_list()], dtype=np.int64),
        task_presence=tasks["presence"].cast(pl.Float64).to_numpy(),
        task_use_case=np.array([USE_CASES.index(x) for x in tasks["use_case"].to_list()], dtype=np.int64),
        task_consequence=tasks["consequence_high"].cast(pl.Float64).to_numpy(),
        sector_codes=sectors["sector_code"].to_list(),
        labor_cost_share=sectors["labor_cost_share"].cast(pl.Float64).to_numpy(),
        demand_elasticity=sectors["demand_elasticity"].cast(pl.Float64).to_numpy(),
        tradable=sectors["tradable"].cast(pl.Float64).to_numpy(),
        sector_friction=sectors["friction"].cast(pl.Float64).to_numpy(),
        consumption_share=sectors["consumption_share"].cast(pl.Float64).to_numpy(),
        occ_sector=occ_sector,
        state_fips=states["fips"].to_list(),
        state_names=states["name"].to_list(),
        state_abbrev=states["abbrev"].to_list(),
        occ_state=occ_state,
        btos=series("btos"),
        metr=series("metr_horizons"),
        capex=series("capex"),
        data_flags=flags,
        data_version=_hash_dir(proc),
    )

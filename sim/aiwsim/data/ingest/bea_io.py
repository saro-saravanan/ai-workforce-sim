"""BEA input-output summary use table (Supply-Use framework, producer values) -> sector parameters and direct requirements.

The workbook has one sheet per year. Rows are commodities (code in the first column, name in the second), columns are
industries (codes in the header row) followed by final-use columns (F010 personal consumption expenditures, ...) and totals;
below the commodity rows sit the value-added rows (V001 compensation of employees, T00OTOP taxes, V003 gross operating
surplus, VABAS value added) and T018 total industry output. Codes and names vary by vintage, so everything is located by
code pattern, not by position, and each derived quantity records how many source rows and columns it used.

Mapping to the 20 NAICS sectors of spec §1.2: BEA summary codes start with the NAICS digits (111CA -> 11, 321 -> 31-33, 4A0 -> 44-45,
521CI -> 52, HS/ORE -> 53, G* -> 92); see ``bea_code_to_sector``.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from aiwsim.data.fixtures import naics_to_sector

SPECIAL = {"HS": "53", "ORE": "53", "GFGD": "92", "GFGN": "92", "GFE": "92", "GSLG": "92", "GSLE": "92", "4A0": "44-45", "5412OP": "54", "521CI": "52",
           "111CA": "11", "113FF": "11", "311FT": "31-33", "313TT": "31-33", "315AL": "31-33", "487OS": "48-49", "561": "56", "711AS": "71", "Used": None, "Other": None}


def bea_code_to_sector(code: str) -> str | None:
    c = str(code).strip()
    if c in SPECIAL:
        return SPECIAL[c]
    if c.startswith("G"):
        return "92"
    digits = re.match(r"^(\d{2,3})", c)
    return naics_to_sector(digits.group(1)[:2]) if digits else None


def _num(v: Any) -> float:
    try:
        x = float(str(v).replace(",", ""))
        return 0.0 if math.isnan(x) else x
    except (TypeError, ValueError):
        return 0.0


def parse_use_table(path: Path, year: str | None = None) -> dict[str, Any]:
    """Returns {year, labor_cost_share{sector}, consumption_share{sector}, direct_requirements{i:{j}}, meta}."""
    import fastexcel
    r = fastexcel.read_excel(str(path))
    years = [s for s in r.sheet_names if re.fullmatch(r"\d{4}", s.strip())]
    if not years:
        raise ValueError(f"no year sheets in {path}: {r.sheet_names}")
    sheet = year if year in years else max(years)
    df = r.load_sheet_by_name(sheet, header_row=None).to_polars()
    rows = [list(x) for x in df.iter_rows()]
    # header row: the one with the most industry-looking codes
    def n_codes(row: list) -> int:
        return sum(1 for v in row[2:] if v is not None and re.fullmatch(r"[A-Za-z0-9]{2,7}", str(v).strip() or "") and bea_code_to_sector(str(v)) is not None)
    hi = max(range(len(rows)), key=lambda i: n_codes(rows[i]))
    header = rows[hi]
    ind_cols = {j: bea_code_to_sector(str(v)) for j, v in enumerate(header) if j >= 2 and v is not None and bea_code_to_sector(str(v)) is not None}
    pce_col = next((j for j, v in enumerate(header) if v is not None and str(v).strip().upper() in ("F010", "PCE")), None)
    codes20 = ["11", "21", "22", "23", "31-33", "42", "44-45", "48-49", "51", "52", "53", "54", "55", "56", "61", "62", "71", "72", "81", "92"]
    use = {i: {j: 0.0 for j in codes20} for i in codes20}       # intermediate use of commodity sector i by industry sector j
    pce = dict.fromkeys(codes20, 0.0); comp = dict.fromkeys(codes20, 0.0); out = dict.fromkeys(codes20, 0.0); va = dict.fromkeys(codes20, 0.0)
    n_comm = 0
    for row in rows[hi + 1:]:
        code = str(row[0]).strip() if row and row[0] is not None else ""
        if not code:
            continue
        up = code.upper()
        if up in ("V001", "COMPENSATION OF EMPLOYEES"):
            for j, sec in ind_cols.items():
                comp[sec] += _num(row[j])
        elif up in ("T018", "TOTAL INDUSTRY OUTPUT"):
            for j, sec in ind_cols.items():
                out[sec] += _num(row[j])
        elif up in ("VABAS", "T016", "VALUE ADDED"):
            for j, sec in ind_cols.items():
                va[sec] += _num(row[j])
        else:
            sec_i = bea_code_to_sector(code)
            if sec_i is None or up.startswith(("T0", "V0", "F0", "VA", "S00")):
                continue
            n_comm += 1
            for j, sec_j in ind_cols.items():
                use[sec_i][sec_j] += _num(row[j])
            if pce_col is not None:
                pce[sec_i] += _num(row[pce_col])
    lcs = {s: (comp[s] / out[s] if out[s] > 0 else None) for s in codes20}
    pce_tot = sum(v for v in pce.values() if v > 0) or 1.0
    cs = {s: max(pce[s], 0.0) / pce_tot for s in codes20}
    A = {i: {j: (use[i][j] / out[j] if out[j] > 0 else 0.0) for j in codes20} for i in codes20}
    meta = {"sheet": sheet, "header_row": hi, "industry_columns": len(ind_cols), "commodity_rows": n_comm, "pce_col": pce_col, "file": str(path),
            "sectors_with_output": sum(1 for s in codes20 if out[s] > 0)}
    return {"year": sheet, "labor_cost_share": {s: v for s, v in lcs.items() if v is not None}, "consumption_share": cs, "direct_requirements": A,
            "value_added_share": {s: (va[s] / out[s] if out[s] > 0 else None) for s in codes20}, "meta": meta}


def parse_use_table_api(path: Path) -> dict[str, Any]:
    """The same output from the BEA API's GetData response (DataSetName=InputOutput, TableID 259 = summary use table, producer prices):
    rows are {RowCode, ColCode, DataValue, ...}; commodity rows by industry columns, value-added rows V001/T018 and the final-use column F010."""
    import json
    payload = json.loads(Path(path).read_text())
    data = payload.get("BEAAPI", {}).get("Results", {}).get("Data", [])
    if not data:
        raise ValueError(f"no Data rows in {path}: {str(payload)[:200]}")
    codes20 = ["11", "21", "22", "23", "31-33", "42", "44-45", "48-49", "51", "52", "53", "54", "55", "56", "61", "62", "71", "72", "81", "92"]
    use = {i: {j: 0.0 for j in codes20} for i in codes20}
    pce = dict.fromkeys(codes20, 0.0); comp = dict.fromkeys(codes20, 0.0); out = dict.fromkeys(codes20, 0.0); va = dict.fromkeys(codes20, 0.0)
    year = str(data[0].get("Year", ""))
    for r in data:
        rc = str(r.get("RowCode", "")).strip(); cc = str(r.get("ColCode", "")).strip(); v = _num(r.get("DataValue"))
        sec_j = bea_code_to_sector(cc) if not cc.upper().startswith(("F0", "T0")) else None
        up = rc.upper()
        if up == "V001" and sec_j:
            comp[sec_j] += v
        elif up == "T018" and sec_j:
            out[sec_j] += v
        elif up in ("VABAS", "T016") and sec_j:
            va[sec_j] += v
        elif not up.startswith(("T0", "V0", "F0", "VA", "S00")):
            sec_i = bea_code_to_sector(rc)
            if sec_i is None:
                continue
            if sec_j:
                use[sec_i][sec_j] += v
            elif cc.upper() == "F010":
                pce[sec_i] += v
    lcs = {s: (comp[s] / out[s] if out[s] > 0 else None) for s in codes20}
    pce_tot = sum(x for x in pce.values() if x > 0) or 1.0
    A = {i: {j: (use[i][j] / out[j] if out[j] > 0 else 0.0) for j in codes20} for i in codes20}
    return {"year": year, "labor_cost_share": {s: x for s, x in lcs.items() if x is not None}, "consumption_share": {s: max(pce[s], 0.0) / pce_tot for s in codes20},
            "direct_requirements": A, "value_added_share": {s: (va[s] / out[s] if out[s] > 0 else None) for s in codes20},
            "meta": {"rows": len(data), "file": str(path), "sectors_with_output": sum(1 for s in codes20 if out[s] > 0)}}

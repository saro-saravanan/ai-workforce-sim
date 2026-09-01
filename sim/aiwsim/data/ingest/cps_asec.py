"""IPUMS CPS ASEC ingest -> real cohort tables (contracts §7): ``occ_age.csv``, ``occ_education.csv``
and the joint ``occ_cohort.csv`` (age x education x decile per occupation), fitted by IPF to the
OEWS-derived decile marginals of ``occ_decile.csv``.

Runs on a networked machine with an IPUMS API key in ``$IPUMS_API_KEY`` (register at
https://cps.ipums.org/ ; the key is on https://account.ipums.org/api_keys).  Inventory row 7 records
the CPS landing page https://cps.ipums.org/cps/ ; the API host below is the IPUMS API v2
documented at https://developer.ipums.org/ .  IPUMS terms forbid redistributing extracts: the raw
download stays in the gitignored ``data/raw/cps_asec/``.

Steps
1. Submit an extract (POST /extracts?collection=cps&version=2): five pooled ASEC samples
   (``SAMPLES``), variables ``VARIABLES``, rectangular on persons, csv.
2. Poll GET /extracts/<n>?collection=cps&version=2 until ``status == "completed"``; download the
   ``downloadLinks.data.url`` (csv.gz) with the same Authorization header.
3. Keep employed persons aged 16+ (EMPSTAT 10/12), weight ASECWT; bands per contracts §7; education
   from EDUC (``EDUC_BANDS``); decile from INCWAGE against ``cohorts/national_deciles.csv``.
4. Crosswalk Census occupation codes (OCC, 2018 basis) to SOC 2018 with the Census "2018 Census
   Occupation Code List with Crosswalk" (``CROSSWALK_URL``; download it by hand if the Census site
   blocks scripts and pass ``--crosswalk``).  A Census code that spans several SOC codes is split
   across the OEWS occupations that carry them in proportion to ``emp_national``.
5. Per occupation, IPF of the weighted age x education x decile counts to three marginals: CPS age,
   CPS education and the OEWS-derived decile shares.  Occupations with fewer than ``MIN_OBS``
   unweighted observations borrow the pooled cube of their minor group, then major group (flagged
   in ``pooled_level``).
6. Write the three tables (atomic: ``.part`` then replace) and provenance with status ``real``.

``--check`` verifies only that the IPUMS API base URL answers; ``--dry-run`` does everything but
write.  This script has not been executed against the live API (the sandbox cannot reach it).
"""

from __future__ import annotations

import gzip
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import polars as pl

from aiwsim.data.clusters import map_to_oews
from aiwsim.data.cohorts import AGE_BANDS, DECILES, EDUCATION_LEVELS
from aiwsim.data.ingest._common import (
    NOT_IN_INVENTORY,
    USER_AGENT,
    base_parser,
    download,
    read_excel_bytes,
    resolve_root,
    run_checks,
    write_provenance,
)
from aiwsim.data.sources import SOURCES

LANDING = "https://cps.ipums.org/cps/"
API_BASE = "https://api.ipums.org"                      # NOT IN INVENTORY (IPUMS API v2 host)
API_VERSION = "2"
COLLECTION = "cps"
# NOT IN INVENTORY: Census "2018 Census Occupation Code List with Crosswalk" (industry-occupation
# guidance page https://www.census.gov/topics/employment/industry-occupation/guidance/code-lists.html)
CROSSWALK_URL = ("https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/"
                 "2018-occupation-code-list-and-crosswalk.xlsx")

# Five pooled ASEC years (IPUMS sample ids: cps<year>_03s).  The 2018 Census occupation basis applies
# to OCC from the 2020 ASEC on; older years would need OCC2010 instead.
SAMPLES = ["cps2020_03s", "cps2021_03s", "cps2022_03s", "cps2023_03s", "cps2024_03s"]
VARIABLES = ["AGE", "EDUC", "OCC", "OCC2010", "INCWAGE", "WKSWORK1", "UHRSWORKT", "ASECWT", "EMPSTAT"]
MIN_OBS = 30          # unweighted persons below which an occupation borrows its group's cube
IPF_ITERS = 200
IPF_TOL = 1e-9
INCWAGE_MISSING = 99_999_999  # IPUMS N.I.U. / missing code for INCWAGE
POLL_SECONDS = 30
POLL_MAX_MINUTES = 120

# IPUMS EDUC (general version) -> education level of contracts §7.
EDUC_BANDS = [  # (upper bound inclusive, level)
    (72, "lt_hs"),          # 0 NIU .. 71 grade 12 no diploma
    (73, "hs"),             # 73 high school diploma or equivalent
    (110, "some_college"),  # 81 some college no degree; 91/92 associate's
    (999, "ba_plus"),       # 111 bachelor's; 123 master's; 124 professional; 125 doctorate
]


# ------------------------------------------------------------------------------------------------
# IPUMS API
# ------------------------------------------------------------------------------------------------
def _api(path: str, key: str, *, method: str = "GET", body: dict | None = None, timeout: int = 60) -> dict:
    url = f"{API_BASE}{path}{'&' if '?' in path else '?'}collection={COLLECTION}&version={API_VERSION}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": key, "Content-Type": "application/json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"IPUMS API {method} {url} -> HTTP {e.code}: {e.read().decode(errors='replace')[:500]}") from e


def extract_definition() -> dict:
    return {
        "description": "aiwsim Phase 2 cohorts: ASEC 2020-2024 pooled, employed persons",
        "dataStructure": {"rectangular": {"on": "P"}},
        "dataFormat": "csv",
        "samples": {s: {} for s in SAMPLES},
        "variables": {v: {} for v in VARIABLES},
    }


def submit_extract(key: str) -> int:
    resp = _api("/extracts", key, method="POST", body=extract_definition())
    number = int(resp["number"])
    print(f"  submitted IPUMS extract #{number}")
    return number


def wait_for_extract(key: str, number: int) -> dict:
    t0 = time.time()
    while True:
        resp = _api(f"/extracts/{number}", key)
        st = resp.get("status", "?")
        print(f"  extract #{number}: {st}")
        if st == "completed":
            return resp
        if st in ("failed", "canceled"):
            raise SystemExit(f"IPUMS extract #{number} {st}")
        if time.time() - t0 > POLL_MAX_MINUTES * 60:
            raise SystemExit(f"IPUMS extract #{number} not ready after {POLL_MAX_MINUTES} min; rerun with "
                             f"--extract {number}")
        time.sleep(POLL_SECONDS)


def download_extract(key: str, resp: dict, dest: Path, force: bool = False) -> Path:
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"  cached  {dest}")
        return dest
    url = resp["downloadLinks"]["data"]["url"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": USER_AGENT})
    print(f"  GET     {url}")
    with urllib.request.urlopen(req, timeout=600) as r, open(part, "wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)
    part.replace(dest)
    print(f"  saved   {dest} ({dest.stat().st_size:,} bytes)")
    return dest


def read_extract(path: Path) -> pl.DataFrame:
    raw = path.read_bytes()
    if path.suffix == ".gz" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    df = pl.read_csv(io.BytesIO(raw), infer_schema_length=0)
    df.columns = [c.strip().upper() for c in df.columns]
    need = {"AGE", "EDUC", "OCC", "INCWAGE", "ASECWT", "EMPSTAT"}
    missing = need - set(df.columns)
    if missing:
        raise SystemExit(f"extract lacks {sorted(missing)}; columns: {df.columns}")
    return df


# ------------------------------------------------------------------------------------------------
# Census OCC -> SOC 2018 -> OEWS occ_code
# ------------------------------------------------------------------------------------------------
SOC_RX = re.compile(r"\b(\d{2}-\d{4})\b")


def load_crosswalk(path: Path) -> pl.DataFrame:
    """``census_occ`` (4-digit string) -> ``soc`` (one SOC 2018 code per row) from the Census workbook.

    The workbook lists one row per 2018 Census code with its SOC equivalents in a text column
    (``11-1011``, ``11-1011, 11-1021``, or a broad ``13-1020``); every code-shaped token is kept.
    """
    raw = path.read_bytes()
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = read_excel_bytes(raw)
    else:
        df = pl.read_csv(io.BytesIO(raw), infer_schema_length=0)
    cols = {c.strip().lower(): c for c in df.columns}
    occ_col = next((cols[c] for c in cols if "2018" in c and "census" in c and "code" in c), None)
    soc_col = next((cols[c] for c in cols if "soc" in c and "code" in c), None)
    if occ_col is None or soc_col is None:
        raise SystemExit(f"could not find the Census code / SOC code columns in {path}: {df.columns}")
    rows = []
    for occ, soc in zip(df[occ_col], df[soc_col]):
        if occ is None or soc is None:
            continue
        code = re.sub(r"\D", "", str(occ))
        if len(code) != 4:
            continue
        for s in SOC_RX.findall(str(soc)):
            rows.append({"census_occ": code, "soc": s})
    out = pl.DataFrame(rows).unique()
    if out.height == 0:
        raise SystemExit(f"no Census -> SOC pairs parsed from {path}")
    return out


def census_to_occ_weights(xw: pl.DataFrame, occ: pl.DataFrame) -> pl.DataFrame:
    """``census_occ, occ_code, w``: how each Census code's workers are split across OEWS codes.

    Each SOC code is mapped to the OEWS code that carries it (``map_to_oews``: exact, crosswalk, or
    broad code); when a Census code maps to several OEWS codes the split is proportional to
    ``emp_national``.  Broad SOC codes (ending in 0) expand to every detailed OEWS code beneath them.
    """
    oews_codes = set(occ["occ_code"])
    emp = dict(zip(occ["occ_code"], occ["emp_national"].cast(pl.Float64)))
    rows = []
    for census_occ, soc in zip(xw["census_occ"], xw["soc"]):
        targets: list[str] = []
        if soc.endswith("0") and soc not in oews_codes:  # broad or minor group -> its detailed codes
            prefix = soc.rstrip("0")
            targets = [c for c in oews_codes if c.startswith(prefix)]
        else:
            m = map_to_oews(soc, oews_codes)
            targets = [m] if m else []
        rows.extend({"census_occ": census_occ, "occ_code": t, "w": emp.get(t, 0.0) or 1.0} for t in targets)
    w = pl.DataFrame(rows).unique(subset=["census_occ", "occ_code"])
    return w.with_columns((pl.col("w") / pl.col("w").sum().over("census_occ")).alias("w"))


# ------------------------------------------------------------------------------------------------
# person records -> banded, weighted counts
# ------------------------------------------------------------------------------------------------
def band_persons(df: pl.DataFrame, cutpoints: list[float]) -> pl.DataFrame:
    """Employed persons 16+ with ``age_band``, ``education``, ``decile``, ``census_occ``, ``wt``."""
    d = df.select(
        pl.col("AGE").cast(pl.Int64, strict=False).alias("age"),
        pl.col("EDUC").cast(pl.Int64, strict=False).alias("educ"),
        pl.col("OCC").cast(pl.Int64, strict=False).alias("occ_int"),
        pl.col("INCWAGE").cast(pl.Float64, strict=False).alias("incwage"),
        pl.col("ASECWT").cast(pl.Float64, strict=False).alias("wt"),
        pl.col("EMPSTAT").cast(pl.Int64, strict=False).alias("empstat"),
    ).filter((pl.col("empstat").is_in([10, 12])) & (pl.col("age") >= 16) & (pl.col("occ_int") > 0)
             & pl.col("wt").is_not_null() & (pl.col("wt") > 0))
    d = d.with_columns(
        pl.when(pl.col("age") <= 24).then(pl.lit("16-24")).when(pl.col("age") <= 44).then(pl.lit("25-44"))
        .when(pl.col("age") <= 54).then(pl.lit("45-54")).otherwise(pl.lit("55+")).alias("age_band"),
        pl.col("occ_int").cast(pl.Utf8).str.zfill(4).alias("census_occ"),
        pl.when(pl.col("incwage") >= INCWAGE_MISSING).then(None).otherwise(pl.col("incwage")).alias("incwage"),
    )
    educ_expr = pl.lit(EDUC_BANDS[-1][1])
    for ub, level in reversed(EDUC_BANDS[:-1]):
        educ_expr = pl.when(pl.col("educ") <= ub).then(pl.lit(level)).otherwise(educ_expr)
    d = d.with_columns(educ_expr.alias("education"))
    dec = pl.lit(1)
    for k, c in enumerate(cutpoints, start=2):  # cutpoints = lower bounds of deciles 2..10
        dec = pl.when(pl.col("incwage") >= c).then(pl.lit(k)).otherwise(dec)
    d = d.with_columns(dec.alias("decile"))
    return d.filter(pl.col("incwage").is_not_null()).select("census_occ", "age_band", "education", "decile", "wt")


def weighted_cubes(persons: pl.DataFrame, xw_w: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(weighted cell counts per occ_code x age x education x decile, unweighted obs per occ_code)."""
    j = persons.join(xw_w, on="census_occ", how="inner")
    cells = j.group_by(["occ_code", "age_band", "education", "decile"]).agg(
        (pl.col("wt") * pl.col("w")).sum().alias("n"))
    obs = j.group_by("occ_code").agg(pl.col("w").sum().alias("obs"))  # fractional persons after the split
    return cells, obs


# ------------------------------------------------------------------------------------------------
# IPF
# ------------------------------------------------------------------------------------------------
def ipf(cube: np.ndarray, m_age: np.ndarray, m_edu: np.ndarray, m_dec: np.ndarray) -> np.ndarray:
    """Fit ``cube`` (4 x 4 x 10) to the three one-way marginals (each summing to 1)."""
    x = cube.astype(float).copy()
    x[x <= 0] = 1e-9  # structural zeros would block the decile marginal; keep a tiny floor
    x /= x.sum()
    for _ in range(IPF_ITERS):
        x *= (m_age / x.sum(axis=(1, 2)))[:, None, None]
        x *= (m_edu / x.sum(axis=(0, 2)))[None, :, None]
        x *= (m_dec / x.sum(axis=(0, 1)))[None, None, :]
        err = max(np.abs(x.sum(axis=(1, 2)) - m_age).max(), np.abs(x.sum(axis=(0, 2)) - m_edu).max(),
                  np.abs(x.sum(axis=(0, 1)) - m_dec).max())
        if err < IPF_TOL:
            break
    return x / x.sum()


def _cube(cells: pl.DataFrame) -> np.ndarray:
    a = {b: i for i, b in enumerate(AGE_BANDS)}
    e = {b: i for i, b in enumerate(EDUCATION_LEVELS)}
    x = np.zeros((len(AGE_BANDS), len(EDUCATION_LEVELS), len(DECILES)))
    for r in cells.to_dicts():
        x[a[r["age_band"]], e[r["education"]], int(r["decile"]) - 1] += r["n"]
    return x


def fit_all(cells: pl.DataFrame, obs: pl.DataFrame, occ: pl.DataFrame, occ_decile: pl.DataFrame,
            tag: str) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, dict]:
    """Per-occupation IPF -> (occ_cohort, occ_age, occ_education, notes)."""
    codes = occ["occ_code"].to_list()
    obs_map = dict(zip(obs["occ_code"], obs["obs"]))
    by_occ = {c: _cube(g) for c, g in cells.partition_by("occ_code", as_dict=True, include_key=False).items()
              for c in [c[0] if isinstance(c, tuple) else c]}

    def pooled(prefix_len: int, code: str) -> np.ndarray:
        x = np.zeros((4, 4, 10))
        for c, cube in by_occ.items():
            if c[:prefix_len] == code[:prefix_len]:
                x += cube
        return x

    dec = occ_decile.with_columns(pl.col("decile").cast(pl.Int64), pl.col("share").cast(pl.Float64))
    dec_map = {c: g.sort("decile")["share"].to_numpy() for c, g in
               dec.partition_by("occ_code", as_dict=True, include_key=False).items()
               for c in [c[0] if isinstance(c, tuple) else c]}
    joint, ages, edus, levels = [], [], [], {"own": 0, "minor": 0, "major": 0, "national": 0}
    national = sum(by_occ.values())
    for code in codes:
        cube, level = by_occ.get(code), "own"
        if cube is None or obs_map.get(code, 0.0) < MIN_OBS:
            cube, level = pooled(5, code), "minor"
            if cube.sum() <= 0 or cube.sum() < MIN_OBS:
                cube, level = pooled(2, code), "major"
            if cube.sum() <= 0:
                cube, level = national, "national"
        levels[level] += 1
        m_age = cube.sum(axis=(1, 2)) / cube.sum()
        m_edu = cube.sum(axis=(0, 2)) / cube.sum()
        m_dec = dec_map[code]
        x = ipf(cube, m_age, m_edu, m_dec)
        for i, a in enumerate(AGE_BANDS):
            ages.append({"occ_code": code, "age_band": a, "share": float(x[i].sum()), "source_tag": tag,
                         "pooled_level": level})
            for j, e in enumerate(EDUCATION_LEVELS):
                for k in DECILES:
                    joint.append({"occ_code": code, "age_band": a, "education": e, "decile": k,
                                  "share": float(x[i, j, k - 1]), "source_tag": tag})
        for j, e in enumerate(EDUCATION_LEVELS):
            edus.append({"occ_code": code, "education": e, "share": float(x[:, j, :].sum()), "source_tag": tag,
                         "pooled_level": level})
    notes = {"pooled_levels": levels, "occupations": len(codes)}
    return pl.DataFrame(joint), pl.DataFrame(ages), pl.DataFrame(edus), notes


# ------------------------------------------------------------------------------------------------
# output
# ------------------------------------------------------------------------------------------------
def atomic_write_csv(df: pl.DataFrame, path: Path, dry_run: bool) -> Path:
    if dry_run:
        print(f"  [dry-run] would write {path} ({df.height} rows, {len(df.columns)} cols)")
        print(df.head(5))
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    df.write_csv(part)
    part.replace(path)
    print(f"  wrote   {path} ({df.height} rows)")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = base_parser(__doc__.split("\n")[0])
    ap.add_argument("--extract", type=int, default=None, help="reuse an already submitted IPUMS extract number")
    ap.add_argument("--extract-file", type=Path, default=None, help="use an already downloaded extract (csv/csv.gz)")
    ap.add_argument("--crosswalk", type=Path, default=None,
                    help="Census 2018 occupation code list with crosswalk (xlsx/csv); downloaded if absent")
    args = ap.parse_args(argv)
    if args.check:
        return run_checks({"ipums_api_base": API_BASE + "/"})
    root = resolve_root(args)
    proc = root / "data" / "processed"
    raw_dir = root / "data" / "raw" / "cps_asec"
    src = SOURCES["cps_ipums"]

    occ_path, dec_path, nat_path = (proc / "occupations.csv", proc / "cohorts" / "occ_decile.csv",
                                    proc / "cohorts" / "national_deciles.csv")
    for p in (occ_path, dec_path, nat_path):
        if not p.exists():
            return _fail(f"{p} missing: run `uv run aiwsim data build` first")
    occ = pl.read_csv(occ_path, infer_schema_length=0)
    occ_decile = pl.read_csv(dec_path, infer_schema_length=0)
    nat = pl.read_csv(nat_path, infer_schema_length=0).with_columns(
        pl.col("decile").cast(pl.Int64), pl.col("lower_bound_annual").cast(pl.Float64)).sort("decile")
    cutpoints = nat["lower_bound_annual"].to_list()[1:]

    # -- extract
    if args.extract_file:
        extract_path, extract_no = Path(args.extract_file), None
    else:
        key = os.environ.get("IPUMS_API_KEY", "")
        if not key:
            return _fail("IPUMS_API_KEY is not set (https://account.ipums.org/api_keys)")
        extract_no = args.extract or submit_extract(key)
        resp = wait_for_extract(key, extract_no)
        extract_path = download_extract(key, resp, raw_dir / f"cps_asec_extract_{extract_no:05d}.csv.gz",
                                        force=args.force)
    df = read_extract(extract_path)
    print(f"  extract: {df.height:,} person records")

    # -- crosswalk
    xw_path = args.crosswalk or raw_dir / Path(CROSSWALK_URL).name
    if not xw_path.exists():
        try:
            download(CROSSWALK_URL, xw_path, force=args.force)
        except Exception as e:  # noqa: BLE001
            return _fail(f"could not download the Census crosswalk ({e}); fetch {CROSSWALK_URL} by hand and pass "
                         f"--crosswalk")
    xw = load_crosswalk(xw_path)
    xw_w = census_to_occ_weights(xw, occ)
    print(f"  crosswalk: {xw['census_occ'].n_unique()} Census codes -> {xw_w['occ_code'].n_unique()} OEWS codes")

    # -- persons -> cubes -> IPF
    persons = band_persons(df, cutpoints)
    cells, obs = weighted_cubes(persons, xw_w)
    unmatched = persons.filter(~pl.col("census_occ").is_in(xw_w["census_occ"]))["census_occ"].unique().to_list()
    if unmatched:
        print(f"  WARNING: {len(unmatched)} Census codes without a SOC mapping dropped: {sorted(unmatched)[:20]}")
    tag = f"real:CPS_ASEC_{SAMPLES[0][3:7]}-{SAMPLES[-1][3:7]}_IPF"
    joint, ages, edus, notes = fit_all(cells, obs, occ, occ_decile, tag)
    print(f"  fitted {notes['occupations']} occupations; pooled levels {notes['pooled_levels']}")

    out = proc / "cohorts"
    p_age = atomic_write_csv(ages.sort(["occ_code", "age_band"]), out / "occ_age.csv", args.dry_run)
    p_edu = atomic_write_csv(edus.sort(["occ_code", "education"]), out / "occ_education.csv", args.dry_run)
    p_joint = atomic_write_csv(joint.sort(["occ_code", "age_band", "education", "decile"]), out / "occ_cohort.csv",
                               args.dry_run)
    if args.dry_run:
        return 0
    common = {
        "source": f"IPUMS CPS ASEC samples {SAMPLES} (extract #{extract_no}), variables {VARIABLES}; Census 2018 "
                  f"occupation crosswalk {xw_path.name}",
        "source_url": LANDING, "license": src.license,
        "notes": f"{NOT_IN_INVENTORY} (API host {API_BASE}; crosswalk {CROSSWALK_URL}). Employed persons 16+ "
                 f"(EMPSTAT 10/12), ASECWT weights, INCWAGE deciles against cohorts/national_deciles.csv. "
                 f"Occupations with fewer than {MIN_OBS} observations borrow their minor / major group cube "
                 f"(pooled_level). Pooled levels: {notes['pooled_levels']}. Census codes without SOC mapping: "
                 f"{sorted(unmatched)}.",
        "extra": {"ingested": True, "samples": SAMPLES, "extract": extract_no,
                  "pooled_levels": notes["pooled_levels"]},
    }
    ipf_note = ("per occupation, IPF of weighted age x education x decile counts to the CPS age marginal, the CPS "
                "education marginal and the OEWS-derived decile marginal (cohorts/occ_decile.csv)")
    write_provenance(root, "cohorts/occ_age", p_age, status="real",
                     transformations=["age bands 16-24 / 25-44 / 45-54 / 55+", ipf_note, "share = age marginal"],
                     **common)
    write_provenance(root, "cohorts/occ_education", p_edu, status="real",
                     transformations=[f"EDUC -> level: {EDUC_BANDS}", ipf_note, "share = education marginal"],
                     **common)
    write_provenance(root, "cohorts/occ_cohort", p_joint, status="real",
                     transformations=["Census OCC -> SOC 2018 -> OEWS code (split by emp_national when several)",
                                      ipf_note, "share = fitted joint cell (sums to 1 per occupation)"], **common)
    return 0


def _fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

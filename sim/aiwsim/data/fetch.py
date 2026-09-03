"""Fetch the raw inputs the build needs, pinned by commit or tag and verified by SHA-256.

`data/raw/` is not committed (see .gitignore); this module reproduces it from public GitHub mirrors so a
clean clone and CI can run `aiwsim data build`. Every entry records where the file comes from and the
checksum of the exact bytes the shipped tables were built from; a checksum mismatch is an error, never
a silent upgrade of the data vintage.

    uv run aiwsim data fetch            # downloads what is missing or mismatched
    uv run aiwsim data fetch --force    # re-downloads everything
"""
from __future__ import annotations

import hashlib
import urllib.request
from dataclasses import dataclass
from pathlib import Path

GPTS_COMMIT = "0471612fef3cc22b74fb884d27bff9dbd3770582"     # openai/GPTs-are-GPTs (MIT), Eloundou et al. replication data
NE_TAG = "v5.1.2"                                             # nvkelso/natural-earth-vector (public domain)
_GPTS = f"https://raw.githubusercontent.com/openai/GPTs-are-GPTs/{GPTS_COMMIT}"
_NE = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{NE_TAG}/geojson"


@dataclass(frozen=True)
class RawFile:
    dest: str      # relative to the repository root
    url: str
    sha256: str


MANIFEST: list[RawFile] = [
    RawFile("data/raw/gpts_are_gpts/LICENSE", f"{_GPTS}/LICENSE", "d831db55645e47ca8e491c5a0e37f1ee744d7b10bf5aa8d50146c795ac0176c0"),
    RawFile("data/raw/gpts_are_gpts/full_labelset.tsv", f"{_GPTS}/data/full_labelset.tsv", "094378905e1f3349e50a9a83dc69643a2ef227954d611c8316a46da08cb3d8de"),
    RawFile("data/raw/gpts_are_gpts/national_May2021_dl.csv", f"{_GPTS}/data/national_May2021_dl.csv", "ed35ea6dda3c430f7865c2194df49bacf8f0502a6783462051c603b53974583f"),
    RawFile("data/raw/gpts_are_gpts/occ_level.csv", f"{_GPTS}/data/occ_level.csv", "40c74f53de40aec91c0017d80690cbba915f83a8bb414bcf2f884692f1749acb"),
    RawFile("data/raw/gpts_are_gpts/occupations_onet_basic_skills.csv", f"{_GPTS}/data/occupations_onet_basic_skills.csv", "a17fa416c923bf16754769e2677e8e83ec1b130abd7c81298c146640e4cbc13a"),
    RawFile("data/raw/gpts_are_gpts/occupations_onet_bls_matched.csv", f"{_GPTS}/data/occupations_onet_bls_matched.csv", "e3289815f87a06bdd0d815971fee1578e58ff408d851c2b0ff030cd3650a7697"),
    RawFile("data/raw/gpts_are_gpts/occupations_onet_work_contexts.csv", f"{_GPTS}/data/occupations_onet_work_contexts.csv", "29a09da45ea0ca0edb55a399e5ed0a1f89233014726971abc5328ec9c9e3f8ae"),
    RawFile("data/raw/gpts_are_gpts/occupations_projections_processed.csv", f"{_GPTS}/data/occupations_projections_processed.csv", "d1f2a237e8ee0016e1ef656f9e453efdfffc48fcc0a8d4b15697fdd57995f730"),
    RawFile("data/raw/gpts_are_gpts/bls_occupation_demographics_2022.xlsx", f"{_GPTS}/data/bls_occupation_demographics_2022.xlsx", "507754314560a648964ea89fde4e7cbb8fe1f2c885fac76ce99d657b31e609e7"),
    RawFile("data/raw/gpts_are_gpts/cpsaat11.xlsx", f"{_GPTS}/data/cpsaat11.xlsx", "e17b2584151d251aa19b9d7dd03b69bf2b7ba786d66f0226299ab3bf5e5bc625"),
    RawFile("data/raw/aioe/AIOE_DataAppendix.xlsx", "https://raw.githubusercontent.com/AIOE-Data/AIOE/main/AIOE_DataAppendix.xlsx",
            "c123b4c64840aff3568ae6c97256678719b88a74d45b6362dbefb5af34667b95"),   # Felten, Raj, Seamans AIOE; no license file: cross-check only, never redistributed
    RawFile("data/raw/natural_earth/ne_50m_admin_0_countries.geojson", f"{_NE}/ne_50m_admin_0_countries.geojson", "3e458fc036ad0a66411f2c1e6cac49c5d7bfb81cb1123bc513b22511a2b7fdeb"),
    RawFile("data/raw/natural_earth/ne_admin0_110m.geojson", f"{_NE}/ne_110m_admin_0_countries.geojson", "6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f"),
    RawFile("data/raw/natural_earth/ne_admin1_110m.geojson", f"{_NE}/ne_110m_admin_1_states_provinces.geojson", "0067dec6a2c4f9c7a644bf7a9a46163d8d881595953326d0c67d89934190aefe"),
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def missing(root: Path) -> list[RawFile]:
    return [f for f in MANIFEST if not (root / f.dest).exists() or sha256_of(root / f.dest) != f.sha256]


def fetch_all(root: Path, force: bool = False, log=print, timeout: int = 120) -> list[str]:
    """Download every manifest entry that is missing or fails its checksum (all of them with force). Returns the paths written."""
    todo = MANIFEST if force else missing(root)
    written: list[str] = []
    for f in todo:
        dest = root / f.dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(dest.suffix + ".part")
        req = urllib.request.Request(f.url, headers={"User-Agent": "aiwsim-data-fetch"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(part, "wb") as fh:
            fh.writelines(iter(lambda: r.read(1 << 20), b""))
        got = sha256_of(part)
        if got != f.sha256:
            part.unlink(missing_ok=True)
            raise RuntimeError(f"checksum mismatch for {f.url}: expected {f.sha256[:12]}…, got {got[:12]}…; the upstream file changed, pin a new revision deliberately")
        part.replace(dest)
        written.append(f.dest)
        log(f"fetched {f.dest} ({dest.stat().st_size:,} bytes)")
    (root / "data/raw/gpts_are_gpts").mkdir(parents=True, exist_ok=True)
    (root / "data/raw/gpts_are_gpts/COMMIT").write_text(GPTS_COMMIT + "\n")
    if not todo:
        log("raw inputs present and verified; nothing to fetch")
    return written

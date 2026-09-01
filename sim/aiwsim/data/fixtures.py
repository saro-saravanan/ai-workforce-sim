"""Phase 1 fixtures: sectors (single ``ALL`` sector + the 20-sector NAICS list) and the state share
proxy (2020 Census apportionment resident population).  Everything here is tagged ``FIXTURE`` and is
replaced by ``aiwsim.data.ingest.oews`` on a machine with network access.
"""

from __future__ import annotations

import polars as pl

FIXTURE_TAG = "FIXTURE"

# Contracts §1, Phase 1 sector fixture.
SECTOR_ALL = {
    "sector_code": "ALL", "title": "All industries (Phase 1 single-sector fixture)",
    "labor_cost_share": 0.58, "demand_elasticity": 0.8, "tradable": 0, "friction": 1.0,
    "consumption_share": 1.0, "source_tag": FIXTURE_TAG,
}

# Spec §1.2: NAICS 2-digit with 31-33, 44-45 and 48-49 merged = 20 sectors.  ``tradable`` is our
# reading of Bessen-style tradables vs local services (E); ``labor_cost_share`` is left empty for
# the BEA input-output ingest (inventory row 24).  The 21st "AI production" sector (NAICS 5182,
# 5415 partial, 2371 partial) is created by the model from capex, not by this table.
SECTORS_20: list[dict] = [
    {"sector_code": "11", "naics": "11", "title": "Agriculture, Forestry, Fishing and Hunting", "tradable": 1},
    {"sector_code": "21", "naics": "21", "title": "Mining, Quarrying, and Oil and Gas Extraction", "tradable": 1},
    {"sector_code": "22", "naics": "22", "title": "Utilities", "tradable": 0},
    {"sector_code": "23", "naics": "23", "title": "Construction", "tradable": 0},
    {"sector_code": "31-33", "naics": "31-33", "title": "Manufacturing", "tradable": 1},
    {"sector_code": "42", "naics": "42", "title": "Wholesale Trade", "tradable": 0},
    {"sector_code": "44-45", "naics": "44-45", "title": "Retail Trade", "tradable": 0},
    {"sector_code": "48-49", "naics": "48-49", "title": "Transportation and Warehousing", "tradable": 0},
    {"sector_code": "51", "naics": "51", "title": "Information", "tradable": 1},
    {"sector_code": "52", "naics": "52", "title": "Finance and Insurance", "tradable": 1},
    {"sector_code": "53", "naics": "53", "title": "Real Estate and Rental and Leasing", "tradable": 0},
    {"sector_code": "54", "naics": "54", "title": "Professional, Scientific, and Technical Services", "tradable": 1},
    {"sector_code": "55", "naics": "55", "title": "Management of Companies and Enterprises", "tradable": 0},
    {"sector_code": "56", "naics": "56",
     "title": "Administrative and Support and Waste Management and Remediation Services", "tradable": 0},
    {"sector_code": "61", "naics": "61", "title": "Educational Services", "tradable": 0},
    {"sector_code": "62", "naics": "62", "title": "Health Care and Social Assistance", "tradable": 0},
    {"sector_code": "71", "naics": "71", "title": "Arts, Entertainment, and Recreation", "tradable": 0},
    {"sector_code": "72", "naics": "72", "title": "Accommodation and Food Services", "tradable": 0},
    {"sector_code": "81", "naics": "81", "title": "Other Services (except Public Administration)", "tradable": 0},
    {"sector_code": "92", "naics": "92", "title": "Public Administration", "tradable": 0},
]


def naics_to_sector(naics: str) -> str | None:
    """Map a NAICS code (any depth; OEWS forms like ``31-33``, ``000000``, ``999200``) to a sector."""
    s = str(naics).strip()
    if s in {"31-33", "44-45", "48-49"}:
        return s
    if s.startswith("99"):  # OEWS government aggregates (999xxx) -> public administration
        return "92"
    two = s[:2]
    if two in {"31", "32", "33"}:
        return "31-33"
    if two in {"44", "45"}:
        return "44-45"
    if two in {"48", "49"}:
        return "48-49"
    return two if any(r["sector_code"] == two for r in SECTORS_20) else None


def sectors_20_frame() -> pl.DataFrame:
    return pl.DataFrame(SECTORS_20).with_columns(
        pl.lit(None, dtype=pl.Float64).alias("labor_cost_share"),
        pl.lit("to be filled by BEA input-output ingest (inventory row 24)").alias("note"),
    )


# 2020 Census apportionment: resident population, April 1, 2020 (50 states + DC).  Public domain.
# Transcribed from memory of the published apportionment table; the sum is asserted to equal the
# published U.S. resident population of 331,449,281 as a transcription check.  Any single state
# is believed accurate to well within 5%; the provenance record says so explicitly.
STATE_POP_2020: list[tuple[str, str, str, int]] = [
    ("01", "Alabama", "AL", 5_024_279), ("02", "Alaska", "AK", 733_391), ("04", "Arizona", "AZ", 7_151_502),
    ("05", "Arkansas", "AR", 3_011_524), ("06", "California", "CA", 39_538_223),
    ("08", "Colorado", "CO", 5_773_714), ("09", "Connecticut", "CT", 3_605_944),
    ("10", "Delaware", "DE", 989_948), ("11", "District of Columbia", "DC", 689_545),
    ("12", "Florida", "FL", 21_538_187), ("13", "Georgia", "GA", 10_711_908), ("15", "Hawaii", "HI", 1_455_271),
    ("16", "Idaho", "ID", 1_839_106), ("17", "Illinois", "IL", 12_812_508), ("18", "Indiana", "IN", 6_785_528),
    ("19", "Iowa", "IA", 3_190_369), ("20", "Kansas", "KS", 2_937_880), ("21", "Kentucky", "KY", 4_505_836),
    ("22", "Louisiana", "LA", 4_657_757), ("23", "Maine", "ME", 1_362_359), ("24", "Maryland", "MD", 6_177_224),
    ("25", "Massachusetts", "MA", 7_029_917), ("26", "Michigan", "MI", 10_077_331),
    ("27", "Minnesota", "MN", 5_706_494), ("28", "Mississippi", "MS", 2_961_279),
    ("29", "Missouri", "MO", 6_154_913), ("30", "Montana", "MT", 1_084_225), ("31", "Nebraska", "NE", 1_961_504),
    ("32", "Nevada", "NV", 3_104_614), ("33", "New Hampshire", "NH", 1_377_529),
    ("34", "New Jersey", "NJ", 9_288_994), ("35", "New Mexico", "NM", 2_117_522),
    ("36", "New York", "NY", 20_201_249), ("37", "North Carolina", "NC", 10_439_388),
    ("38", "North Dakota", "ND", 779_094), ("39", "Ohio", "OH", 11_799_448), ("40", "Oklahoma", "OK", 3_959_353),
    ("41", "Oregon", "OR", 4_237_256), ("42", "Pennsylvania", "PA", 13_002_700),
    ("44", "Rhode Island", "RI", 1_097_379), ("45", "South Carolina", "SC", 5_118_425),
    ("46", "South Dakota", "SD", 886_667), ("47", "Tennessee", "TN", 6_910_840), ("48", "Texas", "TX", 29_145_505),
    ("49", "Utah", "UT", 3_271_616), ("50", "Vermont", "VT", 643_077), ("51", "Virginia", "VA", 8_631_393),
    ("53", "Washington", "WA", 7_705_281), ("54", "West Virginia", "WV", 1_793_716),
    ("55", "Wisconsin", "WI", 5_893_718), ("56", "Wyoming", "WY", 576_851),
]
US_RESIDENT_POP_2020 = 331_449_281


def state_shares() -> pl.DataFrame:
    """fips, name, abbrev, pop_2020, state_share (sums to 1)."""
    total = sum(p for *_, p in STATE_POP_2020)
    if total != US_RESIDENT_POP_2020:
        raise AssertionError(f"state population transcription check failed: {total} != {US_RESIDENT_POP_2020}")
    df = pl.DataFrame(STATE_POP_2020, schema=["fips", "name", "abbrev", "pop_2020"], orient="row")
    return df.with_columns((pl.col("pop_2020") / total).alias("state_share"))


def allocate_integer(total: int, shares: list[float]) -> list[int]:
    """Largest-remainder allocation of ``total`` heads across ``shares`` (sums exactly to total)."""
    raw = [total * s for s in shares]
    base = [int(x) for x in raw]
    short = total - sum(base)
    order = sorted(range(len(raw)), key=lambda i: (raw[i] - base[i]), reverse=True)
    for i in order[:short]:
        base[i] += 1
    return base

"""Registry of every data source, transcribed from ``docs/data-inventory.md`` (v0.2, 2026-09-01).

Each entry records the name, URL, license, what it feeds, and the inventory's verification status
(``direct`` = primary page fetched; ``indirect`` = secondary confirmation; ``unverified``).
Nothing here is from memory: the row numbers match the inventory's dataset table.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    key: str
    name: str
    url: str
    license: str
    feeds: tuple[str, ...]
    verification: str = "indirect"
    inventory_row: int | None = None
    notes: str = ""
    extra_urls: tuple[str, ...] = field(default_factory=tuple)


SOURCES: dict[str, Source] = {
    s.key: s
    for s in [
        Source(
            "onet", "O*NET database 31.0 (Aug 2026)",
            "https://www.onetcenter.org/database.html", "CC BY 4.0",
            ("tasks.weight", "tasks.presence", "tasks.modality"), "indirect", 1,
            "O*NET-SOC 2019 is not one-to-one with SOC 2018; ratings refresh on a ~5-year cycle.",
        ),
        Source(
            "eloundou", "Eloundou, Manning, Mishkin, Rock — 'GPTs are GPTs' task labels",
            "https://github.com/openai/GPTs-are-GPTs", "MIT",
            ("tasks.exposure_label", "tasks.beta", "tasks.weight", "occupations", "clusters"), "direct", 2,
            "Labels are early-2023 capability; rubric '>=50% time reduction'; repo also mirrors "
            "OEWS May 2021 national and BLS EP 2020-30 files used for the Phase 1 partial tables.",
        ),
        Source(
            "aioe", "Felten, Raj, Seamans AIOE", "https://github.com/AIOE-Data/AIOE",
            "No license file (treat as all rights reserved)", ("cross-check only",), "direct", 3,
            "Cross-check only; never redistributed.",
        ),
        Source(
            "ilo", "ILO generative-AI exposure (Gmyrek et al. 2023; 2025 ILO-NASK update)",
            "https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf",
            "ILO knowledge products CC with attribution; score repo has no explicit license",
            ("cross-check only",), "direct", 4,
            extra_urls=("https://github.com/pgmyrek/2025_GenAI_scores_ISCO08",),
        ),
        Source(
            "imf", "IMF SDN/2024/001 (Cazzaniga et al.); WP/23/216 (Pizzinelli et al.)",
            "https://www.imf.org/en/publications/staff-discussion-notes/issues/2024/01/14/"
            "gen-ai-artificial-intelligence-and-the-future-of-work-542379",
            "IMF publication terms; no data license", ("cross-check only",), "indirect", 5,
            "Occupation-level index not published.",
        ),
        Source(
            "aei", "Anthropic Economic Index (dataset)",
            "https://huggingface.co/datasets/Anthropic/EconomicIndex", "Data CC BY; code MIT",
            ("tasks.theta anchoring (P.24)", "P.16 substitution share"), "indirect", 6,
            "HF folders through release_2026_03_24; taxonomy revised V1->V3.",
            extra_urls=("https://www.anthropic.com/research",),
        ),
        Source(
            "bls_oews", "BLS Occupational Employment and Wage Statistics (OEWS)",
            "https://www.bls.gov/oes/", "Public domain (U.S. Government work)",
            ("occupations", "occ_sector", "occ_state", "states"), "indirect", 7,
            "Latest May 2025 (15 May 2026); three-year pooled; excludes self-employed.",
        ),
        Source(
            "bls_ep", "BLS Employment Projections 2024-34", "https://www.bls.gov/emp/",
            "Public domain (U.S. Government work)", ("occupations.baseline_growth_10y",), "indirect", 7,
            "Released 28 Aug 2025. Phase 1 partial tables use the 2020-30 vintage mirrored in the "
            "GPTs-are-GPTs repository.",
        ),
        Source(
            "cps_ipums", "CPS via IPUMS", "https://cps.ipums.org/cps/",
            "IPUMS terms: registration, citation, no redistribution of extracts",
            ("cohorts (Phase 2)", "P.63", "P.67"), "indirect", 7,
        ),
        Source(
            "bls_jolts", "BLS JOLTS", "https://www.bls.gov/jlt/", "Public domain",
            ("validation",), "indirect", 7,
        ),
        Source(
            "btos", "Census Business Trends and Outlook Survey (AI question)",
            "https://www.census.gov/programs-surveys/btos.html", "Public domain",
            ("series/btos", "P.48", "P.49", "P.52"), "indirect", 8,
            "Question wording changed 17 Nov 2025: series break, fitted as two series.",
        ),
        Source(
            "ramp", "Ramp AI Index", "https://ramp.com/data/ai-index", "No data license found",
            ("cross-check only",), "indirect", 9,
        ),
        Source(
            "epoch", "Epoch AI: Notable Models, ECI, inference price trends",
            "https://epoch.ai/data/notable-ai-models", "Data CC BY 4.0; ECI code MIT",
            ("P.04", "P.07", "P.30"), "direct (ECI repo), indirect (site)", 10,
            extra_urls=("https://epoch.ai/eci", "https://epoch.ai/data-insights/llm-inference-price-trends"),
        ),
        Source(
            "metr", "METR time horizons (Kwa et al. 2025; Time Horizon 1.1, Jan 2026)",
            "https://metr.org/time-horizons/", "Repo says 'see LICENSE'; license text not retrieved",
            ("series/metr_horizons", "P.01", "P.28"), "direct (repo), indirect (blog)", 11,
            extra_urls=("https://github.com/METR/eval-analysis-public",),
        ),
        Source(
            "stanford_ai_index", "Stanford AI Index 2025, 2026",
            "https://hai.stanford.edu/ai-index/2026-ai-index-report",
            "Earlier editions CC BY-ND 4.0; 2025/2026 unverified", ("cross-check only",), "indirect", 12,
        ),
        Source(
            "artificial_analysis", "Artificial Analysis", "https://artificialanalysis.ai/data-api",
            "Free API internal use only; no redistribution", ("not used",), "indirect", 13,
        ),
        Source(
            "eurostat_lfs", "Eurostat LFS and national accounts; BLS SOC-ISCO crosswalk",
            "https://ec.europa.eu/eurostat/web/lfs/database",
            "Eurostat reuse with acknowledgement (Decision 2011/833/EU); BLS crosswalk public domain",
            ("EU labor layer (Phase 3)",), "indirect", 14,
            extra_urls=("https://www.bls.gov/soc/ISCO_SOC_Crosswalk.xls",),
        ),
        Source("ilostat", "ILOSTAT", "https://ilostat.ilo.org/", "Free with citation",
               ("Asia labor layer (Phase 3)",), "indirect", 15),
        Source(
            "oecd", "OECD TiVA, productivity, Skills for Jobs",
            "https://www.oecd.org/en/topics/sub-issues/trade-in-value-added.html", "CC BY 4.0 (from 1 Jul 2024)",
            ("P.45", "P.88"), "indirect", 16,
        ),
        Source(
            "national_stats_asia", "National statistics: China NBS, Japan e-Stat, Korea KOSIS, India PLFS, "
            "Taiwan DGBAS, Singapore MOM", "https://www.stats.gov.cn/", "Various (see inventory row 17)",
            ("Asia labor layer (Phase 3)",), "indirect", 17,
            extra_urls=("https://www.e-stat.go.jp/en", "https://kosis.kr/eng/",
                        "https://microdata.gov.in/NADA/index.php/catalog/PLFS",
                        "https://eng.stat.gov.tw/", "https://stats.mom.gov.sg/"),
        ),
        Source("cbo", "CBO, Distribution of Household Income 2022", "https://www.cbo.gov/publication/61911",
               "Public domain", ("P.86", "inequality (§6.6)"), "indirect", 18),
        Source(
            "sec_capex", "Hyperscaler capex (Microsoft, Alphabet, Amazon, Meta) — SEC EDGAR 10-K/10-Q/8-K",
            "https://www.sec.gov/edgar/search/", "Public filings", ("series/capex", "P.80", "P.81"), "indirect", 19,
            "Microsoft June fiscal year; Meta includes finance-lease principal.",
        ),
        Source(
            "regulatory", "Regulatory timeline (EU AI Act, U.S. states, China, export controls)",
            "https://eur-lex.europa.eu/eli/reg/2024/1689/oj", "Public record",
            ("series/regulatory_events", "P.30", "P.31"), "indirect", 20,
        ),
        Source(
            "natural_earth", "Natural Earth admin-0 and admin-1 (1:110m)",
            "https://www.naturalearthdata.com/", "Public domain", ("geo/us_states.geojson",), "direct (repo)", 21,
            extra_urls=("https://github.com/nvkelso/natural-earth-vector",),
        ),
        Source("scf", "Federal Reserve Survey of Consumer Finances 2022",
               "https://www.federalreserve.gov/econres/scfindex.htm", "Public domain",
               ("§6.4, §6.6",), "unverified in sandbox", 22),
        Source("bds", "Census Business Dynamics Statistics", "https://www.census.gov/programs-surveys/bds.html",
               "Public domain", ("P.52",), "unverified in sandbox", 23),
        Source("bea_io", "BEA Input-Output accounts", "https://www.bea.gov/industry/input-output-accounts-data",
               "Public domain", ("sectors.labor_cost_share",), "unverified in sandbox", 24),
        Source("cpi_weights", "BLS CPI relative importance weights",
               "https://www.bls.gov/cpi/tables/relative-importance/", "Public domain",
               ("sectors.consumption_share",), "unverified in sandbox", 25),
        Source("bls_ep_ai", "BLS EP methodology, AI adjustments", "https://www.bls.gov/emp/", "Public domain",
               ("baseline reconstruction (§7.6)",), "unverified", 26),
        Source("onet_work_context", "O*NET Work Context presence items (part of O*NET 31.0)",
               "https://www.onetcenter.org/database.html", "CC BY 4.0", ("tasks.presence",), "indirect", 27),
        Source("sec_margins", "Public gross margins (NVIDIA, TSMC, ASML, Microsoft, Alphabet, Amazon)",
               "https://www.sec.gov/edgar/search/", "Public filings; press estimates flagged E",
               ("P.85",), "indirect (NVIDIA 10-K FY2026 confirmed)", 28),
        Source("cps_matched", "CPS matched monthly files (occupation exits) via IPUMS",
               "https://cps.ipums.org/cps/", "IPUMS terms", ("P.63", "P.67"), "indirect", 29),
        Source("btos_young", "BTOS young-firm cut", "https://www.census.gov/programs-surveys/btos.html",
               "Public domain", ("P.52",), "indirect", 30),
        # Fixture-only source (not in the inventory): used for the Phase 1 state share proxy.
        Source(
            "census_apportionment_2020", "U.S. Census Bureau, 2020 Census apportionment — resident population by state",
            "https://www.census.gov/data/tables/2020/dec/2020-apportionment-data.html", "Public domain",
            ("states (FIXTURE proxy)", "occ_state (FIXTURE proxy)"), "transcribed from memory; not fetched",
            None, "Population share proxy for employment share; replaced by the OEWS state ingest.",
        ),
    ]
}


def get(key: str) -> Source:
    return SOURCES[key]


def by_table(table: str) -> list[Source]:
    """Sources whose ``feeds`` mention ``table`` (prefix match on the table name)."""
    return [s for s in SOURCES.values() if any(f.startswith(table) for f in s.feeds)]

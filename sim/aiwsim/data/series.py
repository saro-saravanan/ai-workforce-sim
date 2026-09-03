"""Time series transcribed verbatim from ``docs/data-inventory.md`` §3-§5 (2026-09-01).

Status of every table here: ``real (transcribed; secondary confirmation)``.  Values are not pulled
from the primary sources in this sandbox; the ingest scripts (``ingest/btos.py``) and later manual
checks replace them.  Where the inventory gives only a month, ``date_precision`` says ``month`` and
the date is the first of that month; approximate values ("~10%") carry a note.
"""

from __future__ import annotations

import polars as pl

TAG = "real (transcribed; secondary confirmation)"

# ---- Census BTOS, share of firms currently using AI (inventory §3) --------------------------------
# share_using_ai is a fraction (0.037 = 3.7%).
BTOS_ROWS = [
    # period_end, share, wording, weighting, date_precision, note
    ("2023-09-30", 0.037, "original", "firm", "month", "Sep 2023 reference period"),
    ("2024-02-29", 0.054, "original", "firm", "month", "Feb 2024 reference period"),
    ("2025-09-30", 0.10, "original", "firm", "month", "approximate ('~10%'), Sep 2025"),
    ("2025-11-30", 0.173, "business_functions", "firm", "month",
     "Nov 2025; first reading after the 17 Nov 2025 wording change"),
    ("2026-01-31", 0.18, "business_functions", "firm", "period",
     "Nov 2025-Jan 2026 pooled, firm-weighted"),
    ("2026-01-31", 0.32, "business_functions", "employment", "period",
     "Nov 2025-Jan 2026 pooled, employment-weighted"),
    ("2026-05-03", 0.198, "business_functions", "firm", "day",
     "period ending 3 May 2026; sector cuts: Information 39.7%, Finance and Insurance 33.9%"),
]


def btos() -> pl.DataFrame:
    return pl.DataFrame(
        BTOS_ROWS,
        schema=["period_end", "share_using_ai", "wording", "weighting", "date_precision", "note"],
        orient="row",
    ).with_columns(pl.lit(TAG).alias("source_tag")).select(
        "period_end", "share_using_ai", "wording", "weighting", "source_tag", "date_precision", "note"
    )


# ---- METR 50% time horizons (inventory §3) --------------------------------------------------------
METR_ROWS = [
    # model, date, p50 minutes, ci_low, ci_high, date_precision, note
    ("Claude Mythos Preview", "2026-03-01", 960.0, 510.0, 3300.0, "month",
     ">= 16 h (lower bound; 95% CI 8.5-55 h); inventory row 11 lists METR's release for it as 8 May 2026"),
    ("GPT-5.6 Sol", "2026-06-26", 678.0, 300.0, 2400.0, "day", "~11.3 h (CI 5-40 h)"),
    ("GPT-5", "2025-08-01", 137.0, None, None, "month", "~2 h 17 min; CI not recorded in inventory"),
]
METR_DOUBLING_NOTES = (
    "Doubling time: ~7 months (2019-2025, original paper); ~4 months (2024-2025 subset); "
    "Time Horizon 1.1 (Jan 2026): 6.3 months all-time, 4.3 months since 2023, ~3 months since 2024. "
    "Only 5 of 228 tasks >= 16 h, so horizons above ~8 h are unstable; software-specific."
)


def metr_horizons() -> pl.DataFrame:
    return pl.DataFrame(
        METR_ROWS,
        schema={"model": pl.Utf8, "date": pl.Utf8, "horizon_minutes_p50": pl.Float64,
                "ci_low_minutes": pl.Float64, "ci_high_minutes": pl.Float64,
                "date_precision": pl.Utf8, "note": pl.Utf8},
        orient="row",
    ).with_columns(pl.lit(TAG).alias("source_tag")).select(
        "model", "date", "horizon_minutes_p50", "ci_low_minutes", "ci_high_minutes", "source_tag",
        "date_precision", "note",
    )


# ---- Hyperscaler capex, USD bn (inventory §4) -----------------------------------------------------
CAPEX_ROWS = [
    # company, year, capex, basis, low, high, note
    ("Microsoft", 2024, 56.0, "fiscal", None, None, "FY ending Jun 2024; incl. finance leases; approximate"),
    ("Microsoft", 2024, 76.0, "calendar", None, None, "calendar 2024; incl. finance leases; approximate"),
    ("Microsoft", 2025, 88.0, "fiscal", None, None, "FY ending Jun 2025; incl. finance leases; approximate"),
    ("Microsoft", 2025, 118.0, "calendar", None, None, "calendar 2025; incl. finance leases; approximate"),
    ("Microsoft", 2026, 175.0, "guidance", None, None, "Jul 2026 guidance, calendar basis; approximate"),
    ("Alphabet", 2024, 52.5, "fiscal", None, None, ""),
    ("Alphabet", 2025, 91.4, "fiscal", None, None, ""),
    ("Alphabet", 2026, 200.0, "guidance", 195.0, 205.0, "Jul 2026 guidance range 195-205; midpoint"),
    ("Amazon", 2024, 83.0, "fiscal", None, None, ""),
    ("Amazon", 2025, 131.8, "fiscal", None, None, ""),
    ("Amazon", 2026, 220.0, "guidance", None, None, "Jul 2026 guidance; approximate"),
    ("Meta", 2024, 39.2, "fiscal", None, None, "incl. finance-lease principal"),
    ("Meta", 2025, 72.2, "fiscal", None, None, "incl. finance-lease principal"),
    ("Meta", 2026, 137.5, "guidance", 130.0, 145.0, "Jul 2026 guidance range 130-145; midpoint"),
]
CAPEX_SUM_NOTES = (
    "Inventory sums: 2024 ~230 (MSFT FY basis) to ~250 (calendar); 2025 ~384 (FY) to ~413 (calendar); "
    "2026 guidance ~720-760."
)


def capex() -> pl.DataFrame:
    return pl.DataFrame(
        CAPEX_ROWS,
        schema={"company": pl.Utf8, "year": pl.Int64, "capex_bn_usd": pl.Float64, "basis": pl.Utf8,
                "capex_bn_usd_low": pl.Float64, "capex_bn_usd_high": pl.Float64, "note": pl.Utf8},
        orient="row",
    ).with_columns(pl.lit(TAG).alias("source_tag")).select(
        "company", "year", "capex_bn_usd", "basis", "source_tag", "capex_bn_usd_low", "capex_bn_usd_high", "note"
    )


# ---- Regulatory timeline (inventory §5) -----------------------------------------------------------
REG_ROWS = [
    # event_id, region, date, kind, description, date_precision
    ("EU-AIA-01", "EU", "2024-08-01", "in_force", "EU AI Act, Reg. (EU) 2024/1689, enters into force", "day"),
    ("EU-AIA-02", "EU", "2025-02-02", "obligation_start", "EU AI Act prohibitions apply", "day"),
    ("EU-AIA-03", "EU", "2025-08-02", "obligation_start", "EU AI Act GPAI and governance obligations apply", "day"),
    ("EU-AIA-04", "EU", "2026-08-02", "superseded",
     "EU AI Act Annex III high-risk obligations, original application date (superseded by EU-AIA-05)", "day"),
    ("EU-AIA-05", "EU", "2026-07-24", "published",
     "Digital Omnibus on AI, Reg. (EU) 2026/1744, published in the Official Journal", "day"),
    ("EU-AIA-06", "EU", "2026-07-27", "in_force", "Digital Omnibus on AI enters into force", "day"),
    ("EU-AIA-07", "EU", "2027-12-02", "obligation_start",
     "EU AI Act Annex III high-risk obligations apply (moved by the Digital Omnibus)", "day"),
    ("EU-AIA-08", "EU", "2028-08-02", "obligation_start",
     "EU AI Act Annex I high-risk obligations apply (moved by the Digital Omnibus)", "day"),
    ("US-CO-01", "US-CO", "2026-06-30", "delay", "Colorado SB 24-205 effective date delayed to 30 Jun 2026", "day"),
    ("US-CO-02", "US-CO", "2026-05-14", "signed",
     "Colorado SB 26-189 signed, repealing and replacing SB 24-205", "day"),
    ("US-CO-03", "US-CO", "2027-01-01", "effective", "Colorado SB 26-189 effective", "day"),
    ("US-CA-01", "US-CA", "2025-09-29", "signed", "California SB 53 signed (frontier models above 10^26 FLOP)", "day"),
    ("US-CA-02", "US-CA", "2026-01-01", "effective", "California SB 53 operative", "day"),
    ("CN-GAI-01", "CN", "2023-07-10", "issued", "Interim Measures for Generative AI Services issued", "day"),
    ("CN-GAI-02", "CN", "2023-08-15", "effective",
     "Interim Measures for Generative AI Services effective; security assessment and algorithm filing", "day"),
    ("CN-GAI-03", "CN", "2026-06-30", "milestone", "988 generative AI services fully filed", "day"),
    ("US-EXP-01", "US", "2022-10-07", "export_control", "BIS advanced computing and semiconductor rule", "day"),
    ("US-EXP-02", "US", "2023-10-17", "export_control", "BIS updated advanced computing rule", "day"),
    ("US-EXP-03", "US", "2025-01-13", "export_control", "BIS AI Diffusion rule issued", "day"),
    ("US-EXP-04", "US", "2025-05-13", "export_control", "AI Diffusion rule rescission announced", "day"),
    ("US-EXP-05", "US", "2025-04-01", "export_control", "H20 license requirement imposed", "month"),
    ("US-EXP-06", "US", "2025-08-01", "export_control",
     "H20 export licenses granted with a 15% revenue expectation", "month"),
    ("US-EXP-07", "US", "2025-12-08", "export_control", "H200 exports to China approved with a 25% revenue share", "day"),
    ("US-EXP-08", "US", "2026-01-15", "export_control", "BIS case-by-case licensing rule effective", "day"),
    ("US-EXP-09", "CN", "2026-08-26", "milestone",
     "First H200 sales to China reported after Chinese customs had blocked imports", "day"),
]


def regulatory_events() -> pl.DataFrame:
    return pl.DataFrame(
        REG_ROWS, schema=["event_id", "region", "date", "kind", "description", "date_precision"], orient="row"
    ).with_columns(pl.lit(TAG).alias("source_tag")).select(
        "event_id", "region", "date", "kind", "description", "source_tag", "date_precision"
    )


BACKTEST_NOTES = ("Observed series the model is scored against for 2024Q1-2026Q2 (review §2.2). model_metric names the model quantity: "
                  "adoption_share_firm_weighted (BTOS share of firms using AI), ai_layoffs_cum (announced AI-cited job cuts since 2023; the model's laid_off_cum "
                  "plus the 2023 count that precedes the horizon), ai_producer_revenue_bn (world), hyperscaler_capex_bn (the capex path, an input), none (context only: "
                  "the model does not track the quantity). used_in_fit marks rows that were used to set a parameter.")


def backtest() -> pl.DataFrame:
    """Backtest targets (transcribed; see BACKTEST_NOTES and docs/data-inventory.md)."""
    rows = [
        # BTOS: share of firms using AI in producing goods or services (original wording) / in business functions (from 17 Nov 2025)
        ("btos_firm", "Firms using AI (BTOS, %)", "2024Q1", 5.4, "% of firms", "adoption_share_firm_weighted", "Census BTOS, Feb 2024 reference period", "real (transcribed; secondary confirmation)", 1),
        ("btos_firm", "Firms using AI (BTOS, %)", "2025Q3", 10.0, "% of firms", "adoption_share_firm_weighted", "Census BTOS, Sep 2025 (~10%)", "real (transcribed; approximate)", 1),
        ("btos_firm", "Firms using AI (BTOS, %)", "2025Q4", 17.3, "% of firms", "adoption_share_firm_weighted", "Census BTOS, Nov 2025, business-functions wording (not comparable with earlier rows)", "real (transcribed; wording change)", 1),
        ("btos_firm", "Firms using AI (BTOS, %)", "2026Q1", 18.0, "% of firms", "adoption_share_firm_weighted", "Census BTOS, Nov 2025-Jan 2026 pooled", "real (transcribed; wording change)", 1),
        # Challenger, Gray & Christmas: announced job cuts citing AI, cumulative since 2023
        ("challenger_ai_cum", "Announced AI-cited job cuts since 2023 (Challenger)", "2023Q4", 3900.0, "cuts", "ai_layoffs_cum", "Challenger 2023 total (before the model horizon; carried as the offset)", "real (transcribed; secondary confirmation)", 0),
        ("challenger_ai_cum", "Announced AI-cited job cuts since 2023 (Challenger)", "2024Q4", 16989.0, "cuts", "ai_layoffs_cum", "Challenger 2024 total 13,089 plus 2023", "real (transcribed; secondary confirmation)", 0),
        ("challenger_ai_cum", "Announced AI-cited job cuts since 2023 (Challenger)", "2025Q4", 71825.0, "cuts", "ai_layoffs_cum", "Challenger 2025 total 54,836 plus prior", "real (transcribed; report)", 1),
        ("challenger_ai_cum", "Announced AI-cited job cuts since 2023 (Challenger)", "2026Q2", 173568.0, "cuts", "ai_layoffs_cum", "Challenger cumulative since 2023 through June 2026", "real (transcribed; report)", 1),
        # AI producers' revenue, world
        ("ai_revenue", "AI industry revenue (world, $bn/yr)", "2025Q4", 60.0, "$bn/yr", "ai_producer_revenue_bn", "OpenAI $13.1bn (FT-verified), Anthropic ~$5bn, Microsoft and Google AI lines, Menlo Ventures enterprise estimate; range 45-80", "press summaries (V: secondary)", 1),
        ("ai_revenue", "AI industry revenue (world, $bn/yr)", "2026Q4", 140.0, "$bn/yr", "ai_producer_revenue_bn", "run rates mid-2026 (OpenAI ~$40bn, Anthropic ~$47bn gross) and market estimates; range 90-200", "press summaries (V: secondary; run rates)", 1),
        # Hyperscaler capex (input path)
        ("capex", "Hyperscaler capex, four companies ($bn/yr)", "2024Q4", 250.7, "$bn/yr", "hyperscaler_capex_bn", "company reports (data/processed/series/capex.csv)", "real (transcribed; secondary confirmation)", 1),
        ("capex", "Hyperscaler capex, four companies ($bn/yr)", "2025Q4", 413.4, "$bn/yr", "hyperscaler_capex_bn", "company reports", "real (transcribed; secondary confirmation)", 1),
        ("capex", "Hyperscaler capex, four companies ($bn/yr)", "2026Q4", 732.5, "$bn/yr", "hyperscaler_capex_bn", "July 2026 guidance", "real (transcribed; guidance)", 1),
        # context only: the model does not track these
        ("grad_unemployment", "Unemployment rate, recent college graduates 22-27 (NY Fed, %)", "2025Q2", 4.8, "%", "none", "NY Fed, The Labor Market for Recent College Graduates", "real (transcribed; secondary confirmation)", 0),
        ("grad_unemployment", "Unemployment rate, recent college graduates 22-27 (NY Fed, %)", "2025Q4", 5.7, "%", "none", "NY Fed", "real (transcribed; secondary confirmation)", 0),
        ("grad_unemployment", "Unemployment rate, recent college graduates 22-27 (NY Fed, %)", "2026Q1", 5.6, "%", "none", "NY Fed", "real (transcribed; secondary confirmation)", 0),
        ("grad_unemployment", "Unemployment rate, recent college graduates 22-27 (NY Fed, %)", "2026Q2", 5.6, "%", "none", "NY Fed", "real (transcribed; secondary confirmation)", 0),
        ("indeed_software", "Software development job postings, Indeed index (Feb 2020 = 100)", "2026Q1", 70.9, "index", "none", "Indeed Hiring Lab via FRED (IHLIDXUSTPSOFTDEVE), 13 Mar 2026", "real (transcribed; single point)", 0),
    ]
    return pl.DataFrame(rows, schema=["series_id", "label", "quarter", "value", "unit", "model_metric", "source", "source_tag", "used_in_fit"], orient="row")

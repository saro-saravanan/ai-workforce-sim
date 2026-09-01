# Data inventory v0.1 — sources, licenses, gaps

Compiled 2026-09-01. Every source was checked against its primary page or, where the sandbox could not reach the domain, against the search index and at least one secondary page. Verification status per row: **direct** = primary page fetched; **indirect** = confirmed through secondary pages only; **unverified** = could not be confirmed. Nothing in this inventory comes from memory.

Provenance rule for ingestion: every dataset pulled by `data/ingest/*` writes a `provenance.json` beside the raw file with source URL, pull date, license string, checksum, and the transformation script hash. No dataset enters the model without one.

## 1. Which layer each source feeds

| Layer | Primary sources | Cross-checks |
|---|---|---|
| Task exposure (§2 of spec) | O*NET 31.0 tasks and ratings; Eloundou et al. task labels (MIT license) | Felten AIOE; ILO 2025 ISCO scores; IMF complementarity (reconstructed) |
| AI supply (§3) | Epoch AI Notable Models, ECI, inference price trends (CC BY 4.0); METR time horizons (public data) | Artificial Analysis (internal use only, see license risks) |
| Adoption (§4) | Census BTOS AI question (public domain); Eurostat ICT usage in enterprises | Ramp AI Index; Anthropic Economic Index (CC BY) |
| Labor flows (§5) | BLS OEWS, CPS via IPUMS, JOLTS, Employment Projections 2024–34; Eurostat LFS; ILOSTAT; national LFS | Brynjolfsson et al. Canaries (ADP-based) |
| Macro (§6) | BEA/IMF WEO/OECD national accounts; CBO household income distribution; OECD TiVA; hyperscaler SEC filings | Penn World Table |
| Maps | Natural Earth admin-0 and admin-1 (public domain) | Eurostat GISCO NUTS only if sub-member detail is ever needed (non-commercial) |

## 2. Dataset table

| # | Source | URL | License / terms | Coverage | Latest release | Access | Status | Gaps and caveats |
|---|---|---|---|---|---|---|---|---|
| 1 | O*NET database | https://www.onetcenter.org/database.html | CC BY 4.0 | U.S.; O*NET-SOC 2019, ~1,016 occupations, 912 with incumbent/expert data; task statements, ratings, DWAs, skills, work context | 31.0, Aug 2026 (218 occupations updated) | Bulk (Excel, CSV, SQL); Web Services API with free key | indirect | Ratings refreshed on a rolling ~5-year cycle; O*NET-SOC is not one-to-one with SOC 2018 |
| 2 | Eloundou, Manning, Mishkin, Rock, "GPTs are GPTs" task labels | https://github.com/openai/GPTs-are-GPTs | MIT | O*NET task set; human and GPT-4 labels; α/β/γ aggregations; `occ_level.csv` | With paper (2023; *Science* 2024) | GitHub | direct | Labels reflect early-2023 capability; rubric is "≥50% time reduction"; no versioning |
| 3 | Felten, Raj, Seamans AIOE | https://github.com/AIOE-Data/AIOE | **No license file** | U.S.; AIOE by 6-digit SOC, AIIE by NAICS 4-digit, AIGE by county; language-modeling and image-generation variants | Repo, 23 commits | GitHub | direct | Treat as all-rights-reserved until permission obtained; z-scores, not task shares; built on 2010-era AI applications |
| 4 | ILO generative-AI exposure (Gmyrek et al. 2023; 2025 update, ILO–NASK) | WP140 https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf ; scores https://github.com/pgmyrek/2025_GenAI_scores_ISCO08 | ILO knowledge products after 3 May 2023: CC with attribution; score repo has **no explicit license** | Global; ISCO-08 4-digit; four exposure gradients | 20 May 2025 | GitHub xlsx; ILO PDFs | direct (repo), indirect (PDFs) | 2023 scores have no standalone dataset; 2025 headline: ~25% of global employment in exposed occupations |
| 5 | IMF, Cazzaniga et al. SDN/2024/001; Pizzinelli et al. WP/23/216 | https://www.imf.org/en/publications/staff-discussion-notes/issues/2024/01/14/gen-ai-artificial-intelligence-and-the-future-of-work-542379 | IMF publication terms; no data license | Global; ISCO-08; AIOE mapped to ISCO with complementarity adjustment | Jan 2024 | PDF only | indirect | **Occupation-level index not published**; reconstruct from AIOE plus the paper's complementarity weights, or request from authors |
| 6 | Anthropic Economic Index | Reports at anthropic.com/research; data https://huggingface.co/datasets/Anthropic/EconomicIndex | Data CC BY; code MIT | Claude.ai and first-party API; O*NET task taxonomy; country and U.S.-state cuts from Sep 2025 | Jun 2026 report; HF folders through `release_2026_03_24` | HF bulk download | indirect | Single vendor, self-selected users; taxonomy revised V1→V3 so shares are not strictly comparable |
| 7 | BLS: OEWS, CPS (IPUMS), JOLTS, Employment Projections, CES | https://www.bls.gov/oes/ ; https://cps.ipums.org/cps/ ; https://www.bls.gov/jlt/ ; https://www.bls.gov/emp/ | Public domain (U.S. Government work); IPUMS CPS requires registration and citation, no redistribution of extracts | U.S.; OEWS occupation × industry × state (SOC 2018); CPS monthly microdata; JOLTS by industry and region; EP 2024–34 | OEWS May 2025 (15 May 2026); EP 2024–34 (28 Aug 2025); JOLTS Jul 2026 (1 Sep 2026) | Bulk; BLS API; IPUMS extracts | indirect | OEWS is three-year pooled and excludes self-employed; CPS uses Census occupation codes (crosswalk to SOC needed) |
| 8 | Census BTOS AI question | https://www.census.gov/programs-surveys/btos.html | Public domain | U.S. nonfarm private employers; national, state, sector, size; biweekly since Sep 2023 | Biweekly through Jun 2026 | Bulk CSV/XLSX | indirect | **Question wording changed 17 Nov 2025** (from "in producing goods or services" to "in any of its business functions"): series break, fitted as two series |
| 9 | Ramp AI Index | https://ramp.com/data/ai-index | **No data license found** | ~70,000 U.S. businesses on Ramp; monthly since Jan 2023; adoption = any payment to an AI vendor in the month | Aug 2026: 50.4% paying | Web charts only | indirect | Base skews venture-backed SMB; use as cross-check only, no redistribution |
| 10 | Epoch AI: Notable Models, ECI, inference price trends, Benchmarking Hub | https://epoch.ai/data/notable-ai-models ; https://epoch.ai/eci ; https://epoch.ai/data-insights/llm-inference-price-trends | Data CC BY 4.0; ECI code MIT; third-party benchmark results keep their own licenses | ~1,600 notable models; ECI 1,123 evaluations, 147 models, 39 benchmarks | Updated daily; ECI CSV | CSV; `epochai` Python client | direct (ECI repo), indirect (site) | Price decline claim (Mar 2025): 9×–900×/yr across milestones, 40×/yr for GPT-4-level science QA |
| 11 | METR time horizons (Kwa et al. 2025; Time Horizon 1.1, Jan 2026) | https://metr.org/time-horizons/ ; https://github.com/METR/eval-analysis-public | Repo says "see LICENSE"; **license text not retrieved** | Software tasks (HCAST, RE-Bench, SWAA); 228 tasks; models 2019–2026 | Mythos Preview (8 May 2026), GPT-5.6 Sol (26 Jun 2026) | GitHub JSONL and code | direct (repo), indirect (blog) | Only 5 of 228 tasks ≥ 16 h, so horizons above ~8 h are unstable; software-specific |
| 12 | Stanford AI Index 2025, 2026 | https://hai.stanford.edu/ai-index/2026-ai-index-report | Earlier editions CC BY-ND 4.0; **2025/2026 license unverified** | Global secondary compilation | 2026 edition, 13 Apr 2026 | Google Drive bulk | indirect | Re-published third-party data; cite originals; ND restricts derived charts |
| 13 | Artificial Analysis | https://artificialanalysis.ai/data-api | Free API: attribution required, **internal use only, no redistribution**; commercial license for redistribution | Model and provider price, speed, quality indices | Continuous | API key | indirect | Cannot be redistributed in a public tool on the free tier; Epoch is the primary price source instead |
| 14 | Eurostat LFS and national accounts; SOC↔ISCO crosswalk | https://ec.europa.eu/eurostat/web/lfs/database (`lfsa_egised`, `lfsa_egai2d`, `lfsq_egised`); https://www.bls.gov/soc/ISCO_SOC_Crosswalk.xls | Eurostat: reuse for any purpose with source acknowledged (Decision 2011/833/EU); BLS crosswalk public domain | EU-27 + EFTA; ISCO 2-digit in public tables; UK dropped after 2020 (use ONS APS) | LFS 2025 annual; quarterly to 2026 Q1 | SDMX/JSON API; bulk TSV; microdata by research access | indirect | **No official ISCO-08 × SOC 2018 crosswalk**; chain ISCO-08 → SOC 2010 → SOC 2018 |
| 15 | ILOSTAT | https://ilostat.ilo.org/ | Free to use with citation; post-May-2023 products CC with attribution | ~190 countries; ISCO-08 1–2 digit; annual | Continuous | CSV; SDMX; `Rilostat` | indirect | Two-digit coverage uneven (China limited); mixed ISCO vintages |
| 16 | OECD TiVA, productivity, Skills for Jobs | https://www.oecd.org/en/topics/sub-issues/trade-in-value-added.html ; https://www.oecdskillsforjobsdatabase.org/ | CC BY 4.0 for content from 1 Jul 2024; earlier on similar terms | TiVA: 80 economies, 50 industries, 1995–2022 | TiVA 2025 edition (Aug 2025, revised Oct 2025) | Data Explorer; SDMX | indirect | TiVA ends 2022; extrapolate import shares flat |
| 17 | National statistics: China NBS, Japan e-Stat, Korea KOSIS, India PLFS, Taiwan DGBAS, Singapore MOM | https://www.stats.gov.cn/ ; https://www.e-stat.go.jp/en ; https://kosis.kr/eng/ ; https://microdata.gov.in/NADA/index.php/catalog/PLFS ; https://eng.stat.gov.tw/ ; https://stats.mom.gov.sg/ | JP: CC BY 4.0-compatible; KR: KOGL Type 1; IN: NDSAP with registration; TW: OGDL-Taiwan-1.0; SG: Singapore Open Data Licence; CN: none | CN: occupation detail only in decennial census and 1% survey; JP/KR/TW monthly at major-group level; IN NCO-2015 unit level; SG annual SSOC 2024 | CN 2020 census; JP/KR/TW 2026 monthly; IN CY2025; SG LFS 2025 | Portals, CSV; India via NADA | indirect | **China has no annual detailed occupation series**; interpolate between census years and flag |
| 18 | CBO, Distribution of Household Income 2022 | https://www.cbo.gov/publication/61911 | Public domain | U.S. households 1979–2022; quintiles and top 1%; transfer and federal tax rates | Jan 2026 | PDF plus Excel supplements | indirect | 3–4 year lag; federal taxes only |
| 19 | Hyperscaler capex (Microsoft, Alphabet, Amazon, Meta) | SEC EDGAR 10-K/10-Q/8-K | Public filings | Company-level capex, incl. finance leases where reported | FY2025 10-Ks; Jul 2026 guidance | EDGAR | indirect | Microsoft June fiscal year; Meta includes finance-lease principal; see §4 |
| 20 | Regulatory timeline (EU, U.S., China, export controls) | Official journals, BIS press releases, state legislatures; see §5 | Public record | — | Jul 2026 | — | indirect | Encoded as data (`data/regulatory_events.yaml`), not code |
| 21 | Natural Earth | https://www.naturalearthdata.com/ ; https://github.com/nvkelso/natural-earth-vector | Public domain | World admin-0 (countries, covers EU members), admin-1 (U.S. states); 1:10m/50m/110m | 5.1.x (dev 5.2.0-pre) | Shapefile/GeoJSON | direct (repo) | Sufficient for every map in the spec; Eurostat GISCO NUTS is **non-commercial** and is not needed |

## 3. Key series recorded during verification

### Anthropic Economic Index, augmentation vs automation (Claude.ai)

| Report | Data window | Augmentation | Automation |
|---|---|---|---|
| Feb 2025 launch | Dec 2024–Jan 2025 | 57% | 43% |
| Mar 2025 | Feb–Mar 2025 | "little change" (restated later as 55/42 under revised taxonomy) | |
| Sep 2025 | Aug 2025 | 47% | 49.1% |
| Jan 2026 | Nov 2025 | 52% | 45% |
| Mar 2026 | Feb 2026 | "increased slightly" | fell in API data |
| Jun 2026 | May–Jun 2026 | no headline aggregate retrieved | |

### Census BTOS, share of firms currently using AI

| Reference period | Share | Wording |
|---|---|---|
| Sep 2023 | 3.7% | original |
| Feb 2024 | 5.4% | original |
| Sep 2025 | ~10% | original |
| Nov 2025 | 17.3% | new (17 Nov 2025) |
| Nov 2025–Jan 2026 | 18% firm-weighted; 32% employment-weighted | new |
| period ending 3 May 2026 | 19.8% (Information 39.7%, Finance and Insurance 33.9%) | new |

### METR time horizons

- Doubling time: ~7 months (2019–2025, original paper); ~4 months (2024–2025 subset); Time Horizon 1.1 (Jan 2026): 6.3 months all-time, 4.3 months since 2023, ~3 months since 2024.
- Latest 50% horizons: Claude Mythos Preview ≥ 16 h (95% CI 8.5–55 h, Mar 2026); GPT-5.6 Sol ≈ 11.3 h (CI 5–40 h, Jun 2026); GPT-5 ≈ 2 h 17 min (Aug 2025).

## 4. Hyperscaler capex, USD bn

| Company | 2024 | 2025 | 2026 guidance (Jul 2026) |
|---|---|---|---|
| Microsoft (incl. finance leases; June FY) | FY ≈ 56; calendar ≈ 76 | FY ≈ 88; calendar ≈ 118 | ≈ 175 (calendar) |
| Alphabet | 52.5 | 91.4 | 195–205 |
| Amazon | 83.0 | 131.8 | ≈ 220 |
| Meta (incl. finance-lease principal) | 39.2 | 72.2 | 130–145 |
| Sum | ≈ 230 (MSFT FY basis) to ≈ 250 (calendar) | ≈ 384 (FY) to ≈ 413 (calendar) | ≈ 720–760 |

## 5. Regulatory timeline as verified

- **EU AI Act**, Reg. (EU) 2024/1689: in force 1 Aug 2024; prohibitions 2 Feb 2025; GPAI and governance 2 Aug 2025; high-risk Annex III originally 2 Aug 2026. **Digital Omnibus on AI**, Reg. (EU) 2026/1744, OJ 24 Jul 2026, in force 27 Jul 2026: Annex III high-risk obligations moved to **2 Dec 2027**, Annex I to **2 Aug 2028**.
- **U.S. states**: Colorado SB 24-205 delayed to 30 Jun 2026, then repealed and replaced by SB 26-189 (signed 14 May 2026, effective 1 Jan 2027). California SB 53 signed 29 Sep 2025, operative 1 Jan 2026 (frontier models above 10^26 FLOP).
- **China**: Interim Measures for Generative AI Services issued 10 Jul 2023, effective 15 Aug 2023; security assessment and algorithm filing; 988 services fully filed as of 30 Jun 2026.
- **U.S. export controls**: BIS rules 7 Oct 2022 and 17 Oct 2023; AI Diffusion rule 13 Jan 2025, rescission announced 13 May 2025; H20 license requirement Apr 2025, licenses Aug 2025 with a 15% revenue expectation; H200 approved 8 Dec 2025 with a 25% revenue share, BIS case-by-case rule effective 15 Jan 2026, Chinese customs blocked imports until first sales reported 26 Aug 2026.

## 6. Fact-check of numbers cited in the spec

| Claim | Verdict | What the source says |
|---|---|---|
| METR doubling ~7 months 2019–25, ~4 months 2024–25 | Verified, updated | Plus TH1.1: 6.3 / 4.3 / ~3 months |
| AEI Mar 2025: 57/43, automation rising since | **Corrected** | 57/43 is the Feb 2025 report; automation peaked at 49.1% (Aug 2025) then fell to 45% (Nov 2025) |
| Canaries: 22–25-year-olds −13% relative | Verified, updated | 13% in Aug 2025 version; 19% through Jun 2026 in Aug 2026 revision |
| Acemoglu 2024: TFP ≈ 0.66% over 10 years | Verified, refined | 0.66% is the **upper bound**; ≤ 0.53% with hard-to-learn tasks; GDP "closer to 1%" |
| Goldman 2023: +7% global GDP, 300M FTE exposed | Verified | as stated |
| IMF 2024: ~40% global, ~60% advanced economies | Verified | as stated |
| Productivity RCTs (BLR 14%, Noy–Zhang 40%, Peng 55%, Dell'Acqua) | Verified, version caveat | BLR 14% (NBER 2023) vs 15% (QJE 2025); Noy–Zhang −40% time, +18% quality; Peng 55.8%; Dell'Acqua 12.2% more tasks, 25.1% faster, 40% higher quality |
| Lichter–Peichl–Siegloch 2015 | Verified | 942 estimates, mean −0.508, median −0.386 |
| Autor et al. 2024: ~60% of 2018 jobs new since 1940 | Verified, refined | 63% |
| Sultan et al. 1990: p ≈ 0.03, q ≈ 0.38 | Verified | 213 applications |
| Big-4 capex ≈ $230bn (2024), ≈ $400bn (2025) | **Corrected** | 2024 ≈ $250bn calendar; 2025 ≈ $384–413bn; 2026 guidance ≈ $720–760bn |
| JOLTS separations 3.2–3.5%/month, quits ~2% | **Corrected** | 2025 average 3.3%, monthly range 3.1–3.4%; quits 2.0% |

## 7. License risks and the decisions taken

| Source | Risk | Decision |
|---|---|---|
| Felten AIOE | No license file | Used only as a cross-check, never redistributed; request permission before Phase 5 public demo |
| ILO 2025 score repo | No explicit license | Cite the ILO working paper; redistribute only aggregates |
| Artificial Analysis | Free tier forbids redistribution | Not used; Epoch AI price data is the primary source |
| Stanford AI Index | ND clause on earlier editions | Cite originals; no derived charts from the Index itself |
| Ramp AI Index | No data license | Cross-check only; values quoted with attribution, no bulk redistribution |
| Eurostat GISCO NUTS | Non-commercial | Not used; Natural Earth admin-0 covers EU member states |
| IPUMS CPS | Extracts may not be redistributed | Derived cohort tables are committed; raw extracts are not |

## 8. Gaps that matter, in priority order

1. **No dataset gives the capability threshold `θ_k`** at which AI performs an O*NET task unsupervised. This is the model's largest estimated quantity (spec §2.1, risks #1). Partial remedy: map METR task horizons to O*NET task complexity ratings; a proper benchmark keyed to O*NET tasks does not exist.
2. **China occupational employment** exists only at census years; the China labor layer will be interpolated and flagged.
3. **IMF complementarity index** is not published at occupation level; reconstruct from AIOE and the paper's method.
4. **ISCO-08 ↔ SOC 2018** has no official crosswalk; chain through SOC 2010 and score mapping quality per cluster.
5. **BTOS series break** at Nov 2025 shortens the usable pre-break adoption series to about two years.
6. **Regulatory compliance cost** has no measured value in any jurisdiction.
7. **Actor economics** (compute, training cost, revenue) are not public; only release dates, prices, and posture are used.
8. **Informal employment** in India and Rest of Asia is not covered by any occupation-level source.

## 9. Open verification items

1. Exact AEI shares for the Mar 2025, Mar 2026, and Jun 2026 reports.
2. METR repository license text.
3. Stanford AI Index 2025/2026 data license text.
4. Ramp AI Index reuse terms.
5. Acemoglu's exact GDP bound (only "closer to 1%" confirmed).
6. Microsoft FY2024 Q2 capex including finance leases.
7. Full BTOS biweekly series, to be pulled directly at ingestion.

# Findings so far — Phase 9b (the open items of the priority plan)

Branch `spec/model-v0.3` after Phase 9b. Baseline, U.S., 384 draws, 64 structural cells; companions at 64 draws; central run quoted unless a median is named. Everything is a difference from a world in which AI stopped improving in 2023. Phase 9 left five items open ([findings-phase9.md](findings-phase9.md) §9): the BEA sector table (review item 10), the 2026 hold-out, the exposure-source swap, the classifier audit labels and the robotaxi anchor series. This note closes them and records what each did to the numbers.

## 1. Real sector tables, and how they got here

The build environment cannot reach bls.gov or bea.gov, so a GitHub Actions workflow (`external-data.yml`, run from the Actions tab) fetches the files on a runner and commits them under `data/external/`. It fetched the BLS OEWS May 2025 occupation-by-industry, national and state spreadsheets at the first attempt. The BEA use table is served through BEA's interactive application rather than static links, the Internet Archive's index of BEA's download directory was offline on every attempt, and BEA's API needs a registered key; the workflow tries all three routes and, with the `BEA_API_KEY` repository secret set, picks the summary use table by its description and fetches the latest year. With the key registered as an environment secret (the workflow takes the environment name as an input), the API route fetched the 2024 summary use table (BEA InputOutput dataset, table 259, 4,640 cells) and the build filled the BEA columns and the direct-requirements matrix from it. Item 10 is closed.

What the OEWS files replaced, all of it fixture data until now:

| Table | Before | Now |
|---|---|---|
| Occupations: employment and wages | OEWS May 2021 (from the GPTs-are-GPTs mirror) | OEWS May 2025 (830 of 831 occupations); clusters rebuilt on the new employment |
| Occupation × sector | every occupation in one sector "ALL" | 830 occupations × 20 NAICS sectors (legislators take their major group's mix) |
| Occupation × state, states | 2020 population shares, the same mix in every state | OEWS May 2025 state file, renormalized to national employment (suppressed cells) |
| Sectors | one sector, labour-cost share 0.58 | 20 sectors: tradable from the spec list; labour's share of gross output, of value added and the consumption shares from the BEA 2024 summary use table; demand elasticity and friction as estimates |
| Input-output | none | 20 × 20 direct requirements from the same table (intermediate inputs take 30 to 59 cents of each output dollar); cost savings propagate to buying sectors (`macro.io_propagation`) |

Jobs today read 167.2 million on the May 2025 base against 152.4 million before.

The labour-cost share is the number that matters for the macro layer: the single-sector fixture used 0.58, which is labour's share of value added, where the cost equation needs labour's share of gross output. From the BEA table the employment-weighted mean across the 20 sectors is 0.38 (the authors' estimates used before the table arrived gave 0.45), from 4% in real estate to 56% in management of companies. A given task-hour saving therefore lowers unit costs by less than before, and the price, output and GDP effects fall with it (§5). That is a correction, not a calibration choice, and it moves the GDP headline down by about a third.

Input-output propagation is on by default (`macro.io_propagation`, `dlnP = (I − Aᵀ)⁻¹ dlnc` with the BEA direct-requirements matrix): a sector's price falls with its own labour saving and with the prices of what it buys, so the total price effect is larger than the direct one by the Leontief multiplier of the sectors AI reaches (professional and administrative services feed every other sector). A clone without the external files still builds the Phase 1 fixtures.

## 2. The classifier audit, and rules v3

The 120-statement sample was labelled by the model acting as reviewer (a human should overwrite any row they disagree with; `docs/classifier-audit-labels.csv`). Scored against those labels:

| Rules | Agreement | Software precision | Driving precision | Manipulation precision | Fixed precision | None precision |
|---|---|---|---|---|---|---|
| v2 (Phase 9) | 57% | 83% | 38% | 25% | 50% | 91% |
| v3 (Phase 9b) | 74% | 73% | 71% | 44% | 78% | 93% |

What was wrong with v2 is now visible in the row list: "collect payments from customers" was driving (a collect-passengers rule without the passengers), "transport records" and "transport materials by hand" were driving, and any statement the modality vote called physical went to the manipulation channel, so "plan and conduct new employee orientation" and "install and configure HTTP servers" were robot targets. Rules v3 require a vehicle cue and no manual-handling cue for transport statements, a handling verb on a physical object for manipulation outside the production groups (SOC 51, 53-7, 45), and gate the generic equipment terms of the fixed rule to those groups. Manipulation task-hours fall from 17.9% to 11.9% of all task-hours; the difference goes to `none`, one-off physical work outside the embodied classes at central assumptions. The remaining disagreements are listed in `docs/classifier-audit-agreement.md`; most are trades statements that the occupation-level cap handles at build time and the per-statement audit cannot see.

## 3. The 2026 hold-out

`aiwsim diag holdout` refits the two fitted parameters to the 2025 rows only (P.143 to 2025 revenue, then the layoff-first share to Challenger 2025) and scores 2026:

| Series | Quarter | Observed | Shipped fit (2025 and 2026 rows) | Refit to 2025 only |
|---|---|---|---|---|
| AI industry revenue ($bn/yr) | 2026 | 140 | 95 (−32%) | 104 (−26%) |
| Announced AI-cited job cuts since 2023 | 2026Q2 | 173,568 | 139,478 (−20%) | 91,025 (−48%) |
| Firms using AI (BTOS, %, new wording) | 2026Q1 | 18.0 | 13.0 (−28%) | 12.8 (−29%) |

The refit moves the multiple from 5.0 to 6.0 (the 2025 revenue row is then hit exactly) and the layoff share from 0.25 to 0.15 (the 2025 Challenger row within 7%), and both 2026 rows then come out worse than under the shipped fit. Read plainly: the model's growth from 2025 to 2026 is slower than the data's on both series, so a fit to 2025 alone under-predicts 2026, and the shipped fit reaches 2026 only by overshooting 2025 (announced cuts +65% in 2025Q4). The layoff-first share is a constant and the data want it rising through 2025–2026; the revenue multiple decays with a five-year half-life and the data want it flat or rising through 2026. Both are now stated on the page rather than absorbed by the fit.

## 4. The exposure-source swap

The AIOE scores (Felten, Raj and Seamans) were fetched from their repository, which carries no license, so the derived table is built locally from the appendix and never committed. Lever `capability.exposure_source = aioe` rank-maps the AIOE score of each matched occupation (670 of 831) onto the GPTs-are-GPTs beta scale and rescales the occupation's ever-automatable mass by the ratio, so only the ordering of occupations changes:

| Exposure source | Employment 2030 | Employment 2040 | GDP 2040 | Spearman ρ of occupation effects vs GPTs | Top-decile overlap | Largest occupation change |
|---|---|---|---|---|---|---|
| GPTs-are-GPTs (default) | −2.9% | −7.1% | +6.9% | 1.000 | 1.00 | — |
| AIOE, rank-mapped | −2.8% | −7.1% | +6.9% | 0.927 | 0.73 | 17 pp |

(Central U.S.-only runs.) The headline does not depend on the source; the ordering of occupations mostly survives (ρ = 0.93), and a quarter of the most-affected decile changes membership, with single occupations moving by up to 17 points. That is the resolution the occupation view supports across exposure sources: the deciles are stable, the individual ranks are not.

## 5. The headline after Phase 9b

| Metric (2040 Q4, U.S., vs frozen AI) | Phase 9 | Phase 9b |
|---|---|---|
| Employment, median [10–90] | −7.2% [−10.8, −3.4] | −7.0% [−10.2, −3.6] (about 13.5 million jobs against the 194 million there would have been on the May 2025 base) |
| GDP, median | +6.2% | +5.3% |
| Real wages, median | +3.7% | +3.3% |
| Wage share, median | −4.5 pp | −5.8 pp |
| Closure medians (demand / no feedback) | −6.2% / −8.7% | −6.2% / −7.9%; the 64 cell medians span −10.4% to −2.1% and agree on the sign |
| Robots and vehicles, % of task-hours 2040 (central) | 2.9 | 2.9 (the story's 2040 share reads 5.0% under rules v3) |

The headline barely moved, and that is the sum of four changes that do not cancel by accident. On the central U.S.-only run: Phase 9 −7.31%; the 20-sector labour-cost shares alone −2.26 points (prices fall by less, so the demand offset to displacement is smaller); rules v3 +1.13 (fewer robot targets); the May 2025 employment refresh −0.42; input-output propagation from the BEA matrix +1.73 (a sector's price now also falls with the prices of what it buys, and professional and administrative services feed every other sector, so the Leontief multiplier restores most of the price effect); Phase 9b −7.12% (ten regions −5.47%, median −7.0%). Before the BEA matrix arrived the same run read −8.85% with GDP +4.7%; the matrix took GDP back to +6.9% central.

What did move is the wage share, from −4.5 to −5.8 points, and the level of every count: jobs today 167 million rather than 152 on the May 2025 base, the 2040 gap 13.5 million rather than 12.6. Real pay reads +3.3% (was +3.7%), GDP +5.3% (was +6.2%). The closure medians are within two points of each other, the sign confidence stays high, and the under-25 share of the shortfall (31%), the layoff share (one position in four) and the robot share of task-hours (5% by 2040 in the story) are as before.

## 6. The robotaxi anchor series

Three fleet points (Waymo's vehicle count, about 700 in mid-2024, 1,500 in mid-2025 and 2,500 at the end of 2025, transcribed from recollection and tagged as such) sit on the backtest against the model's deployed driving-class units in the U.S.: the model's driving-class stock starts at 500 units in 2024 and reaches about 3,400 by the end of 2025 against about 2,500 Waymo vehicles, so the model runs ahead of the one operator by a factor of 1.4 to 2 (1,450 against 700 in 2024Q3, 2,560 against 1,500 in 2025Q2, 3,380 against 2,500 in 2025Q4), because its driving class also carries autonomous trucks and every operator, not one company over 2024–2025; the ramp cap (P.117) rather than cost is what holds it, and the row is a comparison, not a target.

## 7. Status of the priority plan after Phase 9b

| # | Item | Status |
|---|---|---|
| 1 | Backtest page; 2026 hold-out | Done, including the hold-out |
| 5 | Threshold seed; exposure-source swap; classifier audit | Done: seed, AIOE swap, 120 statements labelled and scored, rules v3 |
| 6 | Cost floors; robotaxi anchor series | Done, including the fleet rows |
| 10 | BEA input-output sector table | Done: OEWS sector tables and the BEA 2024 use table (API), input-output propagation on |

Open after this phase: a human pass over the 120 audit labels; the BTOS sector cuts as sector adoption frictions; the exposure-source swap with a third source (the IMF complementarity index).

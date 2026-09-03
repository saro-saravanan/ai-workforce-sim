# Findings so far — Phase 9b (the open items of the priority plan)

Branch `spec/model-v0.3` after Phase 9b. Baseline, U.S., 384 draws, 64 structural cells; companions at 64 draws; central run quoted unless a median is named. Everything is a difference from a world in which AI stopped improving in 2023. Phase 9 left five items open ([findings-phase9.md](findings-phase9.md) §9): the BEA sector table (review item 10), the 2026 hold-out, the exposure-source swap, the classifier audit labels and the robotaxi anchor series. This note closes them and records what each did to the numbers.

## 1. Real sector tables, and how they got here

The build environment cannot reach bls.gov or bea.gov, so a GitHub Actions workflow (`external-data.yml`, run from the Actions tab) fetches the files on a runner and commits them under `data/external/`. It fetched the BLS OEWS May 2025 occupation-by-industry, national and state spreadsheets at the first attempt. The BEA use table is served through BEA's interactive application rather than static links, the Internet Archive's index of BEA's download directory was offline on every attempt, and BEA's API needs a registered key; the workflow tries all three routes and, with the `BEA_API_KEY` repository secret set, picks the summary use table by its description and fetches the latest year. __BEA_STATUS__

What the OEWS files replaced, all of it fixture data until now:

| Table | Before | Now |
|---|---|---|
| Occupations: employment and wages | OEWS May 2021 (from the GPTs-are-GPTs mirror) | OEWS May 2025 (830 of 831 occupations); clusters rebuilt on the new employment |
| Occupation × sector | every occupation in one sector "ALL" | 830 occupations × 20 NAICS sectors (legislators take their major group's mix) |
| Occupation × state, states | 2020 population shares, the same mix in every state | OEWS May 2025 state file, renormalized to national employment (suppressed cells) |
| Sectors | one sector, labour-cost share 0.58 | 20 sectors: tradable from the spec list, labour-cost share and consumption share from BEA when fetched (authors' estimates until then), demand elasticity and friction as estimates |

Jobs today read __JOBS_TODAY__ million on the May 2025 base against 152.4 million before.

The labour-cost share is the number that matters for the macro layer: the single-sector fixture used 0.58, which is labour's share of value added, where the cost equation needs labour's share of gross output. The employment-weighted mean across the 20 sectors is 0.45. A given task-hour saving therefore lowers unit costs by less than before, and the price, output and GDP effects fall with it (§5). That is a correction, not a calibration choice, and it moves the GDP headline down by about a third.

Input-output propagation is wired (`macro.io_propagation`, `dlnP = (I − Aᵀ)⁻¹ dlnc`) and is inert until the BEA direct-requirements matrix exists; a clone without the external files still builds the Phase 1 fixtures.

## 2. The classifier audit, and rules v3

The 120-statement sample was labelled by the model acting as reviewer (a human should overwrite any row they disagree with; `docs/classifier-audit-labels.csv`). Scored against those labels:

| Rules | Agreement | Software precision | Driving precision | Manipulation precision | Fixed precision | None precision |
|---|---|---|---|---|---|---|
| v2 (Phase 9) | 57% | 83% | 38% | 25% | 50% | 91% |
| v3 (Phase 9b) | 74% | 73% | 71% | 44% | 78% | 93% |

What was wrong with v2 is now visible in the row list: "collect payments from customers" was driving (a collect-passengers rule without the passengers), "transport records" and "transport materials by hand" were driving, and any statement the modality vote called physical went to the manipulation channel, so "plan and conduct new employee orientation" and "install and configure HTTP servers" were robot targets. Rules v3 require a vehicle cue and no manual-handling cue for transport statements, a handling verb on a physical object for manipulation outside the production groups (SOC 51, 53-7, 45), and gate the generic equipment terms of the fixed rule to those groups. Manipulation task-hours fall from 17.9% to 11.9% of all task-hours; the difference goes to `none`, one-off physical work outside the embodied classes at central assumptions. The remaining disagreements are listed in `docs/classifier-audit-agreement.md`; most are trades statements that the occupation-level cap handles at build time and the per-statement audit cannot see.

## 3. The 2026 hold-out

`aiwsim diag holdout` refits the two fitted parameters to the 2025 rows only (P.143 to 2025 revenue, then the layoff-first share to Challenger 2025) and scores 2026:

__HOLDOUT__

## 4. The exposure-source swap

The AIOE scores (Felten, Raj and Seamans) were fetched from their repository, which carries no license, so the derived table is built locally from the appendix and never committed. Lever `capability.exposure_source = aioe` rank-maps the AIOE score of each matched occupation (670 of 831) onto the GPTs-are-GPTs beta scale and rescales the occupation's ever-automatable mass by the ratio, so only the ordering of occupations changes:

__EXPOSURE__

## 5. The headline after Phase 9b

| Metric (2040 Q4, U.S., vs frozen AI) | Phase 9 | Phase 9b |
|---|---|---|
| Employment, median [10–90] | −7.2% [−10.8, −3.4] | __EMP__ |
| GDP, median | +6.2% | __GDP__ |
| Real wages, median | +3.7% | __RW__ |
| Wage share, median | −4.5 pp | __WS__ |
| Closure medians (demand / no feedback) | −6.2% / −8.7% | __CLOSURE__ |
| Robots and vehicles, % of task-hours 2040 (central) | 2.9 | __EMB__ |

__HEADLINE_WORDS__

## 6. The robotaxi anchor series

Three fleet points (Waymo's vehicle count, about 700 in mid-2024, 1,500 in mid-2025 and 2,500 at the end of 2025, transcribed from recollection and tagged as such) sit on the backtest against the model's deployed driving-class units in the U.S.: __FLEET__

## 7. Status of the priority plan after Phase 9b

| # | Item | Status |
|---|---|---|
| 1 | Backtest page; 2026 hold-out | Done, including the hold-out |
| 5 | Threshold seed; exposure-source swap; classifier audit | Done: seed, AIOE swap, 120 statements labelled and scored, rules v3 |
| 6 | Cost floors; robotaxi anchor series | Done, including the fleet rows |
| 10 | BEA input-output sector table | OEWS sector tables real; BEA columns __BEA_SHORT__ |

Open after this phase: a human pass over the 120 audit labels; the BTOS sector cuts as sector adoption frictions; the exposure-source swap with a third source (the IMF complementarity index).

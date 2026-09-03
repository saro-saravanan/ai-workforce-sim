# Findings so far — Phase 9 (robustness after the adversarial review)

Branch `spec/model-v0.3` at Phase 9. Baseline, U.S., 384 draws, 64 structural cells (the closure joined the ensemble); companions at 64 draws, central run quoted unless a median is named. Everything is a difference from a world in which AI stopped improving in 2023. The phase implemented the priority plan of [docs/adversarial-review-phase8.md](adversarial-review-phase8.md) §6; the table at the end says which items are done, which changed a result, and which is still open.

## 1. The headline after the closure joined the ensemble

| Metric (2040 Q4, U.S., vs frozen AI) | Phase 8 | Phase 9 |
|---|---|---|
| Employment, median [10–90] | −5.5% [−10.6, −0.4] | −7.2% [−10.8, −3.4] (about 12.6 million jobs against the 174 million there would have been) |
| GDP, median | +8.3% | +6.2% |
| Real wages, median | +3.8% | +3.7% |
| Wage share, median | −4.8 pp | −4.5 pp |
| Median under the demand closure / under no demand feedback | — | −6.2% (32 cells) / −8.7% (32 cells); the 64 cell medians span −11.6% to −1.9% and agree on the sign |

Two things moved the numbers. The demand multiplier P.87 was bounded to the literature (0.3–0.9 instead of 0.3–1.2), which removes the runs in which a permanent productivity gain was spent back with a multiplier above one and takes the top of the employment band with it. And half the ensemble now runs with the multiplier switched off (closure `no_demand_feedback`), so the band's lower half is populated by cells in which nothing is spent back at all. The band is now a range over the assumptions economists actually disagree on rather than over one parameter's range; the Story calls it "the range of the model's assumptions" and shows the two closure medians as the named futures, in place of "gains spent back" and "gains pocketed".

The closure is a switch on demand feedback, not a full-employment closure: nothing in the model clears the labour market through wages. A wage-clearing reading is the market-clearing wage variant (§6), which can be run on either closure.

## 2. The backtest: 2024Q1–2026Q2 against what happened

The model started in 2024 and had never been scored against a quarter it did not fit. The backtest table (`results.backtest`, the Story's "How the model has done so far", the web Backtest view) puts the model's central path against five observed series; rows used in fitting are marked so nobody reads them as a test.

| Series | Quarter | Observed | Model (central) | Error | Used in fit |
|---|---|---|---|---|---|
| Firms using AI (BTOS, %) | 2024Q1 | 5.4 | 5.5 | +3% | yes (adoption q) |
| | 2025Q3 | 10.0 | 10.8 | +8% | yes |
| | 2025Q4 (new wording) | 17.3 | 11.8 | −32% | yes |
| | 2026Q1 (new wording) | 18.0 | 12.8 | −29% | yes |
| AI-cited announced job cuts since 2023 (Challenger) | 2024Q4 | 16,989 | 56,088 | +230% | no |
| | 2025Q4 | 71,825 | 121,748 | +70% | yes (layoff share) |
| | 2026Q2 | 173,568 | 142,971 | −18% | yes |
| AI industry revenue ($bn/yr) | 2025 | 60 | 53 | −12% | yes (P.143, P.140) |
| | 2026 | 140 | 92 | −35% | yes |
| Hyperscaler capex ($bn/yr) | 2024–2026 | 251 / 413 / 733 | 250 / 400 / 720 | within 3% | input path |
| Recent-graduate unemployment (NY Fed, %) | 2025Q2–2026Q2 | 4.8 → 5.6 | not tracked | — | context |
| Software postings (Indeed index) | 2026Q1 | 70.9 | not tracked | — | context |

Mean absolute error by series: adoption 18%, Challenger 106%, revenue 23%, capex 2%.

Reading. The adoption rows are the only genuine out-of-sample check, and the model is within the noise of a survey whose wording changed in late 2025 (the two rows on the new wording are not comparable with the fit). The Challenger and revenue rows are calibration targets and show the fit, not skill; the one Challenger row that was not fitted, 2024, is the most informative row on the page: the model announced 56,000 AI-cited cuts by the end of 2024 against 17,000 counted, so its layoffs start about a year too early even though the 2025–2026 totals are within a third. The layoff share is a constant; the data say it rose. Capex is an input path. The graduate-unemployment and software-postings rows have no model counterpart yet (the model reports entrants' lost positions, not an unemployment rate by age), so they are context rows: a reader can see that the direction the model gives for entrants (hiring that never happens) is the direction the data moved, and no more.

What the backtest cannot say: the horizon is ten quarters and every series but adoption is either fitted or an input. The 2026 hold-out (fit to 2024–2025, score 2026) is the next step and is not done.

## 3. Regional configuration: the three points explained

The review found the U.S. headline three points apart between a U.S.-only run and the ten-region run. The decomposition (`aiwsim regional`, [docs/regional-decomposition.md](regional-decomposition.md)) says where the difference comes from:

| Configuration (central, 2040) | U.S. employment | Robots and vehicles, % of task-hours |
|---|---|---|
| Ten regions (baseline) | −4.64% | 2.85 |
| U.S. only (`config-us-closed`) | −7.62% | 8.23 |
| Ten regions, production ramp allocated locally | −7.37% | 8.36 |
| Ten regions, traded services off | −4.64% | 2.85 |

Nearly all of it is the shared production ramp: with one world capacity for robots and vehicles allocated across ten fleets, the U.S. gets a third of the hardware it gets when it is the only region, and the embodied share of task-hours falls from 8% to 3%. Trade feedback contributes nothing to the U.S. number, for a reason that is a finding in itself: the traded-services channel moves displacement from importers to exporters, and the U.S. leads the displacement it imports, so the export-exposure term is zero for it (it is not zero for India or the Philippines). The rents allocation accounts for the remaining quarter of a point.

So the ten-region number is the model's number, and the question a reader should ask is whether the hardware ramp is one world capacity or one per region. The lever `applications.hardware.ramp_allocation` (`global`, `local`) makes that choice explicit; the U.S.-closed configuration ships as a scenario and its story is exported beside the baseline.

## 4. Convergence and the draw count

`aiwsim convergence` ([docs/convergence.md](convergence.md)) ran the U.S.-only baseline at 64, 128, 256 and 384 draws under three seeds:

| Draws | Across-seed SD of p10 / p50 / p90 (points) |
|---|---|
| 64 | 0.43 / 0.09 / 0.28 |
| 128 | 0.07 / 0.09 / 0.27 |
| 256 | 0.31 / 0.10 / 0.32 |
| 384 | 0.11 / 0.08 / 0.25 |

The median is stable to a tenth of a point at every draw count; the band edges move by a quarter to half a point with the seed and do not converge much between 64 and 384, because with 64 cells the edges are set by a handful of draws in the extreme cells. The confidence label did not change with the seed at any count. The baseline therefore runs 384 draws (six per cell); the honest statement on the Story is that the band edges carry about half a point of Monte Carlo noise, and the exec brief says so.

## 5. The task engine: threshold seed and the classifier

Thresholds are seeded by a hash of the task key. The lever `capability.threshold_seed` re-derives the hash; `aiwsim diag threshold-seeds` ([docs/diagnostics-phase9.md](diagnostics-phase9.md)) reruns the central U.S. path under seeds 0, 1 and 2:

| Seed | Employment 2040 | Spearman rank correlation of occupation effects vs seed 0 | Top-decile overlap | Largest occupation change |
|---|---|---|---|---|
| 0 | −7.31% | 1.000 | 1.00 | 0.0 pp |
| 1 | −7.31% | 1.000 | 0.99 | 0.9 pp |
| 2 | −7.30% | 1.000 | 0.99 | 3.8 pp |

The headline and the ranking of occupations do not depend on the seed: thresholds are spread within an occupation's tasks, and an occupation's effect is an average over hundreds of task groups. Individual small occupations can move by a few points, which is the resolution the engine supports: an occupation's number is good to a few points, its rank is good to a decile.

The classifier audit sample ([docs/classifier-audit-sample.md](classifier-audit-sample.md)) is 120 statements stratified by channel with an empty column for human labels; it is a tool, not a result, and no one has filled it in yet. The one rule change the review forced is done: installation and repair trades (SOC 47-2xxx and 49-xxxx) keep at most 30% of their task-hours on the manipulation channel unless a statement names line, warehouse or repetitive handling. Electricians and HVAC mechanics were 78% and 71% robot-targeted by keyword; they now sit mostly on `none`, where one-off work at customer sites belongs at central assumptions.

## 6. The labour market: the entrant response and market-clearing wages

The review's sharpest distributional point was that nobody in the model changes field of study when an occupation's wages fall. Phase 9 adds an entrant supply response: the share of an occupation's attrition cut that lands on its entrant cohort is `min(1, (w/w0)^ε)` with ε = P.146 (0.5) and an eight-quarter lag (P.147). Positions still close; fewer entrants were queued for them. At ε = 0 the Phase 8 rule is reproduced exactly.

The variant `variant-market-clearing-wages` puts wage adjustment, pass-through, reinstatement and the demand response at the top of their ranges. The Story's pay beat now reads it beside the baseline: real pay about the same (+5% central in both), total jobs 4 points higher, and the under-25 share of the shortfall about the same (42% central in both). Reinstatement and the demand response at the top of their ranges add jobs; faster wage adjustment barely changes real pay because the price level, not the occupation wage, carries most of the real-wage gain. The under-25 share does not move because the entrant response is symmetric across occupations at the central elasticity; the variant is a test of the aggregate claim, not of the distributional one.

## 7. Policy: the basic income sign

The deficit-financed basic income reported +14 million jobs from $1.7 trillion a year of borrowing in a model with no interest-rate or inflation response. Phase 9 books the income-tax surcharge as revenue, so a surcharge-financed item is balanced-budget by construction, and the shipped policy `policy-ubi-ai-tax` is now financed by the surcharge with the AI tax on top. A universal payment is spent at the population-average propensity (P.86, 0.65) rather than the 0.9 that targeted transfers to displaced workers get. The decomposition (U.S.-only, central, 2040 employment):

| Run | Employment | Fiscal balance |
|---|---|---|
| Baseline | −7.31% | 0 |
| Basic income, surcharge-financed, no AI tax | −7.69% | 0 |
| AI tax alone (30% of AI spend) | −7.44% | +$81bn |
| Basic income, surcharge-financed, with AI tax (shipped) | −7.82% | +$81bn |
| Basic income, deficit-financed (`policy-ubi-deficit`) | −1.62% | −$1,661bn, validity flag |

The balanced-budget version takes about 0.4 points off employment: the surcharge falls on income-tax payers at a propensity to consume of 0.7 (authors' estimate) and the payment reaches every decile at the population average of 0.65, so the redistribution takes slightly more spending out than it puts back. That sign is a property of two propensities nobody has measured for this transfer, and the honest statement is that a balanced-budget basic income is close to neutral for total jobs in this model, a tenth of a point either way per 0.05 of propensity. The deficit version ships only to show the validity flag; in the ten-region baseline story the shipped policy reads "816,000 fewer jobs than the baseline by 2040; costs about $1,742 billion a year", which is the redistribution, not a stimulus.

## 8. Embodied cost floors

Under the Seba 2026 preset the manipulation cost per worker-hour reached $0.04 by 2034, below the electricity to run the robot. Each embodiment class now carries a floor (`cost_floor_usd_per_hour`: driving $3.0, manipulation $1.5, fixed $1.0, aerial $0.8; authors' estimates for energy, maintenance, insurance and the capital charge at scale) that bounds both the cost the firm tests and the reported series; the lever `applications.hardware.cost_floor_scale` scales it and 0 reproduces the Phase 8 curves. Under the Seba 2026 preset the manipulation cost now sits at the $1.50 floor from 2025 onwards (its learning curve reaches the floor immediately) and driving at $3.00, so the preset's embodied displacement (10.3% of task-hours by 2040, against 2.9% in the baseline) is set by the ramp and approval paths, not by a cost that keeps falling. In the baseline the manipulation cost reaches the floor in 2040 ($4.27 in 2025, $2.75 in 2030, $2.03 in 2034); driving is at $4.28 in 2040, above its floor. The scoreboard row "RethinkX 2025, robot cost by 2035" now reads $2.0 against the claimed $1.0 (model higher).

## 9. What still did not hold after Phase 9 (closed in [findings-phase9b.md](findings-phase9b.md))

- **Item 10, the BEA input-output sector table, is not done.** bea.gov, bls.gov and FRED are unreachable from the build environment, and a transcribed table without the source file would be a fixture with a real-data label. No sectoral claim should be made until it is in.
- The 2026 hold-out of the backtest is not done, and the graduate-unemployment and software-postings rows have no model counterpart.
- The classifier audit sample is unlabelled.
- The closure switch is a demand-feedback switch, not a wage-clearing closure; the compute constraint still does not bind (review §2.1 item 3 is documented, not modelled).
- The convergence table says the band edges carry about half a point of seed noise at any draw count the API can afford; the fix is more draws per extreme cell, not more draws overall.

## 10. Status of the priority plan

| # | Item | Status |
|---|---|---|
| 1 | Backtest page 2024Q1–2026Q2 | Done: table, story section, web view; hold-out not done |
| 2 | Closure switch as an ensemble axis; P.87 range 0.3–0.9; retire "gains spent back" | Done; 64 cells; futures are the two closure medians |
| 3 | Convergence test; structural spread on the Story; relabel the range | Done (`aiwsim convergence`; spread shown; "range of the model's assumptions") |
| 4 | Regional decomposition; U.S.-closed configuration | Done (`aiwsim regional`; `config-us-closed`; ramp-allocation lever) |
| 5 | Threshold-seed and exposure-source sensitivities; classifier audit | Threshold seed done; audit sample generated, unlabelled; exposure-source swap not done |
| 6 | Cost floors; robotaxi anchor series | Floors done; anchor series not done |
| 7 | Balanced-budget policy closure; drop the UBI sign | Done |
| 8 | Entrant supply response; market-clearing wage variant | Done |
| 9 | One-page model statement; fitted-parameter table; calibration-target marks | Done ([docs/current-model.md](current-model.md)) |
| 10 | BEA input-output sector table | Phase 9b: OEWS sector tables real via a runner workflow; BEA columns pending the API key (see findings-phase9b) |

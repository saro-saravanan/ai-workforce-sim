# Adversarial review of the model at the end of Phase 8

*Written as the review a veteran simulation economist would give before this model is put in front of others. Every claim below was checked against the code, the registry or a diagnostic run made for this review; the diagnostics are listed in §7 so they can be repeated.*

## 0. The verdict in one paragraph

This is a well-instrumented **structured scenario generator**, not an estimated model, and it should describe itself that way. It has 116 parameters, a 32-cell structural ensemble and a copula over the draws, but only six calibration targets (BTOS adoption, Acemoglu's TFP bound, Challenger's AI-cited cuts for 2025 and 2026, and industry revenue for 2025 and 2026), so the parameter space is unidentified by a wide margin and the "likely ranges" are ranges over assumptions, not sampling distributions of anything measured. Within that framing it is unusually honest: every number is traceable, the counterfactual is stated on every page, and the places where the authors reached for a number are tagged. The weaknesses a hostile veteran will go for, in order of damage, are: the macro closure (an exogenous capex path that acts as pure demand stimulus and a demand multiplier that can swing 2040 employment from −6% to +13%); the absence of any backtest against 2024–2026; the sensitivity of the U.S. headline to the regional configuration (three points of employment between a U.S.-only and a ten-region run); a task engine whose two central quantities, the capability clock and the "ever automatable" mass, rest on a benchmark series and a 2023 exposure paper; Monte Carlo bands whose edges move by two points with the seed at the draw count the API uses; and a policy layer that produces a sign for basic income (+14 million jobs) that the literature does not support. None of these is fatal. All of them are fixable or at least statable, and §6 ranks the fixes.

## 1. What the model is, said the way a reviewer would say it

- A **task-based partial-equilibrium simulation**: 19,000 O*NET task statements, a capability clock, a cost test per task, Bass diffusion by firm size and sector, a hiring-first labour market with cohorts, and a macro layer that values output at baseline prices, adds incremental AI capex as investment, passes cost declines to prices with a lever, and feeds household demand back with a multiplier.
- **Not** a general-equilibrium model: no interest rate, no capital stock, no savings-investment identity, no exchange rates, no fiscal reaction function, no labour supply response other than the policy levers. Prices are relative to a baseline path; there is no nominal side.
- **Calibrated by hand** to six point targets and **validated** by three replication presets (Acemoglu, Goldman, IMF) that were built to reproduce published numbers under those authors' assumptions, which is a consistency check, not a validation.
- **Deterministic given the seed**, float32 in the task engine, quarterly steps, 68 quarters, ten regions sharing one capability clock with access lags.

A reviewer will accept all of this if the documents say it. Today the methodology note says most of it; the Story view and the README say less.

## 2. The attacks, ranked by damage

### 2.1 The macro closure is the weakest layer, and the results that matter most run through it

**Evidence.** The tornado on 2040 employment is led by P.87, the demand multiplier: at the bottom of its registry range (0.3) employment is −5.9%, at the top (1.2) it is +13.2%; the same parameter moves GDP from +6.5% to +29.3%. No other parameter comes close. A multiplier of 1.2 on the demand side of a partial-equilibrium model with no supply constraint, no interest rate and no capacity limit produces 23 million extra jobs by 2040, and the story presents that as a named future ("Gains spent back").

**Second piece of evidence.** Halving the capex path (P.80 to 200, P.81 to 20%) leaves 2030 adoption unchanged (74.6% of employment in both runs) while employment in 2040 falls from −7.6% to −8.4% and GDP from +8.7% to +6.8% (U.S.-only, central). So compute capacity never binds; the capex path is pure spending in the GDP identity (§6.1, `ΔI^{AI,dom}`) and a source of construction jobs. That is the opposite of how the capex enters the public argument (as a supply constraint on AI), and a reviewer will say the investment channel is Keynesian by construction.

**What a veteran will say.** "Your headline employment sign is a function of one demand parameter with a range you chose, and your capex is a stimulus term, not a supply term. Show me what the model says with a balanced-budget, supply-constrained closure, and then tell me which closure you believe."

**What to do.**
1. Bound P.87 by the literature explicitly: local fiscal multipliers cluster around 0.5–1.0 with the upper end only at the zero lower bound; a long-run multiplier on a permanent productivity gain in a full-employment economy is closer to zero. Reduce the range to 0.3–0.9, or better, make the multiplier state-dependent (fall as unemployment falls). Retire "Gains spent back" as a named future unless it is reproduced by a scenario a reader can defend.
2. Add a supply-side closure switch: (a) the current demand closure; (b) a full-employment closure in which the demand feedback is zero and displacement is absorbed by wages and participation. Report the headline under both; the ensemble should carry the closure as a structural axis, because that is where the disagreement between economists actually lives.
3. Make compute capacity bind or say that it does not. Either derive a token-supply constraint from the capex path and the yield curve (the machinery exists, `capex_path.tokens_per_bn`) and let adoption saturate against it, or drop the pretence and document the capex path as an investment-demand assumption only.
4. Introduce crowding-out of private investment by the AI build (P.56 exists at 0.3 but is applied only to the incremental term) and a debt or interest-rate response for the policy runs. The UBI run (+14 million jobs from $1.7 trillion a year of deficit spending) is currently reported with a validity flag; a reviewer will want it not reported at all, or reported under a balanced-budget rule that turns the sign.

### 2.2 There is no backtest, and the model started in 2024

**Evidence.** The model runs from 2024Q1 and is fitted to 2025–2026 points; nothing tests whether it reproduces a period it was not fitted to. Adoption is the one series with a history (BTOS from September 2023), and the model's firm-weighted adoption reads 8.0% at 2024Q4 against BTOS 5.4% (February 2024) and 11.8% at 2025Q4 against about 10% (September 2025) and 17.3% (November 2025, after a wording change). That is within noise, but nobody has written the comparison down. Labour-market aggregates (unemployment, payrolls, JOLTS openings, young-graduate unemployment, computer-occupation employment 2023–2026) have not been compared with the model's 2024–2026 path at all.

**What a veteran will say.** "A forecasting model that has never been scored against a single quarter it did not fit is a scenario tool. Call it that or score it."

**What to do.**
1. Build a **backtest page**: model 2024Q1–2026Q2 against BTOS (firm- and employment-weighted), Challenger (already there), BLS payrolls in the ten most exposed occupations, the unemployment rate of recent graduates, software-developer postings (Indeed), and industry revenue. Report each as a scoreboard row with the observed series, not a single point.
2. Hold out 2026: fit to 2024–2025 only, score 2026. If the fit needs 2026 to look right, say so.
3. Add a **pseudo-out-of-sample** test on the presets: the Acemoglu preset was built to hit 0.66% TFP; the interesting test is whether the model with Acemoglu's parameters reproduces his *distribution* across occupations, not his total.

### 2.3 The U.S. headline depends on the regional configuration by three points

**Evidence.** The same baseline scenario gives 2040 U.S. employment of −7.6% (central) when run for the U.S. alone and −4.6% when run with the ten regions. The difference comes from the global production ramp (fleets are allocated across regions, so the U.S. gets fewer robots), from trade feedback and from rents received. The story, the README and the scoreboard all quote the ten-region number; the sim tests and several findings sections use U.S.-only runs.

**What a veteran will say.** "Which is the model? If adding placeholder regions with placeholder occupation mixes changes the U.S. answer by three points, the regional layer is not a refinement, it is a major assumption."

**What to do.**
1. Decompose the three points: rerun with the ramp allocated to the U.S. only, with trade feedback off, with rents off. Publish the decomposition.
2. Make the U.S.-only run a named configuration ("U.S. closed") and report it beside the ten-region run on the Story page.
3. Replace the placeholder occupation mixes outside the U.S. (risk #10) before publishing any non-U.S. jobs number in a headline; until then, drop non-U.S. job losses from the money beat.

### 2.4 The task engine's two load-bearing quantities are borrowed, and the classifier is keyword-based

**Evidence.** Feasibility is a logistic in the distance between a capability index driven by METR's task-horizon doublings and a per-task threshold seeded by a hash of the task text; the ever-automatable mass comes from the GPTs-are-GPTs exposure ratings (2023). Channels (software, driving, manipulation, fixed, aerial, none) are assigned by keyword rules on task statements; electricians land in the robot targets. The presence discount `(1 − presence)^λ` and the whole-job rule for three driving applications are authors' constructions.

**What a veteran will say.** "The capability clock assumes that a benchmark of software-task horizons measures readiness for 19,000 heterogeneous tasks, and your thresholds are pseudo-random. Show me that the ranking of occupations is stable under a different exposure source and a different threshold seed."

**What to do.**
1. **Threshold-seed sensitivity**: rerun with three hash seeds for the per-task thresholds; report the rank correlation of occupation effects and the change in the headline. If the occupation ranking moves, the per-task detail is noise and should be aggregated up.
2. **Exposure-source sensitivity**: swap in Felten's AIOE, Eloundou's β, and the Anthropic Economic Index task usage as alternative exposure sources; report the headline under each as an ensemble axis.
3. **Classifier audit**: sample 200 task statements, hand-label the channel, report precision and recall per channel, and fix the electricians.
4. State the clock's calibration once, plainly: which METR series, which anchor date, what doubling time, and what a "threshold of 4 doublings" means in hours of task horizon.

### 2.5 The uncertainty is smaller than it looks and larger than it says

**Evidence.**
- At 64 draws (the API's companion setting) the 2040 employment band is −12.4/−6.4/−1.9 with seed 42, −10.8/−7.1/+0.5 with seed 7, −11.5/−6.5/−1.7 with seed 99: the p90 edge moves 2.4 points and crosses zero with the seed. At 256 draws the movement is smaller but not reported. The confidence labels ("we would bet on it") are derived from these bands and the tornado, so they can flip with the seed.
- Thirty-two cells at 256 draws leaves eight draws per cell; the ensemble's structural spread is not reported separately from the parametric spread in the results document (`structural` is present but the story does not use it).
- The bands contain no model error. A reader sees "likely between 156 and 174 million jobs" and reads it as a forecast interval; it is the interval of the model's own assumptions.

**What a veteran will say.** "Report Monte Carlo standard errors on your percentiles, separate structural from parametric spread, and stop calling the middle 80% of your own runs a likely range."

**What to do.**
1. Convergence test in CI: run 128, 256, 512 draws with three seeds; report the standard error of p10, p50, p90 for the headline; set the draw count so that the p90 edge is stable to 0.5 points; label the confidence classification with its seed sensitivity.
2. Report the structural spread (cell medians) beside the parametric spread on the Story page; the sureness label should be "a coin flip" whenever cells disagree on sign, regardless of the pooled band.
3. Rename "likely range" to "range of the model's assumptions" in the executive brief, and add one sentence on what is not in the range (model error, data error, events).
4. Stratify draws by cell (Latin hypercube within cell) so eight draws per cell are at least spread.

### 2.6 Calibration practice: fitting to noisy point targets with free parameters

**Evidence.** The layoff-first share (0.25) was fitted to two Challenger counts of *announced* cuts citing AI, which include attrition, redeployment and reputational tagging. The market-price multiple (5.0) and the consumer path were fitted to press-reported revenue whose scope varies by source. Each fit used one free parameter per target, so each target is hit by construction and adds no test of the model.

**What a veteran will say.** "You have fitted one parameter to each observation. Your scoreboard rows for those targets are not evidence; they are the definition of the parameters."

**What to do.**
1. Mark fitted rows on the scoreboard as *calibration targets*, not comparisons (a visual distinction and a separate count: "12 comparisons, 4 targets").
2. For each fitted parameter, report the profile: what the target reads at the low and high end of the registry range. If the model hits the target across the whole range, the target does not constrain it and should not be advertised.
3. Prefer series to points: Challenger monthly since 2023, BTOS biweekly, revenue by quarter. A path with the right shape is evidence; a point is not.

### 2.7 The labour market: the mechanism that drives the distributional headline is an assumption

**Evidence.** "The young pay first" follows from the hiring-first rule: required cuts are met by not refilling positions, and unfilled positions land on the entrant cohort. That is a modelling choice with no calibration; it produces the 35% share of the shortfall borne by under-25s. The wage response uses an excess-supply elasticity with no bargaining, no minimum wage floor, no participation response, no hours margin except the policy lever, and no occupational mobility cost beyond the retraining flows. Entrant cohorts are fixed in size: nobody changes their field of study in response to prices.

**What a veteran will say.** "The claim that entrants bear the adjustment is the most quotable line in the brief and the least tested. Show me the sensitivity to the attrition rule, and show me what happens when wages clear the market."

**What to do.**
1. Add an attrition-versus-layoff sensitivity to the tornado (the lever exists) and report the under-25 share under the layoffs-first variant on the Story page beside the baseline.
2. Add a market-clearing wage variant (higher elasticity, no floor) and report the young-worker share and the wage effect under it.
3. Let entrant supply respond to relative wages with a lag (a one-parameter elasticity from the field-of-study literature); this also fixes the odd result that computer occupations lose 8% of jobs by 2030 with no effect on enrolment.
4. Compare the model's 2025–2026 path of recent-graduate unemployment against the observed series (the Canaries row is a first step and currently reads "model higher"); if the model cannot reproduce the early signal, the hiring channel is too slow, not too fast.

### 2.8 The embodied layer: cost curves without floors, approval as a free lever

**Evidence.** Under the Seba presets the manipulation hardware cost per worker-hour falls to $0.04 by 2034. Wright's law with a learning rate of 0.25 and no floor for energy, maintenance, insurance, capital cost at scale or the integration labour that the task engine adds separately produces numbers below the electricity cost of running the robot. Approval paths cap coverage at 0.85 and are set by the scenario author; the production ramp cap (0.5/yr central) is the binding constraint for a decade and has no empirical anchor beyond EV history.

**What a veteran will say.** "Your robots are cheaper than their electricity. Put a floor under the cost, anchor the ramp to something, and show me the cost-per-hour path against Waymo's disclosed cost per mile."

**What to do.**
1. Add a cost floor per class (energy, maintenance, capital charge) in the registry with a source; report the hardware cost per hour with and without it.
2. Anchor the driving clock and coverage to disclosed series (Waymo paid rides per week, Apollo Go city counts); the data inventory lists them; until then, label every robotaxi date as unanchored.
3. Report the deployment bound and the approval cap on the Applications panel so a reader can see which one binds.

### 2.9 The revenue layer and the investment section: the right question, a fitted answer

**Evidence.** The revenue layer added in Phase 8 makes AI producers' revenue match reported 2025 and 2026 figures through a price multiple over cost and an exogenous consumer path. The multiple also enters firms' cost test. There is no link from revenue to capex (no financing constraint), no price competition dynamics, and the consumer path is a logistic to a chosen ceiling. The investment section then compares the exogenous capex path with this fitted revenue and with a productivity gain that is an output of the same partial-equilibrium closure criticised in §2.1.

**What a veteran will say.** "The investment section is your most policy-relevant page, and every one of its three series is an assumption or a fit. That is acceptable if it is labelled, and it is not acceptable as a finding."

**What to do.**
1. Label the section's three series by status on the page: capex (input, observed to 2026), producers' revenue (fitted to 2025–2026, projected by adoption), productivity gain (model output under the demand closure).
2. Add the capex-halved and capex-doubled runs as named scenarios so the reader sees that adoption does not depend on the build-out in this model.
3. Add a financing-constraint variant: capex after 2027 grows only as fast as producers' revenue permits at a stated revenue-to-capex ratio; report the difference.

### 2.10 Smaller items a careful reader will still catch

- **float32 in the task engine** (`TDTYPE`): fine for speed, but the tests should include a float64 run to show the headline is unchanged to 0.1 points.
- **Quarterly steps with annual parameters**: several rates are converted with `/4` and `**0.25`; one adding-up test per flow (employment identity, rents = spend, GDP decomposition) exists for some but not all; add the rest.
- **Central versus median**: the central run gives −4.6% and the median −5.5% for 2040 employment; the Story quotes the median for the headline and the central for policies and outlooks. State the convention once, and show both on the headline.
- **The sector table is a single-sector fixture**: demand elasticity, labour cost share and consumption share are one number each. Every sector-level statement (pass-through, output substitution by category) inherits this. Replace with the BEA input-output table before any sectoral claim.
- **The regional layer's actor and market-share tables are authors' estimates**; rents by region are outputs of assumed shares. Say so where the rents are shown.
- **Hash-seeded thresholds** make the per-task detail reproducible but arbitrary; do not present occupation-level results at finer than major-group resolution until §2.4 item 1 is done.
- **Documentation drift**: the spec's §16 and the amendment's §A.15–A.16 record deviations, but three phases of changes are spread across findings notes; a single "current model" statement (one page, equations, parameters, what is fitted) is missing and is the first thing a reviewer will ask for.

## 3. What would survive scrutiny today

- The **direction and order of magnitude of the software channel**: office and analytical work reshaped first, computer and administrative occupations down 8–17% by 2030, are consistent with Acemoglu, Eloundou, and the early labour-market data; the scoreboard shows the model is more aggressive than Acemoglu's bound and slower than the Canaries signal, which is the right place to be uncertain.
- The **jobs and people ledgers**, kept apart and explained. Most reports conflate them; this one does not.
- The **counterfactual discipline**: everything against a frozen-AI path, every page.
- The **provenance apparatus**: registry with tags, fixtures labelled, data flags in every document, a scoreboard that runs on every scenario.
- The **investment-versus-returns framing**: right question, honest about the fit, and the productivity-repays-capex-by-2033 result is robust to everything except the closure.

## 4. What a reviewer would ask to see before believing any headline

1. The backtest page (§2.2).
2. The closure switch and the headline under both closures (§2.1).
3. The U.S.-only versus ten-region decomposition (§2.3).
4. Seed and draw-count convergence with standard errors (§2.5).
5. The threshold-seed and exposure-source sensitivities (§2.4).
6. A one-page "current model" statement with the count of fitted parameters and their targets (§2.10).

## 5. What to change in how the results are described

- Say "structured scenario model" in the first sentence of the README and the About page; keep "forecast" for the scoreboard rows only.
- Replace "likely range" with "range of the model's assumptions" and add the one sentence on what it excludes.
- Show the central and the median together on the headline, with one line on why they differ.
- Mark calibration targets on the scoreboard and count them separately.
- Retire "Gains spent back" as a named future until a defensible scenario reproduces it; keep "Gains pocketed".
- Report the under-25 share under the layoffs-first variant beside the baseline wherever the young-worker finding appears.

## 6. Priority plan (effort in days for one person who knows the code)

| Priority | Item | Effort | Why first |
|---|---|---|---|
| 1 | Backtest page 2024Q1–2026Q2 (BTOS, Challenger, exposed-occupation payrolls, graduate unemployment, revenue) | 3 | Turns a scenario tool into a scored model; every later change is judged against it |
| 2 | Closure switch (demand vs full-employment) as an ensemble axis; P.87 range to 0.3–0.9; retire "Gains spent back" | 3 | Removes the single biggest lever a hostile reviewer will pull |
| 3 | Convergence test in CI; structural spread on the Story page; relabel the range | 1 | Cheap, and it stops the confidence labels flipping with the seed |
| 4 | U.S.-only versus ten-region decomposition; "U.S. closed" configuration | 1 | Three points of headline are unexplained today |
| 5 | Threshold-seed and exposure-source sensitivities; classifier audit | 3 | Establishes what resolution the task engine can support |
| 6 | Cost floors for embodied classes; robotaxi anchor series | 2 | Removes the $0.04 robot |
| 7 | Balanced-budget policy closure; drop the UBI sign until then | 2 | The policy page currently reports a result the literature contradicts |
| 8 | Entrant supply response; market-clearing wage variant | 2 | Tests the most-quoted distributional claim |
| 9 | One-page current-model statement; fitted-parameter table; calibration-target marks on the scoreboard | 1 | What the reviewer reads first |
| 10 | BEA input-output sector table | 3 | Prerequisite for any sectoral claim |

Items 1–4 and 9 (nine days) would change the reception of the model more than everything built since Phase 5.

## 7. Diagnostics run for this review (reproducible)

| Check | Setting | Result |
|---|---|---|
| Seed sensitivity | baseline, U.S.-only, 64 draws, seeds 42 / 7 / 99 | 2040 employment p10/p50/p90: −12.4/−6.4/−1.9; −10.8/−7.1/+0.5; −11.5/−6.5/−1.7 |
| Capex halved | P.80 = 200, P.81 = 20%, central, U.S.-only | adoption 2030 unchanged (74.6%); employment 2040 −8.4% vs −7.6%; GDP +6.8% vs +8.7% |
| Regional configuration | baseline central, U.S.-only vs ten regions | 2040 U.S. employment −7.6% vs −4.6% |
| Tornado leaders (2040 employment, ten regions, 256 draws) | registry ranges | P.87 −5.9 to +13.2; P.53 −7.8 to −2.2; P.60 −7.3 to −1.9; P.17 −2.1 to −6.6; P.117 −2.8 to −7.0 |
| Adoption backcheck | firm-weighted, central | model 8.0% (2024Q4), 11.8% (2025Q4) vs BTOS 5.4% (Feb 2024), ~10% (Sep 2025), 17.3% (Nov 2025, new wording) |
| Central vs median | ten regions, 256 draws | 2040 employment −4.6% central, −5.5% median |
| Manipulation cost per hour | Seba 2026 preset | $0.92 (2025), $0.04 (2034) |
| Runtime | baseline, ten regions, 256 draws, 4 cores | 54 s (Monte Carlo 37 s, tornado 10 s, channels 3 s) |

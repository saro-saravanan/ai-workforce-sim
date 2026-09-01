# Findings so far — Phase 2 (U.S., Monte Carlo, structural ensemble, cohorts, presets)

Date: 2026-09-01. Spec v0.2 with the implementation notes in §16. Scenario `baseline`, 200 draws through the correlated copula, 8-cell structural ensemble on by default, tornado over 20 parameters, channel decomposition on the central run. Everything is relative to the frozen-AI baseline. Bands are 10th to 90th percentile.

## What the model currently says

| Quarter | Employment | Real wages | GDP | Wage share |
|---|---|---|---|---|
| 2030 Q4 | −1.6% [−3.1, +0.2] | +1.2% [0.0, +1.6] | +3.0% [+1.8, +4.2] | −1.4 pp [−1.9, −0.7] |
| 2040 Q4 | −3.1% [−6.4, +0.6] | +4.4% [+1.8, +6.2] | +6.0% [+3.0, +10.6] | −2.3 pp [−3.3, −1.3] |

Confidence in the sign at 2040: GDP high, real wages high, wage share high, **employment low**. The sign of the employment effect holds in 86% of draws, but the eight mechanism cells disagree (from −5.8% under Bessen elasticities with low reinstatement and low pass-through, to 0.0% under unit-elastic demand with historical reinstatement and mid pass-through), and one parameter can flip it on its own.

Structural versus parametric spread at 2040, employment: 5.8 pp across mechanism cells against 5.1 pp within them. The disagreement in the literature is as large as the uncertainty in the numbers. That is the single most useful thing the ensemble shows.

## Three findings from Phase 2

1. **The demand-feedback multiplier is the most decision-relevant parameter, and it is the least AI-specific.** The tornado puts `P.87` (the multiplier from household income to non-tradable demand, range 0.3 to 1.2) first with a 10 pp swing in 2040 employment, ahead of demand elasticity, price pass-through, and the automation-share drift. Nobody has estimated this for AI-driven cost savings. It is a macro parameter borrowed from the fiscal literature, and it decides whether the tool says "jobs fall" or "jobs hold".

2. **Displacement is regressive by age and income even though exposure is not.** Jobs below baseline in 2040 land 48% on 16 to 24-year-olds (13% of employment) and 43% on 25 to 44-year-olds, almost nothing on the over-45s. By income decile the employment effect runs from −1.0% in the bottom half to −0.1% in the top decile. This is not because low-wage tasks are more exposed (they are less exposed) but because the whole adjustment runs through hiring, and entrants are young and start in the low deciles. Education shows the same tilt more weakly: high-school −0.9%, bachelor's −0.4%.

3. **The report presets show what separates the published numbers.** The Acemoglu preset (only directly exposed tasks, no reinstatement, no demand feedback, low intensity) gives TFP +0.62% and GDP +1.1% over ten years, inside his stated bounds. The Goldman preset needs no change to feasibility: default task exposure with near-unit-elastic demand (1.1), 90% pass-through of cost savings to prices, historical reinstatement (0.6), and intensity 0.75 gives GDP +7.0% over ten years with employment −0.6%. Between the two reports lie four parameters, none of them about how capable AI is. Both replications now run as tests in CI.

## What surprised me

- **A faster clock does not mean more job loss by 2040.** Moving the central doubling time from 6 to 5 months changed the 2040 employment effect from −3.35% to −3.14%, because displacement arrives earlier, the clock saturates earlier, and reinstatement and re-employment have more years to catch up. Timing and level are different questions; the map at 2030 and the map at 2040 tell different stories.
- **The first-run failure mode was in the equations, not the data.** Before the wage curve and the profit term in the demand feedback, the model produced a wage collapse. With them, real wages rise in every cell of the ensemble. The lesson is recorded in spec §16 so the next reviewer sees the departure from the text.
- **Draws must be re-centred on the scenario.** The first Monte Carlo drew around registry centrals while the levers had moved the central run; the bands were straddling the wrong line. Now a lever moves both.

## What I do not trust yet

1. **Cohort incidence rules are estimates.** Entrant age split (70/30), re-employment and exit hazards by age, and seniority protection are all tagged E; the age marginals are a fixture until the CPS ASEC ingest runs. The direction (young, low-decile) follows from the hiring channel and is robust; the magnitudes are not.
2. **The structural ensemble is three axes, not the whole literature.** Demand elasticity, reinstatement, and pass-through are the disagreements I could name. The ever-automatable mass and the domain-transfer factor are handled parametrically with wide ranges, which understates how much people disagree about them.
3. **The tornado is one-at-a-time.** Interactions (fast clock with low pass-through) are in the Monte Carlo but not in the tornado; the copula correlations are set by judgement (spec §7.1).
4. **Presets replicate headlines by construction.** They demonstrate which parameters separate the reports; they do not validate the model against those reports' internals.
5. **Single sector still.** Sector heterogeneity in demand elasticity and labor cost share is absent until the OEWS industry matrix is ingested, and the Bessen mechanism is the second-largest tornado bar.
6. **The compare view is only as good as the pairing.** Paired deltas assume both runs share the seed and draw count, which the API enforces; a compare across different draw counts truncates to the smaller.

## Runtime and reproducibility

200 draws with the 8-cell ensemble: 9.1 s on 4 cores. Tornado 4.0 s. Channels 1.0 s. Full document 4.3 MB, gzip-served. Same scenario hash and seed give identical percentiles across runs (tested). `make setup && make data && make run` reproduces this note from a clean clone.

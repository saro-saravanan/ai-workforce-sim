# The model on one page (Phase 9b)

*What the model is, what it computes, which numbers are fitted, and which numbers are assumed. Read this before any result.*

## What it is

A **structured scenario model** of how AI reshapes work and output in ten regions, 2024–2040, quarterly. It is not an estimated forecasting model: it has 116 registry parameters plus scenario levers, six calibration targets, and a structural ensemble over the mechanisms economists disagree about. Every output is a difference from a counterfactual in which frontier AI stopped improving in 2023.

## The chain, in five equations

1. **Feasibility.** Each of ~19,000 O*NET task groups becomes feasible when a capability index `C(t)` (a clock in doublings of task horizon, anchored to METR's series, with regional access lags) passes its threshold `θ_k`; softness `s`. Embodied tasks (driving, manipulation, fixed automation, aerial) have their own clocks coupled to the software clock, with an ever-automatable share `a_c` and a presence discount.
2. **Adoption and substitution.** A task is handed to AI when it is feasible and cheaper than the worker: `prof = σ((ln w_o − ln κ_k) / b)`, where `κ_k` is the cost of the AI work (tokens at the fixed-capability price plus integration) times the market-price multiple `m(t)`; adoption follows a Bass curve by firm size and sector calibrated to BTOS.
3. **Labour flows.** The required cut in each occupation is met first by not refilling positions (attrition, landing on entrants) and by layoffs at a fitted share; the displaced flow to other occupations, retraining, unemployment or exit; cohorts age; wages respond to excess supply.
4. **Output and prices.** Output is demand-determined at baseline prices with cost savings raising TFP; prices fall with a pass-through lever; demand responds to lower costs (sector elasticity) and, under the demand closure, to household income through a multiplier `m` (P.87). Incremental AI capex enters as investment.
5. **Producers' revenue and rents.** Employers' spend at market prices plus consumers' AI spending plus AI-made content, split across model, compute, chips and integration stages and allocated to regions by market share.

## What is fitted, and to what

| Parameter | Fitted to | Value |
|---|---|---|
| Adoption `q` and firm-size thresholds | BTOS share of firms using AI, 2023–2026 | q = 0.55 |
| Layoff-first share (labor.layoff_first_share) | Challenger AI-cited announced cuts, 2025 and Jan–Jun 2026 | 0.25 |
| Market-price multiple P.143 (2025) and consumer path P.140 | AI industry revenue 2025 ($45–80bn) and 2026 ($90–200bn) | 5.0; $15bn |
| Capex path P.80–P.82 | Company reports 2024–2025 and 2026 guidance | $400bn (2025), +80%, +10%/yr to 2029 |

Everything else is transcribed from a source (tag S), derived from data (D) or estimated by the authors (E); the registry carries the tag and the source line for each. The four fitted rows appear on the scoreboard marked *calibration target* and are not evidence of fit.

## What is assumed, in order of consequence

1. **Macro closure.** Default: demand closure with multiplier P.87 (0.3–0.9). Alternative: no-demand-feedback closure (the multiplier switched off; a wage-clearing full-employment closure needs the market-clearing wage variant as well). Both are cells of the structural ensemble; the Story shows the median under each.
2. **The capability clock and the ever-automatable mass** (METR horizons; GPTs-are-GPTs exposure; class clocks for embodied work).
3. **Hiring-first adjustment** landing on entrants, with an entrant-supply response to relative wages (P.146).
4. **The regional layer**: shared production ramp (lever: local), rents by assumed market shares, placeholder occupation mixes outside the U.S.
4b. **The sector layer**: 20 NAICS sectors with the OEWS May 2025 occupation mix; labour's share of gross output (prices, demand) and of value added (the reported productivity gain) are authors' estimates until the BEA use table is fetched, when they and the direct-requirements matrix (input-output propagation) come from it.
5. **Embodied cost curves** with learning rates, ramp caps, approval paths and cost floors.
6. **The revenue layer's** multiple and consumer path.

## How it is tested

- **Backtest** 2024Q1–2026Q2 against BTOS, Challenger, industry revenue, capex and the U.S. robotaxi fleet (results `backtest`; the Story's "How the model has done so far"); rows used in fitting are marked; `aiwsim diag holdout` refits to 2025 alone and scores 2026 (`docs/holdout-2026.md`).
- **Scoreboard** of named forecasts on every run (12 comparisons, 4 calibration targets).
- **Convergence**: `aiwsim convergence` reports p10/p50/p90 by draw count and seed; the baseline draw count is set so the p90 edge is stable.
- **Regional decomposition**: `aiwsim regional` reports the U.S. headline under the U.S.-closed configuration, local ramp allocation and traded services off.
- **Threshold-seed sensitivity**, the exposure-source swap (GPTs-are-GPTs against AIOE, rank-mapped) and the classifier audit: 120 statements labelled, the rules scored against them (`aiwsim diag threshold-seeds | exposure-source | audit`).
- Replication presets (Acemoglu, Goldman, IMF) reproduce published totals under those authors' assumptions.
- 85 Python tests (identities, monotonicity, central-equals-single-run, validity flags) and 159 web tests.

## How to read a number

- "x% versus no AI" means against the frozen-2023 counterfactual, not against today.
- "Range of the model's assumptions" is the middle 80% of runs across parameter draws and mechanism cells; it excludes model error.
- The central run (draw 0, the scenario as specified) and the median differ; the Story shows both on the headline.
- A "calibration target" row on the scoreboard is a definition, not a test.

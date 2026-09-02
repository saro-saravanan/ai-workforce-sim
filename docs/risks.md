# Risks and assumptions v0.2, ranked by how much they could change conclusions

Ranking criterion: expected swing in the 2035 U.S. net employment effect (or GDP or inequality where different) if the assumption is wrong within its plausible range. "Lever" names the scenario control that exposes it. Items fixed since v0.1 are noted; the v0.1 review moved several risks out of the equations and into named parameters, which is why the estimated-parameter count rose.

| # | Risk / assumption | Why it matters | Plausible swing | Mitigation in v0.2 | Lever |
|---|---|---|---|---|---|
| 1 | **Ever-automatable mass `a_k` is a prior.** Whether a task can *ever* be done by software AI is now an explicit probability by exposure class and presence requirement, and no dataset measures it. | It sets the 2040 ceiling on displacement directly. Halving the E0 mass or the E2 mass moves long-run exposure by tens of percent of employment. | ±30–50% on 2035–2040 displacement | Wide priors, copula-correlated across classes so the aggregate band is honest; heatmap x-axis shows the ceiling itself so the assumption is visible | `capability.ever_automatable_scale`, `P.20–P.23` |
| 2 | **Feasibility points `θ_k` are anchored to Claude usage.** Usage is a lower bound on feasibility, single-vendor, and self-selected; tasks without observed usage get class-level offsets. | Sets *when* the ceiling is approached. A two-doubling error is about a year at the central clock. | ±1–2 years on timing | Threshold on usage share is a lever; AEI offsets by class; reliability shift; calibration view shows anchored vs offset tasks separately | `P.24–P.28` |
| 3 | **Domain transfer from software to other work `g_m`.** METR measures software tasks; the model assumes other cognitive work progresses at 70% of that rate and interpersonal at 50%. No measurement exists. | Governs how fast non-software occupations are reached. At `g = 0.4` most non-software E2 tasks stay outside the horizon until the mid-2030s. | ±2–4 years for non-software occupations | Explicit lever with wide range; correlated with `a_k` in the copula | `capability.domain_transfer` |
| 4 | **Clock extrapolation (`τ` ≈ 5 months).** METR's series: 6.3 months over 2019–2026, ~3 months since 2024; extrapolated to 2040 with saturation at 20 doublings. | With `a_k` and `g_m` in place the clock no longer makes everything feasible, but it still sets the pace. | Factor of 2 on 2032 displacement | Doubling time, drift, saturation, breakthrough and slowdown scenarios | `capability.doubling_months` |
| 5 | **Reinstatement `ρ_new`.** Acemoglu-low vs historical. | ±4–6 pp on 2040 net employment | Structural ensemble axis; presets | `P.61` |
| 6 | **Pass-through of cost savings to prices `π_p`.** Now the step between productivity and both output demand and real wages. Unmeasured for AI. | Determines whether automation is job-neutral (high pass-through, elastic demand) or job-reducing; also the real-wage headline. | Sign of the sector employment effect in elastic sectors; ±3 pp on real wages | Ensemble axis; price index shown; the explain trace names it whenever demand response is the driver | `labor.price_pass_through` |
| 7 | **Output demand elasticity `η_s`.** Old, pre-AI sector estimates. | Same mechanism as 6; applies to both automation and augmentation now. | Sign of augmentation effect by sector | Ensemble axis (Bessen vs unit-elastic) | `P.60` |
| 8 | **Substitution vs augmentation `σ` and drift.** AEI share 43–49%, non-monotone. | ±3–4 pp on 2035 employment | Range includes zero drift; by task family | `P.16–P.17` |
| 9 | **Adoption ceiling and intensity (`B*_f`, `ι^max`).** BTOS measures use, not task share; the ceiling is fitted on two years with a wording break. | ±40% on 2030 displacement | `p`, `b`, `q^×` fixed at priors so the fit is identified; two-series fit; Ramp and AEI shown alongside | `P.46`, `P.50` |
| 10 | **Wage pass-through `β` and adjustment `ε_w`.** | Wage share ±2 pp; earnings Gini sign | Ensemble axis for `β`; real wages reported; income Gini separate | `P.73–P.74` |
| 11 | **Value-chain split and market shares.** Rents are now an output, but the stage split (model/compute/chips/integration) comes from public gross margins and the share model has two estimated sensitivities. | Region-level rent results ±10 pp | Derived from filings; market-share model loosely checked on Ramp vendor shares; localization lever | `P.85`, `P.57–P.58` |
| 12 | **Integration cost and amortization.** No public estimate; zero for entrants by assumption. | ±2–3 years on sector adoption | Sector-scaled; entrant term makes the assumption explicit | `P.09–P.10`, `adoption.entrant_scale` |
| 13 | **Cross-region task-mix equivalence; thin China data.** | ±30% on non-U.S. displacement | Crosswalk quality scored; hatched on map | (data flag) |
| 14 | **Regulatory effects by use case are estimated.** The Annex III mapping to O*NET task families is ours; compliance cost unmeasured. The Act's effect on displacement-relevant adoption is probably smaller than v0.1 assumed. | ±0.5–1 year on EU adoption | Applies only to high-risk task share; timeline is data | `regulation.*` |
| 15 | **Compute capacity constraint and token growth.** Links adoption to capex through two estimated parameters. If tokens per task grow slower than assumed, cost stays near zero and adoption is friction-bound only. | ±1–2 years on adoption timing after 2028 | On by default with a switch; capex path anchored to 2026 guidance | `cost.*` |
| 16 | **Capex path and crowding-out.** Guidance stops at 2026. | ±1 pp U.S. GDP 2027–29 | Incremental over baseline; crowding-out lever; supply-chain shock | `P.56`, `P.80–P.83` |
| 17 | **Net occupational attrition 2.5%/q.** Derived from CPS matched files; if lower, layoffs come earlier and hit older cohorts. | Cohort incidence; ±1 year on timing | Range 1.5–3.5; Canaries test constrains it | `P.63` |
| 18 | **Demand-feedback multiplier `m`.** | ±1 pp on non-tradable employment | Range; channel shown separately | `P.87` |
| 19 | **Robotics stays slow.** | Large upside after 2032 if wrong | Separate clock and `a_phys` | `P.19`, `P.59` |
| 20 | **No general equilibrium.** | Overstates unemployment persistence in tails | Validity warning when displacement > 15%/decade | — |
| 21 | **Baseline reconstruction.** Restoring BLS AI-adjusted occupations to trend depends on BLS documentation being complete. | ±0.5 pp on net effects | Lever to keep the projection instead | `baseline.bls_ai_adjustment` |
| 22 | **Policy financing rules are static.** | Policy comparisons depend on who pays | Rule per lever; fiscal balance shown | `policy.*.financing` |
| 23 | **Regional occupation structure is a fixture.** Every non-U.S. region runs the U.S. task mix tilted by income, with U.S. cohort shares. | Regional employment effects are composition effects until ILOSTAT/Eurostat data replace the fixture; China and India are the least trustworthy | ±50% on non-U.S. displacement | Hatched on the map; `meta.regions[].data_flags`; ingest scripts ready | (data flag) |
| 24 | **Access lags and market shares are estimates.** China's 4-quarter lag and the actor lags are judgement calls from public release history; list prices are transcribed. | Decides where model-stage rents go and how far China trails | ±2 quarters; ±15 pp on rent shares | Export-control and AI Act levers move them; `ingest/epoch_models.py` replaces release dates | `regulation.export_controls`, `regulation.EU.ai_act` |
| 25 | **Value-chain split is from public gross margins.** Model 25 / compute 35 / chips 25 / integration 15 and the chip split US 55 / TW 35 / EU 10. | The rents map is only as good as this | ±10 pp per stage | Tagged D; one table to edit | `P.85` |

## Assumptions stated once

- Tasks are separable and re-bundlable up to the intensity ceiling.
- Feasibility is monotone in the clock; the ever-automatable mass is fixed over the horizon.
- Firms are cost-minimizers with heterogeneous hurdles; no strategic adoption races.
- Workers do not anticipate displacement beyond observed base rates.
- Regions differ in access, cost, regulation, friction, and institutions, not in task technology.
- Task units are conserved when a task moves from a worker to AI (quality differences enter only through `a_k`, `θ_k`, and the reliability shift).
- Population and baseline participation follow official projections.

## What would most change the conclusions

1. A measured feasibility dataset keyed to O*NET tasks would replace `a_k` and `θ_k`; building a partial one is a Phase 5 candidate.
2. Two more years of BTOS, CPS, and AEI data would let the ceiling, intensity, and hiring-channel parameters be fitted rather than checked.
3. An observed slowdown in the METR series, or evidence on domain transfer, would collapse or extend the upper tail of every scenario.

## Status after Phase 5

What the build has done about each risk, and what it has observed. Numbers refer to the 200-draw baseline (`docs/findings-phase*.md`).

| # | Status | Observation |
|---|---|---|
| 1–3 (feasibility mass, thresholds, domain transfer) | Encoded as levers and sampled in the `feasibility_level` block; AEI anchoring unavailable offline (`meta.data_flags.aei_anchoring`) | The tornado ranks `a_base` third to fifth for employment; the demand multiplier ranks first in every scenario, so feasibility is not the binding uncertainty at the central pace |
| 4–5 (clock, price) | Anchored to METR 2025Q3; drift and doubling levers; negative pairing with price decline | Saturation at 20 doublings is reached by the early 2030s in the central run; the clock note now reports doublings and words instead of an unreadable hour count |
| 6–8 (adoption ceiling, intensity, friction) | Ceiling benefit-driven, friction on speed; BTOS grid fit; intensity ceiling 0.7 with the Acemoglu preset at 0.4 | Adoption is broad (64% of employment by 2030) before the labor effect is (−0.7%); the intensity ceiling and the profitability test, not the S-curve, decide the size |
| 9–11 (demand elasticity, reinstatement, pass-through) | The 2×2×2 structural ensemble | Structural spread (6.1 pp) exceeds the parametric spread (5.7 pp) for 2040 employment; the sign of the employment effect is low confidence for that reason |
| 12 (integration cost) | Sector- and size-scaled; entrant term | Small at the central price path; matters only in low-wage tiers |
| 13, 23 (regional task mix) | FIXTURE, hatched on the map, ingest scripts ready | Regional employment effects are composition effects; EU and U.S. differ by 0.3 pp in 2040 |
| 14 (regulation by use case) | Annex III mapping; AI Act, patchwork, licensing levers | The EU AI Act delay lever moves EU employment by a hundredth of a point; the mapping reaches too few displacement-relevant tasks to matter, which is a finding to test against measured compliance costs |
| 15–16 (compute constraint, capex) | Implemented; capacity never binds in the central run | Token demand from the automated task-hours is small against the capex path |
| 17 (attrition 2.5%/q) | Sampled in the `labor_institutions` block | Attrition absorbs the whole contraction in every shipped scenario: layoffs are zero in the baseline and appear only under fast clocks. Cohort incidence follows directly (young entrants carry about half of jobs below baseline) |
| 18 (demand multiplier `m`) | Sampled 0.3–1.2; channel shown separately | The single largest sensitivity; the one parameter that flips the sign of the baseline employment effect |
| 19 (robotics) | Separate slow clock | Physical-presence tasks are untouched through 2040 in the central run |
| 20 (no general equilibrium) | `meta.validity` and a note flag runs where more than 15% of task-hours are displaced within a decade | Not triggered in the baseline or presets; triggered under fast-clock what-ifs |
| 21–22 (baseline reconstruction, financing) | Levers exist; financing rules static | Not yet exercised in a shipped scenario |
| 24–25 (access lags, value chain) | Estimates, tagged; export-control and localization levers | Hardware trade dominates regional rents; China's 4-quarter lag shifts model-stage rents to domestic labs |

Phase 5 added no new modelling risk. The two risks it opened are operational: the chat layer's prompt has not been exercised against a live model, and the public demo is a static export that goes stale until the Pages workflow reruns.

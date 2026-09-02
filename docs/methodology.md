# Methodology

*How the AI Workforce Sim produces its numbers, what they mean, and where they should not be trusted. Written for a reader who will use the tool or cite it; the full equations are in `docs/model-spec.md` (v0.2) and every departure of the code from that text is logged in its §16.*

## 1. What the tool answers

The simulation asks one question, region by region and quarter by quarter from 2024 to 2040: **compared with a world in which frontier AI froze in 2023, how many jobs, which jobs, whose jobs, and what happens to wages, prices, output, and the distribution of the gains?** Everything it reports is a *difference from that frozen-AI baseline*, never a forecast of the level of employment or GDP. Population, participation, and the pre-AI occupational trend follow official projections in both worlds and cancel out.

It is a **layered, reduced-form simulation**, not a general-equilibrium model and not a statistical forecast. Each layer is small enough to read, every parameter has a source and a range, and the layers are chained so that a change in any input can be traced to its effect on any output. The price of that transparency is that the model has no market clearing: it says how far cost savings, demand responses, and hiring frictions push employment and wages, with a validity warning in the results document (`meta.validity`) and the model notes when the push is large enough that a closed economy would react in ways the model omits (more than 15% of task-hours displaced within a decade).

## 2. The five layers

The model is a pipeline of five layers, run quarterly. The whiteboard version, from the specification:

> AI capability rises on an exponential clock; each task has a probability of ever being automatable by software and, if so, a point on the clock at which it becomes feasible; firms hand over the tasks that are both feasible and cheaper than the worker, on an S-curve gated by benefit, friction, regulation, and access; automation and augmentation both lower unit costs, which raises output demand, so employment falls only where cost savings outrun demand; displaced workers flow to other occupations, retraining, or exit depending on who they are, and cohorts age; wages respond to excess supply and are deflated by falling prices; output, profits, AI rents by value chain, taxes, and inequality follow; and every effect is reported as a band relative to a world where AI froze in 2023, across parameter draws and across the mechanisms the literature disagrees on.

### 2.1 Task feasibility (spec §2)

The unit of analysis is the O*NET task, about 19,000 task statements across 831 six-digit U.S. occupations, merged into roughly 9,400 *task groups* that share an occupation, an exposure class, a modality, a use case, a consequence level, and a physical-presence bucket. Each task carries:

- an **exposure class** from the Eloundou et al. (2023) rubric (E0 not exposed, E1 exposed to a language model alone, E2 exposed with additional software), which sets the **ever-automatable mass** `a_k`: the share of the task's hours software could take over at any capability level (central 0.9 for E1, 0.7 for E2, 0.25 for E0, reduced further where physical presence is required);
- a **feasibility threshold** `θ_k` on the capability clock, the point at which a system at the frontier can do the task at acceptable reliability. Where usage data exist the threshold would be anchored to observed adoption; offline, E1 tasks are spread deterministically across 2024–2025 and E2/E0 tasks follow class offsets. This is the model's largest estimate and is flagged as such in every results document (`meta.data_flags.aei_anchoring`);
- a **modality** (software, other cognitive, interpersonal, physical) with a **domain-transfer factor** `g_m` that slows the clock for work unlike the software tasks the capability benchmark measures;
- a **task-level profitability test**: a task moves only when the cost of the tokens it needs, at the region's price and the task's token demand, is below the worker's wage for those hours, including an integration cost that scales with firm size.

Realized **displacement** `D` (task-hours handed to AI) and **augmentation** `U` (task-hours made more productive while still done by a person) are computed per occupation and quarter from these attributes, the clock, prices, and adoption.

### 2.2 AI capability supply (spec §3)

Capability is a single global **clock** measured in doublings of the METR 50%-success task horizon, anchored at 7.1 doublings in 2025 Q3 with a central doubling time of 5 months and a drift lever; it saturates at 20 doublings. Twenty-three named **actors** (labs, compute providers, chokepoint suppliers) in the U.S., EU, and Asia carry a weights posture, a frontier lag, a release cadence, list prices, and per-region availability. A region reads the frontier at an **access lag**: the larger of its regulatory delay and its best available actor's lag, moved by the EU AI Act and export-control levers. Inference **prices** fall at a fixed capability (central 0.5× per year), compressed further where open-weights models are available, above a **compute cost floor** and a **capacity multiplier** that rises when token demand outruns the capex-implied capacity (it never binds in the central run). Robotics runs on a separate, slower clock. Actor **market shares** per region follow frontier lag, relative price, and availability, and determine where model-stage rents accrue.

### 2.3 Adoption and diffusion (spec §4)

Firms adopt on a **Bass-type S-curve** by sector, firm-size class, and region. The **ceiling** of the curve is driven by the benefit available (the profitable, feasible task share of the wage bill); **friction** (sector-specific and small-firm multipliers, use-case regulation under the EU AI Act Annex III mapping and the U.S. state patchwork) slows the speed, not the ceiling. AI-native **entrants** add adoption without integration cost. Within adopting firms an **intensity ceiling** (central 0.7) caps the share of feasible task-hours actually moved. Adoption in non-U.S. regions receives a **spillover** from U.S. adoption at a lag. The curve is calibrated to the Census Bureau's Business Trends and Outlook Survey (BTOS) 2023–2026 adoption series in a grid fit of the imitation coefficient and the ceiling scale.

### 2.4 Labor-market flows (spec §5)

Labor demand per occupation is a **unified cost–demand treatment**: automation and augmentation both cut unit costs; a sector's output demand responds with elasticity `η_s`; pass-through `π_p` decides how much of the saving reaches prices and therefore demand; the net change in task-hours becomes a change in required employment, offset by a **reinstatement ratio** (new tasks created per task automated, the Acemoglu–Restrepo term). Employers meet a required contraction **first through net occupational attrition** (central 2.5% of an occupation per quarter), so the first casualties are unfilled vacancies, and **second through layoffs** limited by a friction parameter. Workers below baseline flow to re-employment, retraining (a duration queue with a success rate), unemployment, or exit, with hazards by age. **Cohorts** (age band, education, income decile) are tracked as jobs below baseline, and they age. **Wages** adjust partially each quarter toward a wage-curve target in excess supply and rise with pass-through from productivity; real wages deflate by a price index built from the pass-through of cost savings. AI-production employment (data centers, model labs, integrators) is added from the capex and spend paths.

### 2.5 Macro (spec §6)

Output is **task-based**: value added rises with the productivity of automated and augmented task-hours and falls with lost employment, with a demand multiplier `m` on the consumption response. Incremental **AI capex** enters as investment with crowding-out. **Prices** fall with pass-through; **real income** follows. AI **spend** is split across four value-chain stages (model, compute, chips, integration) and the **rents** at each stage are allocated to regions by market share, data-center location, a fixed fab split, and domestic integration; **net AI trade** (rents received minus spend) enters regional GDP. Households' demand feedback uses marginal propensities of 0.7 out of wages and 0.4 out of profits. Government transfers and the policy levers (retraining subsidy, wage insurance, basic income, AI tax, work-week, immigration) have explicit financing rules. Inequality is reported through the wage share and the decile incidence of jobs below baseline.

## 3. Uncertainty: three kinds, reported separately

**Parametric.** Every run is a Monte Carlo of 200 draws from the parameter registry. Draws come from a Gaussian copula with four correlation blocks (feasibility level, capability speed, adoption friction, labor institutions) and a negative pairing of the doubling time with the price decline, through Latin hypercube sampling, **re-centred on the scenario's lever values** so that a lever moves the band and not only the central line. Draw 0 is always the scenario exactly as specified and is drawn as the dashed central line; the shaded bands are the 10th–90th (darker 25th–75th) percentiles of the other draws.

**Structural.** The literature disagrees on three mechanisms that no range on a parameter captures: whether demand responds to lower costs with unit elasticity or with the lower Bessen-style elasticities; whether reinstatement follows the historical Acemoglu–Restrepo rate or the lower recent estimate; and whether pass-through to prices is low or mid. The draws rotate through the 2×2×2 **ensemble cells**, and the results report the spread *between* cell medians alongside the spread *within* cells. When the structural spread exceeds the parametric spread, which is the case for 2040 employment in the baseline, the honest statement is that which theory is right matters more than which number.

**Sensitivity and confidence.** A one-at-a-time **tornado** over twenty curated parameters at their literature low and high reports, for each headline metric, the swing and whether the parameter can flip the sign. A **confidence classification** (high / medium / low) for each headline metric at 2030 and 2040 combines the share of draws agreeing with the central sign, agreement across ensemble cells, and the absence of sign flips in the tornado. The glyph next to every headline tile in the app is this classification; the chat layer and the briefs repeat it with every number.

## 4. Calibration and validation

The model is **fitted** on two quantities only: the adoption curve's imitation coefficient and ceiling scale against BTOS 2023–2026. Everything else is **checked** rather than fitted, because the post-2023 record is too short to identify more: the capability clock against the METR horizon series (2019–2026), the capex path against 2024–2026 guidance, and the early hiring-channel signature against the observed slowdown in entry-level postings in exposed occupations. **Preset scenarios** replicate the headline claims of three published studies by moving only their stated assumptions: the Acemoglu (2024) preset stays within his 0.66% ten-year TFP effect with intensity, pass-through, and reinstatement at his values; the Goldman Sachs (2023) preset reaches its 7% GDP effect (±1.5 pp) with a higher intensity ceiling, demand elasticity, pass-through, and reinstatement; the IMF (2024) preset carries that report's exposure assumptions and is shipped for comparison without a replication test. Continuous integration runs the first two replications as tests, together with conservation checks (jobs lost equal the sum of destinations; rents received across regions equal spend), determinism across runs, and a runtime budget.

## 5. Data and provenance

Every dataset carries a provenance record (`data/provenance/*.json`) with source, license, vintage, access method, and status, and every results document lists its data flags in `meta.data_flags`. As built in the offline sandbox:

| Layer | Real, from source | FIXTURE (structural placeholder, labelled in the UI and the documents) |
|---|---|---|
| Tasks and occupations | O*NET task statements and exposure ratings from the Eloundou et al. *GPTs are GPTs* replication data (MIT license); OEWS May 2021 employment and wages; BLS Employment Projections 2020–30 growth | O*NET Job Zones used for education and age tilts |
| Capability and cost | METR task-horizon series; public release history of 50 models by 23 actors; list prices | Actor availability by region, market-share weights |
| Adoption | BTOS adoption series 2023–2026 | Sector friction multipliers |
| Sub-national and sectoral | Natural Earth 50m/110m boundaries; state and regional population and GDP | Occupation × state and occupation × sector splits |
| Regions | Regional employment, GDP, wage levels, populations | Non-U.S. occupation structure (U.S. mix tilted by income), trade weights, cohort shares |
| Cohorts | OEWS wage percentiles for deciles | Age and education joint distribution |

Ingestion scripts for the fixtures (`sim/aiwsim/data/ingest/`: OEWS 2025, EP 2024–34, ILOSTAT, Eurostat LFS, CPS ASEC via IPUMS, AEI usage anchoring, Epoch notable models, OECD TiVA) are written and untested against the live sources; the model rebuilds from them with one command. Parameters in the registry are tagged **S** (sourced from a study or dataset), **D** (derived from data in the repository), or **E** (the authors' estimate); the tornado and the briefs show the tag next to each parameter.

## 6. How to read a result

- **Relative to the frozen-AI baseline.** "Employment −2.4%" means 2.4% fewer jobs than the same economy would have had without frontier AI, not a fall from today.
- **Median with a band.** The point value is the median draw; the brackets are the 10th–90th percentile. The dashed line is the scenario as specified.
- **Confidence.** High means the sign holds in at least 90% of draws, every ensemble cell agrees, and no single parameter flips it. Low means one of those fails; the results say which parameter can flip it.
- **Hatching** on the map marks regions whose occupational structure is a fixture.
- **Channels.** The Economy view decomposes the headline into automation, augmentation, demand response, reinstatement, demand feedback, and AI investment, switched on in that order, so a reader sees which mechanism carries the result.
- **What changed.** Every run of a child scenario lists the lever differences from its parent with the mechanism each lever acts through; paired comparison against the parent uses the same draws, so the difference band excludes shared parameter noise.

## 7. What the model says now, and what it does not

The findings notes (`docs/findings-phase1.md` to `findings-phase5.md`) record the model's statements after each phase. The stable ones are: employment effects are small relative to GDP effects because cost savings feed demand; the adjustment runs through hiring rather than layoffs at the central pace, which concentrates incidence on entrants and young workers; the demand multiplier dominates the uncertainty in employment; and regional rents concentrate in the chip and model producers. Each of these depends on estimated parameters (`a_k`, `θ_k`, `m`, the attrition rate) that measured data would sharpen; the risks register (`docs/risks.md`) ranks them.

The model does **not** say anything about: levels of employment or GDP; the financial sector, debt, or monetary policy; migration between sub-regions; the informal sector; strategic behaviour by labs or governments; or outcomes in a tail where displacement outruns the economy's ability to respond, where its own validity warning applies.

## 8. The chat layer

The Claude-backed assistant in the app translates a question into scenario levers, proposes a diff, and runs only after confirmation; it explains a number by reading the same channel decomposition, mechanism trace, sensitivity, and confidence the views show; and it ranks findings from a deterministic candidate list. It never computes: every number in a reply comes from a tool call into the API, the reply lists those calls, and the tools refuse to run a scenario the user has not confirmed. Without an API key, the deterministic insights and the briefs still work.

## 9. Reproducing a result

```
make setup && make data          # uv and pnpm install; build the canonical tables with provenance
uv run aiwsim run --scenario baseline           # 200 draws, ten regions, ~20 s on 4 cores
make demo                                        # API on :8000, web app on :5173
```

Every results document carries `meta.scenario_hash`, a hash of the canonical scenario, the specification version, and the data version. The same hash on the same commit reproduces the same document; the briefs print it. The public demo is a static export of the shipped scenarios (`python -m aiwsim_api.export_static`), rebuilt by the Pages workflow on every push.

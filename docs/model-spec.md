# AI Workforce Impact Model — Specification v0.1 (for review)

Status: **draft for review, no simulation code written.**
Scope of this version: the full model as it will exist at Phase 3 (U.S., EU, Asia). Phase 1 implements the U.S. national instance of the same equations with region count = 1.

Decisions already confirmed with the owner (2026-09-01):

| Decision | Choice |
|---|---|
| Occupation × sector grid | ~120 occupation clusters × ~20 sectors |
| Time step | Quarterly, 2024 Q1 → 2040 Q4 (68 steps) |
| Regions at Phase 3 | U.S. (50 states + DC), EU-27 + UK, China, Japan, South Korea, India, Taiwan, Singapore, Rest of Asia |
| Macro layer | Reduced-form, with explicit AI capex channel; not general equilibrium |
| Capability metric | Composite index (task-horizon + benchmark), actors from public data only |
| Calibration | Adoption and prices fitted; labor layer prior-driven and labelled as such |
| Baseline | No frontier AI progress after 2023 Q4 |
| Cohorts | Age (4) × education (4) × income decile (10), jointly fitted from CPS |
| Runtime | Central run < 1 s; 200-draw Monte Carlo < 10 s; cached by scenario hash |
| Data | Open sources only |
| Tooling | Python 3.12 + uv + polars/numpy; Vue 3 + TS + pnpm; monorepo |

Notation conventions: every parameter has an ID (`P.xx`), a central value, a range, a source, and a **provenance tag**: `S` = taken from a cited source, `D` = derived from cited data by a stated transformation, `E` = **estimated by us** (no direct source; flagged and exposed as a lever). All cited numbers were checked against primary sources on 2026-09-01; where a primary page could only be confirmed through secondary pages, the data inventory says so.

---

## 0. The whiteboard version

One sentence: **AI capability rises on an exponential; each task in each occupation flips from "human" to "AI-feasible" when capability crosses that task's threshold; firms adopt on an S-curve gated by cost, regulation, and friction; adopted automation removes labor demand on substitutable tasks and raises productivity on augmentable ones; displaced workers flow to other occupations, retraining, or exit depending on who they are; wages and output respond; and every effect is reported as a band relative to a world where AI froze in 2023.**

```
 AI SUPPLY                 TASKS                    FIRMS                   WORKERS                 ECONOMY
 ┌──────────┐   C_t   ┌────────────┐   S_o,G_o  ┌────────────┐   D,U    ┌────────────┐   ΔL,Δw  ┌────────────┐
 │ actors,  │ ──────▶ │ threshold  │ ─────────▶ │ adoption   │ ───────▶ │ flows by   │ ───────▶ │ output,    │
 │ prices,  │ p_rt    │ crossing   │            │ S-curve by │          │ occupation │          │ wages,     │
 │ regimes  │ ──────▶ │ per task   │            │ sector/size│          │ & cohort   │          │ taxes,     │
 └──────────┘         └────────────┘            └────────────┘          └────────────┘          │ inequality │
      ▲                                              ▲                        │                 └─────┬──────┘
      │ regulation, export controls,                 │ spillover from         │ demand feedback       │
      │ open-weights shocks                          │ other regions          ▼                       │
      └──────────────────────────────────────────────┴────────────────────────────────────────────────┘
```

Five layers, five state vectors, one clock. Everything else is bookkeeping.

---

## 1. Indices, sets, and dimensions

| Symbol | Set | Size (Phase 3) | Source of the list |
|---|---|---|---|
| `t` | quarters 2024Q1..2040Q4 | 68 | — |
| `r` | regions (top level) | 10 (US, EU, UK, CN, JP, KR, IN, TW, SG, RoA) | — |
| `g` | sub-regions | 51 U.S. states+DC; 27 EU members; others = 1 | Census, Eurostat |
| `o` | occupation clusters | ~120 | O*NET-SOC 2019 6-digit → clusters (§1.1) |
| `s` | sectors | 20 | NAICS 2-digit, some merged (§1.2) |
| `k` | tasks | ~19,000 O*NET task statements | O*NET 29.x |
| `c` | cohorts = age × education × income decile | 4 × 4 × 10 = 160 | CPS |
| `f` | firm-size class | 3 (1–49, 50–499, 500+) | Census BTOS, SUSB |
| `a` | AI actors | ~25 | §3.1 |
| `j` | labor-market state | 7 (§5.1) | — |
| `d` | Monte Carlo draw | 200 default | — |

### 1.1 Occupation clusters
Start from the 2019 O*NET-SOC taxonomy (~1,016 occupations, 867 with task data). Cluster to ~120 by: (i) keep every 6-digit SOC with U.S. employment ≥ 300k as its own cluster; (ii) merge remaining occupations within the same 4-digit SOC family when their Eloundou exposure scores are within 0.1 and their median wages within 20%; (iii) never merge across major groups. The clustering is a deterministic script with the thresholds as parameters, and the crosswalk `occupation_cluster.csv` is a versioned artifact. EU and Asia employment are mapped to the same clusters through the BLS/Eurostat SOC↔ISCO-08 crosswalk, with the mapping quality recorded per cluster (§9, gaps).

### 1.2 Sectors
NAICS 2-digit with 31–33 merged (Manufacturing), 44–45 merged (Retail), 48–49 merged (Transportation & Warehousing); 20 sectors. Mapped to NACE Rev.2 sections for EU and to ISIC Rev.4 for Asia.

### 1.3 Cohorts
Age bands {16–24, 25–44, 45–54, 55+}; education {less than high school, high school, some college / associate, bachelor's+}; income decile of individual annual earnings within region. The joint distribution per occupation `π_{o,c}` is fitted once from CPS ASEC microdata (IPUMS) by iterative proportional fitting against the OEWS wage distribution and the ACS age/education marginals per occupation. Non-U.S. regions use the same procedure on EU-LFS microdata where available and marginals-only (age × education, with income deciles imputed from the occupation wage) elsewhere; the imputation is flagged in the UI.

---

## 2. Layer 1 — Task exposure

### 2.1 State (static, computed once at ingestion)

For each task `k` within occupation `o`:

- `w_{o,k}` — task weight, sum to 1 within occupation. Derived from O*NET task ratings: `w ∝ importance × relevance × frequency`, normalized. `[D]`
- `x_k ∈ {0, 0.5, 1}` — LLM exposure label. From Eloundou et al. (2023) task-level labels (E0 = 0, E1 = 1, E2 = 0.5, following their β scoring). Where a task lacks a label, fall back to the occupation-level Felten AIOE score rescaled to [0,1], and flag. `[S]`
- `m_k ∈ {cognitive, interpersonal, physical}` — task modality, from O*NET Generalized Work Activities (GWA) mapping; physical tasks route to the robotics frontier (§3.4), interpersonal tasks receive a substitution penalty. `[D]`
- `θ_k` — **capability threshold**: the value of the capability index `C` at which an AI system performs task `k` at acceptable quality without human review. This is the key bridge between "exposure" and "displacement", and it is **estimated** (`E`) because no dataset provides it. Construction:

$$\theta_k = \theta_{\text{base}}(x_k) + \Delta\theta_{\text{modality}}(m_k) + \Delta\theta_{\text{complexity}}(z_k)$$

where `z_k` is the O*NET "Level" rating of the task's dominant skill (proxy for task length/complexity), and `θ_base(E1) < θ_base(E2) < θ_base(E0)`. Parameters `P.11–P.14`.

- `s_k` — threshold softness (logistic scale); one value per modality. `P.15`
- `σ_k ∈ [0,1]` — **substitution share**: the fraction of a task that, once AI-feasible, removes labor demand rather than raising the worker's output. `1 − σ_k` is the augmentation share. Initialized from the Anthropic Economic Index automation/augmentation split by O*NET task family and allowed to drift with capability (agentic use). The observed automation share is not monotone (43% in the Feb 2025 report, 49% in Sep 2025, 45% in Jan 2026), so the drift is a lever whose range includes zero. `P.16–P.17` `[S → D]`

### 2.2 Update rule (each quarter, given regional capability `C_{r,t}`)

Feasibility of task `k` in region `r` at quarter `t`:

$$F_{k,r,t} = \Lambda\!\left(\frac{C_{r,t} - \theta_k}{s_k}\right), \qquad \Lambda(u) = \frac{1}{1+e^{-u}}$$

Occupation-level substitutable share and augmentable share:

$$S_{o,r,t} = \sum_k w_{o,k}\, \sigma_{k,t}\, F_{k,r,t}, \qquad G_{o,r,t} = \sum_k w_{o,k}\,(1-\sigma_{k,t})\, F_{k,r,t}$$

`S` is the fraction of the occupation's labor input that AI could replace *if fully adopted*; `G` is the fraction that AI could speed up. Exposure as reported by the static literature corresponds to `S + G` at `C → ∞`; what the tool adds is the time path.

Reliability discount: METR reports that the 80%-success horizon is roughly a quarter of the 50% horizon. We use the 50% horizon as the index and shift `θ` up by `P.18` (one doubling by default) for tasks whose O*NET "Consequence of Error" rating is in the top tercile. `[D]`

### 2.3 What this layer does not do
It does not model within-occupation heterogeneity in task mix (a paralegal at a big firm vs a small one); the cluster average is used. It does not model quality-of-output effects except through `θ` and the reliability discount.

---

## 3. Layer 2 — AI capability supply

### 3.1 Actors
Each actor `a` is a record in `data/actors.yaml`, from public data only:

| Field | Meaning | Source |
|---|---|---|
| `region_a` | home jurisdiction (US, EU, UK, CN, JP, KR) | public |
| `λ_a` | frontier lag: quarters behind the global frontier at each release | Epoch Notable Models + benchmark hub `[D]` |
| `κ_a` | release cadence, releases/year | release history `[D]` |
| `ω_a` | open-weights posture ∈ {closed, open-lagged, open-frontier} | release history `[S]` |
| `p_a(t)` | API price per million tokens at the actor's frontier tier | published price lists, Artificial Analysis `[S]` |
| `V_{a,r}(t)` | availability in region r ∈ [0,1] | terms of service, export controls `[S/E]` |
| `role_a` | {lab, compute, chokepoint} | — |

Initial list: US — OpenAI, Anthropic, Google DeepMind, Meta, xAI, Microsoft, Amazon, NVIDIA (compute). EU/UK — Mistral, Aleph Alpha, DeepMind London (folded into Google DeepMind for capability; kept as a regulatory-jurisdiction record), ASML (chokepoint). Asia — DeepSeek, Alibaba (Qwen), ByteDance, Moonshot, Zhipu, Baidu, Tencent, Samsung, SoftBank, Naver, Sakana, TSMC (chokepoint, added because the Taiwan shock needs it).

Compute and chokepoint actors do not release models; they enter through the cost floor and the supply-shock levers (§3.5).

### 3.2 Global frontier capability

`C_t` is the composite capability index of the best model available anywhere at quarter `t`, in units of **doublings of the 50%-success task horizon** (log₂ of horizon in human-minutes, METR definition), cross-checked against the Epoch Capabilities Index so that a benchmark-only actor can still be placed. Anchors `[S]`, METR 50%-success horizons: GPT-5 (Aug 2025) ≈ 2 h 17 min ≈ 7.1 doublings; Claude Mythos Preview (evaluated Mar 2026) ≥ 16 h with a 95% interval of 8.5–55 h ≈ 9.9 doublings. METR notes that only 5 of its 228 tasks exceed 16 hours, so horizons above ~8 h are unstable; the 2026 anchor therefore carries a wide prior.

Update rule (exogenous trend plus shocks):

$$C_{t+1} = C_t + \frac{1}{\tau_t / 3} + \epsilon^{C}_t, \qquad \tau_t = \tau_0 \cdot (1 + \gamma)^{(t - t_0)/4}$$

`τ` is the doubling time in months (`P.01`, central 5, range 3–12; METR Time Horizon 1.1 gives 6.3 months over 2019–2026 and about 3 months since 2024, so the central value deliberately sits between the long-run and the recent rate) and `γ` (`P.02`) is the per-year change in doubling time (central 0 = steady exponential; positive = slowing; the lever "capability progress rate" sets both). `ε^C` is a mean-zero draw per Monte Carlo run (`P.03`). A **frontier breakthrough shock** adds a one-time jump `ΔC` (§8).

**Endogenous feedback (off by default, lever `L.capability_feedback`)**: AI revenue in the model raises lab compute budgets and shortens `τ`. This is the one place where adoption feeds back to capability; it is off by default because the mapping from revenue to capability has no public estimate. `[E]`

### 3.3 Regional available capability and price

Available capability in region `r`:

$$C_{r,t} = \max_a \big[ C_t - \lambda_a - \delta^{\text{reg}}_{r,t} \big] \cdot V_{a,r}(t)$$

with `δ^reg` the regulatory availability delay (quarters) for closed frontier models in `r` (EU AI Act, China licensing), `P.30`.

Price per million tokens at fixed capability level `C'` declines at rate `ρ` per year (`P.04`, central 10×/yr, range 3×–50×):

$$p_t(C') = p_{t_0}(C') \cdot \rho^{-(t - t_0)/4} \cdot \max\big(1, \text{floor}_t / p\big)$$

Open-weights compression: when any actor with `ω = open-frontier` releases within `P.05` quarters (central 2) of the frontier, the price of that capability tier in every region where the weights are legal drops to `P.06 ×` the closed price (central 0.25, range 0.1–0.5). `[D from DeepSeek-R1 / Llama pricing episodes]`

Cost floor: `floor_t` = compute + energy cost per token, itself declining at `P.07` per year but subject to the supply-chain shock (§8).

Effective cost to execute one unit of task `k` in sector `s`, region `r`:

$$\kappa_{k,s,r,t} = \underbrace{p_{r,t}(\theta_k)\cdot n_k}_{\text{inference}} + \underbrace{I_{s} / H}_{\text{integration, amortized}} + \underbrace{\chi_{r,s,t}}_{\text{compliance}}$$

`n_k` tokens per task-unit (`P.08`, estimated from AEI conversation lengths by task family, `E`); `I_s` integration cost per worker-equivalent (`P.09`, `E`, sector-specific); `H` amortization horizon in quarters (`P.10`); `χ` regulatory compliance cost premium (`P.31`).

### 3.4 Robotics frontier
A second index `C^{phys}_t` for manipulation tasks, with its own (slower) doubling time `P.19` (central 24 months, range 12–48, `E`) and a start lag. Physical tasks use `C^phys` in §2.2. Default settings make physical-task displacement small before 2032; the lever exists so the assumption is visible, not buried.

### 3.5 Chokepoints
`floor_t` and `V_{a,r}` are functions of two switches: **export-control regime** (affects `λ` for Chinese actors and `V` for U.S. actors in China) and **supply-chain integrity** (Taiwan/ASML). Both are levers (§8).

---

## 4. Layer 3 — Adoption and diffusion

### 4.1 State
`A_{s,f,r,t} ∈ [0,1]` — share of firms in sector `s`, size class `f`, region `r` that have adopted AI for production tasks (BTOS original wording: "used AI in producing goods or services in the last two weeks"; the question changed on 17 Nov 2025 to "in any of its business functions", which is treated as a second series, see §4.3).
`ι_{s,f,r,t} ∈ [0,1]` — intensity: within adopting firms, the share of feasible task-units actually handed to AI.

### 4.2 Update rules

Net benefit of adopting for the marginal firm (per worker-equivalent, per quarter):

$$B_{s,f,r,t} = \sum_o e_{o,s,r}\, \bar w_{o,r,t}\,\big[S_{o,r,t} + \psi\, G_{o,r,t}\big] - \sum_o e_{o,s,r}\sum_k w_{o,k} F_{k,r,t}\, \kappa_{k,s,r,t}$$

`e_{o,s,r}` is the employment share of occupation `o` in sector `s` (OEWS industry-occupation matrix), `w̄` the mean wage, `ψ` the productivity gain per augmented task-unit (`P.40`, central 0.25, range 0.10–0.50, `[S]` from the RCT literature).

Adoption follows a Bass process whose speed is scaled by benefit, friction, and cross-region spillover:

$$A_{t+1} = A_t + \big[p_{s,f,r} + q\,A_t + q^{\times}\sum_{r' \ne r} \omega_{r r'} A_{s,f,r',t-L}\big]\,(1 - A_t)\,\Lambda\!\left(\frac{B - B^*}{b}\right)\,\phi_s\,\phi_f\,\phi^{\text{reg}}_{r,s}$$

- `p`, `q` innovation and imitation coefficients, `P.41–P.42`, priors from the Bass meta-analysis (Sultan et al. 1990: p≈0.03/yr, q≈0.38/yr) then **fitted to BTOS** (U.S.), Eurostat ICT-usage survey (EU), and national surveys (Asia).
- `q^×`, `L`, `ω_{rr'}` cross-region spillover strength, lag (central 4 quarters, range 2–8), and weights (trade + language + corporate-presence, `E`). `P.43–P.45`
- `B*`, `b` adoption hurdle and softness, `P.46–P.47` (`E`, fitted).
- `φ_s` sector friction ∈ (0,1], `P.48`: derived from the ratio of BTOS sector adoption to the sector's exposure (`D`); low for construction, agriculture, health care delivery; high for information, finance, professional services.
- `φ_f` firm-size friction, `P.49`, from BTOS size gradient (`D`).
- `φ^reg` regulatory friction (`P.32`): a multiplier < 1 for sectors and regions where the use case is "high-risk" under the EU AI Act (employment, credit, education, essential services) or licensed under China's regime.

Intensity ramps within adopters toward a ceiling `ι^max` (`P.50`, central 0.7, range 0.4–0.9, `E`; the ceiling encodes that some feasible tasks stay human for liability or preference reasons) at speed `P.51`.

Realized AI task share in occupation `o`, sector `s`, region `r`:

$$D_{o,s,r,t} = \sum_f \pi_{s,f}\,A_{s,f,r,t}\,\iota_{s,f,r,t}\,S_{o,r,t}, \qquad U_{o,s,r,t} = \sum_f \pi_{s,f}\,A_{s,f,r,t}\,\iota_{s,f,r,t}\,G_{o,r,t}$$

`D` = displacement pressure (share of labor input removed), `U` = augmentation coverage (share of labor input sped up). `π_{s,f}` is the employment share of size class `f` in sector `s` (SUSB).

### 4.3 Calibration targets for this layer (§7)
BTOS national and sector series: 3.7% (Sep 2023) → 5.4% (Feb 2024) → ~10% (Sep 2025) under the original wording; after the 17 Nov 2025 wording change the series jumped to 17.3% and reached 19.8% by May 2026 (32% employment-weighted, 18% firm-weighted over Nov 2025–Jan 2026). The two wordings are fitted as two series with a break, never spliced. BTOS firm-size gradient (employment-weighted vs firm-weighted gap). Ramp AI Index as an upper-bound cross-check (50.4% of businesses paying for an AI vendor in Aug 2026; paying ≠ using in production). AEI task-family usage shares as a check on `ι` composition.

---

## 5. Layer 4 — Labor-market flows

### 5.1 State
`N_{o,s,r,t}` employment (headcount) by occupation, sector, region.
`N_{o,r,c,t}` employment by occupation, region, cohort (cohort is tracked at the occupation level, not sector, to keep memory bounded; consistent by construction because `Σ_s N_{o,s,r} = Σ_c N_{o,r,c}`).
`M_{j,r,c,t}` stock of workers in labor-market state `j ∈ {employed, displaced-searching, retraining, unemployed-long, exited, retired, new-entrant}` by cohort.
`w_{o,r,t}` mean quarterly wage by occupation and region; `w_{o,r,c,t}` cohort wage = `w_{o,r,t} × ζ_{o,c}` (static cohort wage ratios from CPS).
`V_{o,r,t}` vacancies (needed for the hiring channel).

### 5.2 Labor demand
Baseline labor demand `N^0_{o,s,r,t}` follows the frozen-AI counterfactual: BLS Employment Projections 2024–34 growth rates (extended flat to 2040), Eurostat/Cedefop skills forecast for the EU, national projections where they exist, demographic labor-supply trends otherwise.

AI-adjusted labor demand:

$$N^{\ast}_{o,s,r,t} = N^0_{o,s,r,t}\,\underbrace{(1 - D_{o,s,r,t})}_{\text{displacement}}\;\underbrace{(1 + \psi\,U_{o,s,r,t})^{\,\eta_s - 1}}_{\text{augmentation × demand response}}\;\underbrace{(1 + \nu_{o,r,t})}_{\text{new tasks}}\;\underbrace{(1 + \mu_{s,r,t})}_{\text{demand feedback}}$$

- **Augmentation with demand response.** If AI makes a worker `(1+ψU)` times more productive, employment falls unless demand for the sector's output is elastic. `η_s` is the price elasticity of demand for sector output (`P.60`, sector-specific, `[S]` from Bessen 2019 and the trade literature; central 1.0 for tradables, 0.6 for local services, range 0.3–1.5). At `η = 1` augmentation is employment-neutral; below 1 it is job-reducing; above 1 it is job-creating. This is the Bessen mechanism made explicit.
- **New-task creation (`ν`).** Acemoglu–Restrepo reinstatement. New task demand accrues to occupations in proportion to a "complementarity" weight (the Felten/IMF complementarity index) and cumulates to a fraction `ρ_new` (`P.61`, central 0.4, range 0.1–0.8, **the Acemoglu-vs-Goldman disagreement lever**) of cumulative global displacement over 10 years, with a lag `P.62` (central 8 quarters). `[E]`
- **Demand feedback (`μ`).** From the macro layer (§6): lost household income lowers demand for non-tradable output in the same region with multiplier `m`.

### 5.3 The hiring channel first, layoffs second
Firms close the gap between `N` and `N*` in this order each quarter:

1. **Reduced hiring**: gap absorbed by not replacing natural separations, up to the separation rate `ς` (`P.63`, JOLTS: total separations ≈ 3.3%/month ≈ 10%/quarter, `[S]`; retirements from CPS age profile). This is why displacement shows up first as collapsed entry-level hiring, which is the 2025 signal in the data (Brynjolfsson, Chandar, Chen "Canaries in the Coal Mine": a 13% relative employment decline for 22–25-year-olds in the most exposed occupations in the Aug 2025 version, widened to 19% through June 2026 in the Aug 2026 revision `[S]`).
2. **Layoffs**: the remainder, with a layoff friction `P.64` (share of remaining gap closed per quarter; central 0.25, range 0.1–0.5, `E`; regulated higher in the EU via `P.33` employment-protection multiplier).

Cohort incidence: hiring-channel displacement lands on the **new-entrant** cohort (age 16–24 and 25–44 with < 2 years tenure); layoffs land in proportion to `N_{o,r,c}` adjusted by a seniority protection factor (`P.65`, `E`).

### 5.4 Transitions of displaced workers
Each displaced worker draws a destination state each quarter with probabilities from a cohort- and occupation-specific matrix:

$$\Pr(j' \mid j = \text{displaced}, o, c, r) \propto \text{base}_{j'}(c) \times \text{pull}_{j'}(o, r, t) \times \text{policy}_{j'}(r, t)$$

- Destinations: same occupation elsewhere (needs `V_{o,r,t} > 0`), different occupation (weighted by O*NET skill-vector distance `P.66` and by observed CPS occupation-transition frequencies `P.67`, `[D]`), retraining (base rate by education and age, `P.68`, `[D]` from CPS/ACS enrolment), long-term unemployment, labor-force exit (age-rising, `[D]` CPS), retirement (age ≥ 55, `[D]`).
- Reemployment wage: `w' = w × (1 − ℓ_c)` with a scarring loss `ℓ` (`P.69`, central 0.12, range 0.05–0.25, `[S]` displaced-worker literature; larger for older and lower-education cohorts).
- Retraining success: probability `P.70` of landing in a target occupation after `P.71` quarters (central 0.55 and 4, `E` from WIOA outcome data).
- Policy levers enter as multipliers on retraining entry and success, on unemployment duration (wage insurance), and on exit (UBI raises exit slightly; shorter work week converts headcount reduction into hours reduction at a rate `P.72`).

### 5.5 Wages

$$\Delta \ln w_{o,r,t} = -\,\varepsilon_w\,\big(\text{excess supply}_{o,r,t}\big) \;+\; \beta\,\psi\,U_{o,r,t} \;+\; \Delta \ln w^0_{o,r,t}$$

- `ε_w` wage response to excess supply (displaced-searching stock over employment), `P.73`, central 0.3, range 0.15–0.6, `[S]` inverse of own-wage labor demand elasticity from Lichter, Peichl, Siegloch (2015) meta-analysis.
- `β` pass-through of augmentation productivity to the augmented worker's wage, `P.74`, central 0.3, range 0.1–0.6, `[E]`; the RCT literature shows the *productivity* gain, not who captures it, so this is a lever, labelled as such.
- `w^0` baseline wage growth (frozen-AI path).
- Minimum-wage floors per region prevent nominal declines below the floor (`[S]`).

### 5.6 New entrants and demographics
Each quarter a new-entrant flow by cohort enters (population projections: Census, Eurostat EUROPOP, UN WPP), allocated to occupations by the previous year's hiring shares, reduced by the hiring channel. Immigration is a lever on this flow by education (`L.immigration`).

---

## 6. Layer 5 — Macro

Per region, reduced-form and explicit. Nothing clears a market; every equation is an accounting identity or a stated behavioral rule.

### 6.1 Output

$$Y_{r,t} = Y^0_{r,t}\,\exp\!\big(\Delta\ln \text{TFP}^{AI}_{r,t}\big)\,\Big(\tfrac{L^{\text{eff}}_{r,t}}{L^{0}_{r,t}}\Big)^{1-\alpha_r} \;+\; \text{AICAPEX}^{\text{dom}}_{r,t}$$

- `Y^0` frozen-AI baseline path (IMF WEO / OECD long-run projections).
- `L^eff = Σ_o N_{o,r,t}·h·(1 + ψU_{o,r,t})` effective labor (heads × hours × augmentation).
- `ΔlnTFP^AI` from automation cost savings, Acemoglu (2024) task-level formula: `Σ_o (labor-share of o) × D_o × (cost-saving share)` where cost-saving share `= 1 − κ/w̄` clipped to [0,1]. Using his central assumptions reproduces his ~0.66%/10y; using Goldman's exposure and full adoption reproduces their ~7%. The tool ships both as **presets** (§8.4) so a viewer can see exactly which parameters separate the two reports.
- `α_r` capital share (`[S]` Penn World Table).
- **AI capex channel**: `AICAPEX_dom = share_dom × CAPEX_t`; `CAPEX_t` is an exogenous path with growth and plateau levers (`P.80–P.82`; anchored on reported hyperscaler capex `[S, verify]`), `share_dom` the domestic value-added share (`P.83`, central 0.5 for the U.S. since accelerators are imported; `E`). Capex is also the channel by which the **Taiwan/ASML shock** and the **lab exit** shock hit GDP directly.
- Productivity J-curve: realized `ψ` and TFP gains lag adoption by `P.84` quarters (central 4, range 0–8, `[S]` Brynjolfsson–Rock–Syverson).

### 6.2 Income, profits, wage share

$$W_{r,t} = \sum_{o,c} N_{o,r,c,t}\, w_{o,r,c,t}, \qquad \Pi_{r,t} = Y_{r,t} - W_{r,t} - \delta K_{r,t} - \text{AI spend}_{r,t}$$

`AI spend` is what firms pay for AI (`Σ κ × task-units`), which is revenue to actors; it is allocated to the actors' home regions by market share (`P.85`, `[D]` from public revenue estimates, flagged). This is the mechanism by which EU adoption raises U.S. profits, and it is one of the tool's intended non-obvious outputs.

Wage share `= W/Y`. Corporate profits, wage share, and the split of AI rents by region are reported.

### 6.3 Households, demand feedback

Disposable income by cohort `= wages + transfers − taxes`. Consumption `C_c = MPC_c × disposable income` with `MPC` falling in income decile (`P.86`, `[S]` Fagereng et al. / CBO). The demand feedback into §5.2:

$$\mu_{s,r,t} = m \cdot \text{nontradable}_s \cdot \frac{\Delta C_{r,t}}{C^0_{r,t}}$$

`m` multiplier (`P.87`, central 0.6, range 0.3–1.2, `[S]` fiscal-multiplier literature; `E` in the mapping). Tradable-sector demand includes other regions' consumption via import shares (`P.88`, OECD TiVA, `[S]`). That is the entire trade linkage in v0.1: coarse, by design.

### 6.4 Government

Tax base `= τ_inc(W by decile) + τ_pay W + τ_corp Π` with effective rates from CBO (U.S.), Eurostat/OECD (others) `[S]`. Transfers = unemployment insurance (replacement rate × duration, `[S]`) + retraining subsidy + wage insurance + UBI (levers). Fiscal balance is reported, not constrained (no debt dynamics in v0.1).

### 6.5 Inequality
Gini of individual earnings computed from the 160-cohort earnings distribution (decile means × within-decile spread parameter `P.89`), wage share, 90/10 ratio, and the share of income accruing to AI rents. Reported per region and for the U.S. by state.

---

## 7. Uncertainty and calibration

### 7.1 Monte Carlo
Every `P.xx` with a range is a distribution: triangular (min, central, max) unless the source gives a standard error, in which case lognormal. Draws are Latin-hypercube, `n = 200` default, seeded. Correlations imposed only where the source implies them (`τ` and `ρ` negatively correlated: faster capability, faster price decline). Outputs are stored as 10/25/50/75/90 percentiles per series; the UI never draws a single line for a stochastic output.

### 7.2 Sensitivity
For each scenario run, a one-at-a-time tornado of the top 15 parameters is computed from 30 extra central runs (cheap at < 1 s each) and is what the "how confident are we" explanation uses: an effect is **high confidence** if its sign holds in ≥ 90% of draws and no single parameter flips it within its range.

### 7.3 Calibration targets (what is fitted, what is not)

| Target | Data | Fits | Status |
|---|---|---|---|
| Frontier capability path 2023–2026 | METR horizons, Epoch ECI | `C_0`, `τ_0` | fitted |
| Price decline at fixed capability | Epoch/Artificial Analysis price series | `ρ`, `P.06` | fitted |
| Firm adoption path, national | Census BTOS 2023Q3–2026Q2, two wordings with a break at 2025-11-17 | `p`, `q`, `B*`, `b` | fitted |
| Adoption by sector and size | BTOS sector/size cuts | `φ_s`, `φ_f` | fitted |
| Task-family usage mix | Anthropic Economic Index | `ι` composition, `σ` | checked, not fitted |
| Entry-level employment in exposed occupations | CPS; ADP via Brynjolfsson et al. (Aug 2026 revision) | hiring-channel share `P.63` | **checked only**; too few quarters to fit |
| Occupation employment 2023–2026 | OEWS, CPS | — | **not fitted**; shown against the model for honesty |
| Wages by occupation 2023–2026 | OEWS | — | not fitted |
| EU adoption | Eurostat ICT usage in enterprises (AI module) | `p`, `q` for EU | fitted |
| Asia adoption | national surveys where they exist | — | priors only, flagged |

The calibration view shows each fitted series with the model band and the observed points, and each *unfitted* series the same way with a "prior-driven" label.

### 7.4 Determinism
`run(scenario, seed) → results` is a pure function. Same scenario hash and seed give bit-identical output; the hash is the cache key.

---

## 8. Scenarios, levers, shocks

### 8.1 Scenario file
A scenario is a versioned JSON document (`scenarios/*.json`, schema in `scenarios/schema.json`). Every field is optional; missing fields inherit from `parent`, ultimately from `baseline.json`. Two scenarios are compared by canonicalizing (sorted keys, resolved inheritance) and diffing; the diff is what the "what changed" panel and the chat confirmation show.

```json
{
  "schema_version": "0.1",
  "id": "eu-delay-deepseek-2027",
  "name": "EU AI Act delayed 2y + DeepSeek open frontier 2027",
  "parent": "baseline",
  "seed": 42,
  "draws": 200,
  "levers": {
    "capability": { "doubling_months": 6, "doubling_drift_per_year": 0.0,
                    "per_actor": { "deepseek": { "frontier_lag_quarters": 1 } } },
    "cost":       { "price_decline_per_year": 10, "open_weights_multiplier": 0.25 },
    "regulation": { "EU": { "ai_act": "delayed_2y" }, "US": { "regime": "state_patchwork" },
                    "CN": { "licensing": "baseline" }, "export_controls": "2026_status_quo" },
    "adoption":   { "sector_friction_scale": 1.0, "small_firm_friction_scale": 1.0 },
    "policy":     { "US": { "retraining_subsidy_pct_wage": 0, "wage_insurance_replacement": 0,
                            "ubi_monthly_usd": 0, "ai_tax_pct_of_ai_spend": 0,
                            "work_week_hours": 40, "immigration_scale": 1.0 } }
  },
  "shocks": [
    { "type": "open_weights_release", "actor": "deepseek", "at": "2027Q1", "frontier_lag_quarters": 0 }
  ],
  "overrides": { "P.61": { "central": 0.4, "min": 0.1, "max": 0.8 } }
}
```

### 8.2 Levers (minimum set, all present in v0.1)

| Lever | Parameters it moves | Range exposed |
|---|---|---|
| Capability progress rate (global, per actor) | `P.01`, `P.02`, `λ_a` | doubling 4–12 months; per-actor lag 0–8 q |
| Cost decline rate (global, per actor) | `P.04`, `p_a(t)` | 3×–50× per year |
| EU AI Act strictness | `P.30–P.32` for EU | {repealed; baseline = as amended by the Digital Omnibus, Reg. (EU) 2026/1744: Annex III high-risk obligations from 2 Dec 2027, Annex I from 2 Aug 2028; delayed_2y = a further two-year delay; strict_original_2026 = the original 2 Aug 2026 timetable} |
| U.S. regime | `P.31–P.32` for US | {none; state_patchwork = California SB 53 operative 1 Jan 2026, Colorado SB 26-189 effective 1 Jan 2027, others as enacted; federal_light; federal_strict} |
| China licensing | `P.30`, `V_{a,CN}` | {baseline = Interim Measures in force since 15 Aug 2023 with security assessment and algorithm filing; tightened; liberalized} |
| Chip export controls | `λ_a` for CN actors, `floor` for CN | {rescinded; 2026_status_quo = AI Diffusion rule rescinded May 2025, H20 licensed Aug 2025 with a 15% revenue condition, H200 case-by-case from Jan 2026 with a 25% share and Chinese customs friction; tightened} |
| Adoption friction by sector, by size | `P.48`, `P.49` | scale 0.5–2.0 |
| Retraining subsidy | `P.68`, `P.70`, transfers | 0–100% of wage during training |
| Wage insurance | `ℓ` effective, transfers | 0–50% of wage loss for 2 years |
| UBI | transfers, exit rate | 0–$1,500/month |
| AI/automation tax | `κ` (raises cost), tax base | 0–30% of AI spend |
| Shorter work week | `P.72`, hours | 40 → 32 hours |
| Immigration | new-entrant flow by education | scale 0.5–2.0 |
| Reinstatement strength (literature disagreement) | `P.61` | 0.1–0.8 |
| Demand elasticity (Bessen mechanism) | `P.60` | 0.3–1.5 |
| Capability feedback from revenue | `L.capability_feedback` | off / on |

### 8.3 Shocks
Each shock is an event with a quarter and a magnitude; all magnitudes have defaults and ranges.

| Shock | Mechanism |
|---|---|
| Frontier breakthrough | `C_t += ΔC` (default 2 doublings) at quarter `t`, then trend resumes |
| Lab exit | actor `a` removed; frontier recomputed from remaining actors; if `a` was the sole frontier holder, `C` flat for `λ` of the next best |
| Open-weights price collapse | actor `a` sets `ω = open-frontier` at `t`; §3.3 compression applies in regions where legal |
| Supply-chain cut (Taiwan / ASML) | `floor_t` × (1 + severity) for `duration` quarters; `CAPEX` × (1 − severity); `τ` lengthened for the duration |
| Recession | `Y^0` path shifted down by `depth` for `duration` quarters; separations up; adoption `p` down (capex cut) or up (labor-cost pressure) — sign is a lever because the literature disagrees |

### 8.4 Presets (report replication)
Named scenarios whose parameters are set to reproduce a published headline, so a viewer can see what separates them:

- **Acemoglu 2024**: only E1-type tasks feasible within 10 years, cost-saving share 27%, `ρ_new` low, no demand feedback → TFP no more than +0.66%/10y and GDP "closer to 1%", which are his upper bounds.
- **Goldman Sachs 2023**: full exposure feasible, `ρ_new` historical, `η` ≥ 1 → GDP ≈ +7%/10y.
- **IMF 2024**: exposure with complementarity split; advanced vs emerging regions differ in `A` ceilings.
- **Consensus central**: the v0.1 defaults.

Presets are a documentation device, not a claim that those authors' models are nested in ours.

---

## 9. Explainability: "what changed, why, how confident"

Every scenario run produces, in addition to the series:

1. **Scenario diff**: the canonical JSON diff versus the parent, each entry mapped to the mechanism(s) it touches (from a static lever→equation table).
2. **Channel decomposition** for any output series: sequential switch-off runs (displacement, augmentation, new tasks, demand feedback, AI capex, policy transfers) give an additive attribution in a fixed, documented order. Optional Shapley mode averages over all 2⁶ orderings (64 central runs, still well under 10 s).
3. **Confidence**: from the Monte Carlo band and the tornado (§7.2): {high, medium, low} with the top three parameters driving the spread.
4. **Trace**: for a headline like "retail employment fell faster than manufacturing", the explain endpoint returns the intermediate quantities in the chain (`S_o`, `A_s`, `D`, `η_s`, `μ`) for both sectors, which is what the chat narrates.

The chat layer never computes; it calls `run`, `compare`, `explain`, and `sensitivity`, and phrases their outputs. Anything outside those tools is answered with "outside the model's scope".

---

## 10. Parameter registry (v0.1)

Tag legend: `S` sourced, `D` derived from sourced data, `E` estimated by us. Ranges become triangular distributions unless noted. Sources were fact-checked on 2026-09-01; see the data inventory for verification status.

### Capability and cost

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.01 | Task-horizon doubling time `τ₀` | 5 | 3–12 | months | S | METR Kwa et al. 2025: ~7 mo 2019–25, ~4 mo 2024–25; Time Horizon 1.1 (Jan 2026): 6.3 mo all-time, 4.3 mo since 2023, ~3 mo since 2024 |
| P.02 | Drift in doubling time `γ` | 0 | −0.2–0.3 | per year | E | 0 = steady exponential |
| P.03 | Capability noise sd | 0.15 | 0.05–0.3 | doublings/q | E | spread of lab releases around trend |
| P.04 | Price decline at fixed capability `ρ` | 10 | 3–50 | ×/year | S | Epoch AI (Mar 2025): 9×–900×/yr across capability milestones, 40×/yr for GPT-4-level science QA; a16z "LLMflation" ~10×/yr; central is deliberately below Epoch's median |
| P.05 | Open-frontier lag threshold | 2 | 1–4 | quarters | D | DeepSeek-R1 / Llama-3 episodes |
| P.06 | Open-weights price multiplier | 0.25 | 0.1–0.5 | ratio | D | same episodes |
| P.07 | Cost-floor decline | 2 | 1.3–3 | ×/year | E | hardware price-performance (Epoch) |
| P.08 | Tokens per task-unit `n_k` | by family | ±50% | tokens | E | AEI conversation lengths |
| P.09 | Integration cost `I_s` | 15 | 5–40 | % annual wage | E | no public source; sector-scaled |
| P.10 | Amortization horizon `H` | 12 | 8–20 | quarters | E | |
| P.11 | `θ_base(E1)` | 3 | 2–5 | doublings | E | E1 tasks feasible at ~10 min–2 h horizon |
| P.12 | `θ_base(E2)` | 6 | 4–8 | doublings | E | needs tooling/agents |
| P.13 | `θ_base(E0)` | 12 | 9–16 | doublings | E | effectively beyond 2040 at central `τ` |
| P.14 | Modality shift, interpersonal | +2 | 1–4 | doublings | E | |
| P.15 | Threshold softness `s` | 1.0 | 0.5–2 | doublings | E | |
| P.16 | Substitution share `σ` (initial) | 0.45 | 0.25–0.7 | share | S | Anthropic Economic Index automation share: 43% (Feb 2025), 49% (Sep 2025), 45% (Jan 2026); by task family |
| P.17 | `σ` drift per doubling | +0.01 | −0.02–0.06 | share | D | AEI share rose then fell back across 2025–26 releases: not monotone, so the range includes zero |
| P.18 | Reliability shift for high-consequence tasks | 1 | 0.5–2 | doublings | D | METR 80%-vs-50% horizon ratio |
| P.19 | Robotics doubling time `τ_phys` | 24 | 12–48 | months | E | no public horizon series for manipulation |

### Regulation and regional access

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.30 | Availability delay `δ^reg` | EU 1; CN 4 | EU 0–4; CN 2–8 | quarters | S/E | EU: observed launch delays; CN: frontier gap of domestic actors from Epoch benchmark data |
| P.31 | Compliance premium `χ` | EU high-risk 10; US 0; CN 5 | 2–30; 0–5; 1–15 | % of `κ` | E | no public cost estimate; lever |
| P.32 | Regulatory friction `φ^reg` | EU high-risk 0.7 | 0.4–1.0 | multiplier | E | |
| P.33 | Employment-protection multiplier on layoffs | EU 0.5 | 0.3–0.8 | multiplier | D | OECD EPL index ratio EU/US |

### Adoption

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.40 | Augmentation productivity gain `ψ` | 0.25 | 0.10–0.50 | share | S | Brynjolfsson–Li–Raymond 14% (NBER 2023) / 15% (QJE 2025), 34% for novices; Noy–Zhang time −40%, quality +18%; Peng et al. 55.8% faster; Dell'Acqua et al. 12.2% more tasks, 25.1% faster |
| P.41 | Bass innovation `p` | 0.03 | 0.01–0.06 | per year | S→fit | Sultan et al. 1990 prior; fitted to BTOS |
| P.42 | Bass imitation `q` | 0.38 | 0.2–0.6 | per year | S→fit | same |
| P.43 | Cross-region spillover `q^×` | 0.1 | 0–0.3 | per year | E | |
| P.44 | Spillover lag `L` | 4 | 2–8 | quarters | E | |
| P.45 | Spillover weights `ω_rr'` | TiVA-based | — | — | D | trade + language + MNC presence |
| P.46 | Adoption hurdle `B*` | fitted | — | $/worker-q | E | |
| P.47 | Hurdle softness `b` | fitted | — | $/worker-q | E | |
| P.48 | Sector friction `φ_s` | from BTOS | ×0.5–2 | multiplier | D | BTOS sector adoption ÷ sector exposure |
| P.49 | Size friction `φ_f` | small 0.6, mid 0.8, large 1.0 | ±0.2 | multiplier | D→fit | BTOS: 32% employment-weighted vs 18% firm-weighted adoption (Nov 2025–Jan 2026) confirms a steep size gradient; multipliers fitted |
| P.50 | Intensity ceiling `ι^max` | 0.7 | 0.4–0.9 | share | E | liability/preference residual |
| P.51 | Intensity ramp speed | 0.08 | 0.04–0.15 | per quarter | E | |

### Labor

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.60 | Output demand elasticity `η_s` | tradables 1.0; local services 0.6 | 0.5–1.5; 0.3–1.0 | elasticity | S | Bessen (2019) sector estimates |
| P.61 | Reinstatement ratio `ρ_new` | 0.4 | 0.1–0.8 | share of displacement | E | Acemoglu–Restrepo 2019; Autor et al. 2024 (63% of 2018 employment in job titles that did not exist in 1940); **disagreement lever** |
| P.62 | New-task lag | 8 | 4–16 | quarters | E | |
| P.63 | Natural separations `ς` | 10 | 8–12 | %/quarter | S | JOLTS total separations 3.3%/mo (2025 average, unchanged from 2024; monthly range 3.1–3.4%), quits 2.0%; retirements by age from CPS |
| P.64 | Layoff friction | 0.25 | 0.1–0.5 | share of gap/q | E | |
| P.65 | Seniority protection | 0.5 | 0–1 | index | E | |
| P.66 | Skill-distance decay | fitted | — | — | D | O*NET skill vectors |
| P.67 | Occupation transition matrix | — | — | — | D | CPS matched monthly files (IPUMS) |
| P.68 | Retraining entry base rate | by cohort | ±50% | per quarter | D | CPS/ACS enrolment of displaced |
| P.69 | Scarring wage loss `ℓ` | 0.12 | 0.05–0.25 | share | S | Jacobson–LaLonde–Sullivan 1993; Davis–von Wachter 2011 |
| P.70 | Retraining success | 0.55 | 0.35–0.75 | probability | E | WIOA outcome reports |
| P.71 | Retraining duration | 4 | 2–8 | quarters | D | |
| P.72 | Hours-conversion under shorter week | 0.8 | 0.5–1 | share | E | |
| P.73 | Wage response to excess supply `ε_w` | 0.3 | 0.15–0.6 | per quarter | S | Lichter–Peichl–Siegloch 2015: 942 estimates, mean −0.51, median −0.39 own-wage elasticity; `ε_w` is a quarterly partial-adjustment rate toward that long-run elasticity, not the elasticity itself |
| P.74 | Productivity pass-through to wages `β` | 0.3 | 0.1–0.6 | share | E | RCTs measure productivity, not incidence; lever |

### Macro

| ID | Parameter | Central | Range | Unit | Tag | Source / note |
|---|---|---|---|---|---|---|
| P.80 | U.S. AI capex 2025 | 400 | 380–415 | $bn | S | Big-4 hyperscaler capex 2025 ≈ $384–413bn depending on Microsoft's fiscal vs calendar basis (Alphabet 91.4, Amazon 131.8, Meta 72.2, Microsoft ≈88–118); 2024 ≈ $250bn calendar |
| P.81 | Capex growth 2026 | 80 | 60–100 | % | S | July 2026 guidance sums to ≈ $720–760bn (Microsoft ≈175, Alphabet 195–205, Amazon ≈220, Meta 130–145) |
| P.82 | Capex growth after 2026, and plateau year | +10%/yr to 2029, then flat | −10–+30%/yr; plateau 2027–2033 | %/yr, year | E | no guidance beyond 2026; the bust case is the supply-chain and recession shocks |
| P.83 | Domestic value-added share of capex | 0.5 | 0.3–0.7 | share | E | accelerators imported; construction domestic |
| P.84 | Productivity J-curve lag | 4 | 0–8 | quarters | S | Brynjolfsson–Rock–Syverson 2021 |
| P.85 | AI revenue share by actor region | US 0.85 / CN 0.10 / EU 0.05 | ±0.1 | share | E | public revenue estimates |
| P.86 | MPC by income decile | 0.9 → 0.4 | ±0.1 | share | S | Fagereng et al.; CBO |
| P.87 | Demand multiplier `m` | 0.6 | 0.3–1.2 | multiplier | S/E | fiscal-multiplier literature; mapping is ours |
| P.88 | Import shares | TiVA | — | share | S | OECD TiVA |
| P.89 | Within-decile earnings spread | CPS | — | — | D | |

Counts: 61 parameters listed; 19 `S`, 15 `D`, 27 `E`. The `E` count is high and is stated up front rather than hidden: the labor-flow and integration-cost parameters have no public estimates, which is exactly why they are levers with bands.

---

## 11. Outputs (what every view reads)

All outputs are arrays indexed by `[draw-percentile, region, t, ...]` and stored per scenario hash.

| Output | Dimensions | Feeds view |
|---|---|---|
| Employment `N`, vs baseline `N⁰` | o, s, r, g, c, t | map, heatmap, cohort, Sankey |
| Displacement pressure `D`, exposure `S+G` | o, r, t | heatmap ("exposed but not yet hit" = high `S+G`, low realized `D`) |
| Flows between labor-market states | j→j', r, c, t | Sankey |
| Wages `w`, wage share, Gini, 90/10 | o, r, c, t | cohort, dashboard, map |
| Output `Y`, TFP, productivity, profits, AI rents by region | r, t | dashboard, compare |
| Tax base, transfers, fiscal balance | r, t | dashboard |
| Adoption `A`, intensity `ι` | s, f, r, t | timeline, explain |
| Capability `C_t`, `C_{r,t}`, prices, actor releases, regulatory events | a, r, t | supply timeline |
| Channel decomposition, tornado, confidence | per series | explain, insight, compare |

---

## 12. Known limitations (v0.1)

1. **No market clearing.** Wages respond to excess supply through a rule, not an equilibrium; prices of goods do not adjust. Large displacement scenarios will overstate unemployment persistence relative to a general-equilibrium model and understate real-wage effects through prices.
2. **Capability threshold `θ_k` is estimated.** It is the hinge of the whole model and no dataset provides it. The Monte Carlo range is wide on purpose; the calibration view shows how the 2023–2026 usage data constrain it (weakly).
3. **Cohort tracking at occupation level, not occupation × sector.** Consistent in totals but cannot answer "older retail cashiers in Ohio" beyond the occupation × state × cohort cut.
4. **O*NET is U.S.-centric.** Task mixes for the same ISCO occupation differ across countries; v0.1 assumes they do not. Crosswalk quality is scored and shown per cluster.
5. **China occupational data is thin.** NBS does not publish occupation × industry employment at usable detail; China's labor layer uses ILO modelled estimates by ISCO 1-digit spread with the Korean task structure as a proxy, flagged everywhere it appears.
6. **Informal sector** (large in India, Rest of Asia) is outside the model.
7. **No financial sector, no debt dynamics, no monetary policy.** A recession is an exogenous path shift.
8. **Actors' internal economics are not modelled** (compute stock, training cost, revenue) except through the optional capability-feedback lever.
9. **Robotics** is a single slow index; physical-task displacement before 2032 is small by assumption.
10. **Migration between sub-regions** (U.S. states, EU members) is not modelled; state effects are composition effects.
11. **Public-sector employment** is treated like private with lower adoption friction scale; procurement rules are not modelled.
12. **Task substitution assumes tasks are separable.** Bundling effects (an occupation whose remaining tasks cannot be recombined into a job) are captured only through the intensity ceiling `ι^max`.

---

## 13. Questions for the reviewer

1. **Capability units in the UI.** Show the index in METR horizon units ("AI can do 8-hour tasks") or as an abstract 0–10 level? Recommendation: horizon units, because they explain themselves to a non-technical viewer.
2. **Reinstatement default.** `ρ_new = 0.4` sits between Acemoglu and the historical record. If you want the default to lean one way, say which; it moves 2040 employment by several percentage points.
3. **Recession shock sign on adoption.** Literature disagrees (capex cuts vs labor-cost pressure). Proposed: lever with default "neutral".
4. **U.S. state resolution in Phase 1?** Cheap to add early (OEWS state data is in the same file). Recommendation: include in Phase 1 since the map is the first thing a viewer sees.
5. **Presets as first-class scenarios** in the compare view, or hidden under "advanced"? Recommendation: first-class; "why does Goldman say 7% and Acemoglu 0.7%" is the single most useful demo.

---

## 14. Phase mapping

| Phase | Spec sections implemented | Regions | Draws |
|---|---|---|---|
| 1 | §2, §3.2–3.3 (US only), §4, §5.2–5.5, §6.1–6.2, §7.4 | US national (+ states if Q4 = yes) | central only |
| 2 | §7.1–7.3, §8, §9 | US | 200 |
| 3 | §3.1, §3.3 regional, §3.5, §4 spillover, §5.6, §6.3–6.5 trade | all | 200 |
| 4 | chat over §9 endpoints | all | 200 |
| 5 | methodology write-up = this document, revised | all | 200 |

---

## References (parameter sources)

- Acemoglu, D. (2024). *The Simple Macroeconomics of AI.* NBER WP 32487.
- Acemoglu, D., Restrepo, P. (2019). Automation and New Tasks. *JEP* 33(2).
- Anthropic (2025–26). *Anthropic Economic Index* reports (Feb 2025, Mar 2025, Sep 2025, Jan 2026, Mar 2026, Jun 2026) and the Hugging Face dataset (CC BY).
- Autor, D., Chin, C., Salomons, A., Seegmiller, B. (2024). New Frontiers: The Origins and Content of New Work, 1940–2018. *QJE*.
- Bessen, J. (2019). Automation and Jobs: When Technology Boosts Employment. *Economic Policy*.
- Brynjolfsson, E., Chandar, B., Chen, R. (2025; revised Aug 2026). Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of AI. Stanford Digital Economy Lab.
- Brynjolfsson, E., Li, D., Raymond, L. (2023/2025). Generative AI at Work. *QJE*.
- Brynjolfsson, E., Rock, D., Syverson, C. (2021). The Productivity J-Curve. *AEJ: Macro*.
- Cazzaniga, M. et al. (2024). Gen-AI: Artificial Intelligence and the Future of Work. IMF SDN/2024/001.
- Davis, S., von Wachter, T. (2011). Recessions and the Costs of Job Loss. *BPEA*.
- Dell'Acqua, F. et al. (2023). Navigating the Jagged Technological Frontier. HBS WP 24-013.
- Eloundou, T., Manning, S., Mishkin, P., Rock, D. (2023). GPTs are GPTs. *Science* (2024).
- Epoch AI (2024–26). Notable AI Models; Epoch Capabilities Index; LLM inference price trends.
- Felten, E., Raj, M., Seamans, R. (2021/2023). Occupational, industry, and geographic exposure to AI. *Strategic Management Journal*.
- Gmyrek, P., Berg, J., Bescond, D. (2023; 2025 update). Generative AI and jobs. ILO WP 96.
- Goldman Sachs (2023). The Potentially Large Effects of AI on Economic Growth.
- Jacobson, L., LaLonde, R., Sullivan, D. (1993). Earnings Losses of Displaced Workers. *AER*.
- Kwa, T. et al. (2025). Measuring AI Ability to Complete Long Tasks. METR. And METR (2026). Time Horizon 1.1.
- Regulation (EU) 2024/1689 (AI Act) as amended by Regulation (EU) 2026/1744 (Digital Omnibus on AI, OJ 24 Jul 2026).
- Lichter, A., Peichl, A., Siegloch, S. (2015). The own-wage elasticity of labor demand: A meta-regression analysis. *European Economic Review*.
- Noy, S., Zhang, W. (2023). Experimental evidence on the productivity effects of generative AI. *Science*.
- Peng, S. et al. (2023). The Impact of AI on Developer Productivity: Evidence from GitHub Copilot.
- Sultan, F., Farley, J., Lehmann, D. (1990). A Meta-Analysis of Applications of Diffusion Models. *JMR*.
- U.S. Census Bureau. Business Trends and Outlook Survey, AI supplement (2023–).
- U.S. BLS. OEWS, CPS, JOLTS, Employment Projections 2024–34.

# Model specification v0.3 amendment: the application layer

*Status: draft for adversarial review. Amends `docs/model-spec.md` v0.2; section numbers below refer to that document unless prefixed A. Nothing here is implemented. Every number marked `V?` is a provisional value written from the authors' recollection of public sources and must be verified by the data plan in §A.10 before it enters the registry; the ranges around such values are deliberately wide.*

---

## A.0 What v0.2 misses and why

v0.2 has one displacement mechanism: **task substitution inside an employer**. A software system becomes able to do an O*NET task, the task is cheaper than the worker's hours, the firm hands it over on an adoption curve. This is what the exposure literature measures, and it is why the shipped results concentrate on clerical, programming, and analytical work.

Three families of AI application work through other mechanisms, and v0.2 handles each badly for a specific reason:

| Family | Example | Mechanism | Why v0.2 misses it |
|---|---|---|---|
| **Embodied autonomy and automation** | robotaxis and autonomous trucks; warehouse, factory, kitchen, farm, and construction robots; humanoids | a machine with hardware unit economics, a production ramp, and jurisdictional approval replaces physical task-hours | one slow robotics clock and a presence penalty; no hardware cost, no ramp, no approval; rideshare drivers are self-employed and absent from OEWS |
| **Output substitution** | AI-produced video, music, books, images, voice, advertising creative, translation | a competing *product* takes market share; the human-produced sector shrinks even where its workers' tasks are unchanged | no product-market layer; most affected workers are freelance and absent from OEWS |
| **Traded services substitution** | AI agents replacing outsourced customer service, back-office, and IT services | automation in the *importing* region removes the *exporting* region's jobs | tasks are automated where the firm is, but the workers are in India and the Philippines; trade matrix is inert |

Everything else in v0.2 (flows, cohorts, wages, prices, rents, uncertainty, explanation) consumes displacement and augmentation by occupation, region, and quarter and does not care which mechanism produced them. v0.3 therefore adds a layer that **produces** displacement through three new channels and leaves the downstream layers unchanged except where §A.6 says otherwise.

"All implications" is a direction, not a state. v0.3 makes coverage explicit through a **catalogue of applications** (§A.8): what is in, what is out, and why. That is a stronger claim than completeness and the only one a reviewer can check.

---

## A.1 Design principles, and the adversarial pre-review

The amendment was written against the attacks a simulation reviewer would make. Each attack, the defence built into the design, and what remains exposed:

| # | Attack | Defence in v0.3 | Residual exposure |
|---|---|---|---|
| 1 | **Double counting between channels.** A truck driver's driving tasks are E0-physical in the task engine *and* the target of an autonomous-trucking application. | **One task group, one channel.** Every task group carries a channel assignment `χ_k ∈ {software, embodied(c), none}` (§A.2). Embodied channels reuse the feasibility and profitability machinery with their own clock and cost; the software engine never sees an embodied task. Output substitution acts on a different margin (quantity of human-produced output, §A.4) and combines multiplicatively with per-unit labor. CI test: `Σ_channels D ≤ 1` per occupation, and channel sets are disjoint by construction. | The assignment itself is a classifier (tagged `E`, reviewed like the exposure classifier). Misassignment moves a task between clocks; it cannot count it twice. |
| 2 | **Double counting with the baseline.** BLS Employment Projections already embed expected automation; industrial robots were displacing workers before 2023. | The frozen-AI baseline carries the **pre-2023 automation trend**: robot installations continue at their 2015–2023 growth on structured tasks, and EP occupation trends are unchanged. The embodied channel acts only on the **AI-enabled increment**: unstructured, variable, or mobile tasks that the baseline trend does not reach (`χ_k = embodied` is assigned only to those), and the baseline robot stock path `R^0_{c,r,t}` is subtracted from the modelled stock (§A.3.4). The EP adjustment lever (§7.6) is generalised to a per-channel baseline adjustment. | The split of the historical trend between "would have happened anyway" and "AI-enabled" is a judgement; it is a lever with a range that includes zero. |
| 3 | **Half the affected workforce is not in the data.** OEWS counts payroll employees. Rideshare drivers, freelance writers, musicians, translators, and many delivery workers are self-employed. | New stock `N^{self}_{o,r}` (heads and FTE) from CPS class-of-worker and Census Nonemployer Statistics, mapped to occupations (§A.5). Platform and output substitution act on it; the employee stock in the same occupation goes through the task engine. The headline "employment" becomes **FTE jobs including self-employment**, with the payroll-only series still reported and the change flagged in every document. | Multiple-job holding is imperfectly measured; FTE conversion uses CPS hours, tagged `D`. |
| 4 | **Hardware economics are not tokens.** A robotaxi competes on cost per mile with a vehicle, a driver's wage, insurance, and utilization; a warehouse robot on cost per pick with capex, lifetime, and integration. | Each embodied class has a **unit-cost model** (§A.3.2): annualized capex on a Wright's-law learning curve driven by cumulative production, operating cost, utilization, lifetime, integration cost scaled by firm size, entering the same log-ratio profitability test as tokens. Learning rate is a structural ensemble axis (§A.7). | Learning rates for autonomy stacks and humanoids are extrapolations from other hardware; the ranges span solar-like and automotive-like histories. |
| 5 | **Pace is set by ramps and permits, not by capability.** Waymo could not scale to a million vehicles in a year regardless of the software. | Fleet **stock-flow with a production ramp** (maximum growth rate per year, sourced from EV and robot production histories) and **jurisdictional approval shares** `J_{c,r,t}` per region (§A.3.3, §A.3.4). Capability and cost gate the *ceiling*; production and approval gate the *speed*. Approval changes are dated shocks. | Approval timetables outside the U.S. are levers with qualitative states; there is no dataset of future permits. |
| 6 | **Demand does not stand still.** Cheaper rides mean more rides; cheaper content means more content. Ignoring this overstates displacement. | Every application carries the **own-price elasticity of its end product** and enters the sector's demand equation (§5.2) through unit cost, so induced demand is automatic; applications also carry an **adjacent-employment coefficient** (remote assistance and fleet operations per vehicle, curation per unit of content) that adds jobs in named occupations (§A.3.5). | Second-order effects (fewer cars owned, less parking, insurance restructuring) are out of scope and listed as such. |
| 7 | **Product substitution needs a preference model, not a cost test.** People may keep paying for human-made films and music. | Output substitution is a **logit share in relative price and quality** with an explicit **authenticity premium** `α_s` that is a structural ensemble axis {persistent, eroding} (§A.4). The share is calibrated where any series exists (AI-generated share of new releases on streaming platforms, stock-image and translation revenue) and prior-driven where none does, and the results say which. | The authenticity premium is unmeasured beyond a handful of surveys; it is the largest new estimate and ranked first in the updated risk register. |
| 8 | **Free goods break GDP.** If AI films are nearly free, measured output falls while quantity rises. | v0.2 already values output at **baseline prices** (§6.1): real output counts AI-produced units at the baseline price of the category, and the nominal effect is reported separately. A **consumer-surplus proxy** (Harberger triangle by category) is added as an output and labelled as not welfare (§A.6.3). | Quality adjustment of AI-produced goods is not attempted; the proxy is a lower bound under substitution and an upper bound under quality loss, and the document says so. |
| 9 | **Where do the revenues go?** Output substitution creates revenue for platforms and model providers, not for the sector's workers. | AI-produced revenue enters the value-chain rents (§6.3) at the model and integration stages, allocated by the same market-share and location rules; sector wage bills fall with human-produced output. Conservation test: category spending = human-produced revenue + AI-produced revenue + consumer saving. | Platform margins for AI content are `E` until public accounts exist. |
| 10 | **Traded services need an exporter-side mechanism.** Automating a call in Ohio removes a job in Manila. | The **importing region's** displacement for an exported task set is applied to the **exporting region's export-serving employment** `N^{exp}_{o,r}` (services exports by category × occupation composition), using the existing trade matrix direction reversed (§A.5.3). | Services trade data by occupation is coarse (BPM6 categories); the mapping is `D` with a quality score. |
| 11 | **Parameter explosion makes the bands meaningless.** Twenty applications with six parameters each is 120 new estimates. | Applications share **class-level** parameters (one learning rate per embodiment class, one ramp cap per class, one authenticity premium per media category), so the new registry block is 36 parameters (§A.9). The copula gains two blocks (hardware economics; product preferences). The tornado stays curated (top 25). Two new ensemble axes bring the cells to 16; default draws rise to 256 so each cell keeps 16 draws; runtime budget ≤ 60 s for ten regions. | Fewer draws per cell than v0.2's 25; the confidence classification's thresholds are unchanged, so it will call more effects "low", which is the correct response to more structural uncertainty. |
| 12 | **Nothing here is identified.** | §A.10 states what is **fitted** (autonomous fleet ramp against public paid-ride and fleet counts; robot installations against IFR aggregates; BPO revenue trend against industry statistics), what is **anchored**, and what is **prior-driven**. Prior-driven applications are reported with a dashed central line and the `E` count in the explain trace. | Most of the embodied and media parameters are prior-driven through 2026; the amendment does not pretend otherwise. |
| 13 | **Regional realism.** A robot that is cheaper than a $30/hour worker is not cheaper than a $3/hour worker. | The profitability test already runs at regional wage tiers (§2.4, §16); hardware unit cost is global while wages are local, so low-wage regions automate embodied tasks later. Traded-services substitution (attack 10) is the channel through which low-wage regions are hit first, which is the right ordering. | Regional occupation structure is still a fixture until the ILOSTAT ingest runs. |
| 14 | **Cohort incidence changes.** Drivers and warehouse workers are older, less educated, and more male than clerical workers; freelance creatives are younger and more educated. | Cohort attribution uses the affected occupation's own cohort matrix (§1.4), and the self-employed stock gets its own cohort matrix from CPS (§A.5.1). Embodied displacement runs through layoffs more than hiring where fleet operators are new firms (§A.3.6), so the cohort result will differ from the software channel's, and the flows view shows it by channel. | The gig cohort matrix is national; regional gig composition is imputed. |

---

## A.2 Channel assignment of task groups

Every task group `k` (v0.2 §16: ~9,400 groups) receives one channel:

$$\chi_k \in \{\text{software},\ \text{embodied}(c),\ \text{none}\},\qquad c \in \mathcal{C} = \{\text{driving},\ \text{mobile manipulation},\ \text{fixed automation},\ \text{aerial}\}$$

Assignment rule, in order:

1. `m_k = physical` and the task's O*NET Generalized Work Activity is in the driving family (Operating Vehicles, Mechanized Devices, or Equipment; with vehicle keywords) → `embodied(driving)`.
2. `m_k = physical` and the activity is handling, moving, assembling, inspecting, preparing, cleaning, or harvesting in a variable environment (Work Context "Spend Time Handling and Moving Objects" high, "Structured versus Unstructured Work" high) → `embodied(mobile manipulation)`.
3. `m_k = physical` and the same activities in a structured environment → `embodied(fixed automation)`; this is the class the **baseline trend** already reaches, so its AI-enabled increment is the unstructured residual set by `P.104`.
4. `m_k = physical` and delivery or inspection over distance → `embodied(aerial)`.
5. `m_k = physical` otherwise (care, surgery, crafts requiring dexterity beyond the horizon) → `none` within the horizon, with `a_k = a_{\text{phys,none}}` (`P.105`, central 0, range 0–0.1).
6. Non-physical `k` → `software` (unchanged from v0.2).

The classifier is deterministic, keyword-and-rating based, tagged `E`, versioned, and reviewed on a stratified sample like the exposure classifier (v0.2 §16). Its output is a column in `tasks.csv` and is exposed in the Occupations view.

The single robotics clock `C^{phys}` (`P.19`) and `a_phys` (`P.59`) are **retired**; `P.19` is kept as an alias of the mobile-manipulation clock for scenario compatibility.

---

## A.3 Embodied channels

### A.3.1 Embodiment clocks

One capability clock per class, in the same units as the software clock (doublings of a task-horizon-like index) so that `θ_k` remains comparable:

$$C^{emb}_{c,t} = C^{emb}_{c,0} + \frac{\Delta t}{\tau_c}\quad\text{(saturating at } C^{sat}_c\text{)}$$

Anchors: driving to the paid autonomous-ride series and disengagement statistics; mobile manipulation to published manipulation benchmarks and deployed-fleet task breadth; fixed automation to the IFR trend (its increment is small by construction); aerial to approved beyond-visual-line-of-sight operations. Each clock has a coupling `g^{emb}_c` to the software clock (`P.107`): progress in foundation models transfers to embodiment at a fraction, with a range that includes zero. This is the honest replacement for v0.2's "robotics is a single slow clock".

Feasibility for `χ_k = embodied(c)`:

$$F_{k,r,t} = a_k\,\Lambda\!\left(\frac{C^{emb}_{c,t} - \theta_k}{s_k}\right),\qquad a_k = a_{\text{emb}}(c)\,(1-\pi_k)^{\lambda^{emb}_\pi}$$

with `a_emb(c)` per class (`P.100–P.103`, `E`, wide) and a presence exponent that is *weaker* than for software (`P.106`): a robot can be present.

### A.3.2 Hardware unit cost

Cost per task-unit for class `c` in region `r`:

$$\kappa^{emb}_{k,c,r,t} = \frac{\text{AC}_{c,t}\,(1+o_c) + \text{int}_{c,f,r}}{u_{c}\;\text{TU}_{c}}$$

- `AC_{c,t}` annualized capital cost: unit price `p_{c,t}` amortized over lifetime `L_c` at a real rate `i` (`P.110–P.112`).
- Unit price follows **Wright's law** in cumulative production: `p_{c,t} = p_{c,0}\,(Q^{cum}_{c,t}/Q^{cum}_{c,0})^{-b_c}` with learning exponent `b_c` from learning rate `LR_c = 1 − 2^{-b_c}` (`P.113`, structural axis: automotive-like 8% vs electronics-like 20%, `V?`).
- `o_c` operating cost ratio (energy, maintenance, insurance, remote supervision) (`P.114`).
- `int_{c,f,r}` integration cost per unit, scaled by firm size and local integration wages (reuses `P.09` logic).
- `u_c` utilization (hours per year in productive use) and `TU_c` task-units per productive hour relative to a worker (`P.115–P.116`; a robotaxi's utilization is the argument for its economics and a lever).

The profitability test is unchanged in form: `Π_k = F_k Λ((ln ℓ_{o,k} − ln κ^{emb}_k)/b_κ)`. Because `κ^{emb}` is global and `ℓ` is local, the regional ordering falls out of the existing wage tiers.

### A.3.3 Production ramp

Cumulative production and the deployable stock are constrained:

$$\Delta Q^{prod}_{c,t} \le Q^{prod}_{c,t-1}\,(1+g^{max}_c)^{1/4},\qquad Q^{prod}_{c,0} \text{ from 2025 fleet counts}$$

`g^{max}_c` maximum annual production growth (`P.117`, `V?`: EV production grew about 50%/yr over 2015–2023 from a small base and industrial-robot installations about 10%/yr; central 0.5 with a 0.3–1.5 range). Desired production is the profitable-feasible demand from all regions; supply is the constrained path; the shortfall delays deployment rather than raising price (a queue, as with compute capacity in §3.4). Hardware production is booked to the producing region's AI-production sector (§5.7) with a regional production-share table (`P.118`, `D` from vehicle and robot manufacturing locations).

### A.3.4 Deployment stock and approval

Per class, region, and use: stock `R_{c,r,t}` evolves with deliveries, retirements at `1/L_c`, and an approval share

$$R^{dep}_{c,r,t} = R_{c,r,t}\;J_{c,r,t},\qquad J_{c,r,t} \in [0,1]$$

`J` is the share of the class's addressable task-hours in jurisdictions where operation is permitted (driving and aerial: by state, member state, or city; manipulation: near 1, safety certification only). `J` follows a dated baseline path per region with lever states {frozen, baseline, accelerated, moratorium} (`P.119`; the baseline path is a verification item, §A.10). Approval changes are shocks of type `approval_change` (§A.9).

Realized displacement for `χ_k = embodied(c)`:

$$D_{o,s,r,t} = \sum_{k:\chi_k=c} w_{o,k}\,\Pi_{k,o,s,r,t}\;\min\!\Big(1,\ \frac{R^{dep}_{c,r,t}\,\text{TU}_c\,u_c}{\text{task-hours addressable}_{c,r,t}}\Big)$$

The last factor is the **deployment coverage**: displacement cannot exceed what the deployed stock can do. The baseline robot stock `R^0_{c,r,t}` (fixed-automation trend) is netted out so only the increment displaces relative to the baseline.

### A.3.5 Demand and adjacent employment

Embodied cost savings enter the sector unit-cost equation (§5.2) exactly as software savings do, so induced demand follows from `η_s` and `π_p` with no new machinery. Applications add **adjacent employment** in named occupations:

$$\Delta N^{adj}_{o',r,t} = \sum_c \beta_{c,o'}\,R^{dep}_{c,r,t}$$

with `β_{c,o'}` jobs per deployed unit (remote assistance, fleet maintenance, depot operations, safety oversight; `P.120`, `E`, and the only publicly discussed figures are for autonomous ride-hail, `V?`). Adjacent jobs are counted in the AI-production sector's regional employment and in the flows view as a destination.

### A.3.6 Which margin: hiring or layoffs

v0.2's attrition-first rule applies within an employer. Embodied substitution by **new entrants** (an autonomous fleet operator taking ride-hail share) does not run through the incumbent's attrition; it removes demand for the incumbent's service. For `χ_k = embodied(driving)` in platform work, and for output substitution (§A.4), the displacement acts on the **self-employed stock** as a reduction in demanded FTE with no attrition buffer: hours fall first, exits follow at a rate tied to the earnings loss (`P.121`, `E`). For embodied substitution inside an employer (warehouses, factories, kitchens) the v0.2 rule holds, with the layoff share raised where the deployment is a site conversion (`P.122`).

---

## A.4 Output substitution (product markets)

Applies to a set of **content and creative categories** `s ∈ \mathcal{S}^{out}` = {motion picture and video, sound recording and music publishing, book and periodical publishing, advertising creative, graphic and industrial design, photography, translation and interpretation, software as a product (games) partially}. Each category has total real consumption `Q_{s,r,t}`, a human-produced share, and an AI-produced share:

$$s^{AI}_{s,r,t} = \frac{\exp(v^{AI}_{s,r,t})}{\exp(v^{AI}_{s,r,t}) + \exp(v^{H}_{s,r,t})},\qquad v^{AI} - v^{H} = -\gamma_s\,(\ln p^{AI}_{s,t} - \ln p^{H}_{s,t}) + q_{s,t} - \alpha_{s,t}$$

- `γ_s` price sensitivity of the category (`P.125`, `S` from Armington-type elasticities for differentiated goods, `V?`).
- `q_{s,t}` quality gap of AI output relative to human output, a function of the software clock through the category's task feasibility (`q = q_0 + q_1 F̄_s`), so quality rises as the generative tasks of the category become feasible (`P.126`).
- `α_{s,t}` **authenticity premium**: the willingness to pay for human provenance. Structural ensemble axis: **persistent** (`α` constant at its 2025 level) versus **eroding** (`α` decays with a half-life `P.127`). Its 2025 level per category is anchored where survey or market data exist and `E` elsewhere.
- `p^{AI}` follows the token price path (§3.3) plus a platform margin (`P.128`); `p^{H}` is the baseline price adjusted by the task engine's cost saving in the category (human creators use AI tools too, which is the v0.2 channel and is kept).

Total category consumption responds to the average price with the category's own-price elasticity (`η_s` in §5.2), so cheaper content expands the category. **Human-produced output** `Q^H = (1 − s^{AI}) Q`, and the category's labor demand is

$$N^{\ast}_{o,s,r,t} = N^0_{o,s,r,t}\,\frac{Q^H_{s,r,t}}{Q^0_{s,r,t}}\,\frac{1 - D_{o,s,r,t}}{1+\psi U_{o,s,r,t}}\,(1+\nu_{o,r,t})$$

which is §5.2 with `Q` replaced by `Q^H`. The two margins (fewer human-produced units; fewer hours per human-produced unit) multiply and cannot double count. AI-produced revenue `p^{AI} s^{AI} Q` flows to the value-chain rents at the model and integration stages (§6.3). Distribution mapping of categories to occupations uses OEWS occupation × industry for employees and the self-employed table (§A.5) for freelancers; the model does not attempt superstar or long-tail dynamics within an occupation and says so.

**Where the category is an intermediate input** (advertising creative, translation for firms), `s^{AI}` acts on the purchasing sector's costs through §5.2 as well; the category's own employment follows `Q^H`.

---

## A.5 Workforce coverage and traded services

### A.5.1 Self-employed and platform work

New input table `self_employed.csv` (occupation × region): heads, mean weekly hours, FTE, share platform-mediated, and a cohort matrix. Sources: CPS class-of-worker and multiple-job-holding items (IPUMS), Census Nonemployer Statistics by NAICS mapped to occupations, and platform-work supplements where they exist; EU-LFS status in employment for the EU; ILOSTAT for others (`D`, with the fixture rule where unavailable). The stock is reported separately and added to the headline as FTE; every document's `meta.data_flags.self_employed` records the source per region.

### A.5.2 Labor-market states for the self-employed

The seven states of §5.1 apply, with "employed" split into employee and self-employed and a transition between them (`P.123`, `D` from CPS flows). Displaced self-employed workers enter searching with a re-employment hazard drawn from the same age-band table, and their counterfactual earnings are their observed earnings, not an entry wage.

### A.5.3 Traded services

For exporting region `r'`, category `b` of services exports (BPM6: telecommunications, computer, and information services; other business services; call-center and back-office within them where national statistics split them), export-serving employment `N^{exp}_{o,r',b}` is derived from export revenue and category revenue per worker (`D`). The displacement applied to it is the **importers'** weighted task displacement for the category's task set:

$$D^{exp}_{o,r',b,t} = \sum_{r} \omega_{b,r' \to r}\;D_{o,b,r,t}$$

with `ω` the share of `r'`'s category exports going to `r` (the existing `trade_weights` table, reversed direction, extended to services). Demand response is the importer's. This is the channel through which India, the Philippines (in RoA), and Eastern EU members are reached first, and it is the reason the amendment ranks services-trade data above robot data in the plan for Asia.

---

## A.6 Downstream changes

### A.6.1 Channel decomposition (§9)
The explain trace and the Economy view's channel bars gain entries per family: `software tasks`, `embodied: driving`, `embodied: manipulation`, `embodied: fixed`, `embodied: aerial`, `output substitution`, `traded services`, `adjacent employment`. The sequential switch-on order is software → embodied → output → traded → adjacent, and the order is a documented convention as in v0.2.

### A.6.2 Baseline (§7.6)
The frozen-AI counterfactual freezes **all** AI clocks at 2023, including embodiment and generative media, and keeps the pre-2023 automation trend (robot installations, EP occupation trends, historical growth of streaming and stock content). `levers.baseline.automation_trend` scales the trend (0.5–1.5×) so a reviewer can see how much of the result is the increment.

### A.6.3 Outputs (§11)
New series per region: `self_employed_fte`, `fleet_stock` by class, `approval_share` by class, `ai_content_share` by category, `consumer_surplus_proxy_bn` by category (`½ Δp ΔQ` at baseline prices, labelled "not welfare"), and the channel entries above. New results section `applications` with per-application status per quarter: feasible share, profitable share, deployment coverage, realized displacement, adjacent jobs.

### A.6.4 Views
The AI Supply view gains an **Applications** panel: a timeline of each application's gates (feasible, profitable, approved, deployed) per region, with the catalogue entry, its sources, and its `E` count one click away. The Flows view labels the channel of each origin. No new view.

---

## A.7 Uncertainty (§7)

- **Copula blocks** gain `hardware economics` (`LR_c`, `u_c`, `o_c`, `g^{max}_c`; 0.6) and `product preferences` (`α_s`, `γ_s`, `q_1`; 0.6).
- **Structural ensemble** gains two axes: **hardware learning rate** {automotive-like, electronics-like} and **authenticity premium** {persistent, eroding}. Cells: 16 (was 8). Default draws: 256 (was 200), so 16 per cell.
- **Tornado**: curated set grows to 25 parameters, adding `LR_c` (driving, manipulation), `u_driving`, `α_media`, `γ_media`, `g^{max}`, `J` baseline speed.
- **Confidence classification** unchanged; more low-confidence calls are the intended consequence.
- **Runtime budget**: ≤ 60 s for ten regions at 256 draws with tornado and channels on 4 cores. The embodied channel adds four clocks and per-class stock-flows (cheap); output substitution adds eight categories (cheap); the cost is the extra draws.

---

## A.8 Initial application catalogue

Each row is a versioned record in `data/processed/applications.csv` with the fields of §A.9. Timing entries are **provisional ranges for the central draw** (`E`, `V?`) and exist so the reviewer can attack them; they are not results.

| id | Family / class | Targets (task families → occupations, sectors) | Binding constraints | Anchor series (fit or check) | Provisional central: profitable at U.S. wages / deployed at 50% coverage | Regions first |
|---|---|---|---|---|---|---|
| `robotaxi` | embodied: driving | ride-hail and taxi driving → taxi drivers, rideshare (self-employed) | approval by city and state; production ramp; utilization | paid autonomous rides per week and fleet size (public company posts); state permits | 2026–28 / 2031–35 | US metros, CN metros, then UAE and SG (RoA); EU late |
| `autonomous_trucking` | embodied: driving | long-haul freight driving → heavy truck drivers | approval by state and corridor; depot network | driverless corridor launches; permits | 2027–29 / 2033–37 | US Sun Belt corridors, CN |
| `last_mile_delivery` | embodied: driving + aerial | parcel and food delivery → couriers (largely self-employed) | sidewalk and BVLOS approval; density | permitted operations counts | 2027–30 / 2033–38 | US, CN, KR, SG |
| `warehouse_robotics` | embodied: mobile manipulation | picking, packing, moving → laborers and material movers | ramp; integration; site conversion | robot installations (IFR aggregates), retailer disclosures | 2025–27 / 2030–34 | US, CN, JP, KR, EU |
| `manufacturing_flexible` | embodied: mobile manipulation | assembly and inspection in variable settings → assemblers, inspectors | learning rate; integration | IFR installations by application; humanoid pilot counts | 2028–31 / 2034–40 | CN, KR, JP, US, EU |
| `humanoid_general` | embodied: mobile manipulation (late) | broad physical tasks across sectors | unit cost; dexterity; safety certification | unit price disclosures; pilot deployments | 2030–34 / beyond 2040 at central | CN, US |
| `food_service_automation` | embodied: fixed + mobile | cooking, assembly, serving → cooks, food-prep workers | unit cost vs low wages; site conversion | vendor deployments | 2028–32 / 2035–40 | US, JP, KR |
| `agricultural_robotics` | embodied: mobile manipulation | harvesting, weeding → agricultural workers | seasonality; crop specificity | deployment counts by crop | 2027–31 / 2035–40 | US, EU, JP |
| `construction_robotics` | embodied: mobile manipulation | layout, bricklaying, drywall, rebar → construction trades (partial) | site variability; codes | pilot counts | 2030–35 / beyond 2040 | JP, US |
| `retail_checkout_shelf` | embodied: fixed | checkout, shelf scanning → cashiers, stock clerks | shrink and customer acceptance | retailer disclosures | 2025–27 / 2030–34 | US, UK, EU, JP |
| `generative_video` | output: motion picture and video | production → actors, animators, editors, camera operators (mixed employee and freelance) | quality gap; authenticity premium; licensing regime | AI-generated share of new uploads and releases; guild agreements | 2027–30 / 2032–38 | global by platform |
| `generative_music` | output: sound recording | composition, performance, production → musicians, producers | authenticity premium; licensing | AI-generated share of streams and uploads | 2026–28 / 2030–36 | global by platform |
| `generative_text` | output: publishing | writing → writers, editors, journalists | authenticity premium; discoverability | AI-generated share of new titles and articles | 2025–27 / 2029–34 | US, UK, EU |
| `generative_image_design` | output: design, photography, advertising creative | image creation → graphic designers, photographers, illustrators | quality gap | stock-image revenue and AI share | 2024–26 / 2028–32 | global |
| `machine_translation_voice` | output: translation and interpretation; voice | translation, dubbing, narration → translators, voice actors | quality gap in high-stakes domains | translation industry revenue mix | 2024–26 / 2027–31 | global; EU institutional last |
| `ai_customer_service` | software tasks + traded services | customer support, back office → customer service reps in the U.S.; BPO workers in IN and RoA | deflection rates; regulation of automated decisions | BPO revenue growth and headcount; deflection disclosures | 2025–27 / 2029–33 | IN, RoA (Philippines) first via trade; US |
| `ai_tutoring_education` | software tasks | instruction and grading → tutors, teaching assistants (institutional teachers largely protected by presence) | procurement; evidence of efficacy | adoption in districts and platforms | 2026–29 / 2032–38 | US, IN, CN |
| `ai_diagnostics` | software tasks | image reading, triage → radiologic technologists (partial), medical scribes | regulatory clearance; liability | cleared devices counts; deployment | 2026–29 / 2032–38 | US, EU, CN |
| `ai_legal_research` | software tasks | research, drafting → paralegals, associates (partial) | professional rules | firm adoption surveys | 2025–27 / 2029–33 | US, UK |

Software-task rows exist so that the catalogue is the single place where coverage is stated; they add no mechanism beyond v0.2 except the traded-services link for `ai_customer_service`. **Out of scope and why**: care work and surgery (dexterity and liability beyond the horizon at central; `none` channel), military and security applications (no public labor data), scientific R&D acceleration (a TFP effect the model cannot attribute to occupations; noted as an omitted upside), and second-order effects of mobility (car ownership, parking, insurance).

---

## A.9 Registry block, levers, shocks, schema

### Parameters (v0.3 block, P.100–P.135)

| ID | Parameter | Central | Range | Unit | Tag | Note |
|---|---|---|---|---|---|---|
| P.100 | `a_emb(driving)` | 0.85 | 0.5–0.95 | share | E | ever-automatable mass of driving task-hours |
| P.101 | `a_emb(mobile manipulation)` | 0.6 | 0.3–0.85 | share | E | |
| P.102 | `a_emb(fixed automation)` increment | 0.3 | 0.1–0.5 | share | E | over the baseline trend |
| P.103 | `a_emb(aerial)` | 0.5 | 0.2–0.8 | share | E | |
| P.104 | Baseline automation trend scale | 1.0 | 0.5–1.5 | × | E | lever `baseline.automation_trend` |
| P.105 | `a_phys,none` | 0 | 0–0.1 | share | E | |
| P.106 | Presence exponent, embodied `λ^{emb}_π` | 0.5 | 0–1.5 | | E | weaker than software (P.23) |
| P.107 | Coupling to software clock `g^{emb}_c` | 0.3 | 0–0.7 | | E | per class; range includes zero |
| P.108 | Clock anchors `C^{emb}_{c,0}`, doubling `τ_c` | per class | | doublings, months | S/E, V? | driving from paid-ride and disengagement series; others E |
| P.109 | Clock saturation per class | per class | | doublings | E | |
| P.110 | Unit price 2025 `p_{c,0}` | driving V?; manipulation V?; humanoid V? | wide | USD | S, V? | verification items §A.10 |
| P.111 | Lifetime `L_c` | 5 (driving), 8 (manipulation), 10 (fixed) | ±40% | years | S, V? | |
| P.112 | Real rate `i` | 0.06 | 0.03–0.10 | /yr | S | |
| P.113 | Learning rate `LR_c` | 0.12 | 0.05–0.25 | per doubling of cumulative production | S, V? | ensemble axis {0.08, 0.20} |
| P.114 | Operating cost ratio `o_c` | 0.5 | 0.2–1.0 | × annual capital cost | E | |
| P.115 | Utilization `u_c` | driving 0.45 of hours; manipulation 0.6; fixed 0.8 | ±50% | share | E, V? | lever |
| P.116 | Task-units per hour relative to worker `TU_c` | 1.0 | 0.5–2.0 | × | E | |
| P.117 | Max production growth `g^{max}_c` | 0.5 | 0.3–1.5 | /yr | S, V? | EV production ~50%/yr 2015–2023; changed from 0.7 in the draft after the first run (§A.15) |
| P.118 | Production location shares | table | | share | D | vehicle and robot manufacturing |
| P.119 | Approval path `J_{c,r,t}` | table by region | lever states | share | E, V? | baseline path is a verification item |
| P.120 | Adjacent jobs per deployed unit `β_{c,o'}` | driving 0.1; manipulation 0.05 | 0–0.3 | FTE per unit | E, V? | |
| P.121 | Self-employed exit hazard per unit earnings loss | 0.3 | 0.1–0.6 | /yr per 100% loss | E | |
| P.122 | Layoff share for site conversions | 0.6 | 0.3–0.9 | share | E | |
| P.123 | Employee ↔ self-employed transition rates | table | | /q | D | CPS flows |
| P.124 | Export-serving employment per revenue | table by category | | FTE per USD m | D | |
| P.125 | Price sensitivity `γ_s` | 2.0 | 1.0–4.0 | | S, V? | Armington-type |
| P.126 | Quality gap `q_0`, `q_1` | −2.0, 3.0 | wide | logit units | E | |
| P.127 | Authenticity premium `α_s` 2025 level; half-life if eroding | 1.5; 8 | 0.5–3; 4–20 | logit units; years | E, V? | ensemble axis {persistent, eroding} |
| P.128 | AI content platform margin | 0.4 | 0.2–0.7 | share of price | E | |
| P.129 | Category own-price elasticity | per category | | | S, V? | reuses `η_s` where the category is a sector |
| P.130 | Channel switch-on order | fixed | | | — | convention |
| P.131–135 | Reserved for calibration constants of the driving clock, the deflection-rate series, and the services-trade mapping quality score | | | | D | |

### Levers (§8.2 additions)

| Lever | Parameters | Range or states |
|---|---|---|
| Embodiment progress per class | `P.108` | doubling 6–36 months per class |
| Hardware learning rate | `P.113` | 0.05–0.25 |
| Utilization (robotaxi) | `P.115` | 0.2–0.7 |
| Production ramp cap | `P.117` | 0.3–1.5/yr |
| Approval regime per region and class | `P.119` | {frozen, baseline, accelerated, moratorium} |
| Authenticity premium | `P.127` | level 0.5–3; {persistent, eroding} |
| Content licensing regime | `P.128`, `q_1` | {permissive, licensed, restrictive}: restrictive raises AI content price and lowers quality growth |
| Baseline automation trend | `P.104` | 0.5–1.5× |
| Platform labor classification | `P.123` | {status_quo, employee_reclassification}: moves platform FTE to the employee stock, which changes the attrition buffer |

### Shocks (§8.3 additions)
`approval_change` (class, region, at, new `J` path), `hardware_recall` (class, at, duration; sets deliveries to zero and `J` down), `content_licensing_ruling` (category, at, regime), `production_shock` (class, at, cap multiplier).

### Scenario schema
`schema_version` 0.3 adds `levers.applications.{embodiment, hardware, approval, content}` and the four shock types; v0.2 scenarios remain valid (new levers default to baseline).

---

## A.10 Data plan and verification items

Everything below is written from recollection of public sources and is flagged `V?` until an ingest script has fetched it and a provenance record exists; the sandbox that produced this amendment could reach only GitHub.

| Need | Candidate source | Access | Feeds | Fit / anchor / prior |
|---|---|---|---|---|
| Self-employed and platform workers by occupation | CPS (IPUMS) class of worker, hours, multiple jobs; Census Nonemployer Statistics; BLS Contingent Worker Supplement | IPUMS extract (script exists for CPS ASEC); Census API | §A.5.1 | data |
| Autonomous ride-hail fleet and rides | company posts and regulatory filings (paid rides per week, fleet size, cities); state permit registries | scraped and transcribed with dates | driving clock, `J`, ramp | **fit** (ramp, clock anchor) |
| Autonomous trucking corridors | company announcements; state permits | transcribed | `J` driving freight | anchor |
| Robot installations and stock | IFR press-release aggregates (paid detail not used); national robot associations (JARA, KAR); retailer and 3PL disclosures | transcribed, license-checked | baseline trend, manipulation clock, ramp | **fit** (installations trend) |
| Hardware unit prices and learning | vendor disclosures; investment-bank estimates (cited as estimates, not data); EV battery and industrial-robot price histories for `LR` priors | transcribed | `P.110`, `P.113` | prior with verified histories |
| Approval timetables | NHTSA and state DMV rules; EU type-approval; China city pilots; FAA BVLOS rules | transcribed with dates | `P.119` | baseline path |
| AI-generated content shares | streaming and platform statements (uploads flagged as AI-generated), stock-image marketplaces, publisher statements; guild agreements | transcribed | `s^{AI}` anchors, `α` | anchor where any exists, else prior |
| Category consumption and prices | BEA PCE by category; BLS CPI components; national accounts for EU and Asia | public API | `Q_s`, `p^H` | data |
| Authenticity premium | consumer surveys on willingness to pay for human-made content; music and art market studies | literature | `P.127` | prior; ranked first in risks |
| Services exports by category | UNCTAD and WTO BPM6 services trade; NASSCOM and IBPAP industry statistics; Eurostat ITS | public | §A.5.3 | data; **fit** BPO revenue trend |
| Deflection rates in customer service | vendor and enterprise disclosures; surveys | transcribed | `ai_customer_service` check | check |

Verification items to close before implementation (each becomes a row in `docs/data-inventory.md` §9): the 2025 fleet counts and paid-ride series for the driving anchor; a defensible 2025 unit price and utilization for robotaxis; IFR aggregates for 2015–2025; two independent estimates of AI-generated share for music and images; the BPM6 services export matrix for IN, RoA, EU; and a survey basis for the authenticity premium. If an item cannot be verified, the corresponding application ships with a dashed line and an `E` count, never with a fabricated anchor.

---

## A.11 Validation tests (additions to §7.5)

1. **Channel exclusivity**: every task group has exactly one channel; `Σ_channels D_{o,s,r,t} ≤ 1`.
2. **Conservation**: category spending = human-produced revenue + AI-produced revenue + consumer saving, per category, region, quarter; jobs below baseline by channel sum to the total.
3. **Baseline reproduction**: with all AI clocks frozen, the modelled robot stock reproduces the pre-2023 trend within 5%, and no application displaces anything.
4. **Deployment bound**: realized embodied displacement never exceeds deployment coverage.
5. **Regional ordering**: at the central draw, an embodied class becomes profitable in the highest-wage tier no later than in lower tiers.
6. **Monotonicity**: raising `LR_c` or `u_c` weakly raises embodied displacement; raising `α_s` weakly lowers `s^{AI}`.
7. **Fitted anchors**: driving-clock and ramp fit reproduce the paid-ride series within its stated band; IFR trend fit within 10%.
8. **Central-draw identity** (from v0.2 Phase 5) extends to the new fitted constants.
9. **Runtime**: ≤ 60 s for ten regions at 256 draws.

---

## A.12 What the amendment does not do, said plainly

- No general equilibrium: capital reallocation between the auto industry and fleet operators, land and parking, insurance, and energy demand are outside the model.
- No superstar dynamics within creative occupations; the model moves the mean, not the distribution within an occupation.
- No welfare measure; the consumer-surplus proxy is an accounting quantity at baseline prices.
- No endogenous regulation: approval paths are levers and shocks, not responses to accidents or unemployment.
- Care, surgery, crafts, and military applications stay out; scientific acceleration stays out as an unattributed upside.
- Through 2026 most embodied and media parameters are prior-driven, and the explain trace will say so on every number they touch.

---

## A.13 Phase mapping

| Phase | Scope | Demoable end state |
|---|---|---|
| 6 | Channel assignment; self-employed table; embodied channels for driving and mobile manipulation with unit cost, ramp, approval; `robotaxi`, `autonomous_trucking`, `warehouse_robotics`, `retail_checkout_shelf`; channel decomposition and Applications panel | "What happens to drivers, and where, if approvals accelerate?" answered with bands and confidence |
| 7 | Output substitution with the authenticity ensemble axis; `generative_*`, `machine_translation_voice`; consumer-surplus proxy; traded services with `ai_customer_service`; remaining catalogue entries; 16-cell ensemble | "How much of the music sector's employment survives an eroding authenticity premium, and who captures the revenue?" |

Each phase ends with a findings note and an update of this amendment's `V?` marks to `S` or `E` as verification completes.

---

## A.14 Questions for the reviewer

1. Is one channel per task group the right exclusivity rule, or should driving tasks in mixed occupations (delivery drivers who also load) be split by hours across two channels?
2. Should the authenticity premium be a structural axis (as proposed) or a continuous parameter with a wide range? The axis makes the disagreement visible; the parameter would give smoother bands.
3. Is Wright's law in cumulative production the right cost model for autonomy stacks, whose cost is dominated by software amortized over a fleet rather than by hardware?
4. The deployment-coverage bound makes production capacity the binding constraint for a decade at central values. Is that a feature or an assumption smuggled in through `g^{max}`?
5. Traded services reverse the trade matrix; should the model also carry re-shoring (importing regions replacing imports with domestic AI-augmented work), which cuts the other way?
6. Headline employment changes definition (FTE including self-employment). Keep the payroll-only headline as the default and the inclusive one as a toggle, or the reverse?

---

## A.15 Implementation notes and deviations (Phase 6 build)

Where the Phase 6 code departs from or sharpens the text above.

| Topic | Amendment text | Implementation | Why |
|---|---|---|---|
| Channel assignment (§A.2) | O*NET Generalized Work Activity and Work Context items | keyword rules on the task statement (`aiwsim.data.classify.classify_channel`, E), driving and aerial rules applied to every modality, care/dexterity rule maps to `none`; employment-weighted task-hour shares: software 74.9%, manipulation 20.1%, driving 1.9%, fixed 1.6%, none 1.6%, aerial ≈ 0 | GWA and Work Context are not in the offline replication data; the O*NET ingest replaces the rules |
| Embodiment clocks (§A.3.1) | anchored to paid-ride, disengagement, benchmark series | start at 0 in 2024Q1 with class doubling times (P.108) plus coupling to the software clock (P.107); task thresholds `θ_k = θ_lo + (θ_hi − θ_lo)·hash + 0.5·consequence` per class | no anchor series ingested yet; the driving clock fit is the first verification item |
| Fixed-automation increment (§A.2 rule 3, §A.6.2) | baseline robot stock `R^0` netted out | `a_emb(fixed)` is the increment itself and is scaled by `1.5 − 0.5·trend` (lever `baseline.automation_trend`); no explicit `R^0` series | the increment is small (1.6% of task-hours) and no IFR series is ingested |
| Production ramp (§A.3.3) | `g^max` 0.7/yr in the draft | central 0.5/yr (range 0.3–1.5); 2024Q1 production = 15% of 2025 cumulative production; capacity never falls below half the previous quarter | 0.7 sustained for sixteen years produced tens of millions of manipulators by 2040; EV history supports ~50%/yr |
| Deployment (§A.3.4) | per class, region, and use | per class and region; an application aggregates the engine's class-level results over its target occupations, so applications in the same class share a fleet and an approval path | one stock-flow per class keeps the layer cheap; per-use approval arrives with the permit data |
| Self-employed margin (§A.3.6, §A.5.2) | employee/self-employed split with transitions | self-employed FTE is added to `N0`; the attrition buffer applies only to the payroll share; the self-employed share of a required contraction is cut immediately (hours) and exits to searching at hazard P.121; layoff friction for embodied displacement inside employers is P.122 | transitions between the two statuses (P.123) await the CPS flows ingest |
| Adjacent and hardware jobs (§A.3.5) | adjacent jobs in named occupations | adjacent jobs `β_c·R` in the deploying region and hardware-production jobs (1,500 per $bn, E) in producing regions, both counted in `ai_production_jobs` and reported separately as `adjacent_jobs`; paid at $65k (E) | occupation-level adjacent mapping needs the fleet-operations staffing data |
| Ensemble (§A.7) | 16 cells, 256 draws | implemented; the authenticity axis arrives with output substitution in Phase 7 | — |
| Runtime (§A.7) | ≤ 60 s | 69 s for ten regions at 256 draws with tornado (26 parameters) and channels (8 runs) on 4 cores | the budget is exceeded by the larger tornado and channel sets, not by the embodied layer (a central run takes 2 s); tune in Phase 7 |
| Headline (§A.5.1) | payroll series kept alongside | headline is FTE including self-employed and platform workers; `meta.headline_definition` says so; a payroll-only series is not tracked | tracking both requires splitting every flow; deferred to Phase 7 |
| Applications with `*manip` targets | — | `humanoid_general` reports over every occupation with manipulation task-hours | it is the manipulation class reaching breadth, not a separate mechanism |

### Phase 7 rows (output substitution and traded services)

| Topic | Amendment text | Implementation | Why |
|---|---|---|---|
| Category intercept (§A.4) | `q_0` a registry parameter | the logit intercept is **solved at 2024Q1** so each category's AI share equals an anchored `share0` (E, V?: video 0.5%, music 1%, text 2%, image and design 5%, translation and voice 15%, advertising 3%); `P.126.q0` is unused | without an anchor the share started near 100% in 2024; anchoring makes the dynamics (price, quality, authenticity erosion) the only free part |
| AI content price (§A.4) | follows the token price path plus a platform margin | tracks the fixed-capability token price with exponent 0.1 and never falls below half its 2024 ratio; plus margin (P.128) and the licensing regime | distribution, curation and marketing dominate the consumer price of content; a 50× fall in tokens is not a 50× fall in subscriptions (attack 8) |
| Category volume (§A.4) | own-price elasticity | as specified, capped at +50% real consumption per category | an attention budget bounds media consumption; without the cap the price fall tripled categories and the consumer-surplus proxy reached $800bn/yr |
| Human output and labor (§A.4) | `Q^H = (1 − s^{AI}) Q` | `q_out = (1 − s^{AI})·Q/Q_0` multiplies the category occupations' labor demand; a category can gain human employment when volume growth outruns the AI share (video and music at central) | multiplicative margins, no double counting with the task channel |
| Revenues and rents (§A.4, attack 9) | model and integration stages | 60% of AI-content revenue to the model stage by market share, 40% to domestic integration; consumers' payments enter AI spend so the global identity holds | — |
| Traded services (§A.5.3) | export-serving employment from BPM6 × occupation composition | `services_trade.csv` (E, V?) gives exports, FTE per $m, occupations and importer weights; export-serving workers face `max(D_importer − D_local, 0)` on top of local displacement | the importer's software displacement of customer-service and IT tasks is slow at central (presence terms), so the channel reaches 0.04% of Indian employment by 2040; the figure is a statement about the task engine, not about BPO exposure, and the verification items (deflection rates) bear on it directly |
| Ensemble (§A.7) | 16 cells | 32 cells (authenticity axis added), 256 draws, 8 per cell | the classification thresholds are unchanged; more low-confidence calls are the intended consequence (attack 11) |
| Channel decomposition (§A.6.1) | software → embodied → output → traded → adjacent | automation, augmentation, embodied, output substitution, traded services, demand response, reinstatement, demand feedback, AI investment, adjacent (ten runs, threaded) | keeps v0.2's mechanism order inside the family order |

## A.16 Phase 8: policy wiring, induced demand, whole-job substitution, the Seba/RethinkX preset, the forecast scoreboard, the story layer

Phase 8 added no new channel. It wired the policy levers the v0.2 schema already carried (§6.5), gave applications their own demand response, made the driving applications remove roles rather than tasks, added a preset that reproduces Tony Seba's disruption framework as levers so it can be compared with the model on the same footing as the economists' presets, and put a scoreboard of named forecasts in every results document. The story layer (contracts §26–28) reads the results; it computes nothing new.

| Topic | Amendment or spec text | Implementation | Why |
|---|---|---|---|
| Policy levers (§6.5) | retraining subsidy, wage insurance, UBI, AI tax, work week, immigration, financing rules | minimal wiring in `mc.py`: the subsidy raises retraining entry (`×(1 + 2·s)`) and completion (`+0.1·s`); wage insurance pays the replacement share of the re-employed wage loss for its duration; UBI is `$/month × 12 × adults`; the AI tax multiplies the AI price path by `(1 + τ)` and yields `τ × AI spend`; a week of `h < 40` hours converts FTE to heads by `40/h` with pay per head scaled by `h/40`; immigration scales entrants; financing rules decide whether a cost falls on the deficit, the AI tax, or payroll. Transfers enter consumption at a 0.9 propensity, taxes at 0.4 (E). `meta.validity` flags a deficit beyond 3% of GDP in 2040 as outside the model's range | the model has no inflation, interest-rate or debt response; the flag says so and the story layer repeats it. Payroll financing reduces the wage-share term; none of the three rules changes labor demand directly |
| Induced demand (§A.3, §6.1) | sector own-price elasticity | `applications.csv.eta_app` adds an application-level elasticity above the sector's for embodied applications with `*manip` excluded; `Q^{app} = Q · exp(−(η_app − η_sector) · π · Δln c)`, scaled by lever `applications.induced_demand_scale` (0–2) | Seba's central claim for transport is that a ten-fold fall in cost per mile creates trips that do not exist today; the sector elasticity (0.4–0.9) cannot carry that, so the application carries its own (1.5 for robotaxis, 1.2 for delivery, 0.8 for trucking; E, V?) |
| Whole-job substitution (§A.2, §A.6.2) | task-level displacement with the software channel's human-presence discount | for occupations targeted by an application with `whole_job = 1` (robotaxi, autonomous trucking, last-mile delivery), the presence discount `(1 − presence)^λ` is not applied to the driving task groups, and the realized displacement is scaled by `1 / w_driving` so a fully covered fleet removes the whole role; the profitability test and the coverage gate still apply. `meta.whole_job` carries the driving weight, feasible share, profitable-feasible share and coverage per role | a taxi driver's driving tasks are 31% of the role's task-hours; task-level substitution left 69% of the job in place with a vehicle that carries the passenger. The presence discount encodes "someone must be there", which Waymo and Apollo Go rides refute for the driving tasks of these roles. With the rule, robotaxi displacement of taxi drivers reaches 56% by 2040 in the baseline and 73% by 2030 under the Seba preset (capped by approval J = 0.85 and the 85% ever-automatable share) |
| Seba/RethinkX preset (§A.7, §8) | economists' presets only | `preset-seba-rethinkx.json`: LR 0.25, ramp cap 1.5/yr, utilization ×1.5 (transport as a service), unit price ×0.7, driving/manipulation/fixed/aerial doubling 9/8/12/9 months coupled 0.7 to software, accelerated approval where fleets operate, eroding authenticity at 0.6, permissive licensing, price sensitivity 3; `applications.enabled = true` | the levers reproduce the shape of his S-curve argument (cost curves, utilization, fast approval) inside the model's accounting, so the scoreboard compares his numbers with the model's on the same base; the model stays below his 95% claim because approval, the ramp cap and the ever-automatable share bind before the cost does |
| Forecast scoreboard (§7.5) | replication tests for presets | `forecasts.csv` (Seba 2017 robotaxi coverage and driver displacement, RethinkX 2020 embodied share, Acemoglu 2024 TFP, Goldman 2023 GDP, IMF 2024 exposure, Canaries 2025 young exposed employment); `results.forecasts[]` reports the model's central and p10–p90 at the claim's quarter and a verdict; `proxy = 1` marks comparisons with the nearest model quantity | a forecast that cannot be checked against the model is a slogan; the scoreboard makes each claim a row with a verdict on every run, including the preset built to reproduce it |
| Story layer (contracts §26–28) | — | `api/aiwsim_api/story.py`: seven beats, reconciled numbers (a jobs ledger of positions and a people ledger of who was affected, kept apart and explained), named futures from the tornado extremes of P.87 plus scenario runs, policy runs read against the baseline, a personal outlook by occupation and age, and an executive brief with inline SVG charts and no parameter codes | the technical brief answers "what did the model do"; the executive brief answers "what does it mean for me" with the same numbers |
| Seba 2026 variant (§A.7, §8) | — | `preset-seba-2026.json` (parent: the transport preset) carries RethinkX's 2024–2026 labour claims and the 2026 *Rethinking Energy, Mobility, and Materials* roadmap: every embodiment clock at 6 months, `manipulation_automatable_share` 0.85 (new lever on P.101), utilization ×1.6, unit price ×0.5, accelerated approval in every region, induced demand ×2. Scoreboard rows: humanoid labour under $10/hour at entry (2025) and under $1/hour before 2035 (compared with the manipulation class's cost per worker-hour equivalent, new metric `humanoid_cost_per_hour_usd`), robots doing as much work as people by 2039 (read as 50% of task-hours), TaaS at 50% of urban passenger miles by 2032 and 80% by 2035 (compared with robotaxi coverage) | the transport preset tests his 2017 claims; the humanoid claims need the manipulation class pushed as hard, and a preset that cannot reach them says where the model's constraints bind (ramp, approval, the ever-automatable share) |
| Layoffs before attrition (§5.3) | required cuts absorbed by net occupational attrition first, layoffs second (P.63, P.64) | lever `labor.layoff_first_share` φ: a share φ of each quarter's required reduction is taken as layoffs at once, the rest through attrition then P.64. **Fitted** in the baseline to the AI-cited job cuts employers announced (Challenger, Gray & Christmas: 54,836 in 2025; 173,568 since 2023 by June 2026): φ = 0.25 puts the model's central run within ±30% of both counts (the attrition-first rule alone gave a tenth of them). Levels in heads (`baseline_employment_level`, `employment_level`) are reported so the story can say how 2040 compares with today, not only with the no-AI path; the variant `variant-layoffs-first` (φ = 0.5, P.63 low, P.64 high) shows the same total borne by incumbents | the 2025–2026 wave of AI-cited layoffs contradicted the spec's attrition-first reading; announced cuts overstate realized layoffs (they include attrition and redeployment), so the fit is loose and φ is a Phase 9 verification item against realized separations |
| Revenue layer (§6.1, §6.4) | AI spend = displaced task-hours × token cost; rents = that spend by value-chain stage | firms pay a **market price** for AI work: cost (tokens at the fixed-capability price plus integration) × a multiple `m(t)` that starts at P.143 (5.0 in 2025: usage intensity per unit of work delivered, frontier pricing, margin) and decays with half-life P.145 to P.144 (1.5); the multiple enters the profitability test and the cost-saving share as well as the spend. **Consumer AI spending** (subscriptions, advertising, services) follows a logistic from P.140 ($15bn in 2025) to P.141 ($150bn) with midpoint P.142 (2030), is paid by regions in proportion to GDP and split across the value-chain stages like employer spend. Producers' revenue = employer spend at market prices + consumer spending + AI-made content; `ai_spend_at_token_cost_bn` keeps the cost basis. Fitted to reported industry revenue: 2025 $45–80bn, 2026 $90–200bn (scoreboard rows) | the first version priced AI at token cost for displaced hours only and reported $15bn of world revenue in 2026 against an industry earning $90bn or more; the labour engine was not wrong but the revenue accounting was, and the investment section needs the revenue the industry books, not the cost of the work it replaces. Applying the multiple to the cost test lowers firms' savings and trims early displacement slightly (median 2040 employment −5.5% against −5.6%) |
| Structural ensemble (§A.7) | 32 cells | unchanged; policy and application levers re-centre the draws as every lever does | — |
| Embodied cost floor (§A.3.2; Phase 9, review §2.8) | Wright's-law unit price, annualized over utilized hours | `embodiment_classes.csv.cost_floor_usd_per_hour` (driving 3.0, manipulation 1.5, fixed 1.0, aerial 0.8; E) floors both the cost the firm tests, `κ_h = max(annual / cap_unit, floor)`, and the recorded cost per worker-hour; lever `applications.hardware.cost_floor_scale` (0–3) scales it, 0 reproduces the Phase 8 curves | under the Seba 2026 preset the manipulation cost fell to $0.04/hour by 2034, below the electricity to run the robot; energy, maintenance, insurance and the capital charge at scale do not learn away |
| Balanced-budget policy financing (§6.5; Phase 9, review §2.1, §2.10) | financing rules deficit / AI tax / income-tax surcharge | the surcharge is booked as revenue in the fiscal balance (`fiscal = tax − cost + surcharge`), so a surcharge-financed item is balanced-budget; `policy-ubi-ai-tax` now finances the payment by the surcharge with the AI tax on top (renamed "tax-financed"), and `policy-ubi-deficit` keeps the deficit-financed version only to show the validity flag | the deficit-financed UBI reported +14 million jobs from $1.7 trillion a year of deficit spending in a model with no interest-rate or inflation response; the policy page should not report that sign |
| Entrant supply response (§5.3; Phase 9, review §2.7) | entrant cohorts fixed in size | the share of an occupation's attrition cut that lands on its entrant cohort is `s_ent = min(1, clip(w_o(t−L)/w_o^0, 0.5, 1.5)^ε)` with ε = P.146 (0.5, range 0–1.5) and L = P.147 (8 quarters); `w_o/w_o^0 = exp(ln w)` is the occupation's wage index at the lagged quarter. Positions still close (`unhired_cum`, employment), but only `s_ent × via_attr` enters the searching pool and the cohort ledgers; ε = 0 reproduces the Phase 8 rule exactly. `variant-market-clearing-wages` sets P.73, P.74, P.61 and the P.60 scale to the top of their ranges | nobody changed field of study when computer occupations lost 8% of jobs by 2030; the under-25 share of the shortfall (35%) was a modelling choice with no supply response behind it |
| Threshold seed and classifier audit (§2.2; Phase 9, review §2.4) | per-task thresholds spread by a hash of the task key | lever `capability.threshold_seed` (0–999) appends the seed to the hashed key; seed 0 is byte-identical to before. `aiwsim diag threshold-seeds` reports the headline and the Spearman rank correlation of occupation effects across seeds (`docs/diagnostics-phase9.md`); `aiwsim diag classifier-sample` writes a stratified 120-statement audit table for hand labelling (`docs/classifier-audit-sample.md`). Channel rules v2: installation and repair trades (SOC 47-2xxx, 49-xxxx) keep at most 30% of task-hours on the manipulation channel unless a statement names assembly-line, warehouse or repetitive handling; the rest go to `none` | electricians (78% of task-hours on manipulation) and HVAC mechanics (71%) were robot targets by keyword; one-off work at customer sites is outside the manipulation class at central |

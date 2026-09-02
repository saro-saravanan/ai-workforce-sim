# Findings so far — Phase 7 (output substitution, traded services, full catalogue)

*Phase 7 completes the v0.3 application layer: AI-produced content competing in product markets with an authenticity premium, automation abroad reaching exporters' workers, and the catalogue's software rows. Numbers are the 256-draw, 32-cell, ten-region baseline unless stated; every category and trade parameter is an authors' estimate marked V? in the spec.*

## 1. What the model says at the end of v0.3

| U.S., 2040 Q4 | v0.2 (Phase 5) | v0.3 Phase 6 | v0.3 Phase 7 |
|---|---|---|---|
| Employment vs frozen-AI baseline, median [10–90] | −2.5% [−6.5, +1.2] | −4.8% [−10.2, +0.6] | −4.8% [−10.1, +0.3] |
| GDP | +6.8% | +8.1% | +8.2% [+5.1, +16.5] |
| Real wages | +3.1% | +4.1% | +4.1% |
| Wage share | −3.5 pp | −4.6 pp | −4.6 pp |
| Embodied displacement, share of task-hours | — | 5.4% | 5.5% |
| Sign confidence, employment | low | medium | low |

The headline changed between v0.2 and Phase 6, when self-employed workers entered the denominator and the embodied channel arrived. Phase 7 changed it very little: output substitution moves national employment by a twentieth of a point, and traded services do not touch the U.S. at all. What Phase 7 changes is *where* the effects land and *how uncertain* they are: the structural spread across the 32 cells (10.8 pp) is now almost twice the parametric spread within a cell (5.8 pp), and the employment sign returned to low confidence because the authenticity axis and the hardware axis both move it.

## 2. Output substitution: small nationally, decisive within creative work

- By 2040 the median AI-produced share of spending is 72% for translation and voice, 45% for images and design, 28% for advertising creative, 26% for text, 14% for music, and 8% for video (eroding authenticity premium at central). With a persistent premium the video and music shares stay in single digits.
- **Categories can grow while the AI share rises.** The category's real consumption expands with the lower average price (capped at +50%, an attention budget), so human-produced video and music output is roughly flat or up by 2040 at the central draw, while images and design lose about a quarter of human output and translation about 60%. The channel bar for output substitution is −0.08 pp of U.S. employment in 2040: the affected occupations are about 1.3 million jobs, many self-employed.
- The consumer-surplus proxy is $57bn/yr median in 2040 [33, 103], AI-content revenue about $6bn/yr. The first is an accounting quantity at baseline prices, not welfare, and the results say so wherever it appears.
- The anchoring rule mattered more than any parameter: without pinning 2024 shares (0.5% video to 15% translation), the logit started near 100% and the surplus proxy reached $800bn. The spec's calibration clause (anchor where any series exists) is doing real work, and the anchors are the first verification items for this channel.

## 3. Traded services: the channel is real, the task engine keeps it small

Export-serving employment (E, V?): India 3.8M, rest of Asia 1.3M, EU 0.2M. Their displacement follows the importers' automation of customer-service and IT tasks, which at central is slow: 0.04% of Indian employment by 2040, 0.01% in the rest of Asia. This is a statement about the v0.2 task engine's presence and interpersonal terms for customer-service work, not about BPO exposure per se; the deflection-rate verification item bears on it directly, and the lever `services_exposure_scale` doubles it.

## 4. Embodied: unchanged from Phase 6 except the ramp

With the production ramp cap at 0.5/yr (lowered from 0.7 after Phase 6's first run), the U.S. driving fleet reaches 0.38M units and the manipulation fleet 1.3M at the central draw by 2040, against 5.6M manipulators in the first draft. The ramp cap is the fifth-largest employment sensitivity in the model (3.4 pp swing). The Phase 6 caution stands: at central unit economics mobile manipulators are below every wage tier by the mid-2030s, so unit price, utilization, and task-units per hour for unstructured work decide the class.

## 5. Presets

The three published-study presets now switch the application layer off (`applications.enabled = false`), because Acemoglu, Goldman Sachs, and the IMF modelled generative AI on tasks only. With the layer on, the Goldman preset's ten-year GDP effect rose above its replication band, which is the model saying that embodied automation is additional to what those studies counted.

## 6. What I do not trust yet

- The category anchors, price ratios, elasticities, and authenticity levels: all E, V?, and the most consequential of them (anchors) were set by judgement this phase.
- Traded-services occupation mapping and export-serving employment: coarse, and the result depends on the software channel's treatment of interpersonal tasks.
- Eight draws per structural cell. The classification thresholds are unchanged, so "low" is honest, but the within-cell percentiles are noisier than in v0.2.
- Runtime: 86 seconds for the full pipeline against a 60-second budget. The embodied and output layers add about a second each per run; the cost is the 32-cell ensemble, the 29-parameter tornado, and ten channel runs.

## 7. Runtime and verification

Central ten-region run 2.5 s. Full baseline 86 s. Test suites: 65 simulation-core (13 for the application layer), 5 API, web suite reported separately.

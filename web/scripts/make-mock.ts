/**
 * Generates web/src/mock/{results.json, results-b.json, levers.json, scenarios.json, us-states.geojson, world.geojson}.
 * Numbers are deliberately synthetic (smooth S-curves + seeded noise); the shape matches
 * docs/contracts.md §2, the Phase 2 additions in §7–10, the Phase 3 additions in §11–14
 * (ten regions, `world`, `supply`, `ai_rents_received_bn`, `occupations[].by_region`) and the
 * Phase 6 application layer in §19–20 (`applications`, embodied series, `supply.embodiment`,
 * `hours_cut_self`) and the Phase 7 additions in §23–25 (output substitution by content
 * category, traded services, ten-entry channels, 32 mechanism cells with the authenticity axis,
 * output / traded / software catalogue rows). Run: pnpm make-mock
 *
 *  - results.json    the "baseline" run (all percentiles, structural, confidence, tornado, cohorts, flows, trace)
 *  - results-b.json  the "eu-delay-deepseek-2027" run: same generator, shifted parameters, so
 *                    /api/compare can be mocked by paired differences
 *  - levers.json     /api/levers derived from scenarios/schema.json + labels below
 *  - scenarios.json  the scenario documents under scenarios/*.json (for the levers form)
 */
import { readFileSync, writeFileSync, mkdirSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import type {
  ResultsDocument,
  OccupationResult,
  StateResult,
  ChannelName,
  StatesGeoJSON,
  Series,
  HeadlineMetric,
  StructuralSection,
  Confidence,
  TornadoRow,
  CohortRow,
  FlowsSection,
  FlowDestination,
  Trace,
  DiffEntry,
  LeverDef,
  ScenarioDocument,
  ParamTag,
  RegionId,
  RegionSeries,
  RegionInfo,
  WorldEntry,
  WorldGeoJSON,
  SupplySection,
  SupplyRelease,
  RegulatoryEvent,
  RentsByStage,
  RentStage,
  OccupationByRegion,
  CentralSeries,
  ApplicationEntry,
  ApplicationRegion,
  EmbodimentClass,
  EmbodimentSeries,
} from '../src/types/results'
import { HEADLINE_METRICS, FLOW_DESTINATIONS, REGION_IDS, RENT_STAGES } from '../src/types/results'

const here = dirname(fileURLToPath(import.meta.url))
const outDir = resolve(here, '../src/mock')
const repoRoot = resolve(here, '../..')
const rawGeo = resolve(repoRoot, 'data/raw/natural_earth/ne_admin1_110m.geojson')
const rawWorld = resolve(repoRoot, 'data/raw/natural_earth/ne_admin0_110m.geojson')
const scenariosDir = resolve(repoRoot, 'scenarios')

// ---------- deterministic PRNG ----------
function mulberry32(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// ---------- quarters ----------
const quarters: string[] = []
for (let y = 2024; y <= 2040; y++) for (let q = 1; q <= 4; q++) quarters.push(`${y}Q${q}`)
const N = quarters.length // 68
const t = (i: number) => i / 4 // years since 2024Q1
const Q2030 = quarters.indexOf('2030Q4')
const Q2040 = quarters.indexOf('2040Q4')

const logistic = (x: number, mid: number, k: number) => 1 / (1 + Math.exp(-k * (x - mid)))
const round = (v: number, d = 4) => Number(v.toFixed(d))
const curve = (f: (yr: number) => number) => Array.from({ length: N }, (_, i) => f(t(i)))
/** S-curve that starts at 0 in 2024Q1; `lead` (years) shifts the path earlier (>0) or later (<0) */
const rise = (amp: number, mid: number, k: number, lead = 0) =>
  curve((yr) => amp * logistic(yr + lead, mid, k) - amp * logistic(lead, mid, k))
const quarterOf = (date: string) => {
  const y = Number(date.slice(0, 4))
  const mth = Number(date.slice(5, 7))
  return `${y}Q${Math.floor((mth - 1) / 3) + 1}`
}
const add = (a: number[], b: number[]) => a.map((v, i) => v + (b[i] ?? 0))
const mul = (a: number[], k: number) => a.map((v) => v * k)

/**
 * Percentiles around a median: p10<p25<p50<p75<p90 with a band that widens over time,
 * and `central` (the central-parameter run) close to but not equal to p50.
 */
function bandify(
  p50: number[],
  amp: number,
  opts: { floor?: number; ceil?: number; digits?: number; skew?: number; loose?: boolean } = {},
): Series {
  // `loose`: ties are allowed after rounding (small integer counts such as fleets of a few units)
  const { floor, ceil, digits = 4, skew = 0, loose = false } = opts
  const clamp = (v: number) =>
    Math.min(ceil ?? Number.POSITIVE_INFINITY, Math.max(floor ?? Number.NEGATIVE_INFINITY, v))
  const sigma = (i: number) => amp * (0.03 + 0.97 * Math.pow(i / (N - 1), 1.15))
  const at = (z: number) => p50.map((v, i) => round(clamp(v + z * sigma(i) * (1 + skew * z)), digits))
  const central = p50.map((v, i) =>
    round(clamp(v + 0.12 * sigma(i) * Math.sin(i / 9 + 0.7)), digits),
  )
  const s: Series = {
    p10: at(-1.2816),
    p25: at(-0.6745),
    p50: p50.map((v) => round(clamp(v), digits)),
    p75: at(0.6745),
    p90: at(1.2816),
    central,
  }
  // strictness check: bands must be ordered after rounding (except when clamped at a bound)
  for (let i = 1; i < N; i++) {
    const v = [s.p10![i]!, s.p25![i]!, s.p50[i]!, s.p75![i]!, s.p90![i]!]
    for (let k = 1; k < v.length; k++) {
      const clamped = (floor != null && v[k]! <= floor) || (ceil != null && v[k - 1]! >= ceil)
      const ok = loose ? v[k]! >= v[k - 1]! : v[k]! > v[k - 1]!
      if (!ok && !clamped)
        throw new Error(`band not strictly ordered at i=${i}: ${v.join(', ')}`)
    }
  }
  return s
}

// ---------- generator configuration (A vs B differ only here) ----------
interface Cfg {
  scenarioId: string
  hash: string
  adoptionMid: number
  adoptionCeil: number
  gdpAmp: number
  tfpAmp: number
  empDrop: number
  empRecover: number
  wageDip: number
  wageGain: number
  priceAmp: number
  wageShareAmp: number
  displacedAmp: number
  spendAmp: number
  doublingMonths: number
  euAdoptionLead: number
  /** Phase 3: quarter of an open-weights frontier release shock (price ×0.25, CN lag → 0), or null */
  openWeightsAt: string | null
  /** Phase 3: years the EU AI Act high-risk obligations are delayed */
  euAiActDelayYears: number
  /** Phase 6: midpoint (years after 2024) and 2040 level (% of task-hours) of the U.S. embodied displacement path */
  embodiedMid: number
  embodiedAmp: number
  /** Phase 7: years the AI-content share paths lead (>0) the baseline run (a faster-eroding authenticity premium) */
  contentLead: number
  /** Phase 7: 2040 traded-services displacement of Indian employment (%); Rest of Asia is a quarter of it */
  tradedAmp: number
  diff: DiffEntry[]
  notes: string[]
}

const cfgA: Cfg = {
  scenarioId: 'baseline',
  hash: 'sha256:mock-a000000000000000000000000000000000000000000000000000000000000000',
  adoptionMid: 6.5,
  adoptionCeil: 0.78,
  gdpAmp: 6.2,
  tfpAmp: 4.6,
  empDrop: -3.8,
  empRecover: 1.7,
  wageDip: -0.6,
  wageGain: 2.4,
  priceAmp: -3.1,
  wageShareAmp: -2.6,
  displacedAmp: 9.4e6,
  spendAmp: 1050,
  doublingMonths: 6,
  euAdoptionLead: 0,
  openWeightsAt: null,
  euAiActDelayYears: 0,
  embodiedMid: 12.5,
  embodiedAmp: 5.6,
  contentLead: 0,
  tradedAmp: 0.09,
  diff: [],
  notes: [
    'MOCK DATA. Every number here is a synthetic S-curve generated by web/scripts/make-mock.ts, not a model run.',
    'Adoption follows a logistic path from 4% of firms in 2024 to about 80% by 2040, with the midpoint in mid-2030.',
    'Net employment falls to roughly -3.8% versus the no-AI baseline around 2032 before reinstatement and demand feedback recover part of the loss.',
    'The automation and embodied channels are the negative contributors; augmentation, demand response, reinstatement, demand feedback, AI investment and adjacent hardware jobs offset about half of them by 2040.',
    'Embodied automation (robotaxis, trucking, warehouse and fixed robots) arrives late: about 0.3% of U.S. task-hours by 2030 and 5.6% by 2040, gated by class clocks, unit cost and approval (spec v0.3 §A.3).',
    'Output substitution (spec v0.3 §A.4): AI produces about 72% of translation and voice, 44% of image and design and 26% of text consumption by 2040 at central; video and music stay below 15% behind the authenticity premium. Cheaper content expands the categories (up to +50%), so human output in video and music grows for most of the horizon; the consumer-surplus proxy reaches about $55bn per year (an accounting proxy at baseline prices, not welfare).',
    'Traded services (spec v0.3 §A.5.3): export-serving workers in India and Rest of Asia face the importers’ displacement of customer-service and IT tasks; 0.09% of Indian employment by 2040 at central. Importers read zero.',
    'Bands are the pooled 2x2x2x2x2 mechanism ensemble (demand response, reinstatement, pass-through, hardware learning rate, authenticity premium); the structural view separates the 32 cell medians.',
    'State and occupation series are the national path scaled by a fixed per-unit tilt (data_flags.occ_state = FIXTURE), so the map shows spread but no real geography.',
    'Regions: the U.S. is hit first; the EU follows about three quarters later (AI Act high-risk timetable plus a two-quarter availability delay); China and Rest of Asia lag furthest because the closed frontier is unavailable and domestic actors trail it.',
    'Rents: about 70% of value-chain rents accrue to the U.S. (model margin by market share, data-center share, chip design); Taiwan captures a fixed 35% of the chip stage; the EU takes equipment and integration.',
  ],
}

const cfgB: Cfg = {
  ...cfgA,
  scenarioId: 'eu-delay-deepseek-2027',
  hash: 'sha256:mock-b000000000000000000000000000000000000000000000000000000000000000',
  adoptionMid: 5.7,
  adoptionCeil: 0.82,
  gdpAmp: 6.9,
  tfpAmp: 5.1,
  empDrop: -4.5,
  empRecover: 1.9,
  wageDip: -0.9,
  wageGain: 2.7,
  priceAmp: -3.8,
  wageShareAmp: -3.1,
  displacedAmp: 10.8e6,
  spendAmp: 980,
  doublingMonths: 5.5,
  euAdoptionLead: 0.8,
  openWeightsAt: '2027Q1',
  euAiActDelayYears: 2,
  embodiedMid: 11.9,
  embodiedAmp: 6.4,
  contentLead: 0.8,
  tradedAmp: 0.11,
  diff: [
    {
      path: 'levers.regulation.EU.ai_act',
      from: 'baseline',
      to: 'delayed_2y',
      mechanism:
        'EU high-risk use-case availability moves two years earlier (P.30–P.32); EU adoption q rises, spillover to US via tradable sectors.',
    },
    {
      path: 'shocks[deepseek-open-2027]',
      from: null,
      to: { type: 'open_weights_release', actor: 'deepseek', at: '2027Q1', frontier_lag_quarters: 0 },
      mechanism:
        'Open-weights frontier release: inference price ×0.25 (P.05) in EU and CN from 2027Q1; frontier lag 0 for the open actor; US actor revenue share falls.',
    },
  ],
  notes: [
    'MOCK DATA. Every number here is a synthetic S-curve generated by web/scripts/make-mock.ts, not a model run.',
    'Compared with the baseline run, adoption reaches its midpoint about 0.8 years earlier because open weights cut the effective task price from 2027.',
    'Net employment falls further (about -4.5% at the trough) and recovers slightly more by 2040 as reinstatement follows the larger displacement.',
    'GDP and productivity end higher; the wage share falls by another half point.',
    'Output substitution moves about 0.8 years earlier with the cheaper open-weights token price, so the AI shares of text, image and advertising end a few points higher; traded-services displacement in India reaches 0.11% of employment by 2040.',
    'Bands are the pooled 2x2x2x2x2 mechanism ensemble (demand response, reinstatement, pass-through, hardware learning rate, authenticity premium); the structural view separates the 32 cell medians.',
    'State and occupation series are the national path scaled by a fixed per-unit tilt (data_flags.occ_state = FIXTURE), so the map shows spread but no real geography.',
    'Regions: the delayed AI Act moves EU adoption earlier; the 2027 open-weights release closes the Chinese capability gap and cuts prices four-fold in the EU and China, so the U.S. model-margin share of rents falls.',
  ],
}

// ---------- Phase 3: regions, members, actors (contracts §11) ----------
interface RegionCfg {
  id: RegionId
  name: string
  population: number
  gdp_bn_usd: number
  employment_total: number
  /** years the region's adoption/impact path trails (<0) or leads (>0) the U.S. */
  lead: number
  /** multiplier on the U.S. employment / displacement effect */
  amp: number
  wageMul: number
  gdpMul: number
  /** share of global AI spend (U.S. = 1) */
  spend: number
  /** share of global inference capacity (regions.csv data_center_share) */
  dataCenterShare: number
  /** regional available capability lag vs the frontier, in doublings */
  capLag: number
  /** Phase 6: deployed-unit multiplier vs the U.S. and years the approval path trails (<0) or leads (>0) the U.S. */
  fleet: number
  approvalLead: number
  regime: string
  flags: RegionInfo['data_flags']
}
const FIX: RegionInfo['data_flags'] = { occ_region: 'FIXTURE', trade_weights: 'FIXTURE' }
const PART: RegionInfo['data_flags'] = { occ_region: 'partial', trade_weights: 'FIXTURE' }
const REGIONS: RegionCfg[] = [
  { id: 'US', name: 'United States', population: 335e6, gdp_bn_usd: 27_360, employment_total: 160e6, lead: 0, amp: 1, wageMul: 1, gdpMul: 1, spend: 1, dataCenterShare: 0.55, capLag: 0, fleet: 1, approvalLead: 0, regime: 'state_patchwork', flags: { occ_state: 'FIXTURE', occ_region: 'real', trade_weights: 'FIXTURE' } },
  { id: 'EU', name: 'European Union', population: 449e6, gdp_bn_usd: 18_350, employment_total: 200e6, lead: -0.75, amp: 0.78, wageMul: 0.85, gdpMul: 0.85, spend: 0.45, dataCenterShare: 0.15, capLag: 0.6, fleet: 0.5, approvalLead: -2, regime: 'eu_ai_act', flags: PART },
  { id: 'UK', name: 'United Kingdom', population: 68e6, gdp_bn_usd: 3_340, employment_total: 33e6, lead: -0.25, amp: 0.95, wageMul: 0.95, gdpMul: 0.95, spend: 0.07, dataCenterShare: 0.05, capLag: 0.2, fleet: 0.15, approvalLead: -1, regime: 'light', flags: PART },
  { id: 'CN', name: 'China', population: 1_410e6, gdp_bn_usd: 17_800, employment_total: 740e6, lead: -1.1, amp: 0.7, wageMul: 0.9, gdpMul: 1.15, spend: 0.5, dataCenterShare: 0.12, capLag: 1.6, fleet: 1.2, approvalLead: 0, regime: 'licensing', flags: FIX },
  { id: 'JP', name: 'Japan', population: 124e6, gdp_bn_usd: 4_210, employment_total: 68e6, lead: -0.5, amp: 0.75, wageMul: 0.9, gdpMul: 0.9, spend: 0.1, dataCenterShare: 0.04, capLag: 0.25, fleet: 0.3, approvalLead: -1, regime: 'light', flags: PART },
  { id: 'KR', name: 'South Korea', population: 52e6, gdp_bn_usd: 1_710, employment_total: 28e6, lead: -0.4, amp: 0.9, wageMul: 1.05, gdpMul: 1.0, spend: 0.05, dataCenterShare: 0.03, capLag: 0.25, fleet: 0.2, approvalLead: -0.5, regime: 'light', flags: PART },
  { id: 'IN', name: 'India', population: 1_430e6, gdp_bn_usd: 3_550, employment_total: 520e6, lead: -1.5, amp: 0.5, wageMul: 1.2, gdpMul: 1.1, spend: 0.12, dataCenterShare: 0.03, capLag: 0.5, fleet: 0.1, approvalLead: -3, regime: 'light', flags: FIX },
  { id: 'TW', name: 'Taiwan', population: 23e6, gdp_bn_usd: 790, employment_total: 11.5e6, lead: -0.4, amp: 0.85, wageMul: 1.0, gdpMul: 1.2, spend: 0.03, dataCenterShare: 0.02, capLag: 0.25, fleet: 0.05, approvalLead: -1, regime: 'light', flags: PART },
  { id: 'SG', name: 'Singapore', population: 5.9e6, gdp_bn_usd: 500, employment_total: 3.8e6, lead: 0.1, amp: 1.1, wageMul: 1.1, gdpMul: 1.05, spend: 0.02, dataCenterShare: 0.02, capLag: 0, fleet: 0.03, approvalLead: 0.5, regime: 'light', flags: PART },
  { id: 'RoA', name: 'Rest of Asia', population: 1_100e6, gdp_bn_usd: 6_100, employment_total: 700e6, lead: -1.8, amp: 0.45, wageMul: 1.1, gdpMul: 1.0, spend: 0.1, dataCenterShare: 0.02, capLag: 0.8, fleet: 0.1, approvalLead: -3, regime: 'light', flags: FIX },
]

/** EU-27 iso3 codes (Malta is absent at Natural Earth 110m; Cyprus is drawn with the EU). */
const EU27 = new Set(['AUT', 'BEL', 'BGR', 'HRV', 'CYP', 'CZE', 'DNK', 'EST', 'FIN', 'FRA', 'DEU', 'GRC', 'HUN', 'IRL', 'ITA', 'LVA', 'LTU', 'LUX', 'MLT', 'NLD', 'POL', 'PRT', 'ROU', 'SVK', 'SVN', 'ESP', 'SWE'])
const SINGLE: Record<string, RegionId> = { USA: 'US', GBR: 'UK', CHN: 'CN', JPN: 'JP', KOR: 'KR', IND: 'IN', TWN: 'TW', SGP: 'SG' }
/** Rest of Asia = Natural Earth CONTINENT "Asia" in the Eastern / South-Eastern / Southern subregions, minus the named regions. */
const ROA_SUBREGIONS = new Set(['Eastern Asia', 'South-Eastern Asia', 'Southern Asia'])
function assignRegion(p: Record<string, unknown>): RegionId | '' {
  const iso3 = String(p.ADM0_A3)
  if (SINGLE[iso3]) return SINGLE[iso3]!
  if (EU27.has(iso3)) return 'EU'
  if (p.CONTINENT === 'Asia' && ROA_SUBREGIONS.has(String(p.SUBREGION))) return 'RoA'
  return ''
}

interface ActorCfg {
  actor_id: string
  name: string
  region_id: RegionId
  posture: 'closed' | 'open-lagged' | 'open-frontier'
  /** market-share prior within its home region and elsewhere */
  home: number
  abroad: number
}
const ACTORS: ActorCfg[] = [
  { actor_id: 'openai', name: 'OpenAI', region_id: 'US', posture: 'closed', home: 0.34, abroad: 0.3 },
  { actor_id: 'anthropic', name: 'Anthropic', region_id: 'US', posture: 'closed', home: 0.24, abroad: 0.2 },
  { actor_id: 'google', name: 'Google DeepMind', region_id: 'US', posture: 'closed', home: 0.2, abroad: 0.22 },
  { actor_id: 'meta', name: 'Meta', region_id: 'US', posture: 'open-lagged', home: 0.08, abroad: 0.08 },
  { actor_id: 'xai', name: 'xAI', region_id: 'US', posture: 'closed', home: 0.05, abroad: 0.03 },
  { actor_id: 'deepseek', name: 'DeepSeek', region_id: 'CN', posture: 'open-lagged', home: 0.5, abroad: 0.06 },
  { actor_id: 'alibaba', name: 'Alibaba (Qwen)', region_id: 'CN', posture: 'open-lagged', home: 0.4, abroad: 0.05 },
  { actor_id: 'mistral', name: 'Mistral', region_id: 'EU', posture: 'open-lagged', home: 0.12, abroad: 0.02 },
]
const CLOSED_US = ACTORS.filter((a) => a.region_id === 'US' && a.posture === 'closed').map((a) => a.actor_id)

/** Transcribed public release history (capability index on the METR clock where the model is on the series, else null). */
const RELEASES: Array<[string, string, string, number | null, boolean]> = [
  // actor, model, date, capability_index (doublings), open_weights
  ['openai', 'GPT-4o', '2024-05-13', 3.2, false],
  ['anthropic', 'Claude 3.5 Sonnet', '2024-06-20', 4.2, false],
  ['meta', 'Llama 3.1 405B', '2024-07-23', 3.9, true],
  ['mistral', 'Mistral Large 2', '2024-07-24', null, true],
  ['alibaba', 'Qwen2.5', '2024-09-19', null, true],
  ['openai', 'o1', '2024-12-05', 5.3, false],
  ['deepseek', 'DeepSeek-V3', '2024-12-26', 4.3, true],
  ['deepseek', 'DeepSeek-R1', '2025-01-20', 4.9, true],
  ['xai', 'Grok 3', '2025-02-17', null, false],
  ['anthropic', 'Claude 3.7 Sonnet', '2025-02-24', 5.75, false],
  ['google', 'Gemini 2.5 Pro', '2025-03-25', 5.9, false],
  ['openai', 'o3', '2025-04-16', 6.5, false],
  ['alibaba', 'Qwen3', '2025-04-29', null, true],
  ['anthropic', 'Claude Opus 4', '2025-05-22', 6.3, false],
  ['xai', 'Grok 4', '2025-07-09', 6.8, false],
  ['openai', 'GPT-5', '2025-08-07', 7.1, false],
  ['anthropic', 'Claude Sonnet 4.5', '2025-09-29', 7.3, false],
  ['google', 'Gemini 3 Pro', '2025-11-18', 7.8, false],
  ['meta', 'Llama 4 Behemoth', '2026-02-10', null, true],
  ['anthropic', 'Claude Mythos Preview', '2026-03-24', 9.9, false],
  ['deepseek', 'DeepSeek-V4', '2026-06-30', 8.4, true],
]

const REG_EVENTS: Array<[string, RegionId, string, string, string]> = [
  // event_id, region, date, kind, description
  ['eu-ai-act-prohibited', 'EU', '2025-02-02', 'ai_act', 'EU AI Act: prohibited-practice and AI-literacy provisions apply'],
  ['eu-ai-act-gpai', 'EU', '2025-08-02', 'ai_act', 'EU AI Act: general-purpose AI model obligations apply'],
  ['eu-ai-act-high-risk', 'EU', '2026-08-02', 'ai_act', 'EU AI Act: high-risk system obligations apply (Annex III)'],
  ['us-diffusion-rule', 'US', '2025-01-13', 'export_control', 'U.S. AI diffusion rule: tiered export controls on advanced chips and model weights'],
  ['us-ca-sb53', 'US', '2026-01-01', 'state_law', 'California SB 53: frontier-model transparency and incident reporting'],
  ['us-colorado-ai-act', 'US', '2026-06-30', 'state_law', 'Colorado AI Act: duties for high-risk AI systems take effect'],
  ['cn-labelling', 'CN', '2025-09-01', 'licensing', 'China: mandatory labelling of AI-generated content; service registration continues'],
  ['cn-export-response', 'CN', '2025-10-09', 'export_control', 'China: rare-earth and equipment export licensing tightened'],
  ['uk-ai-opportunities', 'UK', '2025-01-13', 'guidance', 'UK AI Opportunities Action Plan: pro-innovation, sector regulators lead'],
  ['jp-ai-promotion-act', 'JP', '2025-05-28', 'guidance', 'Japan AI Promotion Act: principles-based, no licensing'],
  ['kr-ai-basic-act', 'KR', '2026-01-22', 'ai_act', 'Korea AI Basic Act takes effect: high-impact AI duties'],
  ['sg-genai-framework', 'SG', '2024-05-30', 'guidance', 'Singapore Model AI Governance Framework for generative AI'],
  ['in-advisory', 'IN', '2024-03-15', 'guidance', 'India MeitY advisory on deployment of under-tested models'],
  ['tw-ai-basic-act', 'TW', '2025-12-01', 'guidance', 'Taiwan AI Basic Act passed: risk-tiered guidance'],
]

// ---------- shared fixtures ----------
/** contracts §24 order: embodied and adjacent are the Phase 6 channels, output_substitution and traded_services Phase 7 */
const channelOrder: ChannelName[] = [
  'automation',
  'augmentation',
  'embodied',
  'output_substitution',
  'traded_services',
  'demand_response',
  'reinstatement',
  'demand_feedback',
  'ai_investment',
  'adjacent',
]

const occSeed: Array<[string, string, string, number, number, number]> = [
  // code, title, major_group, emp0, wage0, automatable_share
  ['43-3031', 'Bookkeeping and payroll clerks', '43', 1_480_000, 47_000, 0.64],
  ['43-4051', 'Customer service representatives', '43', 2_800_000, 39_000, 0.58],
  ['43-9021', 'Data entry keyers', '43', 160_000, 37_000, 0.81],
  ['43-6014', 'Secretaries and administrative assistants', '43', 1_900_000, 44_000, 0.49],
  ['43-3021', 'Billing and posting clerks', '43', 420_000, 43_000, 0.66],
  ['23-2011', 'Paralegals and legal assistants', '23', 350_000, 60_000, 0.55],
  ['23-1011', 'Lawyers', '23', 730_000, 145_000, 0.34],
  ['27-3091', 'Interpreters and translators', '27', 70_000, 57_000, 0.72],
  ['27-3043', 'Writers and authors', '27', 140_000, 73_000, 0.52],
  ['27-1024', 'Graphic designers', '27', 260_000, 58_000, 0.47],
  ['15-1252', 'Software developers', '15', 1_600_000, 130_000, 0.46],
  ['15-1232', 'Computer user support specialists', '15', 690_000, 59_000, 0.51],
  ['15-2051', 'Data scientists', '15', 200_000, 108_000, 0.42],
  ['15-1211', 'Computer systems analysts', '15', 510_000, 103_000, 0.44],
  ['13-2011', 'Accountants and auditors', '13', 1_450_000, 79_000, 0.56],
  ['13-2051', 'Financial analysts', '13', 330_000, 96_000, 0.5],
  ['13-1071', 'Human resources specialists', '13', 780_000, 65_000, 0.39],
  ['13-1161', 'Market research analysts', '13', 830_000, 68_000, 0.53],
  ['13-2072', 'Loan officers', '13', 320_000, 66_000, 0.48],
  ['41-3091', 'Sales representatives, services', '41', 1_100_000, 62_000, 0.33],
  ['41-2031', 'Retail salespersons', '41', 3_900_000, 33_000, 0.18],
  ['41-9041', 'Telemarketers', '41', 90_000, 32_000, 0.74],
  ['29-1141', 'Registered nurses', '29', 3_200_000, 86_000, 0.12],
  ['29-2010', 'Clinical laboratory technologists', '29', 340_000, 60_000, 0.28],
  ['29-1215', 'Family medicine physicians', '29', 110_000, 224_000, 0.19],
  ['31-1120', 'Home health and personal care aides', '31', 3_700_000, 32_000, 0.05],
  ['25-2021', 'Elementary school teachers', '25', 1_450_000, 63_000, 0.16],
  ['25-1099', 'Postsecondary teachers', '25', 1_300_000, 84_000, 0.24],
  ['11-3031', 'Financial managers', '11', 790_000, 156_000, 0.36],
  ['11-1021', 'General and operations managers', '11', 3_500_000, 128_000, 0.22],
  ['11-2021', 'Marketing managers', '11', 370_000, 158_000, 0.35],
  ['53-3032', 'Heavy and tractor-trailer truck drivers', '53', 2_100_000, 54_000, 0.21],
  ['53-7062', 'Laborers and material movers', '53', 3_000_000, 36_000, 0.14],
  ['47-2061', 'Construction laborers', '47', 1_000_000, 45_000, 0.06],
  ['47-2111', 'Electricians', '47', 760_000, 61_000, 0.07],
  ['51-2090', 'Assemblers and fabricators', '51', 1_200_000, 41_000, 0.17],
  ['35-3023', 'Fast food and counter workers', '35', 3_600_000, 29_000, 0.11],
  ['37-2011', 'Janitors and cleaners', '37', 2_200_000, 34_000, 0.04],
  ['33-3051', 'Police and sheriff patrol officers', '33', 680_000, 72_000, 0.08],
  ['19-3051', 'Urban and regional planners', '19', 45_000, 82_000, 0.31],
  ['53-3054', 'Taxi drivers and chauffeurs', '53', 380_000, 35_000, 0.62],
]
/**
 * Phase 6: the embodied part of each occupation's ever-automatable mass (`automatable_share`
 * includes it, contracts §20); occupations not listed have none.
 */
const EMBODIED_MASS: Record<string, number> = {
  '53-3054': 0.55,
  '53-3032': 0.15,
  '53-7062': 0.12,
  '51-2090': 0.12,
  '41-2031': 0.08,
  '35-3023': 0.08,
  '47-2061': 0.04,
  '37-2011': 0.03,
  '31-1120': 0.02,
}

// ---------- Phase 6: embodiment classes and the application catalogue (contracts §19) ----------
interface ClassCfg {
  cls: EmbodimentClass
  doublingMonths: number
  saturation: number
  /** 2025 unit price, the floor it decays towards (share of the 2025 price) and the decay time (years) */
  price2025: number
  priceFloor: number
  priceTau: number
  costPerHour2025: number
  /** U.S. deployed units in 2024 and the U.S. stock the ramp approaches; regions scale by `fleet` */
  stock2024: number
  stockMax: number
  rampMid: number
  rampK: number
  /** coverage = min(cap, stock / addressable) with addressable = stockMax / cap */
  coverageCap: number
  adjacentPerUnit: number
  /** approval path J: j0 at jStart rising linearly to jFull at jFullYear (U.S.); regions shift by `approvalLead` */
  j0: number
  jFull: number
  jStart: number
  jFullYear: number
}
const CLASS_CFG: ClassCfg[] = [
  { cls: 'driving', doublingMonths: 18, saturation: 8, price2025: 163_000, priceFloor: 0.34, priceTau: 5, costPerHour2025: 17.7, stock2024: 620, stockMax: 400_000, rampMid: 12.5, rampK: 0.9, coverageCap: 0.7, adjacentPerUnit: 0.1, j0: 0.03, jFull: 0.7, jStart: 2025, jFullYear: 2036 },
  { cls: 'manip', doublingMonths: 15, saturation: 10, price2025: 87_000, priceFloor: 0.28, priceTau: 5.5, costPerHour2025: 5.3, stock2024: 5_300, stockMax: 4_600_000, rampMid: 12.5, rampK: 1.0, coverageCap: 1, adjacentPerUnit: 0.05, j0: 0.9, jFull: 1, jStart: 2024, jFullYear: 2030 },
  { cls: 'fixed', doublingMonths: 24, saturation: 8, price2025: 65_000, priceFloor: 0.4, priceTau: 4, costPerHour2025: 1.1, stock2024: 40, stockMax: 76_000, rampMid: 9.5, rampK: 1.1, coverageCap: 1, adjacentPerUnit: 0.03, j0: 0.95, jFull: 1, jStart: 2024, jFullYear: 2030 },
  { cls: 'aerial', doublingMonths: 18, saturation: 8, price2025: 16_300, priceFloor: 0.85, priceTau: 6, costPerHour2025: 2.86, stock2024: 300, stockMax: 2_400, rampMid: 13, rampK: 0.9, coverageCap: 0.8, adjacentPerUnit: 0.05, j0: 0.02, jFull: 0.5, jStart: 2025, jFullYear: 2036 },
]

interface AppCfg {
  app_id: string
  name: string
  classes: EmbodimentClass[]
  platform: boolean
  occ_codes: string[]
  regions_first: RegionId[]
  anchor: string
  constraints: string
  provisional_profitable: string
  provisional_deployed50: string
  /** U.S. target employment 2024, the U.S. displacement path's midpoint (years after 2024), 2040 level (%) and slope */
  targetUS: number
  mid: number
  amp: number
  k: number
}
const PROV = 'spec v0.3 §A.8 catalogue (provisional timings are E, V?)'
const APPS: AppCfg[] = [
  { app_id: 'robotaxi', name: 'Robotaxis', classes: ['driving'], platform: true, occ_codes: ['53-3054', '53-3053'], regions_first: ['US', 'CN', 'SG', 'RoA'], anchor: 'paid autonomous rides per week and fleet size (public company posts); state and city permits', constraints: 'approval by city and state; production ramp; utilization', provisional_profitable: '2026-28', provisional_deployed50: '2031-35', targetUS: 767_000, mid: 13.5, amp: 6, k: 0.8 },
  { app_id: 'autonomous_trucking', name: 'Autonomous trucking', classes: ['driving'], platform: false, occ_codes: ['53-3032'], regions_first: ['US', 'CN'], anchor: 'driverless corridor launches; permits', constraints: 'approval by state and corridor; depot network', provisional_profitable: '2027-29', provisional_deployed50: '2033-37', targetUS: 2_100_000, mid: 13, amp: 12, k: 0.8 },
  { app_id: 'warehouse_robotics', name: 'Warehouse robotics', classes: ['manip'], platform: false, occ_codes: ['53-7062', '53-7064', '53-7065', '53-7051'], regions_first: ['US', 'CN', 'JP', 'KR', 'EU'], anchor: 'robot installations (IFR aggregates); retailer disclosures', constraints: 'ramp; integration; site conversion', provisional_profitable: '2025-27', provisional_deployed50: '2030-34', targetUS: 3_000_000, mid: 11.5, amp: 16, k: 0.8 },
  { app_id: 'retail_checkout_shelf', name: 'Retail checkout and shelf automation', classes: ['fixed', 'manip'], platform: false, occ_codes: ['41-2011', '53-7065', '41-2031'], regions_first: ['US', 'UK', 'EU', 'JP'], anchor: 'retailer disclosures', constraints: 'shrink and customer acceptance', provisional_profitable: '2025-27', provisional_deployed50: '2030-34', targetUS: 3_900_000, mid: 11, amp: 9, k: 0.8 },
]
void PROV

// ---------- Phase 7: content categories, traded services and the non-embodied catalogue rows (contracts §23–24) ----------
interface ContentCfg {
  id: string
  /** anchored 2024Q1 AI share (%) and the 2040 central level; midpoint (years after 2024) and slope of the path */
  share0: number
  share2040: number
  mid: number
  k: number
  /** 2040 consumption relative to baseline (own-price response, capped at 1.5) and the midpoint of its path (years after 2024) */
  ratio2040: number
  ratioMid: number
  /** 2024 U.S. consumption at baseline prices, $bn per year */
  usConsumptionBn: number
}
const CONTENT_CATS: ContentCfg[] = [
  // video and music: the volume response leads the AI share, so human output grows for most of the horizon
  { id: 'video', share0: 0.5, share2040: 8.5, mid: 9, k: 0.7, ratio2040: 1.12, ratioMid: 7, usConsumptionBn: 120 },
  { id: 'music', share0: 1, share2040: 14, mid: 8.5, k: 0.7, ratio2040: 1.18, ratioMid: 7, usConsumptionBn: 30 },
  { id: 'text', share0: 2, share2040: 26, mid: 6, k: 0.8, ratio2040: 1.26, ratioMid: 6, usConsumptionBn: 60 },
  { id: 'image_design', share0: 5, share2040: 44, mid: 5, k: 0.9, ratio2040: 1.5, ratioMid: 5, usConsumptionBn: 40 },
  { id: 'translation_voice', share0: 15, share2040: 72, mid: 3.5, k: 1.0, ratio2040: 1.5, ratioMid: 3.5, usConsumptionBn: 15 },
  { id: 'advertising', share0: 3, share2040: 28, mid: 6, k: 0.8, ratio2040: 1.43, ratioMid: 5.5, usConsumptionBn: 80 },
]
/** AI content price relative to the human price (distribution and curation dominate the consumer price) */
const AI_PRICE_RATIO = 0.05
/** export-serving FTE by region (spec v0.3 §A.5.3; the EU stock is Eastern members' back offices) */
const EXPORT_SERVING_FTE: Partial<Record<RegionId, number>> = { EU: 180_000, IN: 3_790_259, RoA: 1_345_000 }

interface OtherAppCfg {
  app_id: string
  name: string
  family: 'output' | 'traded' | 'software'
  classes: string[]
  occ_codes: string[]
  regions_first: string[]
  anchor: string
  constraints: string
  provisional_profitable: string
  provisional_deployed50: string
  targetUS: number
  /** traded rows: 2040 displacement (%) of the exporters' target workers; software rows: the U.S. path's midpoint, 2040 level and slope */
  exporters?: Partial<Record<RegionId, number>>
  mid?: number
  amp?: number
  k?: number
}
const OTHER_APPS: OtherAppCfg[] = [
  { app_id: 'generative_video', name: 'Generative video', family: 'output', classes: ['video'], occ_codes: ['27-1014', '27-2012', '27-4011', '27-4031', '27-4032'], regions_first: ['global'], anchor: 'AI-generated share of new uploads and releases; guild agreements', constraints: 'quality gap; authenticity premium; licensing regime', provisional_profitable: '2027-30', provisional_deployed50: '2032-38', targetUS: 405_000 },
  { app_id: 'generative_music', name: 'Generative music', family: 'output', classes: ['music'], occ_codes: ['27-2041', '27-2042'], regions_first: ['global'], anchor: 'AI-generated share of streaming uploads; label licensing deals', constraints: 'authenticity premium; licensing regime; platform policy', provisional_profitable: '2026-28', provisional_deployed50: '2031-36', targetUS: 190_000 },
  { app_id: 'generative_text', name: 'Generative text', family: 'output', classes: ['text'], occ_codes: ['27-3023', '27-3041', '27-3042', '27-3043'], regions_first: ['US', 'UK', 'EU'], anchor: 'AI-generated share of new titles and articles', constraints: 'authenticity premium; discoverability', provisional_profitable: '2025-27', provisional_deployed50: '2029-34', targetUS: 291_000 },
  { app_id: 'generative_image_design', name: 'Generative image and design', family: 'output', classes: ['image_design'], occ_codes: ['27-1024', '27-1021', '27-4021'], regions_first: ['US', 'CN', 'EU'], anchor: 'stock-image and design-platform AI share; agency disclosures', constraints: 'licensing regime; brand safety', provisional_profitable: '2024-26', provisional_deployed50: '2028-32', targetUS: 430_000 },
  { app_id: 'machine_translation_voice', name: 'Machine translation and voice', family: 'output', classes: ['translation_voice'], occ_codes: ['27-3091'], regions_first: ['global'], anchor: 'localization-industry AI share; dubbing disclosures', constraints: 'quality for high-stakes text; regulatory acceptance', provisional_profitable: '2024-26', provisional_deployed50: '2027-30', targetUS: 70_000 },
  { app_id: 'generative_advertising', name: 'Generative advertising creative', family: 'output', classes: ['advertising'], occ_codes: ['27-1024', '27-3043', '13-1161'], regions_first: ['US', 'UK', 'CN'], anchor: 'agency and platform AI-creative share', constraints: 'brand safety; platform policy', provisional_profitable: '2025-27', provisional_deployed50: '2029-33', targetUS: 520_000 },
  { app_id: 'ai_customer_service', name: 'AI customer service and back office', family: 'traded', classes: ['bpo'], occ_codes: ['43-3021', '43-3031', '43-4051', '43-4171', '43-9061'], regions_first: ['IN', 'RoA', 'US'], anchor: 'BPO revenue growth and headcount; deflection disclosures', constraints: 'deflection rates; regulation of automated decisions', provisional_profitable: '2025-27', provisional_deployed50: '2029-33', targetUS: 8_530_000, exporters: { IN: 0.9, RoA: 0.8 }, mid: 9, k: 0.7 },
  { app_id: 'ai_it_services', name: 'AI coding agents in IT services', family: 'traded', classes: ['it_services'], occ_codes: ['15-1211', '15-1232', '15-1244', '15-1252', '15-1299'], regions_first: ['IN', 'US'], anchor: 'IT services export growth and headcount', constraints: 'client acceptance; contract structures', provisional_profitable: '2025-27', provisional_deployed50: '2029-33', targetUS: 3_370_000, exporters: { IN: 7, RoA: 0.5 }, mid: 8.5, k: 0.75 },
  { app_id: 'ai_tutoring_education', name: 'AI tutoring', family: 'software', classes: [], occ_codes: ['25-3021', '25-3041', '25-9045'], regions_first: ['US', 'IN', 'CN'], anchor: 'adoption in districts and platforms', constraints: 'procurement; evidence of efficacy', provisional_profitable: '2026-29', provisional_deployed50: '2032-38', targetUS: 1_600_000, mid: 8, amp: 6.3, k: 0.7 },
  { app_id: 'ai_diagnostics', name: 'AI diagnostics and triage', family: 'software', classes: [], occ_codes: ['29-2010', '29-1215', '29-2034'], regions_first: ['US', 'UK', 'CN'], anchor: 'FDA-cleared devices; reimbursement codes', constraints: 'liability; approval; reimbursement', provisional_profitable: '2027-30', provisional_deployed50: '2033-38', targetUS: 560_000, mid: 10, amp: 4.5, k: 0.7 },
  { app_id: 'ai_legal_research', name: 'AI legal research and drafting', family: 'software', classes: [], occ_codes: ['23-2011', '23-1011'], regions_first: ['US', 'UK'], anchor: 'law-firm adoption surveys; court filings', constraints: 'professional rules; verification', provisional_profitable: '2025-27', provisional_deployed50: '2029-33', targetUS: 1_080_000, mid: 7, amp: 9, k: 0.8 },
]

// ---------- states from Natural Earth ----------
interface NeFeature {
  type: 'Feature'
  properties: Record<string, unknown>
  geometry: GeoJSON.Geometry
}
const ne = JSON.parse(readFileSync(rawGeo, 'utf8')) as { features: NeFeature[] }
const usFeatures = ne.features.filter(
  (f) => f.properties.iso_a2 === 'US' && String(f.properties.fips ?? '').startsWith('US'),
)
if (usFeatures.length !== 51) throw new Error(`expected 51 US features, got ${usFeatures.length}`)

const geo: StatesGeoJSON = {
  type: 'FeatureCollection',
  features: usFeatures
    .map((f) => ({
      type: 'Feature' as const,
      properties: {
        fips: String(f.properties.fips).replace(/^US/, ''),
        name: String(f.properties.name),
        abbrev: String(f.properties.postal),
      },
      geometry: f.geometry,
    }))
    .sort((a, b) => a.properties.fips.localeCompare(b.properties.fips)),
}

// ---------- world (admin-0) from Natural Earth ----------
const neWorld = JSON.parse(readFileSync(rawWorld, 'utf8')) as { features: NeFeature[] }
const worldGeo: WorldGeoJSON = {
  type: 'FeatureCollection',
  features: neWorld.features
    .filter((f) => f.properties.ADM0_A3 !== 'ATA')
    .map((f) => ({
      type: 'Feature' as const,
      properties: {
        iso3: String(f.properties.ADM0_A3),
        name: String(f.properties.NAME),
        region_id: assignRegion(f.properties),
      },
      geometry: f.geometry,
    }))
    .sort((a, b) => a.properties.iso3.localeCompare(b.properties.iso3)),
}
const modelledCountries = worldGeo.features.filter((f) => f.properties.region_id !== '')
for (const id of REGION_IDS)
  if (id !== 'SG' && !modelledCountries.some((f) => f.properties.region_id === id))
    throw new Error(`no Natural Earth member for region ${id}`)

/**
 * Mechanism cells (spec §7.2, v0.3 §A.7, contracts §24): demand × reinstatement × pass-through ×
 * hardware learning rate × authenticity premium = 32 cells.
 */
const CELL_AXES: [string, string][] = [
  ['bessen', 'unit_elastic'],
  ['acemoglu_low', 'historical'],
  ['passthrough_low', 'passthrough_mid'],
  ['automotive', 'electronics'],
  ['eroding', 'persistent'],
]
const cells: string[] = CELL_AXES.reduce<string[]>(
  (acc, axis) => acc.flatMap((prefix) => axis.map((v) => (prefix ? `${prefix}|${v}` : v))),
  [''],
)
if (cells.length !== 32) throw new Error(`expected 32 cells, got ${cells.length}`)

const TORNADO_PARAMS: Array<[string, string, ParamTag, number, number, number]> = [
  // param, name, tag, low, high, central
  ['P.01', 'Capability doubling time (months)', 'D', 3, 12, 6],
  ['P.04', 'Price decline per year at fixed capability', 'D', 3, 50, 10],
  ['P.20', 'Ever-automatable mass, E1 tasks', 'E', 0.5, 0.9, 0.7],
  ['P.21', 'Ever-automatable mass, E2 tasks', 'E', 0.2, 0.6, 0.4],
  ['P.34', 'Domain transfer to other cognitive tasks', 'E', 0.4, 1.0, 0.7],
  ['P.38', 'Compute capacity constraint elasticity', 'S', 0.5, 2, 1],
  ['P.40', 'Adoption intensity ceiling', 'D', 0.4, 0.9, 0.7],
  ['P.48', 'Sector adoption friction', 'D', 0.5, 2, 1],
  ['P.52', 'AI-native entrant scale', 'E', 0, 3, 1],
  ['P.53', 'Pass-through to prices', 'S', 0.3, 1.0, 0.7],
  ['P.60', 'Sector demand elasticity', 'S', 0.4, 1.4, 0.8],
  ['P.61', 'Reinstatement ratio', 'S', 0.15, 0.6, 0.4],
  ['P.63', 'Occupational attrition per quarter (%)', 'D', 1.5, 3.5, 2.5],
  ['P.74', 'Wage pass-through', 'S', 0.1, 0.6, 0.3],
  ['P.87', 'Household demand feedback', 'S', 0.2, 1.0, 0.6],
]

// ---------- the document builder ----------
function build(cfg: Cfg): ResultsDocument {
  const rand = mulberry32(42) // same seed for A and B → same state/occupation tilts
  const jitter = (amp: number) => (rand() - 0.5) * 2 * amp

  // the global frontier clock (spec §3.2), shared by every region
  const clock = curve((yr) => Math.min(20, (12 / cfg.doublingMonths) * yr))
  const shockQ = cfg.openWeightsAt ? quarters.indexOf(cfg.openWeightsAt) : -1

  /** Raw medians for one region: the U.S. path shifted by `lead` years and scaled by `amp`. */
  function regionRaw(r: RegionCfg) {
    const euLead = r.id === 'EU' ? cfg.euAdoptionLead : 0
    const lead = r.lead + euLead * 0.3
    const adoption = curve(
      (yr) => 0.04 + cfg.adoptionCeil * r.amp ** 0.3 * logistic(yr + lead, cfg.adoptionMid, 0.75),
    )
    // CN: the open-weights shock removes the domestic-actor lag from the shock quarter on
    const capLagAt = (i: number) =>
      r.id === 'CN' && shockQ >= 0 && i >= shockQ ? Math.min(r.capLag, 0.3) : r.capLag
    const capabilityIndex = clock.map((c, i) => Math.max(0, c - capLagAt(i) * Math.min(1, i / 4)))
    const gdp = rise(cfg.gdpAmp * r.gdpMul * r.amp ** 0.5, 8, 0.6, lead)
    const tfp = rise(cfg.tfpAmp * r.gdpMul * r.amp ** 0.5, 8.5, 0.6, lead)
    const employment = add(
      rise(cfg.empDrop * r.amp, 6, 0.9, lead),
      rise(cfg.empRecover * r.amp, 10, 0.8, lead),
    )
    const realWage = add(
      rise(cfg.wageDip * r.amp, 4, 1.2, lead),
      rise(cfg.wageGain * r.wageMul * r.amp ** 0.5, 9, 0.7, lead),
    )
    const priceIndex = rise(cfg.priceAmp * r.amp ** 0.5, 8, 0.6, lead)
    const nominalWage = add(realWage, priceIndex)
    const wageShare = rise(cfg.wageShareAmp * r.amp, 7.5, 0.7, lead)
    const displaced = rise(cfg.displacedAmp * r.amp * (r.employment_total / 160e6), 7, 0.65, lead)
    const aiSpend = mul(add(curve(() => 210), rise(cfg.spendAmp, 6, 0.6, lead)), r.spend)
    const horizonHours = capabilityIndex.map((idx) => Math.pow(2, idx) / 60)
    return { adoption, capabilityIndex, gdp, tfp, employment, realWage, priceIndex, nominalWage, wageShare, displaced, aiSpend, horizonHours }
  }
  type Raw = ReturnType<typeof regionRaw>

  function regionSeries(raw: Raw, r: RegionCfg): RegionSeries {
    const a = r.amp
    const capabilityIndex = bandify(raw.capabilityIndex, 6, { floor: 0, digits: 2 })
    const horizonHours = bandify(raw.horizonHours, 1, { floor: 0, digits: 2 })
    // capability horizon is 2^index: derive its band from the index band so it stays consistent
    for (const k of ['p10', 'p25', 'p50', 'p75', 'p90', 'central'] as const)
      horizonHours[k] = capabilityIndex[k]!.map((v) => round(Math.pow(2, v) / 60, 2))
    return {
      gdp_pct_vs_baseline: bandify(raw.gdp, 2.4 * a ** 0.5, { skew: 0.1 }),
      employment_pct_vs_baseline: bandify(raw.employment, 1.9 * a, { skew: -0.1 }),
      real_wage_pct_vs_baseline: bandify(raw.realWage, 1.6 * a ** 0.5),
      nominal_wage_pct_vs_baseline: bandify(raw.nominalWage, 2.0 * a ** 0.5),
      wage_share_pp_vs_baseline: bandify(raw.wageShare, 1.2 * a),
      tfp_pct_vs_baseline: bandify(raw.tfp, 1.8 * a ** 0.5),
      price_index_pct_vs_baseline: bandify(raw.priceIndex, 1.4 * a ** 0.5),
      displaced_workers_cum: bandify(raw.displaced, 3.2e6 * a * (r.employment_total / 160e6), { floor: 0, digits: 0 }),
      adoption_share: bandify(raw.adoption, 0.12, { floor: 0, ceil: 1 }),
      ai_spend_bn: bandify(raw.aiSpend, 260 * r.spend, { floor: 0, digits: 1 }),
      capability_index: capabilityIndex,
      capability_horizon_hours: horizonHours,
    }
  }

  const rawByRegion = Object.fromEntries(REGIONS.map((r) => [r.id, regionRaw(r)])) as Record<RegionId, Raw>
  const seriesByRegion = Object.fromEntries(
    REGIONS.map((r) => [r.id, regionSeries(rawByRegion[r.id], r)]),
  ) as Record<RegionId, RegionSeries>

  // U.S. medians feed the Phase 1–2 sections (states, occupations, cohorts, flows, trace)
  const us = rawByRegion.US
  const { adoption, capabilityIndex, gdp, employment, realWage, priceIndex, displaced } = us
  const S = {
    gdp: seriesByRegion.US.gdp_pct_vs_baseline,
    employment: seriesByRegion.US.employment_pct_vs_baseline,
    realWage: seriesByRegion.US.real_wage_pct_vs_baseline,
    wageShare: seriesByRegion.US.wage_share_pp_vs_baseline,
    capabilityIndex: seriesByRegion.US.capability_index,
  }

  // ----- rents by value chain (spec §6.3): stage share × global spend × regional allocation -----
  const globalSpend = quarters.map((_, i) => REGIONS.reduce((acc, r) => acc + (rawByRegion[r.id].aiSpend[i] ?? 0), 0))
  const stageShare: Record<RentStage, number> = { model: 0.25, compute: 0.35, chips: 0.25, integration: 0.15 }
  const chipsFixed: Partial<Record<RegionId, number>> = { US: 0.55, TW: 0.35, EU: 0.1 }
  /** model-margin share by actor home region; the open-weights shock moves share from the U.S. to China */
  const modelShareAt = (id: RegionId, i: number) => {
    const shock = shockQ >= 0 && i >= shockQ ? Math.min(1, (i - shockQ) / 8) : 0
    const base: Partial<Record<RegionId, number>> = { US: 0.78 - 0.18 * shock, CN: 0.16 + 0.17 * shock, EU: 0.05 + 0.01 * shock, UK: 0.01 }
    return base[id] ?? 0
  }
  function rents(r: RegionCfg): RentsByStage {
    const alloc: Record<RentStage, (i: number) => number> = {
      model: (i) => modelShareAt(r.id, i),
      compute: () => r.dataCenterShare,
      chips: () => chipsFixed[r.id] ?? 0,
      integration: (i) => (rawByRegion[r.id].aiSpend[i] ?? 0) / (globalSpend[i] || 1),
    }
    const byStage = {} as Record<RentStage, number[]>
    for (const st of RENT_STAGES)
      byStage[st] = globalSpend.map((x, i) => x * stageShare[st] * alloc[st](i))
    const total = quarters.map((_, i) => RENT_STAGES.reduce((acc, st) => acc + (byStage[st][i] ?? 0), 0))
    const band = (v: number[]) => bandify(v, Math.max(0.1, 0.22 * Math.max(...v)), { floor: 0, digits: 3 })
    return { model: band(byStage.model), compute: band(byStage.compute), chips: band(byStage.chips), integration: band(byStage.integration), total: band(total) }
  }
  for (const r of REGIONS) seriesByRegion[r.id].ai_rents_received_bn = rents(r)

  // ----- Phase 6: embodiment clocks, hardware cost, fleets, coverage, approval (spec v0.3 §A.3) -----
  /** years this run's embodied path leads (>0) the baseline run */
  const embLead = cfgA.embodiedMid - cfg.embodiedMid
  const classClock = (c: ClassCfg) =>
    curve((yr) => Math.min(c.saturation, (12 / c.doublingMonths) * Math.max(0, yr + embLead)))
  const classPrice = (c: ClassCfg) =>
    curve((yr) => c.price2025 * (c.priceFloor + (1 - c.priceFloor) * Math.exp(-Math.max(0, yr + embLead) / c.priceTau)))
  /** a deterministic series: every percentile equals the central path (the approval path J) */
  const flat = (arr: number[], digits = 3): Series => {
    const v = arr.map((x) => round(x, digits))
    return { p10: v, p25: v, p50: v, p75: v, p90: v, central: v }
  }
  const approvalPath = (c: ClassCfg, r: RegionCfg) =>
    curve((yr) => {
      const year = 2024 + yr + r.approvalLead
      const f = Math.min(1, Math.max(0, (year - c.jStart) / (c.jFullYear - c.jStart)))
      return c.j0 + (c.jFull - c.j0) * f
    })
  function embodiedFor(r: RegionCfg) {
    const fleet_stock: Partial<Record<EmbodimentClass, Series>> = {}
    const coverage: Partial<Record<EmbodimentClass, Series>> = {}
    const approval_share: Partial<Record<EmbodimentClass, Series>> = {}
    const adjacent = quarters.map(() => 0)
    const capex = quarters.map(() => 0)
    for (const c of CLASS_CFG) {
      const J = approvalPath(c, r)
      const ramp = curve((yr) => logistic(yr + embLead, c.rampMid, c.rampK) - logistic(embLead, c.rampMid, c.rampK))
      const stock = ramp.map((f, i) => r.fleet * (c.stock2024 + (c.stockMax - c.stock2024) * f * ((J[i] ?? 0) / c.jFull)))
      const addressable = (c.stockMax * r.fleet) / c.coverageCap
      const cov = stock.map((v) => Math.min(c.coverageCap, v / addressable))
      const price = classPrice(c)
      for (let i = 0; i < N; i++) {
        adjacent[i] = (adjacent[i] ?? 0) + (stock[i] ?? 0) * c.adjacentPerUnit
        const delivered = Math.max(0, (stock[i] ?? 0) - (stock[i - 1] ?? stock[i] ?? 0))
        capex[i] = (capex[i] ?? 0) + (delivered * 4 * (price[i] ?? 0)) / 1e9
      }
      fleet_stock[c.cls] = bandify(stock, 0.35 * Math.max(1, ...stock), { floor: 0, digits: 0, loose: true })
      coverage[c.cls] = bandify(cov, 0.3 * c.coverageCap, { floor: 0, ceil: c.coverageCap, digits: 3, loose: true })
      approval_share[c.cls] = flat(J)
    }
    const share = rise(cfg.embodiedAmp * r.amp ** 0.5, cfg.embodiedMid, 0.75, r.lead + 0.3 * r.approvalLead)
    const underemployed = rise(9_000 * r.fleet, cfg.embodiedMid + 0.5, 0.8, r.lead)
    const hoursCut = rise(32_000 * r.fleet, cfg.embodiedMid + 0.5, 0.8, r.lead)
    const out: Partial<RegionSeries> = {
      embodied_displacement_share: bandify(share, 2.0 * r.amp ** 0.5, { floor: 0, digits: 3, loose: true }),
      adjacent_jobs: bandify(adjacent, 0.3 * Math.max(1, ...adjacent), { floor: 0, digits: 0, loose: true }),
      hardware_capex_bn: bandify(capex, 0.5 * Math.max(0.01, ...capex), { floor: 0, digits: 3, loose: true }),
      underemployed_self_fte: bandify(underemployed, 0.6 * Math.max(1, ...underemployed), { floor: 0, digits: 0, loose: true }),
      hours_cut_self_cum: bandify(hoursCut, 0.6 * Math.max(1, ...hoursCut), { floor: 0, digits: 0, loose: true }),
      fleet_stock,
      coverage,
      approval_share,
      self_employed_fte_2024: Math.round(r.employment_total * 0.072),
    }
    return out
  }
  for (const r of REGIONS) Object.assign(seriesByRegion[r.id], embodiedFor(r))
  const embodiment: Partial<Record<EmbodimentClass, EmbodimentSeries>> = {}
  for (const c of CLASS_CFG) {
    const price = classPrice(c)
    embodiment[c.cls] = {
      clock: bandify(classClock(c), 1.2, { floor: 0, ceil: c.saturation, digits: 2, loose: true }),
      unit_price_usd: bandify(price, 0.25 * c.price2025, { floor: 0.1 * c.price2025, digits: 0, loose: true }),
      cost_per_hour_usd: bandify(price.map((p) => (c.costPerHour2025 * p) / c.price2025), 0.25 * c.costPerHour2025, { floor: 0.05, digits: 2, loose: true }),
    }
  }

  // ----- Phase 6: the application catalogue with per-region status (contracts §20) -----
  const firstAt = (arr: number[], thr: number) => {
    const i = arr.findIndex((v) => v >= thr)
    return i >= 0 ? (quarters[i] ?? null) : null
  }
  const applications: ApplicationEntry[] = APPS.map((a) => {
    const c = CLASS_CFG.find((x) => x.cls === a.classes[0])!
    const by_region: Record<string, ApplicationRegion> = {}
    for (const r of REGIONS) {
      const first = a.regions_first.includes(r.id)
      const lead = r.lead + (first ? 0 : -1.5) + embLead
      const J = approvalPath(c, r)
      const disp = rise(a.amp * r.amp ** 0.5 * (first ? 1 : 0.55), a.mid, a.k, lead).map((v, i) => round((v * (J[i] ?? 0)) / c.jFull, 2))
      const cov = rise(c.coverageCap, a.mid - 1.5, a.k, lead).map((v, i) => round(Math.min(c.coverageCap, (v * (J[i] ?? 0)) / c.jFull), 3))
      const target = Math.round(a.targetUS * (r.employment_total / 160e6) * (first ? 1 : 0.8))
      by_region[r.id] = {
        target_employment_2024: target,
        displacement_share: disp,
        jobs_below_baseline: disp.map((d) => round((target * d) / 100, 0)),
        coverage: cov,
        approval: J.map((v) => round(v, 3)),
        first_quarter: {
          displacement_1pct: firstAt(disp, 1),
          displacement_10pct: firstAt(disp, 10),
          coverage_50pct: firstAt(cov, 0.5),
        },
      }
    }
    return {
      app_id: a.app_id,
      name: a.name,
      family: 'embodied',
      classes: a.classes,
      platform: a.platform,
      occ_codes: a.occ_codes,
      regions_first: a.regions_first,
      anchor: a.anchor,
      constraints: a.constraints,
      provisional_profitable: a.provisional_profitable,
      provisional_deployed50: a.provisional_deployed50,
      by_region,
    }
  })

  // ----- Phase 7: output substitution by content category and traded services (contracts §24) -----
  /** a normalized S-curve, 0 in 2024Q1 and 1 in 2040Q4, shifted `lead` years earlier */
  const unitRise = (mid: number, k: number, lead: number) => {
    const r = rise(1, mid, k, lead)
    const end = r[N - 1] || 1
    return r.map((v) => v / end)
  }
  const contentShare = (c: ContentCfg, lead: number) =>
    unitRise(c.mid, c.k, lead).map((u) => c.share0 + (c.share2040 - c.share0) * u)
  const contentRatio = (c: ContentCfg, lead: number) =>
    unitRise(c.ratioMid, c.k, lead).map((u) => Math.min(1.5, 1 + (c.ratio2040 - 1) * u))
  function contentFor(r: RegionCfg) {
    const lead = cfg.contentLead + 0.3 * r.lead
    const ai_content_share: Record<string, Series> = {}
    const content_consumption_ratio: Record<string, Series> = {}
    const revenue = quarters.map(() => 0)
    const surplus = quarters.map(() => 0)
    const gdpScale = r.gdp_bn_usd / 27_360
    for (const c of CONTENT_CATS) {
      const share = contentShare(c, lead)
      const ratio = contentRatio(c, lead)
      const cons = c.usConsumptionBn * gdpScale
      for (let i = 0; i < N; i++) {
        const sh = (share[i] ?? 0) / 100
        const q = ratio[i] ?? 1
        revenue[i] = (revenue[i] ?? 0) + cons * q * sh * AI_PRICE_RATIO
        surplus[i] = (surplus[i] ?? 0) + 0.6 * cons * (sh * (1 - AI_PRICE_RATIO) * 0.6 + (q - 1) * 0.5)
      }
      ai_content_share[c.id] = bandify(share, 0.3 * c.share2040 * (1 - c.share2040 / 100) + 2, { floor: 0, ceil: 100, digits: 2, loose: true })
      content_consumption_ratio[c.id] = bandify(ratio, 0.35 * (c.ratio2040 - 1), { floor: 1, ceil: 1.5, digits: 3, loose: true })
    }
    const out: Partial<RegionSeries> = {
      ai_content_share,
      content_consumption_ratio,
      ai_content_revenue_bn: bandify(revenue, 0.3 * Math.max(0.01, ...revenue), { floor: 0, digits: 3, loose: true }),
      consumer_surplus_proxy_bn: bandify(surplus, 0.3 * Math.max(0.01, ...surplus), { floor: 0, digits: 2, loose: true }),
    }
    return out
  }
  /** traded-services displacement of the region's employment (%): exporters only (spec v0.3 §A.5.3) */
  const tradedShare = (r: RegionCfg) =>
    r.id === 'IN' ? rise(cfg.tradedAmp, 10, 0.7) : r.id === 'RoA' ? rise(0.25 * cfg.tradedAmp, 10.5, 0.7) : quarters.map(() => 0)
  for (const r of REGIONS) {
    Object.assign(seriesByRegion[r.id], contentFor(r))
    const ts = tradedShare(r)
    const tsMax = Math.max(...ts)
    // importers read exactly zero at every percentile (contracts §24)
    seriesByRegion[r.id].traded_services_displacement_share = tsMax > 0 ? bandify(ts, 0.4 * tsMax, { floor: 0, digits: 4, loose: true }) : flat(ts, 4)
  }

  // ----- Phase 7: output, traded and software catalogue rows (contracts §24) -----
  const zeros = quarters.map(() => 0)
  const emptyGates = () => ({ displacement_1pct: null, displacement_10pct: null, coverage_50pct: null })
  const otherApplications: ApplicationEntry[] = OTHER_APPS.map((a) => {
    const by_region: Record<string, ApplicationRegion> = {}
    for (const r of REGIONS) {
      const target = Math.round(a.targetUS * (r.employment_total / 160e6))
      if (a.family === 'output') {
        // human output lost vs baseline, 1 − (1 − s^AI)·Q/Q0 with the frozen baseline holding the
        // anchored 2024 share, so the path starts at 0; negative when the category grows; coverage = s^AI
        const c = CONTENT_CATS.find((x) => x.id === a.classes[0])!
        const lead = cfg.contentLead + 0.3 * r.lead
        const share = contentShare(c, lead)
        const ratio = contentRatio(c, lead)
        const human0 = 1 - c.share0 / 100
        const disp = share.map((sh, i) => round((1 - ((1 - sh / 100) * (ratio[i] ?? 1)) / human0) * 100, 2))
        const cov = share.map((sh) => round(sh / 100, 3))
        by_region[r.id] = {
          target_employment_2024: target,
          displacement_share: disp,
          jobs_below_baseline: disp.map((d) => round((target * d) / 100, 0)),
          coverage: cov,
          approval: zeros,
          first_quarter: { displacement_1pct: firstAt(disp, 1), displacement_10pct: firstAt(disp, 10), coverage_50pct: firstAt(cov, 0.5) },
        }
      } else if (a.family === 'traded') {
        const amp = (a.exporters?.[r.id] ?? 0) * (cfg.tradedAmp / cfgA.tradedAmp)
        const disp = amp ? rise(amp, a.mid ?? 9, a.k ?? 0.7).map((v) => round(v, 3)) : zeros
        by_region[r.id] = {
          target_employment_2024: target,
          displacement_share: disp,
          jobs_below_baseline: disp.map((d) => round((target * d) / 100, 0)),
          coverage: zeros,
          approval: zeros,
          first_quarter: amp ? { displacement_1pct: firstAt(disp, 1), displacement_10pct: firstAt(disp, 10), coverage_50pct: null } : emptyGates(),
        }
      } else {
        const disp = rise((a.amp ?? 5) * r.amp ** 0.5, a.mid ?? 8, a.k ?? 0.7, r.lead).map((v) => round(Math.max(0, v), 2))
        by_region[r.id] = {
          target_employment_2024: target,
          displacement_share: disp,
          jobs_below_baseline: disp.map((d) => round((target * d) / 100, 0)),
          coverage: zeros,
          approval: zeros,
          first_quarter: { displacement_1pct: firstAt(disp, 1), displacement_10pct: firstAt(disp, 10), coverage_50pct: null },
        }
      }
    }
    return {
      app_id: a.app_id,
      name: a.name,
      family: a.family,
      classes: a.classes,
      platform: false,
      occ_codes: a.occ_codes,
      regions_first: a.regions_first,
      anchor: a.anchor,
      constraints: a.constraints,
      provisional_profitable: a.provisional_profitable,
      provisional_deployed50: a.provisional_deployed50,
      by_region,
    }
  })
  applications.push(...otherApplications)

  // ----- regions, world (members carry the region composition) -----
  const regions: RegionInfo[] = REGIONS.map((r) => ({
    region_id: r.id,
    name: r.name,
    employment_total: r.employment_total,
    gdp_bn_usd: r.gdp_bn_usd,
    data_flags: r.flags,
  }))
  const slim = (s: Series) => ({
    p10: s.p10!.map((v) => round(v, 2)),
    p50: s.p50.map((v) => round(v, 2)),
    p90: s.p90!.map((v) => round(v, 2)),
  })
  const world: WorldEntry[] = modelledCountries.map((f) => {
    const rs = seriesByRegion[f.properties.region_id as RegionId]
    return {
      iso3: f.properties.iso3,
      name: f.properties.name,
      region_id: f.properties.region_id,
      employment_pct_vs_baseline: slim(rs.employment_pct_vs_baseline),
      real_wage_pct_vs_baseline: slim(rs.real_wage_pct_vs_baseline),
    }
  })

  // ----- supply timeline (spec §3) -----
  const releases: SupplyRelease[] = RELEASES.map(([actor_id, model, date, capability_index, open_weights]) => {
    const a = ACTORS.find((x) => x.actor_id === actor_id)!
    return { actor_id, name: a.name, region_id: a.region_id, model, date, quarter: quarterOf(date), capability_index, open_weights }
  })
  if (cfg.openWeightsAt) {
    const i = quarters.indexOf(cfg.openWeightsAt)
    const y = cfg.openWeightsAt.slice(0, 4)
    const mth = (Number(cfg.openWeightsAt.slice(5)) - 1) * 3 + 2
    releases.push({
      actor_id: 'deepseek', name: 'DeepSeek', region_id: 'CN', model: 'DeepSeek open frontier (scenario shock)',
      date: `${y}-${String(mth).padStart(2, '0')}-15`, quarter: cfg.openWeightsAt, capability_index: round(clock[i] ?? 0, 2), open_weights: true,
    })
  }
  // synthetic future cadence so the strip continues past the transcribed history
  const futureRand = mulberry32(7)
  for (let yr = 2027; yr <= 2040; yr++)
    for (const [actor, k] of [['openai', 0], ['anthropic', 1], ['google', 2], ['deepseek', 3], ['meta', 4]] as const) {
      if (futureRand() < 0.6) continue
      const mth = 1 + Math.floor(futureRand() * 12)
      const date = `${yr}-${String(mth).padStart(2, '0')}-${String(5 + k * 5).padStart(2, '0')}`
      const qi = quarters.indexOf(quarterOf(date))
      const a = ACTORS.find((x) => x.actor_id === actor)!
      const lag = a.region_id === 'CN' ? (shockQ >= 0 && qi >= shockQ ? 0.2 : 1.4) : a.posture === 'closed' ? 0 : 0.8
      releases.push({ actor_id: actor, name: a.name, region_id: a.region_id, model: `${a.name} ${yr} model`, date, quarter: quarterOf(date), capability_index: round(Math.max(0, (clock[qi] ?? 0) - lag), 2), open_weights: a.posture !== 'closed' })
    }
  releases.sort((a, b) => a.date.localeCompare(b.date))

  const regulatory_events: RegulatoryEvent[] = REG_EVENTS.map(([event_id, region, date, kind, description]) => {
    const d = event_id === 'eu-ai-act-high-risk' && cfg.euAiActDelayYears ? `${Number(date.slice(0, 4)) + cfg.euAiActDelayYears}${date.slice(4)}` : date
    return { event_id, region, date: d, quarter: quarterOf(d), kind, description: cfg.euAiActDelayYears && event_id === 'eu-ai-act-high-risk' ? `${description} — delayed ${cfg.euAiActDelayYears}y in this scenario` : description }
  })

  // availability: closed U.S. actors are unavailable in China; the EU sees each closed frontier release
  // one quarter late while the GPAI code of practice beds in (through 2029); open-weights actors are
  // available everywhere
  const euDelayUntil = quarters.indexOf('2030Q1')
  const frontierQuarters = new Set(
    releases
      .filter((r) => CLOSED_US.includes(r.actor_id) && r.capability_index != null)
      .map((r) => quarters.indexOf(r.quarter))
      .filter((i) => i < euDelayUntil),
  )
  const availability: SupplySection['availability'] = {}
  for (const r of REGIONS) {
    availability[r.id] = {}
    for (const a of ACTORS) {
      availability[r.id]![a.actor_id] = quarters.map((_, i) => {
        if (a.posture !== 'closed') return 1
        if (r.id === 'CN') return 0
        if (r.id === 'EU' && frontierQuarters.has(i)) return 0
        return 1
      })
    }
  }
  const market_share: SupplySection['market_share'] = {}
  for (const r of REGIONS) {
    market_share[r.id] = {}
    const rows = ACTORS.map((a) => {
      const avail = availability[r.id]![a.actor_id]!
      return quarters.map((_, i) => {
        const shock = shockQ >= 0 && i >= shockQ ? Math.min(1, (i - shockQ) / 8) : 0
        let w = a.region_id === r.id ? a.home : a.abroad
        if (a.actor_id === 'deepseek') w *= 1 + 2.5 * shock
        if (a.region_id === 'US' && a.posture === 'closed') w *= 1 - 0.3 * shock
        return w * (avail[i] ?? 1)
      })
    })
    const sums = quarters.map((_, i) => rows.reduce((acc, row) => acc + (row[i] ?? 0), 0))
    ACTORS.forEach((a, k) => {
      market_share[r.id]![a.actor_id] = { central: rows[k]!.map((v, i) => round(v / (sums[i] || 1), 3)) }
    })
  }
  // frontier price drifts down slowly; price at fixed capability falls 10×/yr (P.04) to a cost floor that halves yearly (P.06)
  const priceFrontier = curve((yr) => Math.max(1.5 * Math.pow(0.93, yr), 15 * Math.pow(0.7, yr)))
  const priceFixed = curve((yr) => Math.max(0.06 * Math.pow(0.75, yr), 15 * Math.pow(0.1, yr)))
  if (shockQ >= 0)
    for (let i = shockQ; i < N; i++) {
      priceFrontier[i] = (priceFrontier[i] ?? 0) * 0.25
      priceFixed[i] = (priceFixed[i] ?? 0) * 0.25
    }
  const supply: SupplySection = {
    clock: S.capabilityIndex,
    horizon_hours: seriesByRegion.US.capability_horizon_hours,
    regional_capability: Object.fromEntries(
      REGIONS.map((r) => [r.id, { central: rawByRegion[r.id].capabilityIndex.map((v) => round(v, 2)) }]),
    ) as Record<string, CentralSeries>,
    price_frontier_usd_per_mtok: { central: priceFrontier.map((v) => round(v, 4)) },
    price_fixed_capability_usd_per_mtok: { central: priceFixed.map((v) => round(v, 5)) },
    releases,
    regulatory_events,
    availability,
    market_share,
    embodiment,
  }

  // channels for employment (contributions sum to the median exactly)
  const empRaw: Record<ChannelName, number[]> = {
    automation: rise(cfg.empDrop * 1.6, 6, 0.9),
    augmentation: rise(0.5, 5, 0.9),
    embodied: rise(-0.28 * cfg.embodiedAmp, cfg.embodiedMid, 0.8),
    output_substitution: rise(-0.14, 6.5, 0.85, cfg.contentLead),
    traded_services: rise(-0.01, 9, 0.7),
    demand_response: rise(0.9, 7, 0.8),
    reinstatement: rise(1.1, 10, 0.7),
    demand_feedback: rise(0.7, 8, 0.7),
    ai_investment: rise(0.4, 5, 0.9),
    adjacent: rise(0.22, cfg.embodiedMid - 0.5, 0.8),
  }
  const gdpRaw: Record<ChannelName, number[]> = {
    automation: rise(3.4, 7, 0.65),
    augmentation: rise(1.6, 6, 0.8),
    embodied: rise(0.9, cfg.embodiedMid, 0.8),
    output_substitution: rise(0.28, 6.5, 0.85, cfg.contentLead),
    traded_services: rise(0.02, 9, 0.7),
    demand_response: rise(-0.9, 7.5, 0.7),
    reinstatement: rise(0.8, 10, 0.7),
    demand_feedback: rise(0.6, 8, 0.7),
    ai_investment: rise(1.1, 5, 0.9),
    adjacent: rise(0.15, cfg.embodiedMid - 0.5, 0.8),
  }
  /** keeps the `fixed` channels at their raw values and scales the others so the stack sums to `target` */
  function rescale(raw: Record<ChannelName, number[]>, fixed: ChannelName[], target: number[]) {
    const out: Partial<Record<ChannelName, number[]>> = {}
    for (const c of channelOrder) out[c] = []
    for (let i = 0; i < N; i++) {
      const held = fixed.reduce((acc, c) => acc + (raw[c][i] ?? 0), 0)
      const restRaw = channelOrder
        .filter((c) => !fixed.includes(c))
        .reduce((acc, c) => acc + (raw[c][i] ?? 0), 0)
      const k = restRaw > 1e-9 ? ((target[i] ?? 0) - held) / restRaw : 0
      for (const c of channelOrder)
        out[c]!.push(round(fixed.includes(c) ? (raw[c][i] ?? 0) : (raw[c][i] ?? 0) * k, 4))
    }
    return out
  }

  // occupations
  const occupations: OccupationResult[] = occSeed.map(([code, title, mg, emp0, wage0, auto], i) => {
    // Phase 6: the embodied mass runs on the late embodied path; the software mass as before
    const embMass = EMBODIED_MASS[code] ?? 0
    const swMass = Math.max(0, auto - embMass)
    const lag = 5.5 + jitter(2) + (auto > 0.5 ? -1 : 1)
    const ceiling = swMass * (0.45 + 0.3 * rand()) * (cfg.displacedAmp / cfgA.displacedAmp)
    const k = 0.7 + 0.4 * rand()
    const dispSw = curve((yr) =>
      Math.max(0, ceiling * (logistic(yr, lag + 3, k) - logistic(0, lag + 3, k))),
    )
    const embCeiling = embMass * (0.35 + 0.25 * rand()) * (cfg.embodiedAmp / cfgA.embodiedAmp)
    const dispEmb = rise(embCeiling, cfg.embodiedMid + 0.5, 0.8).map((v) => round(Math.max(0, v), 4))
    const disp = add(dispSw, dispEmb)
    const emp = disp.map((d, j) => -d * 100 * 0.85 + 0.35 * (gdp[j] ?? 0) * (1 - auto))
    const wage = disp.map((d, j) => (realWage[j] ?? 0) * (1.2 - auto) - d * 100 * 0.25)
    // Phase 3: central-only paths per non-U.S. region = the U.S. path shifted by the region's lead and scaled by its amp
    const by_region: Record<string, OccupationByRegion> = {}
    for (const r of REGIONS) {
      if (r.id === 'US') continue
      const shift = Math.round(-r.lead * 4)
      const at = (arr: number[], j: number) => arr[Math.max(0, Math.min(N - 1, j - shift))] ?? 0
      by_region[r.id] = {
        displacement: { central: quarters.map((_, j) => round(at(disp, j) * r.amp, 4)) },
        employment_pct_vs_baseline: { central: quarters.map((_, j) => round(at(emp, j) * r.amp, 4)) },
      }
    }
    return {
      by_region,
      occ_code: code,
      title,
      cluster_id: `c${String(i + 1).padStart(3, '0')}`,
      major_group: mg,
      emp0,
      wage0,
      automatable_share: round(auto, 3),
      exposure_beta: round(Math.min(0.98, auto + 0.08 + jitter(0.05)), 3),
      displacement: bandify(disp, 0.06 + 0.1 * auto, { floor: 0 }),
      automatable_share_embodied: round(embMass, 3),
      displacement_embodied: { central: dispEmb },
      employment_pct_vs_baseline: bandify(emp, 1.5 + 3 * auto),
      real_wage_pct_vs_baseline: bandify(wage, 1.2 + 1.5 * auto),
    }
  })

  // states
  const states: StateResult[] = geo.features.map((f) => {
    const { fips, name } = f.properties
    const tilt = 0.55 + rand() * 0.9
    const lead = jitter(1.2)
    const share = 0.004 + rand() * 0.06
    const emp = curve(
      (yr) =>
        tilt *
        (cfg.empDrop * (logistic(yr - lead, 6, 0.9) - logistic(0, 6, 0.9)) +
          cfg.empRecover * (logistic(yr - lead, 10, 0.8) - logistic(0, 10, 0.8))),
    )
    const wage = realWage.map((v, i) => v * (2 - tilt) + 0.15 * (emp[i] ?? 0))
    const disp = displaced.map((v) => v * share * tilt)
    return {
      fips,
      name,
      employment_pct_vs_baseline: bandify(emp, 1.9 * tilt),
      real_wage_pct_vs_baseline: bandify(wage, 1.6),
      displaced_workers_cum: bandify(disp, 3.2e6 * share * tilt, { floor: 0, digits: 0 }),
    }
  })

  // structural ensemble: 32 cell medians per headline metric
  const headline: Record<HeadlineMetric, Series> = {
    employment_pct_vs_baseline: S.employment,
    gdp_pct_vs_baseline: S.gdp,
    real_wage_pct_vs_baseline: S.realWage,
    wage_share_pp_vs_baseline: S.wageShare,
  }
  // per-metric multiplicative effect of choosing variant B on each axis
  const axisEffect: Record<HeadlineMetric, [number, number, number, number, number]> = {
    employment_pct_vs_baseline: [0.22, -0.35, 0.1, -0.08, 0.05],
    gdp_pct_vs_baseline: [0.12, 0.08, 0.18, 0.05, -0.03],
    real_wage_pct_vs_baseline: [0.1, 0.25, 0.6, 0.04, -0.02],
    wage_share_pp_vs_baseline: [0.05, 0.1, -0.3, -0.03, 0.02],
  }
  const structural: Partial<Record<HeadlineMetric, StructuralSection>> = {}
  for (const m of HEADLINE_METRICS) {
    const base = headline[m].p50
    const by_cell: Record<string, { p50: number[] }> = {}
    cells.forEach((id, ci) => {
      const nAxes = CELL_AXES.length
      const bits = CELL_AXES.map((_, a) => (ci >> (nAxes - 1 - a)) & 1)
      const eff = axisEffect[m]
      let f = 1
      for (let a = 0; a < nAxes; a++) if (bits[a]) f *= 1 + (eff[a] ?? 0)
      // a small time-varying wobble so cells are not exact multiples
      by_cell[id] = {
        p50: base.map((v, i) => round(v * f + 0.05 * Math.sin(i / 7 + ci) * Math.abs(v) * 0.5)),
      }
    })
    const spread: StructuralSection['spread'] = {}
    for (const [qi, qk] of [
      [Q2030, '2030Q4'],
      [Q2040, '2040Q4'],
    ] as const) {
      const meds = cells.map((id) => by_cell[id]!.p50[qi]!)
      const pooled = (headline[m].p90![qi] ?? 0) - (headline[m].p10![qi] ?? 0)
      spread[qk] = {
        parametric_pp: round(pooled * 0.72, 2),
        structural_pp: round(Math.max(...meds) - Math.min(...meds), 2),
      }
    }
    structural[m] = { by_cell, spread }
  }

  // confidence (spec §7.3)
  const conf = (
    level: Confidence['level'],
    sign_share: number,
    cells_agree: boolean,
    flip: string[],
  ): Confidence => ({ level, sign_share, cells_agree, flip_params: flip })
  const confidence: ResultsDocument['confidence'] = {
    employment_pct_vs_baseline: {
      '2030Q4': conf('medium', 0.84, true, ['P.61']),
      '2040Q4': conf('low', 0.66, false, ['P.61', 'P.60']),
    },
    gdp_pct_vs_baseline: {
      '2030Q4': conf('high', 0.97, true, []),
      '2040Q4': conf('high', 0.99, true, []),
    },
    real_wage_pct_vs_baseline: {
      '2030Q4': conf('low', 0.58, false, ['P.74', 'P.53']),
      '2040Q4': conf('medium', 0.78, true, ['P.74']),
    },
    wage_share_pp_vs_baseline: {
      '2030Q4': conf('high', 0.95, true, []),
      '2040Q4': conf('high', 0.93, true, []),
    },
  }

  // tornado at 2040Q4
  const tornado: Partial<Record<HeadlineMetric, TornadoRow[]>> = {}
  for (const m of HEADLINE_METRICS) {
    const v = headline[m].p50[Q2040] ?? 0
    const scale = Math.max(0.4, Math.abs(v))
    const rows: TornadoRow[] = TORNADO_PARAMS.map(([param, name, tag, low, high], k) => {
      const r = mulberry32(1000 + k * 17 + m.length)
      const mag = scale * (0.05 + 0.5 * r())
      const sign = r() < 0.5 ? -1 : 1
      const asym = 0.6 + 0.8 * r()
      return {
        param,
        name,
        tag,
        low,
        high,
        effect_at_low: round(v - sign * mag * asym, 3),
        effect_at_high: round(v + sign * mag, 3),
      }
    })
    rows.sort(
      (a, b) =>
        Math.abs(b.effect_at_high - b.effect_at_low) - Math.abs(a.effect_at_high - a.effect_at_low),
    )
    tornado[m] = rows
  }

  // cohorts: tilt of the national employment path + share of cumulative jobs lost
  function cohortRows(bands: string[], tilts: number[], shares: number[]): CohortRow[] {
    const sum = shares.reduce((a, b) => a + b, 0)
    return bands.map((band, i) => {
      const tilt = tilts[i] ?? 1
      const emp = employment.map((v) => v * tilt)
      const base = (shares[i] ?? 0) / sum
      // shares drift a little over time (young cohorts hit first)
      const share = curve((yr) => base * (1 + 0.15 * (tilt - 1) * Math.exp(-yr / 6)))
      return {
        band,
        employment_pct_vs_baseline: bandify(emp, 1.9 * tilt),
        share_of_jobs_lost: bandify(share, 0.04 * Math.sqrt(base * 4), { floor: 0, ceil: 1 }),
      }
    })
  }
  const cohorts: ResultsDocument['cohorts'] = {
    age: cohortRows(['16-24', '25-44', '45-54', '55+'], [1.7, 1.05, 0.7, 0.85], [0.18, 0.46, 0.2, 0.16]),
    education: cohortRows(
      ['lt_hs', 'hs', 'some_college', 'ba_plus'],
      [0.45, 0.8, 1.1, 1.35],
      [0.05, 0.2, 0.3, 0.45],
    ),
    income_decile: cohortRows(
      Array.from({ length: 10 }, (_, i) => String(i + 1)),
      [0.5, 0.65, 0.85, 1.05, 1.2, 1.3, 1.35, 1.25, 1.0, 0.7],
      [0.04, 0.06, 0.08, 0.1, 0.12, 0.13, 0.14, 0.13, 0.11, 0.09],
    ),
  }

  // flows: origins (6 major groups) and destinations, cumulative
  const originGroups: Array<[string, string, number]> = [
    ['43', 'Office & admin support', 0.31],
    ['13', 'Business & finance', 0.17],
    ['15', 'Computer & math', 0.12],
    ['41', 'Sales', 0.14],
    ['23', 'Legal', 0.05],
    ['27', 'Arts, design & media', 0.06],
    ['53', 'Transportation & material moving', 0.05],
  ]
  // the embodied origin (Transportation) fills in late, on the embodied path
  const lateRaw = rise(1, cfg.embodiedMid, 0.8)
  const late = lateRaw.map((v) => v / (lateRaw[N - 1] || 1))
  const destShare: Record<FlowDestination, number> = {
    reemployed: 0.42,
    retraining: 0.14,
    unemployed: 0.16,
    exited: 0.1,
    retired: 0.1,
    unfilled_entry: 0.08,
  }
  const flows: FlowsSection = {
    origins: originGroups.map(([mg, title, share]) => ({
      major_group: mg,
      title,
      jobs_lost_cum: bandify(
        mg === '53' ? displaced.map((v, i) => v * share * (late[i] ?? 0)) : mul(displaced, share),
        3.2e6 * share,
        { floor: 0, digits: 0 },
      ),
    })),
    destinations: Object.fromEntries(
      FLOW_DESTINATIONS.map((d) => [
        d,
        bandify(
          displaced.map((v, i) => v * destShare[d] * (d === 'reemployed' ? 1 + 0.1 * logistic(t(i), 8, 0.6) : 1)),
          3.2e6 * destShare[d],
          { floor: 0, digits: 0 },
        ),
      ]),
    ) as Record<FlowDestination, Series>,
  }
  // Phase 6: the self-employed and platform margin (spec v0.3 §A.5.2), a stock of hours cut
  flows.destinations.hours_cut_self = seriesByRegion.US.hours_cut_self_cum

  // explain.trace
  const traceAt = (qi: number, m: HeadlineMetric): Trace => ({
    automatable_share: round(0.31 + 0.02 * (cfg.displacedAmp / cfgA.displacedAmp - 1), 3),
    realized_D: round(((displaced[qi] ?? 0) / 160e6) * (m === 'gdp_pct_vs_baseline' ? 1.1 : 1), 4),
    realized_U: round(0.62 * (adoption[qi] ?? 0), 3),
    adoption_emp: round((adoption[qi] ?? 0) * 0.92, 3),
    dln_unit_cost: round(-0.08 * (capabilityIndex[qi] ?? 0) * (adoption[qi] ?? 0), 3),
    q_ratio: round(1 + (gdp[qi] ?? 0) / 100, 4),
    mu: round(0.42 + 0.4 * (adoption[qi] ?? 0) * (m === 'wage_share_pp_vs_baseline' ? 1.1 : 1), 3),
    nu: round(0.15 + 0.55 * (adoption[qi] ?? 0), 3),
    price_index: round(1 + (priceIndex[qi] ?? 0) / 100, 4),
  })
  const trace: NonNullable<ResultsDocument['explain']['trace']> = {}
  for (const m of HEADLINE_METRICS)
    trace[m] = { '2030Q4': traceAt(Q2030, m), '2040Q4': traceAt(Q2040, m) }

  return {
    meta: {
      spec_version: '0.3',
      schema_version: '0.4',
      scenario_id: cfg.scenarioId,
      scenario_hash: cfg.hash,
      seed: 42,
      run_at: '2026-09-01T00:00:00Z',
      draws: 200,
      ensemble: 'all',
      cells,
      percentiles: [10, 25, 50, 75, 90],
      quarters,
      regions: REGION_IDS,
      baseline: 'no_frontier_ai_after_2023',
      data_flags: {
        occ_state: 'FIXTURE',
        occ_sector: 'FIXTURE',
        aei_anchoring: 'unavailable',
        cohorts: 'FIXTURE',
        occ_region: 'FIXTURE',
        trade_weights: 'FIXTURE',
        members: 'composition',
      },
      capability_units: 'doublings of METR 50% task horizon (minutes = 2^index)',
      // Phase 6 (contracts §20)
      headline_definition: 'FTE jobs including self-employed and platform workers (spec v0.3 §A.5.1); payroll-only employment is not separately tracked',
      channels_task_hours: { software: 0.749, emb_driving: 0.018, emb_manip: 0.201, emb_fixed: 0.016, emb_aerial: 0, none: 0.016 },
      self_employed_fte: Object.fromEntries(REGIONS.map((r) => [r.id, Math.round(r.employment_total * 0.072)])),
      embodied_on: true,
      // Phase 7 (contracts §24)
      content_categories: CONTENT_CATS.map((c) => c.id),
      export_serving_fte: Object.fromEntries(REGIONS.map((r) => [r.id, EXPORT_SERVING_FTE[r.id] ?? 0])),
    },
    series: seriesByRegion,
    regions,
    world,
    supply,
    occupations,
    states,
    channels: {
      employment_pct_vs_baseline: {
        order: channelOrder,
        contributions: rescale(empRaw, ['automation', 'embodied', 'output_substitution', 'traded_services'], S.employment.p50),
      },
      gdp_pct_vs_baseline: {
        order: channelOrder,
        contributions: rescale(gdpRaw, ['demand_response'], S.gdp.p50),
      },
    },
    explain: { notes: cfg.notes, trace, diff: cfg.diff },
    structural,
    confidence,
    tornado,
    cohorts,
    flows,
    applications,
  }
}

// ---------- levers from scenarios/schema.json ----------
interface JsonSchema {
  type?: string | string[]
  properties?: Record<string, JsonSchema>
  additionalProperties?: JsonSchema | boolean
  enum?: string[]
  minimum?: number
  maximum?: number
  default?: unknown
  description?: string
}

const LEVER_LABELS: Record<
  string,
  { label: string; unit?: string; param?: string; mechanism?: string; step?: number }
> = {
  doubling_months: {
    label: 'Capability doubling time',
    unit: 'months',
    param: 'P.01',
    step: 0.5,
    mechanism: 'Sets the global frontier clock (§3.2); shorter doubling brings every task threshold forward.',
  },
  doubling_drift_per_year: {
    label: 'Doubling-time drift per year',
    unit: 'fraction/yr',
    param: 'P.02',
    step: 0.05,
    mechanism: 'Accelerates (negative) or slows (positive) the clock each year.',
  },
  feedback_from_revenue: {
    label: 'Capability feedback from AI revenue',
    param: 'L.capability_feedback',
    mechanism: 'Reinvested AI revenue shortens the doubling time.',
  },
  robotics_doubling_months: {
    label: 'Robotics doubling time',
    unit: 'months',
    param: 'P.03',
    step: 1,
    mechanism: 'Clock for physical-modality tasks (§3.5).',
  },
  ever_automatable_scale: {
    label: 'Ever-automatable mass (scale)',
    unit: '×',
    param: 'P.20–P.22',
    step: 0.05,
    mechanism: 'Multiplies the ceiling share of tasks that can ever be automated per exposure class.',
  },
  other_cognitive: {
    label: 'Domain transfer: other cognitive tasks',
    unit: 'share',
    param: 'P.34',
    step: 0.05,
    mechanism: 'Fraction of software-task progress that transfers to non-software cognitive tasks.',
  },
  interpersonal: {
    label: 'Domain transfer: interpersonal tasks',
    unit: 'share',
    param: 'P.34',
    step: 0.05,
    mechanism: 'Fraction of software-task progress that transfers to interpersonal tasks.',
  },
  clock_saturation_doublings: {
    label: 'Clock saturation',
    unit: 'doublings',
    param: 'P.07',
    step: 1,
    mechanism: 'Capability index at which the frontier clock saturates.',
  },
  price_decline_per_year: {
    label: 'Inference price decline per year',
    unit: '×/yr',
    param: 'P.04',
    step: 1,
    mechanism: 'Price at fixed capability falls by this factor each year (§3.3).',
  },
  open_weights_multiplier: {
    label: 'Open-weights price multiplier',
    unit: '×',
    param: 'P.05',
    step: 0.05,
    mechanism: 'Price compression once an open-weights model matches the frontier.',
  },
  cost_floor_decline_per_year: {
    label: 'Cost floor decline per year',
    unit: '×/yr',
    param: 'P.06',
    step: 0.1,
    mechanism: 'Hardware cost floor under the inference price (§3.4).',
  },
  compute_capacity_constraint: {
    label: 'Compute capacity constraint',
    param: 'P.38',
    mechanism: 'When on, demand above installed compute raises prices (§3.4).',
  },
  capacity_price_exponent: {
    label: 'Capacity price exponent ξ',
    unit: '',
    param: 'P.39',
    step: 0.1,
    mechanism: 'How sharply prices rise when compute is scarce.',
  },
  token_growth_per_doubling: {
    label: 'Tokens per task per doubling',
    unit: 'elasticity',
    param: 'P.08',
    step: 0.05,
    mechanism: 'Token use per task grows with capability; feeds effective task cost.',
  },
  ai_act: {
    label: 'EU AI Act timetable',
    param: 'P.30–P.32',
    mechanism: 'Shifts when high-risk use-case tasks become available in the EU.',
  },
  data_localization: {
    label: 'EU data localization',
    mechanism: 'Moves cloud-stage rents into the EU value chain (§6.3).',
  },
  regime: {
    label: 'U.S. regulatory regime',
    param: 'P.31–P.32',
    mechanism: 'Compliance cost and availability for high-risk and transparency use cases.',
  },
  licensing: {
    label: 'China model licensing',
    param: 'P.30',
    mechanism: 'Availability lag of frontier capability in China.',
  },
  export_controls: {
    label: 'Chip export controls',
    param: 'λ_a (CN), K_t (CN)',
    mechanism: 'Frontier lag and compute capacity for Chinese actors.',
  },
  sector_friction_scale: {
    label: 'Sector adoption friction',
    unit: '×',
    param: 'P.48',
    step: 0.05,
    mechanism: 'Scales φ_s for every sector; slows or speeds diffusion (§4.2).',
  },
  small_firm_friction_scale: {
    label: 'Small-firm adoption friction',
    unit: '×',
    param: 'P.49',
    step: 0.05,
    mechanism: 'Scales φ_f for small firms.',
  },
  intensity_ceiling: {
    label: 'Adoption intensity ceiling',
    unit: 'share',
    param: 'P.40',
    step: 0.05,
    mechanism: 'Maximum share of feasible tasks an adopting firm actually automates.',
  },
  spillover_lag_quarters: {
    label: 'Cross-sector spillover lag',
    unit: 'quarters',
    param: 'P.50',
    step: 1,
    mechanism: 'Delay before adoption in one sector raises adoption elsewhere.',
  },
  entrant_scale: {
    label: 'AI-native entrant scale',
    unit: '×',
    param: 'P.52',
    step: 0.1,
    mechanism: 'Scales adoption by new firms; the hiring channel (§5.3).',
  },
  reinstatement_ratio: {
    label: 'Reinstatement ratio',
    unit: 'new tasks per task automated',
    param: 'P.61',
    step: 0.05,
    mechanism: 'New labor tasks created per task automated (a disagreement axis).',
  },
  demand_elasticity_scale: {
    label: 'Demand elasticity (scale)',
    unit: '×',
    param: 'P.60',
    step: 0.05,
    mechanism: 'Scales sector demand response to lower unit costs (a disagreement axis).',
  },
  layoff_friction: {
    label: 'Layoff friction',
    unit: 'share per quarter',
    param: 'P.62',
    step: 0.01,
    mechanism: 'Share of redundant positions actually cut each quarter after attrition.',
  },
  price_pass_through: {
    label: 'Pass-through to prices',
    unit: 'share',
    param: 'P.53',
    step: 0.05,
    mechanism: 'Share of unit-cost savings passed to consumers as lower prices.',
  },
  occupational_attrition_pct_per_quarter: {
    label: 'Occupational attrition',
    unit: '% per quarter',
    param: 'P.63',
    step: 0.1,
    mechanism: 'Natural exits that absorb displacement before layoffs.',
  },
  wage_pass_through: {
    label: 'Wage pass-through',
    unit: 'share',
    param: 'P.74',
    step: 0.05,
    mechanism: 'Share of productivity gains reaching wages (a disagreement axis).',
  },
  retraining_subsidy_pct_wage: {
    label: 'Retraining subsidy',
    unit: '% of wage',
    step: 5,
    mechanism: 'Raises the retraining transition rate for displaced workers.',
  },
  wage_insurance_replacement: {
    label: 'Wage insurance replacement rate',
    unit: 'share',
    step: 0.05,
    mechanism: 'Tops up wages after re-employment at lower pay.',
  },
  wage_insurance_years: {
    label: 'Wage insurance duration',
    unit: 'years',
    step: 0.5,
    mechanism: 'Years the wage insurance is paid.',
  },
  ubi_monthly_usd: {
    label: 'Universal basic income',
    unit: 'USD / month',
    step: 100,
    mechanism: 'Household transfer; supports demand, financed per the financing rule.',
  },
  ai_tax_pct_of_ai_spend: {
    label: 'AI tax',
    unit: '% of AI spend',
    step: 1,
    mechanism: 'Raises the effective task price; finances transfers.',
  },
  work_week_hours: {
    label: 'Standard work week',
    unit: 'hours',
    step: 1,
    mechanism: 'Shorter week spreads remaining hours across more workers.',
  },
  immigration_scale: {
    label: 'Immigration (scale)',
    unit: '×',
    step: 0.1,
    mechanism: 'Scales new-entrant labor supply (§5.6).',
  },
  retraining: { label: 'Financing: retraining', mechanism: 'Who pays for the retraining subsidy.' },
  wage_insurance: { label: 'Financing: wage insurance', mechanism: 'Who pays for wage insurance.' },
  ubi: { label: 'Financing: UBI', mechanism: 'Who pays for the basic income.' },
  work_week: { label: 'Financing: shorter week', mechanism: 'Who pays for the shorter work week.' },
  bls_ai_adjustment: {
    label: 'BLS projection AI adjustment',
    mechanism: 'Restore the pre-AI trend for occupations BLS already adjusted for AI (§7.6).',
  },
  // ---------- Phase 6 (spec v0.3 §A.9, contracts §21); labels follow api/aiwsim_api/levers.py ----------
  automation_trend: {
    label: 'Baseline: pre-AI automation trend (scale)',
    unit: '×',
    param: 'P.104',
    step: 0.05,
    mechanism: 'Scales the pre-2023 automation trend the frozen-AI baseline keeps; results are the AI-enabled increment over it (spec v0.3 §A.6.2).',
  },
  driving_doubling_months: {
    label: 'Driving autonomy doubling time',
    unit: 'months',
    param: 'P.108',
    step: 1,
    mechanism: 'Embodiment clock for driving (spec v0.3 §A.3.1).',
  },
  manipulation_doubling_months: {
    label: 'Mobile manipulation doubling time',
    unit: 'months',
    param: 'P.108',
    step: 1,
    mechanism: 'Embodiment clock for mobile manipulation (spec v0.3 §A.3.1).',
  },
  fixed_doubling_months: {
    label: 'Fixed automation doubling time',
    unit: 'months',
    param: 'P.108',
    step: 1,
    mechanism: 'Embodiment clock for fixed automation (spec v0.3 §A.3.1).',
  },
  aerial_doubling_months: {
    label: 'Aerial autonomy doubling time',
    unit: 'months',
    param: 'P.108',
    step: 1,
    mechanism: 'Embodiment clock for aerial autonomy (spec v0.3 §A.3.1).',
  },
  coupling_to_software: {
    label: 'Coupling of embodiment clocks to the software clock',
    unit: 'share',
    param: 'P.107',
    step: 0.05,
    mechanism: 'Share of software-clock progress that carries over to the embodiment clocks (spec v0.3 §A.3.1).',
  },
  learning_rate: {
    label: 'Hardware learning rate',
    unit: 'per doubling',
    param: 'P.113',
    step: 0.01,
    mechanism: 'Wright’s-law unit-cost decline per doubling of cumulative production (spec v0.3 §A.3.2).',
  },
  utilization_scale: {
    label: 'Hardware utilization (scale)',
    unit: '×',
    param: 'P.115',
    step: 0.05,
    mechanism: 'Scales paid hours per unit; sets the cost per task-hour (spec v0.3 §A.3.2).',
  },
  unit_price_scale: {
    label: 'Hardware unit price 2025 (scale)',
    unit: '×',
    param: 'P.110',
    step: 0.05,
    mechanism: 'Scales the 2025 unit price of every class; sets the cost per task-hour (spec v0.3 §A.3.2).',
  },
  ramp_max_growth_per_year: {
    label: 'Production ramp cap',
    unit: '/yr',
    param: 'P.117',
    step: 0.05,
    mechanism: 'Maximum yearly growth of deliveries; bounds deployment speed (spec v0.3 §A.3.3).',
  },
  platform_labor: {
    label: 'Platform labor classification',
    param: 'P.123',
    mechanism: 'Employee reclassification moves platform FTE to the employee stock, changing the attrition buffer (spec v0.3 §A.3.6).',
  },
}
// ---------- Phase 7 (spec v0.3 §A.9, contracts §25); labels follow api/aiwsim_api/levers.py ----------
Object.assign(LEVER_LABELS, {
  'levers.applications.enabled': {
    label: 'Application layer (v0.3) on',
    mechanism: 'Embodied, output-substitution and traded-services channels (spec v0.3); off reproduces the v0.2 task engine.',
  },
  'levers.applications.content.authenticity': {
    label: 'Authenticity premium',
    param: 'P.127',
    mechanism: 'Willingness to pay for human provenance: persistent (constant at its 2025 level) or eroding with a half-life (spec v0.3 §A.4).',
  },
  'levers.applications.content.authenticity_level_scale': {
    label: 'Authenticity premium level (scale)',
    unit: '×',
    param: 'P.127',
    step: 0.05,
    mechanism: 'Scales the 2025 authenticity premium of every content category (spec v0.3 §A.4).',
  },
  'levers.applications.content.licensing_regime': {
    label: 'Content licensing regime',
    param: 'P.128',
    mechanism: 'AI content price and quality growth under permissive, licensed or restrictive training-data rules (spec v0.3 §A.4).',
  },
  'levers.applications.content.price_sensitivity': {
    label: 'Content price sensitivity γ',
    param: 'P.125',
    step: 0.1,
    mechanism: 'Logit sensitivity of the AI share to the AI/human price ratio (spec v0.3 §A.4).',
  },
  'levers.applications.trade.services_exposure_scale': {
    label: 'Services-trade exposure (scale)',
    unit: '×',
    param: 'P.124',
    step: 0.05,
    mechanism: 'Scales export-serving employment facing the importers’ task displacement (spec v0.3 §A.5.3).',
  },
})
for (const r of REGION_IDS)
  LEVER_LABELS[`levers.applications.approval.${r}`] = {
    label: `Approval regime: ${r}`,
    param: 'P.119',
    mechanism: 'Deployment share J path per region and class: frozen, baseline, accelerated or moratorium (spec v0.3 §A.3.4).',
  }

function niceStep(min: number, max: number): number {
  const raw = (max - min) / 100
  const p = Math.pow(10, Math.floor(Math.log10(raw)))
  const f = raw / p
  return f <= 1 ? p : f <= 2 ? 2 * p : f <= 5 ? 5 * p : 10 * p
}

function humanize(key: string) {
  return key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}

function getPath(obj: unknown, path: string[]): unknown {
  let cur: unknown = obj
  for (const k of path) {
    if (cur == null || typeof cur !== 'object') return undefined
    cur = (cur as Record<string, unknown>)[k]
  }
  return cur
}

function buildLevers(schema: JsonSchema, baseline: ScenarioDocument): LeverDef[] {
  const out: LeverDef[] = []
  const leversSchema = schema.properties?.levers
  if (!leversSchema?.properties) throw new Error('schema has no levers.properties')

  function walk(node: JsonSchema, path: string[], group: string) {
    const key = path[path.length - 1] ?? ''
    // full-path entries win (the per-region approval enums share leaf keys with other groups)
    const meta = LEVER_LABELS[path.join('.')] ?? LEVER_LABELS[key]
    const label = meta?.label ?? humanize(key)
    const def = getPath(baseline, path)
    const base = {
      path: path.join('.'),
      label: path.length > 3 && !meta ? `${humanize(path[2] ?? '')}: ${label}` : label,
      group,
      param: meta?.param,
      mechanism: meta?.mechanism ?? node.description,
    }
    if (node.enum) {
      out.push({ ...base, type: 'enum', options: node.enum, default: (def as string) ?? node.enum[0] })
      return
    }
    if (node.type === 'boolean') {
      out.push({ ...base, type: 'boolean', default: (def as boolean) ?? (node.default as boolean) ?? false })
      return
    }
    if (node.type === 'number' || node.type === 'integer') {
      const min = node.minimum ?? 0
      const max = node.maximum ?? 1
      out.push({
        ...base,
        type: 'number',
        min,
        max,
        step: meta?.step ?? niceStep(min, max),
        unit: meta?.unit ?? '',
        default: (def as number) ?? (node.default as number) ?? min,
      })
      return
    }
    if (node.properties) {
      for (const [k, child] of Object.entries(node.properties)) walk(child, [...path, k], group)
      return
    }
    // additionalProperties maps: expand the keys present in the baseline scenario (policy.US);
    // per-actor / per-sector maps have no baseline entries and are not exposed as form levers.
    if (node.additionalProperties && typeof node.additionalProperties === 'object') {
      const present = getPath(baseline, path)
      if (present && typeof present === 'object')
        for (const k of Object.keys(present))
          walk(node.additionalProperties, [...path, k], group)
    }
  }

  for (const [group, node] of Object.entries(leversSchema.properties)) {
    walk(node, ['levers', group], group)
  }
  return out
}

// ---------- write ----------
const docA = build(cfgA)
const docB = build(cfgB)

const schema = JSON.parse(readFileSync(resolve(scenariosDir, 'schema.json'), 'utf8')) as JsonSchema
const scenarioDocs: ScenarioDocument[] = readdirSync(scenariosDir)
  .filter((f) => f.endsWith('.json') && f !== 'schema.json')
  .sort()
  .map((f) => JSON.parse(readFileSync(resolve(scenariosDir, f), 'utf8')) as ScenarioDocument)
const baseline = scenarioDocs.find((s) => s.id === 'baseline')
if (!baseline) throw new Error('scenarios/baseline.json missing')
const levers = buildLevers(schema, baseline)

mkdirSync(outDir, { recursive: true })
writeFileSync(resolve(outDir, 'results.json'), JSON.stringify(docA))
writeFileSync(resolve(outDir, 'results-b.json'), JSON.stringify(docB))
writeFileSync(resolve(outDir, 'levers.json'), JSON.stringify(levers, null, 1))
writeFileSync(resolve(outDir, 'scenarios.json'), JSON.stringify(scenarioDocs, null, 1))
writeFileSync(resolve(outDir, 'us-states.geojson'), JSON.stringify(geo))
writeFileSync(resolve(outDir, 'world.geojson'), JSON.stringify(worldGeo))
console.log(
  `wrote ${quarters.length} quarters, ${docA.occupations.length} occupations, ${docA.states.length} states, ${REGIONS.length} regions, ${docA.world?.length} countries (${worldGeo.features.length} drawn), ${docA.supply?.releases.length} releases, ${docA.applications?.length} applications, ${docA.meta.content_categories?.length} content categories, ${docA.channels.employment_pct_vs_baseline?.order.length}-entry channels, ${docA.meta.cells?.length} cells, ${levers.length} levers, ${scenarioDocs.length} scenarios → ${outDir}`,
)

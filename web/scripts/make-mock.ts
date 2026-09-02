/**
 * Generates web/src/mock/{results.json, results-b.json, levers.json, scenarios.json, us-states.geojson}.
 * Numbers are deliberately synthetic (smooth S-curves + seeded noise); the shape matches
 * docs/contracts.md §2 and the Phase 2 additions in §7–10 exactly. Run: pnpm make-mock
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
} from '../src/types/results'
import { HEADLINE_METRICS, FLOW_DESTINATIONS } from '../src/types/results'

const here = dirname(fileURLToPath(import.meta.url))
const outDir = resolve(here, '../src/mock')
const repoRoot = resolve(here, '../..')
const rawGeo = resolve(repoRoot, 'data/raw/natural_earth/ne_admin1_110m.geojson')
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
/** S-curve that starts at 0 in 2024Q1 */
const rise = (amp: number, mid: number, k: number) =>
  curve((yr) => amp * logistic(yr, mid, k) - amp * logistic(0, mid, k))
const add = (a: number[], b: number[]) => a.map((v, i) => v + (b[i] ?? 0))
const mul = (a: number[], k: number) => a.map((v) => v * k)

/**
 * Percentiles around a median: p10<p25<p50<p75<p90 with a band that widens over time,
 * and `central` (the central-parameter run) close to but not equal to p50.
 */
function bandify(
  p50: number[],
  amp: number,
  opts: { floor?: number; ceil?: number; digits?: number; skew?: number } = {},
): Series {
  const { floor, ceil, digits = 4, skew = 0 } = opts
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
      if (!(v[k]! > v[k - 1]!) && !clamped)
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
  diff: [],
  notes: [
    'MOCK DATA. Every number here is a synthetic S-curve generated by web/scripts/make-mock.ts, not a model run.',
    'Adoption follows a logistic path from 4% of firms in 2024 to about 80% by 2040, with the midpoint in mid-2030.',
    'Net employment falls to roughly -3.8% versus the no-AI baseline around 2032 before reinstatement and demand feedback recover part of the loss.',
    'The automation channel is the only negative contributor; augmentation, demand response, reinstatement, demand feedback and AI investment offset about half of it by 2040.',
    'Bands are the pooled 2x2x2 mechanism ensemble; the structural view separates the eight cell medians.',
    'State and occupation series are the national path scaled by a fixed per-unit tilt (data_flags.occ_state = FIXTURE), so the map shows spread but no real geography.',
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
    'Bands are the pooled 2x2x2 mechanism ensemble; the structural view separates the eight cell medians.',
    'State and occupation series are the national path scaled by a fixed per-unit tilt (data_flags.occ_state = FIXTURE), so the map shows spread but no real geography.',
  ],
}

// ---------- shared fixtures ----------
const channelOrder: ChannelName[] = [
  'automation',
  'augmentation',
  'demand_response',
  'reinstatement',
  'demand_feedback',
  'ai_investment',
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

/** Mechanism cells (spec §7.2): demand × reinstatement × pass-through. */
const CELL_AXES: [string, string][] = [
  ['bessen', 'unit_elastic'],
  ['acemoglu_low', 'historical'],
  ['passthrough_low', 'passthrough_mid'],
]
const cells: string[] = []
for (const a of CELL_AXES[0]!)
  for (const b of CELL_AXES[1]!) for (const c of CELL_AXES[2]!) cells.push(`${a}|${b}|${c}`)

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

  // national medians
  const adoption = curve(
    (yr) => 0.04 + cfg.adoptionCeil * logistic(yr + cfg.euAdoptionLead * 0.3, cfg.adoptionMid, 0.75),
  )
  const capabilityIndex = curve((yr) => (12 / cfg.doublingMonths) * yr)
  const gdp = rise(cfg.gdpAmp, 8, 0.6)
  const tfp = rise(cfg.tfpAmp, 8.5, 0.6)
  const employment = add(rise(cfg.empDrop, 6, 0.9), rise(cfg.empRecover, 10, 0.8))
  const realWage = add(rise(cfg.wageDip, 4, 1.2), rise(cfg.wageGain, 9, 0.7))
  const priceIndex = rise(cfg.priceAmp, 8, 0.6)
  const nominalWage = add(realWage, priceIndex)
  const wageShare = rise(cfg.wageShareAmp, 7.5, 0.7)
  const displaced = rise(cfg.displacedAmp, 7, 0.65)
  const aiSpend = add(curve(() => 210), rise(cfg.spendAmp, 6, 0.6))
  const horizonHours = capabilityIndex.map((idx) => Math.pow(2, idx) / 60)

  const S = {
    gdp: bandify(gdp, 2.4, { skew: 0.1 }),
    tfp: bandify(tfp, 1.8),
    employment: bandify(employment, 1.9, { skew: -0.1 }),
    realWage: bandify(realWage, 1.6),
    nominalWage: bandify(nominalWage, 2.0),
    wageShare: bandify(wageShare, 1.2),
    priceIndex: bandify(priceIndex, 1.4),
    displaced: bandify(displaced, 3.2e6, { floor: 0, digits: 0 }),
    adoption: bandify(adoption, 0.12, { floor: 0, ceil: 1 }),
    aiSpend: bandify(aiSpend, 260, { floor: 0, digits: 1 }),
    capabilityIndex: bandify(capabilityIndex, 6, { floor: 0, digits: 2 }),
    horizonHours: bandify(horizonHours, 1, { floor: 0, digits: 2 }),
  }
  // capability horizon is 2^index: derive its band from the index band so it stays consistent
  for (const k of ['p10', 'p25', 'p50', 'p75', 'p90', 'central'] as const) {
    S.horizonHours[k] = S.capabilityIndex[k]!.map((v) => round(Math.pow(2, v) / 60, 2))
  }

  // channels for employment (contributions sum to the median exactly)
  const empRaw: Record<ChannelName, number[]> = {
    automation: rise(cfg.empDrop * 1.6, 6, 0.9),
    augmentation: rise(0.5, 5, 0.9),
    demand_response: rise(0.9, 7, 0.8),
    reinstatement: rise(1.1, 10, 0.7),
    demand_feedback: rise(0.7, 8, 0.7),
    ai_investment: rise(0.4, 5, 0.9),
  }
  const gdpRaw: Record<ChannelName, number[]> = {
    automation: rise(3.4, 7, 0.65),
    augmentation: rise(1.6, 6, 0.8),
    demand_response: rise(-0.9, 7.5, 0.7),
    reinstatement: rise(0.8, 10, 0.7),
    demand_feedback: rise(0.6, 8, 0.7),
    ai_investment: rise(1.1, 5, 0.9),
  }
  function rescale(raw: Record<ChannelName, number[]>, negKey: ChannelName, target: number[]) {
    const out: Partial<Record<ChannelName, number[]>> = {}
    for (const c of channelOrder) out[c] = []
    for (let i = 0; i < N; i++) {
      const neg = raw[negKey][i] ?? 0
      const posRaw = channelOrder
        .filter((c) => c !== negKey)
        .reduce((acc, c) => acc + (raw[c][i] ?? 0), 0)
      const k = posRaw > 1e-9 ? ((target[i] ?? 0) - neg) / posRaw : 0
      for (const c of channelOrder)
        out[c]!.push(round(c === negKey ? neg : (raw[c][i] ?? 0) * k, 4))
    }
    return out
  }

  // occupations
  const occupations: OccupationResult[] = occSeed.map(([code, title, mg, emp0, wage0, auto], i) => {
    const lag = 5.5 + jitter(2) + (auto > 0.5 ? -1 : 1)
    const ceiling = auto * (0.45 + 0.3 * rand()) * (cfg.displacedAmp / cfgA.displacedAmp)
    const k = 0.7 + 0.4 * rand()
    const disp = curve((yr) =>
      Math.max(0, ceiling * (logistic(yr, lag + 3, k) - logistic(0, lag + 3, k))),
    )
    const emp = disp.map((d, j) => -d * 100 * 0.85 + 0.35 * (gdp[j] ?? 0) * (1 - auto))
    const wage = disp.map((d, j) => (realWage[j] ?? 0) * (1.2 - auto) - d * 100 * 0.25)
    return {
      occ_code: code,
      title,
      cluster_id: `c${String(i + 1).padStart(3, '0')}`,
      major_group: mg,
      emp0,
      wage0,
      automatable_share: round(auto, 3),
      exposure_beta: round(Math.min(0.98, auto + 0.08 + jitter(0.05)), 3),
      displacement: bandify(disp, 0.06 + 0.1 * auto, { floor: 0 }),
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

  // structural ensemble: 8 cell medians per headline metric
  const headline: Record<HeadlineMetric, Series> = {
    employment_pct_vs_baseline: S.employment,
    gdp_pct_vs_baseline: S.gdp,
    real_wage_pct_vs_baseline: S.realWage,
    wage_share_pp_vs_baseline: S.wageShare,
  }
  // per-metric multiplicative effect of choosing variant B on each axis
  const axisEffect: Record<HeadlineMetric, [number, number, number]> = {
    employment_pct_vs_baseline: [0.22, -0.35, 0.1],
    gdp_pct_vs_baseline: [0.12, 0.08, 0.18],
    real_wage_pct_vs_baseline: [0.1, 0.25, 0.6],
    wage_share_pp_vs_baseline: [0.05, 0.1, -0.3],
  }
  const structural: Partial<Record<HeadlineMetric, StructuralSection>> = {}
  for (const m of HEADLINE_METRICS) {
    const base = headline[m].p50
    const by_cell: Record<string, { p50: number[] }> = {}
    cells.forEach((id, ci) => {
      const bits = [(ci >> 2) & 1, (ci >> 1) & 1, ci & 1]
      const eff = axisEffect[m]
      let f = 1
      for (let a = 0; a < 3; a++) if (bits[a]) f *= 1 + (eff[a] ?? 0)
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
  ]
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
      jobs_lost_cum: bandify(mul(displaced, share), 3.2e6 * share, { floor: 0, digits: 0 }),
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
      spec_version: '0.2',
      schema_version: '0.3',
      scenario_id: cfg.scenarioId,
      scenario_hash: cfg.hash,
      seed: 42,
      run_at: '2026-09-01T00:00:00Z',
      draws: 200,
      ensemble: 'all',
      cells,
      percentiles: [10, 25, 50, 75, 90],
      quarters,
      regions: ['US'],
      baseline: 'no_frontier_ai_after_2023',
      data_flags: {
        occ_state: 'FIXTURE',
        occ_sector: 'FIXTURE',
        aei_anchoring: 'unavailable',
        cohorts: 'FIXTURE',
      },
      capability_units: 'doublings of METR 50% task horizon (minutes = 2^index)',
    },
    series: {
      US: {
        gdp_pct_vs_baseline: S.gdp,
        employment_pct_vs_baseline: S.employment,
        real_wage_pct_vs_baseline: S.realWage,
        nominal_wage_pct_vs_baseline: S.nominalWage,
        wage_share_pp_vs_baseline: S.wageShare,
        tfp_pct_vs_baseline: S.tfp,
        price_index_pct_vs_baseline: S.priceIndex,
        displaced_workers_cum: S.displaced,
        adoption_share: S.adoption,
        ai_spend_bn: S.aiSpend,
        capability_index: S.capabilityIndex,
        capability_horizon_hours: S.horizonHours,
      },
    },
    occupations,
    states,
    channels: {
      employment_pct_vs_baseline: {
        order: channelOrder,
        contributions: rescale(empRaw, 'automation', S.employment.p50),
      },
      gdp_pct_vs_baseline: {
        order: channelOrder,
        contributions: rescale(gdpRaw, 'demand_response', S.gdp.p50),
      },
    },
    explain: { notes: cfg.notes, trace, diff: cfg.diff },
    structural,
    confidence,
    tornado,
    cohorts,
    flows,
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
    const meta = LEVER_LABELS[key]
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
console.log(
  `wrote ${quarters.length} quarters, ${docA.occupations.length} occupations, ${docA.states.length} states, ${levers.length} levers, ${scenarioDocs.length} scenarios → ${outDir}`,
)

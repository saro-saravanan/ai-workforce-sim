/**
 * Generates web/src/mock/results.json and web/src/mock/us-states.geojson.
 * Numbers are deliberately synthetic (smooth S-curves + seeded noise); the shape matches
 * docs/contracts.md §2 exactly. Run: pnpm make-mock
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import type {
  ResultsDocument,
  OccupationResult,
  StateResult,
  ChannelName,
  StatesGeoJSON,
  Series,
} from '../src/types/results'

const here = dirname(fileURLToPath(import.meta.url))
const outDir = resolve(here, '../src/mock')
const rawGeo = resolve(here, '../../data/raw/natural_earth/ne_admin1_110m.geojson')

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
const rand = mulberry32(42)
const jitter = (amp: number) => (rand() - 0.5) * 2 * amp

// ---------- quarters ----------
const quarters: string[] = []
for (let y = 2024; y <= 2040; y++) for (let q = 1; q <= 4; q++) quarters.push(`${y}Q${q}`)
const N = quarters.length // 68
const t = (i: number) => i / 4 // years since 2024Q1

const logistic = (x: number, mid: number, k: number) => 1 / (1 + Math.exp(-k * (x - mid)))
const round = (v: number, d = 3) => Number(v.toFixed(d))
const s = (arr: number[]): Series => ({ p50: arr.map((v) => round(v)) })
const curve = (f: (yr: number) => number) => Array.from({ length: N }, (_, i) => f(t(i)))

// ---------- national series ----------
const adoption = curve((yr) => 0.04 + 0.78 * logistic(yr, 6.5, 0.75))
const capabilityIndex = curve((yr) => 2 * yr) // doublings, 6-month doubling time
const gdp = curve((yr) => 6.2 * logistic(yr, 8, 0.6) - 6.2 * logistic(0, 8, 0.6))
const tfp = curve((yr) => 4.6 * logistic(yr, 8.5, 0.6) - 4.6 * logistic(0, 8.5, 0.6))
const employment = curve(
  (yr) => -3.8 * logistic(yr, 6, 0.9) + 1.7 * logistic(yr, 10, 0.8) + 3.8 * logistic(0, 6, 0.9),
)
const realWage = curve(
  (yr) => -0.6 * logistic(yr, 4, 1.2) + 2.4 * logistic(yr, 9, 0.7) + 0.6 * logistic(0, 4, 1.2),
)
const priceIndex = curve((yr) => -3.1 * logistic(yr, 8, 0.6) + 3.1 * logistic(0, 8, 0.6))
const nominalWage = realWage.map((v, i) => v + (priceIndex[i] ?? 0))
const wageShare = curve((yr) => -2.6 * logistic(yr, 7.5, 0.7) + 2.6 * logistic(0, 7.5, 0.7))
const displaced = curve((yr) => 9.4e6 * logistic(yr, 7, 0.65) - 9.4e6 * logistic(0, 7, 0.65))
const aiSpend = curve((yr) => 210 + 1050 * logistic(yr, 6, 0.6) - 1050 * logistic(0, 6, 0.6))
const horizonHours = capabilityIndex.map((idx) => (Math.pow(2, idx) * 1) / 60) // 1-minute base

// ---------- channels for employment (contributions sum to the series) ----------
const channelOrder: ChannelName[] = [
  'automation',
  'augmentation',
  'demand_response',
  'reinstatement',
  'demand_feedback',
  'ai_investment',
]
const rawChannels: Record<ChannelName, number[]> = {
  automation: curve((yr) => -6.1 * logistic(yr, 6, 0.9) + 6.1 * logistic(0, 6, 0.9)),
  augmentation: curve((yr) => 0.5 * logistic(yr, 5, 0.9) - 0.5 * logistic(0, 5, 0.9)),
  demand_response: curve((yr) => 0.9 * logistic(yr, 7, 0.8) - 0.9 * logistic(0, 7, 0.8)),
  reinstatement: curve((yr) => 1.1 * logistic(yr, 10, 0.7) - 1.1 * logistic(0, 10, 0.7)),
  demand_feedback: curve((yr) => 0.7 * logistic(yr, 8, 0.7) - 0.7 * logistic(0, 8, 0.7)),
  ai_investment: curve((yr) => 0.4 * logistic(yr, 5, 0.9) - 0.4 * logistic(0, 5, 0.9)),
}
// rescale positive channels so the sum equals the employment series exactly
const contributions: Partial<Record<ChannelName, number[]>> = {}
for (const c of channelOrder) contributions[c] = []
for (let i = 0; i < N; i++) {
  const neg = rawChannels.automation[i] ?? 0
  const posRaw = channelOrder
    .filter((c) => c !== 'automation')
    .reduce((acc, c) => acc + (rawChannels[c][i] ?? 0), 0)
  const target = (employment[i] ?? 0) - neg
  const k = posRaw > 1e-9 ? target / posRaw : 0
  for (const c of channelOrder) {
    const v = c === 'automation' ? neg : (rawChannels[c][i] ?? 0) * k
    contributions[c]!.push(round(v, 4))
  }
}

// ---------- occupations (40, obviously synthetic) ----------
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

const occupations: OccupationResult[] = occSeed.map(([code, title, mg, emp0, wage0, auto], i) => {
  const lag = 5.5 + jitter(2) + (auto > 0.5 ? -1 : 1) // cognitive-heavy groups move earlier
  const ceiling = auto * (0.45 + 0.3 * rand()) // realized displacement approaches ~45–75% of the ceiling
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
    displacement: s(disp),
    employment_pct_vs_baseline: s(emp),
    real_wage_pct_vs_baseline: s(wage),
  }
})

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

const states: StateResult[] = geo.features.map((f) => {
  const { fips, name } = f.properties
  const tilt = 0.55 + rand() * 0.9 // 0.55–1.45 × national
  const lead = jitter(1.2) // years ahead/behind
  const share = 0.004 + rand() * 0.06
  const emp = curve(
    (yr) =>
      tilt *
      (-3.8 * logistic(yr - lead, 6, 0.9) +
        1.7 * logistic(yr - lead, 10, 0.8) +
        3.8 * logistic(0, 6, 0.9)),
  )
  const wage = realWage.map((v, i) => v * (2 - tilt) + 0.15 * (emp[i] ?? 0))
  const disp = displaced.map((v) => v * share * tilt)
  return {
    fips,
    name,
    employment_pct_vs_baseline: s(emp),
    real_wage_pct_vs_baseline: s(wage),
    displaced_workers_cum: { p50: disp.map((v) => Math.round(v)) },
  }
})

// ---------- channels for GDP (same mechanism, positive-dominated) ----------
const gdpRaw: Record<ChannelName, number[]> = {
  automation: curve((yr) => 3.4 * logistic(yr, 7, 0.65) - 3.4 * logistic(0, 7, 0.65)),
  augmentation: curve((yr) => 1.6 * logistic(yr, 6, 0.8) - 1.6 * logistic(0, 6, 0.8)),
  demand_response: curve((yr) => -0.9 * logistic(yr, 7.5, 0.7) + 0.9 * logistic(0, 7.5, 0.7)),
  reinstatement: curve((yr) => 0.8 * logistic(yr, 10, 0.7) - 0.8 * logistic(0, 10, 0.7)),
  demand_feedback: curve((yr) => 0.6 * logistic(yr, 8, 0.7) - 0.6 * logistic(0, 8, 0.7)),
  ai_investment: curve((yr) => 1.1 * logistic(yr, 5, 0.9) - 1.1 * logistic(0, 5, 0.9)),
}
const gdpContrib: Partial<Record<ChannelName, number[]>> = {}
for (const c of channelOrder) gdpContrib[c] = []
for (let i = 0; i < N; i++) {
  const neg = gdpRaw.demand_response[i] ?? 0
  const posRaw = channelOrder
    .filter((c) => c !== 'demand_response')
    .reduce((acc, c) => acc + (gdpRaw[c][i] ?? 0), 0)
  const k = posRaw > 1e-9 ? ((gdp[i] ?? 0) - neg) / posRaw : 0
  for (const c of channelOrder) {
    gdpContrib[c]!.push(round(c === 'demand_response' ? neg : (gdpRaw[c][i] ?? 0) * k, 4))
  }
}

const doc: ResultsDocument = {
  meta: {
    spec_version: '0.2',
    schema_version: '0.2',
    scenario_id: 'baseline',
    scenario_hash: 'sha256:mock-0000000000000000000000000000000000000000000000000000000000000000',
    seed: 42,
    run_at: '2026-09-01T00:00:00Z',
    draws: 1,
    ensemble: 'central',
    quarters,
    regions: ['US'],
    baseline: 'no_frontier_ai_after_2023',
    data_flags: { occ_state: 'FIXTURE', occ_sector: 'FIXTURE', aei_anchoring: 'unavailable' },
    capability_units: 'doublings of METR 50% task horizon (minutes = 2^index)',
  },
  series: {
    US: {
      gdp_pct_vs_baseline: s(gdp),
      employment_pct_vs_baseline: s(employment),
      real_wage_pct_vs_baseline: s(realWage),
      nominal_wage_pct_vs_baseline: s(nominalWage),
      wage_share_pp_vs_baseline: s(wageShare),
      tfp_pct_vs_baseline: s(tfp),
      price_index_pct_vs_baseline: s(priceIndex),
      displaced_workers_cum: { p50: displaced.map((v) => Math.round(v)) },
      adoption_share: s(adoption),
      ai_spend_bn: { p50: aiSpend.map((v) => round(v, 1)) },
      capability_index: s(capabilityIndex),
      capability_horizon_hours: { p50: horizonHours.map((v) => round(v, 2)) },
    },
  },
  occupations,
  states,
  channels: {
    employment_pct_vs_baseline: { order: channelOrder, contributions },
    gdp_pct_vs_baseline: { order: channelOrder, contributions: gdpContrib },
  },
  explain: {
    notes: [
      'MOCK DATA. Every number here is a synthetic S-curve generated by web/scripts/make-mock.ts, not a model run.',
      'Adoption follows a logistic path from 4% of firms in 2024 to about 80% by 2040, with the midpoint in mid-2030.',
      'Net employment falls to roughly -3.8% versus the no-AI baseline around 2032 before reinstatement and demand feedback recover part of the loss.',
      'The automation channel is the only negative contributor; augmentation, demand response, reinstatement, demand feedback and AI investment offset about half of it by 2040.',
      'State and occupation series are the national path scaled by a fixed per-unit tilt (data_flags.occ_state = FIXTURE), so the map shows spread but no real geography.',
    ],
  },
}

mkdirSync(outDir, { recursive: true })
writeFileSync(resolve(outDir, 'results.json'), JSON.stringify(doc))
writeFileSync(resolve(outDir, 'us-states.geojson'), JSON.stringify(geo))
console.log(
  `wrote ${quarters.length} quarters, ${occupations.length} occupations, ${states.length} states → ${outDir}`,
)

import type {
  ApplicationMetric,
  ChannelName,
  EmbodiedMetric,
  NationalMetric,
  StateMetric,
} from '@/types/results'
import { fmtBn, fmtCompact, fmtPct, fmtPp, fmtShare } from './format'
import { CATEGORICAL, NEUTRAL, type Mode } from './palette'
import { stackCategorical } from './scales'

export type Polarity = 'diverging' | 'magnitude'

export interface MetricDef {
  label: string
  short: string
  unit: string
  polarity: Polarity
  /** true if a positive value is good for workers (used by nothing color-wise; text only) */
  format: (v: number | null | undefined) => string
  axisFormat: (v: number) => string
}

const pct: Pick<MetricDef, 'unit' | 'polarity' | 'format' | 'axisFormat'> = {
  unit: '% vs baseline',
  polarity: 'diverging',
  format: (v) => fmtPct(v),
  axisFormat: (v) => fmtPct(v, 1),
}

export const STATE_METRICS: Record<StateMetric, MetricDef> = {
  employment_pct_vs_baseline: { label: 'Net employment', short: 'Employment', ...pct },
  real_wage_pct_vs_baseline: { label: 'Real wages', short: 'Real wage', ...pct },
  displaced_workers_cum: {
    label: 'Displaced workers (cumulative)',
    short: 'Displaced',
    unit: 'workers since 2024',
    polarity: 'magnitude',
    format: (v) => fmtCompact(v),
    axisFormat: (v) => fmtCompact(v),
  },
}

export const STATE_METRIC_KEYS = Object.keys(STATE_METRICS) as StateMetric[]

export const DASHBOARD_TILES: Array<{ key: NationalMetric; def: MetricDef }> = [
  { key: 'gdp_pct_vs_baseline', def: { label: 'GDP', short: 'GDP', ...pct } },
  { key: 'tfp_pct_vs_baseline', def: { label: 'Productivity (TFP)', short: 'TFP', ...pct } },
  { key: 'real_wage_pct_vs_baseline', def: { label: 'Real wages', short: 'Real wages', ...pct } },
  {
    key: 'wage_share_pp_vs_baseline',
    def: {
      label: 'Wage share',
      short: 'Wage share',
      unit: 'pp vs baseline',
      polarity: 'diverging',
      format: (v) => fmtPp(v),
      axisFormat: (v) => fmtPp(v),
    },
  },
  { key: 'price_index_pct_vs_baseline', def: { label: 'Price index', short: 'Prices', ...pct } },
  {
    key: 'adoption_share',
    def: {
      label: 'Adoption share',
      short: 'Adoption',
      unit: 'share of firms using AI',
      polarity: 'magnitude',
      format: (v) => fmtShare(v, 1),
      axisFormat: (v) => fmtShare(v, 0),
    },
  },
]

export const CHANNEL_LABELS: Record<string, string> = {
  automation: 'Automation',
  augmentation: 'Augmentation',
  embodied: 'Embodied automation',
  output_substitution: 'Output substitution',
  traded_services: 'Traded services',
  demand_response: 'Demand response',
  reinstatement: 'Reinstatement',
  demand_feedback: 'Demand feedback',
  ai_investment: 'AI investment',
  adjacent: 'Adjacent and hardware jobs',
}

/**
 * Fixed categorical slot per channel so a channel keeps its color whether the document carries
 * the six-entry (v0.2), the eight-entry (Phase 6, contracts §20) or the ten-entry (Phase 7,
 * contracts §24) order.
 */
export const CHANNEL_COLOR_SLOT: Record<ChannelName, number> = {
  automation: 0,
  augmentation: 1,
  demand_response: 2,
  reinstatement: 3,
  demand_feedback: 4,
  ai_investment: 5,
  embodied: 6,
  adjacent: 7,
  output_substitution: 8,
  traded_services: 9,
}

/**
 * Names of the mechanism-cell axes in id order (spec §7.2, v0.3 §A.7, contracts §29): a document
 * with n-part cell ids uses the first n. Eight cells = 3 axes, sixteen = 4, thirty-two = 5,
 * sixty-four = 6 (the macro closure, `demand` / `no_demand_feedback`).
 */
export const CELL_AXIS_NAMES = [
  'demand response',
  'reinstatement',
  'pass-through',
  'hardware learning',
  'authenticity',
  'closure',
] as const
export function cellAxesLabel(parts: number): string {
  return CELL_AXIS_NAMES.slice(0, Math.max(1, Math.min(CELL_AXIS_NAMES.length, parts))).join(' | ')
}

/**
 * Color for a stacked-channel key: channels use their fixed slot; any other key set (the rents
 * stages reuse the same chart) falls back to the positional stack scale.
 */
export function channelColorScale(keys: string[], mode: Mode): (key: string) => string {
  const allChannels = keys.every((k) => k in CHANNEL_COLOR_SLOT)
  if (!allChannels) return stackCategorical(keys, mode)
  return (key: string) => {
    const slot = CHANNEL_COLOR_SLOT[key as ChannelName]
    return slot == null ? NEUTRAL[mode] : (CATEGORICAL[mode][slot] ?? NEUTRAL[mode])
  }
}

export const MAJOR_GROUPS: Record<string, string> = {
  '11': 'Management',
  '13': 'Business & finance',
  '15': 'Computer & math',
  '17': 'Architecture & engineering',
  '19': 'Science',
  '21': 'Community & social service',
  '23': 'Legal',
  '25': 'Education',
  '27': 'Arts, design & media',
  '29': 'Healthcare practitioners',
  '31': 'Healthcare support',
  '33': 'Protective service',
  '35': 'Food preparation',
  '37': 'Building & grounds',
  '39': 'Personal care',
  '41': 'Sales',
  '43': 'Office & admin support',
  '45': 'Farming, fishing & forestry',
  '47': 'Construction',
  '49': 'Installation & repair',
  '51': 'Production',
  '53': 'Transportation',
}

// ---------- Phase 2 ----------

import type {
  CohortFacet,
  ExtraFlowDestination,
  FlowDestination,
  FlowsSection,
  HeadlineMetric,
  TraceKey,
} from '@/types/results'
import { FLOW_DESTINATIONS } from '@/types/results'

export const EMPLOYMENT_DEF: MetricDef = { label: 'Net employment', short: 'Employment', ...pct }

/** Metrics offered in the compare view: employment first, then the dashboard tiles. */
export const COMPARE_METRICS: Array<{ key: NationalMetric; def: MetricDef }> = [
  { key: 'employment_pct_vs_baseline', def: EMPLOYMENT_DEF },
  ...DASHBOARD_TILES,
]

export function metricDef(key: NationalMetric): MetricDef {
  return COMPARE_METRICS.find((m) => m.key === key)?.def ?? EMPLOYMENT_DEF
}

export const HEADLINE_LABELS: Record<HeadlineMetric, string> = {
  employment_pct_vs_baseline: 'Net employment',
  gdp_pct_vs_baseline: 'GDP',
  real_wage_pct_vs_baseline: 'Real wages',
  wage_share_pp_vs_baseline: 'Wage share',
}

export const COHORT_FACET_LABELS: Record<CohortFacet, string> = {
  age: 'Age',
  education: 'Education',
  income_decile: 'Income decile',
}

const COHORT_BANDS: Record<string, string> = {
  lt_hs: 'Less than HS',
  hs: 'High school',
  some_college: 'Some college',
  ba_plus: 'BA or more',
}
export function cohortBandLabel(facet: CohortFacet, band: string): string {
  if (facet === 'education') return COHORT_BANDS[band] ?? band
  if (facet === 'income_decile') return `D${band}`
  return band.replace('-', '–')
}

export const COHORT_METRICS = {
  employment_pct_vs_baseline: {
    label: 'Employment vs baseline',
    unit: '% vs baseline',
    polarity: 'diverging' as Polarity,
    format: (v: number | null | undefined) => fmtPct(v),
    axisFormat: (v: number) => (v === 0 ? '0%' : `${v > 0 ? '+' : '−'}${Math.abs(v)}%`),
  },
  share_of_jobs_lost: {
    label: 'Share of jobs lost',
    unit: 'share of cumulative jobs lost',
    polarity: 'magnitude' as Polarity,
    format: (v: number | null | undefined) => fmtShare(v, 1),
    axisFormat: (v: number) => fmtShare(v, 0),
  },
} as const
export type CohortMetric = keyof typeof COHORT_METRICS

export const FLOW_DESTINATION_LABELS: Record<FlowDestination | ExtraFlowDestination, string> = {
  reemployed: 'Re-employed',
  retraining: 'In retraining',
  unemployed: 'Long-term unemployed',
  exited: 'Exited labor force',
  retired: 'Retired',
  unfilled_entry: 'Unfilled entry positions',
  hours_cut_self: 'Hours cut (self-employed and platform)',
  laid_off: 'Laid off',
  self_employed_margin_cum: 'Self-employed margin (cumulative)',
}

/**
 * The destinations drawn in the Sankey: the six v0.2 states plus, when the document carries it,
 * the Phase 6 self-employed margin `hours_cut_self` (contracts §20). `laid_off` and
 * `self_employed_margin_cum` are cumulative counters, not states, and stay in the table only.
 */
export function flowDestinations(flows: FlowsSection): Array<FlowDestination | 'hours_cut_self'> {
  const out: Array<FlowDestination | 'hours_cut_self'> = [...FLOW_DESTINATIONS]
  if (flows.destinations.hours_cut_self) out.push('hours_cut_self')
  return out
}

export const TRACE_LABELS: Record<TraceKey, string> = {
  automatable_share: 'Ever-automatable share (Σ w·a)',
  realized_D: 'Realized displacement D',
  realized_U: 'Realized task use U',
  adoption_emp: 'Adoption (employment-weighted)',
  dln_unit_cost: 'Δ ln unit cost',
  q_ratio: 'Output ratio Q/Q⁰',
  mu: 'Automation share μ',
  nu: 'New-task share ν',
  price_index: 'Price index',
}

export const PARAM_TAG_LABELS: Record<string, string> = {
  S: 'S: sourced from a study',
  D: 'D: derived from data',
  E: 'E: estimated / expert prior',
}

// ---------- Phase 3 ----------

import type { RegulatoryKind, RentStage, WorldMetric } from '@/types/results'

/** The dashboard tile for `ai_rents_received_bn.total` (spec §6.3). */
export const RENTS_DEF: MetricDef = {
  label: 'AI rents received',
  short: 'AI rents',
  unit: '$bn per year, by value-chain stage',
  polarity: 'magnitude',
  format: (v) => fmtBn(v),
  axisFormat: (v) => fmtBn(v),
}

export const RENT_STAGE_LABELS: Record<RentStage, string> = {
  model: 'Model provider margin',
  compute: 'Compute / cloud operations',
  chips: 'Chips and equipment',
  integration: 'Integration services',
}
// the stacked-channels chart labels its keys through CHANNEL_LABELS
Object.assign(CHANNEL_LABELS, RENT_STAGE_LABELS)

/** Metrics the world map can colour by: the two slim `world[]` series plus regional rents. */
export type MapMetric = WorldMetric | 'ai_rents_received_bn' | StateMetric
export const WORLD_METRICS: Record<WorldMetric | 'ai_rents_received_bn', MetricDef> = {
  employment_pct_vs_baseline: STATE_METRICS.employment_pct_vs_baseline,
  real_wage_pct_vs_baseline: STATE_METRICS.real_wage_pct_vs_baseline,
  ai_rents_received_bn: { ...RENTS_DEF, unit: '$bn per year, region total' },
}
export const MAP_METRIC_KEYS = [
  ...new Set<MapMetric>([
    ...(Object.keys(WORLD_METRICS) as Array<keyof typeof WORLD_METRICS>),
    ...STATE_METRIC_KEYS,
  ]),
]
export function mapMetricDef(k: MapMetric): MetricDef {
  return (WORLD_METRICS as Record<string, MetricDef>)[k] ?? STATE_METRICS[k as StateMetric]
}

export const REGULATORY_KIND_LABELS: Record<RegulatoryKind, string> = {
  ai_act: 'AI act',
  export_control: 'Export control',
  licensing: 'Licensing',
  state_law: 'State law',
  guidance: 'Guidance',
  localization: 'Data localization',
}

// ---------- Phase 6 ----------

/** Economy tiles for the embodied series (contracts §20); shown only when the document has them. */
export const EMBODIED_TILES: Array<{ key: EmbodiedMetric; def: MetricDef }> = [
  {
    key: 'embodied_displacement_share',
    def: {
      label: 'Embodied displacement',
      short: 'Embodied',
      unit: '% of task-hours',
      polarity: 'magnitude',
      format: (v) => (v == null || !Number.isFinite(v) ? '—' : `${v.toFixed(1)}%`),
      axisFormat: (v) => `${Number(v.toFixed(1))}%`,
    },
  },
  {
    key: 'adjacent_jobs',
    def: {
      label: 'Adjacent and hardware jobs',
      short: 'Adjacent jobs',
      unit: 'jobs vs baseline (count)',
      polarity: 'magnitude',
      format: (v) => fmtCompact(v),
      axisFormat: (v) => fmtCompact(v),
    },
  },
]

// ---------- Phase 7 ----------

/** Caption under the consumer-surplus proxy wherever it is shown (contracts §24). */
export const SURPLUS_CAPTION = 'accounting proxy at baseline prices, not welfare'

/**
 * Economy tiles for the Phase 7 series (contracts §24). The consumer-surplus proxy is shown when
 * the series exists; the traded-services tile only for regions where the share is nonzero
 * (exporters: IN, RoA and EU members), see `seriesIsNonzero`.
 */
export const APPLICATION_TILES: Array<{
  key: ApplicationMetric
  def: MetricDef
  note?: string
  /** hide the tile when every median value is zero */
  nonzeroOnly?: boolean
}> = [
  {
    key: 'consumer_surplus_proxy_bn',
    def: {
      label: 'Consumer-surplus proxy',
      short: 'Surplus proxy',
      unit: '$bn per year, AI content at baseline prices',
      polarity: 'magnitude',
      format: (v) => fmtBn(v),
      axisFormat: (v) => fmtBn(v),
    },
    note: SURPLUS_CAPTION,
  },
  {
    key: 'traded_services_displacement_share',
    def: {
      label: 'Traded-services displacement',
      short: 'Traded services',
      unit: '% of employment, export-serving workers',
      polarity: 'magnitude',
      format: (v) => (v == null || !Number.isFinite(v) ? '—' : `${v.toFixed(v < 1 ? 3 : 2)}%`),
      axisFormat: (v) => `${Number(v.toFixed(3))}%`,
    },
    nonzeroOnly: true,
  },
]

/** True when any median value of the series is nonzero (the traded share is zero for importers). */
export function seriesIsNonzero(s: { p50: number[] } | undefined | null): boolean {
  return !!s && s.p50.some((v) => Number.isFinite(v) && v !== 0)
}

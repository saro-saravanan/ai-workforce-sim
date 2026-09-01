/**
 * Results document types, hand-written from docs/contracts.md §2 (contracts v0.2).
 * Every time-indexed array is aligned to `meta.quarters`.
 */

/** A stochastic series: Phase 1 emits `p50` only; render a band whenever p10/p90 exist. */
export interface Series {
  p50: number[]
  p10?: number[]
  p90?: number[]
  p25?: number[]
  p75?: number[]
}

export type DataFlag = 'FIXTURE' | 'real' | 'partial' | 'unavailable' | string

export interface ResultsMeta {
  spec_version: string
  schema_version: string
  scenario_id: string
  scenario_hash: string
  seed: number
  run_at: string
  draws: number
  ensemble: string
  quarters: string[]
  regions: string[]
  baseline: string
  data_flags: {
    occ_state: DataFlag
    occ_sector: DataFlag
    aei_anchoring: DataFlag
    [key: string]: DataFlag
  }
  capability_units: string
}

export type NationalMetric =
  | 'gdp_pct_vs_baseline'
  | 'employment_pct_vs_baseline'
  | 'real_wage_pct_vs_baseline'
  | 'nominal_wage_pct_vs_baseline'
  | 'wage_share_pp_vs_baseline'
  | 'tfp_pct_vs_baseline'
  | 'price_index_pct_vs_baseline'
  | 'displaced_workers_cum'
  | 'adoption_share'
  | 'ai_spend_bn'
  | 'capability_index'
  | 'capability_horizon_hours'

export type RegionSeries = Record<NationalMetric, Series>

export interface OccupationResult {
  occ_code: string
  title: string
  cluster_id: string
  major_group: string
  emp0: number
  wage0: number
  automatable_share: number
  exposure_beta: number
  displacement: Series
  employment_pct_vs_baseline: Series
  real_wage_pct_vs_baseline: Series
}

export type StateMetric =
  'employment_pct_vs_baseline' | 'real_wage_pct_vs_baseline' | 'displaced_workers_cum'

export interface StateResult {
  fips: string
  name: string
  employment_pct_vs_baseline: Series
  real_wage_pct_vs_baseline: Series
  displaced_workers_cum: Series
}

export type ChannelName =
  | 'automation'
  | 'augmentation'
  | 'demand_response'
  | 'reinstatement'
  | 'demand_feedback'
  | 'ai_investment'

export interface ChannelDecomposition {
  order: ChannelName[]
  contributions: Partial<Record<ChannelName, number[]>>
}

export interface ResultsDocument {
  meta: ResultsMeta
  series: Record<string, RegionSeries>
  occupations: OccupationResult[]
  states: StateResult[]
  channels: Partial<Record<NationalMetric, ChannelDecomposition>>
  explain: { notes: string[] }
}

/** GET /api/scenarios */
export interface ScenarioSummary {
  id: string
  name: string
  parent: string | null
  description: string
}

/** POST /api/run */
export interface RunResponse {
  scenario_hash: string
  meta: ResultsMeta
}

/** GET /api/geo/us-states — properties per contracts §3 */
export interface StateProperties {
  fips: string
  name: string
  abbrev: string
}

export interface StateFeature {
  type: 'Feature'
  properties: StateProperties
  geometry: GeoJSON.Geometry
}

export interface StatesGeoJSON {
  type: 'FeatureCollection'
  features: StateFeature[]
}

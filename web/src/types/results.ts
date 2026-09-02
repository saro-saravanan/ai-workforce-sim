/**
 * Results document types, hand-written from docs/contracts.md §2 (v0.2) and §7–10 (v0.3, Phase 2).
 * Every time-indexed array is aligned to `meta.quarters`.
 */

/**
 * A stochastic series. Phase 1 emits `p50` only; Phase 2 adds p10/p25/p75/p90 and `central`
 * (the central-parameter run). Render a band whenever p10/p90 exist.
 */
export interface Series {
  p50: number[]
  p10?: number[]
  p90?: number[]
  p25?: number[]
  p75?: number[]
  central?: number[]
}

export type PercentileKey = 'p10' | 'p25' | 'p50' | 'p75' | 'p90'

export type DataFlag = 'FIXTURE' | 'real' | 'partial' | 'unavailable' | string

export interface ResultsMeta {
  spec_version: string
  schema_version: string
  scenario_id: string
  scenario_hash: string
  seed: number
  run_at: string
  draws: number
  ensemble: 'all' | 'central' | string
  /** Phase 2: the 8 mechanism-cell ids, e.g. "bessen|acemoglu_low|passthrough_low" */
  cells?: string[]
  /** Phase 2: [10, 25, 50, 75, 90] */
  percentiles?: number[]
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

/** The four metrics that carry structural / confidence / tornado / trace sections. */
export type HeadlineMetric =
  | 'employment_pct_vs_baseline'
  | 'gdp_pct_vs_baseline'
  | 'real_wage_pct_vs_baseline'
  | 'wage_share_pp_vs_baseline'

export const HEADLINE_METRICS: HeadlineMetric[] = [
  'employment_pct_vs_baseline',
  'gdp_pct_vs_baseline',
  'real_wage_pct_vs_baseline',
  'wage_share_pp_vs_baseline',
]

/** Phase 3: rents accruing to a region by value-chain stage (spec §6.3), $bn per quarter-year. */
export type RentStage = 'model' | 'compute' | 'chips' | 'integration'
export const RENT_STAGES: RentStage[] = ['model', 'compute', 'chips', 'integration']
export type RentsByStage = Record<RentStage | 'total', Series>

export type RegionSeries = Record<NationalMetric, Series> & {
  /** Phase 3 (contracts §12) */
  ai_rents_received_bn?: RentsByStage
}

/** Phase 3 region ids (contracts §11), in display order. */
export type RegionId = 'US' | 'EU' | 'UK' | 'CN' | 'JP' | 'KR' | 'IN' | 'TW' | 'SG' | 'RoA'
export const REGION_IDS: RegionId[] = ['US', 'EU', 'UK', 'CN', 'JP', 'KR', 'IN', 'TW', 'SG', 'RoA']
export const REGION_NAMES: Record<RegionId, string> = {
  US: 'United States',
  EU: 'European Union',
  UK: 'United Kingdom',
  CN: 'China',
  JP: 'Japan',
  KR: 'South Korea',
  IN: 'India',
  TW: 'Taiwan',
  SG: 'Singapore',
  RoA: 'Rest of Asia',
}
export function isRegionId(v: unknown): v is RegionId {
  return typeof v === 'string' && (REGION_IDS as string[]).includes(v)
}

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
  /** Phase 3: central-only paths for the non-U.S. regions (contracts §12) */
  by_region?: Record<string, OccupationByRegion>
}

export interface OccupationByRegion {
  displacement: Pick<Series, 'central'> & { central: number[] }
  employment_pct_vs_baseline: Pick<Series, 'central'> & { central: number[] }
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

// ---------- Phase 2 sections (contracts §8) ----------

/** Reference quarters at which confidence, spread and trace are reported. */
export type ReferenceQuarter = '2030Q4' | '2040Q4' | string

export interface StructuralSpread {
  /** mean within-cell p90 − p10 */
  parametric_pp: number
  /** range of cell medians */
  structural_pp: number
}

export interface StructuralSection {
  by_cell: Record<string, { p50: number[] }>
  spread: Record<ReferenceQuarter, StructuralSpread>
}

export type ConfidenceLevel = 'high' | 'medium' | 'low'

export interface Confidence {
  level: ConfidenceLevel
  /** share of draws (pooled) with the median's sign */
  sign_share: number
  cells_agree: boolean
  /** parameters whose range flips the sign (spec §7.3) */
  flip_params: string[]
}

export type ParamTag = 'S' | 'D' | 'E'

export interface TornadoRow {
  param: string
  name: string
  tag: ParamTag
  low: number
  high: number
  effect_at_low: number
  effect_at_high: number
}

export interface CohortRow {
  /** "16-24", "hs", "3" … */
  band: string
  employment_pct_vs_baseline: Series
  share_of_jobs_lost: Series
}

export type CohortFacet = 'age' | 'education' | 'income_decile'

export type CohortsSection = Record<CohortFacet, CohortRow[]>

export interface FlowOrigin {
  major_group: string
  title: string
  jobs_lost_cum: Series
}

export type FlowDestination =
  | 'reemployed'
  | 'retraining'
  | 'unemployed'
  | 'exited'
  | 'retired'
  | 'unfilled_entry'

export const FLOW_DESTINATIONS: FlowDestination[] = [
  'reemployed',
  'retraining',
  'unemployed',
  'exited',
  'retired',
  'unfilled_entry',
]

export interface FlowsSection {
  origins: FlowOrigin[]
  destinations: Record<FlowDestination, Series>
}

export type TraceKey =
  | 'automatable_share'
  | 'realized_D'
  | 'realized_U'
  | 'adoption_emp'
  | 'dln_unit_cost'
  | 'q_ratio'
  | 'mu'
  | 'nu'
  | 'price_index'

export type Trace = Record<TraceKey, number>

export interface DiffEntry {
  /** canonical JSON path, e.g. "levers.regulation.EU.ai_act" or "shocks[deepseek-open-2027]" */
  path: string
  from: unknown
  to: unknown
  mechanism: string
}

export interface ExplainSection {
  notes: string[]
  /** Phase 2: per headline metric, per reference quarter */
  trace?: Partial<Record<HeadlineMetric, Record<ReferenceQuarter, Trace>>>
  /** Phase 2: canonical diff vs parent */
  diff?: DiffEntry[]
}

export interface ResultsDocument {
  meta: ResultsMeta
  series: Record<string, RegionSeries>
  occupations: OccupationResult[]
  states: StateResult[]
  channels: Partial<Record<NationalMetric, ChannelDecomposition>>
  explain: ExplainSection
  structural?: Partial<Record<HeadlineMetric, StructuralSection>>
  confidence?: Partial<Record<HeadlineMetric, Record<ReferenceQuarter, Confidence>>>
  tornado?: Partial<Record<HeadlineMetric, TornadoRow[]>>
  cohorts?: CohortsSection
  flows?: FlowsSection
  // ---------- Phase 3 (contracts §12) ----------
  regions?: RegionInfo[]
  world?: WorldEntry[]
  supply?: SupplySection
}

// ---------- Phase 3 sections (contracts §12–13) ----------

export interface RegionInfo {
  region_id: RegionId | string
  name: string
  employment_total: number
  gdp_bn_usd: number
  data_flags: Record<string, DataFlag>
}

/** Slim series: p10/p50/p90 only (document size). */
export type SlimSeries = Pick<Series, 'p10' | 'p50' | 'p90'>

export type WorldMetric = 'employment_pct_vs_baseline' | 'real_wage_pct_vs_baseline'

/** One entry per Natural Earth country in a modelled region; members carry their region's series. */
export interface WorldEntry {
  iso3: string
  name: string
  region_id: RegionId | string
  employment_pct_vs_baseline: SlimSeries
  real_wage_pct_vs_baseline: SlimSeries
}

export type CentralSeries = { central: number[] }

export interface SupplyRelease {
  actor_id: string
  name: string
  region_id: RegionId | string
  model: string
  /** YYYY-MM-DD */
  date: string
  /** "2025Q3" */
  quarter: string
  /** doublings on the METR clock, or null when the model is not on the METR series */
  capability_index: number | null
  open_weights: boolean
}

export type RegulatoryKind =
  | 'ai_act'
  | 'export_control'
  | 'licensing'
  | 'state_law'
  | 'guidance'
  | 'localization'
  | string

export interface RegulatoryEvent {
  event_id: string
  region: RegionId | string
  date: string
  quarter: string
  kind: RegulatoryKind
  description: string
}

export interface SupplySection {
  /** the global frontier clock, capability index (doublings) */
  clock: Series
  /** 2^clock / 60, hours */
  horizon_hours: Series
  /** available capability per region (contracts §12, central only) */
  regional_capability: Record<string, CentralSeries>
  price_frontier_usd_per_mtok: CentralSeries
  price_fixed_capability_usd_per_mtok: CentralSeries
  releases: SupplyRelease[]
  regulatory_events: RegulatoryEvent[]
  /** region → actor → 0/1 per quarter */
  availability: Record<string, Record<string, number[]>>
  market_share: Record<string, Record<string, CentralSeries>>
}

/** GET /api/regions — regions.csv rows (only the columns the web app reads are typed). */
export interface RegionRow {
  region_id: RegionId | string
  name: string
  population?: number
  gdp_bn_usd?: number
  employment_total?: number
  regime?: string
  data_center_share?: number
  [key: string]: unknown
}

/** GET /api/actors */
export interface ActorRow {
  actor_id: string
  name: string
  region_id: RegionId | string
  role: 'lab' | 'compute' | 'chokepoint' | string
  weights_posture: 'closed' | 'open-lagged' | 'open-frontier' | string
  [key: string]: unknown
}
export interface ActorsResponse {
  actors: ActorRow[]
  releases: SupplyRelease[]
}

/** GET /api/geo/world — Natural Earth 110m admin-0 reduced to {iso3, name, region_id} */
export interface WorldProperties {
  iso3: string
  name: string
  /** "" for countries outside the ten regions */
  region_id: RegionId | '' | string
}
export interface WorldFeature {
  type: 'Feature'
  properties: WorldProperties
  geometry: GeoJSON.Geometry
}
export interface WorldGeoJSON {
  type: 'FeatureCollection'
  features: WorldFeature[]
}

// ---------- scenarios and API (contracts §3, §9) ----------

/** GET /api/scenarios */
export interface ScenarioSummary {
  id: string
  name: string
  parent: string | null
  description: string
  /** report-replication preset (spec §8.4) */
  preset?: boolean
  /** saved by a user through POST /api/scenarios */
  user?: boolean
}

/** A scenario document (scenarios/schema.json). Levers are a nested plain object. */
export interface ScenarioDocument {
  schema_version: '0.2'
  id: string
  name: string
  description?: string
  parent: string | null
  created?: string
  author?: string
  seed?: number
  draws?: number
  horizon?: { start?: string; end?: string }
  levers?: Record<string, unknown>
  shocks?: Array<Record<string, unknown> & { id: string; type: string; at: string }>
  overrides?: Record<string, { central?: number; min?: number; max?: number }>
  remove_shocks?: string[]
  ensemble?: { mechanisms?: 'all' | 'central'; shapley?: boolean }
  preset?: boolean
  user?: boolean
}

/** POST /api/run */
export interface RunResponse {
  scenario_hash: string
  meta: ResultsMeta
}

export type LeverGroup = 'capability' | 'cost' | 'regulation' | 'adoption' | 'labor' | 'policy'

/** GET /api/levers */
export interface LeverDef {
  /** dotted path into the scenario document, e.g. "levers.capability.doubling_months" */
  path: string
  label: string
  group: LeverGroup | string
  type: 'number' | 'enum' | 'boolean'
  min?: number
  max?: number
  step?: number
  default?: number | string | boolean
  unit?: string
  /** enum options (type === 'enum') */
  options?: string[]
  /** registry parameter id, e.g. "P.01" */
  param?: string
  mechanism?: string
}

/** GET /api/compare?a=&b= */
export interface CompareResponse {
  diff: DiffEntry[]
  delta: {
    series: Partial<Record<NationalMetric, Pick<Series, 'p10' | 'p50' | 'p90'>>>
    states: Array<{ fips: string; employment_pct_vs_baseline: { p50: number[] } }>
    occupations: Array<{ occ_code: string; displacement: { p50: number[] } }>
  }
  confidence: Partial<Record<HeadlineMetric, Record<ReferenceQuarter, Confidence>>>
}

/** GET /api/explain/{hash}?metric=&quarter= */
export interface ExplainResponse {
  value: Partial<Record<PercentileKey | 'central', number>>
  channels: Partial<Record<ChannelName, number>>
  trace: Trace
  confidence: Confidence
  top_params: TornadoRow[]
  notes: string[]
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

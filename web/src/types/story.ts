/**
 * Story layer types (contracts §26–27): the story document behind the Story view and the
 * executive brief, and the personal outlook. Every number is read from the results document by
 * the server (`api/aiwsim_api/story.py`) or, in static and mock modes, by `lib/outlook.ts`.
 */
import type { ConfidenceLevel, ForecastRow, SlimSeries } from '@/types/results'

export type BeatId = 'jobs' | 'hiring' | 'young' | 'pay' | 'waves' | 'money' | 'futures'
export const BEAT_IDS: BeatId[] = ['jobs', 'hiring', 'young', 'pay', 'waves', 'money', 'futures']

/** high → "we would bet on it" (3 dots), medium → "leaning this way" (2), low → "a coin flip" (1) */
export interface Sureness {
  level: ConfidenceLevel | string
  label: string
  dots: number
}

export interface FanChart {
  type: 'fan'
  series: { employment: SlimSeries; gdp: SlimSeries }
  quarters: string[]
}

export interface BarsChart {
  type: 'bars'
  items: Array<[string, number]>
  /** a thin reference bar under each item (the age beat: each band's share of employment) */
  reference?: Array<[string, number]>
  unit?: string
}

export interface TimelineItem {
  app: string
  family: string
  family_words: string
  /** the year the application first displaces 1% of its target task-hours; null when not by the horizon */
  first_year: string | null
  share_2030: number
  share_2040: number
  target_jobs: number
}

export interface TimelineChart {
  type: 'timeline'
  items: TimelineItem[]
  start: number
  end: number
}

/** [region, employment_pct, gdp_pct, rents_bn] */
export interface RegionsChart {
  type: 'regions'
  items: Array<[string, number, number, number]>
}

export interface FuturesChart {
  type: 'futures'
  items: StoryFuture[]
}

export type StoryChart = FanChart | BarsChart | TimelineChart | RegionsChart | FuturesChart

export interface StoryFuture {
  name: string
  /** set for futures that are scenario runs (the Seba/RethinkX preset); openable in the app */
  scenario_id?: string
  employment_pct: number
  gdp_pct: number | null
  /** jobs fewer than the no-AI world (negative = more jobs) */
  jobs: number
  source: string
  description: string
}

export interface BeatOccupations {
  hit_first: Array<[string, number]>
  hit_most: Array<[string, number]>
  growing: Array<[string, number]>
}

export interface StoryBeat {
  id: BeatId | string
  title: string
  sentence: string
  range: string
  sureness: Sureness
  what_changes_it: string
  chart: StoryChart
  occupations?: BeatOccupations
}

export interface StoryPolicy {
  scenario_id: string
  name: string
  description: string
  jobs_delta: number
  employment_delta_pp: number
  unemployed_delta: number
  real_wage_delta_pp: number
  cost_bn_per_year: number
  ai_tax_revenue_bn: number
  fiscal_balance_bn: number
  /** the fiscal warning (§28) when the run is outside the model's range, else "" */
  validity_note: string
  sentence: string
}

export interface StoryNumbers {
  jobs_base: number
  jobs_gap: number
  jobs_gap_low: number
  jobs_gap_high: number
  employment_pct: { p10: number; p50: number; p90: number }
  displaced_cum: number
  reemployed: number
  unemployed_extra: number
  exited: number
  unfilled: number
  laid_off: number
  hours_cut_self: number
  jobs_removed_by_channel: Record<string, number>
  jobs_added_by_channel: Record<string, number>
  unemployment_peak: { quarter: string; extra: number }
  gdp_pct: number
  real_wage_pct: { p10: number; p50: number; p90: number }
  price_index_pct: number
  wage_share_pp: number
  /** one paragraph keeping the jobs ledger and the people ledger apart */
  reconciliation: string
}

/** GET /api/story/{hash}?region= (contracts §26) */
export interface StoryDocument {
  scenario_hash: string
  scenario_id: string | null
  scenario_name: string | null
  region: string
  horizon: [string, string]
  numbers: StoryNumbers
  beats: StoryBeat[]
  futures: StoryFuture[]
  policies: StoryPolicy[]
  /** the run the policy differences are read against */
  policies_against: string | null
  caveats: string[]
  forecasts: ForecastRow[]
  glossary: Record<string, string>
}

export type OutlookVerdict =
  | 'among the hardest hit'
  | 'harder hit than most'
  | 'about average'
  | 'less affected than most'
  | 'among the most protected'

export interface OutlookOccupation {
  occ_code: string
  title: string
  employment_2024: number
  employment_pct_2030: number
  employment_pct_2040: number
  range_2040: [number, number]
  /** percent of the occupation's task-hours automated by 2040, by channel family */
  task_hours_automated_2040: { software: number; machines: number }
  real_wage_pct_2040: number
  rank_percentile: number
  verdict: OutlookVerdict | string
  how: string
  growing_nearby: Array<[string, number]>
  sentence: string
}

export interface OutlookAge {
  band: string
  share_of_jobs_lost: number
  employment_pct_2040: number
  sentence: string
}

/** GET /api/outlook/{hash}?occ=&age=&region= (contracts §27) */
export interface OutlookResponse {
  region: string
  /** "" for the U.S.; says the detail is U.S. figures elsewhere */
  note: string
  beats: StoryBeat[]
  sureness_legend: Record<string, [string, number]>
  occupation?: OutlookOccupation
  age?: OutlookAge
}

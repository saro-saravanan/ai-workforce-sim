import type { NationalMetric, StateMetric } from '@/types/results'
import { fmtCompact, fmtPct, fmtPp, fmtShare } from './format'

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
  demand_response: 'Demand response',
  reinstatement: 'Reinstatement',
  demand_feedback: 'Demand feedback',
  ai_investment: 'AI investment',
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

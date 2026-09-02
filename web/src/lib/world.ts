/**
 * World aggregates (Phase 3). The results document carries one series block per region; "World"
 * is computed client-side from `regions[].employment_total` and each region's series:
 *   - percentage / point metrics: employment-weighted mean of each percentile (an approximation —
 *     a weighted mean of regional percentiles is not the percentile of the weighted sum);
 *   - counts and dollars (displaced workers, AI spend, rents): sums;
 *   - the capability clock: the frontier, i.e. the maximum over regions.
 */
import type {
  NationalMetric,
  RegionInfo,
  RegionSeries,
  RentsByStage,
  ResultsDocument,
  Series,
} from '@/types/results'
import { RENT_STAGES } from '@/types/results'

export type WorldRule = 'weighted' | 'sum' | 'max'

export const WORLD_RULE: Record<NationalMetric, WorldRule> = {
  gdp_pct_vs_baseline: 'weighted',
  employment_pct_vs_baseline: 'weighted',
  real_wage_pct_vs_baseline: 'weighted',
  nominal_wage_pct_vs_baseline: 'weighted',
  wage_share_pp_vs_baseline: 'weighted',
  tfp_pct_vs_baseline: 'weighted',
  price_index_pct_vs_baseline: 'weighted',
  displaced_workers_cum: 'sum',
  adoption_share: 'weighted',
  ai_spend_bn: 'sum',
  capability_index: 'max',
  capability_horizon_hours: 'max',
}

export const WORLD_RULE_LABEL: Record<WorldRule, string> = {
  weighted: 'employment-weighted mean of the regions',
  sum: 'sum over the regions',
  max: 'frontier (maximum over the regions)',
}

const KEYS = ['p10', 'p25', 'p50', 'p75', 'p90', 'central'] as const
type Key = (typeof KEYS)[number]

/** Combines one series per region under a rule; a percentile key is kept only if every region has it. */
export function aggregateSeries(
  parts: Array<{ weight: number; series: Series }>,
  rule: WorldRule,
): Series | null {
  const usable = parts.filter((p) => p.series && p.series.p50.length > 0)
  if (!usable.length) return null
  const n = Math.max(...usable.map((p) => p.series.p50.length))
  const out: Partial<Record<Key, number[]>> = {}
  for (const k of KEYS) {
    if (!usable.every((p) => p.series[k])) continue
    const arr: number[] = []
    for (let i = 0; i < n; i++) {
      let acc = rule === 'max' ? Number.NEGATIVE_INFINITY : 0
      let wsum = 0
      for (const p of usable) {
        const v = p.series[k]![i]
        if (v == null || !Number.isFinite(v)) continue
        if (rule === 'weighted') {
          acc += v * p.weight
          wsum += p.weight
        } else if (rule === 'sum') acc += v
        else acc = Math.max(acc, v)
      }
      if (rule === 'weighted') arr.push(wsum > 0 ? acc / wsum : 0)
      else arr.push(Number.isFinite(acc) ? acc : 0)
    }
    out[k] = arr
  }
  if (!out.p50) return null
  return out as Series
}

/** Employment weights from `regions[]`; regions missing there get weight 0 (they still count in sums). */
export function employmentWeights(regions: RegionInfo[]): Map<string, number> {
  return new Map(regions.map((r) => [r.region_id, r.employment_total]))
}

export function worldAggregate(
  regions: RegionInfo[],
  series: Record<string, RegionSeries>,
): RegionSeries | null {
  const ids = Object.keys(series)
  if (!ids.length) return null
  if (ids.length === 1) return series[ids[0]!] ?? null
  const w = employmentWeights(regions)
  const out: Partial<Record<NationalMetric, Series>> = {}
  for (const m of Object.keys(WORLD_RULE) as NationalMetric[]) {
    const parts = ids
      .filter((id) => series[id]?.[m])
      .map((id) => ({ weight: w.get(id) ?? 0, series: series[id]![m] }))
    const s = aggregateSeries(parts, WORLD_RULE[m])
    if (s) out[m] = s
  }
  if (!out.employment_pct_vs_baseline) return null
  const rentParts = ids.filter((id) => series[id]?.ai_rents_received_bn)
  let rents: RentsByStage | undefined
  if (rentParts.length) {
    const r: Partial<RentsByStage> = {}
    for (const st of [...RENT_STAGES, 'total'] as const) {
      const s = aggregateSeries(
        rentParts.map((id) => ({ weight: 1, series: series[id]!.ai_rents_received_bn![st] })),
        'sum',
      )
      if (s) r[st] = s
    }
    if (r.total) rents = r as RentsByStage
  }
  return { ...(out as Record<NationalMetric, Series>), ai_rents_received_bn: rents }
}

/** The series block a view should read for a region selection ('world' or a region id). */
export function seriesFor(doc: ResultsDocument | null, region: string): RegionSeries | null {
  if (!doc) return null
  if (region === 'world') return worldAggregate(doc.regions ?? [], doc.series)
  return doc.series[region] ?? null
}

import { describe, expect, it } from 'vitest'
import { aggregateSeries, seriesFor, worldAggregate } from '../world'
import type { RegionInfo, RegionSeries, ResultsDocument, Series } from '@/types/results'

const ser = (p50: number[], extra: Partial<Series> = {}): Series => ({ p50, ...extra })

function region(v: number, withBand = true): RegionSeries {
  const base = [v, v * 2]
  const s = (k: number) => ser(base.map((x) => x * k), withBand ? { p10: base.map((x) => x * k - 1), p90: base.map((x) => x * k + 1), central: base.map((x) => x * k) } : {})
  return {
    gdp_pct_vs_baseline: s(1),
    employment_pct_vs_baseline: s(1),
    real_wage_pct_vs_baseline: s(1),
    nominal_wage_pct_vs_baseline: s(1),
    wage_share_pp_vs_baseline: s(1),
    tfp_pct_vs_baseline: s(1),
    price_index_pct_vs_baseline: s(1),
    displaced_workers_cum: s(1000),
    adoption_share: s(0.1),
    ai_spend_bn: s(10),
    capability_index: s(1),
    capability_horizon_hours: s(1),
    ai_rents_received_bn: { model: s(1), compute: s(1), chips: s(1), integration: s(1), total: s(4) },
  }
}
const regions: RegionInfo[] = [
  { region_id: 'US', name: 'United States', employment_total: 100, gdp_bn_usd: 1, data_flags: {} },
  { region_id: 'EU', name: 'European Union', employment_total: 300, gdp_bn_usd: 1, data_flags: {} },
]

describe('aggregateSeries', () => {
  it('takes an employment-weighted mean of every percentile that all parts carry', () => {
    const out = aggregateSeries(
      [
        { weight: 1, series: ser([1, 1], { p10: [0, 0], p90: [2, 2] }) },
        { weight: 3, series: ser([5, 9], { p10: [4, 8] }) },
      ],
      'weighted',
    )
    expect(out?.p50).toEqual([4, 7])
    expect(out?.p10).toEqual([3, 6])
    expect(out?.p90).toBeUndefined() // not on every part
  })
  it('sums and takes the frontier', () => {
    const parts = [
      { weight: 1, series: ser([1, 2]) },
      { weight: 2, series: ser([3, 1]) },
    ]
    expect(aggregateSeries(parts, 'sum')?.p50).toEqual([4, 3])
    expect(aggregateSeries(parts, 'max')?.p50).toEqual([3, 2])
  })
  it('returns null with no parts', () => {
    expect(aggregateSeries([], 'sum')).toBeNull()
  })
})

describe('worldAggregate', () => {
  const series = { US: region(-4), EU: region(-2) }
  it('weights percentage metrics by employment_total', () => {
    const w = worldAggregate(regions, series)!
    // (100 × −4 + 300 × −2) / 400 = −2.5
    expect(w.employment_pct_vs_baseline.p50[0]).toBeCloseTo(-2.5)
    expect(w.employment_pct_vs_baseline.p10?.[0]).toBeCloseTo(-3.5)
    expect(w.employment_pct_vs_baseline.central?.[0]).toBeCloseTo(-2.5)
  })
  it('sums counts, dollars and rents, and takes the capability frontier', () => {
    const w = worldAggregate(regions, series)!
    expect(w.displaced_workers_cum.p50[0]).toBe(-6000)
    expect(w.ai_spend_bn.p50[1]).toBe(-120)
    expect(w.capability_index.p50[0]).toBe(-2)
    expect(w.ai_rents_received_bn?.total.p50[0]).toBe(-24)
    expect(w.ai_rents_received_bn?.model.p50[0]).toBe(-6)
  })
  it('passes a single region through and ignores unknown weights', () => {
    expect(worldAggregate(regions, { US: series.US })).toBe(series.US)
    const w = worldAggregate([], { US: region(2, false), EU: region(4, false) })!
    // both weights 0 → falls back to 0 for weighted metrics, sums still work
    expect(w.employment_pct_vs_baseline.p50[0]).toBe(0)
    expect(w.employment_pct_vs_baseline.p10).toBeUndefined()
    expect(w.ai_spend_bn.p50[0]).toBe(60)
  })
  it('seriesFor picks the region block or the world aggregate', () => {
    const doc = { series, regions } as unknown as ResultsDocument
    expect(seriesFor(doc, 'EU')).toBe(series.EU)
    expect(seriesFor(doc, 'XX')).toBeNull()
    expect(seriesFor(doc, 'world')?.employment_pct_vs_baseline.p50[0]).toBeCloseTo(-2.5)
    expect(seriesFor(null, 'US')).toBeNull()
  })
})

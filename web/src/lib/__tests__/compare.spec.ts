import { describe, expect, it } from 'vitest'
import type { ResultsDocument, Series } from '@/types/results'
import { deltaSignShare, pairedCompare, pairedDeltaSeries } from '../compare'

const a: Series = { p50: [0, -1, -2], p10: [0, -2, -4], p90: [0, 0, 0] }
const b: Series = { p50: [0, -1.5, -3], p10: [0, -2.5, -5], p90: [0, -0.5, -1] }

describe('pairedDeltaSeries', () => {
  it('takes B − A of the medians', () => {
    const d = pairedDeltaSeries(a, b)
    expect(d.p50).toEqual([0, -0.5, -1])
  })
  it('band is symmetric around the median and narrower than the marginal bands when paired', () => {
    const d = pairedDeltaSeries(a, b, 0.8)
    const halfWidth = (d.p90[2]! - d.p10[2]!) / 2
    expect(d.p50[2]! - d.p10[2]!).toBeCloseTo(halfWidth, 9)
    // marginal σ ≈ 4/2.5631 for both; paired σ ≈ σ√(2 − 2ρ) < σ
    const marginalHalf = 1.2816 * (4 / 2.5631)
    expect(halfWidth).toBeLessThan(marginalHalf)
    expect(halfWidth).toBeGreaterThan(0)
    // uncorrelated draws give a wider band than paired ones
    const d0 = pairedDeltaSeries(a, b, 0)
    expect(d0.p90[2]! - d0.p10[2]!).toBeGreaterThan(d.p90[2]! - d.p10[2]!)
  })
  it('degrades to zero-width band when no percentiles exist', () => {
    const d = pairedDeltaSeries({ p50: [1, 2] }, { p50: [2, 4] })
    expect(d).toEqual({ p10: [1, 2], p50: [1, 2], p90: [1, 2] })
  })
  it('sign share is 1 for a band wholly on one side and 0.5 at zero', () => {
    expect(deltaSignShare({ p10: [-3], p50: [-2], p90: [-1] }, 0)).toBeGreaterThan(0.99)
    expect(deltaSignShare({ p10: [-1], p50: [0], p90: [1] }, 0)).toBeCloseTo(0.5, 6)
  })
})

function doc(id: string, s: Series): ResultsDocument {
  return {
    meta: {
      spec_version: '0.2',
      schema_version: '0.3',
      scenario_id: id,
      scenario_hash: `sha256:${id}`,
      seed: 42,
      run_at: '',
      draws: 200,
      ensemble: 'all',
      quarters: ['2030Q4', '2035Q4', '2040Q4'],
      regions: ['US'],
      baseline: 'x',
      data_flags: { occ_state: 'FIXTURE', occ_sector: 'FIXTURE', aei_anchoring: 'unavailable' },
      capability_units: '',
    },
    series: {
      US: {
        employment_pct_vs_baseline: s,
        gdp_pct_vs_baseline: s,
        real_wage_pct_vs_baseline: s,
        wage_share_pp_vs_baseline: s,
        nominal_wage_pct_vs_baseline: s,
        tfp_pct_vs_baseline: s,
        price_index_pct_vs_baseline: s,
        displaced_workers_cum: s,
        adoption_share: s,
        ai_spend_bn: s,
        capability_index: s,
        capability_horizon_hours: s,
      },
    },
    occupations: [
      {
        occ_code: '43-3031',
        title: 'x',
        cluster_id: 'c1',
        major_group: '43',
        emp0: 1,
        wage0: 1,
        automatable_share: 0.5,
        exposure_beta: 0.5,
        displacement: s,
        employment_pct_vs_baseline: s,
        real_wage_pct_vs_baseline: s,
      },
    ],
    states: [
      { fips: '39', name: 'Ohio', employment_pct_vs_baseline: s, real_wage_pct_vs_baseline: s, displaced_workers_cum: s },
    ],
    channels: {},
    explain: { notes: [], diff: [{ path: 'levers.x', from: 1, to: 2, mechanism: 'm' }] },
  }
}

describe('pairedCompare', () => {
  it('produces the /api/compare shape with paired deltas and confidence', () => {
    const r = pairedCompare(doc('baseline', a), doc('b', b))
    expect(r.delta.series.employment_pct_vs_baseline?.p50).toEqual([0, -0.5, -1])
    expect(r.delta.states[0]).toEqual({ fips: '39', employment_pct_vs_baseline: { p50: [0, -0.5, -1] } })
    expect(r.delta.occupations[0]?.occ_code).toBe('43-3031')
    expect(r.diff).toEqual([{ path: 'levers.x', from: 1, to: 2, mechanism: 'm' }])
    const c = r.confidence.employment_pct_vs_baseline
    expect(c?.['2030Q4']?.sign_share).toBe(1) // zero-width, zero delta: deterministic
    expect(c?.['2040Q4']?.level).toBe('medium') // paired z ≈ 1.0 → ~84% of draws share the sign
    expect(c?.['2040Q4']?.sign_share).toBeGreaterThan(0.7)
    expect(c?.['2040Q4']?.sign_share).toBeLessThan(0.9)
  })
})

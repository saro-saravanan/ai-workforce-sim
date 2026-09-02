import { describe, expect, it } from 'vitest'
import type { ResultsDocument, Series } from '@/types/results'
import {
  candidateInsights,
  mockBriefMarkdown,
  mockInsights,
  tornadoFlips,
  tornadoSwing,
} from '../insights'

const s = (p50: number[], spread = 1): Series => ({
  p50,
  p10: p50.map((v) => v - spread),
  p90: p50.map((v) => v + spread),
})

function fixture(): ResultsDocument {
  const quarters = ['2024Q1', '2030Q4', '2040Q4']
  const block = (emp: number[]) => ({
    gdp_pct_vs_baseline: s([0, 1, 3]),
    employment_pct_vs_baseline: s(emp),
    real_wage_pct_vs_baseline: s([0, 0.5, 1.5]),
    nominal_wage_pct_vs_baseline: s([0, 0, 0]),
    wage_share_pp_vs_baseline: s([0, -0.5, -1]),
    tfp_pct_vs_baseline: s([0, 1, 2]),
    price_index_pct_vs_baseline: s([0, -0.5, -1.5]),
    displaced_workers_cum: s([0, 1e6, 3e6]),
    adoption_share: s([5, 40, 80]),
    ai_spend_bn: s([10, 100, 300]),
    capability_index: s([0, 5, 10]),
    capability_horizon_hours: s([1, 10, 100]),
  })
  return {
    meta: {
      spec_version: '0.2',
      schema_version: '0.3',
      scenario_id: 'baseline',
      scenario_hash: 'sha256:test',
      seed: 1,
      run_at: '2026-01-01T00:00:00Z',
      draws: 10,
      ensemble: 'all',
      cells: ['a', 'b'],
      quarters,
      regions: ['US', 'EU'],
      baseline: 'frozen',
      data_flags: { occ_state: 'FIXTURE', occ_sector: 'real', aei_anchoring: 'real' },
      capability_units: 'doublings',
    },
    series: { US: block([0, -1, -2.5]), EU: block([0, -0.5, -1]) },
    occupations: [],
    states: [],
    channels: {},
    explain: { notes: ['note one'], diff: [] },
    confidence: {
      employment_pct_vs_baseline: {
        '2040Q4': { level: 'low', sign_share: 0.66, cells_agree: false, flip_params: ['P.61'] },
      },
    },
    tornado: {
      employment_pct_vs_baseline: [
        {
          param: 'P.20',
          name: 'Ever-automatable mass',
          tag: 'E',
          low: 0.5,
          high: 0.9,
          effect_at_low: -3.4,
          effect_at_high: -1.1,
        },
        {
          param: 'P.87',
          name: 'Demand multiplier',
          tag: 'S',
          low: 0.5,
          high: 1.5,
          effect_at_low: -2.8,
          effect_at_high: 0.4,
        },
        {
          param: 'P.60',
          name: 'Demand elasticity',
          tag: 'S',
          low: 0.3,
          high: 0.9,
          effect_at_low: -2.2,
          effect_at_high: -1.6,
        },
      ],
    },
    flows: {
      origins: [],
      destinations: {
        reemployed: s([0, 0, 200_000]),
        retraining: s([0, 0, 50_000]),
        unemployed: s([0, 0, 50_000]),
        exited: s([0, 0, 50_000]),
        retired: s([0, 0, 50_000]),
        unfilled_entry: s([0, 0, 600_000]),
      },
    },
  }
}

describe('tornado helpers', () => {
  it('swing is the absolute range; flips when the two ends differ in sign', () => {
    const rows = fixture().tornado!.employment_pct_vs_baseline!
    expect(tornadoSwing(rows[0]!)).toBeCloseTo(2.3, 9)
    expect(tornadoFlips(rows[0]!)).toBe(false)
    expect(tornadoFlips(rows[1]!)).toBe(true)
  })
})

describe('candidateInsights', () => {
  it('produces the ported candidates, sorted by surprise', () => {
    const out = candidateInsights(fixture(), 'US')
    const keys = out.map((c) => c.key)
    expect(keys).toEqual(
      expect.arrayContaining([
        'gdp_vs_employment',
        'hiring_channel',
        'dominant_parameter',
        'regional_divergence',
        'sign_confidence',
      ]),
    )
    for (let i = 1; i < out.length; i++)
      expect(out[i - 1]!.surprise).toBeGreaterThanOrEqual(out[i]!.surprise)
    for (const c of out) {
      expect(c.surprise).toBeGreaterThanOrEqual(0)
      expect(c.surprise).toBeLessThanOrEqual(1)
      expect(c.region).toBe('US')
    }
  })
  it('states the numbers it rests on', () => {
    const out = candidateInsights(fixture(), 'US')
    const gdp = out.find((c) => c.key === 'gdp_vs_employment')!
    expect(gdp.statement).toContain('+3.0%')
    expect(gdp.statement).toContain('-2.5%')
    expect(gdp.confidence).toBe('low')
    const hiring = out.find((c) => c.key === 'hiring_channel')!
    expect(hiring.statement).toContain('60%')
    expect(hiring.evidence.unfilled_share).toBeCloseTo(0.6, 6)
    const dom = out.find((c) => c.key === 'dominant_parameter')!
    // the largest swing is P.87 (3.2 pp), not the first row
    expect(dom.evidence.param).toBe('P.87')
    expect(dom.title).toContain('Demand multiplier')
    expect(dom.statement).toContain('flip the sign')
    const div = out.find((c) => c.key === 'regional_divergence')!
    expect(div.statement).toContain('(US)')
    expect(div.statement).toContain('(EU)')
  })
  it('skips the GDP-vs-employment candidate when both move the same way', () => {
    const d = fixture()
    d.series.US!.employment_pct_vs_baseline = s([0, 1, 2])
    expect(candidateInsights(d, 'US').some((c) => c.key === 'gdp_vs_employment')).toBe(false)
  })
  it('EU region reads the EU block and omits the U.S.-only hiring channel', () => {
    const out = candidateInsights(fixture(), 'EU')
    expect(out.some((c) => c.key === 'hiring_channel')).toBe(false)
    expect(out.find((c) => c.key === 'gdp_vs_employment')!.statement).toContain('In EU')
  })
})

describe('mockInsights', () => {
  it('returns the top n and every candidate', () => {
    const res = mockInsights(fixture(), 'US', 3)
    expect(res.top).toHaveLength(3)
    expect(res.candidates.length).toBeGreaterThanOrEqual(3)
    expect(res.scenario_hash).toBe('sha256:test')
    expect(res.top[0]).toEqual(res.candidates[0])
  })
  it('is empty without a document', () => {
    expect(mockInsights(null).top).toEqual([])
  })
})

describe('mockBriefMarkdown', () => {
  it('carries the headline table, the hash, findings and the compare section', () => {
    const d = fixture()
    const md = mockBriefMarkdown(d, 'US', d)
    expect(md).toContain('# baseline — AI workforce brief')
    expect(md).toContain('| Metric | 2030Q4 | 2040Q4 | Sign confidence (2040Q4) |')
    expect(md).toContain('| Employment | -1.0% [-2.0%, +0.0%] | -2.5% [-3.5%, -1.5%] | low |')
    expect(md).toContain('sha256:test')
    expect(md).toContain('## Findings')
    expect(md).toContain('## Paired comparison')
    expect(md).toContain('- note one')
  })
})

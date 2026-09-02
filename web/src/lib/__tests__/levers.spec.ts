import { describe, expect, it } from 'vitest'
import type { LeverDef, ScenarioDocument } from '@/types/results'
import {
  buildChildScenario,
  childScenarioId,
  clampLever,
  deepMerge,
  getPath,
  layoutLevers,
  leverDiff,
  leverLeaf,
  leverValues,
  leversPatch,
  resolveScenario,
  setPath,
} from '../levers'

const levers: LeverDef[] = [
  {
    path: 'levers.capability.doubling_months',
    label: 'Doubling',
    group: 'capability',
    type: 'number',
    min: 2,
    max: 36,
    step: 0.5,
    default: 6,
    unit: 'months',
    mechanism: 'clock',
  },
  {
    path: 'levers.regulation.EU.ai_act',
    label: 'EU AI Act',
    group: 'regulation',
    type: 'enum',
    options: ['repealed', 'baseline', 'delayed_2y'],
    default: 'baseline',
    mechanism: 'availability',
  },
  {
    path: 'levers.cost.compute_capacity_constraint',
    label: 'Compute constraint',
    group: 'cost',
    type: 'boolean',
    default: true,
  },
]

const baseline: ScenarioDocument = {
  schema_version: '0.2',
  id: 'baseline',
  name: 'Consensus central',
  parent: null,
  levers: {
    capability: { doubling_months: 6 },
    regulation: { EU: { ai_act: 'baseline' } },
    cost: { compute_capacity_constraint: true },
  },
  shocks: [{ id: 'old', type: 'recession', at: '2026Q1' }],
}
const child: ScenarioDocument = {
  schema_version: '0.2',
  id: 'eu-delay',
  name: 'EU delay',
  parent: 'baseline',
  levers: { regulation: { EU: { ai_act: 'delayed_2y' } } },
  shocks: [{ id: 'ds', type: 'open_weights_release', at: '2027Q1' }],
  remove_shocks: ['old'],
}

describe('levers form model', () => {
  it('reads and writes dotted paths', () => {
    expect(getPath(baseline, 'levers.regulation.EU.ai_act')).toBe('baseline')
    expect(getPath(baseline, 'levers.nope.x')).toBeUndefined()
    const o = setPath({} as Record<string, unknown>, 'a.b.c', 3)
    expect(o).toEqual({ a: { b: { c: 3 } } })
  })

  it('deep-merges child levers over the parent', () => {
    const m = deepMerge(baseline.levers, child.levers)
    expect(getPath(m, 'regulation.EU.ai_act')).toBe('delayed_2y')
    expect(getPath(m, 'capability.doubling_months')).toBe(6)
  })

  it('resolves inheritance with shocks keyed by id and remove_shocks', () => {
    const byId = new Map([
      ['baseline', baseline],
      ['eu-delay', child],
    ])
    const r = resolveScenario(child, byId)
    expect(r.id).toBe('eu-delay')
    expect(getPath(r, 'levers.capability.doubling_months')).toBe(6)
    expect(getPath(r, 'levers.regulation.EU.ai_act')).toBe('delayed_2y')
    expect(r.shocks?.map((s) => s.id)).toEqual(['ds'])
  })

  it('computes the diff vs parent only for changed levers', () => {
    const parentValues = leverValues(levers, baseline)
    expect(parentValues).toEqual({
      'levers.capability.doubling_months': 6,
      'levers.regulation.EU.ai_act': 'baseline',
      'levers.cost.compute_capacity_constraint': true,
    })
    const values = { ...parentValues, 'levers.capability.doubling_months': 4.5 }
    const diff = leverDiff(levers, parentValues, values)
    expect(diff).toEqual([
      { path: 'levers.capability.doubling_months', from: 6, to: 4.5, mechanism: 'clock' },
    ])
    expect(leverDiff(levers, parentValues, { ...parentValues })).toEqual([])
    // floating-point noise is not a change
    expect(
      leverDiff(levers, parentValues, { ...parentValues, 'levers.capability.doubling_months': 6 + 1e-12 }),
    ).toEqual([])
  })

  it('turns a diff into a nested levers patch', () => {
    const diff = [
      { path: 'levers.capability.doubling_months', from: 6, to: 4.5, mechanism: '' },
      { path: 'levers.regulation.EU.ai_act', from: 'baseline', to: 'delayed_2y', mechanism: '' },
    ]
    expect(leversPatch(diff)).toEqual({
      capability: { doubling_months: 4.5 },
      regulation: { EU: { ai_act: 'delayed_2y' } },
    })
  })

  it('clamps and snaps number levers', () => {
    const l = levers[0]!
    expect(clampLever(l, 100)).toBe(36)
    expect(clampLever(l, 0)).toBe(2)
    expect(clampLever(l, 4.3)).toBe(4.5)
    expect(clampLever(l, Number.NaN)).toBe(6)
  })

  it('derives a stable, schema-valid child id and document', () => {
    const diff = [{ path: 'levers.capability.doubling_months', from: 6, to: 4.5, mechanism: '' }]
    const id = childScenarioId('Faster clock!', 'baseline', diff)
    expect(id).toMatch(/^[a-z0-9][a-z0-9-]{1,63}$/)
    expect(id.startsWith('faster-clock-')).toBe(true)
    expect(childScenarioId('Faster clock!', 'baseline', diff)).toBe(id)
    expect(childScenarioId('Faster clock!', 'baseline', [])).not.toBe(id)
    const doc = buildChildScenario('Faster clock!', baseline, diff)
    expect(doc.parent).toBe('baseline')
    expect(doc.levers).toEqual({ capability: { doubling_months: 4.5 } })
    expect(doc.user).toBe(true)
  })
})

describe('layoutLevers (Phase 6 compact enum grid)', () => {
  const approval = (r: string): LeverDef => ({
    path: `levers.applications.approval.${r}`,
    label: `Approval regime: ${r}`,
    group: 'applications',
    type: 'enum',
    options: ['frozen', 'baseline', 'accelerated', 'moratorium'],
    default: 'baseline',
    param: 'P.119',
    mechanism: 'J path',
  })
  const number: LeverDef = {
    path: 'levers.applications.hardware.learning_rate',
    label: 'Hardware learning rate',
    group: 'applications',
    type: 'number',
    min: 0.05,
    max: 0.25,
    step: 0.01,
    default: 0.12,
  }
  const platform: LeverDef = {
    path: 'levers.applications.platform_labor',
    label: 'Platform labor classification',
    group: 'applications',
    type: 'enum',
    options: ['status_quo', 'employee_reclassification'],
    default: 'status_quo',
  }
  it('folds the ten approval enums into one grid at the first sibling’s position', () => {
    const regions = ['US', 'EU', 'UK', 'CN', 'JP', 'KR', 'IN', 'TW', 'SG', 'RoA']
    const items = layoutLevers([number, ...regions.map(approval), platform])
    expect(items.map((i) => i.kind)).toEqual(['lever', 'grid', 'lever'])
    const grid = items[1]!
    if (grid.kind !== 'grid') throw new Error('expected a grid')
    expect(grid.levers).toHaveLength(10)
    expect(grid.label).toBe('Approval regime by region')
    expect(grid.options).toEqual(['frozen', 'baseline', 'accelerated', 'moratorium'])
    expect(grid.levers.map(leverLeaf)).toEqual(regions)
  })
  it('leaves fewer than four siblings, or siblings with different options, as plain rows', () => {
    const items = layoutLevers([approval('US'), approval('EU'), approval('UK'), platform])
    expect(items.every((i) => i.kind === 'lever')).toBe(true)
    const odd = { ...approval('CN'), options: ['frozen', 'baseline'] }
    const mixed = layoutLevers([approval('US'), approval('EU'), approval('UK'), approval('JP'), odd])
    expect(mixed.map((i) => i.kind)).toEqual(['grid', 'lever'])
  })
})

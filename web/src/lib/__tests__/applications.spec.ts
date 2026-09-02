import { describe, expect, it } from 'vitest'
import type { ApplicationEntry } from '@/types/results'
import {
  applicationRegion,
  displacementTable,
  gateMarkers,
  hourlyWage,
  meanWage,
  quarterPosition,
  targetTitles,
  yearTicks,
} from '../applications'

describe('quarterPosition', () => {
  it('maps 2024Q1 to the left edge and the last quarter inside the axis', () => {
    expect(quarterPosition('2024Q1')).toBe(0)
    expect(quarterPosition('2032Q3')).toBeCloseTo((8 + 0.5) / 17, 9)
    expect(quarterPosition('2040Q4')).toBeCloseTo(16.75 / 17, 9)
  })
  it('returns null for missing or malformed quarters and clamps out-of-range ones', () => {
    expect(quarterPosition(null)).toBeNull()
    expect(quarterPosition(undefined)).toBeNull()
    expect(quarterPosition('2035')).toBeNull()
    expect(quarterPosition('2050Q1')).toBe(1)
    expect(quarterPosition('2010Q1')).toBe(0)
  })
  it('honours a custom axis', () => {
    expect(quarterPosition('2030Q1', 2020, 2040)).toBeCloseTo(0.5, 9)
    expect(quarterPosition('2030Q1', 2030, 2030)).toBeNull()
  })
})

describe('gateMarkers', () => {
  it('produces the three gates in order, pinning missing ones to the right edge', () => {
    const m = gateMarkers({
      displacement_1pct: '2035Q2',
      displacement_10pct: null,
      coverage_50pct: '2040Q3',
    })
    expect(m.map((x) => x.gate)).toEqual([
      'displacement_1pct',
      'displacement_10pct',
      'coverage_50pct',
    ])
    expect(m[0]!.x).toBeCloseTo((11 + 0.25) / 17, 9)
    expect(m[0]!.missing).toBe(false)
    expect(m[1]!.x).toBe(1)
    expect(m[1]!.missing).toBe(true)
    expect(m[1]!.quarter).toBeNull()
    expect(m[2]!.missing).toBe(false)
    expect(m[2]!.label).toBe('50% coverage')
  })
  it('treats an absent block as three missing gates', () => {
    const m = gateMarkers(undefined)
    expect(m).toHaveLength(3)
    expect(m.every((x) => x.missing && x.x === 1)).toBe(true)
  })
  it('year ticks span the axis every four years', () => {
    expect(yearTicks().map((t) => t.year)).toEqual([2024, 2028, 2032, 2036, 2040])
    expect(yearTicks()[4]!.x).toBeCloseTo(16 / 17, 9)
  })
})

const block = (disp: number[]) => ({
  target_employment_2024: 1000,
  displacement_share: disp,
  jobs_below_baseline: disp.map((d) => d * 10),
  coverage: disp.map((d) => d / 20),
  approval: disp.map(() => 0.5),
  first_quarter: { displacement_1pct: null, displacement_10pct: null, coverage_50pct: null },
})
const app: ApplicationEntry = {
  app_id: 'robotaxi',
  name: 'Robotaxis',
  family: 'embodied',
  classes: ['driving'],
  platform: true,
  occ_codes: ['53-3054', '*manip'],
  regions_first: ['US'],
  anchor: 'rides',
  constraints: 'approval',
  provisional_profitable: '2026-28',
  provisional_deployed50: '2031-35',
  by_region: { US: block([0, 1, 5, 12]), EU: block([0, 0, 2, 6]) },
}

describe('applicationRegion', () => {
  it('reads the region when present and falls back to the U.S. otherwise', () => {
    expect(applicationRegion(app, 'EU')).toMatchObject({ region: 'EU', fallback: false })
    expect(applicationRegion(app, 'CN')).toMatchObject({ region: 'US', fallback: true })
    expect(applicationRegion(app, 'world')).toMatchObject({ region: 'US', fallback: true })
  })
  it('returns a null block when the application has no regions at all', () => {
    expect(applicationRegion({ ...app, by_region: {} }, 'US').block).toBeNull()
  })
})

describe('displacementTable and helpers', () => {
  it('picks the reference quarters for every region, null where the quarter is absent', () => {
    const quarters = ['2024Q1', '2030Q4', '2035Q4', '2040Q4']
    expect(displacementTable(app, quarters)).toEqual([
      { region: 'US', values: [1, 5, 12] },
      { region: 'EU', values: [0, 2, 6] },
    ])
    // quarters are positional: with a two-quarter axis 2040Q4 is index 1
    expect(displacementTable(app, ['2024Q1', '2040Q4'])[0]!.values).toEqual([null, null, 1])
  })
  it('mean wage is employment-weighted and converts to an hourly rate', () => {
    expect(meanWage([{ emp0: 100, wage0: 50_000 }, { emp0: 300, wage0: 30_000 }])).toBe(35_000)
    expect(meanWage([])).toBeNull()
    expect(hourlyWage(41_600)).toBe(20)
    expect(hourlyWage(null)).toBeNull()
  })
  it('titles target codes from the occupation table and explains wildcards', () => {
    const t = targetTitles(app.occ_codes, [{ occ_code: '53-3054', title: 'Taxi drivers' }])
    expect(t[0]).toEqual({ code: '53-3054', title: 'Taxi drivers' })
    expect(t[1]!.title).toContain('manip')
    expect(targetTitles(['99-9999'], [])[0]!.title).toBeNull()
  })
})

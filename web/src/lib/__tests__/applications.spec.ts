import { describe, expect, it } from 'vitest'
import type { ApplicationEntry } from '@/types/results'
import {
  APPLICATION_FAMILY_LABELS,
  FAMILY_COLUMNS,
  OUTPUT_GATE_LABELS,
  applicationRegion,
  contentCategoryLabel,
  displacementTable,
  gateMarkers,
  groupApplications,
  hourlyWage,
  largestExporter,
  meanWage,
  outputStrip,
  quarterPosition,
  targetTitles,
  tradedRegion,
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

// ---------- Phase 7 (contracts §23–24) ----------

const mk = (app_id: string, family: string, by_region: ApplicationEntry['by_region']): ApplicationEntry => ({
  ...app,
  app_id,
  name: app_id,
  family,
  classes: [],
  by_region,
})

describe('groupApplications', () => {
  it('groups rows by family in catalogue order, keeping document order inside a family', () => {
    const apps = [
      mk('legal', 'software', {}),
      mk('video', 'output', {}),
      mk('robotaxi', 'embodied', {}),
      mk('bpo', 'traded', {}),
      mk('text', 'output', {}),
      mk('trucking', 'embodied', {}),
    ]
    const g = groupApplications(apps)
    expect(g.map((x) => x.family)).toEqual(['embodied', 'output', 'traded', 'software'])
    expect(g.map((x) => x.label)).toEqual([
      'Embodied automation',
      'Output substitution',
      'Traded services',
      'Software applications',
    ])
    expect(g[0]!.apps.map((a) => a.app_id)).toEqual(['robotaxi', 'trucking'])
    expect(g[1]!.apps.map((a) => a.app_id)).toEqual(['video', 'text'])
    expect(g[3]!.apps.map((a) => a.app_id)).toEqual(['legal'])
  })
  it('omits absent families and appends unknown ones after the catalogue order', () => {
    const g = groupApplications([mk('x', 'mystery', {}), mk('y', 'output', {})])
    expect(g.map((x) => x.family)).toEqual(['output', 'mystery'])
    expect(g[1]!.label).toBe('mystery')
    expect(groupApplications([])).toEqual([])
  })
  it('publishes the family column captions: output rows read human output and the AI share, no approval', () => {
    expect(FAMILY_COLUMNS.output).toEqual({ displacement: 'Human output vs baseline', bar: 'AI share', approval: false })
    expect(FAMILY_COLUMNS.embodied!.approval).toBe(true)
    expect(FAMILY_COLUMNS.traded!.bar).toBeNull()
    expect(APPLICATION_FAMILY_LABELS.traded).toBe('Traded services')
  })
})

describe('output gates', () => {
  it('labels the three gates on human output lost and the AI share for output rows', () => {
    const m = gateMarkers(
      { displacement_1pct: '2030Q1', displacement_10pct: null, coverage_50pct: '2036Q2' },
      2024,
      2041,
      'output',
    )
    expect(m.map((x) => x.label)).toEqual([
      OUTPUT_GATE_LABELS.displacement_1pct,
      OUTPUT_GATE_LABELS.displacement_10pct,
      OUTPUT_GATE_LABELS.coverage_50pct,
    ])
    expect(m[2]!.label).toBe('AI share 50%')
    expect(m[0]!.label).toBe('1% of human output lost')
    // other families keep the embodied wording
    expect(gateMarkers(undefined, 2024, 2041, 'embodied')[2]!.label).toBe('50% coverage')
    expect(gateMarkers(undefined)[0]!.label).toBe('1% displaced')
  })
})

describe('traded rows: the exporter fallback', () => {
  const traded = mk('bpo', 'traded', {
    US: block([0, 0, 0, 0]),
    EU: block([0, 0, 0, 0]),
    IN: block([0, 0.5, 3, 7]),
    RoA: block([0, 0.8, 1, 1.2]),
  })
  it('picks the exporter with the largest displacement at the current quarter', () => {
    expect(largestExporter(traded, 1)).toBe('RoA')
    expect(largestExporter(traded, 2)).toBe('IN')
    // an all-zero quarter falls back to the horizon end
    expect(largestExporter(traded, 0)).toBe('IN')
    expect(largestExporter(mk('z', 'traded', { US: block([0, 0]) }), 1)).toBeNull()
  })
  it('shows the selected region when it has exposure, else the largest exporter and says so', () => {
    expect(tradedRegion(traded, 'IN', 3)).toMatchObject({ region: 'IN', fallback: false, exporter: false })
    expect(tradedRegion(traded, 'US', 3)).toMatchObject({ region: 'IN', fallback: true, exporter: true })
    expect(tradedRegion(traded, 'US', 1)).toMatchObject({ region: 'RoA', exporter: true })
    expect(tradedRegion(traded, 'world', 3)).toMatchObject({ region: 'IN', exporter: true })
    // no exporter at all: the plain region fallback applies
    const none = mk('z', 'traded', { US: block([0, 0]) })
    expect(tradedRegion(none, 'EU', 1)).toMatchObject({ region: 'US', fallback: true, exporter: false })
  })
})

describe('outputStrip', () => {
  const s = (p50: number[]) => ({ p50, p10: p50.map((v) => v * 0.8), p90: p50.map((v) => v * 1.2) })
  const blk = {
    ai_content_share: { video: s([0.5, 4, 8]), text: s([2, 15, 26]) },
    content_consumption_ratio: { video: s([1, 1.03, 1.07]), text: s([1, 1.1, 1.26]) },
    ai_content_revenue_bn: s([0.1, 2, 5]),
    consumer_surplus_proxy_bn: s([0.5, 20, 55]),
  }
  it('reads one tile per category in meta order with the band, the ratio and the share path', () => {
    const out = outputStrip(blk, 2, ['text', 'video'])!
    expect(out.tiles.map((t) => t.category)).toEqual(['text', 'video'])
    expect(out.tiles[0]).toMatchObject({ label: 'Text', share: 26, shareLo: 26 * 0.8, shareHi: 26 * 1.2, ratio: 1.26 })
    expect(out.tiles[1]!.path).toEqual([0.5, 4, 8])
    expect(out.revenue).toBe(5)
    expect(out.surplus).toBe(55)
    expect(out.surplusLo).toBeCloseTo(44, 9)
  })
  it('falls back to the series keys, skips unknown categories and returns null without the series', () => {
    const out = outputStrip(blk, 1, ['video', 'nope'])!
    expect(out.tiles.map((t) => t.category)).toEqual(['video'])
    expect(outputStrip(blk, 1)!.tiles.map((t) => t.category)).toEqual(['video', 'text'])
    expect(outputStrip({ ai_content_share: { video: { p50: [1, 2] } } }, 1)).toMatchObject({
      tiles: [{ share: 2, shareLo: null, ratio: null }],
      revenue: null,
      surplus: null,
    })
    expect(outputStrip(null, 0)).toBeNull()
    expect(outputStrip({}, 0)).toBeNull()
  })
  it('labels the content categories', () => {
    expect(contentCategoryLabel('image_design')).toBe('Image and design')
    expect(contentCategoryLabel('new_thing')).toBe('New thing')
  })
})

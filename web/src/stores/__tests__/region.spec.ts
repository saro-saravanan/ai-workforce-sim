import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { REGION_OPTIONS, useRegionStore } from '../region'

describe('useRegionStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('defaults to world and lists World first, then the ten regions', () => {
    const s = useRegionStore()
    expect(s.region).toBe('world')
    expect(s.isWorld).toBe(true)
    expect(s.seriesKey).toBeNull()
    expect(REGION_OPTIONS.map((o) => o.id)).toEqual([
      'world', 'US', 'EU', 'UK', 'CN', 'JP', 'KR', 'IN', 'TW', 'SG', 'RoA',
    ])
  })

  it('accepts region ids and rejects unknown ones', () => {
    const s = useRegionStore()
    s.setRegion('EU')
    expect(s.region).toBe('EU')
    expect(s.label).toBe('European Union')
    expect(s.seriesKey).toBe('EU')
    s.setRegion('Mars')
    expect(s.region).toBe('world')
  })

  it('clears the drilled member when the region changes', () => {
    const s = useRegionStore()
    s.setRegion('EU')
    s.selectMember('DEU')
    expect(s.member).toBe('DEU')
    s.setRegion('EU')
    expect(s.member).toBe('DEU')
    s.setRegion('US')
    expect(s.member).toBeNull()
    s.selectMember('not-iso')
    expect(s.member).toBeNull()
  })

  it('serialises to the URL, omitting the default', () => {
    const s = useRegionStore()
    expect(s.toQuery()).toEqual({ region: undefined, member: undefined })
    s.setRegion('CN')
    expect(s.toQuery()).toEqual({ region: 'CN', member: undefined })
    s.setRegion('EU')
    s.selectMember('FRA')
    expect(s.toQuery()).toEqual({ region: 'EU', member: 'FRA' })
  })

  it('applies a URL query and ignores invalid values', () => {
    const s = useRegionStore()
    s.applyQuery({ region: 'JP', member: 'JPN' })
    expect(s.region).toBe('JP')
    expect(s.member).toBe('JPN')
    s.applyQuery({ region: 'bogus', member: 'x' })
    expect(s.region).toBe('world')
    expect(s.member).toBeNull()
    s.applyQuery({})
    expect(s.region).toBe('world')
  })

  it('round-trips through the query', () => {
    const s = useRegionStore()
    s.setRegion('RoA')
    s.selectMember('VNM')
    const q = s.toQuery()
    const t = useRegionStore()
    t.applyQuery(q)
    expect(t.region).toBe('RoA')
    expect(t.member).toBe('VNM')
  })
})

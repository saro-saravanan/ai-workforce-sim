import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { PLAYBACK_MS, useScrubberStore } from '../scrubber'

describe('useScrubberStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('clamps the quarter to the loaded length', () => {
    const s = useScrubberStore()
    s.setLength(68)
    s.set(100)
    expect(s.q).toBe(67)
    s.set(-5)
    expect(s.q).toBe(0)
    s.step(3)
    expect(s.q).toBe(3)
  })

  it('plays at 4 quarters per second and stops at the end', () => {
    const s = useScrubberStore()
    s.setLength(6)
    s.play()
    expect(s.playing).toBe(true)
    vi.advanceTimersByTime(1000)
    expect(s.q).toBe(4)
    expect(PLAYBACK_MS).toBe(250)
    vi.advanceTimersByTime(1000)
    expect(s.q).toBe(5)
    expect(s.playing).toBe(false)
  })

  it('restarts from zero when played at the end', () => {
    const s = useScrubberStore()
    s.setLength(4)
    s.set(3)
    s.play()
    expect(s.q).toBe(0)
    s.pause()
    expect(s.playing).toBe(false)
  })

  it('toggle pauses a running playback', () => {
    const s = useScrubberStore()
    s.setLength(10)
    s.toggle()
    vi.advanceTimersByTime(PLAYBACK_MS * 2)
    s.toggle()
    const at = s.q
    vi.advanceTimersByTime(1000)
    expect(s.q).toBe(at)
  })

  it('serialises to a URL query, omitting defaults', () => {
    const s = useScrubberStore()
    s.setLength(68)
    expect(s.toQuery()).toEqual({ q: undefined, metric: undefined, state: undefined })
    s.set(22)
    s.setMetric('real_wage_pct_vs_baseline')
    s.selectState('39')
    expect(s.toQuery()).toEqual({ q: '22', metric: 'real_wage_pct_vs_baseline', state: '39' })
  })

  it('applies a URL query and ignores invalid values', () => {
    const s = useScrubberStore()
    s.setLength(68)
    s.applyQuery({ q: '30', metric: 'displaced_workers_cum', state: '06' })
    expect(s.q).toBe(30)
    expect(s.metric).toBe('displaced_workers_cum')
    expect(s.state).toBe('06')
    s.applyQuery({ q: 'nope', metric: 'bogus', state: 'Ohio' })
    expect(s.q).toBe(30) // unparsable q leaves the value alone
    expect(s.metric).toBe('employment_pct_vs_baseline')
    expect(s.state).toBeNull()
    s.applyQuery({})
    expect(s.q).toBe(0)
  })

  it('round-trips through the query', () => {
    const s = useScrubberStore()
    s.setLength(68)
    s.set(41)
    s.setMetric('displaced_workers_cum')
    s.selectState('48')
    const query = s.toQuery()
    const t = useScrubberStore()
    t.applyQuery(query)
    expect(t.q).toBe(41)
    expect(t.metric).toBe('displaced_workers_cum')
    expect(t.state).toBe('48')
  })
})

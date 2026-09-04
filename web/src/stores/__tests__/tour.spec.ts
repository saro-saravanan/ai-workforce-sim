import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { TOUR_STEPS, useTourStore } from '@/stores/tour'

describe('tour store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('invites once per browser and remembers a dismissal', () => {
    const t = useTourStore()
    expect(t.maybeWelcome()).toBe(true)
    expect(t.welcome).toBe(true)
    t.dismissWelcome()
    expect(t.welcome).toBe(false)
    expect(localStorage.getItem('aiwsim.tour')).toBe('1')
    expect(t.maybeWelcome()).toBe(false)
  })

  it('walks the steps in order and finishes after the last', () => {
    const t = useTourStore()
    t.start()
    expect(t.active).toBe(true)
    expect(t.step?.id).toBe('welcome')
    t.back()
    expect(t.index).toBe(0)
    for (let i = 1; i < TOUR_STEPS.length; i++) t.next()
    expect(t.isLast).toBe(true)
    expect(t.step?.id).toBe('finish')
    t.next()
    expect(t.active).toBe(false)
    expect(localStorage.getItem('aiwsim.tour')).toBe('1')
  })

  it('skips a step in the direction of travel', () => {
    const t = useTourStore()
    t.start()
    t.next()
    t.skipStep(1)
    expect(t.index).toBe(2)
    t.skipStep(-1)
    expect(t.index).toBe(1)
  })

  it('every spotlight step names a target and the first and last are cards', () => {
    expect(TOUR_STEPS[0]?.target).toBeUndefined()
    expect(TOUR_STEPS[TOUR_STEPS.length - 1]?.target).toBeUndefined()
    for (const s of TOUR_STEPS.slice(1, -1)) expect(s.target).toMatch(/^\[data-tour=/)
  })
})

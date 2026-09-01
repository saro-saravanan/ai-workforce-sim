import { describe, expect, it } from 'vitest'
import { hcl } from 'd3'
import {
  cappedCategorical,
  divergingScale,
  inkOn,
  magnitudeDomain,
  niceSymmetric,
  sequentialScale,
  stackCategorical,
  symmetricDomain,
} from '../scales'
import { CATEGORICAL, DIVERGING, NEUTRAL } from '../palette'

describe('domains', () => {
  it('symmetricDomain centers on zero using the largest magnitude', () => {
    expect(symmetricDomain([-3.2, 1.1, 0.4])).toEqual([-3.2, 3.2])
    expect(symmetricDomain([1, 2, null, undefined, NaN])).toEqual([-2, 2])
    expect(symmetricDomain([])).toEqual([-1, 1])
  })
  it('niceSymmetric rounds up to a clean half-range', () => {
    expect(niceSymmetric([-3.2, 3.2])).toEqual([-5, 5])
    expect(niceSymmetric([-1.7, 1.7])).toEqual([-2, 2])
    expect(niceSymmetric([-0.23, 0.23])).toEqual([-0.25, 0.25])
    expect(niceSymmetric([0, 0])).toEqual([-1, 1])
  })
  it('magnitudeDomain starts at zero', () => {
    expect(magnitudeDomain([5, 120, 3])).toEqual([0, 120])
    expect(magnitudeDomain([])).toEqual([0, 1])
  })
})

describe('divergingScale', () => {
  it('maps zero to the neutral midpoint and clamps the poles in both modes', () => {
    for (const mode of ['light', 'dark'] as const) {
      const s = divergingScale([-4, 4], mode)
      const mid = hcl(s(0))
      const exp = hcl(DIVERGING[mode].mid)
      expect(Math.abs(mid.l - exp.l)).toBeLessThan(1)
      expect(s(-99)).toBe(s(-4))
      expect(s(99)).toBe(s(4))
      // negative pole is warm (red), positive pole is cool (blue)
      const neg = hcl(s(-4)).h
      const pos = hcl(s(4)).h
      expect(neg > 300 || neg < 60).toBe(true)
      expect(pos).toBeGreaterThan(200)
      expect(pos).toBeLessThan(320)
    }
  })
  it('is monotone in lightness on each arm', () => {
    const s = divergingScale([-1, 1], 'light')
    const L = (v: number) => hcl(s(v)).l
    expect(L(-1)).toBeLessThan(L(-0.5))
    expect(L(-0.5)).toBeLessThan(L(0))
    expect(L(1)).toBeLessThan(L(0.5))
    expect(L(0.5)).toBeLessThan(L(0))
  })
})

describe('sequentialScale', () => {
  it('gets darker with magnitude in light mode and lighter in dark mode', () => {
    const light = sequentialScale([0, 10], 'light')
    const dark = sequentialScale([0, 10], 'dark')
    expect(hcl(light(10)).l).toBeLessThan(hcl(light(0)).l)
    expect(hcl(dark(10)).l).toBeGreaterThan(hcl(dark(0)).l)
  })
})

describe('categorical', () => {
  it('assigns the first three slots in fixed order and folds the rest to gray', () => {
    const { scale, kept, other } = cappedCategorical(['43', '15', '29', '11', '53'], 'light')
    expect(kept).toEqual(['43', '15', '29'])
    expect(scale('43')).toBe(CATEGORICAL.light[0])
    expect(scale('15')).toBe(CATEGORICAL.light[1])
    expect(scale('29')).toBe(CATEGORICAL.light[2])
    expect(scale('11')).toBe(NEUTRAL.light)
    expect(other).toBe(NEUTRAL.light)
  })
  it('keeps a key’s color when other keys are removed (color follows entity)', () => {
    const a = cappedCategorical(['x', 'y', 'z'], 'dark').scale
    const b = cappedCategorical(['x', 'z'], 'dark').scale
    expect(b('x')).toBe(a('x'))
  })
  it('stack scale caps at eight slots', () => {
    const keys = Array.from({ length: 10 }, (_, i) => `k${i}`)
    const s = stackCategorical(keys, 'light')
    expect(s('k7')).toBe(CATEGORICAL.light[7])
    expect(s('k8')).toBe(NEUTRAL.light)
  })
})

describe('inkOn', () => {
  it('picks white on dark fills and ink on light fills', () => {
    expect(inkOn('#0d366b')).toBe('#ffffff')
    expect(inkOn('#f0efec')).toBe('#0b0b0b')
  })
})

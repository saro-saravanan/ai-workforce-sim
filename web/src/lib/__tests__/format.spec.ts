import { describe, expect, it } from 'vitest'
import { fmtCompact, fmtPct, fmtPp, fmtShare, quarterLabel } from '../format'

describe('format', () => {
  it('formats quarter labels', () => {
    expect(quarterLabel('2029Q3')).toBe('2029 Q3')
    expect(quarterLabel(undefined)).toBe('')
  })
  it('formats signed percents and points', () => {
    expect(fmtPct(-2.14)).toBe('\u22122.1%')
    expect(fmtPct(0)).toBe('0.0%')
    expect(fmtPct(3)).toBe('+3.0%')
    expect(fmtPp(-1.8)).toBe('\u22121.8 pp')
    expect(fmtShare(0.62)).toBe('62%')
    expect(fmtPct(null)).toBe('—')
  })
  it('compacts counts', () => {
    expect(fmtCompact(1_500_000)).toBe('1.5M')
    expect(fmtCompact(9_400_000_000)).toBe('9.4B')
    expect(fmtCompact(1284)).toBe('1.28k')
  })
})

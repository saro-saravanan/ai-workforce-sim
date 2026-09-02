import { describe, expect, it } from 'vitest'
import type { ChannelName, FlowsSection, Series } from '@/types/results'
import { RENT_STAGES } from '@/types/results'
import {
  CHANNEL_COLOR_SLOT,
  CHANNEL_LABELS,
  EMBODIED_TILES,
  FLOW_DESTINATION_LABELS,
  channelColorScale,
  flowDestinations,
} from '../metrics'
import { CATEGORICAL, NEUTRAL } from '../palette'

const ORDER_V03: ChannelName[] = [
  'automation',
  'augmentation',
  'embodied',
  'demand_response',
  'reinstatement',
  'demand_feedback',
  'ai_investment',
  'adjacent',
]
const ORDER_V02: ChannelName[] = [
  'automation',
  'augmentation',
  'demand_response',
  'reinstatement',
  'demand_feedback',
  'ai_investment',
]

describe('channel colors and labels', () => {
  it('gives the eight v0.3 channels eight distinct colors in both modes', () => {
    for (const mode of ['light', 'dark'] as const) {
      const color = channelColorScale(ORDER_V03, mode)
      const colors = ORDER_V03.map(color)
      expect(new Set(colors).size).toBe(8)
      expect(colors.every((c) => CATEGORICAL[mode].includes(c))).toBe(true)
      expect(colors).not.toContain(NEUTRAL[mode])
    }
  })
  it('keeps a channel’s color between the six- and eight-entry orders (color follows entity)', () => {
    const c6 = channelColorScale(ORDER_V02, 'light')
    const c8 = channelColorScale(ORDER_V03, 'light')
    for (const k of ORDER_V02) expect(c8(k)).toBe(c6(k))
    expect(c8('embodied')).toBe(CATEGORICAL.light[CHANNEL_COLOR_SLOT.embodied])
    expect(c8('adjacent')).toBe(CATEGORICAL.light[CHANNEL_COLOR_SLOT.adjacent])
  })
  it('labels the two new channels for the legend', () => {
    expect(CHANNEL_LABELS.embodied).toBe('Embodied automation')
    expect(CHANNEL_LABELS.adjacent).toBe('Adjacent and hardware jobs')
    for (const k of ORDER_V03) expect(CHANNEL_LABELS[k]).toBeTruthy()
  })
  it('falls back to the positional stack scale for non-channel keys (rents stages)', () => {
    const color = channelColorScale(RENT_STAGES, 'dark')
    expect(color('model')).toBe(CATEGORICAL.dark[0])
    expect(color('integration')).toBe(CATEGORICAL.dark[3])
    expect(color('nope')).toBe(NEUTRAL.dark)
  })
  it('publishes the two embodied tiles with their formats', () => {
    const [share, jobs] = EMBODIED_TILES
    expect(share!.key).toBe('embodied_displacement_share')
    expect(share!.def.format(5.591)).toBe('5.6%')
    expect(share!.def.format(null)).toBe('—')
    expect(jobs!.key).toBe('adjacent_jobs')
    expect(jobs!.def.format(361_402)).toBe('361k')
  })
})

describe('flowDestinations', () => {
  const s = (v: number): Series => ({ p50: [v] })
  const base = {
    reemployed: s(1),
    retraining: s(1),
    unemployed: s(1),
    exited: s(1),
    retired: s(1),
    unfilled_entry: s(1),
  }
  it('keeps the six v0.2 states and appends hours_cut_self only when present', () => {
    const v02: FlowsSection = { origins: [], destinations: base }
    expect(flowDestinations(v02)).toHaveLength(6)
    const v03: FlowsSection = {
      origins: [],
      destinations: { ...base, hours_cut_self: s(2), laid_off: s(3), self_employed_margin_cum: s(4) },
    }
    const d = flowDestinations(v03)
    expect(d).toHaveLength(7)
    expect(d[6]).toBe('hours_cut_self')
    expect(d).not.toContain('laid_off')
    expect(FLOW_DESTINATION_LABELS.hours_cut_self).toBe('Hours cut (self-employed and platform)')
  })
})

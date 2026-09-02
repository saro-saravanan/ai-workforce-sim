import { describe, expect, it } from 'vitest'
import type { ChannelName, FlowsSection, Series } from '@/types/results'
import { RENT_STAGES } from '@/types/results'
import {
  APPLICATION_TILES,
  CHANNEL_COLOR_SLOT,
  CHANNEL_LABELS,
  EMBODIED_TILES,
  FLOW_DESTINATION_LABELS,
  SURPLUS_CAPTION,
  cellAxesLabel,
  channelColorScale,
  flowDestinations,
  seriesIsNonzero,
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
/** contracts §24: the ten-entry Phase 7 order */
const ORDER_V03_P7: ChannelName[] = [
  'automation',
  'augmentation',
  'embodied',
  'output_substitution',
  'traded_services',
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
  it('maps the ten Phase 7 channels to ten distinct colors and keeps every earlier color', () => {
    for (const mode of ['light', 'dark'] as const) {
      const c10 = channelColorScale(ORDER_V03_P7, mode)
      const colors = ORDER_V03_P7.map(c10)
      expect(new Set(colors).size).toBe(10)
      expect(colors.every((c) => CATEGORICAL[mode].includes(c))).toBe(true)
      expect(colors).not.toContain(NEUTRAL[mode])
      const c8 = channelColorScale(ORDER_V03, mode)
      for (const k of ORDER_V03) expect(c10(k)).toBe(c8(k))
      expect(c10('output_substitution')).toBe(CATEGORICAL[mode][CHANNEL_COLOR_SLOT.output_substitution])
      expect(c10('traded_services')).toBe(CATEGORICAL[mode][CHANNEL_COLOR_SLOT.traded_services])
    }
    expect(CHANNEL_LABELS.output_substitution).toBe('Output substitution')
    expect(CHANNEL_LABELS.traded_services).toBe('Traded services')
    for (const k of ORDER_V03_P7) expect(CHANNEL_LABELS[k]).toBeTruthy()
    // every channel has a slot inside the palette
    for (const k of ORDER_V03_P7) expect(CHANNEL_COLOR_SLOT[k]).toBeLessThan(CATEGORICAL.light.length)
  })
  it('names the mechanism-cell axes for 3-, 4- and 5-part ids', () => {
    expect(cellAxesLabel(3)).toBe('demand response | reinstatement | pass-through')
    expect(cellAxesLabel(4)).toBe('demand response | reinstatement | pass-through | hardware learning')
    expect(cellAxesLabel(5)).toBe(
      'demand response | reinstatement | pass-through | hardware learning | authenticity',
    )
    expect(cellAxesLabel(9)).toBe(cellAxesLabel(5))
  })
  it('publishes the Phase 7 tiles: the surplus proxy with its caption, the traded share for exporters only', () => {
    const [surplus, traded] = APPLICATION_TILES
    expect(surplus!.key).toBe('consumer_surplus_proxy_bn')
    expect(surplus!.note).toBe(SURPLUS_CAPTION)
    expect(surplus!.def.format(51.47)).toBe('$51.5bn')
    expect(traded!.key).toBe('traded_services_displacement_share')
    expect(traded!.nonzeroOnly).toBe(true)
    expect(traded!.def.format(0.0362)).toBe('0.036%')
    expect(traded!.def.format(null)).toBe('—')
    expect(seriesIsNonzero({ p50: [0, 0, 0] })).toBe(false)
    expect(seriesIsNonzero({ p50: [0, 0.004, 0.036] })).toBe(true)
    expect(seriesIsNonzero(undefined)).toBe(false)
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

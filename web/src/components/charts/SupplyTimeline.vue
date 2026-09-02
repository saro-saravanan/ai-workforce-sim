<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear, scaleLog } from 'd3'
import type { SupplySection } from '@/types/results'
import { REGION_IDS, REGION_NAMES, isRegionId } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip, type TooltipRow } from '@/composables/useTooltip'
import { fmtHorizon, fmtUsdPerMtok, quarterLabel, quarterYear } from '@/lib/format'
import { REGULATORY_KIND_LABELS } from '@/lib/metrics'
import { CATEGORICAL, NEUTRAL, type Mode } from '@/lib/palette'
import { BAND_OUTER_OPACITY } from '@/lib/bands'
import ChartTooltip from '@/components/ChartTooltip.vue'

export interface ShockMarker {
  quarter: string
  label: string
  detail?: string
}

const props = defineProps<{
  supply: SupplySection
  quarters: string[]
  q: number
  /** 'world' or a region id: the emphasized capability line and the availability shading */
  region: string
  /** draw every region's capability line (muted) rather than only the selected one */
  showAll: boolean
  /** shade quarters where the selected region cannot access the frontier actor */
  showAvailability: boolean
  shocks: ShockMarker[]
  mode: Mode
}>()
const emit = defineEmits<{ scrub: [q: number] }>()

const host = ref<HTMLElement | null>(null)
const { width } = useSize(host, { width: 960, height: 700 })
const { tip, show, hide } = useTooltip()

// ----- layout: one x axis, four stacked panels -----
const m = { top: 30, right: 134, bottom: 34, left: 146 }
const CAP_H = 210
const PRICE_H = 140
const ROW_H = 20
const GAP = 18
const iw = computed(() => Math.max(200, width.value - m.left - m.right))
const n = computed(() => props.quarters.length)
const x = computed(() =>
  scaleLinear()
    .domain([0, Math.max(1, n.value - 1)])
    .range([0, iw.value]),
)
/** a calendar date on the quarter-index axis (2024-02-15 → 0.16) */
function dateIndex(date: string): number {
  const y = Number(date.slice(0, 4))
  const mo = Number(date.slice(5, 7))
  const d = Number(date.slice(8, 10))
  const y0 = quarterYear(props.quarters[0] ?? '2024Q1')
  return (y - y0) * 4 + (mo - 1) / 3 + (d - 1) / 92
}

/** Home-region colours for the release dots: fixed slots, never cycled (only three home regions). */
const HOME = computed<Record<string, string>>(() => ({
  US: CATEGORICAL[props.mode][0] ?? '#2a78d6',
  CN: CATEGORICAL[props.mode][1] ?? '#eb6834',
  EU: CATEGORICAL[props.mode][2] ?? '#1baf7a',
}))
const homeColor = (id: string) => HOME.value[id] ?? NEUTRAL[props.mode]
const frontierHue = computed(() => CATEGORICAL[props.mode][0] ?? '#2a78d6')

// ----- capability panel (log hours) -----
const hoursOf = (idx: number) => Math.pow(2, idx) / 60
const MIN_H = 1 / 60
const capBand = computed(() => {
  const h = props.supply.horizon_hours
  const c = props.supply.clock
  const lo = h?.p10 ?? c.p10?.map(hoursOf)
  const hi = h?.p90 ?? c.p90?.map(hoursOf)
  const p50 = h?.p50 ?? c.p50.map(hoursOf)
  return { lo, hi, p50 }
})
const regionalLines = computed(() =>
  Object.entries(props.supply.regional_capability)
    .filter(([id]) => props.showAll || id === props.region)
    .map(([id, s]) => ({
      id,
      name: isRegionId(id) ? REGION_NAMES[id] : id,
      hours: s.central.map(hoursOf),
      emphasized: id === props.region,
    }))
    .sort((a, b) => Number(a.emphasized) - Number(b.emphasized)),
)
const yCap = computed(() => {
  let lo = Number.POSITIVE_INFINITY
  let hi = 0
  const push = (arr?: number[]) => {
    for (const v of arr ?? []) {
      if (!Number.isFinite(v)) continue
      lo = Math.min(lo, Math.max(MIN_H, v))
      hi = Math.max(hi, v)
    }
  }
  push(capBand.value.lo)
  push(capBand.value.hi)
  push(capBand.value.p50)
  for (const l of regionalLines.value) push(l.hours)
  if (!Number.isFinite(lo)) lo = MIN_H
  return scaleLog()
    .domain([Math.max(MIN_H, lo / 1.5), Math.max(hi * 1.3, lo * 4)])
    .range([CAP_H, 0])
})
const HORIZON_TICKS: Array<[number, string]> = [
  [1 / 60, '1 min'],
  [1 / 6, '10 min'],
  [1, '1 h'],
  [24, '1 day'],
  [168, '1 week'],
  [720, '1 month'],
  [8760, '1 year'],
]
const capTicks = computed(() => {
  const [lo, hi] = yCap.value.domain() as [number, number]
  return HORIZON_TICKS.filter(([v]) => v >= lo && v <= hi).map(([v, label]) => ({ v, label, y: yCap.value(v) }))
})
const MIN_PRICE = 1e-7
function logLine(values: number[] | undefined, y: (v: number) => number, floor = MIN_H): string {
  if (!values) return ''
  let d = ''
  values.forEach((v, i) => {
    if (!Number.isFinite(v)) return
    d += `${d ? 'L' : 'M'}${x.value(i).toFixed(1)},${y(Math.max(floor, v)).toFixed(1)}`
  })
  return d
}
function logArea(lo: number[] | undefined, hi: number[] | undefined, y: (v: number) => number): string {
  if (!lo || !hi) return ''
  const k = Math.min(lo.length, hi.length)
  let top = ''
  let bottom = ''
  for (let i = 0; i < k; i++) {
    top += `${top ? 'L' : 'M'}${x.value(i).toFixed(1)},${y(Math.max(MIN_H, hi[i] ?? MIN_H)).toFixed(1)}`
  }
  for (let i = k - 1; i >= 0; i--) {
    bottom += `L${x.value(i).toFixed(1)},${y(Math.max(MIN_H, lo[i] ?? MIN_H)).toFixed(1)}`
  }
  return top + bottom + 'Z'
}
const capMedian = computed(() => logLine(capBand.value.p50, yCap.value))
const capArea = computed(() => logArea(capBand.value.lo, capBand.value.hi, yCap.value))
const regionalPaths = computed(() =>
  regionalLines.value.map((l) => ({ ...l, d: logLine(l.hours, yCap.value) })),
)
/** End labels for the frontier and the emphasized region only (muted lines are identified by the legend and tooltip). */
const capEndLabels = computed(() => {
  const last = n.value - 1
  const items: Array<{ id: string; text: string; y: number; emphasized: boolean }> = [
    {
      id: 'frontier',
      text: 'Frontier',
      y: yCap.value(Math.max(MIN_H, capBand.value.p50[last] ?? MIN_H)),
      emphasized: true,
    },
  ]
  for (const l of regionalLines.value)
    if (l.emphasized)
      items.push({ id: l.id, text: l.id, y: yCap.value(Math.max(MIN_H, l.hours[last] ?? MIN_H)), emphasized: true })
  items.sort((a, b) => a.y - b.y)
  for (let i = 1; i < items.length; i++) {
    const prev = items[i - 1]!
    const cur = items[i]!
    if (cur.y - prev.y < 14) cur.y = prev.y + 14
  }
  return items
})

// ----- price panel (log $/M tokens) -----
const PRICE_Y0 = CAP_H + GAP
const priceFrontier = computed(() => props.supply.price_frontier_usd_per_mtok.central)
const priceFixed = computed(() => props.supply.price_fixed_capability_usd_per_mtok.central)
const yPrice = computed(() => {
  const all = [...priceFrontier.value, ...priceFixed.value].filter((v) => Number.isFinite(v) && v > 0)
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  return scaleLog()
    .domain([lo / 1.5, hi * 1.5])
    .range([PRICE_H, 0])
})
const priceTicks = computed(() => {
  const [lo, hi] = yPrice.value.domain() as [number, number]
  return [0.0001, 0.001, 0.01, 0.1, 1, 10, 100]
    .filter((v) => v >= lo && v <= hi)
    .map((v) => ({ v, label: v >= 1 ? `$${v}` : `$${v}`, y: yPrice.value(v) }))
})
const priceFrontierPath = computed(() => logLine(priceFrontier.value, yPrice.value, MIN_PRICE))
const priceFixedPath = computed(() => logLine(priceFixed.value, yPrice.value, MIN_PRICE))
const priceEndLabels = computed(() => {
  const last = n.value - 1
  const items = [
    { id: 'frontier', text: 'Frontier', y: yPrice.value(Math.max(MIN_PRICE, priceFrontier.value[last] ?? 1)) },
    { id: 'fixed', text: 'Fixed capability', y: yPrice.value(Math.max(MIN_PRICE, priceFixed.value[last] ?? 1)) },
  ].sort((a, b) => a.y - b.y)
  if (items.length === 2 && items[1]!.y - items[0]!.y < 14) items[1]!.y = items[0]!.y + 14
  return items
})

// ----- releases strip: one row per actor, ordered by home region then name -----
const REL_Y0 = computed(() => PRICE_Y0 + PRICE_H + GAP)
const regionOrder = (id: string) => {
  const i = (REGION_IDS as string[]).indexOf(id)
  return i < 0 ? 99 : i
}
const actors = computed(() => {
  const seen = new Map<string, { actor_id: string; name: string; region_id: string }>()
  for (const r of props.supply.releases)
    if (!seen.has(r.actor_id)) seen.set(r.actor_id, { actor_id: r.actor_id, name: r.name, region_id: r.region_id })
  return [...seen.values()].sort(
    (a, b) => regionOrder(a.region_id) - regionOrder(b.region_id) || a.name.localeCompare(b.name),
  )
})
const actorRow = computed(() => new Map(actors.value.map((a, i) => [a.actor_id, i])))
const releaseDots = computed(() =>
  props.supply.releases.map((r, i) => ({
    key: `${r.actor_id}-${r.model}-${i}`,
    r,
    cx: x.value(dateIndex(r.date)),
    cy: REL_Y0.value + (actorRow.value.get(r.actor_id) ?? 0) * ROW_H + ROW_H / 2,
    color: homeColor(r.region_id),
  })),
)
const REL_H = computed(() => actors.value.length * ROW_H)

// ----- rules strip: one row per region with events -----
const RULES_Y0 = computed(() => REL_Y0.value + REL_H.value + GAP)
const ruleRegions = computed(() =>
  [...new Set(props.supply.regulatory_events.map((e) => e.region))].sort(
    (a, b) => regionOrder(a) - regionOrder(b),
  ),
)
const ruleRow = computed(() => new Map(ruleRegions.value.map((id, i) => [id, i])))
const ruleMarks = computed(() =>
  props.supply.regulatory_events.map((e) => ({
    e,
    x: x.value(dateIndex(e.date)),
    y: RULES_Y0.value + (ruleRow.value.get(e.region) ?? 0) * ROW_H + 4,
  })),
)
const RULES_H = computed(() => ruleRegions.value.length * ROW_H)
const totalH = computed(() => RULES_Y0.value + RULES_H.value)
const height = computed(() => m.top + totalH.value + m.bottom)

// ----- availability: quarters where the selected region cannot access the frontier actor -----
/** the actor holding the frontier at quarter i: highest capability among releases up to that quarter */
const frontierActorAt = computed(() => {
  const out: Array<string | null> = []
  let best: { cap: number; actor: string } | null = null
  const byQuarter = new Map<number, typeof props.supply.releases>()
  for (const r of props.supply.releases) {
    const qi = props.quarters.indexOf(r.quarter)
    if (qi < 0 || r.capability_index == null) continue
    byQuarter.set(qi, [...(byQuarter.get(qi) ?? []), r])
  }
  for (let i = 0; i < n.value; i++) {
    for (const r of byQuarter.get(i) ?? [])
      if (!best || (r.capability_index ?? 0) >= best.cap) best = { cap: r.capability_index ?? 0, actor: r.actor_id }
    out.push(best?.actor ?? null)
  }
  return out
})
const unavailable = computed(() => {
  const av = props.supply.availability[props.region]
  if (!av) return [] as number[]
  const out: number[] = []
  frontierActorAt.value.forEach((actor, i) => {
    if (actor && av[actor]?.[i] === 0) out.push(i)
  })
  return out
})
/** contiguous runs of unavailable quarters, as rects */
const unavailableRuns = computed(() => {
  const runs: Array<{ x0: number; x1: number; from: number; to: number }> = []
  for (const i of unavailable.value) {
    const last = runs[runs.length - 1]
    if (last && last.to === i - 1) last.to = i
    else runs.push({ x0: 0, x1: 0, from: i, to: i })
  }
  return runs.map((r) => ({
    ...r,
    x0: x.value(Math.max(0, r.from - 0.5)),
    x1: x.value(Math.min(n.value - 1, r.to + 0.5)),
  }))
})
const unavailableSet = computed(() => new Set(unavailable.value))

// ----- shocks -----
const shockMarks = computed(() =>
  props.shocks
    .map((s) => ({ ...s, i: props.quarters.indexOf(s.quarter) }))
    .filter((s) => s.i >= 0)
    .map((s) => ({ ...s, x: x.value(s.i) })),
)

// ----- axis -----
const xTicks = computed(() =>
  props.quarters
    .map((qq, i) => ({ i, year: quarterYear(qq), qq }))
    .filter((t) => t.qq.endsWith('Q1') && t.year % 2 === 0),
)

// ----- hover -----
const hoverQ = ref<number | null>(null)
function pos(e: PointerEvent) {
  const r = host.value?.getBoundingClientRect()
  return [e.clientX - (r?.left ?? 0), e.clientY - (r?.top ?? 0)] as const
}
function onPanelMove(e: PointerEvent) {
  const [px, py] = pos(e)
  const i = Math.round(Math.min(n.value - 1, Math.max(0, x.value.invert(px - m.left))))
  hoverQ.value = i
  const rows: TooltipRow[] = []
  const b = capBand.value
  rows.push({
    label: 'Frontier horizon (median)',
    value:
      b.lo && b.hi
        ? `${fmtHorizon(b.p50[i])} [${fmtHorizon(b.lo[i])}, ${fmtHorizon(b.hi[i])}]`
        : fmtHorizon(b.p50[i]),
    swatch: frontierHue.value,
    kind: 'line',
  })
  for (const l of regionalLines.value)
    if (l.emphasized) rows.push({ label: `${l.name} available`, value: fmtHorizon(l.hours[i]) })
  rows.push({ label: 'Frontier price', value: `${fmtUsdPerMtok(priceFrontier.value[i])} / M tok` })
  rows.push({ label: 'Fixed-capability price', value: `${fmtUsdPerMtok(priceFixed.value[i])} / M tok` })
  const fa = frontierActorAt.value[i]
  if (fa && props.region !== 'world')
    rows.push({
      label: `Frontier (${actors.value.find((a) => a.actor_id === fa)?.name ?? fa}) in ${props.region}`,
      value: unavailableSet.value.has(i) ? 'not available' : 'available',
    })
  show(x.value(i) + m.left, Math.min(py, m.top + CAP_H), quarterLabel(props.quarters[i]), rows)
}
function onPanelLeave() {
  hoverQ.value = null
  hide()
}
function onPanelClick() {
  if (hoverQ.value != null) emit('scrub', hoverQ.value)
}
function onDot(e: PointerEvent, d: (typeof releaseDots.value)[number]) {
  const r = d.r
  show(d.cx + m.left, d.cy + m.top, r.model, [
    { label: 'Actor', value: r.name, swatch: d.color, kind: 'rect' },
    { label: 'Home region', value: isRegionId(r.region_id) ? REGION_NAMES[r.region_id] : r.region_id },
    { label: 'Date', value: `${r.date} (${quarterLabel(r.quarter)})` },
    {
      label: 'Capability',
      value:
        r.capability_index == null
          ? 'not on the METR series'
          : `${r.capability_index.toFixed(1)} doublings · ${fmtHorizon(hoursOf(r.capability_index))}`,
    },
    { label: 'Weights', value: r.open_weights ? 'open' : 'closed' },
  ])
  e.stopPropagation()
}
function onRule(d: (typeof ruleMarks.value)[number]) {
  const e = d.e
  show(d.x + m.left, d.y + m.top, e.description, [
    { label: 'Region', value: isRegionId(e.region) ? REGION_NAMES[e.region] : e.region },
    { label: 'Date', value: `${e.date} (${quarterLabel(e.quarter)})` },
    { label: 'Kind', value: REGULATORY_KIND_LABELS[e.kind] ?? e.kind },
  ])
}
function onShock(s: (typeof shockMarks.value)[number]) {
  show(s.x + m.left, m.top, s.label, [
    { label: 'Quarter', value: quarterLabel(s.quarter) },
    ...(s.detail ? [{ label: 'Mechanism', value: s.detail }] : []),
  ])
}
const cursorX = computed(() => x.value(hoverQ.value ?? props.q))
</script>

<template>
  <div ref="host" class="timeline-host" :style="{ height: height + 'px' }">
    <svg :width="width" :height="height" role="img" aria-label="AI supply timeline: capability, price, releases and rules on one time axis">
      <g :transform="`translate(${m.left},${m.top})`">
        <!-- availability shading spans every panel -->
        <g v-if="showAvailability" class="unavail" aria-hidden="true">
          <rect
            v-for="r in unavailableRuns"
            :key="r.from"
            :x="r.x0"
            y="0"
            :width="Math.max(1, r.x1 - r.x0)"
            :height="totalH"
          />
        </g>

        <!-- capability panel -->
        <g class="panel">
          <text class="panel-title" x="0" y="-8">Capability · frontier task horizon (log)</text>
          <g class="grid">
            <line v-for="t in capTicks" :key="'cg' + t.v" x1="0" :x2="iw" :y1="t.y" :y2="t.y" />
          </g>
          <g class="axis">
            <text v-for="t in capTicks" :key="'ct' + t.v" x="-10" :y="t.y" text-anchor="end" dominant-baseline="middle">{{ t.label }}</text>
          </g>
          <path :d="capArea" :fill="frontierHue" :fill-opacity="BAND_OUTER_OPACITY" />
          <path
            v-for="l in regionalPaths"
            :key="l.id"
            :d="l.d"
            fill="none"
            :stroke="l.emphasized ? 'var(--ink)' : 'var(--muted)'"
            :stroke-width="l.emphasized ? 2 : 1"
            :stroke-opacity="l.emphasized ? 1 : 0.7"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
          <path :d="capMedian" fill="none" :stroke="frontierHue" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
          <g class="end-labels">
            <text
              v-for="l in capEndLabels"
              :key="l.id"
              :x="iw + 6"
              :y="l.y"
              dominant-baseline="middle"
              :class="{ strong: l.emphasized }"
            >
              {{ l.text }}
            </text>
          </g>
        </g>

        <!-- price panel -->
        <g class="panel" :transform="`translate(0,${PRICE_Y0})`">
          <text class="panel-title" x="0" y="-6">Price · $ per million tokens (log)</text>
          <g class="grid">
            <line v-for="t in priceTicks" :key="'pg' + t.v" x1="0" :x2="iw" :y1="t.y" :y2="t.y" />
          </g>
          <g class="axis">
            <text v-for="t in priceTicks" :key="'pt' + t.v" x="-10" :y="t.y" text-anchor="end" dominant-baseline="middle">{{ t.label }}</text>
          </g>
          <path :d="priceFixedPath" fill="none" :stroke="frontierHue" stroke-width="2" stroke-dasharray="5 4" stroke-linejoin="round" />
          <path :d="priceFrontierPath" fill="none" :stroke="frontierHue" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
          <g class="end-labels">
            <text v-for="l in priceEndLabels" :key="l.id" :x="iw + 6" :y="l.y" dominant-baseline="middle">{{ l.text }}</text>
          </g>
        </g>

        <!-- crosshair / scrub hit area over the two line panels -->
        <line class="scrub" :x1="x(q)" :x2="x(q)" y1="0" :y2="totalH" />
        <line v-if="hoverQ != null && hoverQ !== q" class="cross" :x1="cursorX" :x2="cursorX" y1="0" :y2="totalH" />
        <rect
          x="0"
          y="0"
          :width="iw"
          :height="PRICE_Y0 + PRICE_H"
          fill="transparent"
          style="cursor: crosshair"
          @pointermove="onPanelMove"
          @pointerleave="onPanelLeave"
          @click="onPanelClick"
        />

        <!-- releases strip -->
        <g class="strip" :transform="`translate(0,${REL_Y0})`">
          <text class="panel-title" x="0" y="-6">Releases · dot = model, hollow = open weights, colour = home region</text>
          <g v-for="(a, i) in actors" :key="a.actor_id">
            <line class="row" x1="0" :x2="iw" :y1="i * ROW_H + ROW_H / 2" :y2="i * ROW_H + ROW_H / 2" />
            <text x="-10" :y="i * ROW_H + ROW_H / 2" text-anchor="end" dominant-baseline="middle">{{ a.name }}</text>
          </g>
        </g>
        <g class="dots">
          <g v-for="d in releaseDots" :key="d.key" tabindex="0" role="img" :aria-label="`${d.r.model}, ${d.r.date}`" @pointerenter="onDot($event, d)" @focus="onDot($event as unknown as PointerEvent, d)" @pointerleave="hide" @blur="hide">
            <circle :cx="d.cx" :cy="d.cy" r="11" fill="transparent" />
            <circle :cx="d.cx" :cy="d.cy" r="5" :fill="d.r.open_weights ? 'var(--surface)' : d.color" :stroke="d.r.open_weights ? d.color : 'var(--surface)'" stroke-width="2" />
          </g>
        </g>

        <!-- rules strip -->
        <g class="strip" :transform="`translate(0,${RULES_Y0})`">
          <text class="panel-title" x="0" y="-6">Rules · regulatory events by region</text>
          <g v-for="(id, i) in ruleRegions" :key="id">
            <line class="row" x1="0" :x2="iw" :y1="i * ROW_H + ROW_H / 2" :y2="i * ROW_H + ROW_H / 2" />
            <text x="-10" :y="i * ROW_H + ROW_H / 2" text-anchor="end" dominant-baseline="middle">{{ isRegionId(id) ? REGION_NAMES[id] : id }}</text>
          </g>
        </g>
        <g class="rules">
          <g v-for="d in ruleMarks" :key="d.e.event_id" tabindex="0" role="img" :aria-label="d.e.description" @pointerenter="onRule(d)" @focus="onRule(d)" @pointerleave="hide" @blur="hide">
            <rect :x="d.x - 8" :y="d.y - 4" width="16" :height="ROW_H" fill="transparent" />
            <rect :x="d.x - 3" :y="d.y" width="6" :height="ROW_H - 8" rx="1.5" fill="var(--ink-2)" />
          </g>
        </g>

        <!-- scenario shocks -->
        <g v-for="s in shockMarks" :key="s.quarter + s.label" class="shock" tabindex="0" role="img" :aria-label="`Shock: ${s.label}`" @pointerenter="onShock(s)" @focus="onShock(s)" @pointerleave="hide" @blur="hide">
          <line :x1="s.x" :x2="s.x" y1="-14" :y2="totalH" />
          <text :x="s.x" y="-18" text-anchor="middle" class="flag">⚑</text>
        </g>

        <!-- shared x axis -->
        <g class="axis" :transform="`translate(0,${totalH})`">
          <line x1="0" :x2="iw" y1="0" y2="0" />
          <g v-for="t in xTicks" :key="'x' + t.i">
            <line :x1="x(t.i)" :x2="x(t.i)" y1="0" y2="5" />
            <text :x="x(t.i)" y="22" text-anchor="middle">{{ t.year }}</text>
          </g>
        </g>
      </g>
    </svg>
    <ChartTooltip :tip="tip" :width="width" />
  </div>
</template>

<style scoped>
.timeline-host {
  min-width: 0;
  overflow: hidden;
  position: relative;
  width: 100%;
}
svg {
  display: block;
}
.panel-title {
  font-size: 14px;
  font-weight: 600;
  fill: var(--ink-2);
}
.strip .row {
  stroke: var(--grid);
  stroke-width: 1;
}
.end-labels text {
  font-size: 14px;
}
.end-labels text.strong {
  fill: var(--ink);
  font-weight: 600;
}
.scrub {
  stroke: var(--ink-2);
  stroke-width: 1.5;
}
.cross {
  stroke: var(--muted);
  stroke-width: 1;
}
.unavail rect {
  fill: var(--ink);
  fill-opacity: 0.07;
}
.dots g,
.rules g,
.shock {
  outline: none;
  cursor: default;
}
.dots g:focus-visible circle:last-child,
.rules g:focus-visible rect:last-child {
  stroke: var(--focus);
  stroke-width: 3;
}
.shock line {
  stroke: var(--ink);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}
.shock .flag {
  font-size: 16px;
  fill: var(--ink);
}
</style>

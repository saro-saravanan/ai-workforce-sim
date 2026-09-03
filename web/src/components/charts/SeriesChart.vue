<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear, extent } from 'd3'
import type { Series } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip, type TooltipRow } from '@/composables/useTooltip'
import { quarterLabel, quarterYear } from '@/lib/format'
import {
  BAND_INNER_OPACITY,
  BAND_OUTER_OPACITY,
  bandPath,
  bandRows,
  hasCentral,
  hasInnerBand,
  hasOuterBand,
  linePath,
  seriesExtentValues,
} from '@/lib/bands'
import ChartTooltip from '@/components/ChartTooltip.vue'

/** A thin comparison line drawn over the series (e.g. a mechanism cell's median). */
export interface Overlay {
  id: string
  label: string
  values: number[]
  /** emphasized overlays are drawn in `color` at 2px; the rest are muted hairlines */
  emphasized?: boolean
  color?: string
}

const props = defineProps<{
  series: Series
  quarters: string[]
  q: number
  hue: string
  label: string
  format: (v: number) => string
  axisFormat: (v: number) => string
  zero?: boolean
  overlays?: Overlay[]
  /** shared y-domain (compare view keeps both panels on one scale) */
  yDomain?: [number, number]
  height?: number
}>()
const emit = defineEmits<{ scrub: [q: number]; domain: [d: [number, number]] }>()

const host = ref<HTMLElement | null>(null)
const { width, height } = useSize(host, { width: 800, height: props.height ?? 300 })
const { tip, show, hide } = useTooltip()
const m = { top: 16, right: 20, bottom: 40, left: 64 }
const iw = computed(() => Math.max(100, width.value - m.left - m.right))
const ih = computed(() => Math.max(80, height.value - m.top - m.bottom))
const n = computed(() => props.series.p50.length)

const x = computed(() =>
  scaleLinear()
    .domain([0, Math.max(1, n.value - 1)])
    .range([0, iw.value]),
)
/** natural domain of this series (+ overlays); exposed so a parent can share it */
const naturalDomain = computed<[number, number]>(() => {
  const all = seriesExtentValues(props.series)
  for (const o of props.overlays ?? []) for (const v of o.values) all.push(v)
  if (props.zero) all.push(0)
  const [lo, hi] = extent(all) as [number, number]
  const padv = (hi - lo || 1) * 0.08
  return [lo - padv, hi + padv]
})
const y = computed(() =>
  scaleLinear()
    .domain(props.yDomain ?? naturalDomain.value)
    .nice(5)
    .range([ih.value, 0]),
)
const outer = computed(() => hasOuterBand(props.series))
const inner = computed(() => hasInnerBand(props.series))
const central = computed(() => hasCentral(props.series))
const median = computed(() => linePath(props.series.p50, x.value, y.value))
const centralPath = computed(() =>
  central.value ? linePath(props.series.central ?? [], x.value, y.value) : '',
)
const outerPath = computed(() =>
  outer.value ? bandPath(props.series.p10 ?? [], props.series.p90 ?? [], x.value, y.value) : '',
)
const innerPath = computed(() =>
  inner.value ? bandPath(props.series.p25 ?? [], props.series.p75 ?? [], x.value, y.value) : '',
)
const overlayPaths = computed(() =>
  (props.overlays ?? []).map((o) => ({ ...o, d: linePath(o.values, x.value, y.value) })),
)
const yTicks = computed(() => y.value.ticks(5))
/** one tick per even year, labelled with the year at Q1 */
const xTicks = computed(() =>
  props.quarters
    .map((qq, i) => ({ i, year: quarterYear(qq), qq }))
    .filter((t) => t.qq.endsWith('Q1') && t.year % 2 === 0),
)
const hoverQ = ref<number | null>(null)
const cursor = computed(() => hoverQ.value ?? props.q)

function onMove(e: PointerEvent) {
  const rect = host.value?.getBoundingClientRect()
  const px = e.clientX - (rect?.left ?? 0) - m.left
  const i = Math.round(Math.min(n.value - 1, Math.max(0, x.value.invert(px))))
  hoverQ.value = i
  const rows: TooltipRow[] = bandRows(props.series, i, props.label, props.format, props.hue)
  for (const o of props.overlays ?? [])
    if (o.emphasized && o.values[i] != null)
      rows.push({ label: o.label, value: props.format(o.values[i]!), swatch: o.color })
  show(
    x.value(i) + m.left,
    y.value(props.series.p50[i] ?? 0) + m.top,
    quarterLabel(props.quarters[i]),
    rows,
  )
}
function onLeave() {
  hoverQ.value = null
  hide()
}
function onClick() {
  if (hoverQ.value != null) emit('scrub', hoverQ.value)
}
defineExpose({ naturalDomain })
</script>

<template>
  <div ref="host" class="series-host" :style="{ height: (props.height ?? 300) + 'px' }">
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="xMinYMin meet" class="rsvg" role="img" :aria-label="`${label} over time`">
      <g :transform="`translate(${m.left},${m.top})`">
        <g class="grid">
          <line v-for="t in yTicks" :key="'g' + t" x1="0" :x2="iw" :y1="y(t)" :y2="y(t)" />
        </g>
        <g class="axis">
          <g v-for="t in yTicks" :key="'y' + t">
            <text :x="-10" :y="y(t)" text-anchor="end" dominant-baseline="middle">
              {{ axisFormat(t) }}
            </text>
          </g>
          <line x1="0" :x2="iw" :y1="ih" :y2="ih" />
          <g v-for="t in xTicks" :key="'x' + t.i">
            <line :x1="x(t.i)" :x2="x(t.i)" :y1="ih" :y2="ih + 5" />
            <text :x="x(t.i)" :y="ih + 22" text-anchor="middle">{{ t.year }}</text>
          </g>
        </g>
        <path v-if="outer" :d="outerPath" :fill="hue" :fill-opacity="BAND_OUTER_OPACITY" />
        <path v-if="inner" :d="innerPath" :fill="hue" :fill-opacity="BAND_INNER_OPACITY" />
        <line v-if="zero" class="zero" x1="0" :x2="iw" :y1="y(0)" :y2="y(0)" />
        <g class="overlays">
          <path
            v-for="o in overlayPaths"
            :key="o.id"
            :d="o.d"
            fill="none"
            :stroke="o.emphasized ? (o.color ?? 'var(--ink)') : 'var(--muted)'"
            :stroke-width="o.emphasized ? 2 : 1"
            :stroke-opacity="o.emphasized ? 1 : 0.7"
            stroke-linejoin="round"
          />
        </g>
        <path
          v-if="central"
          :d="centralPath"
          fill="none"
          :stroke="hue"
          stroke-width="1.2"
          stroke-dasharray="4 3"
        />
        <path
          :d="median"
          fill="none"
          :stroke="hue"
          stroke-width="2"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
        <line class="scrub" :x1="x(q)" :x2="x(q)" y1="0" :y2="ih" />
        <line
          v-if="hoverQ != null && hoverQ !== q"
          class="cross"
          :x1="x(cursor)"
          :x2="x(cursor)"
          y1="0"
          :y2="ih"
        />
        <circle :cx="x(cursor)" :cy="y(series.p50[cursor] ?? 0)" r="5" :fill="hue" class="marker" />
        <rect
          x="0"
          y="0"
          :width="iw"
          :height="ih"
          fill="transparent"
          style="cursor: crosshair"
          @pointermove="onMove"
          @pointerleave="onLeave"
          @click="onClick"
        />
      </g>
    </svg>
    <ChartTooltip :tip="tip" :width="width" />
  </div>
</template>

<style scoped>
.series-host {
  min-width: 0;
  overflow: hidden;
  position: relative;
  width: 100%;
}
svg {
  display: block;
}
.zero {
  stroke: var(--muted);
  stroke-width: 1;
  stroke-dasharray: 2 3;
}
.scrub {
  stroke: var(--ink-2);
  stroke-width: 1.5;
}
.cross {
  stroke: var(--muted);
  stroke-width: 1;
}
.marker {
  stroke: var(--surface);
  stroke-width: 2;
}
.rsvg {
  max-width: 100%;
  height: auto;
  display: block;
}
</style>

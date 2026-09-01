<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear, line as d3line, area as d3area, extent } from 'd3'
import type { Series } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { quarterLabel, quarterYear } from '@/lib/format'
import ChartTooltip from '@/components/ChartTooltip.vue'

const props = defineProps<{
  series: Series
  quarters: string[]
  q: number
  hue: string
  label: string
  format: (v: number) => string
  axisFormat: (v: number) => string
  zero?: boolean
}>()
const emit = defineEmits<{ scrub: [q: number] }>()

const host = ref<HTMLElement | null>(null)
const { width, height } = useSize(host, { width: 800, height: 300 })
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
const y = computed(() => {
  const all = [...props.series.p50, ...(props.series.p10 ?? []), ...(props.series.p90 ?? [])]
  if (props.zero) all.push(0)
  const [lo, hi] = extent(all) as [number, number]
  const padv = (hi - lo || 1) * 0.08
  return scaleLinear()
    .domain([lo - padv, hi + padv])
    .nice(5)
    .range([ih.value, 0])
})
const hasBand = computed(() => !!(props.series.p10 && props.series.p90))
const median = computed(
  () =>
    d3line<number>()
      .x((_, i) => x.value(i))
      .y((d) => y.value(d))(props.series.p50) ?? '',
)
const band = computed(() => {
  if (!hasBand.value) return ''
  const p10 = props.series.p10 ?? []
  const p90 = props.series.p90 ?? []
  return (
    d3area<number>()
      .x((_, i) => x.value(i))
      .y0((_, i) => y.value(p10[i] ?? 0))
      .y1((_, i) => y.value(p90[i] ?? 0))(props.series.p50) ?? ''
  )
})
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
  const v = props.series.p50[i]
  const lo = props.series.p10?.[i]
  const hi = props.series.p90?.[i]
  const rows = [{ label: props.label, value: v == null ? '—' : props.format(v), swatch: props.hue }]
  if (lo != null && hi != null)
    rows.push({
      label: '10–90 band',
      value: `${props.format(lo)} to ${props.format(hi)}`,
      swatch: props.hue,
    })
  show(x.value(i) + m.left, y.value(v ?? 0) + m.top, quarterLabel(props.quarters[i]), rows)
}
function onLeave() {
  hoverQ.value = null
  hide()
}
function onClick() {
  if (hoverQ.value != null) emit('scrub', hoverQ.value)
}
</script>

<template>
  <div ref="host" class="series-host">
    <svg :width="width" :height="height" role="img" :aria-label="`${label} over time`">
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
        <path v-if="hasBand" :d="band" :fill="hue" fill-opacity="0.14" />
        <line v-if="zero" class="zero" x1="0" :x2="iw" :y1="y(0)" :y2="y(0)" />
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
  height: 300px;
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
</style>

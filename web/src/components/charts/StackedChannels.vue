<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  scaleLinear,
  stack,
  stackOffsetDiverging,
  area as d3area,
  line as d3line,
  extent,
} from 'd3'
import type { ChannelDecomposition, Series } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip, type TooltipRow } from '@/composables/useTooltip'
import { quarterLabel, quarterYear } from '@/lib/format'
import { CHANNEL_LABELS, channelColorScale } from '@/lib/metrics'
import type { Mode } from '@/lib/palette'
import ChartTooltip from '@/components/ChartTooltip.vue'

const props = defineProps<{
  channels: ChannelDecomposition
  /** the net series the channels sum to (drawn as an ink line for reference) */
  net: Series
  quarters: string[]
  q: number
  mode: Mode
  format: (v: number) => string
  axisFormat: (v: number) => string
  unit: string
}>()

const host = ref<HTMLElement | null>(null)
const { width, height } = useSize(host, { width: 800, height: 260 })
const { tip, show, hide } = useTooltip()
const m = { top: 12, right: 20, bottom: 40, left: 64 }
const iw = computed(() => Math.max(100, width.value - m.left - m.right))
const ih = computed(() => Math.max(80, height.value - m.top - m.bottom))

const keys = computed(() => props.channels.order.filter((k) => props.channels.contributions[k]))
const color = computed(() => channelColorScale(keys.value, props.mode))
const rows = computed(() =>
  props.quarters.map((_, i) => {
    const row: Record<string, number> = {}
    for (const k of keys.value) row[k] = props.channels.contributions[k]?.[i] ?? 0
    return row
  }),
)
const layers = computed(() =>
  stack<Record<string, number>>().keys(keys.value).offset(stackOffsetDiverging)(rows.value),
)
const x = computed(() =>
  scaleLinear()
    .domain([0, Math.max(1, rows.value.length - 1)])
    .range([0, iw.value]),
)
const y = computed(() => {
  const all: number[] = [0]
  for (const l of layers.value) for (const p of l) all.push(p[0], p[1])
  const [lo, hi] = extent(all) as [number, number]
  return scaleLinear().domain([lo, hi]).nice(5).range([ih.value, 0])
})
const areas = computed(() =>
  layers.value.map((l) => ({
    key: l.key,
    fill: color.value(l.key),
    d:
      d3area<[number, number]>()
        .x((_, i) => x.value(i))
        .y0((d) => y.value(d[0]))
        .y1((d) => y.value(d[1]))(l as unknown as [number, number][]) ?? '',
  })),
)
const netPath = computed(
  () =>
    d3line<number>()
      .x((_, i) => x.value(i))
      .y((d) => y.value(d))(props.net.p50) ?? '',
)
const yTicks = computed(() => y.value.ticks(5))
const xTicks = computed(() =>
  props.quarters
    .map((qq, i) => ({ i, year: quarterYear(qq), qq }))
    .filter((t) => t.qq.endsWith('Q1') && t.year % 2 === 0),
)
const hoverQ = ref<number | null>(null)

function tooltipRows(i: number): TooltipRow[] {
  const out: TooltipRow[] = keys.value.map((k) => ({
    label: CHANNEL_LABELS[k] ?? k,
    value: props.format(rows.value[i]?.[k] ?? 0),
    swatch: color.value(k),
    kind: 'rect',
  }))
  out.push({ label: 'Net', value: props.format(props.net.p50[i] ?? 0) })
  return out
}
function onMove(e: PointerEvent) {
  const rect = host.value?.getBoundingClientRect()
  const px = e.clientX - (rect?.left ?? 0) - m.left
  const i = Math.round(Math.min(rows.value.length - 1, Math.max(0, x.value.invert(px))))
  hoverQ.value = i
  show(x.value(i) + m.left, m.top + 10, quarterLabel(props.quarters[i]), tooltipRows(i))
}
function onLeave() {
  hoverQ.value = null
  hide()
}
const atQ = computed(() => tooltipRows(props.q))
</script>

<template>
  <div class="channels">
    <div class="legend" role="list">
      <span v-for="k in keys" :key="k" class="item" role="listitem">
        <span class="sw" :style="{ background: color(k) }"></span>{{ CHANNEL_LABELS[k] ?? k }}
      </span>
      <span class="item"><span class="sw line"></span>Net</span>
    </div>
    <div ref="host" class="stack-host">
      <svg :width="width" :height="height" role="img" aria-label="Channel decomposition, stacked">
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
          <path
            v-for="a in areas"
            :key="a.key"
            :d="a.d"
            :fill="a.fill"
            fill-opacity="0.85"
            class="layer"
          />
          <line class="zero" x1="0" :x2="iw" :y1="y(0)" :y2="y(0)" />
          <path :d="netPath" fill="none" class="net" stroke-width="2" />
          <line class="scrub" :x1="x(q)" :x2="x(q)" y1="0" :y2="ih" />
          <line
            v-if="hoverQ != null"
            class="cross"
            :x1="x(hoverQ)"
            :x2="x(hoverQ)"
            y1="0"
            :y2="ih"
          />
          <rect
            x="0"
            y="0"
            :width="iw"
            :height="ih"
            fill="transparent"
            style="cursor: crosshair"
            @pointermove="onMove"
            @pointerleave="onLeave"
          />
        </g>
      </svg>
      <ChartTooltip :tip="tip" :width="width" />
    </div>
    <div class="at" role="list" :aria-label="`Contributions at ${quarterLabel(quarters[q])}`">
      <span class="muted at-caption">Contributions at {{ quarterLabel(quarters[q]) }} ({{ unit }})</span>
      <div class="at-cells">
        <div v-for="r in atQ" :key="r.label" class="at-cell" role="listitem">
          <span class="cell-label"
            ><span v-if="r.swatch" class="sw" :style="{ background: r.swatch }"></span
            >{{ r.label }}</span
          >
          <strong class="mono">{{ r.value }}</strong>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.channels {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.stack-host {
  min-width: 0;
  overflow: hidden;
  position: relative;
  width: 100%;
  height: 260px;
}
svg {
  display: block;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 14px;
  color: var(--ink-2);
}
.item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.sw {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
.sw.line {
  height: 2px;
  background: var(--ink);
}
.layer {
  stroke: var(--surface);
  stroke-width: 2;
}
.zero {
  stroke: var(--muted);
  stroke-dasharray: 2 3;
}
.net {
  stroke: var(--ink);
}
.scrub {
  stroke: var(--ink-2);
  stroke-width: 1.5;
}
.cross {
  stroke: var(--muted);
}
.at {
  font-size: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.at-cells {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 22px;
}
.at-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.cell-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ink-2);
}
</style>

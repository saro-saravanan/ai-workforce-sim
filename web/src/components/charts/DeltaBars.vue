<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear } from 'd3'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { DIVERGING, type Mode } from '@/lib/palette'
import ChartTooltip from '@/components/ChartTooltip.vue'

export interface DeltaRow {
  key: string
  label: string
  value: number
  /** extra tooltip rows */
  extra?: Array<{ label: string; value: string }>
}

const props = defineProps<{
  rows: DeltaRow[]
  format: (v: number) => string
  axisFormat: (v: number) => string
  mode: Mode
  title: string
  positiveLabel: string
  negativeLabel: string
}>()

const host = ref<HTMLElement | null>(null)
const ROW_H = 26
const m = { top: 6, right: 16, bottom: 28, left: 290 }
const { width } = useSize(host, { width: 500, height: 200 })
const height = computed(() => m.top + m.bottom + props.rows.length * ROW_H)
const iw = computed(() => Math.max(80, width.value - m.left - m.right))
const { tip, show, hide } = useTooltip()

const x = computed(() => {
  let mx = 0
  for (const r of props.rows) mx = Math.max(mx, Math.abs(r.value))
  if (mx === 0) mx = 1
  return scaleLinear().domain([-mx, mx]).nice(4).range([0, iw.value])
})
const neg = computed(() => DIVERGING[props.mode].neg)
const pos = computed(() => DIVERGING[props.mode].pos)
const BAR = 16
const bars = computed(() =>
  props.rows.map((r, i) => {
    const x0 = x.value(0)
    const xv = x.value(r.value)
    return { r, cy: m.top + i * ROW_H + ROW_H / 2, x: Math.min(x0, xv), w: Math.abs(xv - x0), fill: r.value < 0 ? neg.value : pos.value }
  }),
)
const ticks = computed(() => x.value.ticks(4))
const hovered = ref<string | null>(null)

function onEnter(e: PointerEvent, b: (typeof bars.value)[number]) {
  hovered.value = b.r.key
  const rect = host.value?.getBoundingClientRect()
  show(e.clientX - (rect?.left ?? 0), e.clientY - (rect?.top ?? 0), b.r.label, [
    { label: 'Δ (B − A)', value: props.format(b.r.value), swatch: b.fill, kind: 'rect' },
    ...(b.r.extra ?? []),
  ])
}
function onLeave() {
  hovered.value = null
  hide()
}
</script>

<template>
  <div class="delta-bars">
    <div class="legend" role="list">
      <span class="item" role="listitem"><span class="sw" :style="{ background: neg }"></span>{{ negativeLabel }}</span>
      <span class="item" role="listitem"><span class="sw" :style="{ background: pos }"></span>{{ positiveLabel }}</span>
    </div>
    <div ref="host" class="host">
      <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="xMinYMin meet" class="rsvg" role="img" :aria-label="title">
        <g class="grid">
          <line v-for="t in ticks" :key="'g' + t" :x1="m.left + x(t)" :x2="m.left + x(t)" :y1="m.top" :y2="height - m.bottom" />
        </g>
        <g class="axis">
          <text v-for="t in ticks" :key="'t' + t" :x="m.left + x(t)" :y="height - m.bottom + 18" text-anchor="middle">
            {{ axisFormat(t) }}
          </text>
        </g>
        <g
          v-for="b in bars"
          :key="b.r.key"
          :class="{ dim: hovered && hovered !== b.r.key }"
          @pointerenter="onEnter($event, b)"
          @pointermove="onEnter($event, b)"
          @pointerleave="onLeave"
        >
          <rect :x="0" :y="b.cy - ROW_H / 2" :width="width" :height="ROW_H" fill="transparent" />
          <text :x="m.left - 10" :y="b.cy" text-anchor="end" dominant-baseline="middle" class="name">
            {{ b.r.label.length > 36 ? b.r.label.slice(0, 35) + '…' : b.r.label }}
          </text>
          <rect :x="m.left + b.x" :y="b.cy - BAR / 2" :width="Math.max(0, b.w)" :height="BAR" :fill="b.fill" rx="3" />
        </g>
        <line class="zero" :x1="m.left + x(0)" :x2="m.left + x(0)" :y1="m.top" :y2="height - m.bottom" />
      </svg>
      <ChartTooltip :tip="tip" :width="width" />
    </div>
  </div>
</template>

<style scoped>
.delta-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.host {
  position: relative;
  min-width: 0;
  overflow: hidden;
}
svg {
  display: block;
}
.legend {
  display: flex;
  gap: 14px;
  font-size: 14px;
  color: var(--ink-2);
  flex-wrap: wrap;
}
.item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.sw {
  width: 12px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.name {
  fill: var(--ink);
}
.zero {
  stroke: var(--ink-2);
}
g {
  transition: opacity var(--t);
}
.dim {
  opacity: 0.4;
}
.rsvg {
  max-width: 100%;
  height: auto;
  display: block;
}
</style>

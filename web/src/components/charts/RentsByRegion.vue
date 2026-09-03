<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear } from 'd3'
import type { RentStage, RentsByStage } from '@/types/results'
import { RENT_STAGES } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { stackCategorical } from '@/lib/scales'
import { fmtBn } from '@/lib/format'
import { RENT_STAGE_LABELS } from '@/lib/metrics'
import type { Mode } from '@/lib/palette'
import ChartTooltip from '@/components/ChartTooltip.vue'

const props = defineProps<{
  /** region id → rents by stage */
  rows: Array<{ id: string; name: string; rents: RentsByStage }>
  q: number
  mode: Mode
  quarterLabel: string
}>()

const host = ref<HTMLElement | null>(null)
const { width } = useSize(host, { width: 700, height: 300 })
const { tip, show, hide } = useTooltip()
const m = { top: 4, right: 90, bottom: 26, left: 136 }
const ROW = 26
const BAR = 18
const iw = computed(() => Math.max(100, width.value - m.left - m.right))
const color = computed(() => stackCategorical(RENT_STAGES, props.mode))

const data = computed(() =>
  props.rows
    .map((r) => {
      let acc = 0
      const segs = RENT_STAGES.map((st) => {
        const v = r.rents[st].p50[props.q] ?? 0
        const s = { st, v, x0: acc, x1: acc + v }
        acc += v
        return s
      })
      return { ...r, segs, total: acc }
    })
    .sort((a, b) => b.total - a.total),
)
const x = computed(() =>
  scaleLinear()
    .domain([0, Math.max(1, ...data.value.map((d) => d.total))])
    .nice(4)
    .range([0, iw.value]),
)
const height = computed(() => m.top + data.value.length * ROW + m.bottom)
const ticks = computed(() => x.value.ticks(4))

function onSeg(e: PointerEvent, d: (typeof data.value)[number], s: { st: RentStage; v: number }) {
  const r = host.value?.getBoundingClientRect()
  show(
    e.clientX - (r?.left ?? 0),
    e.clientY - (r?.top ?? 0),
    `${d.name}, ${props.quarterLabel}`,
    [
      { label: RENT_STAGE_LABELS[s.st], value: fmtBn(s.v), swatch: color.value(s.st), kind: 'rect' },
      { label: 'Share of region total', value: d.total > 0 ? `${((100 * s.v) / d.total).toFixed(0)}%` : '—' },
      { label: 'Region total', value: fmtBn(d.total) },
    ],
  )
}
</script>

<template>
  <div ref="host" class="rents-host" :style="{ height: height + 'px' }">
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="xMinYMin meet" class="rsvg" role="img" :aria-label="`AI rents received by region and stage, ${quarterLabel}`">
      <g :transform="`translate(${m.left},${m.top})`">
        <g class="grid">
          <line v-for="t in ticks" :key="t" :x1="x(t)" :x2="x(t)" y1="0" :y2="data.length * ROW" />
        </g>
        <g v-for="(d, i) in data" :key="d.id" :transform="`translate(0,${i * ROW})`">
          <text x="-10" :y="ROW / 2" text-anchor="end" dominant-baseline="middle">{{ d.name }}</text>
          <rect
            v-for="s in d.segs"
            :key="s.st"
            :x="x(s.x0)"
            :y="(ROW - BAR) / 2"
            :width="Math.max(0, x(s.x1) - x(s.x0))"
            :height="BAR"
            :fill="color(s.st)"
            stroke="var(--surface)"
            stroke-width="2"
            @pointerenter="onSeg($event, d, s)"
            @pointermove="onSeg($event, d, s)"
            @pointerleave="hide"
          />
          <text :x="x(d.total) + 8" :y="ROW / 2" dominant-baseline="middle" class="mono total">{{ fmtBn(d.total) }}</text>
        </g>
        <g class="axis" :transform="`translate(0,${data.length * ROW})`">
          <line x1="0" :x2="iw" y1="0" y2="0" />
          <text v-for="t in ticks" :key="'t' + t" :x="x(t)" y="18" text-anchor="middle">{{ fmtBn(t) }}</text>
        </g>
      </g>
    </svg>
    <ChartTooltip :tip="tip" :width="width" />
  </div>
</template>

<style scoped>
.rents-host {
  position: relative;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
svg {
  display: block;
}
.total {
  fill: var(--ink);
  font-variant-numeric: tabular-nums;
}
.rsvg {
  max-width: 100%;
  height: auto;
  display: block;
}
</style>

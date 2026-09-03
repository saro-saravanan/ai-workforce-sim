<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear } from 'd3'
import type { CohortRow } from '@/types/results'
import type { CohortMetric } from '@/lib/metrics'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import ChartTooltip from '@/components/ChartTooltip.vue'

const props = defineProps<{
  rows: CohortRow[]
  metric: CohortMetric
  q: number
  label: (band: string) => string
  /** shared across the three panels so bars are comparable */
  domain: [number, number]
  format: (v: number) => string
  axisFormat: (v: number) => string
  hue: string
  zero: boolean
  selected: string | null
  title: string
}>()
const emit = defineEmits<{ select: [band: string | null] }>()

const host = ref<HTMLElement | null>(null)
const ROW_H = 30
const m = { top: 8, right: 12, bottom: 30, left: 112 }
const { width } = useSize(host, { width: 360, height: 200 })
const height = computed(() => m.top + m.bottom + props.rows.length * ROW_H)
const iw = computed(() => Math.max(80, width.value - m.left - m.right))
const { tip, show, hide } = useTooltip()

const x = computed(() => scaleLinear().domain(props.domain).nice(3).range([0, iw.value]))
const BAR = 18
const bars = computed(() =>
  props.rows.map((r, i) => {
    const s = r[props.metric]
    const v = s.p50[props.q] ?? 0
    const lo = s.p10?.[props.q]
    const hi = s.p90?.[props.q]
    const x0 = x.value(0)
    const xv = x.value(v)
    return {
      band: r.band,
      v,
      lo,
      hi,
      cy: m.top + i * ROW_H + ROW_H / 2,
      x: Math.min(x0, xv),
      w: Math.abs(xv - x0),
      xlo: lo != null ? x.value(lo) : null,
      xhi: hi != null ? x.value(hi) : null,
    }
  }),
)
const ticks = computed(() => x.value.ticks(3))
const hovered = ref<string | null>(null)

function onEnter(e: PointerEvent, b: (typeof bars.value)[number]) {
  hovered.value = b.band
  const rect = host.value?.getBoundingClientRect()
  const rows = [{ label: 'Median', value: props.format(b.v), swatch: props.hue, kind: 'rect' as const }]
  if (b.lo != null && b.hi != null)
    rows.push({ label: '10–90 band', value: `${props.format(b.lo)} to ${props.format(b.hi)}`, swatch: props.hue, kind: 'rect' })
  show(e.clientX - (rect?.left ?? 0), e.clientY - (rect?.top ?? 0), `${props.title}: ${props.label(b.band)}`, rows)
}
function onLeave() {
  hovered.value = null
  hide()
}
function onClick(band: string) {
  emit('select', props.selected === band ? null : band)
}
</script>

<template>
  <div ref="host" class="cohort-host">
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="xMinYMin meet" class="rsvg" role="img" :aria-label="`${title} by cohort`">
      <g class="grid">
        <line
          v-for="t in ticks"
          :key="'g' + t"
          :x1="m.left + x(t)"
          :x2="m.left + x(t)"
          :y1="m.top"
          :y2="height - m.bottom"
        />
      </g>
      <g class="axis">
        <text
          v-for="t in ticks"
          :key="'t' + t"
          :x="m.left + x(t)"
          :y="height - m.bottom + 18"
          text-anchor="middle"
        >
          {{ axisFormat(t) }}
        </text>
      </g>
      <g
        v-for="b in bars"
        :key="b.band"
        class="row"
        :class="{
          dim: (selected && selected !== b.band) || (hovered && hovered !== b.band),
          selected: selected === b.band,
        }"
        tabindex="0"
        role="button"
        :aria-pressed="selected === b.band"
        :aria-label="`${label(b.band)}: ${format(b.v)}`"
        @pointerenter="onEnter($event, b)"
        @pointermove="onEnter($event, b)"
        @pointerleave="onLeave"
        @click="onClick(b.band)"
        @keydown.enter.prevent="onClick(b.band)"
        @keydown.space.prevent="onClick(b.band)"
      >
        <rect :x="0" :y="b.cy - ROW_H / 2" :width="width" :height="ROW_H" fill="transparent" />
        <text :x="m.left - 10" :y="b.cy" text-anchor="end" dominant-baseline="middle" class="name">
          {{ label(b.band) }}
        </text>
        <rect
          :x="m.left + b.x"
          :y="b.cy - BAR / 2"
          :width="Math.max(0, b.w)"
          :height="BAR"
          :fill="hue"
          rx="3"
          class="bar"
        />
        <g v-if="b.xlo != null && b.xhi != null" class="whisker">
          <line :x1="m.left + b.xlo" :x2="m.left + b.xhi" :y1="b.cy" :y2="b.cy" />
          <line :x1="m.left + b.xlo" :x2="m.left + b.xlo" :y1="b.cy - 5" :y2="b.cy + 5" />
          <line :x1="m.left + b.xhi" :x2="m.left + b.xhi" :y1="b.cy - 5" :y2="b.cy + 5" />
        </g>
      </g>
      <line
        v-if="zero"
        class="zero"
        :x1="m.left + x(0)"
        :x2="m.left + x(0)"
        :y1="m.top"
        :y2="height - m.bottom"
      />
    </svg>
    <ChartTooltip :tip="tip" :width="width" />
  </div>
</template>

<style scoped>
.cohort-host {
  position: relative;
  min-width: 0;
  overflow: hidden;
}
svg {
  display: block;
}
.row {
  cursor: pointer;
  outline: none;
  transition: opacity var(--t);
}
.row.dim {
  opacity: 0.4;
}
.row:focus-visible .bar {
  stroke: var(--focus);
  stroke-width: 2;
}
.row.selected .bar {
  stroke: var(--ink);
  stroke-width: 1.5;
}
.name {
  fill: var(--ink);
}
.whisker line {
  stroke: var(--ink);
  stroke-width: 1.5;
}
.zero {
  stroke: var(--ink-2);
  stroke-width: 1;
}
.rsvg {
  max-width: 100%;
  height: auto;
  display: block;
}
</style>

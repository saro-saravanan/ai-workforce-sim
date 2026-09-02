<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear } from 'd3'
import type { RegionsChart } from '@/types/story'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { CATEGORICAL, DIVERGING, type Mode } from '@/lib/palette'
import { fmtBn, fmtPct } from '@/lib/format'
import { regionName } from '@/lib/story'
import ChartTooltip from '@/components/ChartTooltip.vue'

/** The money beat: per region, employment % versus no AI and AI income in $bn a year, side by side. */
const props = defineProps<{ chart: RegionsChart; mode: Mode }>()

const host = ref<HTMLElement | null>(null)
const ROW_H = 26
const BAR = 12
const GAP = 40
const m = { top: 22, right: 56, bottom: 6, left: 130 }
const { width } = useSize(host, { width: 600, height: 200 })
const { tip, show, hide } = useTooltip()

const height = computed(() => m.top + m.bottom + props.chart.items.length * ROW_H)
const panelW = computed(() => Math.max(60, (width.value - m.left - m.right - GAP) / 2))
const empX = computed(() => {
  let mx = 0
  for (const [, e] of props.chart.items) mx = Math.max(mx, Math.abs(e))
  return scaleLinear()
    .domain([-(mx || 1), mx || 1])
    .nice(3)
    .range([0, panelW.value])
})
const rentX = computed(() => {
  let mx = 0
  for (const [, , , r] of props.chart.items) mx = Math.max(mx, r)
  return scaleLinear()
    .domain([0, mx || 1])
    .nice(3)
    .range([0, panelW.value])
})
const rentLeft = computed(() => m.left + panelW.value + GAP)
const pos = computed(() => DIVERGING[props.mode].pos)
const neg = computed(() => DIVERGING[props.mode].neg)
const rentColor = computed(() => CATEGORICAL[props.mode][3] ?? '#eda100')
const rows = computed(() =>
  props.chart.items.map(([id, emp, gdp, rents], i) => {
    const x0 = empX.value(0)
    const xe = empX.value(emp)
    return {
      id,
      name: regionName(id),
      emp,
      gdp,
      rents,
      cy: m.top + i * ROW_H + ROW_H / 2,
      empX: Math.min(x0, xe),
      empW: Math.abs(xe - x0),
      empFill: emp < 0 ? neg.value : pos.value,
      rentW: rentX.value(rents),
    }
  }),
)
const hovered = ref<string | null>(null)

function onEnter(e: PointerEvent, r: (typeof rows.value)[number]) {
  hovered.value = r.id
  const rect = host.value?.getBoundingClientRect()
  show(e.clientX - (rect?.left ?? 0), e.clientY - (rect?.top ?? 0), r.name, [
    { label: 'Jobs in 2040 vs no AI', value: fmtPct(r.emp), swatch: r.empFill, kind: 'rect' },
    { label: 'Economy (GDP) vs no AI', value: fmtPct(r.gdp) },
    { label: 'AI income a year', value: fmtBn(r.rents), swatch: rentColor.value, kind: 'rect' },
  ])
}
function onLeave() {
  hovered.value = null
  hide()
}
</script>

<template>
  <div ref="host" class="host">
    <svg :width="width" :height="height" role="img" aria-label="Jobs and AI income by region">
      <g class="axis">
        <text :x="m.left" :y="12" class="axis-title">Jobs in 2040, % versus no AI</text>
        <text :x="rentLeft" :y="12" class="axis-title">AI income, $bn a year</text>
      </g>
      <g
        v-for="r in rows"
        :key="r.id"
        class="row"
        :class="{ dim: hovered && hovered !== r.id }"
        @pointerenter="onEnter($event, r)"
        @pointermove="onEnter($event, r)"
        @pointerleave="onLeave"
      >
        <rect :x="0" :y="r.cy - ROW_H / 2" :width="width" :height="ROW_H" fill="transparent" />
        <text :x="m.left - 10" :y="r.cy" text-anchor="end" dominant-baseline="middle" class="name">
          {{ r.name }}
        </text>
        <rect
          :x="m.left + r.empX"
          :y="r.cy - BAR / 2"
          :width="Math.max(0, r.empW)"
          :height="BAR"
          :fill="r.empFill"
          rx="2"
        />
        <text
          :x="m.left + (r.emp < 0 ? r.empX - 5 : r.empX + r.empW + 5)"
          :y="r.cy"
          dominant-baseline="middle"
          :text-anchor="r.emp < 0 ? 'end' : 'start'"
          class="val mono"
        >
          {{ fmtPct(r.emp) }}
        </text>
        <rect
          :x="rentLeft"
          :y="r.cy - BAR / 2"
          :width="Math.max(0, r.rentW)"
          :height="BAR"
          :fill="rentColor"
          rx="2"
        />
        <text :x="rentLeft + r.rentW + 5" :y="r.cy" dominant-baseline="middle" class="val mono">
          {{ fmtBn(r.rents) }}
        </text>
      </g>
      <line
        class="zero"
        :x1="m.left + empX(0)"
        :x2="m.left + empX(0)"
        :y1="m.top"
        :y2="height - m.bottom"
      />
      <line class="zero" :x1="rentLeft" :x2="rentLeft" :y1="m.top" :y2="height - m.bottom" />
    </svg>
    <ChartTooltip :tip="tip" :width="width" />
  </div>
</template>

<style scoped>
.host {
  position: relative;
  min-width: 0;
  overflow: hidden;
}
svg {
  display: block;
}
.name {
  fill: var(--ink);
}
.val {
  fill: var(--ink-2);
  font-size: 12px;
}
.zero {
  stroke: var(--ink-2);
}
.row {
  transition: opacity var(--t);
}
.dim {
  opacity: 0.4;
}
</style>

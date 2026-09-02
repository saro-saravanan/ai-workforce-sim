<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear } from 'd3'
import type { TimelineChart, TimelineItem } from '@/types/story'
import { APPLICATION_FAMILIES } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { CATEGORICAL, type Mode } from '@/lib/palette'
import { fmtCompact } from '@/lib/format'
import ChartTooltip from '@/components/ChartTooltip.vue'

/**
 * The waves beat: one dot per application at the year it first displaces 1% of its target
 * task-hours, coloured by family, with the application's name; rows grouped by family.
 */
const props = defineProps<{ chart: TimelineChart; mode: Mode }>()

const host = ref<HTMLElement | null>(null)
const ROW_H = 24
const m = { top: 22, right: 16, bottom: 8, left: 12 }
const { width } = useSize(host, { width: 600, height: 200 })
const { tip, show, hide } = useTooltip()

/** family → palette slot (the validated first four) */
const FAMILY_SLOT: Record<string, number> = { embodied: 1, output: 2, traded: 3, software: 0 }
const familyColor = (f: string) => CATEGORICAL[props.mode][FAMILY_SLOT[f] ?? 4] ?? '#888'
const familyOrder = (f: string) => {
  const i = (APPLICATION_FAMILIES as string[]).indexOf(f)
  return i < 0 ? 99 : i
}
const rows = computed(() =>
  [...props.chart.items]
    .filter((it) => it.first_year)
    .sort(
      (a, b) =>
        familyOrder(a.family) - familyOrder(b.family) ||
        Number(a.first_year) - Number(b.first_year) ||
        a.app.localeCompare(b.app),
    ),
)
const height = computed(() => m.top + m.bottom + rows.value.length * ROW_H)
const iw = computed(() => Math.max(80, width.value - m.left - m.right))
const x = computed(() =>
  scaleLinear()
    .domain([props.chart.start, props.chart.end + 1])
    .range([0, iw.value]),
)
const years = computed(() => {
  const out: number[] = []
  for (let y = props.chart.start; y <= props.chart.end; y += 2) out.push(y)
  return out
})
const dots = computed(() =>
  rows.value.map((it, i) => {
    const cx = x.value(Number(it.first_year) + 0.5)
    const flip = cx + 10 + it.app.length * 7.5 > iw.value
    return { it, cy: m.top + i * ROW_H + ROW_H / 2, cx, fill: familyColor(it.family), flip }
  }),
)
const families = computed(() => {
  const seen = new Map<string, string>()
  for (const it of rows.value) if (!seen.has(it.family)) seen.set(it.family, it.family_words)
  return [...seen.entries()]
    .sort((a, b) => familyOrder(a[0]) - familyOrder(b[0]))
    .map(([family, words]) => ({ family, words, color: familyColor(family) }))
})
const hovered = ref<string | null>(null)

function onEnter(e: PointerEvent, d: { it: TimelineItem; fill: string }) {
  hovered.value = d.it.app
  const rect = host.value?.getBoundingClientRect()
  show(e.clientX - (rect?.left ?? 0), e.clientY - (rect?.top ?? 0), d.it.app, [
    { label: d.it.family_words, value: `from ${d.it.first_year}`, swatch: d.fill, kind: 'rect' },
    { label: 'Task-hours done in 2030', value: `${d.it.share_2030.toFixed(1)}%` },
    { label: 'Task-hours done in 2040', value: `${d.it.share_2040.toFixed(1)}%` },
    { label: 'Workers in its path (2024)', value: fmtCompact(d.it.target_jobs) },
  ])
}
function onLeave() {
  hovered.value = null
  hide()
}
</script>

<template>
  <div class="timeline">
    <div class="legend" role="list">
      <span v-for="f in families" :key="f.family" class="item" role="listitem">
        <span class="sw" :style="{ background: f.color }"></span>{{ f.words }}
      </span>
      <span class="muted">dot = the year the application first does 1% of its target work</span>
    </div>
    <div ref="host" class="host">
      <svg :width="width" :height="height" role="img" aria-label="When each application arrives">
        <g class="grid">
          <line
            v-for="y in years"
            :key="'g' + y"
            :x1="m.left + x(y)"
            :x2="m.left + x(y)"
            :y1="m.top - 4"
            :y2="height - m.bottom"
          />
        </g>
        <g class="axis">
          <text
            v-for="y in years"
            :key="'y' + y"
            :x="m.left + x(y)"
            :y="m.top - 8"
            text-anchor="middle"
          >
            {{ y }}
          </text>
        </g>
        <g
          v-for="d in dots"
          :key="d.it.app"
          class="row"
          :class="{ dim: hovered && hovered !== d.it.app }"
          @pointerenter="onEnter($event, d)"
          @pointermove="onEnter($event, d)"
          @pointerleave="onLeave"
        >
          <rect :x="0" :y="d.cy - ROW_H / 2" :width="width" :height="ROW_H" fill="transparent" />
          <line class="lead" :x1="m.left" :x2="m.left + d.cx" :y1="d.cy" :y2="d.cy" />
          <circle :cx="m.left + d.cx" :cy="d.cy" r="6" :fill="d.fill" class="dot" />
          <text
            :x="m.left + d.cx + (d.flip ? -10 : 10)"
            :y="d.cy"
            dominant-baseline="middle"
            :text-anchor="d.flip ? 'end' : 'start'"
            class="name"
          >
            {{ d.it.app }}
          </text>
        </g>
      </svg>
      <ChartTooltip :tip="tip" :width="width" />
    </div>
  </div>
</template>

<style scoped>
.timeline {
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
  gap: 6px 14px;
  font-size: 14px;
  color: var(--ink-2);
  flex-wrap: wrap;
  align-items: center;
}
.item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.sw {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.lead {
  stroke: var(--grid);
  stroke-dasharray: 2 3;
}
.dot {
  stroke: var(--surface);
  stroke-width: 1.5;
}
.name {
  fill: var(--ink);
  font-size: 13px;
}
.row {
  transition: opacity var(--t);
}
.dim {
  opacity: 0.4;
}
</style>

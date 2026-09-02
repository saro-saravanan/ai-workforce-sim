<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear, Delaunay } from 'd3'
import type { OccupationResult } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { radiusScale } from '@/lib/scales'
import { fmtCompact, fmtShare } from '@/lib/format'
import { MAJOR_GROUPS } from '@/lib/metrics'
import ChartTooltip from '@/components/ChartTooltip.vue'

export interface ScatterPoint {
  occ: OccupationResult
  x: number
  y: number
  gap: number
  /** Phase 6: displacement through the embodied channels at the same quarter (central run) */
  yEmb?: number
}

const props = defineProps<{
  points: ScatterPoint[]
  /** stable y max across all quarters so the axis does not jump during playback */
  yMax: number
  color: (occ: OccupationResult) => string
  quarterLabel: string
  /** occupation codes to direct-label */
  labelled: Set<string>
}>()

const host = ref<HTMLElement | null>(null)
const { width, height } = useSize(host, { width: 900, height: 520 })
const { tip, show, hide } = useTooltip()
const hovered = ref<string | null>(null)

const m = { top: 20, right: 28, bottom: 52, left: 64 }
const iw = computed(() => Math.max(100, width.value - m.left - m.right))
const ih = computed(() => Math.max(100, height.value - m.top - m.bottom))

const xMax = computed(() =>
  Math.min(1, Math.ceil((Math.max(...props.points.map((p) => p.x), 0.1) + 0.05) * 10) / 10),
)
const x = computed(() => scaleLinear().domain([0, xMax.value]).range([0, iw.value]))
const y = computed(() => scaleLinear().domain([0, props.yMax]).range([ih.value, 0]))
const r = computed(() =>
  radiusScale(
    props.points.map((p) => p.occ.emp0),
    Math.min(28, ih.value / 14),
  ),
)

const xTicks = computed(() => x.value.ticks(5))
const yTicks = computed(() => y.value.ticks(5))

const marks = computed(() =>
  props.points.map((p) => ({
    p,
    cx: x.value(p.x),
    cy: y.value(p.y),
    r: r.value(p.occ.emp0),
    fill: props.color(p.occ),
  })),
)

/** Direct labels: rank order in, greedy collision + edge check out (never clipped, never stacked). */
const CH = 7.6 // approx px per character at 14px
const labels = computed(() => {
  const placed: Array<{ x0: number; x1: number; y0: number; y1: number }> = []
  const out: Array<{ key: string; x: number; y: number; anchor: 'start' | 'end'; text: string }> =
    []
  const overlaps = (b: { x0: number; x1: number; y0: number; y1: number }) =>
    placed.some((a) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1)
  const order = [...props.labelled]
  const byCode = new Map(marks.value.map((mk) => [mk.p.occ.occ_code, mk]))
  for (const code of order) {
    const mk = byCode.get(code)
    if (!mk) continue
    const text = mk.p.occ.title
    const w = text.length * CH
    const candidates: Array<{ x: number; anchor: 'start' | 'end' }> = [
      { x: mk.cx + mk.r + 5, anchor: 'start' },
      { x: mk.cx - mk.r - 5, anchor: 'end' },
    ]
    for (const c of candidates) {
      const x0 = c.anchor === 'start' ? c.x : c.x - w
      const x1 = x0 + w
      if (x0 < 0 || x1 > iw.value) continue
      const box = { x0, x1, y0: mk.cy - 9, y1: mk.cy + 9 }
      if (overlaps(box)) continue
      placed.push(box)
      out.push({ key: mk.p.occ.occ_code, x: c.x, y: mk.cy, anchor: c.anchor, text })
      break
    }
  }
  return out
})

/** Diagonal y = x, clipped to the plot. */
const diag = computed(() => {
  const end = Math.min(xMax.value, props.yMax)
  return { x1: x.value(0), y1: y.value(0), x2: x.value(end), y2: y.value(end), end }
})

const delaunay = computed(() =>
  Delaunay.from(
    marks.value,
    (d) => d.cx,
    (d) => d.cy,
  ),
)

function onMove(e: PointerEvent) {
  const rect = host.value?.getBoundingClientRect()
  const px = e.clientX - (rect?.left ?? 0) - m.left
  const py = e.clientY - (rect?.top ?? 0) - m.top
  if (marks.value.length === 0) return
  const i = delaunay.value.find(px, py)
  const mk = marks.value[i]
  if (!mk) return
  const dist = Math.hypot(mk.cx - px, mk.cy - py)
  if (dist > Math.max(24, mk.r + 12)) {
    hovered.value = null
    hide()
    return
  }
  hovered.value = mk.p.occ.occ_code
  show(mk.cx + m.left, mk.cy + m.top, mk.p.occ.title, [
    { label: 'Employment (2023)', value: fmtCompact(mk.p.occ.emp0) },
    { label: 'Ever-automatable share', value: fmtShare(mk.p.x) },
    { label: `Displaced by ${props.quarterLabel}`, value: fmtShare(mk.p.y, 1) },
    { label: 'Gap (exposed, not hit)', value: fmtShare(mk.p.gap, 1) },
    ...(mk.p.occ.automatable_share_embodied != null
      ? [{ label: 'Ever-automatable, embodied', value: fmtShare(mk.p.occ.automatable_share_embodied) }]
      : []),
    ...(mk.p.yEmb != null
      ? [{ label: `Displaced by embodied, ${props.quarterLabel}`, value: fmtShare(mk.p.yEmb, 1) }]
      : []),
    { label: 'Group', value: MAJOR_GROUPS[mk.p.occ.major_group] ?? mk.p.occ.major_group },
  ])
}
function onLeave() {
  hovered.value = null
  hide()
}
</script>

<template>
  <div ref="host" class="scatter-host">
    <svg
      :width="width"
      :height="height"
      role="img"
      aria-label="Scatter of ever-automatable share against realized displacement per occupation"
    >
      <g :transform="`translate(${m.left},${m.top})`">
        <g class="grid">
          <line v-for="t in yTicks" :key="'y' + t" x1="0" :x2="iw" :y1="y(t)" :y2="y(t)" />
        </g>
        <g class="axis">
          <line :x1="0" :x2="iw" :y1="ih" :y2="ih" />
          <g v-for="t in xTicks" :key="'xt' + t">
            <line :x1="x(t)" :x2="x(t)" :y1="ih" :y2="ih + 5" />
            <text :x="x(t)" :y="ih + 22" text-anchor="middle">{{ fmtShare(t) }}</text>
          </g>
          <text class="axis-title" :x="iw" :y="ih + 44" text-anchor="end">
            Ever-automatable share of tasks (Σ w·a)
          </text>
        </g>
        <g class="axis">
          <g v-for="t in yTicks" :key="'yt' + t">
            <text :x="-10" :y="y(t)" text-anchor="end" dominant-baseline="middle">
              {{ fmtShare(t) }}
            </text>
          </g>
          <text class="axis-title" :x="-m.left + 4" :y="-6" text-anchor="start">
            Realized displacement (share of 2023 jobs)
          </text>
        </g>

        <line class="diag" :x1="diag.x1" :y1="diag.y1" :x2="diag.x2" :y2="diag.y2" />
        <text
          class="diag-label"
          :x="diag.x2 - 6"
          :y="diag.y2 - 8"
          text-anchor="end"
          :transform="`rotate(${-(Math.atan2(diag.y1 - diag.y2, diag.x2 - diag.x1) * 180) / Math.PI}, ${diag.x2 - 6}, ${diag.y2 - 8})`"
        >
          as exposed as hit
        </text>

        <g class="marks">
          <circle
            v-for="mk in marks"
            :key="mk.p.occ.occ_code"
            :cx="mk.cx"
            :cy="mk.cy"
            :r="mk.r"
            :fill="mk.fill"
            class="dot"
            :class="{
              hovered: hovered === mk.p.occ.occ_code,
              dim: hovered && hovered !== mk.p.occ.occ_code,
            }"
          />
        </g>
        <g class="labels" aria-hidden="true">
          <text
            v-for="l in labels"
            :key="'l' + l.key"
            :x="l.x"
            :y="l.y"
            :text-anchor="l.anchor"
            dominant-baseline="middle"
            class="direct"
          >
            {{ l.text }}
          </text>
        </g>
        <rect
          class="hit"
          x="0"
          y="0"
          :width="iw"
          :height="ih"
          fill="transparent"
          @pointermove="onMove"
          @pointerleave="onLeave"
        />
      </g>
    </svg>
    <ChartTooltip :tip="tip" :width="width" />
  </div>
</template>

<style scoped>
.scatter-host {
  min-width: 0;
  overflow: hidden;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 360px;
}
svg {
  display: block;
}
.dot {
  stroke: var(--surface);
  stroke-width: 2;
  fill-opacity: 0.82;
  transition: opacity var(--t);
  pointer-events: none;
}
.dot.hovered {
  fill-opacity: 1;
  stroke: var(--ink);
}
.dot.dim {
  opacity: 0.45;
}
.diag {
  stroke: var(--muted);
  stroke-width: 1.5;
  stroke-dasharray: 4 4;
}
.diag-label {
  fill: var(--muted);
  font-size: 14px;
}
.direct {
  fill: var(--ink);
  font-size: 14px;
  paint-order: stroke;
  stroke: var(--surface);
  stroke-width: 3px;
  stroke-linejoin: round;
}
</style>

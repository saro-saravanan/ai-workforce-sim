<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear } from 'd3'
import type { TornadoRow } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { CATEGORICAL, type Mode } from '@/lib/palette'
import { PARAM_TAG_LABELS } from '@/lib/metrics'
import ChartTooltip from '@/components/ChartTooltip.vue'

const props = defineProps<{
  rows: TornadoRow[]
  /** the central-run value the one-at-a-time runs deviate from */
  base: number
  format: (v: number) => string
  axisFormat: (v: number) => string
  mode: Mode
  unit: string
}>()

const host = ref<HTMLElement | null>(null)
const ROW_H = 30
const m = { top: 24, right: 24, bottom: 30, left: 380 }
const { width } = useSize(host, { width: 800, height: 300 })
const height = computed(() => m.top + m.bottom + props.rows.length * ROW_H)
const { tip, show, hide } = useTooltip()
const iw = computed(() => Math.max(120, width.value - m.left - m.right))

const sorted = computed(() =>
  [...props.rows].sort(
    (a, b) =>
      Math.abs(b.effect_at_high - b.effect_at_low) - Math.abs(a.effect_at_high - a.effect_at_low),
  ),
)
const x = computed(() => {
  let lo = props.base
  let hi = props.base
  for (const r of props.rows) {
    lo = Math.min(lo, r.effect_at_low, r.effect_at_high)
    hi = Math.max(hi, r.effect_at_low, r.effect_at_high)
  }
  const pad = (hi - lo || 1) * 0.06
  return scaleLinear()
    .domain([lo - pad, hi + pad])
    .nice(5)
    .range([0, iw.value])
})
const lowHue = computed(() => CATEGORICAL[props.mode][1] ?? '#eb6834')
const highHue = computed(() => CATEGORICAL[props.mode][0] ?? '#2a78d6')
const BAR = 10
const truncate = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1) + '…' : s)
const bars = computed(() =>
  sorted.value.map((r, i) => {
    const cy = m.top + i * ROW_H + ROW_H / 2
    const bx = x.value(props.base)
    const seg = (v: number) => ({ x: Math.min(bx, x.value(v)), w: Math.abs(x.value(v) - bx) })
    return { r, cy, low: seg(r.effect_at_low), high: seg(r.effect_at_high) }
  }),
)
const ticks = computed(() => x.value.ticks(5))
const hovered = ref<string | null>(null)

function onEnter(e: PointerEvent, b: (typeof bars.value)[number]) {
  hovered.value = b.r.param
  const rect = host.value?.getBoundingClientRect()
  show(e.clientX - (rect?.left ?? 0), e.clientY - (rect?.top ?? 0), `${b.r.param} · ${b.r.name}`, [
    { label: `At low (${b.r.low})`, value: props.format(b.r.effect_at_low), swatch: lowHue.value, kind: 'rect' },
    { label: `At high (${b.r.high})`, value: props.format(b.r.effect_at_high), swatch: highHue.value, kind: 'rect' },
    { label: 'Central run', value: props.format(props.base) },
    { label: 'Swing', value: props.format(Math.abs(b.r.effect_at_high - b.r.effect_at_low)).replace(/^[+−-]/, '') },
    { label: 'Provenance', value: PARAM_TAG_LABELS[b.r.tag] ?? b.r.tag },
  ])
}
function onLeave() {
  hovered.value = null
  hide()
}
</script>

<template>
  <div class="tornado">
    <div class="legend" role="list">
      <span class="item" role="listitem"
        ><span class="sw" :style="{ background: lowHue }"></span>Parameter at its low end</span
      >
      <span class="item" role="listitem"
        ><span class="sw" :style="{ background: highHue }"></span>Parameter at its high end</span
      >
      <span class="item" role="listitem"><span class="sw base"></span>Central run</span>
      <span class="item muted" role="listitem">Chip = provenance tag (S study, D data, E estimate)</span>
    </div>
    <div ref="host" class="host">
      <svg :width="width" :height="height" role="img" aria-label="One-at-a-time sensitivity, 2040 Q4">
        <g class="grid">
          <line
            v-for="t in ticks"
            :key="'g' + t"
            :x1="m.left + x(t)"
            :x2="m.left + x(t)"
            :y1="m.top - 4"
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
          <text class="axis-title" :x="m.left + iw" :y="m.top - 10" text-anchor="end">
            {{ unit }}, 2040 Q4
          </text>
        </g>
        <g v-for="b in bars" :key="b.r.param" :class="{ dim: hovered && hovered !== b.r.param }">
          <text :x="m.left - 44" :y="b.cy" text-anchor="end" dominant-baseline="middle" class="name">
            {{ truncate(b.r.name, 44) }}
          </text>
          <g :transform="`translate(${m.left - 36}, ${b.cy - 9})`">
            <rect width="18" height="18" rx="4" class="chip" :class="'tag-' + b.r.tag" />
            <text x="9" y="9.5" text-anchor="middle" dominant-baseline="middle" class="chip-text">
              {{ b.r.tag }}
            </text>
          </g>
          <rect
            :x="m.left + b.low.x"
            :y="b.cy - BAR / 2"
            :width="Math.max(0, b.low.w)"
            :height="BAR"
            :fill="lowHue"
            rx="2"
          />
          <rect
            :x="m.left + b.high.x"
            :y="b.cy - BAR / 2"
            :width="Math.max(0, b.high.w)"
            :height="BAR"
            :fill="highHue"
            rx="2"
          />
          <rect
            :x="m.left"
            :y="b.cy - ROW_H / 2"
            :width="iw"
            :height="ROW_H"
            fill="transparent"
            @pointerenter="onEnter($event, b)"
            @pointermove="onEnter($event, b)"
            @pointerleave="onLeave"
          />
        </g>
        <line
          class="base-line"
          :x1="m.left + x(base)"
          :x2="m.left + x(base)"
          :y1="m.top - 4"
          :y2="height - m.bottom"
        />
      </svg>
      <ChartTooltip :tip="tip" :width="width" />
    </div>
  </div>
</template>

<style scoped>
.tornado {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.host {
  position: relative;
  overflow: hidden;
  min-width: 0;
}
svg {
  display: block;
}
.legend {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 14px;
  color: var(--ink-2);
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
.sw.base {
  width: 2px;
  height: 14px;
  background: var(--ink);
}
.name {
  fill: var(--ink);
}
.chip {
  fill: var(--surface-2);
  stroke: var(--border);
}
.chip-text {
  font-size: 12px;
  font-weight: 700;
  fill: var(--ink-2);
}
.base-line {
  stroke: var(--ink);
  stroke-width: 1.5;
}
.dim {
  opacity: 0.45;
}
g {
  transition: opacity var(--t);
}
</style>

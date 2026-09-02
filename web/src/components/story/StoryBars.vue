<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear } from 'd3'
import type { BarsChart } from '@/types/story'
import { useSize } from '@/composables/useSize'
import { useTooltip } from '@/composables/useTooltip'
import { CATEGORICAL, DIVERGING, NEUTRAL, type Mode } from '@/lib/palette'
import ChartTooltip from '@/components/ChartTooltip.vue'

/**
 * Horizontal bars from zero, one row per item; a thin reference bar under each when the chart
 * carries `reference`; the unit as the axis label.
 */
const props = defineProps<{
  chart: BarsChart
  format: (v: number) => string
  mode: Mode
  title: string
  /** what the reference bars are (e.g. "share of all jobs") */
  referenceLabel?: string
  /** tick labels (defaults to the plain number) */
  axisFormat?: (v: number) => string
}>()
const tick = (t: number) => (props.axisFormat ? props.axisFormat(t) : String(t))

const host = ref<HTMLElement | null>(null)
const ROW_H = 32
const BAR = 14
const REF = 4
const m = { top: 6, right: 70, bottom: 26, left: 250 }
const { width } = useSize(host, { width: 600, height: 200 })
const height = computed(() => m.top + m.bottom + props.chart.items.length * ROW_H)
const iw = computed(() => Math.max(80, width.value - m.left - m.right))
const { tip, show, hide } = useTooltip()

const refByLabel = computed(() => new Map(props.chart.reference ?? []))
const x = computed(() => {
  const vals = [
    0,
    ...props.chart.items.map(([, v]) => v),
    ...(props.chart.reference ?? []).map(([, v]) => v),
  ]
  const lo = Math.min(...vals)
  const hi = Math.max(...vals)
  return scaleLinear()
    .domain([lo, hi === lo ? lo + 1 : hi])
    .nice(4)
    .range([0, iw.value])
})
const pos = computed(() => CATEGORICAL[props.mode][0] ?? '#2a78d6')
const neg = computed(() => DIVERGING[props.mode].neg)
const refColor = computed(() => NEUTRAL[props.mode])
const bars = computed(() =>
  props.chart.items.map(([label, value], i) => {
    const x0 = x.value(0)
    const xv = x.value(value)
    const ref = refByLabel.value.get(label)
    const cy = m.top + i * ROW_H + ROW_H / 2
    return {
      key: `${i}-${label}`,
      label,
      value,
      ref,
      cy,
      x: Math.min(x0, xv),
      w: Math.abs(xv - x0),
      fill: value < 0 ? neg.value : pos.value,
      refX: ref != null ? Math.min(x0, x.value(ref)) : 0,
      refW: ref != null ? Math.abs(x.value(ref) - x0) : 0,
      labelX: Math.max(x0, xv) + 6,
    }
  }),
)
const ticks = computed(() => x.value.ticks(4))
const hovered = ref<string | null>(null)

function onEnter(e: PointerEvent, b: (typeof bars.value)[number]) {
  hovered.value = b.key
  const rect = host.value?.getBoundingClientRect()
  const rows = [
    { label: props.title, value: props.format(b.value), swatch: b.fill, kind: 'rect' as const },
  ]
  if (b.ref != null)
    rows.push({
      label: props.referenceLabel ?? 'reference',
      value: props.format(b.ref),
      swatch: refColor.value,
      kind: 'rect',
    })
  show(e.clientX - (rect?.left ?? 0), e.clientY - (rect?.top ?? 0), b.label, rows)
}
function onLeave() {
  hovered.value = null
  hide()
}
</script>

<template>
  <div class="story-bars">
    <div v-if="chart.reference && referenceLabel" class="legend" role="list">
      <span class="item" role="listitem"
        ><span class="sw" :style="{ background: pos }"></span>{{ title }}</span
      >
      <span class="item" role="listitem"
        ><span class="sw thin" :style="{ background: refColor }"></span>{{ referenceLabel }}</span
      >
    </div>
    <div ref="host" class="host">
      <svg :width="width" :height="height" role="img" :aria-label="title">
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
            :y="height - m.bottom + 16"
            text-anchor="middle"
          >
            {{ tick(t) }}
          </text>
          <text
            v-if="chart.unit"
            class="axis-title"
            :x="m.left + iw"
            :y="height - 2"
            text-anchor="end"
          >
            {{ chart.unit }}
          </text>
        </g>
        <g
          v-for="b in bars"
          :key="b.key"
          class="row"
          :class="{ dim: hovered && hovered !== b.key }"
          @pointerenter="onEnter($event, b)"
          @pointermove="onEnter($event, b)"
          @pointerleave="onLeave"
        >
          <rect :x="0" :y="b.cy - ROW_H / 2" :width="width" :height="ROW_H" fill="transparent" />
          <text
            :x="m.left - 10"
            :y="b.cy - (b.ref != null ? 3 : 0)"
            text-anchor="end"
            dominant-baseline="middle"
            class="name"
          >
            {{ b.label.length > 34 ? b.label.slice(0, 33) + '…' : b.label }}
          </text>
          <rect
            :x="m.left + b.x"
            :y="b.cy - BAR / 2 - (b.ref != null ? 3 : 0)"
            :width="Math.max(0, b.w)"
            :height="BAR"
            :fill="b.fill"
            rx="3"
          />
          <rect
            v-if="b.ref != null"
            :x="m.left + b.refX"
            :y="b.cy + BAR / 2 - 1"
            :width="Math.max(0, b.refW)"
            :height="REF"
            :fill="refColor"
            rx="1"
          />
          <text
            :x="m.left + b.labelX"
            :y="b.cy - (b.ref != null ? 3 : 0)"
            dominant-baseline="middle"
            class="val mono"
          >
            {{ format(b.value) }}
          </text>
        </g>
        <line
          class="zero"
          :x1="m.left + x(0)"
          :x2="m.left + x(0)"
          :y1="m.top"
          :y2="height - m.bottom"
        />
      </svg>
      <ChartTooltip :tip="tip" :width="width" />
    </div>
  </div>
</template>

<style scoped>
.story-bars {
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
.sw.thin {
  height: 4px;
}
.name {
  fill: var(--ink);
}
.val {
  fill: var(--ink-2);
  font-size: 13px;
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

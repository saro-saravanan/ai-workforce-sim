<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear, scalePoint } from 'd3'
import type { BacktestRow } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip, type TooltipRow } from '@/composables/useTooltip'
import { quarterLabel } from '@/lib/format'
import { CATEGORICAL, NEUTRAL, type Mode } from '@/lib/palette'
import ChartTooltip from '@/components/ChartTooltip.vue'

/**
 * One backtest series: the observed points per quarter and, for series the model tracks, the
 * model's central value at the same quarters as a second mark (hollow diamond, dashed line).
 * Context series (`model_metric === 'none'`) draw the observed points only.
 */
const props = defineProps<{
  rows: BacktestRow[]
  mode: Mode
  format: (v: number) => string
  /** tick labels (defaults to `format`) */
  axisFormat?: (v: number) => string
  /** the series' unit, shown at the end of the legend */
  unit?: string
}>()
const tick = (t: number) => (props.axisFormat ? props.axisFormat(t) : props.format(t))

const host = ref<HTMLElement | null>(null)
const HEIGHT = 170
const m = { top: 10, right: 16, bottom: 30, left: 56 }
const { width } = useSize(host, { width: 420, height: HEIGHT })
const iw = computed(() => Math.max(60, width.value - m.left - m.right))
const ih = HEIGHT - m.top - m.bottom
const { tip, show, hide } = useTooltip()

const observedColor = computed(() => CATEGORICAL[props.mode][0] ?? '#2a78d6')
const modelColor = computed(() => CATEGORICAL[props.mode][1] ?? '#eb6834')
const gridColor = computed(() => NEUTRAL[props.mode])

const sorted = computed(() => [...props.rows].sort((a, b) => a.quarter.localeCompare(b.quarter)))
const quarters = computed(() => [...new Set(sorted.value.map((r) => r.quarter))])
const hasModel = computed(() => sorted.value.some((r) => r.model_central != null))

const x = computed(() =>
  scalePoint<string>().domain(quarters.value).range([0, iw.value]).padding(0.5),
)
const y = computed(() => {
  const vals = [0, ...sorted.value.map((r) => r.value)]
  for (const r of sorted.value) if (r.model_central != null) vals.push(r.model_central)
  const lo = Math.min(...vals)
  const hi = Math.max(...vals)
  return scaleLinear()
    .domain([lo, hi === lo ? lo + 1 : hi])
    .nice(4)
    .range([ih, 0])
})
const yTicks = computed(() => y.value.ticks(4))
const line = (pts: Array<[number, number]>) =>
  pts.map(([px, py], i) => `${i ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join(' ')
const observedPath = computed(() =>
  line(sorted.value.map((r) => [x.value(r.quarter) ?? 0, y.value(r.value)])),
)
const modelPath = computed(() =>
  line(
    sorted.value
      .filter((r) => r.model_central != null)
      .map((r) => [x.value(r.quarter) ?? 0, y.value(r.model_central as number)]),
  ),
)
const points = computed(() =>
  sorted.value.map((r) => ({
    row: r,
    cx: x.value(r.quarter) ?? 0,
    cyObs: y.value(r.value),
    cyModel: r.model_central != null ? y.value(r.model_central) : null,
  })),
)
/** one x label per quarter when they fit, else every other */
const xLabels = computed(() => {
  const every = quarters.value.length * 60 > iw.value ? 2 : 1
  return quarters.value.filter((_, i) => i % every === 0)
})

function onEnter(e: PointerEvent, p: (typeof points.value)[number]) {
  const rect = host.value?.getBoundingClientRect()
  const rows: TooltipRow[] = [
    {
      label: 'observed',
      value: props.format(p.row.value),
      swatch: observedColor.value,
      kind: 'rect',
    },
  ]
  if (p.row.model_central != null)
    rows.push({
      label: 'model',
      value: props.format(p.row.model_central),
      swatch: modelColor.value,
      kind: 'line',
    })
  if (p.row.error_pct != null)
    rows.push({
      label: 'error',
      value: `${p.row.error_pct > 0 ? '+' : ''}${p.row.error_pct.toFixed(0)}%`,
    })
  show(
    e.clientX - (rect?.left ?? 0),
    e.clientY - (rect?.top ?? 0),
    quarterLabel(p.row.quarter),
    rows,
  )
}
</script>

<template>
  <div class="backtest-chart">
    <div class="legend" role="list">
      <span class="item" role="listitem"
        ><span class="sw dot" :style="{ background: observedColor }"></span>observed</span
      >
      <span v-if="hasModel" class="item" role="listitem"
        ><span class="sw diamond" :style="{ borderColor: modelColor }"></span>model, central
        run</span
      >
      <span v-else class="item muted" role="listitem">observed only</span>
      <span v-if="unit" class="item muted unit" role="listitem">{{ unit }}</span>
    </div>
    <div ref="host" class="host">
      <svg
        :width="width"
        :height="HEIGHT"
        role="img"
        aria-label="Observed values and the model's values by quarter"
      >
        <g :transform="`translate(${m.left},${m.top})`">
          <g class="grid">
            <line
              v-for="t in yTicks"
              :key="'g' + t"
              x1="0"
              :x2="iw"
              :y1="y(t)"
              :y2="y(t)"
              :stroke="gridColor"
              stroke-opacity="0.35"
            />
          </g>
          <g class="axis">
            <text
              v-for="t in yTicks"
              :key="'y' + t"
              :x="-8"
              :y="y(t)"
              text-anchor="end"
              dominant-baseline="middle"
            >
              {{ tick(t) }}
            </text>
            <text
              v-for="qq in xLabels"
              :key="'x' + qq"
              :x="x(qq)"
              :y="ih + 18"
              text-anchor="middle"
            >
              {{ quarterLabel(qq) }}
            </text>
          </g>
          <path
            :d="observedPath"
            fill="none"
            :stroke="observedColor"
            stroke-width="1.5"
            stroke-opacity="0.6"
          />
          <path
            v-if="hasModel"
            :d="modelPath"
            fill="none"
            :stroke="modelColor"
            stroke-width="1.5"
            stroke-dasharray="4 3"
          />
          <g
            v-for="p in points"
            :key="p.row.quarter"
            class="pt"
            @pointerenter="onEnter($event, p)"
            @pointermove="onEnter($event, p)"
            @pointerleave="hide()"
          >
            <rect :x="p.cx - 14" y="0" width="28" :height="ih" fill="transparent" />
            <circle class="observed" :cx="p.cx" :cy="p.cyObs" r="4.5" :fill="observedColor" />
            <rect
              v-if="p.cyModel != null"
              class="model"
              :x="p.cx - 4.5"
              :y="p.cyModel - 4.5"
              width="9"
              height="9"
              :transform="`rotate(45 ${p.cx} ${p.cyModel})`"
              fill="var(--surface)"
              :stroke="modelColor"
              stroke-width="2"
            />
          </g>
        </g>
      </svg>
      <ChartTooltip :tip="tip" :width="width" />
    </div>
  </div>
</template>

<style scoped>
.backtest-chart {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
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
  font-size: 13px;
  color: var(--ink-2);
  flex-wrap: wrap;
}
.item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.sw {
  width: 10px;
  height: 10px;
  display: inline-block;
}
.sw.dot {
  border-radius: 50%;
}
.sw.diamond {
  width: 8px;
  height: 8px;
  border: 2px solid;
  transform: rotate(45deg);
}
.axis text {
  fill: var(--muted);
  font-size: 12px;
}
.unit {
  margin-left: auto;
}
.observed {
  stroke: var(--surface);
  stroke-width: 1.5;
}
</style>

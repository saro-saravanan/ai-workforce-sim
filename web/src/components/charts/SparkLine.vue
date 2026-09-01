<script setup lang="ts">
import { computed, ref } from 'vue'
import { scaleLinear, line as d3line, area as d3area, extent } from 'd3'
import type { Series } from '@/types/results'
import { useSize } from '@/composables/useSize'

const props = defineProps<{
  series: Series
  q: number
  /** stroke/fill hue (a categorical slot) */
  hue: string
  /** draw a dotted line at zero (the no-AI baseline) */
  zero?: boolean
}>()

const host = ref<HTMLElement | null>(null)
const { width, height } = useSize(host, { width: 240, height: 64 })
const pad = { top: 6, bottom: 6, left: 4, right: 8 }

const n = computed(() => props.series.p50.length)
const x = computed(() =>
  scaleLinear()
    .domain([0, Math.max(1, n.value - 1)])
    .range([pad.left, width.value - pad.right]),
)
const y = computed(() => {
  const all = [...props.series.p50, ...(props.series.p10 ?? []), ...(props.series.p90 ?? [])]
  if (props.zero) all.push(0)
  const [lo, hi] = extent(all) as [number, number]
  return scaleLinear()
    .domain([lo === hi ? lo - 1 : lo, lo === hi ? hi + 1 : hi])
    .range([height.value - pad.bottom, pad.top])
})
const hasBand = computed(() => !!(props.series.p10 && props.series.p90))
const median = computed(
  () =>
    d3line<number>()
      .x((_, i) => x.value(i))
      .y((d) => y.value(d))(props.series.p50) ?? '',
)
const band = computed(() => {
  if (!hasBand.value) return ''
  const p10 = props.series.p10 ?? []
  const p90 = props.series.p90 ?? []
  return (
    d3area<number>()
      .x((_, i) => x.value(i))
      .y0((_, i) => y.value(p10[i] ?? 0))
      .y1((_, i) => y.value(p90[i] ?? 0))(props.series.p50) ?? ''
  )
})
const marker = computed(() => ({
  x: x.value(props.q),
  y: y.value(props.series.p50[props.q] ?? 0),
}))
</script>

<template>
  <div ref="host" class="spark-host">
    <svg :width="width" :height="height" aria-hidden="true">
      <path v-if="hasBand" :d="band" :fill="hue" fill-opacity="0.14" />
      <line v-if="zero" class="zero" :x1="pad.left" :x2="width - pad.right" :y1="y(0)" :y2="y(0)" />
      <path
        :d="median"
        fill="none"
        :stroke="hue"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
      <line class="scrub" :x1="marker.x" :x2="marker.x" :y1="pad.top" :y2="height - pad.bottom" />
      <circle :cx="marker.x" :cy="marker.y" r="4.5" :fill="hue" class="marker" />
    </svg>
  </div>
</template>

<style scoped>
.spark-host {
  min-width: 0;
  overflow: hidden;
  width: 100%;
  height: 64px;
}
svg {
  display: block;
}
.zero {
  stroke: var(--muted);
  stroke-width: 1;
  stroke-dasharray: 2 3;
}
.scrub {
  stroke: var(--ink-2);
  stroke-width: 1;
}
.marker {
  stroke: var(--surface);
  stroke-width: 2;
}
</style>

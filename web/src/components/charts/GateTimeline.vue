<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSize } from '@/composables/useSize'
import { quarterLabel } from '@/lib/format'
import { yearTicks, type GateMarker } from '@/lib/applications'

/**
 * A one-line gate timeline, 2024–2040: three markers (1% displaced, 10% displaced, 50% coverage)
 * from an application's `first_quarter`; gates not passed by the horizon sit past the right end
 * as hollow markers. With `years` it draws the shared year axis instead (the header row).
 */
const props = defineProps<{
  markers?: GateMarker[]
  /** 0..1 position of the scrubber's quarter */
  current?: number | null
  years?: boolean
  height?: number
}>()

const host = ref<HTMLElement | null>(null)
const { width } = useSize(host, { width: 240, height: 28 })
const pad = { left: 8, right: 26 }
const h = computed(() => props.height ?? 28)
const iw = computed(() => Math.max(40, width.value - pad.left - pad.right))
const px = (x: number) => pad.left + x * iw.value
const ticks = yearTicks()
const mid = computed(() => h.value / 2)
/** missing gates stack past the axis end so three of them stay legible */
const missingOffset = (m: GateMarker, i: number) => (m.missing ? 8 + i * 6 : 0)
function title(m: GateMarker) {
  return `${m.label}: ${m.missing ? 'not by 2040' : quarterLabel(m.quarter ?? '')}`
}
</script>

<template>
  <div ref="host" class="gate-host" :style="{ height: h + 'px' }">
    <svg :width="width" :height="h" :viewBox="`0 0 ${width} ${h}`" preserveAspectRatio="xMinYMin meet" class="rsvg" aria-hidden="true">
      <template v-if="years">
        <text
          v-for="(t, i) in ticks"
          :key="t.year"
          :x="px(t.x)"
          :y="mid + 5"
          :text-anchor="i === 0 ? 'start' : 'middle'"
          class="year"
        >
          {{ t.year }}
        </text>
      </template>
      <template v-else>
        <line class="axis-line" :x1="px(0)" :x2="px(1)" :y1="mid" :y2="mid" />
        <line
          v-for="t in ticks"
          :key="t.year"
          class="tick"
          :x1="px(t.x)"
          :x2="px(t.x)"
          :y1="mid - 3"
          :y2="mid + 3"
        />
        <line v-if="current != null" class="now" :x1="px(current)" :x2="px(current)" :y1="2" :y2="h - 2" />
        <g
          v-for="(m, i) in markers ?? []"
          :key="m.gate"
          :class="['marker', m.gate, { missing: m.missing }]"
          :transform="`translate(${px(m.x) + missingOffset(m, i)},${mid})`"
        >
          <title>{{ title(m) }}</title>
          <circle v-if="m.gate === 'displacement_1pct'" r="3.5" />
          <circle v-else-if="m.gate === 'displacement_10pct'" r="5.5" />
          <rect v-else x="-4.5" y="-4.5" width="9" height="9" transform="rotate(45)" />
        </g>
      </template>
    </svg>
  </div>
</template>

<style scoped>
.gate-host {
  min-width: 0;
  overflow: hidden;
  width: 100%;
}
svg {
  display: block;
}
.axis-line {
  stroke: var(--axis);
  stroke-width: 1;
}
.tick {
  stroke: var(--axis);
}
.now {
  stroke: var(--ink-2);
  stroke-width: 1.5;
}
.year {
  font-size: 12px;
  fill: var(--muted);
}
.marker circle,
.marker rect {
  stroke: var(--surface);
  stroke-width: 1.5;
  fill: var(--ink);
}
.marker.displacement_10pct circle {
  fill: var(--accent);
}
.marker.coverage_50pct rect {
  fill: var(--surface);
  stroke: var(--ink);
  stroke-width: 1.5;
}
.marker.missing circle,
.marker.missing rect {
  fill: var(--surface);
  stroke: var(--muted);
  stroke-dasharray: 2 1.5;
}
.rsvg {
  max-width: 100%;
  height: auto;
  display: block;
}
</style>

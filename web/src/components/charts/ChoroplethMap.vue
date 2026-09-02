<script setup lang="ts">
import { computed, ref } from 'vue'
import { geoAlbersUsa, geoPath } from 'd3'
import type { StateFeature, StatesGeoJSON } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip, type TooltipRow } from '@/composables/useTooltip'
import ChartTooltip from '@/components/ChartTooltip.vue'

export interface StateValue {
  value: number | undefined
  lo?: number
  hi?: number
}

const props = defineProps<{
  geo: StatesGeoJSON
  /** value lookup per fips at the current quarter */
  values: Map<string, StateValue>
  color: (v: number) => string
  format: (v: number) => string
  metricLabel: string
  selected: string | null
  /** secondary rows shown in the tooltip (e.g. other metrics) */
  extra?: (fips: string) => TooltipRow[]
}>()

const emit = defineEmits<{ select: [fips: string | null] }>()

const host = ref<HTMLElement | null>(null)
const { width, height } = useSize(host, { width: 900, height: 560 })
const { tip, show, move, hide } = useTooltip()
const hovered = ref<string | null>(null)

const projection = computed(() =>
  geoAlbersUsa().fitExtent(
    [
      [8, 8],
      [width.value - 8, height.value - 8],
    ],
    props.geo as unknown as GeoJSON.FeatureCollection,
  ),
)
const path = computed(() => geoPath(projection.value))

const shapes = computed(() =>
  props.geo.features.map((f: StateFeature) => {
    const fips = f.properties.fips
    const v = props.values.get(fips)
    const d = path.value(f as unknown as GeoJSON.Feature) ?? ''
    const c = path.value.centroid(f as unknown as GeoJSON.Feature)
    return {
      fips,
      name: f.properties.name,
      abbrev: f.properties.abbrev,
      d,
      cx: c[0],
      cy: c[1],
      fill: v?.value == null ? 'var(--surface-2)' : props.color(v.value),
      area: path.value.area(f as unknown as GeoJSON.Feature),
    }
  }),
)

/** Label the largest states directly (abbreviation inside the fill). */
const labelled = computed(() =>
  shapes.value.filter((s) => s.area > 1800 && Number.isFinite(s.cx) && Number.isFinite(s.cy)),
)

function rows(fips: string): TooltipRow[] {
  const v = props.values.get(fips)
  const out: TooltipRow[] = [
    {
      label: props.metricLabel,
      value:
        v?.value == null
          ? '—'
          : v.lo != null && v.hi != null
            ? `${props.format(v.value)} [${props.format(v.lo)}, ${props.format(v.hi)}]`
            : props.format(v.value),
    },
  ]
  return props.extra ? out.concat(props.extra(fips)) : out
}

function pos(e: PointerEvent) {
  const r = host.value?.getBoundingClientRect()
  return [e.clientX - (r?.left ?? 0), e.clientY - (r?.top ?? 0)] as const
}
function onEnter(e: PointerEvent, s: { fips: string; name: string }) {
  hovered.value = s.fips
  const [x, y] = pos(e)
  show(x, y, s.name, rows(s.fips))
}
function onMove(e: PointerEvent) {
  const [x, y] = pos(e)
  move(x, y)
}
function onLeave() {
  hovered.value = null
  hide()
}
function onClick(fips: string) {
  emit('select', props.selected === fips ? null : fips)
}
function onKey(e: KeyboardEvent, s: { fips: string; name: string }) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    onClick(s.fips)
  }
}
function onFocus(s: { fips: string; name: string; cx: number; cy: number }) {
  hovered.value = s.fips
  show(s.cx, s.cy, s.name, rows(s.fips))
}
</script>

<template>
  <div ref="host" class="map-host">
    <svg
      :width="width"
      :height="height"
      role="img"
      :aria-label="`Map of U.S. states, ${metricLabel}`"
    >
      <g class="states">
        <path
          v-for="s in shapes"
          :key="s.fips"
          :d="s.d"
          :fill="s.fill"
          class="state"
          :class="{ selected: s.fips === selected, hovered: s.fips === hovered }"
          tabindex="0"
          role="button"
          :aria-label="`${s.name}: ${rows(s.fips)[0]?.value ?? ''}`"
          :aria-pressed="s.fips === selected"
          @pointerenter="onEnter($event, s)"
          @pointermove="onMove"
          @pointerleave="onLeave"
          @focus="onFocus(s)"
          @blur="onLeave"
          @click="onClick(s.fips)"
          @keydown="onKey($event, s)"
        />
      </g>
      <g class="labels" aria-hidden="true">
        <text
          v-for="s in labelled"
          :key="s.fips"
          :x="s.cx"
          :y="s.cy"
          text-anchor="middle"
          dominant-baseline="middle"
          :fill="'var(--ink)'"
          class="abbrev"
        >
          {{ s.abbrev }}
        </text>
      </g>
    </svg>
    <ChartTooltip :tip="tip" :width="width" />
  </div>
</template>

<style scoped>
.map-host {
  min-width: 0;
  overflow: hidden;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 240px;
}
svg {
  display: block;
}
.state {
  stroke: var(--surface);
  stroke-width: 1;
  cursor: pointer;
  transition: opacity var(--t);
  outline: none;
}
.state.hovered {
  stroke: var(--ink);
  stroke-width: 1.5;
}
.state.selected {
  stroke: var(--ink);
  stroke-width: 2.5;
}
.state:focus-visible {
  stroke: var(--focus);
  stroke-width: 3;
}
.abbrev {
  font-size: 14px;
  font-weight: 600;
  pointer-events: none;
  paint-order: stroke;
  stroke: var(--surface);
  stroke-width: 3px;
  stroke-linejoin: round;
}
</style>

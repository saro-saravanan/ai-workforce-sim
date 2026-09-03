<script setup lang="ts">
import { computed, ref } from 'vue'
import { geoArea, geoMercator, geoNaturalEarth1, geoPath, type GeoProjection } from 'd3'
import type { WorldFeature, WorldGeoJSON } from '@/types/results'
import { useSize } from '@/composables/useSize'
import { useTooltip, type TooltipRow } from '@/composables/useTooltip'
import ChartTooltip from '@/components/ChartTooltip.vue'

export interface CountryValue {
  value: number | undefined
  lo?: number
  hi?: number
}

const props = defineProps<{
  geo: WorldGeoJSON
  /** 'world' draws the globe (Natural Earth I); a region id zooms to its countries (Mercator fit) */
  focus: string
  /** value per iso3 at the current quarter */
  values: Map<string, CountryValue>
  color: (v: number) => string
  format: (v: number) => string
  metricLabel: string
  regionName: (id: string) => string
  /** regions whose data_flags mark a fixture: hatched */
  fixtureRegions: Set<string>
  /** selected member (iso3) in a region drill */
  selected: string | null
  extra?: (iso3: string, region: string) => TooltipRow[]
}>()

const emit = defineEmits<{ selectRegion: [id: string]; selectMember: [iso3: string | null] }>()

const host = ref<HTMLElement | null>(null)
const { width, height } = useSize(host, { width: 900, height: 520 })
const { tip, show, move, hide } = useTooltip()
const hovered = ref<string | null>(null)
const hoveredRegion = ref<string | null>(null)
const uid = `wm-${Math.random().toString(36).slice(2, 8)}`

const isWorld = computed(() => props.focus === 'world')
const focusFeatures = computed(() =>
  isWorld.value
    ? props.geo.features
    : props.geo.features.filter((f) => f.properties.region_id === props.focus),
)
/** The largest polygon of a feature by spherical area (France without French Guiana, the U.S. mainland). */
function mainPolygon(f: WorldFeature): GeoJSON.Geometry {
  const g = f.geometry
  if (g.type !== 'MultiPolygon') return g
  let best: GeoJSON.Polygon | null = null
  let bestArea = -1
  for (const coords of g.coordinates) {
    const poly: GeoJSON.Polygon = { type: 'Polygon', coordinates: coords }
    const a = geoArea(poly)
    if (a > bestArea) {
      bestArea = a
      best = poly
    }
  }
  return best ?? g
}
const projection = computed<GeoProjection>(() => {
  if (isWorld.value)
    return geoNaturalEarth1().fitExtent(
      [
        [8, 8],
        [width.value - 8, height.value - 8],
      ],
      { type: 'FeatureCollection', features: props.geo.features } as unknown as GeoJSON.FeatureCollection,
    )
  // zoom on the region's main landmasses so overseas territories do not shrink the fit
  const fc = {
    type: 'FeatureCollection',
    features: focusFeatures.value.map((f) => ({ type: 'Feature', properties: {}, geometry: mainPolygon(f) })),
  } as unknown as GeoJSON.FeatureCollection
  const pad = Math.min(60, width.value * 0.08)
  return geoMercator().fitExtent(
    [
      [pad, pad],
      [width.value - pad, height.value - pad],
    ],
    fc,
  )
})
const path = computed(() => geoPath(projection.value))
const sphere = computed(() => (isWorld.value ? (path.value({ type: 'Sphere' }) ?? '') : ''))

interface Shape {
  iso3: string
  name: string
  region: string
  d: string
  fill: string
  modelled: boolean
  inFocus: boolean
  fixture: boolean
  area: number
  cx: number
  cy: number
}

/** Centroid of the largest polygon (keeps the U.S. label on the mainland, not between Alaska and Hawaii). */
function mainCentroid(f: WorldFeature): [number, number] {
  return path.value.centroid(mainPolygon(f))
}

/** Greedy label placement: largest first, drop any label that would overlap one already placed. */
function dropColliding<T extends { x: number; y: number; text: string; area: number }>(items: T[]): T[] {
  const placed: T[] = []
  for (const it of [...items].sort((a, b) => b.area - a.area)) {
    const w = it.text.length * 8 + 8
    const hit = placed.some(
      (p) => Math.abs(p.y - it.y) < 16 && Math.abs(p.x - it.x) < (w + p.text.length * 8 + 8) / 2,
    )
    if (!hit) placed.push(it)
  }
  return placed
}

const shapes = computed<Shape[]>(() =>
  props.geo.features.map((f) => {
    const { iso3, name, region_id } = f.properties
    const region = region_id ?? ''
    const modelled = region !== ''
    const inFocus = isWorld.value || region === props.focus
    const v = props.values.get(iso3)
    const [cx, cy] = mainCentroid(f)
    return {
      iso3,
      name,
      region,
      d: path.value(f as unknown as GeoJSON.Feature) ?? '',
      fill:
        modelled && inFocus && v?.value != null && Number.isFinite(v.value)
          ? props.color(v.value)
          : 'var(--surface-2)',
      modelled,
      inFocus,
      fixture: modelled && props.fixtureRegions.has(region),
      area: path.value.area(f as unknown as GeoJSON.Feature),
      cx,
      cy,
    }
  }),
)

/** One label per region, on its largest country, when that country is big enough to carry it. */
const regionLabels = computed(() => {
  const best = new Map<string, Shape>()
  for (const s of shapes.value) {
    if (!s.modelled || !s.inFocus) continue
    const b = best.get(s.region)
    if (!b || s.area > b.area) best.set(s.region, s)
  }
  const minArea = isWorld.value ? 350 : 900
  return dropColliding(
    [...best.entries()]
      .filter(([, s]) => s.area > minArea && Number.isFinite(s.cx) && Number.isFinite(s.cy))
      .map(([region, s]) => ({ region, x: s.cx, y: s.cy, text: isWorld.value ? region : s.name, area: s.area })),
  )
})
/** In a region drill, label each member country that is large enough (largest first, no overlaps). */
const memberLabels = computed(() =>
  isWorld.value
    ? []
    : dropColliding(
        shapes.value
          .filter((s) => s.inFocus && s.area > 700 && Number.isFinite(s.cx))
          .map((s) => ({ iso3: s.iso3, x: s.cx, y: s.cy, text: s.name, area: s.area })),
      ),
)

function rows(s: Shape): TooltipRow[] {
  if (!s.modelled) return [{ label: 'Region', value: 'not modelled' }]
  const v = props.values.get(s.iso3)
  const out: TooltipRow[] = [
    { label: 'Region', value: props.regionName(s.region) },
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
  if (s.fixture) out.push({ label: 'Data', value: 'fixture (hatched)' })
  return props.extra ? out.concat(props.extra(s.iso3, s.region)) : out
}

function pos(e: PointerEvent) {
  const r = host.value?.getBoundingClientRect()
  return [e.clientX - (r?.left ?? 0), e.clientY - (r?.top ?? 0)] as const
}
function onEnter(e: PointerEvent, s: Shape) {
  hovered.value = s.iso3
  hoveredRegion.value = s.modelled ? s.region : null
  const [x, y] = pos(e)
  show(x, y, s.name, rows(s))
}
function onMove(e: PointerEvent) {
  const [x, y] = pos(e)
  move(x, y)
}
function onLeave() {
  hovered.value = null
  hoveredRegion.value = null
  hide()
}
function onFocus(s: Shape) {
  hovered.value = s.iso3
  hoveredRegion.value = s.modelled ? s.region : null
  show(s.cx, s.cy, s.name, rows(s))
}
function onClick(s: Shape) {
  if (!s.modelled) return
  if (isWorld.value) emit('selectRegion', s.region)
  else if (s.inFocus) emit('selectMember', props.selected === s.iso3 ? null : s.iso3)
  else emit('selectRegion', s.region)
}
function onKey(e: KeyboardEvent, s: Shape) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    onClick(s)
  }
}
function isHighlighted(s: Shape) {
  return isWorld.value
    ? s.modelled && s.region === hoveredRegion.value
    : s.iso3 === hovered.value
}
const ariaLabel = computed(() =>
  isWorld.value
    ? `World map of countries by their region's ${props.metricLabel}`
    : `Map of ${props.regionName(props.focus)}, ${props.metricLabel}`,
)
</script>

<template>
  <div ref="host" class="map-host">
    <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="xMinYMin meet" class="rsvg" role="img" :aria-label="ariaLabel">
      <defs>
        <pattern
          :id="uid"
          patternUnits="userSpaceOnUse"
          width="7"
          height="7"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="7" stroke="var(--surface)" stroke-width="2.2" />
        </pattern>
      </defs>
      <path v-if="sphere" :d="sphere" class="sphere" />
      <g class="countries">
        <path
          v-for="s in shapes"
          :key="s.iso3"
          :d="s.d"
          :fill="s.fill"
          class="country"
          :class="{
            modelled: s.modelled && s.inFocus,
            dim: !s.inFocus,
            highlighted: isHighlighted(s),
            selected: s.iso3 === selected,
          }"
          :tabindex="s.modelled && s.inFocus ? 0 : -1"
          :role="s.modelled ? 'button' : undefined"
          :aria-label="s.modelled ? `${s.name}: ${rows(s)[1]?.value ?? ''}` : undefined"
          :aria-pressed="s.modelled ? s.iso3 === selected : undefined"
          @pointerenter="onEnter($event, s)"
          @pointermove="onMove"
          @pointerleave="onLeave"
          @focus="onFocus(s)"
          @blur="onLeave"
          @click="onClick(s)"
          @keydown="onKey($event, s)"
        />
      </g>
      <g class="hatch" aria-hidden="true">
        <path
          v-for="s in shapes.filter((x) => x.fixture && x.inFocus)"
          :key="'h' + s.iso3"
          :d="s.d"
          :fill="`url(#${uid})`"
        />
      </g>
      <g class="labels" aria-hidden="true">
        <text
          v-for="l in memberLabels"
          :key="'m' + l.iso3"
          :x="l.x"
          :y="l.y"
          text-anchor="middle"
          dominant-baseline="middle"
          class="member"
        >
          {{ l.text }}
        </text>
        <text
          v-for="l in regionLabels"
          v-show="isWorld"
          :key="l.region"
          :x="l.x"
          :y="l.y"
          text-anchor="middle"
          dominant-baseline="middle"
          class="region-label"
        >
          {{ l.text }}
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
.sphere {
  fill: none;
  stroke: var(--grid);
  stroke-width: 1;
}
.country {
  stroke: var(--surface);
  stroke-width: 0.8;
  outline: none;
  transition: opacity var(--t);
}
.country.modelled {
  cursor: pointer;
}
.country.dim {
  opacity: 0.55;
}
.country.highlighted {
  stroke: var(--ink);
  stroke-width: 1.4;
}
.country.selected {
  stroke: var(--ink);
  stroke-width: 2.5;
}
.country:focus-visible {
  stroke: var(--focus);
  stroke-width: 3;
}
.hatch path {
  pointer-events: none;
}
.region-label,
.member {
  font-size: 14px;
  font-weight: 600;
  fill: var(--ink);
  pointer-events: none;
  paint-order: stroke;
  stroke: var(--surface);
  stroke-width: 3px;
  stroke-linejoin: round;
}
.member {
  font-weight: 500;
}
.rsvg {
  max-width: 100%;
  height: auto;
  display: block;
}
</style>

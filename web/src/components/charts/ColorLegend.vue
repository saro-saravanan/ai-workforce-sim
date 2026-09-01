<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  /** color function over the domain */
  color: (v: number) => string
  domain: [number, number]
  format: (v: number) => string
  title: string
  /** show a "0" tick at the midpoint for diverging scales */
  diverging?: boolean
}>()

const id = `lg-${Math.random().toString(36).slice(2, 8)}`
const stops = computed(() => {
  const [lo, hi] = props.domain
  return Array.from({ length: 21 }, (_, i) => {
    const t = i / 20
    return { offset: `${t * 100}%`, color: props.color(lo + t * (hi - lo)) }
  })
})
const W = 300
const ticks = computed(() => {
  const [lo, hi] = props.domain
  const vals = props.diverging ? [lo, lo / 2, 0, hi / 2, hi] : [lo, (lo + hi) / 2, hi]
  return vals.map((v, i) => ({
    v,
    x: ((v - lo) / (hi - lo)) * W,
    labelled: !props.diverging || i % 2 === 0,
  }))
})
</script>

<template>
  <figure class="legend">
    <figcaption>{{ title }}</figcaption>
    <svg :width="W" height="40" aria-hidden="true">
      <defs>
        <linearGradient :id="id" x1="0" x2="1" y1="0" y2="0">
          <stop v-for="s in stops" :key="s.offset" :offset="s.offset" :stop-color="s.color" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" :width="W" height="12" rx="2" :fill="`url(#${id})`" />
      <g v-for="t in ticks" :key="t.v">
        <line :x1="t.x" :x2="t.x" y1="12" y2="16" stroke="var(--axis)" />
        <text
          v-if="t.labelled"
          :x="t.x"
          y="32"
          :text-anchor="t.x === 0 ? 'start' : t.x === W ? 'end' : 'middle'"
        >
          {{ format(t.v) }}
        </text>
      </g>
    </svg>
  </figure>
</template>

<style scoped>
.legend {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
}
figcaption {
  margin-bottom: 4px;
}
svg {
  display: block;
  overflow: visible;
}
</style>

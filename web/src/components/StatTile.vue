<script setup lang="ts">
import { computed } from 'vue'
import type { Series } from '@/types/results'
import SparkLine from '@/components/charts/SparkLine.vue'

const props = defineProps<{
  label: string
  unit: string
  series: Series
  q: number
  hue: string
  format: (v: number | null | undefined) => string
  zero: boolean
  expanded: boolean
}>()
defineEmits<{ toggle: [] }>()

const value = computed(() => props.series.p50[props.q])
const band = computed(() => {
  const lo = props.series.p10?.[props.q]
  const hi = props.series.p90?.[props.q]
  return lo != null && hi != null ? `[${props.format(lo)}, ${props.format(hi)}]` : ''
})
</script>

<template>
  <button
    class="tile card"
    :class="{ expanded }"
    :aria-expanded="expanded"
    @click="$emit('toggle')"
  >
    <div class="head">
      <span class="label">{{ label }}</span>
      <span class="chev" aria-hidden="true">{{ expanded ? '▾' : '▸' }}</span>
    </div>
    <div class="value">
      {{ format(value) }}
      <span v-if="band" class="band mono">{{ band }}</span>
    </div>
    <div class="unit">{{ unit }}</div>
    <SparkLine :series="series" :q="q" :hue="hue" :zero="zero" />
  </button>
</template>

<style scoped>
.tile {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px 10px;
  text-align: left;
  cursor: pointer;
  width: 100%;
  transition: border-color var(--t);
}
.tile:hover,
.tile.expanded {
  border-color: var(--ink-2);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.label {
  font-size: 14px;
  color: var(--ink-2);
  font-weight: 600;
}
.chev {
  color: var(--muted);
  font-size: 14px;
}
.value {
  font-size: 30px;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.01em;
}
.band {
  font-size: 14px;
  color: var(--ink-2);
  font-weight: 500;
  margin-left: 6px;
}
.unit {
  font-size: 14px;
  color: var(--muted);
  margin-bottom: 4px;
}
</style>

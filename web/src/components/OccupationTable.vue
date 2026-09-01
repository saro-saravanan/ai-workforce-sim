<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ScatterPoint } from '@/components/charts/OccupationScatter.vue'
import { fmtCompact, fmtShare, fmtPct, fmtUsd } from '@/lib/format'
import { MAJOR_GROUPS } from '@/lib/metrics'

const props = defineProps<{ points: ScatterPoint[]; q: number; quarterLabel: string }>()

type Col = 'title' | 'group' | 'emp0' | 'wage0' | 'x' | 'y' | 'gap' | 'emp'
const cols: Array<{ key: Col; label: string; num?: boolean }> = [
  { key: 'title', label: 'Occupation' },
  { key: 'group', label: 'Group' },
  { key: 'emp0', label: 'Employment 2023', num: true },
  { key: 'wage0', label: 'Wage 2023', num: true },
  { key: 'x', label: 'Automatable share', num: true },
  { key: 'y', label: 'Displaced', num: true },
  { key: 'gap', label: 'Gap (x − y)', num: true },
  { key: 'emp', label: 'Employment vs baseline', num: true },
]
const sortKey = ref<Col>('gap')
const sortDir = ref<1 | -1>(-1)

function val(p: ScatterPoint, k: Col): number | string {
  switch (k) {
    case 'title':
      return p.occ.title
    case 'group':
      return MAJOR_GROUPS[p.occ.major_group] ?? p.occ.major_group
    case 'emp0':
      return p.occ.emp0
    case 'wage0':
      return p.occ.wage0
    case 'x':
      return p.x
    case 'y':
      return p.y
    case 'gap':
      return p.gap
    case 'emp':
      return p.occ.employment_pct_vs_baseline.p50[props.q] ?? 0
  }
}
function fmt(p: ScatterPoint, k: Col): string {
  const v = val(p, k)
  if (typeof v === 'string') return v
  switch (k) {
    case 'emp0':
      return fmtCompact(v)
    case 'wage0':
      return fmtUsd(v)
    case 'x':
      return fmtShare(v)
    case 'y':
    case 'gap':
      return fmtShare(v, 1)
    case 'emp':
      return fmtPct(v)
    default:
      return String(v)
  }
}
const sorted = computed(() =>
  [...props.points].sort((a, b) => {
    const va = val(a, sortKey.value)
    const vb = val(b, sortKey.value)
    const c =
      typeof va === 'string' || typeof vb === 'string'
        ? String(va).localeCompare(String(vb))
        : va - vb
    return c * sortDir.value
  }),
)
function sortBy(k: Col) {
  if (sortKey.value === k) sortDir.value = sortDir.value === 1 ? -1 : 1
  else {
    sortKey.value = k
    sortDir.value = k === 'title' || k === 'group' ? 1 : -1
  }
}
defineExpose({ sortBy })
</script>

<template>
  <div class="table-wrap card">
    <table class="data">
      <thead>
        <tr>
          <th
            v-for="c in cols"
            :key="c.key"
            :class="{ num: c.num }"
            :aria-sort="
              sortKey === c.key ? (sortDir === 1 ? 'ascending' : 'descending') : undefined
            "
            scope="col"
            @click="sortBy(c.key)"
          >
            {{ c.key === 'y' ? `Displaced by ${quarterLabel}` : c.label }}
            <span v-if="sortKey === c.key" aria-hidden="true">{{ sortDir === 1 ? '↑' : '↓' }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in sorted" :key="p.occ.occ_code">
          <td v-for="c in cols" :key="c.key" :class="{ num: c.num }">{{ fmt(p, c.key) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow: auto;
  max-height: 100%;
  min-height: 0;
}
</style>

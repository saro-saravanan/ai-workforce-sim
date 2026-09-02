<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { RouterLink, useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import type { OutlookResponse } from '@/types/story'
import * as api from '@/api/client'
import { useResultsStore } from '@/stores/results'
import { useRegionStore } from '@/stores/region'
import { AGE_BANDS, AGE_LABELS } from '@/lib/outlook'
import { pct1, regionName } from '@/lib/story'
import { pyFixed, pySigned } from '@/lib/plain'
import { fmtCompact } from '@/lib/format'
import StoryBeat from '@/components/story/StoryBeat.vue'

const results = useResultsStore()
const regionStore = useRegionStore()
const route = useRoute()
const router = useRouter()

const str = (v: unknown) => (typeof v === 'string' ? v : Array.isArray(v) ? String(v[0] ?? '') : '')
/** `occ=` and `age=` in the URL, so an outlook can be shared */
const occ = ref<string>(str(route.query.occ))
const age = ref<string>(
  (AGE_BANDS as readonly string[]).includes(str(route.query.age)) ? str(route.query.age) : '',
)
watch(
  () => [route.query.occ, route.query.age],
  ([o, a]) => {
    occ.value = str(o)
    age.value = (AGE_BANDS as readonly string[]).includes(str(a)) ? str(a) : ''
  },
)
watch([occ, age], ([o, a]) => {
  if (o === str(route.query.occ) && a === str(route.query.age)) return
  const query: LocationQueryRaw = { ...route.query, occ: o || undefined, age: a || undefined }
  for (const k of Object.keys(query)) if (query[k] === undefined) delete query[k]
  router.replace({ query })
})

const filter = ref('')
const occupations = computed(() =>
  [...results.occupations]
    .sort((a, b) => a.title.localeCompare(b.title))
    .filter((o) => !filter.value || o.title.toLowerCase().includes(filter.value.toLowerCase())),
)
const region = computed(() => api.storyRegion(regionStore.region))

const outlook = shallowRef<OutlookResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
let seq = 0
watch(
  () => [results.doc, region.value, occ.value, age.value] as const,
  async ([doc, r, o, a]) => {
    const my = ++seq
    if (!doc) {
      outlook.value = null
      return
    }
    loading.value = true
    error.value = null
    try {
      const res = await api.fetchOutlook(doc, o || null, a || null, r)
      if (my === seq) outlook.value = res
    } catch (e) {
      if (my === seq) {
        outlook.value = null
        error.value = (e as Error).message
      }
    } finally {
      if (my === seq) loading.value = false
    }
  },
  { immediate: true },
)

const occCard = computed(() => outlook.value?.occupation ?? null)
const taskSplit = computed(() => {
  const t = occCard.value?.task_hours_automated_2040
  if (!t) return null
  const sw = Math.max(0, Math.min(100, t.software))
  const mc = Math.max(0, Math.min(100 - sw, t.machines))
  return { software: sw, machines: mc, people: Math.max(0, 100 - sw - mc) }
})
const legend = computed(() => Object.entries(outlook.value?.sureness_legend ?? {}))
</script>

<template>
  <article class="outlook">
    <header class="head">
      <div class="titles">
        <h2>Your outlook</h2>
        <p class="lede">
          What this run says for one occupation and one age group in {{ regionName(region) }}, by
          2040, versus a world in which AI stopped improving in 2023.
        </p>
      </div>
      <RouterLink class="btn link" :to="{ path: '/story', query: $route.query }"
        >Back to the story</RouterLink
      >
    </header>

    <section class="card picks">
      <label class="pick occ">
        <span class="muted">Occupation</span>
        <input
          v-model="filter"
          class="filter"
          type="search"
          placeholder="Filter by name…"
          aria-label="Filter occupations"
        />
        <select v-model="occ" class="select" aria-label="Occupation">
          <option value="">— pick an occupation —</option>
          <option v-for="o in occupations" :key="o.occ_code" :value="o.occ_code">
            {{ o.title }}
          </option>
        </select>
      </label>
      <label class="pick">
        <span class="muted">Age</span>
        <select v-model="age" class="select" aria-label="Age band">
          <option value="">— pick an age band —</option>
          <option v-for="b in AGE_BANDS" :key="b" :value="b">{{ AGE_LABELS[b] }}</option>
        </select>
      </label>
      <span v-if="loading" class="muted">Working…</span>
    </section>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="outlook?.note" class="chart-note">{{ outlook.note }}</p>

    <section v-if="occCard" class="card person" data-card="occupation">
      <div class="verdict">{{ occCard.verdict }}</div>
      <h3>{{ occCard.title }}</h3>
      <p class="sentence">{{ occCard.sentence }}</p>
      <dl class="stats">
        <div>
          <dt>Jobs by 2030</dt>
          <dd class="mono">{{ pct1(occCard.employment_pct_2030, 0) }}</dd>
        </div>
        <div>
          <dt>Jobs by 2040</dt>
          <dd class="mono">
            {{ pct1(occCard.employment_pct_2040, 0) }}
            <span class="muted range"
              >likely {{ pySigned(occCard.range_2040[0]) }}% to
              {{ pySigned(occCard.range_2040[1]) }}%</span
            >
          </dd>
        </div>
        <div>
          <dt>Real pay by 2040</dt>
          <dd class="mono">{{ pct1(occCard.real_wage_pct_2040, 0) }}</dd>
        </div>
        <div>
          <dt>Workers today</dt>
          <dd class="mono">{{ fmtCompact(occCard.employment_2024) }}</dd>
        </div>
      </dl>
      <div v-if="taskSplit" class="split">
        <div class="split-head">
          <span
            >Task-hours automated by 2040:
            {{ pyFixed(taskSplit.software + taskSplit.machines) }}%</span
          >
          <span class="muted">{{ occCard.how }}</span>
        </div>
        <div
          class="bar"
          role="img"
          :aria-label="`${pyFixed(taskSplit.software)}% software, ${pyFixed(taskSplit.machines)}% machines and vehicles`"
        >
          <span class="seg software" :style="{ width: taskSplit.software + '%' }"></span>
          <span class="seg machines" :style="{ width: taskSplit.machines + '%' }"></span>
        </div>
        <div class="split-legend">
          <span><span class="sw software"></span>software {{ pyFixed(taskSplit.software) }}%</span>
          <span
            ><span class="sw machines"></span>machines and vehicles
            {{ pyFixed(taskSplit.machines) }}%</span
          >
          <span
            ><span class="sw people"></span>still done by people
            {{ pyFixed(taskSplit.people) }}%</span
          >
        </div>
      </div>
      <div v-if="occCard.growing_nearby.length" class="nearby">
        <h4>Growing nearby (same occupation family)</h4>
        <ul>
          <li v-for="[title, v] in occCard.growing_nearby" :key="title">
            <span>{{ title }}</span>
            <span class="mono muted">{{ pct1(v, 0) }}</span>
          </li>
        </ul>
      </div>
    </section>
    <p v-else-if="occ && outlook && !loading" class="muted">No occupation {{ occ }} in this run.</p>

    <section v-if="outlook?.age" class="card person" data-card="age">
      <div class="verdict small">{{ AGE_LABELS[outlook.age.band] ?? outlook.age.band }}</div>
      <p class="sentence">{{ outlook.age.sentence }}</p>
    </section>

    <p v-if="!occ && !age" class="muted empty">
      Pick an occupation and an age band to see your outlook.
    </p>

    <template v-if="outlook?.beats.length">
      <h3 class="sub">The bigger picture</h3>
      <StoryBeat v-for="(b, i) in outlook.beats" :key="b.id" :beat="b" :index="i + 1" compact />
      <p class="muted legend">
        How sure:
        <template v-for="([level, [label, n]], i) in legend" :key="level">
          <span>{{ '●'.repeat(n) }}{{ '○'.repeat(3 - n) }} {{ label }}</span
          ><span v-if="i < legend.length - 1"> · </span>
        </template>
      </p>
    </template>
  </article>
</template>

<style scoped>
.outlook {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 24px;
  min-width: 0;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  flex-wrap: wrap;
}
.head h2 {
  font-size: 22px;
  margin-bottom: 4px;
}
.lede {
  margin: 0;
  color: var(--ink-2);
  font-size: 15px;
}
.btn.link {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.picks {
  padding: 12px 16px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: flex-end;
  font-size: 14px;
}
.pick {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.pick.occ {
  flex: 1 1 320px;
}
.pick .select {
  max-width: 100%;
}
.filter {
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 14px;
}
.person {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.verdict {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.1;
}
.verdict.small {
  font-size: 18px;
}
.person h3 {
  font-size: 15px;
  color: var(--ink-2);
  font-weight: 500;
}
.sentence {
  margin: 0;
  line-height: 1.55;
  max-width: 78ch;
}
.stats {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px 16px;
  font-size: 14px;
}
.stats dt {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.stats dd {
  margin: 0;
  font-weight: 600;
  font-size: 18px;
}
.stats .range {
  display: block;
  font-size: 12px;
  font-weight: 400;
}
.split {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}
.split-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.bar {
  display: flex;
  height: 14px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--grid);
}
.seg.software,
.sw.software {
  background: var(--accent);
}
.seg.machines,
.sw.machines {
  background: #eb6834;
}
.sw.people {
  background: var(--grid);
}
.split-legend {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: var(--ink-2);
  font-size: 13px;
}
.split-legend > span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.sw {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.nearby h4 {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.nearby ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 14px;
  max-width: 480px;
}
.nearby li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.sub {
  margin-top: 6px;
  font-size: 15px;
  color: var(--ink-2);
}
.legend {
  margin: 0;
  font-size: 13px;
}
.empty {
  padding: 20px;
  text-align: center;
}
.error {
  background: var(--warn-bg);
  color: var(--warn-ink);
  padding: 8px 12px;
  border-radius: 6px;
}
</style>

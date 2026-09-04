<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { VIEWS } from '@/router'
import { useResultsStore } from '@/stores/results'
import { REGION_OPTIONS, useRegionStore } from '@/stores/region'
import { REGION_NAMES, isRegionId } from '@/types/results'
import { useToastStore } from '@/stores/toast'
import * as api from '@/api/client'
import { briefHtml } from '@/lib/insights'
import ThemeToggle from '@/components/ThemeToggle.vue'

const results = useResultsStore()
const regionStore = useRegionStore()
const toast = useToastStore()

// ----- Export brief (contracts §16–17) -----
const briefOpen = ref(false)
const briefBusy = ref(false)
const briefHash = computed(() => results.doc?.meta.scenario_hash ?? null)
const compareHash = computed(() => results.docB?.meta.scenario_hash ?? null)
/** the brief is per series block; World aggregates client-side only, so it reports the U.S. */
const briefRegion = computed(() => (regionStore.isWorld ? 'US' : regionStore.region))
const briefRegionName = computed(() =>
  isRegionId(briefRegion.value) ? REGION_NAMES[briefRegion.value] : briefRegion.value,
)
function briefTitle() {
  return `${results.scenarioName} — brief`
}
async function briefMarkdown() {
  return api.fetchBriefMarkdown(
    briefHash.value!,
    briefRegion.value,
    compareHash.value,
    results.doc,
    results.docB,
  )
}
async function exportMarkdown() {
  if (!briefHash.value) return
  briefOpen.value = false
  briefBusy.value = true
  try {
    const md = await briefMarkdown()
    const url = URL.createObjectURL(new Blob([md], { type: 'text/markdown;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `${results.scenarioId}-brief.md`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
  } catch (e) {
    toast.push(`Brief: ${(e as Error).message}`, 'warn')
  } finally {
    briefBusy.value = false
  }
}
async function openHtml() {
  if (!briefHash.value) return
  briefOpen.value = false
  if (!api.USE_MOCK && !api.USE_STATIC) {
    window.open(api.briefUrl(briefHash.value, 'html', briefRegion.value, compareHash.value), '_blank', 'noopener')
    return
  }
  // no server: the exporter's brief when one matches this request (static mode), else the
  // client-side brief rendered into a self-contained page
  briefBusy.value = true
  try {
    const file = await api.staticBriefFile(briefHash.value, 'html', briefRegion.value, compareHash.value)
    if (file) {
      window.open(file, '_blank', 'noopener')
      return
    }
    const html = briefHtml(await briefMarkdown(), briefTitle())
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }))
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (e) {
    toast.push(`Brief: ${(e as Error).message}`, 'warn')
  } finally {
    briefBusy.value = false
  }
}
function onMenuKey(e: KeyboardEvent) {
  if (e.key === 'Escape') briefOpen.value = false
}
defineProps<{ explainOpen: boolean; leversOpen: boolean }>()
defineEmits<{ toggleExplain: []; toggleLevers: [] }>()

const groups = computed(() => [
  { label: 'Scenarios', items: results.scenarios.filter((s) => !s.preset && !s.user) },
  { label: 'Report presets', items: results.scenarios.filter((s) => s.preset) },
  { label: 'Saved', items: results.scenarios.filter((s) => s.user) },
])

function onScenario(e: Event) {
  results.scenarioId = (e.target as HTMLSelectElement).value
}
/** World, then the ten regions; regions absent from the run stay listed but are marked. */
const regionOptions = computed(() =>
  REGION_OPTIONS.map((o) => ({
    ...o,
    missing: o.id !== 'world' && results.doc != null && !results.regionIds.includes(o.id),
  })),
)
function onRegion(e: Event) {
  regionStore.setRegion((e.target as HTMLSelectElement).value)
}
</script>

<template>
  <header class="topbar">
    <div class="row">
      <div class="brand">
        <span class="dot" aria-hidden="true"></span>
        <h1>AI Workforce Sim</h1>
        <span class="muted sub">10 regions · 2024–2040 · vs no-AI baseline</span>
      </div>
      <label class="scenario">
        <span class="muted">Scenario</span>
        <select
          class="select"
          :value="results.scenarioId"
          :disabled="results.loading"
          @change="onScenario"
        >
          <template v-for="g in groups" :key="g.label">
            <optgroup v-if="g.items.length" :label="g.label">
              <option v-for="s in g.items" :key="s.id" :value="s.id">{{ s.name }}</option>
            </optgroup>
          </template>
          <option
            v-if="!results.scenarios.some((s) => s.id === results.scenarioId)"
            :value="results.scenarioId"
          >
            {{ results.scenarioId }}
          </option>
        </select>
      </label>
      <label class="scenario region">
        <span class="muted">Region</span>
        <select
          class="select"
          :value="regionStore.region"
          aria-label="Region"
          title="region= in the URL; every view reads this region's series"
          @change="onRegion"
        >
          <option v-for="o in regionOptions" :key="o.id" :value="o.id">
            {{ o.label }}{{ o.missing ? ' (not in run)' : '' }}
          </option>
        </select>
      </label>
      <button class="btn" :aria-pressed="leversOpen" @click="$emit('toggleLevers')">
        What if
      </button>
      <RouterLink class="btn link compare-link" :to="{ path: '/compare', query: $route.query }">Compare</RouterLink>
      <div class="menu-wrap" @keydown="onMenuKey">
        <button
          class="btn"
          aria-haspopup="menu"
          :aria-expanded="briefOpen"
          :disabled="!briefHash || briefBusy"
          :title="
            briefHash
              ? `Export the technical brief for ${results.scenarioName}${compareHash ? ' with the compare run' : ''}`
              : 'No run to brief yet'
          "
          @click="briefOpen = !briefOpen"
        >
          {{ briefBusy ? 'Exporting…' : 'Export' }} <span aria-hidden="true">▾</span>
        </button>
        <div v-if="briefOpen" class="menu-scrim" @click="briefOpen = false"></div>
        <div v-if="briefOpen" class="menu card" role="menu" aria-label="Export">
          <p class="muted hint top">
            Technical brief: the headline table with its bands, what changed against the parent,
            the three top findings, the model notes, the sensitivities, the regions and the
            scenario as JSON.
          </p>
          <button class="item" role="menuitem" @click="openHtml">Technical brief · open as a page</button>
          <button class="item" role="menuitem" @click="exportMarkdown">Technical brief · download Markdown</button>
          <RouterLink
            class="item"
            role="menuitem"
            :to="{ path: '/story', query: $route.query }"
            @click="briefOpen = false"
            >Executive brief · on the Story view</RouterLink
          >
          <p class="muted hint">
            {{ briefRegionName }}{{ regionStore.isWorld ? ' (World reads the U.S. ledger)' : '' }} ·
            {{ results.scenarioName }}{{ compareHash ? ` vs ${results.compareName}` : '' }}
          </p>
        </div>
      </div>
      <span v-if="results.loading" class="muted running">Running…</span>
      <span v-if="results.isMock" class="badge fixture" title="VITE_USE_MOCK=1: synthetic data"
        >mock data</span
      >
      <RouterLink
        v-else-if="results.isStatic"
        class="badge static"
        :to="{ path: '/about', query: $route.query, hash: '#static-demo' }"
        title="Precomputed runs from the static export, no server: scenarios, regions, quarters and briefs work; new lever values, saving and Ask need the local API. About explains."
        >static demo · precomputed runs</RouterLink
      >
      <div class="spacer"></div>
      <ThemeToggle />
      <button class="btn" :aria-pressed="explainOpen" @click="$emit('toggleExplain')">
        Explain
      </button>
    </div>
    <nav class="row tabs" aria-label="Views">
      <RouterLink
        v-for="v in VIEWS"
        :key="v.name"
        :to="{ path: v.path, query: $route.query }"
        class="tab"
        active-class="active"
      >
        {{ v.label }}<sup v-if="v.phase > 2" class="muted" title="Later phase">{{ v.phase }}</sup>
      </RouterLink>
    </nav>
  </header>
</template>

<style scoped>
.topbar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 8px 16px 0;
}
.row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.brand h1 {
  font-size: 17px;
}
.brand .sub {
  font-size: 14px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent);
  align-self: center;
}
.scenario {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.spacer {
  flex: 1;
}
.tabs {
  gap: 2px;
  margin-top: 6px;
}
.tab {
  padding: 8px 12px;
  color: var(--ink-2);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  font-size: 14px;
  font-weight: 500;
}
.tab:hover {
  color: var(--ink);
}
.tab.active {
  color: var(--ink);
  border-bottom-color: var(--ink);
}
.tab.later {
  color: var(--muted);
}
.btn.link {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.menu-wrap {
  position: relative;
}
.menu-scrim {
  position: fixed;
  inset: 0;
  z-index: 24;
}
.menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 25;
  width: 330px;
  max-width: calc(100vw - 24px);
  padding: 4px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
}
.menu .item {
  border: 0;
  background: transparent;
  text-align: left;
  padding: 7px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.menu .item:hover {
  background: var(--surface-2);
}
.menu .item.router-link-active,
.menu a.item {
  text-decoration: none;
  display: block;
}
.menu .hint.top {
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
  margin-bottom: 4px;
}
.menu .hint {
  margin: 4px 10px 4px;
  font-size: 13px;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.badge.static {
  background: var(--surface-2);
  color: var(--ink-2);
  border: 1px solid var(--border);
  text-decoration: none;
}
.badge.static:hover {
  color: var(--ink);
  text-decoration: underline;
}
.tab sup {
  font-size: 10px;
  margin-left: 2px;
}
@media (max-width: 720px) {
  .topbar {
    padding: 6px 10px 0;
  }
  .row {
    gap: 6px 8px;
  }
  .brand .sub,
  .btn.link.compare-link,
  .badge.static,
  .running {
    display: none;
  }
  .brand h1 {
    font-size: 15px;
  }
  .scenario {
    flex: 1 1 100%;
    min-width: 0;
  }
  .scenario.region {
    flex: 1 1 auto;
  }
  .scenario .select {
    flex: 1;
    min-width: 0;
    max-width: 100%;
  }
  .tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    margin-top: 2px;
  }
  .tabs::-webkit-scrollbar {
    display: none;
  }
  .tab {
    padding: 8px 9px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .btn {
    padding: 5px 9px;
  }
}
</style>

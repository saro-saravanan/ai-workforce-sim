<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { VIEWS } from '@/router'
import { useResultsStore } from '@/stores/results'
import ThemeToggle from '@/components/ThemeToggle.vue'

const results = useResultsStore()
defineProps<{ explainOpen: boolean }>()
defineEmits<{ toggleExplain: [] }>()

function onScenario(e: Event) {
  results.scenarioId = (e.target as HTMLSelectElement).value
}
</script>

<template>
  <header class="topbar">
    <div class="row">
      <div class="brand">
        <span class="dot" aria-hidden="true"></span>
        <h1>AI Workforce Sim</h1>
        <span class="muted sub">U.S. 2024–2040 · vs no-AI baseline</span>
      </div>
      <label class="scenario">
        <span class="muted">Scenario</span>
        <select
          class="select"
          :value="results.scenarioId"
          :disabled="results.loading"
          @change="onScenario"
        >
          <option v-for="s in results.scenarios" :key="s.id" :value="s.id">{{ s.name }}</option>
          <option v-if="results.scenarios.length === 0" :value="results.scenarioId">
            {{ results.scenarioId }}
          </option>
        </select>
      </label>
      <span v-if="results.loading" class="muted">Running…</span>
      <span v-if="results.isMock" class="badge fixture" title="VITE_USE_MOCK=1: synthetic data"
        >mock data</span
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
        :class="{ later: v.phase > 1 }"
        active-class="active"
      >
        {{ v.label }}<sup v-if="v.phase > 1" class="muted" title="Phase 2">2</sup>
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
.tab sup {
  font-size: 10px;
  margin-left: 2px;
}
</style>

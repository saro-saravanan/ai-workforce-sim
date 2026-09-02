<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import type { ScenarioDocument } from '@/types/results'
import TopBar from '@/components/TopBar.vue'
import ExplainPanel from '@/components/ExplainPanel.vue'
import TimeScrubber from '@/components/TimeScrubber.vue'
import LeversDrawer from '@/components/LeversDrawer.vue'
import ToastStack from '@/components/ToastStack.vue'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { useThemeStore } from '@/stores/theme'
import { useUrlSync } from '@/composables/useUrlSync'
import { VIEWS } from '@/router'

const results = useResultsStore()
const scrubber = useScrubberStore()
useThemeStore()
useUrlSync()
const router = useRouter()

const explainOpen = ref(
  (() => {
    try {
      return localStorage.getItem('aiwsim.explain') !== '0'
    } catch {
      return true
    }
  })(),
)
const leversOpen = ref(false)
/** a chat proposal handed to the levers drawer by its Edit button (Phase 4) */
const leversPreset = shallowRef<ScenarioDocument | null>(null)
function editProposal(doc: ScenarioDocument) {
  leversPreset.value = doc
  leversOpen.value = true
}
function closeLevers() {
  leversOpen.value = false
  leversPreset.value = null
}
function toggleExplain() {
  explainOpen.value = !explainOpen.value
  try {
    localStorage.setItem('aiwsim.explain', explainOpen.value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

watch(
  () => results.quarters.length,
  (n) => scrubber.setLength(n),
  { immediate: true },
)
watch(
  () => results.scenarioId,
  (id) => results.runScenario(id),
  { immediate: true },
)

function onKey(e: KeyboardEvent) {
  const t = e.target as HTMLElement | null
  const tag = t?.tagName
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || t?.isContentEditable) return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    scrubber.pause()
    scrubber.step(e.shiftKey ? -4 : -1)
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    scrubber.pause()
    scrubber.step(e.shiftKey ? 4 : 1)
  } else if (e.key === ' ' && tag !== 'BUTTON' && t?.getAttribute('role') !== 'button') {
    e.preventDefault()
    scrubber.toggle()
  } else if (/^[1-7]$/.test(e.key) && !e.metaKey && !e.ctrlKey && !e.altKey) {
    const v = VIEWS[Number(e.key) - 1]
    if (v) router.push({ path: v.path, query: router.currentRoute.value.query })
  }
}
onMounted(() => {
  window.addEventListener('keydown', onKey)
  results.loadScenarios()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="shell">
    <TopBar
      :explain-open="explainOpen"
      :levers-open="leversOpen"
      @toggle-explain="toggleExplain"
      @toggle-levers="leversOpen = !leversOpen"
    />
    <div class="body">
      <main class="main" :class="{ stale: results.loading && results.doc }">
        <p v-if="results.error" class="error" role="alert">{{ results.error }}</p>
        <RouterView v-if="results.doc" />
        <p v-else-if="!results.error" class="muted loading">Loading results…</p>
      </main>
      <ExplainPanel :open="explainOpen" @toggle="toggleExplain" @edit="editProposal" />
    </div>
    <TimeScrubber />
    <LeversDrawer :open="leversOpen" :preset="leversPreset" @close="closeLevers" />
    <ToastStack />
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-rows: auto 1fr auto;
  grid-template-columns: minmax(0, 1fr);
  height: 100%;
  min-height: 0;
}
.body {
  display: flex;
  min-height: 0;
  min-width: 0;
}
.main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  padding: 14px 16px;
  transition: opacity var(--t);
}
.main.stale {
  opacity: 0.6;
}
.error {
  background: var(--warn-bg);
  color: var(--warn-ink);
  padding: 8px 12px;
  border-radius: 6px;
}
.loading {
  padding: 40px;
  text-align: center;
}
</style>

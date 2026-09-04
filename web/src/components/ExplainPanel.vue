<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useResultsStore } from '@/stores/results'
import { useScrubberStore } from '@/stores/scrubber'
import { HEADLINE_METRICS, type ScenarioDocument, type TraceKey } from '@/types/results'
import { HEADLINE_LABELS, TRACE_LABELS } from '@/lib/metrics'
import { fmtLeverValue } from '@/lib/levers'
import { referenceQuarter } from '@/lib/confidence'
import { quarterLabel } from '@/lib/format'
import ConfidenceGlyph from '@/components/ConfidenceGlyph.vue'
import ChatPanel from '@/components/ChatPanel.vue'

const results = useResultsStore()
const scrubber = useScrubberStore()
const chat = useChatStore()
defineProps<{ open: boolean }>()
defineEmits<{ toggle: []; edit: [doc: ScenarioDocument] }>()

/** The panel's mode (contracts §17: Explain · Ask), remembered per browser. */
type PanelTab = 'explain' | 'ask'
const TAB_KEY = 'aiwsim.panel'
const tab = ref<PanelTab>(
  (() => {
    try {
      return localStorage.getItem(TAB_KEY) === 'ask' ? 'ask' : 'explain'
    } catch {
      return 'explain'
    }
  })(),
)
function setTab(t: PanelTab) {
  tab.value = t
  try {
    localStorage.setItem(TAB_KEY, t)
  } catch {
    /* ignore */
  }
}
/** Ask exists only when the API server reports a model (ANTHROPIC_API_KEY set); until the status is known the tab stays hidden */
const askAvailable = computed(() => chat.status?.available === true)
onMounted(() => {
  if (!chat.status) void chat.loadStatus()
})
watch(
  () => chat.status,
  (s) => {
    if (s && !s.available && tab.value === 'ask') tab.value = 'explain'
  },
  { immediate: true },
)

const refQ = computed(() => referenceQuarter(results.quarters, scrubber.q))
const traceRows = computed(() => {
  const t = results.trace.employment_pct_vs_baseline?.[refQ.value]
  if (!t) return []
  return (Object.keys(TRACE_LABELS) as TraceKey[]).map((k) => ({ k, label: TRACE_LABELS[k], v: t[k] }))
})
</script>

<template>
  <aside
    class="explain"
    :class="{ open, ask: tab === 'ask' }"
    :aria-label="askAvailable ? 'Explain and Ask' : 'Explain'"
  >
    <button
      v-if="!open"
      class="rail"
      :title="askAvailable ? 'Open the Explain · Ask panel' : 'Open the Explain panel'"
      :aria-label="askAvailable ? 'Open the Explain and Ask panel' : 'Open the Explain panel'"
      @click="$emit('toggle')"
    >
      <span class="rail-label">{{ askAvailable ? 'Explain · Ask' : 'Explain' }}</span>
    </button>
    <template v-else>
      <div class="head">
        <div class="seg" role="tablist" aria-label="Panel mode">
          <button
            class="btn"
            role="tab"
            :aria-selected="tab === 'explain'"
            :aria-pressed="tab === 'explain'"
            @click="setTab('explain')"
          >
            Explain
          </button>
          <button
            v-if="askAvailable"
            class="btn"
            role="tab"
            :aria-selected="tab === 'ask'"
            :aria-pressed="tab === 'ask'"
            @click="setTab('ask')"
          >
            Ask
          </button>
        </div>
        <button class="btn" aria-label="Collapse panel" @click="$emit('toggle')">›</button>
      </div>
      <ChatPanel v-if="tab === 'ask' && askAvailable" @edit="$emit('edit', $event)" />
      <template v-else>
      <p class="muted small">Notes generated from the mechanism trace, no free text from an LLM.</p>
      <ol v-if="results.notes.length" class="notes">
        <li v-for="(n, i) in results.notes" :key="i">{{ n }}</li>
      </ol>
      <p v-else class="muted">No notes for this run.</p>

      <h3 class="sub">Confidence at {{ quarterLabel(refQ) }}</h3>
      <ul class="conf-list small">
        <li v-for="m in HEADLINE_METRICS" :key="m">
          <ConfidenceGlyph :confidence="results.confidenceAt(m, refQ)" :at="refQ" with-label />
          <span>{{ HEADLINE_LABELS[m] }}</span>
        </li>
      </ul>

      <h3 class="sub">Diff vs parent <span class="muted">({{ results.diff.length }})</span></h3>
      <p v-if="!results.diff.length" class="muted small">No parent, or identical to it.</p>
      <ul v-else class="diff small">
        <li v-for="d in results.diff" :key="d.path">
          <code>{{ d.path.replace(/^levers\./, '') }}</code>
          <span class="mono">{{ fmtLeverValue(d.from) }} → <strong>{{ fmtLeverValue(d.to) }}</strong></span>
          <span v-if="d.mechanism" class="muted">{{ d.mechanism }}</span>
        </li>
      </ul>

      <template v-if="traceRows.length">
        <h3 class="sub">Trace, net employment, {{ quarterLabel(refQ) }}</h3>
        <dl class="meta small">
          <template v-for="r in traceRows" :key="r.k">
            <dt>{{ r.label }}</dt>
            <dd class="mono">{{ r.v }}</dd>
          </template>
        </dl>
      </template>
      <h3 class="sub">Run</h3>
      <dl v-if="results.meta" class="meta small">
        <dt>Scenario</dt>
        <dd>{{ results.meta.scenario_id }}</dd>
        <dt>Ensemble</dt>
        <dd>
          {{ results.meta.ensemble }} · {{ results.meta.draws }} draw{{
            results.meta.draws === 1 ? '' : 's'
          }}
        </dd>
        <dt>Data flags</dt>
        <dd>
          <span v-for="(v, k) in results.meta.data_flags" :key="k" class="flag"
            >{{ k }}: {{ v }}</span
          >
        </dd>
      </dl>
      </template>
    </template>
  </aside>
</template>

<style scoped>
.explain {
  background: var(--surface);
  border-left: 1px solid var(--border);
  width: 44px;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: width var(--t);
}
.explain.open {
  width: 320px;
  padding: 12px 14px;
  overflow: auto;
}
/* the Ask tab scrolls its own transcript and keeps the composer at the bottom */
.explain.open.ask {
  width: 380px;
  overflow: hidden;
}
/* phones and narrow tablets: a bottom sheet over the content instead of a docked column; the rail is hidden (the top bar's
   Explain button opens it) so the main column keeps the full width */
@media (max-width: 720px) {
  .explain {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    width: auto;
    max-height: 62%;
    border-left: 0;
    border-top: 1px solid var(--border);
    box-shadow: var(--shadow);
    z-index: 20;
    transition: none;
  }
  .explain:not(.open) {
    display: none;
  }
  .explain.open,
  .explain.open.ask {
    width: auto;
  }
}
.head .seg .btn {
  padding: 5px 12px;
}
.rail {
  flex: 1;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: var(--ink-2);
}
.rail:hover {
  background: var(--surface-2);
}
.rail-label {
  writing-mode: vertical-rl;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.small {
  font-size: 14px;
}
.notes {
  padding-left: 20px;
  margin: 8px 0 14px;
  font-size: 14px;
  display: grid;
  gap: 8px;
}
.meta {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  margin: 0;
  color: var(--ink-2);
}
.meta dt {
  font-weight: 600;
}
.meta dd {
  margin: 0;
}
.flag {
  display: block;
}
.sub {
  margin: 12px 0 4px;
  font-size: 14px;
}
.conf-list,
.diff {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.conf-list li {
  display: flex;
  align-items: center;
  gap: 8px;
}
.diff li {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.diff code {
  font-size: 13px;
  background: var(--surface-2);
  padding: 1px 6px;
  border-radius: 4px;
  align-self: flex-start;
}
</style>

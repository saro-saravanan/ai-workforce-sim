<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useChatStore, type TranscriptMessage } from '@/stores/chat'
import { useResultsStore } from '@/stores/results'
import { useRegionStore } from '@/stores/region'
import * as api from '@/api/client'
import type { ChatMode, Insight } from '@/types/chat'
import type { Confidence, HeadlineMetric, ScenarioDocument } from '@/types/results'
import { HEADLINE_METRICS } from '@/types/results'
import { renderMarkdown } from '@/lib/markdown'
import { fmtLeverValue } from '@/lib/levers'
import { CONFIDENCE_GLYPH } from '@/lib/confidence'
import ConfidenceGlyph from '@/components/ConfidenceGlyph.vue'

const emit = defineEmits<{ edit: [doc: ScenarioDocument] }>()
const chat = useChatStore()
const results = useResultsStore()
const regionStore = useRegionStore()
const route = useRoute()

// the store stays router-agnostic; the panel tells it which view is open (chat context)
watch(
  () => route.name,
  (n) => (chat.view = typeof n === 'string' ? n : ''),
  { immediate: true },
)
onMounted(() => {
  if (!chat.status) void chat.loadStatus()
  void results.loadLevers() // lever labels for proposal cards
})

const draft = ref('')
const listEl = ref<HTMLElement | null>(null)

// ----- insight cards (deterministic, no model) -----
const insights = ref<Insight[]>([])
const insightsLoading = ref(false)
const insightsError = ref<string | null>(null)
const expanded = ref<Record<string, boolean>>({})
const hash = computed(() => results.doc?.meta.scenario_hash ?? null)
/** World has no series block on the server; the U.S. is the reference region. */
const insightRegion = computed(() => (regionStore.isWorld ? 'US' : regionStore.region))
watch(
  [hash, insightRegion],
  async ([h, r]) => {
    if (!h) {
      insights.value = []
      return
    }
    insightsLoading.value = true
    insightsError.value = null
    try {
      const res = await api.fetchInsights(h, r, 3, results.doc)
      if (hash.value === h && insightRegion.value === r) insights.value = res.top
    } catch (e) {
      insightsError.value = (e as Error).message
    } finally {
      insightsLoading.value = false
    }
  },
  { immediate: true },
)
/** Reuse the run's own classification when the insight inherits it; else a plain glyph. */
function confidenceFor(c: Insight): Confidence | undefined {
  const m = c.metric as HeadlineMetric | null
  if (!m || !(HEADLINE_METRICS as string[]).includes(m)) return undefined
  const byQ = results.confidence[m]
  const conf = byQ?.[c.quarter] ?? byQ?.['2040Q4']
  return conf && conf.level === c.confidence ? conf : undefined
}
function glyphFor(c: Insight): string {
  return (CONFIDENCE_GLYPH as Record<string, string>)[c.confidence] ?? '·'
}
function onCard(c: Insight) {
  if (chat.available) void chat.send(`Explain: ${c.title}`, 'explain')
  else expanded.value = { ...expanded.value, [c.key]: !expanded.value[c.key] }
}

// ----- transcript -----
const canSend = computed(() => chat.available && !chat.pending)
const compareReady = computed(() => !!results.docB)
function scrollToEnd() {
  void nextTick(() => listEl.value?.scrollTo({ top: listEl.value.scrollHeight }))
}
watch(
  () => [chat.messages.length, chat.pending] as const,
  () => scrollToEnd(),
)
async function submit() {
  const t = draft.value
  if (!t.trim() || !canSend.value) return
  draft.value = ''
  await chat.send(t, 'chat')
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    void submit()
  }
}
function chip(text: string, mode: ChatMode) {
  if (canSend.value) void chat.send(text, mode)
}
function leverLabel(path: string): string {
  return results.levers.find((l) => l.path === path)?.label ?? path.replace(/^levers\./, '')
}
function run(m: TranscriptMessage) {
  if (m.proposal) void chat.confirm(m.proposal.proposal_id)
}
function setCurrent(m: TranscriptMessage) {
  if (m.proposal) void chat.confirm(m.proposal.proposal_id, 'current')
}
function edit(m: TranscriptMessage) {
  if (m.proposal) emit('edit', m.proposal.scenario)
}
const shortHash = (h: string) => h.replace(/^sha256:/, '').slice(0, 10)
</script>

<template>
  <section class="chat" aria-label="Ask">
    <p v-if="chat.unavailableReason" class="notice small" role="status">
      Ask is unavailable: {{ chat.unavailableReason }} The findings below need no model.
    </p>

    <div ref="listEl" class="list">
      <template v-if="!chat.messages.length">
        <p class="muted small intro">
          Ask about this run. Every number in a reply comes from a tool call on the same results the
          views read; the model never computes.
        </p>
        <h3 class="sub">
          Top findings <span class="muted">· {{ insightRegion }}</span>
        </h3>
        <p v-if="insightsLoading && !insights.length" class="muted small">Ranking findings…</p>
        <p v-else-if="insightsError" class="err small">{{ insightsError }}</p>
        <p v-else-if="!insights.length" class="muted small">No findings for this run.</p>
        <article
          v-for="c in insights"
          :key="c.key"
          class="insight card"
          role="button"
          tabindex="0"
          :title="chat.available ? 'Ask the model to explain this finding' : 'Show the evidence'"
          @click="onCard(c)"
          @keydown.enter.prevent="onCard(c)"
        >
          <div class="insight-head">
            <ConfidenceGlyph
              v-if="confidenceFor(c)"
              :confidence="confidenceFor(c)"
              :at="c.quarter"
            />
            <span
              v-else
              class="glyph"
              :class="c.confidence"
              :title="`${c.confidence} confidence (model classification)`"
              aria-hidden="true"
              >{{ glyphFor(c) }}</span
            >
            <strong>{{ c.title }}</strong>
          </div>
          <p class="stmt">{{ c.statement }}</p>
          <p class="mech muted">{{ c.mechanism }}</p>
          <div class="surprise" :title="`surprise ${c.surprise}`" aria-hidden="true">
            <span :style="{ width: `${Math.round(c.surprise * 100)}%` }"></span>
          </div>
          <details v-if="!chat.available" :open="expanded[c.key] === true" @click.stop>
            <summary class="muted small">Evidence</summary>
            <pre class="evidence">{{ JSON.stringify(c.evidence, null, 2) }}</pre>
          </details>
        </article>
      </template>

      <div v-for="m in chat.messages" :key="m.id" class="msg" :class="m.role">
        <p v-if="m.role === 'user'" class="bubble">{{ m.content }}</p>
        <template v-else>
          <p v-if="m.pending" class="muted small pending">
            <span class="spinner" aria-hidden="true"></span> Thinking…
          </p>
          <p v-else-if="m.error" class="err small">{{ m.error }}</p>
          <div v-else class="md" v-html="renderMarkdown(m.content)"></div>
          <details v-if="m.toolCalls?.length" class="tools small">
            <summary>
              Grounded by {{ m.toolCalls.length }} tool call{{
                m.toolCalls.length === 1 ? '' : 's'
              }}
            </summary>
            <ul>
              <li v-for="(t, i) in m.toolCalls" :key="i">
                <code>{{ t.name }}</code>
                <span class="status" :class="t.ok ? 'ok' : 'bad'">{{ t.ok ? 'ok' : 'error' }}</span>
                <span class="muted">{{ t.summary }}</span>
              </li>
            </ul>
          </details>

          <div v-if="m.proposal" class="proposal card">
            <div class="p-head">
              <strong>{{ m.proposal.scenario.name }}</strong>
              <span class="muted small">child of {{ m.proposal.parent }}</span>
            </div>
            <table class="diff-table small">
              <thead>
                <tr>
                  <th>Lever</th>
                  <th>From → To</th>
                  <th>Mechanism</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in m.proposal.diff" :key="d.path">
                  <td>{{ leverLabel(d.path) }}</td>
                  <td class="mono nowrap">
                    {{ fmtLeverValue(d.from) }} → <strong>{{ fmtLeverValue(d.to) }}</strong>
                  </td>
                  <td class="muted">{{ d.mechanism }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="m.proposal.rationale" class="muted small rationale">
              {{ m.proposal.rationale }}
            </p>
            <div class="p-actions">
              <template v-if="!m.ran">
                <button class="btn primary" :disabled="m.running" @click="run(m)">
                  <span v-if="m.running" class="spinner light" aria-hidden="true"></span>
                  {{ m.running ? 'Running…' : 'Run' }}
                </button>
                <button class="btn" :disabled="m.running" @click="edit(m)">Edit</button>
                <span class="muted small"
                  >Run makes it
                  {{ results.doc ? 'the compare scenario (B)' : 'the current scenario' }}.</span
                >
              </template>
              <template v-else>
                <span class="small ran">
                  Ran → <code>{{ shortHash(m.ran.scenario_hash) }}</code> ·
                  {{
                    m.ran.as === 'compare'
                      ? 'set as the compare scenario (B)'
                      : 'set as the current scenario'
                  }}
                </span>
                <RouterLink
                  v-if="m.ran.as === 'compare'"
                  class="btn link"
                  :to="{ path: '/compare', query: $route.query }"
                  >Open Compare</RouterLink
                >
                <button
                  v-if="m.ran.as === 'compare'"
                  class="btn"
                  :disabled="m.running"
                  @click="setCurrent(m)"
                >
                  {{ m.running ? 'Switching…' : 'Set as current' }}
                </button>
                <button class="btn" :disabled="m.running" @click="edit(m)">Edit</button>
              </template>
            </div>
          </div>
          <p v-if="m.runs?.length" class="muted small">
            Runs this turn:
            <span v-for="r in m.runs" :key="r.scenario_hash" class="run-chip">{{
              r.scenario_name ?? r.scenario_id ?? shortHash(r.scenario_hash)
            }}</span>
          </p>
        </template>
      </div>
    </div>

    <div class="chips" aria-label="Quick actions">
      <button
        class="btn chip"
        :disabled="!canSend"
        @click="chip('Explain the current metric at the current quarter', 'explain')"
      >
        Explain this metric
      </button>
      <button
        class="btn chip"
        :disabled="!canSend"
        @click="chip('What is surprising in this run?', 'insights')"
      >
        What's surprising?
      </button>
      <button
        v-if="compareReady"
        class="btn chip"
        :disabled="!canSend"
        @click="chip(`Compare ${results.scenarioName} (A) with ${results.compareName} (B)`, 'chat')"
      >
        Compare A vs B
      </button>
      <button
        v-if="chat.messages.length"
        class="btn chip"
        :disabled="chat.pending"
        title="Clear the transcript"
        @click="chat.clear()"
      >
        Clear
      </button>
    </div>
    <form class="composer" @submit.prevent="submit">
      <textarea
        v-model="draft"
        class="input"
        rows="2"
        aria-label="Message"
        :placeholder="
          chat.available
            ? 'Ask about this run… (Enter sends, Shift+Enter for a new line)'
            : 'Chat unavailable'
        "
        :disabled="!canSend"
        @keydown="onKey"
      ></textarea>
      <button class="btn primary" type="submit" :disabled="!canSend || !draft.trim()">
        {{ chat.pending ? '…' : 'Send' }}
      </button>
    </form>
    <p v-if="chat.error" class="err small" role="alert">{{ chat.error }}</p>
  </section>
</template>

<style scoped>
.chat {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.small {
  font-size: 14px;
}
.sub {
  margin: 8px 0 2px;
  font-size: 14px;
}
.intro {
  margin: 0;
}
.notice {
  margin: 0;
  background: var(--warn-bg);
  color: var(--warn-ink);
  padding: 6px 10px;
  border-radius: 6px;
}
.err {
  color: var(--warn-ink);
  background: var(--warn-bg);
  padding: 4px 8px;
  border-radius: 6px;
  margin: 0;
}
.list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 2px;
}

/* insight cards */
.insight {
  padding: 10px 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  transition: background var(--t);
}
.insight:hover {
  background: var(--surface-2);
}
.insight-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.glyph {
  font-size: 16px;
  line-height: 1;
  color: var(--ink-2);
}
.glyph.low {
  color: var(--muted);
}
.stmt {
  margin: 0;
}
.mech {
  margin: 0;
  font-size: 13px;
}
.surprise {
  height: 3px;
  background: var(--grid);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 4px;
}
.surprise span {
  display: block;
  height: 100%;
  background: var(--accent);
}
.evidence {
  margin: 4px 0 0;
  font-size: 12px;
  white-space: pre-wrap;
  background: var(--surface-2);
  padding: 6px 8px;
  border-radius: 4px;
  max-height: 200px;
  overflow: auto;
}

/* messages */
.msg {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
}
.msg.user {
  align-items: flex-end;
}
.bubble {
  margin: 0;
  max-width: 88%;
  background: var(--surface-2);
  color: var(--ink-2);
  padding: 6px 10px;
  border-radius: 10px 10px 2px 10px;
  white-space: pre-wrap;
}
.pending {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.md :deep(p) {
  margin: 0 0 8px;
}
.md :deep(p:last-child) {
  margin-bottom: 0;
}
.md :deep(.md-h) {
  margin-top: 6px;
}
.md :deep(ul),
.md :deep(ol) {
  margin: 0 0 8px;
  padding-left: 20px;
}
.md :deep(li) {
  margin: 2px 0;
}
.md :deep(code) {
  font-size: 13px;
  background: var(--surface-2);
  padding: 1px 5px;
  border-radius: 4px;
}
.md :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 4px 0 8px;
  font-size: 13px;
}
.md :deep(th),
.md :deep(td) {
  text-align: left;
  vertical-align: top;
  padding: 3px 6px;
  border-bottom: 1px solid var(--grid);
}
.md :deep(th) {
  font-weight: 600;
  color: var(--ink-2);
}
.tools summary {
  cursor: pointer;
  color: var(--muted);
}
.tools ul {
  list-style: none;
  padding: 0;
  margin: 4px 0 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tools li {
  display: flex;
  gap: 6px;
  align-items: baseline;
  flex-wrap: wrap;
  font-size: 13px;
}
.tools code {
  font-size: 12px;
  background: var(--surface-2);
  padding: 1px 5px;
  border-radius: 4px;
}
.status.ok {
  color: var(--ink-2);
}
.status.bad {
  color: var(--warn-ink);
  font-weight: 600;
}

/* proposal card */
.proposal {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-left: 3px solid var(--accent);
}
.p-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: baseline;
  flex-wrap: wrap;
}
.diff-table {
  border-collapse: collapse;
  width: 100%;
}
.diff-table th,
.diff-table td {
  text-align: left;
  vertical-align: top;
  padding: 3px 6px 3px 0;
  border-bottom: 1px solid var(--grid);
}
.diff-table th {
  font-weight: 600;
  color: var(--ink-2);
}
.diff-table td.muted {
  font-size: 13px;
}
.nowrap {
  white-space: nowrap;
}
.rationale {
  margin: 0;
}
.p-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ran code {
  font-size: 12px;
  background: var(--surface-2);
  padding: 1px 5px;
  border-radius: 4px;
}
.run-chip {
  display: inline-block;
  margin-left: 6px;
  background: var(--surface-2);
  padding: 0 6px;
  border-radius: 999px;
}

/* composer */
.chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.btn.chip {
  padding: 3px 10px;
  font-size: 13px;
  border-radius: 999px;
}
.composer {
  display: flex;
  gap: 6px;
  align-items: flex-end;
}
.input {
  flex: 1;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--ink);
  border-radius: 6px;
  padding: 6px 10px;
  font: inherit;
  font-size: 14px;
  resize: vertical;
  min-height: 40px;
  min-width: 0;
}
.input:disabled {
  opacity: 0.6;
}
.btn.primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.btn.link {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--border);
  border-top-color: var(--ink);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: -2px;
}
.spinner.light {
  border-color: rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none;
  }
}
</style>

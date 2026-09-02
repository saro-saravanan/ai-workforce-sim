import { defineStore } from 'pinia'
import { computed, markRaw, ref } from 'vue'
import * as api from '@/api/client'
import type { ResultsDocument } from '@/types/results'
import type { ChatContext, ChatMode, ChatRun, ChatStatus, Proposal, ToolCall } from '@/types/chat'
import { useResultsStore } from '@/stores/results'
import { useRegionStore } from '@/stores/region'
import { useScrubberStore } from '@/stores/scrubber'
import { useToastStore } from '@/stores/toast'

/** Where a confirmed proposal's run went (contracts §17: current or compare scenario). */
export type RunSlot = 'current' | 'compare'

export interface TranscriptMessage {
  id: number
  role: 'user' | 'assistant'
  /** markdown for assistant turns, plain text for the user's */
  content: string
  toolCalls?: ToolCall[]
  proposal?: Proposal | null
  runs?: ChatRun[]
  /** the proposal has been run through the results store */
  ran?: { scenario_hash: string; scenario_id: string; as: RunSlot }
  /** the results document of that run, kept so the slot can be switched without re-running */
  runDoc?: ResultsDocument
  running?: boolean
  /** assistant placeholder while the request is in flight */
  pending?: boolean
  error?: string
}

/** The transcript is in memory only (this session); at most this many turns are sent per request. */
export const MAX_TURNS = 40

export const useChatStore = defineStore('chat', () => {
  const results = useResultsStore()
  const regionStore = useRegionStore()
  const scrubber = useScrubberStore()

  const messages = ref<TranscriptMessage[]>([])
  const status = ref<ChatStatus | null>(null)
  const pending = ref(false)
  const error = ref<string | null>(null)
  /** the current view name; the panel keeps it in step with the router (the store stays router-agnostic) */
  const view = ref('')
  const confirmedProposals = ref<string[]>([])
  let nextId = 1

  const available = computed(() => status.value?.available === true)
  const unavailableReason = computed(() =>
    status.value && !status.value.available
      ? (status.value.reason ?? 'The chat layer is not available on this API server.')
      : null,
  )

  /** Current UI state, the default for every tool call (contracts §15). World has no series block: US. */
  const context = computed<ChatContext>(() => {
    const d = results.doc
    const b = results.docB
    return {
      scenario_hash: d?.meta.scenario_hash,
      scenario_id: results.scenarioId,
      compare_hash: b?.meta.scenario_hash,
      compare_id: results.compareId ?? undefined,
      region: regionStore.isWorld ? 'US' : regionStore.region,
      quarter: results.quarters[scrubber.q],
      view: view.value || undefined,
    }
  })

  async function loadStatus() {
    try {
      status.value = await api.fetchChatStatus()
    } catch (e) {
      status.value = { available: false, model: '', reason: (e as Error).message }
    }
    return status.value
  }

  /** Text-only visible transcript, last turn the user's. */
  function transcript() {
    return messages.value
      .filter((m) => !m.pending && !m.error && m.content)
      .map((m) => ({ role: m.role, content: m.content }))
      .slice(-MAX_TURNS)
  }

  async function send(text: string, mode: ChatMode = 'chat') {
    const t = text.trim()
    if (!t || pending.value) return null
    error.value = null
    messages.value.push({ id: nextId++, role: 'user', content: t })
    const placeholderId = nextId++
    messages.value.push({ id: placeholderId, role: 'assistant', content: '', pending: true })
    pending.value = true
    try {
      const res = await api.sendChat(
        {
          messages: transcript(),
          context: context.value,
          confirmed_proposals: [...confirmedProposals.value],
          mode,
        },
        results.doc,
      )
      const m = messages.value.find((x) => x.id === placeholderId)
      if (m) {
        m.pending = false
        m.content = res.reply
        m.toolCalls = res.tool_calls
        m.proposal = res.proposed_scenario
        m.runs = res.runs
      }
      return res
    } catch (e) {
      const msg = (e as Error).message
      const m = messages.value.find((x) => x.id === placeholderId)
      if (m) {
        m.pending = false
        m.error = msg
      }
      error.value = msg
      useToastStore().push(`Chat: ${msg}`, 'warn')
      return null
    } finally {
      pending.value = false
    }
  }

  /**
   * Runs a proposed scenario through the results store. With a current run it becomes the compare
   * scenario (B); without one it becomes the current run. The proposal id is then sent as confirmed.
   */
  async function confirm(proposalId: string, as?: RunSlot) {
    const m = messages.value.find((x) => x.proposal?.proposal_id === proposalId)
    if (!m?.proposal || m.running) return null
    const slot: RunSlot = as ?? (results.doc ? 'compare' : 'current')
    m.running = true
    try {
      const run = m.runDoc
        ? await results.adoptRun(m.runDoc, m.proposal.scenario, slot)
        : await results.runProposal(m.proposal.scenario, slot)
      if (!run) throw new Error(results.error ?? 'the run failed')
      if (!confirmedProposals.value.includes(proposalId)) confirmedProposals.value.push(proposalId)
      m.runDoc = markRaw(run)
      m.ran = {
        scenario_hash: run.meta.scenario_hash,
        scenario_id: m.proposal.scenario.id,
        as: slot,
      }
      return m.ran
    } catch (e) {
      const msg = (e as Error).message
      error.value = msg
      useToastStore().push(`Run failed: ${msg}`, 'warn')
      return null
    } finally {
      m.running = false
    }
  }

  function clear() {
    messages.value = []
    error.value = null
  }

  return {
    messages,
    status,
    pending,
    error,
    view,
    confirmedProposals,
    available,
    unavailableReason,
    context,
    loadStatus,
    transcript,
    send,
    confirm,
    clear,
  }
})

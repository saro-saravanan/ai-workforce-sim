/**
 * Chat layer, insights and briefs (Phase 4), hand-written from docs/contracts.md §15–17.
 * The chat layer never computes: every number in a reply comes from a tool call the reply lists.
 */
import type { DiffEntry, ScenarioDocument } from '@/types/results'

export type ChatRole = 'user' | 'assistant'
export type ChatMode = 'chat' | 'explain' | 'insights'

export interface ChatMessage {
  role: ChatRole
  content: string
}

/** The current UI state; the default for every tool call the model makes. */
export interface ChatContext {
  scenario_hash?: string
  scenario_id?: string
  compare_hash?: string
  compare_id?: string
  region?: string
  quarter?: string
  view?: string
}

/** POST /api/chat */
export interface ChatRequest {
  messages: ChatMessage[]
  context: ChatContext
  confirmed_proposals: string[]
  mode: ChatMode
}

export interface ToolCall {
  name: string
  input: Record<string, unknown>
  ok: boolean
  seconds: number
  summary: string
}

/** A validated, not yet run, child scenario the model proposes. */
export interface Proposal {
  proposal_id: string
  scenario: ScenarioDocument
  diff: DiffEntry[]
  parent: string
  rationale: string
}

export interface ChatRun {
  scenario_hash: string
  scenario_id: string | null
  scenario_name: string | null
}

export interface ChatResponse {
  /** markdown */
  reply: string
  tool_calls: ToolCall[]
  proposed_scenario: Proposal | null
  proposals: Proposal[]
  runs: ChatRun[]
  usage: { input_tokens: number; output_tokens: number }
  model: string
  stop_reason: string | null
}

/** GET /api/chat/status */
export interface ChatStatus {
  available: boolean
  model: string
  reason?: string | null
}

export type InsightConfidence = 'high' | 'medium' | 'low' | 'n/a' | string

/** One deterministic candidate finding (contracts §16). */
export interface Insight {
  key: string
  title: string
  statement: string
  mechanism: string
  confidence: InsightConfidence
  /** 0–1, how far the finding sits from a naive prior */
  surprise: number
  evidence: Record<string, unknown>
  metric: string | null
  quarter: string
  region: string
}

/** GET /api/insights/{hash} */
export interface InsightsResponse {
  scenario_hash: string
  scenario_id?: string | null
  region: string
  top: Insight[]
  candidates: Insight[]
  method: string
}

export type BriefFormat = 'md' | 'html' | 'json'

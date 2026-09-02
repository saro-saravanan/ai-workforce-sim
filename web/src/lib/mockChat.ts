/**
 * Canned, deterministic chat replies for mock mode (`VITE_USE_MOCK=1`): no model, no numbers
 * outside the results document. The real app posts to /api/chat (contracts §15).
 */
import type { ResultsDocument, ScenarioDocument, DiffEntry } from '@/types/results'
import type { ChatRequest, ChatResponse, Insight, Proposal, ToolCall } from '@/types/chat'
import { candidateInsights } from '@/lib/insights'
import { quarterLabel } from '@/lib/format'

const CAN = [
  'explain a headline metric at the current quarter (mode `explain`)',
  'list what is surprising in the current run (ask "what is surprising?")',
  'propose a what-if scenario (try "what if capability doubles every 4 months")',
]

function call(name: string, input: Record<string, unknown>, summary: string, ok = true): ToolCall {
  return { name, input, ok, seconds: 0, summary }
}

function insightsReply(top: Insight[]): string {
  if (!top.length) return 'The mock has no insight candidates for this document.'
  return (
    'The three findings that sit furthest from a naive prior in this run:\n\n' +
    top
      .map(
        (c, i) =>
          `${i + 1}. **${c.title}.** ${c.statement}\n   *Mechanism:* ${c.mechanism} *Confidence:* ${c.confidence}.`,
      )
      .join('\n\n')
  )
}

function proposal(parent: string): Proposal {
  const diff: DiffEntry[] = [
    {
      path: 'levers.capability.doubling_months',
      from: 5,
      to: 4,
      mechanism:
        'Sets the global frontier clock (§3.2); shorter doubling brings every task threshold forward.',
    },
  ]
  const scenario: ScenarioDocument = {
    schema_version: '0.2',
    id: 'faster-capability-4mo',
    name: 'Faster capability (4-month doubling)',
    description: 'What-if from the chat: capability doubling time 5 → 4 months.',
    parent,
    levers: { capability: { doubling_months: 4 } },
    ensemble: { mechanisms: 'all' },
    user: true,
  }
  return {
    proposal_id: 'prop-mock-4mo',
    scenario,
    diff,
    parent,
    rationale:
      'A 4-month doubling time expresses "capability doubles every 4 months" directly through P.01; nothing else was approximated.',
  }
}

function explainReply(doc: ResultsDocument, ctx: ChatRequest['context']): string {
  const metric = 'employment_pct_vs_baseline'
  const region = ctx.region ?? 'US'
  const q = ctx.quarter ?? doc.meta.quarters[doc.meta.quarters.length - 1] ?? ''
  const i = doc.meta.quarters.indexOf(q)
  const s = doc.series[region]?.[metric] ?? doc.series.US?.[metric]
  if (!s || i < 0) return 'The mock cannot explain this metric at this quarter.'
  const f = (v: number | undefined) => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`)
  const ref = q > '2030Q4' ? '2040Q4' : '2030Q4'
  const conf = doc.confidence?.[metric]?.[ref]
  return (
    `Net employment in ${region} at ${quarterLabel(q)} is **${f(s.p50[i])}** vs the frozen-AI baseline` +
    (s.p10 && s.p90 ? ` (10–90 band ${f(s.p10[i])} to ${f(s.p90[i])})` : '') +
    `. Mechanism: task automation lowers unit costs (spec §5.2) and displacement runs through unfilled entry positions before layoffs (spec §5.3).` +
    (conf
      ? ` Sign confidence at ${quarterLabel(ref)} is **${conf.level}**: the sign holds in ${Math.round(conf.sign_share * 100)}% of draws.`
      : '') +
    `\n\n| | value |\n|---|---|\n| median | ${f(s.p50[i])} |\n| p10 | ${f(s.p10?.[i])} |\n| p90 | ${f(s.p90?.[i])} |`
  )
}

export function mockChat(body: ChatRequest, doc: ResultsDocument | null): ChatResponse {
  const last = body.messages[body.messages.length - 1]?.content ?? ''
  const text = last.toLowerCase()
  const hash = doc?.meta.scenario_hash ?? body.context.scenario_hash ?? ''
  const region = body.context.region ?? 'US'
  const base: ChatResponse = {
    reply: '',
    tool_calls: [],
    proposed_scenario: null,
    proposals: [],
    runs: [],
    usage: { input_tokens: 0, output_tokens: 0 },
    model: 'mock',
    stop_reason: 'end_turn',
  }
  const insightTitle = /^explain:\s*(.+)$/i.exec(last.trim())?.[1]?.trim()
  if (insightTitle && doc) {
    const c = candidateInsights(doc, region).find(
      (x) => x.title.toLowerCase() === insightTitle.toLowerCase(),
    )
    if (c)
      return {
        ...base,
        reply: `**${c.title}.** ${c.statement}\n\n*Mechanism:* ${c.mechanism}\n\n*Confidence:* ${c.confidence}.`,
        tool_calls: [
          call(
            'candidate_insights',
            { scenario_hash: hash, region },
            `${candidateInsights(doc, region).length} candidates`,
          ),
        ],
      }
  }
  if (body.mode === 'insights' || text.includes('surpris')) {
    const top = doc ? candidateInsights(doc, region).slice(0, 3) : []
    return {
      ...base,
      reply: insightsReply(top),
      tool_calls: [
        call(
          'candidate_insights',
          { scenario_hash: hash, region },
          `${top.length} of top candidates`,
        ),
      ],
    }
  }
  if (body.mode === 'explain' && doc) {
    return {
      ...base,
      reply: explainReply(doc, body.context),
      tool_calls: [
        call(
          'explain',
          {
            scenario_hash: hash,
            metric: 'employment_pct_vs_baseline',
            quarter: body.context.quarter ?? null,
            region,
          },
          'value, channels, trace, confidence, top_params, notes',
        ),
      ],
    }
  }
  if (text.includes('what if') || text.includes('doubl') || text.includes('delay')) {
    const p = proposal(body.context.scenario_id ?? 'baseline')
    return {
      ...base,
      reply:
        `I read that as a shorter capability doubling time. Proposed child of **${p.parent}**:\n\n` +
        `| Lever | From → To | Mechanism |\n|---|---|---|\n| Capability doubling time | 5 → 4 months | frontier clock (§3.2) |\n\n` +
        `Nothing else was approximated. Confirm to run it (or press **Run** on the card); I will not run it until you do.`,
      tool_calls: [
        call('list_levers', { group: 'capability' }, '8 rows'),
        call(
          'propose_scenario',
          {
            parent: p.parent,
            name: p.scenario.name,
            levers: p.scenario.levers ?? {},
            shocks: [],
            remove_shocks: [],
            rationale: p.rationale,
          },
          `1 lever change(s) validated; proposal ${p.proposal_id}`,
        ),
      ],
      proposed_scenario: p,
      proposals: [p],
    }
  }
  return {
    ...base,
    reply:
      'The mock chat cannot answer that (there is no model behind it in mock mode). It can:\n\n' +
      CAN.map((c) => `- ${c}`).join('\n'),
  }
}

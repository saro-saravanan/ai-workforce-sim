import type {
  CompareResponse,
  ExplainResponse,
  LeverDef,
  ResultsDocument,
  RunResponse,
  ScenarioDocument,
  ScenarioSummary,
  StatesGeoJSON,
  TornadoRow,
  HeadlineMetric,
  WorldGeoJSON,
  RegionRow,
  ActorsResponse,
} from '@/types/results'
import type {
  BriefFormat,
  ChatRequest,
  ChatResponse,
  ChatStatus,
  InsightsResponse,
} from '@/types/chat'
import type { OutlookResponse, StoryDocument } from '@/types/story'
import { pairedCompare } from '@/lib/compare'
import { seriesFor } from '@/lib/world'

export const USE_MOCK =
  import.meta.env.VITE_USE_MOCK === '1' || import.meta.env.VITE_USE_MOCK === 'true'

/**
 * Static mode (contracts §18): no server; every document comes from `${BASE_URL}static/` as
 * written by `python -m aiwsim_api.export_static`. Mock mode wins when both flags are set.
 */
export const USE_STATIC =
  !USE_MOCK && (import.meta.env.VITE_STATIC === '1' || import.meta.env.VITE_STATIC === 'true')

export const REPO_URL = 'https://github.com/saro-saravanan/ai-workforce-sim'
export const STATIC_RUN_MESSAGE =
  'Static demo: running a new scenario needs the local API (make demo). Pick a precomputed scenario instead.'
export const STATIC_SAVE_MESSAGE =
  'Static demo: saving a scenario needs the local API (make demo). Pick a precomputed scenario instead.'
export const STATIC_CHAT_REASON =
  'Static demo: the chat layer needs the local API server with ANTHROPIC_API_KEY set.'

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) throw new Error(`${init?.method ?? 'GET'} ${url} → ${res.status} ${res.statusText}`)
  return (await res.json()) as T
}

function postJson<T>(url: string, body: unknown): Promise<T> {
  return getJson<T>(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/** result hash → scenario id, for the hash-keyed endpoints (compare=, briefs, insights) */
const hashToId = new Map<string, string>()

// ---------- static helpers (contracts §18) ----------

export interface StaticRun {
  id: string
  name: string
  parent: string | null
  description: string
  preset: boolean
  hash: string
  draws: number
  ensemble: string
  file: string
}

export interface StaticManifest {
  generated_at?: string
  spec_version?: string
  data_version?: string
  draws?: number
  runs: StaticRun[]
  /** `a` and `b` are scenario ids; the exporter's compares are for the U.S. series */
  compares?: Array<{ a: string; b: string; file: string; region?: string }>
  levers?: string
  /** the raw scenario documents (a file name, or inline) */
  scenarios?: string | ScenarioDocument[]
  regions?: string
  actors?: string
  geo?: { us_states?: string; world?: string }
  /** keys: `<id>` and `<id>__vs__<a>` */
  insights?: Record<string, string>
  briefs?: Record<string, Partial<Record<BriefFormat, string>>>
  // ---------- Phase 8 (contracts §28) ----------
  /** `<id>` → `story/<id>.json` (the U.S. story, policies against the exported baseline) */
  story?: Record<string, string>
  /** `<id>` → the executive brief files */
  exec_briefs?: Record<string, { md?: string; html?: string }>
  /** the policy scenarios and the named-future scenarios the exporter ran */
  policy_scenarios?: string[]
  future_scenarios?: string[]
}

/** `${BASE_URL}static/<file>`; BASE_URL is `/` or the sub-path (`VITE_BASE`, e.g. `/ai-workforce-sim/`). */
export function staticUrl(file: string): string {
  const base = import.meta.env.BASE_URL || '/'
  return `${base.endsWith('/') ? base : `${base}/`}static/${file.replace(/^\/+/, '')}`
}

let manifestPromise: Promise<StaticManifest> | null = null
let manifestCache: StaticManifest | null = null
let staticScenariosPromise: Promise<ScenarioDocument[]> | null = null

/** The manifest, fetched once per session. */
export function staticManifest(): Promise<StaticManifest> {
  if (!manifestPromise)
    manifestPromise = getJson<StaticManifest>(staticUrl('manifest.json')).then(
      (m) => {
        m.runs ??= []
        manifestCache = m
        for (const r of m.runs) hashToId.set(r.hash, r.id)
        return m
      },
      (e: unknown) => {
        manifestPromise = null
        throw e
      },
    )
  return manifestPromise
}

/** Forgets the cached manifest and scenario list (tests). */
export function resetStaticCache(): void {
  manifestPromise = null
  manifestCache = null
  staticScenariosPromise = null
  hashToId.clear()
}

/** The run listed under a scenario id or a result hash. */
function staticRunOf(m: StaticManifest, ref: string): StaticRun | undefined {
  return m.runs.find((r) => r.id === ref || r.hash === ref)
}

async function staticRun(ref: string): Promise<StaticRun> {
  const run = staticRunOf(await staticManifest(), ref)
  if (!run)
    throw new Error(`Static demo: no precomputed run for "${ref}". Pick a precomputed scenario instead.`)
  return run
}

/** The raw scenario documents the exporter writes beside the runs (`scenarios.json`). */
async function staticScenarioDocs(): Promise<ScenarioDocument[]> {
  const m = await staticManifest()
  if (Array.isArray(m.scenarios)) return m.scenarios
  staticScenariosPromise ??= getJson<ScenarioDocument[]>(
    staticUrl(typeof m.scenarios === 'string' ? m.scenarios : 'scenarios.json'),
  )
  return staticScenariosPromise
}

// ---------- mock helpers ----------

/** Mock scenario summaries come from the scenario documents shipped in src/mock/scenarios.json. */
async function mockScenarioDocs(): Promise<ScenarioDocument[]> {
  const mod = await import('@/mock/scenarios.json')
  return structuredClone(mod.default as unknown as ScenarioDocument[])
}

/** User scenarios saved in mock mode live in memory for the session. */
const mockUserScenarios: ScenarioDocument[] = []

function summarize(s: ScenarioDocument): ScenarioSummary {
  return {
    id: s.id,
    name: s.name,
    parent: s.parent ?? null,
    description: s.description ?? '',
    preset: s.preset === true,
    user: s.user === true,
  }
}

/** The mock has two runs: A (baseline and everything else) and B (the example child scenario). */
async function mockResults(id: string): Promise<ResultsDocument> {
  const isB = id === 'eu-delay-deepseek-2027'
  const mod = isB ? await import('@/mock/results-b.json') : await import('@/mock/results.json')
  const doc = structuredClone(mod.default as unknown as ResultsDocument)
  doc.meta.scenario_id = id
  if (!isB && id !== 'baseline') {
    doc.meta.scenario_hash = `sha256:mock-${id}`
    if (id.startsWith('preset-')) doc.meta.ensemble = 'central'
  }
  return doc
}

// ---------- scenarios ----------

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  if (USE_MOCK) return [...(await mockScenarioDocs()), ...mockUserScenarios].map(summarize)
  if (USE_STATIC)
    return (await staticManifest()).runs.map((r) => ({
      id: r.id,
      name: r.name || r.id,
      parent: r.parent ?? null,
      description: r.description ?? '',
      preset: r.preset === true,
      user: false,
      hash: r.hash,
    }))
  return getJson<ScenarioSummary[]>('/api/scenarios')
}

/** GET /api/scenarios/{id}: the canonical (inheritance-resolved) scenario. */
export async function fetchScenario(id: string): Promise<ScenarioDocument> {
  if (USE_MOCK) {
    const all = [...(await mockScenarioDocs()), ...mockUserScenarios]
    const { resolveScenario } = await import('@/lib/levers')
    const byId = new Map(all.map((s) => [s.id, s]))
    const doc = byId.get(id)
    if (!doc) throw new Error(`mock: unknown scenario ${id}`)
    return resolveScenario(doc, byId)
  }
  if (USE_STATIC) {
    // the exporter writes the raw scenario documents; the manifest run entry (the run's meta)
    // stands in for a scenario the list does not carry, with its ancestors resolved as in mock mode
    const [m, docs] = await Promise.all([staticManifest(), staticScenarioDocs()])
    const { resolveScenario } = await import('@/lib/levers')
    const byId = new Map(docs.map((s) => [s.id, s]))
    let doc = byId.get(id)
    if (!doc) {
      const run = staticRunOf(m, id)
      if (!run) throw new Error(`Static demo: unknown scenario ${id}`)
      doc = {
        schema_version: '0.2',
        id: run.id,
        name: run.name || run.id,
        description: run.description ?? '',
        parent: run.parent ?? null,
        preset: run.preset === true,
        levers: {},
      }
      byId.set(doc.id, doc)
    }
    return resolveScenario(doc, byId)
  }
  return getJson<ScenarioDocument>(`/api/scenarios/${encodeURIComponent(id)}`)
}

/** POST /api/scenarios: saves a child scenario, returns the canonical form. */
export async function saveScenario(doc: ScenarioDocument): Promise<ScenarioDocument> {
  if (USE_MOCK) {
    const i = mockUserScenarios.findIndex((s) => s.id === doc.id)
    const saved = { ...doc, user: true }
    if (i >= 0) mockUserScenarios[i] = saved
    else mockUserScenarios.push(saved)
    return saved
  }
  if (USE_STATIC) throw new Error(STATIC_SAVE_MESSAGE)
  return postJson<ScenarioDocument>('/api/scenarios', doc)
}

// ---------- runs ----------

export async function runScenario(id: string): Promise<ResultsDocument> {
  if (USE_MOCK) return mockResults(id)
  // static: `id` may be a scenario id or a result hash (compare= in the URL, contracts §10)
  if (USE_STATIC) return getJson<ResultsDocument>(staticUrl((await staticRun(id)).file))
  // `compare=` may carry a result hash (contracts §10) as well as a scenario id
  if (id.startsWith('sha256:')) return getJson<ResultsDocument>(`/api/results/${encodeURIComponent(id)}`)
  const run = await postJson<RunResponse>('/api/run', { id })
  hashToId.set(run.scenario_hash, id)
  return getJson<ResultsDocument>(`/api/results/${encodeURIComponent(run.scenario_hash)}`)
}

/** POST /api/run with a full scenario document (a what-if child). */
export async function runScenarioDoc(doc: ScenarioDocument): Promise<ResultsDocument> {
  if (USE_MOCK) {
    // the mock has no engine: reuse the parent's run under the child's id
    const res = await mockResults(doc.parent ?? 'baseline')
    res.meta.scenario_id = doc.id
    res.meta.scenario_hash = `sha256:mock-${doc.id}`
    res.explain.diff = Object.keys(doc.levers ?? {}).length
      ? flattenLevers(doc.levers ?? {}).map(([path, to]) => ({
          path,
          from: undefined,
          to,
          mechanism: 'mock: parent run reused; the backend fills the mechanism',
        }))
      : []
    return res
  }
  if (USE_STATIC) throw new Error(STATIC_RUN_MESSAGE)
  const run = await postJson<RunResponse>('/api/run', doc)
  hashToId.set(run.scenario_hash, doc.id)
  return getJson<ResultsDocument>(`/api/results/${encodeURIComponent(run.scenario_hash)}`)
}

function flattenLevers(obj: Record<string, unknown>, prefix = 'levers'): Array<[string, unknown]> {
  const out: Array<[string, unknown]> = []
  for (const [k, v] of Object.entries(obj)) {
    const p = `${prefix}.${k}`
    if (v && typeof v === 'object' && !Array.isArray(v))
      out.push(...flattenLevers(v as Record<string, unknown>, p))
    else out.push([p, v])
  }
  return out
}

// ---------- Phase 2 endpoints ----------

export async function fetchLevers(): Promise<LeverDef[]> {
  if (USE_MOCK) {
    const mod = await import('@/mock/levers.json')
    return structuredClone(mod.default as unknown as LeverDef[])
  }
  if (USE_STATIC) return getJson<LeverDef[]>(staticUrl((await staticManifest()).levers ?? 'levers.json'))
  return getJson<LeverDef[]>('/api/levers')
}

/**
 * GET /api/compare?a=HASH&b=HASH. In mock mode: paired differences of the two documents for the
 * selected region ('world' aggregates client-side). The API takes an optional `region=`; without
 * it the series delta is the U.S. Static mode uses the exporter's `compare/<a>__<b>.json` when
 * the manifest lists that exact pair for the region (a paired delta cannot be reversed by
 * negation: its percentiles are not symmetric), else the client-side paired difference.
 */
export async function compareRuns(
  a: ResultsDocument,
  b: ResultsDocument,
  region = 'US',
): Promise<CompareResponse> {
  if (USE_MOCK) return pairedCompare(a, b, region)
  if (USE_STATIC) {
    const m = await staticManifest()
    const is = (ref: string, d: ResultsDocument) =>
      ref === d.meta.scenario_id || ref === d.meta.scenario_hash
    const entry = (m.compares ?? []).find(
      (c) => is(c.a, a) && is(c.b, b) && (c.region ?? 'US') === region,
    )
    if (entry) {
      try {
        return await getJson<CompareResponse>(staticUrl(entry.file))
      } catch {
        /* listed but unreadable: the client-side delta is still correct */
      }
    }
    return pairedCompare(a, b, region)
  }
  const qs = new URLSearchParams({ a: a.meta.scenario_hash, b: b.meta.scenario_hash })
  if (region !== 'US') qs.set('region', region)
  return getJson<CompareResponse>(`/api/compare?${qs}`)
}

export async function fetchSensitivity(doc: ResultsDocument): Promise<ResultsDocument['tornado']> {
  if (USE_MOCK || USE_STATIC) return doc.tornado ?? {}
  return getJson<Partial<Record<HeadlineMetric, TornadoRow[]>>>(
    `/api/sensitivity/${encodeURIComponent(doc.meta.scenario_hash)}`,
  )
}

/** The explain response assembled from the document itself (mock and static modes). */
function explainFromDoc(
  doc: ResultsDocument,
  metric: HeadlineMetric,
  quarter: string,
  region: string,
): ExplainResponse | null {
  const i = doc.meta.quarters.indexOf(quarter)
  const s = seriesFor(doc, region)?.[metric]
  if (!s || i < 0) return null
  const ref = quarter >= '2040Q4' ? '2040Q4' : quarter > '2030Q4' ? '2040Q4' : '2030Q4'
  const trace = doc.explain.trace?.[metric]?.[ref]
  const conf = doc.confidence?.[metric]?.[ref]
  if (!trace || !conf) return null
  const ch = doc.channels[metric]
  const channels: ExplainResponse['channels'] = {}
  if (ch) for (const k of ch.order) channels[k] = ch.contributions[k]?.[i]
  return {
    value: { p10: s.p10?.[i], p25: s.p25?.[i], p50: s.p50[i], p75: s.p75?.[i], p90: s.p90?.[i], central: s.central?.[i] },
    channels,
    trace,
    confidence: conf,
    top_params: (doc.tornado?.[metric] ?? []).slice(0, 5),
    notes: doc.explain.notes,
  }
}

export async function fetchExplain(
  doc: ResultsDocument,
  metric: HeadlineMetric,
  quarter: string,
  region = 'US',
): Promise<ExplainResponse | null> {
  if (USE_MOCK || USE_STATIC) return explainFromDoc(doc, metric, quarter, region)
  const qs = new URLSearchParams({ metric, quarter })
  if (region !== 'US') qs.set('region', region)
  return getJson<ExplainResponse>(`/api/explain/${encodeURIComponent(doc.meta.scenario_hash)}?${qs}`)
}

export async function fetchStatesGeo(): Promise<StatesGeoJSON> {
  if (USE_MOCK) {
    const url = (await import('@/mock/us-states.geojson?url')).default
    return getJson<StatesGeoJSON>(url)
  }
  if (USE_STATIC)
    return getJson<StatesGeoJSON>(
      staticUrl((await staticManifest()).geo?.us_states ?? 'geo/us-states.geojson'),
    )
  return getJson<StatesGeoJSON>('/api/geo/us-states')
}

// ---------- Phase 3 endpoints (contracts §13) ----------

/** GET /api/geo/world — Natural Earth 110m admin-0 reduced to {iso3, name, region_id}. */
export async function fetchWorldGeo(): Promise<WorldGeoJSON> {
  if (USE_MOCK) {
    const url = (await import('@/mock/world.geojson?url')).default
    return getJson<WorldGeoJSON>(url)
  }
  if (USE_STATIC)
    return getJson<WorldGeoJSON>(staticUrl((await staticManifest()).geo?.world ?? 'geo/world.geojson'))
  return getJson<WorldGeoJSON>('/api/geo/world')
}

/** GET /api/regions — regions.csv rows. In mock mode: derived from the results document's `regions`. */
export async function fetchRegions(doc?: ResultsDocument | null): Promise<RegionRow[]> {
  if (USE_MOCK) return (doc?.regions ?? []).map((r) => ({ ...r }))
  if (USE_STATIC) return getJson<RegionRow[]>(staticUrl((await staticManifest()).regions ?? 'regions.json'))
  return getJson<RegionRow[]>('/api/regions')
}

/** GET /api/actors — actors and releases. In mock mode: derived from `supply.releases`. */
export async function fetchActors(doc?: ResultsDocument | null): Promise<ActorsResponse> {
  if (USE_MOCK) {
    const releases = doc?.supply?.releases ?? []
    const seen = new Map<string, ActorsResponse['actors'][number]>()
    for (const r of releases)
      if (!seen.has(r.actor_id))
        seen.set(r.actor_id, {
          actor_id: r.actor_id,
          name: r.name,
          region_id: r.region_id,
          role: 'lab',
          weights_posture: r.open_weights ? 'open-lagged' : 'closed',
        })
    return { actors: [...seen.values()], releases }
  }
  if (USE_STATIC) return getJson<ActorsResponse>(staticUrl((await staticManifest()).actors ?? 'actors.json'))
  return getJson<ActorsResponse>('/api/actors')
}

// ---------- Phase 4 endpoints (contracts §15–17) ----------

/** FastAPI puts the reason in `detail`; surface it instead of the bare status line. */
async function fetchOrDetail(url: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(url, init)
  if (res.ok) return res
  let detail = ''
  try {
    const body = (await res.json()) as { detail?: unknown }
    detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? '')
  } catch {
    /* not JSON */
  }
  throw new Error(detail || `${init?.method ?? 'GET'} ${url} → ${res.status} ${res.statusText}`)
}

/** GET /api/chat/status → {available, model, reason}. Mock mode answers with canned replies. */
export async function fetchChatStatus(): Promise<ChatStatus> {
  if (USE_MOCK) return { available: true, model: 'mock' }
  if (USE_STATIC) return { available: false, model: 'none', reason: STATIC_CHAT_REASON }
  return getJson<ChatStatus>('/api/chat/status')
}

/**
 * POST /api/chat. The optional `doc` is read only in mock mode, where the canned replies quote
 * the current results document (lib/mockChat.ts); the server reads its own copy by hash.
 */
export async function sendChat(body: ChatRequest, doc?: ResultsDocument | null): Promise<ChatResponse> {
  if (USE_MOCK) {
    const { mockChat } = await import('@/lib/mockChat')
    return mockChat(body, doc ?? null)
  }
  if (USE_STATIC) throw new Error(STATIC_CHAT_REASON)
  const res = await fetchOrDetail('/api/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  return (await res.json()) as ChatResponse
}

/**
 * GET /api/insights/{hash}?region=&n=[&compare=] — deterministic, no model call. With
 * `compareHash` the ranking also covers what this run changed against run A (paired). Static
 * mode reads `insights/<id>__vs__<a>.json` when the manifest lists it, else `insights/<id>.json`
 * (both are the exporter's U.S. rankings), else the client-side port.
 */
export async function fetchInsights(
  hash: string,
  region = 'US',
  n = 3,
  doc?: ResultsDocument | null,
  compareHash?: string | null,
): Promise<InsightsResponse> {
  if (USE_MOCK) {
    const { mockInsights } = await import('@/lib/insights')
    return mockInsights(doc ?? null, region, n)
  }
  if (USE_STATIC) {
    const m = await staticManifest()
    const id = staticRunOf(m, hash)?.id
    const cmpId = compareHash ? staticRunOf(m, compareHash)?.id : undefined
    const file =
      id && region === 'US'
        ? ((cmpId ? m.insights?.[`${id}__vs__${cmpId}`] : undefined) ?? m.insights?.[id])
        : undefined
    if (file) {
      try {
        const res = await getJson<InsightsResponse>(staticUrl(file))
        return { ...res, top: res.top.slice(0, Math.max(1, n)) }
      } catch {
        /* listed but unreadable: rank client-side */
      }
    }
    const { mockInsights } = await import('@/lib/insights')
    return mockInsights(doc ?? null, region, n)
  }
  const qs = new URLSearchParams({ region, n: String(n) })
  if (compareHash) qs.set('compare', compareHash)
  return getJson<InsightsResponse>(`/api/insights/${encodeURIComponent(hash)}?${qs}`)
}

/**
 * URL of GET /api/brief/{hash}?format=&region=[&compare=] (contracts §16). Static mode: the
 * exporter's `briefs/<id>.<format>` (see `staticBriefFile` for whether it matches the request).
 */
export function briefUrl(
  hash: string,
  format: BriefFormat = 'md',
  region = 'US',
  compareHash?: string | null,
): string {
  if (USE_STATIC) {
    const id = hashToId.get(hash) ?? manifestCache?.runs.find((r) => r.id === hash)?.id ?? hash
    return staticUrl(manifestCache?.briefs?.[id]?.[format] ?? `briefs/${id}.${format}`)
  }
  const qs = new URLSearchParams({ format, region })
  if (compareHash) qs.set('compare', compareHash)
  return `/api/brief/${encodeURIComponent(hash)}?${qs}`
}

/**
 * Static mode: the URL of the precomputed brief when one answers this exact request, else null.
 * The exporter briefs the U.S. series and pairs every non-reference run with the reference run
 * (the `a` of its compare entry), so the file stands for `region=US` with exactly that compare.
 */
export async function staticBriefFile(
  hash: string,
  format: BriefFormat,
  region = 'US',
  compareHash?: string | null,
): Promise<string | null> {
  if (!USE_STATIC) return null
  const m = await staticManifest()
  const id = staticRunOf(m, hash)?.id
  const file = id ? m.briefs?.[id]?.[format] : undefined
  if (!id || !file || region !== 'US') return null
  const fileCompare = (m.compares ?? []).find((c) => c.b === id)?.a ?? null
  const wantCompare = compareHash ? (staticRunOf(m, compareHash)?.id ?? compareHash) : null
  return wantCompare === fileCompare ? staticUrl(file) : null
}

/** The Markdown brief as text. In mock mode: built client-side from the documents (lib/insights.ts). */
export async function fetchBriefMarkdown(
  hash: string,
  region = 'US',
  compareHash?: string | null,
  doc?: ResultsDocument | null,
  docB?: ResultsDocument | null,
): Promise<string> {
  if (USE_MOCK || USE_STATIC) {
    if (USE_STATIC) {
      const url = await staticBriefFile(hash, 'md', region, compareHash)
      if (url) {
        const res = await fetch(url)
        if (res.ok) return res.text()
      }
    }
    if (!doc) throw new Error(`${USE_STATIC ? 'static' : 'mock'}: no results document to brief`)
    const { mockBriefMarkdown } = await import('@/lib/insights')
    return mockBriefMarkdown(doc, region, compareHash ? (docB ?? null) : null)
  }
  const res = await fetchOrDetail(briefUrl(hash, 'md', region, compareHash))
  return res.text()
}

// ---------- Phase 8 endpoints (contracts §26–27) ----------

/**
 * The region the story endpoints take: a series block. World is aggregated client-side only, so
 * the story and the outlook read the U.S. for it.
 */
export function storyRegion(region: string): string {
  return region === 'world' ? 'US' : region
}

/** The mock story (a real baseline story, U.S.) relabelled for the current mock run. */
async function mockStory(doc: ResultsDocument): Promise<StoryDocument> {
  const mod = await import('@/mock/story.json')
  const st = structuredClone(mod.default as unknown as StoryDocument)
  st.scenario_hash = doc.meta.scenario_hash
  st.scenario_id = doc.meta.scenario_id
  st.scenario_name = doc.meta.scenario_name ?? (doc.meta.scenario_id === 'baseline' ? st.scenario_name : null)
  return st
}

/**
 * GET /api/story/{hash}?region= — the story document. Static mode reads the exporter's
 * `story/<id>.json` (the U.S. story; other regions get it too, marked by its `region`); mock
 * mode reads `src/mock/story.json` for every run.
 */
export async function fetchStory(doc: ResultsDocument, region = 'US'): Promise<StoryDocument> {
  const r = storyRegion(region)
  if (USE_MOCK) return mockStory(doc)
  if (USE_STATIC) {
    const m = await staticManifest()
    const id = staticRunOf(m, doc.meta.scenario_hash)?.id ?? doc.meta.scenario_id
    const file = m.story?.[id]
    if (!file)
      throw new Error(`Static demo: no story for "${id}". Pick a precomputed scenario instead.`)
    return getJson<StoryDocument>(staticUrl(file))
  }
  return getJson<StoryDocument>(
    `/api/story/${encodeURIComponent(doc.meta.scenario_hash)}?${new URLSearchParams({ region: r })}`,
  )
}

/**
 * GET /api/outlook/{hash}?occ=&age=&region= — the personal outlook. Static and mock modes
 * compute it client-side from the document (lib/outlook.ts, the same rules as the server) with
 * the beats of the story.
 */
export async function fetchOutlook(
  doc: ResultsDocument,
  occ: string | null | undefined,
  age: string | null | undefined,
  region = 'US',
): Promise<OutlookResponse> {
  const r = storyRegion(region)
  if (USE_MOCK || USE_STATIC) {
    let beats: StoryDocument['beats'] = []
    try {
      beats = (await fetchStory(doc, r)).beats
    } catch {
      /* no story file: the cards still work without the beats */
    }
    const { outlookFromDoc } = await import('@/lib/outlook')
    return outlookFromDoc(doc, occ, age, r, beats)
  }
  const qs = new URLSearchParams({ region: r })
  if (occ) qs.set('occ', occ)
  if (age) qs.set('age', age)
  return getJson<OutlookResponse>(`/api/outlook/${encodeURIComponent(doc.meta.scenario_hash)}?${qs}`)
}

/**
 * URL of the executive brief page (GET /api/brief/{hash}?format=exec-html). Static mode: the
 * exporter's `briefs/<id>.exec.html` once the manifest is known. Null when no page exists for
 * this run (mock mode, or a static run without an exported brief): the view then renders the
 * brief client-side from the story.
 */
export function execBriefUrl(doc: ResultsDocument, region = 'US'): string | null {
  if (USE_MOCK) return null
  if (USE_STATIC) {
    const id = hashToId.get(doc.meta.scenario_hash) ?? doc.meta.scenario_id
    const file = manifestCache?.exec_briefs?.[id]?.html
    return file ? staticUrl(file) : null
  }
  const qs = new URLSearchParams({ format: 'exec-html', region: storyRegion(region) })
  return `/api/brief/${encodeURIComponent(doc.meta.scenario_hash)}?${qs}`
}

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
} from '@/types/results'
import { pairedCompare } from '@/lib/compare'

export const USE_MOCK =
  import.meta.env.VITE_USE_MOCK === '1' || import.meta.env.VITE_USE_MOCK === 'true'

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

const hashToId = new Map<string, string>()

// ---------- scenarios ----------

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  if (USE_MOCK) return [...(await mockScenarioDocs()), ...mockUserScenarios].map(summarize)
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
  return postJson<ScenarioDocument>('/api/scenarios', doc)
}

// ---------- runs ----------

export async function runScenario(id: string): Promise<ResultsDocument> {
  if (USE_MOCK) return mockResults(id)
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
  return getJson<LeverDef[]>('/api/levers')
}

/** GET /api/compare?a=HASH&b=HASH. In mock mode: paired differences of the two documents. */
export async function compareRuns(a: ResultsDocument, b: ResultsDocument): Promise<CompareResponse> {
  if (USE_MOCK) return pairedCompare(a, b)
  const qs = new URLSearchParams({ a: a.meta.scenario_hash, b: b.meta.scenario_hash })
  return getJson<CompareResponse>(`/api/compare?${qs}`)
}

export async function fetchSensitivity(doc: ResultsDocument): Promise<ResultsDocument['tornado']> {
  if (USE_MOCK) return doc.tornado ?? {}
  return getJson<Partial<Record<HeadlineMetric, TornadoRow[]>>>(
    `/api/sensitivity/${encodeURIComponent(doc.meta.scenario_hash)}`,
  )
}

export async function fetchExplain(
  doc: ResultsDocument,
  metric: HeadlineMetric,
  quarter: string,
): Promise<ExplainResponse | null> {
  if (USE_MOCK) {
    const i = doc.meta.quarters.indexOf(quarter)
    const s = doc.series.US?.[metric]
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
  const qs = new URLSearchParams({ metric, quarter })
  return getJson<ExplainResponse>(`/api/explain/${encodeURIComponent(doc.meta.scenario_hash)}?${qs}`)
}

export async function fetchStatesGeo(): Promise<StatesGeoJSON> {
  if (USE_MOCK) {
    const url = (await import('@/mock/us-states.geojson?url')).default
    return getJson<StatesGeoJSON>(url)
  }
  return getJson<StatesGeoJSON>('/api/geo/us-states')
}

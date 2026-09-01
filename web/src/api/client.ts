import type { ResultsDocument, RunResponse, ScenarioSummary, StatesGeoJSON } from '@/types/results'

export const USE_MOCK =
  import.meta.env.VITE_USE_MOCK === '1' || import.meta.env.VITE_USE_MOCK === 'true'

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) throw new Error(`${init?.method ?? 'GET'} ${url} → ${res.status} ${res.statusText}`)
  return (await res.json()) as T
}

const MOCK_SCENARIOS: ScenarioSummary[] = [
  {
    id: 'baseline',
    name: 'Consensus central',
    parent: null,
    description: 'v0.2 defaults; all levers central, no shocks. (mock)',
  },
  {
    id: 'eu-delay-deepseek-2027',
    name: 'EU AI Act delayed 2y + DeepSeek open frontier 2027',
    parent: 'baseline',
    description: 'Example what-if from the brief. (mock: same numbers as baseline)',
  },
]

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  if (USE_MOCK) return MOCK_SCENARIOS
  return getJson<ScenarioSummary[]>('/api/scenarios')
}

export async function runScenario(id: string): Promise<ResultsDocument> {
  if (USE_MOCK) {
    const mod = await import('@/mock/results.json')
    const doc = structuredClone(mod.default as unknown as ResultsDocument)
    doc.meta.scenario_id = id
    return doc
  }
  const run = await getJson<RunResponse>('/api/run', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ id }),
  })
  return getJson<ResultsDocument>(`/api/results/${encodeURIComponent(run.scenario_hash)}`)
}

export async function fetchStatesGeo(): Promise<StatesGeoJSON> {
  if (USE_MOCK) {
    const url = (await import('@/mock/us-states.geojson?url')).default
    return getJson<StatesGeoJSON>(url)
  }
  return getJson<StatesGeoJSON>('/api/geo/us-states')
}
